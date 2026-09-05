# AI Indian Equity Opportunity Engine — End-to-End Build Specification

## 0. Mission

Build a production-style, AI-powered Indian equity **opportunity discovery and decision-support system** for NSE/BSE.

The system must not start with a stock ticker and wait for the user. Its primary job is to **actively hunt the entire Indian equity market for opportunities**, including small-cap, mid-cap and large-cap companies.

It continuously combines:

- market/price/volume anomalies
- active web search
- financial news
- NSE/BSE filings
- company investor-relations information
- fundamentals
- analyst commentary
- social sentiment
- sector/macro information
- historical analogues

It then uses a multi-agent research floor, adversarial Bull/Bear analysis, quantitative ML, calibration and an independent risk veto to produce a ranked set of actionable recommendations.

The user remains the final decision-maker and manually executes trades.

### Important performance objective

Target **~90%+ precision on a highly selective, high-confidence subset of signals** as a research objective.

This is NOT a guaranteed result. Never claim guaranteed returns, zero losses or 90% accuracy without properly validated evidence.

The system must optimize for:

- precision at the top of the ranking
- positive expectancy
- risk-adjusted return
- controlled drawdown
- calibration
- realistic transaction costs/slippage

It must be completely honest about losing trades.

---

# 1. Product Behavior

The user opens a TradingView-style terminal and can:

1. Watch the entire Indian market being scanned.
2. See newly discovered opportunities.
3. Search any stock manually.
4. Chat with the AI research floor.
5. Inspect the chart and evidence behind a recommendation.
6. See Bull/Bear arguments.
7. See ML probability and historical evidence.
8. See portfolio-aware recommendations.
9. Receive BUY / SELL / HOLD / ROTATE / NO TRADE recommendations.
10. Receive exact suggested allocation, quantity, entry range, target and invalidation.
11. Receive alerts when an existing thesis changes.
12. Review every historical prediction and its eventual outcome.

The AI does NOT execute trades.

No broker write access in the initial system.

Forbidden capabilities:

- `place_order`
- `modify_order`
- `cancel_order`
- withdrawals
- fund transfers

The system may eventually support read-only portfolio/holding information.

---

# 2. Core Architecture

```text
NSE / BSE + Market Data + Web + News + Filings + Social
                         |
                         v
                DATA INGESTION BUS
                         |
                         v
              NORMALIZATION / ETL
                         |
                         v
             ACTIVE OPPORTUNITY SCANNER
                         |
              +----------+----------+
              |          |          |
              v          v          v
          Price       Web Search   News/Filings
          Scanner        Agent       Discovery
              |          |          |
              +----------+----------+
                         |
                         v
              ENTITY + EVENT ENGINE
                         |
                  1000s -> 100s
                         |
                         v
                 AI RESEARCH FLOOR
                         |
        +----------------+----------------+
        |        |       |       |        |
       News   Market  Fundamental Sentiment
        |        |       |       |        |
        +--------+-------+-------+--------+
                         |
                Historical Analogue
                         |
                         v
                  BULL <-> BEAR
                         |
                         v
                  JUDGE / DECISION
                         |
                         v
                  QUANT / ML ENGINE
                         |
                         v
                    RISK ENGINE
                    /          \
                 VETO          PASS
                                |
                                v
                    PORTFOLIO / TRADER
                                |
                                v
                    OPPORTUNITY RANKER
                                |
                                v
                 BUY / SELL / HOLD / ROTATE
                         / NO TRADE
                                |
                                v
                         HUMAN USER
                                |
                         MANUAL EXECUTION
```

---

# 3. Nine AI Agents

Use exactly these nine core AI roles initially.

## Agent 1 — Discovery Agent

Mission:

**Find opportunities the user did not ask for.**

Inputs:

- market scanner candidates
- active web search results
- news
- filings
- sector signals
- unusual price/volume activity

Responsibilities:

