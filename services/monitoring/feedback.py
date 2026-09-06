"""User feedback store — kept SEPARATE from realized outcomes.

Feedback (useful / not useful, executed / not executed) is the user's opinion and
must never be mixed with the fixed-rule realized outcomes used to grade the system.
Append-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FeedbackLabel(str, Enum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    EXECUTED = "executed"
    NOT_EXECUTED = "not_executed"


class Feedback(BaseModel):
    instrument_id: str
    rec_id: str = ""
    label: FeedbackLabel
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._items: list[Feedback] = []
        self._path = Path(path) if path else None

    def record(self, feedback: Feedback) -> Feedback:
        self._items.append(feedback)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(feedback.model_dump_json() + "\n")
        return feedback

    def items(self) -> list[Feedback]:
        return list(self._items)

    def by_instrument(self, instrument_id: str) -> list[Feedback]:
        return [f for f in self._items if f.instrument_id == instrument_id]
