"""Frozen gold-fact lists: split once, mark every draft against the same facts. No network, no model."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from aiomim import facts
from aiomim.export import _redact, export_run
from aiomim.facts import (MARK_SYSTEM, MARK_WHOLE_SYSTEM, SPLIT_SYSTEM, FactStore, eval_gold_text_frozen,
                          frozen_facts, judge_file, paragraph_key, rescore_run)
from aiomim.gaps import GAPS_SYSTEM, gaps_run
from aiomim.models import (EntryParagraph, EntrySection, GeneratedEntry, GoldAllelicVariant, GoldEntry,
                           GoldParagraph, Paper)

PARA_A = "Smith et al. (2001) studied 3 sibs with seizures. They found a homozygous ARG12TRP mutation (100000.0001)."
PARA_B = "Jones et al. (2005) reported a girl with ataxia and optic atrophy."
SPLITS = {PARA_A: ["3 sibs were studied", "the sibs had seizures", "a homozygous R12W mutation was found"],
          PARA_B: ["a girl was reported", "the girl had ataxia", "the girl had optic atrophy"]}


class _Usage:
    def summary(self):
        return {"total": {"calls": 0, "cached": 0, "input_tokens": 0, "output_tokens": 0}}


class FakeLLM:
    """Answers split, mark and gap prompts from simple rules; records every call."""

    def __init__(self, replicate: str = "", mark=None, gap=None):
        self.settings = SimpleNamespace(replicate=replicate, model_for=lambda s: "m", effort_for=lambda s: "e")
        self.usage = _Usage()
        self.calls: list[tuple[str, str]] = []
        self.mark = mark or self._mark
        self.gap = gap or self._gap

    def map(self, stage, system, prompts, output):
        out = []
        for prompt in prompts:
            self.calls.append((system, prompt))
            if system == SPLIT_SYSTEM:
                ref = re.search(r"<reference>\n(.*)\n</reference>", prompt, re.S).group(1)
                out.append(output.model_validate({"facts": SPLITS[ref]}))
            elif system in (MARK_SYSTEM, MARK_WHOLE_SYSTEM):
                out.append(output.model_validate({"marks": self.mark(prompt)}))
            elif system == GAPS_SYSTEM:
                out.append(output.model_validate({"verdicts": self.gap(prompt)}))
            else:
                raise AssertionError(system[:40])
        return out

    @staticmethod
    def numbered(prompt):
        block = re.search(r"<facts>\n(.*?)\n</facts>", prompt, re.S).group(1)
        return [(int(n), text) for n, text in re.findall(r"^(\d+)\. (.*)$", block, re.M)]

    def _mark(self, prompt):
        draft = re.search(r"<draft>\n(.*)\n</draft>", prompt, re.S).group(1).lower()
        return [{"n": n, "status": "present" if any(w in draft for w in ("seizures", "ataxia")) and
                 any(w in text for w in ("seizures", "ataxia")) else "absent", "note": ""}
                for n, text in self.numbered(prompt)]

    def _gap(self, prompt):
        return [{"n": n, "in_text": "yes" if "seizures" in text else "no",
                 "quote": "three sibs had seizures" if "seizures" in text else ""}
                for n, text in self.numbered(prompt)]

    def n(self, system):
        return sum(1 for s, _ in self.calls if s == system)


def _gold() -> GoldEntry:
    return GoldEntry(mim="200000", title="TEST", cited_pmids=["1", "2"], allelic_variants=[
        GoldAllelicVariant(omim_id="100000.0001", paragraphs=[GoldParagraph(text=PARA_A, pmids=["1"])]),
        GoldAllelicVariant(omim_id="100000.0002", paragraphs=[GoldParagraph(text=PARA_B, pmids=["2"]),
                                                              GoldParagraph(text="Out of scope.", pmids=["9"])]),
    ])


def _entry(strategy: str, text_1: str, text_2: str | None = None) -> GeneratedEntry:
    paras = [EntryParagraph(text=text_1, pmids=["1"])]
    if text_2 is not None:
        paras.append(EntryParagraph(text=text_2, pmids=["2"]))
    return GeneratedEntry(mim="200000", sections=[EntrySection(name="clinical", heading="Clinical", paragraphs=paras)],
                          meta={"strategy": strategy})


LEVELS = {"1": "fulltext", "2": "abstract"}


def test_one_split_per_paragraph_shared_by_every_draft(tmp_path):
    store, llm = FactStore(tmp_path / "store"), FakeLLM()
    gold = _gold()
    a = eval_gold_text_frozen(_entry("direct", "Three sibs had seizures.", "A girl with ataxia."), gold, LEVELS, llm, store)
    b = eval_gold_text_frozen(_entry("kg", "Nothing relevant here."), gold, LEVELS, llm, store)
    assert llm.n(SPLIT_SYSTEM) == 2                       # two in-scope paragraphs, split once
    assert a["n_facts"] == b["n_facts"] == 6 and a["n_out_of_scope"] == 1
    ids = lambda r: [f["id"] for p in r["paragraphs"] for f in p["facts"]]  # noqa: E731
    assert ids(a) == ids(b) and len(set(ids(a))) == 6
    assert a["present"] == 2 and a["coverage"] == round(2 / 6, 3)
    # kg wrote nothing citing paper 2: those facts are absent without a call.
    assert llm.n(MARK_SYSTEM) == 3 and b["paragraphs"][1]["absent"] == 3
    assert all("fact" not in f for p in a["paragraphs"] for f in p["facts"])   # no wording in eval files
    assert a["by_content_level"]["fulltext"]["n_facts"] == 3
    # The split prompt never contains a draft.
    assert all("<draft>" not in p for s, p in llm.calls if s == SPLIT_SYSTEM)
    stored = store.get(paragraph_key(PARA_A))
    assert [f["fact"] for f in stored["facts"]] == SPLITS[PARA_A]


def test_first_stored_list_wins(tmp_path):
    store = FactStore(tmp_path)
    key = paragraph_key(PARA_A)
    first = store.put({"key": key, "facts": [{"id": "x", "n": 1, "fact": "one"}]})
    second = store.put({"key": key, "facts": [{"id": "y", "n": 1, "fact": "other"}]})
    assert first == second and store.get(key)["facts"][0]["fact"] == "one"
    # Whitespace does not change the key; content does.
    assert paragraph_key(PARA_A.replace(" ", "  ")) == key != paragraph_key(PARA_B)


def test_incomplete_reply_is_asked_again_once_then_unjudged(tmp_path):
    replies = []

    def mark(prompt):
        replies.append(prompt)
        if len(replies) == 1:   # duplicate 1, misses 3
            return [{"n": 1, "status": "present", "note": ""}, {"n": 1, "status": "absent", "note": ""},
                    {"n": 2, "status": "partial", "note": "fewer sibs"}]
        return [{"n": 1, "status": "present", "note": ""}, {"n": 2, "status": "partial", "note": "x"}]  # still no 3

    gold = GoldEntry(mim="1", cited_pmids=["1"], allelic_variants=[
        GoldAllelicVariant(omim_id="1.1", paragraphs=[GoldParagraph(text=PARA_A, pmids=["1"])])])
    llm = FakeLLM(mark=mark)
    r = eval_gold_text_frozen(_entry("direct", "Sibs with seizures."), gold, LEVELS, llm, FactStore(tmp_path))
    assert len(replies) == 2 and "each number exactly once" in replies[1]
    para = r["paragraphs"][0]
    assert [f["status"] for f in para["facts"]] == ["present", "partial", "unjudged"]
    assert para["mark_attempts"] == 2 and r["unjudged"] == 1 and r["n_facts"] == 3 and r["n_judged"] == 2
    assert r["coverage"] == 0.75          # over the judged facts; partial counts half
    assert r["n_mark_retries"] == 1


def test_whole_draft_marks_against_every_paragraph(tmp_path):
    store, llm = FactStore(tmp_path), FakeLLM()
    # Seizures are stated, but under paper 2's citation only.
    entry = _entry("graph", "Unrelated.", "Three sibs had seizures.")
    cited = eval_gold_text_frozen(entry, _gold(), LEVELS, llm, store)
    whole = eval_gold_text_frozen(entry, _gold(), LEVELS, llm, store, whole=True)
    assert cited["paragraphs"][0]["present"] == 0 and whole["paragraphs"][0]["present"] == 1
    assert whole["draft_scope"] == "whole" and llm.n(MARK_WHOLE_SYSTEM) == 2


def _run(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "r"
    d = run / "200000"
    d.mkdir(parents=True)
    (d / "gold.json").write_text(_gold().model_dump_json())
    (d / "papers.json").write_text(json.dumps([{"pmid": "1", "content_level": "fulltext"},
                                               {"pmid": "2", "content_level": "abstract"}]))
    for s, entry in (("direct", _entry("direct", "Three sibs had seizures.", "A girl.")),
                     ("kg", _entry("kg", "Sibs.", "A girl with ataxia."))):
        (d / f"entry.{s}.json").write_text(entry.model_dump_json())
        (d / f"eval.{s}.json").write_text(json.dumps({"mim": "200000", "strategy": s, "faithfulness": {},
                                                      "gold_text": {"coverage": 0.5, "n_facts": 5, "paragraphs": []}}))
    return run


def test_rescore_writes_new_key_and_replicates_go_elsewhere(tmp_path):
    run, store = _run(tmp_path), FactStore(tmp_path / "store")
    llm = FakeLLM()
    summary = rescore_run(run, ["direct", "kg"], whole=True, llm=llm, store=store)
    d = run / "200000"
    ev = json.loads((d / "eval.direct.json").read_text())
    assert ev["gold_text"]["coverage"] == 0.5          # old score untouched
    assert ev["gold_text_frozen"]["n_facts"] == 6 and "gold_text_frozen_whole" in ev
    assert summary["means"]["kg"]["gold_text_frozen_n_facts"] == summary["means"]["direct"]["gold_text_frozen_n_facts"]
    gf = json.loads((d / "gold_facts.json").read_text())
    assert [p["text"] for p in gf["paragraphs"]] == [PARA_A, PARA_B]
    before = (d / "eval.direct.json").read_text()

    # A judge replicate: no split, marks to judge_<salt>.<strategy>.json, eval file unchanged.
    rep = FakeLLM(replicate="j1")
    rescore_run(run, ["direct"], llm=rep, store=store)
    assert rep.n(SPLIT_SYSTEM) == 0 and rep.n(MARK_SYSTEM) == 2
    assert (d / "eval.direct.json").read_text() == before
    judged = json.loads((d / judge_file("direct", "j1")).read_text())
    assert judged["replicate"] == "j1" and judged["gold_text_frozen"]["n_facts"] == 6
    assert not list(d.glob("eval.*.j1*.json")) and (run / "rescore.judge_j1.json").exists()


def test_splitter_never_salts_the_split(monkeypatch):
    class Dummy:
        def __init__(self, settings):
            self.settings = settings

    import aiomim.llm

    monkeypatch.setattr(aiomim.llm, "LLM", Dummy)
    from aiomim.config import get_settings
    from dataclasses import replace

    salted = SimpleNamespace(settings=replace(get_settings(), replicate="r9"))
    clone = facts.splitter(salted)
    assert clone.settings.replicate == "" and facts.splitter(salted) is clone
    unsalted = SimpleNamespace(settings=replace(get_settings(), replicate=""))
    assert facts.splitter(unsalted) is unsalted


def test_frozen_gaps_judge_availability_once_for_all_strategies(tmp_path):
    run, store = _run(tmp_path), FactStore(tmp_path / "store")
    llm = FakeLLM()
    rescore_run(run, ["direct", "kg"], llm=llm, store=store)
    papers = {"1": Paper(pmid="1", title="T", abstract="We report that three sibs had seizures." * 5),
              "2": Paper(pmid="2", title="Girl")}
    for s in ("direct", "kg"):
        summary = gaps_run(run, s, llm=llm, load=lambda d: papers, frozen=True, store=store)
        assert summary["frozen"] and summary["n_paragraphs"] == 2
    assert llm.n(GAPS_SYSTEM) == 2              # once per paragraph, not per strategy
    entry_gaps = json.loads((run / "200000" / "gaps.direct.frozen.json").read_text())
    missed = [f for p in entry_gaps["paragraphs"] for f in p["facts"]]
    assert {f["draft_status"] for f in missed} <= {"absent", "partial"}
    assert all(f["in_text"] in ("yes", "partly", "no", "unjudged") for f in missed)
    assert (run / "gaps.direct.frozen.md").exists() and not (run / "gaps.direct.md").exists()
    gf = json.loads((run / "200000" / "gold_facts.json").read_text())
    assert all("availability" in p for p in gf["paragraphs"])
    run_level = (run / "gaps.kg.frozen.json").read_text()
    assert "seizures" not in run_level                  # counts only


def test_export_drops_fact_lists_and_wording(tmp_path):
    run, store = _run(tmp_path), FactStore(tmp_path / "store")
    rescore_run(run, ["direct", "kg"], whole=True, llm=FakeLLM(), store=store)
    ev = json.loads((run / "200000" / "eval.direct.json").read_text())
    ev["gold_text_frozen"]["paragraphs"][0]["facts"][0]["note"] = "draft says two sibs"
    red = _redact(ev)
    for key in ("gold_text_frozen", "gold_text_frozen_whole"):
        for p in red[key]["paragraphs"]:
            assert all(set(f) == {"id", "status"} for f in p["facts"])
    out = tmp_path / "export"
    export_run(run, out)
    assert not (out / "200000" / "gold_facts.json").exists()
    blob = "".join(p.read_text() for p in (out / "200000").glob("*"))
    for phrase in [*SPLITS[PARA_A], *SPLITS[PARA_B], "Smith et al.", "draft says two sibs"]:
        assert phrase not in blob
    exported = json.loads((out / "200000" / "eval.direct.json").read_text())
    assert exported["gold_text_frozen"]["n_facts"] == 6
