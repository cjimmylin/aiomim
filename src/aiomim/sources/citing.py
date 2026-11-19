"""Second-hand evidence: what later open-access papers say a paper reported.

For a paper that could not be read in full, find open-access papers that cite it
(Europe PMC `cites:` search), fetch their JATS full text, locate the target in
their reference list, and keep the body paragraphs and table rows whose citations
point at it, trimmed to the sentences around the citation.

    citing_papers(pmid)            who cites it (Europe PMC, lite records)
    fetch_jats(pmcid)              JATS XML (NCBI PMC efetch, else Europe PMC)
    cited_passages(xml, target)    the passages of one citing paper that cite the target
    secondhand_for(paper, exclude) all of it for one paper, capped and ranked, cached

Everything fetched is cached on disk under the data home; a failed or empty
lookup yields no passages, never an exception. Requests carry only the generic
User-Agent and `tool=aiomim`: no email, no API key, nothing about the project.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from lxml import etree

from ..cache import DiskCache, stable_hash
from ..config import get_settings
from ..http import EUTILS_HOST, Http, HttpError, get_http
from ..models import Paper, SecondhandPassage, squash
from .europepmc import BASE as EPMC
from .fulltext import _PARSER, _caption, _clean, _local

log = logging.getLogger(__name__)

# Caps (per target paper unless said otherwise).
MAX_CITING_FETCH = 8      # citing papers whose full text is fetched
MAX_PASSAGES = 6          # passages kept
MAX_PER_CITING = 2        # passages kept from any one citing paper
PASSAGE_CHARS = 1200      # each passage, trimmed to the sentences around the citation
TOTAL_CHARS = 6000        # all passages together

SEARCH_PAGE = 300
MAX_IN_FLIGHT = 4         # requests in flight from this module, process-wide
TIMEOUT_S = 90.0          # a `cites:` search through the proxy takes 25-55 s
TRIES = 3
SEARCH_MAX_AGE_S = 90 * 86400
MISS_TTL_S = 30 * 86400
RESULT_VERSION = 1        # bump to invalidate cached per-target results

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MARKER = "[*]"

_SLOTS = threading.BoundedSemaphore(MAX_IN_FLIGHT)


# --------------------------------------------------------------------------- #
# HTTP: the shared cache and per-host rate limits, longer timeout, nothing personal
# --------------------------------------------------------------------------- #


class _PlainHttp(Http):
    """Same disk cache and host rate limiters as `get_http()`, but a longer timeout,
    fewer tries, and no identification beyond `tool=aiomim` (never email or key)."""

    def __init__(self) -> None:
        super().__init__(timeout=TIMEOUT_S, max_tries=TRIES)
        base = get_http()
        self._limiters, self._lim_lock = base._limiters, base._lim_lock

    def _augment(self, url: str, params: dict | None) -> dict:
        params = dict(params or {})
        if url.startswith(f"https://{EUTILS_HOST}/"):
            params.setdefault("tool", "aiomim")
        return params


_HTTP: _PlainHttp | None = None
_HTTP_LOCK = threading.Lock()


def _http() -> _PlainHttp:
    global _HTTP
    with _HTTP_LOCK:
        if _HTTP is None:
            _HTTP = _PlainHttp()
        return _HTTP


def _miss_cache() -> DiskCache:
    return DiskCache(get_settings().http_cache / "citing_miss", suffix=".json")


def _result_cache() -> DiskCache:
    return DiskCache(get_settings().home / "cache" / "citing", suffix=".json")


# --------------------------------------------------------------------------- #
# Who cites a paper
# --------------------------------------------------------------------------- #


@dataclass
class CitingPaper:
    pmid: str
    pmcid: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    pub_types: list[str] = field(default_factory=list)
    open_access: bool = False

    @property
    def label(self) -> str:
        return Paper(pmid=self.pmid, authors=self.authors, year=self.year).label

    @property
    def kind(self) -> str:
        types = " ".join(self.pub_types).lower()
        if "review" in types:
            return "review"
        if "case report" in types or "case-report" in types or re.search(r"\bcase series\b", self.title, re.I):
            return "case report"
        return "article"


def _authors(author_string: str) -> list[str]:
    return [a.strip() for a in (author_string or "").rstrip(".").split(",") if a.strip()]


def parse_search(data: dict) -> list[CitingPaper]:
    out = []
    for r in ((data or {}).get("resultList") or {}).get("result") or []:
        pmid = str(r.get("pmid") or "")
        if not pmid:
            continue
        year = str(r.get("pubYear") or "")
        out.append(CitingPaper(
            pmid=pmid, pmcid=str(r.get("pmcid") or ""), title=_strip_tags(r.get("title") or ""),
            authors=_authors(r.get("authorString", "")), year=int(year) if year.isdigit() else None,
            pub_types=[t.strip() for t in str(r.get("pubType") or "").split(";") if t.strip()],
            open_access=r.get("isOpenAccess") == "Y",
        ))
    return out


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return squash(text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"'))


def citing_papers(pmid: str) -> list[CitingPaper] | None:
    """Papers that cite `pmid` (first page of up to 300), or None when the lookup failed.

    Filtering to open access happens here, client-side: adding `open_access:y` to
    the query makes Europe PMC time out.
    """
    try:
        with _SLOTS:
            data = _http().get_json(f"{EPMC}/search", {
                "query": f"cites:{pmid}_MED", "resultType": "lite", "pageSize": SEARCH_PAGE, "format": "json",
            }, max_age_s=SEARCH_MAX_AGE_S)
    except (HttpError, OSError, ValueError) as exc:
        log.warning("citing papers of %s: lookup failed: %s", pmid, exc)
        return None
    return parse_search(data)


# --------------------------------------------------------------------------- #
# Full text of a citing paper
# --------------------------------------------------------------------------- #


def _has_body(xml: str) -> bool:
    return "<body" in xml and "<article" in xml


def fetch_jats(pmcid: str) -> tuple[str, str] | None:
    """(JATS XML, source) for an open-access PMC article, else None. Misses are remembered."""
    digits = re.sub(r"\D", "", pmcid or "")
    if not digits:
        return None
    miss = _miss_cache()
    if miss.get_text(f"PMC{digits}", MISS_TTL_S) is not None:
        return None
    attempts = (
        ("ncbi_pmc", EFETCH, {"db": "pmc", "id": digits}),
        ("europepmc", f"{EPMC}/PMC{digits}/fullTextXML", None),
    )
    for source, url, params in attempts:
        try:
            with _SLOTS:
                xml = _http().get_text(url, params)
        except (HttpError, OSError) as exc:
            log.debug("JATS for PMC%s from %s: %s", digits, source, exc)
            continue
        if _has_body(xml):
            return xml, source
        # A body-less reply (no open-access text, or an error page) must not be
        # served from the cache next time as if it were the article.
        try:
            _http().cache.path(_http().cache_key(url, params)).unlink()
        except FileNotFoundError:
            pass
    miss.put_json(f"PMC{digits}", {"pmcid": pmcid})
    return None


# --------------------------------------------------------------------------- #
# Parsing: the reference to the target, and the passages that cite it
# --------------------------------------------------------------------------- #


@dataclass
class Target:
    pmid: str
    doi: str = ""
    title: str = ""
    year: int | None = None
    first_author: str = ""

    @classmethod
    def of(cls, paper: Paper) -> Target:
        first = paper.label.split(" et al.")[0].split(" and ")[0].split(" (")[0] if paper.authors else ""
        return cls(pmid=paper.pmid, doi=(paper.doi or "").lower(), title=paper.title, year=paper.year,
                   first_author=first)


@dataclass
class RawPassage:
    section: str
    kind: str          # "paragraph" | "table"
    text: str          # trimmed, with MARKER where the target is cited
    n_other_refs: int
    full_chars: int


_WORD = re.compile(r"[a-z0-9]+")
_DASHES = "-–—‐‑−"
_RANGE_TEXT = re.compile(rf"^\s*(\d+)\s*[{_DASHES}]\s*(\d+)\s*$")
_STOP = set("a an the of in on and or with for to by from at as is are was were its their this that "
            "associated due novel new case cases report patient patients study".split())


def _norm_words(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def _text(el) -> str:
    return squash("".join(el.itertext())) if el is not None else ""


def _ref_matches(ref, target: Target) -> bool:
    for pid in ref.iter():
        if _local(pid) not in ("pub-id", "object-id", "ext-link"):
            continue
        value = _text(pid).lower()
        kind = (pid.get("pub-id-type") or "").lower()
        if kind == "pmid" and value == target.pmid:
            return True
        if target.doi and (kind == "doi" or "doi" in value) and value.endswith(target.doi):
            return True
    if not target.title:
        return False
    want = _norm_words(target.title)
    if len(want) < 4:
        return False
    title_el = next((e for e in ref.iter() if _local(e) == "article-title"), None)
    year_el = next((e for e in ref.iter() if _local(e) == "year"), None)
    year = re.search(r"\d{4}", _text(year_el)) if year_el is not None else None
    if year and target.year and abs(int(year.group(0)) - target.year) > 1:
        return False
    if title_el is not None:
        have = _norm_words(_text(title_el))
        return SequenceMatcher(None, want, have, autojunk=False).ratio() >= 0.85
    # A citation with no marked-up title: look for the title's words in order.
    have = " " + " ".join(_norm_words(_text(ref))) + " "
    return " " + " ".join(want[:12]) + " " in have


def find_reference(root, target: Target) -> set[str]:
    """IDs of the reference-list entries that are the target paper."""
    return {ref.get("id") for ref in root.iter() if _local(ref) == "ref" and ref.get("id")
            and _ref_matches(ref, target)}


class _Refs:
    """Reference ids in list order, and their numeric labels, for expanding ranges."""

    def __init__(self, root):
        self.order: dict[str, int] = {}
        self.by_label: dict[int, str] = {}
        ids: list[str] = []
        for ref in root.iter():
            if _local(ref) == "ref" and ref.get("id"):
                rid = ref.get("id")
                self.order[rid] = len(ids)
                ids.append(rid)
                label = next((e for e in ref if _local(e) == "label"), None)
                num = re.sub(r"\D", "", _text(label)) if label is not None else ""
                if num:
                    self.by_label.setdefault(int(num), rid)
        self.ids = ids

    def between(self, a: str, b: str) -> set[str]:
        if a not in self.order or b not in self.order:
            return {a, b}
        i, j = sorted((self.order[a], self.order[b]))
        return set(self.ids[i:j + 1]) if j - i <= 60 else {a, b}

    def labels(self, lo: int, hi: int) -> set[str]:
        if hi < lo or hi - lo > 60:
            return set()
        return {self.by_label[n] for n in range(lo, hi + 1) if n in self.by_label}


def _bibr(el) -> bool:
    return _local(el) == "xref" and el.get("ref-type") == "bibr"


def _xref_targets(xrefs: list, refs: _Refs) -> dict[int, set[str]]:
    """For each xref (by id()), the reference ids it stands for, expanding ranges.

    "[3–7]" may be one xref whose text is the range, or two xrefs (3 and 7) joined
    by a dash in the text between them; either way it cites 3, 4, 5, 6 and 7.
    """
    out: dict[int, set[str]] = {}
    for i, x in enumerate(xrefs):
        ids = set((x.get("rid") or "").split())
        m = _RANGE_TEXT.match(_text(x))
        if m:
            ids |= refs.labels(int(m.group(1)), int(m.group(2)))
        out[id(x)] = out.get(id(x), set()) | ids
        nxt = xrefs[i + 1] if i + 1 < len(xrefs) else None
        tail = (x.tail or "").strip()
        if (nxt is not None and x.getnext() is nxt and tail and all(c in _DASHES for c in tail)
                and x.get("rid") and nxt.get("rid")):
            span = refs.between(x.get("rid").split()[0], nxt.get("rid").split()[-1])
            out[id(x)] |= span
            out[id(nxt)] = out.get(id(nxt), set()) | span
    return out


_SKIP_BLOCK = {"sec", "p", "table-wrap", "table-wrap-group", "fig", "fig-group", "list", "disp-quote",
               "boxed-text", "supplementary-material", "def-list", "statement", "ref-list", "fn-group",
               "media", "graphic", "inline-graphic", "app", "app-group", "ack", "notes"}


def _own_xrefs(el) -> list:
    """Citation xrefs of `el` itself, not of block elements nested inside it."""
    out = []

    def walk(node):
        for child in node:
            name = _local(child)
            if not name:
                continue
            if _bibr(child):
                out.append(child)
            elif name not in _SKIP_BLOCK:
                walk(child)
    walk(el)
    return out


def _render(el, cites: dict[int, set[str]], target_ids: set[str]) -> str:
    """Inline text of `el`: citations of the target become MARKER, numbered ones vanish,
    author-year ones stay as text (followed by MARKER when they are the target)."""
    out: list[str] = []

    def walk(node):
        if node.text:
            out.append(node.text)
        for child in node:
            name = _local(child)
            if not name:
                pass
            elif _bibr(child):
                text = _text(child)
                numeric = bool(re.fullmatch(rf"[\d\s,{_DASHES}]*", text))
                hit = bool(cites.get(id(child), set()) & target_ids)
                if not numeric:
                    out.append(text)
                if hit:
                    out.append(f" {MARKER} ")
            elif name in _SKIP_BLOCK or name in ("xref",) and child.get("ref-type") == "fn":
                pass
            else:
                walk(child)
                if name in ("td", "th"):
                    out.append(" | ")
            if child.tail:
                out.append(child.tail)
    walk(el)
    text = re.sub(r"\s+", " ", "".join(out))
    marker = re.escape(MARKER)
    # One citation group, one marker: "[*] – [*]" (a range) -> "[*]".
    text = re.sub(rf"{marker}(?:[\s,;{_DASHES}]*{marker})+", MARKER, text)
    # Brackets left around the marker by dropped numbers: "( [*] - )" -> " [*]".
    text = re.sub(rf"[\[(][\s,;{_DASHES}]*{marker}[\s,;{_DASHES}]*[\])]", f" {MARKER}", text)
    # A marker set after the sentence's full stop belongs to that sentence.
    text = re.sub(rf"([.;,:])\s*{marker}[\s{_DASHES}]*", rf" {MARKER}\1 ", text)
    text = _clean(text)
    return re.sub(r"\s{2,}", " ", text).strip(" |")


_ABBREV = re.compile(r"(?:\bet al|\be\.g|\bi\.e|\bFig|\bFigs|\bvs|\bca|\bapprox|\bNo|\bRef|\bRefs|\bresp|\bcf|\b[A-Z])\.$")


def sentences(text: str) -> list[str]:
    out, start = [], 0
    for m in re.finditer(r"[.!?]\s+(?=[A-Z(\[0-9])", text):
        if _ABBREV.search(text[start:m.start() + 1]):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def trim_around(text: str, limit: int = PASSAGE_CHARS) -> str:
    """The sentence(s) citing the target, widened by neighbours while under `limit` characters."""
    if len(text) <= limit:
        return text
    sents = sentences(text)
    hits = [i for i, s in enumerate(sents) if MARKER in s]
    if not hits:
        return text[:limit].rsplit(" ", 1)[0] + " …"
    lo, hi = hits[0], hits[-1]
    if sum(len(s) + 1 for s in sents[lo:hi + 1]) > limit:
        lo = hi = hits[0]
    chosen = " ".join(sents[lo:hi + 1])
    if len(chosen) > limit:
        at = chosen.find(MARKER)
        start = max(0, min(at - limit * 2 // 3, len(chosen) - limit))
        cut = chosen[start:start + limit]
        return ("… " if start else "") + cut.strip() + " …"
    grew = True
    while grew:
        grew = False
        for cand in ((lo - 1, hi), (lo, hi + 1)):
            a, b = cand
            if a < 0 or b >= len(sents):
                continue
            longer = " ".join(sents[a:b + 1])
            if len(longer) <= limit:
                lo, hi, chosen, grew = a, b, longer, True
    return ("… " if lo > 0 else "") + chosen + (" …" if hi < len(sents) - 1 else "")


def _section_of(el) -> str:
    titles = []
    node = el.getparent()
    while node is not None:
        if _local(node) in ("sec", "app", "boxed-text"):
            title = next((c for c in node if _local(c) == "title"), None)
            if title is not None and _text(title):
                titles.append(_text(title))
        node = node.getparent()
    titles.reverse()
    return " > ".join(titles[-2:])


def _main_article(root):
    if _local(root) == "article":
        return root
    return next((e for e in root.iter() if _local(e) == "article"), None)


def cited_passages(xml: str, target: Target) -> tuple[bool, list[RawPassage]]:
    """(reference found, passages) for one citing paper's JATS."""
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data, _PARSER)
    except etree.XMLSyntaxError:
        return False, []
    article = _main_article(root) if root is not None else None
    if article is None:
        return False, []
    target_ids = find_reference(article, target)
    if not target_ids:
        return False, []
    refs = _Refs(article)
    parts = [c for c in article if _local(c) in ("body", "floats-group")]
    out: list[RawPassage] = []
    seen: set[str] = set()

    def add(section: str, kind: str, raw: str, cited: set[str]):
        if MARKER not in raw:
            return
        text = trim_around(raw)
        if text in seen:
            return
        seen.add(text)
        out.append(RawPassage(section=section, kind=kind, text=text,
                              n_other_refs=len(cited - target_ids), full_chars=len(raw)))

    for part in parts:
        for el in part.iter():
            name = _local(el)
            if name == "p" and not any(_local(a) in ("table-wrap", "fig", "ref-list", "fn-group", "caption")
                                       for a in el.iterancestors()):
                xrefs = _own_xrefs(el)
                cites = _xref_targets(xrefs, refs)
                cited = set().union(*cites.values()) if cites else set()
                if cited & target_ids:
                    add(_section_of(el), "paragraph", _render(el, cites, target_ids), cited)
            elif name == "table-wrap":
                caption = _caption(el, "Table")
                header = None
                for tr in (t for t in el.iter() if _local(t) == "tr"):
                    cells = [c for c in tr if _local(c) in ("td", "th")]
                    if header is None:
                        header = " | ".join(_text(c) for c in cells)
                        if all(_local(c) == "th" for c in cells) or _local(tr.getparent()) == "thead":
                            continue
                    xrefs = [x for c in cells for x in c.iter() if _bibr(x)]
                    cites = _xref_targets(xrefs, refs)
                    cited = set().union(*cites.values()) if cites else set()
                    if not cited & target_ids:
                        continue
                    row = " | ".join(_render(c, cites, target_ids) for c in cells)
                    text = (f"{caption}\nColumns: {header}\nRow: {row}" if caption
                            else f"Columns: {header}\nRow: {row}")
                    label = caption.split(".")[0] if caption else "Table"
                    add(label, "table", text, cited)
    return True, out


