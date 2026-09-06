"""Real FreeLLMAPI adapter, tested against a simulated server (httpx MockTransport)."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from services.research_workers.llm_gateway import (
    FreeLLMProvider,
    GatewayState,
    LLMTask,
    ProviderError,
    ProviderTimeout,
    build_real_gateway,
    health_check,
)
from services.research_workers.llm_gateway.policies import FAST, REASONING

_SETTINGS = SimpleNamespace(
    freellm_api_base="http://localhost:3001/v1", freellm_api_key="freellmapi-testkey",
    freellm_model_fast="", freellm_model_reasoning="",
)


def _chat_response(content: str, captured: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["request"] = request
            captured["body"] = json.loads(request.content)
        return httpx.Response(200, headers={"X-Routed-Via": "groq/llama-3.1"}, json={
            "choices": [{"message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })
    return httpx.MockTransport(handler)


def _client(transport):
    return httpx.AsyncClient(transport=transport)


def test_complete_sends_freellm_wire_format():
    captured: dict = {}
    provider = FreeLLMProvider(_SETTINGS.freellm_api_base, _SETTINGS.freellm_api_key,
                               {FAST: "auto:fast"}, client=_client(_chat_response('{"ok":1}', captured)))
    out = asyncio.run(provider.complete(route=FAST, system="SYS", user="USER",
                                        params={"temperature": 0.0}))
    assert out == '{"ok":1}'
    body, req = captured["body"], captured["request"]
    assert body["model"] == "auto:fast"                       # logical tier -> model id
    assert body["response_format"] == "json_object"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert req.headers["authorization"] == "Bearer freellmapi-testkey"
    assert req.url.path.endswith("/chat/completions")
    assert provider.last_routed_via == "groq/llama-3.1"


def test_reasoning_route_maps_to_auto_smart():
    captured: dict = {}
    provider = FreeLLMProvider("http://x/v1", "k", {REASONING: "auto:smart"},
                               client=_client(_chat_response("{}", captured)))
    asyncio.run(provider.complete(route=REASONING, system="s", user="u", params={}))
    assert captured["body"]["model"] == "auto:smart"


def test_server_error_raises_provider_error():
    provider = FreeLLMProvider("http://x/v1", "k", {},
                               client=_client(httpx.MockTransport(lambda r: httpx.Response(500))))
    with pytest.raises(ProviderError):
        asyncio.run(provider.complete(route=FAST, system="s", user="u", params={}))


def test_timeout_raises_provider_timeout():
    def boom(r): raise httpx.ReadTimeout("timeout")
    provider = FreeLLMProvider("http://x/v1", "k", {}, client=_client(httpx.MockTransport(boom)))
    with pytest.raises(ProviderTimeout):
        asyncio.run(provider.complete(route=FAST, system="s", user="u", params={}))


def test_health_check():
    ok = httpx.MockTransport(lambda r: httpx.Response(200, json={"data": []}))
    bad = httpx.MockTransport(lambda r: httpx.Response(503))
    assert asyncio.run(health_check("http://x/v1", "k", client=_client(ok))) is True
    assert asyncio.run(health_check("http://x/v1", "k", client=_client(bad))) is False


def test_real_gateway_end_to_end_validates():
    # A simulated FreeLLMAPI returning a valid, cited extraction -> VALIDATED via the gateway.
    extraction = json.dumps({
        "event_candidates": [{"type": "contract_order", "materiality": 0.8, "novelty": 0.7}],
        "claims": [{"claim": "order won", "polarity": "positive",
                    "evidence_ids": ["doc1"], "confidence": 0.8}],
        "citations": ["doc1"],
    })
    gw = build_real_gateway(_SETTINGS, client=_client(_chat_response(extraction)))
    result = asyncio.run(gw.request(
        agent="news", task=LLMTask.EVENT_EXTRACTION,
        payload={"instruction": "extract", "sources": [{"id": "doc1", "text": "NSE filing"}]}))
    assert result.state is GatewayState.VALIDATED
    assert result.data["event_candidates"][0]["type"] == "contract_order"
    assert result.run.selected_route == FAST                  # event_extraction -> fast tier