- generate search queries dynamically
- discover unknown companies
- discover catalysts
- investigate unusual market activity
- create candidate opportunities
- prioritize candidates for deeper analysis

It must be able to initiate follow-up searches.

Example:

```text
ABC suddenly +8% with 5x volume
        |
        v
Search ABC
        |
        +--> NSE filing
        +--> BSE filing
        +--> company IR
        +--> news
        +--> analyst commentary
        +--> sector news
        +--> social discussion
        +--> historical events
```

---

## Agent 2 — News/Event Agent

Responsibilities:

- understand breaking news
- identify catalysts
- classify event type
- assess novelty
- assess materiality
- assess surprise
- determine whether news is already priced in
- identify conflicting reports
- rank source quality

Event taxonomy should include:

- acquisitions
- partnerships
- contracts/orders
- government orders
- capacity expansion
- regulatory approvals
- earnings surprises
- guidance changes
- promoter buying/selling
- insider activity
- buybacks
- dividends
- management changes
- credit rating changes
- litigation
- regulatory actions
- fundraising
- product launches
- index inclusion/exclusion
- block deals
- commodity shocks
- sector policy changes

---

## Agent 3 — Market Agent

Analyze:

- price action
- volume
- volatility
- momentum
- trend
- breakouts
- relative strength
- sector-relative performance
- gap behavior
- VWAP
- ATR
- abnormal volume
- price/volume divergence

Do not rely on LLM interpretation for numerical calculations. Numerical features come from deterministic market-data code.

---

## Agent 4 — Fundamental Agent

Analyze:

- revenue growth
- earnings growth
- margins
- ROE/ROCE
- debt
- cash flow
- valuation
- earnings surprise
- promoter/shareholding changes
- business quality
- event-to-revenue significance

The agent should explain whether a catalyst is financially meaningful.

---

## Agent 5 — Sentiment Agent

Analyze:

- financial-news sentiment
- analyst commentary
- social sentiment
- discussion velocity
- sentiment divergence
- crowd behavior
- source credibility

Important:

Do not treat 100 copied articles/posts as 100 independent confirmations.

Detect:

- duplicated stories
- syndicated wire stories
- coordinated posts
- obvious pump behavior
- bot-like activity

Social sentiment is secondary evidence, not proof.

---

## Agent 6 — Historical Analogue Agent

Find historically similar situations.

Similarity dimensions:

- event type
- sector
- company size
- event magnitude
- price reaction
- volume reaction
- market regime
- valuation
- event novelty

Return:

```text
sample_count
positive_1d_rate
positive_3d_rate
positive_5d_rate
median_1d_return
median_3d_return
median_5d_return
drawdown_statistics
regime_condition
similarity_score
```

Only use information that would have been available at the historical decision timestamp.

---

## Agent 7 — Bull Agent

Construct the strongest evidence-based long/bull case.

Must:

- cite evidence
- identify catalysts
- quantify expected upside where possible
- identify why the market may be underpricing the information
- explicitly list assumptions

It cannot invent evidence.

---

## Agent 8 — Bear Agent

Construct the strongest opposing case.

Must search for:

- already-priced-in risk
- weak fundamentals
- misleading headlines
- poor liquidity
- circuit risk
- manipulation
- valuation risk
- sector weakness
- macro risk
- catalyst decay
- historical failure cases

The Bear agent has equal access to the evidence.

---

## Agent 9 — Judge / Decision Agent

Inputs:

- all analyst outputs
- Bull case
- Bear case
- historical analogues
- quantitative features
- ML outputs
- market regime
- risk information

Responsibilities:

- resolve contradictions
- rank evidence
- identify uncertainty
- produce a structured thesis
- recommend BUY / SELL / HOLD / ROTATE / NO TRADE

The Judge is NOT allowed to override the independent Risk Engine.

---

# 4. Non-LLM Quantitative Engines

These are separate from the AI agents.

## A. Market Feature Engine

Deterministically calculate:

