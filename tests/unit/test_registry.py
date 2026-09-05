"""Experiment registry and reproducibility check."""

from services.evaluation import ExperimentRecord, ExperimentRegistry, is_reproducible


def _rec(seed=7, metrics=None, name="baseline"):
    return ExperimentRecord(
        name=name, data_snapshot="snap_abc", feature_set_version="fs-0.1",
        config={"stop_pct": 0.03, "target_pct": 0.06}, seed=seed,
        code_version="deadbeef", metrics=metrics or {"win_rate": 0.6, "profit_factor": 1.86},
    )


def test_same_fingerprint_and_metrics_is_reproducible():
    assert is_reproducible(_rec(), _rec())


def test_different_metrics_breaks_reproducibility():
    assert not is_reproducible(_rec(), _rec(metrics={"win_rate": 0.55, "profit_factor": 1.5}))


def test_different_seed_is_a_different_experiment():
    # Different fingerprint -> not the "same run", so not comparable as reproducible.
    assert not is_reproducible(_rec(seed=7), _rec(seed=8))


def test_registry_register_and_persist(tmp_path):
    path = tmp_path / "experiments.jsonl"
    reg = ExperimentRegistry(path)
    r = reg.register(_rec())
    assert reg.get(r.experiment_id) is not None
    assert len(ExperimentRegistry.load(path)) == 1
    assert reg.by_name("baseline")[0].data_snapshot == "snap_abc"
