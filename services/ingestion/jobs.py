"""Lightweight job runner with bounded retries and a dead-letter queue.

A dependency-free stand-in for the production orchestrator (Prefect is the Phase 7
target). Jobs that exhaust their retries land in the dead-letter queue for replay
instead of failing silently.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeadLetter(BaseModel):
    job: str
    error: str
    attempts: int
    at: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class DeadLetterQueue:
    def __init__(self, path: str | Path | None = None) -> None:
        self._items: list[DeadLetter] = []
        self._path = Path(path) if path else None

    def add(self, item: DeadLetter) -> None:
        self._items.append(item)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(item.model_dump_json() + "\n")

    def items(self) -> list[DeadLetter]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)


class JobResult(BaseModel):
    job: str
    success: bool
    attempts: int
    error: str | None = None


def run_job(
    name: str,
    fn: Callable[[], Any],
    *,
    retries: int = 2,
    backoff_s: float = 0.0,
    dlq: DeadLetterQueue | None = None,
    payload: dict[str, Any] | None = None,
) -> JobResult:
    """Run fn, retrying up to `retries` times. On final failure, dead-letter it."""
    last_error = ""
    for attempt in range(1, retries + 2):        # initial try + `retries` retries
        try:
            fn()
            return JobResult(job=name, success=True, attempts=attempt)
        except Exception as exc:                  # noqa: BLE001 — runner captures all
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt <= retries and backoff_s:
                time.sleep(backoff_s)

    if dlq is not None:
        dlq.add(DeadLetter(job=name, error=last_error, attempts=retries + 1,
                           payload=payload or {}))
    return JobResult(job=name, success=False, attempts=retries + 1, error=last_error)
