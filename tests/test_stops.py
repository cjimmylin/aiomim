"""Replies stopped by the model's safety filter, and empty writer replies.

Such a reply comes back from the CLI as a success with an empty structure. It must
be recorded as "no draft", never scored as a draft that says nothing.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from aiomim import compare, pipeline
from aiomim.config import get_settings
from aiomim.llm import EMPTY_REPLY, LLM, SAFETY_STOP, LLMRefusal
from aiomim.models import GeneratedEntry, Seed
from aiomim.synthesize import has_content


class _Intro(BaseModel):
    text: str = ""


class _Draft(BaseModel):
    intro: _Intro = _Intro()
    sections: list[str] = []


class _Backend:
    """Stands in for the CLI: hands out the scripted (data, meta) pairs in order."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete(self, **_):
        self.calls += 1
        return self.replies.pop(0)


def _llm(tmp_path: Path, replies) -> LLM:
    llm = LLM(replace(get_settings(), home=tmp_path))
    llm.backend = _Backend(replies)
    return llm


META = {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.01, "seconds": 1.0, "turns": 1}
EMPTY = {"intro": {"text": ""}, "sections": []}
FULL = {"intro": {"text": "A disorder."}, "sections": ["x"]}


def test_has_content():
    assert has_content(_Draft.model_validate(FULL))
    assert has_content(_Draft(intro=_Intro(text="Only an intro.")))
    assert not has_content(_Draft.model_validate(EMPTY))


def test_safety_stop_raises_and_is_cached(tmp_path):
    llm = _llm(tmp_path, [(EMPTY, {**META, "safety_stops": 1})])
    with pytest.raises(LLMRefusal, match="safety filter"):
        llm.call("synthesize", "sys", "prompt", _Draft, accept=has_content)
    # Asked again, the stop comes from the cache: no second request is paid for.
    with pytest.raises(LLMRefusal) as again:
        llm.call("synthesize", "sys", "prompt", _Draft, accept=has_content)
    assert str(again.value) == SAFETY_STOP
    assert llm.backend.calls == 1


def test_cached_empty_reply_is_asked_again(tmp_path):
    # An empty entry cached before stops were recorded: valid, but not acceptable.
    llm = _llm(tmp_path, [(EMPTY, META), (FULL, META)])
    assert llm.call("synthesize", "sys", "prompt", _Draft).sections == []      # no check: cached as is
    assert llm.backend.calls == 1
    llm.backend.replies = [(FULL, META)]
    reply = llm.call("synthesize", "sys", "prompt", _Draft, accept=has_content)
    assert reply.sections == ["x"] and llm.backend.calls == 2
    # The good reply replaced the empty one in the cache.
    assert llm.call("synthesize", "sys", "prompt", _Draft, accept=has_content).sections == ["x"]
    assert llm.backend.calls == 2


def test_two_empty_replies_are_a_refusal(tmp_path):
    llm = _llm(tmp_path, [(EMPTY, META), (EMPTY, META)])
    with pytest.raises(LLMRefusal) as exc:
        llm.call("synthesize", "sys", "prompt", _Draft, accept=has_content)
    assert str(exc.value) == EMPTY_REPLY and llm.backend.calls == 2


def test_stopped_writer_leaves_a_marked_entry(tmp_path, monkeypatch):
    def stopped(name, seed, papers, llm, out_dir):
        raise LLMRefusal(SAFETY_STOP)

    monkeypatch.setattr(pipeline, "run_strategy", stopped)
    cfg = pipeline.RunConfig(run="t", strategies=("direct",))
    entries, _ = pipeline.build_entries(Seed(mim="100001", title="EXAMPLE SYNDROME"), [], cfg, llm=object(),
                                        out_dir=tmp_path)
    entry = entries["direct"]
    assert entry.meta["stopped"] == SAFETY_STOP and not entry.all_paragraphs()
    saved = GeneratedEntry.model_validate(json.loads((tmp_path / "entry.direct.json").read_text()))
    assert saved.meta["stopped"] == SAFETY_STOP
    assert "No entry was written" in (tmp_path / "entry.direct.md").read_text()


def _eval(coverage: float, stopped: str = "", mim: str = "100001") -> dict:
    out = {"mim": mim, "faithfulness": {"n_claims": 10, "supported": 9, "supported_rate": 0.9, "error_rate": 0.0},
           "gold_text": {"coverage": coverage, "n_facts": 10, "present": int(coverage * 10), "partial": 0,
                         "absent": 10 - int(coverage * 10), "contradicted": 0, "paragraphs": []}}
    if stopped:
        out["stopped"] = stopped
    return out


def test_comparison_leaves_stopped_entries_out(tmp_path):
    run = tmp_path / "run"
    for folder, kg, direct in (("100001", _eval(0.6), _eval(0.5)),
                               ("100002", _eval(0.7, mim="100002"),
                                _eval(0.0, stopped=SAFETY_STOP, mim="100002"))):
        (run / folder).mkdir(parents=True)
        (run / folder / "eval.kg.json").write_text(json.dumps(kg))
        (run / folder / "eval.direct.json").write_text(json.dumps(direct))
    evals = compare.load_evals(run)
    assert set(evals["kg"]) == {"100001", "100002"} and set(evals["direct"]) == {"100001"}
    assert compare.stopped_entries(run) == {"direct": {"100002": SAFETY_STOP}}
    result = compare.compare_strategies(run)
    # Both strategies are compared on the one entry both of them wrote.
    assert result["n_entries"] == 1 and result["stopped"] == {"direct": ["100002"]}
    assert "Left out: 1 entries" in compare.strategies_markdown(result)


def test_run_summary_lists_stopped_entries_apart(tmp_path, monkeypatch):
    run = tmp_path / "run"
    (run / "100002").mkdir(parents=True)
    (run / "100002" / "eval.direct.json").write_text(json.dumps(_eval(0.0, stopped=SAFETY_STOP, mim="100002")))
    summary = pipeline.collect_summary(run)
    assert summary["stopped"] == {"direct": ["100002"]}
    assert "direct" not in summary["strategies"]     # nothing was averaged for it
