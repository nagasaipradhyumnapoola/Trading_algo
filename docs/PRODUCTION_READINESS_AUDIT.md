# Production Readiness Audit

**Date:** 2026-09-06
**Method:** Direct source inspection — `grep`/read across all modules, tests, and config.
README phase labels were **not** trusted; every claim below cites `file:line` evidence.
**Scope:** entire `Indian Alpha` repository at the current `main`.

## Headline verdict

**NOT ready for real-money use. Not ready for any real-data use.**

The repository is a **well-tested deterministic research engine running entirely on
synthetic data with a mock LLM.** 155 tests pass, but every test exercises in-memory
objects, a seeded synthetic universe, or a `MockProvider`. There is:

- **no configuration system** — nothing in the code reads `.env` (grep for
  `os.environ|getenv|BaseSettings|DATABASE_URL|create_engine|sqlalchemy|psycopg|httpx|requests|aiohttp`
  returns **zero matches** across all `*.py`);
- **no database** — "records" are Pydantic models kept in Python lists with optional
  JSONL append; no Postgres, no migrations, no persistence guarantees;
- **no real data feed** — the only market-data source is `CsvEodAdapter` + a seeded
  synthetic generator (`services/ingestion/sample.py`);
- **no real LLM** — `providers.py` contains only `MockProvider`/`AsyncMockProvider`;
- **7 of 9 agents are `NotImplementedError`**;
- **EOD only** — `Timeframe` has a single value `EOD` (`services/ingestion/models.py:23`);
  no intraday framework;
- **no auth** on the API; `TerminalService()` trains a model and fabricates
  recommendations at import time (`apps/api/app/main.py:27`).

What IS genuinely solid: the deterministic quant/risk/evaluation core and the LLM
**gateway machinery** (validation, citation-checking, injection defense, fallback,
degraded mode) — all real and tested, just never connected to a real provider or feed.

## Legend

| Tag | Meaning |
|---|---|
| ✅ **TESTED** | Implemented and covered by passing tests (against synthetic/in-memory inputs) |
| 🟡 **SAMPLE-ONLY** | Implemented but only ever run on synthetic/sample/mock data |
| ⛔ **UNIMPLEMENTED** | Placeholder / `NotImplementedError` / absent |
| ⚠️ **UNSAFE** | Present but incomplete or unsafe for real-data/real-money use |

---

## A. Subsystem inventory

### A1. Configuration, runtime, security

| Component | Status | Evidence | Gap for real use | Production gate |
|---|---|---|---|---|
| Settings / env loading | ✅ TESTED (Phase A) | `services/config/settings.py`, `test_config.py` | Typed Settings + validation + presence-only startup report | Provide real feed/DB values |
| `.env.example` | ✅ TESTED (Phase A) | `.env.example` | Blank-value contract, no fake URLs/creds | — |
| `APP_MODE` demo/real split | ✅ TESTED (Phase A) | `settings.py` `_enforce_mode`, `test_config.py` | Real mode fails fast without feeds/DB | — |
| DEMO/REAL indicator | ✅ TESTED (Phase A) | `apps/api/app/main.py` X-Data-Mode + `data_mode`; UI tag | Present on every response + UI | — |
| API authentication / RBAC | ⛔ UNIMPLEMENTED | grep: no `Depends`/`api_key`/`Authorization` in `apps/api/app` | Open, unauthenticated endpoints | Auth on all non-public routes; RBAC if multi-user |
| Import-time side effects | ✅ TESTED (Phase A) | `apps/api/app/main.py` lazy `get_terminal()` | Demo-only lazy build; real mode 503, no fabrication at import | — |
| Secret handling | 🟡 SAMPLE-ONLY | `startup_report()` presence-only | Keys in `.env`; no secrets manager | Secrets manager in deployment |

### A2. Data ingestion & evidence

