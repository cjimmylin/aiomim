"""The "case table first" strategy, offline: scripted model, stubbed ontology services.

Pins down the guard rails and the arithmetic: a record whose quote is not in the
paper never reaches the writer; counts pool across papers (whole-group features,
"n of m" counts, explicit absences); the same variant named two ways is one row;
the inheritance rule; paragraphs citing unknown ids are dropped; synopsis items
carry individual counts.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import extract
from aiomim.config import get_settings
from aiomim.models import Paper, Seed, VariantMention
from aiomim.strategies import cohort

A_TEXT = (
    "We describe a consanguineous Turkish family in which three affected sibs had childhood-onset generalized "
    "dystonia. Optic atrophy was present in two of the three sibs. None of the sibs had seizures. "
    "Exome sequencing identified a homozygous c.100C>T (p.Arg34Trp) variant in GENEX that segregated with the disease."
)
B_TEXT = (
    "A 9-year-old girl presented with dystonia and seizures. Fundoscopy showed no optic atrophy. "
    "She carried the homozygous R34W mutation in GENEX. "
    "In patient fibroblasts, GENEX protein levels were reduced to 30% of control."
)
PAPER_A = Paper(pmid="111", title="Dystonia in a Turkish family", authors=["Kaya A", "Demir B", "Ozturk C"],
                year=2001, journal="J Neurol", abstract=A_TEXT)
PAPER_B = Paper(pmid="222", title="GENEX dystonia", authors=["Smith J", "Jones K"], year=2005,
                journal="Neurology", abstract=B_TEXT)
SEED = Seed(mim="600000", prefix="#", title="DYSTONIA WITH OPTIC ATROPHY", symbol="DYTOA")


@dataclass
class _Hit:
    id: str
    label: str
    score: float = 1.0
    matched_text: str = ""


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy", "HP:0001250": "Seizure", "HP:0001251": "Ataxia"}

    def exact(self, text):
        return next((i for i, label in self.terms.items() if label.lower() == text.lower()), None)

    def search(self, text, k=10):
        return [_Hit(i, label) for i, label in self.terms.items() if text.split()[0].lower() in label.lower()][:k]

    def label(self, hpo_id):
        return self.terms.get(hpo_id, "")

    def is_phenotype(self, hpo_id):
        return hpo_id in self.terms

    def parents(self, hpo_id):
        return []

    def ancestors(self, hpo_id, include_self=True):
        return frozenset({hpo_id} if include_self else set())

    def category(self, hpo_id):
        return "Head & Neck: Eyes" if hpo_id == "HP:0000648" else "Neurologic"


@dataclass
class _Gene:
    symbol: str
    omim_id: str
    location: str


@pytest.fixture(autouse=True)
def stub_services(monkeypatch):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: FakeHPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    hgnc_module.normalize_symbol = lambda s: s.upper()
    hgnc_module.gene_info = lambda s: _Gene("GENEX", "612345", "15q21.1") if s.upper() == "GENEX" else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


def _ph(text, label, present=True, n_with=None, n_assessed=None, some_only=False, other_cause=False):
    return cohort.XCasePhenotype(text=text, hpo_label=label, present=present, n_with=n_with,
                                 n_assessed=n_assessed, some_only=some_only, other_cause=other_cause)


def _var(as_reported, cdna="", protein="", zygosity="homozygous", origin="inherited", gene="GENEX",
         conclusion="causal"):
    return cohort.XCaseVariant(gene=gene, as_reported=as_reported, cdna=cdna, protein=protein, genomic="",
                               zygosity=zygosity, origin=origin, consequence="missense",
                               authors_conclusion=conclusion)


def _rec(label, kind, n, phenotypes, variants, quote, inheritance="UNKNOWN", **kw):
    fields = dict(label=label, kind=kind, family="", n_affected=n, n_families=1, sex="", ancestry="",
                  consanguinity="not_stated", onset="", age_last="", phenotypes=phenotypes, variants=variants,
                  segregation="", inheritance=inheritance, previously_reported="", mixed_genotypes=False,
                  quotes=[quote])
    fields.update(kw)
    return cohort.XRecord(**fields)


class ScriptedLLM:
    def __init__(self):
        self.settings = get_settings()
        self.calls: list[tuple[str, str]] = []

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    def _XCases(self, prompt):
        if "PMID 111" in prompt:
            return cohort.XCases(relevance="primary", relevance_reason="first report", records=[
                _rec("Family 1", "family", 3,
                     [_ph("generalized dystonia", "Dystonia"),
                      _ph("optic atrophy", "Optic atrophy", n_with=2, n_assessed=3),
                      _ph("seizures", "Seizure", present=False)],
                     [_var("c.100C>T (p.Arg34Trp)", cdna="c.100C>T", protein="p.Arg34Trp"),
                      # Dismissed by the authors: must not make GENEW a causal gene.
                      _var("c.5A>G", cdna="c.5A>G", zygosity="heterozygous", gene="GENEW", conclusion="not_causal")],
                     "three affected sibs had childhood-onset generalized dystonia",
                     consanguinity="yes", ancestry="Turkish", inheritance="AR"),
                # Invented: not in the abstract, so this record must be set aside.
                _rec("Patient 7", "individual", 1, [_ph("ataxia", "Ataxia")], [],
                     "A seventh patient developed cerebellar ataxia at age 40 years."),
            ], notes=[])
        return cohort.XCases(relevance="supporting", relevance_reason="further case", records=[
            _rec("Patient", "individual", 1,
                 [_ph("dystonia", "Dystonia"), _ph("seizures", "Seizure"),
                  _ph("ataxia from drug toxicity", "Ataxia", other_cause=True),   # not counted
                  _ph("optic atrophy", "Optic atrophy", present=False)],
                 [_var("R34W"),
                  # A candidate the writer will not confirm: its gene must stay out of relationships.
                  _var("c.77G>A", cdna="c.77G>A", gene="GENEV", zygosity="heterozygous", conclusion="uncertain")],
                 "A 9-year-old girl presented with dystonia and seizures.", sex="female"),
        ], notes=[cohort.XNote(section="pathogenesis", inheritance="UNKNOWN",
                               statement="Smith and Jones (2005) found GENEX protein reduced to 30% of control.",
                               quotes=["GENEX protein levels were reduced to 30% of control"])])

    def _XChoices(self, prompt):
        return extract.XChoices(choices=[])

    def _CEntry(self, prompt):
        P = cohort.CParagraph
        return cohort.CEntry(
            intro=P(text="A number sign (#) is used with this entry because of evidence that DYTOA is caused by "
                         "homozygous mutation in the GENEX gene (612345) on chromosome 15q21.",
                    evidence_ids=["R:111:1", "R:222:1"]),
            sections=[
                cohort.CSection(name="clinical_features", paragraphs=[
                    P(text="Kaya et al. (2001) described 3 sibs of a consanguineous Turkish family with dystonia.",
                      evidence_ids=["R:111:1"]),
                    P(text="A seventh patient had ataxia.", evidence_ids=["R:111:2"]),     # dropped record
                    P(text="Brown et al. (1999) described the disorder first.", evidence_ids=["R:999:1"]),
                ]),
                cohort.CSection(name="pathogenesis", paragraphs=[
                    P(text="Smith and Jones (2005) found GENEX protein reduced to 30% of control.",
                      evidence_ids=["N:222:1"])]),
            ],
            relationships=[
                cohort.CRelationship(gene_symbol="genex", record_ids=["R:111:1", "R:222:1"]),
                cohort.CRelationship(gene_symbol="GENEQ", record_ids=["R:111:1"]),        # not a candidate
                cohort.CRelationship(gene_symbol="GENEV", record_ids=["R:111:1"]),        # no record carries it there
            ],
            allelic_variants=[
                cohort.CAllelicVariant(variant_id="V1", name="GENEX, ARG34TRP", phenotype="Dystonia with optic atrophy",
                                       paragraphs=[P(text="In 3 sibs, Kaya et al. (2001) found a homozygous "
                                                          "c.100C-T transition.", evidence_ids=["R:111:1"])]),
                cohort.CAllelicVariant(variant_id="V9", name="GENEX, MADEUP", phenotype="x",
                                       paragraphs=[P(text="Invented.", evidence_ids=["R:111:1"])]),
            ],
        )


@pytest.fixture
def run(tmp_path):
    llm = ScriptedLLM()
    entry = cohort.run(SEED, [PAPER_A, PAPER_B], llm, tmp_path)
    table = json.loads((tmp_path / "cohort.json").read_text())
    return entry, table, llm


def test_record_with_invented_quote_is_set_aside(run):
    entry, table, llm = run
    assert [r["id"] for r in table["dropped"]["records"]] == ["R:111:2"]
    assert entry.meta["cohort"]["records_dropped_ungrounded"] == 1
    prompt = next(p for stage, p in llm.calls if stage == "synthesize")
    assert "[R:111:1]" in prompt and "[N:222:1]" in prompt
    assert "R:111:2" not in prompt and "cerebellar ataxia" not in prompt.lower()
    assert "seventh" not in entry.plain_text()


def test_counts_pool_across_papers(run):
    _, table, _ = run
    assert table["totals"]["individuals"] == 4 and table["totals"]["families"] == 2
    ph = table["phenotypes"]
    assert (ph["HP:0001332"]["present"], ph["HP:0001332"]["absent"], ph["HP:0001332"]["assessed"]) == (4, 0, 4)
    # "2 of 3" in paper A (the third sib is assessed, not explicitly without it), explicitly absent in paper B.
    assert (ph["HP:0000648"]["present"], ph["HP:0000648"]["absent"], ph["HP:0000648"]["assessed"]) == (2, 1, 4)
    assert not any(r["label"] == "Ataxia" for r in ph.values())     # attributed to another cause
    # Absent in all 3 sibs, present in the girl.
    assert (ph["HP:0001250"]["present"], ph["HP:0001250"]["absent"]) == (1, 3)


def test_same_variant_named_two_ways_is_one_row(run):
    entry, table, _ = run
    assert len(table["variants"]) == 3              # the GENEX change named two ways, GENEW, GENEV
    row = table["variants"][0]
    assert row["id"] == "V1" and row["records"] == ["R:111:1", "R:222:1"] and row["individuals"] == 4
    assert set(row["keys"]) == {"c.100C>T", "p.R34W"}
    assert [av.name for av in entry.allelic_variants] == ["GENEX, ARG34TRP"]


def test_structured_parts_come_from_the_table(run):
    entry, _, _ = run
    assert entry.inheritance == ["AR"]
    assert [r.gene_symbol for r in entry.relationships] == ["GENEX"]     # GENEW was dismissed by its authors
    rel = entry.relationships[0]
    assert (rel.gene_symbol, rel.gene_mim, rel.inheritance, rel.pmids) == ("GENEX", "612345", ["AR"], ["111", "222"])
    synopsis = {i.hpo_id: (i.n_present, i.n_assessed, i.n_papers, i.category) for i in entry.clinical_synopsis}
    assert synopsis == {"HP:0001332": (4, 4, 2, "Neurologic"), "HP:0000648": (2, 4, 2, "Head & Neck: Eyes")}
    assert "HP:0001250" not in synopsis         # more individuals without it than with it


def test_paragraphs_without_valid_ids_are_dropped(run):
    entry, _, _ = run
    text = entry.plain_text()
    assert "Brown" not in text and "seventh" not in text and "Invented" not in text
    assert len([d for d in entry.meta["dropped_ungrounded"] if not d.startswith("relationship")]) == 3
    assert entry.sections[0].paragraphs[0].pmids == ["111"]
    assert [s.name for s in entry.sections] == ["clinical_features", "pathogenesis"]
    assert entry.intro.pmids == ["111", "222"]
    assert [r.pmid for r in entry.references] == ["111", "222"]


def _record(variants, inheritance="UNKNOWN", n=1, kind="family", rid="R:1:1"):
    return cohort.CaseRecord(id=rid, pmid=rid.split(":")[1], kind=kind, n_affected=n,
                             variants=[VariantMention(**v) for v in variants], inheritance=inheritance)


def test_transcript_ids_do_not_merge_variants():
    a = VariantMention(gene="GENEX", as_reported="NM_001256545.2:c.2096G>C", cdna="NM_001256545.2:c.2096G>C")
    b = VariantMention(gene="GENEX", as_reported="(NM_001256545.2): c.352T>C")
    from aiomim.kg import variant_keys
    assert variant_keys(cohort._without_transcript(a)) == {"c.2096G>C"}
    assert variant_keys(cohort._without_transcript(b)) == {"c.352T>C"}


def test_inheritance_rule():
    ar = _record([{"gene": "GENEX", "as_reported": "c.1A>G", "zygosity": "compound_heterozygous"}])
    assert cohort.record_mode(ar)[0] == "AR"
    two_het = _record([{"gene": "GENEX", "key": "V1", "zygosity": "heterozygous"},
                       {"gene": "GENEX", "key": "V2", "zygosity": "heterozygous"}])
    assert cohort.record_mode(two_het)[0] == "AR"
    de_novo = _record([{"gene": "GENEY", "as_reported": "c.5C>T", "zygosity": "heterozygous", "origin": "de_novo"}])
    assert cohort.record_mode(de_novo) == ("AD", "heterozygous de novo variant")
    mito = _record([{"gene": "MT-ND6", "as_reported": "m.14459G>A", "zygosity": "heteroplasmic"}], inheritance="AD")
    assert cohort.record_mode(mito)[0] == "MT"
    xl = _record([{"gene": "GENEZ", "as_reported": "c.9G>A", "zygosity": "heterozygous"}])
    assert cohort.record_mode(xl, {"GENEZ"})[0] == "XL"
    mixed = _record([{"gene": "GENEX", "key": "V1", "zygosity": "heterozygous"},
                     {"gene": "GENEX", "key": "V2", "zygosity": "heterozygous"}])
    mixed.mixed_genotypes = True          # two members, one variant each: not two alleles of one person
    assert cohort.record_mode(mixed)[0] == ""
    lone_het = _record([{"gene": "GENEX", "as_reported": "c.1A>G", "zygosity": "heterozygous"}])
    assert cohort.record_mode(lone_het)[0] == ""

    # Selection: a minor mode is reported only with real support.
    support = {"AR": {"individuals": 10, "records": ["a", "b", "c"]}, "AD": {"individuals": 1, "records": ["d"]}}
    assert cohort.choose_modes(support) == ["AR"]
    support["AD"] = {"individuals": 4, "records": ["d", "e"]}
    assert cohort.choose_modes(support) == ["AR", "AD"]


def test_group_feature_counts():
    whole = cohort.CasePhenotype(text="x")
    some = cohort.CasePhenotype(text="x", some_only=True)
    counted = cohort.CasePhenotype(text="x", n_with=2, n_assessed=5)
    absent = cohort.CasePhenotype(text="x", present=False)
    assert cohort._tally_feature(whole, 6) == (6, 0, 6)
    assert cohort._tally_feature(some, 6) == (1, 0, 6)       # "some": a lower bound, never the whole group
    assert cohort._tally_feature(counted, 6) == (2, 0, 5)
    assert cohort._tally_feature(absent, 6) == (0, 6, 6)


def test_follow_up_records_are_not_counted_twice():
    def rec(rid, label, hpo_ids, previously=""):
        return cohort.CaseRecord(id=rid, pmid=rid.split(":")[1], label=label, kind="family", n_affected=3,
                                 previously_reported=previously,
                                 phenotypes=[cohort.CasePhenotype(text=h, hpo_id=h, hpo_label=h) for h in hpo_ids])
    cases = [
        cohort.PaperCases(pmid="111", relevance="primary", records=[rec("R:111:1", "Family 1", ["HP:0001332"])]),
        cohort.PaperCases(pmid="222", relevance="primary", records=[
            rec("R:222:1", "Family 1", ["HP:0001332", "HP:0001250"], previously="Kaya et al., 2001")]),
    ]
    table = cohort.CaseTable(SEED, {"111": PAPER_A, "222": PAPER_B}, cases, normalize_gene=str.upper)
    assert table.records["R:222:1"].followup_of == "111"
    assert table.totals()["individuals"] == 3 and table.totals()["follow_up_records"] == 1
    ph = table.phenotype_table()
    assert ph["HP:0001332"]["present"] == 3 and ph["HP:0001332"]["pmids"] == ["111", "222"]
    assert ph["HP:0001250"]["present"] == 3 and ph["HP:0001250"].get("from_follow_up")   # only the follow-up has it


def test_writer_confirms_causal_genes_from_the_candidates(run):
    entry, table, llm = run
    genes = entry.meta["cohort"]["genes"]
    assert genes["candidates"] == ["GENEX", "GENEV"]            # GENEW was dismissed by its authors
    assert genes["confirmed"] == ["GENEX"] and genes["not_confirmed"] == ["GENEV"]
    assert {d["gene"]: d["reason"] for d in genes["dropped"]} == {"GENEQ": "not a candidate",
                                                                  "GENEV": "no valid record id"}
    assert [r.gene_symbol for r in entry.relationships] == ["GENEX"]
    assert entry.inheritance == ["AR"] and table["inheritance"]["genes"] == ["GENEX"]
    prompt = next(p for stage, p in llm.calls if stage == "synthesize")
    assert "CANDIDATE CAUSAL GENES" in prompt and "- GENEV:" in prompt
