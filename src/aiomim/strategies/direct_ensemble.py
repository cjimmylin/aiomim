"""Three direct-reading drafts merged into one (D3 of `docs/direct-improvements.md`).

1. Three drafts with direct reading's prompt: the baseline's own (draft A, from the
   cache only, as `direct_complete` takes it) and two fresh samples (B and C). The
   fresh ones are the same writer call made under a replicate salt that is set on
   these two calls only (`<salt>/ensemble-2`, `-3`, after any run-wide salt), so no
   existing cache key changes and nothing else in the entry is salted. Above the
   one-prompt budget each draft is direct reading's batched draft.
2. Allelic variants are matched across the drafts without a model: two variants
   are the same when they share a canonical key (gene plus nucleotide or protein
   change, `evaluate._variant_keys`) or, failing keys, the same name. Gene
   relationships and clinical-synopsis phrases are pooled as direct reading's
   batching pools them.
3. One merge call (stage `merge_drafts`) sees the three drafts, not the papers. For
   every paragraph of the merged entry it names the draft paragraphs it is made from
   (`sources`) and writes one text keeping every distinct statement they make, once.
   A merged paragraph cites the union of its sources' PMIDs, assigned here, never by
   the model. A merged text much longer than its sources together is refused (the
   longest source is kept instead); a paragraph naming no valid source is dropped; a
   draft paragraph the merge left out is put back only when it is the only one citing
   some paper, so no paper drops out of the entry (each such case is counted).
4. `draft_to_entry`, the guards every strategy shares.

A stopped draft (any of the three) or a stopped merge leaves no draft: an
ensemble must not become a way round a stopped reply.

What happened is in `meta.direct_ensemble`; the three drafts and the merge plan
are kept in the entry folder as `direct_ensemble.json` (model-written, no OMIM text).
"""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..auditstress import sentences
from ..evaluate import _variant_keys
from ..models import GeneratedEntry, Paper, SectionName, Seed, squash
from ..synthesize import DAllelicVariant, DEntry, DParagraph, DSection, _header, draft_to_entry
from . import direct
from .direct_complete import baseline_draft

log = logging.getLogger(__name__)

RECORD = "direct_ensemble.json"
DRAFTS = ("A", "B", "C")
SALTED = (2, 3)            # draft B is sample 2, draft C sample 3; A is the baseline's


def salt_for(base: str, k: int) -> str:
    return f"{base}/ensemble-{k}" if base else f"direct_ensemble-{k}"


def salted(llm, k: int):
    """The same wrapper (backend, cache, usage ledger) with a replicate salt on its calls."""
    if not hasattr(llm, "settings") or not dataclasses.is_dataclass(llm.settings):
        return llm   # a scripted test double
    clone = copy.copy(llm)
    clone.settings = dataclasses.replace(llm.settings, replicate=salt_for(llm.settings.replicate, k))
    return clone


MERGE_DRAFTS_SYSTEM = """\
You are a senior curator merging three drafts of the same entry for OMIM (Online Mendelian Inheritance in \
Man) into one. The drafts (A, B and C) were written independently from the same papers, so they describe \
largely the same reports, but each may state findings, numbers or details that the others leave out. Every \
draft paragraph has an ID (P1, P2, ...). The allelic variants have already been matched across the drafts: \
each variant group (G1, G2, ...) lists the paragraphs the drafts wrote under that variant.

Your job is editorial only. You do not have the papers, so you cannot add anything: no fact, number, \
variant, citation or interpretation that is not in the drafts, and nothing from your own memory.

Write one entry that keeps every distinct statement any draft makes, each stated once:
- For each paragraph of the merged entry give `sources`, the IDs of the draft paragraphs it is made from, \
and `text`. Paragraphs of different drafts about the same report (the same paper, or the same family or \
study within it) in the same section go into one merged paragraph: list all of them in `sources`, and \
write `text` so that it contains every statement any of them makes (every count, age, sex, ancestry, \
clinical or laboratory finding, variant, zygosity, segregation result, control figure, functional result \
and conclusion), without repeating a statement that two drafts make in different words. Where drafts give \
the same thing in different notation, keep one. Where they disagree about the same report (a different \
number, zygosity or variant), keep both versions, each worded as its draft words it; do not choose \
between them and do not comment on the difference.
- Keep the drafts' house style: past tense, statements attributed by citation label as the drafts \
attribute them ("Smith et al. (2001) found ..."), the drafts' variant notation, and numbers and units \
exactly as the drafts give them.
- Use the sections the drafts use, and keep paragraphs in chronological order of the reports within each \
section. Description, Inheritance and similar summary paragraphs are merged across drafts in the same way.
- Use every draft paragraph in exactly one merged paragraph.
- The intro is one sentence merged from the three intros, naming every causal gene any of them names.
- For each variant group, merge the paragraphs listed under it in the same way, and give the group's ID \
in `group`.\
"""


