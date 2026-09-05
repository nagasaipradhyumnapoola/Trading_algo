"""Indian Alpha API — Phase 1 sample service.

Read-only decision support. There are NO broker-write endpoints by design:
no place_order / modify_order / cancel_order / withdraw / transfer. Ever.

This Phase 1 build serves a deterministic SAMPLE universe (clearly labelled) so
the scanner and NO_TRADE path are exercisable end-to-end. Phase 2 swaps in real
ingestion behind the same endpoints.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from services.evaluation import BaselineStrategy
from services.ingestion.sample import build_sample_universe
from services.quant import ScanConfig, scan

app = FastAPI(
    title="Indian Alpha API",
    version="0.1.0",
    description="Agentic Indian equity opportunity discovery & decision support (NSE/BSE).",
)

# Build the sample universe once at import (Phase 1 only).
_REPO, _MASTER, _LAST_SESSION = build_sample_universe()
_STRATEGY = BaselineStrategy()
_WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    try:
        return _WEB.read_text(encoding="utf-8")
    except FileNotFoundError:                       # pragma: no cover
        return "<h1>Indian Alpha</h1><p>UI not found.</p>"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data": "sample", "last_session": _LAST_SESSION.isoformat()}


@app.get("/instruments")
async def instruments() -> dict[str, object]:
    rows = [
        {"instrument_id": i.instrument_id, "symbol": i.symbol,
         "name": i.name, "sector": i.sector, "status": i.status.value}
        for i in _MASTER
    ]
    return {"count": len(rows), "instruments": rows}


@app.get("/opportunities/top")
async def top_opportunities(
    limit: int = Query(5, ge=1, le=50),
    as_of: date | None = None,
) -> dict[str, object]:
    """Ranked candidates from the deterministic scanner, or NO_TRADE."""
    when = as_of or _LAST_SESSION
    candidates = scan(_REPO, _MASTER, when, ScanConfig(top_k=limit))

    if not candidates:
        return {"as_of": when.isoformat(), "action": "NO_TRADE", "count": 0,
                "opportunities": [], "note": "No candidate cleared the gates."}

    opportunities = []
    for c in candidates:
        sig = _STRATEGY.signal_for(c.instrument_id, when)
        opportunities.append({
            "action": "BUY",
            "instrument_id": c.instrument_id,
            "last_close": c.features.values.get("last_close"),
            "score": round(c.score, 4),
            "momentum": round(c.momentum, 4),
            "volume_ratio": round(c.volume_ratio, 2),
            "avg_turnover": round(c.avg_turnover, 0),
            "rs_percentile": round(c.rs_percentile, 3),
            "entry_rule": sig.entry_rule,
            "stop_pct": sig.stop_pct,
            "target_pct": sig.target_pct,
            "horizon_sessions": sig.horizon_sessions,
            "reason": c.reason,
        })
    return {"as_of": when.isoformat(), "action": "BUY",
            "count": len(opportunities), "opportunities": opportunities}
