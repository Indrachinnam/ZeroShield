"""
ZeroShield: FastAPI Backend Application
Provides RESTful APIs and SSE endpoints for network traffic analysis,
alert logging, LOAO metrics, runtime threshold configuration, and static frontend serving.
"""

import os
import sys
import io
import json
import time
from typing import Optional, List
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.inference import engine
from backend.stream_service import stream_simulator
from backend.database import (
    save_alert,
    get_alerts,
    save_scan,
    get_runtime_threshold,
    set_runtime_threshold,
    get_kpi_stats
)
from backend.models import (
    ThresholdUpdateRequest,
    ModelInfoResponse
)

app = FastAPI(
    title="ZeroShield API",
    description="Zero-Day Exploit Detection Using Transformer-Based Network Traffic Classification",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")


# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "ZeroShield", "timestamp": time.time()}


@app.get("/api/model-info", response_model=ModelInfoResponse)
async def get_model_info():
    """Returns architecture, parameters, calibration details, and feature schema."""
    total_params = sum(p.numel() for p in engine.model.parameters()) if engine.model else 0
    cur_threshold = engine.get_effective_threshold()

    return ModelInfoResponse(
        model_name="FlowTransformer",
        architecture="FT-Transformer (Feature Tokenization + 3-Layer Self-Attention + Energy Head)",
        parameters=total_params,
        d_model=64,
        nhead=4,
        num_encoder_layers=3,
        classes=engine.classes,
        calibrated_threshold=engine.calibrated_threshold,
        current_runtime_threshold=cur_threshold,
        calibrated_fpr=0.05,
        test_accuracy=engine.config.get("test_accuracy", 1.0),
        test_macro_f1=engine.config.get("test_macro_f1", 1.0),
        is_synthetic=engine.config.get("is_synthetic", True),
        training_samples=engine.config.get("training_samples", 15000),
        device=engine.device
    )


@app.post("/api/analyze")
async def analyze_flows(
    file: Optional[UploadFile] = File(None),
    threshold: Optional[float] = Form(None)
):
    """
    Accepts CSV upload of flows, runs FlowTransformer inference,
    calculates class probabilities, novelty scores, and assigns verdicts.
    """
    if file is None:
        raise HTTPException(status_code=400, detail="CSV file is required for analysis.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .csv file.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    # Run inference
    analysis = engine.analyze_dataframe(df, override_threshold=threshold)

    # Save alerts into SQLite
    for res in analysis["results"]:
        if res["verdict"] != "Benign":
            try:
                save_alert({
                    "flow_id": res["flow_id"],
                    "verdict": res["verdict"],
                    "attack_class": res["predicted_class"] if res["verdict"] != "Potential Zero-Day" else "Zero-Day Exploit",
                    "novelty_score": res["novelty_score"],
                    "threshold": res["threshold"],
                    "confidence": res["confidence"],
                    "severity": res["severity"],
                    "protocol": res["raw_features"]["protocol"],
                    "dst_port_category": res["raw_features"]["dst_port_category"],
                    "flow_duration": res["raw_features"]["flow_duration"],
                    "total_fwd_packets": res["raw_features"]["total_fwd_packets"],
                    "total_bwd_packets": res["raw_features"]["total_bwd_packets"],
                    "bytes_per_sec": res["raw_features"]["bytes_per_sec"],
                    "packets_per_sec": res["raw_features"]["packets_per_sec"],
                    "features": res["raw_features"],
                    "status": "active"
                })
            except Exception as e:
                print(f"[!] Warning: Failed to save alert: {e}")

    # Record scan history
    save_scan({
        "source": "upload",
        "filename": file.filename,
        "total_flows": analysis["total_flows"],
        "benign_count": analysis["benign_count"],
        "known_attack_count": analysis["known_attack_count"],
        "zero_day_count": analysis["zero_day_count"],
        "avg_latency_ms": analysis["avg_inference_latency_ms"]
    })

    return analysis


@app.get("/api/stream")
async def stream_live_traffic(
    request: Request,
    flows_per_sec: float = Query(2.0, ge=0.5, le=10.0, description="Replay rate in flows/second")
):
    """
    Server-Sent Events endpoint streaming replayed network traffic in real time.
    """
    return EventSourceResponse(stream_simulator.event_generator(flows_per_sec=flows_per_sec))


@app.get("/api/alerts")
async def get_security_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query("all"),
    verdict: Optional[str] = Query("all"),
    search: Optional[str] = Query(None)
):
    """
    Returns paginated alerts with filtering by severity, verdict, and search term.
    """
    alerts, total = get_alerts(
        page=page,
        page_size=page_size,
        severity=severity,
        verdict=verdict,
        search=search
    )
    return {
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "alerts": alerts
    }


@app.get("/api/metrics")
async def get_evaluation_metrics():
    """
    Returns Leave-One-Attack-Out benchmark scores and baseline comparison results.
    """
    eval_file = os.path.join(DATA_DIR, "evaluation_results.json")
    if os.path.exists(eval_file):
        with open(eval_file, "r") as f:
            data = json.load(f)
        return data

    raise HTTPException(status_code=404, detail="Evaluation results not found. Run evaluate.py first.")


@app.post("/api/threshold")
async def update_novelty_threshold(req: ThresholdUpdateRequest):
    """
    Updates the novelty rejection threshold dynamically at runtime.
    """
    set_runtime_threshold(req.threshold)
    return {
        "status": "success",
        "new_threshold": req.threshold,
        "message": f"Runtime novelty threshold updated to {req.threshold:.4f}"
    }


@app.get("/api/stats")
async def get_dashboard_stats():
    """
    Returns KPI statistics (flows analyzed, benign %, known attacks, zero-days, avg latency).
    """
    return get_kpi_stats()


@app.get("/api/sample-csv")
async def download_sample_csv(variant: str = Query("mixed", pattern="^(mixed|benign|zero_day)$")):
    """
    Downloads sample CSV flow files for testing the upload page.
    """
    if variant == "zero_day":
        file_path = os.path.join(DATA_DIR, "sample_zero_days.csv")
    elif variant == "benign":
        # Filter benign from sample flows
        synth_file = os.path.join(DATA_DIR, "synthetic_ids2017.csv")
        df = pd.read_csv(synth_file)
        benign_df = df[df["label"] == "Benign"].head(100)
        file_path = os.path.join(DATA_DIR, "sample_benign.csv")
        benign_df.to_csv(file_path, index=False)
    else:
        file_path = os.path.join(DATA_DIR, "sample_flows.csv")

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/csv", filename=f"zeroshield_{variant}_sample.csv")

    raise HTTPException(status_code=404, detail="Sample CSV not found.")


# =====================================================================
# Serve Frontend Static Assets and SPA
# =====================================================================

if os.path.exists(FRONTEND_DIR):
    # Mount css, js subdirectories
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
