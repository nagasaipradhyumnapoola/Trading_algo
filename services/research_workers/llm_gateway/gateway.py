"""LLMGateway — the ONE path from application code to any LLM.

Mandatory. No agent, route, worker, or frontend calls a provider directly. The
gateway resolves a route from configuration, enforces the task policy, sanitizes
untrusted content, validates structured output and citations, retries/falls back
across approved routes, trips a circuit breaker on unhealthy routes, caches only
safe deterministic tasks, writes an immutable llm_run per call, and degrades
cleanly (deterministic results preserved, nothing fabricated) when all routes fail.

Numbers (probabilities, expected return, risk, sizing, P&L) are NEVER produced
here — those are deterministic quant-engine outputs.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from .contracts import (
    DataClass,
    GatewayResult,
    GatewayState,
    LLMRunRecord,
    LLMTask,
    ModelRoute,
)
from .policies import get_policy
from .providers import LLMProvider, ProviderError, ProviderTimeout
from .registry import ModelCapabilityRegistry, build_default_registry
from .sanitize import build_user_prompt
from .schemas import response_model_for
from .templates import TEMPLATE_VERSION, system_for

_DATA_ORDER = {DataClass.PUBLIC: 0, DataClass.INTERNAL: 1, DataClass.USER: 2}


class CircuitBreaker:
    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold
        self._failures: dict[str, int] = {}
        self._open: set[str] = set()

    def is_open(self, route: str) -> bool:
        return route in self._open

    def record_failure(self, route: str) -> None:
        self._failures[route] = self._failures.get(route, 0) + 1
        if self._failures[route] >= self.threshold:
            self._open.add(route)

    def record_success(self, route: str) -> None:
        self._failures[route] = 0
        self._open.discard(route)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LLMGateway:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        registry: ModelCapabilityRegistry | None = None,
        *,
        audit_path: str | Path | None = None,
        breaker_threshold: int = 3,
    ) -> None:
        self.provider = provider
        self.registry = registry or build_default_registry()
        self.breaker = CircuitBreaker(breaker_threshold)
        self.runs: list[LLMRunRecord] = []
        self._cache: dict[str, dict] = {}
        self._audit_path = Path(audit_path) if audit_path else None

    # -- public ----------------------------------------------------------------

    async def request(
        self,
        *,
        agent: str,
        task: LLMTask,
        payload: dict[str, Any],
        source_ids: list[str] | None = None,
    ) -> GatewayResult:
        policy = get_policy(task)
        model = response_model_for(task)
        system = system_for(task)
        sources = payload.get("sources", [])
        instruction = payload.get("instruction", "")
        valid_ids = {str(s.get("id")) for s in sources} | set(source_ids or [])
        user = build_user_prompt(instruction, sources)

        run = LLMRunRecord(
            run_id=f"run_{uuid.uuid4().hex[:12]}", agent=agent, task=task,
            policy_version=policy.version, template_version=TEMPLATE_VERSION,
            input_source_ids=sorted(valid_ids),
            input_content_hashes=[_sha(str(s.get("text", ""))) for s in sources],
        )

        # cache (deterministic tasks only)
        cache_key = None
        if policy.cacheable:
            cache_key = _sha(f"{task.value}|{policy.version}|{TEMPLATE_VERSION}|{user}")
            if cache_key in self._cache:
                run.selected_route = "cache"
                run.state = GatewayState.VALIDATED
                self._commit(run)
                return GatewayResult(state=GatewayState.VALIDATED, task=task,
                                     data=self._cache[cache_key], run=run)

        if self.provider is None:
            return self._degraded(task, run, "no provider configured")

        routes = self._candidate_routes(policy.allowed_routes + policy.fallback_order,
                                        policy.data_classification)
        if not routes:
            return self._degraded(task, run, "no healthy route available")

        started = time.perf_counter()
        for route in routes:
            outcome = await self._try_route(route, system, user, policy, model, valid_ids, run)
            if outcome is not None:                       # validated data
                run.selected_route = route.name
                run.latency_ms = int((time.perf_counter() - started) * 1000)
                run.state = GatewayState.VALIDATED
                self._commit(run)
                if cache_key is not None:
                    self._cache[cache_key] = outcome
                return GatewayResult(state=GatewayState.VALIDATED, task=task,
                                     data=outcome, run=run)

        run.latency_ms = int((time.perf_counter() - started) * 1000)
        return self._degraded(task, run, "all routes failed validation/availability")

    # -- internals -------------------------------------------------------------

    def _candidate_routes(self, names: list[str], max_class: DataClass) -> list[ModelRoute]:
        seen: set[str] = set()
        out: list[ModelRoute] = []
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            route = self.registry.get(name)
            # a route must be cleared for AT LEAST the task's data sensitivity
            if (route and route.healthy and not self.breaker.is_open(name)
                    and _DATA_ORDER[route.permitted_data_classification] >= _DATA_ORDER[max_class]):
                out.append(route)
        return out

    async def _try_route(self, route, system, user, policy, model, valid_ids, run) -> dict | None:
        """Try one route with bounded retries. Returns validated data or None."""
        for attempt in range(policy.retry.max_retries + 1):
            run.attempted_routes.append(route.name)
            try:
                raw = await self.provider.complete(
                    route=route.name, system=system, user=user,
                    params={"temperature": policy.temperature,
                            "max_tokens": policy.token_budget, "timeout": policy.timeout_s},
                )
            except ProviderTimeout as exc:
                self.breaker.record_failure(route.name)
                run.validation_failures.append(f"timeout:{exc}")
                run.retry_count += 1
                if "timeout" in policy.retry.retry_on and attempt < policy.retry.max_retries:
                    continue
                return None
            except ProviderError as exc:
                self.breaker.record_failure(route.name)
                run.validation_failures.append(f"provider:{exc}")
                run.retry_count += 1
                if "provider_5xx" in policy.retry.retry_on and attempt < policy.retry.max_retries:
                    continue
                return None

            ok, payload = self._validate(raw, model, valid_ids)
            if ok:
                self.breaker.record_success(route.name)
                return payload
            run.validation_failures.append(payload)          # reason string
            if payload.startswith("schema") and "schema" in policy.retry.retry_on \
                    and attempt < policy.retry.max_retries:
                run.retry_count += 1
                continue
            self.breaker.record_failure(route.name)
            return None
        return None

    @staticmethod
    def _validate(raw: str, model, valid_ids: set[str]) -> tuple[bool, Any]:
        try:
            obj = json.loads(raw)
        except (ValueError, TypeError):
            return False, "schema:invalid_json"
        try:
            instance = model.model_validate(obj)
        except Exception:                                    # pydantic ValidationError et al.
            return False, "schema:validation_error"
        unknown = instance.cited_ids() - valid_ids
        if unknown:
            return False, f"citation:unknown:{sorted(unknown)}"
        return True, instance.model_dump()

    def _degraded(self, task: LLMTask, run: LLMRunRecord, reason: str) -> GatewayResult:
        run.state = GatewayState.FAILED
        run.validation_failures.append(f"degraded:{reason}")
        self._commit(run)
        return GatewayResult(state=GatewayState.FAILED, task=task, run=run, error=reason)

    def _commit(self, run: LLMRunRecord) -> None:
        self.runs.append(run)
        if self._audit_path is not None:
            with self._audit_path.open("a", encoding="utf-8") as fh:
                fh.write(run.model_dump_json() + "\n")
