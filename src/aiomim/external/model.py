"""The project's model, reached for free-text and structured completions with the project's cache.

`llm.LLM.call` always asks for a JSON Schema and validates the reply against a pydantic
model; the adapter also needs plain free-text completions. Rather than change
`llm.py`, this module adds a free-text call on a subclass of the same `ClaudeCode`
backend: the identical `claude -p` command line minus `--json-schema`, the same
neutral working directory, the same error classification, the same usage fields.
Structured completions go through `ClaudeCode.complete` unchanged.

Caching: replies are stored in the project's disk cache (`<home>/cache/llm`) under a
key that holds a namespace, the model, the effort, the system prompt, the prompt, the
schema (or None) and the replicate salt. The namespace keeps these entries apart from
`LLM.call`'s keys, which are never produced here.

A reply stopped by the model's safety filter (the CLI's `safety_stops` count, or
`stop_reason == "refusal"`) is cached as a stop and is never retried.
"""

from __future__ import annotations

import json
import logging
import random
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ..cache import DiskCache, stable_hash
from ..config import Settings, get_settings
from ..llm import ClaudeCode, LLMError, LLMLimitReached, LLMRefusal, _classify

log = logging.getLogger(__name__)

CACHE_NAMESPACE = "aiomim.external.shim/v1"
DEFAULT_EFFORT = "medium"     # the effort the project uses for per-paper extraction (config.DEFAULT_EFFORT["extract"])
DEFAULT_SYSTEM = "You are a helpful assistant."   # used only when a request carries no system message


class TextClaudeCode(ClaudeCode):
    """`ClaudeCode` plus a free-text completion (no schema)."""

    def complete_text(self, *, system: str, prompt: str, model: str, effort: str,
                      timeout_s: int | None = None) -> tuple[str, dict[str, Any]]:
        cmd = [
            self.settings.claude_bin, "-p",
            "--model", model,
            "--effort", effort,
            "--output-format", "json",
            "--system-prompt", system,
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "",
            "--disable-slash-commands",
            "--no-session-persistence",
        ]
        timeout_s = timeout_s or self.settings.llm_timeout_s
        started = time.time()
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=self._cwd,
                                  timeout=timeout_s)
        except FileNotFoundError as exc:
            raise LLMError(f"Claude Code CLI not found ({self.settings.claude_bin!r})") from exc
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"claude -p exceeded {timeout_s}s") from exc
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            detail = (proc.stderr or proc.stdout or "").strip()[:500]
            raise _classify(f"claude -p returned no JSON (exit {proc.returncode}): {detail}")
        if result.get("stop_reason") == "refusal":
            raise LLMRefusal(str(result.get("result", ""))[:300] or "model refused")
        if result.get("is_error"):
            raise _classify(f"claude -p error ({result.get('api_error_status')}): {str(result.get('result'))[:500]}")
        return str(result.get("result") or ""), _meta(result, model, effort, started)


def _meta(result: dict[str, Any], model: str, effort: str, started: float) -> dict[str, Any]:
    """The same usage fields `ClaudeCode.complete` reports."""
    usage = result.get("usage") or {}
    return {
        "model": model, "effort": effort,
        "input_tokens": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": result.get("total_cost_usd", 0.0),
        "seconds": round(time.time() - started, 2),
        "turns": result.get("num_turns", 1),
        "safety_stops": int(result.get("safety_stops") or 0),
    }


@dataclass
class Completion:
    """One answered request: text (or parsed JSON for structured calls) and how it was obtained."""

    text: str
    meta: dict[str, Any]
    cached: bool
    stopped: bool = False          # the safety filter stopped the reply (content is empty)
    json_valid: bool | None = None  # for JSON-mode requests: whether the final reply parses
    attempts: int = 1
    key: str = ""
    notes: list[str] = field(default_factory=list)


def shim_cache_key(model: str, effort: str, system: str, prompt: str, schema: dict[str, Any] | None,
                   json_mode: bool, replicate: str = "") -> str:
    parts: list[Any] = [CACHE_NAMESPACE, model, effort, system, prompt, schema, bool(json_mode)]
    if replicate:
        parts.append({"replicate": replicate})
    return stable_hash(*parts)


