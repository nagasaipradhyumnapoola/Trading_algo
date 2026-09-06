# Runbook: LLM provider outage

**Symptom:** rising `llm_failure_rate` in `/metrics`; `llm_run` records in
`FAILED` state; grounded chat and extraction return refusals.

**Automatic behavior (already enforced):**
- The `LLMGateway` retries, then falls back across approved routes, then trips a
  circuit breaker and returns an explicit **degraded FAILED** state.
- Deterministic results (scanner, features, risk, sizing, calibrated probability,
  P&L) are **unaffected** — they never depend on the LLM.
- Grounded chat and News/Fundamental extraction refuse rather than invent.

**Steps:**
1. Confirm via `GET /metrics` (`derived.llm_failure_rate`) and the `llm_run` audit log.
2. Check FreeLLMAPI status and the capability registry health flags.
3. Update routing config / registry if a route must be disabled; the gateway picks
   the next approved route — no code change or redeploy of agents needed.
4. Recommendations continue (deterministic). Only LLM-dependent research is paused;
   the UI labels it unavailable.
5. When routes recover, clear the breaker (restart the worker) and confirm a test
   `POST /chat` returns `grounded: true`.

**Never:** hard-code a model, bypass the gateway, or synthesize an "answer" while the
provider is down.