- returns
- momentum
- volatility
- ATR
- RSI if used
- VWAP distance
- volume ratios
- abnormal volume
- relative strength
- sector-relative returns
- beta
- drawdown
- gap
- breakout distance
- liquidity
- turnover
- spread where available

## B. Event Study Engine

For historical events calculate:

```text
AR_1D
AR_3D
AR_5D
AR_10D
CAR_1_3D
CAR_1_5D
maximum adverse excursion
maximum favorable excursion
```

Use benchmark/sector-adjusted returns.

## C. ML Engine

Start with tabular models:

- LightGBM
- XGBoost
- logistic regression baseline
- ranking model
- probability calibration

Potential prediction targets:

```text
P(+1% within N days)
P(+2% within N days)
P(target before invalidation)
P(invalidation before target)
expected return
expected downside
```

Do not train only on raw future price direction.

## D. Calibration Engine

The displayed probability must be calibrated.

Track:

- calibration curve
- Brier score
- log loss
- precision at threshold
- reliability by confidence bucket

Example:

```text
Model says 90-95%
Actual historical success: 91.7%
```

This is meaningful.

An LLM saying "confidence 94%" is not.

## E. Opportunity Ranking Engine

Rank candidates using:

- calibrated probability
- expected return
- expected downside
- risk
- liquidity
- catalyst strength
- novelty
- historical analogue quality
- market regime
- portfolio interaction

---

# 5. Active Discovery System

The system must continuously hunt.

## Market scanners

Scan:

- all supported NSE/BSE equities
- small-cap
- mid-cap
- large-cap

Candidate triggers:

- abnormal volume
- abnormal volatility
- sharp movement
- relative strength
- breakout
- unusual weakness
- price/volume divergence
- sector rotation
- fresh highs/lows
- sudden liquidity increase

## Active Web Search

Use dynamic queries such as:

```text
"Indian listed company new order"
"smallcap order win India"
"NSE company contract today"
"listed company capacity expansion"
"promoter buying India"
"government order listed company"
"Indian defence order"
"railway order smallcap"
"semiconductor India listed supplier"
"Indian company acquisition"
"regulatory approval listed company"
"analyst upgrade India"
"earnings surprise India"
```

The Discovery Agent must generate follow-up queries based on what it finds.

## Source hierarchy

Tier 1:

- NSE/BSE
- company investor relations
- SEBI
- RBI
- government sources
- official releases

Tier 2:

- Reuters
- other high-quality institutional financial sources

Tier 3:

- Economic Times
- Moneycontrol
- Business Standard
- CNBC-TV18
- Mint
- NDTV Profit
- similar major financial media

Tier 4:

- blogs
- screeners
- forums
- social media
- IPO/GMP sites such as InvestorGain

Tier 4 is supporting sentiment/context only.

---

# 6. External Discovery Inputs

Integrate existing market-discovery platforms where legally/API-accessible.

## TradingView

Use as a discovery/reference input for:

- unusual volume
- market movers
- technical screens
- breakouts
- volatility
- relative strength

## Trendlyne

Use as a discovery/reference input for:

- volume shockers
- small-cap screens
- fundamental screens
- unusual activity

## Screener.in

Use as a fundamental discovery/reference input for:

- financial metrics
- growth
- valuation
- earnings
- custom fundamental screens

These are **candidate generators**, not final decision-makers.

Do not make the architecture dependent on scraping if an official API/licensed feed is unavailable. Prefer legal APIs, feeds, exports, or user-authorized access.

---

# 7. Data Architecture

## Primary storage

Use:

- PostgreSQL / TimescaleDB for application and time-series data
- DuckDB + Parquet for research/backtesting
- pgvector for semantic historical retrieval if needed
- Redis for cache and task state

## Raw data layer

Immutable storage for:

- raw news
- raw filings
- raw web results
- raw market data
- timestamps
- source URLs
- retrieval time

## Normalized layer

Tables/entities:

