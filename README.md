<div align="center">

# 🐂 Indian Alpha 🐻

### An AI research floor that hunts the *entire* Indian market for trades — before you even ask.

**Not a chatbot. Not a screener. Not an autopilot broker.**
An agentic, market-wide opportunity-discovery and quant decision-support engine for NSE/BSE.

`DISCOVER → RESEARCH → DEBATE → QUANTIFY → RISK-CHECK → RANK → RECOMMEND → OBSERVE → LEARN`

![Status](https://img.shields.io/badge/status-MVP%20complete%20·%20sample%20data-16c784)
![CI](https://github.com/nagasaipradhyumnapoola/Trading_algo/actions/workflows/ci.yml/badge.svg)
![Market](https://img.shields.io/badge/market-NSE%20%2F%20BSE-blue)
![Agents](https://img.shields.io/badge/AI%20agents-9-8A2BE2)
![LLM](https://img.shields.io/badge/LLM%20access-gateway%20only-6f42c1)
![Execution](https://img.shields.io/badge/broker%20writes-NONE-red)

</div>

---

## The pitch

Most tools wait for you to type a ticker. **This one doesn't.**

Indian Alpha continuously scans small-, mid- and large-caps across NSE/BSE, cross-referencing price/volume anomalies, live web search, breaking news, exchange filings, fundamentals, analyst commentary and social sentiment. When it smells an opportunity, it spins up a **nine-agent research floor** — including an adversarial **Bull vs. Bear** debate — grades the idea with **calibrated machine learning**, runs it past an **independent risk engine with veto power**, and hands you a single, evidence-backed recommendation.

Then it watches what actually happens and **grades itself**. Every prediction. Wins *and* losses.

> **You** stay the decision-maker. **You** execute every trade. The system never touches a broker.

---

## How it works — step by step

1. **Ingest** — instrument master + point-in-time market data, filings, news and fundamentals land in an immutable, timestamped store.
2. **Scan** — deterministic scanners sweep thousands of tickers for volume/volatility/breakout/relative-strength anomalies.
3. **Discover** — the Discovery Agent turns anomalies + disclosures + web search into *candidates the user never asked for*.
4. **Resolve & dedup** — entity resolution links names/tickers/ISINs; syndicated news collapses to one event, not fifty confirmations.
5. **Research (parallel)** — News, Market, Fundamental, Sentiment and Historical-Analogue agents investigate each candidate at once.
6. **Debate** — 🐂 Bull and 🐻 Bear build opposing cases from the **same** evidence set.
7. **Judge** — the Research Judge resolves the debate into a structured thesis. It **cannot** override risk.
8. **Quantify** — deterministic engines compute features, event-study returns, a **calibrated** probability and expected value. *Numbers never come from an LLM.*
9. **Risk-check** — the independent risk engine applies liquidity/spread/circuit/manipulation/concentration gates and can **VETO**.
10. **Rank & recommend** — survivors are scored and the top opportunities surface as `BUY / SELL / HOLD / ROTATE / NO_TRADE`, each with entry, target, invalidation, sizing and evidence.
11. **Observe & learn** — every recommendation is logged, later **graded** against a fixed rule, and attributed to the agents/models/regime responsible.

---

## Architecture

```text
      NSE / BSE  ·  Web  ·  News  ·  Filings  ·  Social
                         │
                         ▼
              INGEST → NORMALIZE (point-in-time)
                         │
                         ▼
        ACTIVE SCANNER  ── thousands of tickers
                         │
                         ▼
        ENTITY + EVENT ENGINE  ── narrows to hundreds
                         │
                         ▼
        ┌──────── AI RESEARCH FLOOR (9 agents) ────────┐
        │  News · Market · Fundamental · Sentiment      │
        │  Historical Analogue · Discovery              │
        │        (all LLM calls via LLMGateway)         │
        └───────────────────┬───────────────────────────┘
                             ▼
                   🐂 BULL  ⚔️  BEAR 🐻   (same evidence)
                             ▼
                     JUDGE  ── writes the thesis
                             ▼
              QUANT / ML  ── calibrated probability
                             ▼
              RISK ENGINE  ── PASS ✅ / VETO ⛔ (independent)
                             ▼
              PORTFOLIO  +  OPPORTUNITY RANKER
                             ▼
        BUY · SELL · HOLD · ROTATE · NO_TRADE  →  you
```

### Two brains, kept strictly apart

| 🧠 The LLM brain (9 agents) | 🔢 The math brain (deterministic) |
|---|---|
| Reads evidence, argues, judges | Calculates every number |
| Discovery · News · Market read · Fundamental · Sentiment · Historical · Bull · Bear · Judge | Features (RSI/ATR/VWAP/vol) · Event studies (AR/CAR) · LightGBM/XGBoost · **Calibration** · Ranking |
| *An LLM saying "94% confident" is worthless.* | *A model whose "90–95%" bucket hits 91.7% in reality is gold.* |

### One door to every LLM — the `LLMGateway`

**Every** LLM call goes through a single mandatory routing service. No agent, API route, worker or frontend component calls a provider directly.

```text
agent → LLMGateway.request(task, payload) → route select (config, not code)
      → structured-JSON + citation validation → retry/fallback → immutable llm_run
      → validated result OR explicit failure (degraded mode, never fabricated)
```

Model names are never hard-coded — routing comes from **versioned task policies** + a **capability registry**. If all routes fail, deterministic results survive and LLM-dependent recommendations are suppressed. Full contract: [`docs/LLM_GATEWAY.md`](docs/LLM_GATEWAY.md).

---

## The nine agents

| # | Agent | Job |
|---|-------|-----|
| 1 | **Discovery** | Find opportunities you never asked about; generate its own follow-up searches |
| 2 | **News / Event** | Classify the catalyst — material, novel, already priced in? |
| 3 | **Market** | Read price action, momentum, breakouts (numbers from code, not the LLM) |
| 4 | **Fundamental** | Is the catalyst *financially* meaningful to the business? |
| 5 | **Sentiment** | Dedup syndicated wires; sniff out pump-and-dump and bot activity |
| 6 | **Historical Analogue** | Find similar past setups and their real hit-rates |
| 7 | **Bull** 🐂 | Build the strongest evidence-based long case |
| 8 | **Bear** 🐻 | Build the strongest opposing case — equal access to evidence |
| 9 | **Judge** | Resolve the debate, rank evidence, recommend. **Cannot override Risk.** |

---

## Getting started

**Prerequisites:** Python 3.11+, Docker (for Postgres/TimescaleDB + Redis).

```bash
git clone https://github.com/nagasaipradhyumnapoola/Trading_algo.git
cd Trading_algo

# 1) Configure environment (never commit the real .env)
cp .env.example .env        # then fill in values

# 2) Bring up local datastores
docker compose up -d        # Postgres/TimescaleDB + Redis

# 3) Python env + dependencies
python -m venv .venv
# Windows: .venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# 4) Run the tests
pytest -q
```

The real `.env` is **git-ignored** and kept separate; only `.env.example` (placeholders) is tracked. All provider/API keys stay server-side.

### See it run (Phase 1, sample data)

```bash
# End-to-end pipeline: scan → baseline signal → backtest → paper ledger (honest, net of costs)
python scripts/pipeline_demo.py

# The dark terminal + JSON API on a sample universe
python -m uvicorn apps.api.app.main:app --port 8000
# then open http://localhost:8000  (or GET /opportunities/top?limit=5)

# Phase 2: point-in-time reproducibility (Parquet reload -> identical dataset)
python scripts/reproducibility_demo.py

# Phase 3: discover -> extract via the LLMGateway (mock provider) -> score -> rank
python scripts/discovery_demo.py

# Phase 4: PIT dataset -> purged walk-forward -> calibrated model vs baseline
python scripts/quant_demo.py

# Phase 5: candidate -> prob -> risk veto -> sizing -> rec -> rotation -> paper + NAV rebuild
python scripts/phase5_demo.py
```

**Run the terminal** (Phase 6 — dark TradingView-style UI at http://localhost:8000):

```bash
python -m uvicorn apps.api.app.main:app --port 8000
```

Phase 1 runs on a clearly-labelled **sample** universe so the scanner, `NO_TRADE`
path and net-of-cost backtest are exercisable end-to-end. A real EOD feed and
Postgres persistence land in Phase 2 behind the same interfaces.

---

## Build phases

The [phase-wise plan](docs/PHASE_WISE_BUILD_PLAN.md) is the authoritative build order. Data integrity and a validated baseline come **before** any terminal polish — a beautiful dashboard around unvalidated signals is not a product.

| Phase | Focus | State |
|---|---|---|
| **0** | Charter, data feasibility, fixed outcome definitions | 🟡 seeded ([outcome](docs/outcome-definitions.md) · [sources](docs/data-sources.md) · [risk](docs/risk-policy.md)) |
| **1** | Data spine + deterministic baseline + honest backtest + paper ledger | ✅ **MVP done (sample data)** — spine · scanner · baseline · backtest · ledger · API · terminal. Real EOD feed + Postgres persistence = Phase 2 |
| **2** | Reliable data platform + point-in-time feature store | ✅ **core done (sample data)** — corporate actions/adjustment · calendar · universe membership · data-quality · Parquet persistence · PIT feature store · doc store · job runner. Real feeds + Prefect = later |
| **3** | Discovery + filings + structured LLM extraction (the `LLMGateway` + agents) | ✅ **core done (mock LLM)** — gateway live · entity resolution · News/Fundamental agents · review queue · discovery scoring · extraction eval. Real FreeLLMAPI routes = drop-in |
| **4** | Quant, event studies, calibrated ranking | ✅ **core done (sample data)** — event studies · fixed labels · logistic vs base-rate/momentum · isotonic/Platt calibration + reliability · purged walk-forward · model registry. LightGBM/XGBoost = drop-in |
| **5** | Risk, portfolio, paper trading, rotation | ✅ **core done (sample data)** — risk vetoes · position sizing · rotation · paper simulator (NAV rebuilds from ledger) · performance dashboard · complete recommendation object |
| **6** | Terminal UI, alerts, grounded chat | ✅ **core done (sample data)** — full dark terminal (chart + recommendation card + risk/evidence panels + portfolio/performance/alerts/chat tabs) · alert engine · grounded chat |
| **7** | Production hardening + controlled release | ✅ **core done** — CI (ruff+pytest) · observability (`/metrics`) · degraded mode · rate limiting · drift (PSI) · model rollback · end-to-end audit export · feedback store · runbooks |

**Delivery gates** (from the plan): baseline must be *reproducible* (end P1) → LLM extraction must be *grounded* (end P3) → ranking must *beat baseline on untouched data after costs* (end P4) → paper trading must *match its simulated assumptions* (end P5) before anything is called production-ready.

---

## Stack

**Backend** FastAPI · async workers · PostgreSQL/TimescaleDB · DuckDB + Parquet · Redis · MinIO (object store)
**ML** LightGBM · XGBoost · logistic baseline · probability calibration · MLflow
**LLM** FreeLLMAPI behind the mandatory `LLMGateway` (routing · validation · fallback · immutable audit)
**Frontend** Next.js · React · Tailwind — a dark, techy TradingView-style terminal ([design guide](docs/UI_DESIGN_GUIDE.md))

---

## Repository layout

```text
Trading_algo/
├─ apps/
│  ├─ web/                    # Next.js terminal + chat (Phase 6)
│  └─ api/                    # FastAPI request layer
├─ services/
│  ├─ ingestion/              # source adapters, calendars, normalization  ← Phase 1
│  ├─ research_workers/
│  │  ├─ agents/              # the 9 AI roles (+ Pydantic contracts)
│  │  └─ llm_gateway/         # MANDATORY single path to any LLM
│  ├─ quant/                  # features, event studies, models, ranking, calibration
│  ├─ risk_portfolio/         # deterministic vetoes, sizing, rotation
│  └─ evaluation/             # backtests, walk-forward, paper ledger
├─ packages/                  # contracts (schemas) · ui · config
├─ data-contracts/            # schema definitions + migrations
├─ infra/                     # docker, IaC, monitoring
├─ data/                      # raw · normalized · features   (contents git-ignored)
├─ notebooks/  models/  scripts/  migrations/  docker/
├─ tests/                     # unit · integration · e2e · fixtures
├─ docs/                      # spec, phase plan, gateway, UI guide, policies
├─ CLAUDE.md                  # performance/P&L directive + governing rules
├─ .env.example  docker-compose.yml  pyproject.toml
```

---

## Documentation

| Doc | What's in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Performance, P&L & success requirements; governing rules (honesty-first) |
| [`docs/PHASE_WISE_BUILD_PLAN.md`](docs/PHASE_WISE_BUILD_PLAN.md) | Authoritative build order, data contracts, delivery gates |
| [`docs/INDIAN_EQUITY_AI_MASTER_SPEC.md`](docs/INDIAN_EQUITY_AI_MASTER_SPEC.md) | Full engineering spec |
| [`docs/LLM_GATEWAY.md`](docs/LLM_GATEWAY.md) | Mandatory LLM routing architecture |
| [`docs/UI_DESIGN_GUIDE.md`](docs/UI_DESIGN_GUIDE.md) | Dark techy terminal — palette + rules |
| [`docs/outcome-definitions.md`](docs/outcome-definitions.md) · [`data-sources.md`](docs/data-sources.md) · [`risk-policy.md`](docs/risk-policy.md) | Phase 0 policy docs |

---

## ⚠️ Honest disclaimer

This is a **research and decision-support** project, **not** financial advice and **not** a broker.

- The ~90% precision figure is a **research target on a highly selective, high-confidence subset** — never a promise, never a guarantee.
- +10% monthly is an **aspirational evaluation hypothesis**, not a design requirement.
- It will have losing trades, and it is built to report them honestly (report 62% if it's 62%).
- No `place_order`, `modify_order`, `cancel_order`, withdrawals or transfers exist — by design.
- **You** make every decision and execute every trade yourself.

Markets carry risk. Do your own research.

<div align="center">

*Built to discover first and analyze second — and to never fake its confidence.*

</div>