class EParagraph(BaseModel):
    sources: list[str] = Field(description='IDs of the draft paragraphs this paragraph is made from, e.g. ["P3", "P41", "P77"]')
    text: str = Field(description="The merged text: every distinct statement of the sources, each once")


class ESection(BaseModel):
    name: SectionName
    paragraphs: list[EParagraph]


class EVariant(BaseModel):
    group: str = Field(description='The variant group ID, e.g. "G2"')
    paragraphs: list[EParagraph]


class EEntry(BaseModel):
    intro: EParagraph
    sections: list[ESection]
    allelic_variants: list[EVariant]


# --------------------------------------------------------------------------- #
# Matching variants across drafts (no model)
# --------------------------------------------------------------------------- #


def variant_groups(drafts: list[DEntry]) -> list[list[tuple[int, int]]]:
    """Groups of (draft index, variant index) that are the same variant, in order of first appearance.

    Same variant: a shared canonical key (gene + nucleotide or protein change) or,
    for a variant with no key, the same gene and name.
    """
    items = [(d, v) for d, raw in enumerate(drafts) for v in range(len(raw.allelic_variants))]
    keys: dict[tuple[int, int], set[str]] = {}
    for d, v in items:
        av = drafts[d].allelic_variants[v]
        gene = av.gene_symbol.strip().upper()
        found = {f"{gene}:{k}" for k in _variant_keys([av.name, *av.hgvs], av.gene_symbol)}
        keys[(d, v)] = found or {f"{gene}:name:{squash(av.name).upper()}"}
    parent = {i: i for i in items}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a_i, a in enumerate(items):
        for b in items[a_i + 1:]:
            if keys[a] & keys[b]:
                parent[find(b)] = find(a)
    groups: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i in items:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


# --------------------------------------------------------------------------- #
# The merge prompt
# --------------------------------------------------------------------------- #


def merge_prompt(seed: Seed, papers: list[Paper], drafts: list[DEntry], groups: list[list[tuple[int, int]]]
                 ) -> tuple[str, dict[str, tuple[tuple, DParagraph, int]]]:
    """The three drafts with paragraph IDs, variant paragraphs under their group.

    Returns the prompt and the ID table: Pn -> (home, paragraph, draft index), where
    home is ("intro",), ("section", name) or ("variant", Gn).
    """
    labels = {p.pmid: p.label for p in papers}
    paragraphs: dict[str, tuple[tuple, DParagraph, int]] = {}

    def line(home: tuple, x: DParagraph, d: int, indent: str = "", tag: str = "") -> str:
        pid = f"P{len(paragraphs) + 1}"
        paragraphs[pid] = (home, x, d)
        cites = "; ".join(f"{p} = {labels.get(str(p).strip(), '?')}" for p in x.pmids) or "none"
        return f"{indent}[{pid}] ({tag}cites {cites}) {squash(x.text)}"

    out = [_header(seed), ""]
    for d, raw in enumerate(drafts):
        out.append(f"=== DRAFT {DRAFTS[d]} ===")
        out.append("INTRO")
        out.append(line(("intro",), raw.intro, d))
        for section in raw.sections:
            out.append(f"SECTION {section.name}")
            out.extend(line(("section", section.name), x, d) for x in section.paragraphs)
        out.append("")
    if groups:
        out.append("=== ALLELIC VARIANTS, matched across the drafts ===")
    for g, members in enumerate(groups, 1):
        gid = f"G{g}"
        avs = [drafts[d].allelic_variants[v] for d, v in members]
        names = list(dict.fromkeys(squash(a.name) for a in avs))
        hgvs = list(dict.fromkeys(squash(h) for a in avs for h in a.hgvs))
        in_drafts = ", ".join(dict.fromkeys(DRAFTS[d] for d, _ in members))
        out.append(f"[{gid}] {avs[0].gene_symbol} | {' / '.join(names)} | {'; '.join(hgvs)} | in drafts {in_drafts}")
        for (d, v), av in zip(members, avs):
            out.extend(line(("variant", gid), x, d, "    ", f"draft {DRAFTS[d]}; ") for x in av.paragraphs)
    return "\n".join(out), paragraphs


# --------------------------------------------------------------------------- #
# Assembling the merged draft
# --------------------------------------------------------------------------- #


