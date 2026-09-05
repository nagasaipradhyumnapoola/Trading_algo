# Risk Policy

> Phase 0 deliverable. Deterministic constraints the independent risk engine
> enforces (Phase 5). The risk engine can VETO; the LLM Judge cannot override it.

**Status:** DRAFT — to be finalized in Phase 0.

## Position / portfolio limits (to finalize)

- [ ] max position size (% of capital)
- [ ] per-trade risk (% of capital, e.g. 0.5%)
- [ ] max sector concentration
- [ ] max correlation / cluster exposure
- [ ] cash reserve floor
- [ ] max portfolio drawdown + throttle response

## Tradability gates (to finalize)

- [ ] minimum turnover / liquidity
- [ ] maximum spread by bucket
- [ ] circuit / price-limit risk
- [ ] gap risk
- [ ] volatility ceiling
- [ ] data-quality minimum
- [ ] event-uncertainty threshold
- [ ] manipulation heuristics
- [ ] stale-signal expiry

## Small-cap rules (to finalize)

Small/mid-caps are in-universe but face extra liquidity/spread/circuit/
manipulation/execution/information-quality checks. A high predicted return never
overrides unacceptable execution risk.

## Manual-execution safety

No order placement, fund transfer, or broker write path exists. `BROKER_WRITE_ENABLED=false`.
