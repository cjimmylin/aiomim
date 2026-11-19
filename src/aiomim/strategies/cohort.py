"""Case table first: patient-level records, pooled, then rendered.

The database-first route to an entry. Instead of free statements, each paper is
read once for the patients it reports, in the spirit of GA4GH Phenopackets: one
structured record per reported individual, family, or patient group described
together, plus "notes" for citable results that are not about particular
patients (functional work, animal models, mapping, management ...).

    papers ─(one call each)▶ records + notes ─(quotes checked)▶ case table
           ─(computed, no model)▶ clinical synopsis, causal genes, inheritance
           ─(one call)▶ prose, each paragraph naming the records/notes it rests on

The research question: does going through patient-level records give a better
clinical synopsis, inheritance call and variant list than extracting free
statements, and what does it cost?

Counting rules (see `_tally_feature` and `pool`):

* Only records from papers judged primary or supporting are pooled; records from
  background papers are shown to the writer but never counted.
* Each affected individual belongs to exactly one record of a paper (the prompt
  asks for that). A record's size is its `n_affected`, or 1 when not given.
* A feature reported for a record with no counts applies to the whole record
  (n present, n assessed). A count ("2 of 5") is taken as stated: 2 present,
  3 absent, 5 assessed; a count without a denominator gives present = assessed =
  that count. A feature that only "some" members had, without a number, counts
  as 1 present (a lower bound) and the record's size as assessed. A feature the
  paper says was absent counts the same way on the absent side.
* The same term reported twice in one record is counted once (the larger tally).
* Records are never merged across papers by guesswork. A record the paper itself
  says was reported before, in a supplied earlier paper, is a follow-up: it is
  left out of the individual and family totals and out of per-term counts,
  except that a term no first report recorded takes its count from the
  follow-ups (at most once). Records in different papers that share a label are
  kept separate and listed as possible duplicates.

Inheritance rule (see `record_mode` and `choose_modes`): each pooled record
gives at most one mode from the genotypes it carries: an mtDNA variant → MT;
homozygous, compound heterozygous, or two different heterozygous variants in one
gene → AR; hemizygous, or any variant in a gene on chromosome X → XL (XLR/XLD if
the paper says which); a heterozygous de novo variant → AD; another single
heterozygous variant → the mode the paper states for that family, if any; no
usable genotype → the stated mode. Modes are weighted by individuals. The mode
with the most individuals is called; another mode is added only if it rests on
at least two records or three individuals and on at least a quarter as many
individuals as the leader. With no record evidence at all, the mode most papers
state is used.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..extract import XVariant, build_prompt, resolve_hpo_terms
from ..grounding import GROUNDED, SourceIndex
from ..kg import CORE_RELEVANCE, _UnionFind, is_mito_gene, omim_variant_name, variant_keys
from ..models import (
    INHERITANCE_HPO,
    SECTION_ORDER,
    AllelicVariantEntry,
    EntryParagraph,
    EntrySection,
    GeneratedEntry,
    GenePhenotypeRelationship,
    InheritanceCode,
    Paper,
    Relevance,
    SectionName,
    Seed,
    SynopsisItem,
    VariantMention,
    squash,
)
from ..synthesize import (
    INTRO_RULE,
    STYLE,
    _attach_text_citations,
    _gene_reference,
    _header,
    _labels,
    _order_sections,
    _references,
    _strip_mim_numbers,
)

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# What the extraction model returns
# --------------------------------------------------------------------------- #


class XCasePhenotype(BaseModel):
    text: str = Field(description="The clinical feature as a short noun phrase")
    hpo_label: str = Field(description="Best-matching Human Phenotype Ontology term name")
    present: bool = Field(description="False if the paper says the feature was absent in this record")
    n_with: int | None = Field(description="How many individuals of this record had the feature (or, if present is "
                                           "false, lacked it), when the paper gives a number; else null")
    n_assessed: int | None = Field(description="How many individuals of this record were assessed for it, when the "
                                               "paper gives a number; else null")
    some_only: bool = Field(description='True when the paper says only some members had it ("some", "several", '
                                        '"most") without giving a number')


class XRecord(BaseModel):
    label: str = Field(description='The paper\'s own label, e.g. "Patient 3", "Family 2", "II-4"; else a short description')
    kind: Literal["individual", "family", "group"]
    family: str = Field(description="For an individual: the paper's label for the family it belongs to, if any; else \"\"")
    n_affected: int | None = Field(description="Affected individuals this record covers")
    n_families: int | None = Field(description="Families this record covers")
    sex: str = Field(description='e.g. "female", "2 males, 1 female"; else ""')
    ancestry: str = Field(description='Ancestry, ethnicity or country; else ""')
    consanguinity: Literal["yes", "no", "not_stated"]
    onset: str = Field(description='Age at onset as stated; else ""')
    age_last: str = Field(description='Age at last report, or at death (say "died at ..."), as stated; else ""')
    phenotypes: list[XCasePhenotype]
    variants: list[XVariant]
    segregation: str = Field(description='How the variant segregated in the family, as stated; else ""')
    inheritance: InheritanceCode = Field(description="Mode the family shows or the authors state for it; else UNKNOWN")
    previously_reported: str = Field(description='If the paper says these patients were reported before, the citation '
                                                 'it gives (e.g. "Smith et al. 1998"); else ""')
    quotes: list[str]


class XNote(BaseModel):
    section: SectionName
    statement: str
    inheritance: InheritanceCode = Field(description="Mode of inheritance this note states, else UNKNOWN")
    quotes: list[str]


class XCases(BaseModel):
    relevance: Relevance
    relevance_reason: str
    records: list[XRecord]
    notes: list[XNote]


CASES_SYSTEM = """\
You are a biocurator building a case-level database for an entry in OMIM (Online Mendelian Inheritance \
in Man). You will be given the header of the entry being written and the text of one published paper. \
Record every patient the paper reports as structured case records, in the spirit of GA4GH Phenopackets, \
and every other citable result as a note, each backed by verbatim quotes from the paper.

