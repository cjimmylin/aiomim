"""Case table, matched (review, section 3, issue 2), and its hybrid with the papers' text.

`cohort_matched` changes three things in the case-table strategy and nothing else:

* per-paper case extraction runs at the writer's effort (stage "cases_matched",
  the same prompts as "cases");
* the writer chooses the clinical-synopsis terms from the table, instead of
  `CaseTable.synopsis`. Its phrases take the route direct reading's take
  (`synthesize.synopsis_from_phrases`): exact HPO match, else the model chooses
  among ontology search hits, so no HPO id is written by the model;
* the writer chooses the mode of inheritance, per confirmed gene and overall,
  instead of the rule (`record_mode` / `choose_modes`). The table is shown as in
  `cohort`, pooled feature tallies included; the rule's per-record genotype
  tallies are shown as evidence, but not its call.

Causal genes are unchanged: the writer confirms them from the table's candidates,
each with records carrying variants in it.

`cohort_hybrid` (see cohort_hybrid.py) is the same, and the writer also receives
the papers' text, laid out exactly as direct reading lays it out
(`synthesize.paper_blocks`). There a paragraph must cite supplied papers; it may
name records and notes it used, but need not.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..models import (
    AllelicVariantEntry,
    EntryParagraph,
    EntrySection,
    GenePhenotypeRelationship,
    GeneratedEntry,
    InheritanceCode,
    Paper,
    SectionName,
    Seed,
    squash,
)
from ..synthesize import (
    INTRO_RULE,
    STYLE,
    _attach_text_citations,
    _codes,
    _gene_reference,
    _header,
    _labels,
    _order_sections,
    _references,
    _resolve_gene,
    _strip_mim_numbers,
    has_content,
    paper_blocks,
    synopsis_from_phrases,
)
from .cohort import (
    CAllelicVariant,
    CaseTable,
    CParagraph,
    CSection,
    cohort_context,
    extract_cases,
    ground_case_phenotypes,
)
from .kg_matched import HSynopsisItem

log = logging.getLogger(__name__)

CASES_STAGE = "cases_matched"

# --------------------------------------------------------------------------- #
# Reply schemas
# --------------------------------------------------------------------------- #


class CMSynopsisItem(BaseModel):
    feature: str
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    evidence_ids: list[str] = Field(description='IDs of the records (R:...) reporting this feature')


class CMRelationship(BaseModel):
    gene_symbol: str = Field(description="A gene from the candidate list")
    inheritance: list[InheritanceCode] = Field(description="Mode(s) of inheritance the records show for this gene")
    record_ids: list[str] = Field(description='IDs of the records (R:...) whose patients show this gene causes the '
                                              'disorder of this entry')


class CMEntry(BaseModel):
    intro: CParagraph
    sections: list[CSection]
    relationships: list[CMRelationship]
    allelic_variants: list[CAllelicVariant]
    inheritance: list[InheritanceCode] = Field(description="Mode(s) of inheritance of this entry's disorder")
    clinical_synopsis: list[CMSynopsisItem]


class CHParagraph(BaseModel):
    text: str
    pmids: list[str] = Field(description="PMIDs of the papers this paragraph draws on")
    evidence_ids: list[str] = Field(description='IDs of records (R:...) and notes (N:...) this paragraph uses; '
                                                'may be empty')


class CHSection(BaseModel):
    name: SectionName
    paragraphs: list[CHParagraph]


class CHAllelicVariant(BaseModel):
    variant_id: str = Field(description='The variant\'s ID from the variant table, e.g. "V3", or "" if it is not '
                                        'in the table')
    gene_symbol: str
    name: str
    hgvs: list[str]
    phenotype: str
    paragraphs: list[CHParagraph]


class CHEntry(BaseModel):
    intro: CHParagraph
    sections: list[CHSection]
    relationships: list[CMRelationship]
    allelic_variants: list[CHAllelicVariant]
    inheritance: list[InheritanceCode] = Field(description="Mode(s) of inheritance of this entry's disorder")
    clinical_synopsis: list[HSynopsisItem]


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

_CHOICES = """\
`relationships`: the candidate causal genes are every gene with patient variants in a primary or \
supporting paper, so they can include genes that cause a sister disorder or a second condition in the \
same patients. From the candidates only, name the gene(s) that the records show to cause THIS entry's \
disorder, each with the mode(s) of inheritance the records show for it and the IDs of the records \
(R:...) whose patients carry variants in it and have this disorder. Judge from the evidence, not from \
memory. Leave it empty for a gene entry.