def _longest(sources: list[DParagraph]) -> DParagraph:
    return max(sources, key=lambda s: len(squash(s.text)))


def assemble(plan: EEntry, paragraphs: dict[str, tuple[tuple, DParagraph, int]], drafts: list[DEntry],
             groups: list[list[tuple[int, int]]]) -> tuple[DEntry, dict[str, Any]]:
    """The merged draft from the plan: citations are the union of the sources', never the model's."""
    used: set[str] = set()
    stats: dict[str, Any] = {"merged_paragraphs": 0, "single_source": 0, "multi_source": 0,
                             "rejected_longer": 0, "empty_text_kept_longest": 0, "unknown_ids": 0,
                             "reused_ids": 0, "unsourced_dropped": 0, "restored": [], "unused": [],
                             "groups_restored": 0}

    def build(item: EParagraph) -> DParagraph | None:
        ids = []
        for raw_id in item.sources:
            pid = str(raw_id).strip().strip("[]")
            if pid not in paragraphs:
                stats["unknown_ids"] += 1
            elif pid not in ids:
                ids.append(pid)
        if not ids:
            stats["unsourced_dropped"] += 1
            return None
        stats["reused_ids"] += sum(1 for pid in ids if pid in used)
        used.update(ids)
        sources = [paragraphs[pid][1] for pid in ids]
        pmids = list(dict.fromkeys(str(p).strip() for s in sources for p in s.pmids))
        text = squash(item.text)
        if not text:
            stats["empty_text_kept_longest"] += 1
            text = squash(_longest(sources).text)
        elif direct._longer_than_sources(text, sources):
            stats["rejected_longer"] += 1
            text = squash(_longest(sources).text)
        stats["merged_paragraphs"] += 1
        stats["single_source" if len(ids) == 1 else "multi_source"] += 1
        return DParagraph(text=text, pmids=pmids)

    merged = DEntry(intro=DParagraph(text="", pmids=[]), sections=[],
                    relationships=direct._pool_relationships(drafts), allelic_variants=[],
                    clinical_synopsis=direct._pool_synopsis(drafts))
    by_section: dict[str, DSection] = {}

    def section(name: str) -> DSection:
        if name not in by_section:
            by_section[name] = DSection(name=name, paragraphs=[])
            merged.sections.append(by_section[name])
        return by_section[name]

    intro = build(plan.intro)
    if intro is not None:
        merged.intro = intro
    for s in plan.sections:
        target = section(s.name)
        target.paragraphs.extend(p for item in s.paragraphs if (p := build(item)) is not None)

    group_ids = {f"G{g}": members for g, members in enumerate(groups, 1)}
    placed: dict[str, DAllelicVariant] = {}

    def variant(gid: str) -> DAllelicVariant:
        if gid not in placed:
            avs = [drafts[d].allelic_variants[v] for d, v in group_ids[gid]]
            placed[gid] = DAllelicVariant(
                gene_symbol=avs[0].gene_symbol, name=avs[0].name,
                hgvs=list(dict.fromkeys(h for a in avs for h in a.hgvs)),
                phenotype=next((a.phenotype for a in avs if squash(a.phenotype)), ""), paragraphs=[])
            merged.allelic_variants.append(placed[gid])
        return placed[gid]

    for v in plan.allelic_variants:
        gid = str(v.group).strip().strip("[]")
        if gid not in group_ids:
            stats["unknown_ids"] += 1
            continue
        av = variant(gid)
        av.paragraphs.extend(p for item in v.paragraphs if (p := build(item)) is not None)

    # A variant group the plan left out entirely keeps the paragraphs of its first draft.
    for gid, members in group_ids.items():
        if gid in placed:
            continue
        pids = [pid for pid, (home, _, d) in paragraphs.items() if home == ("variant", gid)]
        first = min((paragraphs[pid][2] for pid in pids), default=None)
        av = variant(gid)
        for pid in pids:
            if paragraphs[pid][2] == first:
                av.paragraphs.append(DParagraph(text=paragraphs[pid][1].text, pmids=list(paragraphs[pid][1].pmids)))
                used.add(pid)
        stats["groups_restored"] += 1

    # A draft paragraph the plan did not use is put back only if it is the only one citing a paper.
    cited = direct.cited_in(merged)
    for pid, (home, x, d) in paragraphs.items():
        if pid in used or not squash(x.text):
            continue
        lost = {str(p).strip() for p in x.pmids} - cited
        if not lost:
            stats["unused"].append(pid)
            continue
        restored = DParagraph(text=x.text, pmids=list(x.pmids))
        if home[0] == "intro":
            if not squash(merged.intro.text):
                merged.intro = restored
            else:
                section("description").paragraphs.append(restored)
        elif home[0] == "section":
            section(home[1]).paragraphs.append(restored)
        else:
            variant(home[1]).paragraphs.append(restored)
        cited |= lost
        stats["restored"].append(pid)
    stats["draft_paragraphs"] = sum(1 for _, x, _ in paragraphs.values() if squash(x.text))
    stats["pmids_lost"] = sorted(set().union(*(direct.cited_in(r) for r in drafts)) - direct.cited_in(merged))
    return merged, stats


