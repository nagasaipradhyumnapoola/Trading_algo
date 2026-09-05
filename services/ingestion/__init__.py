"""ingestion — source adapters, trading calendars, normalization.

Phase 1 home: instrument master + EOD OHLCV ingestion (raw snapshots,
idempotency, freshness checks, adjusted/unadjusted series). Everything else in
the system sits on this data spine.
"""
