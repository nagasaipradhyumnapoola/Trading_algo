"""ingestion — source adapters, trading calendars, normalization.

Phase 1 home: instrument master + EOD OHLCV ingestion (raw snapshots,
idempotency, freshness checks, adjusted/unadjusted series). Everything else in
the system sits on this data spine.
"""

from .adapters import CsvEodAdapter, SourceAdapter
from .instruments import InstrumentMaster, load_instruments_csv
from .loader import LoadReport, load_eod
from .models import (
    Bar,
    Exchange,
    Instrument,
    InstrumentStatus,
    Timeframe,
)
from .repository import BarRepository, InMemoryBarRepository

__all__ = [
    "Bar",
    "Instrument",
    "Exchange",
    "Timeframe",
    "InstrumentStatus",
    "InstrumentMaster",
    "load_instruments_csv",
    "CsvEodAdapter",
    "SourceAdapter",
    "BarRepository",
    "InMemoryBarRepository",
    "load_eod",
    "LoadReport",
]
