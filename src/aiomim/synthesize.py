"""Stage 5: write the OMIM-style entry.

Two strategies produce the same `GeneratedEntry`, so they can be scored side by
side:

kg      The writer sees only quote-verified findings, arranged by the knowledge
        graph (per section, with the cross-paper variant, gene, inheritance and
        phenotype tables). Every paragraph must name the findings it rests on;
        a paragraph that names none is removed. The clinical synopsis and the
        inheritance are computed from the graph, not written by the model.

direct  The baseline: the papers' text goes straight into one prompt and the
        model writes the entry, citing PMIDs. No extraction, no graph.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date

from pydantic import BaseModel, Field

from .extract import resolve_hpo_terms
from .kg import KnowledgeGraph
from .llm import LLM
from .models import (
    GENE_SECTIONS,
    INHERITANCE_HPO,
    PHENOTYPE_SECTIONS,
    SECTION_HEADINGS,
    SECTION_ORDER,
    AllelicVariantEntry,
    EntryParagraph,
    EntrySection,
    GeneratedEntry,
    GenePhenotypeRelationship,
    InheritanceCode,
    Paper,
    Reference,
    SectionName,
    Seed,
    SynopsisItem,
    squash,
)

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# House style, shared by both strategies
# --------------------------------------------------------------------------- #

STYLE = """\
OMIM house style
- Past tense, third person, plain declarative prose. Attribute every statement to its source using the \
citation label supplied for that paper, as the grammatical subject or in running text: "Novotny et al. \
(1986) described ...", "... was reported by Jun et al. (1994)".
- In Clinical Features and Molecular Genetics, give each paper (or each distinct family or study within \
a paper) its own paragraph, in chronological order. State who was studied (number of patients and \
families, ancestry, consanguinity), then the salient findings. Keep the numbers, ages and units exactly \
as given.
- Description is a short overview of the disorder (or gene product): two to four sentences defining its \
cardinal features, without restating individual case reports.
- Inheritance states the transmission pattern and which report(s) established it.
- Molecular Genetics states, per report, in whom the variants were found, in which gene, their zygosity, \
how they were found, segregation or de novo occurrence, and any functional evidence.
- Variant notation: write nucleotide changes with a hyphen ("c.367C-T transition"), amino acid changes \
as "arg123-to-trp (R123W)", and use "mutation" for a disease-causing variant, as OMIM does. Use "sibs" \
for siblings.
- Each allelic variant gets a name in OMIM form, "GENE, ARG123TRP" or "GENE, 3697G-A" or \
"GENE, 1-BP DEL, 1234A", and one paragraph per report that describes the patients carrying it, the \
change at nucleotide and protein level, zygosity, and the evidence for pathogenicity.
- Do not write OMIM cross-reference numbers: no allelic-variant numbers such as "(516006.0002)" and \
no MIM numbers of other disorders such as "(540000)". They are not in the evidence, so any you wrote \
would come from memory. The only MIM numbers allowed are those listed in the reference data, used \
where a gene is first named.
- Include a section only if there is material for it. Do not pad, do not speculate, do not add \
general background knowledge, and do not smooth over disagreements between reports: describe them.\
"""

INTRO_RULE = """\
The `intro` is OMIM's opening sentence. For a phenotype whose molecular basis is known it reads: "A \
number sign (#) is used with this entry because of evidence that <disorder> (<symbol>) is caused by \
<heterozygous | homozygous | compound heterozygous | hemizygous | ...> mutation in the <GENE> gene \
(<gene MIM number>) on chromosome <location>." Take the zygosity and gene from the evidence, and the \
gene's MIM number and location from the reference data provided. If several genes are involved, name \
every one of them (the same genes you list in `relationships`). If the evidence does not establish a causal gene, write one sentence saying what the entry \
describes instead, without the number-sign formula. For a gene entry leave the intro text empty.\
"""


# --------------------------------------------------------------------------- #
# Reply schemas
# --------------------------------------------------------------------------- #


class XParagraph(BaseModel):
    text: str
    finding_ids: list[str] = Field(description='IDs of the findings this paragraph rests on, e.g. "8016139:3"')


class XSection(BaseModel):
    name: SectionName
    paragraphs: list[XParagraph]


class XRelationship(BaseModel):
    gene_symbol: str
    inheritance: list[InheritanceCode]
    finding_ids: list[str]


class XAllelicVariant(BaseModel):
    variant_id: str = Field(description="The variant's ID from the variant table")
    name: str
    phenotype: str
    paragraphs: list[XParagraph]


class XEntry(BaseModel):
    intro: XParagraph
    sections: list[XSection]
    relationships: list[XRelationship]
    allelic_variants: list[XAllelicVariant]


class DParagraph(BaseModel):
    text: str
    pmids: list[str]


class DSection(BaseModel):
    name: SectionName
    paragraphs: list[DParagraph]


class DRelationship(BaseModel):
    gene_symbol: str
    inheritance: list[InheritanceCode]
    pmids: list[str]


class DAllelicVariant(BaseModel):
    gene_symbol: str
    name: str
    hgvs: list[str]
    phenotype: str
    paragraphs: list[DParagraph]


class DSynopsisItem(BaseModel):
    feature: str
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    pmids: list[str]


class DEntry(BaseModel):
    intro: DParagraph
    sections: list[DSection]
    relationships: list[DRelationship]
    allelic_variants: list[DAllelicVariant]
    clinical_synopsis: list[DSynopsisItem]


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

_CITATION = re.compile(r"([A-Z][\w'’\-]+(?: [A-Z][\w'’\-]+)?(?: et al\.| and [A-Z][\w'’\-]+)?) \((\d{4})\)")
# The parenthetical form: "(Boyden et al., 2012)", "(Jun and Brown, 1994; ...)".
_CITATION_PAREN = re.compile(r"([A-Z][\w'’\-]+(?: [A-Z][\w'’\-]+)?(?: et al\.| and [A-Z][\w'’\-]+)?),? (\d{4})(?=[;,)])")


def _header(seed: Seed) -> str:
    kind = "gene" if seed.entry_type == "gene" else "phenotype (disorder)"
    lines = [f"Entry to write: {kind} entry", f"Title: {seed.title}"]
    if seed.symbol:
        lines.append(f"Symbol: {seed.symbol}")
    if seed.alt_titles:
        lines.append("Alternative titles: " + "; ".join(seed.alt_titles))
    if seed.mim:
        lines.append(f"MIM number: {seed.mim}")
    sections = GENE_SECTIONS if seed.entry_type == "gene" else PHENOTYPE_SECTIONS
    lines.append("Sections available: " + ", ".join(sections))
    return "\n".join(lines)


def _gene_reference(symbols: list[str]) -> tuple[str, dict[str, dict[str, str]]]:
    """Nomenclature facts for the genes in play (HGNC), for the intro and the gene map."""
    from .sources.hgnc import gene_info

    facts: dict[str, dict[str, str]] = {}
    lines = []
    for symbol in symbols:
        try:
            info = gene_info(symbol)
        except Exception as exc:  # noqa: BLE001 - nomenclature lookup is best-effort
            log.warning("HGNC lookup failed for %s: %s", symbol, exc)
            info = None
        if info is None:
            continue
        facts[info.symbol] = {"location": info.location or "", "mim": info.omim_id or ""}
        lines.append(f"{info.symbol}: MIM number {info.omim_id or 'unknown'}; location {info.location or 'unknown'}")
    return "\n".join(lines), facts


def _resolve_gene(symbol: str, facts: dict[str, dict[str, str]]) -> tuple[str, dict[str, str]]:
    """Approved symbol and nomenclature facts for a gene the writer named, alias or not."""
    from .sources.hgnc import normalize_symbol

    try:
        approved = normalize_symbol(symbol) or symbol.upper()
    except Exception as exc:  # noqa: BLE001 - nomenclature lookup is best-effort
        log.warning("HGNC lookup failed for %s: %s", symbol, exc)
        approved = symbol.upper()
    if approved not in facts:
        facts.update(_gene_reference([approved])[1])
    return approved, facts.get(approved, {})


_AV_NUMBER = re.compile(r"\b\d{6}\.\d{4}\b")
_PARENTHETICAL = re.compile(r"\(([^()]*)\)")
_BARE_MIM = re.compile(r"^(?:see|e\.g\.,?|MIM|OMIM)?\s*#?\s*([1-6]\d{5})$", re.I)


def _strip_mim_numbers(text: str, allowed: set[str], removed: list[str]) -> str:
    """Delete OMIM cross-reference numbers the evidence cannot have supplied.

    Papers do not contain OMIM allelic-variant numbers, and the only MIM numbers
    given to the writer are the entry's own and those of the genes in the HGNC
    reference data. Any other cross-reference in the draft was recalled by the
    model, so it is removed here and counted, whatever the prompt said.

    Only OMIM's own cross-reference syntax is touched: "NNNNNN.NNNN" anywhere, and
    a bare six-digit number standing alone as an item inside parentheses, as in
    "(540000)" or "(LHON; 535000)". Six-digit quantities in running text are left
    alone.
    """
    def clean_group(match: re.Match) -> str:
        kept = []
        for item in re.split(r"\s*;\s*", match.group(1)):
            item = _AV_NUMBER.sub(lambda m: removed.append(m.group(0)) or "", item).strip(" ,")
            bare = _BARE_MIM.match(item)
            if bare and bare.group(1) not in allowed:
                removed.append(bare.group(1))
                continue
            if item:
                kept.append(item)
        return f"({'; '.join(kept)})" if kept else ""

    text = _PARENTHETICAL.sub(clean_group, text)
    text = _AV_NUMBER.sub(lambda m: removed.append(m.group(0)) or "", text)
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _labels(papers) -> dict[str, list[str]]:
    """Citation label -> PMIDs. Two papers can share a label (same first author and year)."""
    out: dict[str, list[str]] = {}
    for paper in papers:
        out.setdefault(paper.label, []).append(paper.pmid)
    return out


def _fold(text: str) -> str:
    """Accent- and case-insensitive form for comparing author names: 'Müller et al.' ~ 'Muller et al'."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).replace("ø", "o").replace("Ø", "O")
    return re.sub(r"[.,'’`\-]", "", text).lower()


