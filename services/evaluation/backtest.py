"""Leakage-controlled backtester (Phase 1).

Entry is the NEXT session's open after the signal date — the strategy never sees
the bar it acts on. Each held session is checked against the fixed stop/target;
unresolved by the horizon, the trade exits at the last session's close. All
reported returns are NET of the cost model.

Same-bar ambiguity (both stop and target touched) resolves stop-first by default
(conservative). Gap handling fills at the stop/target level — a Phase 2 refinement
will model gap-through fills more strictly.
"""

from __future__ import annotations

import statistics
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from services.ingestion.models import Timeframe
from services.ingestion.repository import BarRepository

from .costs import CostModel
from .strategy import TradeSignal


class Outcome(str, Enum):
    TARGET = "TARGET"
    STOP = "STOP"
    HORIZON = "HORIZON"
    NO_ENTRY = "NO_ENTRY"


class Trade(BaseModel):
    instrument_id: str
    signal_date: date
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    outcome: Outcome
    gross_return: float
    net_return: float
    holding_sessions: int
    model_version: str


def simulate(
    signal: TradeSignal,
    repo: BarRepository,
    cost_model: CostModel,
    *,
    target_first: bool = False,
) -> Trade | None:
    """Simulate one signal. Returns None if there is no session to enter on."""
    series = repo.as_of(signal.instrument_id, Timeframe.EOD, date.max)
    after = [b for b in series if b.session_date > signal.signal_date]
    if not after:
        return None

    entry_bar = after[0]
    entry = float(entry_bar.open)
    stop_price = entry * (1 - signal.stop_pct)
    target_price = entry * (1 + signal.target_pct)

    window = after[: signal.horizon_sessions]
    exit_price = float(window[-1].close)
    exit_date = window[-1].session_date
    outcome = Outcome.HORIZON

    for held, bar in enumerate(window, start=1):
        hit_stop = float(bar.low) <= stop_price
        hit_target = float(bar.high) >= target_price
        order = [("target", hit_target), ("stop", hit_stop)] if target_first \
            else [("stop", hit_stop), ("target", hit_target)]
        resolved = next((name for name, hit in order if hit), None)
        if resolved == "stop":
            exit_price, exit_date, outcome = stop_price, bar.session_date, Outcome.STOP
            window = window[:held]
            break
        if resolved == "target":
            exit_price, exit_date, outcome = target_price, bar.session_date, Outcome.TARGET
            window = window[:held]
            break

    return Trade(
        instrument_id=signal.instrument_id, signal_date=signal.signal_date,
        entry_date=entry_bar.session_date, entry_price=entry,
        exit_date=exit_date, exit_price=exit_price, outcome=outcome,
        gross_return=CostModel.gross_return(entry, exit_price),
        net_return=cost_model.net_return(entry, exit_price),
        holding_sessions=len(window), model_version=signal.model_version,
    )


class BacktestReport(BaseModel):
    n_trades: int = 0
    n_wins: int = 0
    win_rate: float = 0.0
    avg_net_return: float = 0.0
    median_net_return: float = 0.0
    avg_gross_return: float = 0.0
    profit_factor: float | None = None
    max_drawdown: float = 0.0
    avg_holding_sessions: float = 0.0
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    cost_model: CostModel = Field(default_factory=CostModel)


def _max_drawdown(net_returns_in_time_order: list[float]) -> float:
    equity, peak, mdd = 1.0, 1.0, 0.0
    for r in net_returns_in_time_order:
        equity *= (1 + r)
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)
    return mdd


def report_for(trades: list[Trade], cost_model: CostModel | None = None) -> BacktestReport:
    if not trades:
        return BacktestReport(cost_model=cost_model or CostModel())

    nets = [t.net_return for t in trades]
    ordered = [t.net_return for t in sorted(trades, key=lambda t: t.exit_date)]
    wins = [r for r in nets if r > 0]
    gross_profit = sum(r for r in nets if r > 0)
    gross_loss = abs(sum(r for r in nets if r < 0))

    counts: dict[str, int] = {}
    for t in trades:
        counts[t.outcome.value] = counts.get(t.outcome.value, 0) + 1

    return BacktestReport(
        n_trades=len(trades),
        n_wins=len(wins),
        win_rate=len(wins) / len(trades),
        avg_net_return=statistics.fmean(nets),
        median_net_return=statistics.median(nets),
        avg_gross_return=statistics.fmean(t.gross_return for t in trades),
        profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else None,
        max_drawdown=_max_drawdown(ordered),
        avg_holding_sessions=statistics.fmean(t.holding_sessions for t in trades),
        outcome_counts=counts,
        cost_model=cost_model or CostModel(),
    )


def run_backtest(
    signals: list[TradeSignal],
    repo: BarRepository,
    cost_model: CostModel | None = None,
    *,
    target_first: bool = False,
) -> tuple[list[Trade], BacktestReport]:
    cm = cost_model or CostModel()
    trades = [t for s in signals if (t := simulate(s, repo, cm, target_first=target_first))]
    return trades, report_for(trades, cm)


def chronological_split(
    signals: list[TradeSignal], *, train: float = 0.6, val: float = 0.2
) -> dict[str, list[TradeSignal]]:
    """Split signals by time into train / validation / untouched test. Never shuffle."""
    ordered = sorted(signals, key=lambda s: s.signal_date)
    n = len(ordered)
    i, j = int(n * train), int(n * (train + val))
    return {"train": ordered[:i], "validation": ordered[i:j], "test": ordered[j:]}
