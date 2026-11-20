"""Experiment C: what kinds of error the claim-level audit catches, beyond single values.

`auditcheck` showed that the audit flags a changed number, zygosity, residue or mode of
inheritance (60 of 60) and passes the unaltered paragraphs. This module plants six other
kinds of error in paragraphs the audit had passed and audits them again, each against an
unaltered control audited with fresh calls in the same run:

C1  citation swap, other entry   the paragraph's citation (pmid and in-text label) becomes a
                                 paper of another entry
C2  citation swap, same entry    ... becomes another paper of the same entry; truth only for
                                 claims naming a variant absent from the new paper's text
C3  conflation                   a variant-naming sentence of the paragraph about paper A is
                                 moved into the paragraph about paper B (same entry)
C4  over-citation                a second, unrelated paper is added to the citation
C5  dropped qualifier            a restricting phrase is deleted by rule
C6  omitted finding              a supported sentence is deleted; the audit is not meant to
                                 see this, so a separate completeness check is tested

Everything is planted by rule (no model), recorded with before and after text, and audited
with the audit's own prompts (`verify._decompose`, `verify._audit_prompt`), keeping every
paper's verdict on every claim, not only the best one.

    python -m aiomim.auditstress build      items, seeded  -> runs/<run>/audit_stress/items.json
    python -m aiomim.auditstress run        audits, controls, completeness checks (resumable)
    python -m aiomim.auditstress precision  citation precision from the stored audits (no new calls)
    python -m aiomim.auditstress summarise  -> results/<run>/audit_stress.json | .md

Curator-written wording (gold paragraphs, fact lists) is read only to build prompts for the
natural-omission judge; it is never written to `runs/.../audit_stress/` or `results/`.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import random
import re
import statistics
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel

from .grounding import SourceIndex, tokens
from .kg import frameshift_short, nucleotide_key, protein_key
from .models import EntryParagraph, GeneratedEntry, Paper, squash

log = logging.getLogger(__name__)

STRATEGY = "kg"               # as the single-value planted test
NATURAL_STRATEGY = "direct"   # where the stored omission judgements are
CLASSES = ("C1", "C2", "C3", "C4", "C5", "C6")
CLASS_NAMES = {
    "C1": "citation swap, other entry", "C2": "citation swap, same entry", "C3": "conflation",
    "C4": "over-citation", "C5": "dropped qualifier", "C6": "omitted finding",
}
CHUNK = 5                     # items audited together; fixed, so a pilot's calls are reused by the full run
DEFAULT_N = 30                # reduced from the design's 60 at the user's request
DEFAULT_SEED = 23
SALT = "auditstress-1"
CALL_CAP = 600                # reduced from 1,200 at the user's request
NATURAL_FACT_CAP = 60
MAX_PER_ENTRY = 3
OUT_DIR = "audit_stress"
FLAGGED = ("unsupported", "contradicted")
SEVERITY = {"contradicted": 4, "unsupported": 3, "partially_supported": 2, "supported": 1, "not_checkable": 0}

# --------------------------------------------------------------------------- #
# Text: sentences, labels, variants
# --------------------------------------------------------------------------- #

_ABBREV = re.compile(r"(?:\bet al|\be\.g|\bi\.e|\bvs|\bcf|\bca|\bapprox|\bFigs?|\b[Nn]o|\b[cpgmnr]|\b[A-Z]|\bSt|\bDr)\.$")


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each sentence; 'et al.', 'e.g.', 'c.' and initials do not end one."""
    spans, start = [], 0
    for m in re.finditer(r"[.!?](?=\s+[A-Z(\[])", text):
        if _ABBREV.search(text[start:m.end()]):
            continue
        spans.append((start, m.end()))
        start = m.end()
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text) and text[start:].strip():
        spans.append((start, len(text.rstrip())))
    return spans


def sentences(text: str) -> list[str]:
    return [text[a:b] for a, b in sentence_spans(text)]


def label_forms(label: str) -> tuple[str, str] | None:
    """'Seliem et al. (2000)' -> ('Seliem et al. (2000)', 'Seliem et al., 2000'); None for a PMID label."""
    m = re.match(r"^(.*) \((\d{4}|n\.d\.)\)$", label or "")
    if not m or m.group(1).startswith("PMID "):
        return None
    return label, f"{m.group(1)}, {m.group(2)}"


def find_label(text: str, label: str) -> bool:
    forms = label_forms(label)
    return bool(forms) and (forms[0] in text or forms[1] in text)


def relabel(text: str, old: str, new: str) -> tuple[str, int]:
    """Replace every narrative and parenthetical citation of `old` by `new`."""
    a, b = label_forms(old) or (None, None), label_forms(new) or (None, None)
    if not a[0] or not b[0]:
        return text, 0
    n = text.count(a[0]) + text.count(a[1])
    return text.replace(a[0], b[0]).replace(a[1], b[1]), n


def add_citation(text: str, old: str, new: str) -> tuple[str, str]:
    """Cite `new` beside the first citation of `old`: 'A (2000)' -> 'A (2000) and B (2010)', '(A, 2000' -> '(A, 2000; B, 2010'."""
    a, b = label_forms(old), label_forms(new)
    if not a or not b:
        return text, ""
    i, j = text.find(a[0]), text.find(a[1])
    if i >= 0 and (j < 0 or i <= j):
        return text[:i] + f"{a[0]} and {b[0]}" + text[i + len(a[0]):], "narrative"
    if j >= 0:
        return text[:j] + f"{a[1]}; {b[1]}" + text[j + len(a[1]):], "parenthetical"
    return text, ""


_AA3 = "ala|arg|asn|asp|cys|gln|glu|gly|his|ile|leu|lys|met|phe|pro|ser|thr|trp|tyr|val|sec"
_AA1 = "ACDEFGHIKLMNPQRSTVWY"
_VARIANT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("p", re.compile(rf"\b(?:{_AA3})\d+-?to-?(?:{_AA3}|ter|stop)\b", re.I)),                 # arg123-to-trp
    ("p", re.compile(rf"\b(?:{_AA3})\d+(?:_(?:{_AA3})\d+)?(?:{_AA3})?(?:fs|del|dup|ins|ext|ter|\*)[a-z*\d]*",
                     re.I)),                                                                  # GLU296LYSFS, Arg5del
    ("p", re.compile(rf"\bp\.\(?(?:{_AA3})\d+(?:_(?:{_AA3})\d+)?(?:{_AA3}|ter|\*|=|fs|del|dup|ins|ext)[a-z*\d]*",
                     re.I)),                                                                  # p.Arg123Trp
    ("p", re.compile(rf"\b(?:{_AA3})\d+(?:{_AA3}|ter)\b", re.I)),                            # Arg123Trp
    ("p", re.compile(rf"\bp\.\(?[{_AA1}*]\d+(?:_[{_AA1}]\d+)?(?:[{_AA1}*=X]|fs|del|dup|ins|ext)[A-Za-z*\d]*")),
    ("p", re.compile(rf"(?<![\w.])[{_AA1}]\d{{1,5}}(?:[{_AA1}*X]|fs\*?\d*|del)(?![\w])")),    # R123W, A2V
    ("c", re.compile(r"\b[cgmn]\.[-*]?\d+(?:[+-]\d+)?(?:_[-*]?\d+(?:[+-]\d+)?)?"
                     r"(?:[ACGT]>[ACGT]|delins[ACGT]+|del[ACGT]*|dup[ACGT]*|ins[ACGT]+|inv)")),
    ("c", re.compile(r"(?<![\w.])-?\d+(?:[+-]\d+)?[ACGT]-[ACGT]\b")),                         # OMIM 367C-T
    ("c", re.compile(r"(?<![\w.])[ACGT]\d{2,6}[ACGT](?![\w])")),                              # legacy C367T
]


def _normalise_hgvs(text: str) -> str:
    text = re.sub(r"(\d)\s+([ACGT])\s*>\s*([ACGT])", r"\1\2>\3", text)
    return re.sub(r"([ACGT])\s*>\s*([ACGT])", r"\1>\2", text)


def mention_keys(mention: str, kind: str) -> set[str]:
    """Exact keys of one variant mention (protein and/or nucleotide), plus position keys ('pos:...')."""
    keys: set[str] = set()
    pk = protein_key(mention) if kind == "p" or re.fullmatch(r"[ACGT]\d+[ACGT]", mention) else ""
    nk = nucleotide_key(mention) if kind == "c" else ""
    if kind == "p" and re.fullmatch(r"[ACGT]\d+[ACGT]", mention):
        nk = nucleotide_key(mention)   # 'G131A' may be either; take both
    for k in (pk, nk):
        if k:
            keys.add(k)
            if short := frameshift_short(k):
                keys.add(short)
            if m := re.match(r"^p\.([A-Z*])(\d+)", k):
                keys.add(f"pos:p{m.group(1)}{m.group(2)}")
            if m := re.match(r"^[cgmn]\.(-?\*?\d+(?:[+-]\d+)?)", k):
                keys.add(f"pos:c{m.group(1)}")
    return keys


def variant_mentions(text: str) -> dict[str, set[str]]:
    """Variant names found in `text`, each with its keys; mentions that give no key are dropped."""
    text = _normalise_hgvs(text or "")
    out: dict[str, set[str]] = {}
    for kind, pattern in _VARIANT_PATTERNS:
        for m in pattern.finditer(text):
            mention = m.group(0).rstrip(").,;")
            keys = mention_keys(mention, kind)
            if keys:
                out.setdefault(mention, set()).update(keys)
    return out


def exact_keys(mentions: dict[str, set[str]]) -> set[str]:
    return {k for keys in mentions.values() for k in keys if not k.startswith("pos:")}


def text_variant_keys(text: str) -> set[str]:
    return {k for keys in variant_mentions(text).values() for k in keys}


def occurs(mention: str, keys: set[str], paper_keys: set[str], paper_text_lower: str) -> bool:
    """Generous: the variant occurs if any of its keys, its position, or its raw name is in the paper."""
    if keys & paper_keys:
        return True
    raw = re.sub(r"^[pc]\.", "", mention, flags=re.I).lower()
    return len(raw) >= 4 and raw in paper_text_lower


# --------------------------------------------------------------------------- #
# C5 deletion rules
# --------------------------------------------------------------------------- #

_NUMW = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
_PEOPLE = (r"(?:patients?|famil(?:y|ies)|individuals?|probands?|cases?|sibs?|siblings?|children|members?|"
           r"kindreds?|pedigrees?|subjects?|carriers?|alleles?|chromosomes?|controls?)")


