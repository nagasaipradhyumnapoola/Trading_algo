"""Grounded chat: answers only from evidence, refuses otherwise."""

import asyncio
import json

from services.research_workers.chat import GroundedChat
from services.research_workers.llm_gateway import (
    DataClass,
    LLMGateway,
    MockProvider,
    ModelCapabilityRegistry,
    ModelRoute,
)
from services.research_workers.llm_gateway.policies import MID

EVIDENCE = [{"id": "doc1", "text": "NSE filing dated 2026-01-01: order won"}]


def _reg():
    reg = ModelCapabilityRegistry()
    # CHAT_ANSWER is USER-class data -> the route must permit USER.
    reg.register(ModelRoute(name=MID, healthy=True,
                            permitted_data_classification=DataClass.USER))
    return reg


def _chat(responder):
    return GroundedChat(LLMGateway(MockProvider(responder), _reg()))


def test_answers_from_evidence():
    chat = _chat(lambda c: json.dumps({"answer": "An order was won.", "citations": ["doc1"]}))
    res = asyncio.run(chat.answer("What happened?", EVIDENCE))
    assert res.grounded and "order" in res.answer.lower()
    assert res.citations == ["doc1"]


def test_refuses_without_evidence():
    chat = _chat(lambda c: json.dumps({"answer": "x", "citations": []}))
    res = asyncio.run(chat.answer("What happened?", []))
    assert not res.grounded


def test_refuses_when_answer_not_grounded():
    chat = _chat(lambda c: json.dumps({"answer": "made up", "citations": ["ghost"]}))
    res = asyncio.run(chat.answer("What happened?", EVIDENCE))     # cites unknown id -> rejected
    assert not res.grounded


def test_refuses_when_llm_unavailable():
    chat = GroundedChat(LLMGateway(MockProvider(lambda c: "{}"), ModelCapabilityRegistry()))
    res = asyncio.run(chat.answer("What happened?", EVIDENCE))     # no route -> degraded
    assert not res.grounded
