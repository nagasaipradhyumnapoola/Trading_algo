"""Baseline strategy — turns a candidate into an explicit, testable trade signal.

Fixed rule, no look-ahead: enter at the NEXT session's open after the signal date,
with a fixed stop, target, and maximum holding horizon. Success is defined here,
before any backtest, and never redefined afterward (CLAUDE.md §3).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

BASELINE_VERSION = "baseline-0.1"


class TradeSignal(BaseModel):
    instrument_id: str
    signal_date: date               # the as_of date the signal was formed
    entry_rule: str = "next_open"   # enter at next available session open
    stop_pct: float = 0.03          # invalidation distance below entry
    target_pct: float = 0.06        # target distance above entry (2:1 vs stop)
    horizon_sessions: int = 5
    model_version: str = BASELINE_VERSION


class BaselineStrategy(BaseModel):
    stop_pct: float = 0.03
    target_pct: float = 0.06
    horizon_sessions: int = 5

    def signal_for(self, instrument_id: str, as_of: date) -> TradeSignal:
        return TradeSignal(
            instrument_id=instrument_id, signal_date=as_of,
            stop_pct=self.stop_pct, target_pct=self.target_pct,
            horizon_sessions=self.horizon_sessions,
        )