def _rule_count(text: str) -> list[tuple[int, int]]:
    spans = [m.span() for m in re.finditer(
        rf",?\s(?:in|of|among) {_NUMW} (?:of|out of) (?:the )?{_NUMW}(?: (?:[a-z-]+ ){{0,2}}?{_PEOPLE})?\b", text, re.I)]
    spans += [m.span() for m in re.finditer(rf"\s\({_NUMW} (?:of|out of) {_NUMW}(?: [a-z-]+){{0,3}}\)", text, re.I)]
    spans += [m.span() for m in re.finditer(r"\s\(\d+/\d+\)", text)]
    return spans


def _rule_zygosity(text: str) -> list[tuple[int, int]]:
    spans = [m.span() for m in re.finditer(
        r",?\s(?:in (?:the )?|in a )?(?:compound )?(?:homozygous|heterozygous|hemizygous|heteroplasmic|homoplasmic) "
        r"(?:state|form)\b", text)]
    spans += [m.span() for m in re.finditer(
        r"\b(?:compound )?(?:homozygous|heterozygous|hemizygous|heteroplasmic|homoplasmic) (?=[a-z])(?!state|form)",
        text)]
    return spans


def _rule_single(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in re.finditer(
        r",?\s(?:in|from|of) (?:one|a single) (?:[A-Za-z-]+ ){0,2}?"
        r"(?:family|kindred|pedigree|patient|proband|individual|child|boy|girl|man|woman|case)\b", text)]


def _rule_negation(text: str) -> list[tuple[int, int]]:
    spans = [m.span(1) for m in re.finditer(
        r"\b(?:did|does|do|was|were|is|are|has|have|had|could|can|would|should)( not)\b", text)]
    spans += [m.span(1) for m in re.finditer(r"\b(?:had|showed|found|with|revealed|detected|identified)( no)\b", text)]
    return spans


def _rule_hedge(text: str) -> list[tuple[int, int]]:
    spans = [m.span() for m in re.finditer(
        r"\b(?:most )?(?:possibly|probably|presumably|putatively|potentially|apparently)\s", text)]
    spans += [m.span() for m in re.finditer(r"\b(?:most )?likely\s(?!to\b)", text)]
    spans += [m.span() for m in re.finditer(r"\bputative\s", text)]
    return spans


C5_RULES: list[tuple[str, Callable[[str], list[tuple[int, int]]]]] = [
    ("count", _rule_count), ("zygosity", _rule_zygosity), ("single family or patient", _rule_single),
    ("negation", _rule_negation), ("hedge", _rule_hedge),
]


def _fix_article(text: str, at: int) -> str:
    """After a deletion at `at`, make a preceding 'a'/'an' agree with the next word."""
    m = re.search(r"\b(a|an|A|An) $", text[:at])
    nxt = re.match(r"\s*(\w)", text[at:])
    if not m or not nxt:
        return text
    want = "an" if nxt.group(1).lower() in "aeiou" else "a"
    if m.group(1).lower() == want:
        return text
    word = want if m.group(1)[0].islower() else want.capitalize()
    return text[:m.start(1)] + word + text[m.end(1):]


def delete_span(text: str, span: tuple[int, int]) -> str:
    a, b = span
    out = text[:a] + text[b:]
    out = _fix_article(out, a)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;:)])", r"\1", out)
    return re.sub(r",\s*,", ",", out).strip()


def apply_rule(text: str, rule: str) -> dict[str, Any] | None:
    """The first deletion `rule` finds in `text`, with the sentence before and after."""
    fn = dict(C5_RULES)[rule]
    spans = sorted(fn(text))
    if not spans:
        return None
    span = spans[0]
    after = delete_span(text, span)
    if after == text:
        return None
    sent = next(((a, b) for a, b in sentence_spans(text) if a <= span[0] < b), (0, len(text)))
    before_sentence = text[sent[0]:sent[1]]
    after_sentence = delete_span(before_sentence, (span[0] - sent[0], span[1] - sent[0]))
    return {"rule": rule, "deleted": text[span[0]:span[1]].strip(" ,"), "before_sentence": before_sentence,
            "after_sentence": after_sentence, "altered_text": after, "offset": span[0]}


# --------------------------------------------------------------------------- #
# Distinctive tokens (C6 matching)
# --------------------------------------------------------------------------- #

_YEAR = re.compile(r"^(?:19|20)\d\d$")


def distinctive(sentence: str) -> dict[str, Any]:
    """Variant keys and numbers of a sentence, years and MIM numbers left out."""
    keys = exact_keys(variant_mentions(sentence))
    variant_text = " ".join(variant_mentions(sentence))
    stripped = re.sub(r"\b[A-Z][\w'-]+(?: and [A-Z][\w'-]+| et al\.)?,? \(?\d{4}\)?", " ", sentence)
    for v in variant_mentions(sentence):
        stripped = stripped.replace(v, " ")
    numbers = sorted({n for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", stripped)
                      if not _YEAR.match(n) and len(n) != 6}, key=lambda s: (len(s), s))
    return {"keys": sorted(keys), "numbers": numbers, "has_variant_text": bool(variant_text)}


def mechanical_match(sentence: str, omission_texts: list[str]) -> bool | None:
    """Does any listed omission carry the sentence's variant (by key) or all its numbers? None if nothing distinctive."""
    d = distinctive(sentence)
    if not d["keys"] and not d["numbers"]:
        return None
    for text in omission_texts:
        if d["keys"]:
            if set(d["keys"]) & exact_keys(variant_mentions(text)):
                return True
            continue
        toks = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", text))
        if all(n in toks for n in d["numbers"]):
            return True
    return False


# --------------------------------------------------------------------------- #
# Item construction
# --------------------------------------------------------------------------- #


def base_pool(run_dir: Path, strategy: str = STRATEGY) -> list[dict[str, Any]]:
    """Paragraphs the audit passed, chosen as `auditcheck.plant_errors` chooses them."""
    pool = []
    for path in sorted(run_dir.glob(f"*/entry.{strategy}.json")):
        entry = GeneratedEntry.model_validate_json(path.read_text())
        for para in entry.all_paragraphs():
            if para.status == "supported" and len(para.pmids) == 1 and len(para.text) > 150:
                pool.append({"mim": path.parent.name, "paragraph_id": para.id, "pmid": para.pmids[0],
                             "text": para.text})
    return pool


def draft_about(entry: GeneratedEntry, pmid: str, replace: dict[str, str] | None = None) -> str:
    """The draft's text citing `pmid` (as `evaluate._draft_text_for`, intro included), with paragraphs replaced."""
    replace = replace or {}
    chunks = []
    if entry.intro and pmid in entry.intro.checked_pmids:
        chunks.append(f"[Introduction] {replace.get(entry.intro.id, entry.intro.text)}")
    for section in entry.sections:
        for para in section.paragraphs:
            if pmid in para.checked_pmids:
                text = replace.get(para.id, para.text)
                if text:
                    chunks.append(f"[{section.heading}] {text}")
    for av in entry.allelic_variants:
        for para in av.paragraphs:
            if pmid in para.checked_pmids:
                text = replace.get(para.id, para.text)
                if text:
                    chunks.append(f"[Allelic variant {av.name}] {text}")
    return "\n\n".join(chunks)


_AUTHOR_LABEL = re.compile(r"\bet al\.|\b[A-Z][\w'-]+ and [A-Z][\w'-]+ \(\d{4}|\(\d{4}\)|, \d{4}[;)]")


def load_as_run(entry_dir: Path) -> dict[str, Paper]:
    """The entry's papers at the access level the run recorded: full text fetched only for papers the run
    read in full (cached), so a paper the run had only as an abstract is not looked up again (and cannot
    gain text the writer never had)."""
    from .sources.fulltext import fetch_fulltext
    from .sources.ncbi import pubmed_fetch
    records = json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))
    level = {r["pmid"]: r.get("content_level") for r in records}
    out = {}
    for p in pubmed_fetch([r["pmid"] for r in records]):
        if level.get(p.pmid) == "fulltext":
            got = fetch_fulltext(p)
            if got:
                p = p.model_copy(update={"fulltext": got[0], "fulltext_source": got[1]})
        if level.get(p.pmid) and p.content_level != level[p.pmid]:
            log.warning("[%s] paper %s reads as %s, run had %s", entry_dir.name, p.pmid, p.content_level,
                        level[p.pmid])
        out[p.pmid] = p
    return out


class Library:
    """Papers and entries of a run, loaded on demand."""

    def __init__(self, run_dir: Path, strategy: str = STRATEGY, loader: Callable[[Path], dict[str, Paper]] | None = None):
        self.run_dir, self.strategy = run_dir, strategy
        self._store = loader is None
        self._loader = loader or load_as_run
        self._papers: dict[str, dict[str, Paper]] = {}
        self._entries: dict[str, GeneratedEntry] = {}
        self._keys: dict[str, set[str]] = {}

    def papers(self, mim: str) -> dict[str, Paper]:
        """The entry's papers; kept in `audit_stress/papers/` after the first load (fetches that fail are not
        cached by the HTTP layer and would be retried, slowly, on every run)."""
        if mim not in self._papers:
            store = self.run_dir / OUT_DIR / "papers" / f"{mim}.json"
            if self._loader is not None and store.exists() and self._store:
                self._papers[mim] = {k: Paper.model_validate(v) for k, v in json.loads(store.read_text()).items()}
            else:
                self._papers[mim] = self._loader(self.run_dir / mim)
                if self._store:
                    _save_json(store, {k: v.model_dump() for k, v in self._papers[mim].items()})
        return self._papers[mim]

    def entry(self, mim: str, strategy: str | None = None) -> GeneratedEntry:
        key = f"{mim}/{strategy or self.strategy}"
        if key not in self._entries:
            self._entries[key] = GeneratedEntry.model_validate_json(
                (self.run_dir / mim / f"entry.{strategy or self.strategy}.json").read_text())
        return self._entries[key]

    def paper(self, pmid: str) -> Paper:
        for papers in self._papers.values():
            if pmid in papers:
                return papers[pmid]
        raise KeyError(pmid)

    def source(self, pmid: str) -> str:
        from .verify import MAX_SOURCE_CHARS
        return self.paper(pmid).source_text(MAX_SOURCE_CHARS)

    def keys(self, pmid: str) -> set[str]:
        if pmid not in self._keys:
            self._keys[pmid] = text_variant_keys(self.source(pmid))
        return self._keys[pmid]

    def variant_status(self, text: str, pmid: str) -> list[dict[str, Any]]:
        """Each variant named in `text`, and whether it occurs in paper `pmid`'s text."""
        lower = _normalise_hgvs(self.source(pmid)).lower()
        return [{"mention": m, "occurs": occurs(m, k, self.keys(pmid), lower)}
                for m, k in variant_mentions(text).items()]


