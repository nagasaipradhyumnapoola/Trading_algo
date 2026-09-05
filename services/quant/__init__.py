"""quant — deterministic numerical authority.

Market scanner, point-in-time features, event studies, ML models, calibration,
expected value, and ranking. Every number in the system originates here, never
from an LLM.
"""

from .event_study import AggregateStudy, EventStudy, EventStudyResult
from .features import FEATURE_SET_VERSION, FeatureSnapshot, Quality, compute_features
from .model_registry import Approval, ModelCard, ModelRegistry, beats_baseline
from .scanner import ScanCandidate, ScanConfig, scan

__all__ = [
    "compute_features",
    "FeatureSnapshot",
    "Quality",
    "FEATURE_SET_VERSION",
    "scan",
    "ScanConfig",
    "ScanCandidate",
    "EventStudy",
    "EventStudyResult",
    "AggregateStudy",
    "Approval",
    "ModelCard",
    "ModelRegistry",
    "beats_baseline",
]