```text
companies
securities
prices
volumes
fundamentals
corporate_actions
filings
news_articles
web_documents
events
sentiment
analyst_views
social_posts
market_regimes
features
signals
predictions
recommendations
portfolio_snapshots
outcomes
agent_runs
model_runs
```

---

# 8. Point-in-Time Data Integrity

This is mandatory.

Every information item needs:

```text
published_at
effective_at
retrieved_at
market_timestamp
```

The historical model may only access information that existed at the decision time.

Prevent:

- look-ahead bias
- survivorship bias
- future corporate-action leakage
- revised fundamental leakage
- future news leakage

Maintain historical universe membership where possible.

Adjust historical prices for splits/bonuses/dividends appropriately.

---

# 9. News Deduplication

Indian financial news is heavily syndicated.

Implement:

- canonical URL extraction
- title similarity
- content similarity
- entity overlap
- event overlap
- timestamp proximity
- source clustering

Example:

```text
10 articles
     |
     v
8 are copies of one Reuters story
     |
     v
Count as 1 information event
```

---

# 10. Small-Cap / Manipulation Layer

Small companies are a core target.

Do NOT exclude them simply because they are small.

But apply additional checks:

```text
liquidity
spread
turnover
circuit status
price history
volume anomaly
social velocity
source quality
promoter/shareholding behavior
news originality
```

Potential manipulation flags:

- extreme social activity without credible news
- repeated identical posts
- abnormal price/volume without information
- suspicious low-float behavior
- sudden promotional coverage
- recycled old news

If manipulation risk is high:

```text
RISK ENGINE -> VETO
```

---

# 11. Agent Orchestration

Use asynchronous parallel execution.

Example:

```python
results = await asyncio.gather(
    news_agent.run(candidate),
    market_agent.run(candidate),
    fundamental_agent.run(candidate),
    sentiment_agent.run(candidate),
    historical_agent.run(candidate),
    macro_agent.run(candidate),
)
```

Bull and Bear should then run in parallel on the same evidence set.

Do not create unnecessary sequential LLM calls.

Use precomputed information wherever possible.

---

# 12. FreeLLM Integration

Create an internal AI gateway:

```text
application
    |
    v
AI Gateway
    |
    v
FreeLLM API
    |
    +-- routing
    +-- fallback
    +-- model selection
    +-- tool calling
    +-- structured outputs
    +-- latency tracking
    +-- model/provider logging
```

Keep model names configurable.

Recommended roles can include:

- fast models for filtering
- stronger reasoning models for research
- multiple independent models for Bull/Bear/Judge
- Fusion for high-value synthesis

Do not hard-code the system to one model.

Log:

```text
requested_model
actual_model
provider
agent
latency
tokens
success/failure
fallback
response_id
```

Eventually measure model performance by task.

---

# 13. Structured Agent Contracts

Every agent must return machine-readable JSON validated with Pydantic.

Example:

```json
{
  "ticker": "ABC",
  "thesis": "...",
  "event": {
    "type": "government_contract",
    "novelty": 0.91,
    "materiality": 0.82,
    "surprise": 0.77
  },
  "market_reaction": {
    "return_1d": 0.084,
    "volume_ratio": 4.8
  },
  "sentiment": 0.72,
  "risks": [],
  "evidence": [
    {
      "source": "NSE",
      "url": "...",
      "timestamp": "...",
      "claim": "..."
    }
  ]
}
```

Never pass free-form agent prose directly into the ML engine.

---

# 14. Final Recommendation Object

Example:

```json
{
  "action": "BUY",
  "ticker": "ABC",
  "allocation_rupees": 2000,
  "quantity": 5,
  "entry_low": 410,
  "entry_high": 415,
  "target": 445,
  "invalidation": 398,
  "holding_period": "1-5D",
  "probability": 0.914,
  "expected_return": 0.031,
  "risk_score": 0.21,
  "risk_verdict": "PASS",
  "historical_sample_size": 143,
  "thesis": "...",
  "bull_case": "...",
  "bear_case": "...",
  "evidence": [],
  "what_changes_decision": []
}
```

