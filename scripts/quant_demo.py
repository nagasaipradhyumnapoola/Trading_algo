"""Phase 4 demo: point-in-time dataset -> purged walk-forward -> calibrated model.

Builds features (point-in-time) and fixed labels (forward), runs purged/embargoed
walk-forward CV, trains the logistic model with per-fold isotonic calibration, and
compares OUT-OF-SAMPLE against the base-rate and momentum benchmarks. Reports the
real numbers (synthetic data — illustrative, not edge) and registers the model,
approving it only if it beats the baseline.

Run:
    python scripts/quant_demo.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.evaluation import LabelConfig, label_signal, purged_walk_forward   # noqa: E402
from services.ingestion.models import Timeframe                                   # noqa: E402
from services.ingestion.sample import SAMPLE_START, build_sample_universe         # noqa: E402
from services.quant import (                                                     # noqa: E402
    Approval, ModelCard, ModelRegistry, beats_baseline, compute_features,
)
from services.quant.calibration import (                                         # noqa: E402
    IsotonicCalibrator, brier, precision_at_coverage, reliability_curve,
)
from services.quant.ml import (                                                  # noqa: E402
    DEFAULT_FEATURES, BaseRateModel, LogisticModel, MomentumRuleModel,
)

N = 160


def build_dataset():
    repo, master, _ = build_sample_universe(n=N)
    pairs, dates = [], []
    for day in range(25, N - 8):
        as_of = SAMPLE_START + timedelta(days=day)
        for inst in master.tradable():
            bars = repo.as_of(inst.instrument_id, Timeframe.EOD, as_of)
            if len(bars) < 22:
                continue
            snap = compute_features(bars, as_of)
            if not all(f in snap.values for f in DEFAULT_FEATURES):
                continue
            lbl = label_signal(inst.instrument_id, as_of, repo, LabelConfig())
            if lbl is None:
                continue
            pairs.append((snap, lbl))
            dates.append(as_of)
    X = np.array([[p[0].values[f] for f in DEFAULT_FEATURES] for p in pairs])
    y = np.array([p[1].y for p in pairs], int)
    return X, y, dates


def main() -> None:
    X, y, dates = build_dataset()
    folds = purged_walk_forward(dates, n_splits=5, horizon=5, embargo=2)

    log_p, mom_p, yt = [], [], []
    for train_idx, test_idx in folds:
        if len(train_idx) < 10:
            continue
        Xtr, ytr, Xte, yte = X[train_idx], y[train_idx], X[test_idx], y[test_idx]
        lm = LogisticModel().fit(Xtr, ytr)
        cal = IsotonicCalibrator().fit(lm.predict_proba(Xtr), ytr)     # calibrate on TRAIN only
        log_p += cal.transform(lm.predict_proba(Xte)).tolist()
        mom_p += MomentumRuleModel().fit(Xtr, ytr).predict_proba(Xte).tolist()
        yt += yte.tolist()

    yt = np.array(yt, int)
    base_rate = float(yt.mean())
    cov = 0.3
    metrics = {
        "n_oos": float(len(yt)),
        "base_rate": base_rate,
        "brier_logistic": brier(log_p, yt),
        "brier_baserate": brier(np.full(len(yt), base_rate), yt),
        "precision@30_logistic": precision_at_coverage(log_p, yt, cov),
        "precision@30_momentum": precision_at_coverage(mom_p, yt, cov),
    }

    print("== OUT-OF-SAMPLE (purged walk-forward, net-of-cost labels) ==")
    print(f"samples:              {len(y)}  (oos {len(yt)})   base rate {base_rate:.1%}")
    print(f"Brier  logistic:      {metrics['brier_logistic']:.4f}   base-rate {metrics['brier_baserate']:.4f}")
    print(f"Precision@30%  logistic:  {metrics['precision@30_logistic']:.1%}   "
          f"momentum {metrics['precision@30_momentum']:.1%}   base {base_rate:.1%}")

    print("\nreliability (logistic, calibrated):")
    for b in reliability_curve(log_p, yt, bins=5):
        print(f"  pred~{b.mean_pred:.2f}  actual {b.frac_pos:.2f}  n={b.count}")

    approved = beats_baseline(metrics, {"precision@30_logistic": base_rate},
                              key="precision@30_logistic", margin=0.02)
    reg = ModelRegistry()
    card = reg.register(ModelCard(name="logistic", feature_set_version="fs-0.1",
                                  label_version="lbl-0.1", data_snapshot="sample-seed-7",
                                  config={"features": DEFAULT_FEATURES}, metrics=metrics))
    reg.set_approval(card.model_id, Approval.APPROVED if approved else Approval.REJECTED)
    print(f"\nmodel {card.model_id}: {reg.get(card.model_id).approval.value.upper()} "
          f"(beats baseline: {approved})")
    print("Synthetic data - honest reporting: if it does not beat baseline, it is rejected.")


if __name__ == "__main__":
    main()
