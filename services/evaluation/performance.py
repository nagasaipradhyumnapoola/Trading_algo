"""Performance dashboard metrics from realized paper/live returns.

Everything here is computed from realized outcomes — honest reporting, including
losses and drawdown. Precision-by-confidence-bucket answers the key question:
does a 90% bucket actually win ~90% of the time?
"""

from __future__ import annotations

import statistics

import numpy as np
from pydantic import BaseModel


class PerformanceReport(BaseModel):
    n: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float | None = None
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0


def _max_drawdown(returns: list[float]) -> float:
    equity, peak, mdd = 1.0, 1.0, 0.0
    for r in returns:
        equity *= (1 + r)
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)
    return mdd


def compute_performance(returns: list[float]) -> PerformanceReport:
    if not returns:
        return PerformanceReport()

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    equity = 1.0
    for r in returns:
        equity *= (1 + r)

    mean = statistics.fmean(returns)
    std = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    downside = [min(0.0, r) for r in returns]
    dstd = statistics.pstdev(downside) if len(downside) > 1 else 0.0

    return PerformanceReport(
        n=len(returns),
        win_rate=len(wins) / len(returns),
        avg_win=statistics.fmean(wins) if wins else 0.0,
        avg_loss=statistics.fmean(losses) if losses else 0.0,
        profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else None,
        total_return=equity - 1.0,
        max_drawdown=_max_drawdown(returns),
        sharpe=(mean / std) if std > 0 else 0.0,
        sortino=(mean / dstd) if dstd > 0 else 0.0,
    )


class Bucket(BaseModel):
    lo: float
    hi: float
    precision: float
    count: int


def precision_by_bucket(probs, y, edges=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01)) -> list[Bucket]:
    """Realized precision within each confidence band — calibration in production."""
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    out: list[Bucket] = []
    for lo, hi in zip(edges, edges[1:]):
        mask = (probs >= lo) & (probs < hi)
        if mask.any():
            out.append(Bucket(lo=lo, hi=hi, precision=float(y[mask].mean()),
                              count=int(mask.sum())))
    return out
