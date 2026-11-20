"""The adopted default strategy: routing by access, and a stopped revision keeping the draft."""

from types import SimpleNamespace

import pytest

from aiomim.llm import LLMLimitReached, LLMRefusal
from aiomim.strategies import STRATEGIES, recommended


def _paper(level):
    return SimpleNamespace(content_level=level)


def _entry():
    return SimpleNamespace(meta={})


def _seed():
    return SimpleNamespace(mim="100000", title="TEST")


def test_registered_and_not_in_all():
    from aiomim.strategies import parse_strategies
    assert "recommended" in STRATEGIES
    assert "recommended" not in parse_strategies("all")


def test_no_fulltext_uses_direct_reading(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(recommended.direct, "run", lambda *a, **k: calls.append("direct") or _entry())
    monkeypatch.setattr(recommended.direct, "draft", lambda *a, **k: pytest.fail("checklist draft not expected"))
    entry = recommended.run(_seed(), [_paper("abstract"), _paper("title")], object(), tmp_path)
    assert calls == ["direct"]
    assert entry.meta["recommended"]["route"] == "direct reading"


def test_fulltext_uses_checklist_and_completeness_pass(monkeypatch, tmp_path):
    seen = {}

    def fake_draft(seed, papers, llm, system):
        seen["system"] = system
        return "RAW", {}, {}

    def fake_pass(seed, papers, llm, out_dir, raw, gene_facts, meta, **kw):
        seen.update(kw)
        e = _entry()
        e.meta[kw["strategy"]] = {"omissions_kept": 3}
        return e

    monkeypatch.setattr(recommended.direct, "draft", fake_draft)
    monkeypatch.setattr(recommended, "completeness_pass", fake_pass)
    entry = recommended.run(_seed(), [_paper("abstract"), _paper("fulltext")], object(), tmp_path)
    assert seen["system"] == recommended.CHECKLIST_SYSTEM
    assert seen["revise"] == recommended.REVISE_CHECKLIST_SYSTEM
    assert seen["strategy"] == "recommended"
    assert entry.meta["recommended"]["route"] == "checklist draft with the completeness pass"
    assert entry.meta["recommended"]["omissions_kept"] == 3


def test_stopped_revision_keeps_checklist_draft(monkeypatch, tmp_path):
    kept = {}
    monkeypatch.setattr(recommended.direct, "draft", lambda *a, **k: ("RAW", {}, {}))

    def stopped(*a, **k):
        raise LLMRefusal("the model's safety filter stopped this reply")

    def fake_to_entry(seed, papers, raw, llm, strategy, gene_facts, meta):
        kept["raw"], kept["strategy"] = raw, strategy
        return _entry()

    monkeypatch.setattr(recommended, "completeness_pass", stopped)
    monkeypatch.setattr(recommended, "draft_to_entry", fake_to_entry)
    entry = recommended.run(_seed(), [_paper("fulltext")], object(), tmp_path)
    assert kept == {"raw": "RAW", "strategy": "recommended"}
    assert entry.meta["recommended"]["route"] == "checklist draft, unrevised"


def test_usage_limit_is_not_swallowed(monkeypatch, tmp_path):
    monkeypatch.setattr(recommended.direct, "draft", lambda *a, **k: ("RAW", {}, {}))

    def limit(*a, **k):
        raise LLMLimitReached("usage limit")

    monkeypatch.setattr(recommended, "completeness_pass", limit)
    with pytest.raises(LLMLimitReached):
        recommended.run(_seed(), [_paper("fulltext")], object(), tmp_path)


def test_stopped_writer_still_leaves_no_draft(monkeypatch, tmp_path):
    def stopped(*a, **k):
        raise LLMRefusal("the model's safety filter stopped this reply")

    monkeypatch.setattr(recommended.direct, "draft", stopped)
    with pytest.raises(LLMRefusal):
        recommended.run(_seed(), [_paper("fulltext")], object(), tmp_path)
