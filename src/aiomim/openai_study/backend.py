"""The model backend of the study: it records requests instead of calling a model.

`StudyBackend` takes `aiomim.llm.ClaudeCode`'s place in an `LLM` (the `backend`
attribute). The project's `LLM.call` reads the cache first; only on a miss, or when
the cached reply is unusable, does it call the backend. The backend then:

* computes the cache key exactly as `LLM.call` does (`llm.cache_key`), so a reply
  written there by `ingest` is found by the next wave's run;
* on a miss, records the request (custom_id derived from the key) and raises
  `Pending`, which stops the task for this wave;
* when the cached reply is there but the project rejected it (it does not parse,
  does not validate, or the writer's reply is empty), asks once more under a
  distinct retry key and returns that reply when it has come back. If it is
  rejected too, `LLM.call` gives up exactly as it does with Claude (two bad replies:
  `LLMError`, or `LLMRefusal(EMPTY_REPLY)` for an empty writer reply);
* never sends a reply the model's safety filter stopped again: a stop is cached
  with `safety_stops = 1`, which `LLM.call` turns into `LLMRefusal` on every read.
  The judge procedure (`facts.map_covering`) re-asks a failed reply with a note
  appended; after a stop that would be a changed prompt, so the backend returns
  the stop for the re-ask instead of sending it.

Every request is labelled by its system prompt; a task may only make the calls its
kind allows (`ForbiddenCall` otherwise, never sent).
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from ..cache import stable_hash
from ..llm import cache_key
from .config import CLAUDE_MODEL, Study
from .errors import ForbiddenCall, Pending
from .openai_format import request_line, strict_problems

RETRY_SALT = "openai-study-retry"


def retry_key(key: str, attempt: int = 2) -> str:
    """Where the re-ask of a rejected reply is cached: distinct from the call's own key."""
    return stable_hash(key, RETRY_SALT, attempt)


def custom_id_for(storage_key: str, attempt: int) -> str:
    """The batch custom_id of a request: the attempt and the first 60 hex digits of its cache key."""
    return f"r{attempt}-{storage_key[:60]}"


# --------------------------------------------------------------------------- #
# Which call is this?
# --------------------------------------------------------------------------- #

_labels: dict[str, str] | None = None
_labels_lock = threading.Lock()


def system_labels() -> dict[str, str]:
    """System prompt -> label. Built from the project's own prompt constants."""
    global _labels
    with _labels_lock:
        if _labels is None:
            from .. import evaluate, extract, facts, gaps, synthesize, verify
            from ..strategies import closedbook, direct

            _labels = {
                facts.MARK_SYSTEM: "judge:mark",
                facts.MARK_WHOLE_SYSTEM: "judge:mark_whole",
                facts.SPLIT_SYSTEM: "judge:split",
                gaps.GAPS_SYSTEM: "judge:avail",
                gaps.GAPS_OTHER_SYSTEM: "judge:avail_other",
                evaluate.JUDGE_SYSTEM: "judge:per_draft_split",
                evaluate.MATCH_SYSTEM: "judge:variant_match",
                synthesize.DIRECT_SYSTEM: "synthesize:direct",
                synthesize.KG_SYSTEM: "synthesize:kg",
                direct.MERGE_SYSTEM: "synthesize:merge",
                extract.EXTRACT_SYSTEM: "extract",
                extract.NORMALIZE_SYSTEM: "normalize",
                closedbook.CLOSEDBOOK_SYSTEM: "recall:closedbook",
                verify.VERIFY_SYSTEM: "audit:verify",
                verify.DECOMPOSE_SYSTEM: "audit:decompose",
                verify.REPAIR_SYSTEM: "audit:repair",
            }
        return _labels


def label_for(system: str) -> str:
    return system_labels().get(system, "unknown")


def _note_pattern() -> re.Pattern:
    from ..facts import RETRY_NOTE

    head, _, tail = RETRY_NOTE.partition("{n}")
    return re.compile(re.escape(head) + r"(\d+)" + re.escape(tail) + r"\Z")


_NOTE: re.Pattern | None = None


def split_retry_note(prompt: str) -> str | None:
    """The prompt without the judge's coverage note, if it ends with one (`facts.RETRY_NOTE`)."""
    global _NOTE
    if _NOTE is None:
        _NOTE = _note_pattern()
    m = _NOTE.search(prompt)
    return prompt[:m.start()] if m else None


# --------------------------------------------------------------------------- #
# The request recorder (one per collect)
# --------------------------------------------------------------------------- #


