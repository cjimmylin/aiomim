"""Recall, then verify.

The usual order inverted: the model first writes the entry from memory with no
papers (the `closedbook` draft), then the draft is taken claim by claim to the
papers with the standard audit (`verify.verify_entry`), and one rewrite keeps only
what the papers supported:

    supported            kept, attributed to the paper that supported it
    partially_supported  restated to say exactly what the evidence quote says
    contradicted         corrected to what the paper says (quote and auditor's note)
    unsupported          deleted
    not_checkable        deleted

The rewriter never sees the papers, only the draft and the audit, and may add
nothing that is not in one of them. Paragraphs left with no supporting paper are
dropped by `draft_to_entry`. The pipeline then audits the result again (and runs
its one repair round), which is where the reported faithfulness comes from.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from pydantic import Field

from ..llm import LLM
from ..models import EntryParagraph, GeneratedEntry, Paper, Seed
from ..synthesize import (
    INTRO_RULE,
    STYLE,
    DEntry,
    DParagraph,
    DRelationship,
    _gene_reference,
    _header,
    draft_to_entry,
)
from ..verify import verify_entry
from . import closedbook

log = logging.getLogger(__name__)

VERDICTS = ("supported", "partially_supported", "contradicted", "unsupported", "not_checkable")
KEPT = ("supported", "partially_supported", "contradicted")   # survive, possibly restated
BATCH_PARAGRAPHS = 40
BATCH_CHARS = 120_000


class RecallDraft(DEntry):
    omitted_claims: list[str] = Field(
        description='IDs of the audited claims you left out of the revised entry, e.g. "clinical_features.2#3"')


RECALL_SYSTEM = f"""\
You are a senior curator revising a draft entry for OMIM (Online Mendelian Inheritance in Man). The \
draft was written from memory, without sources. It has since been fact-checked claim by claim against \
the papers: for each paragraph you are given its text and, for every claim in it, the checker's \
verdict, the paper it was checked against (PMID and citation label), and either the passage from the \
paper that decides it or the checker's note.

Rewrite the entry so that it contains only what the papers support:
- supported: keep the claim.
- partially_supported: keep it, restated to say exactly what the evidence passage says and no more. \
The checker's note says which part goes beyond the paper: remove or narrow that part, and keep the \
paper's own scope, counts and qualifications (one family rather than families, "compatible with" or \
"suggested" rather than a firm statement). Do not keep the draft's wording where the note faults it.
- contradicted: correct it to what the paper says, as given by the passage and the checker's note. If \
the note and passage do not make clear what the paper says, delete the claim.
- unsupported or not_checkable: delete the claim.

You do not have the papers, only this audit. Add nothing that is not in the draft or in the evidence \
passages and notes: no new facts, numbers, variants, citations or interpretations, however sure you \
are of them. Where the audit leaves a gap, leave the gap. The entry you return is the draft with its \
unsupported parts removed and its errors corrected, not a new entry written from the passages: use \
an evidence passage only to restate or correct the claim it was given for, and do not take further \
details from it (other patients, numbers, findings or variants the claim did not mention), even \
though the passage contains them. A revised entry about as long as the surviving claims is expected.

Attribute every statement you keep to the paper that supported it, by its citation label written \
exactly as listed ("Jun et al. (1994) found ..."), and list in each paragraph's `pmids` the PMIDs of \
those papers. A claim supported by a \
paper other than the one the draft named is now attributed to the paper that supports it. Reorganise \
as OMIM style requires (one paragraph per report in Clinical Features and Molecular Genetics, in \
chronological order) and merge or drop paragraphs as deletions leave them; the result must still read \
as an OMIM entry, not as a list of claims. A paragraph with nothing left is omitted.

{STYLE}

{INTRO_RULE}

`relationships`, `allelic_variants` and `clinical_synopsis`: keep from the draft only the genes, \
variants and clinical features that surviving claims support, with the PMIDs of the papers that \
support them, and correct them where a claim about them was corrected. A gene is kept in \
`relationships` only if a surviving claim shows that it causes this phenotype.

