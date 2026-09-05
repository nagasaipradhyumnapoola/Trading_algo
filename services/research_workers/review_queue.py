"""Human-review queue.

Low-confidence extractions, conflicting claims, and degraded (LLM-unavailable)
results are queued for a human instead of flowing downstream unquestioned.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ReviewReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    CONFLICT = "conflict"
    DEGRADED = "degraded"


class ReviewItem(BaseModel):
    instrument_id: str
    task: str
    reason: ReviewReason
    detail: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewQueue:
    def __init__(self, path: str | Path | None = None) -> None:
        self._items: list[ReviewItem] = []
        self._path = Path(path) if path else None

    def enqueue(self, item: ReviewItem) -> ReviewItem:
        self._items.append(item)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(item.model_dump_json() + "\n")
        return item

    def items(self) -> list[ReviewItem]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)
