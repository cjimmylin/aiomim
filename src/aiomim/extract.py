"""Stage 3: read each paper once and pull out citable, quote-backed findings.

One model call per paper. The reply is a list of findings, each a statement in
OMIM's house style plus the verbatim quotes that justify it. Quotes are then
checked against the paper text without a model (see grounding.py); findings whose
quotes cannot be found are set aside and never reach the knowledge graph.

Phenotype mentions are mapped to HPO terms in a second, cheaper step: exact label
or synonym match first, then a model choice among lexical candidates.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from .grounding import SourceIndex
from .llm import LLM
from .models import (
    Finding,
    InheritanceCode,
    Paper,
    PaperExtraction,
    PhenotypeMention,
    Relevance,
    SectionName,
    Seed,
    VariantMention,
    squash,
)

log = logging.getLogger(__name__)

# Long enough for any research article; a handful of very long reviews get cut,
# and when that happens it is recorded on the extraction rather than hidden.
MAX_SOURCE_CHARS = 180_000

# --------------------------------------------------------------------------- #
# What the model returns
# --------------------------------------------------------------------------- #

Zygosity = Literal[
    "heterozygous", "homozygous", "compound_heterozygous", "hemizygous",
    "heteroplasmic", "homoplasmic", "mosaic", "unknown",
]


class XVariant(BaseModel):
    gene: str = Field(description="Gene symbol as the paper gives it")
    as_reported: str = Field(description="The variant exactly as the paper names it")
    cdna: str = Field(description='Coding DNA change if stated, e.g. "c.3697G>A"; else ""')
    protein: str = Field(description='Protein change if stated, e.g. "p.Gly131Ser"; else ""')
    genomic: str = Field(description='Genomic or mitochondrial change if stated, e.g. "m.14459G>A"; else ""')
    zygosity: Zygosity
    origin: Literal["de_novo", "inherited", "unknown"]
    consequence: str = Field(description='e.g. "missense", "nonsense", "frameshift", "splice site"; else ""')


class XPhenotype(BaseModel):
    text: str = Field(description="The clinical feature as a short noun phrase")
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    present: bool = Field(description="False if the paper says the feature was absent")
    frequency: str = Field(description='Affected/assessed if stated, e.g. "3/5"; else ""')
    onset: str = Field(description='Age or period of onset if stated; else ""')


class XFinding(BaseModel):
    section: SectionName
    statement: str
    quotes: list[str]
    genes: list[str]
    variants: list[XVariant]
    phenotypes: list[XPhenotype]
    inheritance: InheritanceCode
    n_affected: int | None
    n_families: int | None
    population: str


class XExtraction(BaseModel):
    relevance: Relevance
    relevance_reason: str
    study_types: list[str]
    findings: list[XFinding]


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

EXTRACT_SYSTEM = """\
You are a biocurator preparing material for an entry in OMIM (Online Mendelian Inheritance in Man). \
You will be given the header of the entry being written and the text of one published paper. Your job \
is to pull out of this paper every finding a curator would want in that entry, each one backed by \
verbatim quotes from the paper.

The paper text you are given is the only source. A separate program will search the text for every \
quote you return and throw away any finding whose quotes are not found there, and a second reviewer \
will audit each statement against the paper. So work only from what is on the page: do not add \
anything you remember about this paper, this disorder, this gene, or the existing OMIM entry, even if \
you are sure it is true. If only the abstract is supplied, extract only what the abstract says.

What a finding is
A finding is one citable unit: what one paper established about one family, patient group, variant, \
experiment or analysis. Write its `statement` the way OMIM writes: past tense, attributed to the \
authors using exactly the citation label you are given ("Novotny et al. (1986) described ..."), \
self-contained, and specific: numbers of patients and families, sex, ages, ancestry or country, \
consanguinity, the key clinical, imaging, laboratory and pathology results, and for genetic results \
the gene, the variant as the paper names it together with the nucleotide and protein change, zygosity, \
how it was found, segregation or de novo status, population-database frequency, and what functional \
studies showed. One to four sentences. Report what the authors observed and concluded, not your own \
interpretation, and keep their hedges ("suggested", "postulated").

Split by section and by subject. A clinical description of a family and the variant found in that \
family are two findings (clinical_features and molecular_genetics). Two unrelated families described \
separately are two findings. Each distinct variant gets its own molecular_genetics finding so it can \
become an allelic-variant record. Be complete: a clinical paper's phenotype detail and a genetics \
paper's variant detail are exactly what the entry is built from.

