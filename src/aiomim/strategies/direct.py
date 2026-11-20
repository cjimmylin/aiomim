"""Direct reading: the baseline. See `synthesize.synthesize_direct`.

When the papers fit the single-prompt budget (`DIRECT_TOTAL_CHARS` of paper text
in all) the strategy is exactly `synthesize_direct`: one prompt, one call, and
the cached calls of earlier runs keep hitting.

Above that budget, which only entries with dozens of references reach, the
papers are read in batches:

1. They are sorted by date and cut into consecutive batches, each holding at
   most `BATCH_CHARS` of paper text, so no paper is shortened (a single paper
   longer than a whole batch is the only thing ever cut, and it is recorded).
2. Each batch gets the unchanged direct prompt and the model writes a partial
   entry from it, citing PMIDs as usual.
3. One merge call joins the partial entries. It does not see the papers and
   writes no new paragraph: it says, for every paragraph of the merged entry,
   which partial paragraphs it is made from, and may reword only where it
   combines paragraphs that say the same thing. A merged paragraph cites the
   union of its sources' PMIDs, assigned here rather than by the model, and any
   partial paragraph the merge did not place is put back where it was. Gene
   relationships and clinical-synopsis phrases are pooled without a model.
4. The merged draft goes through `draft_to_entry`, the same guards as always.

What happened is recorded in `entry.meta["direct_batching"]`.

The input limit of the model behind the CLI was measured, not assumed: the CLI
reports a 1,000,000-token context and a 128,000-token output ceiling for
claude-opus-5-5, and refuses a prompt of about 2.15M characters of
paper-like text ("~1,011,806 tokens (limit 1000000)"); 700,000 characters went
through as 336,000 input tokens. Paper text runs at about 2.2 characters per
token here, so the current 600,000-character budget is roughly 270,000 tokens,
far inside the limit; batches are kept to the same size so that each batch is
read the way a single-prompt entry is, rather than to stay under the ceiling.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field

from ..llm import LLMRefusal
from ..models import GeneratedEntry, Paper, SectionName, Seed, squash
from ..synthesize import (
    DIRECT_SYSTEM,
    DIRECT_TOTAL_CHARS,
    DAllelicVariant,
    DEntry,
    DParagraph,
    DRelationship,
    DSection,
    DSynopsisItem,
    _gene_reference,
    _header,
    direct_prompt,
    draft_to_entry,
    has_content,
    synthesize_direct,
)

log = logging.getLogger(__name__)

# Paper text per batch. The same figure as the single-prompt budget by default;
# AIOMIM_DIRECT_BATCH_CHARS overrides it (it never changes the threshold).
BATCH_CHARS = int(os.environ.get("AIOMIM_DIRECT_BATCH_CHARS") or DIRECT_TOTAL_CHARS)


def _ordered(papers: list[Paper]) -> list[Paper]:
    return sorted(papers, key=lambda p: (p.year or 9999, p.pmid))


def source_chars(papers: list[Paper]) -> int:
    """Paper text the direct prompt would carry before any truncation."""
    return sum(len(p.source_text()) for p in papers)


def needs_batching(papers: list[Paper], budget: int = DIRECT_TOTAL_CHARS) -> bool:
    """True when the papers' text exceeds the single-prompt budget."""
    return source_chars(papers) > budget