# --------------------------------------------------------------------------- #
# How much of each draft the merge kept (approximate, no model)
# --------------------------------------------------------------------------- #

_STOP = set("""a an the and or of in on at to for with by from as was were is are be been this that these those
it its their his her they he she which who whom whose than then also had has have not no all any each both
other into after before during between among about over under within without per one two three""".split())
_TOKEN = re.compile(r"[a-z0-9][a-z0-9'\-\.>]*", re.I)


def content_tokens(text: str) -> set[str]:
    out = set()
    for t in _TOKEN.findall(text.lower()):
        t = t.strip(".'-")
        if t and t not in _STOP and (len(t) > 2 or any(c.isdigit() for c in t)):
            out.add(t)
    return out


def retention(drafts: list[DEntry], merged: DEntry, threshold: float = 0.85) -> dict[str, Any]:
    """Per draft: its sentences, and how many have at least `threshold` of their content words in the merged draft.

    A rough mechanical estimate of what the merge kept; it cannot tell a statement
    kept from its words reused elsewhere.
    """
    merged_tokens = content_tokens(" ".join(x.text for x in direct._all_paragraphs(merged)))
    out = {}
    for d, raw in enumerate(drafts):
        sents = [squash(s) for x in direct._all_paragraphs(raw) for s in sentences(squash(x.text)) if squash(s)]
        kept = 0
        for s in sents:
            toks = content_tokens(s)
            if not toks or len(toks & merged_tokens) / len(toks) >= threshold:
                kept += 1
        out[DRAFTS[d]] = {"sentences": len(sents), "kept_approx": kept,
                          "chars": sum(len(squash(x.text)) for x in direct._all_paragraphs(raw))}
    out["merged"] = {"sentences": sum(len(sentences(squash(x.text))) for x in direct._all_paragraphs(merged)
                                      if squash(x.text)),
                     "chars": sum(len(squash(x.text)) for x in direct._all_paragraphs(merged))}
    return out


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    first, gene_facts, meta = baseline_draft(seed, papers, llm)
    # The two fresh samples; a stopped one raises LLMRefusal (no draft for the entry).
    with ThreadPoolExecutor(max_workers=len(SALTED)) as pool:
        others = list(pool.map(lambda k: direct.draft(seed, papers, salted(llm, k)), SALTED))
    drafts = [first, *(raw for raw, _, _ in others)]
    groups = variant_groups(drafts)
    prompt, paragraphs = merge_prompt(seed, papers, drafts, groups)
    plan = llm.call("merge_drafts", MERGE_DRAFTS_SYSTEM, prompt, EEntry)   # a stop raises: no draft
    merged, stats = assemble(plan, paragraphs, drafts, groups)
    kept = retention(drafts, merged)
    record = {
        "salts": [salt_for(getattr(getattr(llm, "settings", None), "replicate", "") or "", k) for k in SALTED],
        "variant_groups": len(groups), "variants_per_draft": [len(r.allelic_variants) for r in drafts],
        "merge": {k: (len(v) if isinstance(v, list) and k in ("restored", "unused") else v) for k, v in stats.items()},
        "unused_ids": stats["unused"], "restored_ids": stats["restored"],
        "retention": kept, "prompt_chars": len(prompt),
        "batching": [m.get("direct_batching", {}).get("used", False) for m in (meta, *(m for _, _, m in others))],
    }
    _write_json(Path(out_dir) / RECORD, {**record, "drafts": [r.model_dump() for r in drafts],
                                         "plan": plan.model_dump(), "merged": merged.model_dump()})
    log.info("[%s] direct_ensemble: %d draft paragraphs -> %d merged (%d multi-source), %d unused, %d restored",
             seed.mim or seed.title, stats["draft_paragraphs"], stats["merged_paragraphs"], stats["multi_source"],
             len(stats["unused"]), len(stats["restored"]))
    return draft_to_entry(seed, papers, merged, llm, strategy="direct_ensemble", gene_facts=gene_facts,
                          meta={**meta, "direct_ensemble": record})
