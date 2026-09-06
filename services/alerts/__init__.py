"""alerts — deduplicated, audited alert delivery.

Emits alerts for new approved opportunities, thesis invalidation, target hits, risk
vetoes, and stale data. Duplicates are suppressed by key; non-critical alerts are
held during quiet hours; every decision is written to an append-only audit log.
"""

from .engine import (
    Alert,
    AlertEngine,
    AlertEvent,
    AlertType,
    Severity,
    make_new_opportunity,
    make_risk_veto,
    make_target_hit,
    make_thesis_invalidated,
)

__all__ = [
    "Alert",
    "AlertEngine",
    "AlertEvent",
    "AlertType",
    "Severity",
    "make_new_opportunity",
    "make_thesis_invalidated",
    "make_target_hit",
    "make_risk_veto",
]
