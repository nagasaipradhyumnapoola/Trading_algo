"""Indian Alpha — FastAPI entry point (Phase 1 skeleton).

Read-only decision support. There are NO broker-write endpoints by design:
no place_order / modify_order / cancel_order / withdraw / transfer. Ever.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Indian Alpha API",
    version="0.1.0",
    description="Agentic Indian equity opportunity discovery & decision support (NSE/BSE).",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/opportunities/top")
async def top_opportunities(limit: int = 5) -> dict[str, object]:
    """Return the current top-ranked opportunities.

    Stub: the discovery → agents → judge → risk → ranker pipeline is not wired
    yet. Returns an empty ranked set so the terminal UI can integrate early.
    """
    return {"count": 0, "limit": limit, "opportunities": []}