| Component | Status | Evidence | Gap | Production gate |
|---|---|---|---|---|
| Instrument master | 🟡 SAMPLE-ONLY | `services/ingestion/instruments.py`, CSV loader | Loads from CSV only; no real universe/membership feed | Provider adapter + historical membership/delistings |
| EOD OHLCV ingestion | 🟡 SAMPLE-ONLY | `adapters.py` `CsvEodAdapter`, `sample.py` | CSV/synthetic only; no licensed feed | Real EOD provider behind `SourceAdapter` |
| Intraday OHLCV | ⛔ UNIMPLEMENTED | `Timeframe.EOD` only (`models.py:23`) | No 1/5/15-min bars, no live feed | Intraday bars + near-real-time provider |
| Bar repository | ✅ TESTED | `repository.py`, `test_ingestion.py` | In-memory only; point-in-time `as_of` guard works | DB-backed store + parquet research layer |
| Corporate actions / adjust | ✅ TESTED | `corporate_actions.py`, `test_corporate_actions.py` | Split/bonus/dividend back-adjust; not fed real actions | Real corporate-action feed |
| Trading calendar | 🟡 SAMPLE-ONLY | `calendar.py`, derived from bars | No real NSE holiday/session calendar, no IST session states | Official calendar + pre-open/auction/circuit states |
| Universe membership (PIT) | ✅ TESTED | `universe.py`, `test_calendar_universe.py` | Logic present; no real membership history loaded | Real membership history |
| Data-quality suite | ✅ TESTED | `quality.py`, `test_quality.py` | Quarantine logic present; run on synthetic | Wire to real feeds + freshness/staleness gates |
| Raw document store | ✅ TESTED | `document_store.py`, `test_document_store.py` | Content-hash + provenance; JSONL/in-memory, not DB | DB/object-store persistence |
| Parquet store | ✅ TESTED | `parquet_store.py`, `test_persistence.py` | Research persistence works | Wire into pipeline |
| Filings / news / web adapters | ⛔ UNIMPLEMENTED | no HTTP client anywhere | No NSE/BSE filings, news, or web-search adapters | Licensed/permitted provider adapters + rights metadata |

### A3. Quant & ML

| Component | Status | Evidence | Gap | Production gate |
|---|---|---|---|---|
| Market features (EOD) | ✅ TESTED | `features.py`, tests | Deterministic; EOD only | Intraday feature set (VWAP, ORB, rel-vol, breadth) |
| Scanner | ✅ TESTED | `scanner.py`, `test_scanner.py` | EOD momentum/vol/liquidity; synthetic | Run on real universe; intraday scanner |
| Event study (AR/CAR) | ✅ TESTED | `event_study.py`, tests | Synthetic; leave-one-out benchmark | Real events + sector/index benchmark |
| Labels (fixed, versioned) | ✅ TESTED | `labels.py`, `test_labels.py` | EOD next-open rule only | Separate intraday/1-day/swing label sets |
| ML baseline (logistic) | ✅ TESTED | `ml.py`, `test_ml.py` | sklearn logistic + base-rate/momentum; LightGBM/XGBoost absent | Per-horizon models; real features |
| Calibration | ✅ TESTED | `calibration.py`, `test_calibration.py` | isotonic/Platt/reliability/Brier | Validated on real OOS before display |
| Walk-forward CV (purged) | ✅ TESTED | `cv.py`, `test_cv.py` | Purge+embargo correct | Apply to real datasets |
| Model registry + rollback | ✅ TESTED | `model_registry.py`, `test_model_registry.py` | Champion/challenger + rollback; in-memory | DB-backed registry |

### A4. LLM gateway & agents

| Component | Status | Evidence | Gap | Production gate |
|---|---|---|---|---|
| Gateway pipeline | ✅ TESTED | `gateway.py`, `test_llm_gateway.py` | Routing/validation/citation/fallback/breaker/cache/audit/degraded — all real | Exercise against a real provider |
| Provider adapter (FreeLLMAPI) | ⛔ UNIMPLEMENTED | `providers.py` — Mock only, no `httpx` | No real LLM call path | Real adapter verified against FreeLLMAPI docs |
| Injection defense | ✅ TESTED | `sanitize.py`, gateway tests | Source text never reaches system role | Re-verify with real content |
| News/Event agent | 🟡 SAMPLE-ONLY | `agents/news.py` | Implemented via gateway; only run on mock | Real provider + labeled precision/recall |
| Fundamental agent | 🟡 SAMPLE-ONLY | `agents/fundamental.py` | Same | Same |
| Discovery agent | ⛔ UNIMPLEMENTED | `agents/discovery.py:16` | `NotImplementedError` | Implement + wire scanner/web |
| Market agent | ⛔ UNIMPLEMENTED | `agents/market.py:16` | `NotImplementedError` | Implement (consume deterministic features) |
| Sentiment agent | ⛔ UNIMPLEMENTED | `agents/sentiment.py:17` | `NotImplementedError` | Implement dedup-aware sentiment |
| Historical agent | ⛔ UNIMPLEMENTED | `agents/historical.py:17` | `NotImplementedError` | PIT analogue retrieval |
| Bull agent | ⛔ UNIMPLEMENTED | `agents/bull.py:17` | `NotImplementedError` | Implement over shared evidence |
| Bear agent | ⛔ UNIMPLEMENTED | `agents/bear.py:17` | `NotImplementedError` | Implement over shared evidence |
| Judge agent | ⛔ UNIMPLEMENTED | `agents/judge.py:19` | `NotImplementedError` | Implement synthesis; cannot override risk |
| Orchestration (parallel floor) | ⛔ UNIMPLEMENTED | no `asyncio.gather` pipeline wiring agents | Agents not composed into a floor | Async orchestration per pipeline |
| Grounded chat | 🟡 SAMPLE-ONLY | `chat.py`, `test_chat.py` | Real logic; mock provider | Real provider |
| Extraction eval harness | ✅ TESTED | `extraction_eval.py`, tests | precision/recall by type | Feed real labeled sample |

