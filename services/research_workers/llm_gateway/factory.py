"""Build a real, FreeLLMAPI-backed LLMGateway from Settings.

Maps the logical routing tiers used by the task policies to FreeLLMAPI model ids
(configurable via env; defaults to the server's own `auto:*` routers). The gateway
stays the only path to the provider.
"""

from __future__ import annotations

import httpx

from .contracts import DataClass, ModelRoute
from .freellm import FreeLLMProvider
from .gateway import LLMGateway
from .policies import FAST, MID, REASONING
from .registry import ModelCapabilityRegistry


def _model_map(settings) -> dict[str, str]:
    return {
        FAST: settings.freellm_model_fast or "auto:fast",
        MID: settings.freellm_model_reasoning or "auto",
        REASONING: settings.freellm_model_reasoning or "auto:smart",
    }


def build_real_registry() -> ModelCapabilityRegistry:
    reg = ModelCapabilityRegistry()
    for name in (FAST, MID, REASONING):
        # the local FreeLLMAPI server handles user data; permit up to USER class.
        reg.register(ModelRoute(name=name, provider="freellmapi", healthy=True,
                                permitted_data_classification=DataClass.USER))
    return reg


def build_real_gateway(settings, *, client: httpx.AsyncClient | None = None,
                       audit_path=None) -> LLMGateway:
    """Requires settings.freellm_api_base + freellm_api_key (enforced in real mode)."""
    provider = FreeLLMProvider(settings.freellm_api_base, settings.freellm_api_key,
                               _model_map(settings), client=client)
    return LLMGateway(provider, build_real_registry(), audit_path=audit_path)