`inheritance`: the mode(s) of inheritance of this entry's disorder, as the patients' genotypes, the \
families' pedigrees and the authors' statements show them. Decide this yourself; the genotype patterns \
listed with the table are evidence for it, not a decision.

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name and the IDs of the records (R:...) reporting it. \
Choose them from the evidence; the CLINICAL FEATURES table shows the HPO terms the records' features \
were mapped to, with pooled counts of individuals.\
"""

COHORT_MATCHED_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header and a case table assembled from the literature: one quote-verified record \
per reported patient, family or patient group, pooled tables of clinical features, variants and genes, \
and notes holding the other citable results of each paper. Write the entry from this material, \
including its clinical synopsis and mode of inheritance.

The records and notes are the only admissible evidence. Each has already been checked against its \
paper, and after you write, every sentence will be audited against the paper it cites. So write only \
what the records, their quotes and the notes say: no facts, numbers, variants, citations or \
interpretations from your own memory of the disorder, the gene, or the existing OMIM entry, however \
confident you are. If the evidence leaves a gap, leave the gap. Never attribute a record or note to a \
paper other than the one it came from.

The pooled counts (how many individuals across all papers had a feature) are given to help you judge \
the clinical synopsis and are not statements any paper made: do not write cross-paper totals or \
percentages in the text. Report numbers per paper, as each paper gave them.

For each paragraph, list in `evidence_ids` exactly the records (R:...) and notes (N:...) it draws on. \
A paragraph with no valid ID is discarded. Papers marked "background" are context: draw on them only \
where they bear on this entry's subject. Use the evidence fully: in Clinical Features describe each \
paper's patients (who, how many, ancestry, consanguinity, onset, course and the salient findings) and \
in Molecular Genetics the variants found in them; a curator reading your entry should not need to \
reopen the papers to learn who was studied, what was found and how it was shown.

{STYLE}

{INTRO_RULE} Name in the intro exactly the genes you confirm in `relationships`.

{_CHOICES}

