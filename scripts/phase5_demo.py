"""Phase 5 end-to-end: candidate -> calibrated prob -> risk veto -> sizing ->
recommendation -> portfolio rotation -> paper fills -> dashboard + NAV rebuild.

All numbers deterministic; probability from the calibrated model, risk/sizing from
the deterministic engines. Sample data (illustrative). No broker.

Run:
    python scripts/phase5_demo.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.evaluation import (  # noqa: E402
    CostModel,
    LabelConfig,
    PaperBroker,
    TradeSignal,
    compute_performance,
    label_signal,
    reconstruct_cash,
)
from services.ingestion.models import Timeframe  # noqa: E402
from services.ingestion.sample import SAMPLE_START, build_sample_universe  # noqa: E402
from services.quant import ScanConfig, compute_features, scan  # noqa: E402
from services.quant.calibration import IsotonicCalibrator  # noqa: E402
from services.quant.ml import DEFAULT_FEATURES, LogisticModel  # noqa: E402
from services.risk_portfolio import (  # noqa: E402
    Portfolio,
    RecAction,
    RiskInputs,
    assess_risk,
    build_recommendation,
    recommend_rotation,
    size_position,
)

N = 160
AS_OF = SAMPLE_START + timedelta(days=119)      # a spike session with candidates


def _train(repo, master):
    pairs = []
    for day in range(25, 112):
        as_of = SAMPLE_START + timedelta(days=day)
        if as_of >= AS_OF:
            break
        for inst in master.tradable():
            bars = repo.as_of(inst.instrument_id, Timeframe.EOD, as_of)
            if len(bars) < 22:
                continue
            snap = compute_features(bars, as_of)
            if not all(f in snap.values for f in DEFAULT_FEATURES):
                continue
            lbl = label_signal(inst.instrument_id, as_of, repo, LabelConfig())
            if lbl:
                pairs.append((snap, lbl))
    X = np.array([[p[0].values[f] for f in DEFAULT_FEATURES] for p in pairs])
    y = np.array([p[1].y for p in pairs], int)
    model = LogisticModel().fit(X, y)
    cal = IsotonicCalibrator().fit(model.predict_proba(X), y)
    return model, cal, len(pairs)


def main() -> None:
    repo, master, _ = build_sample_universe(n=N)
    model, cal, n_train = _train(repo, master)

    candidates = scan(repo, master, AS_OF, ScanConfig(top_k=5))
    print(f"as_of {AS_OF}   trained on {n_train} samples   candidates {len(candidates)}\n")

    recs, edges = [], {}
    print(f"{'TICKER':<7}{'PROB':<7}{'RISK':<8}{'QTY':<6}{'ALLOC':<9}{'R:R':<6}{'ENTRY->TGT/STOP'}")
    for c in candidates:
        feat = np.array([[c.features.values.get(f, 0.0) for f in DEFAULT_FEATURES]])
        prob = float(cal.transform(model.predict_proba(feat))[0])
        entry = c.features.values["last_close"]

        risk = assess_risk(RiskInputs(
            instrument_id=c.instrument_id, avg_turnover=c.avg_turnover, spread_bps=20,
            realized_vol=c.features.values.get("realized_vol", 0.02),
            manipulation_score=0.1, event_uncertainty=0.3, signal_age_days=0))
        sizing = size_position(entry, entry * 0.97, avg_turnover=c.avg_turnover)

        if risk.verdict.value == "VETO" or sizing.quantity <= 0:
            print(f"{c.instrument_id:<7}{prob:<7.1%}{risk.verdict.value:<8}"
                  f"{'-':<6}{'-':<9}{'-':<6}vetoed/no-size")
            continue

        rec = build_recommendation(
            action=RecAction.BUY, instrument_id=c.instrument_id, as_of=AS_OF, entry=entry,
            stop_pct=0.03, target_pct=0.06, horizon_sessions=5, quantity=sizing.quantity,
            calibrated_probability=prob, historical_sample_size=n_train,
            risk_verdict=risk.verdict.value, evidence_ids=[f"scan_{c.instrument_id}"],
            model_version="logistic-0.1")
        recs.append(rec)
        edges[c.instrument_id] = rec.expected_net_return
        print(f"{c.instrument_id:<7}{prob:<7.1%}{risk.verdict.value:<8}{rec.quantity:<6}"
              f"{rec.allocation:<9.0f}{rec.risk_reward:<6.1f}{entry:.0f}->{rec.target:.0f}/{rec.invalidation:.0f}")

    # portfolio rotation (empty book, 100k cash)
    pf = Portfolio(cash=100_000)
    moves = recommend_rotation(pf, edges, [(r.instrument_id, r.expected_net_return, True) for r in recs])
    print("\nportfolio moves:", ", ".join(f"{m.action.value} {m.instrument_id}" for m in moves))

    # paper-trade the recommendations
    broker = PaperBroker(100_000, CostModel())
    probs, successes = [], []
    for r in recs:
        closed = broker.execute(TradeSignal(instrument_id=r.instrument_id, signal_date=AS_OF),
                                r.quantity, repo)
        if closed:
            probs.append(r.calibrated_probability)
            successes.append(int(closed.net_return > 0))

    perf = compute_performance([t.net_return for t in broker.trades])
    print(f"\npaper: {perf.n} trades  win {perf.win_rate:.0%}  "
          f"net {perf.total_return:+.2%}  maxDD {perf.max_drawdown:.2%}  "
          f"PF {perf.profit_factor if perf.profit_factor is None else round(perf.profit_factor,2)}")
    print(f"NAV reported {broker.cash:,.2f}  reconstructed "
          f"{reconstruct_cash(broker.fills, broker.starting_cash):,.2f}  "
          f"(match: {abs(broker.cash - reconstruct_cash(broker.fills, broker.starting_cash)) < 1e-6})")
    print("\nManual execution only. Probability from calibrated quant; risk/sizing deterministic.")


if __name__ == "__main__":
    main()
