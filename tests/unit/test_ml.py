"""ML baseline models + feature-matrix assembly."""

from types import SimpleNamespace

import numpy as np

from services.quant.ml import (
    BaseRateModel,
    LogisticModel,
    MomentumRuleModel,
    build_xy,
)


def _data():
    mom = np.linspace(-0.2, 0.2, 60)
    X = np.column_stack([mom, np.full(60, 2.0), np.full(60, 0.02)])
    y = (mom > 0).astype(int)
    return X, y


def test_logistic_learns_separable_signal():
    X, y = _data()
    m = LogisticModel().fit(X, y)
    p = m.predict_proba(X)
    assert p[y == 1].mean() > p[y == 0].mean() + 0.2


def test_base_rate_is_constant():
    X, y = _data()
    m = BaseRateModel().fit(X, y)
    p = m.predict_proba(X)
    assert np.allclose(p, y.mean())


def test_momentum_rule_monotonic():
    X, y = _data()
    p = MomentumRuleModel().fit(X, y).predict_proba(X)
    assert p[-1] > 0.5 > p[0]                       # +momentum vs -momentum


def test_logistic_single_class_falls_back():
    X = np.random.RandomState(0).rand(10, 3)
    m = LogisticModel().fit(X, np.ones(10, int))    # all positive
    assert np.allclose(m.predict_proba(X), 1.0)


def test_build_xy_skips_rows_missing_features():
    pairs = [
        (SimpleNamespace(values={"momentum": 0.1, "volume_ratio": 2.0, "realized_vol": 0.02}),
         SimpleNamespace(y=1)),
        (SimpleNamespace(values={"momentum": 0.1, "volume_ratio": 2.0}),   # missing realized_vol
         SimpleNamespace(y=0)),
    ]
    X, y = build_xy(pairs)
    assert X.shape == (1, 3) and list(y) == [1]
