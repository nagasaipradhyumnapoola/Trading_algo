"""Agent 6 — Historical Analogue. Retrieve POINT-IN-TIME past analogues.

Deterministic: finds prior high-volume events for the instrument whose forward
window is entirely before `as_of` (so their outcomes were knowable then — no
look-ahead) and aggregates their abnormal-return hit-rates via the event-study
engine. No LLM produces these numbers.
"""

from __future__ import annotations

from datetime import date

from services.ingestion.models import Timeframe
from services.quant.event_study import EventStudy
from services.quant.features import volume_ratio

from .base import AgentResult


class HistoricalAgent:
    name = "historical"

    def __init__(self, repo, universe_ids: list[str], *, min_vr: float = 1.5,
                 horizon: int = 10, window: int = 20) -> None:
        self.repo = repo
        self.min_vr = min_vr
        self.horizon = horizon
        self.window = window
        self.study = EventStudy(repo, universe_ids)

    def run(self, instrument_id: str, as_of: date) -> AgentResult:
        bars = self.repo.as_of(instrument_id, Timeframe.EOD, as_of)
        events: list[tuple[str, date]] = []
        for i in range(self.window, len(bars)):
            if i + self.horizon >= len(bars):          # forward window must be fully known by as_of
                break
            vr = volume_ratio(bars[: i + 1], self.window)
            if vr and vr >= self.min_vr:
                events.append((instrument_id, bars[i].session_date))

        agg = self.study.aggregate(events, horizons=(1, 3, 5))
        pos3 = agg.positive_rate.get(3)
        thesis = (f"{agg.n} prior analogues; 3D positive {pos3:.0%}"
                  if agg.n and pos3 is not None else f"{agg.n} analogues")
        return AgentResult(
            agent=self.name, ticker=instrument_id, thesis=thesis, confidence=0.0,
            data={"sample_count": agg.n, "positive_rate": agg.positive_rate,
                  "mean_car": agg.mean_car, "point_in_time": True},
        )
