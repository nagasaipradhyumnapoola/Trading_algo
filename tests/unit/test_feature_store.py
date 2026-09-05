"""Point-in-time feature store: determinism, no look-ahead, persistence."""

from datetime import timedelta

from services.ingestion import Bar
from services.ingestion.sample import SAMPLE_START, build_sample_universe
from services.quant.feature_store import (
    FeatureStore,
    build_features_asof,
    to_dataframe,
)

AS_OF = SAMPLE_START + timedelta(days=40)


def _snap(snaps, iid):
    return next(s for s in snaps if s.instrument_id == iid)


def test_dataset_build_is_deterministic():
    repo, master, _ = build_sample_universe()
    a = build_features_asof(repo, master, AS_OF)
    b = build_features_asof(repo, master, AS_OF)
    assert {s.instrument_id: s.values for s in a} == {s.instrument_id: s.values for s in b}


def test_features_have_no_lookahead():
    repo, master, _ = build_sample_universe()
    before = _snap(build_features_asof(repo, master, AS_OF), "MOMO").values

    # Inject a wild FUTURE bar; features as-of the earlier date must not change.
    repo.upsert(Bar(instrument_id="MOMO", session_date=AS_OF + timedelta(days=3),
                    open=999, high=1200, low=998, close=1100, volume=99, source="sample"))
    after = _snap(build_features_asof(repo, master, AS_OF), "MOMO").values
    assert before == after


def test_feature_store_jsonl_round_trip(tmp_path):
    repo, master, _ = build_sample_universe()
    path = tmp_path / "features.jsonl"
    store = FeatureStore(path)
    for snap in build_features_asof(repo, master, AS_OF):
        store.put(snap)

    reloaded = FeatureStore.load(path)
    assert len(reloaded) == len(store)
    momo = reloaded.get("MOMO", AS_OF, "fs-0.1")
    assert momo is not None and "momentum" in momo.values


def test_to_dataframe_shape():
    repo, master, _ = build_sample_universe()
    df = to_dataframe(build_features_asof(repo, master, AS_OF))
    assert "momentum" in df.columns and "instrument_id" in df.columns
    assert len(df) >= 1
