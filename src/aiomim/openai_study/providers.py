"""Where batches go: the OpenAI Batch API through the official SDK, or a local fake for dry runs.

A provider has four operations, mirroring the Batch API:

    upload(path) -> file id                     Files API, purpose "batch"
    create(file_id, metadata) -> batch dict     POST /v1/batches, endpoint /v1/responses, 24h window
    retrieve(batch_id) -> batch dict            GET /v1/batches/{id}
    download(file_id, dest)                     GET /v1/files/{id}/content

The fake provider answers each request by replaying the project's own cached Claude
reply for the same system prompt, prompt and schema (the key the original runs used),
written in the OpenAI output format; a request the Claude cache does not hold gets a
schema-valid synthetic reply. It can inject invalid replies, refusals and expired
requests to exercise those paths. It never touches the network.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import time
from pathlib import Path
from typing import Any

from ..cache import DiskCache
from .config import read_json, write_json
from .errors import StudyError
from .openai_format import request_parts

TERMINAL = ("completed", "expired", "cancelled", "failed")


def _as_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    for attr in ("model_dump", "to_dict", "dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except TypeError:
                continue
    return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))


class OpenAIProvider:
    """The real thing. Needs the `openai` package and OPENAI_API_KEY (read by the SDK, never printed)."""

    name = "openai"

    def __init__(self, completion_window: str = "24h"):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise StudyError("the `openai` package is not installed (pip install openai)") from exc
        self.client = OpenAI()
        self.window = completion_window

    def upload(self, path: Path) -> str:
        with open(path, "rb") as fh:
            return self.client.files.create(file=fh, purpose="batch").id

    def create(self, file_id: str, metadata: dict[str, str]) -> dict[str, Any]:
        batch = self.client.batches.create(input_file_id=file_id, endpoint="/v1/responses",
                                           completion_window=self.window, metadata=metadata)
        return _as_dict(batch)

    def retrieve(self, batch_id: str) -> dict[str, Any]:
        return _as_dict(self.client.batches.retrieve(batch_id))

    def download(self, file_id: str, dest: Path) -> None:
        content = self.client.files.content(file_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        if hasattr(content, "write_to_file"):
            content.write_to_file(tmp)
        else:  # pragma: no cover - older SDKs
            tmp.write_bytes(content.read() if hasattr(content, "read") else content.content)
        tmp.replace(dest)

    def cancel(self, batch_id: str) -> dict[str, Any]:
        return _as_dict(self.client.batches.cancel(batch_id))


# --------------------------------------------------------------------------- #
# Fake provider (dry runs, tests)
# --------------------------------------------------------------------------- #


def _u(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


_FACTS = re.compile(r"<facts>\n(.*?)\n</facts>", re.DOTALL)
_HPO_LINE = re.compile(r"^\s+(HP:\d{7})\s", re.MULTILINE)
_PMID = re.compile(r'pmid="(\d+)"')


def synthetic_instance(schema: dict[str, Any], prompt: str, rng: random.Random) -> Any:
    """A reply that satisfies `schema` and fits the prompt's numbered items where it has any."""
    props = (schema or {}).get("properties") or {}
    facts = _FACTS.search(prompt)
    n_items = len([ln for ln in facts.group(1).splitlines() if re.match(r"\d+\. ", ln)]) if facts else 0
    if set(props) == {"marks"}:
        return {"marks": [{"n": i, "status": rng.choice(["present", "partial", "absent", "absent"]), "note": ""}
                          for i in range(1, n_items + 1)]}
    if set(props) == {"verdicts"}:
        return {"verdicts": [{"n": i, "in_text": rng.choice(["yes", "partly", "no", "no"]), "quote": ""}
                             for i in range(1, n_items + 1)]}
    if set(props) == {"choices"}:
        out, n = [], 0
        for block in prompt.split("\n\n"):
            m = re.match(r"(\d+)\. ", block)
            if not m:
                continue
            n = int(m.group(1))
            hits = _HPO_LINE.findall(block)
            out.append({"n": n, "hpo_id": hits[0] if hits else ""})
        return {"choices": out}
    pmids = _PMID.findall(prompt)
    return _minimal(schema, rng, pmids)


