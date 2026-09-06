# Runbook: Feed outage / stale data

**Symptom:** `/health` returns `status: DEGRADED` with `stale_feed` or `data_quality`
in `degraded_reasons`; the terminal shows a red DEGRADED banner.

**Automatic behavior (already enforced):**
- `evaluate_health` sets `suppress_recommendations: true` when feed age exceeds
  `max_feed_age_days` or data quality checks fail.
- The data-quality suite (`services/ingestion/quality`) quarantines bad data rather
  than letting it change signals.

**Steps:**
1. Confirm scope: `GET /health` and `GET /metrics`; check ingestion freshness.
2. Identify the failing source in [`docs/data-sources.md`](../data-sources.md); switch to
   the documented fallback feed if available.
3. Do **not** override the staleness gate. Recommendations stay suppressed until fresh,
   validated data lands.
4. Re-run ingestion; verify idempotency (a re-load reports `skipped`, not duplicates).
5. When `/health` returns `OK`, recommendations resume automatically.

**Never:** backfill with synthetic prices, or relabel stale data as current.