The paper text you are given is the only source. A separate program will search the text for every \
quote you return and throw away any record or note whose quotes are not found there, and the counts \
you give will be added up across papers. So work only from what is on the page: do not add anything you \
remember about this paper, this disorder, this gene, or the existing OMIM entry, even if you are sure \
it is true. If only the abstract is supplied, record only what the abstract says.

Records
A record is one affected individual, one family, or one group of patients the paper describes \
together. Use the finest level the paper gives detail for: when it describes patients one by one \
(case reports, a per-patient table), make one `individual` record each and give the family label in \
`family`; when it describes a family as a unit, one `family` record; when it only reports patients in \
aggregate ("three affected sibs had X", "of 12 patients, 9 had Y"), one `group` record with those \
numbers. Never invent per-person detail the paper does not give. Every affected individual belongs to \
exactly one record: do not also add a summary record for patients already recorded individually, and \
do not record unaffected carriers or healthy relatives as records. Patients the paper only cites from \
earlier literature without new data are not records.

`n_affected` and `n_families`: how many affected individuals and families the record covers (1 and 1 \
for an individual), or null if not stated. Fill `sex`, `ancestry`, `consanguinity`, `onset`, `age_last` \
only from what is stated. `previously_reported`: if the paper says these patients were described \
before, the citation it gives.

`phenotypes`: each clinical, imaging, laboratory or pathology feature reported for the record, as a \
short noun phrase, with `hpo_label` set to the Human Phenotype Ontology term name you believe matches \
best. Set `present` to false only for features the paper explicitly says were absent or normal. Counts \
are added up across papers, so be exact: for a group, if the paper gives a number ("2 of 5 had \
seizures"), set `n_with` 2 and `n_assessed` 5; if it says the whole group had it, leave both null; if \
it says only "some", "several" or "most" had it without a number, set `some_only` true and leave the \
numbers null. Never count a feature as present in the whole group when the paper says only some had it.

`variants`: the variants found in the record's affected members, one item each, with the fields filled \
only from what the paper states (leave a field empty rather than deriving it); zygosity as found in the \
patient; `origin` de_novo only if the paper says so. `segregation`: how the variant segregated in the \
family, in a few words, as stated. `inheritance`: the mode the family's pedigree shows or the authors \
state for it, otherwise UNKNOWN.

Notes
A note is any citable result that is not about particular patients: functional studies, animal or \
cellular models, linkage and mapping, gene structure and function, population data, diagnosis, \
management, nomenclature, or the authors' general description of the disorder. Give its OMIM `section` \
and a `statement` written the way OMIM writes: past tense, attributed to the authors using exactly the \
citation label you are given ("Novotny et al. (1986) found ..."), self-contained and specific, one to \
three sentences, keeping the authors' hedges. Do not write notes that only repeat what the records say.

Sections for notes: description, nomenclature, clinical_features, other_features, biochemical_features, \
inheritance, cytogenetics, mapping, heterogeneity, molecular_genetics, genotype_phenotype_correlations, \
pathogenesis, diagnosis, clinical_management, population_genetics, animal_model, gene_function, \
cloning_expression, gene_structure, evolution, history.

Quotes
Give one to three `quotes` per record and per note, copied character for character from the supplied \
text, that together justify it. Prefer the sentences that carry the numbers, the features, the variant \
and the segregation. Keep each quote to a continuous span of at most about 50 words; do not stitch \
separate passages together and do not correct or reformat the text. Table rows may be quoted as they appear.

