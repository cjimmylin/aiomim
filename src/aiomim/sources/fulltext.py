"""Open-access full text: Europe PMC JATS first, then NCBI BioC.

Only text from the PMC open-access / author-manuscript collections is used;
nothing is scraped from publisher sites.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

from lxml import etree

from ..cache import DiskCache
from ..config import get_settings
from ..http import HttpError, get_http
from ..models import Paper
from . import europepmc
from .ncbi import pubmed_fetch

log = logging.getLogger(__name__)

BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{id}/unicode"
MIN_BODY_CHARS = 1500
MISS_TTL_S = 7 * 86400

_PARSER = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False, no_network=True)

# Sections that carry no scientific content for curation.
_DROP_TITLE = re.compile(
    r"^\s*(\d+(\.\d+)*\.?\s*)?("
    r"acknowledg|funding|financial (support|disclosure)|grant|conflicts? of interest|competing interest|"
    r"declaration of (competing|interest)|disclosure|duality of interest|author'?s'? contribution|"
    r"contributors|supplementa|supporting information|electronic supplementary|additional (file|information)|"
    r"data availability|availability of data|abbreviations|consent for publication|"
    r"ethics approval and consent|web resources|url|references?$|bibliography|footnotes|notes$|"
    r"orcid|publisher'?s note|declarations$|credit authorship|contributor information|associated data|"
    r"author information|financial disclosures?|study funding"
    r")", re.I)
_DROP_SEC_TYPES = {
    "supplementary-material", "COI-statement", "funding-information", "acknowledgment",
    "acknowledgments", "acknowledgements", "author-contributions", "data-availability", "ethics-statement",
    "ack", "contrib-info", "ref-list", "fn-group", "notes", "funding", "conflict", "COI",
    "supplementary-materials", "display-objects-skip",
}
_BLOCK = {"sec", "p", "table-wrap", "table-wrap-group", "fig", "fig-group", "list", "disp-quote",
          "boxed-text", "supplementary-material", "def-list", "statement", "glossary", "app",
          "app-group", "ref-list", "fn-group", "ack", "notes", "speech", "verse-group",
          "disp-formula-group", "media"}
_SKIP_INLINE = {"supplementary-material", "media", "graphic", "inline-graphic", "alternatives-skip",
                "object-id", "label-skip"}


def _local(el) -> str:
    tag = el.tag
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    # Remnants of dropped citation markers: "[ ]", "[, ]", "( ; )", "[–]".
    text = re.sub(r"\s*[\[(][\s,;–\-]*[\])]", "", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    return text.strip()


def _numeric_cite(xref) -> bool:
    """True for numbered citation markers ("12", "3-5"); False for author-year text."""
    t = "".join(xref.itertext()).strip()
    return bool(re.fullmatch(r"[\d\s,–\-]*", t)) and not re.search(r"\b(1[6-9]|20)\d\d\b", t)


def _inline(el, out: list[str] | None = None) -> str:
    """Text of `el`, skipping citation xrefs and nested block elements."""
    top = out is None
    if out is None:
        out = []
    if el.text:
        out.append(el.text)
    for child in el:
        name = _local(child)
        if not name:  # comments / PIs
            pass
        elif name == "xref" and child.get("ref-type") in ("bibr", "fn") and _numeric_cite(child):
            pass
        elif name in _BLOCK or name in _SKIP_INLINE:
            pass
        elif name in ("break",):
            out.append(" ")
        else:
            _inline(child, out)
            if name in ("td", "th", "label"):
                out.append(" ")
        if child.tail:
            out.append(child.tail)
    return _clean("".join(out)) if top else ""


def _caption(el, kind: str) -> str:
    label = _inline(el.find("label")) if el.find("label") is not None else ""
    cap = el.find("caption")
    cap_text = ""
    if cap is not None:
        parts = []
        for c in cap:
            if _local(c) in ("title", "p"):
                parts.append(_inline(c))
        cap_text = " ".join(p for p in parts if p) or _inline(cap)
    head = (label or kind).rstrip(".:")
    return f"{head}. {cap_text}".strip() if cap_text else (label or "")


def _table_rows(table) -> list[str]:
    rows = []
    for tr in table.iter():
        if _local(tr) != "tr":
            continue
        cells = [_inline(c) for c in tr if _local(c) in ("td", "th")]
        if any(cells):
            rows.append(" | ".join(cells))
    return rows


class _Renderer:
    def __init__(self) -> None:
        self.blocks: list[str] = []

    def add(self, text: str) -> None:
        text = text.strip()
        if text:
            self.blocks.append(text)

    def table_wrap(self, el) -> None:
        lines = []
        cap = _caption(el, "Table")
        if cap:
            lines.append(cap)
        for table in el.iter():
            if _local(table) == "table":
                lines.extend(_table_rows(table))
        foot = None
        for c in el:
            if _local(c) == "table-wrap-foot":
                foot = c
        if foot is not None:
            for c in foot.iter():
                if _local(c) in ("p",) and _inline(c):
                    lines.append(_inline(c))
        self.add("\n".join(lines))

    def render(self, el, depth: int = 0) -> None:
        name = _local(el)
        if not name:
            return
        if name in ("ref-list", "ack", "fn-group", "notes", "supplementary-material", "media",
                    "glossary", "graphic", "permissions", "funding-group"):
            return
        if name in ("sec", "app", "boxed-text"):
            title_el = el.find("title")
            title = _inline(title_el) if title_el is not None else ""
            if (el.get("sec-type") in _DROP_SEC_TYPES or (el.get("id") or "").startswith("notes")
                    or (title and _DROP_TITLE.match(title))):
                return
            if title:
                self.add(f"{'#' * min(2 + depth, 4)} {title}")
            for child in el:
                if _local(child) in ("title", "label"):
                    continue
                self.render(child, depth + 1)
            return
        if name in ("p", "disp-quote", "statement", "speech"):
            self.add(_inline(el))
            for child in el:  # block content nested inside a paragraph
                if _local(child) in _BLOCK:
                    self.render(child, depth)
            return
        if name in ("table-wrap",):
            self.table_wrap(el)
            return
        if name == "fig":
            self.add(_caption(el, "Figure"))
            return
        if name in ("list", "def-list"):
            items = []
            for it in el:
                if _local(it) in ("list-item", "def-item"):
                    items.append("- " + " ".join(_inline(p) for p in it.iter()
                                                 if _local(p) in ("p", "term", "def") and _inline(p)))
            self.add("\n".join(i for i in items if i.strip() != "-"))
            return
        if name in ("disp-formula",):
            self.add(_inline(el))
            return
        # Containers: table-wrap-group, fig-group, app-group, body, floats-group, ...
        for child in el:
            self.render(child, depth)


def jats_to_text(xml: str) -> str:
    """Body of a JATS article as plain text with '## ' section headings."""
    if not xml:
        return ""
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data, _PARSER)
    except etree.XMLSyntaxError:
        return ""
    if root is None:
        return ""
    r = _Renderer()
    # Only the main article (not sub-articles / responses).
    article = root if _local(root) == "article" else next(
        (e for e in root.iter() if _local(e) == "article"), root)
    for part in article:
        name = _local(part)
        if name == "body":
            r.render(part, 0)
        elif name == "floats-group":
            r.render(part, 0)
        elif name == "back":
            for child in part:
                if _local(child) == "app-group" or _local(child) == "app":
                    r.render(child, 0)
    return "\n\n".join(r.blocks)


# --------------------------------------------------------------------------- #
# BioC
# --------------------------------------------------------------------------- #

_BIOC_SKIP = {"REF", "COMP_INT", "ACK_FUND", "AUTH_CONT", "SUPPL", "ABBR", "TITLE", "ABSTRACT",
              "KEYWORD", "REVIEW_INFO"}


def _bioc_table(p: dict) -> str:
    xml = (p.get("infons") or {}).get("xml")
    if xml:
        try:
            el = etree.fromstring(xml.encode("utf-8"), _PARSER)
            if el is not None:
                rows = _table_rows(el)
                if rows:
                    return "\n".join(rows)
        except etree.XMLSyntaxError:
            pass
    text = p.get("text", "")
    rows = [r.strip("\t ") for r in re.split(r"\t \t", text)]
    return "\n".join(" | ".join(c.strip() for c in r.split("\t")) for r in rows if r)


def bioc_to_text(data) -> str:
    """Reassemble BioC JSON passages (in document order) into plain text."""
    docs = []
    for coll in data if isinstance(data, list) else [data]:
        docs.extend((coll or {}).get("documents") or [])
    if not docs:
        return ""
    blocks: list[str] = []
    skip_level: int | None = None
    for p in docs[0].get("passages") or []:
        inf = p.get("infons") or {}
        sec = (inf.get("section_type") or "").upper()
        typ = (inf.get("type") or "").lower()
        text = (p.get("text") or "").strip()
        if sec in _BIOC_SKIP or typ in ("ref", "front", "abstract", "abstract_title_1"):
            continue
        if not text:
            continue
        m = re.match(r"title_?(\d*)$", typ)
        if m:
            level = int(m.group(1) or 1)
            if skip_level is not None and level > skip_level:
                continue
            skip_level = None
            if _DROP_TITLE.match(text):
                skip_level = level
                continue
            blocks.append(f"{'#' * min(1 + level, 4)} {_clean(text)}")
            continue
        if skip_level is not None:
            continue
        if typ == "table":
            blocks.append(_bioc_table(p))
        elif typ == "table_caption":
            blocks.append(f"Table. {_clean(text)}")
        elif typ in ("fig_caption", "fig_title_caption"):
            blocks.append(f"Figure. {_clean(text)}")
        else:
            blocks.append(_clean(text))
    return "\n\n".join(b for b in blocks if b)


def bioc_fulltext(id_: str) -> str | None:
    try:
        raw = get_http().get_text(BIOC.format(id=id_), max_age_s=MISS_TTL_S, max_tries=3)
    except HttpError as exc:
        log.debug("BioC %s: %s", id_, exc)
        return None
    if not raw.lstrip().startswith(("[", "{")):
        return None  # "[Error] : No result can be found."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return bioc_to_text(data) or None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def _miss_cache() -> DiskCache:
    return DiskCache(get_settings().http_cache / "fulltext_miss", suffix=".json")


def fetch_fulltext(paper: Paper) -> tuple[str, str] | None:
    """(text, source) from the first open-access source with a real body, else None."""
    try:
        # Text the user supplies for papers they have the right to read:
        # <AIOMIM_HOME>/fulltext/<pmid>.txt takes precedence over any download.
        local = get_settings().home / "fulltext" / f"{paper.pmid}.txt"
        if local.is_file():
            text = local.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) >= MIN_BODY_CHARS:
                return text, "local"
        miss = _miss_cache()
        if miss.get_text(paper.pmid, MISS_TTL_S) is not None:
            return None
        if paper.pmcid:
            xml = europepmc.fulltext_xml(paper.pmcid)
            if xml:
                text = jats_to_text(xml)
                if len(text) >= MIN_BODY_CHARS:
                    return text, "europepmc"
        for id_ in [x for x in (paper.pmcid, paper.pmid) if x]:
            text = bioc_fulltext(id_)
            if text and len(text) >= MIN_BODY_CHARS:
                return text, "ncbi_bioc"
        miss.put_json(paper.pmid, {"pmcid": paper.pmcid})
    except Exception as exc:  # never fail a pipeline run over optional text
        log.warning("full text lookup failed for %s: %s", paper.pmid, exc)
    return None


def load_papers(pmids: list[str], with_fulltext: bool = True, max_workers: int = 4) -> list[Paper]:
    papers = pubmed_fetch(pmids)
    if not with_fulltext or not papers:
        return papers

    def attach(p: Paper) -> Paper:
        got = fetch_fulltext(p)
        if got:
            return p.model_copy(update={"fulltext": got[0], "fulltext_source": got[1]})
        return p

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        return list(pool.map(attach, papers))
