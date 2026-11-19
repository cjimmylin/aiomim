"""Data model shared by every stage of the pipeline.

The flow is:

    Seed ─▶ [Paper] ─▶ [PaperExtraction → Finding] ─▶ KnowledgeGraph ─▶ GeneratedEntry
                                                                              │
    GoldEntry (public OMIM-derived sources) ───────────────▶ evaluation ◀─────┘

`GoldEntry` is only ever read by the evaluator (and, in "oracle" retrieval mode,
for its list of cited PMIDs). Nothing gold reaches the extraction or writing
prompts.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# OMIM vocabulary
# --------------------------------------------------------------------------- #

# Text sections, in the order OMIM prints them. Phenotype entries and gene
# entries draw on different subsets; a section is printed only if it has content.
SECTION_HEADINGS: dict[str, str] = {
    "description": "Description",
    "nomenclature": "Nomenclature",
    "cloning_expression": "Cloning and Expression",
    "gene_structure": "Gene Structure",
    "clinical_features": "Clinical Features",
    "other_features": "Other Features",
    "biochemical_features": "Biochemical Features",
    "inheritance": "Inheritance",
    "cytogenetics": "Cytogenetics",
    "mapping": "Mapping",
    "heterogeneity": "Heterogeneity",
    "gene_function": "Gene Function",
    "molecular_genetics": "Molecular Genetics",
    "genotype_phenotype_correlations": "Genotype/Phenotype Correlations",
    "pathogenesis": "Pathogenesis",
    "diagnosis": "Diagnosis",
    "clinical_management": "Clinical Management",
    "population_genetics": "Population Genetics",
    "evolution": "Evolution",
    "animal_model": "Animal Model",
    "history": "History",
}
SECTION_ORDER: list[str] = list(SECTION_HEADINGS)

PHENOTYPE_SECTIONS = [
    "description", "nomenclature", "clinical_features", "other_features",
    "biochemical_features", "inheritance", "cytogenetics", "mapping", "heterogeneity",
    "molecular_genetics", "genotype_phenotype_correlations", "pathogenesis", "diagnosis",
    "clinical_management", "population_genetics", "animal_model", "history",
]
GENE_SECTIONS = [
    "description", "nomenclature", "cloning_expression", "gene_structure", "mapping",
    "gene_function", "biochemical_features", "molecular_genetics",
    "genotype_phenotype_correlations", "population_genetics", "evolution", "animal_model",
    "history",
]

SectionName = Literal[
    "description", "nomenclature", "cloning_expression", "gene_structure",
    "clinical_features", "other_features", "biochemical_features", "inheritance",
    "cytogenetics", "mapping", "heterogeneity", "gene_function", "molecular_genetics",
    "genotype_phenotype_correlations", "pathogenesis", "diagnosis", "clinical_management",
    "population_genetics", "evolution", "animal_model", "history",
]

# Inheritance codes used in prompts, with their HPO mode-of-inheritance terms.
INHERITANCE_HPO: dict[str, tuple[str, str]] = {
    "AD": ("HP:0000006", "Autosomal dominant"),
    "AR": ("HP:0000007", "Autosomal recessive"),
    "XL": ("HP:0001417", "X-linked"),
    "XLD": ("HP:0001423", "X-linked dominant"),
    "XLR": ("HP:0001419", "X-linked recessive"),
    "YL": ("HP:0001450", "Y-linked"),
    "MT": ("HP:0001427", "Mitochondrial"),
    "DIGENIC": ("HP:0010984", "Digenic"),
    "SEMIDOMINANT": ("HP:0032113", "Semidominant"),
    "MULTIFACTORIAL": ("HP:0001426", "Multifactorial"),
    "SOMATIC": ("HP:0001428", "Somatic mutation"),
    "SOMATIC_MOSAIC": ("HP:0001442", "Somatic mosaicism"),
}
InheritanceCode = Literal[
    "AD", "AR", "XL", "XLD", "XLR", "YL", "MT", "DIGENIC", "SEMIDOMINANT",
    "MULTIFACTORIAL", "SOMATIC", "SOMATIC_MOSAIC", "UNKNOWN",
]
HPO_TO_INHERITANCE: dict[str, str] = {hpo: code for code, (hpo, _) in INHERITANCE_HPO.items()}

# For scoring, X-linked subtypes collapse into one class: OMIM and HPO annotators
# differ on whether they record "XL" or "XLR" for the same disorder.
INHERITANCE_COARSE: dict[str, str] = {
    "AD": "AD", "AR": "AR", "XL": "XL", "XLD": "XL", "XLR": "XL", "YL": "YL", "MT": "MT",
    "DIGENIC": "DIGENIC", "SEMIDOMINANT": "AD", "MULTIFACTORIAL": "MULTIFACTORIAL",
    "SOMATIC": "SOMATIC", "SOMATIC_MOSAIC": "SOMATIC",
}

# --------------------------------------------------------------------------- #
# Literature
# --------------------------------------------------------------------------- #

ContentLevel = Literal["fulltext", "abstract", "title"]

_INITIALS = re.compile(r"^[A-Z]{1,4}$")
_NAME_SUFFIX = {"Jr", "Sr", "2nd", "3rd", "4th", "II", "III", "IV"}


def _surname(author: str) -> str:
    """'Novotny EJ' -> 'Novotny', 'Smith JR Jr' -> 'Smith'; a collective name is kept whole."""
    tokens = author.split()
    while len(tokens) > 1 and tokens[-1] in _NAME_SUFFIX:
        tokens.pop()
    if len(tokens) > 1 and _INITIALS.match(tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


class Paper(BaseModel):
    """One PubMed record plus whatever text we could legally obtain for it."""

    pmid: str
    pmcid: str | None = None
    doi: str | None = None
    title: str = ""
    abstract: str = ""
    authors: list[str] = Field(default_factory=list, description='PubMed style, e.g. "Novotny EJ"')
    year: int | None = None
    journal: str = ""
    volume: str = ""
    pages: str = ""
    pub_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    fulltext: str | None = Field(default=None, description="Plain-text body, section headings kept")
    fulltext_source: str | None = None

    @property
    def content_level(self) -> ContentLevel:
        if self.fulltext and len(self.fulltext) > 2000:
            return "fulltext"
        if self.abstract and len(self.abstract) > 100:
            return "abstract"
        return "title"

    @property
    def label(self) -> str:
        """OMIM in-text citation label, e.g. 'Novotny et al. (1986)'."""
        year = self.year if self.year else "n.d."
        last = [_surname(a) for a in self.authors]
        if not last:
            return f"PMID {self.pmid} ({year})"
        if len(last) == 1:
            return f"{last[0]} ({year})"
        if len(last) == 2:
            return f"{last[0]} and {last[1]} ({year})"
        return f"{last[0]} et al. ({year})"

    @property
    def reference(self) -> str:
        """Full reference line in OMIM's reference-list style."""
        authors = ", ".join(self.authors[:10]) + (", and others" if len(self.authors) > 10 else "")
        bits = [f"{authors}." if authors else "", self.title.rstrip(".") + "." if self.title else ""]
        src = self.journal
        if self.volume:
            src += f" {self.volume}"
        if self.pages:
            src += f": {self.pages}"
        if self.year:
            src += f", {self.year}"
        bits.append(src + "." if src else "")
        bits.append(f"[PubMed: {self.pmid}]")
        return " ".join(b for b in bits if b)

    def source_text(self, max_chars: int | None = None) -> str:
        """Title + abstract + full text: the text extraction and verification read."""
        parts = [f"TITLE: {self.title}"]
        if self.abstract:
            parts.append(f"ABSTRACT:\n{self.abstract}")
        if self.fulltext:
            parts.append(f"FULL TEXT:\n{self.fulltext}")
        text = "\n\n".join(parts)
        if max_chars is not None and len(text) > max_chars:
            text = text[:max_chars]
        return text


