"""Event-study engine — benchmark-adjusted abnormal returns.

For an event at (instrument, date), measures the forward abnormal return (AR) and
cumulative abnormal return (CAR) over 1/3/5/10 sessions versus a leave-one-out
equal-weight universe benchmark, plus maximum adverse/favorable excursion. Uses
only sessions AFTER the event; outcomes are realized forward data, which is the
correct use (feature computation stays point-in-time elsewhere).
"""

from __future__ import annotations

from datetime import date
from statistics import fmean

from pydantic import BaseModel, Field

from services.ingestion.models import Timeframe
from services.ingestion.repository import BarRepository

_HORIZONS = (1, 3, 5, 10)


class EventStudyResult(BaseModel):
    instrument_id: str
    event_date: date
    ar_1d: float = 0.0
    car: dict[int, float] = Field(default_factory=dict)
    mae: float = 0.0                # max adverse excursion (min cumulative AR)
    mfe: float = 0.0                # max favorable excursion (max cumulative AR)
    n_sessions: int = 0


class AggregateStudy(BaseModel):
    n: int = 0
    mean_car: dict[int, float] = Field(default_factory=dict)
    positive_rate: dict[int, float] = Field(default_factory=dict)


class EventStudy:
    def __init__(self, repo: BarRepository, instrument_ids: list[str]) -> None:
        self._rets: dict[str, dict[date, float]] = {}
        for iid in instrument_ids:
            bars = repo.as_of(iid, Timeframe.EOD, date.max)
            series: dict[date, float] = {}
            for prev, cur in zip(bars, bars[1:]):
                if float(prev.close):
                    series[cur.session_date] = float(cur.close) / float(prev.close) - 1.0
            self._rets[iid] = series

    def _benchmark(self, exclude: str, d: date) -> float:
        others = [r[d] for iid, r in self._rets.items() if iid != exclude and d in r]
        return fmean(others) if others else 0.0

    def study(self, instrument_id: str, event_date: date,
              horizons: tuple[int, ...] = _HORIZONS) -> EventStudyResult:
        series = self._rets.get(instrument_id, {})
        post = sorted(d for d in series if d > event_date)[: max(horizons)]
        ar = [series[d] - self._benchmark(instrument_id, d) for d in post]

        cum, running, mae, mfe = [], 0.0, 0.0, 0.0
        for a in ar:
            running += a
            cum.append(running)
            mae, mfe = min(mae, running), max(mfe, running)

        car = {h: cum[h - 1] for h in horizons if len(cum) >= h}
        return EventStudyResult(
            instrument_id=instrument_id, event_date=event_date,
            ar_1d=ar[0] if ar else 0.0, car=car, mae=mae, mfe=mfe, n_sessions=len(ar),
        )

    def aggregate(self, events: list[tuple[str, date]],
                  horizons: tuple[int, ...] = _HORIZONS) -> AggregateStudy:
        results = [self.study(iid, d, horizons) for iid, d in events]
        agg = AggregateStudy(n=len(results))
        for h in horizons:
            cars = [r.car[h] for r in results if h in r.car]
            if cars:
                agg.mean_car[h] = fmean(cars)
                agg.positive_rate[h] = sum(1 for c in cars if c > 0) / len(cars)
        return agg
