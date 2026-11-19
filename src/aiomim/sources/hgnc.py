"""HGNC gene symbols: approved symbol lookup with previous/alias fallbacks."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from urllib.parse import quote

from ..http import HttpError, get_http

log = logging.getLogger(__name__)

BASE = "https://rest.genenames.org/fetch"
CACHE_S = 90 * 86400

# OMIM still uses pre-2005 mitochondrial gene symbols (MTND1, MTTL1, MTATP6 ...).
_MT_LEGACY = re.compile(r"^MT-?(ND[1-6]|ND4L|CO[1-3]|ATP[68]|CYB|RNR[12]|T[A-Z][12]?)$")


@dataclass(frozen=True)
class GeneInfo:
    symbol: str
    hgnc_id: str = ""
    entrez_id: str = ""
    omim_id: str = ""
    location: str = ""
    name: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)
    prev_symbols: tuple[str, ...] = field(default_factory=tuple)


def mito_symbol(symbol: str) -> str:
    """'MTND1' -> 'MT-ND1', 'MTTL1' -> 'MT-TL1'; anything else unchanged (upper-cased)."""
    s = (symbol or "").strip().upper()
    m = _MT_LEGACY.match(s)
    if m:
        return f"MT-{m.group(1)}"
    # Papers on mtDNA disease often write the complex I subunit genes bare ("ND1").
    # No nuclear gene has these symbols, so the mapping is unambiguous.
    if re.fullmatch(r"ND(?:[1-6]|4L)", s):
        return f"MT-{s}"
    return s


def _fetch(field_: str, value: str) -> list[dict]:
    try:
        data = get_http().get_json(f"{BASE}/{field_}/{quote(value, safe='')}", max_age_s=CACHE_S)
    except HttpError as exc:
        log.debug("HGNC %s/%s: %s", field_, value, exc)
        return []
    return ((data or {}).get("response") or {}).get("docs") or []


def _to_info(doc: dict) -> GeneInfo:
    omim = doc.get("omim_id") or []
    if isinstance(omim, str):
        omim = [omim]
    return GeneInfo(
        symbol=doc.get("symbol", ""),
        hgnc_id=doc.get("hgnc_id", ""),
        entrez_id=str(doc.get("entrez_id", "") or ""),
        omim_id=str(omim[0]) if omim else "",
        location=doc.get("location", "") or "",
        name=doc.get("name", "") or "",
        aliases=tuple(doc.get("alias_symbol") or ()),
        prev_symbols=tuple(doc.get("prev_symbol") or ()),
    )


_memo: dict[str, GeneInfo | None] = {}
_lock = threading.Lock()


def gene_info(symbol: str) -> GeneInfo | None:
    raw = (symbol or "").strip()
    if not raw:
        return None
    key = raw.upper()
    with _lock:
        if key in _memo:
            return _memo[key]
    candidates = list(dict.fromkeys([mito_symbol(raw), raw, key]))
    info: GeneInfo | None = None
    for field_ in ("symbol", "prev_symbol", "alias_symbol"):
        for cand in candidates:
            docs = [d for d in _fetch(field_, cand) if d.get("status", "Approved") == "Approved"]
            if len(docs) == 1 or (docs and field_ == "symbol"):
                info = _to_info(docs[0])
                break
            if docs and field_ != "symbol":
                # Ambiguous previous/alias symbol: take it only if unique.
                log.debug("ambiguous HGNC %s %s -> %s", field_, cand, [d.get("symbol") for d in docs])
        if info:
            break
    with _lock:
        _memo[key] = info
    return info


def normalize_symbol(symbol: str) -> str:
    info = gene_info(symbol)
    return info.symbol if info else (symbol or "").strip().upper()
