"""Reconciled case database: the case table after an explicit reconciliation step.

The case table of the `cohort` strategy keeps every paper's records apart, so a
patient reported in three papers is counted three times, and nothing settles a
value two papers state differently. Following SLIDERS, this strategy puts a
reconciliation step between extraction and everything computed from the table,
and treats the reconciled table as a product of its own: the start of an
OMIM-like case database (`casebase.json`).

    records (cohort extraction, unchanged, so cache hits)
      ─ propose (model): which records are the same individual or family, or one
        is included in another's group; which variant rows are the same variant;
        which stated values conflict. Each proposal names record ids, a reason and
        verbatim evidence quotes.
      ─ verify (a second, independent model call): accept or reject each proposal
        on the evidence; similarity alone is not evidence.
      ─ apply (code): merge accepted records, keep every source, settle conflicts
        by the rules below, log everything.
      ─ synopsis, genes, inheritance by the cohort rules; entry by the cohort renderer.

Hard rules applied in code whatever the verifier said (each logged as a rejection):
a proposal needs two or more known record ids and at least one evidence quote found
verbatim in a supplied paper; a same-individual merge is refused when two sources
state different sexes; a variant merge is refused across genes.

Merging an accepted cluster of records (`_merge`):

* unit: an individual if every source is one person; otherwise a family (or a
  group if any source is a group). Its size is the largest of: any family or
  group source's affected count, and the number of distinct individual records
  one paper contributes (people from the same paper are different people).
* variants: the union, by variant row.
* phenotypes, per HPO term: the source with the largest tally of individuals with
  the feature gives the count (not the sum: they are the same patients). A term
  one source reports present and another absent is kept present (features
  accumulate over follow-up) and logged as a conflict.
* other stated values, when sources disagree: full text outranks abstract outranks
  title; among equals the original (earliest) report wins for sex, ancestry,
  consanguinity, onset, segregation and stated inheritance, and the latest report
  wins for age at last report and for a variant's zygosity and origin (later
  reports reflect fuller testing and longer follow-up). Every disagreement is
  logged with the values, the source of each and the value kept.

Records the cohort table already treats as follow-ups (the paper names the
earlier supplied report) and that reconciliation did not merge stay excluded,
as in `cohort`.
"""

from __future__ import annotations

import copy
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..grounding import SourceIndex
from ..kg import _UnionFind, omim_variant_name
from ..models import GeneratedEntry, Paper, Seed, squash
from ..synthesize import _gene_reference
from .cohort import (
    CasePhenotype,
    CaseRecord,
    CaseTable,
    PaperCases,
    _record_line,
    _tally_feature,
    extract_cases,
    ground_case_phenotypes,
    record_mode,
    render_entry,
)

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Model replies
# --------------------------------------------------------------------------- #


class XEvidence(BaseModel):
    pmid: str = Field(description="PMID of the paper the quote is taken from")
    quote: str = Field(description="Verbatim text from that paper (a record quote or an evidence sentence)")


class XSameCase(BaseModel):
    record_ids: list[str]
    relation: Literal["same_individual", "same_family", "included_in_group"]
    reason: str
    evidence: list[XEvidence]


class XSameVariant(BaseModel):
    variant_ids: list[str]
    reason: str
    evidence: list[XEvidence]


class XConflict(BaseModel):
    record_ids: list[str]
    field: str = Field(description='e.g. "sex", "onset", "zygosity of V2", "seizures present/absent"')
    values: list[str]
    note: str


class XProposals(BaseModel):
    same_cases: list[XSameCase]
    same_variants: list[XSameVariant]
    conflicts: list[XConflict]


class XDecision(BaseModel):
    proposal_id: str
    accept: bool
    reason: str


class XDecisions(BaseModel):
    decisions: list[XDecision]


