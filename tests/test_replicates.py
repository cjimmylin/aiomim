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