### A5. Risk, portfolio, evaluation, paper

| Component | Status | Evidence | Gap | Production gate |
|---|---|---|---|---|
| Risk engine (vetoes) | ✅ TESTED | `risk_engine.py`, `test_risk_engine.py` | Deterministic veto/review; inputs synthetic | Feed real liquidity/spread/circuit/manip signals |
| Position sizing | ✅ TESTED | `sizing.py`, `test_sizing.py` | All caps + drawdown throttle | Real capital/holdings |
| Portfolio + rotation | 🟡 SAMPLE-ONLY | `portfolio.py`; sample holdings in `terminal.py` | Static sample holdings | User-entered/imported holdings + DB |
| Recommendation object | ✅ TESTED | `recommendation.py`, tests | Completeness gate enforced | Populate from real pipeline |
| Backtester (EOD) | ✅ TESTED | `backtest.py`, `test_evaluation.py` | Next-open, costs, leakage-safe; EOD only | Intraday backtester with fills/impact |
| Paper trading + NAV rebuild | ✅ TESTED | `paper_trading.py`, `test_paper_trading.py` | Immutable fills, NAV reconstructs | Live shadow run 60–90 days |
| Performance dashboard | ✅ TESTED | `performance.py`, tests | Win/PF/DD/Sharpe/Sortino + buckets | On real paper track |
| Paper ledger | ✅ TESTED | `paper_ledger.py` | Append-only; JSONL/in-memory | DB-backed |

### A6. API, UI, alerts, monitoring

| Component | Status | Evidence | Gap | Production gate |
|---|---|---|---|---|
| FastAPI endpoints | 🟡 SAMPLE-ONLY | `apps/api/app/main.py` | Serve sample terminal service | Real data mode; auth; no import-time build |
| Terminal UI | 🟡 SAMPLE-ONLY | `apps/web/index.html` | Chart/card/tabs/chat over sample | Real feeds; intraday controls; logbook tab |
| Alerts engine | ✅ TESTED | `alerts/engine.py`, `test_alerts.py` | Dedupe/quiet/audit; no channels | Telegram/email delivery adapters |
| Metrics / health / degraded | ✅ TESTED | `services/monitoring/*`, tests | Real logic; fed synthetic | Wire to real feed/LLM health |
| Rate limiting | ✅ TESTED | `ratelimit.py` | In-process fixed window | Redis-backed shared limit |
| Drift (PSI) | ✅ TESTED | `drift.py` | Correct | Wire reference vs live |
| Audit export | ✅ TESTED | `audit.py`, `test_hardening.py` | Reconstructable bundle | Pull from DB |
| Feedback store | ✅ TESTED | `feedback.py` | Separate from outcomes | DB-backed |
| Immutable DB logbook | 🟡 SAMPLE-ONLY (Phase B) | `services/persistence/*`, `migrations/`, `test_persistence_db.py` | All 13 record tables + append-only repos + Alembic migration, tested on SQLite; NOT yet wired into the pipeline or Postgres-deployed | Wire pipeline writes; Postgres; Logbook UI tab |

---

## B. Production gates (from the upgrade directive §9) — current status

