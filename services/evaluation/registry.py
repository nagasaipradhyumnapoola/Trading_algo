"""Experiment registry — reproducibility bookkeeping.

Every research run records what fully determines it: the data snapshot, feature-set
version, config, seed, and code version, plus the metrics it produced. Two runs
with the same fingerprint must produce the same metrics; if they don't, the run is
not reproducible and the result is not trustworthy.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    created_at: datetime = Field(default_factory=_utcnow)
    name: str
    data_snapshot: str                 # id/hash/path of the source snapshot
    feature_set_version: str
    config: dict[str, Any] = Field(default_factory=dict)
    seed: int = 0
    code_version: str = ""             # git commit / tag
    model_artifact_uri: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)

    def fingerprint(self) -> tuple:
        """What must match for two runs to be considered the same experiment."""
        return (self.data_snapshot, self.feature_set_version,
                tuple(sorted(self.config.items())), self.seed, self.code_version)


def metrics_match(a: dict[str, float], b: dict[str, float], *, tol: float = 1e-9) -> bool:
    if a.keys() != b.keys():
        return False
    return all(abs(a[k] - b[k]) <= tol for k in a)


def is_reproducible(a: ExperimentRecord, b: ExperimentRecord, *, tol: float = 1e-9) -> bool:
    return a.fingerprint() == b.fingerprint() and metrics_match(a.metrics, b.metrics, tol=tol)


class ExperimentRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[ExperimentRecord] = []
        self._path = Path(path) if path else None

    def register(self, record: ExperimentRecord) -> ExperimentRecord:
        self._records.append(record)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(record.model_dump_json() + "\n")
        return record

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        return next((r for r in self._records if r.experiment_id == experiment_id), None)

    def by_name(self, name: str) -> list[ExperimentRecord]:
        return [r for r in self._records if r.name == name]

    def all(self) -> list[ExperimentRecord]:
        return list(self._records)

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentRegistry":
        reg = cls(path)
        p = Path(path)
        if p.exists():
            reg._records = [ExperimentRecord.model_validate_json(line)
                            for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        return reg

    def __len__(self) -> int:
        return len(self._records)