def plan_batches(papers: list[Paper], budget: int = BATCH_CHARS) -> list[list[Paper]]:
    """Consecutive date-ordered batches, each holding at most `budget` characters of paper text.

    Batches are as even as the date order allows: with k the fewest batches that
    can work, each is filled up to about 1/k of the text, so 650,000 characters
    become two batches of about 325,000 rather than one full batch and a scrap.
    k grows until every batch fits. A paper longer than the budget on its own
    forms a batch by itself (and is truncated to the budget when the prompt is
    built).
    """
    ordered = _ordered(papers)
    sizes = [min(len(p.source_text()), budget) for p in ordered]
    total = sum(sizes)
    k = max(1, -(-total // budget))
    while True:
        target = total / k
        batches: list[list[Paper]] = []
        current: list[Paper] = []
        size = 0
        for p, n in zip(ordered, sizes):
            # Close the batch when adding the paper would overshoot the target by
            # more than leaving it out undershoots it, or would break the budget.
            if current and (size + n > budget or (size + n - target > target - size and len(batches) < k - 1)):
                batches.append(current)
                current, size = [], 0
            current.append(p)
            size += n
        if current:
            batches.append(current)
        if len(batches) <= k or k >= len(ordered):
            return batches
        k += 1


def batch_prompt(seed: Seed, papers: list[Paper], gene_ref: str, budget: int = BATCH_CHARS) -> tuple[str, list[str]]:
    """The direct prompt for one batch, in exactly `synthesize_direct`'s layout.

    Only the per-paper cap differs: a batch is sized to its budget, so a paper is
    cut only if it alone exceeds the whole budget.
    """
    truncated, blocks = [], []
    for p in _ordered(papers):
        text = p.source_text()
        if len(text) > budget:
            truncated.append(p.pmid)
            text = text[:budget]
        blocks.append(f'<paper pmid="{p.pmid}" label="{p.label}" available="{p.content_level}">\n'
                      f"{p.reference}\n\n{text}\n</paper>")
    prompt = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none supplied'}\n\n"
        + "\n\n".join(blocks)
    )
    return prompt, truncated


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #

MERGE_SYSTEM = """\
You are a senior curator assembling one entry for OMIM (Online Mendelian Inheritance in Man) from \
partial entries. The papers for the entry were too many to read at once, so they were read in \
consecutive batches by publication date, and a partial entry was written from each batch. Each \
partial paragraph has an ID (P1, P2, ...) and each partial allelic variant an ID (V1, V2, ...).

Your job is editorial only. You do not have the papers, so you cannot add anything: no fact, \
number, variant, citation or interpretation that is not already in the partial paragraphs, and \
nothing from your own memory.

For each paragraph of the merged entry give `sources`, the IDs of the partial paragraphs it is made \
from, and `text`:
- To keep a partial paragraph as it is, give its ID alone and leave `text` empty. Most paragraphs \
  are of this kind: per-paper paragraphs in Clinical Features, Molecular Genetics and the allelic \
  variants come from a single batch and are kept word for word.
- Where several partial paragraphs say the same thing (each batch writes its own Description, \
  Inheritance and intro, for example), combine them into one paragraph: list all of them in \
  `sources` and write `text` using only what they say, keeping every author-year citation that \
  remains relevant. Where they disagree, say so rather than choosing.
- Keep paragraphs in chronological order of the reports within each section, and move a paragraph \
  to another section only if it plainly belongs there.

Use every partial paragraph exactly once. The intro is OMIM's opening sentence: write one for the \
whole entry from the partial intros (list them as its sources), naming every causal gene the \
partial intros name. Allelic variants: list each distinct variant once; where partial entries \
describe the same variant (same gene and same change), give all their V IDs in `sources` and put \
all of their paragraphs under it.\
"""


class MParagraph(BaseModel):
    sources: list[str] = Field(description='IDs of the partial paragraphs this paragraph is made from, e.g. ["P12"]')
    text: str = Field(description="Empty to keep a single source paragraph word for word; otherwise the "
                                  "combined text, using only what the sources say")


class MSection(BaseModel):
    name: SectionName
    paragraphs: list[MParagraph]


class MVariant(BaseModel):
    sources: list[str] = Field(description='IDs of the partial variants that are this variant, e.g. ["V3", "V17"]')
    name: str = Field(description='OMIM-style name, e.g. "GENE, ARG123TRP"')
    paragraphs: list[MParagraph]


class MEntry(BaseModel):
    intro: MParagraph
    sections: list[MSection]
    allelic_variants: list[MVariant]


def _merge_prompt(seed: Seed, partials: list[tuple[list[Paper], DEntry]]) -> tuple[str, dict, dict]:
    """Render the partial entries with IDs; return the prompt and the ID tables.

    paragraphs: Pn -> (home, DParagraph), where home is ("intro",), ("section", name)
    or ("variant", Vn). variants: Vn -> DAllelicVariant.
    """
    paragraphs: dict[str, tuple[tuple, DParagraph]] = {}
    variants: dict[str, DAllelicVariant] = {}
    lines = [_header(seed), ""]

    def para_line(home: tuple, x: DParagraph, labels: dict[str, str], indent: str = "") -> str:
        pid = f"P{len(paragraphs) + 1}"
        paragraphs[pid] = (home, x)
        cites = "; ".join(f"{p} = {labels.get(str(p).strip(), '?')}" for p in x.pmids) or "none"
        return f"{indent}[{pid}] (cites {cites}) {squash(x.text)}"

    for n, (batch, raw) in enumerate(partials, 1):
        labels = {p.pmid: p.label for p in batch}
        years = [p.year for p in batch if p.year]
        span = f"{min(years)}-{max(years)}" if years else "undated"
        lines.append(f"=== PARTIAL ENTRY {n} of {len(partials)}: {len(batch)} papers, {span} ===")
        lines.append("INTRO")
        lines.append(para_line(("intro",), raw.intro, labels))
        for section in raw.sections:
            lines.append(f"SECTION {section.name}")
            lines.extend(para_line(("section", section.name), x, labels) for x in section.paragraphs)
        if raw.allelic_variants:
            lines.append("ALLELIC VARIANTS")
        for av in raw.allelic_variants:
            vid = f"V{len(variants) + 1}"
            variants[vid] = av
            lines.append(f"[{vid}] {av.gene_symbol} | {squash(av.name)} | {'; '.join(av.hgvs)} | {squash(av.phenotype)}")
            lines.extend(para_line(("variant", vid), x, labels, "    ") for x in av.paragraphs)
        lines.append("")
    return "\n".join(lines), paragraphs, variants


def _pool_relationships(partials: list[DEntry]) -> list[DRelationship]:
    pooled: dict[str, DRelationship] = {}
    for raw in partials:
        for rel in raw.relationships:
            key = rel.gene_symbol.strip().upper()
            if key not in pooled:
                pooled[key] = DRelationship(gene_symbol=rel.gene_symbol, inheritance=[], pmids=[])
            have = pooled[key]
            have.inheritance = list(dict.fromkeys([*have.inheritance, *rel.inheritance]))
            have.pmids = list(dict.fromkeys([*have.pmids, *rel.pmids]))
    return list(pooled.values())


def _pool_synopsis(partials: list[DEntry]) -> list[DSynopsisItem]:
    pooled: dict[str, DSynopsisItem] = {}
    for raw in partials:
        for item in raw.clinical_synopsis:
            key = (item.hpo_label or item.feature).strip().lower()
            if key not in pooled:
                pooled[key] = DSynopsisItem(feature=item.feature, hpo_label=item.hpo_label, pmids=[])
            pooled[key].pmids = list(dict.fromkeys([*pooled[key].pmids, *item.pmids]))
    return list(pooled.values())


def _longer_than_sources(text: str, sources: list[DParagraph]) -> bool:
    """A combined paragraph should not be much longer than what it combines."""
    return len(text) > 1.2 * sum(len(squash(s.text)) for s in sources) + 200


def assemble(plan: MEntry | None, paragraphs: dict, variants: dict, partials: list[DEntry]) -> tuple[DEntry, dict]:
    """Build the merged draft from the merge plan, enforcing what the merge may do.

    Citations come from the sources, never from the model; a combined paragraph
    that grew well beyond its sources is replaced by them; every partial paragraph
    the plan did not use goes back where it came from, so no cited paper is lost.
    With no plan (merge call failed) the partial entries are simply concatenated.
    """
    used: set[str] = set()
    stats = {"combined": 0, "kept": 0, "rejected_longer": 0, "unknown_ids": 0, "restored": 0,
             "restored_intros": 0, "variants_merged": 0}

    def build(item: MParagraph) -> list[DParagraph]:
        ids = []
        for raw_id in item.sources:
            pid = str(raw_id).strip().strip("[]")
            if pid not in paragraphs:
                stats["unknown_ids"] += 1
            elif pid not in ids:
                ids.append(pid)
        fresh = [pid for pid in ids if pid not in used]
        text = squash(item.text)
        if not ids:
            return []
        sources = [paragraphs[pid][1] for pid in ids]
        if text and len(ids) > 1 and not _longer_than_sources(text, sources):
            used.update(ids)
            stats["combined"] += 1
            pmids = list(dict.fromkeys(str(p).strip() for s in sources for p in s.pmids))
            return [DParagraph(text=text, pmids=pmids)]
        if text and len(ids) > 1:
            stats["rejected_longer"] += 1
        # Kept word for word (one source, no text, or a rejected combination):
        # each unused source as it was. A single source the merge reworded is still
        # kept in its original words: rewording is allowed only to combine duplicates.
        used.update(fresh)
        stats["kept"] += len(fresh)
        return [DParagraph(text=paragraphs[pid][1].text, pmids=list(paragraphs[pid][1].pmids)) for pid in fresh]

    merged = DEntry(intro=DParagraph(text="", pmids=[]), sections=[], relationships=_pool_relationships(partials),
                    allelic_variants=[], clinical_synopsis=_pool_synopsis(partials))
    by_section: dict[str, DSection] = {}
    variant_home: dict[str, DAllelicVariant] = {}

    def section(name: str) -> DSection:
        if name not in by_section:
            by_section[name] = DSection(name=name, paragraphs=[])
            merged.sections.append(by_section[name])
        return by_section[name]

    if plan is not None:
        # The intro is one sentence: a combination of the partial intros, or else
        # the first one named, kept as written.
        ids = [i for i in dict.fromkeys(str(x).strip().strip("[]") for x in plan.intro.sources)
               if i in paragraphs]
        combined = (len(ids) > 1 and squash(plan.intro.text)
                    and not _longer_than_sources(squash(plan.intro.text), [paragraphs[i][1] for i in ids]))
        intro = build(plan.intro if combined else MParagraph(sources=ids[:1], text=""))
        if intro:
            merged.intro = intro[0]
        for s in plan.sections:
            target = section(s.name)
            for item in s.paragraphs:
                target.paragraphs.extend(build(item))
        for v in plan.allelic_variants:
            vids = [i for i in dict.fromkeys(str(x).strip().strip("[]") for x in v.sources)
                    if i in variants and i not in variant_home]
            if not vids:
                stats["unknown_ids"] += 1
                continue
            first = variants[vids[0]]
            av = DAllelicVariant(
                gene_symbol=first.gene_symbol, name=squash(v.name) or first.name,
                hgvs=list(dict.fromkeys(h for i in vids for h in variants[i].hgvs)),
                phenotype=first.phenotype, paragraphs=[],
            )
            for item in v.paragraphs:
                av.paragraphs.extend(build(item))
            for i in vids:
                variant_home[i] = av
            stats["variants_merged"] += len(vids) - 1
            merged.allelic_variants.append(av)

    # Put back what the plan left out, where it came from.
    for pid, (home, x) in paragraphs.items():
        if pid in used:
            continue
        restored = DParagraph(text=x.text, pmids=list(x.pmids))
        if home[0] == "intro":
            if not merged.intro.text:
                merged.intro = restored
                continue
            continue  # handled below if it is the only place a paper is cited
        stats["restored"] += 1 if plan is not None else 0
        if home[0] == "section":
            section(home[1]).paragraphs.append(restored)
        else:
            vid = home[1]
            if vid not in variant_home:
                src = variants[vid]
                variant_home[vid] = DAllelicVariant(gene_symbol=src.gene_symbol, name=src.name, hgvs=list(src.hgvs),
                                                    phenotype=src.phenotype, paragraphs=[])
                merged.allelic_variants.append(variant_home[vid])
            variant_home[vid].paragraphs.append(restored)
        used.add(pid)

    # An unused intro that is the only paragraph citing some paper is kept, as a
    # Description paragraph, so that no cited paper drops out of the entry.
    cited = {str(p).strip() for x in _all_paragraphs(merged) for p in x.pmids}
    for pid, (home, x) in paragraphs.items():
        if pid in used or home[0] != "intro":
            continue
        if {str(p).strip() for p in x.pmids} - cited:
            section("description").paragraphs.append(DParagraph(text=x.text, pmids=list(x.pmids)))
            cited |= {str(p).strip() for p in x.pmids}
            stats["restored_intros"] += 1
    return merged, stats


def _all_paragraphs(raw: DEntry) -> list[DParagraph]:
    return [raw.intro, *(x for s in raw.sections for x in s.paragraphs),
            *(x for v in raw.allelic_variants for x in v.paragraphs)]


def cited_in(raw: DEntry) -> set[str]:
    """PMIDs cited by a draft's paragraphs and gene relationships."""
    return ({str(p).strip() for x in _all_paragraphs(raw) for p in x.pmids if squash(x.text)}
            | {str(p).strip() for r in raw.relationships for p in r.pmids})


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def draft_batched(seed: Seed, papers: list[Paper], llm, budget: int = BATCH_CHARS,
                  system: str = DIRECT_SYSTEM) -> tuple[DEntry, dict, dict]:
    """The batched writer's merged draft, before the guards: (draft, nomenclature facts, meta).

    `system` is the writer's system prompt for every batch (direct reading's by
    default; a variant of direct reading passes its own). The merge of the partial
    entries is the same whatever the writer's prompt.
    """
    batches = plan_batches(papers, budget)
    gene_ref, gene_facts = _gene_reference(seed.gene_symbols)
    built = [batch_prompt(seed, batch, gene_ref, budget) for batch in batches]
    log.info("[%s] direct: %d papers, %d characters, read in %d batches", seed.mim or seed.title,
             len(papers), source_chars(papers), len(batches))
    replies = llm.map("synthesize", system, [b[0] for b in built], DEntry)

    # A reply with no paragraph at all is what the CLI hands back when the model
    # abandons a long structured answer (seen on large entries: the response is
    # stopped, the model then submits an empty skeleton, and the call "succeeds").
    # It would be cached like any other reply, so it is asked for once more afresh.
    retried: list[int] = []
    for i, reply in enumerate(replies):
        if isinstance(reply, DEntry) and not any(squash(x.text) for x in _all_paragraphs(reply)):
            retried.append(i + 1)
            try:
                replies[i] = llm.call("synthesize", system, built[i][0], DEntry, use_cache=False)
            except Exception as exc:  # noqa: BLE001 - recorded as a failed batch below
                replies[i] = exc
            if isinstance(replies[i], DEntry) and not any(squash(x.text) for x in _all_paragraphs(replies[i])):
                replies[i] = RuntimeError("the model returned an empty partial entry twice")

    partials: list[tuple[list[Paper], DEntry]] = []
    failed: list[dict] = []
    for n, (batch, reply) in enumerate(zip(batches, replies), 1):
        if isinstance(reply, Exception):
            log.warning("direct: batch %d of %d failed: %s", n, len(batches), reply)
            failed.append({"batch": n, "pmids": [p.pmid for p in batch], "error": f"{type(reply).__name__}: {reply}"[:300]})
        else:
            partials.append((batch, reply))
    if failed or not partials:
        # A draft built from only some of the batches would be scored as though it
        # had read every paper. No draft is the honest outcome.
        raise LLMRefusal(f"direct: {len(failed)} of {len(batches)} batches failed "
                         f"({failed[0]['error'] if failed else 'no batches'})")

    merge_stats: dict = {}
    if len(partials) == 1:
        merged = partials[0][1]
    else:
        prompt, paragraphs, variants = _merge_prompt(seed, partials)
        try:
            plan = llm.call("synthesize", MERGE_SYSTEM, prompt, MEntry)
            if not any(s.paragraphs for s in plan.sections):
                merge_stats["empty_plan_retried"] = True
                plan = llm.call("synthesize", MERGE_SYSTEM, prompt, MEntry, use_cache=False)
        except Exception as exc:  # noqa: BLE001 - fall back to concatenating the partial entries
            log.warning("direct: merge failed (%s); partial entries are concatenated", exc)
            plan = None
            merge_stats["merge_failed"] = f"{type(exc).__name__}: {exc}"[:300]
        merged, stats = assemble(plan, paragraphs, variants, [raw for _, raw in partials])
        merge_stats.update(stats, partial_paragraphs=len(paragraphs), partial_variants=len(variants),
                           merged_paragraphs=sum(1 for x in _all_paragraphs(merged) if squash(x.text)),
                           merged_variants=len(merged.allelic_variants))
        lost = set().union(*(cited_in(raw) for _, raw in partials)) - cited_in(merged)
        merge_stats["pmids_lost_in_merge"] = sorted(lost)

    meta = {"direct_batching": {
        "used": True,
        "threshold_chars": DIRECT_TOTAL_CHARS, "batch_chars": budget,
        "source_chars": source_chars(papers),
        "batches": [{"n_papers": len(b), "chars": sum(min(len(p.source_text()), budget) for p in b),
                     "years": [min((p.year for p in b if p.year), default=None),
                               max((p.year for p in b if p.year), default=None)],
                     "pmids": [p.pmid for p in _ordered(b)]} for b in batches],
        "failed_batches": failed,
        "empty_batches_retried": retried,
        "merge": merge_stats,
    }}
    truncated = [pmid for _, t in built for pmid in t]
    return merged, gene_facts, {"truncated_papers": truncated, **meta}


def run_batched(seed: Seed, papers: list[Paper], llm, budget: int = BATCH_CHARS) -> GeneratedEntry:
    merged, gene_facts, meta = draft_batched(seed, papers, llm, budget)
    return draft_to_entry(seed, papers, merged, llm, strategy="direct", gene_facts=gene_facts, meta=meta)


def draft(seed: Seed, papers: list[Paper], llm, system: str = DIRECT_SYSTEM) -> tuple[DEntry, dict, dict]:
    """Direct reading's draft before the guards: (draft, nomenclature facts, meta).

    Exactly the writer calls `run` makes (one prompt, or batches above the budget),
    so with the default `system` the replies of earlier direct-reading runs are
    read from the cache. For strategies that start from, or vary, direct reading's
    draft; `meta` holds `truncated_papers` and `direct_batching` as `run` records them.
    A stopped writer raises `LLMRefusal`, as in `run`.
    """
    if needs_batching(papers):
        return draft_batched(seed, papers, llm, system=system)
    prompt, truncated, gene_facts = direct_prompt(seed, papers)
    raw = llm.call("synthesize", system, prompt, DEntry, accept=has_content)
    return raw, gene_facts, {"truncated_papers": truncated,
                             "direct_batching": {"used": False, "threshold_chars": DIRECT_TOTAL_CHARS,
                                                 "source_chars": source_chars(papers)}}


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    if not needs_batching(papers):
        entry = synthesize_direct(seed, papers, llm)
        entry.meta["direct_batching"] = {"used": False, "threshold_chars": DIRECT_TOTAL_CHARS,
                                         "source_chars": source_chars(papers)}
        return entry
    return run_batched(seed, papers, llm)
