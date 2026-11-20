"""Stopped entries put back: counted as zero, or replaced by the draft the revision would have revised."""

import pytest

from aiomim import directplus as dp


def _measures(v):
    return {key: v for key, *_ in dp.MEASURES} | {f"{key}_n": 1 for key, *_ in dp.MEASURES}


def _fake(monkeypatch, status, scores):
    monkeypatch.setattr(dp, "completion", lambda run_dir, mims, arms: status)
    monkeypatch.setattr(dp, "entry_measures", lambda run_dir, m, a: _measures(scores[a][m]))


def _status(mims, lost=None):
    lost = lost or {}
    return {a: {m: ("no_draft" if m in lost.get(a, ()) else "complete") for m in mims} for a in dp.ALL_ARMS}


def test_as_zero_and_draft_kept(monkeypatch, tmp_path):
    mims = ["1", "2"]
    scores = {a: {"1": 0.5, "2": 0.6} for a in dp.ALL_ARMS}
    scores["direct_checklist"] = {"1": 0.55, "2": 0.7}
    scores["direct_checklist_complete"] = {"1": 0.6}           # entry 2 lost to a stopped revision
    _fake(monkeypatch, _status(mims, {"direct_checklist_complete": ["2"]}), scores)
    r = dp.missing_sensitivity(tmp_path, mims)
    row = r["measures"]["all"]
    assert r["lost_to_a_stop"] == {"direct_checklist_complete": ["2"]}
    assert row["as_zero"]["direct_checklist_complete"]["mean_over_entries"] == pytest.approx(0.3)
    # D4's lost entry gets D1's draft (the checklist draft the revision would have revised)
    assert row["draft_kept"]["direct_checklist_complete"]["mean_over_entries"] == pytest.approx(0.65)
    assert row["draft_kept"]["direct_checklist_complete"]["versus_baseline"]["n"] == 2


def test_arm_without_a_draft_to_keep_counts_zero_under_both(monkeypatch, tmp_path):
    mims = ["1"]
    scores = {a: {"1": 0.5} for a in dp.ALL_ARMS}
    scores["direct_ensemble"] = {}
    _fake(monkeypatch, _status(mims, {"direct_ensemble": ["1"]}), scores)
    r = dp.missing_sensitivity(tmp_path, mims)
    for rule in dp.SENSITIVITY_RULES:
        assert r["measures"]["all"][rule]["direct_ensemble"]["mean_over_entries"] == 0.0


def test_incomplete_baseline_is_refused(monkeypatch, tmp_path):
    status = _status(["1"], {"direct": ["1"]})
    _fake(monkeypatch, status, {a: {"1": 0.5} for a in dp.ALL_ARMS})
    with pytest.raises(RuntimeError):
        dp.missing_sensitivity(tmp_path, ["1"])
