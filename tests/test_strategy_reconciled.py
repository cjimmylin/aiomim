"""The "reconciled case database" strategy and the case-database scoring, offline.

Scripted model, stubbed ontology services. Pins down: a re-reported family is
merged and counted once; an unrelated patient with the same variant stays
separate when the verifier rejects; an accepted merge whose evidence quote is not
in any paper is refused by rule; conflicting values are settled by the stated
rule and logged; variant rows merge within one gene only; the frequency-agreement
arithmetic; the pooled export.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import casebase, extract
from aiomim.config import get_settings
from aiomim.models import Paper, Seed, VariantMention
from aiomim.strategies import cohort, reconciled

A_TEXT = (
    "We describe a consanguineous Turkish family in which three affected sibs had childhood-onset generalized "
    "dystonia. Optic atrophy was present in two of the three sibs. None of the sibs had seizures. "
    "Exome sequencing identified a homozygous c.100C>T (p.Arg34Trp) variant in GENEX that segregated with the disease."
)
B_TEXT = (
    "We re-examined the consanguineous Turkish family previously reported by Kaya et al. (2001). "
    "The three affected sibs had onset of dystonia in infancy. One of the three sibs had seizures. "
    "Optic atrophy was present in all three sibs. The sibs were homozygous for the R34W mutation in GENEX."
)
C_TEXT = "A 7-year-old Pakistani girl had generalized dystonia. She was homozygous for the R34W mutation in GENEX."
PAPER_A = Paper(pmid="111", title="Dystonia in a Turkish family", authors=["Kaya A", "Demir B", "Ozturk C"],
                year=2001, journal="J Neurol", abstract=A_TEXT)
PAPER_B = Paper(pmid="222", title="Follow-up of GENEX dystonia", authors=["Smith J", "Kaya A"], year=2005,
                journal="Neurology", abstract=B_TEXT)
PAPER_C = Paper(pmid="333", title="GENEX dystonia in Pakistan", authors=["Lee K", "Khan M"], year=2006,
                journal="Mov Disord", abstract=C_TEXT)
SEED = Seed(mim="600000", prefix="#", title="DYSTONIA WITH OPTIC ATROPHY", symbol="DYTOA")


@dataclass
class _Hit:
    id: str
    label: str
    score: float = 1.0
    matched_text: str = ""


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy", "HP:0001250": "Seizure"}

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


def _ph(text, label, present=True, n_with=None, n_assessed=None):
    return cohort.XCasePhenotype(text=text, hpo_label=label, present=present, n_with=n_with,
                                 n_assessed=n_assessed, some_only=False, other_cause=False)


def _var(as_reported, cdna="", protein=""):
    return cohort.XCaseVariant(gene="GENEX", as_reported=as_reported, cdna=cdna, protein=protein, genomic="",
                               zygosity="homozygous", origin="inherited", consequence="missense",
                               authors_conclusion="causal")


def _rec(label, kind, n, phenotypes, variants, quote, **kw):
    fields = dict(label=label, kind=kind, family="", n_affected=n, n_families=1, sex="", ancestry="Turkish",
                  consanguinity="yes", onset="", age_last="", phenotypes=phenotypes, variants=variants,
                  segregation="", inheritance="AR", previously_reported="", mixed_genotypes=False, quotes=[quote])
    fields.update(kw)
    return cohort.XRecord(**fields)


TRUE_EVIDENCE = "We re-examined the consanguineous Turkish family previously reported by Kaya et al. (2001)."


class ScriptedLLM:
    def __init__(self):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str]] = []

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, system, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    def _XCases(self, prompt):
        if "PMID 111" in prompt:
            return cohort.XCases(relevance="primary", relevance_reason="", notes=[], records=[
                _rec("Family 1", "family", 3,
                     [_ph("generalized dystonia", "Dystonia"),
                      _ph("optic atrophy", "Optic atrophy", n_with=2, n_assessed=3),
                      _ph("seizures", "Seizure", present=False)],
                     [_var("c.100C>T (p.Arg34Trp)", cdna="c.100C>T", protein="p.Arg34Trp")],
                     "three affected sibs had childhood-onset generalized dystonia", onset="childhood")])
        if "PMID 222" in prompt:
            return cohort.XCases(relevance="supporting", relevance_reason="", notes=[], records=[
                _rec("Turkish family", "family", 3,
                     [_ph("dystonia", "Dystonia"), _ph("optic atrophy", "Optic atrophy"),
                      _ph("seizures", "Seizure", n_with=1, n_assessed=3)],
                     [_var("R34W")], "The three affected sibs had onset of dystonia in infancy.", onset="infancy")])
        return cohort.XCases(relevance="supporting", relevance_reason="", notes=[], records=[
            _rec("Patient", "individual", 1, [_ph("generalized dystonia", "Dystonia")], [_var("R34W")],
                 "A 7-year-old Pakistani girl had generalized dystonia.", sex="female", ancestry="Pakistani",
                 consanguinity="not_stated")])

    def _XChoices(self, prompt):
        return extract.XChoices(choices=[])

    def _XProposals(self, prompt):
        E = reconciled.XEvidence
        return reconciled.XProposals(
            same_cases=[
                reconciled.XSameCase(record_ids=["R:111:1", "R:222:1"], relation="same_family",
                                     reason="re-examined family", evidence=[E(pmid="222", quote=TRUE_EVIDENCE)]),
                reconciled.XSameCase(record_ids=["R:333:1", "R:111:1"], relation="included_in_group",
                                     reason="SIMILARITY-ONLY-REASON",
                                     evidence=[E(pmid="333", quote="She was homozygous for the R34W mutation in GENEX.")]),
                reconciled.XSameCase(record_ids=["R:333:1", "R:222:1"], relation="same_individual",
                                     reason="invented", evidence=[E(pmid="333", quote="The girl was one of the Turkish sibs.")]),
            ],
            same_variants=[],
            conflicts=[reconciled.XConflict(record_ids=["R:111:1", "R:222:1"], field="onset",
                                            values=["childhood", "infancy"], note="")])

    def _XDecisions(self, prompt):
        D = reconciled.XDecision
        return reconciled.XDecisions(decisions=[
            D(proposal_id="P1", accept=True, reason="the later paper says it re-examined the family"),
            D(proposal_id="P2", accept=False, reason="only the same variant"),
            D(proposal_id="P3", accept=True, reason="accepted, but its quote is invented"),
        ])

    def _CEntry(self, prompt):
        P = cohort.CParagraph
        return cohort.CEntry(
            intro=P(text="A number sign (#) is used with this entry because DYTOA is caused by homozygous mutation "
                         "in the GENEX gene (612345).", evidence_ids=["R:111:1"]),
            sections=[cohort.CSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 Turkish sibs with dystonia.", evidence_ids=["R:111:1"]),
                P(text="Lee et al. (2006) described a Pakistani girl with dystonia.", evidence_ids=["R:333:1"])])],
            relationships=[cohort.CRelationship(gene_symbol="GENEX", record_ids=["R:111:1", "R:333:1"])],
            allelic_variants=[])


@pytest.fixture
def run(tmp_path):
    llm = ScriptedLLM()
    out = tmp_path / "run" / "600000"
    entry = reconciled.run(SEED, [PAPER_A, PAPER_B, PAPER_C], llm, out)
    return entry, json.loads((out / "casebase.json").read_text()), llm, out


def test_rereported_family_is_merged_and_counted_once(run):
    entry, base, _, _ = run
    assert base["totals"]["before"]["individuals"] == 7 and base["totals"]["before"]["families"] == 3
    assert base["totals"]["after"]["individuals"] == 4 and base["totals"]["after"]["families"] == 2
    assert base["log"]["clusters"] == {"C:1": ["R:111:1", "R:222:1"]}
    unit = next(u for u in base["units"] if u["id"] == "C:1")
    assert unit["sources"] == ["R:111:1", "R:222:1"] and unit["pmids"] == ["111", "222"] and unit["n_affected"] == 3
    meta = entry.meta["reconciled"]
    assert (meta["records_before"], meta["records_after"]) == (3, 2)
    assert (meta["merges_proposed"], meta["merges_accepted"]) == (3, 1)
    # The variant is counted over reconciled units: 3 sibs + 1 girl, not 7.
    assert [(v["id"], v["individuals"]) for v in base["variants"]] == [("V1", 4)]


def test_same_variant_unrelated_patient_stays_separate(run):
    entry, base, _, _ = run
    rejected = {r["proposal_id"]: r for r in base["log"]["rejected"]}
    assert rejected["P2"]["by"] == "verifier"
    assert rejected["P3"] == {"proposal_id": "P3", "by": "rule",
                              "reason": "no evidence quote found verbatim in a supplied paper"}
    assert any(u["id"] == "R:333:1" and u["sources"] == ["R:333:1"] for u in base["units"])
    assert entry.meta["reconciled"]["merges_rejected_by_verifier"] == 1
    assert entry.meta["reconciled"]["merges_rejected_by_rule"] == 1


def test_verifier_is_independent_of_the_proposer(run):
    _, _, llm, _ = run
    verify_prompt = next(p for stage, system, p in llm.calls if system == reconciled.VERIFY_SYSTEM)
    assert "SIMILARITY-ONLY-REASON" not in verify_prompt
    assert "NOT FOUND in the papers" in verify_prompt and "found in PMID 222" in verify_prompt


def test_conflicts_are_settled_by_rule_and_logged(run):
    _, base, _, _ = run
    conflicts = {c["field"]: c for c in base["log"]["conflicts"]}
    assert conflicts["onset"]["kept"] == "childhood"                     # the original report wins
    assert "original" in conflicts["onset"]["rule"]
    assert conflicts["Seizure present/absent"]["kept"] == "present"
    after, before = base["phenotypes"]["after"], base["phenotypes"]["before"]
    assert (before["HP:0001332"]["present"], after["HP:0001332"]["present"]) == (7, 4)
    assert sorted(after["HP:0001332"]["pmids"]) == ["111", "222", "333"]       # every reporting paper still supports it
    assert (after["HP:0000648"]["present"], after["HP:0000648"]["assessed"]) == (3, 3)
    assert (before["HP:0001250"]["present"], before["HP:0001250"]["absent"]) == (1, 3)
    assert (after["HP:0001250"]["present"], after["HP:0001250"]["absent"]) == (1, 0)


def test_entry_is_rendered_from_the_reconciled_table(run):
    entry, _, llm, _ = run
    prompt = next(p for stage, system, p in llm.calls if stage == "synthesize")
    assert "4 affected individuals, 2 families" in prompt
    assert "reconciled: same patients as R:222:1" in prompt
    assert [r.gene_symbol for r in entry.relationships] == ["GENEX"] and entry.inheritance == ["AR"]
    synopsis = {i.hpo_id: (i.n_present, i.n_assessed) for i in entry.clinical_synopsis}
    assert synopsis["HP:0001332"] == (4, 4)


def test_variant_rows_merge_within_one_gene_only():
    def rec(rid, gene, name):
        return cohort.CaseRecord(id=rid, pmid=rid.split(":")[1], kind="individual",
                                 variants=[VariantMention(gene=gene, as_reported=name, zygosity="homozygous")])
    cases = [cohort.PaperCases(pmid="111", relevance="primary", records=[rec("R:111:1", "GENEX", "IVS3+1G>A")]),
             cohort.PaperCases(pmid="222", relevance="primary", records=[rec("R:222:1", "GENEX", "c.250+1G>A"),
                                                                         rec("R:222:2", "GENEY", "c.9del")])]
    table = reconciled.ReconciledTable(SEED, {"111": PAPER_A, "222": PAPER_B}, cases, normalize_gene=str.upper)
    assert len(table.variants) == 3
    cross = {"type": "same_variant", "variant_ids": ["V2", "V3"], "evidence": [{"found_in": "222"}]}
    assert reconciled._rule_refusal(cross, table) == "variants in different genes"
    table.apply([], [{"variant_ids": ["V1", "V2"]}])
    assert [r["id"] for r in table.variants] == ["V1", "V3"]
    assert table.records["R:222:1"].variants[0].key == "V1"
    assert table.variants[0]["individuals"] == 2


def test_frequency_agreement_arithmetic():
    gold = {"hpo_annotations": [
        {"hpo_id": "HP:1", "aspect": "P", "frequency": "3/4"},
        {"hpo_id": "HP:2", "aspect": "P", "frequency": "2/4"},
        {"hpo_id": "HP:3", "aspect": "P", "frequency": "HP:0040281"},     # a frequency term, not a fraction
        {"hpo_id": "HP:4", "aspect": "P", "frequency": "1/2"},            # not in the table
        {"hpo_id": "HP:5", "aspect": "P", "frequency": "1/3"},
        {"hpo_id": "HP:5", "aspect": "P", "frequency": "1/1"},            # two references: summed to 2/4
    ]}
    table = {"HP:1": {"present": 3, "assessed": 4}, "HP:2": {"present": 1, "assessed": 2},
             "HP:3": {"present": 2, "assessed": 5}, "HP:5": {"present": 1, "assessed": 4}}
    freq = casebase.gold_frequencies(gold)
    assert freq == {"HP:1": (3, 4), "HP:2": (2, 4), "HP:4": (1, 2), "HP:5": (2, 4)}
    a = casebase.frequency_agreement(table, freq)
    assert a["n_compared"] == 3
    assert a["denominator_agreement"] == round(2 / 3, 3)                # HP:1 and HP:5
    assert a["fraction_agreement"] == round(2 / 3, 3)                   # HP:1, and HP:2 (1/2 = 2/4)
    assert a["count_agreement"] == round(1 / 3, 3)
    assert a["mean_abs_diff"] == round((0 + 0 + 0.25) / 3, 4)


def test_export(run):
    _, _, _, out = run
    run_dir = out.parent
    (out / "gold.json").write_text(json.dumps({"title": "TEST", "hpo_annotations": [
        {"hpo_id": "HP:0001332", "aspect": "P", "frequency": "4/4"},
        {"hpo_id": "HP:0000648", "aspect": "P", "frequency": "2/3"}]}))
    summary = casebase.build_casebase(run_dir, "reconciled")
    row = summary["entries"][0]
    # After: dystonia 4/4 (agrees), optic atrophy 3/3 against 2/3 (same denominator, different fraction).
    assert row["reconciled"]["n_compared"] == 2 and row["reconciled"]["fraction_agreement"] == 0.5
    assert row["reconciled"]["denominator_agreement"] == 1.0
    # Before: 7/7 and 5/6, counting the re-reported sibs twice: no denominator agrees.
    assert row["reconciled"]["before_reconciliation"]["denominator_agreement"] == 0.0
    assert row["reconciled"]["individuals_before"] == 7 and row["reconciled"]["individuals"] == 4
    individuals = (run_dir / "casebase" / "individuals.tsv").read_text().splitlines()
    assert len(individuals) == 3 and individuals[0].startswith("mim\tid\tkind")
    phenotypes = (run_dir / "casebase" / "phenotypes.tsv").read_text()
    assert "HP:0001332" in phenotypes and "\t4/4\t" in phenotypes
    assert (run_dir / "casebase" / "variants.tsv").exists() and (run_dir / "casebase" / "summary.md").exists()


def test_planted_rereport_copies_records():
    case = cohort.PaperCases(pmid="111", relevance="primary", records=[
        cohort.CaseRecord(id="R:111:1", pmid="111", label="Family 1", kind="family", n_affected=3)])
    fake, copied, pairs = casebase.plant_rereport([PAPER_A, PAPER_B], [case], "111")
    assert fake.year == 2007 and "previously described by Kaya et al. (2001)" in fake.abstract
    assert pairs == [("R:111:1", f"R:{fake.pmid}:1")]
    assert copied.records[0].label == "Case A" and case.records[0].label == "Family 1"
