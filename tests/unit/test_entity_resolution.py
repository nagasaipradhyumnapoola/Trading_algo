"""Entity resolution + document clustering."""

from datetime import date

from services.ingestion import Instrument, InstrumentMaster
from services.research_workers.entity_resolution import EntityResolver, cluster_documents


def _master():
    return InstrumentMaster([
        Instrument(instrument_id="INDA0001", symbol="RELIANCE",
                   name="Reliance Industries Ltd", isin="INE002A01018"),
        Instrument(instrument_id="INDA0002", symbol="TCS",
                   name="Tata Consultancy Services Ltd", isin="INE467B01029"),
    ])


def test_resolve_by_symbol_isin_name_alias():
    r = EntityResolver(_master(), aliases={"RIL": "INDA0001"})
    assert r.resolve_mention("RELIANCE") == "INDA0001"
    assert r.resolve_mention("INE002A01018") == "INDA0001"
    assert r.resolve_mention("Reliance Industries Limited") == "INDA0001"   # normalized
    assert r.resolve_mention("RIL") == "INDA0001"                          # alias
    assert r.resolve_mention("NOPE") is None


def test_resolve_text_finds_multiple():
    r = EntityResolver(_master())
    ids = r.resolve_text("TCS wins deal; Reliance Industries up 5%")
    assert ids == {"INDA0001", "INDA0002"}


def test_cluster_dedups_by_hash_and_event():
    docs = [
        {"content_hash": "h1", "instrument_id": "A"},
        {"content_hash": "h1", "instrument_id": "A"},                     # syndicated copy
        {"instrument_id": "B", "event_type": "earnings", "date": date(2026, 1, 1)},
        {"instrument_id": "B", "event_type": "earnings", "date": date(2026, 1, 1)},  # dup event
        {"content_hash": "h2", "instrument_id": "C"},
    ]
    clusters = cluster_documents(docs)
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2, 2]                                              # h1(2), B-earnings(2), h2(1)
