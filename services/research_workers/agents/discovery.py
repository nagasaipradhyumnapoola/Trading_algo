"""Agent 1 — Discovery. Surface candidates the user did not ask for.

Deterministic entry point: runs the market scanner over the universe and attaches a
discovery score (source reliability, novelty/materiality placeholders, price-already-
reacted, liquidity, data quality). Real web/filings-driven follow-up queries plug in
via the news/filings providers; the scoring stays deterministic code.
"""

from __future__ import annotations

from datetime import date

from services.quant import ScanConfig, scan

from ..discovery import DiscoverySignal, discovery_score


class DiscoveryAgent:
    name = "discovery"

    def run(self, repo, master, as_of: date, *, config: ScanConfig | None = None) -> list[dict]:
        candidates = scan(repo, master, as_of, config or ScanConfig())
        out: list[dict] = []
        for c in candidates:
            sig = DiscoverySignal(
                instrument_id=c.instrument_id, source_tier=1, novelty=0.5, materiality=0.5,
                event_age_days=0.0, price_reacted=min(1.0, max(0.0, c.momentum)),
                avg_turnover=c.avg_turnover)
            scored = discovery_score(sig)
            out.append({"instrument_id": c.instrument_id, "scan_score": round(c.score, 3),
                        "discovery_score": round(scored.score, 3), "reason": c.reason})
        return out
