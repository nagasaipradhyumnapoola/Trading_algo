"""Agent 3 — Market. Interpret price/volume behavior from DETERMINISTIC features.

No LLM: all numbers come from services/quant. The agent turns the computed feature
vector into a structured read (trend/volume/volatility) for the floor. It never
produces a trade probability — that is the calibrated ML engine's job.
"""

from __future__ import annotations

from .base import AgentResult


class MarketAgent:
    name = "market"

    def run(self, instrument_id: str, features) -> AgentResult:
        vals = features.values if hasattr(features, "values") else dict(features)
        mom = vals.get("momentum", 0.0)
        vr = vals.get("volume_ratio", 0.0)
        rv = vals.get("realized_vol", 0.0)

        trend = "up" if mom > 0 else ("down" if mom < 0 else "flat")
        vol_state = "abnormal" if vr >= 1.5 else "normal"
        thesis = (f"trend {trend} (momentum {mom:.2%}), volume {vol_state} (x{vr:.1f}), "
                  f"realized vol {rv:.3f}")

        return AgentResult(
            agent=self.name, ticker=instrument_id, thesis=thesis, confidence=0.0,
            data={"trend": trend, "volume_state": vol_state, "features": vals, "deterministic": True},
        )