Relevance of the paper to this entry
primary: reports patients, variants or experiments that directly establish or characterise this entry's subject.
supporting: adds evidence about it (further cases, functional work, models, mapping).
background: about a related subject; contributes context only.
not_relevant: nothing a curator would cite in this entry. Return no records and no notes.\
"""

# --------------------------------------------------------------------------- #
# Kept records and notes
# --------------------------------------------------------------------------- #


class CasePhenotype(BaseModel):
    text: str
    hpo_label: str = ""
    hpo_id: str = ""
    present: bool = True
    n_with: int | None = None
    n_assessed: int | None = None
    some_only: bool = False


class CaseRecord(BaseModel):
    id: str
    pmid: str
    label: str = ""
    kind: str = "individual"
    family: str = ""
    n_affected: int | None = None
    n_families: int | None = None
    sex: str = ""
    ancestry: str = ""
    consanguinity: str = "not_stated"
    onset: str = ""
    age_last: str = ""
    phenotypes: list[CasePhenotype] = Field(default_factory=list)
    variants: list[VariantMention] = Field(default_factory=list)
    segregation: str = ""
    inheritance: str = "UNKNOWN"
    previously_reported: str = ""
    quotes: list[str] = Field(default_factory=list)
    quote_grounding: list[float] = Field(default_factory=list)
    # Filled while pooling.
    followup_of: str = Field(default="", description="PMID of the supplied earlier paper this record re-reports")
    genotype_mode: str = ""
    genotype_reason: str = ""

    @property
    def grounded(self) -> bool:
        return any(s >= GROUNDED for s in self.quote_grounding)

    @property
    def size(self) -> int:
        return max(1, self.n_affected or 1) if self.kind != "individual" else 1


class CaseNote(BaseModel):
    id: str
    pmid: str
    section: str
    statement: str
    inheritance: str = "UNKNOWN"
    quotes: list[str] = Field(default_factory=list)
    quote_grounding: list[float] = Field(default_factory=list)

    @property
    def grounded(self) -> bool:
        return any(s >= GROUNDED for s in self.quote_grounding)


class PaperCases(BaseModel):
    pmid: str
    relevance: str = "supporting"
    relevance_reason: str = ""
    content_level: str = "abstract"
    records: list[CaseRecord] = Field(default_factory=list)
    notes: list[CaseNote] = Field(default_factory=list)
    dropped_records: list[CaseRecord] = Field(default_factory=list)
    dropped_notes: list[CaseNote] = Field(default_factory=list)
    error: str = ""


def _to_cases(paper: Paper, source: str, raw: XCases) -> PaperCases:
    index = SourceIndex(source)
    out = PaperCases(pmid=paper.pmid, relevance=raw.relevance, relevance_reason=squash(raw.relevance_reason),
                     content_level=paper.content_level)

    def quotes(qs: list[str]) -> tuple[list[str], list[float]]:
        kept = [squash(q) for q in qs if squash(q)]
        return kept, [round(index.score(q), 3) for q in kept]

    for n, x in enumerate(raw.records, 1):
        qs, scores = quotes(x.quotes)
        rec = CaseRecord(
            id=f"R:{paper.pmid}:{n}", pmid=paper.pmid, label=squash(x.label), kind=x.kind, family=squash(x.family),
            n_affected=x.n_affected if (x.n_affected or 0) > 0 else None,
            n_families=x.n_families if (x.n_families or 0) > 0 else None,
            sex=squash(x.sex), ancestry=squash(x.ancestry), consanguinity=x.consanguinity,
            onset=squash(x.onset), age_last=squash(x.age_last),
            phenotypes=[CasePhenotype(text=squash(p.text), hpo_label=squash(p.hpo_label), present=p.present,
                                      n_with=p.n_with if p.n_with is not None and p.n_with >= 0 else None,
                                      n_assessed=p.n_assessed if (p.n_assessed or 0) > 0 else None,
                                      some_only=p.some_only)
                        for p in x.phenotypes if squash(p.text)],
            variants=[VariantMention(**v.model_dump()) for v in x.variants],
            segregation=squash(x.segregation), inheritance=x.inheritance,
            previously_reported=squash(x.previously_reported), quotes=qs, quote_grounding=scores,
        )
        (out.records if rec.grounded else out.dropped_records).append(rec)
    for n, x in enumerate(raw.notes, 1):
        qs, scores = quotes(x.quotes)
        note = CaseNote(id=f"N:{paper.pmid}:{n}", pmid=paper.pmid, section=x.section, statement=squash(x.statement),
                        inheritance=x.inheritance, quotes=qs, quote_grounding=scores)
        if note.statement:
            (out.notes if note.grounded else out.dropped_notes).append(note)
    if raw.relevance == "not_relevant":
        out.records, out.notes = [], []
    return out


def extract_cases(seed: Seed, papers: list[Paper], llm) -> list[PaperCases]:
    built = [build_prompt(seed, p) for p in papers]
    replies = llm.map("cases", CASES_SYSTEM, [b[0] for b in built], XCases)
    out: list[PaperCases] = []
    for paper, (_, source, truncated), reply in zip(papers, built, replies):
        if isinstance(reply, Exception):
            log.warning("cases: PMID %s failed: %s", paper.pmid, reply)
            out.append(PaperCases(pmid=paper.pmid, relevance="not_relevant", content_level=paper.content_level,
                                  error=f"{type(reply).__name__}: {reply}"[:500]))
            continue
        cases = _to_cases(paper, source, reply)
        if truncated:
            cases.error = "source text truncated"
        if cases.dropped_records or cases.dropped_notes:
            log.info("cases: PMID %s: %d record(s), %d note(s) dropped, quotes not found", paper.pmid,
                     len(cases.dropped_records), len(cases.dropped_notes))
        out.append(cases)
    return out


def ground_case_phenotypes(cases: list[PaperCases], llm) -> dict[str, int]:
    """Map every kept record's phenotype phrases to HPO ids by ontology search, in place."""
    from ..sources.hpo import get_hpo

    hpo = get_hpo()
    mentions = [p for c in cases for r in c.records for p in r.phenotypes]
    resolved, stats = resolve_hpo_terms([(m.text, m.hpo_label) for m in mentions], llm)
    for m in mentions:
        m.hpo_id = resolved.get((m.text.lower(), m.hpo_label.lower()), "")
        m.hpo_label = hpo.label(m.hpo_id) if m.hpo_id else ""
    return stats


# --------------------------------------------------------------------------- #
# Pooling
# --------------------------------------------------------------------------- #


def _tally_feature(p: CasePhenotype, size: int) -> tuple[int, int, int]:
    """(present, absent, assessed) individuals one record contributes for one feature."""
    n = max(size, p.n_with or 0)
    if p.n_with is not None:
        assessed = max(p.n_assessed or p.n_with, p.n_with)
        hit, miss = p.n_with, assessed - p.n_with
    elif p.some_only:
        assessed = max(n, p.n_assessed or 0)
        hit, miss = min(1, assessed), 0
    else:
        assessed = p.n_assessed or n
        hit, miss = assessed, 0
    return (hit, miss, assessed) if p.present else (miss, hit, assessed)


_X_LIKE = ("XL", "XLR", "XLD")


def _is_mtdna(v: VariantMention) -> bool:
    return (is_mito_gene(v.gene) or v.zygosity in ("heteroplasmic", "homoplasmic")
            or (v.genomic or "").strip().lower().startswith("m."))


