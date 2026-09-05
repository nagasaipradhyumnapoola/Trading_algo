"""Paper-trading simulator — realistic fills, immutable ledger, no broker.

Executes signals against historical bars (entry at next session open, exit at the
stop/target/horizon from the leakage-safe simulator), applies slippage + fees per
leg, and records every fill append-only. The account NAV can be reconstructed from
the ledger alone and must match the reported NAV (Phase 5 acceptance).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .backtest import Outcome, simulate
from .costs import CostModel
from .strategy import TradeSignal


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PaperFill(BaseModel):
    model_config = ConfigDict(frozen=True)

    fill_id: str = Field(default_factory=lambda: f"fill_{uuid.uuid4().hex[:12]}")
    instrument_id: str
    side: Side
    quantity: int
    price: float
    cost: float
    session_date: date
    kind: str                      # "ENTRY" | "EXIT"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClosedTrade(BaseModel):
    instrument_id: str
    quantity: int
    entry_price: float
    exit_price: float
    realized_pnl: float
    net_return: float
    outcome: Outcome
    entry_date: date
    exit_date: date


class PaperBroker:
    def __init__(self, starting_cash: float, cost_model: CostModel | None = None,
                 ledger_path: str | Path | None = None) -> None:
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.realized_pnl = 0.0
        self.fills: list[PaperFill] = []
        self.trades: list[ClosedTrade] = []
        self._cost = cost_model or CostModel()
        self._path = Path(ledger_path) if ledger_path else None

    def _fee_frac(self) -> float:
        return (self._cost.brokerage_bps + self._cost.statutory_bps) / 1e4

    def _record(self, fill: PaperFill) -> None:
        self.fills.append(fill)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(fill.model_dump_json() + "\n")

    def execute(self, signal: TradeSignal, quantity: int, repo) -> ClosedTrade | None:
        trade = simulate(signal, repo, self._cost)
        if trade is None or quantity <= 0:
            return None

        slip = self._cost.slippage_bps / 1e4
        fee = self._fee_frac()
        entry_fill = trade.entry_price * (1 + slip)      # pay up on entry
        exit_fill = trade.exit_price * (1 - slip)        # give up on exit
        fee_entry = quantity * entry_fill * fee
        fee_exit = quantity * exit_fill * fee

        self._record(PaperFill(instrument_id=signal.instrument_id, side=Side.BUY,
                               quantity=quantity, price=entry_fill, cost=fee_entry,
                               session_date=trade.entry_date, kind="ENTRY"))
        self._record(PaperFill(instrument_id=signal.instrument_id, side=Side.SELL,
                               quantity=quantity, price=exit_fill, cost=fee_exit,
                               session_date=trade.exit_date, kind="EXIT"))

        buy_cash = -(quantity * entry_fill + fee_entry)
        sell_cash = quantity * exit_fill - fee_exit
        realized = buy_cash + sell_cash
        self.cash += realized
        self.realized_pnl += realized

        closed = ClosedTrade(
            instrument_id=signal.instrument_id, quantity=quantity,
            entry_price=entry_fill, exit_price=exit_fill, realized_pnl=realized,
            net_return=realized / (quantity * trade.entry_price),
            outcome=trade.outcome, entry_date=trade.entry_date, exit_date=trade.exit_date,
        )
        self.trades.append(closed)
        return closed

    @property
    def nav(self) -> float:
        return self.cash              # fully-closed trades: no open positions


def reconstruct_cash(fills: list[PaperFill], starting_cash: float) -> float:
    """Replay the ledger to recover cash — must equal the broker's reported cash."""
    cash = starting_cash
    for f in fills:
        if f.side is Side.BUY:
            cash -= f.quantity * f.price + f.cost
        else:
            cash += f.quantity * f.price - f.cost
    return cash
