"""The matched ablations of the two extract-then-write strategies (review, section 3, issue 2).

Offline: a scripted model and stubbed ontology services. Two things are pinned
down:

1. The existing strategies send exactly the prompts they sent before the
   ablations were added. Every call the evidence graph, the case table and direct
   reading make here (stage, system prompt, user prompt and reply schema) is
   hashed, and the hash is compared with one recorded on the code before the
   change. A changed byte would make every cached reply of earlier runs miss.
2. The four new strategies: which stage the per-paper extraction runs at, that
   the writer chooses the synopsis terms (and, for the case table, the
   inheritance) through ontology search, what the hybrid writer is shown, which
   paragraphs survive, and that failed papers and stopped writers are recorded.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import extract, synthesize
from aiomim.config import get_settings
from aiomim.llm import LLMRefusal, schema_for
from aiomim.models import Paper, Seed
from aiomim.strategies import cohort, run_strategy

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
B_FULL = ("Introduction. " + B_TEXT + " Methods. Fibroblasts were cultured from a skin biopsy. " * 60
          + "Results. Spasticity of the legs was noted at age 12 years.")
PAPER_A = Paper(pmid="111", title="Dystonia in a Turkish family", authors=["Kaya A", "Demir B", "Ozturk C"],
                year=2001, journal="J Neurol", abstract=A_TEXT)
PAPER_B = Paper(pmid="222", title="GENEX dystonia", authors=["Smith J", "Jones K"], year=2005,
                journal="Neurology", abstract=B_TEXT, fulltext=B_FULL)
PAPERS = [PAPER_A, PAPER_B]
SEED = Seed(mim="600000", prefix="#", title="DYSTONIA WITH OPTIC ATROPHY", symbol="DYTOA")


@dataclass
class _Hit:
    id: str
    label: str
    score: float = 1.0
    matched_text: str = ""


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy", "HP:0001250": "Seizure",
             "HP:0001251": "Ataxia", "HP:0001257": "Spasticity", "HP:0002650": "Generalized dystonia"}

    def exact(self, text):
        return next((i for i, label in self.terms.items() if label.lower() == text.lower()), None)

    def search(self, text, k=10):
        word = text.split()[0].lower() if text.split() else ""
        return [_Hit(i, label) for i, label in self.terms.items() if word and word[:5] in label.lower()][:k]

    def label(self, hpo_id):
        return self.terms.get(hpo_id, "")

    def is_phenotype(self, hpo_id):
        return hpo_id in self.terms

    def parents(self, hpo_id):
        return ["HP:0001332"] if hpo_id == "HP:0002650" else []

    def ancestors(self, hpo_id, include_self=True):
        out = {hpo_id} if include_self else set()
        return frozenset(out | set(self.parents(hpo_id)))

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


# --------------------------------------------------------------------------- #
# A scripted model that answers every stage of every strategy compared here
# --------------------------------------------------------------------------- #


def _xph(text, label, present=True, frequency=""):
    return extract.XPhenotype(text=text, hpo_label=label, present=present, frequency=frequency, onset="")


def _xvar(as_reported, cdna="", protein=""):
    return extract.XVariant(gene="GENEX", as_reported=as_reported, cdna=cdna, protein=protein, genomic="",
                            zygosity="homozygous", origin="inherited", consequence="missense")


def _xf(section, statement, quote, variants=(), phenotypes=(), inheritance="UNKNOWN"):
    return extract.XFinding(section=section, statement=statement, quotes=[quote], genes=["GENEX"],
                            variants=list(variants), phenotypes=list(phenotypes), inheritance=inheritance,
                            n_affected=3, n_families=1, population="Turkish")


def _cph(text, label, present=True, n_with=None, n_assessed=None):
    return cohort.XCasePhenotype(text=text, hpo_label=label, present=present, n_with=n_with,
                                 n_assessed=n_assessed, some_only=False, other_cause=False)


def _cvar(as_reported, cdna="", protein="", zygosity="homozygous"):
    return cohort.XCaseVariant(gene="GENEX", as_reported=as_reported, cdna=cdna, protein=protein, genomic="",
                               zygosity=zygosity, origin="inherited", consequence="missense",
                               authors_conclusion="causal")


def _rec(label, kind, n, phenotypes, variants, quote, inheritance="UNKNOWN"):
    return cohort.XRecord(label=label, kind=kind, family="", n_affected=n, n_families=1, sex="", ancestry="",
                          consanguinity="yes", onset="", age_last="", phenotypes=phenotypes, variants=variants,
                          segregation="", inheritance=inheritance, previously_reported="", mixed_genotypes=False,
                          quotes=[quote])


class ScriptedLLM:
    """Canned replies by reply type; records every call as it was sent."""

    def __init__(self, fail_pmids=(), stop_writer=False):
        self.settings = get_settings()
        self.calls: list[dict] = []
        self.fail_pmids = set(fail_pmids)
        self.stop_writer = stop_writer
        self.accepts: list[object] = []

    def call(self, stage, system, prompt, output, **kw):
        self.calls.append({"stage": stage, "system": system, "prompt": prompt,
                           "schema": json.dumps(schema_for(output), sort_keys=True)})
        if stage in ("synthesize",):
            self.accepts.append(kw.get("accept"))
            if self.stop_writer:
                raise LLMRefusal("the model's safety filter stopped this reply")
        if any(f"PMID {p}." in prompt for p in self.fail_pmids) and stage not in ("synthesize", "normalize"):
            raise RuntimeError("extraction failed")
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        out = []
        for p in prompts:
            try:
                out.append(self.call(stage, system, p, output))
            except Exception as exc:  # noqa: BLE001 - as LLM.map does
                out.append(exc)
        return out

    # -- per-paper extraction --------------------------------------------- #

    def _XExtraction(self, prompt):
        if "PMID 111" in prompt:
            return extract.XExtraction(relevance="primary", relevance_reason="first", study_types=["family study"],
                                       findings=[
                _xf("clinical_features", "Kaya et al. (2001) described 3 Turkish sibs with dystonia.",
                    "three affected sibs had childhood-onset generalized dystonia",
                    phenotypes=[_xph("generalized dystonia", "Generalized dystonia", frequency="3/3"),
                                _xph("optic atrophy", "Optic atrophy", frequency="2/3"),
                                _xph("seizures", "Seizure", present=False)], inheritance="AR"),
                _xf("molecular_genetics", "Kaya et al. (2001) found a homozygous c.100C>T variant in GENEX.",
                    "identified a homozygous c.100C>T (p.Arg34Trp) variant in GENEX",
                    variants=[_xvar("c.100C>T (p.Arg34Trp)", "c.100C>T", "p.Arg34Trp")], inheritance="AR"),
            ])
        return extract.XExtraction(relevance="supporting", relevance_reason="case", study_types=["case report"],
                                   findings=[
            _xf("clinical_features", "Smith and Jones (2005) described a girl with dystonia and seizures.",
                "A 9-year-old girl presented with dystonia and seizures.",
                phenotypes=[_xph("dystonia", "Dystonia"), _xph("fits", "Seizures"),
                            _xph("optic atrophy", "Optic atrophy", present=False)]),
            _xf("molecular_genetics", "Smith and Jones (2005) found the homozygous R34W mutation.",
                "She carried the homozygous R34W mutation in GENEX.", variants=[_xvar("R34W", protein="R34W")]),
        ])

    def _XCases(self, prompt):
        if "PMID 111" in prompt:
            return cohort.XCases(relevance="primary", relevance_reason="first", records=[
                _rec("Family 1", "family", 3,
                     [_cph("generalized dystonia", "Generalized dystonia"),
                      _cph("optic atrophy", "Optic atrophy", n_with=2, n_assessed=3),
                      _cph("seizures", "Seizure", present=False)],
                     [_cvar("c.100C>T (p.Arg34Trp)", "c.100C>T", "p.Arg34Trp")],
                     "three affected sibs had childhood-onset generalized dystonia", inheritance="AR"),
            ], notes=[])
        return cohort.XCases(relevance="supporting", relevance_reason="case", records=[
            _rec("Patient", "individual", 1, [_cph("dystonia", "Dystonia"), _cph("fits", "Seizures")],
                 [_cvar("R34W", protein="R34W")], "A 9-year-old girl presented with dystonia and seizures."),
        ], notes=[cohort.XNote(section="pathogenesis", inheritance="UNKNOWN",
                               statement="Smith and Jones (2005) found GENEX protein reduced to 30% of control.",
                               quotes=["GENEX protein levels were reduced to 30% of control"])])

    def _XChoices(self, prompt):
        # Pick the first candidate offered for each phrase.
        choices, n = [], None
        for line in prompt.splitlines():
            if line[:1].isdigit() and ". " in line:
                n = int(line.split(".", 1)[0])
            elif n is not None and line.strip().startswith("HP:"):
                choices.append(extract.XChoice(n=n, hpo_id=line.split()[0]))
                n = None
        return extract.XChoices(choices=choices)

    # -- writers ----------------------------------------------------------- #

    def _XEntry(self, prompt):
        P = synthesize.XParagraph
        return synthesize.XEntry(
            intro=P(text="A number sign (#) is used with this entry because DYTOA is caused by homozygous mutation "
                         "in the GENEX gene (612345).", finding_ids=["111:2"]),
            sections=[synthesize.XSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 Turkish sibs with dystonia.", finding_ids=["111:1"])])],
            relationships=[synthesize.XRelationship(gene_symbol="GENEX", inheritance=["AR"], finding_ids=["111:2"])],
            allelic_variants=[])

    def _KMEntry(self, prompt):
        from aiomim.strategies import kg_matched as km

        P = synthesize.XParagraph
        return km.KMEntry(
            intro=P(text="A number sign (#) is used with this entry because DYTOA is caused by homozygous mutation "
                         "in the GENEX gene (612345).", finding_ids=["111:2"]),
            sections=[synthesize.XSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 Turkish sibs with dystonia.", finding_ids=["111:1"]),
                P(text="Nobody described this.", finding_ids=["999:9"])])],
            relationships=[synthesize.XRelationship(gene_symbol="GENEX", inheritance=["AR"], finding_ids=["111:2"])],
            allelic_variants=[],
            clinical_synopsis=[
                km.KMSynopsisItem(feature="generalized dystonia", hpo_label="Generalized dystonia",
                                  finding_ids=["111:1"]),
                km.KMSynopsisItem(feature="seizures", hpo_label="Seizure", finding_ids=["222:1"]),
            ])

    def _KHEntry(self, prompt):
        from aiomim.strategies import kg_matched as km

        P = km.HParagraph
        return km.KHEntry(
            intro=P(text="A number sign (#) is used with this entry because DYTOA is caused by homozygous mutation "
                         "in the GENEX gene (612345).", pmids=["111"], finding_ids=["111:2"]),
            sections=[km.HSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 Turkish sibs with dystonia.", pmids=[], finding_ids=["111:1"]),
                # Read in the text, with no finding behind it: kept, because it cites a supplied paper.
                P(text="Smith and Jones (2005) noted spasticity of the legs at age 12 years.", pmids=["222"],
                  finding_ids=[]),
                P(text="An uncited paragraph.", pmids=["999"], finding_ids=["999:9"])])],
            relationships=[km.HRelationship(gene_symbol="GENEX", inheritance=["AR"], pmids=["111"],
                                            finding_ids=[])],
            allelic_variants=[
                km.HAllelicVariant(variant_id="", gene_symbol="GENEX", name="GENEX, ARG34TRP",
                                   hgvs=["c.100C>T", "p.Arg34Trp"], phenotype="Dystonia",
                                   paragraphs=[P(text="Kaya et al. (2001) found c.100C-T.", pmids=["111"],
                                                 finding_ids=[])])],
            clinical_synopsis=[
                km.HSynopsisItem(feature="spasticity", hpo_label="Spasticity", pmids=["222"]),
                km.HSynopsisItem(feature="generalized dystonia", hpo_label="Generalized dystonia", pmids=["111"]),
            ])

    def _CEntry(self, prompt):
        P = cohort.CParagraph
        return cohort.CEntry(
            intro=P(text="A number sign (#) is used with this entry because of evidence that DYTOA is caused by "
                         "homozygous mutation in the GENEX gene (612345).", evidence_ids=["R:111:1"]),
            sections=[cohort.CSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 sibs of a consanguineous Turkish family.",
                  evidence_ids=["R:111:1"])])],
            relationships=[cohort.CRelationship(gene_symbol="GENEX", record_ids=["R:111:1", "R:222:1"])],
            allelic_variants=[])

    def _CMEntry(self, prompt):
        from aiomim.strategies import cohort_matched as cm

        P = cohort.CParagraph
        return cm.CMEntry(
            intro=P(text="A number sign (#) is used with this entry because of evidence that DYTOA is caused by "
                         "homozygous mutation in the GENEX gene (612345).", evidence_ids=["R:111:1"]),
            sections=[cohort.CSection(name="clinical_features", paragraphs=[
                P(text="Kaya et al. (2001) described 3 sibs of a consanguineous Turkish family.",
                  evidence_ids=["R:111:1"])])],
            relationships=[cm.CMRelationship(gene_symbol="GENEX", inheritance=["AR"],
                                             record_ids=["R:111:1", "R:222:1"]),
                           cm.CMRelationship(gene_symbol="GENEQ", inheritance=["AD"], record_ids=["R:111:1"])],
            allelic_variants=[],
            inheritance=["AR"],
            clinical_synopsis=[
                cm.CMSynopsisItem(feature="generalized dystonia", hpo_label="Generalized dystonia",
                                  evidence_ids=["R:111:1"]),
                cm.CMSynopsisItem(feature="optic atrophy", hpo_label="Optic atrophy", evidence_ids=["R:111:1"]),
            ])

    def _CHEntry(self, prompt):
        from aiomim.strategies import cohort_matched as cm

        P = cm.CHParagraph
        return cm.CHEntry(
            intro=P(text="A number sign (#) is used with this entry because of evidence that DYTOA is caused by "
                         "homozygous mutation in the GENEX gene (612345).", pmids=["111"], evidence_ids=[]),
            sections=[cm.CHSection(name="clinical_features", paragraphs=[
                P(text="Smith and Jones (2005) noted spasticity of the legs at age 12 years.", pmids=["222"],
                  evidence_ids=[]),
                P(text="Nobody.", pmids=[], evidence_ids=["R:999:1"])])],
            relationships=[cm.CMRelationship(gene_symbol="GENEX", inheritance=["AR"], record_ids=["R:111:1"])],
            allelic_variants=[cm.CHAllelicVariant(variant_id="V1", gene_symbol="GENEX", name="GENEX, ARG34TRP",
                                                  hgvs=[], phenotype="Dystonia",
                                                  paragraphs=[P(text="Kaya et al. (2001) found c.100C-T.",
                                                                pmids=["111"], evidence_ids=["R:111:1"])])],
            inheritance=["AR"],
            clinical_synopsis=[cm.HSynopsisItem(feature="spasticity", hpo_label="Spasticity", pmids=["222"])])

    def _DEntry(self, prompt):
        D = synthesize
        return D.DEntry(
            intro=D.DParagraph(text="A number sign (#) is used with this entry because DYTOA is caused by mutation "
                                    "in GENEX.", pmids=["111"]),
            sections=[D.DSection(name="clinical_features", paragraphs=[
                D.DParagraph(text="Kaya et al. (2001) described 3 sibs.", pmids=["111"])])],
            relationships=[D.DRelationship(gene_symbol="GENEX", inheritance=["AR"], pmids=["111"])],
            allelic_variants=[],
            clinical_synopsis=[D.DSynopsisItem(feature="dystonia", hpo_label="Dystonia", pmids=["111", "222"]),
                               D.DSynopsisItem(feature="fits", hpo_label="Seizures", pmids=["222"])])


def _digest(calls: list[dict]) -> str:
    h = hashlib.sha256()
    for c in calls:
        for part in (c["stage"], c["system"], c["prompt"], c["schema"]):
            h.update(part.encode())
            h.update(b"\x00")
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 1. The existing strategies' prompts are unchanged
# --------------------------------------------------------------------------- #

# Recorded on commit 525bc46, before the ablation strategies were implemented:
# sha256 over (stage, system, prompt, schema) of every call, in order.
BEFORE = {
    "kg": "ccea6955649aed87f39458671f7d3806a44d3fc27ebb96b2cf03c55e6a0f7637",
    "cohort": "76aecdfa6c6b41065fcee391919125ac03fb678ce23b84a86f831cc6217c3f94",
    "direct": "f58b9d33fc5a2b1d61d3099db0b8804dd5f20ad94a10b63c457a09b0ed3f75ab",
}


@pytest.mark.parametrize("strategy", sorted(BEFORE))
def test_existing_strategies_send_byte_identical_prompts(strategy, tmp_path):
    llm = ScriptedLLM()
    run_strategy(strategy, SEED, PAPERS, llm, tmp_path)
    assert llm.calls, "the strategy made no calls"
    assert _digest(llm.calls) == BEFORE[strategy], (_digest(llm.calls), [(c["stage"], len(c["prompt"])) for c in llm.calls])


def test_direct_reading_lays_out_the_papers_as_before():
    blocks, truncated = synthesize.paper_blocks(PAPERS)
    assert truncated == [] and [b.split('"')[1] for b in blocks] == ["111", "222"]
    assert blocks[1].startswith('<paper pmid="222" label="Smith and Jones (2005)" available="fulltext">\n')


# --------------------------------------------------------------------------- #
# 2. The new strategies
# --------------------------------------------------------------------------- #

NEW = ("kg_matched", "kg_hybrid", "cohort_matched", "cohort_hybrid")


def _run(strategy, tmp_path, **kw):
    llm = ScriptedLLM(**kw)
    entry = run_strategy(strategy, SEED, PAPERS, llm, tmp_path)
    return entry, llm


def _writer(llm):
    calls = [c for c in llm.calls if c["stage"] == "synthesize"]
    assert len(calls) == 1
    return calls[0]


@pytest.mark.parametrize("base,variant,stage", [("kg", "kg_matched", "extract_matched"),
                                                ("kg", "kg_hybrid", "extract_matched"),
                                                ("cohort", "cohort_matched", "cases_matched"),
                                                ("cohort", "cohort_hybrid", "cases_matched")])
def test_extraction_is_the_same_prompts_at_the_matched_stage(base, variant, stage, tmp_path):
    _, base_llm = _run(base, tmp_path / "a")
    _, var_llm = _run(variant, tmp_path / "b")
    base_calls = [c for c in base_llm.calls if c["stage"] == base_llm.calls[0]["stage"]]
    var_calls = [c for c in var_llm.calls if c["stage"] == stage]
    assert len(var_calls) == len(PAPERS)
    assert [(c["system"], c["prompt"], c["schema"]) for c in var_calls] == \
        [(c["system"], c["prompt"], c["schema"]) for c in base_calls]
    settings = get_settings()
    assert settings.effort_for(stage) == settings.effort_for("synthesize") == "high"


def test_kg_matched_writer_sees_only_the_graph_and_chooses_the_synopsis(tmp_path):
    entry, llm = _run("kg_matched", tmp_path)
    writer = _writer(llm)
    assert writer["system"].startswith(synthesize.KG_SYSTEM) and "`clinical_synopsis`" in writer["system"]
    assert "<paper " not in writer["prompt"] and "<evidence>" in writer["prompt"]
    assert llm.accepts == [synthesize.has_content]
    # The writer's phrases, mapped through the ontology, not the graph's rule.
    assert {(i.hpo_id, tuple(i.pmids)) for i in entry.clinical_synopsis} == \
        {("HP:0002650", ("111",)), ("HP:0001250", ("222",))}
    assert entry.meta["synopsis"]["chosen_by"] == "writer"
    # Paragraphs still need findings.
    assert all(p.finding_ids for p in entry.all_paragraphs())
    assert any("Nobody described this" in d for d in entry.meta["dropped_ungrounded"])
    assert entry.inheritance == ["AR"]
    assert entry.meta["extraction"]["stage"] == "extract_matched" and entry.meta["extraction"]["papers_failed"] == []
    assert (tmp_path / "kg.kg_matched.json").exists() and not (tmp_path / "kg.json").exists()


def test_kg_hybrid_writer_reads_the_papers_as_direct_reading_does(tmp_path):
    entry, llm = _run("kg_hybrid", tmp_path)
    writer = _writer(llm)
    blocks, _ = synthesize.paper_blocks(PAPERS)
    assert "\n\n".join(blocks) in writer["prompt"]
    assert writer["prompt"].index("<paper ") < writer["prompt"].index("<evidence>")
    assert llm.accepts == [synthesize.has_content]
    texts = {p.text: p for p in entry.all_paragraphs()}
    # Written from the text alone, citing a supplied paper: kept.
    spast = texts["Smith and Jones (2005) noted spasticity of the legs at age 12 years."]
    assert spast.pmids == ["222"] and spast.finding_ids == []
    # Cites a finding only: kept, with the finding's paper.
    assert texts["Kaya et al. (2001) described 3 Turkish sibs with dystonia."].pmids == ["111"]
    assert "An uncited paragraph." not in texts
    av = entry.allelic_variants[0]
    assert av.gene_symbol == "GENEX" and av.hgvs == ["c.100C>T", "p.Arg34Trp"]
    assert {i.hpo_id for i in entry.clinical_synopsis} == {"HP:0001257", "HP:0002650"}
    assert [r.gene_symbol for r in entry.relationships] == ["GENEX"]


def test_cohort_matched_writer_chooses_synopsis_and_inheritance(tmp_path):
    entry, llm = _run("cohort_matched", tmp_path)
    writer = _writer(llm)
    assert "<paper " not in writer["prompt"]
    assert "- called:" not in writer["prompt"] and "GENOTYPE PATTERNS" in writer["prompt"]
    assert "CLINICAL FEATURES (pooled individuals present / assessed; absent)" in writer["prompt"]
    assert "computed from the patients' genotypes and is given" not in writer["system"]
    assert llm.accepts == [synthesize.has_content]
    assert entry.inheritance == ["AR"] and entry.relationships[0].inheritance == ["AR"]
    assert [r.gene_symbol for r in entry.relationships] == ["GENEX"]       # GENEQ is not a candidate
    synopsis = {i.hpo_id: i for i in entry.clinical_synopsis}
    assert set(synopsis) == {"HP:0002650", "HP:0000648"}                    # the writer's two, not the rule's
    assert (synopsis["HP:0000648"].n_present, synopsis["HP:0000648"].n_assessed) == (2, 3)
    assert entry.meta["inheritance_choice"]["chosen_by"] == "writer"
    assert entry.meta["cohort"]["stage"] == "cases_matched" and entry.meta["cohort"]["papers_failed"] == []
    assert (tmp_path / "cohort.cohort_matched.json").exists() and not (tmp_path / "cohort.json").exists()


def test_cohort_hybrid_writer_reads_the_papers(tmp_path):
    entry, llm = _run("cohort_hybrid", tmp_path)
    writer = _writer(llm)
    blocks, _ = synthesize.paper_blocks(PAPERS)
    assert "\n\n".join(blocks) in writer["prompt"] and "<case_table>" in writer["prompt"]
    texts = {p.text: p for p in entry.all_paragraphs()}
    assert texts["Smith and Jones (2005) noted spasticity of the legs at age 12 years."].pmids == ["222"]
    assert "Nobody." not in texts
    assert entry.allelic_variants[0].hgvs and entry.allelic_variants[0].gene_symbol == "GENEX"
    assert [i.hpo_id for i in entry.clinical_synopsis] == ["HP:0001257"]
    assert entry.inheritance == ["AR"]


@pytest.mark.parametrize("strategy,record", [("kg_matched", "extraction"), ("kg_hybrid", "extraction"),
                                             ("cohort_matched", "cohort"), ("cohort_hybrid", "cohort")])
def test_a_failed_paper_is_recorded(strategy, record, tmp_path):
    entry, _ = _run(strategy, tmp_path, fail_pmids=["222"])
    assert entry.meta[record]["papers_failed"] == ["222"]


@pytest.mark.parametrize("strategy", NEW)
def test_a_stopped_writer_is_recorded_not_retried(strategy, tmp_path):
    from aiomim.pipeline import RunConfig, build_entries

    llm = ScriptedLLM(stop_writer=True)
    with pytest.raises(LLMRefusal):
        run_strategy(strategy, SEED, PAPERS, llm, tmp_path / "a")
    assert sum(c["stage"] == "synthesize" for c in llm.calls) == 1
    llm = ScriptedLLM(stop_writer=True)
    entries, _ = build_entries(SEED, PAPERS, RunConfig(strategies=(strategy,), evaluate=False), llm, tmp_path / "b")
    assert entries[strategy].meta["stopped"]
