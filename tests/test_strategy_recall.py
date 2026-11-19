"""The memory-only control (`closedbook`) and recall-then-verify (`recall`), offline.

A scripted model stands in for Claude: it writes a memory draft with one citation
to a supplied paper, one to a paper that was not supplied and one uncited
paragraph, and an auditor that judges claims by keyword against the abstract.
No network and no model calls.
"""

from __future__ import annotations

import re
import sys
import types

import pytest

from aiomim import synthesize, verify
from aiomim.config import get_settings
from aiomim.models import Paper, Seed
from aiomim.pipeline import RunConfig, build_entries
from aiomim.strategies import closedbook, recall

from test_pipeline_offline import ABSTRACT, PAPER, SEED, FakeHPO, _Gene  # noqa: F401 - shared fixtures

OTHER = Paper(pmid="222", title="Follow-up of a family with optic atrophy", authors=["Smith AB", "Lee C"],
              year=2001, journal="Ophthalmology",
              abstract="We report long-term ophthalmologic follow-up of a family with optic atrophy.")
PAPERS = [PAPER, OTHER]

HETERO_QUOTE = "a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 gene"
DYSTONIA_QUOTE = "Eight affected members had childhood-onset generalized dystonia"


@pytest.fixture(autouse=True)
def stub_services(monkeypatch):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: FakeHPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    aliases = {"ND6": "MT-ND6", "MTND6": "MT-ND6", "MT-ND6": "MT-ND6"}
    hgnc_module.normalize_symbol = lambda s: aliases.get(s.upper(), s.upper())
    hgnc_module.gene_info = lambda s: _Gene("MT-ND6", "516006", "mitochondria") if s.upper() in aliases else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


_PARAGRAPH = re.compile(r'<paragraph id="([^"]+)">\n(.*?)\n</paragraph>', re.S)
_CLAIM = re.compile(r"^\[([^\]]+#\d+)\] (.*)$", re.M)


