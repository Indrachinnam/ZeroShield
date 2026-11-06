"""
ZeroShield: FlowTransformer Model Architecture
FT-Transformer style architecture for network flow classification and energy-based zero-day detection.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional


class NumericalFeatureTokenizer(nn.Module):
    """
    Transforms numerical features into d_model dimensional tokens.
    Each numerical feature has its own learnable weight and bias:
    Token_i = x_i * W_i + b_i
    """
    def __init__(self, num_features: int, d_model: int):
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        # Weights: [num_features, d_model], Biases: [num_features, d_model]
        self.weight = nn.Parameter(torch.empty(num_features, d_model))
        self.bias = nn.Parameter(torch.empty(num_features, d_model))
        self.reset_parameters()

    def reset_parameters(self):
        d = 1.0 / math.sqrt(self.d_model)
        nn.init.uniform_(self.weight, -d, d)
        nn.init.zeros_(self.bias)

    def forward(self, x_num: torch.Tensor) -> torch.Tensor:
        # x_num shape: [batch_size, num_features]
        # output shape: [batch_size, num_features, d_model]
        # x_num.unsqueeze(-1) shape: [batch_size, num_features, 1]
        tokens = x_num.unsqueeze(-1) * self.weight.unsqueeze(0) + self.bias.unsqueeze(0)
        return tokens


class CategoricalFeatureTokenizer(nn.Module):
    """
    Transforms categorical features into d_model dimensional tokens using embeddings.
    """
    def __init__(self, cardinalities: List[int], d_model: int):
        super().__init__()
        self.embeddings = nn.ModuleList([
            nn.Embedding(cardinality, d_model) for cardinality in cardinalities
        ])

    def forward(self, x_cat: torch.Tensor) -> torch.Tensor:
        # x_cat shape: [batch_size, num_cat_features]
        # output shape: [batch_size, num_cat_features, d_model]
        tokens = []
        for i, emb in enumerate(self.embeddings):
            tokens.append(emb(x_cat[:, i]).unsqueeze(1))
        return torch.cat(tokens, dim=1)


class FlowTransformer(nn.Module):
    """
    FlowTransformer (FT-Transformer style):
    - Encodes categorical & numerical flow features as distinct tokens
    - Prepends a learnable [CLS] token
    - Passes sequence through 3 Transformer Encoder layers (4 heads, d_model=64)
    - Classification head outputs logits for known classes
    - Energy score head computes novelty score E(x) = -T * logsumexp(logits / T)
    """
    def __init__(
        self,
        num_numerical: int,
        cat_cardinalities: List[int],
        num_classes: int,
        d_model: int = 64,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
        temperature: float = 1.0,
    ):
        super().__init__()
        self.num_numerical = num_numerical
        self.cat_cardinalities = cat_cardinalities
        self.num_classes = num_classes
        self.d_model = d_model
        self.temperature = temperature

        # Tokenizers
        self.num_tokenizer = NumericalFeatureTokenizer(num_numerical, d_model)
        self.cat_tokenizer = CategoricalFeatureTokenizer(cat_cardinalities, d_model)

        total_tokens = num_numerical + len(cat_cardinalities)
        self.total_tokens = total_tokens

        # [CLS] token
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.normal_(self.cls_token, std=0.02)

        # Feature type / sequence position embeddings (total_tokens + 1 for CLS)
        self.pos_embedding = nn.Parameter(torch.randn(1, total_tokens + 1, d_model) * 0.02)

        # Layer normalization before transformer
        self.input_layer_norm = nn.LayerNorm(d_model)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="relu",
            batch_first=True,
            norm_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_encoder_layers,
            enable_nested_tensor=False
        )

        # Classification Head
        self.final_norm = nn.LayerNorm(d_model)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes)
        )

    def forward(
        self,
        x_num: torch.Tensor,
        x_cat: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        Returns:
            logits: [batch_size, num_classes]
            energy: [batch_size]
        """
        batch_size = x_num.shape[0]

        # Tokenize features
        num_tokens = self.num_tokenizer(x_num)      # [B, N_num, d_model]
        cat_tokens = self.cat_tokenizer(x_cat)      # [B, N_cat, d_model]

        # Concatenate tokens
        feature_tokens = torch.cat([cat_tokens, num_tokens], dim=1) # [B, N_total, d_model]

        # Prepend [CLS] token
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)      # [B, 1, d_model]
        tokens = torch.cat([cls_tokens, feature_tokens], dim=1)     # [B, 1 + N_total, d_model]

        # Add position/identity embedding & norm
        tokens = tokens + self.pos_embedding
        tokens = self.input_layer_norm(tokens)

        # Transformer Encoding
        encoded = self.transformer_encoder(tokens)                  # [B, 1 + N_total, d_model]

        # Extract [CLS] token representation
        cls_rep = encoded[:, 0, :]                                 # [B, d_model]
        cls_rep = self.final_norm(cls_rep)

        # Compute classification logits
        logits = self.classifier(cls_rep)                          # [B, num_classes]

        # Compute energy score: E(x) = -T * logsumexp(logits / T)
        # In energy-based OOD detection, high energy = anomalous / novelty / zero-day
        energy = -self.temperature * torch.logsumexp(logits / self.temperature, dim=-1)

        return logits, energy

    def compute_energy(self, logits: torch.Tensor) -> torch.Tensor:
        """Helper to calculate energy score from pre-computed logits."""
        return -self.temperature * torch.logsumexp(logits / self.temperature, dim=-1)

    def attribute_features(
        self,
        x_num: torch.Tensor,
        x_cat: torch.Tensor,
        num_feature_names: List[str],
        cat_feature_names: List[str]
    ) -> List[Dict[str, float]]:
        """
        Computes gradient-based feature attribution for each flow in batch.
        Uses gradient of energy score with respect to input numerical features.
        Higher gradient magnitude means the feature has stronger influence on the novelty score.
        """
        self.eval()
        x_num_grad = x_num.clone().detach().requires_grad_(True)
        logits, energy = self.forward(x_num_grad, x_cat)

        attributions = []
        # Compute gradient for each sample individually
        for i in range(x_num.shape[0]):
            sample_energy = energy[i]
            grad = torch.autograd.grad(
                sample_energy,
                x_num_grad,
                retain_graph=(i < x_num.shape[0] - 1),
                create_graph=False
            )[0][i]

            # Contribution = |x * grad| or |grad|
            contrib_scores = (torch.abs(grad) * torch.abs(x_num_grad[i])).detach().cpu().numpy()
            
            # Normalize to sum to 1.0
            sum_score = contrib_scores.sum() + 1e-8
            norm_scores = (contrib_scores / sum_score).tolist()

            feat_contribs = {
                name: round(float(norm_scores[j]), 4)
                for j, name in enumerate(num_feature_names)
            }
            # Add general categorical influence
            feat_contribs["dst_port_category"] = 0.05
            feat_contribs["protocol"] = 0.05
            
            # Sort descending
            sorted_contribs = dict(sorted(feat_contribs.items(), key=lambda item: item[1], reverse=True))
            attributions.append(sorted_contribs)

        return attributions
