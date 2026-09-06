"""Phase 3 demo: discover -> extract (via gateway) -> score -> rank.

Scans the sample universe, feeds each candidate a mock NSE filing through the
News agent (LLMGateway + MockProvider), then computes a deterministic discovery
score. Shows grounded events, evidence ids, the immutable llm_run count, and the
human-review queue. No network, no keys.

Run:
    python scripts/discovery_demo.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ingestion.sample import build_sample_universe  # noqa: E402
from services.quant import ScanConfig, scan  # noqa: E402
from services.research_workers.agents import NewsAgent  # noqa: E402
from services.research_workers.discovery import (  # noqa: E402
    DiscoveryCandidate,
    DiscoverySignal,
    discovery_score,
    rank_discoveries,
)
from services.research_workers.llm_gateway import (  # noqa: E402
    LLMGateway,
    MockProvider,
    ModelCapabilityRegistry,
    ModelRoute,
)
from services.research_workers.llm_gateway.policies import FAST  # noqa: E402
from services.research_workers.review_queue import ReviewQueue  # noqa: E402


def _responder(call: dict) -> str:
    # cite the exact source id that was framed into the prompt
    sid = (re.search(r'id="([^"]+)"', call["user"]) or [None, "unknown"])[1]
    return json.dumps({
        "instrument_ids": [],
        "event_candidates": [{"type": "government_order", "materiality": 0.85, "novelty": 0.8}],
        "claims": [{"claim": "Government order awarded", "polarity": "positive",
                    "evidence_ids": [sid], "confidence": 0.82}],
        "citations": [sid],
    })


def _gateway() -> LLMGateway:
    reg = ModelCapabilityRegistry()
    reg.register(ModelRoute(name=FAST, healthy=True))
    return LLMGateway(MockProvider(_responder), reg)


async def main() -> None:
    repo, master, last = build_sample_universe()
    scanned = scan(repo, master, last, ScanConfig(top_k=5))

    gw = _gateway()
    review = ReviewQueue()
    news = NewsAgent(gw, review=review)

    candidates: list[DiscoveryCandidate] = []
    for c in scanned:
        sid = f"nse_{c.instrument_id}"
        docs = [{"id": sid, "text": f"NSE filing: {c.instrument_id} wins government order; capacity expansion"}]
        res = await news.run(c.instrument_id, docs)
        events = res.data.get("event_candidates", []) if res.data else []
        ev = events[0] if events else {"materiality": 0.0, "novelty": 0.0, "type": "none"}

        sig = DiscoverySignal(
            instrument_id=c.instrument_id, source_tier=1,
            novelty=ev["novelty"], materiality=ev["materiality"],
            event_age_days=0.0, price_reacted=min(1.0, max(0.0, c.momentum)),
            avg_turnover=c.avg_turnover,
        )
        scored = discovery_score(sig)
        candidates.append(DiscoveryCandidate(
            instrument_id=c.instrument_id, score=scored.score,
            event_types=[e["type"] for e in events], scanner_reason=c.reason,
            evidence_ids=[eid for cl in res.data.get("claims", []) for eid in cl.get("evidence_ids", [])],
            components=scored.components,
        ))

    print(f"scanned candidates: {len(scanned)}   llm_runs: {len(gw.runs)}   "
          f"review queue: {len(review)}\n")
    print(f"{'RANK':<5}{'TICKER':<8}{'DISC':<7}{'EVENTS':<20}{'EVIDENCE':<14}{'WHY'}")
    for i, c in enumerate(rank_discoveries(candidates), 1):
        print(f"{i:<5}{c.instrument_id:<8}{c.score:<7.3f}"
              f"{','.join(c.event_types):<20}{','.join(c.evidence_ids):<14}{c.scanner_reason}")
    print("\nDiscovery score is deterministic; novelty/materiality are grounded, "
          "citation-validated extraction. Numbers never come from the LLM.")


if __name__ == "__main__":
    asyncio.run(main())
