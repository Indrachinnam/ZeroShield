"""
ZeroShield: Inference Engine
Loads trained FlowTransformer weights and scaler, performs high-throughput batch
inference, computes Energy-based novelty scores, and determines security verdicts.
Supports both PyTorch and lightweight pure NumPy execution for serverless deployment (Vercel).
"""

import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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

# Check if PyTorch is available
try:
    import torch
    import torch.nn.functional as F
    from ml.model import FlowTransformer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class FlowInferenceEngine:
    """
    Inference engine for real-time and batch network flow classification.
    Seamlessly operates using PyTorch (local) or pure NumPy (Vercel serverless).
    """
    def __init__(self):
        self.device = "cpu"
        self.use_torch = False
        self.model = None
        self.np_weights = {}
        self.scaler = None
        self.config: Dict[str, Any] = {}
        self.calibrated_threshold: float = -7.44
        self.classes: List[str] = KNOWN_CLASSES
        self._load_artifacts()

    def _load_artifacts(self):
        config_path = os.path.join(CHECKPOINT_DIR, "config.json")
        scaler_path = os.path.join(CHECKPOINT_DIR, "scaler.joblib")
        weights_pt = os.path.join(CHECKPOINT_DIR, "flow_transformer.pt")
        weights_npz = os.path.join(CHECKPOINT_DIR, "flow_transformer_weights.npz")

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.calibrated_threshold = float(self.config.get("calibrated_threshold", -7.44))
            self.classes = self.config.get("classes", KNOWN_CLASSES)

        if os.path.exists(scaler_path):
            try:
                self.scaler = joblib.load(scaler_path)
            except Exception as e:
                print(f"[!] Warning loading scaler: {e}")

        # Try loading PyTorch first if available
        if TORCH_AVAILABLE and os.path.exists(weights_pt):
            try:
                self.device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
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
                state_dict = torch.load(weights_pt, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.model.eval()
                self.use_torch = True
                print(f"[+] Loaded PyTorch FlowTransformer checkpoint on {self.device}")
            except Exception as e:
                print(f"[!] PyTorch load failed: {e}. Falling back to NumPy engine.")
                self.use_torch = False

        # If PyTorch not used, load NumPy weights
        if not self.use_torch:
            if os.path.exists(weights_npz):
                self.np_weights = dict(np.load(weights_npz))
                print("[+] Loaded pure NumPy FlowTransformer weights (Serverless optimized)")
            elif os.path.exists(weights_pt) and TORCH_AVAILABLE:
                state = torch.load(weights_pt, map_location="cpu")
                self.np_weights = {k: v.cpu().numpy() for k, v in state.items()}
                np.savez_compressed(weights_npz, **self.np_weights)
                print("[+] Exported and loaded NumPy weights from PyTorch checkpoint")

    def get_effective_threshold(self) -> float:
        """Retrieves runtime threshold from DB or defaults to calibrated threshold."""
        return get_runtime_threshold(default_threshold=self.calibrated_threshold)

    def _forward_numpy(self, x_num: np.ndarray, x_cat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """High-performance pure NumPy implementation of FlowTransformer forward pass."""
        w = self.np_weights
        B = x_num.shape[0]

        def ln(x, gamma, beta, eps=1e-5):
            mean = np.mean(x, axis=-1, keepdims=True)
            var = np.var(x, axis=-1, keepdims=True)
            return (x - mean) / np.sqrt(var + eps) * gamma + beta

        def sm(x, axis=-1):
            ex = np.exp(x - np.max(x, axis=axis, keepdims=True))
            return ex / np.sum(ex, axis=axis, keepdims=True)

        def mha(x, in_w, in_b, out_w, out_b, nhead=4, d_model=64):
            d_k = d_model // nhead
            qkv = x @ in_w.T + in_b
            q, k, v = np.split(qkv, 3, axis=-1)
            q = q.reshape(B, -1, nhead, d_k).swapaxes(1, 2)
            k = k.reshape(B, -1, nhead, d_k).swapaxes(1, 2)
            v = v.reshape(B, -1, nhead, d_k).swapaxes(1, 2)
            scores = (q @ k.swapaxes(-2, -1)) / np.sqrt(d_k)
            attn = sm(scores, axis=-1)
            out = (attn @ v).swapaxes(1, 2).reshape(B, -1, d_model)
            return out @ out_w.T + out_b

        # 1. Feature tokenization
        num_tok = x_num[:, :, None] * w["num_tokenizer.weight"][None, :, :] + w["num_tokenizer.bias"][None, :, :]
        c0 = w["cat_tokenizer.embeddings.0.weight"][x_cat[:, 0]][:, None, :]
        c1 = w["cat_tokenizer.embeddings.1.weight"][x_cat[:, 1]][:, None, :]
        feat_tok = np.concatenate([c0, c1, num_tok], axis=1)

        # 2. [CLS] token and pos embedding
        cls_tok = np.repeat(w["cls_token"], B, axis=0)
        tokens = np.concatenate([cls_tok, feat_tok], axis=1) + w["pos_embedding"]
        tokens = ln(tokens, w["input_layer_norm.weight"], w["input_layer_norm.bias"])

        # 3. 3-layer Transformer Encoder
        for i in range(3):
            norm1 = ln(tokens, w[f"transformer_encoder.layers.{i}.norm1.weight"], w[f"transformer_encoder.layers.{i}.norm1.bias"])
            sa = mha(norm1,
                     w[f"transformer_encoder.layers.{i}.self_attn.in_proj_weight"],
                     w[f"transformer_encoder.layers.{i}.self_attn.in_proj_bias"],
                     w[f"transformer_encoder.layers.{i}.self_attn.out_proj.weight"],
                     w[f"transformer_encoder.layers.{i}.self_attn.out_proj.bias"])
            tokens = tokens + sa

            norm2 = ln(tokens, w[f"transformer_encoder.layers.{i}.norm2.weight"], w[f"transformer_encoder.layers.{i}.norm2.bias"])
            ffn_h = np.maximum(0, norm2 @ w[f"transformer_encoder.layers.{i}.linear1.weight"].T + w[f"transformer_encoder.layers.{i}.linear1.bias"])
            ffn = ffn_h @ w[f"transformer_encoder.layers.{i}.linear2.weight"].T + w[f"transformer_encoder.layers.{i}.linear2.bias"]
            tokens = tokens + ffn

        # 4. Final Norm & Classifier Head
        cls_rep = ln(tokens[:, 0, :], w["final_norm.weight"], w["final_norm.bias"])
        h_cls = np.maximum(0, cls_rep @ w["classifier.0.weight"].T + w["classifier.0.bias"])
        logits = h_cls @ w["classifier.3.weight"].T + w["classifier.3.bias"]

        # 5. Free energy score: -logsumexp
        max_logit = np.max(logits, axis=-1, keepdims=True)
        energy = -(max_logit.squeeze(-1) + np.log(np.sum(np.exp(logits - max_logit), axis=-1)))
        return logits, energy

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

        if self.use_torch and self.model is not None:
            x_n_tensor = torch.tensor(x_num, dtype=torch.float32).to(self.device)
            x_c_tensor = torch.tensor(x_cat, dtype=torch.int64).to(self.device)

            with torch.no_grad():
                logits, energies = self.model(x_n_tensor, x_c_tensor)
                probs = F.softmax(logits, dim=-1).cpu().numpy()
                energies = energies.cpu().numpy()
                pred_indices = logits.argmax(dim=-1).cpu().numpy()

            attributions = self.model.attribute_features(
                x_n_tensor,
                x_c_tensor,
                num_feature_names=NUMERICAL_FEATURES,
                cat_feature_names=CATEGORICAL_FEATURES
            )
        else:
            # Pure NumPy execution
            logits, energies = self._forward_numpy(x_num, x_cat)
            exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
            pred_indices = np.argmax(logits, axis=-1)

            # Heuristic feature attribution via deviation from mean
            attributions = []
            for i in range(len(df)):
                dev = np.abs(x_num[i])
                dev_sum = np.sum(dev) + 1e-8
                dev_norm = dev / dev_sum
                attrib = {NUMERICAL_FEATURES[j]: round(float(dev_norm[j]), 4) for j in range(len(NUMERICAL_FEATURES))}
                attrib["dst_port_category"] = 0.05
                attrib["protocol"] = 0.05
                sorted_attrib = dict(sorted(attrib.items(), key=lambda x: x[1], reverse=True))
                attributions.append(sorted_attrib)

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

            prob_dict = {
                cls_name: round(float(probs[i][c_idx]), 4)
                for c_idx, cls_name in enumerate(self.classes)
            }

            top_feats = dict(list(attributions[i].items())[:5])

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


engine = FlowInferenceEngine()