# --------------------------------------------------------------------------- #
# Choosing citing papers and passages
# --------------------------------------------------------------------------- #


def _content_words(text: str) -> set[str]:
    return {w for w in _norm_words(text) if len(w) > 2 and w not in _STOP}


def rank_citing(candidates: list[CitingPaper], target: Target, exclude: set[str]) -> list[CitingPaper]:
    """Open-access citing papers with a PMCID, not the entry's own, most useful first:
    reviews and case reports ahead, then by how much of the target's title they share."""
    want = _content_words(target.title)
    eligible = [c for c in candidates if c.open_access and c.pmcid and c.pmid not in exclude and c.pmid != target.pmid]

    def score(c: CitingPaper) -> tuple[float, int]:
        overlap = len(want & _content_words(c.title)) / max(1, len(want))
        bonus = 0.4 if c.kind in ("review", "case report") else 0.0
        return (overlap + bonus, c.year or 0)
    return sorted(eligible, key=score, reverse=True)


_VARIANT = re.compile(r"\b[cgmnp]\.\s?[A-Za-z*]*\d+[\w>*_]*|\b[ACGT]\d{2,5}[ACGT]\b|\b\d+[ACGT]\s?>\s?[ACGT]\b"
                      r"|\b(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val)\d+"
                      r"(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter|fs|\*)"
                      r"|\b[A-Z]\d{2,4}[A-Z*]\b")