PROPOSE_SYSTEM = """\
You are reconciling a case-level database built for an entry in OMIM (Online Mendelian Inheritance in \
Man). Each record below was extracted from one paper and describes one affected individual, one family, \
or a group of patients the paper reports together. The same patients are often reported more than once: \
a family is described and later re-studied, a case report is later included in a series, a follow-up \
paper revisits the same patients. Your job is to find these, so that no patient is counted twice.

Propose:
- `same_cases`: sets of records that describe the same individual (`same_individual`), the same family \
(`same_family`), or where one record's patients are part of another record's group (`included_in_group`, \
listing the group record first).
- `same_variants`: variant table rows that are the same change named differently (for example legacy \
and HGVS numbering of one change), only within one gene.
- `conflicts`: values that two records of the same patients state differently (sex, ages, onset, \
consanguinity, zygosity, a feature present in one and absent in the other, the mode of inheritance).

Evidence rule. Propose a merge only when the papers say or clearly show the patients are the same: a \
paper states that it re-reports, follows up or includes patients described in another supplied paper \
(by citation, or by an author-and-year reference), or the records share specific identifying details \
that cannot plausibly coincide (the same pedigree labels in papers by overlapping authors, together with \
matching ages, sexes and family structure). Sharing a variant, a phenotype, a country or an ethnicity is \
not evidence: recurrent and founder variants occur in unrelated families, and such records must stay \
separate. Each proposal must give one or more `evidence` quotes copied verbatim from the record quotes or \
the evidence sentences shown, with the PMID of the paper they come from; a program will check them. When \
in doubt, do not propose. Return empty lists if nothing qualifies.\
"""

VERIFY_SYSTEM = """\
You are an independent reviewer checking proposed merges in a case-level database for an OMIM entry. \
Each proposal claims that some records (each extracted from one paper) describe the same patients, or \
that two variant rows are the same variant. You see the records, the evidence quotes offered for each \
proposal (with whether a program found them verbatim in the paper), and sentences from the papers that \
mention earlier reports.

Accept a proposal only if the evidence shows the identity: a paper stating that it re-reports, follows \
up or includes the other paper's patients, or specific identifying details that cannot plausibly \
coincide. Reject it when the evidence is only similarity (the same variant, the same features, the same \
country or ethnicity): unrelated patients with the same variant must stay separate. Reject it when the \
records contradict identity (an individual reported as male in one and female in the other, a different \
family structure, a different variant). Reject a variant merge unless the two names denote the same \
change in the same gene. Decide every proposal by its `proposal_id`, with a one-sentence reason. When in \
doubt, reject.\
"""

# --------------------------------------------------------------------------- #
# Evidence sentences
# --------------------------------------------------------------------------- #

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
_REREPORT = re.compile(
    r"previously (?:reported|described|published|studied|identified)|(?:reported|described|published) "
    r"(?:previously|earlier|before|elsewhere)|originally (?:reported|described)|same (?:patients?|family|families|"
    r"kindreds?|probands?|individuals?|pedigrees?)|follow[- ]?up|re-?evaluat|re-?examin|re-?investigat|"
    r"re-?stud|updated?\b|(?:part|subset) of (?:a|the|our) (?:previous|earlier|larger)|included in", re.I)


def evidence_sentences(papers: dict[str, Paper], pmids: list[str], per_paper: int = 25) -> dict[str, list[str]]:
    """Sentences that can tie one paper's patients to another's, per paper (no model).

    A sentence qualifies if it speaks of earlier reports, follow-up or the same
    patients, or names the first author of another supplied paper.
    """
    surnames = {}
    for pmid in pmids:
        p = papers.get(pmid)
        if p and p.authors:
            name = p.authors[0].split()[0]
            if len(name) >= 3:
                surnames[pmid] = name
    out: dict[str, list[str]] = {}
    for pmid in pmids:
        p = papers.get(pmid)
        if p is None:
            continue
        others = [re.escape(n) for q, n in surnames.items() if q != pmid]
        cites = re.compile(r"\b(?:" + "|".join(others) + r")\b") if others else None
        found = []
        for sent in _SENT.split(squash(p.source_text())):
            if len(sent) < 25:
                continue
            if _REREPORT.search(sent) or (cites and cites.search(sent)):
                found.append(sent[:400])
            if len(found) >= per_paper:
                break
        out[pmid] = found
    return out


