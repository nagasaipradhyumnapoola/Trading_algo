"""Feature/score drift via Population Stability Index (PSI).

PSI compares a current distribution against a reference (training) distribution.
Rule of thumb: < 0.1 stable, 0.1-0.25 moderate shift, > 0.25 significant drift.
Drift flags a model for review/recalibration — it never silently changes signals.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel


class DriftReport(BaseModel):
    psi: float
    drifted: bool
    threshold: float
    n_ref: int
    n_cur: int


def population_stability_index(reference, current, bins: int = 10, eps: float = 1e-6) -> float:
    reference, current = np.asarray(reference, float), np.asarray(current, float)
    if reference.size == 0 or current.size == 0:
        return 0.0
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    ref_pct = np.histogram(reference, bins=edges)[0] / reference.size
    cur_pct = np.histogram(current, bins=edges)[0] / current.size
    ref_pct = np.clip(ref_pct, eps, None)
    cur_pct = np.clip(cur_pct, eps, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def detect_drift(reference, current, *, threshold: float = 0.25, bins: int = 10) -> DriftReport:
    psi = population_stability_index(reference, current, bins=bins)
    return DriftReport(psi=psi, drifted=psi > threshold, threshold=threshold,
                       n_ref=len(reference), n_cur=len(current))
