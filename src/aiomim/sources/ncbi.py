"""NCBI E-utilities: OMIM summaries and links, PubMed records and searches."""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable

from lxml import etree

from ..cache import DiskCache
from ..config import get_settings
from ..http import HttpError, get_http
from ..models import Paper, squash

log = logging.getLogger(__name__)

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_BATCH = 150

_PARSER = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False, no_network=True)


def _eutils(endpoint: str, params: dict, *, cache: bool = True, max_age_s: float | None = None) -> Any:
    return get_http().get_json(f"{EUTILS}/{endpoint}.fcgi", {**params, "retmode": "json"},
                               cache=cache, max_age_s=max_age_s)


def _clean_mim(mim: str | int) -> str:
    return re.sub(r"\D", "", str(mim))


# --------------------------------------------------------------------------- #
# OMIM via E-utilities
# --------------------------------------------------------------------------- #


def split_omim_title(title: str) -> tuple[str, str]:
    """'LOEYS-DIETZ SYNDROME 3; LDS3' -> ('LOEYS-DIETZ SYNDROME 3', 'LDS3')."""
    title = squash(title)
    if "; " in title:
        main, _, sym = title.rpartition("; ")
        # OMIM symbols never contain spaces except 'FORMERLY'-style suffixes.
        if sym and len(sym) <= 30 and not re.search(r"\s", sym.replace(", FORMERLY", "")):
            return main.strip(), sym.strip()
    return title, ""


def split_alt_titles(alttitles: str) -> list[str]:
    """OMIM alternative titles are ';;'-separated, each optionally '; SYMBOL'."""
    out: list[str] = []
    for part in (alttitles or "").split(";;"):
        part = squash(part)
        if not part:
            continue
        title, _ = split_omim_title(part)
        if title and title not in out:
            out.append(title)
    return out


def parse_omim_summary(doc: dict) -> dict:
    oid = doc.get("oid", "") or ""
    mim = str(doc.get("uid") or _clean_mim(oid))
    prefix = oid[0] if oid and not oid[0].isdigit() else ""
    title, symbol = split_omim_title(doc.get("title", ""))
    return {
        "mim": mim,
        "prefix": prefix,
        "title": title,
        "alt_titles": split_alt_titles(doc.get("alttitles", "")),
        "symbol": symbol,
        "locus": doc.get("locus", "") or "",
    }


def omim_summaries(mims: Iterable[str]) -> dict[str, dict]:
    mims = [_clean_mim(m) for m in mims if _clean_mim(m)]
    out: dict[str, dict] = {}
    for i in range(0, len(mims), 200):
        chunk = mims[i:i + 200]
        data = _eutils("esummary", {"db": "omim", "id": ",".join(chunk)}, max_age_s=30 * 86400)
        res = data.get("result", {})
        for uid in res.get("uids", []):
            doc = res.get(uid) or {}
            if "error" in doc:
                continue
            out[str(uid)] = parse_omim_summary(doc)
    return out


def omim_summary(mim: str) -> dict:
    mim = _clean_mim(mim)
    got = omim_summaries([mim]).get(mim)
    if not got:
        raise HttpError("OMIM entry not found in E-utilities", status=None, url=f"omim:{mim}")
    return got


def _elink_ids(dbfrom: str, db: str, id_: str, linkname: str | None = None,
               max_age_s: float | None = 30 * 86400) -> list[str]:
    params = {"dbfrom": dbfrom, "db": db, "id": id_}
    if linkname:
        params["linkname"] = linkname
    data = _eutils("elink", params, max_age_s=max_age_s)
    out: list[str] = []
    for ls in data.get("linksets", []) or []:
        for lsdb in ls.get("linksetdbs", []) or []:
            if lsdb.get("dbto") != db:
                continue
            if linkname and lsdb.get("linkname") != linkname:
                continue
            for link in lsdb.get("links", []) or []:
                link = str(link["id"] if isinstance(link, dict) else link)
                if link not in out:
                    out.append(link)
    return out


def omim_cited_pmids(mim: str) -> list[str]:
    return _elink_ids("omim", "pubmed", _clean_mim(mim), "omim_pubmed_cited")


def omim_linked_ids(mim: str, db: str) -> list[str]:
    if db not in {"clinvar", "medgen", "pubmed", "pmc"}:
        raise ValueError(f"unsupported link target {db!r}")
    if db == "pubmed":
        return omim_cited_pmids(mim)
    return _elink_ids("omim", db, _clean_mim(mim))