def parse_json_reply(text: str) -> Any:
    """The JSON value in a reply: the whole text, or the body of one ```json fence. Raises ValueError."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return json.loads(s)


class ProjectModel:
    """Free-text, JSON-mode and schema-constrained completions of the project's one model, cached.

    `backend` may be replaced (tests): it needs `complete_text(system=, prompt=, model=, effort=)`
    and `complete(system=, prompt=, schema=, model=, effort=)`.
    """

    def __init__(self, settings: Settings | None = None, *, effort: str = DEFAULT_EFFORT, backend=None,
                 cache: DiskCache | None = None, max_concurrency: int = 6):
        self.settings = settings or get_settings()
        self.model = self.settings.model_for("extract")
        self.effort = effort
        self.backend = backend or TextClaudeCode(self.settings)
        self.cache = cache or DiskCache(self.settings.llm_cache)
        # Cap on simultaneous model calls; cache hits never wait for a slot.
        self.slots = threading.BoundedSemaphore(max(1, max_concurrency))
        self._inflight: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self._inflight.setdefault(key, threading.Lock())

    def complete(self, system: str, prompt: str, *, schema: dict[str, Any] | None = None,
                 json_mode: bool = False) -> Completion:
        """One completion. `schema`: constrained by the CLI's structured output; `json_mode`: free
        text that must parse as JSON (asked once more if it does not). Raises LLMLimitReached and
        LLMError (after transient retries); a safety stop comes back as `stopped`."""
        key = shim_cache_key(self.model, self.effort, system, prompt, schema, json_mode, self.settings.replicate)
        with self._lock(key):   # identical concurrent requests make one call
            hit = self.cache.get_json(key)
            if hit is not None:
                meta = hit.get("meta", {})
                return Completion(text=hit.get("text", ""), meta=meta, cached=True,
                                  stopped=bool(hit.get("stopped")), json_valid=hit.get("json_valid"),
                                  attempts=hit.get("attempts", 1), key=key)
            done = self._fresh(system, prompt, schema, json_mode)
            done.key = key
            self.cache.put_json(key, {"text": done.text, "meta": done.meta, "stopped": done.stopped,
                                      "json_valid": done.json_valid, "attempts": done.attempts,
                                      "notes": done.notes})
            return done

    def _call(self, system: str, prompt: str, schema: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
        with self.slots:
            return self._call_unlimited(system, prompt, schema)

    def _call_unlimited(self, system: str, prompt: str, schema: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
        if schema is not None:
            data, meta = self.backend.complete(system=system, prompt=prompt, schema=schema, model=self.model,
                                               effort=self.effort)
            return json.dumps(data, ensure_ascii=False), meta
        return self.backend.complete_text(system=system, prompt=prompt, model=self.model, effort=self.effort)

    def _fresh(self, system: str, prompt: str, schema: dict[str, Any] | None, json_mode: bool) -> Completion:
        """Transient failures are retried with back-off as `LLM.call` does; a malformed reply
        (no structured output, or JSON mode that does not parse) is asked again once."""
        total: dict[str, Any] = {}
        notes: list[str] = []
        attempts = 0
        last_text = ""
        malformed = 0
        for transient in range(5):
            try:
                attempts += 1
                text, meta = self._call(system, prompt, schema)
            except LLMRefusal as exc:     # stop_reason == "refusal": a stop, never retried
                meta = {"model": self.model, "effort": self.effort, "safety_stops": 1,
                        "refusal": str(exc)[:300]}
                return Completion("", _add(total, meta), cached=False, stopped=True, attempts=attempts, notes=notes)
            except LLMLimitReached:
                raise
            except (ConnectionError, TimeoutError) as exc:
                delay = min(240.0, 20.0 * 2**transient) + random.uniform(0, 5)
                log.warning("shim: transient model failure (%s); retrying in %.0fs", exc, delay)
                notes.append(f"transient: {str(exc)[:200]}")
                time.sleep(delay)
                continue
            except ValueError as exc:     # schema call answered without structured output
                malformed += 1
                notes.append(f"malformed: {str(exc)[:200]}")
                if malformed >= 2:
                    return Completion("", total, cached=False, json_valid=False, attempts=attempts, notes=notes)
                continue
            total = _add(total, meta)
            if meta.get("safety_stops"):
                return Completion("", total, cached=False, stopped=True, attempts=attempts, notes=notes)
            if not json_mode or schema is not None:
                return Completion(text, total, cached=False, json_valid=True if schema is not None else None,
                                  attempts=attempts, notes=notes)
            last_text = text
            try:
                parse_json_reply(text)
                return Completion(text, total, cached=False, json_valid=True, attempts=attempts, notes=notes)
            except ValueError:
                malformed += 1
                notes.append("reply did not parse as JSON")
                if malformed >= 2:
                    return Completion(last_text, total, cached=False, json_valid=False, attempts=attempts,
                                      notes=notes)
        raise LLMError(f"shim: giving up after repeated failures: {notes[-1] if notes else ''}")


def _add(total: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Sum the usage of several attempts (a re-asked JSON reply costs two calls)."""
    if not total:
        return dict(meta)
    out = dict(total)
    for k in ("input_tokens", "output_tokens", "cost_usd", "seconds", "turns", "safety_stops"):
        out[k] = (out.get(k) or 0) + (meta.get(k) or 0)
    return out
