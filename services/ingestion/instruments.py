"""Instrument master — the tradable universe.

Loads instruments from a CSV (Phase 1 offline path) into a lookup keyed by
instrument_id, with a symbol index. Point-in-time universe membership (which names
were listed on a given date) is added in Phase 2.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterator

from .models import Exchange, Instrument, InstrumentStatus


def _parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    return date.fromisoformat(value) if value else None


def load_instruments_csv(path: str | Path) -> list[Instrument]:
    """Columns: instrument_id, symbol, name, [exchange, isin, sector, listing_date, status]."""
    out: list[Instrument] = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(
                Instrument(
                    instrument_id=row["instrument_id"].strip(),
                    symbol=row["symbol"].strip(),
                    name=row["name"].strip(),
                    exchange=Exchange((row.get("exchange") or "NSE").strip() or "NSE"),
                    isin=(row.get("isin") or "").strip() or None,
                    sector=(row.get("sector") or "").strip() or None,
                    listing_date=_parse_date(row.get("listing_date")),
                    status=InstrumentStatus((row.get("status") or "LISTED").strip() or "LISTED"),
                )
            )
    return out


class InstrumentMaster:
    """In-memory universe with id and symbol lookups."""

    def __init__(self, instruments: list[Instrument]) -> None:
        self._by_id: dict[str, Instrument] = {i.instrument_id: i for i in instruments}
        self._by_symbol: dict[str, Instrument] = {i.symbol: i for i in instruments}

    @classmethod
    def from_csv(cls, path: str | Path) -> "InstrumentMaster":
        return cls(load_instruments_csv(path))

    def get(self, instrument_id: str) -> Instrument | None:
        return self._by_id.get(instrument_id)

    def by_symbol(self, symbol: str) -> Instrument | None:
        return self._by_symbol.get(symbol)

    def tradable(self) -> list[Instrument]:
        return [i for i in self._by_id.values() if i.status is InstrumentStatus.LISTED]

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self) -> Iterator[Instrument]:
        return iter(self._by_id.values())
