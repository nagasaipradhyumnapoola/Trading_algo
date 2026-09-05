"""Backtester, cost model, report, split, and paper-ledger tests."""

from datetime import date, timedelta

from services.ingestion import Bar, InMemoryBarRepository
from services.evaluation import (
    Action,
    BaselineStrategy,
    CostModel,
    Outcome,
    PaperLedger,
    PaperSignal,
    TradeSignal,
    chronological_split,
    report_for,
    run_backtest,
    simulate,
)


def _bar(repo, iid, d, o, h, low, c, v=100000):
    repo.upsert(Bar(instrument_id=iid, session_date=d, open=o, high=h, low=low,
                    close=c, volume=v, source="synthetic"))


def _repo_target():
    repo = InMemoryBarRepository()
    _bar(repo, "TGT", date(2026, 1, 1), 100, 101, 99, 100)     # signal day (not entered)
    _bar(repo, "TGT", date(2026, 1, 2), 100, 108, 99, 107)     # next open=100, target 106 hit
    return repo


def _signal(iid, d, stop=0.03, target=0.06, horizon=5):
    return TradeSignal(instrument_id=iid, signal_date=d, stop_pct=stop,
                       target_pct=target, horizon_sessions=horizon)


# --- fills / outcomes ---------------------------------------------------------

def test_entry_is_next_session_open_no_lookahead():
    repo = _repo_target()
    trade = simulate(_signal("TGT", date(2026, 1, 1)), repo, CostModel())
    assert trade.entry_date == date(2026, 1, 2)     # not the signal day
    assert trade.entry_price == 100.0


def test_target_outcome():
    repo = _repo_target()
    trade = simulate(_signal("TGT", date(2026, 1, 1)), repo, CostModel())
    assert trade.outcome is Outcome.TARGET
    assert trade.exit_price == 106.0                # entry*(1+0.06)
    assert trade.gross_return > trade.net_return    # costs drag


def test_stop_outcome():
    repo = InMemoryBarRepository()
    _bar(repo, "STP", date(2026, 1, 1), 100, 101, 99, 100)
    _bar(repo, "STP", date(2026, 1, 2), 100, 101, 96, 98)      # low 96 <= stop 97
    trade = simulate(_signal("STP", date(2026, 1, 1)), repo, CostModel())
    assert trade.outcome is Outcome.STOP
    assert trade.exit_price == 97.0
    assert trade.net_return < 0


def test_horizon_outcome():
    repo = InMemoryBarRepository()
    _bar(repo, "HZN", date(2026, 1, 1), 100, 101, 99, 100)
    _bar(repo, "HZN", date(2026, 1, 2), 100, 102, 99, 101)
    _bar(repo, "HZN", date(2026, 1, 3), 101, 103, 100, 102)
    trade = simulate(_signal("HZN", date(2026, 1, 1), horizon=2), repo, CostModel())
    assert trade.outcome is Outcome.HORIZON
    assert trade.exit_date == date(2026, 1, 3)
    assert trade.holding_sessions == 2


def test_no_entry_when_no_future_session():
    repo = _repo_target()
    assert simulate(_signal("TGT", date(2026, 1, 2)), repo, CostModel()) is None


# --- report -------------------------------------------------------------------

def test_report_metrics_win_and_loss():
    repo = _repo_target()
    _bar(repo, "STP", date(2026, 1, 1), 100, 101, 99, 100)
    _bar(repo, "STP", date(2026, 1, 2), 100, 101, 96, 98)
    signals = [_signal("TGT", date(2026, 1, 1)), _signal("STP", date(2026, 1, 1))]
    trades, rep = run_backtest(signals, repo, CostModel())
    assert rep.n_trades == 2
    assert rep.win_rate == 0.5
    assert rep.profit_factor is not None
    assert rep.max_drawdown <= 0.0
    assert rep.outcome_counts == {"TARGET": 1, "STOP": 1}


def test_empty_report():
    assert report_for([]).n_trades == 0


# --- split --------------------------------------------------------------------

def test_chronological_split_preserves_time_order():
    base = date(2026, 1, 1)
    signals = [_signal(f"S{i}", base + timedelta(days=i)) for i in range(10)]
    parts = chronological_split(signals, train=0.6, val=0.2)
    assert (len(parts["train"]), len(parts["validation"]), len(parts["test"])) == (6, 2, 2)
    assert parts["train"][-1].signal_date < parts["test"][0].signal_date


# --- paper ledger -------------------------------------------------------------

def test_paper_ledger_append_only_and_persists(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = PaperLedger(path)
    rec = PaperSignal(instrument_id="TGT", as_of=date(2026, 1, 1), action=Action.BUY,
                      model_version="baseline-0.1", data_version="csv-fixtures")
    ledger.append(rec)
    ledger.append(PaperSignal(instrument_id="STP", as_of=date(2026, 1, 1),
                              action=Action.NO_TRADE, model_version="baseline-0.1",
                              data_version="csv-fixtures"))
    assert len(ledger) == 2
    ledger.all().clear()                     # mutating the copy must not touch the ledger
    assert len(ledger) == 2

    reloaded = PaperLedger.load(path)         # durable audit trail round-trips
    assert len(reloaded) == 2
    assert reloaded.all()[0].instrument_id == "TGT"


def test_baseline_strategy_builds_signal():
    sig = BaselineStrategy().signal_for("TGT", date(2026, 1, 1))
    assert sig.entry_rule == "next_open" and sig.horizon_sessions == 5
