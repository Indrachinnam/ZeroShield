"""
ZeroShield: Live Traffic Stream Replay Service (SSE)
Simulates live network traffic by replaying flows with dynamic rate control,
performing real-time FlowTransformer classification, calculating novelty scores,
and streaming Server-Sent Events to the frontend.
"""

import os
import sys
import json
import time
import asyncio
import pandas as pd
from typing import AsyncGenerator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.inference import engine
from backend.database import save_alert, get_connection

DATA_DIR = os.path.join(BASE_DIR, "data")


class TrafficStreamSimulator:
    """
    Manages continuous live flow streaming from sample files.
    """
    def __init__(self):
        self.sample_flows_path = os.path.join(DATA_DIR, "sample_flows.csv")
        self.zero_days_path = os.path.join(DATA_DIR, "sample_zero_days.csv")
        self._load_datasets()

    def _load_datasets(self):
        if os.path.exists(self.sample_flows_path):
            self.df_flows = pd.read_csv(self.sample_flows_path)
        else:
            self.df_flows = pd.DataFrame()

        if os.path.exists(self.zero_days_path):
            self.df_zd = pd.read_csv(self.zero_days_path)
        else:
            self.df_zd = pd.DataFrame()

    async def event_generator(self, flows_per_sec: float = 2.0) -> AsyncGenerator[str, None]:
        """
        Asynchronously yields SSE events containing analyzed network flows.
        """
        delay = 1.0 / max(0.5, min(flows_per_sec, 10.0))
        flow_idx = 0
        total_samples = len(self.df_flows)

        # Counter for injecting occasional zero-days (e.g. every 8-12 flows)
        zd_counter = 0

        while True:
            # Check if we should reload dataset if empty
            if self.df_flows.empty:
                self._load_datasets()
                if self.df_flows.empty:
                    await asyncio.sleep(1.0)
                    continue

            # Decide whether to send a normal flow or inject a zero-day
            zd_counter += 1
            if zd_counter >= 9 and not self.df_zd.empty:
                zd_idx = (flow_idx // 9) % len(self.df_zd)
                single_row_df = self.df_zd.iloc[[zd_idx]].copy()
                zd_counter = 0
            else:
                single_row_df = self.df_flows.iloc[[flow_idx % total_samples]].copy()
                flow_idx += 1

            # Give a unique timestamped flow ID
            sim_flow_id = f"NET-{int(time.time()*1000) % 1000000:06d}"
            single_row_df["flow_id"] = sim_flow_id

            # Run inference on single flow
            analysis = engine.analyze_dataframe(single_row_df)
            result = analysis["results"][0]
            result["timestamp"] = time.strftime("%H:%M:%S")

            # If it's an alert (Known Attack or Potential Zero-Day), save to DB
            if result["verdict"] != "Benign":
                try:
                    save_alert({
                        "flow_id": result["flow_id"],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "verdict": result["verdict"],
                        "attack_class": result["predicted_class"] if result["verdict"] != "Potential Zero-Day" else "Zero-Day Exploit",
                        "novelty_score": result["novelty_score"],
                        "threshold": result["threshold"],
                        "confidence": result["confidence"],
                        "severity": result["severity"],
                        "protocol": result["raw_features"]["protocol"],
                        "dst_port_category": result["raw_features"]["dst_port_category"],
                        "flow_duration": result["raw_features"]["flow_duration"],
                        "total_fwd_packets": result["raw_features"]["total_fwd_packets"],
                        "total_bwd_packets": result["raw_features"]["total_bwd_packets"],
                        "bytes_per_sec": result["raw_features"]["bytes_per_sec"],
                        "packets_per_sec": result["raw_features"]["packets_per_sec"],
                        "features": result["raw_features"],
                        "status": "active"
                    })
                except Exception as e:
                    print(f"[!] Error saving alert: {e}")

            # Yield SSE format: data: <json>\n\n
            data_json = json.dumps(result)
            yield f"data: {data_json}\n\n"

            await asyncio.sleep(delay)


stream_simulator = TrafficStreamSimulator()
