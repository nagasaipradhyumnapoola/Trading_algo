"""Purged walk-forward CV."""

from datetime import date, timedelta

from services.evaluation import purged_walk_forward

DATES = [date(2026, 1, 1) + timedelta(days=i) for i in range(100)]


def test_folds_are_chronological_and_purged():
    folds = purged_walk_forward(DATES, n_splits=4, horizon=5, embargo=2)
    assert len(folds) == 4
    for train_idx, test_idx in folds:
        if not train_idx:
            continue
        max_train = max(DATES[i] for i in train_idx)
        min_test = min(DATES[i] for i in test_idx)
        assert max_train < min_test                              # chronological
        assert (min_test - max_train).days > 5 + 2 - 1          # purge + embargo gap


def test_test_blocks_disjoint():
    folds = purged_walk_forward(DATES, n_splits=4)
    seen: set[int] = set()
    for _, test_idx in folds:
        assert not (seen & set(test_idx))
        seen |= set(test_idx)