# --------------------------------------------------------------------------- #
# The reconciled table
# --------------------------------------------------------------------------- #


class MergedRecord(CaseRecord):
    """One individual, family or group after reconciliation, with its source records."""

    sources: list[str] = Field(default_factory=list)
    source_pmids: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)


_LEVEL = {"fulltext": 0, "abstract": 1, "title": 2}


class ReconciledTable(CaseTable):
    """A `CaseTable` whose counts run over reconciled cases.

    `records` still holds every source record (the writer cites them, and each
    belongs to one paper); `merged` holds the reconciled units that replace their
    sources wherever anything is counted.
    """

    def __init__(self, *args, **kwargs):
        self.merged: dict[str, MergedRecord] = {}
        self.absorbed: dict[str, str] = {}          # source record id -> merged id
        self.conflicts: list[dict[str, Any]] = []
        self.variant_merges: list[dict[str, Any]] = []
        super().__init__(*args, **kwargs)

    # -- counting over reconciled units ------------------------------------ #

    def pooled(self) -> list[CaseRecord]:
        units = [r for r in super().pooled() if r.id not in self.absorbed]
        units += [m for m in self.merged.values() if self.is_core(m.pmid)]

        def key(r: CaseRecord):
            p = self.papers.get(r.pmid)
            return ((p.year or 9999) if p else 9999, r.pmid, r.id)
        return sorted(units, key=key)

    def phenotype_table(self) -> dict[str, dict[str, Any]]:
        rows = super().phenotype_table()
        # A merged unit is counted once, but every paper that reported the feature still supports it.
        for m in self.merged.values():
            for p in m.phenotypes:
                row = rows.get(p.hpo_id)
                if row is None or m.id not in row["records"]:
                    continue
                for sid in m.sources:
                    src = self.records[sid]
                    if any(q.hpo_id == p.hpo_id and not q.other_cause for q in src.phenotypes) \
                            and src.pmid not in row["pmids"]:
                        row["pmids"].append(src.pmid)
        return rows

    def compute_inheritance(self, genes: set[str] | None = None) -> dict[str, Any]:
        use = set(self.genes) if genes is None else set(genes)
        for m in self.merged.values():
            m.genotype_mode, m.genotype_reason = record_mode(m, self.x_genes, use or None)
        result = super().compute_inheritance(genes)
        for m in self.merged.values():
            m.genotype_mode, m.genotype_reason = record_mode(m, self.x_genes, use or None)
        return result

    def _recount_variants(self) -> None:
        rows = {r["id"]: r for r in self.variants}
        for row in rows.values():
            row["individuals"] = 0
        for unit in self.pooled():
            if unit.mixed_genotypes:
                continue
            for vid in {v.key for v in unit.variants if v.key in rows}:
                rows[vid]["individuals"] += unit.size
        self.genes = self._build_genes()

    # -- applying accepted proposals ---------------------------------------- #

    def _priority(self, rid: str, latest: bool) -> tuple:
        rec = self.records[rid]
        paper = self.papers.get(rec.pmid)
        level = _LEVEL.get(paper.content_level, 3) if paper else 3
        year = (paper.year or 9999) if paper else 9999
        return (level, -year if latest else year, rec.pmid, rid)

    def _settle(self, cluster: str, field: str, values: dict[str, str], latest: bool) -> str:
        """Pick one of the sources' stated values by the stated rule; log a disagreement."""
        stated = {rid: v for rid, v in values.items() if v and v not in ("not_stated", "UNKNOWN", "unknown")}
        if not stated:
            return next(iter(values.values()), "")
        best = min(stated, key=lambda rid: self._priority(rid, latest))
        if len({squash(v).lower() for v in stated.values()}) > 1:
            self.conflicts.append({
                "case": cluster, "field": field, "values": stated, "kept": stated[best], "from": best,
                "rule": ("full text first, then the latest report" if latest
                         else "full text first, then the original (earliest) report"),
            })
        return stated[best]

    def _merge(self, cid: str, ids: list[str], relations: list[str]) -> MergedRecord:
        srcs = [self.records[i] for i in ids]
        core = [r for r in srcs if self.is_core(r.pmid)] or srcs
        anchor = min(core, key=lambda r: self._priority(r.id, latest=False)[1:])
        if all(r.kind == "individual" for r in srcs) and all(
                sum(1 for r in srcs if r.pmid == pmid) == 1 for pmid in {r.pmid for r in srcs}):
            kind, size = "individual", 1
        else:
            kind = "group" if any(r.kind == "group" for r in srcs) else "family"
            per_paper = Counter(r.pmid for r in srcs if r.kind == "individual")
            size = max([r.size for r in srcs if r.kind != "individual"] + list(per_paper.values()) + [1])
        families = max([r.n_families or 1 for r in srcs if r.kind != "individual"] + [1])

        def settle(field: str, latest: bool = False) -> str:
            return self._settle(cid, field, {r.id: getattr(r, field) for r in srcs}, latest)

        merged = MergedRecord(
            id=cid, pmid=anchor.pmid, kind=kind,
            label=" = ".join(dict.fromkeys(f"{r.label} ({self.label(r.pmid)})" for r in srcs)),
            family=anchor.family if kind == "individual" else "",
            n_affected=size, n_families=families,
            sex=settle("sex"), ancestry=settle("ancestry"), consanguinity=settle("consanguinity"),
            onset=settle("onset"), age_last=settle("age_last", latest=True), segregation=settle("segregation"),
            inheritance=settle("inheritance") or "UNKNOWN",
            mixed_genotypes=any(r.mixed_genotypes for r in srcs),
            quotes=[q for r in srcs for q in r.quotes],
            quote_grounding=[s for r in srcs for s in r.quote_grounding],
            sources=ids, source_pmids=list(dict.fromkeys(r.pmid for r in srcs)), relations=relations,
        )
        n_sizes = {r.id: (size if kind == "individual" else r.size) for r in srcs}

        # Variants: union by row; zygosity and origin settled by the latest-report rule.
        by_row: dict[str, list[tuple[CaseRecord, int]]] = defaultdict(list)
        for r in srcs:
            for i, v in enumerate(r.variants):
                by_row[v.key or f"raw:{v.as_reported}"].append((r, i))
        for row_id, mentions in by_row.items():
            first_rec, first_i = min(mentions, key=lambda m: self._priority(m[0].id, latest=True))
            v = first_rec.variants[first_i].model_copy()
            for attr in ("zygosity", "origin"):
                setattr(v, attr, self._settle(cid, f"{attr} of {row_id}",
                                              {r.id: getattr(r.variants[i], attr) for r, i in mentions}, latest=True))
            merged.variants.append(v)
            roles = [r.variant_roles[i] for r, i in mentions if i < len(r.variant_roles)]
            merged.variant_roles.append("causal" if "causal" in roles else
                                        "uncertain" if "uncertain" in roles or not roles else "not_causal")

        # Phenotypes: per term, the largest tally of one source; present beats absent.
        by_term: dict[str, list[tuple[CaseRecord, CasePhenotype]]] = defaultdict(list)
        for r in srcs:
            for p in r.phenotypes:
                if p.hpo_id:
                    by_term[p.hpo_id].append((r, p))
        for hpo_id, items in by_term.items():
            counted = [(r, p) for r, p in items if not p.other_cause]
            if not counted:
                merged.phenotypes.append(items[0][1].model_copy())
                continue
            tallies = [(r, p, _tally_feature(p, n_sizes[r.id])) for r, p in counted]
            present = [t for t in tallies if t[2][0] > 0]
            absent = [t for t in tallies if t[2][1] > 0 and t[2][0] == 0]
            if present and absent:
                self.conflicts.append({
                    "case": cid, "field": f"{items[0][1].hpo_label or hpo_id} present/absent",
                    "values": {r.id: ("present" if t[0] else "absent") for r, _, t in present + absent},
                    "kept": "present", "from": max(present, key=lambda t: t[2][0])[0].id,
                    "rule": "present outranks absent (features accumulate over follow-up)",
                })
            if present:
                r, p, (hit, _, assessed) = max(present, key=lambda t: (t[2][0], t[2][2]))
                merged.phenotypes.append(p.model_copy(update={
                    "present": True, "n_with": min(hit, size), "n_assessed": min(max(assessed, hit), size),
                    "some_only": False}))
            else:
                r, p, (_, miss, assessed) = max(absent, key=lambda t: (t[2][1], t[2][2]))
                merged.phenotypes.append(p.model_copy(update={
                    "present": False, "n_with": min(miss, size), "n_assessed": min(max(assessed, miss), size),
                    "some_only": False}))
        return merged

    def apply(self, case_merges: list[dict[str, Any]], variant_merges: list[dict[str, Any]]) -> None:
        """Apply accepted proposals: variant rows first, then record clusters."""
        rows = {r["id"]: r for r in self.variants}
        uf_v = _UnionFind()
        for vm in variant_merges:
            ids = [i for i in vm["variant_ids"] if i in rows]
            for a in ids[1:]:
                uf_v.union(a, ids[0])
        groups: dict[str, list[str]] = defaultdict(list)
        for vid in rows:
            groups[uf_v.find(vid)].append(vid)
        rename: dict[str, str] = {}
        for members in groups.values():
            if len(members) < 2:
                continue
            members.sort(key=lambda v: int(v[1:]))
            keep = rows[members[0]]
            for vid in members[1:]:
                other = rows.pop(vid)
                for k in other["keys"]:
                    if k not in keep["keys"]:
                        keep["keys"].append(k)
                for name in ("as_reported", "records", "pmids"):
                    keep[name] += [x for x in other[name] if x not in keep[name]]
                for name in ("zygosity", "origin", "authors"):
                    for k, n in other[name].items():
                        keep[name][k] = keep[name].get(k, 0) + n
                rename[vid] = keep["id"]
            keep["omim_name"] = omim_variant_name(keep["gene"], keep["keys"]) if keep["keys"] else keep["omim_name"]
            self.variant_merges.append({"kept": keep["id"], "merged": members[1:], "keys": keep["keys"]})
        self.variants = [r for r in self.variants if r["id"] in rows]
        for rec in self.records.values():
            for v in rec.variants:
                v.key = rename.get(v.key, v.key)

        uf = _UnionFind()
        relations: dict[Any, list[str]] = defaultdict(list)
        for cm in case_merges:
            ids = [i for i in cm["record_ids"] if i in self.records]
            for a in ids[1:]:
                uf.union(a, ids[0])
        clusters: dict[Any, list[str]] = defaultdict(list)
        for rid in self.records:
            if rid in uf.parent:
                clusters[uf.find(rid)].append(rid)
        for cm in case_merges:
            ids = [i for i in cm["record_ids"] if i in self.records]
            if ids:
                relations[uf.find(ids[0])].append(cm["relation"])
        n = 0
        for root, ids in sorted(clusters.items(), key=lambda kv: sorted(kv[1])[0]):
            if len(ids) < 2:
                continue
            n += 1
            ordered = sorted(ids, key=lambda rid: self._priority(rid, latest=False)[1:])
            merged = self._merge(f"C:{n}", ordered, relations[root])
            self.merged[merged.id] = merged
            for rid in ids:
                self.absorbed[rid] = merged.id
                src = self.records[rid]
                src.followup_of = ""
                others = ", ".join(i for i in ordered if i != rid)
                src.label = f"{src.label}; reconciled: same patients as {others}"
        self._recount_variants()

    def units_json(self) -> list[dict[str, Any]]:
        out = []
        for u in self.pooled():
            m = u if isinstance(u, MergedRecord) else None
            out.append({
                "id": u.id, "kind": u.kind, "label": u.label, "n_affected": u.size,
                "n_families": u.n_families or 1, "sex": u.sex, "ancestry": u.ancestry,
                "consanguinity": u.consanguinity, "onset": u.onset, "age_last": u.age_last,
                "inheritance_stated": u.inheritance, "genotype_mode": u.genotype_mode,
                "sources": m.sources if m else [u.id], "pmids": m.source_pmids if m else [u.pmid],
                "relations": m.relations if m else [],
                "variants": [{"id": v.key, "gene": v.gene, "as_reported": v.as_reported, "zygosity": v.zygosity,
                              "origin": v.origin} for v in u.variants],
                "phenotypes": [{"hpo_id": p.hpo_id, "label": p.hpo_label, "text": p.text, "present": p.present,
                                "n_with": p.n_with, "n_assessed": p.n_assessed, "other_cause": p.other_cause}
                               for p in u.phenotypes],
            })
        return out


