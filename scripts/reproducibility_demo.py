"""Phase 2 demo: point-in-time reproducibility end to end.

Persists the sample bars to Parquet, reloads them, and shows the feature dataset
rebuilt from the reloaded snapshot is IDENTICAL — then runs data quality, the
document-store dedup, and the experiment reproducibility check.

Run:
    python scripts/reproducibility_demo.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.evaluation import ExperimentRecord, is_reproducible          # noqa: E402
from services.ingestion import RawDocumentStore, TradingCalendar, run_quality  # noqa: E402
from services.ingestion.parquet_store import ParquetBarRepository          # noqa: E402
from services.ingestion.sample import SAMPLE_START, build_sample_universe  # noqa: E402
from services.quant.feature_store import build_dataset, to_dataframe       # noqa: E402


def main() -> None:
    repo, master, last = build_sample_universe()
    as_of_dates = [SAMPLE_START + timedelta(days=d) for d in (30, 35, 40, 45)]

    tmp = Path(tempfile.mkdtemp())

    # 1) persist to Parquet, reload
    pq = ParquetBarRepository(tmp / "bars.parquet")
    for b in repo.history_bars():
        pq.upsert(b)
    pq.save()
    reloaded = ParquetBarRepository.load(tmp / "bars.parquet")

    # 2) rebuild the dataset from both sources; compare
    d_orig = {(s.instrument_id, s.as_of): s.values for s in build_dataset(repo, master, as_of_dates)}
    d_reload = {(s.instrument_id, s.as_of): s.values for s in build_dataset(reloaded, master, as_of_dates)}
    match = d_orig == d_reload
    print(f"bars persisted:        {len(pq.history_bars())}")
    print(f"dataset rows:          {len(d_orig)}")
    print(f"reproducible rebuild:  {'MATCH' if match else 'MISMATCH'}")

    df = to_dataframe(build_dataset(repo, master, [last]))
    print(f"feature matrix (as of {last}): {df.shape[0]} rows x {df.shape[1]} cols")

    # 3) data quality
    cal = TradingCalendar.from_bars(repo.history_bars())
    rep = run_quality(repo.all_latest(), calendar=cal, as_of=last)
    print(f"data quality:          {len(rep.errors())} errors, {len(rep.warnings())} warnings")

    # 4) document dedup (syndicated copies -> one event)
    docs = RawDocumentStore(tmp / "docs")
    docs.store("Reuters: Co wins order", source="Reuters", tier=2)
    docs.store("Reuters: Co wins order", source="ET-syndicated", tier=3)
    print(f"documents (2 copies):  {len(docs)} unique")

    # 5) reproducibility check
    a = ExperimentRecord(name="baseline", data_snapshot="parquet:bars", feature_set_version="fs-0.1",
                         config={"stop_pct": 0.03}, seed=7, metrics={"win_rate": 0.6})
    b = a.model_copy(update={"experiment_id": "exp_second"})
    print(f"experiment reproducible: {is_reproducible(a, b)}")


if __name__ == "__main__":
    main()
