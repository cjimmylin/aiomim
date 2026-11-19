"""Offline tests for the learned-curation-guide strategy and its two analyses.

No network and no model calls: a scripted model returns canned replies. All
texts here are invented for the test; none is OMIM's wording.
"""

from __future__ import annotations

import json
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

from aiomim import editorial, gaps, guide, synthesize
from aiomim.config import get_settings
from aiomim.evalset import stratum_of
from aiomim.models import (
    AllelicVariantEntry,
    EntryParagraph,
    EntrySection,
    GeneratedEntry,
    GoldAllelicVariant,
    GoldEntry,
    GoldParagraph,
    Paper,
    Seed,
)

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# A scripted model
# --------------------------------------------------------------------------- #


class ScriptedLLM:
    def __init__(self, replies: dict[str, object] | None = None):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str]] = []
        self.replies = replies or {}

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, system, prompt))
        reply = self.replies[output.__name__]
        return reply(prompt) if callable(reply) else reply

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]


# --------------------------------------------------------------------------- #
# 1. The split
# --------------------------------------------------------------------------- #


def _rows(mims):
    return ["mim\tstratum\ttitle"] + [f"{m}\t{stratum_of(m)}\tENTRY {m}" for m in mims]


def test_split_is_stratified_reproducible_and_keeps_the_worked_example_out():
    mims = ([str(100000 + i) for i in range(19)] + ["500001"] + [str(600000 + i) for i in range(20)]
            + [str(610000 + i) for i in range(20)] + [str(616000 + i) for i in range(20)]
            + [str(620000 + i) for i in range(20)])
    train, test = guide.split_rows(_rows(mims), n_train=30, seed=5)
    assert len(train) == 30 and len(test) == 70
    assert Counter(stratum_of(r.split("\t")[0]) for r in train) == {s: 6 for s in {stratum_of(m) for m in mims}}
    assert "500001" in {r.split("\t")[0] for r in test}
    # The same seed gives the same split whatever the row order; another seed gives another split.
    again, _ = guide.split_rows(_rows(list(reversed(mims))), n_train=30, seed=5)
    assert sorted(again) == sorted(train)
    other, _ = guide.split_rows(_rows(mims), n_train=30, seed=6)
    assert sorted(other) != sorted(train)


def test_committed_split_matches_the_generator():
    source = (ROOT / "evalsets" / "omim100.tsv").read_text(encoding="utf-8").splitlines()
    train, test = guide.split_rows(source)
    on_disk = lambda name: [ln for ln in (ROOT / "evalsets" / name).read_text().splitlines()[1:] if ln]  # noqa: E731
    assert on_disk("omim100.train.tsv") == train and on_disk("omim100.test.tsv") == test
    assert len(train) == 30 and len(test) == 70
    assert Counter(stratum_of(r.split("\t")[0]) for r in train).most_common()[0][1] == 6
    assert any(r.startswith("500001\t") for r in test)
    assert source[0] == (ROOT / "evalsets" / "omim100.train.tsv").read_text().splitlines()[0]


# --------------------------------------------------------------------------- #
# 2. Gap analysis
# --------------------------------------------------------------------------- #

FULL = Paper(pmid="1", title="A study of a rare disorder", authors=["Doe J"], year=2001, abstract="Two sibs were studied.",
             fulltext="Both sibs had onset at age 3 years. Muscle enzyme activity was 12% of control values.")
ABSTRACT_ONLY = Paper(pmid="2", title="Another report", authors=["Roe R"], year=2005,
                      abstract="A boy carried a homozygous frameshift.")


def _fact(text, status):
    return {"fact": text, "status": status, "note": ""}


def _gap_dir(tmp_path):
    d = tmp_path / "run" / "100001"
    d.mkdir(parents=True)
    paragraphs = [
        {"pmids": ["1"], "content_level": "fulltext", "reference": "invented reference one", "draft": "x",
         "facts": [_fact("onset at age 3", "absent"), _fact("activity 12% of control", "partial"),
                   _fact("two sibs", "present"), _fact("seizures", "absent")]},
        {"pmids": ["2"], "content_level": "abstract", "reference": "invented reference two", "draft": "y",
         "facts": [_fact("homozygous frameshift", "present"), _fact("born to cousins", "absent"),
                   _fact("died at age 2", "contradicted")]},
        {"pmids": ["2"], "content_level": "abstract", "reference": "invented reference three", "draft": "z",
         "facts": [_fact("a boy", "present")]},
    ]
    (d / "eval.direct.json").write_text(json.dumps({"mim": "100001", "gold_text": {"paragraphs": paragraphs}}))
    (d / "papers.json").write_text(json.dumps([{"pmid": "1", "content_level": "fulltext"},
                                               {"pmid": "2", "content_level": "abstract"}]))
    return d