# --------------------------------------------------------------------------- #
# Propose, verify, apply
# --------------------------------------------------------------------------- #


def _paper_lines(table: CaseTable) -> list[str]:
    lines = ["PAPERS"]
    for c in table.cases:
        p = table.papers.get(c.pmid)
        if p is None or not c.records:
            continue
        authors = ", ".join(p.authors[:8]) + (", ..." if len(p.authors) > 8 else "")
        lines.append(f"- PMID {p.pmid} | {p.label} | {p.year} | text: {p.content_level} | {c.relevance} | "
                     f"authors: {authors} | {p.title}")
    return lines


def _record_block(table: CaseTable, ids: list[str] | None = None) -> list[str]:
    lines = []
    for rec in table._ordered():
        if ids is not None and rec.id not in ids:
            continue
        line = _record_line(rec, table)
        if rec.previously_reported:
            line += f"\n  says previously reported in: {rec.previously_reported}"
        lines.append(line)
    return lines


def _variant_block(table: CaseTable) -> list[str]:
    return [f"- {r['id']} | gene {r['gene'] or '?'} | {' / '.join(r['keys']) or '; '.join(r['as_reported'])} | "
            f"as reported: {'; '.join(r['as_reported'])} | records: {', '.join(r['records'])}" for r in table.variants]