def _minimal(schema: dict[str, Any], rng: random.Random, pmids: list[str], depth: int = 0) -> Any:
    if "anyOf" in schema:
        return _minimal(schema["anyOf"][0], rng, pmids, depth)
    if "enum" in schema:
        return schema["enum"][0]
    t = schema.get("type")
    if t == "object":
        out = {}
        for name, sub in (schema.get("properties") or {}).items():
            if name == "text":
                out[name] = "A synthetic paragraph written by the fake provider for a dry run."
            elif name == "pmids":
                out[name] = pmids[:1]
            else:
                out[name] = _minimal(sub, rng, pmids, depth + 1)
        return out
    if t == "array":
        return []
    if t == "string":
        return ""
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    if t == "null":
        return None
    return None


class FakeProvider:
    """Answers batches locally. `faults` sets the share of invalid replies, refusals and expired requests."""

    name = "fake"

    def __init__(self, store: Path, requests_dir: Path, claude_cache: Path | None,
                 faults: dict[str, float] | None = None, polls_until_done: int = 1, model: str = "fake"):
        self.store = Path(store)
        self.requests_dir = Path(requests_dir)
        self.claude = DiskCache(Path(claude_cache)) if claude_cache else None
        self.faults = {"invalid": 0.0, "refusal": 0.0, "expired": 0.0, **(faults or {})}
        self.polls_until_done = polls_until_done
        self.model = model
        (self.store / "files").mkdir(parents=True, exist_ok=True)
        self.state_path = self.store / "batches.json"
        self.stats = {"replayed": 0, "synthetic": 0, "invalid": 0, "refusal": 0, "expired": 0, "claude_stop": 0}

    # ------------------------------------------------------------- state
    def _state(self) -> dict[str, Any]:
        return read_json(self.state_path, {"files": 0, "batches": {}, "faulted": []})

    def _save(self, st: dict[str, Any]) -> None:
        write_json(self.state_path, st)

    def _manifest(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        smoke = self.requests_dir.parent / "smoke" / "smoke.manifest.json"
        for p in [*sorted(self.requests_dir.glob("*.manifest.json")), smoke]:
            for e in (read_json(p, {}) or {}).get("requests", []):
                out[e["custom_id"]] = e
        return out

    # ------------------------------------------------------------- API
    def upload(self, path: Path) -> str:
        st = self._state()
        st["files"] += 1
        fid = f"file-fake{st['files']:05d}"
        shutil.copyfile(path, self.store / "files" / fid)
        self._save(st)
        return fid

    def create(self, file_id: str, metadata: dict[str, str]) -> dict[str, Any]:
        st = self._state()
        bid = f"batch_fake{len(st['batches']) + 1:05d}"
        out_id, err_id = self._answer(file_id, bid, st)
        st["batches"][bid] = {"id": bid, "status": "in_progress", "input_file_id": file_id, "metadata": metadata,
                              "output_file_id": out_id, "error_file_id": err_id, "polls": 0,
                              "created_at": int(time.time())}
        self._save(st)
        return self._view(st["batches"][bid], hide_files=True)

    def retrieve(self, batch_id: str) -> dict[str, Any]:
        st = self._state()
        b = st["batches"].get(batch_id)
        if b is None:
            raise StudyError(f"fake provider: no batch {batch_id}")
        b["polls"] += 1
        if b["polls"] >= self.polls_until_done:
            b["status"] = "completed"
        self._save(st)
        return self._view(b, hide_files=b["status"] != "completed")

    def download(self, file_id: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.store / "files" / file_id, dest)

    def _view(self, b: dict[str, Any], hide_files: bool) -> dict[str, Any]:
        lines = (self.store / "files" / b["input_file_id"]).read_text(encoding="utf-8").count("\n")
        return {"id": b["id"], "status": b["status"], "input_file_id": b["input_file_id"],
                "output_file_id": None if hide_files else b["output_file_id"],
                "error_file_id": None if hide_files else b["error_file_id"],
                "request_counts": {"total": lines, "completed": 0 if hide_files else lines, "failed": 0},
                "metadata": b.get("metadata")}

    # ------------------------------------------------------------- replies
    def _answer(self, file_id: str, bid: str, st: dict[str, Any]) -> tuple[str | None, str | None]:
        manifest = self._manifest()
        faulted = set(st.get("faulted", []))
        out_lines, err_lines = [], []
        for n, raw in enumerate((self.store / "files" / file_id).read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            line = json.loads(raw)
            cid = line["custom_id"]
            system, prompt, schema = request_parts(line)
            entry = manifest.get(cid, {})
            u = _u(cid, "fault")
            first_time = cid not in faulted
            f = self.faults
            if first_time and u < f["expired"]:
                faulted.add(cid)
                self.stats["expired"] += 1
                err_lines.append({"id": f"batch_req_{bid}_{n}", "custom_id": cid, "response": None,
                                  "error": {"code": "batch_expired", "message": "This request could not be executed "
                                            "before the completion window expired."}})
                continue
            usage = {"input_tokens": len(system + prompt) // 3, "input_tokens_details": {"cached_tokens": 0},
                     "output_tokens": 400, "output_tokens_details": {"reasoning_tokens": 200}}
            content: list[dict[str, Any]]
            status = "completed"
            hit = self.claude.get_json(entry["claude_key"]) if (self.claude and entry.get("claude_key")) else None
            if hit is not None and (hit.get("meta") or {}).get("safety_stops"):
                self.stats["claude_stop"] += 1
                content = [{"type": "refusal", "refusal": "I can't help with that."}]
            elif first_time and f["expired"] <= u < f["expired"] + f["refusal"]:
                faulted.add(cid)
                self.stats["refusal"] += 1
                content = [{"type": "refusal", "refusal": "I can't help with that."}]
            elif first_time and f["expired"] + f["refusal"] <= u < f["expired"] + f["refusal"] + f["invalid"]:
                faulted.add(cid)
                self.stats["invalid"] += 1
                content = [{"type": "output_text", "text": '{"truncated": '}]
            else:
                if hit is not None and hit.get("data") is not None:
                    self.stats["replayed"] += 1
                    data = hit["data"]
                    meta = hit.get("meta") or {}
                    usage["output_tokens"] = int(meta.get("output_tokens", 400) or 400)
                else:
                    self.stats["synthetic"] += 1
                    data = synthetic_instance(schema, prompt, random.Random(cid))
                content = [{"type": "output_text", "text": json.dumps(data, ensure_ascii=False)}]
            body = {"id": f"resp_{hashlib.sha1(cid.encode()).hexdigest()[:20]}", "object": "response",
                    "status": status, "model": line["body"].get("model"),
                    "output": [{"type": "reasoning", "id": "rs_fake", "summary": []},
                               {"type": "message", "role": "assistant", "status": "completed", "content": content}],
                    "usage": usage}
            out_lines.append({"id": f"batch_req_{bid}_{n}", "custom_id": cid,
                              "response": {"status_code": 200, "request_id": f"req_{n}", "body": body},
                              "error": None})
        st["faulted"] = sorted(faulted)
        out_id = err_id = None
        if out_lines:
            st["files"] += 1
            out_id = f"file-fake{st['files']:05d}"
            (self.store / "files" / out_id).write_text("".join(json.dumps(x) + "\n" for x in out_lines))
        if err_lines:
            st["files"] += 1
            err_id = f"file-fake{st['files']:05d}"
            (self.store / "files" / err_id).write_text("".join(json.dumps(x) + "\n" for x in err_lines))
        stats_path = self.store / "stats.json"
        old = read_json(stats_path, {}) or {}
        write_json(stats_path, {k: old.get(k, 0) + v for k, v in self.stats.items()})
        self.stats = dict.fromkeys(self.stats, 0)
        return out_id, err_id


def make_provider(paths, study, fake: dict[str, Any] | None = None):
    """The provider for this run: the fake one when `fake` (a dict of options) is given."""
    if fake is not None:
        return FakeProvider(paths.private / "fake_provider", paths.requests, fake.get("claude_cache"),
                            faults=fake.get("faults"), polls_until_done=int(fake.get("polls", 1)),
                            model=study.model)
    return OpenAIProvider(study.setting("batch", "completion_window", default="24h"))
