"""ML models: a logistic baseline plus the benchmarks it must beat.

Baselines before complexity (CLAUDE.md / phase plan): a base-rate model and a
momentum rule are the bar; the logistic model must beat them on untouched data
after costs or it is rejected. LightGBM/XGBoost slot in behind the same fit /
predict_proba interface once available on the runtime.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEFAULT_FEATURES = ["momentum", "volume_ratio", "realized_vol"]


def build_xy(pairs, feature_names=DEFAULT_FEATURES):
    """pairs: list of (FeatureSnapshot, Label). Rows missing any feature are skipped."""
    X, y = [], []
    for snap, label in pairs:
        if all(f in snap.values for f in feature_names):
            X.append([snap.values[f] for f in feature_names])
            y.append(int(label.y))
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int)


class BaseRateModel:
    """Predicts the training positive rate for everyone. The floor benchmark."""

    def __init__(self) -> None:
        self.rate = 0.5

    def fit(self, X, y):
        self.rate = float(np.mean(y)) if len(y) else 0.5
        return self

    def predict_proba(self, X):
        return np.full(len(X), self.rate, dtype=float)


class MomentumRuleModel:
    """Monotonic in the momentum feature (column 0). A simple rule benchmark."""

    def __init__(self, k: float = 20.0) -> None:
        self.k = k

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        z = self.k * np.asarray(X, float)[:, 0]
        return 1.0 / (1.0 + np.exp(-z))


class LogisticModel:
    """Standardized logistic regression. Falls back to base rate if y is single-class."""

    def __init__(self) -> None:
        self._pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        self._constant: float | None = None

    def fit(self, X, y):
        y = np.asarray(y, int)
        if len(np.unique(y)) < 2:
            self._constant = float(np.mean(y)) if len(y) else 0.5
        else:
            self._constant = None
            self._pipe.fit(X, y)
        return self

    def predict_proba(self, X):
        if self._constant is not None:
            return np.full(len(X), self._constant, dtype=float)
        return self._pipe.predict_proba(X)[:, 1]