def record_mode(rec: CaseRecord, x_genes: set[str] = frozenset()) -> tuple[str, str]:
    """The mode of inheritance one record's genotypes show, with the reason ("" if none)."""
    stated = rec.inheritance if rec.inheritance in INHERITANCE_HPO else ""
    vs = [v for v in rec.variants if v.gene or v.as_reported]
    if any(_is_mtdna(v) for v in vs):
        return "MT", "mtDNA variant"
    if any(v.zygosity in ("homozygous", "compound_heterozygous") for v in vs):
        return "AR", "biallelic variants"
    het_by_gene: dict[str, set[str]] = defaultdict(set)
    for v in vs:
        if v.zygosity == "heterozygous" and v.gene:
            het_by_gene[v.gene].add(v.key or v.as_reported)
    if any(len(keys) >= 2 for keys in het_by_gene.values()):
        return "AR", "two different heterozygous variants in one gene"
    if any(v.zygosity == "hemizygous" or v.gene in x_genes for v in vs):
        return (stated if stated in _X_LIKE else "XL"), "variant in an X-chromosome gene"
    het = [v for v in vs if v.zygosity == "heterozygous"]
    if any(v.origin == "de_novo" for v in het):
        return "AD", "heterozygous de novo variant"
    if het and stated:
        return stated, "single heterozygous variant; mode as stated for the family"
    if stated:
        return stated, "stated for the family"
    return "", "no genotype or stated mode"


def choose_modes(support: dict[str, dict[str, Any]]) -> list[str]:
    """Apply the selection rule to {mode: {individuals, records, ...}}."""
    if not support:
        return []
    ranked = sorted(support, key=lambda m: (-support[m]["individuals"], -len(support[m]["records"]), m))
    lead = support[ranked[0]]["individuals"]
    chosen = [ranked[0]]
    for mode in ranked[1:]:
        s = support[mode]
        if (len(s["records"]) >= 2 or s["individuals"] >= 3) and s["individuals"] >= 0.25 * lead:
            chosen.append(mode)
    # "XL" next to a specific X-linked subtype adds nothing.
    if "XL" in chosen and any(m in chosen for m in ("XLR", "XLD")):
        chosen.remove("XL")
    return chosen


def _mode_support(records: list[CaseRecord]) -> dict[str, dict[str, Any]]:
    support: dict[str, dict[str, Any]] = {}
    for rec in records:
        if not rec.genotype_mode:
            continue
        s = support.setdefault(rec.genotype_mode, {"individuals": 0, "records": [], "pmids": [], "reasons": Counter()})
        s["individuals"] += rec.size
        s["records"].append(rec.id)
        if rec.pmid not in s["pmids"]:
            s["pmids"].append(rec.pmid)
        s["reasons"][rec.genotype_reason] += 1
    return support


def _surname_year(text: str) -> tuple[str, str]:
    m = re.search(r"([A-Z][\w'’\-]+).*?((?:19|20)\d\d)", text or "")
    return (m.group(1).lower(), m.group(2)) if m else ("", "")


def _is_generic_label(label: str) -> bool:
    return bool(re.fullmatch(r"(patient|case|family|proband|subject|individual|sib|pedigree|kindred|p|f)?"
                             r"\s*[#.:-]?\s*[\dIVXivx]+([-.:]\d+)?[a-z]?", label.strip().lower()))


