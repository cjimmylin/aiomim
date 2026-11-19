"""Evidence graph, matched (review, section 3, issue 2), and its hybrid with the papers' text.

`kg_matched` changes two things in the evidence-graph strategy and nothing else:

* per-paper extraction runs at the writer's effort (stage "extract_matched", the
  same prompts as "extract");
* the writer chooses the clinical-synopsis terms itself, from what the graph
  holds, instead of `synthesize._synopsis_from_graph`. Its phrases take the route
  direct reading's take (`synthesize.synopsis_from_phrases`): exact HPO match, else
  the model chooses among ontology search hits, so no HPO id is written by the
  model.

The writer still sees only the graph, and every paragraph must name the
quote-verified findings it rests on, as in `kg`.

`kg_hybrid` (see kg_hybrid.py) is the same, and the writer also receives the
papers' text, laid out exactly as direct reading lays it out
(`synthesize.paper_blocks`), with the graph as an aid. There a paragraph must
cite supplied papers; it may name findings it used, but need not.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from ..extract import extract_papers, ground_phenotypes
from ..kg import KnowledgeGraph, build_graph
from ..models import (
    AllelicVariantEntry,
    EntryParagraph,
    EntrySection,
    GeneratedEntry,
    GenePhenotypeRelationship,
    InheritanceCode,
    Paper,
    SectionName,
    Seed,
    squash,
)
from ..synthesize import (
    INTRO_RULE,
    KG_SYSTEM,
    STYLE,
    XEntry,
    _attach_text_citations,
    _codes,
    _gene_reference,
    _header,
    _kg_context,
    _labels,
    _order_sections,
    _references,
    _resolve_gene,
    _strip_mim_numbers,
    has_content,
    paper_blocks,
    synopsis_from_phrases,
)

log = logging.getLogger(__name__)

EXTRACT_STAGE = "extract_matched"

# --------------------------------------------------------------------------- #
# Reply schemas
# --------------------------------------------------------------------------- #


class KMSynopsisItem(BaseModel):
    feature: str
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    finding_ids: list[str] = Field(description='IDs of the findings reporting this feature, e.g. "8016139:3"')


class KMEntry(XEntry):
    clinical_synopsis: list[KMSynopsisItem]


class HParagraph(BaseModel):
    text: str
    pmids: list[str] = Field(description="PMIDs of the papers this paragraph draws on")
    finding_ids: list[str] = Field(description='IDs of graph findings this paragraph uses, e.g. "8016139:3"; '
                                               'may be empty')


class HSection(BaseModel):
    name: SectionName
    paragraphs: list[HParagraph]


class HRelationship(BaseModel):
    gene_symbol: str
    inheritance: list[InheritanceCode]
    pmids: list[str]
    finding_ids: list[str]


class HAllelicVariant(BaseModel):
    variant_id: str = Field(description='The variant\'s ID from the variant table, or "" if it is not in the table')
    gene_symbol: str
    name: str
    hgvs: list[str]
    phenotype: str
    paragraphs: list[HParagraph]


class HSynopsisItem(BaseModel):
    feature: str
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    pmids: list[str]


class KHEntry(BaseModel):
    intro: HParagraph
    sections: list[HSection]
    relationships: list[HRelationship]
    allelic_variants: list[HAllelicVariant]
    clinical_synopsis: list[HSynopsisItem]


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

# The evidence-graph writer's prompt, unchanged, plus the synopsis instruction
# direct reading gets (with finding IDs in place of PMIDs).
KG_MATCHED_SYSTEM = KG_SYSTEM + """

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name and the IDs of the findings reporting it. Choose them \
from the findings; the CLINICAL FEATURES table shows the HPO terms the findings' phenotypes were mapped \
to and how many papers report each present or absent.\
"""

KG_HYBRID_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header, the text of the papers to base it on, and an evidence graph assembled from \
those papers: quote-verified findings grouped by section, and tables showing which papers report each \
gene, variant, mode of inheritance and clinical feature. Write the entry from the papers, using the \
graph as an aid to find and organise what they report.

The supplied paper texts are the only admissible evidence; the graph's findings were extracted from \
them and their quotes checked, but a finding can be incomplete, and anything the papers say can be \
used whether or not a finding holds it. After you write, every sentence will be audited against the \
paper it cites. So write only what the papers say: no facts, numbers, variants, citations or \
interpretations from your own memory of the disorder, the gene, or the existing OMIM entry, however \
confident you are. Where only an abstract is supplied, rely only on the abstract. Never merge two \
papers' results into a claim neither paper made, and never attribute a result to a paper other than \
the one it came from.

For each paragraph, list in `pmids` the PMIDs of the papers it draws on; a paragraph that cites no \
supplied paper is discarded. In `finding_ids` you may list the graph findings the paragraph uses; leave \
it empty where you wrote from the text alone. Papers that turn out not to concern this entry's subject \
can be left uncited.

