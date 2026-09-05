"""Fixed, versioned outcome labels for supervised learning.

The label rule is frozen BEFORE training and never redefined after seeing results
(CLAUDE.md §3). A label is 1 when the realized NET return over the trade (entry at
next open, fixed stop/target/horizon, target-first/stop-first) meets the threshold.
The realized return and outcome are stored alongside for auditing.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .backtest import Outcome, simulate
from .costs import CostModel
from .strategy import TradeSignal

LABEL_VERSION = "lbl-0.1"


class LabelConfig(BaseModel):
    version: str = LABEL_VERSION
    stop_pct: float = 0.03
    target_pct: float = 0.06
    horizon_sessions: int = 5
    net_threshold: float = 0.0        # label=1 when realized net return >= this
    target_first: bool = False


class Label(BaseModel):
    instrument_id: str
    signal_date: date
    y: int
    realized_net: float
    outcome: Outcome
    label_version: str


def label_signal(instrument_id: str, signal_date: date, repo, cfg: LabelConfig,
                 cost_model: CostModel | None = None) -> Label | None:
    sig = TradeSignal(instrument_id=instrument_id, signal_date=signal_date,
                      stop_pct=cfg.stop_pct, target_pct=cfg.target_pct,
                      horizon_sessions=cfg.horizon_sessions)
    trade = simulate(sig, repo, cost_model or CostModel(), target_first=cfg.target_first)
    if trade is None:
        return None
    return Label(
        instrument_id=instrument_id, signal_date=signal_date,
        y=int(trade.net_return >= cfg.net_threshold), realized_net=trade.net_return,
        outcome=trade.outcome, label_version=cfg.version,
    )


def label_dataset(signals: list[tuple[str, date]], repo, cfg: LabelConfig | None = None,
                  cost_model: CostModel | None = None) -> list[Label]:
    cfg = cfg or LabelConfig()
    out = []
    for iid, d in signals:
        lbl = label_signal(iid, d, repo, cfg, cost_model)
        if lbl is not None:
            out.append(lbl)
    return out
