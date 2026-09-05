# Indian Equity AI Decision-Support System — Phase-Wise Build Plan

> Governing build order and delivery gates. Pairs with the engineering spec
> ([`INDIAN_EQUITY_AI_MASTER_SPEC.md`](INDIAN_EQUITY_AI_MASTER_SPEC.md)) and the
> performance directive ([`../CLAUDE.md`](../CLAUDE.md)). Where this plan and the
> master spec differ on sequencing or structure, **this plan wins** — it is the
> newer, execution-ordered intent.

## 1. Product boundary and non-negotiables

Build a research and decision-support system for the broad Indian listed-equity universe (NSE and BSE), including liquid small- and mid-cap names. It continuously discovers possible opportunities from market activity, exchange/company disclosures, news, and structured financial data; researches them; ranks them with quantitative evidence; and presents a human-readable recommendation.

**The user always manually executes trades.** The application must not place orders, transfer funds, connect to broker execution, or circumvent that control.

Permitted decisions: `BUY`, `SELL`, `HOLD`, `ROTATE`, `NO_TRADE`. `NO_TRADE` is a valid and often preferred result.

### Honest performance policy

- A 90%+ precision rate is an **aspirational, selective-set research target**, not a promise and not a system-wide prediction claim.
- +10% monthly is an **aspirational evaluation hypothesis**, not a design requirement or guaranteed outcome.
- No-loss claims are prohibited. Losses, uncertainty, drawdowns, and failed signals must be plainly shown.
- All results must include realistic costs: brokerage assumptions, statutory/exchange charges, taxes where applicable, slippage, spreads, liquidity limits, and corporate actions.
- The LLM never invents probability, P&L, sources, or confidence. Probabilities must come from calibrated quantitative models and must display sample size and date range.
- A backtest, validation set, untouched test set, paper-trading record, and real-money user journal are separate datasets and separate labels in the UI.

## 2. Critical build order

```text
Data integrity → point-in-time features → simple baseline signal → honest backtest
→ paper/shadow ledger → risk & sizing → discovery + event extraction
→ ranking/calibration → portfolio rotation → alerts/API → terminal/chat polish
```

Do not build a polished TradingView clone until a reproducible baseline strategy has a credible out-of-sample and paper-trading record. A beautiful dashboard around unvalidated signals is not a product.

## 3. Suggested architecture and stack

| Layer | Recommended starting choice | Why |
|---|---|---|
| Monorepo | `pnpm` + Turborepo | One frontend, API, workers, shared contracts |
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, TradingView Lightweight Charts | Fast terminal/chat interface without overbuilding charts |
| API | FastAPI (Python) | Best fit for quant, ML, and data workflows |
| Workers | Celery or Dramatiq + Redis; scheduled jobs | Reliable ingestion, retries, and research pipelines |
| Operational DB | PostgreSQL + TimescaleDB | Transactions, time-series quotes, auditability |
| Object store | S3-compatible/MinIO | Raw filings, news snapshots, model artifacts |
| Analytics | Parquet + DuckDB; later ClickHouse if needed | Cheap reproducible research and fast scans |
| Feature/model | Python, Polars, scikit-learn, LightGBM/XGBoost, MLflow | Strong tabular baseline and experiment tracking |
| Orchestration | Prefect (or simple scheduled workers initially) | Observable, replayable pipelines |
| Messaging | Redis streams initially; Kafka only if volume proves it necessary | Avoid infrastructure burden in MVP |
| Observability | OpenTelemetry, Sentry, Prometheus/Grafana | Data freshness, job, model, and UI observability |
| LLM gateway | Internal provider adapter over FreeLLMAPI | Keep prompts/providers replaceable and fully logged |

Use official/licensed data sources where possible. Record source terms, access date, raw payload hash, and license/attribution restrictions. Do not rely on brittle, prohibited scraping for production market data.

## 4. Core data contracts

All timestamps use UTC internally plus `Asia/Kolkata` market-session fields. Use decimal types for money, immutable IDs, schema versions, and source provenance.

### 4.1 Essential entities