def _readable(paper: Paper) -> bool:
    return paper.content_level in ("abstract", "fulltext")


def build_items(run_dir: Path, n: int = DEFAULT_N, seed: int = DEFAULT_SEED, lib: Library | None = None,
                classes: tuple[str, ...] = CLASSES) -> dict[str, Any]:
    """All classes' items, chosen from one seeded order of the pool so that classes share paragraphs."""
    lib = lib or Library(run_dir)
    rng = random.Random(seed)
    pool = base_pool(run_dir)
    rng.shuffle(pool)
    mims = sorted({b["mim"] for b in pool})
    for mim in mims:
        lib.papers(mim)
    pool = [b for b in pool if b["pmid"] in lib.papers(b["mim"])]
    others = [(mim, pmid) for mim in mims for pmid, p in sorted(lib.papers(mim).items()) if _readable(p)]
    by_entry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in pool:
        by_entry[b["mim"]].append(b)

    def base(b: dict[str, Any]) -> dict[str, Any]:
        return {"mim": b["mim"], "paragraph_id": b["paragraph_id"], "pmid": b["pmid"], "text": b["text"],
                "content_level": lib.papers(b["mim"])[b["pmid"]].content_level}

    def other_entry_paper(b: dict[str, Any], r: random.Random) -> str:
        own = set(lib.papers(b["mim"]))
        while True:
            mim, pmid = r.choice(others)
            if mim != b["mim"] and pmid not in own:
                return pmid

    def make(cls: str, b: dict[str, Any], r: random.Random) -> dict[str, Any] | None:
        paper = lib.papers(b["mim"])[b["pmid"]]
        if cls in ("C1", "C2", "C4") and not find_label(b["text"], paper.label):
            return None
        if cls == "C1":
            new = other_entry_paper(b, r)
            text, n_rel = relabel(b["text"], paper.label, lib.paper(new).label)
            return {**base(b), "altered_text": text, "pmids": [new], "new_pmid": new, "relabelled": n_rel,
                    "new_content_level": lib.paper(new).content_level, "truth_known": True}
        if cls == "C2":
            if not variant_mentions(b["text"]):
                return None
            cands = [pm for pm, p in sorted(lib.papers(b["mim"]).items()) if pm != b["pmid"] and _readable(p)]
            if not cands:
                return None
            new = r.choice(cands)
            text, n_rel = relabel(b["text"], paper.label, lib.paper(new).label)
            status = lib.variant_status(b["text"], new)
            return {**base(b), "altered_text": text, "pmids": [new], "new_pmid": new, "relabelled": n_rel,
                    "new_content_level": lib.paper(new).content_level, "variants": status,
                    "truth_known": any(not v["occurs"] for v in status)}
        if cls == "C3":
            spans = sentence_spans(b["text"])
            moved = [(a, z) for a, z in spans if variant_mentions(b["text"][a:z])
                     and not _AUTHOR_LABEL.search(b["text"][a:z])]
            if not moved or len(spans) < 2:
                return None
            a, z = r.choice(moved)
            sentence = b["text"][a:z]
            s_keys = exact_keys(variant_mentions(sentence))
            targets = [t for t in by_entry[b["mim"]] if t["pmid"] != b["pmid"]
                       and not (s_keys & exact_keys(variant_mentions(t["text"])))]
            if not targets:
                return None
            t = r.choice(targets)
            t_spans = sentence_spans(t["text"])
            at = r.randint(1, len(t_spans))
            cut = t_spans[at - 1][1]
            text = (t["text"][:cut].rstrip() + " " + sentence + " " + t["text"][cut:].lstrip()).strip()
            status = lib.variant_status(sentence, t["pmid"])
            return {"mim": b["mim"], "paragraph_id": t["paragraph_id"], "pmid": t["pmid"], "text": t["text"],
                    "content_level": lib.papers(b["mim"])[t["pmid"]].content_level,
                    "source_paragraph_id": b["paragraph_id"], "source_pmid": b["pmid"], "source_text": b["text"],
                    "moved_sentence": sentence, "inserted_after_sentence": at, "altered_text": text,
                    "pmids": [t["pmid"]], "variants": status, "moved_keys": sorted(s_keys),
                    "truth_known": bool(status) and all(not v["occurs"] for v in status)}
        if cls == "C4":
            new = other_entry_paper(b, r)
            text, how = add_citation(b["text"], paper.label, lib.paper(new).label)
            if not how:
                return None
            return {**base(b), "altered_text": text, "pmids": [b["pmid"], new], "added_pmid": new,
                    "citation_form": how, "new_content_level": lib.paper(new).content_level, "truth_known": True}
        if cls == "C6":
            entry = lib.entry(b["mim"])
            spans = sentence_spans(b["text"])
            if len(spans) < 2:
                return None
            cands = []
            for k, (a, z) in enumerate(spans[1:], 1):
                sentence = b["text"][a:z]
                d = distinctive(sentence)
                if not d["keys"] and not d["numbers"]:
                    continue
                rest = draft_about(entry, b["pmid"], {b["paragraph_id"]: b["text"][:a] + b["text"][z:]})
                rest_keys = exact_keys(variant_mentions(rest))
                rest_nums = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", rest))
                if (set(d["keys"]) - rest_keys) or (not d["keys"] and set(d["numbers"]) - rest_nums):
                    cands.append((k, a, z))
            if not cands:
                return None
            k, a, z = r.choice(cands)
            altered = (b["text"][:a].rstrip() + " " + b["text"][z:].lstrip()).strip()
            return {**base(b), "altered_text": altered, "pmids": [b["pmid"]], "deleted_sentence": b["text"][a:z],
                    "deleted_index": k, "distinctive": distinctive(b["text"][a:z]),
                    "draft_before": draft_about(entry, b["pmid"]),
                    "draft_after": draft_about(entry, b["pmid"], {b["paragraph_id"]: altered}), "truth_known": True}
        raise ValueError(cls)

    items: dict[str, list[dict[str, Any]]] = {}
    for cls in classes:
        r = random.Random(f"{seed}:{cls}")
        chosen: list[dict[str, Any]] = []
        per_entry: Counter = Counter()
        if cls == "C5":
            quota = max(1, n // len(C5_RULES)) + 2
            per_rule: Counter = Counter()
            for i, b in enumerate(pool):
                if len(chosen) >= n:
                    break
                if per_entry[b["mim"]] >= MAX_PER_ENTRY:
                    continue
                order = C5_RULES[i % len(C5_RULES):] + C5_RULES[:i % len(C5_RULES)]
                for rule, _ in order:
                    if per_rule[rule] >= quota:
                        continue
                    done = apply_rule(b["text"], rule)
                    if done:
                        per_rule[rule] += 1
                        per_entry[b["mim"]] += 1
                        chosen.append({**base(b), **done, "pmids": [b["pmid"]], "truth_known": True})
                        break
        else:
            for b in pool:
                if len(chosen) >= n:
                    break
                if per_entry[b["mim"]] >= MAX_PER_ENTRY:
                    continue
                item = make(cls, b, r)
                if item:
                    per_entry[b["mim"]] += 1
                    chosen.append(item)
        for i, item in enumerate(chosen):
            item["id"] = f"{cls}.{i}"
        items[cls] = chosen

    return {"run": run_dir.name, "strategy": STRATEGY, "seed": seed, "n_per_class": n, "chunk": CHUNK,
            "pool_size": len(pool), "items": items, "controls": control_list(items)}


def control_list(items: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Unaltered paragraphs every class needs, ordered item-index first so a pilot's are a prefix."""
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    longest = max((len(v) for v in items.values()), default=0)
    for i in range(longest):
        for cls in CLASSES:
            if i >= len(items.get(cls, [])):
                continue
            it = items[cls][i]
            pairs = [(it["paragraph_id"], it["pmid"], it["text"])]
            if cls == "C3":
                pairs.append((it["source_paragraph_id"], it["source_pmid"], it["source_text"]))
            for pid, pmid, text in pairs:
                key = (it["mim"], pid)
                if key not in seen:
                    seen[key] = {"id": f"ctl.{len(seen)}", "mim": it["mim"], "paragraph_id": pid, "pmid": pmid,
                                 "text": text, "first_needed_by": i}
    return list(seen.values())


def natural_targets(run_dir: Path, strategy: str = NATURAL_STRATEGY) -> list[dict[str, Any]]:
    """Per (entry, paper): curator facts stated in the text the writer had but absent from the draft.

    Only gold paragraphs citing one paper. Ids only, never wording.
    """
    out = []
    for path in sorted(run_dir.glob(f"*/gaps.{strategy}.frozen.json")):
        frozen = json.loads(path.read_text())
        by_pmid: dict[str, dict[str, Any]] = {}
        for para in frozen.get("paragraphs", []):
            if len(para.get("pmids") or []) != 1:
                continue
            target = [f["id"] for f in para.get("facts", []) if f.get("draft_status") == "absent"
                      and f.get("in_text") == "yes"]
            rec = by_pmid.setdefault(para["pmids"][0], {"mim": path.parent.name, "pmid": para["pmids"][0],
                                                         "gold_keys": [], "target_fact_ids": [],
                                                         "content_level": para.get("content_level")})
            rec["gold_keys"].append(para["key"])
            rec["target_fact_ids"] += target
        out += [r for r in by_pmid.values() if r["target_fact_ids"]]
    return out


def select_natural(targets: list[dict[str, Any]], cap: int, seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """At most `cap` target facts: seeded order, papers readable in full first; grouped back by paper."""
    rank = {"fulltext": 0, "abstract": 1, "title": 2}
    rng = random.Random(f"{seed}:natural")
    pairs = [(t, fid) for t in targets for fid in t["target_fact_ids"]]
    rng.shuffle(pairs)
    pairs.sort(key=lambda p: rank.get(p[0].get("content_level") or "", 3))
    chosen: dict[tuple[str, str], dict[str, Any]] = {}
    for t, fid in pairs[:cap]:
        rec = chosen.setdefault((t["mim"], t["pmid"]), {**t, "target_fact_ids": []})
        rec["target_fact_ids"].append(fid)
    return list(chosen.values())


# --------------------------------------------------------------------------- #
# The audit, keeping every paper's verdict
# --------------------------------------------------------------------------- #


def status_of(verdicts: list[str]) -> str:
    if not verdicts:
        return "unverified"
    if any(v in FLAGGED for v in verdicts):
        return "flagged"
    if "partially_supported" in verdicts:
        return "partial"
    return "supported"


def audit_paragraphs(paras: list[EntryParagraph], papers: dict[str, Paper], llm) -> dict[str, dict[str, Any]]:
    """`verify.verify_entry` step for step (same prompts, same best-verdict rule), keeping per-paper verdicts."""
    from .verify import VERIFY_SYSTEM, XAudit, _RANK, _audit_prompt, _decompose

    targets = [p for p in paras if any(pmid in papers for pmid in p.checked_pmids)]
    if not targets:
        return {}
    claims_by_para = _decompose(targets, papers, llm)
    per_paper: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    claim_text: dict[str, str] = {}
    claim_pmids: dict[str, list[str]] = {}
    by_id = {p.id: p for p in targets}
    for para_id, claims in claims_by_para.items():
        for n, claim in enumerate(claims, 1):
            cid = f"{para_id}#{n}"
            claim_text[cid], claim_pmids[cid] = claim.text, claim.pmids
            for pmid in claim.pmids:
                per_paper[pmid][para_id].append((cid, claim.text))
    pmids = sorted(per_paper)
    built = [_audit_prompt(papers[pmid], [(by_id[pid], cl) for pid, cl in per_paper[pmid].items()]) for pmid in pmids]
    replies = llm.map("verify", VERIFY_SYSTEM, [b[0] for b in built], XAudit)
    judged: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    failed: dict[str, str] = {}
    for pmid, (_, source), reply in zip(pmids, built, replies):
        if isinstance(reply, Exception):
            failed[pmid] = f"{type(reply).__name__}: {str(reply)[:200]}"
            continue
        index = SourceIndex(source)
        for v in reply.verdicts:
            cid = v.claim_id.strip().strip("[]")
            if cid not in claim_text or pmid not in claim_pmids[cid] or pmid in judged[cid]:
                continue
            verdict, quote = v.verdict, squash(v.evidence_quote)
            verified = bool(quote) and index.contains(quote)
            if verdict == "supported" and not verified:
                verdict = "partially_supported"
            judged[cid][pmid] = {"verdict": verdict, "model_verdict": v.verdict, "quote_verified": verified,
                                 "explanation": squash(v.explanation)}
    out: dict[str, dict[str, Any]] = {}
    for para in targets:
        claims = claims_by_para.get(para.id)
        if claims is None:
            out[para.id] = {"status": status_of(["not_checkable"]), "error": "claims not extracted",
                            "claims": [], "verdicts": ["not_checkable"]}
            continue
        rows = []
        for n, claim in enumerate(claims, 1):
            per = judged.get(f"{para.id}#{n}", {})
            # The order of `per` follows the replies; max() keeps the first best, as verify_entry does.
            best = max(per.values(), key=lambda c: _RANK[c["verdict"]])["verdict"] if per else "not_checkable"
            rows.append({"text": claim.text, "pmids": claim.pmids, "per_paper": per, "verdict": best})
        verdicts = [r["verdict"] for r in rows]
        out[para.id] = {"status": status_of(verdicts), "claims": rows, "verdicts": verdicts,
                        "failed_papers": {pm: failed[pm] for pm in para.checked_pmids if pm in failed}}
    return out


# --------------------------------------------------------------------------- #
# Completeness check and judges
# --------------------------------------------------------------------------- #

COMPLETE_SYSTEM = """\
You are checking a draft entry for OMIM (Online Mendelian Inheritance in Man) for completeness against \
one of the papers it cites. You are given the paper's text as it was available (the full text where it \
could be read, otherwise the abstract, or only the title) and everything the draft says that cites \
this paper.

List the findings this paper reports that the draft does not convey: findings of the kind an OMIM \
entry records about a paper, such as who was studied and how many patients or families, their \
ancestry, clinical, imaging and laboratory features, ages, inheritance and segregation, each variant \
with its nucleotide and protein change and zygosity, de novo status, functional results, and the \
authors' conclusions about the disorder or the gene. A finding counts as conveyed if the draft states \
it in any wording or notation; if the draft states it only in part, list it with the missing detail. \
Do not list background the paper attributes to earlier work, methods without a result, or statistics \
that are not about the patients, the variants or the functional results. Judge only against the \
supplied text, not against what you know of the subject.

For each omitted finding give `finding`, one self-contained sentence, and `quote`, the passage of the \
paper that states it, copied character for character from the paper text (one continuous span, at \
most about 50 words). Return an empty list if the draft conveys every such finding.\
"""


class XOmission(BaseModel):
    finding: str
    quote: str


class XOmissions(BaseModel):
    omissions: list[XOmission]


MATCH_SYSTEM = """\
You are comparing a sentence that was deleted from a draft with a numbered list of FINDINGS that a \
checker reports the draft omits. Say which listed findings state the content of the deleted sentence: \
"full" if the finding states what the sentence asserts (wording and notation may differ; the same \
variant written another way is the same variant), "partial" if it states part of what the sentence \
asserts. List only findings that match; return an empty list if none does.\
"""


class XMatch(BaseModel):
    n: int
    match: Literal["full", "partial"]


class XMatches(BaseModel):
    matches: list[XMatch]


FACTS_SYSTEM = """\
You are given a numbered list of FACTS about one paper, taken from a curator's summary of it, and a \
numbered list of FINDINGS that a checker reports a draft omitted about the same paper. For every fact, \
say which findings state it: `stating` lists findings that state the fact (wording and notation may \
differ; the same variant written another way is the same variant), `stating_part` lists findings that \
state part of the fact. Return one row for every fact number, with empty lists where no finding states it.\
"""


class XFactMatch(BaseModel):
    n: int
    stating: list[int]
    stating_part: list[int]


class XFactMatches(BaseModel):
    facts: list[XFactMatch]


def complete_prompt(paper: Paper, source: str, draft: str) -> str:
    available = {"fulltext": "full text", "abstract": "abstract only", "title": "title only"}[paper.content_level]
    return (f"Paper: {paper.label}, PMID {paper.pmid} (text supplied: {available}).\n\n<paper>\n{source}\n</paper>\n\n"
            f"<draft>\n{draft or '(the draft has no text citing this paper)'}\n</draft>")


def numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {squash(t)}" for i, t in enumerate(items, 1))


def match_prompt(sentence: str, findings: list[str]) -> str:
    return f"<deleted_sentence>\n{sentence}\n</deleted_sentence>\n\n<findings>\n{numbered(findings)}\n</findings>"


def facts_prompt(facts: list[str], findings: list[str]) -> str:
    return f"<facts>\n{numbered(facts)}\n</facts>\n\n<findings>\n{numbered(findings)}\n</findings>"


def checked_omissions(reply: XOmissions | Exception, source: str) -> dict[str, Any]:
    if isinstance(reply, Exception):
        return {"error": f"{type(reply).__name__}: {str(reply)[:200]}", "omissions": []}
    index = SourceIndex(source)
    return {"error": None, "omissions": [{"finding": squash(o.finding), "quote": squash(o.quote),
                                          "quote_verified": bool(squash(o.quote)) and index.contains(o.quote)}
                                         for o in reply.omissions if squash(o.finding)]}


# --------------------------------------------------------------------------- #
# Call budget and LLM wiring
# --------------------------------------------------------------------------- #


class BudgetBackend:
    """Wraps the CLI backend: counts every model call made (fresh, not cached) and stops at the cap."""

    def __init__(self, inner, ledger: Path, cap: int):
        self.inner, self.ledger, self.cap = inner, ledger, cap
        self.lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        if self.ledger.exists():
            return json.loads(self.ledger.read_text())
        return {"calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "safety_stops": 0,
                "refusals": 0, "errors": 0, "by_stage": {}}

    def _write(self, data: dict[str, Any]) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ledger.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1))
        tmp.replace(self.ledger)

    def complete(self, **kw):
        from .llm import LLMLimitReached, LLMRefusal
        with self.lock:
            data = self._read()
            if data["calls"] >= self.cap:
                raise LLMLimitReached(f"auditstress call cap of {self.cap} reached")
            data["calls"] += 1
            self._write(data)
        stage = "?"
        try:
            out, meta = self.inner.complete(**kw)
        except LLMRefusal:
            with self.lock:
                data = self._read()
                data["refusals"] += 1
                self._write(data)
            raise
        except Exception:
            with self.lock:
                data = self._read()
                data["errors"] += 1
                self._write(data)
            raise
        with self.lock:
            data = self._read()
            data["cost_usd"] = round(data["cost_usd"] + float(meta.get("cost_usd") or 0), 4)
            data["input_tokens"] += int(meta.get("input_tokens") or 0)
            data["output_tokens"] += int(meta.get("output_tokens") or 0)
            data["safety_stops"] += 1 if meta.get("safety_stops") else 0
            stage = kw.get("effort", "?")
            data["by_stage"][stage] = data["by_stage"].get(stage, 0) + 1
            self._write(data)
        return out, meta


class CacheOnlyBackend:
    """For replaying stored audits: any call not already in the cache is refused."""

    def complete(self, **kw):
        from .llm import LLMError
        raise LLMError("not in cache (replay makes no new calls)")


def make_llm(out_dir: Path, salt: str = SALT, cap: int = CALL_CAP, concurrency: int = 3):
    from .config import get_settings
    from .llm import LLM
    settings = dataclasses.replace(get_settings(), replicate=salt, llm_concurrency=min(3, concurrency))
    llm = LLM(settings)
    llm.backend = BudgetBackend(llm.backend, out_dir / "ledger.json", cap)
    return llm


def replay_llm():
    from .config import get_settings
    from .llm import LLM
    settings = dataclasses.replace(get_settings(), replicate="", llm_concurrency=4)
    llm = LLM(settings)
    llm.backend = CacheOnlyBackend()
    return llm


# --------------------------------------------------------------------------- #
# Running
# --------------------------------------------------------------------------- #


def _load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text()) if path.exists() else default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    tmp.replace(path)