def _attach_text_citations(para: EntryParagraph, label_to_pmids: dict[str, list[str]], unknown: list[str]) -> None:
    """Make sure every 'Author et al. (year)' named in the text is among the paragraph's PMIDs.

    A citation that matches no supplied paper is recorded: it would be a reference
    the writer brought in from outside the evidence, or one that a supplied paper
    itself cites.
    """
    text = _fold(para.text)
    known = {_fold(label): pmids for label, pmids in label_to_pmids.items()}
    for label, pmids in known.items():
        # "Jun et al. (1994)" in running text, or "(Jun et al., 1994)" in parentheses.
        parenthetical = re.sub(r" \((\d{4}|nd)\)$", r" \1", label)
        if (label in text or parenthetical in text) and not set(pmids) & set(para.pmids):
            # Ambiguous labels attach every candidate, so the audit checks them all.
            para.pmids.extend(pmids)
    cited = [(m.group(1), m.group(2)) for m in _CITATION.finditer(para.text)]
    cited += [(m.group(1), m.group(2)) for m in _CITATION_PAREN.finditer(para.text)]
    for name, year in cited:
        found = _fold(f"{name} ({year})")
        # The pattern may clip a surname particle ("van der Knaap") or swallow a
        # leading capitalised word ("In Smith"); either way it overlaps a known label.
        if not any(label.endswith(found) or found.endswith(label) for label in known):
            unknown.append(f"{name} ({year})")


