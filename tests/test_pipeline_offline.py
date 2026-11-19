"""End-to-end run of stages 3-6 with a scripted model and stubbed ontology services.

No network and no model calls. The point is to pin down the guard rails: what
happens to a finding whose quote is not in the paper, to a paragraph that cites
no finding, to an audit verdict resting on a quote that is not in the paper, and
to a paragraph the audit flags.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import extract, synthesize, verify
from aiomim.config import get_settings
from aiomim.models import Paper, Seed
from aiomim.pipeline import RunConfig, build_entries

ABSTRACT = (
    "We studied a large Hispanic family with maternally inherited Leber optic atrophy and dystonia. "
    "Eight affected members had childhood-onset generalized dystonia with bilateral striatal lesions on imaging. "
    "Sequencing of mitochondrial DNA identified a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 "
    "gene, changing alanine 72 to valine. The mutation was absent from 310 controls."
)
PAPER = Paper(pmid="111", title="A mitochondrial ND6 mutation in optic atrophy and dystonia",
              authors=["Jun AS", "Brown MD", "Wallace DC"], year=1994, journal="Proc Natl Acad Sci U S A",
              abstract=ABSTRACT)
SEED = Seed(mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", symbol="LDYT")


# --------------------------------------------------------------------------- #
# Stubs for the ontology and nomenclature services
# --------------------------------------------------------------------------- #


@dataclass
class _Hit:
    id: str
    label: str
    score: float = 1.0
    matched_text: str = ""


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy", "HP:0012638": "Abnormal nervous system physiology"}
    parents_of = {"HP:0001332": ["HP:0012638"], "HP:0000648": ["HP:0000118"], "HP:0012638": ["HP:0000118"]}

    def exact(self, text):
        return next((i for i, label in self.terms.items() if label.lower() == text.lower()), None)

    def search(self, text, k=10):
        return [_Hit(i, label) for i, label in self.terms.items() if text.split()[0].lower() in label.lower()][:k]

    def label(self, hpo_id):
        return self.terms.get(hpo_id, "")

    def is_phenotype(self, hpo_id):
        return hpo_id in self.terms

    def resolve(self, hpo_id):
        return hpo_id if hpo_id in self.terms else None

    def parents(self, hpo_id):
        return self.parents_of.get(hpo_id, [])

    def ancestors(self, hpo_id, include_self=True):
        out, frontier = ({hpo_id} if include_self else set()), list(self.parents(hpo_id))
        while frontier:
            term = frontier.pop()
            out.add(term)
            frontier.extend(self.parents(term))
        return frozenset(out)

    def category(self, hpo_id):
        return "Neurologic" if hpo_id != "HP:0000648" else "Head & Neck: Eyes"

    def information_content(self, hpo_id):
        return 1.0


@dataclass
class _Gene:
    symbol: str
    omim_id: str
    location: str


@pytest.fixture(autouse=True)
def stub_services(monkeypatch, tmp_path):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: FakeHPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    aliases = {"ND6": "MT-ND6", "MTND6": "MT-ND6", "MT-ND6": "MT-ND6"}
    hgnc_module.normalize_symbol = lambda s: aliases.get(s.upper(), s.upper())
    hgnc_module.gene_info = lambda s: _Gene("MT-ND6", "516006", "mitochondria") if s.upper() in aliases else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


# --------------------------------------------------------------------------- #
# A scripted model
# --------------------------------------------------------------------------- #


class ScriptedLLM:
    """Returns canned replies by output type and records what it was asked."""

    def __init__(self):
        self.settings = get_settings()
        self.calls: list[tuple[str, str]] = []
        self.audit_rounds = 0

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    def _XExtraction(self, prompt):
        variant = extract.XVariant(gene="ND6", as_reported="G14459A", cdna="", protein="A72V", genomic="",
                                   zygosity="heteroplasmic", origin="inherited", consequence="missense")

        def finding(section, statement, quote, variants=(), phenotypes=(), inheritance="UNKNOWN"):
            return extract.XFinding(section=section, statement=statement, quotes=[quote], genes=["ND6"],
                                    variants=list(variants), phenotypes=list(phenotypes), inheritance=inheritance,
                                    n_affected=None, n_families=1, population="Hispanic")

        dystonia = extract.XPhenotype(text="generalized dystonia", hpo_label="Dystonia", present=True,
                                      frequency="8/8", onset="childhood")
        return extract.XExtraction(relevance="primary", relevance_reason="first report", study_types=["family study"], findings=[
            finding("clinical_features", "Jun et al. (1994) studied a large Hispanic family with dystonia.",
                    "Eight affected members had childhood-onset generalized dystonia with bilateral striatal lesions on imaging.",
                    phenotypes=[dystonia], inheritance="MT"),
            finding("molecular_genetics", "Jun et al. (1994) identified a heteroplasmic 14459G-A transition in ND6.",
                    "identified a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 gene",
                    variants=[variant], inheritance="MT"),
            # Invented: the quote is nowhere in the abstract, so this finding must be dropped.
            finding("biochemical_features", "Jun et al. (1994) found complex I activity reduced to 20% in muscle.",
                    "Complex I activity in skeletal muscle mitochondria was reduced to 20% of control values."),
        ])

    def _XChoices(self, prompt):
        return extract.XChoices(choices=[])

    def _XEntry(self, prompt):
        P = synthesize.XParagraph
        return synthesize.XEntry(
            intro=P(text="A number sign (#) is used with this entry because LDYT is caused by mutation in the "
                         "MT-ND6 gene (516006).", finding_ids=["111:2"]),
            sections=[synthesize.XSection(name="clinical_features", paragraphs=[
                P(text="Jun et al. (1994) studied a large Hispanic family in which 8 members had childhood-onset "
                       "dystonia. Twelve members were blind.", finding_ids=["111:1"]),
                # Cites a finding that does not exist: must be discarded.
                P(text="Novotny et al. (1986) described the same kindred.", finding_ids=["999:1"]),
                # Cites nothing at all: must be discarded.
                P(text="The disorder is thought to affect 1 in 50,000 people.", finding_ids=[]),
            ])],
            relationships=[synthesize.XRelationship(gene_symbol="ND6", inheritance=["MT"], finding_ids=["111:2"])],
            allelic_variants=[
                synthesize.XAllelicVariant(variant_id="variant:MT-ND6:m.14459G>A", name="MTND6, ALA72VAL",
                                           phenotype="Leber optic atrophy and dystonia", paragraphs=[
                    P(text="In a Hispanic family, Jun et al. (1994) identified a heteroplasmic 14459G-A transition.",
                      finding_ids=["111:2"])]),
                synthesize.XAllelicVariant(variant_id="variant:MADE:UP", name="X", phenotype="Y", paragraphs=[
                    P(text="An invented variant.", finding_ids=["111:2"])]),
            ],
        )

    def _XClaimSets(self, prompt):
        A = verify.XAttributedClaim
        table = {
            "intro": [A(text="LDYT is caused by mutation in MT-ND6", pmids=["111"])],
            "clinical_features.1": [A(text="8 members of the family had childhood-onset dystonia", pmids=["111"]),
                                    A(text="Twelve members of the family were blind", pmids=["111"])],
            "av0001.1": [A(text="Jun et al. (1994) identified a heteroplasmic 14459G-A transition",
                           pmids=["not-a-cited-pmid"])],   # bad attribution falls back to the cited paper
        }
        if "Twelve" not in prompt:   # the repaired paragraph no longer makes that claim
            table["clinical_features.1"].pop()
        return verify.XClaimSets(paragraphs=[
            verify.XParagraphClaims(paragraph_id=pid, claims=claims)
            for pid, claims in table.items() if f'id="{pid}"' in prompt
        ])

    def _XAudit(self, prompt):
        self.audit_rounds += 1
        V = verify.XVerdict
        real = "Eight affected members had childhood-onset generalized dystonia"
        verdicts = []
        if "[clinical_features.1#1]" in prompt:
            verdicts.append(V(claim_id="clinical_features.1#1", verdict="supported", evidence_quote=real, explanation=""))
        if "[clinical_features.1#2]" in prompt:
            verdicts.append(V(claim_id="clinical_features.1#2", verdict="unsupported", evidence_quote="",
                              explanation="not stated"))
        if "[intro#1]" in prompt:
            # "Supported" on the strength of a quote that is not in the paper.
            verdicts.append(V(claim_id="intro#1", verdict="supported", explanation="",
                              evidence_quote="We conclude that the ND6 mutation is the sole cause of the disease in all families."))
        if "[av0001.1#1]" in prompt:
            verdicts.append(V(claim_id="av0001.1#1", verdict="supported", explanation="",
                              evidence_quote="a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 gene"))
        verdicts.append(V(claim_id="no-such-claim#9", verdict="contradicted", evidence_quote="", explanation="ignored"))
        return verify.XAudit(verdicts=verdicts)

    def _XRevisions(self, prompt):
        return verify.XRevisions(paragraphs=[verify.XRevision(
            paragraph_id="clinical_features.1",
            text="Jun et al. (1994) studied a large Hispanic family in which 8 members had childhood-onset dystonia.")])


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


@pytest.fixture
def run(tmp_path):
    llm = ScriptedLLM()
    entries, extractions = build_entries(SEED, [PAPER], RunConfig(strategies=("kg",)), llm, tmp_path)
    return entries["kg"], extractions[0], llm, tmp_path


def test_finding_with_invented_quote_never_reaches_the_graph(run):
    entry, extraction, _, _ = run
    assert [f.id for f in extraction.findings] == ["111:1", "111:2"]
    assert [f.id for f in extraction.dropped_findings] == ["111:3"]
    assert entry.meta["extraction"]["findings_dropped_ungrounded"] == 1
    assert "complex I" not in entry.plain_text()


def test_writer_never_sees_the_dropped_finding(run):
    _, _, llm, _ = run
    prompt = next(p for stage, p in llm.calls if stage == "synthesize" and "<evidence>" in p)
    assert "[111:1]" in prompt and "[111:2]" in prompt
    assert "111:3" not in prompt and "20%" not in prompt


def test_paragraphs_without_valid_findings_are_discarded(run):
    entry, _, _, _ = run
    text = entry.plain_text()
    assert "Novotny" not in text and "1 in 50,000" not in text and "invented variant" not in text
    assert len(entry.meta["dropped_ungrounded"]) == 3
    assert [av.name for av in entry.allelic_variants] == ["MTND6, ALA72VAL"]


def test_structured_fields_come_from_the_graph(run):
    entry, _, _, _ = run
    rel = entry.relationships[0]
    assert (rel.gene_symbol, rel.gene_mim, rel.inheritance, rel.pmids) == ("MT-ND6", "516006", ["MT"], ["111"])
    assert entry.inheritance == ["MT"]
    assert [(i.hpo_id, i.category, i.pmids) for i in entry.clinical_synopsis] == [("HP:0001332", "Neurologic", ["111"])]
    assert entry.allelic_variants[0].hgvs == ["m.14459G>A", "p.A72V"]
    assert [r.pmid for r in entry.references] == ["111"]


def test_audit_downgrades_a_verdict_whose_quote_is_not_in_the_paper(run):
    entry, _, _, _ = run
    check = entry.intro.checks[0]
    assert check.verdict == "partially_supported"
    assert "not found verbatim" in check.explanation
    assert entry.intro.status == "partial"


def test_flagged_paragraph_is_repaired_and_reaudited(run):
    entry, _, llm, _ = run
    para = entry.sections[0].paragraphs[0]
    assert "Twelve members were blind" not in para.text
    assert para.status == "supported"
    assert entry.meta["audit_before_repair"]["unsupported"] == 1
    assert entry.meta["repair"] == {"flagged": 1, "revised": 1, "deleted": 0}
    assert llm.audit_rounds == 2                      # one paper, audited once and re-audited after repair
    assert [c.verdict for c in para.checks] == ["supported"]
    assert entry.meta["audit"].get("unsupported", 0) == 0


def test_outputs_are_written(run):
    _, _, _, out_dir = run
    for name in ("extractions.json", "kg.json", "kg_triples.tsv", "entry.kg.json", "entry.kg.md"):
        assert (out_dir / name).exists(), name
    markdown = (out_dir / "entry.kg.md").read_text()
    assert "LEBER OPTIC ATROPHY AND DYSTONIA; LDYT" in markdown and "MTND6, ALA72VAL" in markdown