# --------------------------------------------------------------------------- #
# Pipeline input
# --------------------------------------------------------------------------- #

EntryType = Literal["phenotype", "gene"]


class Seed(BaseModel):
    """What the pipeline is told about the entry it should write.

    For replication this is the public header of an OMIM entry (number, title,
    symbol, and the gene it maps to). For a new entry it is whatever the curator
    supplies: a disease name, a gene, optionally a few key PMIDs.
    """

    mim: str | None = None
    entry_type: EntryType = "phenotype"
    prefix: str = ""
    title: str
    alt_titles: list[str] = Field(default_factory=list)
    symbol: str = ""
    gene_symbols: list[str] = Field(default_factory=list)
    seed_pmids: list[str] = Field(default_factory=list)
    max_year: int | None = Field(default=None, description="Ignore literature published after this year")


# --------------------------------------------------------------------------- #
# Gold standard (public, OMIM-derived)
# --------------------------------------------------------------------------- #


class GoldParagraph(BaseModel):
    """One OMIM-authored paragraph with the reference(s) it summarises."""

    text: str
    pmids: list[str] = Field(default_factory=list)
    mims: list[str] = Field(default_factory=list, description="Phenotype MIM numbers the paragraph is about")


class GoldAllelicVariant(BaseModel):
    """An OMIM allelic variant as OMIM submitted it to ClinVar."""

    omim_id: str = Field(description='e.g. "516000.0012"')
    gene_symbol: str = ""
    name: str = Field(default="", description='OMIM variant name, e.g. "MTND1, 3697G-A"')
    clinvar_variation_id: str = ""
    clinvar_name: str = Field(default="", description="ClinVar preferred (HGVS) name")
    scv: str = ""
    protein_change: str = ""
    phenotypes: list[str] = Field(default_factory=list)
    paragraphs: list[GoldParagraph] = Field(default_factory=list)


