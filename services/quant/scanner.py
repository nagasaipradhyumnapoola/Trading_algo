"""Deterministic market scanner (Phase 1).

Momentum / relative-strength + abnormal-volume + liquidity filter over the
universe, at a point in time. Produces ranked candidates; emits an empty list
(-> NO_TRADE upstream) when nothing clears the gates. No LLM involved.

The composite score here is intentionally simple and provisional; the empirically
optimized ranking is Phase 4 (see CLAUDE.md §10).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from services.ingestion.instruments import InstrumentMaster
from services.ingestion.models import Timeframe
from services.ingestion.repository import BarRepository

from .features import FeatureSnapshot, compute_features


class ScanConfig(BaseModel):
    momentum_lookback: int = 20
    volume_window: int = 20
    liquidity_window: int = 20
    min_avg_turnover: float = 1_000_000.0    # rupees/day; drop illiquid names
    min_volume_ratio: float = 1.5            # abnormal volume gate
    min_momentum: float = 0.0                # require positive momentum
    top_k: int | None = None                 # None = all passing candidates


class ScanCandidate(BaseModel):
    instrument_id: str
    as_of: date
    score: float
    momentum: float
    volume_ratio: float
    avg_turnover: float
    rs_percentile: float
    reason: str
    features: FeatureSnapshot


def _passes(f: FeatureSnapshot, cfg: ScanConfig) -> bool:
    v = f.values
    return (
        "momentum" in v and "volume_ratio" in v and "avg_turnover" in v
        and v["avg_turnover"] >= cfg.min_avg_turnover
        and v["volume_ratio"] >= cfg.min_volume_ratio
        and v["momentum"] > cfg.min_momentum
    )


def scan(
    repo: BarRepository,
    master: InstrumentMaster,
    as_of: date,
    config: ScanConfig | None = None,
) -> list[ScanCandidate]:
    cfg = config or ScanConfig()

    # 1) point-in-time features for every tradable instrument
    passing: list[FeatureSnapshot] = []
    for inst in master.tradable():
        bars = repo.as_of(inst.instrument_id, Timeframe.EOD, as_of)
        if not bars:
            continue
        f = compute_features(
            bars, as_of,
            momentum_lookback=cfg.momentum_lookback,
            volume_window=cfg.volume_window,
            liquidity_window=cfg.liquidity_window,
        )
        if _passes(f, cfg):
            passing.append(f)

    if not passing:
        return []

    # 2) relative strength = momentum percentile within the passing set
    moms = sorted(f.values["momentum"] for f in passing)

    def percentile(x: float) -> float:
        below = sum(1 for m in moms if m < x)
        return below / (len(moms) - 1) if len(moms) > 1 else 1.0

    # 3) composite score (provisional): 70% relative strength, 30% abnormal volume
    candidates: list[ScanCandidate] = []
    for f in passing:
        rs = percentile(f.values["momentum"])
        vr = f.values["volume_ratio"]
        vr_norm = min(vr / (cfg.min_volume_ratio * 2), 1.0)
        score = 0.7 * rs + 0.3 * vr_norm
        candidates.append(
            ScanCandidate(
                instrument_id=f.instrument_id, as_of=as_of, score=score,
                momentum=f.values["momentum"], volume_ratio=vr,
                avg_turnover=f.values["avg_turnover"], rs_percentile=rs,
                reason=(f"momentum={f.values['momentum']:.2%}, vol x{vr:.1f}, "
                        f"turnover={f.values['avg_turnover']:,.0f}"),
                features=f,
            )
        )

    candidates.sort(key=lambda c: (c.score, c.momentum), reverse=True)
    return candidates[: cfg.top_k] if cfg.top_k else candidates
