"""Parquet-backed bar repository for reproducible research.

Same semantics as InMemoryBarRepository, persisted to a Parquet file. Decimals and
dates are stored as strings so money and sessions round-trip exactly; the full
correction history is written, not just the latest version, so any dated dataset
can be rebuilt from the stored snapshot.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .models import Bar, Timeframe
from .repository import InMemoryBarRepository

_COLUMNS = [
    "instrument_id", "timeframe", "session_date", "open", "high", "low", "close",
    "volume", "turnover", "source", "adjusted", "ingested_at", "correction_version",
]


def _bar_to_row(b: Bar) -> dict:
    return {
        "instrument_id": b.instrument_id,
        "timeframe": b.timeframe.value,
        "session_date": b.session_date.isoformat(),
        "open": str(b.open), "high": str(b.high), "low": str(b.low), "close": str(b.close),
        "volume": int(b.volume),
        "turnover": None if b.turnover is None else str(b.turnover),
        "source": b.source,
        "adjusted": bool(b.adjusted),
        "ingested_at": b.ingested_at.isoformat(),
        "correction_version": int(b.correction_version),
    }


def _row_to_bar(row: dict) -> Bar:
    turnover = row["turnover"]
    _missing = turnover is None or (isinstance(turnover, float) and pd.isna(turnover))
    turnover = None if _missing else Decimal(str(turnover))
    return Bar(
        instrument_id=row["instrument_id"],
        timeframe=Timeframe(row["timeframe"]),
        session_date=date.fromisoformat(row["session_date"]),
        open=Decimal(str(row["open"])), high=Decimal(str(row["high"])),
        low=Decimal(str(row["low"])), close=Decimal(str(row["close"])),
        volume=int(row["volume"]), turnover=turnover, source=row["source"],
        adjusted=bool(row["adjusted"]),
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
        correction_version=int(row["correction_version"]),
    )


class ParquetBarRepository(InMemoryBarRepository):
    """In-memory logic + Parquet persistence."""

    def __init__(self, path: str | Path | None = None) -> None:
        super().__init__()
        self.path = Path(path) if path else None

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("no path given to save()")
        rows = [_bar_to_row(b) for b in sorted(
            self.history_bars(), key=lambda b: (b.instrument_id, b.session_date, b.correction_version)
        )]
        df = pd.DataFrame(rows, columns=_COLUMNS)
        target.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(target, index=False)
        return target

    @classmethod
    def load(cls, path: str | Path) -> "ParquetBarRepository":
        repo = cls(path)
        p = Path(path)
        if p.exists():
            df = pd.read_parquet(p)
            # replay in correction order so latest() reflects the newest version
            for row in df.sort_values("correction_version").to_dict("records"):
                repo.upsert(_row_to_bar(row))
        return repo