class ScriptedLLM:
    def __init__(self):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str]] = []

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, system, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    # The memory draft ------------------------------------------------------ #
    def _DEntry(self, prompt):
        P = synthesize.DParagraph
        return synthesize.DEntry(
            intro=P(text="A number sign (#) is used with this entry because LDYT is caused by mutation in the "
                         "MT-ND6 gene.", pmids=[]),
            sections=[
                synthesize.DSection(name="clinical_features", paragraphs=[
                    P(text="Jun et al. (1994) described a Hispanic family in which 8 members had childhood-onset "
                           "dystonia. Twelve members were blind.", pmids=[]),
                    P(text="Novotny et al. (1986) described the same kindred.", pmids=["99999999"]),
                ]),
                synthesize.DSection(name="molecular_genetics", paragraphs=[
                    P(text="Jun et al. (1994) found a homozygous 14459G-A transition in the ND6 gene.", pmids=[]),
                ]),
            ],
            relationships=[synthesize.DRelationship(gene_symbol="ND6", inheritance=["MT"], pmids=[])],
            allelic_variants=[],
            clinical_synopsis=[synthesize.DSynopsisItem(feature="dystonia", hpo_label="Dystonia", pmids=[])],
        )

    # The audit: claims are sentences; verdicts by keyword ------------------- #
    def _XClaimSets(self, prompt):
        out = []
        for pid, text in _PARAGRAPH.findall(prompt):
            sentences = [s for s in re.split(r"(?<=\.)\s+(?=[A-Z])", text) if s]
            out.append(verify.XParagraphClaims(
                paragraph_id=pid, claims=[verify.XAttributedClaim(text=s, pmids=[]) for s in sentences]))
        return verify.XClaimSets(paragraphs=out)

    def _XAudit(self, prompt):
        V = verify.XVerdict
        on_jun = "PMID 111" in prompt.split("\n", 1)[0]
        verdicts = []
        for claim_id, text in _CLAIM.findall(prompt):
            if not on_jun or "Twelve" in text or "Novotny" in text:
                verdicts.append(V(claim_id=claim_id, verdict="unsupported", evidence_quote="", explanation="not stated"))
            elif "homozygous" in text:
                verdicts.append(V(claim_id=claim_id, verdict="contradicted", evidence_quote=HETERO_QUOTE,
                                  explanation="the paper reports a heteroplasmic, not homozygous, change"))
            elif "dystonia" in text:
                verdicts.append(V(claim_id=claim_id, verdict="supported", evidence_quote=DYSTONIA_QUOTE, explanation=""))
            elif "ND6" in text or "14459" in text:
                verdicts.append(V(claim_id=claim_id, verdict="supported", evidence_quote=HETERO_QUOTE, explanation=""))
            else:
                verdicts.append(V(claim_id=claim_id, verdict="unsupported", evidence_quote="", explanation="not stated"))
        return verify.XAudit(verdicts=verdicts)

    def _XRevisions(self, prompt):
        return verify.XRevisions(paragraphs=[])

    def _XChoices(self, prompt):
        from aiomim import extract
        return extract.XChoices(choices=[])

    # The rewrite from the audit -------------------------------------------- #
    def _RecallDraft(self, prompt):
        P = synthesize.DParagraph
        return recall.RecallDraft(
            intro=P(text="A number sign (#) is used with this entry because LDYT is caused by mutation in the "
                         "MT-ND6 gene (516006) on mitochondria.", pmids=["111"]),
            sections=[
                synthesize.DSection(name="clinical_features", paragraphs=[
                    P(text="Jun et al. (1994) described a Hispanic family in which 8 members had childhood-onset "
                           "dystonia.", pmids=["111"]),
                    # Survives the rewrite but names no paper: must be dropped.
                    P(text="The disorder is maternally transmitted.", pmids=[]),
                ]),
                synthesize.DSection(name="molecular_genetics", paragraphs=[
                    P(text="Jun et al. (1994) found a heteroplasmic 14459G-A transition in the ND6 gene.",
                      pmids=["111"]),
                ]),
            ],
            relationships=[synthesize.DRelationship(gene_symbol="ND6", inheritance=["MT"], pmids=["111"])],
            allelic_variants=[],
            clinical_synopsis=[synthesize.DSynopsisItem(feature="dystonia", hpo_label="Dystonia", pmids=["111"])],
            omitted_claims=["clinical_features.1#2", "clinical_features.2#1", "no-such#1"],
        )


# --------------------------------------------------------------------------- #
# closedbook
# --------------------------------------------------------------------------- #


def test_closedbook_prompt_holds_no_paper_material(tmp_path):
    llm = ScriptedLLM()
    closedbook.run(SEED, PAPERS, llm, tmp_path)
    (stage, system, prompt), = [c for c in llm.calls if c[0] == "recall"]
    for text in (prompt, system):   # the house-style examples in the system prompt do name "Jun et al."
        assert "111" not in text and "222" not in text
        assert "14459" not in text and "Hispanic" not in text and "Reference data from HGNC" not in text
    assert "Jun" not in prompt and "Smith" not in prompt and "follow-up" not in prompt
    assert "LEBER OPTIC ATROPHY AND DYSTONIA" in prompt and "500001" in prompt


def test_closedbook_citations_are_mapped_and_uncited_paragraphs_checked_against_all(tmp_path):
    entry = closedbook.run(SEED, PAPERS, ScriptedLLM(), tmp_path)
    cf, mg = entry.sections
    assert cf.paragraphs[0].pmids == ["111"]               # "Jun et al. (1994)" matched a supplied paper
    assert mg.paragraphs[0].pmids == ["111"]
    assert cf.paragraphs[1].pmids == ["111", "222"]        # cites an unsupplied paper: checked against all
    assert entry.intro.pmids == ["111", "222"]             # cites nothing: checked against all
    assert entry.meta["unknown_citations"] == ["Novotny et al. (1986)"]
    meta = entry.meta["closedbook"]
    assert meta["paragraphs"] == 4
    assert meta["paragraphs_citing_supplied_papers"] == 2
    assert meta["paragraphs_checked_against_all_papers"] == 2
    assert meta["citations_matched"] == ["Jun et al. (1994)"]
    assert meta["citations_unmatched"] == ["Novotny et al. (1986)"]
    assert meta["pmids_offered"] == 1 and meta["pmids_offered_matching_supplied"] == 0
    assert (meta["supplied_papers"], meta["supplied_papers_cited"]) == (2, 1)
    assert meta["reference_recall_from_memory"] == 0.5
    # Uncited relationships survive in the control (keep_uncited).
    assert [r.gene_symbol for r in entry.relationships] == ["MT-ND6"]