| # | Gate | Status |
|---|---|---|
| 1 | Real feeds + real LLM routing, no sample fallback | ⛔ FAIL — no real feed, mock LLM only |
| 2 | All nine agents work or explicitly disabled; no placeholder | ⛔ FAIL — 7/9 `NotImplementedError` |
| 3 | Intraday + swing backtests pass leakage/cost/quality checks | ⛔ FAIL — no intraday; EOD backtest is leakage/cost-checked ✅ |
| 4 | Model beats fixed baseline on untouched data after costs, or rejected | 🟡 PARTIAL — mechanism exists + demoed on synthetic; not on real data |
| 5 | Calibration validated; no uncalibrated certainty shown | 🟡 PARTIAL — calibration engine + reliability exist; not validated on real OOS |
| 6 | 60–90 trading days paper/shadow per horizon | ⛔ FAIL — none |
| 7 | Paper fills reconciled against backtest assumptions | 🟡 PARTIAL — NAV reconstruction ✅; no live reconciliation |
| 8 | Portfolio/logbook/audit reconstruction for every recommendation | 🟡 PARTIAL — audit bundle ✅; no DB logbook |
| 9 | Risk policy + outcome definitions finalized, versioned, not draft | ⛔ FAIL — `docs/outcome-definitions.md`, `docs/risk-policy.md` marked DRAFT |
| 10 | No broker-write endpoints or hidden execution paths | ✅ PASS — none exist (verified: no order/execute endpoints, `BROKER_WRITE_ENABLED=false`) |

**Only gate 10 passes today.** The system must not be represented as usable for real
money, and this document supersedes the README's green phase checkmarks (those denote
"core logic built on sample data," not production readiness).

---

## C. Cross-cutting blockers (fix in this order)

1. **Configuration contract & runtime** — typed `Settings`, `APP_MODE` (demo/real),
   fail-fast, DEMO/REAL indicator, remove import-time `TerminalService()` build,
   rewrite `.env.example` with blank values. *(No behavior can be trusted until the
   app has a real vs demo boundary.)*
2. **Persistence & migrations** — Postgres/TimescaleDB schema for the record tables in
   directive §6; Alembic migrations; move JSONL/in-memory stores behind repositories.
3. **Real provider interfaces** — market data, filings, news/web, and the FreeLLMAPI
   adapter, each behind the existing `SourceAdapter`/`LLMProvider` protocols, with
   rights metadata and health checks.
4. **Real data + LLM routing** — wire adapters into ingestion and the gateway; prove
   degraded mode on real outages.
5. **Complete the 9 agents + orchestration** — remove all `NotImplementedError`; async
   research floor; agent-level evaluation.
6. **Intraday framework** — timeframes, IST calendar/session states, intraday features,
   separate strategies/labels/backtests/dashboards.
7. **Daily portfolio plan + immutable logbook** — DB-backed, append-only,
   reconstructable; Logbook UI tab.
8. **UI/terminal completion** — real-data terminal, intraday controls, logbook, health.
9. **Gates 1–9** — run the real-data, OOS, and 60–90-day paper gates honestly.

## D. Runtime note

Local runtime is **Python 3.14.4**, on which `duckdb`, `sqlalchemy`, `lightgbm`,
`xgboost`, `polars` have no wheels installed (grep confirms none imported). The
directive requires standardizing on **Python 3.12** (or another fully supported
version). CI already targets 3.12 (`.github/workflows/ci.yml`); local dev must match
before DB/LightGBM work begins.

---

## E. Upgrade progress log

| Phase | Commit | What changed | Audit items moved |
|---|---|---|---|
| Audit | `4187917` | This document + README honesty banner | — |
| A — config contract | `08dda3b` | Typed `Settings`, `APP_MODE` demo/real, fail-fast, `.env.example` blank contract, DEMO/REAL indicator, removed import-time terminal build | A1 config rows ⛔→✅ |
| B — persistence + migrations | _(this commit)_ | SQLAlchemy models for all 13 append-only record tables, append-only repositories, Alembic baseline migration; tested on SQLite (167 tests) | A6 DB logbook ⛔→🟡 |

**Still blocking real use:** API auth, real feeds + real FreeLLMAPI adapter, 7/9
agents, intraday, pipeline→DB wiring, and gates 1–9. Runtime for DB work is SQLite
locally / Postgres in deployment (SQLAlchemy 2.0 + Alembic verified on 3.14).

---

*This audit is updated at the end of every upgrade phase. A feature moves out of
SAMPLE-ONLY/UNIMPLEMENTED only when it runs on real data/providers and its gate passes.*
