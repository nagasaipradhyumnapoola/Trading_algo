"""The production-quality recommendation object (phase plan §11 / §4.3).

Not a bullish paragraph — a timestamped, expiring, auditable record. The API/UI
must reject a BUY/ROTATE that is missing target, stop, horizon, quantity,
allocation, a calibrated probability, a risk verdict, or source citations.
The probability comes from the calibrated quant system, never from an LLM.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class RecAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ROTATE = "ROTATE"
    NO_TRADE = "NO_TRADE"


class Recommendation(BaseModel):
    action: RecAction
    instrument_id: str
    as_of: date
    entry_low: float | None = None
    entry_high: float | None = None
    target: float | None = None
    invalidation: float | None = None
    max_holding_sessions: int | None = None
    quantity: int = 0
    allocation: float = 0.0
    calibrated_probability: float | None = None
    expected_net_return: float | None = None
    expected_downside: float | None = None
    risk_reward: float | None = None
    historical_sample_size: int = 0
    risk_verdict: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    model_version: str = ""
    expires_on: date | None = None
    thesis: str = ""

    def missing_fields(self) -> list[str]:
        """Required fields for an actionable BUY/ROTATE. Empty => complete."""
        if self.action not in (RecAction.BUY, RecAction.ROTATE):
            return []
        required = {
            "entry_low": self.entry_low, "entry_high": self.entry_high,
            "target": self.target, "invalidation": self.invalidation,
            "max_holding_sessions": self.max_holding_sessions,
            "calibrated_probability": self.calibrated_probability,
            "risk_verdict": self.risk_verdict or None, "model_version": self.model_version or None,
        }
        missing = [k for k, v in required.items() if v is None]
        if self.quantity <= 0:
            missing.append("quantity")
        if self.allocation <= 0:
            missing.append("allocation")
        if not self.evidence_ids:
            missing.append("evidence_ids")
        return missing

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields()


def build_recommendation(
    *, action: RecAction, instrument_id: str, as_of: date, entry: float,
    stop_pct: float, target_pct: float, horizon_sessions: int, quantity: int,
    calibrated_probability: float, historical_sample_size: int, risk_verdict: str,
    evidence_ids: list[str], model_version: str, thesis: str = "",
) -> Recommendation:
    invalidation = entry * (1 - stop_pct)
    target = entry * (1 + target_pct)
    risk_reward = target_pct / stop_pct if stop_pct > 0 else None
    p = calibrated_probability
    expected_net = p * target_pct - (1 - p) * stop_pct
    return Recommendation(
        action=action, instrument_id=instrument_id, as_of=as_of,
        entry_low=round(entry * 0.999, 2), entry_high=round(entry * 1.001, 2),
        target=round(target, 2), invalidation=round(invalidation, 2),
        max_holding_sessions=horizon_sessions, quantity=quantity,
        allocation=round(quantity * entry, 2), calibrated_probability=p,
        expected_net_return=expected_net, expected_downside=-stop_pct,
        risk_reward=risk_reward, historical_sample_size=historical_sample_size,
        risk_verdict=risk_verdict, evidence_ids=evidence_ids, model_version=model_version,
        expires_on=as_of + timedelta(days=horizon_sessions * 2), thesis=thesis,
    )
