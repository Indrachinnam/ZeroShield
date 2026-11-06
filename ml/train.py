"""
ZeroShield: Model Training & Threshold Calibration
Trains FlowTransformer on CIC-IDS2017 or realistic synthetic network traffic,
calibrates the open-set energy score threshold at 5% FPR on benign flows,
and saves the checkpoint for real-time inference.
"""

import os
import sys
import glob
import json
import time
from typing import Tuple, Dict, List, Optional, Any
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

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
    FlowDataset,
    preprocess_features,
    generate_synthetic_ids2017,
    generate_zero_day_flows
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "ml", "checkpoints")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def load_or_generate_dataset() -> Tuple[pd.DataFrame, bool]:
    """
    Checks for real CIC-IDS2017 CSV files in data/.
    If none found, generates realistic synthetic dataset mimicking the distributions.
    """
    cic_files = glob.glob(os.path.join(DATA_DIR, "*IDS2017*.csv"))
    if cic_files:
        print(f"[*] Found {len(cic_files)} CIC-IDS2017 files in data/. Loading...")
        dfs = []
        for f in cic_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:
                print(f"[!] Warning: Failed to read {f}: {e}")
        df = pd.concat(dfs, ignore_index=True)
        is_synthetic = False
        print(f"[+] Loaded {len(df)} real flows from CIC-IDS2017.")
    else:
        synth_file = os.path.join(DATA_DIR, "synthetic_ids2017.csv")
        if os.path.exists(synth_file):
            print(f"[*] Loading existing synthetic dataset from {synth_file}...")
            df = pd.read_csv(synth_file)
        else:
            print("[*] Generating realistic synthetic network traffic dataset (15,000 flows)...")
            df = generate_synthetic_ids2017(num_samples=15000, random_state=42)
            df.to_csv(synth_file, index=False)
            print(f"[+] Saved synthetic dataset to {synth_file}")
        is_synthetic = True

    # Also generate sample files for live streaming and upload demonstrations
    sample_flows_path = os.path.join(DATA_DIR, "sample_flows.csv")
    if not os.path.exists(sample_flows_path):
        # Create a balanced 200-flow sample with benign and various attacks
        sample_df = df.groupby("label", group_keys=False).apply(lambda x: x.sample(min(len(x), 35), random_state=42))
        sample_df = sample_df.sample(frac=1.0, random_state=42).reset_index(drop=True)
        sample_df.to_csv(sample_flows_path, index=False)
        print(f"[+] Created sample replay flows: {sample_flows_path}")

    sample_zd_path = os.path.join(DATA_DIR, "sample_zero_days.csv")
    if not os.path.exists(sample_zd_path):
        zd_df = generate_zero_day_flows(num_samples=250, random_state=999)
        zd_df.to_csv(sample_zd_path, index=False)
        print(f"[+] Created sample zero-day test flows: {sample_zd_path}")

    return df, is_synthetic