def test_gap_analysis_counts_by_access_level(tmp_path):
    d = _gap_dir(tmp_path)
    V = gaps.XGapVerdict

    def reply(prompt):
        if "invented reference one" in prompt:
            return gaps.XGapVerdicts(verdicts=[
                V(n=1, in_text="yes", quote="Both sibs had onset at age 3 years"),
                V(n=2, in_text="yes", quote="activity was 99% of control"),   # quote not in the text: downgraded
                V(n=3, in_text="no", quote="")])
        return gaps.XGapVerdicts(verdicts=[V(n=1, in_text="no", quote="")])

    llm = ScriptedLLM({"XGapVerdicts": reply})
    summary = gaps.gaps_run(tmp_path / "run", "direct", llm=llm, load=lambda _: {"1": FULL, "2": ABSTRACT_ONLY})
    assert len(llm.calls) == 2 and all(stage == "judge" for stage, _, _ in llm.calls)   # nothing missed in paragraph 3
    # Only the missed facts are sent, numbered, with the paper's text as the writer had it.
    first = llm.calls[0][2]
    assert "1. onset at age 3" in first and "two sibs" not in first.split("<facts>")[1].split("</facts>")[0]
    assert "Muscle enzyme activity" in first

    entry = json.loads((d / "gaps.direct.json").read_text())
    facts = entry["paragraphs"][0]["facts"]
    assert [f["in_text"] for f in facts] == ["yes", "partly", "no"]
    assert facts[1]["model_in_text"] == "yes" and not facts[1]["quote_verified"]

    full, abstract = summary["by_content_level"]["fulltext"], summary["by_content_level"]["abstract"]
    assert (full["n_gold_facts"], full["present"], full["n_not_conveyed"]) == (4, 1, 3)
    assert (full["yes"], full["partly"], full["no"]) == (1, 1, 1)
    assert full["by_draft_status"]["partial"]["partly"] == 1
    assert (abstract["n_gold_facts"], abstract["present"], abstract["contradicted"], abstract["n_not_conveyed"]) == (4, 2, 1, 1)
    assert abstract["no"] == 1 and abstract["share_not_in_text"] == 1.0
    assert summary["overall"]["n_not_conveyed"] == 4 and summary["yes_downgraded"] == 1
    assert summary["overall"]["share_in_text"] == 0.25
    # The run-level files carry counts, not fact wording.
    run_level = (tmp_path / "run" / "gaps.direct.json").read_text() + (tmp_path / "run" / "gaps.direct.md").read_text()
    assert "onset at age 3" not in run_level and "invented reference" not in run_level
    assert "| Full text | 4 | 1 | 3 | 1 | 1 | 1 | 0 | 33% |" in (tmp_path / "run" / "gaps.direct.md").read_text()


def test_gap_judge_reads_each_paper_cut_where_the_writer_cut_it():
    assert gaps.per_paper_chars(3) == 200_000
    assert gaps.per_paper_chars(100) == 20_000


# --------------------------------------------------------------------------- #
# 3. Editorial precision
# --------------------------------------------------------------------------- #


def _editorial_dir(tmp_path, strategy="direct"):
    d = tmp_path / "run" / "100002"
    d.mkdir(parents=True, exist_ok=True)
    gold = GoldEntry(mim="100002", title="INVENTED DISORDER", cited_pmids=["1", "2", "3"], allelic_variants=[
        GoldAllelicVariant(omim_id="1.0001", gene_symbol="GENEX", name="GENEX, ARG1TRP", paragraphs=[
            GoldParagraph(text="Invented reference about paper one.", pmids=["1"]),
            GoldParagraph(text="Invented reference about paper two.", pmids=["2"]),
            GoldParagraph(text="Invented reference about paper three.", pmids=["3"]),
            GoldParagraph(text="Invented reference about an uncited paper.", pmids=["9"])])])
    entry = GeneratedEntry(mim="100002", title="INVENTED DISORDER", sections=[
        EntrySection(name="clinical_features", paragraphs=[
            EntryParagraph(text="Doe et al. (2001) studied two sibs.", pmids=["1"]),
            EntryParagraph(text="Roe et al. (2005) studied a boy.", pmids=["2"])])],
        allelic_variants=[AllelicVariantEntry(number=1, gene_symbol="GENEX", name="GENEX, ARG1TRP", paragraphs=[
            EntryParagraph(text="In two sibs, Doe et al. (2001) found a missense change.", pmids=["1"])])])
    (d / f"entry.{strategy}.json").write_text(entry.model_dump_json())
    (d / "gold.json").write_text(gold.model_dump_json())
    (d / "papers.json").write_text(json.dumps([
        {"pmid": "1", "content_level": "fulltext", "label": "Doe et al. (2001)"},
        {"pmid": "2", "content_level": "abstract", "label": "Roe et al. (2005)"},
        {"pmid": "3", "content_level": "title", "label": "Poe et al. (2010)"}]))
    (d / f"eval.{strategy}.json").write_text(json.dumps({"gold_text": {"paragraphs": [
        {"pmids": ["1"], "n_facts": 5}, {"pmids": ["2"], "n_facts": 3}, {"pmids": ["3"], "n_facts": 4}]}}))
    return d


