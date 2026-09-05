"""Phase 1 data-spine demo — reproducible EOD load from the sample fixtures.

Run:
    python scripts/load_eod_demo.py

Loads the instrument master and EOD bars, prints a load report, then re-runs the
same feed to show the load is idempotent (second pass changes nothing).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on path

from services.ingestion import (
    CsvEodAdapter,
    InMemoryBarRepository,
    InstrumentMaster,
    Timeframe,
    load_eod,
)

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def main() -> None:
    master = InstrumentMaster.from_csv(FIXTURES / "sample_instruments.csv")
    print(f"instruments: {len(master)} loaded, {len(master.tradable())} tradable")

    repo = InMemoryBarRepository()
    as_of = date(2026, 9, 4)

    first = load_eod(CsvEodAdapter(FIXTURES / "sample_eod.csv"), repo, as_of=as_of)
    print(f"pass 1  added={first.added} skipped={first.skipped} "
          f"corrected={first.corrected}  last={first.last_session_date} "
          f"stale={first.is_stale}")

    second = load_eod(CsvEodAdapter(FIXTURES / "sample_eod.csv"), repo, as_of=as_of)
    print(f"pass 2  added={second.added} skipped={second.skipped} "
          f"corrected={second.corrected}  (idempotent: no changes)")

    # Point-in-time view: what was known about SMALLCO as of 2026-09-02.
    visible = repo.as_of("INDA0003", Timeframe.EOD, date(2026, 9, 2))
    print(f"SMALLCO known as-of 2026-09-02: "
          f"{[str(b.session_date) for b in visible]} "
          f"(latest close {visible[-1].close})")


if __name__ == "__main__":
    main()
