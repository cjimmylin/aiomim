"""Memory only: the control arm.

The model is given the entry's header and nothing else (no papers, no reference
list, no nomenclature data) and writes the entry as it remembers it. The draft is
not repaired; the pipeline audits it against the supplied papers, which measures
two things at once: how much of the entry the model has memorised, and how much
of what it remembers the accessible literature backs.

Citations are mapped to the supplied papers by author and year. A paragraph whose
citations match none of them (or that cites nothing) is kept, and is attributed to
every supplied paper, so that the audit can still find its claims supported
wherever the literature states them. `meta["closedbook"]["supplied_papers_cited"]`
counts the papers the draft cited by itself, before that attribution.

`draft` is shared with the `recall` strategy, which starts from the same draft.
"""

from __future__ import annotations

from pathlib import Path

from ..llm import LLM
from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import _CITATION, INTRO_RULE, STYLE, DEntry, _fold, _header, _labels, draft_to_entry

CLOSEDBOOK_SYSTEM = f"""\
You are a senior curator who knows OMIM (Online Mendelian Inheritance in Man) well. You are given only \
the header of an OMIM entry: its title, symbol, alternative titles and MIM number. You are given no \
papers. Write the entry as you know it, from memory.

This is a memory test. Afterwards every claim you make will be checked, one by one, against the \
published papers. So write what you actually remember and stop there. An honest short entry is worth \
more than an invented long one: if you remember only the outline of the disorder and its gene, write \
only that. Do not fabricate citations, authors, years, patient counts, ages, variants or any other \
number you do not remember; leave out a detail rather than guess it. Where you are unsure of a \
detail, say less, not something approximate.

Cite the primary papers in running text by first author and year, as OMIM does ("Jun et al. (1994) \
described ..."), so that each statement can be traced to the paper you remember it from. Give each \
reported family or study its own paragraph where you remember them separately. Leave `pmids` empty \
unless you are certain of a paper's PubMed ID.

{STYLE}

Since no reference data is supplied here, a gene's MIM number and chromosomal location may be given \
only if you are sure of them; never write any other OMIM cross-reference number.

{INTRO_RULE}

`relationships`: the gene(s) you know to cause this phenotype, with the mode(s) of inheritance. Leave \
empty if you do not know, or for a gene entry.

`allelic_variants`: the disease-causing variants you remember with confidence, each with the patients \
and report it comes from; `hgvs` lists its nucleotide and protein names as you remember them. Leave \
empty if you do not remember specific variants.

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name.\
"""


def draft(seed: Seed, llm: LLM) -> DEntry:
    """The raw memory draft. Only the header goes into the prompt."""
    return llm.call("recall", CLOSEDBOOK_SYSTEM, _header(seed), DEntry)


def _draft_texts(raw: DEntry) -> list[str]:
    texts = [raw.intro.text]
    texts += [p.text for s in raw.sections for p in s.paragraphs]
    texts += [p.text for av in raw.allelic_variants for p in av.paragraphs]
    return [t for t in texts if t and t.strip()]


def _matched_labels(raw: DEntry, papers: list[Paper]) -> list[str]:
    """Author-year citations in the draft that correspond to a supplied paper (same rule as draft_to_entry)."""
    known = [_fold(label) for label in _labels(papers)]
    out = []
    for text in _draft_texts(raw):
        for match in _CITATION.finditer(text):
            found = _fold(f"{match.group(1)} ({match.group(2)})")
            if any(label.endswith(found) or found.endswith(label) for label in known):
                out.append(f"{match.group(1)} ({match.group(2)})")
    return sorted(set(out))


def build(seed: Seed, papers: list[Paper], raw: DEntry, llm: LLM, *, strategy: str = "closedbook") -> GeneratedEntry:
    """The closed-book entry from a memory draft, with uncited paragraphs attributed to every paper."""
    supplied = [p.pmid for p in papers]
    offered_pmids = [str(i).strip() for x in _all_draft_paragraphs(raw) for i in (x.pmids or [])]
    entry = draft_to_entry(seed, papers, raw, llm, strategy=strategy, keep_uncited=True)

    paragraphs = entry.all_paragraphs()
    matched = [p for p in paragraphs if p.pmids]
    cited_from_memory = [pmid for pmid in entry.cited_pmids() if pmid in supplied]
    widened = 0
    for para in paragraphs:
        if not para.pmids and supplied:
            para.audit_pmids = list(supplied)
            widened += 1

    entry.meta["closedbook"] = {
        "paragraphs": len(paragraphs),
        "paragraphs_citing_supplied_papers": len(matched),
        "paragraphs_checked_against_all_papers": widened,
        "citations_matched": _matched_labels(raw, papers),
        "citations_unmatched": list(entry.meta.get("unknown_citations", [])),
        "pmids_offered": len(set(offered_pmids)),
        "pmids_offered_matching_supplied": len(set(offered_pmids) & set(supplied)),
        "supplied_papers": len(supplied),
        "supplied_papers_cited": len(cited_from_memory),
        "supplied_papers_cited_pmids": cited_from_memory,
        "reference_recall_from_memory": round(len(cited_from_memory) / len(supplied), 3) if supplied else None,
    }
    return entry


def _all_draft_paragraphs(raw: DEntry):
    yield raw.intro
    for s in raw.sections:
        yield from s.paragraphs
    for av in raw.allelic_variants:
        yield from av.paragraphs


def run(seed: Seed, papers: list[Paper], llm: LLM, out_dir: Path) -> GeneratedEntry:
    return build(seed, papers, draft(seed, llm), llm)
