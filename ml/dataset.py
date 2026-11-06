"""
ZeroShield: Dataset Preprocessing and Realistic Synthetic Data Generator
Handles tokenization mappings, normalization, and generation of network flows
mimicking the CIC-IDS2017 distribution.
"""

import os
import json
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler

# Class definitions
KNOWN_CLASSES = ["Benign", "DoS", "PortScan", "BruteForce", "WebAttack", "Botnet"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(KNOWN_CLASSES)}
IDX_TO_CLASS = {idx: name for idx, name in enumerate(KNOWN_CLASSES)}

# Feature definitions
CATEGORICAL_FEATURES = ["protocol", "dst_port_category"]
NUMERICAL_FEATURES = [
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "packet_len_mean",
    "packet_len_std",
    "bytes_per_sec",
    "packets_per_sec",
    "flag_syn",
    "flag_fin",
    "flag_rst",
    "flag_ack",
    "flag_psh",
    "flow_iat_mean",
    "flow_iat_std"
]

PROTOCOL_MAP = {"TCP": 0, "UDP": 1, "ICMP": 2, "OTHER": 3}
PORT_CATEGORY_MAP = {"well-known": 0, "registered": 1, "ephemeral": 2}


def port_to_category(port: any) -> str:
    """Converts a raw port number to category, or preserves existing category."""
    if isinstance(port, str):
        p_lower = port.lower().strip()
        if p_lower in PORT_CATEGORY_MAP:
            return p_lower
        try:
            port = int(port)
        except ValueError:
            return "well-known"

    try:
        p = int(port)
        if 0 <= p <= 1023:
            return "well-known"
        elif 1024 <= p <= 49151:
            return "registered"
        else:
            return "ephemeral"
    except (TypeError, ValueError):
        return "well-known"


def encode_categorical(df: pd.DataFrame) -> np.ndarray:
    """Encodes protocol and dst_port_category into integer indices."""
    cat_data = np.zeros((len(df), 2), dtype=np.int64)

    # Protocol
    if "protocol" in df.columns:
        cat_data[:, 0] = df["protocol"].astype(str).str.upper().map(
            lambda x: PROTOCOL_MAP.get(x, PROTOCOL_MAP["OTHER"])
        ).values
    else:
        cat_data[:, 0] = PROTOCOL_MAP["TCP"]

    # Port Category
    if "dst_port_category" in df.columns:
        cat_data[:, 1] = df["dst_port_category"].astype(str).map(
            lambda x: PORT_CATEGORY_MAP.get(port_to_category(x), 0)
        ).values
    elif "dst_port" in df.columns or "Destination Port" in df.columns:
        col = "dst_port" if "dst_port" in df.columns else "Destination Port"
        cat_data[:, 1] = df[col].map(lambda x: PORT_CATEGORY_MAP.get(port_to_category(x), 0)).values
    else:
        cat_data[:, 1] = 0

    return cat_data