def _chunks(n_items: int, limit: int | None) -> list[tuple[int, int]]:
    upto = n_items if limit is None else min(n_items, limit)
    return [(s, min(s + CHUNK, n_items)) for s in range(0, upto, CHUNK)]


def _papers_for(lib: Library, mim: str, pmids: list[str]) -> dict[str, Paper]:
    out = {}
    for pmid in pmids:
        try:
            out[pmid] = lib.papers(mim)[pmid]
        except KeyError:
            out[pmid] = lib.paper(pmid)
    return out


def run_audits(out_dir: Path, built: dict[str, Any], lib: Library, llm, limit: int | None,
               classes: tuple[str, ...]) -> None:
    """Audit altered items of each class and the controls, chunk by chunk; finished chunks are skipped."""
    for cls in classes:
        items = built["items"][cls]
        path = out_dir / f"audit.{cls}.json"
        done = _load_json(path, {})
        for a, b in _chunks(len(items), limit):
            key = f"{a}-{b}"
            if key in done:
                continue
            chunk = items[a:b]
            for it in chunk:
                lib.papers(it["mim"])
            for it in chunk:
                for pm in it["pmids"]:
                    lib.paper(pm)
            papers = {pm: lib.paper(pm) for it in chunk for pm in it["pmids"]}
            paras = [EntryParagraph(id=it["id"], text=it["altered_text"], pmids=it["pmids"]) for it in chunk]
            stops_before = llm.safety_stops
            result = audit_paragraphs(paras, papers, llm)
            done[key] = {"results": result, "safety_stops": llm.safety_stops - stops_before}
            _save_json(path, done)
            log.info("%s chunk %s: %s", cls, key, Counter(r["status"] for r in result.values()))
    controls = built["controls"]
    need = max((len(built["items"][c][:limit]) if limit else len(built["items"][c]) for c in classes), default=0)
    upto = max((i + 1 for i, c in enumerate(controls) if c["first_needed_by"] < need), default=0)
    path = out_dir / "audit.control.json"
    done = _load_json(path, {})
    for a, b in _chunks(len(controls), upto):
        key = f"{a}-{b}"
        if key in done:
            continue
        chunk = controls[a:b]
        papers = {c["pmid"]: lib.papers(c["mim"])[c["pmid"]] for c in chunk}
        paras = [EntryParagraph(id=c["id"], text=c["text"], pmids=[c["pmid"]]) for c in chunk]
        stops_before = llm.safety_stops
        result = audit_paragraphs(paras, papers, llm)
        done[key] = {"results": result, "safety_stops": llm.safety_stops - stops_before}
        _save_json(path, done)
        log.info("control chunk %s: %s", key, Counter(r["status"] for r in result.values()))


