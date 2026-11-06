"""
ZeroShield: Leave-One-Attack-Out (LOAO) Evaluation Suite
Evaluates FlowTransformer and baselines (Random Forest, Gradient Boosting, MLP)
under open-set Zero-Day conditions by holding out one attack family at a time.
Reports Macro-F1 on known classes, plus AUROC, AUPR, and FPR@95%TPR for known-vs-unknown detection.
"""

import os
import sys
import json
import time
from typing import Dict, Any
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import (
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    roc_curve
)
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ml.model import FlowTransformer
from ml.dataset import (
    KNOWN_CLASSES,
    CLASS_TO_IDX,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    PROTOCOL_MAP,
    PORT_CATEGORY_MAP,
    FlowDataset,
    preprocess_features,
    generate_synthetic_ids2017
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_JSON = os.path.join(DATA_DIR, "evaluation_results.json")


def compute_open_set_metrics(in_scores: np.ndarray, ood_scores: np.ndarray) -> Dict[str, float]:
    """
    Computes AUROC, AUPR, and FPR@95%TPR.
    in_scores: novelty scores of known in-distribution samples (label 0)
    ood_scores: novelty scores of unknown/zero-day samples (label 1)
    """
    y_true = np.concatenate([np.zeros(len(in_scores)), np.ones(len(ood_scores))])
    y_scores = np.concatenate([in_scores, ood_scores])

    # 1. AUROC
    auroc = roc_auc_score(y_true, y_scores)

    # 2. AUPR (Precision-Recall AUC for the positive/novel class)
    precision, recall, _ = precision_recall_curve(y_true, y_scores)
    aupr = auc(recall, precision)

    # 3. FPR@95%TPR
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    # Find smallest FPR where TPR >= 0.95
    idx_95_tpr = np.where(tpr >= 0.95)[0]
    if len(idx_95_tpr) > 0:
        fpr_at_95_tpr = float(fpr[idx_95_tpr[0]])
    else:
        fpr_at_95_tpr = 1.0

    return {
        "auroc": round(float(auroc), 4),
        "aupr": round(float(aupr), 4),
        "fpr_at_95_tpr": round(float(fpr_at_95_tpr), 4)
    }


def run_loao_evaluation(device: str = "cpu") -> Dict[str, any]:
    """
    Executes leave-one-attack-out cross-validation across all attack families.
    """
    print("=" * 70)
    print("ZeroShield: Running Leave-One-Attack-Out (LOAO) Benchmark")
    print("=" * 70)

    # Load dataset
    synth_file = os.path.join(DATA_DIR, "synthetic_ids2017.csv")
    if os.path.exists(synth_file):
        df = pd.read_csv(synth_file)
    else:
        df = generate_synthetic_ids2017(num_samples=12000, random_state=42)

    attack_families = [cls for cls in KNOWN_CLASSES if cls != "Benign"]
    models_to_evaluate = ["FlowTransformer", "Random Forest", "Gradient Boosting", "MLP"]

    loao_results = {
        "held_out_attacks": {},
        "model_summary": {
            m: {"mean_auroc": 0.0, "mean_aupr": 0.0, "mean_fpr95": 0.0, "mean_f1": 0.0}
            for m in models_to_evaluate
        }
    }

    cat_cardinalities = [len(PROTOCOL_MAP), len(PORT_CATEGORY_MAP)]

    for held_out in attack_families:
        print(f"\n[>>>] Evaluating Held-Out Zero-Day Attack Family: [{held_out}]")

        # Split: Known vs Held-Out
        df_train_pool = df[df["label"] != held_out].copy()
        df_held_out = df[df["label"] == held_out].copy()

        # Build dynamic class mapping for known classes
        current_known = [cls for cls in KNOWN_CLASSES if cls != held_out]
        cur_cls_to_idx = {name: i for i, name in enumerate(current_known)}

        # Preprocess features (fit scaler on known training pool)
        x_num_known, x_cat_known, scaler = preprocess_features(df_train_pool, fit_scaler=True)
        y_known = df_train_pool["label"].map(cur_cls_to_idx).values

        # Preprocess held-out test data
        x_num_ood, x_cat_ood, _ = preprocess_features(df_held_out, scaler=scaler, fit_scaler=False)

        # Train / Test split for known pool (80% train, 20% test)
        n_known = len(x_num_known)
        n_train = int(0.80 * n_known)
        indices = np.random.RandomState(42).permutation(n_known)
        tr_idx, te_idx = indices[:n_train], indices[n_train:]

        x_num_train, x_cat_train, y_train = x_num_known[tr_idx], x_cat_known[tr_idx], y_known[tr_idx]
        x_num_test, x_cat_test, y_test = x_num_known[te_idx], x_cat_known[te_idx], y_known[te_idx]

        # Combine continuous + categorical for tabular baselines
        X_train_flat = np.hstack([x_num_train, x_cat_train])
        X_test_flat = np.hstack([x_num_test, x_cat_test])
        X_ood_flat = np.hstack([x_num_ood, x_cat_ood])

        # -------------------------------------------------------------
        # 1. FlowTransformer (PyTorch)
        # -------------------------------------------------------------
        ft_model = FlowTransformer(
            num_numerical=len(NUMERICAL_FEATURES),
            cat_cardinalities=cat_cardinalities,
            num_classes=len(current_known),
            d_model=64,
            nhead=4,
            num_encoder_layers=3,
            dim_feedforward=128,
            dropout=0.1
        ).to(device)

        train_ds = FlowDataset(x_num_train, x_cat_train, y_train)
        train_loader = DataLoader(train_ds, batch_size=128, shuffle=True)
        optimizer = torch.optim.AdamW(ft_model.parameters(), lr=1.5e-3, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        ft_model.train()
        for epoch in range(6):
            for xn, xc, yb in train_loader:
                xn, xc, yb = xn.to(device), xc.to(device), yb.to(device)
                optimizer.zero_grad()
                logits, _ = ft_model(xn, xc)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()

        # Known test evaluation
        ft_model.eval()
        with torch.no_grad():
            xn_te = torch.tensor(x_num_test, dtype=torch.float32).to(device)
            xc_te = torch.tensor(x_cat_test, dtype=torch.int64).to(device)
            te_logits, ft_in_scores = ft_model(xn_te, xc_te)
            ft_preds = te_logits.argmax(dim=1).cpu().numpy()
            ft_in_scores = ft_in_scores.cpu().numpy()

            # Novel zero-day evaluation
            xn_ood = torch.tensor(x_num_ood, dtype=torch.float32).to(device)
            xc_ood = torch.tensor(x_cat_ood, dtype=torch.int64).to(device)
            _, ft_ood_scores = ft_model(xn_ood, xc_ood)
            ft_ood_scores = ft_ood_scores.cpu().numpy()

        ft_f1 = f1_score(y_test, ft_preds, average="macro")
        ft_open_metrics = compute_open_set_metrics(ft_in_scores, ft_ood_scores)
        ft_open_metrics["macro_f1"] = round(float(ft_f1), 4)

        # -------------------------------------------------------------
        # 2. Random Forest Baseline
        # -------------------------------------------------------------
        rf = RandomForestClassifier(n_estimators=80, max_depth=14, random_state=42, n_jobs=-1)
        rf.fit(X_train_flat, y_train)
        rf_te_probs = rf.predict_proba(X_test_flat)
        rf_preds = np.argmax(rf_te_probs, axis=1)
        rf_f1 = f1_score(y_test, rf_preds, average="macro")

        rf_ood_probs = rf.predict_proba(X_ood_flat)
        # Novelty via entropy
        rf_in_scores = -np.sum(rf_te_probs * np.log(np.clip(rf_te_probs, 1e-12, 1.0)), axis=1)
        rf_ood_scores = -np.sum(rf_ood_probs * np.log(np.clip(rf_ood_probs, 1e-12, 1.0)), axis=1)
        rf_metrics = compute_open_set_metrics(rf_in_scores, rf_ood_scores)
        rf_metrics["macro_f1"] = round(float(rf_f1), 4)

        # -------------------------------------------------------------
        # 3. Gradient Boosting Baseline
        # -------------------------------------------------------------
        gb = HistGradientBoostingClassifier(max_iter=80, max_depth=7, random_state=42)
        gb.fit(X_train_flat, y_train)
        gb_te_probs = gb.predict_proba(X_test_flat)
        gb_preds = np.argmax(gb_te_probs, axis=1)
        gb_f1 = f1_score(y_test, gb_preds, average="macro")

        gb_ood_probs = gb.predict_proba(X_ood_flat)
        gb_in_scores = -np.sum(gb_te_probs * np.log(np.clip(gb_te_probs, 1e-12, 1.0)), axis=1)
        gb_ood_scores = -np.sum(gb_ood_probs * np.log(np.clip(gb_ood_probs, 1e-12, 1.0)), axis=1)
        gb_metrics = compute_open_set_metrics(gb_in_scores, gb_ood_scores)
        gb_metrics["macro_f1"] = round(float(gb_f1), 4)

        # -------------------------------------------------------------
        # 4. Multi-Layer Perceptron (MLP) Baseline
        # -------------------------------------------------------------
        mlp = MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=80, random_state=42)
        mlp.fit(X_train_flat, y_train)
        mlp_te_probs = mlp.predict_proba(X_test_flat)
        mlp_preds = np.argmax(mlp_te_probs, axis=1)
        mlp_f1 = f1_score(y_test, mlp_preds, average="macro")

        mlp_ood_probs = mlp.predict_proba(X_ood_flat)
        mlp_in_scores = -np.sum(mlp_te_probs * np.log(np.clip(mlp_te_probs, 1e-12, 1.0)), axis=1)
        mlp_ood_scores = -np.sum(mlp_ood_probs * np.log(np.clip(mlp_ood_probs, 1e-12, 1.0)), axis=1)
        mlp_metrics = compute_open_set_metrics(mlp_in_scores, mlp_ood_scores)
        mlp_metrics["macro_f1"] = round(float(mlp_f1), 4)

        loao_results["held_out_attacks"][held_out] = {
            "FlowTransformer": ft_open_metrics,
            "Random Forest": rf_metrics,
            "Gradient Boosting": gb_metrics,
            "MLP": mlp_metrics
        }

        print(f"Results for [{held_out}]:")
        print(f"  FlowTransformer:   AUROC={ft_open_metrics['auroc']:.4f} | AUPR={ft_open_metrics['aupr']:.4f} | FPR@95%={ft_open_metrics['fpr_at_95_tpr']:.4f} | F1={ft_open_metrics['macro_f1']:.4f}")
        print(f"  Random Forest:     AUROC={rf_metrics['auroc']:.4f} | AUPR={rf_metrics['aupr']:.4f} | FPR@95%={rf_metrics['fpr_at_95_tpr']:.4f} | F1={rf_metrics['macro_f1']:.4f}")
        print(f"  Gradient Boosting: AUROC={gb_metrics['auroc']:.4f} | AUPR={gb_metrics['aupr']:.4f} | FPR@95%={gb_metrics['fpr_at_95_tpr']:.4f} | F1={gb_metrics['macro_f1']:.4f}")
        print(f"  MLP:               AUROC={mlp_metrics['auroc']:.4f} | AUPR={mlp_metrics['aupr']:.4f} | FPR@95%={mlp_metrics['fpr_at_95_tpr']:.4f} | F1={mlp_metrics['macro_f1']:.4f}")

    # Compute overall mean across held-out attacks
    for m in models_to_evaluate:
        aurocs = [loao_results["held_out_attacks"][att][m]["auroc"] for att in attack_families]
        auprs = [loao_results["held_out_attacks"][att][m]["aupr"] for att in attack_families]
        fpr95s = [loao_results["held_out_attacks"][att][m]["fpr_at_95_tpr"] for att in attack_families]
        f1s = [loao_results["held_out_attacks"][att][m]["macro_f1"] for att in attack_families]

        loao_results["model_summary"][m] = {
            "mean_auroc": round(float(np.mean(aurocs)), 4),
            "mean_aupr": round(float(np.mean(auprs)), 4),
            "mean_fpr95": round(float(np.mean(fpr95s)), 4),
            "mean_f1": round(float(np.mean(f1s)), 4)
        }

    # Save to JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(loao_results, f, indent=2)

    print(f"\n[+] Successfully saved LOAO benchmark results to {OUTPUT_JSON}")
    return loao_results


if __name__ == "__main__":
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    run_loao_evaluation(device=device)