def _references(entry: GeneratedEntry, papers: dict[str, Paper]) -> list[Reference]:
    refs = [
        Reference(pmid=pmid, label=papers[pmid].label, citation=papers[pmid].reference,
                  content_level=papers[pmid].content_level)
        for pmid in entry.cited_pmids() if pmid in papers
    ]
    return sorted(refs, key=lambda r: (r.label.lower(), r.pmid))


def _order_sections(sections: list[EntrySection]) -> list[EntrySection]:
    merged: dict[str, EntrySection] = {}
    for section in sections:
        if not section.paragraphs:
            continue
        if section.name in merged:
            merged[section.name].paragraphs.extend(section.paragraphs)
        else:
            section.heading = SECTION_HEADINGS.get(section.name, section.name)
            merged[section.name] = section
    return sorted(merged.values(), key=lambda s: SECTION_ORDER.index(s.name) if s.name in SECTION_ORDER else 99)


def _codes(values: list[str]) -> list[str]:
    return [c for c in dict.fromkeys(values) if c in INHERITANCE_HPO]


# --------------------------------------------------------------------------- #
# Strategy 1: from the knowledge graph
# --------------------------------------------------------------------------- #

KG_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header and an evidence graph assembled from the literature: quote-verified findings \
grouped by section, and tables showing which papers report each gene, variant, mode of inheritance and \
clinical feature. Write the entry from this evidence.

