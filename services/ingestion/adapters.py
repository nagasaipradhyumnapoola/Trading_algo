"""Source adapters — turn a raw feed into validated `Bar` objects.

CsvEodAdapter reads a local OHLCV CSV (the Phase 1 sample/offline path). Licensed
API adapters implement the same `SourceAdapter` protocol in Phase 2 without any
change downstream.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Protocol

from .models import Bar, Timeframe


class SourceAdapter(Protocol):
    name: str
    def bars(self) -> Iterator[Bar]: ...


class CsvEodAdapter:
    """EOD OHLCV from a CSV.

    Expected columns: instrument_id, session_date (YYYY-MM-DD), open, high, low,
    close, volume, and optional turnover.
    """

    def __init__(self, path: str | Path, *, source: str = "csv", adjusted: bool = False) -> None:
        self.path = Path(path)
        self.name = source
        self.adjusted = adjusted

    def bars(self) -> Iterator[Bar]:
        with self.path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                turnover = row.get("turnover")
                yield Bar(
                    instrument_id=row["instrument_id"].strip(),
                    timeframe=Timeframe.EOD,
                    session_date=date.fromisoformat(row["session_date"].strip()),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=int(row["volume"]),
                    turnover=Decimal(turnover) if turnover not in (None, "") else None,
                    source=self.name,
                    adjusted=self.adjusted,
                )
