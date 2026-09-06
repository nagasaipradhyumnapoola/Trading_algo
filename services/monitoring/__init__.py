"""monitoring — observability, health/degraded mode, rate limiting, drift.

Deterministic results are preserved in degraded mode; recommendations that depend
on missing data or LLM research are suppressed, never fabricated.
"""

from .audit import AuditBundle, build_audit_bundle
from .drift import DriftReport, detect_drift, population_stability_index
from .feedback import Feedback, FeedbackLabel, FeedbackStore
from .health import HealthInputs, HealthReport, HealthStatus, evaluate_health
from .metrics import MetricsRegistry
from .ratelimit import RateLimiter

__all__ = [
    "MetricsRegistry",
    "AuditBundle",
    "build_audit_bundle",
    "Feedback",
    "FeedbackLabel",
    "FeedbackStore",
    "HealthInputs",
    "HealthReport",
    "HealthStatus",
    "evaluate_health",
    "RateLimiter",
    "population_stability_index",
    "detect_drift",
    "DriftReport",
]
