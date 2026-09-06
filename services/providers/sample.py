"""Sample provider implementations (demo mode).

Demo runs through the SAME interfaces as real providers — so wiring the quant engine
to a provider is exercised end-to-end without a live feed. Clearly synthetic.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from services.ingestion.corporate_actions import CorporateAction
from services.ingestion.models import Bar, Instrument, Timeframe
from services.ingestion.sample import build_sample_universe

from .interfaces import RawItem


class SampleMarketDataProvider:
    name = "sample"

    def __init__(self, n: int = 160) -> None:
        self._repo, self._master, self._last = build_sample_universe(n=n)

    def instruments(self) -> list[Instrument]:
        return list(self._master)

    def eod_bars(self, instrument_id: str, *, start: date | None = None,
                 end: date | None = None) -> list[Bar]:
        bars = self._repo.as_of(instrument_id, Timeframe.EOD, end or date.max)
        return [b for b in bars if start is None or b.session_date >= start]

    def corporate_actions(self, instrument_id: str) -> list[CorporateAction]:
        return []                       # synthetic universe has none


class SampleNewsProvider:
    name = "sample"

    def search(self, query: str, *, since: datetime | None = None, limit: int = 50) -> list[RawItem]:
        now = datetime.now(timezone.utc)
        return [RawItem(content=f"Sample news re '{query}': momentum and volume elevated.",
                        source="SampleWire", tier=3, published_at=now, title=query)][:limit]


class SampleFilingsProvider:
    name = "sample"

    def filings(self, instrument_id: str, *, since: datetime | None = None,
                limit: int = 50) -> list[RawItem]:
        now = datetime.now(timezone.utc)
        return [RawItem(content=f"NSE filing ({instrument_id}): order/catalyst noted.",
                        source="NSE", tier=1, published_at=now, instrument_id=instrument_id,
                        title=f"{instrument_id} disclosure")][:limit]
