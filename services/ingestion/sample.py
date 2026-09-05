"""Deterministic synthetic universe for demos and the Phase 1 sample API.

Clearly SAMPLE data — not a market feed. Phase 2 replaces this with licensed
ingestion. Seeded, so the same call always yields the same bars.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from .instruments import InstrumentMaster
from .models import Bar, Instrument
from .repository import InMemoryBarRepository

SAMPLE_START = date(2026, 1, 1)
SAMPLE_SEED = 7

# instrument_id -> (drift, base_price, base_volume)
_SPEC = {
    "MOMO": (0.006, 100, 40000),     # uptrend, liquid
    "CHOP": (0.000, 200, 40000),     # sideways
    "WEAK": (-0.006, 150, 40000),    # downtrend
    "ILLQ": (0.006, 90, 30),         # uptrend but illiquid
}


def build_sample_universe(
    n: int = 60, seed: int = SAMPLE_SEED
) -> tuple[InMemoryBarRepository, InstrumentMaster, date]:
    rng = random.Random(seed)
    repo = InMemoryBarRepository()

    for iid, (drift, base_price, base_vol) in _SPEC.items():
        price = float(base_price)
        closes = []
        for _ in range(n):
            price *= 1 + drift + rng.uniform(-0.02, 0.02)
            closes.append(price)
        for i, c in enumerate(closes):
            o = closes[i - 1] if i > 0 else c
            hi = max(o, c) * (1 + rng.uniform(0.0, 0.01))
            lo = min(o, c) * (1 - rng.uniform(0.0, 0.01))
            vol = base_vol * (2 if i % 5 == 4 else 1)   # spike days incl. the latest session
            repo.upsert(Bar(instrument_id=iid, session_date=SAMPLE_START + timedelta(days=i),
                            open=round(o, 2), high=round(hi, 2), low=round(lo, 2),
                            close=round(c, 2), volume=vol, source="sample"))

    master = InstrumentMaster([
        Instrument(instrument_id=x, symbol=x, name=x, sector="Sample") for x in _SPEC
    ])
    last_session = SAMPLE_START + timedelta(days=n - 1)
    return repo, master, last_session