def run_completeness_planted(out_dir: Path, built: dict[str, Any], lib: Library, llm, limit: int | None) -> None:
    """C6: the completeness check on the draft with and without the deleted sentence, then the match judge."""
    from .verify import MAX_SOURCE_CHARS
    items = built["items"]["C6"]
    path = out_dir / "complete.C6.json"
    done = _load_json(path, {})
    for a, b in _chunks(len(items), limit):
        key = f"{a}-{b}"
        if key in done:
            continue
        chunk = items[a:b]
        jobs = []
        for it in chunk:
            paper = lib.papers(it["mim"])[it["pmid"]]
            source = paper.source_text(MAX_SOURCE_CHARS)
            for arm, draft in (("altered", it["draft_after"]), ("control", it["draft_before"])):
                jobs.append((it, arm, source, complete_prompt(paper, source, draft)))
        stops_before = llm.safety_stops
        replies = llm.map("complete", COMPLETE_SYSTEM, [j[3] for j in jobs], XOmissions)
        rows: dict[str, dict[str, Any]] = defaultdict(dict)
        for (it, arm, source, _), reply in zip(jobs, replies):
            rows[it["id"]][arm] = checked_omissions(reply, source)
        judge_jobs = [(iid, arm) for iid, arms in rows.items() for arm, r in arms.items() if r["omissions"]]
        by_id = {it["id"]: it for it in chunk}
        prompts = [match_prompt(by_id[iid]["deleted_sentence"], [o["finding"] for o in rows[iid][arm]["omissions"]])
                   for iid, arm in judge_jobs]
        judged = llm.map("judge", MATCH_SYSTEM, prompts, XMatches) if prompts else []
        for (iid, arm), reply in zip(judge_jobs, judged):
            r = rows[iid][arm]
            if isinstance(reply, Exception):
                r["judge_error"] = f"{type(reply).__name__}: {str(reply)[:200]}"
                continue
            n_om = len(r["omissions"])
            r["judge"] = [{"n": m.n, "match": m.match} for m in reply.matches if 1 <= m.n <= n_om]
        for iid, arms in rows.items():
            for arm, r in arms.items():
                texts = [o["finding"] + " " + o["quote"] for o in r["omissions"]]
                r["mechanical"] = mechanical_match(by_id[iid]["deleted_sentence"], texts)
                vtexts = [o["finding"] + " " + o["quote"] for o in r["omissions"] if o["quote_verified"]]
                r["mechanical_verified"] = mechanical_match(by_id[iid]["deleted_sentence"], vtexts)
        done[key] = {"results": rows, "safety_stops": llm.safety_stops - stops_before}
        _save_json(path, done)
        log.info("C6 completeness chunk %s done", key)


def _gold_facts(entry_dir: Path) -> dict[str, list[dict[str, str]]]:
    """gold paragraph key -> its frozen facts (id, wording). In memory only."""
    data = json.loads((entry_dir / "gold_facts.json").read_text())
    return {p["key"]: p.get("facts", []) for p in data.get("paragraphs", [])}


def run_completeness_natural(out_dir: Path, run_dir: Path, lib: Library, llm, limit: int | None,
                             seed: int = DEFAULT_SEED) -> None:
    """Natural omissions: the check on the direct-reading draft's text about each paper, then the facts judge."""
    from .evaluate import _draft_text_for
    from .gaps import per_paper_chars
    targets = select_natural(natural_targets(run_dir), NATURAL_FACT_CAP, seed)
    path = out_dir / "complete.natural.json"
    done = _load_json(path, {"targets": [{k: t[k] for k in ("mim", "pmid", "target_fact_ids", "content_level")}
                                          for t in targets], "chunks": {}})
    for a, b in _chunks(len(targets), limit):
        key = f"{a}-{b}"
        if key in done["chunks"]:
            continue
        chunk = targets[a:b]
        jobs = []
        for t in chunk:
            entry_dir = run_dir / t["mim"]
            papers = lib.papers(t["mim"])
            paper = papers[t["pmid"]]
            n_papers = len(json.loads((entry_dir / "papers.json").read_text()))
            source = paper.source_text(per_paper_chars(n_papers))
            entry = lib.entry(t["mim"], NATURAL_STRATEGY)
            jobs.append((t, source, complete_prompt(paper, source, _draft_text_for(entry, [t["pmid"]]))))
        stops_before = llm.safety_stops
        replies = llm.map("complete", COMPLETE_SYSTEM, [j[2] for j in jobs], XOmissions)
        rows = {}
        judge_jobs, prompts = [], []
        for (t, source, _), reply in zip(jobs, replies):
            r = checked_omissions(reply, source)
            facts_by_key = _gold_facts(run_dir / t["mim"])
            facts = [f for k in t["gold_keys"] for f in facts_by_key.get(k, [])]
            r["fact_ids"] = [f["id"] for f in facts]
            r["target_fact_ids"] = t["target_fact_ids"]
            r["n_draft_chars"] = len(_draft_text_for(lib.entry(t["mim"], NATURAL_STRATEGY), [t["pmid"]]))
            rid = f"{t['mim']}:{t['pmid']}"
            rows[rid] = r
            if r["omissions"] and facts:
                judge_jobs.append(rid)
                prompts.append(facts_prompt([f["fact"] for f in facts], [o["finding"] for o in r["omissions"]]))
        judged = llm.map("judge", FACTS_SYSTEM, prompts, XFactMatches) if prompts else []
        for rid, reply in zip(judge_jobs, judged):
            r = rows[rid]
            if isinstance(reply, Exception):
                r["judge_error"] = f"{type(reply).__name__}: {str(reply)[:200]}"
                continue
            n_om, ids = len(r["omissions"]), r["fact_ids"]
            marks = {}
            for fm in reply.facts:
                if 1 <= fm.n <= len(ids) and ids[fm.n - 1] not in marks:
                    marks[ids[fm.n - 1]] = {"stating": sorted({x for x in fm.stating if 1 <= x <= n_om}),
                                            "stating_part": sorted({x for x in fm.stating_part if 1 <= x <= n_om})}
            r["fact_marks"] = marks
        done["chunks"][key] = {"results": rows, "safety_stops": llm.safety_stops - stops_before}
        _save_json(path, done)
        log.info("natural chunk %s done", key)


# --------------------------------------------------------------------------- #
# Citation precision from the stored audits (no new calls)
# --------------------------------------------------------------------------- #

PRECISION_STRATEGIES = ("kg", "direct", "agent", "cohort", "recall", "closedbook")


def replay_entry(entry: GeneratedEntry, papers: dict[str, Paper], llm) -> dict[str, dict[str, Any]] | None:
    """Re-derive every paper's verdict on every claim from the cached audit replies of the run.

    Only possible where the stored paragraphs are those the audit read (no repair changed the
    entry). A paragraph is kept only if the replayed best verdicts equal the stored ones.
    """
    paras = [p.model_copy(deep=True) for p in entry.all_paragraphs()]
    result = audit_paragraphs(paras, papers, llm)
    kept = {}
    for para in entry.all_paragraphs():
        r = result.get(para.id)
        if not r or r.get("error"):
            continue
        stored = [(squash(c.claim), c.verdict) for c in para.checks]
        replayed = [(squash(c["text"]), c["verdict"]) for c in r["claims"]]
        if stored == replayed and not r.get("failed_papers"):
            kept[para.id] = r
    return kept


def precision_tally(paragraphs: list[tuple[EntryParagraph, dict[str, Any]]]) -> dict[str, Any]:
    """Over paragraphs citing two or more papers: each (claim, attributed paper) pair's own verdict."""
    pairs: Counter = Counter()
    n_par = n_claims = attributed_all = best_ok_some_bad = 0
    for para, r in paragraphs:
        if len(para.pmids) < 2:
            continue
        n_par += 1
        for c in r["claims"]:
            n_claims += 1
            attributed_all += 1 if set(para.checked_pmids) <= set(c["pmids"]) else 0
            for pmid in c["pmids"]:
                v = c["per_paper"].get(pmid, {}).get("verdict", "no_verdict")
                pairs[v] += 1
            own = [c["per_paper"].get(pm, {}).get("verdict") for pm in c["pmids"]]
            if c["verdict"] in ("supported", "partially_supported") and any(v in FLAGGED for v in own):
                best_ok_some_bad += 1
    total = sum(pairs.values())
    bad = pairs["unsupported"] + pairs["contradicted"]
    return {"paragraphs": n_par, "claims": n_claims, "pairs": total, "pair_verdicts": dict(pairs),
            "share_not_supported": round(bad / total, 4) if total else None,
            "share_supported_or_partly": round((pairs["supported"] + pairs["partially_supported"]) / total, 4)
            if total else None,
            "claims_attributed_to_every_cited_paper": attributed_all,
            "claims_passing_with_a_non_supporting_cited_paper": best_ok_some_bad}


