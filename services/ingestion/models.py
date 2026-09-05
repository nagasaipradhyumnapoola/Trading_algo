"""Domain models for the data spine (Phase 1).

Point-in-time by construction: every bar carries the session it belongs to plus
when it was ingested and which correction version it is, so historical queries can
reproduce exactly what was known at a past decision time. Money is Decimal.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"


class Timeframe(str, Enum):
    EOD = "EOD"


class InstrumentStatus(str, Enum):
    LISTED = "LISTED"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Instrument(BaseModel):
    """One tradable security in the universe. `instrument_id` is the immutable key."""

    model_config = ConfigDict(frozen=True)

    instrument_id: str                      # canonical internal id (stable, immutable)
    isin: str | None = None
    symbol: str                             # primary trading symbol
    name: str
    exchange: Exchange = Exchange.NSE
    nse_symbol: str | None = None
    bse_code: str | None = None
    sector: str | None = None
    listing_date: date | None = None
    status: InstrumentStatus = InstrumentStatus.LISTED


class Bar(BaseModel):
    """One OHLCV bar. Immutable; corrections append a new correction_version."""

    model_config = ConfigDict(frozen=True)

    instrument_id: str
    timeframe: Timeframe = Timeframe.EOD
    session_date: date                      # Asia/Kolkata trading session
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = Field(ge=0)
    turnover: Decimal | None = None
    source: str
    adjusted: bool = False                  # split/bonus/dividend adjusted?
    ingested_at: datetime = Field(default_factory=_utcnow)
    correction_version: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_ohlc(self) -> "Bar":
        hi, lo = self.high, self.low
        if hi < lo:
            raise ValueError(f"high {hi} < low {lo}")
        if hi < max(self.open, self.close):
            raise ValueError("high below open/close")
        if lo > min(self.open, self.close):
            raise ValueError("low above open/close")
        return self

    @property
    def value_key(self) -> tuple:
        """Identity of the bar's *content* (excludes ingest metadata)."""
        return (
            self.instrument_id, self.timeframe, self.session_date,
            self.source, self.adjusted,
        )

    @property
    def value_payload(self) -> tuple:
        """The values a correction would change."""
        return (self.open, self.high, self.low, self.close, self.volume, self.turnover)
