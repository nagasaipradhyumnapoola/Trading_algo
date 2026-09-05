"""Bar storage with idempotency, correction history, and point-in-time queries.

InMemoryBarRepository is the reference implementation (stdlib only, test-friendly).
ParquetBarRepository persists the same semantics to a Parquet file for research.
A Postgres/TimescaleDB adapter follows in Phase 2.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

from .models import Bar, Timeframe


class BarRepository(Protocol):
    def upsert(self, bar: Bar) -> str: ...
    def latest(self, value_key: tuple) -> Bar | None: ...
    def all_latest(self) -> list[Bar]: ...
    def as_of(
        self, instrument_id: str, timeframe: Timeframe, as_of: date,
        *, source: str | None = None, adjusted: bool = False,
    ) -> list[Bar]: ...


class InMemoryBarRepository:
    """Keeps full correction history per content key; returns the latest by default."""

    def __init__(self) -> None:
        # value_key -> list[Bar] ordered by correction_version
        self._history: dict[tuple, list[Bar]] = {}

    def upsert(self, bar: Bar) -> str:
        """Return 'added' | 'skipped' | 'corrected'.

        - new content key            -> add at correction_version 0        -> 'added'
        - same key, identical values -> no-op (idempotent)                 -> 'skipped'
        - same key, changed values   -> append correction_version+1        -> 'corrected'
        """
        hist = self._history.get(bar.value_key)
        if hist is None:
            self._history[bar.value_key] = [bar.model_copy(update={"correction_version": 0})]
            return "added"
        current = hist[-1]
        if current.value_payload == bar.value_payload:
            return "skipped"
        corrected = bar.model_copy(update={"correction_version": current.correction_version + 1})
        hist.append(corrected)
        return "corrected"

    def upsert_many(self, bars: Iterable[Bar]) -> dict[str, int]:
        counts = {"added": 0, "skipped": 0, "corrected": 0}
        for bar in bars:
            counts[self.upsert(bar)] += 1
        return counts

    def latest(self, value_key: tuple) -> Bar | None:
        hist = self._history.get(value_key)
        return hist[-1] if hist else None

    def all_latest(self) -> list[Bar]:
        return [hist[-1] for hist in self._history.values()]

    def as_of(
        self, instrument_id: str, timeframe: Timeframe, as_of: date,
        *, source: str | None = None, adjusted: bool = False,
    ) -> list[Bar]:
        """Bars for an instrument with session_date <= as_of. The leakage guard."""
        out = [
            hist[-1]
            for hist in self._history.values()
            if hist[-1].instrument_id == instrument_id
            and hist[-1].timeframe == timeframe
            and hist[-1].adjusted == adjusted
            and (source is None or hist[-1].source == source)
            and hist[-1].session_date <= as_of
        ]
        return sorted(out, key=lambda b: b.session_date)

    def __len__(self) -> int:
        return len(self._history)
