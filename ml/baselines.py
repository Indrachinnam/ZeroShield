"""
ZeroShield: Baseline Classifiers (Random Forest, Gradient Boosting, MLP)
Provides comparison models for network traffic classification and open-set anomaly detection.
"""

import numpy as np
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier


class BaselineSuite:
    """
    Manages classical ML baselines:
    - Random Forest
    - Gradient Boosting (HistGradientBoosting, XGBoost style)
    - Multi-Layer Perceptron (MLP)
    """
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.models = {
            "Random Forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=16,
                random_state=random_state,
                n_jobs=-1
            ),
            "Gradient Boosting": HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=8,
                random_state=random_state
            ),
            "MLP": MLPClassifier(
                hidden_layer_sizes=(128, 64),
                max_iter=150,
                early_stopping=True,
                random_state=random_state
            )
        }

    def fit_all(self, X_train: np.ndarray, y_train: np.ndarray):
        """Fits all baseline models on training data."""
        for name, model in self.models.items():
            model.fit(X_train, y_train)

    def predict_with_novelty(self, name: str, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Predicts class probabilities and open-set novelty score for a given model.
        Novelty score for baselines is defined via Prediction Entropy:
        H(x) = -sum(p_k * log(p_k + 1e-12))
        Higher entropy = lower confidence / higher novelty.
        Returns:
            preds: predicted class indices
            probs: probability matrix [N, num_classes]
            novelty_scores: continuous novelty scores [N]
        """
        model = self.models[name]
        probs = model.predict_proba(X)
        preds = np.argmax(probs, axis=1)

        # Entropy-based novelty score
        entropy = -np.sum(probs * np.log(np.clip(probs, 1e-12, 1.0)), axis=1)
        # Normalize roughly so higher means more novel
        return preds, probs, entropy
