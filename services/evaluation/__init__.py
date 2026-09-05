"""evaluation — backtests, walk-forward validation, paper ledger, calibration.

Leakage-controlled, point-in-time, immutable reporting. Keeps training /
validation / untouched test / paper / live-journal as separate labeled datasets.
Phase 1 seeds the leakage-safe backtester + paper ledger.
"""

from .backtest import (
    BacktestReport,
    Outcome,
    Trade,
    chronological_split,
    report_for,
    run_backtest,
    simulate,
)
from .costs import CostModel
from .cv import purged_walk_forward
from .labels import LABEL_VERSION, Label, LabelConfig, label_dataset, label_signal
from .paper_ledger import Action, PaperLedger, PaperSignal
from .registry import (
    ExperimentRecord,
    ExperimentRegistry,
    is_reproducible,
    metrics_match,
)
from .strategy import BASELINE_VERSION, BaselineStrategy, TradeSignal

__all__ = [
    "CostModel",
    "BaselineStrategy",
    "TradeSignal",
    "BASELINE_VERSION",
    "simulate",
    "run_backtest",
    "report_for",
    "chronological_split",
    "Trade",
    "Outcome",
    "BacktestReport",
    "PaperLedger",
    "PaperSignal",
    "Action",
    "ExperimentRecord",
    "ExperimentRegistry",
    "is_reproducible",
    "metrics_match",
    "Label",
    "LabelConfig",
    "LABEL_VERSION",
    "label_signal",
    "label_dataset",
    "purged_walk_forward",
]
