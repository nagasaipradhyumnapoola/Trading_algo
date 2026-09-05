"""Discovery scoring — deterministic candidate prioritization.

Combines source reliability, novelty, materiality, event age, how much price has
already reacted, liquidity, and data quality into one 0..1 score. Novelty and
materiality come from grounded LLM extraction; the score itself is deterministic
code (an LLM never produces the number). Liquidity and data-quality act as gates.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Source reliability by tier (1=NSE/SEBI/official … 4=social).
SOURCE_TIER_WEIGHT = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.3}
_AGE_HALFLIFE_DAYS = 3.0


class DiscoverySignal(BaseModel):
    instrument_id: str
    source_tier: int = Field(default=3, ge=1, le=4)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    materiality: float = Field(default=0.0, ge=0.0, le=1.0)
    event_age_days: float = 0.0
    price_reacted: float = Field(default=0.0, ge=0.0, le=1.0)   # 1 = move already fully happened
    avg_turnover: float = 0.0
    min_turnover: float = 1_000_000.0
    data_quality_ok: bool = True


class ScoredDiscovery(BaseModel):
    instrument_id: str
    score: float
    components: dict[str, float] = Field(default_factory=dict)


def discovery_score(sig: DiscoverySignal) -> ScoredDiscovery:
    reliability = SOURCE_TIER_WEIGHT.get(sig.source_tier, 0.3)
    age_decay = 0.5 ** (max(0.0, sig.event_age_days) / _AGE_HALFLIFE_DAYS)
    price_factor = max(0.0, 1.0 - sig.price_reacted)
    liquidity = 1.0 if sig.avg_turnover >= sig.min_turnover else 0.0
    dq = 1.0 if sig.data_quality_ok else 0.0

    score = reliability * sig.materiality * sig.novelty * age_decay * price_factor * liquidity * dq
    return ScoredDiscovery(instrument_id=sig.instrument_id, score=score, components={
        "reliability": reliability, "materiality": sig.materiality, "novelty": sig.novelty,
        "age_decay": age_decay, "price_factor": price_factor,
        "liquidity": liquidity, "data_quality": dq,
    })


class DiscoveryCandidate(BaseModel):
    instrument_id: str
    score: float
    event_types: list[str] = Field(default_factory=list)
    scanner_reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    components: dict[str, float] = Field(default_factory=dict)


def rank_discoveries(candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    return sorted(candidates, key=lambda c: c.score, reverse=True)
