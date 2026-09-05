"""Calibration + reliability metrics."""

import numpy as np

from services.quant.calibration import (
    IsotonicCalibrator,
    PlattCalibrator,
    brier,
    logloss,
    precision_at_coverage,
    precision_at_threshold,
    reliability_curve,
)

# Correct ranking, poor calibration: negatives at 0.4, positives at 0.6.
Y = np.array([0] * 50 + [1] * 50)
RAW = np.concatenate([np.full(50, 0.4), np.full(50, 0.6)])


def test_brier_rewards_good_probabilities():
    assert brier(Y.astype(float), Y) == 0.0                 # perfect
    assert brier(np.full(100, 0.5), Y) > brier(RAW, Y)      # 0.5 worse than ranked


def test_isotonic_improves_calibration():
    cal = IsotonicCalibrator().fit(RAW, Y).transform(RAW)
    assert brier(cal, Y) < brier(RAW, Y)


def test_platt_improves_calibration():
    cal = PlattCalibrator().fit(RAW, Y).transform(RAW)
    assert cal[Y == 1].mean() > cal[Y == 0].mean()          # ranking preserved
    assert brier(cal, Y) < brier(np.full(100, 0.5), Y)      # better than uninformative


def test_reliability_curve_partitions_all():
    bins = reliability_curve(RAW, Y, bins=10)
    assert sum(b.count for b in bins) == 100
    for b in bins:
        assert b.lo - 1e-9 <= b.mean_pred <= b.hi + 1e-9    # tolerate float edges
    # the ~0.6 bin is all positives, the ~0.4 bin all negatives
    assert any(b.frac_pos == 1.0 for b in bins) and any(b.frac_pos == 0.0 for b in bins)


def test_logloss_finite():
    assert np.isfinite(logloss(RAW, Y))


def test_precision_at_threshold_and_coverage():
    probs = np.array([0.9, 0.8, 0.4, 0.3])
    y = np.array([1, 1, 0, 0])
    prec, cov = precision_at_threshold(probs, y, 0.5)
    assert prec == 1.0 and cov == 0.5
    assert precision_at_coverage(probs, y, 0.5) == 1.0
