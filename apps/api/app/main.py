"""Indian Alpha API.

Read-only decision support. There are NO broker-write endpoints by design:
no place_order / modify_order / cancel_order / withdraw / transfer. Ever.

Runtime boundary (services/config):
- APP_MODE=demo  -> serves the deterministic SAMPLE universe + mock LLM.
- APP_MODE=real  -> real feeds/LLM are not wired yet, so data endpoints return 503
  rather than silently falling back to sample data. Missing real-mode config fails
  fast at import (Settings validation).

Every response carries an X-Data-Mode header (DEMO/REAL); JSON bodies include
`data_mode` where practical.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from services.config import AppMode, get_settings

from .terminal import TerminalService

SETTINGS = get_settings()          # fail-fast in real mode if required config is missing

app = FastAPI(
    title="Indian Alpha API",
    version="0.7.0",
    description="Agentic Indian equity opportunity discovery & decision support (NSE/BSE).",
)

_WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "index.html"
_terminal: TerminalService | None = None


def get_terminal() -> TerminalService:
    """Lazy singleton. Built only in demo mode; real mode is not wired yet."""
    global _terminal
    if SETTINGS.app_mode is AppMode.REAL:
        raise HTTPException(
            status_code=503,
            detail="APP_MODE=real: real data feeds and LLM routing are not wired yet. "
                   "Use APP_MODE=demo for the sample terminal.",
        )
    if _terminal is None:
        _terminal = TerminalService()
    return _terminal


@app.middleware("http")
async def _data_mode_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Data-Mode"] = SETTINGS.data_mode
    return response


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    try:
        return _WEB.read_text(encoding="utf-8")
    except FileNotFoundError:                       # pragma: no cover
        return "<h1>Indian Alpha</h1><p>UI not found.</p>"


@app.get("/health")
async def health() -> dict[str, object]:
    out: dict[str, object] = {"status": "ok", "data_mode": SETTINGS.data_mode,
                              "app_env": SETTINGS.app_env}
    if SETTINGS.app_mode is AppMode.REAL:
        out["note"] = "real mode: data feeds/LLM not wired; data endpoints return 503"
        return out
    t = get_terminal()
    out.update(t.health_dict())
    out["data_mode"] = SETTINGS.data_mode
    out["data"] = "sample"
    out["last_session"] = t.last.isoformat()
    return out


@app.get("/config/report")
async def config_report() -> dict[str, object]:
    """Presence-only configuration report — never exposes secret values."""
    return SETTINGS.startup_report()


@app.get("/instruments")
async def instruments() -> dict[str, object]:
    rows = get_terminal().instruments()
    return {"data_mode": SETTINGS.data_mode, "count": len(rows), "instruments": rows}


@app.get("/recommendations")
async def recommendations() -> dict[str, object]:
    t = get_terminal()
    action = "BUY" if t.recs else "NO_TRADE"
    return {"data_mode": SETTINGS.data_mode, "as_of": t.current_as_of.isoformat(),
            "action": action, "count": len(t.recs), "recommendations": t.recs,
            "vetoed": t.vetoed}


@app.get("/portfolio")
async def portfolio() -> dict[str, object]:
    return {"data_mode": SETTINGS.data_mode, **get_terminal().portfolio_data}


@app.get("/performance")
async def performance() -> dict[str, object]:
    return {"data_mode": SETTINGS.data_mode, **get_terminal().perf}


@app.get("/alerts")
async def alerts() -> dict[str, object]:
    rows = get_terminal().alert_rows
    return {"data_mode": SETTINGS.data_mode, "count": len(rows), "alerts": rows}


@app.get("/metrics")
async def metrics() -> dict[str, object]:
    return get_terminal().metrics_snapshot()


@app.get("/audit/{instrument_id}")
async def audit(instrument_id: str) -> dict[str, object]:
    return get_terminal().audit(instrument_id)


@app.get("/bars/{instrument_id}")
async def bars(instrument_id: str, limit: int = Query(60, ge=5, le=200)) -> dict[str, object]:
    return {"data_mode": SETTINGS.data_mode, "instrument_id": instrument_id,
            "bars": get_terminal().bars(instrument_id, limit)}


@app.get("/evidence/{instrument_id}")
async def evidence(instrument_id: str) -> dict[str, object]:
    return {"data_mode": SETTINGS.data_mode, "instrument_id": instrument_id,
            "evidence": get_terminal().evidence(instrument_id)}


class ChatRequest(BaseModel):
    question: str
    instrument_id: str | None = None


@app.post("/chat")
async def chat(req: ChatRequest) -> dict[str, object]:
    t = get_terminal()
    if not t.chat_allowed():
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    return await t.chat(req.question, req.instrument_id)


class FeedbackRequest(BaseModel):
    instrument_id: str
    label: str                       # useful | not_useful | executed | not_executed
    rec_id: str = ""
    note: str = ""


@app.post("/feedback")
async def feedback(req: FeedbackRequest) -> dict[str, object]:
    try:
        return get_terminal().record_feedback(req.instrument_id, req.label, req.rec_id, req.note)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid feedback label")