The findings are the only admissible evidence. Each one has already been checked against its paper, \
and after you write, every sentence will be audited against the paper it cites. So write only what the \
findings say: no facts, numbers, variants, citations or interpretations from your own memory of the \
disorder, the gene, or the existing OMIM entry, however confident you are. If the findings leave a gap, \
leave the gap. Never merge two papers' results into a claim neither paper made, and never attribute a \
finding to a paper other than the one it came from.

For each paragraph, list in `finding_ids` exactly the findings it draws on. A paragraph with no \
finding IDs is discarded. Papers marked "background" are context: draw on them only where they bear \
on this entry's subject. Use the findings fully: a curator reading your entry should not need to \
reopen the papers to learn who was studied, what was found and how it was shown.

{STYLE}

{INTRO_RULE}

`relationships`: one item per gene that the evidence shows to cause this phenotype (patient variants \
with segregation, de novo occurrence or functional support), with the mode(s) of inheritance the \
evidence establishes for it and the supporting finding IDs. Leave it empty if no causal gene is \
established. For a gene entry, leave it empty.

`allelic_variants`: one item per variant in the variant table that was reported as disease-causing in \
patients, keyed by its `variant_id`, in chronological order of first report. `phenotype` is the \
disorder the variant causes, as named in this entry.\
"""


def _kg_context(kg: KnowledgeGraph) -> tuple[str, list[str]]:
    lines: list[str] = []
    papers = sorted(kg.papers.values(), key=lambda p: (p.year or 9999, p.pmid))
    counts: dict[str, int] = {}
    for f in kg.findings.values():
        counts[f.pmid] = counts.get(f.pmid, 0) + 1

    lines.append("PAPERS")
    for p in papers:
        if p.pmid not in kg.relevance:
            continue
        lines.append(f"- {p.label} | PMID {p.pmid} | {kg.relevance[p.pmid]} | text: {p.content_level} | "
                     f"{counts.get(p.pmid, 0)} findings | {p.title}")

    def labels(pmids: list[str]) -> str:
        return "; ".join(kg.papers[p].label for p in pmids if p in kg.papers)

    gene_support = kg.gene_support()
    lines.append("\nGENES WITH PATIENT VARIANTS (papers reporting them)")
    lines.extend(f"- {g}: {labels(s['pmids'])}" for g, s in gene_support.items())
    if not gene_support:
        lines.append("- none")

    lines.append("\nMODES OF INHERITANCE ASSERTED (papers)")
    inheritance = kg.inheritance_support()
    lines.extend(f"- {code} ({INHERITANCE_HPO[code][1]}): {labels(pmids)}" for code, pmids in inheritance.items())
    if not inheritance:
        lines.append("- none stated")

    lines.append("\nVARIANT TABLE (one row per distinct variant after merging names across papers)")
    for node in kg.variant_nodes():
        reports = kg.findings_for(node["id"])
        if not reports:
            continue
        named = " / ".join(k for k in node.get("keys", []) if not k.startswith("raw:")) or node["label"]
        cited = "; ".join(dict.fromkeys(f"{kg.papers[f.pmid].label} [{f.id}]" for f in reports if f.pmid in kg.papers))
        lines.append(f"- variant_id={node['id']} | gene {node.get('gene', '?')} | {named} | reported in: {cited}")

    profile = kg.phenotype_profile()
    if profile:
        lines.append("\nCLINICAL FEATURES (HPO term: papers reporting it present / absent)")
        for hpo_id, row in sorted(profile.items(), key=lambda kv: (-len(kv[1]["present"]), kv[1]["label"])):
            lines.append(f"- {row['label']} ({hpo_id}): {len(row['present'])} present, {len(row['absent'])} absent")

    lines.append("\nFINDINGS BY SECTION")
    for section in SECTION_ORDER:
        findings = kg.findings_in(section)
        if not findings:
            continue
        lines.append(f"\n## {section}")
        for f in findings:
            tags = []
            if f.variants:
                tags.append("variants: " + ", ".join(v.key for v in f.variants if v.key))
            if f.n_affected is not None:
                tags.append(f"n_affected={f.n_affected}")
            if f.n_families is not None:
                tags.append(f"n_families={f.n_families}")
            if f.population:
                tags.append(f"population: {f.population}")
            if kg.relevance.get(f.pmid) == "background":
                tags.append("background paper")
            suffix = f"  ({'; '.join(tags)})" if tags else ""
            lines.append(f"[{f.id}] {f.statement}{suffix}")
    return "\n".join(lines), list(gene_support)


def _synopsis_from_graph(kg: KnowledgeGraph) -> list[SynopsisItem]:
    """Clinical synopsis computed from the graph: features with more support than refutation."""
    from .sources.hpo import get_hpo

    hpo = get_hpo()
    profile = {t: row for t, row in kg.phenotype_profile().items()
               if row["present"] and len(row["present"]) >= len(row["absent"])}
    items = []
    for hpo_id, row in profile.items():
        # A general term adds nothing when a more specific one rests on the same papers.
        ancestors_of_others = any(
            other != hpo_id and hpo_id in hpo.ancestors(other, include_self=False)
            and set(row["present"]) <= set(profile[other]["present"])
            for other in profile
        )
        if ancestors_of_others:
            continue
        items.append(SynopsisItem(category=hpo.category(hpo_id), feature=row["text"], hpo_id=hpo_id,
                                  hpo_label=row["label"], pmids=row["present"], n_papers=len(row["present"])))
    return sorted(items, key=lambda i: (i.category, -i.n_papers, i.hpo_label))


def synthesize_from_graph(seed: Seed, kg: KnowledgeGraph, llm: LLM) -> GeneratedEntry:
    context, genes = _kg_context(kg)
    gene_ref, gene_facts = _gene_reference(sorted(set(genes) | set(seed.gene_symbols)))
    prompt = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
        f"<evidence>\n{context}\n</evidence>"
    )
    raw = llm.call("synthesize", KG_SYSTEM, prompt, XEntry)

    label_to_pmid = _labels(kg.papers.values())
    dropped: list[str] = []
    unknown_citations: list[str] = []
    removed_mims: list[str] = []
    allowed_mims = {f["mim"] for f in gene_facts.values() if f.get("mim")} | ({seed.mim} if seed.mim else set())

    def paragraph(x: XParagraph, where: str) -> EntryParagraph | None:
        text = _strip_mim_numbers(squash(x.text), allowed_mims, removed_mims)
        if not text:
            return None
        ids = [i.strip().strip("[]") for i in x.finding_ids]
        valid = [i for i in dict.fromkeys(ids) if i in kg.findings]
        if not valid:
            dropped.append(f"{where}: {text[:120]}")
            return None
        para = EntryParagraph(text=text, finding_ids=valid,
                              pmids=list(dict.fromkeys(kg.findings[i].pmid for i in valid)))
        _attach_text_citations(para, label_to_pmid, unknown_citations)
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
        valid = [i for i in rel.finding_ids if i in kg.findings]
        if not valid:
            dropped.append(f"relationship: {rel.gene_symbol}")
            continue
        symbol, facts = _resolve_gene(rel.gene_symbol, gene_facts)
        # The gene must be one that the cited findings are actually about; this is
        # what keeps the gene table a product of the graph rather than of the prose.
        mentioned = {g for i in valid for g in kg.findings[i].genes} | \
                    {v.gene for i in valid for v in kg.findings[i].variants if v.gene}
        if symbol not in mentioned:
            close = [g for g in mentioned if g.endswith(symbol) or symbol.endswith(g)]
            if len(close) != 1:
                dropped.append(f"relationship: {rel.gene_symbol} is not a gene of the findings cited for it")
                continue
            symbol, facts = _resolve_gene(close[0], gene_facts)
        if any(r.gene_symbol == symbol for r in entry.relationships):
            continue
        entry.relationships.append(GenePhenotypeRelationship(
            phenotype=seed.title, phenotype_mim=seed.mim or "", gene_symbol=symbol,
            gene_mim=facts.get("mim", ""), location=facts.get("location", ""),
            inheritance=_codes(rel.inheritance), mapping_key=3,
            pmids=list(dict.fromkeys(kg.findings[i].pmid for i in valid)),
        ))

    for x in raw.allelic_variants:
        node = kg.nodes.get(x.variant_id)
        paras = [p for xp in x.paragraphs if (p := paragraph(xp, f"allelic variant {x.name}"))]
        if node is None or not paras:
            if node is None:
                dropped.append(f"allelic variant with unknown id {x.variant_id!r}")
            continue
        entry.allelic_variants.append(AllelicVariantEntry(
            number=len(entry.allelic_variants) + 1, gene_symbol=node.get("gene", ""),
            name=squash(x.name) or node.get("omim_name", ""),
            hgvs=[k for k in node.get("keys", []) if not k.startswith("raw:")],
            phenotype=squash(x.phenotype), paragraphs=paras,
        ))

    entry.inheritance = _codes([c for rel in entry.relationships for c in rel.inheritance])
    if not entry.inheritance:
        # No causal gene established: fall back to the mode most papers assert.
        entry.inheritance = list(kg.inheritance_support())[:1]
    entry.clinical_synopsis = _synopsis_from_graph(kg)
    entry.assign_paragraph_ids()
    entry.references = _references(entry, kg.papers)
    entry.meta = {
        "strategy": "kg", "generated": date.today().isoformat(),
        "model": llm.settings.model_for("synthesize"),
        "dropped_ungrounded": dropped, "unknown_citations": sorted(set(unknown_citations)),
        "removed_cross_references": removed_mims, "kg": kg.stats(),
    }
    return entry


# --------------------------------------------------------------------------- #
# Strategy 2: direct baseline
# --------------------------------------------------------------------------- #

DIRECT_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header and the text of the papers to base it on. Write the entry from these papers.

The supplied paper texts are the only admissible evidence. After you write, every sentence will be \
audited against the paper it cites. So write only what the papers say: no facts, numbers, variants, \
citations or interpretations from your own memory of the disorder, the gene, or the existing OMIM \
entry, however confident you are. Where only an abstract is supplied, rely only on the abstract.

For each paragraph, list in `pmids` the PMIDs of the papers it draws on. Papers that turn out not to \
concern this entry's subject can be left uncited.

{STYLE}

{INTRO_RULE}

`relationships`: one item per gene that the papers show to cause this phenotype, with the mode(s) of \
inheritance they establish and the supporting PMIDs. Leave empty if none, or for a gene entry.

`allelic_variants`: one item per variant reported as disease-causing in patients, in chronological \
order of first report, with `hgvs` listing its nucleotide and protein names as the papers give them.

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name and the PMIDs reporting it.\
"""

