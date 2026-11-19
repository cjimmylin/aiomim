"""The agentic curator with a scripted model: workspace, call contract, quote check, meta.

No network and no model calls; the ontology and nomenclature services are
stubbed as in `test_pipeline_offline.py`.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from aiomim.config import get_settings
from aiomim.models import Paper, Seed
from aiomim.strategies import agent
from aiomim.synthesize import DSynopsisItem

from test_pipeline_offline import FakeHPO, _Gene

ABSTRACT = (
    "We studied a large Hispanic family with maternally inherited Leber optic atrophy and dystonia. "
    "Eight affected members had childhood-onset generalized dystonia with bilateral striatal lesions on imaging. "
    "Sequencing of mitochondrial DNA identified a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 "
    "gene, changing alanine 72 to valine. The mutation was absent from 310 controls."
)
# A full text whose paragraphs are single very long lines, as our texts are.
FULLTEXT = "INTRODUCTION\n" + " ".join(
    f"Sentence {i} of the introduction describes the long-standing clinical observations in family {i}."
    for i in range(40)
) + "\nRESULTS\n" + "Two sibs were homozygous for the ND6 change and had optic atrophy from age 12 years. " * 30

PAPERS = [
    Paper(pmid="111", title="A mitochondrial ND6 mutation in optic atrophy and dystonia",
          authors=["Jun AS", "Brown MD", "Wallace DC"], year=1994, journal="Proc Natl Acad Sci U S A",
          abstract=ABSTRACT),
    Paper(pmid="222", title="Follow-up of the ND6 family", authors=["Novotny EJ", "Singh G"], year=1986,
          journal="Neurology", abstract="A short abstract about the family and its dystonia, which began in childhood.",
          fulltext=FULLTEXT),
]
SEED = Seed(mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", symbol="LDYT")


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


class ScriptedAgentLLM:
    def __init__(self):
        self.settings = get_settings()
        self.calls: list[dict] = []

    def call(self, stage, system, prompt, output, **kwargs):
        workdir = kwargs.get("workdir")
        self.calls.append({"stage": stage, "system": system, "prompt": prompt, "output": output, **kwargs,
                           "files": sorted(str(p.relative_to(workdir)) for p in
                                           Path(workdir).rglob("*") if p.is_file())})
        if output is agent.AEntry:
            return self._entry()
        return output.model_validate({"choices": []})  # HPO disambiguation, unused with exact labels

    def _entry(self):
        P = agent.AParagraph
        return agent.AEntry(
            intro=P(text="A number sign (#) is used with this entry because LDYT is caused by mutation in the "
                         "MT-ND6 gene (516006).", pmids=["111"],
                    quotes=["a heteroplasmic G-to-A transition at nucleotide 14459 in the ND6 gene"]),
            sections=[agent.ASection(name="clinical_features", paragraphs=[
                P(text="Jun et al. (1994) studied a large Hispanic family in which 8 members had childhood-onset "
                       "dystonia.", pmids=["111"],
                  quotes=["Eight affected members had childhood-onset generalized dystonia"]),
                # The quote spans a wrapped line break in the workspace file: still found.
                P(text="Novotny and Singh (1986) reported 2 homozygous sibs with optic atrophy from age 12 years.",
                  pmids=["222"],
                  quotes=["Two sibs were homozygous for the ND6 change and had optic atrophy from age 12 years. "
                          "Two sibs were homozygous for the ND6 change"]),
                # Invented quote: the paragraph must be dropped.
                P(text="Jun et al. (1994) found complex I activity reduced to 20% in muscle.", pmids=["111"],
                  quotes=["Complex I activity in skeletal muscle mitochondria was reduced to 20% of control values."]),
            ])],
            relationships=[agent.ARelationship(gene_symbol="ND6", inheritance=["MT"], pmids=["111"])],
            allelic_variants=[],
            clinical_synopsis=[DSynopsisItem(feature="generalized dystonia", hpo_label="Dystonia", pmids=["111"])],
            papers_read=["111", "222", "999"],
            process_note="Read both papers in full; searched for 14459.",
        )


@pytest.fixture
def run(tmp_path):
    llm = ScriptedAgentLLM()
    entry = agent.run(SEED, PAPERS, llm, tmp_path)
    return entry, llm, tmp_path


def test_workspace_holds_exactly_the_papers_wrapped_and_indexed(run, tmp_path):
    _, llm, out_dir = run
    ws = out_dir / "agent_workspace"
    assert llm.calls[0]["files"] == ["PAPERS.md", "papers/111.txt", "papers/222.txt"]
    long_text = (ws / "papers" / "222.txt").read_text()
    assert max(len(line) for line in long_text.splitlines()) <= agent.WRAP
    assert "\n\nRESULTS\n\n" in long_text
    # Nothing is lost by wrapping: the same words in the same order.
    assert long_text.split() == PAPERS[1].source_text().split()
    index = (ws / "PAPERS.md").read_text()
    row = next(line for line in index.splitlines() if line.startswith("| 222 "))
    for cell in ("Novotny and Singh (1986)", "1986", "Neurology", "Follow-up of the ND6 family", "full text",
                 "papers/222.txt"):
        assert cell in row
    assert "abstract only" in next(line for line in index.splitlines() if line.startswith("| 111 "))
    # A rebuild leaves no stray files behind.
    (ws / "gold.json").write_text("{}")
    agent.build_workspace(PAPERS[:1], ws)
    assert sorted(str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()) == ["PAPERS.md", "papers/111.txt"]


def test_call_is_an_agent_session_keyed_on_the_workspace(run, tmp_path):
    _, llm, out_dir = run
    call = llm.calls[0]
    assert call["stage"] == "agent" and call["output"] is agent.AEntry
    assert call["tools"] == ("Read", "Grep", "Glob")
    assert call["workdir"] == str(out_dir / "agent_workspace")
    assert "PAPERS.md" in call["prompt"] and "LEBER OPTIC ATROPHY AND DYSTONIA" in call["prompt"]
    key = call["workspace_key"]
    assert key and agent.build_workspace(PAPERS, tmp_path / "again")[1] == key
    changed = [PAPERS[0].model_copy(update={"abstract": ABSTRACT + " One more sentence."}), PAPERS[1]]
    assert agent.build_workspace(changed, tmp_path / "changed")[1] != key


def test_quote_check_keeps_real_and_drops_invented(run):
    entry, _, _ = run
    text = entry.plain_text()
    assert "8 members had childhood-onset dystonia" in text
    assert "homozygous sibs" in text
    assert "complex I" not in text
    assert entry.meta["quote_check"]["paragraphs_dropped"] == 1
    assert entry.intro is not None
    assert [r.gene_symbol for r in entry.relationships] == ["MT-ND6"]


def test_agent_meta_is_filled(run):
    entry, _, _ = run
    meta = entry.meta["agent"]
    assert meta["papers_read"] == ["111", "222"]
    assert meta["papers_not_read"] == []
    assert meta["papers_read_unknown"] == ["999"]
    assert meta["process_note"].startswith("Read both papers")
    assert entry.meta["strategy"] == "agent"
