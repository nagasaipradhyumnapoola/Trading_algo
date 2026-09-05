"""Phase 1 end-to-end demo: scan -> baseline signal -> backtest -> paper ledger.

Reproducible (seeded synthetic universe). Shows ranked candidates, the NO_TRADE
path, and an HONEST net-of-cost backtest report. No LLM, no broker.

Run:
    python scripts/pipeline_demo.py
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.evaluation import (            # noqa: E402
    Action,
    BaselineStrategy,
    CostModel,
    PaperLedger,
    PaperSignal,
    run_backtest,
)
from services.ingestion import (             # noqa: E402
    Bar,
    InMemoryBarRepository,
    Instrument,
    InstrumentMaster,
)
from services.quant import ScanConfig, scan  # noqa: E402

START = date(2026, 1, 1)
N = 60
RNG = random.Random(7)


def _write_path(repo, iid, drift, base_price, base_vol):
    price = base_price
    closes = []
    for _ in range(N):
        price *= 1 + drift + RNG.uniform(-0.02, 0.02)
        closes.append(price)
    for i, c in enumerate(closes):
        prev = closes[i - 1] if i > 0 else c
        o, cl = prev, c
        hi = max(o, cl) * (1 + RNG.uniform(0.0, 0.01))
        lo = min(o, cl) * (1 - RNG.uniform(0.0, 0.01))
        vol = base_vol * (2 if i % 5 == 0 else 1)            # periodic volume spike
        repo.upsert(Bar(instrument_id=iid, session_date=START + timedelta(days=i),
                        open=round(o, 2), high=round(hi, 2), low=round(lo, 2),
                        close=round(cl, 2), volume=vol, source="synthetic"))


def build_universe():
    repo = InMemoryBarRepository()
    _write_path(repo, "MOMO", 0.006, 100, 40000)     # uptrend, liquid
    _write_path(repo, "CHOP", 0.000, 200, 40000)     # sideways
    _write_path(repo, "WEAK", -0.006, 150, 40000)    # downtrend -> filtered
    _write_path(repo, "ILLQ", 0.006, 90, 30)         # uptrend but illiquid -> filtered
    master = InstrumentMaster([
        Instrument(instrument_id=x, symbol=x, name=x) for x in ("MOMO", "CHOP", "WEAK", "ILLQ")
    ])
    return repo, master


def main() -> None:
    repo, master = build_universe()
    strat = BaselineStrategy()
    ledger = PaperLedger()
    signals, no_trade_days = [], 0

    # Walk the scanner across a window; each day either yields a top candidate or NO_TRADE.
    for day in range(25, 46):
        as_of = START + timedelta(days=day)
        top = scan(repo, master, as_of, ScanConfig(top_k=1))
        if not top:
            no_trade_days += 1
            ledger.append(PaperSignal(instrument_id="-", as_of=as_of, action=Action.NO_TRADE,
                                      model_version="baseline-0.1",
                                      data_version="synthetic-seed-7"))
            continue
        c = top[0]
        signals.append(strat.signal_for(c.instrument_id, as_of))
        ledger.append(PaperSignal(
            instrument_id=c.instrument_id, as_of=as_of, action=Action.BUY,
            stop_pct=strat.stop_pct, target_pct=strat.target_pct,
            horizon_sessions=strat.horizon_sessions, score=c.score, reason=c.reason,
            model_version="baseline-0.1", data_version="synthetic-seed-7",
        ))

    trades, rep = run_backtest(signals, repo, CostModel())

    print("== SCAN / SIGNALS ==")
    print(f"scanned days: 21   BUY signals: {len(signals)}   NO_TRADE days: {no_trade_days}")
    print(f"ledger records (append-only): {len(ledger)}")
    if signals:
        picks = {}
        for s in signals:
            picks[s.instrument_id] = picks.get(s.instrument_id, 0) + 1
        print(f"picks by instrument: {picks}")

    print("\n== BACKTEST (net of costs) ==")
    print(f"trades:            {rep.n_trades}")
    print(f"win rate:          {rep.win_rate:.0%}")
    print(f"avg net return:    {rep.avg_net_return:+.2%}")
    print(f"median net return: {rep.median_net_return:+.2%}")
    pf = f"{rep.profit_factor:.2f}" if rep.profit_factor is not None else "n/a"
    print(f"profit factor:     {pf}")
    print(f"max drawdown:      {rep.max_drawdown:.2%}")
    print(f"avg holding:       {rep.avg_holding_sessions:.1f} sessions")
    print(f"outcomes:          {rep.outcome_counts}")
    print("\nNote: synthetic data - illustrates the pipeline and honest reporting, not edge.")


if __name__ == "__main__":
    main()