_PEOPLE = re.compile(r"\b(?:patients?|probands?|famil(?:y|ies)|sibs?|siblings?|individuals?|affected|homozygous|"
                     r"heterozygous|compound|de novo|consanguineous|onset|carriers?|kindreds?|pedigrees?|"
                     r"boys?|girls?|males?|females?|children)\b", re.I)


def passage_score(p: RawPassage, target: Target) -> float:
    """Few other references and concrete content (numbers, patients, variants) rank first."""
    text = p.text.replace(MARKER, " ")
    score = 0.5 * min(6, len(re.findall(r"\b\d+(?:\.\d+)?\b", text)))
    score += 2.0 if _VARIANT.search(text) else 0.0
    score += 0.5 * min(4, len(_PEOPLE.findall(text)))
    if target.first_author and re.search(rf"\b{re.escape(target.first_author)}\b", text):
        score += 2.0   # names the target's authors: the passage is about that paper
    score -= 0.6 * min(10, p.n_other_refs)
    return round(score, 2)


def select_passages(found: list[tuple[CitingPaper, RawPassage]], target: Target) -> list[tuple[CitingPaper, RawPassage, float]]:
    ranked = sorted(((c, p, passage_score(p, target)) for c, p in found), key=lambda t: -t[2])
    chosen, per, total = [], {}, 0
    for c, p, s in ranked:
        if len(chosen) >= MAX_PASSAGES:
            break
        if per.get(c.pmid, 0) >= MAX_PER_CITING or total + len(p.text) > TOTAL_CHARS:
            continue
        chosen.append((c, p, s))
        per[c.pmid] = per.get(c.pmid, 0) + 1
        total += len(p.text)
    return chosen