def test_editorial_precision_is_aggregated_per_paper(tmp_path):
    d = _editorial_dir(tmp_path)
    S = editorial.XStatement

    def reply(prompt):
        if "paper one" in prompt:
            assert "Doe et al. (2001) studied two sibs." in prompt and "found a missense change" in prompt
            assert "Roe" not in prompt.split("<draft>")[1]       # only the draft text that cites this paper
            return editorial.XStatements(statements=[S(statement="two sibs", counterpart="yes"),
                                                     S(statement="missense change", counterpart="partly"),
                                                     S(statement="an extra detail", counterpart="no"),
                                                     S(statement="another extra", counterpart="no")])
        return editorial.XStatements(statements=[S(statement="a boy", counterpart="yes"),
                                                 S(statement="an aside", counterpart="no")])

    llm = ScriptedLLM({"XStatements": reply})
    result = editorial.editorial_run(tmp_path / "run", ("direct",), llm=llm)
    assert len(llm.calls) == 2      # paper three has no draft text: no call; the uncited paper is out of scope
    entry = json.loads((d / "editorial.direct.json").read_text())
    assert [p["n_statements"] for p in entry["paragraphs"]] == [4, 2, 0]
    assert entry["paragraphs"][0]["precision"] == 0.375 and entry["paragraphs"][2]["precision"] is None
    s = result["strategies"]["direct"]["pooled"]
    assert (s["n_statements"], s["yes"], s["partly"], s["no"]) == (6, 2, 1, 3)
    assert s["precision"] == round(2.5 / 6, 3)
    assert s["statements_per_paper"] == 2.0 and s["omim_facts_per_paper"] == 4.0
    assert s["statements_per_omim_fact"] == 0.5
    by_level = result["strategies"]["direct"]["by_content_level"]
    assert by_level["fulltext"]["n_statements"] == 4 and by_level["title"]["n_statements"] == 0
    assert (tmp_path / "run" / "editorial.direct.md").exists()


# --------------------------------------------------------------------------- #
# 4. The guide's checks and the selection rule
# --------------------------------------------------------------------------- #

REFERENCE = ("In a 4-year-old girl with the invented disorder, Doe et al. (2001) identified a homozygous "
             "missense mutation that segregated with the disorder in the family.")


def test_overlap_check_rejects_a_guide_that_copies_gold_wording():
    copied = ("## Curation guide\n- Write it like this: in a 4-year-old girl with the invented disorder, "
              "Doe et al. identified something.")
    result = guide.check_guide(copied, [REFERENCE])
    assert not result["ok"] and result["shared_8word_runs"] >= 1
    with pytest.raises(guide.GuideLeak):
        guide.assert_clean(copied, [REFERENCE])
    # Case and punctuation do not hide a copy.
    assert guide.shared_runs("IN A 4-YEAR-OLD GIRL, WITH THE INVENTED DISORDER; DOE", [REFERENCE])
    clean = ("## Curation guide\n- State the age and sex of each patient, the zygosity of the variant, and whether "
             "it segregated with the disorder in the family.")
    assert guide.check_guide(clean, [REFERENCE])["ok"]
    # Seven shared words in a row are allowed; gene symbols and entry titles are not.
    assert not guide.shared_runs("homozygous missense mutation that segregated with the", [REFERENCE])
    assert guide.check_guide(clean + " Mention GENEX first.", [REFERENCE], symbols={"GENEX"})["gene_symbols"] == ["GENEX"]
    assert not guide.check_guide(clean, [REFERENCE], titles={"INVENTED DISORDER TYPE 2"})["entry_titles"]
    assert not guide.check_guide(clean + " Like invented disorder type 2.", [REFERENCE],
                                 titles={"INVENTED DISORDER TYPE 2"})["ok"]