Actions:

```text
BUY
SELL
HOLD
ROTATE
NO_TRADE
```

---

# 15. Portfolio Agent

Input:

- current holdings
- current exposure
- cash
- risk limits
- existing signals

Output:

```text
BUY new position
ADD
REDUCE
EXIT
ROTATE A -> B
HOLD
NO TRADE
```

Example:

```text
Reduce HAL by ₹1,000
Add XYZ by ₹1,000

Reason:
XYZ has stronger calibrated expected edge,
lower portfolio correlation and stronger catalyst persistence.
```

Never force a trade.

---

# 16. Risk Engine

The Risk Engine is independent of the LLM Judge.

Checks:

- liquidity
- slippage
- spread
- volatility
- position concentration
- sector concentration
- portfolio correlation
- drawdown
- circuit risk
- manipulation risk
- market regime
- catalyst decay
- event uncertainty

It has veto power.

```text
AI consensus = BUY
ML = strong
Historical analogue = strong

RISK ENGINE
       |
       +--> PASS
       |
       +--> VETO
```

---

# 17. Persistent Memory

Use three memory classes.

## Episodic

Individual decisions:

```text
signal
timestamp
evidence
agent outputs
prediction
recommendation
```

## Semantic

Reusable knowledge:

```text
company
event type
historical analogue
sector behavior
market regime
```

## Performance

Agent/model performance:

```text
agent precision
model precision
confidence calibration
event-type performance
market-regime performance
failure modes
```

---

# 18. Outcome Learning

Every prediction must eventually be graded.

Example:

```text
Prediction:
P(+2% in 3D) = 0.91

Actual:
+2.7% in 3D

Result:
SUCCESS
```

Also record losses:

```text
Prediction:
P(+2% in 3D) = 0.91

Actual:
-3.4%

Result:
FAILURE
```

Track attribution:

```text
Which agent helped?
Which agent was wrong?
Which evidence was misleading?
Which model was used?
What was the market regime?
```

Do not automatically retrain from live outcomes without validation.

---

# 19. Backtesting

Build the backtester before trusting real money.

Pipeline:

```text
Point-in-time historical data
        |
        v
Historical discovery
        |
        v
Historical feature generation
        |
        v
ML prediction
        |
        v
Risk engine
        |
        v
Execution simulation
        |
        v
P&L
```

Include:

- brokerage
- taxes/fees where applicable
- slippage
- liquidity constraints
- realistic fills
- circuit constraints

Use:

- chronological train/validation/test
- walk-forward validation
- purging/embargo where appropriate
- untouched final test period

Never tune on the final test period.

---

# 20. Evaluation Metrics

Primary:

- precision at top-K
- precision above probability threshold
- expectancy

Secondary:

- average win
- average loss
- profit factor
- max drawdown
- Sharpe
- Sortino
- hit rate
- Brier score
- calibration error
- turnover
- slippage
- average holding period

Break down performance by:

- market cap
- sector
- event type
- market regime
- confidence bucket
- agent/model
- holding period

---

# 21. Trading Terminal

Use Next.js + React.

Main screen:

```text
+-------------------------------------------------------------+
| NIFTY | MARKET REGIME | SEARCH | PORTFOLIO | ALERTS        |
+-------------+---------------------------+-------------------+
| WATCHLIST   |                           | AI FLOOR          |
|             |      CANDLE CHART         |                   |
| ABC   🟢    |                           | News      ✓       |
| XYZ   🟢    |          PRICE            | Fundamental ✓     |
| TCS         |                           | Market    ✓       |
| HAL         |          VOLUME           | Sentiment ~       |
| ...         |                           | Historical ✓     |
|             |                           |                   |
|             |                           | 🐂 Bull           |
|             |                           | 🐻 Bear           |
|             |                           | Risk PASS ✓       |
+-------------+---------------------------+-------------------+
| FINAL OPPORTUNITY                                           |
| BUY XYZ | Qty 5 | ₹410-415 | Target ₹445 | Risk ₹398      |
| Probability | Historical Evidence | Thesis | Sources       |
+-------------------------------------------------------------+
```