def _esearch(db: str, term: str, retmax: int, extra: dict | None = None,
             max_age_s: float | None = 7 * 86400) -> list[str]:
    out: list[str] = []
    start = 0
    page = min(retmax, 10000)
    while len(out) < retmax:
        params = {"db": db, "term": term, "retmax": page, "retstart": start, **(extra or {})}
        data = _eutils("esearch", params, max_age_s=max_age_s)
        res = data.get("esearchresult", {})
        ids = [str(x) for x in res.get("idlist", [])]
        out.extend(ids)
        count = int(res.get("count", 0) or 0)
        start += len(ids)
        if not ids or start >= count:
            break
    return out[:retmax]


def omim_search(term: str, retmax: int = 500) -> list[str]:
    return _esearch("omim", term, retmax)


# --------------------------------------------------------------------------- #
# PubMed
# --------------------------------------------------------------------------- #


def _text(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return squash("".join(el.itertext()))


def _year_from(el: etree._Element | None) -> int | None:
    if el is None:
        return None
    y = el.findtext("Year")
    if y and y.strip()[:4].isdigit():
        return int(y.strip()[:4])
    md = el.findtext("MedlineDate")
    if md:
        m = re.search(r"\b(1[89]\d\d|20\d\d)\b", md)
        if m:
            return int(m.group(1))
    return None


def _authors(author_list: etree._Element | None) -> list[str]:
    out: list[str] = []
    if author_list is None:
        return out
    for a in author_list.findall("Author"):
        if a.get("ValidYN", "Y") == "N":
            continue
        coll = a.findtext("CollectiveName")
        if coll:
            out.append(squash(coll))
            continue
        last = squash(a.findtext("LastName") or "")
        init = squash(a.findtext("Initials") or "")
        if not init:
            fore = a.findtext("ForeName") or ""
            init = "".join(w[0] for w in re.split(r"[\s-]+", fore) if w)
        if last:
            out.append(f"{last} {init}".strip())
    return out


def _abstract(abs_el: etree._Element | None) -> str:
    if abs_el is None:
        return ""
    parts = []
    for at in abs_el.findall("AbstractText"):
        txt = _text(at)
        if not txt:
            continue
        label = at.get("Label")
        parts.append(f"{label}: {txt}" if label else txt)
    return "\n".join(parts)


def parse_pubmed_article(el: etree._Element) -> Paper | None:
    """Parse one <PubmedArticle> or <PubmedBookArticle> element."""
    if el.tag == "PubmedArticle":
        mc = el.find("MedlineCitation")
        if mc is None:
            return None
        pmid = (mc.findtext("PMID") or "").strip()
        art = mc.find("Article")
        if art is None or not pmid:
            return None
        journal = art.find("Journal")
        issue = journal.find("JournalIssue") if journal is not None else None
        year = _year_from(issue.find("PubDate")) if issue is not None else None
        if year is None:
            for ad in art.findall("ArticleDate"):
                year = _year_from(ad)
                if year:
                    break
        jname = ""
        if journal is not None:
            jname = squash(journal.findtext("ISOAbbreviation") or "") or squash(journal.findtext("Title") or "")
        if not jname:
            jname = squash(mc.findtext("MedlineJournalInfo/MedlineTA") or "")
        pages = squash(art.findtext("Pagination/MedlinePgn") or "")
        if not pages:
            sp, ep = art.findtext("Pagination/StartPage"), art.findtext("Pagination/EndPage")
            pages = "-".join(x.strip() for x in (sp, ep) if x and x.strip())
        doi = None
        for eloc in art.findall("ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                doi = eloc.text.strip()
        ids = el.find("PubmedData/ArticleIdList")
        pmcid = None
        if ids is not None:
            for aid in ids.findall("ArticleId"):
                kind, val = aid.get("IdType"), (aid.text or "").strip()
                if kind == "pmc" and val:
                    pmcid = val
                elif kind == "doi" and val and not doi:
                    doi = val
        return Paper(
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=_text(art.find("ArticleTitle")) or _text(art.find("VernacularTitle")),
            abstract=_abstract(art.find("Abstract")),
            authors=_authors(art.find("AuthorList")),
            year=year,
            journal=jname,
            volume=squash(issue.findtext("Volume") or "") if issue is not None else "",
            pages=pages,
            pub_types=[_text(p) for p in art.findall("PublicationTypeList/PublicationType")],
            mesh_terms=[_text(d) for d in mc.findall("MeshHeadingList/MeshHeading/DescriptorName")],
        )
    if el.tag == "PubmedBookArticle":
        bd = el.find("BookDocument")
        if bd is None:
            return None
        pmid = (bd.findtext("PMID") or "").strip()
        if not pmid:
            return None
        book = bd.find("Book")
        title = _text(bd.find("ArticleTitle")) or (_text(book.find("BookTitle")) if book is not None else "")
        authors = []
        for al in bd.findall("AuthorList") + (book.findall("AuthorList") if book is not None else []):
            authors = _authors(al)
            if authors:
                break
        year = _year_from(book.find("PubDate")) if book is not None else None
        journal = _text(book.find("BookTitle")) if book is not None else ""
        doi = None
        pmcid = None
        for aid in el.findall("PubmedBookData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = (aid.text or "").strip() or None
            elif aid.get("IdType") == "pmc":
                pmcid = (aid.text or "").strip() or None
        return Paper(
            pmid=pmid, pmcid=pmcid, doi=doi, title=title,
            abstract=_abstract(bd.find("Abstract")), authors=authors, year=year,
            journal=journal,
            pub_types=[_text(p) for p in bd.findall("PublicationType")] or ["Book"],
        )
    return None


def parse_pubmed_xml(xml: str | bytes) -> list[Paper]:
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    root = etree.fromstring(xml, _PARSER)
    if root is None:
        return []
    out = []
    for el in root:
        if el.tag in ("PubmedArticle", "PubmedBookArticle"):
            p = parse_pubmed_article(el)
            if p is not None:
                out.append(p)
    return out


def _record_cache() -> DiskCache:
    return DiskCache(get_settings().http_cache / "pubmed", suffix=".xml")


def _article_pmid(el: etree._Element) -> str:
    if el.tag == "PubmedArticle":
        return (el.findtext("MedlineCitation/PMID") or "").strip()
    return (el.findtext("BookDocument/PMID") or "").strip()


def pubmed_fetch(pmids: list[str]) -> list[Paper]:
    """Fetch PubMed records, cached per PMID, in input order; unknown ids are skipped."""
    wanted = [str(p).strip() for p in pmids if str(p).strip().isdigit()]
    cache = _record_cache()
    raw: dict[str, str] = {}
    missing: list[str] = []
    for pmid in dict.fromkeys(wanted):
        hit = cache.get_text(pmid)
        if hit is not None:
            raw[pmid] = hit
        else:
            missing.append(pmid)
    for i in range(0, len(missing), PUBMED_BATCH):
        chunk = missing[i:i + PUBMED_BATCH]
        xml = get_http().get_text(f"{EUTILS}/efetch.fcgi",
                                  {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"},
                                  cache=False)
        root = etree.fromstring(xml.encode("utf-8"), _PARSER)
        if root is None:
            continue
        for el in root:
            if el.tag not in ("PubmedArticle", "PubmedBookArticle"):
                continue
            pmid = _article_pmid(el)
            if pmid in chunk:
                text = etree.tostring(el, encoding="unicode")
                cache.put_text(pmid, text)
                raw[pmid] = text
    out: list[Paper] = []
    for pmid in wanted:
        if pmid not in raw:
            continue
        try:
            el = etree.fromstring(raw[pmid].encode("utf-8"), _PARSER)
            paper = parse_pubmed_article(el) if el is not None else None
        except etree.XMLSyntaxError:
            paper = None
        if paper is not None:
            out.append(paper)
    return out


def pubmed_search(query: str, retmax: int = 100, min_year: int | None = None,
                  max_year: int | None = None, sort: str = "relevance") -> list[str]:
    extra: dict = {"sort": {"relevance": "relevance", "date": "pub_date",
                            "pub_date": "pub_date"}.get(sort, sort)}
    if min_year or max_year:
        extra.update(datetype="pdat", mindate=str(min_year or 1800), maxdate=str(max_year or 3000))
    return _esearch("pubmed", query, retmax, extra)


def pubmed_similar(pmid: str, n: int = 20) -> list[str]:
    data = _eutils("elink", {"dbfrom": "pubmed", "db": "pubmed", "id": str(pmid),
                             "cmd": "neighbor_score", "linkname": "pubmed_pubmed"},
                   max_age_s=90 * 86400)
    scored: list[tuple[int, str]] = []
    for ls in data.get("linksets", []) or []:
        for lsdb in ls.get("linksetdbs", []) or []:
            if lsdb.get("linkname") != "pubmed_pubmed":
                continue
            for link in lsdb.get("links", []) or []:
                if isinstance(link, dict):
                    scored.append((int(link.get("score", 0) or 0), str(link["id"])))
                else:
                    scored.append((0, str(link)))
    scored.sort(key=lambda t: -t[0])  # stable: equal scores keep NCBI's order
    out = [pid for _, pid in scored if pid != str(pmid)]
    return list(dict.fromkeys(out))[:n]


def pubmed_cited_by(pmid: str) -> list[str]:
    return _elink_ids("pubmed", "pubmed", str(pmid), "pubmed_pubmed_citedin", max_age_s=30 * 86400)
