"""Append-only paper-signal ledger.

Records every signal exactly as if it were live — no broker connection. Immutable:
records are appended, never edited or deleted, and each carries the model and data
versions that produced it. Optionally mirrored to a JSONL file for a durable audit
trail. This is the record graded later against realized outcomes.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ROTATE = "ROTATE"
    NO_TRADE = "NO_TRADE"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaperSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    created_at: datetime = Field(default_factory=_utcnow)
    instrument_id: str
    as_of: date
    action: Action
    entry_rule: str = "next_open"
    stop_pct: float | None = None
    target_pct: float | None = None
    horizon_sessions: int | None = None
    score: float | None = None
    reason: str = ""
    model_version: str
    data_version: str


class PaperLedger:
    """In-memory append-only ledger, optionally mirrored to a JSONL file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[PaperSignal] = []
        self._path = Path(path) if path else None

    def append(self, record: PaperSignal) -> PaperSignal:
        self._records.append(record)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(record.model_dump_json() + "\n")
        return record

    def all(self) -> list[PaperSignal]:
        return list(self._records)          # copy: callers cannot mutate the ledger

    @classmethod
    def load(cls, path: str | Path) -> "PaperLedger":
        ledger = cls(path)
        p = Path(path)
        if p.exists():
            with p.open(encoding="utf-8") as fh:
                ledger._records = [PaperSignal.model_validate_json(line) for line in fh if line.strip()]
        return ledger

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[PaperSignal]:
        return iter(self._records)
