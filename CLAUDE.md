# PERFORMANCE, P&L AND SUCCESS REQUIREMENTS

> Project-level directive for Indian Alpha. This governs the **entire**
> implementation. It sits alongside the engineering spec at
> [`docs/INDIAN_EQUITY_AI_MASTER_SPEC.md`](docs/INDIAN_EQUITY_AI_MASTER_SPEC.md).
> The goal is not "build a cool trading dashboard" — it is to discover and rank
> genuine, positive-expectancy opportunities and to report performance honestly.

## Governing documents (read before building)

- **Build order & delivery gates:** [`docs/PHASE_WISE_BUILD_PLAN.md`](docs/PHASE_WISE_BUILD_PLAN.md)
  — the authoritative phase sequence. Where it conflicts with the master spec on
  sequencing or structure, the phase plan wins. **Do not build terminal polish
  before a reproducible baseline has an out-of-sample + paper-trading record.**
- **Full engineering spec:** [`docs/INDIAN_EQUITY_AI_MASTER_SPEC.md`](docs/INDIAN_EQUITY_AI_MASTER_SPEC.md)
- **UI look & feel:** [`docs/UI_DESIGN_GUIDE.md`](docs/UI_DESIGN_GUIDE.md) — dark,
  techy terminal; greyscale (black/white/grey shades) with **green = up/buy/pass**
  and **red = down/sell/veto** as the only meaningful colors; monospace numbers.
- **LLM access:** [`docs/LLM_GATEWAY.md`](docs/LLM_GATEWAY.md) — **mandatory.**

### LLM access rule (non-negotiable)

Every LLM call goes through the internal `LLMGateway` service. **No agent, API
route, worker, or frontend component may call FreeLLMAPI or any provider
directly.** Model names are never hard-coded in prompts or agents — routing comes
from versioned task policies + a capability registry. Every call is schema- and
citation-validated and written to an immutable `llm_run` record; on total route
failure the system enters degraded mode (deterministic results preserved,
LLM-dependent recommendations suppressed, nothing fabricated). LLMs do reasoning,
extraction, summarization and synthesis **only** — probabilities, expected return,
risk vetoes, position sizing, P&L and backtest evaluation are deterministic engine
outputs, never LLM outputs. Gateway is implemented in Phase 3; reserved now.

## Environment & secrets policy

- **`.env` is maintained separately and is never committed.** Only
  [`.env.example`](.env.example) (placeholders) lives in Git; `.gitignore` excludes
  the real `.env`.
- All provider/API keys (FreeLLMAPI, market data, news) are **server-side only** —
  never shipped to or referenced from the frontend.
- Copy `.env.example` → `.env` locally and fill real values. Keep `BROKER_WRITE_ENABLED=false`.

## Core Objective

The system must be engineered specifically to discover and rank
**high-probability, positive-expectancy opportunities** in the Indian equity market.

The primary research target is:

> Achieve approximately 90%+ precision on a highly selective subset of final trade recommendations.

This is an aspirational engineering target, NOT a guaranteed result.

The system must NEVER fabricate, manipulate, or hide performance statistics to appear successful.

If the validated system only achieves 62%, report 62%.

If it achieves 91% under a genuinely out-of-sample test, report 91%.

---

## 1. DO NOT OPTIMIZE FOR TRADE FREQUENCY

The system must NOT feel obligated to generate trades.

Valid outputs include:

- BUY
- SELL
- HOLD
- ROTATE
- NO TRADE

The system should prefer:

> NO TRADE

over a low-quality setup.

The objective is to maximize the quality of the **highest-ranked opportunities**,
not the number of recommendations.

---

## 2. 90% SUCCESS TARGET

Define the primary target as:

### Precision of final high-confidence recommendations

For example:

```text
System evaluates:        5,000 candidates

Potential candidates:      300

Deeply researched:          80

Final recommendations:     10

Successful outcomes:        9

Precision:                 90%
```

Do NOT claim:
"The system predicts 90% of all Indian stocks."

