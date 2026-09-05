"""Smoke tests: packages import and the LLM boundary holds."""

import asyncio

import pytest

from services.research_workers.agents import (
    BearAgent,
    BullAgent,
    DiscoveryAgent,
    JudgeAgent,
    MarketAgent,
    NewsAgent,
)
from services.research_workers.llm_gateway import (
    DEFAULT_POLICIES,
    GatewayState,
    LLMGateway,
    LLMTask,
    get_policy,
)


def test_nine_agents_importable():
    names = {
        DiscoveryAgent().name,
        NewsAgent().name,
        MarketAgent().name,
        BullAgent().name,
        BearAgent().name,
        JudgeAgent().name,
    }
    assert {"discovery", "news", "market", "bull", "bear", "judge"} <= names


def test_api_imports():
    from apps.api.app.main import app

    assert app.title == "Indian Alpha API"


def test_every_task_has_a_versioned_policy():
    for task in LLMTask:
        policy = get_policy(task)
        assert policy.version
        assert policy.allowed_routes, f"{task} has no allowed routes"
    assert set(DEFAULT_POLICIES) == set(LLMTask)


def test_policies_never_hardcode_provider_model_names():
    # Routes must be logical tiers, not concrete provider model ids.
    banned = ("gpt", "claude", "gemini", "llama", "mistral")
    for policy in DEFAULT_POLICIES.values():
        for route in [*policy.allowed_routes, *policy.fallback_order]:
            assert not any(b in route.lower() for b in banned), route


def test_gateway_blocks_until_phase3():
    # No provider calls are permitted yet; the single path raises explicitly.
    gw = LLMGateway()
    with pytest.raises(NotImplementedError):
        asyncio.run(gw.request(agent="test", task=LLMTask.EVENT_EXTRACTION, payload={}))


def test_degraded_state_is_a_clean_failure():
    gw = LLMGateway()
    result = gw._degraded(LLMTask.BULL_CASE, "all routes down")
    assert result.state is GatewayState.FAILED
    assert result.ok is False
    assert result.data is None
