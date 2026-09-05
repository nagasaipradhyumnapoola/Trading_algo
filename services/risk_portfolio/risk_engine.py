"""Independent risk engine — deterministic vetoes.

Separate from the LLM Judge and holds final veto power (the Judge cannot override
it). Every input is a deterministic number/flag; no LLM produces a risk verdict.
A hard flag => VETO; a soft flag => REVIEW; otherwise PASS.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskVerdict(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    VETO = "VETO"


class RiskFlag(BaseModel):
    code: str
    verdict: RiskVerdict
    detail: str = ""


class RiskConfig(BaseModel):
    min_turnover: float = 1_000_000.0
    max_spread_bps: float = 100.0
    max_realized_vol: float = 0.06        # daily; above -> REVIEW
    max_manipulation: float = 0.6
    max_event_uncertainty: float = 0.7
    min_circuit_band: float = 0.05        # <= this -> circuit-prone (REVIEW)


class RiskInputs(BaseModel):
    instrument_id: str
    avg_turnover: float = 0.0
    spread_bps: float = 0.0
    realized_vol: float = 0.0
    manipulation_score: float = 0.0
    event_uncertainty: float = 0.0
    data_quality_ok: bool = True
    circuit_locked: bool = False
    circuit_band: float | None = None     # e.g. 0.05 / 0.10 / 0.20
    gap_risk: bool = False
    signal_age_days: float = 0.0
    signal_expiry_days: float = 5.0


class RiskResult(BaseModel):
    instrument_id: str
    verdict: RiskVerdict
    flags: list[RiskFlag] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict is RiskVerdict.PASS


def assess_risk(inp: RiskInputs, config: RiskConfig | None = None) -> RiskResult:
    cfg = config or RiskConfig()
    flags: list[RiskFlag] = []

    def veto(code, detail=""):
        flags.append(RiskFlag(code=code, verdict=RiskVerdict.VETO, detail=detail))

    def review(code, detail=""):
        flags.append(RiskFlag(code=code, verdict=RiskVerdict.REVIEW, detail=detail))

    # hard vetoes
    if inp.avg_turnover < cfg.min_turnover:
        veto("LIQUIDITY", f"turnover {inp.avg_turnover:,.0f} < {cfg.min_turnover:,.0f}")
    if inp.spread_bps > cfg.max_spread_bps:
        veto("SPREAD", f"{inp.spread_bps:.0f}bps > {cfg.max_spread_bps:.0f}")
    if not inp.data_quality_ok:
        veto("DATA_QUALITY", "quarantined data")
    if inp.manipulation_score > cfg.max_manipulation:
        veto("MANIPULATION", f"score {inp.manipulation_score:.2f}")
    if inp.signal_age_days > inp.signal_expiry_days:
        veto("STALE", f"age {inp.signal_age_days:.1f}d > expiry {inp.signal_expiry_days:.1f}d")
    if inp.circuit_locked:
        veto("CIRCUIT", "instrument circuit-locked")

    # soft reviews
    if inp.realized_vol > cfg.max_realized_vol:
        review("VOLATILITY", f"vol {inp.realized_vol:.3f}")
    if inp.event_uncertainty > cfg.max_event_uncertainty:
        review("EVENT_UNCERTAINTY", f"{inp.event_uncertainty:.2f}")
    if inp.gap_risk:
        review("GAP", "gap risk")
    if inp.circuit_band is not None and inp.circuit_band <= cfg.min_circuit_band:
        review("CIRCUIT_BAND", f"band {inp.circuit_band:.0%}")

    if any(f.verdict is RiskVerdict.VETO for f in flags):
        verdict = RiskVerdict.VETO
    elif any(f.verdict is RiskVerdict.REVIEW for f in flags):
        verdict = RiskVerdict.REVIEW
    else:
        verdict = RiskVerdict.PASS
    return RiskResult(instrument_id=inp.instrument_id, verdict=verdict, flags=flags)