def preprocess_features(
    df: pd.DataFrame,
    scaler: Optional[StandardScaler] = None,
    fit_scaler: bool = False
) -> Tuple[np.ndarray, np.ndarray, StandardScaler]:
    """
    Extracts and standardizes numerical features and encodes categorical features.
    Guarantees no raw ports or IP addresses are processed.
    """
    # 1. Encode categoricals
    cat_data = encode_categorical(df)

    # 2. Extract numericals with fallback defaults
    num_df = pd.DataFrame(index=df.index)
    for col in NUMERICAL_FEATURES:
        if col in df.columns:
            num_df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            # Check alternative naming conventions (e.g. CIC-IDS2017 raw headers)
            alt_map = {
                "flow_duration": ["Flow Duration", "duration"],
                "total_fwd_packets": ["Total Fwd Packets", "fwd_packets"],
                "total_bwd_packets": ["Total Backward Packets", "bwd_packets"],
                "packet_len_mean": ["Packet Length Mean", "pkt_len_mean"],
                "packet_len_std": ["Packet Length Std", "pkt_len_std"],
                "bytes_per_sec": ["Flow Bytes/s", "bytes_s"],
                "packets_per_sec": ["Flow Packets/s", "packets_s"],
                "flag_syn": ["SYN Flag Count", "syn_count"],
                "flag_fin": ["FIN Flag Count", "fin_count"],
                "flag_rst": ["RST Flag Count", "rst_count"],
                "flag_ack": ["ACK Flag Count", "ack_count"],
                "flag_psh": ["PSH Flag Count", "psh_count"],
                "flow_iat_mean": ["Flow IAT Mean", "iat_mean"],
                "flow_iat_std": ["Flow IAT Std", "iat_std"],
            }
            matched = False
            for alt in alt_map.get(col, []):
                if alt in df.columns:
                    num_df[col] = pd.to_numeric(df[alt], errors='coerce').fillna(0.0)
                    matched = True
                    break
            if not matched:
                num_df[col] = 0.0

    # Clean infinities and clip extreme outliers
    num_arr = np.nan_to_num(num_df.values, nan=0.0, posinf=1e8, neginf=-1e8)

    # Apply log1p scaling to skewed volume features before standard scaling
    skewed_idx = [0, 1, 2, 5, 6, 12, 13]  # duration, packets, rates, IAT
    for idx in skewed_idx:
        num_arr[:, idx] = np.log1p(np.clip(num_arr[:, idx], a_min=0, a_max=None))

    if fit_scaler:
        scaler = StandardScaler()
        num_scaled = scaler.fit_transform(num_arr)
    else:
        if scaler is None:
            raise ValueError("Must provide a fitted scaler if fit_scaler is False.")
        num_scaled = scaler.transform(num_arr)

    return num_scaled.astype(np.float32), cat_data.astype(np.int64), scaler


class FlowDataset(Dataset):
    def __init__(self, x_num: np.ndarray, x_cat: np.ndarray, y: Optional[np.ndarray] = None):
        self.x_num = torch.tensor(x_num, dtype=torch.float32)
        self.x_cat = torch.tensor(x_cat, dtype=torch.int64)
        self.y = torch.tensor(y, dtype=torch.int64) if y is not None else None

    def __len__(self):
        return len(self.x_num)

    def __getitem__(self, idx):
        if self.y is not None:
            return self.x_num[idx], self.x_cat[idx], self.y[idx]
        return self.x_num[idx], self.x_cat[idx]