Instead measure:
"Of the opportunities the system classified as high-confidence, how many actually
satisfied the predefined outcome?"

The outcome definition must be fixed BEFORE testing.

---

## 3. DEFINE SUCCESS MATHEMATICALLY

Every recommendation must have a predefined:

- entry range
- target
- invalidation
- maximum holding period

Example:

```text
Entry:        ₹100–₹102
Target:       ₹110
Invalidation: ₹97
Horizon:      3 trading days
```

A recommendation is successful only according to the predefined evaluation rule.

Do not redefine success after seeing the result.

---

## 4. P&L OBJECTIVE

Track actual P&L after:

- brokerage
- exchange charges
- taxes/fees
- slippage
- realistic execution assumptions

Calculate:

```text
Gross P&L
Net P&L
Return %
Risk-adjusted return
Maximum drawdown
```

Never report gross theoretical returns as actual trading performance.

---

## 5. MONTHLY RETURN TARGET

The aspirational objective is to investigate whether the strategy can produce:
**~10% monthly return under controlled risk.**

This is NOT a required guaranteed outcome.

Do not force the system to achieve 10% by increasing leverage, risk, trade
frequency, or concentration.

If the validated strategy produces `+3%` monthly, report +3%.
If it produces `+8%`, report +8%.
If it loses money `-4%`, report -4%.

The system must never optimize specifically to manufacture a +10% number.

---

## 6. RISK / REWARD

Prefer opportunities with favorable asymmetric risk/reward.

For example:

```text
Potential reward: +6%
Potential loss:   -2%

Risk/Reward = 3:1
```

Do not select a trade simply because its probability of winning is high.
A 90% win rate with catastrophic losses can still be a losing strategy.

The ranking system must therefore consider:

```text
Probability
× Expected Return
× Risk/Reward
× Liquidity
× Confidence
```

along with portfolio and market-regime constraints.

---

## 7. MAXIMUM DRAWDOWN

The system must explicitly track maximum drawdown.

Track:

```text
Peak portfolio value
Trough portfolio value
Maximum drawdown %
Time to recovery
```

A strategy with high returns but unacceptable drawdown must be rejected.
The system should prioritize capital preservation.

---

## 8. POSITION SIZING

The system must calculate position size rather than simply saying "BUY."

Example:

```text
Portfolio:        ₹50,000

Recommended risk: 0.5%
Maximum loss:     ₹250

Entry:            ₹100
Invalidation:     ₹95

Risk/share:       ₹5

Maximum quantity:
₹250 / ₹5 = 50 shares

Position value:
₹5,000
```

The system must also respect:

- liquidity
- concentration
- sector exposure
- correlation
- volatility
- portfolio drawdown

---

## 9. SMALL-CAP OPPORTUNITY TARGET

Small and mid-cap companies are explicitly part of the opportunity universe.

Do NOT bias the ranking toward large-cap companies simply because they are famous.

The discovery engine should actively search for:

- small-cap catalysts
- unusual volume
- new contracts
- government orders
- partnerships
- capacity expansions
- regulatory approvals
- earnings surprises
- promoter activity
- sector-specific catalysts
- unusual price/volume behavior

However, small-cap candidates must pass additional:

- liquidity
- spread
- circuit
- manipulation
- execution
- information-quality

checks.

A high predicted return does not override unacceptable execution risk.

---

## 10. OPPORTUNITY RANKING

Every candidate should receive a composite score.

Conceptually:

```text
Opportunity Score =
    calibrated_probability
  × expected_return
  × risk_adjustment
  × catalyst_strength
  × historical_edge
  × liquidity_factor
  × regime_factor
```

The exact mathematical formulation should be empirically optimized and validated
rather than hard-coded permanently.

The system should rank the entire candidate universe and surface the
highest-quality opportunities.

---

## 11. EXPECTED OUTPUT

Every final recommendation should contain:

