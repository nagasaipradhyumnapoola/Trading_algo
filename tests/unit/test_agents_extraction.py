"""News/Fundamental agents over the gateway, with the human-review queue."""

import asyncio
import json

from services.research_workers.agents import FundamentalAgent, NewsAgent
from services.research_workers.llm_gateway import (
    LLMGateway,
    ModelCapabilityRegistry,
    ModelRoute,
    MockProvider,
)
from services.research_workers.llm_gateway.policies import FAST
from services.research_workers.review_queue import ReviewQueue, ReviewReason

SOURCES = [{"id": "doc1", "text": "NSE filing: government order won"}]


def _reg():
    reg = ModelCapabilityRegistry()
    reg.register(ModelRoute(name=FAST, healthy=True))
    return reg


def _extraction(claims, events=(("contract_order", 0.8, 0.7),)):
    return json.dumps({
        "instrument_ids": ["INDA0001"],
        "event_candidates": [{"type": t, "materiality": m, "novelty": n} for t, m, n in events],
        "claims": claims,
        "citations": ["doc1"],
    })


def _claim(text, pol="positive", conf=0.8):
    return {"claim": text, "polarity": pol, "evidence_ids": ["doc1"], "confidence": conf}


def _news(responder, review=None):
    return NewsAgent(LLMGateway(MockProvider(responder), _reg()), review=review)


def test_news_agent_returns_grounded_events():
    agent = _news(lambda c: _extraction([_claim("order won")]))
    res = asyncio.run(agent.run("INDA0001", SOURCES))
    assert "contract_order" in res.thesis
    assert res.confidence == 0.8
    assert res.data["event_candidates"][0]["type"] == "contract_order"
    assert res.evidence[0].source == "doc1"


def test_low_confidence_is_flagged_for_review():
    q = ReviewQueue()
    agent = _news(lambda c: _extraction([_claim("weak signal", conf=0.2)]), review=q)
    asyncio.run(agent.run("INDA0001", SOURCES))
    assert any(i.reason is ReviewReason.LOW_CONFIDENCE for i in q.items())


def test_conflicting_claims_flagged():
    q = ReviewQueue()
    agent = _news(lambda c: _extraction([_claim("good", "positive"), _claim("bad", "negative")]), review=q)
    asyncio.run(agent.run("INDA0001", SOURCES))
    assert any(i.reason is ReviewReason.CONFLICT for i in q.items())


def test_degraded_when_llm_unavailable():
    q = ReviewQueue()
    agent = NewsAgent(LLMGateway(MockProvider(lambda c: "{}"), ModelCapabilityRegistry()), review=q)
    res = asyncio.run(agent.run("INDA0001", SOURCES))     # no routes -> degraded
    assert res.data["available"] is False
    assert any(i.reason is ReviewReason.DEGRADED for i in q.items())


def test_fundamental_agent_runs():
    agent = FundamentalAgent(LLMGateway(MockProvider(lambda c: _extraction(
        [_claim("revenue +20%")], events=())), _reg()))
    res = asyncio.run(agent.run("INDA0001", SOURCES))
    assert "facts" in res.thesis and res.confidence == 0.8