| Entity | Required fields |
|---|---|
| `instrument` | `instrument_id`, NSE/BSE identifiers, ISIN, symbol, name, sector, listing dates, status |
| `bar` | `instrument_id`, `timeframe`, `ts`, OHLCV, turnover, source, ingested_at, correction_version |
| `corporate_action` | instrument, action type, ex/record dates, ratio/value, source document |
| `source_document` | `document_id`, source URL, publisher, published_at, fetched_at, content hash, raw object URI, rights metadata |
| `event` | event ID, instrument IDs, type, event time, discovered time, materiality, novelty, extraction version, evidence IDs |
| `feature_snapshot` | instrument, `as_of_ts`, feature-set version, named values, data-quality flags |
| `signal` | signal ID, instrument, as-of time, horizon, target/stop rule, model version, score, calibrated probability, expected return, evidence IDs |
| `recommendation` | recommendation ID, action, entry range, target, invalidation, expiry, status, risk verdict, explanation snapshot |
| `paper_order` / `paper_fill` | recommended/assumed time, price, quantity, costs, fill assumptions, immutable audit trail |
| `portfolio_snapshot` | cash, holdings, average cost, exposure, sector weights, value, source/user-entered time |
| `evaluation_outcome` | signal ID, fixed success rule, realization window, gross/net return, MFE/MAE, target/stop first-hit result |
| `llm_run` | agent, prompt/template version, FreeLLMAPI route/model, input document IDs, structured output, validator result, latency, cost/tokens if available |

### 4.2 Agent response contract

Every agent returns schema-validated JSON, never free-form instructions:

```json
{
  "schema_version": "1.0",
  "instrument_ids": ["INE..."],
  "as_of_ts": "2026-09-05T09:45:00Z",
  "claims": [{"claim": "Order awarded", "polarity": "positive", "evidence_ids": ["doc_123"], "confidence": 0.78}],
  "event_candidates": [{"type": "government_contract", "materiality": 0.72, "novelty": 0.85}],
  "unknowns": ["contract margin not disclosed"],
  "citations": ["doc_123"],
  "validation": {"source_grounded": true, "warnings": []}
}
```

`confidence` here measures extraction/evidence confidence, **not trade-win probability**. Enforce JSON Schema/Pydantic validation, citation existence, entity resolution, and source quotation checks before downstream use.

### 4.3 Recommendation contract

```json
{
  "recommendation_id": "rec_...",
  "action": "BUY|SELL|HOLD|ROTATE|NO_TRADE",
  "instrument_id": "...",
  "as_of_ts": "...",
  "entry": {"low": 410.0, "high": 415.0},
  "target": 445.0,
  "invalidation": 398.0,
  "max_holding_sessions": 5,
  "quantity": 5,
  "allocation": 2060.0,
  "calibrated_probability": 0.0,
  "expected_net_return": 0.0,
  "expected_downside": 0.0,
  "risk_reward": 0.0,
  "historical_sample_size": 0,
  "risk_verdict": "PASS|VETO|REVIEW",
  "evidence_ids": ["..."],
  "model_version": "...",
  "expires_at": "..."
}
```

The API must reject a recommendation if the target/stop/horizon, data timestamp, model version, costs, sample size, or source citations are missing.

## 5. Roles and responsibility boundaries

### LLM-assisted agents (FreeLLMAPI via the internal gateway)

1. **Discovery Agent** — turns market anomalies, exchange disclosures, and web/IR feeds into candidates.
2. **News/Event Agent** — extracts, deduplicates, timestamps, and cites catalysts.
3. **Fundamental Agent** — extracts reported financial facts and flags missing information.
4. **Sentiment Agent** — summarizes source-weighted sentiment; never treats social chatter as fact.
5. **Historical Analogue Agent** — retrieves similar *point-in-time* events and explains comparability.
6. **Bull Agent** — evidence-grounded upside thesis.
7. **Bear Agent** — evidence-grounded disconfirmation, governance, liquidity, and execution risks.
8. **Research Judge** — synthesizes claims and unknowns; cannot override quantitative risk gates.
9. **Chat Agent** — answers user questions only from retrieved, timestamped data and recommendation records.

### Deterministic/quantitative engines (final authority for numbers)

- **Market scanner:** price/volume, breadth, relative strength, volatility, gaps, liquidity.
- **Feature/ranking engine:** point-in-time features, model inference, calibration, expected value/ranking.
- **Event-study engine:** event windows, abnormal return versus benchmark/sector, historical outcome labels.
- **Risk engine:** liquidity/spread/circuit/volatility/manipulation flags, concentration/correlation/drawdown constraints; it can veto.
- **Portfolio engine:** sizing, allocation, exits, and rotation proposals based on user-entered holdings and constraints.
- **Evaluation engine:** backtests, walk-forward validation, paper fills, calibration, and immutable reporting.

## 6. Phases

### Phase 0 — Charter, compliance, and data feasibility (2–4 days)

**Prerequisites:** none.

**Build/deliverables:**