def train_model(
    epochs: int = 10,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    device: str = "cpu"
) -> Dict[str, any]:
    """
    Trains FlowTransformer and calibrates novelty threshold.
    """
    df, is_synthetic = load_or_generate_dataset()

    # Filter to known classes
    df_known = df[df["label"].isin(KNOWN_CLASSES)].copy()
    y_raw = df_known["label"].map(CLASS_TO_IDX).values

    print(f"[*] Preprocessing {len(df_known)} flows across {len(KNOWN_CLASSES)} classes...")
    x_num, x_cat, scaler = preprocess_features(df_known, fit_scaler=True)

    # Train / Val / Test split (70% / 15% / 15%)
    n_total = len(x_num)
    n_train = int(0.70 * n_total)
    n_val = int(0.15 * n_total)
    n_test = n_total - n_train - n_val

    indices = np.random.RandomState(42).permutation(n_total)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train_dataset = FlowDataset(x_num[train_idx], x_cat[train_idx], y_raw[train_idx])
    val_dataset = FlowDataset(x_num[val_idx], x_cat[val_idx], y_raw[val_idx])
    test_dataset = FlowDataset(x_num[test_idx], x_cat[test_idx], y_raw[test_idx])

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # Initialize FlowTransformer
    # Categorical cardinalities: Protocol (4), Dst Port Category (3)
    cat_cardinalities = [len(PROTOCOL_MAP), len(PORT_CATEGORY_MAP)]
    model = FlowTransformer(
        num_numerical=len(NUMERICAL_FEATURES),
        cat_cardinalities=cat_cardinalities,
        num_classes=len(KNOWN_CLASSES),
        d_model=64,
        nhead=4,
        num_encoder_layers=3,
        dim_feedforward=128,
        dropout=0.1
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    print(f"[*] Training FlowTransformer on {device} ({epochs} epochs)...")
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for x_n, x_c, y in train_loader:
            x_n, x_c, y = x_n.to(device), x_c.to(device), y.to(device)
            optimizer.zero_grad()
            logits, _ = model(x_n, x_c)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(y)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += len(y)

        scheduler.step()
        train_acc = correct / total
        train_loss = total_loss / total

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for x_n, x_c, y in val_loader:
                x_n, x_c, y = x_n.to(device), x_c.to(device), y.to(device)
                logits, _ = model(x_n, x_c)
                preds = logits.argmax(dim=1)
                val_correct += (preds == y).sum().item()
                val_total += len(y)

        val_acc = val_correct / val_total
        print(f"Epoch {epoch:02d}/{epochs:02d} - Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.2f}% | Val Acc: {val_acc*100:.2f}%")

    train_duration = time.time() - start_time
    print(f"[+] Training completed in {train_duration:.2f}s")

    # Evaluate on test set
    model.eval()
    all_preds, all_targets, all_energies = [], [], []
    with torch.no_grad():
        for x_n, x_c, y in test_loader:
            x_n, x_c = x_n.to(device), x_c.to(device)
            logits, energies = model(x_n, x_c)
            all_preds.extend(logits.argmax(dim=1).cpu().numpy())
            all_targets.extend(y.numpy())
            all_energies.extend(energies.cpu().numpy())

    test_acc = accuracy_score(all_targets, all_preds)
    test_macro_f1 = f1_score(all_targets, all_preds, average="macro")
    print(f"[+] Test Accuracy: {test_acc*100:.2f}% | Macro-F1: {test_macro_f1:.4f}")

    # ==========================================================
    # Calibration of Novelty Threshold (5% FPR on Benign Validation)
    # ==========================================================
    print("[*] Calibrating Energy Score Novelty Threshold at 5% FPR on Benign flows...")
    val_benign_mask = (y_raw[val_idx] == CLASS_TO_IDX["Benign"])
    val_benign_x_num = torch.tensor(x_num[val_idx][val_benign_mask], dtype=torch.float32).to(device)
    val_benign_x_cat = torch.tensor(x_cat[val_idx][val_benign_mask], dtype=torch.int64).to(device)

    with torch.no_grad():
        _, val_benign_energies = model(val_benign_x_num, val_benign_x_cat)
        val_benign_energies = val_benign_energies.cpu().numpy()

    # 95th percentile corresponds to exactly 5% False Positive Rate on benign flows
    threshold_5pct_fpr = float(np.percentile(val_benign_energies, 95.0))
    print(f"[+] Calibrated Threshold: {threshold_5pct_fpr:.4f}")
    print(f"    - Benign Energy Min: {val_benign_energies.min():.4f}")
    print(f"    - Benign Energy Median: {np.median(val_benign_energies):.4f}")
    print(f"    - Benign Energy 95th %ile: {threshold_5pct_fpr:.4f}")
    print(f"    - Benign Energy Max: {val_benign_energies.max():.4f}")

    # Save checkpoint artifacts
    checkpoint_path = os.path.join(CHECKPOINT_DIR, "flow_transformer.pt")
    scaler_path = os.path.join(CHECKPOINT_DIR, "scaler.joblib")
    config_path = os.path.join(CHECKPOINT_DIR, "config.json")

    torch.save(model.state_dict(), checkpoint_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        "model_name": "FlowTransformer",
        "architecture": "FT-Transformer with [CLS] token and Multi-Head Self-Attention",
        "d_model": 64,
        "nhead": 4,
        "num_encoder_layers": 3,
        "dim_feedforward": 128,
        "num_classes": len(KNOWN_CLASSES),
        "classes": KNOWN_CLASSES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numerical_features": NUMERICAL_FEATURES,
        "calibrated_threshold": threshold_5pct_fpr,
        "calibrated_fpr": 0.05,
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_f1": round(float(test_macro_f1), 4),
        "is_synthetic": is_synthetic,
        "training_samples": len(df_known),
        "train_duration_sec": round(train_duration, 2),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(config_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[+] Saved checkpoint and configuration to {CHECKPOINT_DIR}")
    return metadata


if __name__ == "__main__":
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    train_model(epochs=8, batch_size=128, device=device)
