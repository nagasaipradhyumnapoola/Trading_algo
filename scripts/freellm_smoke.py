"""Live smoke test against a local FreeLLMAPI server, through the mandatory gateway.

Set FREELLM_API_BASE (default http://localhost:3001/v1) and FREELLM_API_KEY in .env,
start your FreeLLMAPI server, then:

    python scripts/freellm_smoke.py

Runs a /models health check and one real EVENT_EXTRACTION call, printing the routed
model (X-Routed-Via), the gateway verdict, and the grounded/validated events. Nothing
is fabricated: if the LLM output fails JSON/citation validation, the gateway reports
a degraded failure rather than inventing analysis.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.config import load_settings  # noqa: E402
from services.research_workers.llm_gateway import (  # noqa: E402
    LLMTask,
    build_real_gateway,
    health_check,
)

SOURCES = [{"id": "nse_demo", "text":
            "NSE filing: ABC Ltd wins a government order worth Rs 500 cr; capacity "
            "expansion of 40% announced; management guides higher FY revenue."}]


async def main() -> None:
    s = load_settings()
    base = s.freellm_api_base or "http://localhost:3001/v1"
    if not s.freellm_api_key:
        print("Set FREELLM_API_KEY (and optionally FREELLM_API_BASE) in .env first.")
        return
    s.freellm_api_base = base

    print(f"FreeLLMAPI base: {base}")
    ok = await health_check(base, s.freellm_api_key)
    print(f"/models health: {'OK' if ok else 'UNREACHABLE'}")
    if not ok:
        print("Server not reachable — start FreeLLMAPI locally and retry.")
        return

    gw = build_real_gateway(s)
    result = await gw.request(agent="news", task=LLMTask.EVENT_EXTRACTION,
                              payload={"instruction": "Extract material market events.",
                                       "sources": SOURCES})
    print(f"routed via: {gw.provider.last_routed_via}")
    print(f"gateway state: {result.state.value}   selected_route: "
          f"{result.run.selected_route if result.run else '-'}")
    if result.ok:
        data = result.data or {}
        print(f"events: {[e.get('type') for e in data.get('event_candidates', [])]}")
        print(f"claims: {len(data.get('claims', []))}  citations: {data.get('citations')}")
    else:
        print(f"degraded (nothing fabricated): {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
