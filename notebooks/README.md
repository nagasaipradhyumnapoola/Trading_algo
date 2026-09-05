# Research notebooks

Read-only, reproducible exploration. Every run must be rebuildable from a
recorded snapshot + feature version + config + seed (see the experiment registry
in `services/evaluation/registry.py`).

## Canonical reproducible pattern

`scripts/reproducibility_demo.py` is the reference: build a point-in-time dataset
from a persisted Parquet snapshot, and confirm a rebuild is identical. Start any
research notebook from that pattern:

```python
from services.ingestion.parquet_store import ParquetBarRepository
from services.quant.feature_store import build_dataset, to_dataframe
from services.evaluation import ExperimentRecord, ExperimentRegistry

repo = ParquetBarRepository.load("data/snapshots/<dated>.parquet")
# ... build point-in-time features, train, evaluate ...
# register the run so it can be reproduced and compared:
ExperimentRegistry("experiments.jsonl").register(ExperimentRecord(
    name="...", data_snapshot="<dated>", feature_set_version="fs-0.1",
    config={...}, seed=7, metrics={...}))
```

Do not tune on the untouched test period. Keep train / validation / test / paper
as separate labeled datasets.
