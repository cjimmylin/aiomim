"""LLM access through the Claude Code CLI in headless mode.

The pipeline runs on a Claude subscription rather than an API key: every model
call is one `claude -p` subprocess with tools switched off, our own system
prompt, and a JSON Schema the reply must satisfy. `claude` must be installed and
logged in (`claude` then `/login`, or `claude setup-token` for a headless box).

Three things are layered on top of the raw call:

* a disk cache keyed on (model, effort, system prompt, user prompt, schema), so
  re-running a stage costs nothing and results are reproducible;
* validation of the reply against a pydantic model, with one retry;
* a usage ledger per stage, reported at the end of a run.
"""

from __future__ import annotations

import json
import logging
import random
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence, TypeVar

from pydantic import BaseModel, ValidationError

from .cache import DiskCache, stable_hash
from .config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The model call failed and retrying did not help."""


class LLMRefusal(LLMError):
    """The model declined the request (stop_reason == 'refusal')."""


class LLMLimitReached(LLMError):
    """The subscription's usage limit is exhausted; waiting is the only fix."""


# --------------------------------------------------------------------------- #
# JSON Schema from pydantic
# --------------------------------------------------------------------------- #


def schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """A self-contained JSON Schema for `model`: refs inlined, objects closed."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(defs[node["$ref"].rsplit("/", 1)[-1]])
        out = {k: walk(v) for k, v in node.items() if k not in ("title", "default")}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"])
        return out

    return walk(raw)


# --------------------------------------------------------------------------- #
# Usage accounting
# --------------------------------------------------------------------------- #


@dataclass
class StageUsage:
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    list_price_usd: float = 0.0
    seconds: float = 0.0
    # What these calls cost when made, whether or not this pass read them from cache.
    # A cached re-run spends nothing, but the method still costs this much to run fresh.
    full_input_tokens: int = 0
    full_output_tokens: int = 0
    full_list_price_usd: float = 0.0
    full_seconds: float = 0.0
    turns: int = 0


_SUMMED = ("calls", "cached", "input_tokens", "output_tokens", "list_price_usd", "seconds",
           "full_input_tokens", "full_output_tokens", "full_list_price_usd", "full_seconds", "turns")


@dataclass
class UsageLedger:
    stages: dict[str, StageUsage] = field(default_factory=dict)
    phase: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, stage: str, *, cached: bool, meta: dict[str, Any]) -> None:
        key = f"{self.phase}/{stage}" if self.phase else stage
        with self._lock:
            s = self.stages.setdefault(key, StageUsage())
            s.calls += 1
            s.full_input_tokens += int(meta.get("input_tokens", 0))
            s.full_output_tokens += int(meta.get("output_tokens", 0))
            s.full_list_price_usd += float(meta.get("cost_usd", 0.0))
            s.full_seconds += float(meta.get("seconds", 0.0))
            s.turns += int(meta.get("turns", 1) or 1)
            if cached:
                s.cached += 1
                return
            s.input_tokens += int(meta.get("input_tokens", 0))
            s.output_tokens += int(meta.get("output_tokens", 0))
            s.list_price_usd += float(meta.get("cost_usd", 0.0))
            s.seconds += float(meta.get("seconds", 0.0))

    def summary(self) -> dict[str, Any]:
        with self._lock:
            out = {name: vars(s).copy() for name, s in sorted(self.stages.items())}
        out["total"] = {key: round(sum(s[key] for s in out.values()), 4) for key in _SUMMED}
        return out


# --------------------------------------------------------------------------- #
# The Claude Code backend
# --------------------------------------------------------------------------- #

_LIMIT_MARKERS = ("usage limit", "limit reached", "out of extra usage", "quota")
_TRANSIENT_MARKERS = ("overloaded", "rate limit", "rate_limit", "timeout", "timed out", "529", "503", "502", "500")


class ClaudeCode:
    """One-shot structured completions via `claude -p`."""

    def __init__(self, settings: Settings):
        self.settings = settings
        # A neutral, empty working directory: no project CLAUDE.md, no repo context.
        self._cwd = tempfile.mkdtemp(prefix="aiomim-llm-")

    def complete(
        self, *, system: str, prompt: str, schema: dict[str, Any], model: str, effort: str,
        tools: tuple[str, ...] = (), workdir: str | None = None, timeout_s: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """One structured completion.

        With no `tools` this is a single model call. With `tools` (read-only file
        tools such as Read, Grep, Glob) it is an agent session: the model works in
        `workdir`, calling tools for as many turns as it needs, and the schema
        applies to its final answer. `--restricted` confines the file tools to that
        directory and removes anything that could run code or reach the network.
        """
        cmd = [
            self.settings.claude_bin, "-p",
            "--model", model,
            "--effort", effort,
            "--output-format", "json",
            "--system-prompt", system,
            "--json-schema", json.dumps(schema),
            # No MCP servers, no user/project settings, no skills, nothing written
            # to the session history.
            "--tools", ",".join(tools),
            "--strict-mcp-config",
            "--setting-sources", "",
            "--disable-slash-commands",
            "--no-session-persistence",
        ]
        if tools:
            cmd.append("--restricted")
        timeout_s = timeout_s or self.settings.llm_timeout_s
        started = time.time()
        try:
            proc = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True,
                cwd=workdir or self._cwd, timeout=timeout_s,
            )
        except FileNotFoundError as exc:
            raise LLMError(
                f"Claude Code CLI not found ({self.settings.claude_bin!r}). Install it and log in "
                "with your Claude subscription, or set AIOMIM_CLAUDE_BIN."
            ) from exc
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

        data = result.get("structured_output")
        if data is None:
            # The schema is enforced through a tool call; a plain-text reply means the
            # model skipped it. Accept the text if it happens to be the JSON we asked for.
            try:
                data = json.loads(result.get("result") or "")
            except json.JSONDecodeError:
                raise ValueError("model replied without structured output")

        usage = result.get("usage") or {}
        meta = {
            "model": model,
            "effort": effort,
            "input_tokens": usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_usd": result.get("total_cost_usd", 0.0),
            "seconds": round(time.time() - started, 2),
            "turns": result.get("num_turns", 1),
        }
        return data, meta


def _classify(message: str) -> Exception:
    low = message.lower()
    if any(marker in low for marker in _LIMIT_MARKERS):
        return LLMLimitReached(message)
    if any(marker in low for marker in _TRANSIENT_MARKERS):
        return ConnectionError(message)
    return LLMError(message)


# --------------------------------------------------------------------------- #
# Public interface
# --------------------------------------------------------------------------- #


class LLM:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.backend = ClaudeCode(self.settings)
        self.cache = DiskCache(self.settings.llm_cache)
        self.usage = UsageLedger()

    def call(
        self, stage: str, system: str, prompt: str, output: type[T], *, use_cache: bool = True,
        tools: tuple[str, ...] = (), workdir: str | None = None, workspace_key: str = "",
    ) -> T:
        """Run one structured completion for `stage` and validate it as `output`.

        `tools` and `workdir` turn the call into an agent session (see
        `ClaudeCode.complete`); `workspace_key` must then identify the contents of
        the working directory, so that the cache distinguishes one library of papers
        from another.
        """
        model = self.settings.model_for(stage)
        effort = self.settings.effort_for(stage)
        schema = schema_for(output)
        key = (stable_hash(model, effort, system, prompt, schema, list(tools), workspace_key) if tools
               else stable_hash(model, effort, system, prompt, schema))

        if use_cache:
            hit = self.cache.get_json(key)
            if hit is not None:
                try:
                    parsed = output.model_validate(hit["data"])
                except ValidationError:
                    parsed = None
                if parsed is not None:
                    self.usage.add(stage, cached=True, meta=hit.get("meta", {}))
                    return parsed

        last: Exception | None = None
        for attempt in range(5):
            try:
                data, meta = self.backend.complete(
                    system=system, prompt=prompt, schema=schema, model=model, effort=effort,
                    tools=tools, workdir=workdir,
                    timeout_s=self.settings.agent_timeout_s if tools else None,
                )
                parsed = output.model_validate(data)
            except (LLMRefusal, LLMLimitReached):
                raise
            except (ConnectionError, TimeoutError) as exc:
                last = exc
                delay = min(240.0, 20.0 * 2**attempt) + random.uniform(0, 5)
                log.warning("%s: transient LLM failure (%s); retrying in %.0fs", stage, exc, delay)
                time.sleep(delay)
            except (ValidationError, ValueError) as exc:
                # A malformed reply is usually a one-off; a second identical one is not.
                last = exc
                if attempt >= 1:
                    break
                log.warning("%s: reply failed validation (%s); retrying once", stage, str(exc)[:200])
            else:
                self.cache.put_json(key, {"data": data, "meta": meta})
                self.usage.add(stage, cached=False, meta=meta)
                return parsed
        raise LLMError(f"{stage}: giving up after repeated failures: {last}")

    def map(
        self,
        stage: str,
        system: str,
        prompts: Sequence[str],
        output: type[T],
        *,
        on_done: Callable[[int, T | Exception], None] | None = None,
    ) -> list[T | Exception]:
        """Run many independent calls concurrently; failures come back as exceptions.

        A refusal or a broken reply for one paper must not sink the entry, so each
        slot holds either the parsed reply or the exception that replaced it. An
        exhausted usage limit is the exception to that: it is raised, because every
        remaining call would fail the same way.
        """
        results: list[T | Exception | None] = [None] * len(prompts)

        def work(i: int) -> None:
            try:
                results[i] = self.call(stage, system, prompts[i], output)
            except LLMLimitReached:
                raise
            except Exception as exc:  # noqa: BLE001 - recorded per item, reported by caller
                results[i] = exc
            if on_done:
                on_done(i, results[i])  # type: ignore[arg-type]

        with ThreadPoolExecutor(max_workers=max(1, self.settings.llm_concurrency)) as pool:
            for future in [pool.submit(work, i) for i in range(len(prompts))]:
                future.result()
        return results  # type: ignore[return-value]


_default: LLM | None = None


def get_llm() -> LLM:
    global _default
    if _default is None:
        _default = LLM()
    return _default