# --------------------------------------------------------------------------- #
# Everything for one paper
# --------------------------------------------------------------------------- #


def secondhand_for(paper: Paper, exclude: set[str] | frozenset[str] = frozenset()) -> dict[str, Any]:
    """Second-hand passages for `paper`, with a record of how they were found.

    Returns {"pmid", "n_citing", "n_open_access", "n_eligible", "fetched": [...], "passages": [...],
    "n_chars", "seconds", "error", "cached"}; `passages` are `SecondhandPassage` dicts plus a
    "score". Never raises.
    """
    key = stable_hash("citing", RESULT_VERSION, paper.pmid, sorted(exclude),
                      (MAX_CITING_FETCH, MAX_PASSAGES, MAX_PER_CITING, PASSAGE_CHARS, TOTAL_CHARS))
    cache = _result_cache()
    try:
        hit = cache.get_json(key)
    except ValueError:
        hit = None
    if hit is not None:
        return {**hit, "cached": True}

    started = time.time()
    record: dict[str, Any] = {"pmid": paper.pmid, "n_citing": 0, "n_open_access": 0, "n_eligible": 0,
                              "fetched": [], "passages": [], "n_chars": 0, "error": ""}
    try:
        target = Target.of(paper)
        found = citing_papers(paper.pmid)
        if found is None:
            record["error"] = "citation lookup failed"
        else:
            record["n_citing"] = len(found)
            record["n_open_access"] = sum(1 for c in found if c.open_access and c.pmcid)
            ranked = rank_citing(found, target, set(exclude))
            record["n_eligible"] = len(ranked)
            pool: list[tuple[CitingPaper, RawPassage]] = []
            for c in ranked[:MAX_CITING_FETCH]:
                got = fetch_jats(c.pmcid)
                row = {"pmid": c.pmid, "pmcid": c.pmcid, "label": c.label, "kind": c.kind, "title": c.title,
                       "source": got[1] if got else None, "reference_found": False, "n_passages": 0}
                if got:
                    row["reference_found"], passages = cited_passages(got[0], target)
                    row["n_passages"] = len(passages)
                    pool.extend((c, p) for p in passages)
                record["fetched"].append(row)
            for c, p, s in select_passages(pool, target):
                passage = SecondhandPassage(
                    citing_pmid=c.pmid, citing_pmcid=c.pmcid, citing_label=c.label, citing_title=c.title,
                    citing_year=c.year, section=p.section, kind=p.kind, text=p.text, n_other_refs=p.n_other_refs)
                record["passages"].append({**passage.model_dump(), "score": s})
            record["n_chars"] = sum(len(p["text"]) for p in record["passages"])
    except Exception as exc:  # noqa: BLE001 - optional evidence must never fail a run
        log.warning("second-hand evidence for %s failed: %s", paper.pmid, exc)
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["seconds"] = round(time.time() - started, 1)
    if not record["error"]:
        cache.put_json(key, record)
    return {**record, "cached": False}


def passages_of(record: dict[str, Any]) -> list[SecondhandPassage]:
    fields = set(SecondhandPassage.model_fields)
    return [SecondhandPassage(**{k: v for k, v in p.items() if k in fields}) for p in record.get("passages", [])]