```text
Ticker
Action
Current price

Entry range
Quantity
Capital allocation

Target
Invalidation / stop
Expected holding period

Probability
Expected return
Expected downside
Risk/reward

Historical sample size
Historical success rate

Bull case
Bear case

Risk-engine verdict

Evidence / sources

What would invalidate the thesis
```

Example:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        TOP OPPORTUNITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

XYZ — BUY

Current:       ₹412

Entry:         ₹410–₹415
Quantity:      5
Allocation:    ₹2,060

Target:        ₹445
Invalidation:  ₹398
Horizon:       1–5 trading days

Calibrated P:  91.2%
Expected:      +4.8%
Risk/Reward:   2.7:1

Historical:
143 similar events
89.5% positive at 3D

Risk: PASS ✓

Bull:
...

Bear:
...

Evidence:
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The probability must come from the calibrated quantitative system, NOT from the
LLM's subjective confidence.

---

## 12. PERFORMANCE DASHBOARD

Build a dedicated performance dashboard.

Track:

**Overall**

- total recommendations
- successful recommendations
- failed recommendations
- precision
- recall where meaningful
- average return
- median return
- total net P&L
- cumulative return
- maximum drawdown
- profit factor
- Sharpe
- Sortino

**By confidence**

```text
50–60%
60–70%
70–80%
80–90%
90–95%
95%+
```

This allows us to determine whether 90% confidence actually corresponds to
approximately 90% real-world success.

**By market cap**

```text
Large
Mid
Small
```

**By event type**

```text
Contract
Acquisition
Earnings
Regulatory
Promoter activity
Breakout
Momentum
Sector rotation
etc.
```

**By agent** — measure which agents actually improve outcomes.

---

## 13. MODEL PERFORMANCE

Track each model and agent independently.

Example:

```text
Agent              Predictions   Precision

News Agent              820        84.1%
Market Agent            820        77.4%
Fundamental Agent       820        81.6%
Sentiment Agent         820        68.2%
Historical Agent        820        88.3%
Bull Agent              820        72.5%
Bear Agent              820        83.7%

FINAL SYSTEM            210        91.0%
```

These numbers must be calculated from actual historical/live outcomes.
Never generate them manually.

---

## 14. MODEL SELECTION

Do not assume the strongest LLM is the strongest financial predictor.

Measure:

```text
event extraction accuracy
evidence accuracy
classification accuracy
directional precision
calibration
latency
failure rate
```

Use FreeLLM routing to test different models and learn which models perform best
for each agent role.

---

## 15. BACKTEST PERFORMANCE MUST BE HONEST

Every backtest report must clearly distinguish:

```text
Training
Validation
Test
Final untouched test
Paper trading
Live/shadow
```

- Never mix them.
- Never tune the system against the final test set.
- Never use future information.
- Never use today's surviving companies to represent the historical universe
  without accounting for survivorship bias.

---

## 16. PAPER TRADING GATE

Before recommending real-money deployment, run the complete system in
paper/shadow mode. Record every signal exactly as if it were live.

Evaluate:

```text
30 days
60 days
90+ days
```

depending on the strategy and available opportunity frequency.

Compare:

```text
Predicted probability
vs
Actual outcome
```

The system should only be considered production-ready after demonstrating stable
out-of-sample behavior.

---

## 17. REAL-MONEY SAFETY

The AI never directly executes trades. The final action is:

```text
AI
 ↓
RECOMMENDATION
 ↓
USER REVIEW
 ↓
USER MANUALLY EXECUTES
```

- No automatic order execution.
- No automatic leverage.
- No automatic fund transfer.
- No mechanism should be added simply to increase P&L.

---

## 18. CRITICAL RULE

Never optimize the system to make the backtest look good.

Optimize for:

> Generalization to unseen Indian-market conditions.

The ultimate question is not:
"Can we make the historical chart look amazing?"

It is:

> "If this exact system had made this recommendation at that exact historical
> timestamp, using only information available then, would the outcome have
> justified the recommendation?"

That standard must govern the entire implementation.