Features:

- candlestick chart
- volume
- indicators
- event markers
- watchlist
- market scanner
- opportunity leaderboard
- portfolio
- AI agent status
- Bull/Bear view
- evidence/source panel
- chat
- alerts
- recommendation history

---

# 22. Backend Services

Recommended services:

```text
api/
ingestion/
market_scanner/
web_search/
news/
entity_resolution/
event_engine/
agents/
ai_gateway/
feature_engine/
historical_engine/
ml/
calibration/
risk/
portfolio/
ranking/
memory/
backtesting/
paper_trading/
alerts/
monitoring/
```

Use FastAPI as the main API layer.

Use asynchronous workers for agent jobs.

Redis can handle:

- caching
- queues
- job state
- short-lived market state

---

# 23. Suggested Project Structure

```text
indian-alpha/
|
├── apps/
│   ├── web/
│   └── api/
|
├── services/
│   ├── discovery/
│   ├── ingestion/
│   ├── market_scanner/
│   ├── web_search/
│   ├── news/
│   ├── entity_resolution/
│   ├── event_engine/
│   ├── agents/
│   │   ├── discovery.py
│   │   ├── news.py
│   │   ├── market.py
│   │   ├── fundamental.py
│   │   ├── sentiment.py
│   │   ├── historical.py
│   │   ├── bull.py
│   │   ├── bear.py
│   │   └── judge.py
│   ├── ai_gateway/
│   ├── quant/
│   ├── ml/
│   ├── risk/
│   ├── portfolio/
│   ├── ranking/
│   ├── memory/
│   ├── backtesting/
│   ├── paper_trading/
│   └── alerts/
|
├── data/
│   ├── raw/
│   ├── normalized/
│   └── features/
|
├── models/
├── notebooks/
├── tests/
├── scripts/
├── docker/
├── migrations/
├── docs/
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# 24. Fast Build Strategy

Do not build every production component before seeing a working signal.

## Phase 1 — Working discovery MVP

Build first:

1. NSE/BSE universe
2. market scanner
3. web/news discovery
4. entity resolution
5. candidate ranking
6. 9 agents
7. FreeLLM gateway
8. structured JSON
9. basic risk engine
10. terminal UI

Goal:

```text
Entire market
    ↓
discover candidates
    ↓
AI investigates
    ↓
recommendation
```

## Phase 2 — Quant intelligence

Add:

1. historical event database
2. event studies
3. feature store
4. LightGBM/XGBoost
5. calibration
6. ranking
7. portfolio allocation

## Phase 3 — Validation

Add:

1. point-in-time backtesting
2. walk-forward testing
3. paper trading
4. prediction grading
5. agent attribution
6. model registry
7. performance dashboard

## Phase 4 — Production hardening

Add:

- observability
- caching
- retry/fallback
- rate limiting
- data-quality checks
- security
- source monitoring
- drift detection

Do not connect broker write APIs.

---

# 25. Latency Design

The system must feel fast.

Do NOT execute every agent sequentially.

Use:

```text
Fast deterministic scanners
        ↓
Candidate shortlist
        ↓
Parallel AI agents
        ↓
Parallel Bull/Bear
        ↓
Fast quant/risk calculations
        ↓
