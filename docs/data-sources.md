# Data Source Inventory

> Phase 0 deliverable. For every source record: rights/terms, access date, raw
> payload hash, license/attribution restrictions, latency, historical depth,
> adjustment method, and fallback. Prefer official/licensed feeds; do not rely on
> brittle or prohibited scraping for production market data.

**Status:** DRAFT — to be completed in Phase 0.

| Category | Source | Rights / license | Latency | History depth | Adjustment | Fallback | Status |
|---|---|---|---|---|---|---|---|
| Instrument master / reference | _tbd_ | | | | | | ☐ |
| EOD OHLCV | _tbd_ | | | | | | ☐ |
| Corporate actions | _tbd_ | | | | | | ☐ |
| Trading calendar | _tbd_ | | | | | | ☐ |
| Index / universe membership (point-in-time) | _tbd_ | | | | | | ☐ |
| Fundamentals / financials | _tbd_ | | | | | | ☐ |
| Exchange filings / announcements | NSE / BSE | | | | | | ☐ |
| News | _tbd_ | | | | | | ☐ |
| Macro / sector benchmarks | _tbd_ | | | | | | ☐ |

## Notes

- All access is server-side only; keys live in `.env` (never committed) — see CLAUDE.md.
- Every fetched document is stored raw with a content hash and immutable provenance.