class GoldPhenotypeAnnotation(BaseModel):
    """One row of HPO's phenotype.hpoa for an OMIM disease."""

    hpo_id: str
    label: str = ""
    aspect: str = Field(default="P", description="P phenotype, I inheritance, C clinical course, M modifier, H history")
    qualifier: str = ""
    frequency: str = ""
    onset: str = ""
    evidence: str = ""
    reference: str = ""


class GoldGene(BaseModel):
    symbol: str
    entrez_id: str = ""
    mim: str = ""
    location: str = ""
    source: str = ""


class GoldEntry(BaseModel):
    mim: str
    prefix: str = ""
    entry_type: str = "phenotype"
    title: str = ""
    alt_titles: list[str] = Field(default_factory=list)
    symbol: str = ""
    cited_pmids: list[str] = Field(default_factory=list)
    genes: list[GoldGene] = Field(default_factory=list)
    inheritance: list[str] = Field(default_factory=list, description="Inheritance codes, see INHERITANCE_HPO")
    hpo_annotations: list[GoldPhenotypeAnnotation] = Field(default_factory=list)
    allelic_variants: list[GoldAllelicVariant] = Field(default_factory=list)
    medgen_cui: str = ""
    definition: str = ""
    definition_source: str = ""
    # Only populated when an OMIM API key is configured.
    omim_text: dict[str, str] | None = None
    omim_clinical_synopsis: dict[str, str] | None = None
    provenance: dict[str, str] = Field(default_factory=dict)

    @property
    def gold_paragraphs(self) -> list[GoldParagraph]:
        """OMIM-authored per-paper paragraphs that concern this entry."""
        out: list[GoldParagraph] = []
        for av in self.allelic_variants:
            for para in av.paragraphs:
                if self.entry_type == "gene" or not para.mims or self.mim in para.mims:
                    out.append(para)
        return out

    @property
    def scoped_paragraphs(self) -> list[GoldParagraph]:
        """The subset of `gold_paragraphs` that summarise a paper this entry itself cites.

        OMIM files allelic-variant text under the gene entry, whose reference list
        is larger than the phenotype entry's. A paragraph about a paper the
        phenotype entry does not cite is outside what that entry was written from,
        so it is not held against a replication of it.
        """
        cited = set(self.cited_pmids)
        return [p for p in self.gold_paragraphs if cited & set(p.pmids)]

    def scoped_variants(self) -> list[GoldAllelicVariant]:
        """Allelic variants with at least one in-scope paragraph about this entry."""
        scoped = {id(p) for p in self.scoped_paragraphs}
        return [av for av in self.allelic_variants if any(id(p) in scoped for p in av.paragraphs)]


# --------------------------------------------------------------------------- #
# Evidence extraction
# --------------------------------------------------------------------------- #


class VariantMention(BaseModel):
    gene: str = ""
    as_reported: str = Field(default="", description="The variant exactly as the paper names it")
    cdna: str = ""
    protein: str = ""
    genomic: str = ""
    zygosity: str = ""
    origin: str = ""
    consequence: str = ""
    key: str = Field(default="", description="Canonical key assigned by the knowledge graph")


class PhenotypeMention(BaseModel):
    text: str
    hpo_id: str = ""
    hpo_label: str = ""
    present: bool = True
    frequency: str = Field(default="", description='e.g. "3/5" if the paper gives counts')
    onset: str = ""


class Finding(BaseModel):
    """One citable statement from one paper, with the quotes that justify it."""

    id: str = Field(description='"<pmid>:<n>"')
    pmid: str
    section: str
    statement: str
    quotes: list[str] = Field(default_factory=list)
    quote_grounding: list[float] = Field(default_factory=list, description="Per-quote match score in [0, 1]")
    genes: list[str] = Field(default_factory=list)
    variants: list[VariantMention] = Field(default_factory=list)
    phenotypes: list[PhenotypeMention] = Field(default_factory=list)
    inheritance: str = "UNKNOWN"
    n_affected: int | None = None
    n_families: int | None = None
    population: str = ""

    @property
    def grounded(self) -> bool:
        """True when at least one supporting quote was found in the source text."""
        return any(score >= 0.85 for score in self.quote_grounding)


