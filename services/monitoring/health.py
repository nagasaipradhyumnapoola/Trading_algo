"""System health + degraded mode.

Degraded mode preserves deterministic results and suppresses only what is unsafe:
stale/quarantined data suppresses recommendations; an LLM outage suppresses only
LLM-dependent features (chat, extraction) while deterministic recommendations stand.
Nothing is fabricated to fill a gap.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"


class HealthInputs(BaseModel):
    feed_age_days: float = 0.0
    max_feed_age_days: float = 3.0
    data_quality_ok: bool = True
    llm_available: bool = True


class HealthReport(BaseModel):
    status: HealthStatus
    degraded_reasons: list[str] = Field(default_factory=list)
    suppress_recommendations: bool = False       # deterministic recs unsafe (bad/stale data)
    suppress_llm_features: bool = False           # chat/extraction unavailable
    feed_age_days: float = 0.0
    llm_available: bool = True


def evaluate_health(inp: HealthInputs) -> HealthReport:
    reasons: list[str] = []
    suppress_recs = False
    suppress_llm = False

    if inp.feed_age_days > inp.max_feed_age_days:
        reasons.append("stale_feed")
        suppress_recs = True
    if not inp.data_quality_ok:
        reasons.append("data_quality")
        suppress_recs = True
    if not inp.llm_available:
        reasons.append("llm_unavailable")
        suppress_llm = True                       # deterministic recs still valid

    return HealthReport(
        status=HealthStatus.DEGRADED if reasons else HealthStatus.OK,
        degraded_reasons=reasons, suppress_recommendations=suppress_recs,
        suppress_llm_features=suppress_llm, feed_age_days=inp.feed_age_days,
        llm_available=inp.llm_available,
    )
