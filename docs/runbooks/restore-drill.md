# Runbook: Backup & restore drill

Run quarterly. Proves that any recommendation can be reconstructed end to end and
that state restores cleanly.

**Audit reconstruction (per-recommendation):**
1. `GET /audit/{instrument_id}` returns an `AuditBundle`: the recommendation, cited
   evidence, `llm_run` records, model version + card, and data snapshot.
2. Assert `reconstructable: true`. The bundle alone must explain *what* was
   recommended, *on what evidence*, and *with which model + data*.

**State restore:**
1. Restore Postgres/TimescaleDB and the object store from the latest backup into a
   scratch environment.
2. Rebuild a dated dataset from raw source snapshots (point-in-time); confirm it
   matches the recorded feature/label versions.
3. Re-run the paper ledger reconstruction: `reconstruct_cash(fills, starting_cash)`
   must equal the reported NAV.
4. Record RTO/RPO and any gaps.

**Pass criteria:** every sampled recommendation reconstructs; NAV rebuilds exactly;
no broker credentials or write paths exist anywhere in the restored system.
