"""Replicate runs: the cache-key salt and the run-to-run variance analysis."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from aiomim.cache import stable_hash
from aiomim.config import get_settings
from aiomim.llm import LLM, cache_key, schema_for


class _Out(BaseModel):
    text: str


SCHEMA = schema_for(_Out)
MODEL, EFFORT, SYSTEM, PROMPT = "claude-opus-5-5", "high", "SYS", "PROMPT"
TOOLS, WORKSPACE = ("Read", "Grep"), "ws123"

# Keys computed with the code as it was before the replicate salt existed:
#   no tools: stable_hash(model, effort, system, prompt, schema)
#   tools:    stable_hash(model, effort, system, prompt, schema, list(tools), workspace_key)
KEY_NO_TOOLS = "7f95152d6eb4c4f2ca9a8b1d1c009ed9673036d60ce2c06937d8d5c2035db1d1"
KEY_TOOLS = "8a45680773d0e4f18ee9ea6f69bd8958acc7b3b5881542a62d08243e65e246fa"


def test_unsalted_keys_are_unchanged():
    # The formula as it stood, and the fixed values it produced, both match the new function.
    assert stable_hash(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA) == KEY_NO_TOOLS
    assert stable_hash(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, list(TOOLS), WORKSPACE) == KEY_TOOLS
    assert cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA) == KEY_NO_TOOLS
    assert cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, replicate="") == KEY_NO_TOOLS
    assert cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, TOOLS, WORKSPACE) == KEY_TOOLS
    assert cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, TOOLS, WORKSPACE, replicate="") == KEY_TOOLS


def test_salt_changes_every_key():
    keys = {
        cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, replicate="r2"),
        cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, replicate="r3"),
        cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, TOOLS, WORKSPACE, replicate="r2"),
        cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, TOOLS, WORKSPACE, replicate="r3"),
    }
    assert len(keys) == 4 and not keys & {KEY_NO_TOOLS, KEY_TOOLS}


def test_settings_read_the_variable(monkeypatch):
    get_settings.cache_clear()
    try:
        monkeypatch.delenv("AIOMIM_REPLICATE", raising=False)
        assert get_settings().replicate == ""
        get_settings.cache_clear()
        monkeypatch.setenv("AIOMIM_REPLICATE", "r2")
        assert get_settings().replicate == "r2"
    finally:
        monkeypatch.delenv("AIOMIM_REPLICATE", raising=False)
        get_settings.cache_clear()


class _Backend:
    def __init__(self):
        self.calls = 0

    def complete(self, **_):
        self.calls += 1
        return {"text": f"reply {self.calls}"}, {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}


def _llm(tmp_path: Path, replicate: str) -> LLM:
    settings = replace(get_settings(), home=tmp_path, replicate=replicate,
                       models={"synthesize": MODEL}, efforts={"synthesize": EFFORT})
    llm = LLM(settings)
    llm.backend = _Backend()
    return llm


@pytest.mark.parametrize("tools,expected", [((), KEY_NO_TOOLS), (TOOLS, KEY_TOOLS)])
def test_call_caches_under_the_old_key_without_salt(tmp_path, tools, expected):
    llm = _llm(tmp_path, "")
    llm.call("synthesize", SYSTEM, PROMPT, _Out, tools=tools, workspace_key=WORKSPACE if tools else "")
    assert llm.cache.path(expected).exists()


def test_salted_run_calls_afresh_and_caches_apart(tmp_path):
    base = _llm(tmp_path, "")
    first = base.call("synthesize", SYSTEM, PROMPT, _Out)
    again = base.call("synthesize", SYSTEM, PROMPT, _Out)
    assert base.backend.calls == 1 and again == first

    salted = _llm(tmp_path, "r2")
    other = salted.call("synthesize", SYSTEM, PROMPT, _Out)
    assert salted.backend.calls == 1 and other.text == "reply 1"
    salted.call("synthesize", SYSTEM, PROMPT, _Out)
    assert salted.backend.calls == 1          # cached under its own salt
    key = cache_key(MODEL, EFFORT, SYSTEM, PROMPT, SCHEMA, replicate="r2")
    assert salted.cache.path(key).exists() and base.cache.path(KEY_NO_TOOLS).exists()


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

from aiomim.replicates import analyse, completed_in_full, replicates_markdown, variance_components  # noqa: E402


def test_variance_components_balanced_table():
    # Entry effects 0 and 1; run noise of +-0.1 around them.
    matrix = [[0.0, 0.1, -0.1], [1.0, 1.1, 0.9]]
    c = variance_components(matrix)
    assert c["within_sd"] == pytest.approx(0.1)
    # MSB = 3 * var([0, 1]) = 1.5, MSW = 0.01 -> between = (1.5 - 0.01) / 3
    assert c["between_sd"] == pytest.approx(((1.5 - 0.01) / 3) ** 0.5)
    assert c["within_share"] == pytest.approx(0.01 / (0.01 + (1.5 - 0.01) / 3))
    no_noise = variance_components([[0.2, 0.2], [0.4, 0.4]])
    assert no_noise["within_sd"] == 0 and no_noise["within_share"] == 0


def _eval(mim: str, coverage: float, stopped: str = "") -> dict:
    e = {"mim": mim, "title": "T", "gold_text": {"coverage": coverage},
         "faithfulness": {"supported_rate": 0.9, "before_repair": {"error_rate": 0.01}},
         "synopsis": {"exact": {"f1": 0.3}}, "variants": {"recall": 0.5}, "genes": {"f1": 1.0},
         "inheritance": {"match": True}}
    if stopped:
        e["stopped"] = stopped
    return e


def _write_run(root: Path, name: str, scores: dict[str, dict[str, float]], stopped=()) -> Path:
    run = root / name
    for strategy, by_mim in scores.items():
        for mim, cov in by_mim.items():
            d = run / mim
            d.mkdir(parents=True, exist_ok=True)
            why = "stopped" if (mim, strategy) in stopped else ""
            (d / f"eval.{strategy}.json").write_text(json.dumps(_eval(mim, cov, why)))
            (d / "usage.json").write_text(json.dumps({"total": {"calls": 4, "cached": 1, "list_price_usd": 0.5},
                                                      "by_strategy": {}}))
    return run


def test_analyse_three_replicates(tmp_path):
    mims = [str(100000 + i) for i in range(6)]
    runs = []
    for j, noise in enumerate((0.0, 0.02, -0.02)):
        direct = {m: 0.4 + 0.05 * i + noise for i, m in enumerate(mims)}
        kg = {m: v - 0.01 for m, v in direct.items()}
        stopped = {(mims[0], "kg")} if j == 2 else set()
        runs.append(_write_run(tmp_path, f"r{j + 1}", {"direct": direct, "kg": kg}, stopped))
    r = analyse(runs)
    cov = r["strategies"]["direct"]["gold_fact_coverage"]
    assert cov["n_entries"] == 6 and cov["within_sd"] == pytest.approx(0.02)
    assert cov["mean_range"] == pytest.approx(0.04)
    assert r["entries"]["kg"] == 5 and r["paired_entries"] == 5   # the stopped draft is left out
    paired = r["paired"]["gold_fact_coverage"]
    assert all(x["difference"] == pytest.approx(-0.01) for x in paired["replicates"])
    assert paired["difference_within_sd"] == pytest.approx(0.0, abs=1e-12)
    assert r["usage"]["r1"]["fresh_calls"] == 6 * (4 - 1)
    md = replicates_markdown(r)
    assert "salts every model call" in md and "Evidence graph minus direct reading" in md


def test_completed_in_full(tmp_path):
    d = tmp_path / "100001"
    d.mkdir()
    for s in ("direct", "kg"):
        (d / f"eval.{s}.json").write_text(json.dumps(_eval("100001", 0.5)))
    (d / "entry.kg.json").write_text(json.dumps({"meta": {"extraction": {"papers_failed": []}}}))
    assert completed_in_full(d)
    (d / "entry.kg.json").write_text(json.dumps({"meta": {"extraction": {"papers_failed": ["1"]}}}))
    assert not completed_in_full(d)
    (d / "entry.kg.json").write_text(json.dumps({"meta": {"extraction": {"papers_failed": []}}}))
    (d / "eval.direct.json").write_text(json.dumps(_eval("100001", 0.5, "stopped")))
    assert not completed_in_full(d)
