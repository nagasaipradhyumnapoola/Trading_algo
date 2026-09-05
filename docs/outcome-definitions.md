# Outcome Definitions

> **Fix these BEFORE any modeling or backtest.** Success is defined here and never
> redefined after seeing results (CLAUDE.md §3, Phase-plan §7.1). This document is
> versioned; changing it creates a new label version, it never edits history.

**Status:** DRAFT — to be finalized in Phase 0.

## Strategy horizon (starting point)

- End-of-day **swing**, holding **3–10 trading sessions** (per phase plan Phase 0).

## Success rule (to finalize)

A recommendation is graded against a fixed rule. Candidate rule:

```text
Entry:        next available session open after signal (no look-ahead)
Target:       predefined level (per recommendation)
Invalidation: predefined stop (per recommendation)
Horizon:      max_holding_sessions (per recommendation)

Result = SUCCESS if target is hit before invalidation within horizon,
         under target-first / stop-first ordering on intraday ambiguity,
         measured on NET return after costs.
```

Decisions to lock in Phase 0:

- [ ] target-first vs stop-first tie-breaking on same-bar touches
- [ ] end-of-horizon net-return threshold if neither target nor stop hits
- [ ] execution timing (open / VWAP / close of next session)
- [ ] gap handling (gap through stop or target)
- [ ] circuit / suspension / delisting treatment
- [ ] corporate-action adjustment method

## Cost model (to finalize)

- [ ] brokerage assumption
- [ ] statutory / exchange charges
- [ ] taxes where applicable
- [ ] slippage model
- [ ] spread assumption by liquidity bucket

## Label versions

| Version | Date | Change |
|---|---|---|
| _tbd_ | _tbd_ | initial |