def _sentence_block(sentences: dict[str, list[str]], pmids: list[str] | None = None) -> list[str]:
    lines = []
    for pmid, sents in sentences.items():
        if pmids is not None and pmid not in pmids:
            continue
        if sents:
            lines.append(f"PMID {pmid}:")
            lines.extend(f'  - "{s}"' for s in sents)
    return lines or ["(none)"]


def _ground(evidence: list[XEvidence], indexes: dict[str, SourceIndex], allowed: set[str]) -> list[dict[str, Any]]:
    out = []
    for e in evidence:
        quote = squash(e.quote)
        pmid = e.pmid.strip()
        hits = [p for p in ([pmid] if pmid in indexes else []) + sorted(allowed) if p in indexes
                and indexes[p].contains(quote)]
        out.append({"pmid": pmid, "quote": quote, "found_in": hits[0] if hits else ""})
    return out


def reconcile(seed: Seed, papers: dict[str, Paper], cases: list[PaperCases], llm,
              normalize_gene=None) -> tuple[ReconciledTable, dict[str, Any]]:
    """Propose, verify and apply. Returns the reconciled table and the reconciliation log."""
    table = ReconciledTable(seed, papers, cases, normalize_gene=normalize_gene)
    log_: dict[str, Any] = {"proposed": [], "verified": [], "applied": [], "rejected": [], "conflicts_proposed": [],
                            "conflicts": [], "variant_merges": []}
    if len(table.records) < 2:
        log_["skipped"] = "fewer than two records"
        return table, log_

    pmids = [c.pmid for c in cases if c.records]
    sentences = evidence_sentences(papers, pmids)
    header = f"Entry: {seed.title}" + (f" ({seed.symbol})" if seed.symbol else "")
    prompt = "\n".join([header, "", *_paper_lines(table), "", "RECORDS", *_record_block(table), "",
                        "VARIANT TABLE", *(_variant_block(table) or ["- none"]), "",
                        "EVIDENCE SENTENCES (from the papers' text: mentions of earlier reports, follow-up, or "
                        "the first author of another supplied paper)", *_sentence_block(sentences)])
    proposals = llm.call("reconcile", PROPOSE_SYSTEM, prompt, XProposals)

    indexes = {pmid: SourceIndex(papers[pmid].source_text()) for pmid in pmids if pmid in papers}
    items: list[dict[str, Any]] = []
    for n, x in enumerate(proposals.same_cases, 1):
        ids = list(dict.fromkeys(i.strip().strip("[]") for i in x.record_ids))
        allowed = {table.records[i].pmid for i in ids if i in table.records}
        items.append({"proposal_id": f"P{n}", "type": "same_case", "relation": x.relation, "record_ids": ids,
                      "reason": squash(x.reason), "evidence": _ground(x.evidence, indexes, allowed)})
    for n, x in enumerate(proposals.same_variants, 1):
        ids = list(dict.fromkeys(i.strip() for i in x.variant_ids))
        items.append({"proposal_id": f"V{n}", "type": "same_variant", "variant_ids": ids,
                      "reason": squash(x.reason), "evidence": _ground(x.evidence, indexes, set(pmids))})
    log_["proposed"] = items
    log_["conflicts_proposed"] = [x.model_dump() for x in proposals.conflicts]
    if not items:
        return table, log_

    # Independent check: the verifier sees the claim and the evidence, not the proposer's reasoning.
    involved = sorted({i for it in items for i in it.get("record_ids", [])})
    blocks = []
    rows = {r["id"]: r for r in table.variants}
    for it in items:
        if it["type"] == "same_case":
            claim = f"{it['relation'].replace('_', ' ')}: {', '.join(it['record_ids'])}"
        else:
            claim = "same variant: " + "; ".join(
                f"{v} ({rows[v]['gene']} {' / '.join(rows[v]['keys']) or '; '.join(rows[v]['as_reported'])})"
                if v in rows else f"{v} (unknown)" for v in it["variant_ids"])
        ev = "\n".join(f'    - PMID {e["pmid"]}: "{e["quote"]}" '
                       f'[{"found in PMID " + e["found_in"] if e["found_in"] else "NOT FOUND in the papers"}]'
                       for e in it["evidence"]) or "    (no evidence offered)"
        blocks.append(f"[{it['proposal_id']}] {claim}\n  evidence:\n{ev}")
    involved_pmids = sorted({table.records[i].pmid for i in involved if i in table.records}) or pmids
    vprompt = "\n".join([header, "", "PROPOSALS", *blocks, "", "RECORDS INVOLVED",
                         *_record_block(table, set(involved)), "", "EVIDENCE SENTENCES",
                         *_sentence_block(sentences, involved_pmids)])
    decisions = {d.proposal_id.strip(): d for d in llm.call("reconcile", VERIFY_SYSTEM, vprompt, XDecisions).decisions}

    case_merges, variant_merges = [], []
    for it in items:
        d = decisions.get(it["proposal_id"])
        it["verdict"] = {"accept": bool(d and d.accept), "reason": squash(d.reason) if d else "no decision"}
        log_["verified"].append({"proposal_id": it["proposal_id"], **it["verdict"]})
        refusal = _rule_refusal(it, table)
        if not it["verdict"]["accept"] or refusal:
            log_["rejected"].append({"proposal_id": it["proposal_id"],
                                     "by": "rule" if it["verdict"]["accept"] else "verifier",
                                     "reason": refusal if it["verdict"]["accept"] else it["verdict"]["reason"]})
            continue
        log_["applied"].append(it["proposal_id"])
        (case_merges if it["type"] == "same_case" else variant_merges).append(it)

    table.apply(case_merges, variant_merges)
    log_["conflicts"] = table.conflicts
    log_["variant_merges"] = table.variant_merges
    log_["clusters"] = {m.id: m.sources for m in table.merged.values()}
    return table, log_


