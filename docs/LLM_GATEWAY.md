# LLM Gateway — Mandatory Routing Architecture

> **Hard rule.** Every LLM call in this system goes through one internal
> `LLMGateway` service. **No agent, API route, worker, or frontend component may
> call FreeLLMAPI (or any LLM provider) directly.** There is exactly one code path
> to a model, and it is auditable, validated, and replaceable.

## 1. Why

- **Replaceable providers/models** — prompts and agents never name a model; routing is configuration.
- **Every call is auditable** — one immutable `llm_run` record per call.
- **Nothing unvalidated flows downstream** — schema + citation validation gate every result.
- **Injection containment** — untrusted source text can never become instructions or gain tool access.
- **Clean failure** — if LLM research is unavailable, deterministic results survive and LLM-dependent recommendations are suppressed, never fabricated.

## 2. Request flow

```text
Agent / worker
   │  LLMGateway.request(task, payload, policy)
   ▼
LLMGateway
   ├─ resolve task policy (versioned)
   ├─ select route/model from capability registry (deterministic rules)
   ├─ enforce rate/concurrency/timeout/token/cost limits
   ├─ sanitize untrusted source content (injection defense)
   ├─ call FreeLLMAPI route
   ├─ validate structured JSON (Pydantic / JSON Schema)
   ├─ validate citations (every claim → real evidence id)
   ├─ retry / fallback to next approved route when eligible
   ├─ write immutable llm_run audit record
   └─ return VALIDATED result  OR  explicit FAILURE state
        (never partial, never unvalidated, never fabricated)
```

## 3. Versioned task policies

One policy per task, each versioned. Initial task set:

`event_extraction` · `entity_resolution` · `document_summary` · `bull_case` ·
`bear_case` · `research_synthesis` · `chat_answer`

Each policy configures:

| Field | Purpose |
|---|---|
| `version` | Immutable policy version, logged in every `llm_run` |
| `allowed_routes` | Ordered list of permitted FreeLLMAPI models/routes |
| `timeout_s` | Per-call timeout |
| `token_budget` | Max input+output tokens |
| `temperature` | Sampling temperature |
| `response_schema` | Required JSON schema for the structured output |
| `retry` | Max retries + which failures are retry-eligible |
| `fallback_order` | Approved fallback routes if the primary fails |
| `max_cost` | Hard per-call cost ceiling |
| `data_classification` | Max data sensitivity this task may send |
| `cacheable` | Whether content-hash caching is allowed (deterministic tasks only) |

**Deterministic starting routing rules:**

- Cheap/fast models → `event_extraction`, `entity_resolution`, `document_summary`.
- Stronger reasoning models → `bull_case`, `bear_case`, `research_synthesis`, judge/synthesis tasks.
- `chat_answer` → mid-tier, retrieval-grounded, strict "answer only from provided evidence."

Routing is empirical later (measure per-task model performance), but it always comes from configuration — **never hard-coded in a prompt or agent.**

## 4. Model capability registry

Configurable registry describing each route/model:

```text
route/model name
provider
context window support
structured-output reliability   (measured)
latency expectations
availability / health status
permitted data classification
cost profile
```

The gateway picks a route by matching the policy's requirements against the
registry (capability + health + cost), not by a name written in agent code.

## 5. Resilience

- Rate limits + concurrency caps (global and per-route)
- Per-call timeouts
- Bounded retries (only for retry-eligible failures)
- Circuit breakers per route
- Provider health checks feeding the registry
- Approved fallback routes only — never an arbitrary substitute

## 6. Validation (every response, before any downstream use)

1. **Structured-output validation** — Pydantic / JSON Schema. Malformed → retry, then fallback, then failure.
2. **Citation validation** — every claim references a real evidence/source id present in the input set. Uncited or invented citations → reject.
3. **Entity/source-grounding checks** — outputs must resolve to known instruments and quoted source sections.

A response that fails validation **cannot** enter the feature store, ranking, or a recommendation.

## 7. Untrusted content & prompt-injection defense

Filings, web pages, news, and user-provided content are **untrusted data, not instructions.**

- Wrap/segregate source content so it is treated as data (clear delimiters, role separation, no instruction execution).
- Strip/neutralize instruction-like payloads from sources before prompting.
- System/task instructions come only from the versioned policy — never from source text.
- Source content can never trigger tool calls, change routing, or alter system instructions.

## 8. Caching

- Content-hash cache **only** for safe, deterministic research tasks (e.g. `document_summary`, `event_extraction` on a fixed document hash).
- **Never** cache time-sensitive trading decisions beyond their expiry.
- Cache key includes: task policy version + model route + input content hash. A policy or route change invalidates the entry.

## 9. Immutable `llm_run` audit record

Every call logs, append-only:

```text
agent
task policy + version
selected route/model + all attempted routes/models
prompt / template version
input source IDs + content hashes
raw result location + validated result location
validation failures (schema / citation / grounding)
latency
retry count
returned token / cost data
final state: VALIDATED | FAILED
```

## 10. Degraded mode

If FreeLLMAPI or **all** approved routes fail:

- Mark **LLM research = unavailable**.
- **Preserve** deterministic market/scanner/risk/quant results.
- **Suppress** any recommendation that requires the missing LLM research.
- **Never fabricate** analysis, citations, or confidence to fill the gap.
- Surface the degraded state in the UI (greyscale "LLM RESEARCH UNAVAILABLE" tag).

## 11. Responsibility boundary (do not blur)

| LLM / gateway may produce | Deterministic engines own (LLM must NOT) |
|---|---|
| reasoning, extraction, summarization | calibrated probabilities |
| evidence synthesis, bull/bear theses | expected return, expected downside |
| event/entity classification | risk vetoes |
| grounded chat answers | position sizing |
| | P&L and final backtest evaluation |

The gateway routes reasoning. **Numbers are never an LLM output.**

## 12. Required tests (land with the gateway build — Phase 3)

- **Route selection** — policy + registry produce the expected route; deterministic rules honored.
- **Provider failure / fallback** — primary down → approved fallback → success; all down → degraded mode.
- **Schema failure** — malformed JSON rejected, retried, then failed cleanly (never passed downstream).
- **Citation failure** — invented/missing citations rejected.
- **Prompt-injection resistance** — adversarial source text cannot change instructions, routing, or trigger tools.
- **Caching behavior** — deterministic tasks cache by content hash; time-sensitive results never cached past expiry; policy/route change invalidates.
- **Degraded mode** — LLM-dependent recommendations suppressed, deterministic results preserved, nothing fabricated.

## 13. Build sequencing

Per [`PHASE_WISE_BUILD_PLAN.md`](PHASE_WISE_BUILD_PLAN.md), the gateway is **implemented in
Phase 3**. It is documented and architecturally reserved now so that, from the first
line of agent code, there is no legitimate path that calls a provider directly.
Phase 1 (data spine + deterministic baseline) uses **no LLM** and therefore does not
touch the gateway.