- Product charter, approved universe definition, strategy horizons (start with end-of-day swing, e.g. 3–10 sessions), and explicit `NO_TRADE` behavior.
- Data-source inventory: exchange/reference/master data, OHLCV, corporate actions, filings, financials, news, macro/sector benchmarks. For each, document rights, latency, historical depth, adjustment method, and fallback.
- Fixed outcome definitions before modeling: target-first vs stop-first; end-of-horizon net return; execution timing; costs/slippage; treatment of gaps, circuits, suspensions, delistings, and corporate actions.
- Risk policy: maximum position/sector/correlation concentration, minimum turnover, max spread, max portfolio drawdown response, and small-cap exclusion/review rules.
- Security/operations: secrets manager, provider keys only server-side, audit log, retention policy, disclaimer/review language.

**Acceptance:** a reviewer can reproduce one symbol's price and corporate-action history from raw source to adjusted series; every performance metric has a written definition; no broker execution scope exists.

### Phase 1 — Two-day MVP: validated baseline, not terminal polish (days 1–2)

**Prerequisites:** one reliable EOD OHLCV source, liquid initial universe (e.g. Nifty 500 plus an explicitly liquidity-qualified extension), Python/Postgres local environment.

**Build only this:**

1. Instrument master and EOD ingestion with raw snapshots, idempotency, freshness checks, and adjusted/unadjusted series.
2. A simple deterministic scanner: momentum/relative-strength + abnormal volume + liquidity filter.
3. One explicit baseline strategy with entry at next available session, fixed stop/target/horizon, costs, and no look-ahead.
4. Event-time-safe vectorized backtest plus walk-forward split and a short report.
5. Minimal API/CLI endpoint producing ranked candidates and `NO_TRADE` when no candidate meets gates.
6. Append-only paper-signal ledger (no broker connection), including model/data versions.
7. Tiny web page or table: date, ranked candidates, price chart, entry/stop/target, and warnings. No chat, multi-agent debate, or custom chart workspace yet.

**MVP acceptance:**

- Re-running the same input/date gives the same candidates and report.
- A deliberate future-data mutation fails a leakage test.
- Backtest report shows number of trades, net return, win rate, average/median return, profit factor, max drawdown, turnover, costs, exposure, and confidence intervals where meaningful.
- Results are segmented by train/validation/untouched test and do not claim production readiness.
- At least one clear `NO_TRADE` day is represented correctly.

**MVP explicitly does not include:** real-time quotes, web crawling at scale, full LLM research floor, model optimization, broker APIs, auto execution, or a TradingView-like layout.

### Phase 2 — Reliable data platform and research reproducibility (weeks 1–2)

**Prerequisites:** Phase 1 reproducibility and source contracts.

**Deliverables:**

- Market/benchmark/sector/index ingestion, corporate actions, trading calendars, universe membership history, and delisting/suspension handling.
- Data quality suite: missing bars, duplicates, stale source, outliers, split adjustments, timezone/session tests.
- Raw document store for filings/announcements/news with content hash and immutable provenance.
- Feature store with point-in-time `as_of_ts`; dataset builder that joins only data available at that time.
- Prefect/worker schedules, retries, dead-letter handling, data freshness dashboard.
- Research notebook templates and experiment registry (data snapshot + feature version + config + seed + model artifact).

**Acceptance:** the system can rebuild any dated training/backtest dataset from source snapshots; a simulated correction creates a new version without overwriting the prior audit record; quality failures quarantine data rather than silently changing signals.

### Phase 3 — Discovery, filings, and structured LLM extraction (weeks 2–4)

**Prerequisites:** Phase 2 source provenance and document pipeline.

**Deliverables:**

- Candidate intake from abnormal market activity, official exchange/company disclosures first, then licensed/allowed news and web intelligence.
- Entity resolution between names, tickers, ISINs, subsidiaries, and parent companies; document/event deduplication.
- FreeLLMAPI gateway: typed calls, rate limits, retries, circuit breaker, provider/model routing, prompt/template versioning, and complete `llm_run` audit records.
- News/Event and Fundamental agents with strict structured output; retrieval of cited source sections; human-review queue for low confidence/conflicts.
- Event taxonomy: orders/contracts, earnings/guidance, promoter holdings, M&A, capacity, approvals/regulation, management/governance, policy/commodity/sector shock.
- Discovery scoring: source reliability, novelty, materiality, event age, price-already-reacted, liquidity, and data quality.

**Acceptance:** a held-out, manually labeled sample meets agreed extraction precision/recall thresholds by event type; every displayed event links to raw evidence; unsupported LLM claims cannot enter the feature store.