def generate_synthetic_ids2017(
    num_samples: int = 15000,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset mimicking the CIC-IDS2017 distribution.
    Features follow distinctive real-world network traffic behavior for benign
    and 5 attack categories + novel zero-day exploits.
    """
    np.random.seed(random_state)
    records = []

    # Proportions: Benign (60%), DoS (12%), PortScan (10%), BruteForce (8%), WebAttack (5%), Botnet (5%)
    class_dist = {
        "Benign": int(num_samples * 0.55),
        "DoS": int(num_samples * 0.12),
        "PortScan": int(num_samples * 0.11),
        "BruteForce": int(num_samples * 0.08),
        "WebAttack": int(num_samples * 0.07),
        "Botnet": int(num_samples * 0.07),
    }

    flow_counter = 1000

    for label, count in class_dist.items():
        for _ in range(count):
            flow_id = f"FL-{flow_counter}"
            flow_counter += 1

            if label == "Benign":
                protocol = np.random.choice(["TCP", "UDP"], p=[0.75, 0.25])
                dst_port_cat = np.random.choice(["well-known", "registered", "ephemeral"], p=[0.70, 0.20, 0.10])
                duration = np.random.exponential(scale=150000) + 100
                fwd_pkts = int(np.random.gamma(shape=3.0, scale=4.0)) + 1
                bwd_pkts = int(fwd_pkts * np.random.uniform(0.6, 1.4)) + 1
                pkt_mean = np.random.normal(loc=450, scale=120)
                pkt_std = np.random.normal(loc=180, scale=60)
                bytes_sec = (fwd_pkts + bwd_pkts) * pkt_mean / max(duration / 1e6, 0.001)
                pkts_sec = (fwd_pkts + bwd_pkts) / max(duration / 1e6, 0.001)
                syn = 1 if protocol == "TCP" else 0
                fin = 1 if protocol == "TCP" and np.random.rand() > 0.3 else 0
                rst = 1 if np.random.rand() < 0.05 else 0
                ack = 1 if protocol == "TCP" else 0
                psh = np.random.randint(0, 3)
                iat_mean = max(10.0, np.random.exponential(scale=12000))
                iat_std = max(5.0, iat_mean * np.random.uniform(0.3, 0.9))

            elif label == "DoS":
                # High packet rate, small packet variance, asymmetric (minimal bwd)
                protocol = np.random.choice(["TCP", "UDP"], p=[0.85, 0.15])
                dst_port_cat = "well-known"
                duration = np.random.exponential(scale=50000) + 50
                fwd_pkts = int(np.random.uniform(150, 2000))
                bwd_pkts = int(np.random.uniform(0, 5))
                pkt_mean = np.random.normal(loc=64, scale=12)
                pkt_std = np.random.uniform(0, 15)
                bytes_sec = (fwd_pkts * pkt_mean) / max(duration / 1e6, 0.001)
                pkts_sec = fwd_pkts / max(duration / 1e6, 0.001)
                syn = 1
                fin = 0
                rst = 1 if np.random.rand() > 0.6 else 0
                ack = 0 if np.random.rand() > 0.3 else 1
                psh = 0
                iat_mean = np.random.uniform(5.0, 50.0)
                iat_std = np.random.uniform(1.0, 15.0)

            elif label == "PortScan":
                # Quick sweep, minimal duration, 1-2 fwd packets, 0 bwd, ephemeral/registered ports
                protocol = "TCP"
                dst_port_cat = np.random.choice(["registered", "ephemeral"], p=[0.60, 0.40])
                duration = np.random.uniform(20, 500)
                fwd_pkts = np.random.choice([1, 2, 3], p=[0.8, 0.15, 0.05])
                bwd_pkts = 0 if np.random.rand() > 0.1 else 1
                pkt_mean = np.random.uniform(40, 60)
                pkt_std = np.random.uniform(0, 5)
                bytes_sec = (fwd_pkts * pkt_mean) / max(duration / 1e6, 0.0001)
                pkts_sec = fwd_pkts / max(duration / 1e6, 0.0001)
                syn = 1
                fin = 0
                rst = 0
                ack = 0
                psh = 0
                iat_mean = duration / max(fwd_pkts, 1)
                iat_std = 0.0

            elif label == "BruteForce":
                # Rhythmic authentication attempts, moderate duration, SSH/FTP ports
                protocol = "TCP"
                dst_port_cat = "well-known"
                duration = np.random.uniform(3000, 15000)
                fwd_pkts = np.random.randint(8, 25)
                bwd_pkts = np.random.randint(6, 20)
                pkt_mean = np.random.normal(loc=120, scale=30)
                pkt_std = np.random.normal(loc=40, scale=15)
                bytes_sec = (fwd_pkts + bwd_pkts) * pkt_mean / (duration / 1e6)
                pkts_sec = (fwd_pkts + bwd_pkts) / (duration / 1e6)
                syn = 1
                fin = 1
                rst = 0
                ack = 1
                psh = np.random.randint(3, 8)
                iat_mean = np.random.uniform(200, 800)
                iat_std = np.random.uniform(20, 100)

            elif label == "WebAttack":
                # High payload sizes, PSH flags, HTTP/HTTPS ports, irregular responses
                protocol = "TCP"
                dst_port_cat = "well-known"
                duration = np.random.exponential(scale=60000) + 500
                fwd_pkts = np.random.randint(10, 45)
                bwd_pkts = np.random.randint(15, 60)
                pkt_mean = np.random.normal(loc=750, scale=200)
                pkt_std = np.random.normal(loc=350, scale=80)
                bytes_sec = (fwd_pkts + bwd_pkts) * pkt_mean / max(duration / 1e6, 0.001)
                pkts_sec = (fwd_pkts + bwd_pkts) / max(duration / 1e6, 0.001)
                syn = 1
                fin = 1
                rst = 0
                ack = 1
                psh = np.random.randint(4, 15)
                iat_mean = np.random.exponential(scale=4000)
                iat_std = iat_mean * 1.2

            elif label == "Botnet":
                # Periodic C2 beaconing, fixed intervals, registered/ephemeral ports
                protocol = np.random.choice(["TCP", "UDP"], p=[0.7, 0.3])
                dst_port_cat = np.random.choice(["registered", "ephemeral"], p=[0.65, 0.35])
                duration = np.random.uniform(8000, 30000)
                fwd_pkts = np.random.randint(5, 14)
                bwd_pkts = np.random.randint(4, 12)
                pkt_mean = np.random.normal(loc=180, scale=40)
                pkt_std = np.random.normal(loc=30, scale=10)
                bytes_sec = (fwd_pkts + bwd_pkts) * pkt_mean / (duration / 1e6)
                pkts_sec = (fwd_pkts + bwd_pkts) / (duration / 1e6)
                syn = 1 if protocol == "TCP" else 0
                fin = 1 if protocol == "TCP" else 0
                rst = 0
                ack = 1 if protocol == "TCP" else 0
                psh = 2
                iat_mean = np.random.uniform(1500, 2500)
                iat_std = np.random.uniform(10, 50)  # Very low variance beaconing

            records.append({
                "flow_id": flow_id,
                "protocol": protocol,
                "dst_port_category": dst_port_cat,
                "flow_duration": max(1.0, float(duration)),
                "total_fwd_packets": max(1, int(fwd_pkts)),
                "total_bwd_packets": max(0, int(bwd_pkts)),
                "packet_len_mean": max(20.0, float(pkt_mean)),
                "packet_len_std": max(0.0, float(pkt_std)),
                "bytes_per_sec": max(1.0, float(bytes_sec)),
                "packets_per_sec": max(0.1, float(pkts_sec)),
                "flag_syn": int(syn),
                "flag_fin": int(fin),
                "flag_rst": int(rst),
                "flag_ack": int(ack),
                "flag_psh": int(psh),
                "flow_iat_mean": max(1.0, float(iat_mean)),
                "flow_iat_std": max(0.0, float(iat_std)),
                "label": label,
            })

    df = pd.DataFrame(records)
    # Shuffle
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return df


def generate_zero_day_flows(num_samples: int = 500, random_state: int = 999) -> pd.DataFrame:
    """
    Generates synthetic novel Zero-Day exploits that do not conform to any
    standard known signature (e.g. DNS Tunneling exfiltration, covert steganographic channels,
    kernel remote code execution probes).
    These have unusual combinations of high payload on ephemeral ports, strange flag combos,
    or abnormal burst timings that trigger high energy scores.
    """
    np.random.seed(random_state)
    records = []
    for i in range(num_samples):
        flow_id = f"ZD-{2000 + i}"
        proto = np.random.choice(["TCP", "UDP", "OTHER"], p=[0.6, 0.3, 0.1])
        dst_port_cat = np.random.choice(["ephemeral", "registered"], p=[0.75, 0.25])
        duration = np.random.uniform(500000, 3000000)
        fwd_pkts = np.random.randint(80, 500)
        bwd_pkts = np.random.randint(1, 4)
        pkt_mean = np.random.uniform(900, 1450)  # Heavy exfiltration
        pkt_std = np.random.uniform(10, 40)
        bytes_sec = (fwd_pkts * pkt_mean) / (duration / 1e6)
        pkts_sec = fwd_pkts / (duration / 1e6)
        
        # Anomalous flag pattern (SYN + FIN + PSH without ACK, or non-standard)
        syn = 1 if np.random.rand() > 0.4 else 0
        fin = 1 if np.random.rand() > 0.3 else 0
        rst = 1 if np.random.rand() > 0.5 else 0
        ack = 0 if np.random.rand() > 0.4 else 1
        psh = np.random.randint(5, 30)

        iat_mean = np.random.uniform(20000, 80000)
        iat_std = np.random.uniform(15000, 60000)

        records.append({
            "flow_id": flow_id,
            "protocol": proto,
            "dst_port_category": dst_port_cat,
            "flow_duration": float(duration),
            "total_fwd_packets": int(fwd_pkts),
            "total_bwd_packets": int(bwd_pkts),
            "packet_len_mean": float(pkt_mean),
            "packet_len_std": float(pkt_std),
            "bytes_per_sec": float(bytes_sec),
            "packets_per_sec": float(pkts_sec),
            "flag_syn": int(syn),
            "flag_fin": int(fin),
            "flag_rst": int(rst),
            "flag_ack": int(ack),
            "flag_psh": int(psh),
            "flow_iat_mean": float(iat_mean),
            "flow_iat_std": float(iat_std),
            "label": "Zero-Day",
        })
    return pd.DataFrame(records)