class CaseTable:
    """The pooled cohort: totals, per-term, per-variant and per-gene tables, inheritance evidence."""

    def __init__(self, seed: Seed, papers: dict[str, Paper], cases: list[PaperCases], normalize_gene=None):
        if normalize_gene is None:
            from ..sources.hgnc import normalize_symbol as normalize_gene
        self.seed = seed
        self.papers = papers
        self.cases = cases
        self.relevance = {c.pmid: c.relevance for c in cases}
        self.records: dict[str, CaseRecord] = {r.id: r for c in cases for r in c.records}
        self.notes: dict[str, CaseNote] = {n.id: n for c in cases for n in c.notes}
        self._gene_cache: dict[str, str] = {}
        self._normalize = normalize_gene
        self._normalise_genes()
        self._mark_followups()
        self.variants = self._build_variants()
        self.genes = self._build_genes()
        self.x_genes: set[str] = set()

    # -- helpers ----------------------------------------------------------- #

    def gene(self, symbol: str) -> str:
        key = (symbol or "").strip()
        if not key:
            return ""
        if key not in self._gene_cache:
            try:
                self._gene_cache[key] = self._normalize(key) or key.upper()
            except Exception as exc:  # noqa: BLE001 - nomenclature lookup is best-effort
                log.warning("HGNC lookup failed for %s: %s", key, exc)
                self._gene_cache[key] = key.upper()
        return self._gene_cache[key]

    def is_core(self, pmid: str) -> bool:
        return self.relevance.get(pmid) in CORE_RELEVANCE

    def pooled(self) -> list[CaseRecord]:
        """Records that are counted: from core papers and not re-reports of a supplied earlier paper."""
        return [r for r in self._ordered() if self.is_core(r.pmid) and not r.followup_of]

    def _ordered(self) -> list[CaseRecord]:
        def key(r: CaseRecord):
            p = self.papers.get(r.pmid)
            return ((p.year or 9999) if p else 9999, r.pmid, int(r.id.rsplit(":", 1)[-1]))
        return sorted(self.records.values(), key=key)

    def label(self, pmid: str) -> str:
        return self.papers[pmid].label if pmid in self.papers else f"PMID {pmid}"

    # -- construction ------------------------------------------------------ #

    def _normalise_genes(self) -> None:
        for rec in self.records.values():
            for v in rec.variants:
                v.gene = self.gene(v.gene)

    def _mark_followups(self) -> None:
        by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
        for pmid, paper in self.papers.items():
            if paper.authors and paper.year:
                by_name[(paper.authors[0].split()[0].lower(), str(paper.year))].append(pmid)
        for rec in self.records.values():
            if not rec.previously_reported:
                continue
            earlier = [p for p in by_name.get(_surname_year(rec.previously_reported), []) if p != rec.pmid]
            if earlier:
                rec.followup_of = earlier[0]

    def _build_variants(self) -> list[dict[str, Any]]:
        """One row per distinct variant, mentions merged across names and papers by `variant_keys`."""
        uf = _UnionFind()
        mention_keys: dict[tuple[str, int], set[tuple[str, str]]] = {}
        for rec in self.records.values():
            for i, v in enumerate(rec.variants):
                keys = {(v.gene, k) for k in variant_keys(v)} or {(v.gene, "raw:" + v.as_reported.strip().lower())}
                mention_keys[(rec.id, i)] = keys
                first = next(iter(keys))
                for k in keys:
                    uf.union(first, k)
        clusters: dict[Any, set[tuple[str, str]]] = defaultdict(set)
        for keys in mention_keys.values():
            for k in keys:
                clusters[uf.find(k)].add(k)

        rows: dict[Any, dict[str, Any]] = {}
        for rec in self._ordered():
            for i, v in enumerate(rec.variants):
                root = uf.find(next(iter(mention_keys[(rec.id, i)])))
                row = rows.get(root)
                if row is None:
                    keys = sorted(k for _, k in clusters[root])
                    named = [k for k in keys if not k.startswith("raw:")]
                    row = rows[root] = {
                        "id": f"V{len(rows) + 1}", "gene": root[0], "keys": named,
                        "omim_name": omim_variant_name(root[0], named) if named else
                        f"{root[0]}, {v.as_reported.upper()}".strip(", "),
                        "as_reported": [], "records": [], "pmids": [], "individuals": 0,
                        "zygosity": Counter(), "origin": Counter(), "consequence": "",
                    }
                v.key = row["id"]
                if v.as_reported and v.as_reported not in row["as_reported"]:
                    row["as_reported"].append(v.as_reported)
                if rec.id not in row["records"]:
                    row["records"].append(rec.id)
                    if self.is_core(rec.pmid) and not rec.followup_of:
                        row["individuals"] += rec.size
                if rec.pmid not in row["pmids"]:
                    row["pmids"].append(rec.pmid)
                row["zygosity"][v.zygosity or "unknown"] += 1
                row["origin"][v.origin or "unknown"] += 1
                row["consequence"] = row["consequence"] or v.consequence
        return [{**r, "zygosity": dict(r["zygosity"]), "origin": dict(r["origin"])} for r in rows.values()]

    def _build_genes(self) -> dict[str, dict[str, Any]]:
        """Genes with patient variants in records from core papers, with the papers and individuals."""
        genes: dict[str, dict[str, Any]] = {}
        for row in self.variants:
            if not row["gene"]:
                continue
            core_pmids = [p for p in row["pmids"] if self.is_core(p)]
            if not core_pmids:
                continue
            g = genes.setdefault(row["gene"], {"pmids": [], "variants": [], "individuals": 0})
            g["pmids"] = sorted(set(g["pmids"]) | set(core_pmids))
            g["variants"].append(row["id"])
            g["individuals"] += row["individuals"]
        return genes

    # -- derived tables ---------------------------------------------------- #

    def totals(self) -> dict[str, int]:
        pooled = self.pooled()
        families = 0
        seen_family: set[tuple[str, str]] = set()
        for r in pooled:
            if r.kind == "individual" and r.family:
                key = (r.pmid, r.family.lower())
                if key in seen_family:
                    continue
                seen_family.add(key)
                families += 1
            else:
                families += r.n_families or 1
        return {"individuals": sum(r.size for r in pooled), "families": families, "records": len(pooled),
                "follow_up_records": sum(1 for r in self.records.values() if r.followup_of and self.is_core(r.pmid)),
                "background_records": sum(1 for r in self.records.values() if not self.is_core(r.pmid))}

    def phenotype_table(self) -> dict[str, dict[str, Any]]:
        """HPO term -> individuals present / absent / assessed, records and papers (see module docstring)."""
        rows: dict[str, dict[str, Any]] = {}

        def contributions(records: list[CaseRecord]) -> dict[str, dict[str, Any]]:
            out: dict[str, dict[str, Any]] = {}
            for rec in records:
                per_term: dict[str, tuple[tuple[int, int, int], CasePhenotype]] = {}
                for p in rec.phenotypes:
                    if not p.hpo_id:
                        continue
                    t = _tally_feature(p, rec.size)
                    if p.hpo_id not in per_term or t > per_term[p.hpo_id][0]:
                        per_term[p.hpo_id] = (t, p)
                for hpo_id, ((hit, miss, assessed), p) in per_term.items():
                    row = out.setdefault(hpo_id, {"label": p.hpo_label, "present": 0, "absent": 0, "assessed": 0,
                                                  "records": [], "pmids": [], "texts": Counter(), "lower_bound": False})
                    row["present"] += hit
                    row["absent"] += miss
                    row["assessed"] += assessed
                    row["records"].append(rec.id)
                    if rec.pmid not in row["pmids"]:
                        row["pmids"].append(rec.pmid)
                    row["texts"][p.text] += 1
                    row["lower_bound"] |= p.some_only and p.present and p.n_with is None
            return out

        first = contributions(self.pooled())
        follow = contributions([r for r in self._ordered() if self.is_core(r.pmid) and r.followup_of])
        for hpo_id, row in first.items():
            rows[hpo_id] = row
            if hpo_id in follow:
                for p in follow[hpo_id]["pmids"]:
                    if p not in row["pmids"]:
                        row["pmids"].append(p)
                row["records"] += follow[hpo_id]["records"]
        for hpo_id, row in follow.items():
            if hpo_id not in rows:  # a feature only the follow-up recorded: counted once, from it
                row["from_follow_up"] = True
                rows[hpo_id] = row
        for row in rows.values():
            row["text"] = row.pop("texts").most_common(1)[0][0]
        return rows

    def compute_inheritance(self) -> dict[str, Any]:
        for rec in self.records.values():
            rec.genotype_mode, rec.genotype_reason = record_mode(rec, self.x_genes)
        pooled = self.pooled()
        overall = _mode_support(pooled)
        chosen = choose_modes(overall)
        per_gene: dict[str, list[str]] = {}
        for gene in self.genes:
            recs = [r for r in pooled if any(v.gene == gene for v in r.variants)]
            per_gene[gene] = choose_modes(_mode_support(recs)) or chosen
        fallback: dict[str, list[str]] = {}
        if not chosen:
            for r in self.records.values():
                if self.is_core(r.pmid) and r.inheritance in INHERITANCE_HPO:
                    fallback.setdefault(r.inheritance, []).append(r.pmid)
            for n in self.notes.values():
                if self.is_core(n.pmid) and n.inheritance in INHERITANCE_HPO:
                    fallback.setdefault(n.inheritance, []).append(n.pmid)
            if fallback:
                chosen = [max(fallback, key=lambda m: (len(set(fallback[m])), m))]
        return {
            "chosen": chosen, "per_gene": per_gene,
            "support": {m: {**s, "reasons": dict(s["reasons"])} for m, s in overall.items()},
            "stated_fallback": {m: sorted(set(p)) for m, p in fallback.items()},
        }

    def possible_duplicates(self) -> list[list[str]]:
        """Records in different papers sharing a specific label: kept separate, listed for a curator."""
        by_label: dict[str, list[CaseRecord]] = defaultdict(list)
        for r in self.records.values():
            if r.label and not _is_generic_label(r.label):
                by_label[r.label.lower()].append(r)
        return [[r.id for r in recs] for recs in by_label.values() if len({r.pmid for r in recs}) > 1]

    def synopsis(self) -> list[SynopsisItem]:
        """Terms with at least one individual present and no more absent than present."""
        from ..sources.hpo import get_hpo

        hpo = get_hpo()
        table = {t: r for t, r in self.phenotype_table().items() if r["present"] >= 1 and r["absent"] <= r["present"]}
        items = []
        for hpo_id, row in table.items():
            # A general term adds nothing when a more specific one rests on the same records.
            if any(other != hpo_id and hpo_id in hpo.ancestors(other, include_self=False)
                   and set(row["records"]) <= set(table[other]["records"]) for other in table):
                continue
            items.append(SynopsisItem(
                category=hpo.category(hpo_id), feature=row["text"], hpo_id=hpo_id, hpo_label=row["label"],
                pmids=row["pmids"], n_papers=len(row["pmids"]), n_present=row["present"], n_assessed=row["assessed"],
            ))
        return sorted(items, key=lambda i: (i.category, -(i.n_present or 0), i.hpo_label))

    def to_json(self, inheritance: dict[str, Any]) -> dict[str, Any]:
        return {
            "seed": self.seed.model_dump(),
            "totals": self.totals(),
            "papers": [{"pmid": c.pmid, "label": self.label(c.pmid), "relevance": c.relevance,
                        "content_level": c.content_level, "records": len(c.records), "notes": len(c.notes),
                        "dropped_records": len(c.dropped_records), "dropped_notes": len(c.dropped_notes),
                        "error": c.error} for c in self.cases],
            "phenotypes": self.phenotype_table(),
            "variants": self.variants,
            "genes": self.genes,
            "inheritance": inheritance,
            "possible_duplicates": self.possible_duplicates(),
            "records": [r.model_dump() for r in self._ordered()],
            "notes": [n.model_dump() for n in self.notes.values()],
            "dropped": {"records": [r.model_dump() for c in self.cases for r in c.dropped_records],
                        "notes": [n.model_dump() for c in self.cases for n in c.dropped_notes]},
        }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


