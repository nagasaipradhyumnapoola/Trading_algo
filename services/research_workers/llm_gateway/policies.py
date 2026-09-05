"""Versioned task policies (configuration, not code-baked model names).

Routes are logical tiers ("fast-tier", "reasoning-tier") resolved to concrete
FreeLLMAPI models by the capability registry + environment config. Deterministic
starting rules per docs/LLM_GATEWAY.md §3:
  - cheap/fast tier  -> extraction / classification / summary
  - reasoning tier   -> bull / bear / synthesis / judge
"""

from __future__ import annotations

from .contracts import DataClass, LLMTask, RetryPolicy, TaskPolicy

# Logical route tiers; concrete models are supplied by the registry/env, never here.
FAST = "fast-tier"
REASONING = "reasoning-tier"
MID = "mid-tier"

DEFAULT_POLICIES: dict[LLMTask, TaskPolicy] = {
    LLMTask.EVENT_EXTRACTION: TaskPolicy(
        task=LLMTask.EVENT_EXTRACTION, version="1.0",
        allowed_routes=[FAST], fallback_order=[MID],
        timeout_s=20, token_budget=3000, temperature=0.0,
        response_schema="event_extraction.schema.json",
        retry=RetryPolicy(max_retries=2), max_cost=0.02,
        data_classification=DataClass.PUBLIC, cacheable=True,
    ),
    LLMTask.ENTITY_RESOLUTION: TaskPolicy(
        task=LLMTask.ENTITY_RESOLUTION, version="1.0",
        allowed_routes=[FAST], fallback_order=[MID],
        timeout_s=15, token_budget=2000, temperature=0.0,
        response_schema="entity_resolution.schema.json",
        retry=RetryPolicy(max_retries=2), max_cost=0.02,
        data_classification=DataClass.PUBLIC, cacheable=True,
    ),
    LLMTask.DOCUMENT_SUMMARY: TaskPolicy(
        task=LLMTask.DOCUMENT_SUMMARY, version="1.0",
        allowed_routes=[FAST], fallback_order=[MID],
        timeout_s=30, token_budget=6000, temperature=0.1,
        response_schema="document_summary.schema.json",
        retry=RetryPolicy(max_retries=1), max_cost=0.03,
        data_classification=DataClass.PUBLIC, cacheable=True,
    ),
    LLMTask.BULL_CASE: TaskPolicy(
        task=LLMTask.BULL_CASE, version="1.0",
        allowed_routes=[REASONING], fallback_order=[MID],
        timeout_s=45, token_budget=6000, temperature=0.2,
        response_schema="thesis.schema.json",
        retry=RetryPolicy(max_retries=1), max_cost=0.08,
        data_classification=DataClass.INTERNAL, cacheable=False,
    ),
    LLMTask.BEAR_CASE: TaskPolicy(
        task=LLMTask.BEAR_CASE, version="1.0",
        allowed_routes=[REASONING], fallback_order=[MID],
        timeout_s=45, token_budget=6000, temperature=0.2,
        response_schema="thesis.schema.json",
        retry=RetryPolicy(max_retries=1), max_cost=0.08,
        data_classification=DataClass.INTERNAL, cacheable=False,
    ),
    LLMTask.RESEARCH_SYNTHESIS: TaskPolicy(
        task=LLMTask.RESEARCH_SYNTHESIS, version="1.0",
        allowed_routes=[REASONING], fallback_order=[],
        timeout_s=60, token_budget=8000, temperature=0.1,
        response_schema="synthesis.schema.json",
        retry=RetryPolicy(max_retries=1), max_cost=0.12,
        data_classification=DataClass.INTERNAL, cacheable=False,
    ),
    LLMTask.CHAT_ANSWER: TaskPolicy(
        task=LLMTask.CHAT_ANSWER, version="1.0",
        allowed_routes=[MID], fallback_order=[FAST],
        timeout_s=30, token_budget=4000, temperature=0.1,
        response_schema="chat_answer.schema.json",
        retry=RetryPolicy(max_retries=1), max_cost=0.05,
        data_classification=DataClass.USER, cacheable=False,
    ),
}


def get_policy(task: LLMTask) -> TaskPolicy:
    """Return the current policy for a task. Raises if unconfigured."""
    try:
        return DEFAULT_POLICIES[task]
    except KeyError as exc:  # pragma: no cover
        raise KeyError(f"No task policy configured for {task!r}") from exc
