"""Extraction eval harness: precision/recall by event type."""

import asyncio
import json

from services.research_workers.agents import NewsAgent
from services.research_workers.extraction_eval import LabeledExample, evaluate
from services.research_workers.llm_gateway import (
    LLMGateway,
    ModelCapabilityRegistry,
    ModelRoute,
    MockProvider,
)
from services.research_workers.llm_gateway.policies import FAST

SOURCES = [{"id": "doc1", "text": "government order won"}]


def _reg():
    reg = ModelCapabilityRegistry()
    reg.register(ModelRoute(name=FAST, healthy=True))
    return reg


def _agent(event_type):
    def responder(call):
        return json.dumps({
            "event_candidates": [{"type": event_type, "materiality": 0.8, "novelty": 0.7}],
            "claims": [{"claim": "x", "polarity": "positive", "evidence_ids": ["doc1"], "confidence": 0.8}],
            "citations": ["doc1"],
        })
    return NewsAgent(LLMGateway(MockProvider(responder), _reg()))


def test_perfect_extraction_scores_one():
    examples = [LabeledExample(instrument_id="A", sources=SOURCES, expected_types={"contract_order"})]
    rep = asyncio.run(evaluate(_agent("contract_order"), examples))
    assert rep.precision == 1.0 and rep.recall == 1.0
    assert rep.per_type["contract_order"].tp == 1


def test_wrong_type_tanks_precision_and_recall():
    examples = [LabeledExample(instrument_id="A", sources=SOURCES, expected_types={"contract_order"})]
    rep = asyncio.run(evaluate(_agent("earnings"), examples))     # predicts wrong type
    assert rep.precision == 0.0 and rep.recall == 0.0
    assert rep.fp == 1 and rep.fn == 1