Sections
description: a general statement defining the disorder (or, for a gene entry, the gene product).
nomenclature: naming of the disorder or gene.
clinical_features: patients and families, signs, symptoms, course, imaging, pathology.
other_features: notable associated findings outside the core phenotype.
biochemical_features: enzyme, metabolite and other laboratory or biochemical studies in patients.
inheritance: pedigree pattern and transmission.
cytogenetics: chromosomal rearrangements, deletions, duplications.
mapping: linkage and positional mapping to a chromosomal region.
heterogeneity: evidence for genetic or clinical heterogeneity.
molecular_genetics: variants identified in patients and the evidence that they are causal.
genotype_phenotype_correlations: how genotype relates to phenotype or severity.
pathogenesis: disease mechanism.
diagnosis: diagnostic criteria, testing, prenatal diagnosis.
clinical_management: treatment and outcome of treatment.
population_genetics: prevalence, carrier frequency, founder effects.
animal_model: animal or cellular disease models.
gene_function, cloning_expression, gene_structure, evolution: properties of the gene and its product.
history: historical notes.

Quotes
Give one to three `quotes` per finding, copied character for character from the supplied text, that \
together justify the statement. Prefer the sentence that carries the key numbers, the variant, or the \
conclusion. Keep each quote to a continuous span of at most about 50 words; do not stitch separate \
passages together and do not correct or reformat the text. Table rows may be quoted as they appear.

Structured fields
`genes`: gene symbols this finding is about. `variants`: one item per variant the finding reports, \
with the fields filled only from what the paper states (leave a field empty rather than deriving it). \
`phenotypes`: the individual clinical features the finding reports, each as a short noun phrase, with \
`hpo_label` set to the Human Phenotype Ontology term name you believe matches best; set `present` to \
false for features the paper explicitly says were absent, and give `frequency` as affected/assessed \
when the paper reports counts. `inheritance`: the mode the finding asserts or directly demonstrates, \
otherwise UNKNOWN. `n_affected` and `n_families`: counts for the patients this finding describes, or \
null. `population`: ancestry, ethnicity or country if stated.

Relevance of the paper to this entry
primary: reports patients, variants or experiments that directly establish or characterise this entry's subject.
supporting: adds evidence about it (further cases, functional work, models, mapping).
background: about a related subject; contributes context only.
not_relevant: nothing a curator would cite in this entry. Return no findings.
`study_types`: short tags such as "case report", "case series", "family study", "cohort", \
"functional study", "animal model", "linkage", "review".\
"""


def _header(seed: Seed) -> str:
    kind = "gene" if seed.entry_type == "gene" else "phenotype (disorder)"
    lines = [f"OMIM entry being written ({kind} entry)", f"Title: {seed.title}"]
    if seed.symbol:
        lines.append(f"Symbol: {seed.symbol}")
    if seed.alt_titles:
        lines.append("Alternative titles: " + "; ".join(seed.alt_titles))
    if seed.gene_symbols:
        lines.append("Gene(s): " + ", ".join(seed.gene_symbols))
    return "\n".join(lines)


def build_prompt(seed: Seed, paper: Paper) -> tuple[str, str, bool]:
    """Returns (prompt, source_text, truncated)."""
    source = paper.source_text()
    truncated = len(source) > MAX_SOURCE_CHARS
    if truncated:
        source = source[:MAX_SOURCE_CHARS]
    available = {
        "fulltext": "the full text",
        "abstract": "the abstract only (the full text was not openly available)",
        "title": "the title only (no abstract or full text was available)",
    }[paper.content_level]
    prompt = (
        f"{_header(seed)}\n\n"
        f"Paper: PMID {paper.pmid}. {paper.reference}\n"
        f"Citation label to use in statements: {paper.label}\n"
        f"Text available: {available}.\n\n"
        f"<paper>\n{source}\n</paper>"
    )
    return prompt, source, truncated


# --------------------------------------------------------------------------- #
# Running the stage
# --------------------------------------------------------------------------- #


def _to_extraction(paper: Paper, source: str, raw: XExtraction) -> PaperExtraction:
    index = SourceIndex(source)
    kept: list[Finding] = []
    dropped: list[Finding] = []
    for n, xf in enumerate(raw.findings, 1):
        quotes = [squash(q) for q in xf.quotes if squash(q)]
        finding = Finding(
            id=f"{paper.pmid}:{n}",
            pmid=paper.pmid,
            section=xf.section,
            statement=squash(xf.statement),
            quotes=quotes,
            quote_grounding=[round(index.score(q), 3) for q in quotes],
            genes=[g.strip() for g in xf.genes if g.strip()],
            variants=[VariantMention(**v.model_dump()) for v in xf.variants],
            phenotypes=[
                PhenotypeMention(
                    text=squash(p.text), hpo_label=squash(p.hpo_label), present=p.present,
                    frequency=p.frequency, onset=p.onset,
                )
                for p in xf.phenotypes if squash(p.text)
            ],
            inheritance=xf.inheritance,
            n_affected=xf.n_affected,
            n_families=xf.n_families,
            population=xf.population,
        )
        (kept if finding.grounded else dropped).append(finding)
    relevance = raw.relevance
    return PaperExtraction(
        pmid=paper.pmid,
        relevance=relevance,
        relevance_reason=squash(raw.relevance_reason),
        study_types=raw.study_types,
        content_level=paper.content_level,
        findings=[] if relevance == "not_relevant" else kept,
        dropped_findings=dropped,
    )


def extract_papers(seed: Seed, papers: list[Paper], llm: LLM, stage: str = "extract") -> list[PaperExtraction]:
    """Extract findings from every paper, concurrently. Order follows `papers`.

    `stage` picks the model and effort; the matched ablations run the same prompts
    as "extract_matched", at the writer's effort."""
    built = [build_prompt(seed, p) for p in papers]
    replies = llm.map(stage, EXTRACT_SYSTEM, [b[0] for b in built], XExtraction)
    out: list[PaperExtraction] = []
    for paper, (_, source, truncated), reply in zip(papers, built, replies):
        if isinstance(reply, Exception):
            log.warning("extract: PMID %s failed: %s", paper.pmid, reply)
            out.append(PaperExtraction(
                pmid=paper.pmid, relevance="not_relevant", content_level=paper.content_level,
                error=f"{type(reply).__name__}: {reply}"[:500],
            ))
            continue
        extraction = _to_extraction(paper, source, reply)
        if truncated:
            extraction.error = f"source text truncated to {MAX_SOURCE_CHARS} characters"
        if extraction.dropped_findings:
            log.info("extract: PMID %s: %d finding(s) dropped, quotes not found in source",
                     paper.pmid, len(extraction.dropped_findings))
        out.append(extraction)
    return out