`allelic_variants`: one item per variant in the variant table that was reported as disease-causing in \
patients, keyed by its `variant_id`, in chronological order of first report, each with paragraphs \
citing the records that carry it. For a record marked MIXED GENOTYPES, do not attribute its \
features or numbers to the carriers of any one of its variants. `phenotype` is the disorder the variant causes, as named in this entry.\
"""

COHORT_HYBRID_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header, the text of the papers to base it on, and a case table assembled from those \
papers: one quote-verified record per reported patient, family or patient group, pooled tables of \
clinical features, variants and genes, and notes holding the other citable results of each paper. \
Write the entry from the papers, including its clinical synopsis and mode of inheritance, using the \
case table as an aid to find and organise what they report.

The supplied paper texts are the only admissible evidence; the records and notes were extracted from \
them and their quotes checked, but a record can be incomplete, and anything the papers say can be used \
whether or not a record holds it. After you write, every sentence will be audited against the paper it \
cites. So write only what the papers say: no facts, numbers, variants, citations or interpretations \
from your own memory of the disorder, the gene, or the existing OMIM entry, however confident you are. \
Where only an abstract is supplied, rely only on the abstract. Never attribute a result to a paper \
other than the one it came from.

The pooled counts in the case table (how many individuals across all papers had a feature) are given \
to help you judge the clinical synopsis and are not statements any paper made: do not write \
cross-paper totals or percentages in the text. Report numbers per paper, as each paper gave them.

For each paragraph, list in `pmids` the PMIDs of the papers it draws on; a paragraph that cites no \
supplied paper is discarded. In `evidence_ids` you may list the records (R:...) and notes (N:...) the \
paragraph uses; leave it empty where you wrote from the text alone. Papers that turn out not to concern \
this entry's subject can be left uncited.

{STYLE}

{INTRO_RULE} Name in the intro exactly the genes you confirm in `relationships`.

{_CHOICES}

`allelic_variants`: one item per variant reported as disease-causing in patients, in chronological \
order of first report, with `hgvs` listing its nucleotide and protein names as the papers give them. \
Give its `variant_id` from the variant table when it is there, else "".\
"""


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def render_entry(seed: Seed, table: CaseTable, inheritance: dict[str, Any], gene_ref: str,
                 gene_facts: dict[str, dict[str, str]], papers: list[Paper], llm, *, hybrid: bool,
                 strategy: str) -> GeneratedEntry:
    context = cohort_context(table, inheritance, call_inheritance=False)
    truncated: list[str] = []
    if hybrid:
        blocks, truncated = paper_blocks(papers)
        prompt = (
            f"{_header(seed)}\n\n"
            f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
            + "\n\n".join(blocks)
            + f"\n\n<case_table>\n{context}\n</case_table>"
        )
        raw = llm.call("synthesize", COHORT_HYBRID_SYSTEM, prompt, CHEntry, accept=has_content)
    else:
        prompt = (
            f"{_header(seed)}\n\n"
            f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
            f"<case_table>\n{context}\n</case_table>"
        )
        raw = llm.call("synthesize", COHORT_MATCHED_SYSTEM, prompt, CMEntry, accept=has_content)

    by_pmid = {p.pmid: p for p in papers} | dict(table.papers)
    evidence: dict[str, str] = {**{i: r.pmid for i, r in table.records.items()},
                                **{i: n.pmid for i, n in table.notes.items()}}
    label_to_pmid = _labels(by_pmid.values())
    dropped: list[str] = []
    unknown_citations: list[str] = []
    removed_mims: list[str] = []
    allowed_mims = {f["mim"] for f in gene_facts.values() if f.get("mim")} | ({seed.mim} if seed.mim else set())

    def valid_evidence(ids: list[str]) -> list[str]:
        return [i for i in dict.fromkeys(str(i).strip().strip("[]") for i in ids) if i in evidence]

    def paragraph(x, where: str) -> EntryParagraph | None:
        text = _strip_mim_numbers(squash(x.text), allowed_mims, removed_mims)
        if not text:
            return None
        valid = valid_evidence(x.evidence_ids)
        if hybrid:
            cited = [p for p in dict.fromkeys(str(i).strip() for i in (x.pmids or [])) if p in by_pmid]
            pmids = list(dict.fromkeys(cited + [evidence[i] for i in valid]))
        else:
            if not valid:
                dropped.append(f"{where}: {text[:120]}")
                return None
            pmids = list(dict.fromkeys(evidence[i] for i in valid))
        para = EntryParagraph(text=text, finding_ids=valid, pmids=pmids)
        _attach_text_citations(para, label_to_pmid, unknown_citations)
        if not para.pmids:
            dropped.append(f"{where}: {text[:120]}")
            return None
        return para

    entry = GeneratedEntry(mim=seed.mim, prefix=seed.prefix, entry_type=seed.entry_type, title=seed.title,
                           alt_titles=seed.alt_titles, symbol=seed.symbol)
    entry.intro = paragraph(raw.intro, "intro")
    entry.sections = _order_sections([
        EntrySection(name=s.name, paragraphs=[p for x in s.paragraphs if (p := paragraph(x, s.name))])
        for s in raw.sections
    ])

    rows = {r["id"]: r for r in table.variants}
    seen: set[str] = set()
    for x in raw.allelic_variants:
        row = rows.get(x.variant_id.strip()) if x.variant_id.strip() else None
        if row is None and not hybrid:
            dropped.append(f"allelic variant with unknown id {x.variant_id!r}")
            continue
        if row is not None and row["id"] in seen:
            continue
        paras = [p for xp in x.paragraphs if (p := paragraph(xp, f"allelic variant {x.name}"))]
        if not paras:
            continue
        if row is not None:
            seen.add(row["id"])
            hgvs = list(dict.fromkeys(list(row["keys"]) + (list(x.hgvs) if hybrid else [])))
            gene, name = row["gene"], squash(x.name) or row["omim_name"]
        else:
            hgvs, name = list(x.hgvs), squash(x.name)
            gene = _resolve_gene(x.gene_symbol, gene_facts)[0]
        entry.allelic_variants.append(AllelicVariantEntry(
            number=len(entry.allelic_variants) + 1, gene_symbol=gene, name=name, hgvs=hgvs,
            phenotype=squash(x.phenotype), paragraphs=paras,
        ))

    # Causal genes, as in `cohort`: from the table's candidates only, each on records
    # that carry variants in it. The mode is the writer's, not the rule's.
    overall = _codes(list(raw.inheritance))
    confirmed: dict[str, dict[str, list[str]]] = {}
    gene_decisions: dict[str, Any] = {"candidates": list(table.genes), "confirmed": [], "dropped": []}
    if seed.entry_type != "gene":
        for rel in raw.relationships:
            symbol = table.gene(rel.gene_symbol)
            if symbol not in table.genes:
                gene_decisions["dropped"].append({"gene": rel.gene_symbol, "reason": "not a candidate"})
                dropped.append(f"relationship: {rel.gene_symbol} is not a candidate gene of the case table")
                continue
            ids = [i.strip().strip("[]") for i in rel.record_ids]
            valid = [i for i in dict.fromkeys(ids)
                     if i in table.records and any(v.gene == symbol for v in table.records[i].variants)]
            if not valid:
                gene_decisions["dropped"].append({"gene": symbol, "reason": "no valid record id"})
                dropped.append(f"relationship: {rel.gene_symbol} cites no record carrying a variant in it")
                continue
            slot = confirmed.setdefault(symbol, {"records": [], "inheritance": []})
            slot["records"] += [i for i in valid if i not in slot["records"]]
            slot["inheritance"] = _codes(slot["inheritance"] + list(rel.inheritance))
    gene_decisions["confirmed"] = list(confirmed)
    gene_decisions["not_confirmed"] = [g for g in table.genes if g not in confirmed]

    for gene, slot in confirmed.items():
        facts = gene_facts.get(gene, {})
        entry.relationships.append(GenePhenotypeRelationship(
            phenotype=seed.title, phenotype_mim=seed.mim or "", gene_symbol=gene,
            gene_mim=facts.get("mim", ""), location=facts.get("location", ""),
            inheritance=slot["inheritance"] or overall, mapping_key=3, pmids=table.genes[gene]["pmids"],
        ))
    entry.inheritance = _codes([c for rel in entry.relationships for c in rel.inheritance]) or overall

    pheno = table.phenotype_table()
    if hybrid:
        phrases = [(i.feature, i.hpo_label, [p for p in dict.fromkeys(str(x).strip() for x in i.pmids) if p in by_pmid])
                   for i in raw.clinical_synopsis]
    else:
        phrases = [(i.feature, i.hpo_label, list(dict.fromkeys(evidence[e] for e in valid_evidence(i.evidence_ids))))
                   for i in raw.clinical_synopsis]
    entry.clinical_synopsis, synopsis_stats = synopsis_from_phrases(phrases, llm)
    for item in entry.clinical_synopsis:
        # The table's individual counts, where the term is one the records were mapped to.
        if item.hpo_id in pheno:
            item.n_present, item.n_assessed = pheno[item.hpo_id]["present"], pheno[item.hpo_id]["assessed"]

    entry.assign_paragraph_ids()
    entry.references = _references(entry, by_pmid)
    entry.meta = {
        "genes": gene_decisions,
        "strategy": strategy, "generated": date.today().isoformat(),
        "model": llm.settings.model_for("synthesize"),
        "dropped_ungrounded": dropped, "unknown_citations": sorted(set(unknown_citations)),
        "removed_cross_references": removed_mims,
        "synopsis": {"chosen_by": "writer", "phrases": len(raw.clinical_synopsis),
                     "terms": len(entry.clinical_synopsis), "hpo_resolution": synopsis_stats},
        "inheritance_choice": {"chosen_by": "writer", "overall": overall,
                               "per_gene": {g: s["inheritance"] for g, s in confirmed.items()},
                               "rule_would_call": list(inheritance["chosen"])},
        **({"truncated_papers": truncated, "paragraphs_citing_evidence":
            sum(1 for p in entry.all_paragraphs() if p.finding_ids)} if hybrid else {}),
    }
    return entry


