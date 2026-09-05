"""Deterministic point-in-time market features.

All features are computed from bars with session_date <= as_of (the caller passes
a point-in-time slice from the repository). No LLM touches these numbers.
"""

from __future__ import annotations

import statistics
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from services.ingestion.models import Bar

FEATURE_SET_VERSION = "fs-0.1"


class Quality(str, Enum):
    OK = "ok"
    INSUFFICIENT_HISTORY = "insufficient_history"


def _closes(bars: list[Bar]) -> list[float]:
    return [float(b.close) for b in bars]


def daily_returns(bars: list[Bar]) -> list[float]:
    closes = _closes(bars)
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1] != 0]


def total_return(bars: list[Bar], lookback: int) -> float | None:
    if len(bars) < lookback + 1:
        return None
    c_now = float(bars[-1].close)
    c_then = float(bars[-1 - lookback].close)
    return (c_now / c_then - 1.0) if c_then else None


def avg_volume(bars: list[Bar], window: int) -> float | None:
    if len(bars) < window + 1:            # need window prior bars, excluding today
        return None
    prior = bars[-1 - window:-1]
    return statistics.fmean(b.volume for b in prior)


def volume_ratio(bars: list[Bar], window: int) -> float | None:
    av = avg_volume(bars, window)
    if av is None or av == 0:
        return None
    return bars[-1].volume / av


def _turnover(bar: Bar) -> float:
    if bar.turnover is not None:
        return float(bar.turnover)
    return float(bar.close) * bar.volume


def avg_turnover(bars: list[Bar], window: int) -> float | None:
    if len(bars) < window:
        return None
    recent = bars[-window:]
    return statistics.fmean(_turnover(b) for b in recent)


def realized_vol(bars: list[Bar], window: int) -> float | None:
    rets = daily_returns(bars[-(window + 1):]) if len(bars) >= window + 1 else []
    if len(rets) < 2:
        return None
    return statistics.pstdev(rets)


class FeatureSnapshot(BaseModel):
    instrument_id: str
    as_of: date
    feature_set_version: str = FEATURE_SET_VERSION
    values: dict[str, float] = Field(default_factory=dict)
    quality: Quality = Quality.OK


def compute_features(
    bars: list[Bar],
    as_of: date,
    *,
    momentum_lookback: int = 20,
    volume_window: int = 20,
    liquidity_window: int = 20,
    vol_window: int = 20,
) -> FeatureSnapshot:
    """Compute the feature snapshot for one instrument as of `as_of`.

    `bars` must already be the point-in-time slice (session_date <= as_of), ascending.
    """
    if not bars:
        raise ValueError("no bars")

    values: dict[str, float] = {}
    quality = Quality.OK

    mom = total_return(bars, momentum_lookback)
    vr = volume_ratio(bars, volume_window)
    liq = avg_turnover(bars, liquidity_window)
    rv = realized_vol(bars, vol_window)

    if mom is None or vr is None or liq is None:
        quality = Quality.INSUFFICIENT_HISTORY

    if mom is not None:
        values["momentum"] = mom
    if vr is not None:
        values["volume_ratio"] = vr
    if liq is not None:
        values["avg_turnover"] = liq
    if rv is not None:
        values["realized_vol"] = rv
    values["last_close"] = float(bars[-1].close)

    return FeatureSnapshot(
        instrument_id=bars[-1].instrument_id, as_of=as_of, values=values, quality=quality
    )
