"""Immutable raw-document store for filings, announcements, and news.

Content-addressed: a document is keyed by the SHA-256 of its content, so storing
the same content twice de-duplicates to one record (the basis for the Phase 3 news
dedup — syndicated copies collapse to one information event). Raw content is
written once under the store root and never overwritten; provenance is immutable.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    content_hash: str
    source: str                       # publisher / feed
    url: str | None = None
    title: str = ""
    tier: int = Field(default=3, ge=1, le=4)   # 1=NSE/SEBI … 4=social
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=_utcnow)
    raw_uri: str | None = None        # where the raw bytes live
    rights: str | None = None         # license / attribution restrictions


class RawDocumentStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._raw = self.root / "raw"
        self._raw.mkdir(exist_ok=True)
        self._index_path = self.root / "index.jsonl"
        self._by_hash: dict[str, SourceDocument] = {}
        self._by_id: dict[str, SourceDocument] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            for line in self._index_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    doc = SourceDocument.model_validate_json(line)
                    self._by_hash[doc.content_hash] = doc
                    self._by_id[doc.document_id] = doc

    def store(self, content: str, *, source: str, url: str | None = None,
              title: str = "", tier: int = 3, published_at: datetime | None = None,
              rights: str | None = None) -> SourceDocument:
        h = content_hash(content)
        if h in self._by_hash:
            return self._by_hash[h]                    # dedup: same content -> one record

        raw_path = self._raw / f"{h}.txt"
        if not raw_path.exists():                       # write raw once, never overwrite
            raw_path.write_text(content, encoding="utf-8")

        doc = SourceDocument(
            document_id=f"doc_{h[:12]}", content_hash=h, source=source, url=url,
            title=title, tier=tier, published_at=published_at,
            raw_uri=str(raw_path), rights=rights,
        )
        self._by_hash[h] = doc
        self._by_id[doc.document_id] = doc
        with self._index_path.open("a", encoding="utf-8") as fh:
            fh.write(doc.model_dump_json() + "\n")
        return doc

    def get(self, document_id: str) -> SourceDocument | None:
        return self._by_id.get(document_id)

    def by_hash(self, h: str) -> SourceDocument | None:
        return self._by_hash.get(h)

    def read_raw(self, document_id: str) -> str | None:
        doc = self._by_id.get(document_id)
        if doc and doc.raw_uri and Path(doc.raw_uri).exists():
            return Path(doc.raw_uri).read_text(encoding="utf-8")
        return None

    def __len__(self) -> int:
        return len(self._by_id)