`omitted_claims`: the IDs of every claim you left out, whatever the reason.\
"""


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #


def _claim_lines(para: EntryParagraph, labels: dict[str, str]) -> list[str]:
    lines = []
    for n, check in enumerate(para.checks, 1):
        source = f"{labels.get(check.pmid, 'PMID ' + check.pmid)}, PMID {check.pmid}" if check.pmid else "no paper"
        line = f"[{para.id}#{n}] {check.verdict.upper()} | {source} | claim: {check.claim}"
        if check.evidence_quote:
            line += f'\n    paper says: "{check.evidence_quote}"'
        if check.explanation:
            line += f"\n    checker: {check.explanation}"
        lines.append(line)
    return lines or [f"[{para.id}] (no claims could be extracted from this paragraph)"]


def _units(entry: GeneratedEntry) -> list[tuple[str, list[EntryParagraph]]]:
    """Blocks that stay together in one rewrite batch: each section, each allelic variant."""
    units: list[tuple[str, list[EntryParagraph]]] = []
    if entry.intro:
        units.append(("Intro", [entry.intro]))
    for section in entry.sections:
        units.append((f"Section: {section.name}", section.paragraphs))
    for av in entry.allelic_variants:
        hgvs = f" ({'; '.join(av.hgvs)})" if av.hgvs else ""
        units.append((f"Allelic variant: {av.name}{hgvs}, gene {av.gene_symbol}, phenotype {av.phenotype}",
                      av.paragraphs))
    return units


def _unit_text(title: str, paras: list[EntryParagraph], labels: dict[str, str]) -> str:
    blocks = [f"### {title}"]
    for para in paras:
        blocks.append(f'<paragraph id="{para.id}">\n{para.text}\n</paragraph>\nAudit:\n'
                      + "\n".join(_claim_lines(para, labels)))
    return "\n".join(blocks)


def _structured(raw: DEntry) -> str:
    rels = "\n".join(f"- {r.gene_symbol}: {', '.join(r.inheritance) or 'inheritance not given'}"
                     for r in raw.relationships) or "- none"
    synopsis = "\n".join(f"- {i.feature} [{i.hpo_label}]" for i in raw.clinical_synopsis) or "- none"
    return (f"Draft gene-phenotype relationships:\n{rels}\n\n"
            f"Draft clinical synopsis (features to keep only where a surviving claim reports them):\n{synopsis}")


def _batches(units: list[tuple[str, int]]) -> list[list[str]]:
    """Group whole units into batches of at most BATCH_PARAGRAPHS paragraphs / BATCH_CHARS characters."""
    batches: list[list[str]] = [[]]
    size = n = 0
    for text, count in units:
        if batches[-1] and (n + count > BATCH_PARAGRAPHS or size + len(text) > BATCH_CHARS):
            batches.append([])
            size = n = 0
        batches[-1].append(text)
        size += len(text)
        n += count
    return [b for b in batches if b]


def _merge(replies: list[RecallDraft]) -> RecallDraft:
    if len(replies) == 1:
        return replies[0]
    intro = next((r.intro for r in replies if r.intro.text.strip()), replies[0].intro)
    rels: dict[str, DRelationship] = {}
    for r in replies:
        for rel in r.relationships:
            key = rel.gene_symbol.upper()
            if key in rels:
                rels[key].inheritance = list(dict.fromkeys(rels[key].inheritance + rel.inheritance))
                rels[key].pmids = list(dict.fromkeys(rels[key].pmids + rel.pmids))
            else:
                rels[key] = rel.model_copy(deep=True)
    return RecallDraft(
        intro=intro,
        sections=[s for r in replies for s in r.sections],
        relationships=list(rels.values()),
        allelic_variants=[av for r in replies for av in r.allelic_variants],
        clinical_synopsis=[i for r in replies for i in r.clinical_synopsis],
        omitted_claims=[c for r in replies for c in r.omitted_claims],
    )


def _surviving_genes(raw: DEntry, memory: GeneratedEntry) -> list[str]:
    """Genes from the draft that a supported or corrected claim names: these get HGNC reference data."""
    claims = " ".join(c.claim + " " + c.evidence_quote for p in memory.all_paragraphs()
                      for c in p.checks if c.verdict in KEPT).upper()
    named = [r.gene_symbol for r in raw.relationships] + [av.gene_symbol for av in raw.allelic_variants]
    named += [r.gene_symbol for r in memory.relationships]
    return sorted({g for g in named if g and g.upper() in claims})


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def run(seed: Seed, papers: list[Paper], llm: LLM, out_dir: Path) -> GeneratedEntry:
    from ..pipeline import _write

    by_pmid = {p.pmid: p for p in papers}
    labels = {p.pmid: p.label for p in papers}

    raw = closedbook.draft(seed, llm)
    memory = closedbook.build(seed, papers, raw, llm, strategy="recall")
    verify_entry(memory, by_pmid, llm)
    _write(out_dir / "recall.memory_audit.json", memory.model_dump())

    checks = {f"{p.id}#{n}": c for p in memory.all_paragraphs() for n, c in enumerate(p.checks, 1)}
    by_verdict = Counter(c.verdict for c in checks.values())

    gene_ref, gene_facts = _gene_reference(_surviving_genes(raw, memory))
    head = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
        "Papers the claims were checked against:\n"
        + "\n".join(f"- PMID {p.pmid} = {p.label}" for p in sorted(papers, key=lambda p: (p.year or 9999, p.pmid)))
        + f"\n\n{_structured(raw)}\n\n"
    )
    units = [(_unit_text(title, paras, labels), len(paras)) for title, paras in _units(memory)]
    batches = _batches(units)
    note = ("" if len(batches) == 1 else
            "\n\nThis is part {i} of {n} of the draft; revise only the paragraphs shown here and the "
            "structured fields they support. Write the intro only if it is shown.")
    prompts = [head + "<draft>\n" + "\n\n".join(b) + "\n</draft>" + note.format(i=i, n=len(batches))
               for i, b in enumerate(batches, 1)]
    if checks:
        replies = llm.map("synthesize", RECALL_SYSTEM, prompts, RecallDraft)
        failed = [r for r in replies if isinstance(r, Exception)]
        if failed:
            log.warning("[%s] recall: %d of %d rewrite batches failed: %s",
                        seed.mim or seed.title, len(failed), len(replies), failed[0])
        good = [r for r in replies if not isinstance(r, Exception)]
        if not good:
            raise failed[0]
        revised = _merge(good)
    else:
        # Nothing could be audited (no papers, or no paragraphs): nothing survives.
        revised = RecallDraft(intro=DParagraph(text="", pmids=[]), sections=[], relationships=[],
                              allelic_variants=[], clinical_synopsis=[], omitted_claims=[])

    omitted = [c for c in dict.fromkeys(i.strip().strip("[]") for i in revised.omitted_claims) if c in checks]
    omitted_by_verdict = Counter(checks[c].verdict for c in omitted)
    entry = draft_to_entry(seed, papers, revised, llm, strategy="recall", gene_facts=gene_facts)

    total = len(checks)
    entry.meta["recall"] = {
        "memory_claims": total,
        "memory_claims_by_verdict": {v: by_verdict.get(v, 0) for v in VERDICTS},
        "memory_supported_rate": round(by_verdict.get("supported", 0) / total, 3) if total else None,
        "paragraphs_before": len(memory.all_paragraphs()),
        "paragraphs_after": len(entry.all_paragraphs()),
        "claims_omitted_by_verdict": {v: omitted_by_verdict.get(v, 0) for v in VERDICTS},
        "claims_survived_share": round((total - len(omitted)) / total, 3) if total else None,
        # Claims the instructions say must go but the rewrite did not report as omitted.
        "deletable_not_reported_omitted": sum(
            1 for cid, c in checks.items() if c.verdict in ("unsupported", "not_checkable") and cid not in omitted),
        "paragraphs_dropped_uncited": len(entry.meta.get("dropped_ungrounded", [])),
        "rewrite_batches": len(prompts) if checks else 0,
        "hgnc_genes": sorted(gene_facts),
        "memory": memory.meta.get("closedbook", {}),
    }
    return entry
