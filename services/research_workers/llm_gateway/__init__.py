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
from .factory import build_real_gateway, build_real_registry
from .freellm import FreeLLMProvider, health_check
from .gateway import CircuitBreaker, LLMGateway
from .policies import DEFAULT_POLICIES, get_policy
from .providers import (
    AsyncMockProvider,
    LLMProvider,
    MockProvider,
    ProviderError,
    ProviderTimeout,
)
from .registry import ModelCapabilityRegistry, build_default_registry
from .sanitize import build_user_prompt, sanitize_source
from .schemas import (
    Claim,
    EventCandidate,
    EventType,
    ExtractionResult,
    ThesisResult,
    response_model_for,
)
from .templates import TEMPLATE_VERSION, system_for

__all__ = [
    "LLMGateway",
    "CircuitBreaker",
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
    "LLMProvider",
    "MockProvider",
    "AsyncMockProvider",
    "ProviderError",
    "ProviderTimeout",
    "FreeLLMProvider",
    "health_check",
    "build_real_gateway",
    "build_real_registry",
    "sanitize_source",
    "build_user_prompt",
    "system_for",
    "TEMPLATE_VERSION",
    "EventType",
    "Claim",
    "EventCandidate",
    "ExtractionResult",
    "ThesisResult",
    "response_model_for",
]