Final Judge
```

Precompute:

- market features
- company fundamentals
- historical analogues
- embeddings
- recurring company metadata
- current news/event representations

Target interactive decision latency in the order of seconds for an already-discovered candidate, rather than minutes.

Continuous background discovery should do most expensive work before the user asks.

---

# 26. Alert System

Alert conditions:

- new high-ranked opportunity
- existing opportunity score changes materially
- thesis invalidated
- target reached
- risk veto triggered
- new contradictory information
- portfolio rotation opportunity
- major new event
- model confidence crosses validated threshold

Channels:

- in-app
- Telegram
- Discord
- email
- push notification

---

# 27. Security

- API keys only server-side
- never expose FreeLLM keys in frontend
- encrypt sensitive configuration
- role-based internal permissions
- audit logs
- rate limits
- strict tool allowlists
- no broker write permissions
- validate all LLM outputs
- never execute arbitrary tool calls from model text
- sanitize web content before passing into agents

Treat web pages as untrusted input.

Prompt injection from external web content must not be able to change system instructions or gain tool access.

---

# 28. Core Design Principles

1. **Discover first, analyze second.**
2. **Small-cap, mid-cap and large-cap are all valid candidates.**
3. **Web search is a first-class discovery mechanism.**
4. **LLMs analyze evidence; deterministic code calculates numbers.**
5. **Bull and Bear see the same evidence.**
6. **Risk has independent veto power.**
7. **NO TRADE is a valid and important result.**
8. **Every material claim must have evidence.**
9. **Every prediction gets graded.**
10. **No look-ahead bias.**
11. **No survivorship bias.**
12. **No fake confidence.**
13. **No guaranteed-return claims.**
14. **Optimize top-of-book opportunity precision, not forced trade frequency.**
15. **User always manually executes trades.**

---

# 29. First Implementation Objective

The first working version should be able to answer:

> **"Find the best opportunity in the Indian market right now."**

It should:

```text
scan market
   ↓
search web
   ↓
discover companies/events
   ↓
filter candidates
   ↓
run parallel agents
   ↓
Bull/Bear
   ↓
Judge
   ↓
ML/quant score
   ↓
risk veto
   ↓
rank
   ↓
show TOP opportunities
```

Example final output:

```text
# TOP OPPORTUNITY

XYZ — BUY

Allocation: ₹2,000
Quantity: 5
Entry: ₹410–415
Target: ₹445
Invalidation: ₹398
Holding: 1–5 days

Calibrated probability: XX%
Expected return: XX%
Historical analogue: XX / XXX positive

WHY:
...

BULL:
...

BEAR:
...

RISK:
PASS

EVIDENCE:
NSE filing
Company IR
News source
Market data

WHAT WOULD INVALIDATE THIS:
...
```

If nothing meets the validated threshold:

```text
NO TRADE
```

---

# 30. Final Acceptance Criteria

The system is considered a successful MVP when:

- It scans a broad NSE/BSE universe.
- It actively discovers opportunities without a user-provided ticker.
- It can discover small companies as well as large companies.
- It can actively search the web and perform follow-up research.
- It uses all 9 AI agent roles.
- Agents execute asynchronously where possible.
- FreeLLM is integrated behind an AI gateway.
- Agent outputs are structured and validated.
- Quantitative features are calculated outside the LLM.
- ML produces calibrated scores.
- Historical analogues are available.
- Risk can veto a recommendation.
- Portfolio-aware BUY/SELL/ROTATE/HOLD/NO TRADE recommendations work.
- Recommendations include allocation, quantity, entry, target and invalidation.
- Evidence is displayed.
- The UI provides a TradingView-style chart and AI research floor.
- Every prediction is persisted.
- Outcomes can be graded.
- Backtesting is point-in-time and leakage-controlled.
- Paper trading works.
- No broker order execution exists.
- The system can honestly report its actual performance.

## Ultimate product definition

This is not a chatbot.

This is not a simple stock screener.

This is not an autonomous broker.

It is an:

**AI-powered, agentic, market-wide Indian equity opportunity discovery and quantitative decision-support platform.**

Its core loop is:

**DISCOVER → RESEARCH → DEBATE → QUANTIFY → RISK-CHECK → RANK → RECOMMEND → OBSERVE OUTCOME → LEARN.**
