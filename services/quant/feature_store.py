"""Point-in-time feature store and dataset builder.

Features are keyed by (instrument_id, as_of, feature_set_version) and are always
computed from `repo.as_of(as_of)` — the builder can only see data that existed at
that time, so a dataset rebuilt from the same source snapshot is identical and
free of look-ahead. Persisted as JSONL for a faithful, auditable round-trip.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from services.ingestion.instruments import InstrumentMaster
from services.ingestion.models import Timeframe
from services.ingestion.repository import BarRepository

from .features import FeatureSnapshot, compute_features


class FeatureStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._store: dict[tuple[str, str, str], FeatureSnapshot] = {}
        self._path = Path(path) if path else None

    @staticmethod
    def _key(instrument_id: str, as_of: date, version: str) -> tuple[str, str, str]:
        return (instrument_id, as_of.isoformat(), version)

    def put(self, snap: FeatureSnapshot) -> None:
        self._store[self._key(snap.instrument_id, snap.as_of, snap.feature_set_version)] = snap
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(snap.model_dump_json() + "\n")

    def get(self, instrument_id: str, as_of: date, version: str) -> FeatureSnapshot | None:
        return self._store.get(self._key(instrument_id, as_of, version))

    def all(self) -> list[FeatureSnapshot]:
        return list(self._store.values())

    @classmethod
    def load(cls, path: str | Path) -> "FeatureStore":
        store = cls()
        p = Path(path)
        if p.exists():
            with p.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        snap = FeatureSnapshot.model_validate_json(line)
                        store._store[cls._key(snap.instrument_id, snap.as_of, snap.feature_set_version)] = snap
        return store

    def __len__(self) -> int:
        return len(self._store)


def build_features_asof(
    repo: BarRepository, master: InstrumentMaster, as_of: date, **kwargs
) -> list[FeatureSnapshot]:
    """Point-in-time feature snapshots for every tradable instrument as of `as_of`."""
    out: list[FeatureSnapshot] = []
    for inst in master.tradable():
        bars = repo.as_of(inst.instrument_id, Timeframe.EOD, as_of)
        if bars:
            out.append(compute_features(bars, as_of, **kwargs))
    return out


def build_dataset(
    repo: BarRepository,
    master: InstrumentMaster,
    as_of_dates: Iterable[date],
    *,
    store: FeatureStore | None = None,
    **kwargs,
) -> list[FeatureSnapshot]:
    """Build a point-in-time feature dataset across many as_of dates (deterministic)."""
    rows: list[FeatureSnapshot] = []
    for as_of in as_of_dates:
        for snap in build_features_asof(repo, master, as_of, **kwargs):
            rows.append(snap)
            if store is not None:
                store.put(snap)
    return rows


def to_dataframe(snapshots: list[FeatureSnapshot]) -> pd.DataFrame:
    records = []
    for s in snapshots:
        rec = {"instrument_id": s.instrument_id, "as_of": s.as_of,
               "feature_set_version": s.feature_set_version, "quality": s.quality.value}
        rec.update(s.values)
        records.append(rec)
    return pd.DataFrame(records)
