"""Europe PMC REST: relevance search, reference lists, citations, open-access JATS."""

from __future__ import annotations

import logging

from ..http import HttpError, get_http

log = logging.getLogger(__name__)

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def search(query: str, limit: int = 100, min_year: int | None = None,
           max_year: int | None = None) -> list[str]:
    """PMIDs of MEDLINE records matching `query`, in Europe PMC relevance order."""
    q = f"({query}) AND SRC:MED"
    if min_year or max_year:
        q += f" AND PUB_YEAR:[{min_year or 1800} TO {max_year or 3000}]"
    out: list[str] = []
    cursor = "*"
    while len(out) < limit:
        page = min(1000, max(25, limit - len(out)))
        data = get_http().get_json(f"{BASE}/search", {
            "query": q, "format": "json", "resultType": "idlist", "pageSize": page,
            "cursorMark": cursor,
        }, max_age_s=7 * 86400)
        results = (data.get("resultList") or {}).get("result") or []
        for r in results:
            pmid = r.get("pmid") or (r.get("id") if r.get("source") == "MED" else None)
            if pmid and pmid not in out:
                out.append(str(pmid))
        nxt = data.get("nextCursorMark")
        if not results or not nxt or nxt == cursor:
            break
        cursor = nxt
    return out[:limit]


def _paged_ids(pmid: str, kind: str, list_key: str, item_key: str, limit: int) -> list[str]:
    out: list[str] = []
    page = 1
    while len(out) < limit:
        try:
            data = get_http().get_json(f"{BASE}/MED/{pmid}/{kind}", {
                "format": "json", "page": page, "pageSize": 1000,
            }, max_age_s=30 * 86400)
        except HttpError as exc:
            log.debug("europepmc %s for %s: %s", kind, pmid, exc)
            break
        items = ((data.get(list_key) or {}).get(item_key)) or []
        for it in items:
            if (it.get("source") == "MED" and it.get("id") and str(it["id"]) != pmid
                    and str(it["id"]) not in out):
                out.append(str(it["id"]))
        total = int(data.get("hitCount", 0) or 0)
        if not items or page * 1000 >= total:
            break
        page += 1
    return out[:limit]


def references(pmid: str) -> list[str]:
    """PMIDs in the reference list of `pmid` (only those Europe PMC could match)."""
    return _paged_ids(str(pmid), "references", "referenceList", "reference", 10_000)


def citations(pmid: str, limit: int = 200) -> list[str]:
    """PMIDs of MEDLINE articles that cite `pmid`."""
    return _paged_ids(str(pmid), "citations", "citationList", "citation", limit)


def fulltext_xml(pmcid: str) -> str | None:
    """JATS XML for an article in Europe PMC's open-access subset, else None."""
    if not pmcid:
        return None
    pmcid = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
    try:
        # Europe PMC answers 404 or 500 for "no open-access text"; retry little.
        xml = get_http().get_text(f"{BASE}/{pmcid}/fullTextXML", max_tries=2)
    except HttpError as exc:
        log.debug("no Europe PMC full text for %s: %s", pmcid, exc)
        return None
    head = xml.lstrip()[:500]
    if "<article" not in head and not head.startswith("<?xml"):
        return None
    return xml
