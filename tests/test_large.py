"""Direct reading on large entries: batching, the merge, and the unchanged small-entry path.

Offline: a scripted model and stubbed ontology and nomenclature services.
"""

from __future__ import annotations

import random
import re
import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import synthesize
from aiomim.config import get_settings
from aiomim.models import Paper, Seed
from aiomim.strategies import direct
from aiomim.synthesize import DIRECT_SYSTEM, DIRECT_TOTAL_CHARS, DEntry, DParagraph, DSection

SEED = Seed(mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", symbol="LDYT")


# --------------------------------------------------------------------------- #
# Stubs
# --------------------------------------------------------------------------- #


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy"}

    def exact(self, text):
        return next((i for i, label in self.terms.items() if label.lower() == text.lower()), None)

    def search(self, text, k=10):
        return []

    def label(self, hpo_id):
        return self.terms.get(hpo_id, "")

    def is_phenotype(self, hpo_id):
        return hpo_id in self.terms

    def category(self, hpo_id):
        return "Neurologic"


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
    hgnc_module.gene_info = lambda s: _Gene("MT-ND6", "516006", "mitochondria") if s.upper() == "MT-ND6" else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


# --------------------------------------------------------------------------- #
# Papers
# --------------------------------------------------------------------------- #

_WORDS = ("patients family mutation heteroplasmic dystonia striatal lesions optic atrophy sequencing "
          "segregated affected members childhood onset controls transition nucleotide").split()


def make_paper(pmid: str, year: int, chars: int, author: str = "Smith") -> Paper:
    rng = random.Random(pmid)
    body = " ".join(rng.choice(_WORDS) for _ in range(chars // 7 + 10))[:chars]
    return Paper(pmid=pmid, title=f"Report {pmid}", authors=[f"{author} AB", "Jones CD", "Lee EF"], year=year,
                 journal="J Test", abstract="An abstract long enough to count as an abstract. " * 4,
                 fulltext=body if chars > 2000 else None)


def large_set(n: int = 40, seed: int = 7) -> list[Paper]:
    rng = random.Random(seed)
    papers = [make_paper(str(10_000 + i), 1980 + rng.randint(0, 40), rng.choice([1500, 30_000, 60_000, 90_000]),
                         author=f"Author{i}") for i in range(n)]
    papers.append(make_paper("99999", 1999, DIRECT_TOTAL_CHARS + 50_000, author="Huge"))  # longer than a batch
    return papers


def small_set() -> list[Paper]:
    return [make_paper("111", 1994, 30_000, "Jun"), make_paper("222", 1990, 1500, "Novotny"),
            make_paper("333", 2001, 45_000, "Gropman")]


# --------------------------------------------------------------------------- #
# Scripted model
# --------------------------------------------------------------------------- #

_PMID = re.compile(r'<paper pmid="(\d+)"')


class ScriptedLLM:
    """Writes a partial entry for any batch prompt, and a merge plan that exercises the guards."""

    def __init__(self, merge_fails: bool = False):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str, str]] = []   # (stage, output, system, prompt)
        self.merge_fails = merge_fails

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, output.__name__, system, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    def _XChoices(self, prompt):
        from aiomim.extract import XChoices
        return XChoices(choices=[])

    def _DEntry(self, prompt):
        pmids = _PMID.findall(prompt)
        P = DParagraph
        return DEntry(
            intro=P(text=f"A number sign (#) is used with this entry because LDYT is caused by mutation in MT-ND6 "
                         f"(batch starting {pmids[0]}).", pmids=pmids[:1]),
            sections=[
                DSection(name="description", paragraphs=[P(text="LDYT combines optic atrophy and dystonia.",
                                                           pmids=pmids[:1])]),
                DSection(name="clinical_features", paragraphs=[
                    P(text=f"Report {p} described affected members.", pmids=[p]) for p in pmids]),
            ],
            relationships=[synthesize.DRelationship(gene_symbol="MT-ND6", inheritance=["MT"], pmids=pmids[:1])],
            allelic_variants=[synthesize.DAllelicVariant(
                gene_symbol="MT-ND6", name="MTND6, ALA72VAL", hgvs=["m.14459G>A"], phenotype="LDYT",
                paragraphs=[P(text=f"Report {pmids[-1]} found the 14459G-A transition.", pmids=[pmids[-1]])])],
            clinical_synopsis=[synthesize.DSynopsisItem(feature="dystonia", hpo_label="Dystonia", pmids=pmids[:2])],
        )

    def _MEntry(self, prompt):
        if self.merge_fails:
            raise RuntimeError("merge refused")
        ids = re.findall(r"\[(P\d+)\] \(cites .*?\) ((?:A number sign|LDYT combines|Report ).*)$", prompt, re.M)
        intros = [pid for pid, text in ids if text.startswith("A number sign")]
        descriptions = [pid for pid, text in ids if text.startswith("LDYT combines")]
        clinical = [pid for pid, text in ids if text.startswith("Report") and "described" in text]
        variant_paras = [pid for pid, text in ids if "14459G-A" in text]
        vids = re.findall(r"^\[(V\d+)\]", prompt, re.M)
        M = direct.MParagraph
        return direct.MEntry(
            intro=M(sources=intros, text="A number sign (#) is used with this entry because LDYT is caused by "
                                         "mutation in MT-ND6."),
            sections=[
                direct.MSection(name="description", paragraphs=[
                    M(sources=descriptions, text="LDYT combines optic atrophy and dystonia.")]),
                # The last three clinical paragraphs are left out: they must be put back.
                direct.MSection(name="clinical_features", paragraphs=[M(sources=[pid], text="")
                                                                      for pid in clinical[:-3]]
                                + [M(sources=["P9999"], text="")]),   # an ID that does not exist
            ],
            allelic_variants=[direct.MVariant(sources=vids, name="MTND6, ALA72VAL",
                                              paragraphs=[M(sources=variant_paras, text="")])],
        )


# --------------------------------------------------------------------------- #
# Below the threshold: unchanged
# --------------------------------------------------------------------------- #


def _todays_prompt(seed: Seed, papers: list[Paper]) -> str:
    """The direct prompt as synthesize_direct has always built it (no HGNC data for a blind seed)."""
    per_paper = max(20_000, DIRECT_TOTAL_CHARS // max(1, len(papers)))
    blocks = []
    for p in sorted(papers, key=lambda p: (p.year or 9999, p.pmid)):
        text = p.source_text()[:per_paper]
        blocks.append(f'<paper pmid="{p.pmid}" label="{p.label}" available="{p.content_level}">\n'
                      f"{p.reference}\n\n{text}\n</paper>")
    return (f"{synthesize._header(seed)}\n\nReference data from HGNC (nomenclature only, not literature "
            f"evidence):\nnone supplied\n\n" + "\n\n".join(blocks))


def test_below_threshold_the_direct_prompt_is_todays(tmp_path):
    papers = small_set()
    assert not direct.needs_batching(papers)
    llm = ScriptedLLM()
    entry = direct.run(SEED, papers, llm, tmp_path)
    writes = [c for c in llm.calls if c[1] == "DEntry"]
    assert len(writes) == 1
    stage, _, system, prompt = writes[0]
    assert (stage, system) == ("synthesize", DIRECT_SYSTEM)
    assert prompt == _todays_prompt(SEED, papers)
    assert not any(c[1] == "MEntry" for c in llm.calls)
    assert entry.meta["direct_batching"]["used"] is False

    # And it is the very call synthesize_direct makes, so cached replies keep hitting.
    again = ScriptedLLM()
    synthesize.synthesize_direct(SEED, papers, again)
    assert [c for c in again.calls if c[1] == "DEntry"] == writes


def test_below_threshold_keeps_todays_per_paper_cap():
    # 12 papers with one long one, still under the total budget: cut as before, not batched.
    papers = [make_paper(str(i), 2000 + i, 10_000) for i in range(11)] + [make_paper("77", 2020, 80_000)]
    assert not direct.needs_batching(papers)
    assert _todays_prompt(SEED, papers).count("<paper ") == 12


def test_threshold_is_the_single_prompt_budget():
    papers = small_set()
    total = direct.source_chars(papers)
    assert not direct.needs_batching(papers, budget=total)
    assert direct.needs_batching(papers, budget=total - 1)
    assert direct.needs_batching(large_set())


# --------------------------------------------------------------------------- #
# Above it: batches
# --------------------------------------------------------------------------- #


def test_batches_respect_the_budget_and_the_date_order():
    papers = large_set()
    budget = direct.BATCH_CHARS
    batches = direct.plan_batches(papers, budget)
    assert len(batches) > 1
    flat = [p for b in batches for p in b]
    assert sorted(p.pmid for p in flat) == sorted(p.pmid for p in papers)        # each paper exactly once
    assert flat == sorted(papers, key=lambda p: (p.year or 9999, p.pmid))         # consecutive, by date
    for b in batches:
        if len(b) > 1:
            assert sum(len(p.source_text()) for p in b) <= budget
    huge = next(b for b in batches if any(p.pmid == "99999" for p in b))
    assert len(huge) == 1                                                          # alone in its batch


def test_batch_prompt_has_todays_layout_and_cuts_only_an_oversized_paper():
    papers = small_set()
    prompt, truncated = direct.batch_prompt(SEED, papers, "")
    assert prompt == _todays_prompt(SEED, papers) and truncated == []
    huge = make_paper("99999", 1999, 5000)
    prompt, truncated = direct.batch_prompt(SEED, [huge], "", budget=3000)
    assert truncated == ["99999"] and huge.source_text()[:3000] + "\n</paper>" in prompt


@pytest.fixture
def batched(tmp_path):
    papers = large_set()
    llm = ScriptedLLM()
    entry = direct.run(SEED, papers, llm, tmp_path)
    return entry, llm, papers


def test_each_batch_gets_the_direct_prompt_within_budget(batched):
    entry, llm, papers = batched
    writes = [c for c in llm.calls if c[1] == "DEntry"]
    meta = entry.meta["direct_batching"]
    assert meta["used"] is True and len(writes) == len(meta["batches"]) > 1
    header = len(_todays_prompt(SEED, []))
    for stage, _, system, prompt in writes:
        assert (stage, system) == ("synthesize", DIRECT_SYSTEM)
        n = len(_PMID.findall(prompt))
        # paper text within budget; the rest is the header and each paper's tag and reference line
        assert len(prompt) <= direct.BATCH_CHARS + header + n * 400
    assert entry.meta["truncated_papers"] == ["99999"]
    assert sum(b["n_papers"] for b in meta["batches"]) == len(papers)


def test_merged_entry_keeps_every_cited_paper(batched):
    entry, llm, papers = batched
    merges = [c for c in llm.calls if c[1] == "MEntry"]
    assert len(merges) == 1
    assert "<paper" not in merges[0][3]                    # the merge never sees the papers
    assert set(entry.cited_pmids()) == {p.pmid for p in papers}
    merge = entry.meta["direct_batching"]["merge"]
    assert merge["pmids_lost_in_merge"] == []
    assert merge["restored"] == 3 and merge["unknown_ids"] == 1


def test_merge_combines_duplicates_with_the_union_of_their_citations(batched):
    entry, llm, papers = batched
    n_batches = len(entry.meta["direct_batching"]["batches"])
    description = next(s for s in entry.sections if s.name == "description")
    assert len(description.paragraphs) == 1
    first_of_each = {b["pmids"][0] for b in entry.meta["direct_batching"]["batches"]}
    assert set(description.paragraphs[0].pmids) == first_of_each
    assert len(entry.allelic_variants) == 1                 # one variant, reported in every batch
    assert len(entry.allelic_variants[0].paragraphs) == n_batches
    assert entry.intro.text.startswith("A number sign") and "batch starting" not in entry.intro.text
    assert len(entry.relationships) == 1 and entry.relationships[0].gene_symbol == "MT-ND6"
    assert len(entry.clinical_synopsis) == 1


def test_merge_may_not_grow_a_paragraph():
    paragraphs = {"P1": (("section", "description"), DParagraph(text="Short one.", pmids=["1"])),
                  "P2": (("section", "description"), DParagraph(text="Short two.", pmids=["2"]))}
    plan = direct.MEntry(intro=direct.MParagraph(sources=[], text=""), allelic_variants=[], sections=[
        direct.MSection(name="description", paragraphs=[
            direct.MParagraph(sources=["P1", "P2"], text="An invented, much longer paragraph " * 20)])])
    empty = DEntry(intro=DParagraph(text="", pmids=[]), sections=[], relationships=[], allelic_variants=[],
                   clinical_synopsis=[])
    merged, stats = direct.assemble(plan, paragraphs, {}, [empty])
    assert stats["rejected_longer"] == 1
    assert [p.text for p in merged.sections[0].paragraphs] == ["Short one.", "Short two."]


def test_failed_merge_falls_back_to_the_partial_entries(tmp_path):
    papers = large_set()
    llm = ScriptedLLM(merge_fails=True)
    entry = direct.run(SEED, papers, llm, tmp_path)
    assert "merge_failed" in entry.meta["direct_batching"]["merge"]
    assert set(entry.cited_pmids()) == {p.pmid for p in papers}