class CParagraph(BaseModel):
    text: str
    evidence_ids: list[str] = Field(description='IDs of the records and notes this paragraph rests on, e.g. "R:8016139:2", "N:8016139:1"')


class CSection(BaseModel):
    name: SectionName
    paragraphs: list[CParagraph]


class CAllelicVariant(BaseModel):
    variant_id: str = Field(description='The variant\'s ID from the variant table, e.g. "V3"')
    name: str
    phenotype: str
    paragraphs: list[CParagraph]


class CEntry(BaseModel):
    intro: CParagraph
    sections: list[CSection]
    allelic_variants: list[CAllelicVariant]


COHORT_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are \
given the entry's header and a case table assembled from the literature: one quote-verified record \
per reported patient, family or patient group, pooled tables of clinical features, variants and genes, \
the mode of inheritance computed from the patients' genotypes, and notes holding the other citable \
results of each paper. Write the entry's text from this material.

The records and notes are the only admissible evidence. Each has already been checked against its \
paper, and after you write, every sentence will be audited against the paper it cites. So write only \
what the records, their quotes and the notes say: no facts, numbers, variants, citations or \
interpretations from your own memory of the disorder, the gene, or the existing OMIM entry, however \
confident you are. If the evidence leaves a gap, leave the gap. Never attribute a record or note to a \
paper other than the one it came from.