def _sex(value: str) -> str:
    v = value.strip().lower()
    if re.fullmatch(r"(?:a |an )?(?:male|man|boy|m)", v):
        return "male"
    if re.fullmatch(r"(?:a |an )?(?:female|woman|girl|f)", v):
        return "female"
    return ""


def _rule_refusal(it: dict[str, Any], table: ReconciledTable) -> str:
    """The hard rules: a reason to refuse an accepted proposal, or ''."""
    if not any(e["found_in"] for e in it["evidence"]):
        return "no evidence quote found verbatim in a supplied paper"
    if it["type"] == "same_variant":
        rows = {r["id"]: r for r in table.variants}
        ids = [v for v in it["variant_ids"] if v in rows]
        if len(ids) < 2:
            return "fewer than two known variant ids"
        if len({rows[v]["gene"] for v in ids}) > 1:
            return "variants in different genes"
        return ""
    ids = [i for i in it["record_ids"] if i in table.records]
    if len(ids) < 2:
        return "fewer than two known record ids"
    if it["relation"] == "same_individual":
        sexes = {_sex(table.records[i].sex) for i in ids} - {""}
        if len(sexes) > 1:
            return "the records state different sexes"
    return ""


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    from ..pipeline import _write

    by_pmid = {p.pmid: p for p in papers}
    cases = extract_cases(seed, papers, llm)              # the cohort prompts: cache hits after a cohort run
    hpo_stats = ground_case_phenotypes(cases, llm)

    before = CaseTable(seed, by_pmid, copy.deepcopy(cases))
    before_totals, before_pheno = before.totals(), before.phenotype_table()

    table, rlog = reconcile(seed, by_pmid, copy.deepcopy(cases), llm)
    gene_ref, gene_facts = _gene_reference(sorted(set(table.genes) | set(seed.gene_symbols)))
    table.x_genes = {g for g, f in gene_facts.items() if (f.get("location") or "").upper().startswith("X")}
    candidate_inheritance = table.compute_inheritance()
    entry = render_entry(seed, table, candidate_inheritance, gene_ref, gene_facts, llm)
    gene_decisions = entry.meta.pop("genes")
    inheritance = entry.meta.pop("final_inheritance")
    after_totals = table.totals()

    _write(out_dir / "casebase.json", {
        "seed": seed.model_dump(),
        "totals": {"before": before_totals, "after": after_totals},
        "units": table.units_json(),
        "records": [r.model_dump() for r in table._ordered()],
        "variants": table.variants,
        "genes": table.genes, "gene_decisions": gene_decisions,
        "inheritance": inheritance, "candidate_inheritance": candidate_inheritance["chosen"],
        "phenotypes": {"before": before_pheno, "after": table.phenotype_table()},
        "log": rlog,
    })
    n_prop_cases = sum(1 for p in rlog["proposed"] if p["type"] == "same_case")
    rejected = {r["proposal_id"]: r for r in rlog["rejected"]}
    entry.meta["reconciled"] = {
        "records_before": before_totals["records"], "records_after": after_totals["records"],
        "individuals_before": before_totals["individuals"], "individuals_after": after_totals["individuals"],
        "families_before": before_totals["families"], "families_after": after_totals["families"],
        "merges_proposed": n_prop_cases,
        "merges_accepted": sum(1 for p in rlog["applied"] if p.startswith("P")),
        "merges_rejected_by_verifier": sum(1 for p, r in rejected.items() if p.startswith("P") and r["by"] == "verifier"),
        "merges_rejected_by_rule": sum(1 for p, r in rejected.items() if p.startswith("P") and r["by"] == "rule"),
        "variant_merges_proposed": len(rlog["proposed"]) - n_prop_cases,
        "variants_merged": sum(len(v["merged"]) for v in rlog["variant_merges"]),
        "conflicts_found": len(rlog["conflicts"]),
        "conflicts_settled": Counter(c["rule"] for c in rlog["conflicts"]),
        "conflicts_proposed_by_model": len(rlog["conflicts_proposed"]),
        "clusters": rlog.get("clusters", {}),
        "hpo_resolution": hpo_stats,
        "genes": {k: gene_decisions[k] for k in ("candidates", "confirmed", "not_confirmed", "dropped")},
        "inheritance": inheritance["chosen"],
    }
    log.info("[%s] reconciled: %d -> %d individuals, %d merges", seed.mim or seed.title,
             before_totals["individuals"], after_totals["individuals"], len(table.merged))
    return entry