# --------------------------------------------------------------------------- #
# HPO grounding of phenotype mentions
# --------------------------------------------------------------------------- #

NORMALIZE_SYSTEM = """\
You map clinical feature phrases taken from case reports to Human Phenotype Ontology (HPO) terms. For \
each numbered phrase you are given candidate HPO terms found by a text search. Choose the candidate \
whose meaning matches the phrase. If no candidate means the same thing, choose the closest candidate \
that is a correct but more general description of the phrase. If none of the candidates is a correct \
description, answer with an empty string; a wrong term is worse than no term. Answer only with \
candidate IDs from the list given for that phrase.\
"""


class XChoice(BaseModel):
    n: int = Field(description="The phrase number")
    hpo_id: str = Field(description='Chosen candidate ID such as "HP:0000648", or "" for none')


class XChoices(BaseModel):
    choices: list[XChoice]


def resolve_hpo_terms(
    phrases: list[tuple[str, str]], llm: LLM, batch: int = 40
) -> tuple[dict[tuple[str, str], str], dict[str, int]]:
    """Map (phrase, guessed HPO label) pairs to HPO ids.

    Exact label/synonym matches are taken as they are. The rest go to the model,
    which may only pick from candidates the ontology search returned, so an HPO id
    can never be invented. Returns the mapping and counts of how phrases resolved.
    """
    from .sources.hpo import get_hpo  # imported lazily: loading the ontology takes a moment

    hpo = get_hpo()
    resolved: dict[tuple[str, str], str] = {}
    pending: list[tuple[str, str]] = []
    stats = {"exact": 0, "chosen": 0, "unmapped": 0}

    for key in dict.fromkeys((text.lower(), guess.lower()) for text, guess in phrases):
        text, guess = key
        hit = (guess and hpo.exact(guess)) or hpo.exact(text)
        if hit and hpo.is_phenotype(hit):
            resolved[key] = hit
            stats["exact"] += 1
        else:
            pending.append(key)

    for start in range(0, len(pending), batch):
        chunk = pending[start:start + batch]
        blocks, candidates_by_n = [], {}
        for n, (text, guess) in enumerate(chunk, 1):
            hits = {h.id: h for h in hpo.search(text, 8)}
            if guess and guess != text:
                for h in hpo.search(guess, 6):
                    hits.setdefault(h.id, h)
            candidates_by_n[n] = set(hits)
            listing = "\n".join(f"   {h.id}  {h.label}" for h in hits.values()) or "   (no candidates)"
            blocks.append(f"{n}. {text}\n{listing}")
        if not any(candidates_by_n.values()):
            continue
        reply = llm.call("normalize", NORMALIZE_SYSTEM, "\n\n".join(blocks), XChoices)
        for choice in reply.choices:
            if 1 <= choice.n <= len(chunk) and choice.hpo_id in candidates_by_n.get(choice.n, ()):
                if chunk[choice.n - 1] not in resolved:
                    resolved[chunk[choice.n - 1]] = choice.hpo_id
                    stats["chosen"] += 1

    stats["unmapped"] = len(pending) - stats["chosen"]
    return resolved, stats


def ground_phenotypes(extractions: list[PaperExtraction], llm: LLM) -> dict[str, int]:
    """Fill `hpo_id`/`hpo_label` on every phenotype mention, in place."""
    from .sources.hpo import get_hpo

    hpo = get_hpo()
    mentions = [m for ex in extractions for f in ex.findings for m in f.phenotypes]
    resolved, stats = resolve_hpo_terms([(m.text, m.hpo_label) for m in mentions], llm)
    for m in mentions:
        hpo_id = resolved.get((m.text.lower(), m.hpo_label.lower()), "")
        m.hpo_id = hpo_id
        m.hpo_label = hpo.label(hpo_id) if hpo_id else ""
    return stats
