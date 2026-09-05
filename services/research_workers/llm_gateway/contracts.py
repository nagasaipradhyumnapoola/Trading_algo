"""Typed contracts for the LLM Gateway.

See docs/LLM_GATEWAY.md. These shapes are the stable surface; the routing,
validation, and provider calls are implemented in Phase 3.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMTask(str, Enum):
    EVENT_EXTRACTION = "event_extraction"
    ENTITY_RESOLUTION = "entity_resolution"
    DOCUMENT_SUMMARY = "document_summary"
    BULL_CASE = "bull_case"
    BEAR_CASE = "bear_case"
    RESEARCH_SYNTHESIS = "research_synthesis"
    CHAT_ANSWER = "chat_answer"


class DataClass(str, Enum):
    """Max data sensitivity a task/route may handle."""

    PUBLIC = "public"
    INTERNAL = "internal"
    USER = "user"


class GatewayState(str, Enum):
    VALIDATED = "validated"
    FAILED = "failed"


class RetryPolicy(BaseModel):
    max_retries: int = 1
    retry_on: list[str] = Field(default_factory=lambda: ["timeout", "schema", "provider_5xx"])


class TaskPolicy(BaseModel):
    """Versioned configuration for one LLM task. Never names a model in a prompt."""

    task: LLMTask
    version: str
    allowed_routes: list[str]           # ordered; resolved against the registry
    fallback_order: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    token_budget: int = 4000
    temperature: float = 0.0
    response_schema: str = ""           # JSON Schema name / ref the output must satisfy
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    max_cost: float = 0.05              # hard per-call ceiling
    data_classification: DataClass = DataClass.PUBLIC
    cacheable: bool = False             # deterministic tasks only


class ModelRoute(BaseModel):
    """One entry in the model capability registry."""

    name: str                          # route/model identifier (from config, not code)
    provider: str = "freellmapi"
    context_tokens: int = 8000
    structured_output_reliability: float = 0.0   # measured, 0..1
    latency_ms_p50: int = 0
    healthy: bool = True
    permitted_data_classification: DataClass = DataClass.PUBLIC
    cost_per_1k_tokens: float = 0.0


class LLMRunRecord(BaseModel):
    """Immutable audit record. One per gateway call."""

    run_id: str
    agent: str
    task: LLMTask
    policy_version: str
    selected_route: str | None = None
    attempted_routes: list[str] = Field(default_factory=list)
    template_version: str = ""
    input_source_ids: list[str] = Field(default_factory=list)
    input_content_hashes: list[str] = Field(default_factory=list)
    raw_result_uri: str | None = None
    validated_result_uri: str | None = None
    validation_failures: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    retry_count: int = 0
    tokens: int | None = None
    cost: float | None = None
    state: GatewayState = GatewayState.FAILED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GatewayResult(BaseModel):
    """What every agent gets back. Either a validated payload or an explicit failure."""

    state: GatewayState
    task: LLMTask
    data: dict[str, Any] | None = None     # validated structured output (VALIDATED only)
    run: LLMRunRecord | None = None
    error: str | None = None               # populated on FAILED / degraded mode

    @property
    def ok(self) -> bool:
        return self.state is GatewayState.VALIDATED