def run_precision(run_dir: Path, out_dir: Path, strategies: tuple[str, ...] = PRECISION_STRATEGIES) -> dict[str, Any]:
    llm = replay_llm()
    out: dict[str, Any] = {}
    for s in strategies:
        rows: list[tuple[EntryParagraph, dict[str, Any]]] = []
        cov = Counter()
        for path in sorted(run_dir.glob(f"*/entry.{s}.json")):
            entry = GeneratedEntry.model_validate_json(path.read_text())
            meta = entry.meta
            if "audit" not in meta or meta.get("stopped"):
                cov["not_audited"] += 1
                continue
            rep = meta.get("repair")
            multi = [p for p in entry.all_paragraphs() if len(p.pmids) >= 2]
            cov["multi_paragraphs_total"] += len(multi)
            if rep and (rep.get("revised") or rep.get("deleted")):
                cov["entries_repaired_excluded"] += 1
                cov["multi_paragraphs_in_repaired_entries"] += len(multi)
                continue
            cov["entries_replayed"] += 1
            kept = replay_entry(entry, load_as_run(path.parent), llm)
            for p in multi:
                if p.id in kept:
                    rows.append((p, kept[p.id]))
                    cov["multi_paragraphs_replayed"] += 1
                else:
                    cov["multi_paragraphs_replay_failed"] += 1
        out[s] = {"coverage": dict(cov), **precision_tally(rows)}
        log.info("precision %s: %s", s, out[s])
    out["_usage"] = llm.usage.summary()["total"]
    _save_json(out_dir / "precision.json", out)
    return out


# --------------------------------------------------------------------------- #
# Tallies
# --------------------------------------------------------------------------- #


