"""
ZeroShield: Inference Engine
Loads trained FlowTransformer weights and scaler, performs high-throughput batch
inference, computes Energy-based novelty scores, and determines security verdicts.
"""

import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ml.model import FlowTransformer
from ml.dataset import (
    KNOWN_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    PROTOCOL_MAP,
    PORT_CATEGORY_MAP,
    preprocess_features
)
from backend.database import get_runtime_threshold

CHECKPOINT_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")


class FlowInferenceEngine:
    """
    Singleton inference engine for real-time and batch network flow classification.
    """
    def __init__(self):
        self.device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model: Optional[FlowTransformer] = None
        self.scaler = None
        self.config: Dict[str, Any] = {}
        self.calibrated_threshold: float = -7.44
        self.classes: List[str] = KNOWN_CLASSES
        self._load_artifacts()

    def _load_artifacts(self):
        config_path = os.path.join(CHECKPOINT_DIR, "config.json")
        scaler_path = os.path.join(CHECKPOINT_DIR, "scaler.joblib")
        weights_path = os.path.join(CHECKPOINT_DIR, "flow_transformer.pt")

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.calibrated_threshold = float(self.config.get("calibrated_threshold", -7.44))
            self.classes = self.config.get("classes", KNOWN_CLASSES)

        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)

        # Initialize model
        cat_cardinalities = [len(PROTOCOL_MAP), len(PORT_CATEGORY_MAP)]
        self.model = FlowTransformer(
            num_numerical=len(NUMERICAL_FEATURES),
            cat_cardinalities=cat_cardinalities,
            num_classes=len(self.classes),
            d_model=64,
            nhead=4,
            num_encoder_layers=3,
            dim_feedforward=128,
            dropout=0.0
        ).to(self.device)

        if os.path.exists(weights_path):
            state_dict = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.eval()
            print(f"[+] Loaded FlowTransformer checkpoint successfully on {self.device}")
        else:
            print("[!] Checkpoint not found; running with initialized weights.")

    def get_effective_threshold(self) -> float:
        """Retrieves runtime threshold from DB or defaults to calibrated threshold."""
        return get_runtime_threshold(default_threshold=self.calibrated_threshold)

    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        override_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Runs batch inference on a DataFrame of network flows.
        Returns detailed predictions, novelty scores, and aggregate stats.
        """
        start_time = time.time()
        effective_threshold = override_threshold if override_threshold is not None else self.get_effective_threshold()

        # Preprocess features
        x_num, x_cat, _ = preprocess_features(df, scaler=self.scaler, fit_scaler=False)

        x_n_tensor = torch.tensor(x_num, dtype=torch.float32).to(self.device)
        x_c_tensor = torch.tensor(x_cat, dtype=torch.int64).to(self.device)

        with torch.no_grad():
            logits, energies = self.model(x_n_tensor, x_c_tensor)
            probs = F.softmax(logits, dim=-1).cpu().numpy()
            energies = energies.cpu().numpy()
            pred_indices = logits.argmax(dim=-1).cpu().numpy()

        # Compute feature attributions for top 50 or sample
        attributions = self.model.attribute_features(
            x_n_tensor,
            x_c_tensor,
            num_feature_names=NUMERICAL_FEATURES,
            cat_feature_names=CATEGORICAL_FEATURES
        )

        results = []
        benign_cnt = 0
        known_cnt = 0
        zd_cnt = 0

        for i in range(len(df)):
            row = df.iloc[i]
            flow_id = str(row.get("flow_id", f"FL-{1000 + i}"))
            novelty = float(energies[i])
            pred_idx = int(pred_indices[i])
            pred_class = self.classes[pred_idx]
            conf = float(probs[i][pred_idx])

            # Class probabilities dict
            prob_dict = {
                cls_name: round(float(probs[i][c_idx]), 4)
                for c_idx, cls_name in enumerate(self.classes)
            }

            # Top 4 contributing features
            top_feats = dict(list(attributions[i].items())[:5])

            # Zero-Day Rejection Decision:
            # If novelty (free energy) exceeds threshold, flag as Potential Zero-Day
            if novelty > effective_threshold:
                verdict = "Potential Zero-Day"
                severity = "critical"
                is_anomaly = True
                zd_cnt += 1
            else:
                is_anomaly = False
                if pred_class == "Benign":
                    verdict = "Benign"
                    severity = "low"
                    benign_cnt += 1
                else:
                    verdict = "Known Attack"
                    severity = "high" if pred_class in ["DoS", "Botnet"] else "medium"
                    known_cnt += 1

            # Format raw features dictionary for easy UI display
            raw_feats = {
                "protocol": str(row.get("protocol", "TCP")),
                "dst_port_category": str(row.get("dst_port_category", "well-known")),
                "flow_duration": round(float(row.get("flow_duration", 0)), 2),
                "total_fwd_packets": int(row.get("total_fwd_packets", 0)),
                "total_bwd_packets": int(row.get("total_bwd_packets", 0)),
                "packet_len_mean": round(float(row.get("packet_len_mean", 0)), 2),
                "packet_len_std": round(float(row.get("packet_len_std", 0)), 2),
                "bytes_per_sec": round(float(row.get("bytes_per_sec", 0)), 2),
                "packets_per_sec": round(float(row.get("packets_per_sec", 0)), 2),
                "flag_syn": int(row.get("flag_syn", 0)),
                "flag_fin": int(row.get("flag_fin", 0)),
                "flag_rst": int(row.get("flag_rst", 0)),
                "flag_ack": int(row.get("flag_ack", 0)),
                "flag_psh": int(row.get("flag_psh", 0)),
                "flow_iat_mean": round(float(row.get("flow_iat_mean", 0)), 2),
                "flow_iat_std": round(float(row.get("flow_iat_std", 0)), 2)
            }

            results.append({
                "flow_id": flow_id,
                "verdict": verdict,
                "predicted_class": pred_class,
                "confidence": round(conf, 4),
                "novelty_score": round(novelty, 4),
                "threshold": round(effective_threshold, 4),
                "is_anomaly": is_anomaly,
                "severity": severity,
                "class_probabilities": prob_dict,
                "top_features": top_feats,
                "raw_features": raw_feats
            })

        total_time_ms = (time.time() - start_time) * 1000.0
        avg_latency_ms = round(total_time_ms / max(len(df), 1), 3)

        return {
            "total_flows": len(df),
            "benign_count": benign_cnt,
            "known_attack_count": known_cnt,
            "zero_day_count": zd_cnt,
            "avg_inference_latency_ms": avg_latency_ms,
            "threshold_used": round(effective_threshold, 4),
            "results": results
        }


# Global singleton instance
engine = FlowInferenceEngine()
