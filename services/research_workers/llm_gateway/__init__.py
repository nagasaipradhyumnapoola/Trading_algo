"""LLM Gateway — mandatory single path to any LLM provider.

See docs/LLM_GATEWAY.md. Agents import from here; they never import a provider SDK.
"""

from .contracts import (
    DataClass,
    GatewayResult,
    GatewayState,
    LLMRunRecord,
    LLMTask,
    ModelRoute,
    TaskPolicy,
)
from .gateway import LLMGateway
from .policies import DEFAULT_POLICIES, get_policy
from .registry import ModelCapabilityRegistry, build_default_registry

__all__ = [
    "LLMGateway",
    "LLMTask",
    "TaskPolicy",
    "ModelRoute",
    "LLMRunRecord",
    "GatewayResult",
    "GatewayState",
    "DataClass",
    "DEFAULT_POLICIES",
    "get_policy",
    "ModelCapabilityRegistry",
    "build_default_registry",
]
