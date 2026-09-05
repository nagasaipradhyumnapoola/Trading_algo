"""Purged, embargoed walk-forward cross-validation.

Chronological folds only — never shuffle time series. Training samples whose label
window (signal_date + horizon) plus an embargo overlaps the test period are purged,
so a model is never trained on information that leaks into the test window.
"""

from __future__ import annotations

from datetime import date, timedelta


def purged_walk_forward(
    dates: list[date], *, n_splits: int = 4, horizon: int = 5, embargo: int = 2
) -> list[tuple[list[int], list[int]]]:
    """Return [(train_idx, test_idx), ...] over expanding, purged, embargoed folds."""
    n = len(dates)
    order = sorted(range(n), key=lambda i: dates[i])
    fold = max(1, n // (n_splits + 1))
    gap = timedelta(days=horizon + embargo)

    folds: list[tuple[list[int], list[int]]] = []
    for k in range(1, n_splits + 1):
        start = k * fold
        end = (k + 1) * fold if k < n_splits else n
        if start >= n:
            break
        test_idx = order[start:end]
        test_start = dates[order[start]]
        train_idx = [i for i in order[:start] if dates[i] + gap < test_start]  # purge + embargo
        if test_idx:
            folds.append((train_idx, test_idx))
    return folds