class Recorder:
    """Collects the requests of one wave, deduplicated by custom_id.

    With `out` the OpenAI request lines are streamed to that file as they are
    recorded (prompts can be large); `entries` keeps the manifest: custom_id,
    cache keys, attempt, label, efforts, size and the tasks that need it.
    """

    def __init__(self, study: Study | None, out: Path | None = None, *, model: str | None = None):
        self.study = study
        self.model = model or (study.model if study else "")
        self.out = Path(out) if out else None
        self.entries: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._strict: dict[str, bool] = {}
        self._fh = None
        if self.out:
            self.out.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.out, "w", encoding="utf-8")

    def close(self) -> None:
        with self._lock:
            if self._fh:
                self._fh.close()
                self._fh = None

    def strict_for(self, schema: dict[str, Any]) -> bool:
        mode = (self.study.setting("request", "strict", default="auto") if self.study else "auto")
        if mode is False or mode == "never":
            return False
        h = stable_hash(schema)
        if h not in self._strict:
            self._strict[h] = not strict_problems(schema)
        if mode is True or mode == "always":
            return True
        return self._strict[h]

    def add(self, *, task_id: str, storage_key: str, call_key: str, attempt: int, label: str, effort: str,
            system: str, prompt: str, schema: dict[str, Any], retry_note: bool = False) -> str:
        cid = custom_id_for(storage_key, attempt)
        with self._lock:
            have = self.entries.get(cid)
            if have is not None:
                if task_id not in have["tasks"]:
                    have["tasks"].append(task_id)
                return cid
            strict = self.strict_for(schema)
            openai_effort = self.study.openai_effort(effort) if self.study else effort
            store = bool(self.study.setting("request", "store", default=False)) if self.study else False
            max_out = self.study.setting("request", "max_output_tokens") if self.study else None
            line = request_line(cid, model=self.model, effort=openai_effort, system=system, prompt=prompt,
                                schema=schema, name=label.replace(":", "_"), strict=strict, store=store,
                                max_output_tokens=max_out)
            text = json.dumps(line, ensure_ascii=False)
            if self._fh:
                self._fh.write(text + "\n")
            self.entries[cid] = {
                "custom_id": cid, "storage_key": storage_key, "cache_key": call_key, "attempt": attempt,
                "label": label, "effort": effort, "openai_effort": openai_effort, "strict": strict,
                "retry_note": retry_note,
                "chars": len(system) + len(prompt) + len(json.dumps(schema)), "bytes": len(text.encode("utf-8")) + 1,
                # The same call under the original runs' model: equal to a key in their cache only when the
                # system prompt, prompt and schema are byte for byte what those runs sent.
                "claude_key": cache_key(CLAUDE_MODEL, effort, system, prompt, schema),
                "tasks": [task_id],
            }
            return cid


# --------------------------------------------------------------------------- #
# The backend
# --------------------------------------------------------------------------- #


class StudyBackend:
    """Records cache misses for one task; see the module docstring."""

    def __init__(self, *, settings, cache, recorder: Recorder, task_id: str, allowed: set[str] | frozenset[str]):
        self.settings = settings
        self.cache = cache
        self.recorder = recorder
        self.task_id = task_id
        self.allowed = set(allowed)
        self.requests = 0          # requests recorded by this task in this pass
        self.stops_not_sent = 0    # re-asks of a stopped reply that were answered with the stop
        self._lock = threading.Lock()

    def complete(self, *, system: str, prompt: str, schema: dict[str, Any], model: str, effort: str,
                 tools: tuple[str, ...] = (), workdir: str | None = None, timeout_s: int | None = None,
                 ) -> tuple[Any, dict[str, Any]]:
        if tools:
            raise ForbiddenCall(f"{self.task_id}: tool sessions are not part of this study")
        label = label_for(system)
        if label not in self.allowed:
            raise ForbiddenCall(f"{self.task_id}: a {label!r} call is not part of this task")
        replicate = getattr(self.settings, "replicate", "") or ""
        key = cache_key(model, effort, system, prompt, schema, replicate=replicate)

        # The judge's re-ask (prompt + coverage note) of a reply the safety filter stopped
        # would be the stopped request with a changed prompt: answer it with the stop.
        base = split_retry_note(prompt)
        if base is not None:
            hit = self.cache.get_json(cache_key(model, effort, system, base, schema, replicate=replicate))
            if hit is not None and (hit.get("meta") or {}).get("safety_stops"):
                with self._lock:
                    self.stops_not_sent += 1
                return {}, {"model": model, "effort": effort, "provider": "openai", "safety_stops": 1,
                            "not_sent": "re-ask of a reply the safety filter stopped", "input_tokens": 0,
                            "output_tokens": 0, "cost_usd": 0.0}

        primary = self.cache.get_json(key)
        if primary is None:
            self._record(key, key, 1, label, effort, system, prompt, schema)
            raise Pending(f"{self.task_id}: {label}")
        # The reply is cached, yet the project asked again: it did not parse or validate, the
        # writer's reply was empty, or the code asked afresh (use_cache=False). One more try.
        rkey = retry_key(key)
        retry = self.cache.get_json(rkey)
        if retry is None:
            self._record(rkey, key, 2, label, effort, system, prompt, schema)
            raise Pending(f"{self.task_id}: {label} (retry)")
        return retry.get("data"), dict(retry.get("meta") or {})

    def _record(self, storage_key: str, call_key: str, attempt: int, label: str, effort: str, system: str,
                prompt: str, schema: dict[str, Any]) -> None:
        self.recorder.add(task_id=self.task_id, storage_key=storage_key, call_key=call_key, attempt=attempt,
                          label=label, effort=effort, system=system, prompt=prompt, schema=schema,
                          retry_note=split_retry_note(prompt) is not None)
        with self._lock:
            self.requests += 1