### Phase 4 — Quant, event studies, and honest ranking (weeks 4–7)

**Prerequisites:** Phase 2 datasets and Phase 3 labeled events.

**Deliverables:**

- Event-study module with market/sector-adjusted abnormal returns across 1D/3D/5D/10D horizons.
- Baselines before complexity: rules, logistic regression, then LightGBM/XGBoost ranking/classification. Compare against simple momentum and random/universe benchmarks.
- Labels fixed ahead of training: positive net return threshold, target-first, stop-first, and horizon return. Store label version.
- Walk-forward cross-validation, purged/embargoed splits where samples overlap, survivorship-bias controls, and point-in-time universe membership.
- Calibration (isotonic/Platt as appropriate), reliability curves, Brier score, precision/recall at coverage, expected value, and subgroup reporting.
- Model registry, approval state, reproducible inference bundle, drift monitoring plan.

**Acceptance:** the chosen model materially beats the predefined baseline on untouched periods after realistic costs, or it is rejected. Report intervals and cohort sizes. A high confidence band is only shown if calibration supports it; otherwise label it uncalibrated or suppress it.

### Phase 5 — Risk, portfolio, paper trading, and rotation (weeks 7–9)

**Prerequisites:** a versioned candidate/ranking system with a conservative model approval state.

**Deliverables:**

- Deterministic risk vetoes: tradability, turnover/spread, volatility, circuit risk, price-limit/gap risk, data quality, event uncertainty, manipulation heuristics, and stale signal expiry.
- Position-sizing engine: user capital, per-trade risk, stop distance, max allocation, liquidity caps, sector/correlation caps, cash reserve, and drawdown throttle.
- Portfolio optimizer/rotation recommender: compare hold vs sell/trim vs rotate using expected net value after costs, taxes supplied/configured by user, turnover, concentration, and risk constraints.
- Paper-trading simulator: next-bar/realistic fill rules, partial fills where relevant, costs/slippage, immutable signal-to-outcome ledger.
- Daily/weekly performance dashboard and paper-trading review workflow. User can import/manual-enter holdings; no trade placement functionality.

**Acceptance:** every `BUY`/`ROTATE` recommendation has an entry, stop/invalidation, horizon, quantity, allocation, costs, expiry, and veto record. Reconstructing a paper portfolio from its ledger matches its reported NAV. The system is observed in shadow/paper mode for at least 30/60/90 days appropriate to frequency before any real-money-use recommendation.

### Phase 6 — User terminal, alerts, and grounded chat (weeks 9–12)

**Prerequisites:** stable API contracts and a paper-trading record.

**Deliverables:**

- TradingView-like terminal: watchlists, broad-market scanner, candidate table, chart overlays, evidence timeline, research tabs, risk panel, portfolio/rotation view, and performance pages.
- Recommendation card: action, entry/target/invalidation/horizon, quantitative probability and sample, net expected return, risk verdict, bull/bear evidence, source links, and "what invalidates this thesis."
- Grounded chat with retrieval limited to stored data/evidence and a timestamped answer trail. It can explain data and workflows, not invent trades or bypass risk gates.
- Alerts for new high-ranked approved candidates, risk/stop/expiry conditions, data staleness, and material follow-up disclosures. Include dedupe, quiet hours, and alert audit log.
- Role-based access, user preferences, exports, and feedback labels (useful/not useful, manually executed/not executed) separated from realized outcomes.

**Acceptance:** every number visible in UI traces to a timestamped calculation and data version; alerts are deduplicated and testable; UI cannot represent a vetoed candidate as a recommendation; there is no order-submit button or hidden execution endpoint.

### Phase 7 — Production hardening and controlled release (ongoing)

**Prerequisites:** completed paper-trading gate, documented performance results, and operational review.

**Deliverables:**

- CI/CD, migrations, environment separation, backups/restore drills, secret rotation, rate limiting, incident runbooks, and dependency/security scans.
- Full observability: feed freshness, job failures, queue latency, LLM structured-output failure rate, model/data drift, recommendation coverage, risk-veto rate, alert delivery.
- Model governance: champion/challenger, rollback switch, model cards, quarterly recalibration/review, and reproducibility tests.
- Controlled user release with explicit risk disclosure, manual execution only, and a feedback/issue loop.

**Acceptance:** recovery from a failed feed/provider is tested; degraded mode labels stale/partial data and suppresses recommendations when necessary; a model can be rolled back without a data migration; audit export reconstructs any recommendation end to end.

## 7. Backtesting and evaluation protocol