The pooled counts (how many individuals across all papers had a feature) are computed for the clinical \
synopsis and are not statements any paper made: do not write cross-paper totals or percentages in the \
text. Report numbers per paper, as each paper gave them.

For each paragraph, list in `evidence_ids` exactly the records (R:...) and notes (N:...) it draws on. \
A paragraph with no valid ID is discarded. Papers marked "background" are context: draw on them only \
where they bear on this entry's subject. Use the evidence fully: in Clinical Features describe each \
paper's patients (who, how many, ancestry, consanguinity, onset, course and the salient findings) and \
in Molecular Genetics the variants found in them; a curator reading your entry should not need to \
reopen the papers to learn who was studied, what was found and how it was shown.

{STYLE}

{INTRO_RULE} The causal genes and the mode of inheritance have been computed from the case table and \
are given to you; use them in the intro.

`allelic_variants`: one item per variant in the variant table that was reported as disease-causing in \
patients, keyed by its `variant_id`, in chronological order of first report, each with paragraphs \
citing the records that carry it. `phenotype` is the disorder the variant causes, as named in this entry.\
"""


def _record_line(rec: CaseRecord, table: CaseTable) -> str:
    bits = [table.label(rec.pmid), f'{rec.kind} "{rec.label}"' if rec.label else rec.kind]
    if rec.family:
        bits.append(f"family {rec.family}")
    if rec.kind != "individual":
        bits.append(f"{rec.n_affected if rec.n_affected else '?'} affected, "
                    f"{rec.n_families if rec.n_families else '?'} famil{'y' if rec.n_families == 1 else 'ies'}")
    for name, value in (("sex", rec.sex), ("ancestry", rec.ancestry), ("onset", rec.onset), ("last report", rec.age_last)):
        if value:
            bits.append(f"{name}: {value}")
    if rec.consanguinity != "not_stated":
        bits.append(f"consanguineous: {rec.consanguinity}")
    if table.relevance.get(rec.pmid) == "background":
        bits.append("background paper")
    if rec.followup_of:
        bits.append(f"re-reports patients of {table.label(rec.followup_of)}")
    lines = [f"[{rec.id}] " + " | ".join(bits)]
    feats = []
    for p in rec.phenotypes:
        count = (f" {p.n_with}/{p.n_assessed}" if p.n_with is not None and p.n_assessed else
                 f" {p.n_with}" if p.n_with is not None else " (some)" if p.some_only else "")
        feats.append(f"{p.text}{' [' + p.hpo_label + ']' if p.hpo_label else ''}"
                     f"{'' if p.present else ' ABSENT'}{count}")
    if feats:
        lines.append("  features: " + "; ".join(feats))
    if rec.variants:
        lines.append("  variants: " + "; ".join(
            f"{v.key} {v.gene} {v.as_reported}".strip() + f" ({', '.join(x for x in (v.zygosity, v.origin, v.consequence) if x and x != 'unknown')})"
            for v in rec.variants))
    if rec.segregation:
        lines.append(f"  segregation: {rec.segregation}")
    if rec.inheritance in INHERITANCE_HPO:
        lines.append(f"  inheritance stated: {rec.inheritance}")
    lines.append("  quotes: " + " | ".join(f'"{q}"' for q, s in zip(rec.quotes, rec.quote_grounding) if s >= GROUNDED))
    return "\n".join(lines)


def cohort_context(table: CaseTable, inheritance: dict[str, Any]) -> str:
    lines: list[str] = ["PAPERS"]
    for pmid in sorted(table.relevance, key=lambda p: ((table.papers[p].year or 9999) if p in table.papers else 9999, p)):
        if pmid not in table.papers or table.relevance[pmid] == "not_relevant":
            continue
        c = next(c for c in table.cases if c.pmid == pmid)
        p = table.papers[pmid]
        lines.append(f"- {p.label} | PMID {pmid} | {c.relevance} | text: {p.content_level} | "
                     f"{len(c.records)} records, {len(c.notes)} notes | {p.title}")

    t = table.totals()
    lines.append(f"\nCASE TABLE TOTALS (pooled, for orientation only): {t['individuals']} affected individuals, "
                 f"{t['families']} families, {t['records']} records")
    lines.append("\nCAUSAL GENES (computed: genes with patient variants in primary or supporting papers)")
    lines.extend(f"- {g}: {s['individuals']} individuals; papers: "
                 f"{'; '.join(table.label(p) for p in s['pmids'])}" for g, s in table.genes.items())
    if not table.genes:
        lines.append("- none established")
    lines.append("\nMODE OF INHERITANCE (computed from genotypes and stated family patterns)")
    lines.append("- called: " + (", ".join(f"{m} ({INHERITANCE_HPO[m][1]})" for m in inheritance["chosen"]) or "none"))
    for mode, s in inheritance["support"].items():
        lines.append(f"- {mode}: {s['individuals']} individuals in {len(s['records'])} records "
                     f"({'; '.join(f'{k}: {v}' for k, v in s['reasons'].items())})")

    lines.append("\nVARIANT TABLE (one row per distinct variant after merging names across papers)")
    for row in table.variants:
        lines.append(f"- variant_id={row['id']} | gene {row['gene'] or '?'} | "
                     f"{' / '.join(row['keys']) or '; '.join(row['as_reported'])} | "
                     f"zygosity {row['zygosity']} | carried in records: {', '.join(row['records'])}")
    if not table.variants:
        lines.append("- none")

    pheno = table.phenotype_table()
    if pheno:
        lines.append("\nCLINICAL FEATURES (pooled individuals present / assessed; absent)")
        for hpo_id, row in sorted(pheno.items(), key=lambda kv: (-kv[1]["present"], kv[1]["label"])):
            lines.append(f"- {row['label']} ({hpo_id}): {row['present']}/{row['assessed']}, {row['absent']} absent"
                         f"{' (lower bound)' if row['lower_bound'] else ''}")

    lines.append("\nRECORDS (oldest paper first)")
    for rec in table._ordered():
        lines.append(_record_line(rec, table))

    lines.append("\nNOTES BY SECTION")
    for section in SECTION_ORDER:
        notes = sorted((n for n in table.notes.values() if n.section == section),
                       key=lambda n: ((table.papers[n.pmid].year or 9999) if n.pmid in table.papers else 9999,
                                      n.pmid, int(n.id.rsplit(":", 1)[-1])))
        if not notes:
            continue
        lines.append(f"\n## {section}")
        for n in notes:
            tag = "  (background paper)" if table.relevance.get(n.pmid) == "background" else ""
            lines.append(f"[{n.id}] {n.statement}{tag}")
    return "\n".join(lines)


def render_entry(seed: Seed, table: CaseTable, inheritance: dict[str, Any], gene_ref: str,
                 gene_facts: dict[str, dict[str, str]], llm) -> GeneratedEntry:
    context = cohort_context(table, inheritance)
    prompt = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none'}\n\n"
        f"<case_table>\n{context}\n</case_table>"
    )
    raw = llm.call("synthesize", COHORT_SYSTEM, prompt, CEntry)

    evidence: dict[str, str] = {**{i: r.pmid for i, r in table.records.items()},
                                **{i: n.pmid for i, n in table.notes.items()}}
    label_to_pmid = _labels(table.papers.values())
    dropped: list[str] = []
    unknown_citations: list[str] = []
    removed_mims: list[str] = []
    allowed_mims = {f["mim"] for f in gene_facts.values() if f.get("mim")} | ({seed.mim} if seed.mim else set())

    def paragraph(x: CParagraph, where: str) -> EntryParagraph | None:
        text = _strip_mim_numbers(squash(x.text), allowed_mims, removed_mims)
        if not text:
            return None
        ids = [i.strip().strip("[]") for i in x.evidence_ids]
        valid = [i for i in dict.fromkeys(ids) if i in evidence]
        if not valid:
            dropped.append(f"{where}: {text[:120]}")
            return None
        para = EntryParagraph(text=text, finding_ids=valid, pmids=list(dict.fromkeys(evidence[i] for i in valid)))
        _attach_text_citations(para, label_to_pmid, unknown_citations)
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
        row = rows.get(x.variant_id.strip())
        if row is None:
            dropped.append(f"allelic variant with unknown id {x.variant_id!r}")
            continue
        if row["id"] in seen:
            continue
        paras = [p for xp in x.paragraphs if (p := paragraph(xp, f"allelic variant {x.name}"))]
        if not paras:
            continue
        seen.add(row["id"])
        entry.allelic_variants.append(AllelicVariantEntry(
            number=len(entry.allelic_variants) + 1, gene_symbol=row["gene"],
            name=squash(x.name) or row["omim_name"], hgvs=list(row["keys"]),
            phenotype=squash(x.phenotype), paragraphs=paras,
        ))

    # Structured parts: from the table, not from the prose.
    if seed.entry_type != "gene":
        for gene, support in table.genes.items():
            facts = gene_facts.get(gene, {})
            entry.relationships.append(GenePhenotypeRelationship(
                phenotype=seed.title, phenotype_mim=seed.mim or "", gene_symbol=gene,
                gene_mim=facts.get("mim", ""), location=facts.get("location", ""),
                inheritance=inheritance["per_gene"].get(gene, inheritance["chosen"]), mapping_key=3,
                pmids=support["pmids"],
            ))
    entry.inheritance = list(inheritance["chosen"])
    entry.clinical_synopsis = table.synopsis()
    entry.assign_paragraph_ids()
    entry.references = _references(entry, table.papers)
    entry.meta = {
        "strategy": "cohort", "generated": date.today().isoformat(),
        "model": llm.settings.model_for("synthesize"),
        "dropped_ungrounded": dropped, "unknown_citations": sorted(set(unknown_citations)),
        "removed_cross_references": removed_mims,
    }
    return entry


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    from ..pipeline import _write

    cases = extract_cases(seed, papers, llm)
    hpo_stats = ground_case_phenotypes(cases, llm)
    table = CaseTable(seed, {p.pmid: p for p in papers}, cases)

    gene_ref, gene_facts = _gene_reference(sorted(set(table.genes) | set(seed.gene_symbols)))
    table.x_genes = {g for g, f in gene_facts.items() if (f.get("location") or "").upper().startswith("X")}
    inheritance = table.compute_inheritance()
    _write(out_dir / "cohort.json", table.to_json(inheritance))

    entry = render_entry(seed, table, inheritance, gene_ref, gene_facts, llm)
    totals = table.totals()
    n_rec = sum(len(c.records) for c in cases)
    n_rec_drop = sum(len(c.dropped_records) for c in cases)
    n_note = sum(len(c.notes) for c in cases)
    n_note_drop = sum(len(c.dropped_notes) for c in cases)
    entry.meta["cohort"] = {
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
        "inheritance": {"chosen": inheritance["chosen"], "per_gene": inheritance["per_gene"],
                        "support": {m: {k: v for k, v in s.items() if k != "records"} | {"n_records": len(s["records"])}
                                    for m, s in inheritance["support"].items()},
                        "stated_fallback": inheritance["stated_fallback"]},
        "possible_duplicates": table.possible_duplicates(),
    }
    log.info("[%s] cohort: %d individuals, %d families, %d records", seed.mim or seed.title,
             totals["individuals"], totals["families"], totals["records"])
    return entry
