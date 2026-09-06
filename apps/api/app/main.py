"""Indian Alpha API — Phase 6 terminal service (SAMPLE data).

Read-only decision support. There are NO broker-write endpoints by design:
no place_order / modify_order / cancel_order / withdraw / transfer. Ever.

Serves a deterministic SAMPLE universe (clearly labelled). Probability comes from
the calibrated quant system; risk/sizing/P&L are deterministic; the LLM only powers
grounded chat via the gateway. Phase 7 swaps sample ingestion for real feeds.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .terminal import TerminalService

app = FastAPI(
    title="Indian Alpha API",
    version="0.6.0",
    description="Agentic Indian equity opportunity discovery & decision support (NSE/BSE).",
)

_TERMINAL = TerminalService()
_WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    try:
        return _WEB.read_text(encoding="utf-8")
    except FileNotFoundError:                       # pragma: no cover
        return "<h1>Indian Alpha</h1><p>UI not found.</p>"


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "data": "sample",
            "as_of": _TERMINAL.current_as_of.isoformat(),
            "last_session": _TERMINAL.last.isoformat()}


@app.get("/instruments")
async def instruments() -> dict[str, object]:
    rows = _TERMINAL.instruments()
    return {"count": len(rows), "instruments": rows}


@app.get("/recommendations")
async def recommendations() -> dict[str, object]:
    recs = _TERMINAL.recs
    action = "BUY" if recs else "NO_TRADE"
    return {"as_of": _TERMINAL.current_as_of.isoformat(), "action": action,
            "count": len(recs), "recommendations": recs, "vetoed": _TERMINAL.vetoed}


@app.get("/portfolio")
async def portfolio() -> dict[str, object]:
    return _TERMINAL.portfolio_data


@app.get("/performance")
async def performance() -> dict[str, object]:
    return _TERMINAL.perf


@app.get("/alerts")
async def alerts() -> dict[str, object]:
    return {"count": len(_TERMINAL.alert_rows), "alerts": _TERMINAL.alert_rows}


@app.get("/bars/{instrument_id}")
async def bars(instrument_id: str, limit: int = Query(60, ge=5, le=200)) -> dict[str, object]:
    return {"instrument_id": instrument_id, "bars": _TERMINAL.bars(instrument_id, limit)}


@app.get("/evidence/{instrument_id}")
async def evidence(instrument_id: str) -> dict[str, object]:
    return {"instrument_id": instrument_id, "evidence": _TERMINAL.evidence(instrument_id)}


class ChatRequest(BaseModel):
    question: str
    instrument_id: str | None = None


@app.post("/chat")
async def chat(req: ChatRequest) -> dict[str, object]:
    return await _TERMINAL.chat(req.question, req.instrument_id)
