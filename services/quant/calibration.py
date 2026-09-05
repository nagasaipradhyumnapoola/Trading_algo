"""Probability calibration + reliability metrics.

The displayed probability must be calibrated: a "90%" bucket should hit ~90% in
reality. Provides isotonic and Platt calibrators, a reliability curve, Brier score,
log loss, and precision at a threshold / at a coverage. A confidence band is only
trustworthy if these say so.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss


class IsotonicCalibrator:
    def __init__(self) -> None:
        self._iso = IsotonicRegression(out_of_bounds="clip")

    def fit(self, scores, y):
        self._iso.fit(np.asarray(scores, float), np.asarray(y, int))
        return self

    def transform(self, scores):
        return self._iso.predict(np.asarray(scores, float))


class PlattCalibrator:
    def __init__(self) -> None:
        self._lr = LogisticRegression()

    def fit(self, scores, y):
        self._lr.fit(np.asarray(scores, float).reshape(-1, 1), np.asarray(y, int))
        return self

    def transform(self, scores):
        return self._lr.predict_proba(np.asarray(scores, float).reshape(-1, 1))[:, 1]


class ReliabilityBin(BaseModel):
    lo: float
    hi: float
    mean_pred: float
    frac_pos: float
    count: int


def reliability_curve(probs, y, bins: int = 10) -> list[ReliabilityBin]:
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    edges = np.linspace(0.0, 1.0, bins + 1)
    out: list[ReliabilityBin] = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (probs >= lo) & (probs < hi if i < bins - 1 else probs <= hi)
        if mask.any():
            out.append(ReliabilityBin(lo=lo, hi=hi, mean_pred=float(probs[mask].mean()),
                                      frac_pos=float(y[mask].mean()), count=int(mask.sum())))
    return out


def brier(probs, y) -> float:
    return float(brier_score_loss(np.asarray(y, int), np.asarray(probs, float)))


def logloss(probs, y) -> float:
    p = np.clip(np.asarray(probs, float), 1e-9, 1 - 1e-9)
    return float(log_loss(np.asarray(y, int), p, labels=[0, 1]))


def precision_at_threshold(probs, y, threshold: float) -> tuple[float, float]:
    """Returns (precision, coverage) among predictions with prob >= threshold."""
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    sel = probs >= threshold
    if not sel.any():
        return 0.0, 0.0
    return float(y[sel].mean()), float(sel.mean())


def precision_at_coverage(probs, y, coverage: float) -> float:
    """Precision on the top `coverage` fraction ranked by probability."""
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    n = max(1, int(round(coverage * len(probs))))
    top = np.argsort(probs)[::-1][:n]
    return float(y[top].mean())