def _flat(done: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for chunk in done.values():
        out.update(chunk["results"])
    return out


def claim_overlap(claim: str, sentence: str) -> float:
    stop = {"the", "a", "an", "of", "in", "and", "was", "were", "with", "to", "for", "by", "that", "this", "is",
            "are", "et", "al", "on", "as", "at", "from", "had", "has", "their", "they", "which"}
    c = [t for t in tokens(claim) if t not in stop]
    s = {t for t in tokens(sentence) if t not in stop}
    return sum(1 for t in c if t in s) / len(c) if c else 0.0


def planted_claims(cls: str, item: dict[str, Any], claims: list[dict[str, Any]], lib: Library | None = None,
                   paper_keys: set[str] | None = None, control: bool = False) -> list[int] | None:
    """Indexes of the claims that carry the planted error (or, on a control, the same content).

    C1, C4: every claim. C2: claims naming a variant absent from the new paper (truth by construction).
    C3: claims naming the moved sentence's variant. C5: claims taken from the altered sentence.
    C6: none (the error is an absence). None when the class has no planted claim.
    """
    if cls in ("C1", "C4"):
        return list(range(len(claims)))
    if cls == "C2":
        absent = {v["mention"] for v in item.get("variants", []) if not v["occurs"]}
        absent_keys = set()
        for m, ks in variant_mentions(" ".join(absent)).items():
            absent_keys |= {k for k in ks if not k.startswith("pos:")}
        return [i for i, c in enumerate(claims) if exact_keys(variant_mentions(c["text"])) & absent_keys]
    if cls == "C3":
        moved = set(item.get("moved_keys", []))
        return [i for i, c in enumerate(claims) if exact_keys(variant_mentions(c["text"])) & moved]
    if cls == "C5":
        sentence = item["before_sentence"] if control else item["after_sentence"]
        scores = [claim_overlap(c["text"], sentence) for c in claims]
        picked = [i for i, s in enumerate(scores) if s >= 0.6]
        if not picked and scores and max(scores) > 0:
            picked = [scores.index(max(scores))]
        return picked
    return None


def _worst(verdicts: list[str]) -> str:
    return max(verdicts, key=lambda v: SEVERITY.get(v, 0)) if verdicts else "none"


def tally_class(cls: str, items: list[dict[str, Any]], results: dict[str, dict[str, Any]],
                control: dict[str, dict[str, Any]], control_ids: dict[tuple[str, str], str]) -> dict[str, Any]:
    """Counts for one class: altered items and their controls, split by whether truth is known."""
    rows = []
    for it in items:
        r = results.get(it["id"])
        if r is None:
            continue
        claims = r["claims"]
        idx = planted_claims(cls, it, claims)
        planted_verdicts = [claims[i]["verdict"] for i in idx] if idx is not None else []
        ctl_id = control_ids.get((it["mim"], it["paragraph_id"]))
        ctl = control.get(ctl_id) if ctl_id else None
        row = {"id": it["id"], "truth_known": it.get("truth_known", True), "status": r["status"],
               "paragraph_flagged": r["status"] == "flagged", "n_claims": len(claims),
               "n_planted_claims": len(idx) if idx is not None else None,
               "planted_flagged": (any(v in FLAGGED for v in planted_verdicts) if idx else None),
               "planted_worst": _worst(planted_verdicts) if idx else None,
               "planted_claims_flagged": sum(1 for v in planted_verdicts if v in FLAGGED),
               "control_status": ctl["status"] if ctl else None}
        # The control analogue of the planted claim.
        if ctl is not None and cls in ("C1", "C2", "C4", "C5"):
            cidx = planted_claims(cls, it, ctl["claims"], control=True)
            cv = [ctl["claims"][i]["verdict"] for i in cidx] if cidx else []
            row["control_planted_flagged"] = any(v in FLAGGED for v in cv) if cidx else None
            row["control_planted_claims"] = len(cidx or [])
            row["control_planted_claims_flagged"] = sum(1 for v in cv if v in FLAGGED)
        if cls == "C3":
            src = control.get(control_ids.get((it["mim"], it["source_paragraph_id"]), ""))
            if src is not None:
                cidx = planted_claims("C3", it, src["claims"])
                cv = [src["claims"][i]["verdict"] for i in cidx]
                row["control_planted_flagged"] = any(v in FLAGGED for v in cv) if cidx else None
                row["control_planted_claims"] = len(cidx)
                row["control_planted_claims_flagged"] = sum(1 for v in cv if v in FLAGGED)
        if cls == "C4":
            added = it["added_pmid"]
            per = [c["per_paper"].get(added, {}).get("verdict", "no_verdict") if added in c["pmids"] else "not_attributed"
                   for c in claims]
            row["added_paper_verdicts"] = dict(Counter(per))
        if cls == "C5":
            row["rule"] = it["rule"]
        if cls in ("C1", "C2"):
            row["relabelled"] = it.get("relabelled")
        rows.append(row)
    return {"rows": rows, "known": summarise_rows([r for r in rows if r["truth_known"]], cls),
            "unknown": summarise_rows([r for r in rows if not r["truth_known"]], cls) if cls in ("C2", "C3") else None,
            "all": summarise_rows(rows, cls)}


def _share(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def summarise_rows(rows: list[dict[str, Any]], cls: str) -> dict[str, Any]:
    n = len(rows)
    with_planted = [r for r in rows if r["n_planted_claims"]]
    ctl = [r for r in rows if r["control_status"] is not None]
    ctl_planted = [r for r in rows if r.get("control_planted_flagged") is not None]
    out = {
        "items": n,
        "paragraphs_flagged": sum(r["paragraph_flagged"] for r in rows),
        "paragraph_flag_rate": _share(sum(r["paragraph_flagged"] for r in rows), n),
        "paragraphs_partial": sum(r["status"] == "partial" for r in rows),
        "items_with_planted_claim_identified": len(with_planted),
        "planted_claim_flagged": sum(bool(r["planted_flagged"]) for r in with_planted),
        "planted_claim_flag_rate": _share(sum(bool(r["planted_flagged"]) for r in with_planted), len(with_planted)),
        "planted_claim_worst_verdict": dict(Counter(r["planted_worst"] for r in with_planted)),
        "planted_claims": sum(r["n_planted_claims"] for r in with_planted),
        "planted_claims_flagged": sum(r["planted_claims_flagged"] for r in with_planted),
        "control_items": len(ctl),
        "control_paragraphs_flagged": sum(r["control_status"] == "flagged" for r in ctl),
        "control_paragraph_flag_rate": _share(sum(r["control_status"] == "flagged" for r in ctl), len(ctl)),
        "control_planted_items": len(ctl_planted),
        "control_planted_flagged": sum(bool(r["control_planted_flagged"]) for r in ctl_planted),
        "control_planted_flag_rate": _share(sum(bool(r["control_planted_flagged"]) for r in ctl_planted),
                                            len(ctl_planted)),
    }
    out["planted_claim_share_flagged"] = _share(out["planted_claims_flagged"], out["planted_claims"])
    if cls == "C4":
        agg: Counter = Counter()
        for r in rows:
            agg.update(r.get("added_paper_verdicts", {}))
        out["added_paper_verdicts"] = dict(agg)
        attributed = sum(v for k, v in agg.items() if k != "not_attributed")
        out["added_paper_judged_claims"] = attributed
        out["added_paper_share_supported_or_partly"] = _share(agg["supported"] + agg["partially_supported"], attributed)
        out["added_paper_share_flagged"] = _share(agg["unsupported"] + agg["contradicted"], attributed)
    if cls == "C5":
        out["by_rule"] = {}
        for rule in sorted({r["rule"] for r in rows}):
            sub = [r for r in rows if r["rule"] == rule]
            sp = [r for r in sub if r["n_planted_claims"]]
            out["by_rule"][rule] = {"items": len(sub), "paragraphs_flagged": sum(r["paragraph_flagged"] for r in sub),
                                    "planted_claim_flagged": sum(bool(r["planted_flagged"]) for r in sp),
                                    "items_with_planted_claim_identified": len(sp),
                                    "planted_claim_worst_verdict": dict(Counter(r["planted_worst"] for r in sp))}
    return out


def tally_c6(items: list[dict[str, Any]], done: dict[str, Any]) -> dict[str, Any]:
    rows = _flat(done)
    out: dict[str, Any] = {}
    for arm in ("altered", "control"):
        rs = [(it, rows[it["id"]][arm]) for it in items if it["id"] in rows and arm in rows[it["id"]]]
        ok = [(it, r) for it, r in rs if not r["error"]]
        n_om = [len(r["omissions"]) for _, r in ok]
        n_ver = [sum(o["quote_verified"] for o in r["omissions"]) for _, r in ok]
        mech = [r["mechanical"] for _, r in ok if r["mechanical"] is not None]
        mech_v = [r["mechanical_verified"] for _, r in ok if r["mechanical_verified"] is not None]
        judged = [r for _, r in ok if "judge" in r or not r["omissions"]]
        full = [any(m["match"] == "full" for m in r.get("judge", [])) for r in judged]
        anym = [bool(r.get("judge")) for r in judged]
        # Judge matches restricted to omissions whose quote was verified.
        full_v = [any(m["match"] == "full" and r["omissions"][m["n"] - 1]["quote_verified"] for m in r.get("judge", []))
                  for r in judged]
        out[arm] = {
            "items": len(rs), "errors": len(rs) - len(ok),
            "omissions_listed_mean": round(statistics.mean(n_om), 2) if n_om else None,
            "omissions_listed_median": statistics.median(n_om) if n_om else None,
            "omissions_listed_total": sum(n_om), "omissions_quote_verified_total": sum(n_ver),
            "items_with_no_omission": sum(1 for x in n_om if x == 0),
            "deleted_sentence_listed_mechanical": sum(mech), "mechanical_items": len(mech),
            "deleted_sentence_listed_mechanical_verified_quotes": sum(mech_v),
            "deleted_sentence_listed_judge_full": sum(full), "deleted_sentence_listed_judge_full_or_partial": sum(anym),
            "deleted_sentence_listed_judge_full_verified_quotes": sum(full_v),
            "judged_items": len(judged),
            "rate_judge_full": _share(sum(full), len(judged)), "rate_judge_any": _share(sum(anym), len(judged)),
            "rate_mechanical": _share(sum(mech), len(mech)),
        }
    return out


def tally_natural(done: dict[str, Any]) -> dict[str, Any]:
    rows = [r for ch in done.get("chunks", {}).values() for r in ch["results"].values()]
    ok = [r for r in rows if not r["error"]]
    targets = yes = part = 0
    targets_v = 0
    om_total = om_match = om_match_part = om_verified = 0
    for r in ok:
        marks = r.get("fact_marks", {})
        verified = {i + 1 for i, o in enumerate(r["omissions"]) if o["quote_verified"]}
        for fid in r["target_fact_ids"]:
            targets += 1
            m = marks.get(fid, {"stating": [], "stating_part": []})
            yes += bool(m["stating"])
            part += bool(m["stating"] or m["stating_part"])
            targets_v += bool(set(m["stating"]) & verified)
        n = len(r["omissions"])
        om_total += n
        om_verified += len(verified)
        stating = {x for m in marks.values() for x in m["stating"]}
        stating_part = stating | {x for m in marks.values() for x in m["stating_part"]}
        om_match += len(stating)
        om_match_part += len(stating_part)
    n_om = [len(r["omissions"]) for r in ok]
    return {
        "papers": len(rows), "errors": len(rows) - len(ok), "judge_errors": sum(1 for r in ok if r.get("judge_error")),
        "target_facts": targets, "target_facts_listed": yes, "recall": _share(yes, targets),
        "target_facts_listed_or_partly": part, "recall_incl_partly": _share(part, targets),
        "target_facts_listed_with_verified_quote": targets_v, "recall_verified_quotes": _share(targets_v, targets),
        "omissions_listed_total": om_total, "omissions_per_paper_mean": round(statistics.mean(n_om), 2) if n_om else None,
        "omissions_quote_verified": om_verified,
        "omissions_matching_a_curator_fact": om_match, "share_matching_a_curator_fact": _share(om_match, om_total),
        "omissions_matching_incl_partly": om_match_part, "share_matching_incl_partly": _share(om_match_part, om_total),
        "papers_with_no_draft_text": sum(1 for r in ok if r.get("n_draft_chars") == 0),
    }


DECISIONS = [
    "Strategy planted in: the evidence-graph drafts ('kg') of run omim100, as the single-value planted test, with its "
    "selection rule (paragraphs passed as fully supported, citing one paper, longer than 150 characters); at most 3 "
    "items per entry per class. One seeded order of that pool serves all classes, so classes share paragraphs and one "
    "control audit of the union of their unaltered paragraphs serves every class.",
    "C3 is planted in the same 'kg' drafts, not the direct-reading drafts: its truth (the moved variant does not occur "
    "in paper B's text) is decided mechanically from the paper text, so it needs no stored omission judgement, and "
    "keeping one strategy keeps the classes comparable. The moved sentence names a variant and carries no author "
    "citation (so it is not explicitly attributed to paper A); it is inserted at a seeded sentence boundary after B's "
    "first sentence; B must not already name that variant.",
    "C6's planted deletions are in the 'kg' drafts; C6's natural omissions use the direct-reading drafts ('direct'), "
    "where the stored judgements are: curator facts of gold paragraphs citing one paper, marked absent from the draft "
    "and stated (verdict 'yes', quote verified) in the text the writer had. Facts marked partly conveyed or partly "
    "stated are not targets.",
    "Citation swaps (C1, C2) and over-citation (C4) change the in-text author-year label as well as the cited PMID "
    "(only paragraphs whose label occurs in the text are used): 'A et al. (2000)' -> 'B et al. (2010)' for swaps, "
    "'A et al. (2000) and B et al. (2010)' or '(A et al., 2000; B et al., 2010)' for over-citation. The new paper of "
    "C1 and C4 is a random readable paper (abstract or full text) of another entry; of C2 a random readable other "
    "paper of the same entry.",
    "Variant occurrence (C2, C3) is decided on the text the auditor reads (title, abstract and full text cut at "
    "180,000 characters). A variant occurs if any of its protein or nucleotide keys (kg.protein_key / nucleotide_key, "
    "so one- and three-letter, 'arg123-to-trp', p. and c. forms meet), its residue or nucleotide position, or its raw "
    "name occurs in the paper. C2 items are truth-known when the paragraph names at least one variant that does not "
    "occur in the new paper; C3 items when none of the moved sentence's variants occurs in B.",
    "Planted claim: C1 and C4 every claim; C2 claims naming a variant absent from the new paper; C3 claims naming the "
    "moved variant; C5 claims taken from the altered sentence (at least 60% of a claim's content words in the "
    "sentence, else the best-overlapping claim); C6 none. An item counts as 'planted claim flagged' when any planted "
    "claim is unsupported or contradicted. Control analogue: the same rule on the unaltered paragraph (for C3, the "
    "moved sentence's claims in paper A's own paragraph, against paper A).",
    "C6 deleted sentence: not the first sentence, carrying a variant or a number (years and MIM numbers aside) that "
    "appears nowhere else in the draft's text citing that paper. Mechanical match: a listed omission names one of the "
    "sentence's variants (by key), or, for a sentence without variants, carries all its numbers. Judge match: stage "
    "'judge'. The draft text given to the check is all paragraphs of the entry citing the paper (as in scoring).",
    "The audit is run on items in fixed chunks of 5 (one claim-decomposition call per chunk, then one call per cited "
    "paper), not on one 60-paragraph holder as the single-value test did (decomposition batches of 25); this lets the "
    "pilot's calls be reused and the run resume. All calls are made under the replicate salt 'auditstress-1', so "
    "altered and control audits are fresh and from the same run.",
    "Per-paper verdicts are kept by `auditstress.audit_paragraphs`, which runs the audit's own prompts and best-verdict "
    "rule (verify._decompose, verify._audit_prompt); a unit test checks it agrees with verify.verify_entry.",
    "Citation precision: the run's entry files keep only each claim's best verdict, not every paper's. Per-paper "
    "verdicts were recovered by replaying the stored audit from the model-reply cache with a backend that refuses "
    "any uncached call (no new calls). That is possible only for entries the repair round left unchanged; entries "
    "with a revised or deleted paragraph are excluded, and a paragraph is kept only if the replayed best verdict of "
    "every claim equals the stored one.",
]


def summarise(run_dir: Path, results_dir: Path) -> dict[str, Any]:
    out_dir = run_dir / OUT_DIR
    built = _load_json(out_dir / "items.json", None)
    control = _flat(_load_json(out_dir / "audit.control.json", {}))
    control_ids = {(c["mim"], c["paragraph_id"]): c["id"] for c in built["controls"]}
    classes = {}
    for cls in CLASSES:
        done = _load_json(out_dir / f"audit.{cls}.json", {})
        if not done:
            continue
        t = tally_class(cls, built["items"][cls], _flat(done), control, control_ids)
        t["stops"] = sum(ch.get("safety_stops", 0) for ch in done.values())
        classes[cls] = {k: v for k, v in t.items() if k != "rows"}
        classes[cls]["item_rows"] = t["rows"]
    ctl_rows = [r for r in control.values()]
    from .auditcheck import control_tally
    control_overall = control_tally([r["verdicts"] for r in ctl_rows])
    c5 = built["items"]["C5"]
    result = {
        "run": run_dir.name, "strategy": STRATEGY, "natural_strategy": NATURAL_STRATEGY, "seed": built["seed"],
        "salt": SALT, "pool_size": built["pool_size"],
        "items_built": {c: len(v) for c, v in built["items"].items()},
        "classes": classes,
        "control_overall": control_overall,
        "c5_rules": dict(Counter(it["rule"] for it in c5)),
        "c6_completeness_planted": tally_c6(built["items"]["C6"], _load_json(out_dir / "complete.C6.json", {})),
        "c6_completeness_natural": tally_natural(_load_json(out_dir / "complete.natural.json", {})),
        "citation_precision": _load_json(out_dir / "precision.json", None),
        "usage": _load_json(out_dir / "ledger.json", None),
        "decisions": DECISIONS,
        "deviations": _load_json(out_dir / "notes.json", {}).get("deviations", []),
        "pilot_review": _load_json(out_dir / "notes.json", {}).get("pilot_review", []),
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    _save_json(results_dir / "audit_stress.json", result)
    (results_dir / "audit_stress.md").write_text(markdown(result), encoding="utf-8")
    return result


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.0f}%"


def markdown(r: dict[str, Any]) -> str:
    L = [f"# Audit coverage: planted errors beyond single values (Experiment C, run {r['run']})", "",
         f"Planted in the '{r['strategy']}' drafts; natural omissions from the '{r['natural_strategy']}' drafts. "
         f"Seed {r['seed']}, replicate salt '{r['salt']}'. Pool of passed single-paper paragraphs: {r['pool_size']}.", "",
         "## Audit on planted errors", "",
         "| Class | Items | Truth known | Paragraph flagged | Planted claim flagged | Control paragraph flagged | "
         "Control planted-claim analogue flagged |", "|---|---|---|---|---|---|---|"]
    for cls, t in r["classes"].items():
        k, a = t["known"], t["all"]
        L.append(f"| {cls} {CLASS_NAMES[cls]} | {a['items']} | {k['items']} | {k['paragraphs_flagged']}/{k['items']} "
                 f"({_pct(k['paragraph_flag_rate'])}) | {k['planted_claim_flagged']}/{k['items_with_planted_claim_identified']} "
                 f"({_pct(k['planted_claim_flag_rate'])}) | {k['control_paragraphs_flagged']}/{k['control_items']} "
                 f"({_pct(k['control_paragraph_flag_rate'])}) | {k['control_planted_flagged']}/{k['control_planted_items']} "
                 f"({_pct(k['control_planted_flag_rate'])}) |")
    L += ["", "Counts are over truth-known items. 'Planted claim flagged': at least one planted claim unsupported or "
          "contradicted, over items where a planted claim was identified. C4's expected outcome is a pass (the claim "
          "takes the best cited paper's verdict); C6's is a pass (the audit judges only what is written).", ""]
    for cls in ("C2", "C3"):
        t = r["classes"].get(cls)
        if t and t["unknown"]:
            u = t["unknown"]
            L.append(f"- {cls} truth unknown (variant occurs in the new paper's text): {u['items']} items, paragraph "
                     f"flagged {u['paragraphs_flagged']}, planted-claim-analogue flagged {u['planted_claim_flagged']}/"
                     f"{u['items_with_planted_claim_identified']}.")
    L += ["", "### Verdict on the planted claim (worst planted claim per item, truth-known items)", "",
          "| Class | contradicted | unsupported | partially supported | supported | not checkable |", "|---|---|---|---|---|---|"]
    for cls, t in r["classes"].items():
        w = t["known"]["planted_claim_worst_verdict"]
        L.append(f"| {cls} | {w.get('contradicted', 0)} | {w.get('unsupported', 0)} | {w.get('partially_supported', 0)} | "
                 f"{w.get('supported', 0)} | {w.get('not_checkable', 0)} |")
    if "C1" in r["classes"] or "C4" in r["classes"]:
        L += ["", "Claim level (C1, C4: every claim is planted):", ""]
        for cls in ("C1", "C4"):
            if cls in r["classes"]:
                k = r["classes"][cls]["known"]
                L.append(f"- {cls}: {k['planted_claims_flagged']} of {k['planted_claims']} claims flagged "
                         f"({_pct(k['planted_claim_share_flagged'])}).")
    if "C4" in r["classes"]:
        k = r["classes"]["C4"]["known"]
        L += ["", "### C4: the added paper's own verdicts", "",
              f"Of {sum(k['added_paper_verdicts'].values())} claims, the decomposer attributed "
              f"{k['added_paper_judged_claims']} to the added paper. Its own verdicts: "
              + ", ".join(f"{v} {n}" for v, n in sorted(k["added_paper_verdicts"].items()))
              + f". Share judged supported or partly by the added (unrelated) paper: "
              f"{_pct(k['added_paper_share_supported_or_partly'])}; flagged: {_pct(k['added_paper_share_flagged'])}."]
    if "C5" in r["classes"]:
        L += ["", "### C5 by deletion rule", "", "| Rule | Items | Paragraph flagged | Planted claim flagged | Worst verdict |",
              "|---|---|---|---|---|"]
        for rule, s in r["classes"]["C5"]["all"]["by_rule"].items():
            L.append(f"| {rule} | {s['items']} | {s['paragraphs_flagged']} | {s['planted_claim_flagged']}/"
                     f"{s['items_with_planted_claim_identified']} | "
                     + ", ".join(f"{v} {n}" for v, n in sorted(s["planted_claim_worst_verdict"].items())) + " |")
    co = r["control_overall"]
    L += ["", "### Control (all unaltered paragraphs, re-audited fresh)", "",
          f"{co['paragraphs']} paragraphs, {co['paragraphs_flagged']} flagged ({_pct(co['paragraph_flag_rate'])}); "
          f"{co['claims_audited']} claims, {co['claims_flagged']} flagged ({co['claim_flag_rate']}), "
          f"{co['claims_partly_supported']} partly supported."]
    p, ctl = r["c6_completeness_planted"].get("altered"), r["c6_completeness_planted"].get("control")
    if p:
        L += ["", "## C6 completeness check", "", "### Planted deletions", "",
              "| | Items | Omissions listed (mean / median) | Deleted sentence listed: mechanical | judge full | judge full or partial |",
              "|---|---|---|---|---|---|"]
        for name, x in (("Sentence deleted", p), ("Unaltered (false-alarm side)", ctl)):
            L.append(f"| {name} | {x['items']} | {x['omissions_listed_mean']} / {x['omissions_listed_median']} | "
                     f"{x['deleted_sentence_listed_mechanical']}/{x['mechanical_items']} ({_pct(x['rate_mechanical'])}) | "
                     f"{x['deleted_sentence_listed_judge_full']}/{x['judged_items']} ({_pct(x['rate_judge_full'])}) | "
                     f"{x['deleted_sentence_listed_judge_full_or_partial']}/{x['judged_items']} ({_pct(x['rate_judge_any'])}) |")
        L.append("")
        L.append(f"Quotes verified: {p['omissions_quote_verified_total']} of {p['omissions_listed_total']} omissions "
                 f"(deleted), {ctl['omissions_quote_verified_total']} of {ctl['omissions_listed_total']} (unaltered). "
                 f"Judge full matches with a verified quote: {p['deleted_sentence_listed_judge_full_verified_quotes']} (deleted), "
                 f"{ctl['deleted_sentence_listed_judge_full_verified_quotes']} (unaltered).")
    n = r["c6_completeness_natural"]
    if n.get("papers"):
        L += ["", "### Natural omissions (direct-reading drafts)", "",
              f"{n['papers']} papers ({n['errors']} failed), {n['target_facts']} curator facts stated in the text the "
              f"writer had but absent from the draft. Listed by the check (judge 'states it'): {n['target_facts_listed']} "
              f"({_pct(n['recall'])}); including 'states part': {n['target_facts_listed_or_partly']} "
              f"({_pct(n['recall_incl_partly'])}); with a verified quote: {n['target_facts_listed_with_verified_quote']} "
              f"({_pct(n['recall_verified_quotes'])}).", "",
              f"Omissions listed: {n['omissions_listed_total']} ({n['omissions_per_paper_mean']} per paper; "
              f"{n['omissions_quote_verified']} with a verified quote). Matching any curator fact about the paper: "
              f"{n['omissions_matching_a_curator_fact']} ({_pct(n['share_matching_a_curator_fact'])}); including partial "
              f"matches {n['omissions_matching_incl_partly']} ({_pct(n['share_matching_incl_partly'])})."]
    cp = r.get("citation_precision")
    if cp:
        L += ["", "## Citation precision (stored audits, no new calls)", "",
              "Paragraphs citing two or more papers; each (claim, paper the claim is attributed to) pair's own verdict.", "",
              "| Strategy | Entries replayed | Multi-citation paragraphs (replayed / all) | Pairs | Not supported | "
              "Supported or partly | Claims passing with a non-supporting cited paper |", "|---|---|---|---|---|---|---|"]
        for s, x in cp.items():
            if s.startswith("_"):
                continue
            c = x["coverage"]
            L.append(f"| {s} | {c.get('entries_replayed', 0)} | {c.get('multi_paragraphs_replayed', 0)} / "
                     f"{c.get('multi_paragraphs_total', 0)} | {x['pairs']} | {_pct(x['share_not_supported'])} | "
                     f"{_pct(x['share_supported_or_partly'])} | {x['claims_passing_with_a_non_supporting_cited_paper']} "
                     f"of {x['claims']} |")
    u = r.get("usage") or {}
    L += ["", "## Calls and cost", "",
          f"New model calls: {u.get('calls')} (cap {CALL_CAP}); safety-filter stops: {u.get('safety_stops')}; refusals "
          f"raised: {u.get('refusals')}; failed calls: {u.get('errors')}; list-price cost ${u.get('cost_usd')}.", "",
          "## Decisions", ""] + [f"- {d}" for d in r["decisions"]]
    if r.get("pilot_review"):
        L += ["", "## Pilot review", ""] + [f"- {d}" for d in r["pilot_review"]]
    L += ["", "## Deviations from the design", ""] + ([f"- {d}" for d in r["deviations"]] or ["- None."])
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> None:
    from .config import get_settings
    ap = argparse.ArgumentParser(prog="python -m aiomim.auditstress", description=__doc__.split("\n")[0])
    ap.add_argument("--run", default="omim100")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--n", type=int, default=DEFAULT_N)
    b.add_argument("--seed", type=int, default=DEFAULT_SEED)
    b.add_argument("--rules", default=",".join(r for r, _ in C5_RULES), help="C5 rules to use")
    r = sub.add_parser("run")
    r.add_argument("--limit", type=int, default=None, help="items per class (rounded up to a chunk of 5)")
    r.add_argument("--classes", default=",".join(CLASSES))
    r.add_argument("--parts", default="audit,complete,natural")
    r.add_argument("--natural-limit", type=int, default=None)
    sub.add_parser("precision")
    sub.add_parser("summarise")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_dir = get_settings().runs / a.run
    out_dir = run_dir / OUT_DIR
    if a.cmd == "build":
        keep = tuple(x for x in a.rules.split(",") if x)
        globals()["C5_RULES"] = [(n, f) for n, f in C5_RULES if n in keep]
        built = build_items(run_dir, n=a.n, seed=a.seed)
        built["c5_rules"] = keep
        if (out_dir / "items.json").exists():
            old = json.loads((out_dir / "items.json").read_text())
            if old != built:
                (out_dir / "items.previous.json").write_text(json.dumps(old, indent=1, ensure_ascii=False))
        _save_json(out_dir / "items.json", built)
        print(json.dumps({c: [len(v), sum(1 for x in v if x.get("truth_known"))] for c, v in built["items"].items()}),
              "controls", len(built["controls"]))
    elif a.cmd == "run":
        built = json.loads((out_dir / "items.json").read_text())
        lib = Library(run_dir)
        llm = make_llm(out_dir)
        parts = set(a.parts.split(","))
        classes = tuple(c for c in a.classes.split(",") if c)
        if "audit" in parts:
            run_audits(out_dir, built, lib, llm, a.limit, classes)
        if "complete" in parts and "C6" in classes:
            run_completeness_planted(out_dir, built, lib, llm, a.limit)
        if "natural" in parts:
            run_completeness_natural(out_dir, run_dir, lib, llm, a.natural_limit if a.natural_limit is not None
                                     else a.limit)
        print(json.dumps({"usage": llm.usage.summary()["total"], "safety_stops": llm.safety_stops,
                          "ledger": _load_json(out_dir / "ledger.json", {})}, indent=1))
    elif a.cmd == "precision":
        res = run_precision(run_dir, out_dir)
        print(json.dumps({s: {k: v for k, v in x.items() if k != "pair_verdicts"} for s, x in res.items()}, indent=1))
    elif a.cmd == "summarise":
        res = summarise(run_dir, Path("results") / a.run)
        print(markdown(res))


if __name__ == "__main__":
    main()