def test_selection_rejects_a_guide_that_only_writes_more():
    base = {"gold_fact_coverage": 0.5, "synopsis_exact_f1": 0.3, "statements_per_paper": 10.0}
    wordy = guide.objective({"gold_fact_coverage": 0.6, "synopsis_exact_f1": 0.3, "statements_per_paper": 13.0}, base)
    modest = guide.objective({"gold_fact_coverage": 0.53, "synopsis_exact_f1": 0.32, "statements_per_paper": 11.0}, base)
    assert wordy["grows_too_much"] and not modest["grows_too_much"] and modest["objective"] == 0.05
    rounds = [{"round": 1, "checks": {"ok": True}, "selection": wordy},
              {"round": 2, "checks": {"ok": True}, "selection": modest},
              {"round": 3, "checks": {"ok": False}, "selection": {**modest, "objective": 0.2}}]
    assert guide.choose_round(rounds)["round"] == 2
    assert guide.choose_round(rounds[:1]) is None


# --------------------------------------------------------------------------- #
# 5. The strategy
# --------------------------------------------------------------------------- #


class _HPO:
    def category(self, _):
        return ""

    def label(self, _):
        return ""


@pytest.fixture
def writer(monkeypatch):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: _HPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    hgnc_module.normalize_symbol = lambda s: s.upper()
    hgnc_module.gene_info = lambda s: None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)
    D = synthesize
    draft = D.DEntry(intro=D.DParagraph(text="An invented disorder.", pmids=["1"]), sections=[
        D.DSection(name="clinical_features", paragraphs=[D.DParagraph(text="Doe et al. (2001) studied two sibs.",
                                                                       pmids=["1"])])],
        relationships=[], allelic_variants=[], clinical_synopsis=[])
    return ScriptedLLM({"DEntry": draft})


SEED = Seed(mim="100003", title="INVENTED DISORDER")


def test_guided_strategy_puts_the_guide_in_the_system_prompt(writer, tmp_path, monkeypatch):
    from aiomim.strategies import run_strategy

    path = tmp_path / "guide.md"
    path.write_text("## Curation guide\n- Report the age at onset of each patient.\n")
    monkeypatch.setenv("AIOMIM_GUIDE", str(path))
    entry = run_strategy("guided", SEED, [FULL], writer, tmp_path)
    stage, system, _ = writer.calls[0]
    assert stage == "synthesize"
    assert system.startswith(synthesize.DIRECT_SYSTEM) and system.endswith("- Report the age at onset of each patient.")
    assert entry.meta["strategy"] == "guided"
    info = entry.meta["guide"]
    assert info["path"] == str(path) and info["words"] == 12 and len(info["sha256"]) == 64
    assert entry.meta["truncated_papers"] == []


def test_baseline_prompt_is_untouched_without_rules(writer, tmp_path):
    from aiomim.strategies import run_strategy

    run_strategy("direct", SEED, [FULL], writer, tmp_path)
    synthesize.synthesize_direct(SEED, [FULL], writer, extra_rules="  \n")
    assert [c[1] for c in writer.calls] == [synthesize.DIRECT_SYSTEM, synthesize.DIRECT_SYSTEM]
    assert writer.calls[0][2] == writer.calls[1][2]


def test_guided_strategy_fails_clearly_without_a_guide(writer, tmp_path, monkeypatch):
    from aiomim.strategies import run_strategy

    monkeypatch.setenv("AIOMIM_GUIDE", str(tmp_path / "missing.md"))
    with pytest.raises(FileNotFoundError, match="guide-learn"):
        run_strategy("guided", SEED, [FULL], writer, tmp_path)
    assert not writer.calls


# --------------------------------------------------------------------------- #
# 6. compare --entries-file
# --------------------------------------------------------------------------- #


def test_compare_entries_file_restricts_and_keeps_main_files(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from aiomim import cli
    from tests.test_compare import _run

    run = _run(tmp_path)
    (tmp_path / "test.tsv").write_text("mim\tstratum\n100100\tx\n616100\tx\n620200\tx\n")
    monkeypatch.setattr(cli, "get_settings", lambda: types.SimpleNamespace(runs=tmp_path))
    out = CliRunner().invoke(cli.main, ["compare", "demo", "--entries-file", str(tmp_path / "test.tsv"),
                                        "--tag", "heldout"])
    assert out.exit_code == 0, out.output
    result = json.loads((run / "strategies.heldout.json").read_text())
    assert result["n_entries"] == 3 and result["entries_file"] == str(tmp_path / "test.tsv")
    assert (run / "strategies.heldout.md").exists()
    assert not (run / "strategies.json").exists() and not list(run.glob("knowledge_graph.*.tsv"))

    from aiomim.compare import compare_strategies
    assert compare_strategies(run)["n_entries"] == 6
    assert compare_strategies(run, entries=["100100"])["n_entries"] == 1
    assert compare_strategies(run, entries=[]) == {}
