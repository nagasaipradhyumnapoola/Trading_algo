"""Paper broker fills, NAV reconstruction, and performance metrics."""

from datetime import date

from services.evaluation import (
    CostModel,
    PaperBroker,
    Side,
    TradeSignal,
    compute_performance,
    precision_by_bucket,
    reconstruct_cash,
)
from services.ingestion import Bar, InMemoryBarRepository


def _repo():
    repo = InMemoryBarRepository()
    _add = lambda iid, d, o, h, low, c: repo.upsert(
        Bar(instrument_id=iid, session_date=d, open=o, high=h, low=low, close=c,
            volume=1000, source="syn"))
    _add("TGT", date(2026, 1, 1), 100, 101, 99, 100)
    _add("TGT", date(2026, 1, 2), 100, 108, 99, 107)     # hits +6% target
    _add("STP", date(2026, 1, 1), 100, 101, 99, 100)
    _add("STP", date(2026, 1, 2), 100, 101, 96, 98)      # hits -3% stop
    return repo


def _sig(iid):
    return TradeSignal(instrument_id=iid, signal_date=date(2026, 1, 1))


def test_execute_records_entry_and_exit_fills():
    broker = PaperBroker(100_000, CostModel())
    trade = broker.execute(_sig("TGT"), 10, _repo())
    assert trade is not None and trade.outcome.value == "TARGET"
    kinds = [f.kind for f in broker.fills]
    assert kinds == ["ENTRY", "EXIT"]
    assert broker.fills[0].side is Side.BUY and broker.fills[1].side is Side.SELL


def test_nav_reconstructs_from_ledger():
    broker = PaperBroker(100_000, CostModel())
    broker.execute(_sig("TGT"), 10, _repo())
    broker.execute(_sig("STP"), 10, _repo())
    reconstructed = reconstruct_cash(broker.fills, broker.starting_cash)
    assert abs(reconstructed - broker.cash) < 1e-6        # ledger reproduces reported NAV


def test_winning_trade_increases_cash():
    broker = PaperBroker(100_000, CostModel())
    broker.execute(_sig("TGT"), 10, _repo())
    assert broker.cash > 100_000                          # net of costs, target hit


def test_performance_report():
    rep = compute_performance([0.05, -0.03, 0.04, -0.01])
    assert rep.n == 4 and rep.win_rate == 0.5
    assert rep.profit_factor is not None
    assert rep.max_drawdown <= 0.0


def test_precision_by_bucket():
    probs = [0.55, 0.65, 0.92, 0.95]
    y = [0, 1, 1, 1]
    buckets = precision_by_bucket(probs, y)
    top = [b for b in buckets if b.lo >= 0.9]
    assert top and all(b.precision == 1.0 for b in top)