1. Freeze the decision rule, outcome definition, slippage/cost assumptions, and universe before a run.
2. Build data point-in-time, including delisted names and historical index/universe membership.
3. Use chronological train → validation → final untouched test; tune only on train/validation.
4. Use walk-forward testing and report by market regime, liquidity bucket, market cap, sector, event type, and time horizon.
5. Record coverage: what fraction of opportunities does the system select? Precision without coverage is incomplete.
6. Report gross and net outcomes, confidence intervals/bootstrap where appropriate, maximum drawdown, time-to-recovery, tail loss, turnover, capacity/liquidity, and calibration.
7. Run shadow/paper mode before trusting real-world usability. Compare predicted versus realized outcomes under recorded fill assumptions.
8. Never quietly replace a poor result. Failed cohorts, model versions, and paper outcomes remain visible in the audit record.

## 8. Recommended repository structure

```text
indian-equity-ai/
├─ apps/
│  ├─ web/                         # Next.js terminal and chat
│  └─ api/                         # FastAPI request layer
├─ services/
│  ├─ ingestion/                   # source adapters, calendars, normalization
│  ├─ research-workers/            # discovery, documents, LLM agent jobs
│  ├─ quant/                       # features, models, ranking, calibration
│  ├─ risk-portfolio/              # vetoes, sizing, rotation
│  └─ evaluation/                  # backtest and paper ledger
├─ packages/
│  ├─ contracts/                   # JSON Schema/OpenAPI/generated clients
│  ├─ ui/                          # shared components
│  └─ config/                      # lint/types/tooling config
├─ data-contracts/                 # schema definitions and migrations
├─ infra/                          # Docker, IaC, monitoring, deployments
├─ notebooks/                      # read-only reproducible exploration
├─ tests/
│  ├─ fixtures/                    # point-in-time market/doc fixtures
│  ├─ integration/
│  └─ e2e/
├─ docs/
│  ├─ data-sources.md
│  ├─ outcome-definitions.md
│  ├─ risk-policy.md
│  ├─ model-cards/
│  └─ runbooks/
└─ README.md
```

Keep raw source data and generated model artifacts outside Git. Version schemas, configurations, and metadata in Git; use migrations for database changes.

## 9. Test strategy

| Area | Required tests |
|---|---|
| Ingestion | idempotency, schema drift, timezone/session boundaries, corrections, stale/missing data |
| Point-in-time integrity | no feature can read a document/bar later than `as_of_ts`; intentionally injected future data must fail |
| Corporate actions | split/dividend adjustment and delisted/suspended instrument cases |
| Agents | JSON-schema validation, citation existence, entity resolution, adversarial unsupported-claim rejection |
| Quant | deterministic seed/replay, temporal split, calibration/reliability, benchmark comparison |
| Backtest | next-bar execution, gap/stop ordering, cost/slippage, no-trade and illiquid cases |
| Risk/portfolio | veto precedence, max loss/position, sector/correlation caps, rotation turnover/costs |
| API/UI | contract tests, authorization, recommendation completeness, source traceability, no execution endpoint |
| Operations | retries, provider outage, dead-letter/replay, backup restore, alert dedupe |

## 10. Delivery gates and decisions

| Gate | Decision |
|---|---|
| End of Phase 1 | Is the data and baseline reproducible? If no, fix it before collecting features or UI work. |
| End of Phase 3 | Is LLM extraction demonstrably grounded and useful? If no, keep deterministic source parsing and simplify. |
| End of Phase 4 | Does ranking beat the baseline on untouched data after costs? If no, reject/iterate; do not market it as intelligent. |
| End of Phase 5 | Does paper trading behave consistently with the simulated assumptions? If no, correct fills, constraints, or model before expanding. |
| Production | Is data freshness, auditability, rollback, and manual-only execution proven? If no, keep it in research/paper mode. |

## 11. Definition of a production-quality recommendation

It is not merely a bullish LLM paragraph. It is a timestamped, expiring, auditable record with:

- exact instrument and current data timestamp;
- action and clear `NO_TRADE` alternative where applicable;
- entry range, invalidation/stop, target, holding horizon, and position size;
- expected *net* return/downside, risk-reward, and calibrated probability with sample size;
- risk/portfolio verdict and all veto/warning flags;
- source-linked evidence plus explicit uncertainties and invalidation conditions;
- data, feature, model, prompt/agent, and policy versions;
- eventual realized paper/live-journal outcome under a fixed measurement rule.

The aim is disciplined, evidence-backed selection — not an illusion of certainty.
