"""LLMGateway — the ONE path from application code to any LLM.

Mandatory. No agent, route, worker, or frontend calls a provider directly.
Full implementation lands in Phase 3 (docs/LLM_GATEWAY.md §13); this fixes the
public surface so agents are written against it from day one.
"""

from __future__ import annotations

from typing import Any

from .contracts import GatewayResult, GatewayState, LLMTask
from .policies import get_policy
from .registry import ModelCapabilityRegistry, build_default_registry


class LLMGateway:
    """Routes reasoning tasks to FreeLLMAPI with validation, audit, and fallback.

    Numbers (probabilities, expected return, risk, sizing, P&L) are NEVER produced
    here — those are deterministic quant-engine outputs.
    """

    def __init__(self, registry: ModelCapabilityRegistry | None = None) -> None:
        self.registry = registry or build_default_registry()

    async def request(
        self,
        *,
        agent: str,
        task: LLMTask,
        payload: dict[str, Any],
        source_ids: list[str] | None = None,
    ) -> GatewayResult:
        """Execute one validated LLM call.

        Flow (Phase 3): resolve policy -> select healthy route from registry ->
        enforce limits -> sanitize untrusted content -> call provider -> validate
        JSON schema -> validate citations -> retry/fallback -> write immutable
        llm_run -> return VALIDATED result or explicit FAILED (degraded) state.
        """
        policy = get_policy(task)  # noqa: F841  (used once routing is implemented)
        raise NotImplementedError(
            "Phase 3: implement route selection, provider call, validation, "
            "audit, and degraded mode. Until then no LLM calls are permitted."
        )

    def _degraded(self, task: LLMTask, reason: str) -> GatewayResult:
        """Explicit failure state: preserve deterministic results, fabricate nothing."""
        return GatewayResult(state=GatewayState.FAILED, task=task, error=reason)