Relevance = Literal["primary", "supporting", "background", "not_relevant"]


class PaperExtraction(BaseModel):
    pmid: str
    relevance: Relevance = "supporting"
    relevance_reason: str = ""
    study_types: list[str] = Field(default_factory=list)
    content_level: ContentLevel = "abstract"
    findings: list[Finding] = Field(default_factory=list)
    dropped_findings: list[Finding] = Field(
        default_factory=list, description="Findings whose quotes could not be located in the source"
    )
    error: str = ""


# --------------------------------------------------------------------------- #
# Generated entry
# --------------------------------------------------------------------------- #

Verdict = Literal["supported", "partially_supported", "unsupported", "contradicted", "not_checkable"]


class ClaimCheck(BaseModel):
    """The verifier's judgement of one atomic claim against one source paper."""

    claim: str
    pmid: str = ""
    verdict: Verdict = "not_checkable"
    evidence_quote: str = ""
    explanation: str = ""


class EntryParagraph(BaseModel):
    id: str = ""
    text: str
    pmids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    checks: list[ClaimCheck] = Field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.checks:
            return "unverified"
        bad = [c for c in self.checks if c.verdict in ("unsupported", "contradicted")]
        if bad:
            return "flagged"
        if any(c.verdict == "partially_supported" for c in self.checks):
            return "partial"
        return "supported"


class EntrySection(BaseModel):
    name: str
    heading: str = ""
    paragraphs: list[EntryParagraph] = Field(default_factory=list)


class GenePhenotypeRelationship(BaseModel):
    phenotype: str = ""
    phenotype_mim: str = ""
    gene_symbol: str = ""
    gene_mim: str = ""
    location: str = ""
    inheritance: list[str] = Field(default_factory=list, description="Inheritance codes")
    mapping_key: int = Field(default=3, description="OMIM phenotype mapping key; 3 = molecular basis known")
    pmids: list[str] = Field(default_factory=list)


class SynopsisItem(BaseModel):
    category: str = Field(description='Clinical synopsis heading, e.g. "Neurologic"')
    feature: str
    hpo_id: str = ""
    hpo_label: str = ""
    pmids: list[str] = Field(default_factory=list)
    n_papers: int = 0


class AllelicVariantEntry(BaseModel):
    number: int = 0
    gene_symbol: str = ""
    name: str = Field(default="", description='OMIM-style variant name, e.g. "MTND6, ALA72VAL"')
    hgvs: list[str] = Field(default_factory=list)
    phenotype: str = ""
    paragraphs: list[EntryParagraph] = Field(default_factory=list)


class Reference(BaseModel):
    pmid: str
    label: str = ""
    citation: str = ""
    content_level: ContentLevel = "abstract"


class GeneratedEntry(BaseModel):
    mim: str | None = None
    prefix: str = ""
    entry_type: EntryType = "phenotype"
    title: str = ""
    alt_titles: list[str] = Field(default_factory=list)
    symbol: str = ""
    relationships: list[GenePhenotypeRelationship] = Field(default_factory=list)
    intro: EntryParagraph | None = None
    sections: list[EntrySection] = Field(default_factory=list)
    inheritance: list[str] = Field(default_factory=list)
    clinical_synopsis: list[SynopsisItem] = Field(default_factory=list)
    allelic_variants: list[AllelicVariantEntry] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

    def all_paragraphs(self) -> list[EntryParagraph]:
        paras: list[EntryParagraph] = []
        if self.intro:
            paras.append(self.intro)
        for section in self.sections:
            paras.extend(section.paragraphs)
        for av in self.allelic_variants:
            paras.extend(av.paragraphs)
        return paras

    def assign_paragraph_ids(self) -> None:
        if self.intro:
            self.intro.id = "intro"
        for section in self.sections:
            for i, para in enumerate(section.paragraphs, 1):
                para.id = f"{section.name}.{i}"
        for av in self.allelic_variants:
            for i, para in enumerate(av.paragraphs, 1):
                para.id = f"av{av.number:04d}.{i}"

    def cited_pmids(self) -> list[str]:
        seen: dict[str, None] = {}
        for para in self.all_paragraphs():
            for pmid in para.pmids:
                seen.setdefault(pmid)
        for rel in self.relationships:
            for pmid in rel.pmids:
                seen.setdefault(pmid)
        return list(seen)

    def plain_text(self) -> str:
        return "\n\n".join(p.text for p in self.all_paragraphs())


_WS = re.compile(r"\s+")


def squash(text: str) -> str:
    """Collapse whitespace; used wherever text is compared or embedded in a prompt."""
    return _WS.sub(" ", text or "").strip()
