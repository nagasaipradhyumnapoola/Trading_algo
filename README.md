<div align="center">

# 🐂 Indian Alpha 🐻

### An AI research floor that hunts the *entire* Indian market for trades — before you even ask.

**Not a chatbot. Not a screener. Not an autopilot broker.**
It's an agentic, market-wide opportunity-discovery and quant decision-support engine for NSE/BSE.

`DISCOVER → RESEARCH → DEBATE → QUANTIFY → RISK-CHECK → RANK → RECOMMEND → OBSERVE → LEARN`

![Status](https://img.shields.io/badge/status-Phase%201%20scaffold-orange)
![Market](https://img.shields.io/badge/market-NSE%20%2F%20BSE-blue)
![Agents](https://img.shields.io/badge/AI%20agents-9-8A2BE2)
![Execution](https://img.shields.io/badge/broker%20writes-NONE-red)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

</div>

---

## The pitch

Most tools wait for you to type a ticker. **This one doesn't.**

Indian Alpha continuously scans small-, mid- and large-caps across NSE/BSE, cross-referencing price/volume anomalies, live web search, breaking news, exchange filings, fundamentals, analyst commentary and social sentiment. When it smells an opportunity, it spins up a **nine-agent research floor** — including an adversarial **Bull vs. Bear** debate — grades the idea with **calibrated machine learning**, runs it past an **independent risk engine with veto power**, and hands you a single, evidence-backed recommendation.

Then it watches what actually happens and **grades itself**. Every prediction. Wins *and* losses.

> **You** stay the decision-maker. **You** execute every trade. The system never touches a broker.

---

## How it thinks

```text
      NSE / BSE  ·  Web  ·  News  ·  Filings  ·  Social
                         │
                         ▼
              INGEST → NORMALIZE (point-in-time)
                         │
                         ▼
        ACTIVE SCANNER  ── thousands of tickers
                         │   vol/price/breakout anomalies
                         ▼
        ENTITY + EVENT ENGINE  ── narrows to hundreds
                         │
                         ▼
        ┌──────── AI RESEARCH FLOOR (9 agents) ────────┐
        │  News · Market · Fundamental · Sentiment      │
        │  Historical Analogue · Discovery              │
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

---

## Two brains, kept strictly apart

| 🧠 The LLM brain (9 agents) | 🔢 The math brain (deterministic) |
|---|---|
| Reads evidence, argues, judges | Calculates every number |
| Discovery · News · Market read · Fundamental · Sentiment · Historical · Bull · Bear · Judge | Features (RSI/ATR/VWAP/vol) · Event studies (AR/CAR) · LightGBM/XGBoost · **Calibration** · Ranking |
| *An LLM saying "94% confident" is worthless.* | *A model whose "90–95%" bucket hits 91.7% in reality is gold.* |

**The line is sacred:** LLMs interpret evidence; deterministic code produces the numbers. They never blur.

---

## The nine agents

| # | Agent | Job |
|---|-------|-----|
| 1 | **Discovery** | Find opportunities you never asked about; generate its own follow-up searches |
| 2 | **News / Event** | Classify the catalyst — is it material, novel, already priced in? |
| 3 | **Market** | Read price action, momentum, breakouts (numbers from code, not the LLM) |
| 4 | **Fundamental** | Is the catalyst *financially* meaningful to the business? |
| 5 | **Sentiment** | Dedup syndicated wires; sniff out pump-and-dump and bot activity |
| 6 | **Historical Analogue** | Find similar past setups and their real hit-rates |
| 7 | **Bull** 🐂 | Build the strongest evidence-based long case |
| 8 | **Bear** 🐻 | Build the strongest opposing case — equal access to evidence |
| 9 | **Judge** | Resolve the debate, rank evidence, recommend. **Cannot override Risk.** |

---

## What comes out

```json
{
  "action": "BUY",
  "ticker": "XYZ",
  "allocation_rupees": 2000,
  "quantity": 5,
  "entry_low": 410, "entry_high": 415,
  "target": 445, "invalidation": 398,
  "holding_period": "1-5D",
  "probability": 0.914,
  "expected_return": 0.031,
  "risk_verdict": "PASS",
  "historical_sample_size": 143,
  "thesis": "…", "bull_case": "…", "bear_case": "…",
  "evidence": [ … ],
  "what_changes_decision": [ … ]
}
```

Every recommendation ships with allocation, quantity, entry range, target, invalidation, a **calibrated** probability, the historical sample behind it, both sides of the debate, the raw evidence — and exactly what would prove it wrong.

---

## The laws we don't break

- **Point-in-time or it didn't happen.** The historical model sees *only* data that existed at decision time. No look-ahead, no survivorship, no future-news leakage.
- **Dedup the noise.** Eight copies of one Reuters wire count as **one** information event, not eight confirmations.
- **Small-caps welcome, manipulation isn't.** We don't exclude small companies — we flag pump behavior, low-float games and recycled news. High manipulation risk → **risk veto**.
- **Every prediction gets graded.** Successes *and* losses, attributed to the agent, model and market regime responsible.
- **`NO_TRADE` is a real answer.** The system never forces a trade to look busy.
- **Risk has the final no.** The Judge proposes; the independent Risk Engine can always veto.

---

## Roadmap

- [x] **Phase 0** — Repo, spec, scaffold
- [ ] **Phase 1** — Discovery MVP: universe · scanner · web/news · 9 agents · AI gateway · basic risk · terminal UI → *"Find the best opportunity right now."*
- [ ] **Phase 2** — Quant: event DB · feature store · LightGBM/XGBoost · calibration · ranking · portfolio allocation
- [ ] **Phase 3** — Validation: point-in-time backtest · walk-forward · paper trading · prediction grading · attribution
- [ ] **Phase 4** — Hardening: observability · retry/fallback · rate limits · drift detection

📄 **Full engineering spec:** [`docs/INDIAN_EQUITY_AI_MASTER_SPEC.md`](docs/INDIAN_EQUITY_AI_MASTER_SPEC.md)

---

## Stack

**Backend** FastAPI · async workers · PostgreSQL/TimescaleDB · DuckDB + Parquet · Redis · pgvector
**ML** LightGBM · XGBoost · logistic baseline · probability calibration
**LLM** FreeLLM behind a configurable AI gateway (routing · fallback · logging)
**Frontend** Next.js · React — a TradingView-style terminal with a live AI research floor

---

## Repo layout

```text
indian-alpha/
├── apps/
│   ├── web/                 # Next.js trading terminal
│   └── api/                 # FastAPI gateway
├── services/
│   ├── discovery/  ingestion/  market_scanner/  web_search/  news/
│   ├── entity_resolution/  event_engine/
│   ├── agents/              # the 9 AI roles
│   ├── ai_gateway/  quant/  ml/  calibration/
│   ├── risk/  portfolio/  ranking/  memory/
│   └── backtesting/  paper_trading/  alerts/
├── data/  { raw · normalized · features }
├── models/  notebooks/  tests/  scripts/  docker/  migrations/
└── docs/
```

---

## ⚠️ Honest disclaimer

This is a **research and decision-support** project, **not** financial advice and **not** a broker.

- The ~90% precision figure is a **research target on a highly selective, high-confidence subset** — never a promise, never a guarantee.
- It will have losing trades, and it is built to report them honestly.
- No `place_order`, `modify_order`, `cancel_order`, withdrawals or transfers exist — by design.
- **You** make every decision and execute every trade yourself.

Markets carry risk. Do your own research.

<div align="center">

*Built to discover first and analyze second — and to never fake its confidence.*

</div>
