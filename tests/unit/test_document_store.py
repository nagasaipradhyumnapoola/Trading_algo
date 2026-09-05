"""Raw document store: content addressing, dedup, immutability, persistence."""

from services.ingestion import RawDocumentStore, content_hash


def test_store_and_read(tmp_path):
    store = RawDocumentStore(tmp_path)
    doc = store.store("NSE filing: order won", source="NSE", tier=1, title="Order")
    assert doc.content_hash == content_hash("NSE filing: order won")
    assert store.read_raw(doc.document_id) == "NSE filing: order won"
    assert store.get(doc.document_id) is doc


def test_same_content_dedups(tmp_path):
    store = RawDocumentStore(tmp_path)
    a = store.store("identical wire story", source="ReuterA")
    b = store.store("identical wire story", source="ReuterB")   # syndicated copy
    assert a.document_id == b.document_id                        # one information event
    assert len(store) == 1


def test_index_persists(tmp_path):
    store = RawDocumentStore(tmp_path)
    store.store("doc one", source="ET")
    store.store("doc two", source="Mint")
    reloaded = RawDocumentStore(tmp_path)
    assert len(reloaded) == 2