# --------------------------------------------------------------------------- #
# recall
# --------------------------------------------------------------------------- #


@pytest.fixture
def recalled(tmp_path):
    llm = ScriptedLLM()
    return recall.run(SEED, PAPERS, llm, tmp_path), llm, tmp_path


def test_rewriter_sees_the_audit_but_not_the_papers(recalled):
    _, llm, out_dir = recalled
    (_, _, prompt), = [c for c in llm.calls if c[0] == "synthesize"]
    assert "CONTRADICTED" in prompt and HETERO_QUOTE in prompt and "heteroplasmic, not homozygous" in prompt
    assert "UNSUPPORTED" in prompt and "PMID 111 = Jun et al. (1994)" in prompt
    assert "MT-ND6: MIM number 516006" in prompt          # HGNC data for the gene that survived
    assert "310 controls" not in prompt                   # no paper text beyond the audit's quotes
    assert (out_dir / "recall.memory_audit.json").exists()


def test_recall_keeps_only_what_the_papers_support(recalled):
    entry, _, _ = recalled
    text = entry.plain_text()
    assert "Twelve members were blind" not in text        # unsupported: deleted
    assert "Novotny" not in text
    assert "homozygous" not in text and "heteroplasmic 14459G-A" in text   # contradicted: corrected
    assert "maternally transmitted" not in text           # survived the rewrite with no paper: dropped
    assert len(entry.meta["dropped_ungrounded"]) == 1
    assert all(p.pmids == ["111"] for p in entry.all_paragraphs())
    rel = entry.relationships[0]
    assert (rel.gene_symbol, rel.gene_mim, rel.location, rel.pmids) == ("MT-ND6", "516006", "mitochondria", ["111"])
    assert "516006" in entry.intro.text                   # allowed: HGNC reference data
    assert [i.hpo_id for i in entry.clinical_synopsis] == ["HP:0001332"]


def test_recall_meta_counts(recalled):
    entry, _, _ = recalled
    meta = entry.meta["recall"]
    assert meta["memory_claims"] == 5
    assert meta["memory_claims_by_verdict"] == {"supported": 2, "partially_supported": 0, "contradicted": 1,
                                                "unsupported": 2, "not_checkable": 0}
    assert meta["paragraphs_before"] == 4 and meta["paragraphs_after"] == 3
    assert meta["claims_omitted_by_verdict"]["unsupported"] == 2
    assert sum(meta["claims_omitted_by_verdict"].values()) == 2   # the unknown id is ignored
    assert meta["claims_survived_share"] == 0.6
    assert meta["deletable_not_reported_omitted"] == 0
    assert meta["paragraphs_dropped_uncited"] == 1
    assert meta["hgnc_genes"] == ["MT-ND6"]
    assert meta["memory"]["supplied_papers_cited"] == 1


def test_both_strategies_run_through_the_pipeline(tmp_path):
    llm = ScriptedLLM()
    entries, _ = build_entries(SEED, PAPERS, RunConfig(strategies=("closedbook", "recall")), llm, tmp_path)
    cb, rc = entries["closedbook"], entries["recall"]
    assert cb.meta["strategy"] == "closedbook" and rc.meta["strategy"] == "recall"
    assert "repair" not in cb.meta                          # the control is audited, never repaired
    assert cb.meta["audit"]["unsupported"] == 2 and cb.meta["audit"]["contradicted"] == 1
    assert rc.meta["audit"] == {"supported": 3}
    for name in ("closedbook", "recall"):
        assert (tmp_path / f"entry.{name}.md").exists()