{STYLE}

{INTRO_RULE}

`relationships`: one item per gene that the papers show to cause this phenotype, with the mode(s) of \
inheritance they establish and the supporting PMIDs (and finding IDs, if any). Leave empty if none, or \
for a gene entry.

`allelic_variants`: one item per variant reported as disease-causing in patients, in chronological \
order of first report, with `hgvs` listing its nucleotide and protein names as the papers give them. \
Give its `variant_id` from the variant table when it is there, else "".

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name and the PMIDs reporting it.\
"""


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def write_from_graph(seed: Seed, kg: KnowledgeGraph, papers: list[Paper], llm, *, hybrid: bool,
                     strategy: str) -> GeneratedEntry:
    """The writer call and the same guards as `synthesize_from_graph`, with a writer-chosen synopsis."""
    context, genes = _kg_context(kg)
    gene_ref, gene_facts = _gene_reference(sorted(set(genes) | set(seed.gene_symbols)))
    truncated: list[str] = []
    if hybrid:
        blocks, truncated = paper_blocks(papers)
        prompt = (
            f"{_header(seed)}\n\n"
            f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
            + "\n\n".join(blocks)
            + f"\n\n<evidence>\n{context}\n</evidence>"
        )
        raw = llm.call("synthesize", KG_HYBRID_SYSTEM, prompt, KHEntry, accept=has_content)
    else:
        prompt = (
            f"{_header(seed)}\n\n"
            f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
            f"<evidence>\n{context}\n</evidence>"
        )
        raw = llm.call("synthesize", KG_MATCHED_SYSTEM, prompt, KMEntry, accept=has_content)

    by_pmid = {p.pmid: p for p in papers} | dict(kg.papers)
    label_to_pmid = _labels(by_pmid.values())
    dropped: list[str] = []
    unknown_citations: list[str] = []
    removed_mims: list[str] = []
    for rel in raw.relationships:
        _resolve_gene(rel.gene_symbol, gene_facts)
    allowed_mims = {f["mim"] for f in gene_facts.values() if f.get("mim")} | ({seed.mim} if seed.mim else set())

    def valid_findings(ids: list[str]) -> list[str]:
        return [i for i in dict.fromkeys(str(i).strip().strip("[]") for i in ids) if i in kg.findings]

    def paragraph(x, where: str) -> EntryParagraph | None:
        text = _strip_mim_numbers(squash(x.text), allowed_mims, removed_mims)
        if not text:
            return None
        valid = valid_findings(x.finding_ids)
        if hybrid:
            cited = [p for p in dict.fromkeys(str(i).strip() for i in (x.pmids or [])) if p in by_pmid]
            pmids = list(dict.fromkeys(cited + [kg.findings[i].pmid for i in valid]))
        else:
            if not valid:
                dropped.append(f"{where}: {text[:120]}")
                return None
            pmids = list(dict.fromkeys(kg.findings[i].pmid for i in valid))
        para = EntryParagraph(text=text, finding_ids=valid, pmids=pmids)
        _attach_text_citations(para, label_to_pmid, unknown_citations)
        if not para.pmids:
            dropped.append(f"{where}: {text[:120]}")
            return None
        return para

    entry = GeneratedEntry(
        mim=seed.mim, prefix=seed.prefix, entry_type=seed.entry_type, title=seed.title,
        alt_titles=seed.alt_titles, symbol=seed.symbol,
    )
    entry.intro = paragraph(raw.intro, "intro")
    entry.sections = _order_sections([
        EntrySection(name=s.name, paragraphs=[p for x in s.paragraphs if (p := paragraph(x, s.name))])
        for s in raw.sections
    ])

    for rel in raw.relationships:
        valid = valid_findings(rel.finding_ids)
        if hybrid:
            # As in direct reading: the gene must rest on supplied papers.
            pmids = [p for p in dict.fromkeys(str(i).strip() for i in rel.pmids) if p in by_pmid]
            pmids = list(dict.fromkeys(pmids + [kg.findings[i].pmid for i in valid]))
            if not pmids:
                dropped.append(f"relationship: {rel.gene_symbol}")
                continue
            symbol, facts = _resolve_gene(rel.gene_symbol, gene_facts)
        else:
            if not valid:
                dropped.append(f"relationship: {rel.gene_symbol}")
                continue
            symbol, facts = _resolve_gene(rel.gene_symbol, gene_facts)
            mentioned = {g for i in valid for g in kg.findings[i].genes} | \
                        {v.gene for i in valid for v in kg.findings[i].variants if v.gene}
            if symbol not in mentioned:
                close = [g for g in mentioned if g.endswith(symbol) or symbol.endswith(g)]
                if len(close) != 1:
                    dropped.append(f"relationship: {rel.gene_symbol} is not a gene of the findings cited for it")
                    continue
                symbol, facts = _resolve_gene(close[0], gene_facts)
            pmids = list(dict.fromkeys(kg.findings[i].pmid for i in valid))
        if any(r.gene_symbol == symbol for r in entry.relationships):
            continue
        entry.relationships.append(GenePhenotypeRelationship(
            phenotype=seed.title, phenotype_mim=seed.mim or "", gene_symbol=symbol,
            gene_mim=facts.get("mim", ""), location=facts.get("location", ""),
            inheritance=_codes(rel.inheritance), mapping_key=3, pmids=pmids,
        ))

    for x in raw.allelic_variants:
        node = kg.nodes.get(x.variant_id.strip()) if x.variant_id.strip() else None
        paras = [p for xp in x.paragraphs if (p := paragraph(xp, f"allelic variant {x.name}"))]
        if not paras:
            continue
        if node is None and not hybrid:
            dropped.append(f"allelic variant with unknown id {x.variant_id!r}")
            continue
        if node is not None:
            keys = [k for k in node.get("keys", []) if not k.startswith("raw:")]
            hgvs = list(dict.fromkeys(keys + (list(x.hgvs) if hybrid else [])))
            gene = node.get("gene", "")
            name = squash(x.name) or node.get("omim_name", "")
        else:
            hgvs, name = list(x.hgvs), squash(x.name)
            gene = _resolve_gene(x.gene_symbol, gene_facts)[0]
        entry.allelic_variants.append(AllelicVariantEntry(
            number=len(entry.allelic_variants) + 1, gene_symbol=gene, name=name, hgvs=hgvs,
            phenotype=squash(x.phenotype), paragraphs=paras,
        ))

    entry.inheritance = _codes([c for rel in entry.relationships for c in rel.inheritance])
    if not entry.inheritance:
        # As in `kg`: no causal gene established, so the mode most papers assert.
        entry.inheritance = list(kg.inheritance_support())[:1]

    if hybrid:
        phrases = [(i.feature, i.hpo_label,
                    [p for p in dict.fromkeys(str(x).strip() for x in i.pmids) if p in by_pmid])
                   for i in raw.clinical_synopsis]
    else:
        phrases = [(i.feature, i.hpo_label, list(dict.fromkeys(kg.findings[f].pmid
                                                               for f in valid_findings(i.finding_ids))))
                   for i in raw.clinical_synopsis]
    entry.clinical_synopsis, synopsis_stats = synopsis_from_phrases(phrases, llm)

    entry.assign_paragraph_ids()
    entry.references = _references(entry, by_pmid)
    entry.meta = {
        "strategy": strategy, "generated": date.today().isoformat(),
        "model": llm.settings.model_for("synthesize"),
        "dropped_ungrounded": dropped, "unknown_citations": sorted(set(unknown_citations)),
        "removed_cross_references": removed_mims, "kg": kg.stats(),
        "synopsis": {"chosen_by": "writer", "phrases": len(raw.clinical_synopsis),
                     "terms": len(entry.clinical_synopsis), "hpo_resolution": synopsis_stats},
        **({"truncated_papers": truncated, "paragraphs_citing_findings":
            sum(1 for p in entry.all_paragraphs() if p.finding_ids)} if hybrid else {}),
    }
    return entry


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def build(seed: Seed, papers: list[Paper], llm, out_dir: Path, *, hybrid: bool, strategy: str) -> GeneratedEntry:
    from ..pipeline import _write

    extractions = extract_papers(seed, papers, llm, stage=EXTRACT_STAGE)
    hpo_stats = ground_phenotypes(extractions, llm)
    # Own file names: the per-entry folder is shared with `kg`, whose files must stay as they are.
    _write(out_dir / f"extractions.{strategy}.json", [e.model_dump() for e in extractions])
    kg = build_graph(seed, papers, extractions)
    _write(out_dir / f"kg.{strategy}.json", kg.to_json())
    log.info("[%s] %s graph: %s", seed.mim or seed.title, strategy, kg.stats()["nodes"])
    entry = write_from_graph(seed, kg, papers, llm, hybrid=hybrid, strategy=strategy)
    n_found = sum(len(e.findings) for e in extractions)
    n_dropped = sum(len(e.dropped_findings) for e in extractions)
    entry.meta["extraction"] = {
        "stage": EXTRACT_STAGE, "effort": llm.settings.effort_for(EXTRACT_STAGE),
        "findings_kept": n_found, "findings_dropped_ungrounded": n_dropped,
        "quote_grounding_rate": round(n_found / (n_found + n_dropped), 3) if n_found + n_dropped else None,
        "papers_by_relevance": _count(e.relevance for e in extractions),
        "papers_failed": [e.pmid for e in extractions if e.error and not e.findings],
        "hpo_resolution": hpo_stats,
    }
    return entry


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    return build(seed, papers, llm, out_dir, hybrid=False, strategy="kg_matched")