def build(seed: Seed, papers: list[Paper], llm, out_dir: Path, *, hybrid: bool, strategy: str) -> GeneratedEntry:
    from ..pipeline import _write

    cases = extract_cases(seed, papers, llm, stage=CASES_STAGE)
    hpo_stats = ground_case_phenotypes(cases, llm)
    table = CaseTable(seed, {p.pmid: p for p in papers}, cases)

    gene_ref, gene_facts = _gene_reference(sorted(set(table.genes) | set(seed.gene_symbols)))
    table.x_genes = {g for g, f in gene_facts.items() if (f.get("location") or "").upper().startswith("X")}
    # Computed only to show the per-record genotype tallies, and to record what the
    # rule would have called; the entry's mode is the writer's.
    rule = table.compute_inheritance()
    entry = render_entry(seed, table, rule, gene_ref, gene_facts, papers, llm, hybrid=hybrid, strategy=strategy)
    gene_decisions = entry.meta.pop("genes")
    if gene_decisions["confirmed"]:
        entry.meta["inheritance_choice"]["rule_would_call_for_confirmed_genes"] = list(
            table.compute_inheritance(set(gene_decisions["confirmed"]))["chosen"])
    # Own file name: the per-entry folder is shared with `cohort`.
    _write(out_dir / f"cohort.{strategy}.json", {**table.to_json(rule), "gene_decisions": gene_decisions,
                                                  "inheritance_choice": entry.meta["inheritance_choice"]})
    totals = table.totals()
    n_rec = sum(len(c.records) for c in cases)
    n_rec_drop = sum(len(c.dropped_records) for c in cases)
    n_note = sum(len(c.notes) for c in cases)
    n_note_drop = sum(len(c.dropped_notes) for c in cases)
    entry.meta["cohort"] = {
        "stage": CASES_STAGE, "effort": llm.settings.effort_for(CASES_STAGE),
        "records_kept": n_rec, "records_dropped_ungrounded": n_rec_drop,
        "notes_kept": n_note, "notes_dropped_ungrounded": n_note_drop,
        "quote_grounding_rate": round((n_rec + n_note) / (n_rec + n_rec_drop + n_note + n_note_drop), 3)
        if n_rec + n_rec_drop + n_note + n_note_drop else None,
        "individuals_pooled": totals["individuals"], "families_pooled": totals["families"],
        "records_pooled": totals["records"], "follow_up_records": totals["follow_up_records"],
        "background_records": totals["background_records"],
        "papers_by_relevance": dict(Counter(c.relevance for c in cases)),
        "papers_failed": [c.pmid for c in cases if c.error and not c.records and not c.notes],
        "hpo_resolution": hpo_stats,
        "possible_duplicates": table.possible_duplicates(),
        "genes": {"candidates": gene_decisions["candidates"], "confirmed": gene_decisions["confirmed"],
                  "not_confirmed": gene_decisions["not_confirmed"], "dropped": gene_decisions["dropped"]},
    }
    log.info("[%s] %s: %d individuals, %d families, %d records", seed.mim or seed.title, strategy,
             totals["individuals"], totals["families"], totals["records"])
    return entry


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    return build(seed, papers, llm, out_dir, hybrid=False, strategy="cohort_matched")
