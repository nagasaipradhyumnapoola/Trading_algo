"""Deterministic entity resolution + document/event clustering.

Maps company mentions (symbol / name / ISIN / alias) to instrument ids using the
instrument master — no LLM guessing. Also clusters documents/events so syndicated
copies and same-day duplicates count as one information event.
"""

from __future__ import annotations

import re
from datetime import date

from services.ingestion.instruments import InstrumentMaster

_SUFFIXES = re.compile(r"\b(LIMITED|LTD\.?|PVT\.?|PRIVATE|INDIA|CORPORATION|CORP\.?|INC\.?)\b")
_NONWORD = re.compile(r"[^A-Z0-9 ]+")


def normalize_name(name: str) -> str:
    s = name.upper()
    s = _NONWORD.sub(" ", s)
    s = _SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


class EntityResolver:
    def __init__(self, master: InstrumentMaster, aliases: dict[str, str] | None = None) -> None:
        self._by_symbol: dict[str, str] = {}
        self._by_isin: dict[str, str] = {}
        self._by_name: dict[str, str] = {}
        for inst in master:
            self._by_symbol[inst.symbol.upper()] = inst.instrument_id
            if inst.isin:
                self._by_isin[inst.isin.upper()] = inst.instrument_id
            self._by_name[normalize_name(inst.name)] = inst.instrument_id
        self._aliases = {k.upper(): v for k, v in (aliases or {}).items()}

    def resolve_mention(self, mention: str) -> str | None:
        m = mention.strip().upper()
        if m in self._by_symbol:
            return self._by_symbol[m]
        if m in self._by_isin:
            return self._by_isin[m]
        if m in self._aliases:
            return self._aliases[m]
        return self._by_name.get(normalize_name(mention))

    def resolve_text(self, text: str) -> set[str]:
        found: set[str] = set()
        upper = text.upper()
        for sym, iid in self._by_symbol.items():
            if re.search(rf"\b{re.escape(sym)}\b", upper):
                found.add(iid)
        norm = normalize_name(text)
        for name, iid in self._by_name.items():
            if name and name in norm:
                found.add(iid)
        for alias, iid in self._aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                found.add(iid)
        return found


def cluster_documents(docs: list[dict]) -> list[list[dict]]:
    """Group near-duplicate docs. Key: content_hash if present, else
    (instrument_id, event_type, session date). Returns clusters (each a list)."""
    groups: dict[object, list[dict]] = {}
    for d in docs:
        if d.get("content_hash"):
            key: object = ("hash", d["content_hash"])
        else:
            day = d.get("date")
            day = day.isoformat() if isinstance(day, date) else day
            key = ("evt", d.get("instrument_id"), d.get("event_type"), day)
        groups.setdefault(key, []).append(d)
    return list(groups.values())
