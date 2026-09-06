"""Provider-agnostic adapter interfaces.

The quant engine consumes NORMALIZED domain types (Instrument, Bar, CorporateAction,
SourceDocument) — never a provider SDK. Any licensed NSE/BSE market-data feed, news
API, or filings source is plugged in by implementing these Protocols and registering
it in the factory; nothing in services/quant changes.

Three separate concerns, deliberately decoupled:
  - MarketDataProvider  -> prices/volume + corporate data
  - NewsProvider        -> reputable news APIs (Reuters/ET/Moneycontrol/...)
  - FilingsProvider     -> official NSE/BSE/company IR disclosures (highest trust)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from services.ingestion.corporate_actions import CorporateAction
from services.ingestion.models import Bar, Instrument


class NotConfigured(RuntimeError):
    """Raised in real mode when a required provider is not configured/registered."""


class RawItem(BaseModel):
    """A fetched document before persistence. RawDocumentStore turns it into a
    content-addressed, de-duplicated SourceDocument."""

    content: str
    source: str
    url: str | None = None
    title: str = ""
    tier: int = Field(default=3, ge=1, le=4)     # 1=NSE/SEBI … 4=social
    published_at: datetime | None = None
    rights: str | None = None
    instrument_id: str | None = None


@runtime_checkable
class MarketDataProvider(Protocol):
    name: str
    def instruments(self) -> list[Instrument]: ...
    def eod_bars(self, instrument_id: str, *, start: date | None = None,
                 end: date | None = None) -> list[Bar]: ...
    def corporate_actions(self, instrument_id: str) -> list[CorporateAction]: ...


@runtime_checkable
class NewsProvider(Protocol):
    name: str
    def search(self, query: str, *, since: datetime | None = None,
               limit: int = 50) -> list[RawItem]: ...


@runtime_checkable
class FilingsProvider(Protocol):
    name: str
    def filings(self, instrument_id: str, *, since: datetime | None = None,
                limit: int = 50) -> list[RawItem]: ...
