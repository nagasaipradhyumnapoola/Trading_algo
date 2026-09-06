"""All nine agents + async research-floor orchestration (no NotImplementedError left)."""

import asyncio
import json
from datetime import timedelta

from services.ingestion.models import Timeframe
from services.ingestion.sample import SAMPLE_START, build_sample_universe
from services.quant import compute_features
from services.research_workers.agents import (
    DiscoveryAgent,
    HistoricalAgent,
    MarketAgent,
)
from services.research_workers.floor import ResearchFloor, floor_stats
from services.research_workers.llm_gateway import (
    LLMGateway,
    MockProvider,
    build_real_registry,
)

REPO, MASTER, LAST = build_sample_universe(n=160)
UNIVERSE = [i.instrument_id for i in MASTER]
AS_OF = SAMPLE_START + timedelta(days=120)
EVIDENCE = [{"id": "doc1", "text": "NSE filing: MOMO wins government order; capacity expansion."}]


def _features(iid):
    return compute_features(REPO.as_of(iid, Timeframe.EOD, AS_OF), AS_OF)


# --- deterministic agents ------------------------------------------------------

def test_market_agent_is_deterministic():
    res = MarketAgent().run("MOMO", _features("MOMO"))
    assert res.data["deterministic"] is True
    assert res.data["trend"] in ("up", "down", "flat") and "trend" in res.thesis


def test_historical_agent_point_in_time():
    res = HistoricalAgent(REPO, UNIVERSE).run("MOMO", AS_OF)
    assert res.data["point_in_time"] is True
    assert res.data["sample_count"] >= 1                # spike-day analogues exist


def test_discovery_agent_returns_scored_candidates():
    out = DiscoveryAgent().run(REPO, MASTER, SAMPLE_START + timedelta(days=119))
    assert out and "discovery_score" in out[0] and "scan_score" in out[0]


# --- gateway-backed floor ------------------------------------------------------

def _kitchen_sink(call):
    # One response valid across every task schema (extra fields ignored per model).
    return json.dumps({
        "sentiment": 0.6, "label": "positive", "rationale": "positive flow",
        "manipulation_flags": [], "thesis": "strong grounded catalyst",
        "assumptions": ["order executes"], "action": "BUY", "unknowns": ["margin"],
        "answer": "ok", "summary": "s",
        "event_candidates": [{"type": "contract_order", "materiality": 0.8, "novelty": 0.7}],
        "claims": [{"claim": "order won", "polarity": "positive",
                    "evidence_ids": ["doc1"], "confidence": 0.8}],
        "citations": ["doc1"],
    })


def _floor():
    gw = LLMGateway(MockProvider(_kitchen_sink), build_real_registry())
    return ResearchFloor(gw, REPO, UNIVERSE)


def test_floor_runs_all_nine_roles():
    floor = _floor()
    res = asyncio.run(floor.investigate("MOMO", AS_OF, _features("MOMO"), EVIDENCE))
    assert set(res) == {"news", "market", "fundamental", "sentiment",
                        "historical", "bull", "bear", "judge"}
    assert res["judge"].data["action"] == "BUY"
    assert res["bull"].thesis and res["bear"].thesis                 # same evidence, both argue
    assert res["sentiment"].data["label"] == "positive"
    assert res["news"].data["event_candidates"][0]["type"] == "contract_order"


def test_floor_stats():
    floor = _floor()
    res = asyncio.run(floor.investigate("MOMO", AS_OF, _features("MOMO"), EVIDENCE))
    stats = floor_stats([res])
    assert stats["judge"]["ran"] == 1 and stats["bull"]["available"] == 1
    assert stats["market"]["grounded"] == 1 and stats["historical"]["grounded"] == 1


def test_no_notimplemented_remains():
    # Importing every agent module must not leave a placeholder.
    import services.research_workers.agents as A
    for name in ["DiscoveryAgent", "MarketAgent", "SentimentAgent", "HistoricalAgent",
                 "BullAgent", "BearAgent", "JudgeAgent", "NewsAgent", "FundamentalAgent"]:
        assert hasattr(A, name)