DIRECT_TOTAL_CHARS = 600_000


def synthesize_direct(seed: Seed, papers: list[Paper], llm: LLM) -> GeneratedEntry:
    per_paper = max(20_000, DIRECT_TOTAL_CHARS // max(1, len(papers)))
    truncated = []
    blocks = []
    for p in sorted(papers, key=lambda p: (p.year or 9999, p.pmid)):
        text = p.source_text()
        if len(text) > per_paper:
            truncated.append(p.pmid)
            text = text[:per_paper]
        blocks.append(f'<paper pmid="{p.pmid}" label="{p.label}" available="{p.content_level}">\n'
                      f"{p.reference}\n\n{text}\n</paper>")
    gene_ref, gene_facts = _gene_reference(seed.gene_symbols)
    prompt = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none supplied'}\n\n"
        + "\n\n".join(blocks)
    )
    raw = llm.call("synthesize", DIRECT_SYSTEM, prompt, DEntry)
    return draft_to_entry(seed, papers, raw, llm, strategy="direct", gene_facts=gene_facts,
                          meta={"truncated_papers": truncated})


def draft_to_entry(
    seed: Seed,
    papers: list[Paper],
    raw,
    llm: LLM,
    *,
    strategy: str,
    gene_facts: dict[str, dict[str, str]] | None = None,
    keep_uncited: bool = False,
    check_quotes: bool = False,
    meta: dict | None = None,
) -> GeneratedEntry:
    """Turn a model-written draft into a `GeneratedEntry`, applying the same guards for every strategy.

    `raw` has the shape of `DEntry`: an intro, sections of paragraphs, gene
    relationships, allelic variants and clinical-synopsis phrases, each naming the
    PMIDs it rests on. Any strategy that has a model write prose directly ends
    here, so they all get identical treatment:

    * PMIDs that are not among the supplied papers are discarded; author-year
      citations in the text are mapped to supplied papers, and ones that match none
      are recorded;
    * a paragraph left with no supplied paper behind it is dropped, unless
      `keep_uncited` (used for the memory-only control, whose point is to see what
      the model writes without sources);
    * with `check_quotes`, a paragraph that offers verbatim `quotes` must have at
      least one of them found in a paper it cites, or it is dropped;
    * OMIM cross-reference numbers the evidence cannot have supplied are stripped;
    * gene symbols are normalised, and synopsis phrases are mapped to HPO terms by
      ontology search, never by recall.
    """
    from .grounding import SourceIndex
    from .sources.hpo import get_hpo

    gene_facts = dict(gene_facts or {})
    by_pmid = {p.pmid: p for p in papers}
    label_to_pmid = _labels(papers)
    dropped: list[str] = []
    unknown_citations: list[str] = []
    removed_mims: list[str] = []
    quote_stats = {"paragraphs_with_quotes": 0, "quotes": 0, "quotes_found": 0, "paragraphs_dropped": 0}
    indexes: dict[str, SourceIndex] = {}
    # The writer may name a causal gene the seed did not; its MIM number is looked up
    # here so that it counts as supplied reference data, not as recall.
    for rel in raw.relationships:
        _resolve_gene(rel.gene_symbol, gene_facts)
    allowed_mims = {f["mim"] for f in gene_facts.values() if f.get("mim")} | ({seed.mim} if seed.mim else set())

    def quotes_hold(x, pmids: list[str]) -> bool:
        quotes = [squash(q) for q in (getattr(x, "quotes", None) or []) if squash(q)]
        if not check_quotes or not quotes:
            return True
        quote_stats["paragraphs_with_quotes"] += 1
        quote_stats["quotes"] += len(quotes)
        found = 0
        for quote in quotes:
            for pmid in pmids:
                if pmid not in indexes:
                    indexes[pmid] = SourceIndex(by_pmid[pmid].source_text())
                if indexes[pmid].contains(quote):
                    found += 1
                    break
        quote_stats["quotes_found"] += found
        return found > 0

    def paragraph(x, where: str) -> EntryParagraph | None:
        text = _strip_mim_numbers(squash(x.text), allowed_mims, removed_mims)
        if not text:
            return None
        pmids = [p for p in dict.fromkeys(str(i).strip() for i in (x.pmids or [])) if p in by_pmid]
        para = EntryParagraph(text=text, pmids=pmids)
        _attach_text_citations(para, label_to_pmid, unknown_citations)
        if not para.pmids and not keep_uncited:
            dropped.append(f"{where}: {text[:120]}")
            return None
        if not quotes_hold(x, para.pmids):
            quote_stats["paragraphs_dropped"] += 1
            dropped.append(f"{where} (quotes not found in the cited paper): {text[:120]}")
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
        pmids = [p for p in dict.fromkeys(str(i).strip() for i in (rel.pmids or [])) if p in by_pmid]
        if not pmids and not keep_uncited:
            dropped.append(f"relationship: {rel.gene_symbol}")
            continue
        symbol, facts = _resolve_gene(rel.gene_symbol, gene_facts)
        if any(r.gene_symbol == symbol for r in entry.relationships):
            continue
        entry.relationships.append(GenePhenotypeRelationship(
            phenotype=seed.title, phenotype_mim=seed.mim or "", gene_symbol=symbol,
            gene_mim=facts.get("mim", ""), location=facts.get("location", ""),
            inheritance=_codes(rel.inheritance), mapping_key=3, pmids=pmids,
        ))

    for x in raw.allelic_variants:
        paras = [p for xp in x.paragraphs if (p := paragraph(xp, f"allelic variant {x.name}"))]
        if paras:
            entry.allelic_variants.append(AllelicVariantEntry(
                number=len(entry.allelic_variants) + 1, gene_symbol=_resolve_gene(x.gene_symbol, gene_facts)[0],
                name=squash(x.name), hgvs=list(x.hgvs), phenotype=squash(x.phenotype), paragraphs=paras,
            ))

    hpo = get_hpo()
    resolved, hpo_stats = resolve_hpo_terms([(i.feature, i.hpo_label) for i in raw.clinical_synopsis], llm)
    seen: set[str] = set()
    for item in raw.clinical_synopsis:
        hpo_id = resolved.get((item.feature.lower(), item.hpo_label.lower()), "")
        if not hpo_id or hpo_id in seen:
            continue
        seen.add(hpo_id)
        pmids = [p for p in dict.fromkeys(str(i).strip() for i in (item.pmids or [])) if p in by_pmid]
        entry.clinical_synopsis.append(SynopsisItem(
            category=hpo.category(hpo_id), feature=squash(item.feature), hpo_id=hpo_id,
            hpo_label=hpo.label(hpo_id), pmids=pmids, n_papers=len(pmids),
        ))
    entry.clinical_synopsis.sort(key=lambda i: (i.category, -i.n_papers, i.hpo_label))

    entry.inheritance = _codes([c for rel in entry.relationships for c in rel.inheritance])
    entry.assign_paragraph_ids()
    entry.references = _references(entry, by_pmid)
    entry.meta = {
        "strategy": strategy, "generated": date.today().isoformat(),
        "model": llm.settings.model_for("synthesize"),
        "dropped_ungrounded": dropped, "unknown_citations": sorted(set(unknown_citations)),
        "removed_cross_references": removed_mims, "hpo_resolution": hpo_stats,
        **({"quote_check": quote_stats} if check_quotes else {}),
        **(meta or {}),
    }
    return entry
