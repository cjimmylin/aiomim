"""The study's configuration (`study.json`), its folders, prices and the effort mapping."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import StudyError

# The model family of the original runs. Used only to compare prompts with the ones
# those runs sent (a Claude-model cache key over the same system prompt, prompt and
# schema), never to call it.
CLAUDE_MODEL = "claude-opus-5-5"

PROJECT_EFFORTS = ("low", "medium", "high", "xhigh", "max")
OPENAI_EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")   # "none" is rejected by the 6.2 models

TASK_KINDS = ("A1", "A2F", "A2C", "A3", "B1", "B2")
TASK_LABELS = {
    "A1": "Second judge: fixed-fact marks on the six strategies' drafts",
    "A2F": "Second judge: availability of each fixed fact in its paper's text (gaps --frozen)",
    "A2C": "Second judge: conveyed facts re-checked against the other papers (gaps --conveyed)",
    "A3": "Second judge: fixed-fact marks on the hidden-full-text arms",
    "B1": "Second writer: direct reading, evidence graph, memory only",
    "B2": "Second writer: hidden-full-text manipulation (full text, abstract only)",
}


@dataclass(frozen=True)
class StudyPaths:
    """Every folder of a study directory. `private/` never goes into git."""

    root: Path

    @property
    def study_json(self) -> Path:
        return self.root / "study.json"

    @property
    def private(self) -> Path:
        return self.root / "private"

    @property
    def bundle(self) -> Path:
        return self.private / "bundle"

    @property
    def bundle_tar(self) -> Path:
        return self.private / "openai_study_bundle.tar.gz"

    @property
    def requests(self) -> Path:
        return self.private / "requests"

    @property
    def responses(self) -> Path:
        return self.private / "responses"

    @property
    def work(self) -> Path:
        return self.private / "work"

    @property
    def home(self) -> Path:
        """The aiomim data home of the study (AIOMIM_HOME): model cache, fact store, ontology, HGNC."""
        return self.work / "home"

    @property
    def results(self) -> Path:
        return self.private / "results"

    @property
    def logs(self) -> Path:
        return self.private / "logs"

    @property
    def smoke(self) -> Path:
        return self.private / "smoke"

    @property
    def private_ledger(self) -> Path:
        return self.private / "requests_sent.json"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def waves(self) -> Path:
        return self.state / "waves"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def schemas(self) -> Path:
        return self.root / "schemas"


def write_json(path: Path, data: Any, *, indent: int | None = 1) -> None:
    """Write JSON atomically (write, then rename)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=indent, ensure_ascii=False, sort_keys=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Study:
    """`study.json`, checked on load."""

    def __init__(self, data: dict[str, Any], path: Path | None = None):
        self.data = data
        self.path = path
        self._check()

    @classmethod
    def load(cls, paths: StudyPaths) -> Study:
        if not paths.study_json.exists():
            raise StudyError(f"no study.json in {paths.root}")
        return cls(json.loads(paths.study_json.read_text(encoding="utf-8")), paths.study_json)

    # ------------------------------------------------------------- checks
    def _check(self) -> None:
        d = self.data
        model = d.get("model")
        allowed = d.get("models_allowed") or []
        if model not in allowed:
            raise StudyError(f"study.json: model {model!r} is not one of {allowed}")
        if model not in (d.get("prices_usd_per_1m_tokens") or {}).get("batch", {}):
            raise StudyError(f"study.json: no batch price for {model!r}")
        for project, openai in (d.get("effort_map") or {}).items():
            if project not in PROJECT_EFFORTS or openai not in OPENAI_EFFORTS:
                raise StudyError(f"study.json: effort_map {project!r} -> {openai!r} is not valid")
        if set(d.get("effort_map") or {}) != set(PROJECT_EFFORTS):
            raise StudyError("study.json: effort_map must map every project effort (low ... max)")
        if self.cap_usd <= 0:
            raise StudyError("study.json: the cost cap must be positive")

    # ------------------------------------------------------------- accessors
    @property
    def model(self) -> str:
        return self.data["model"]

    @property
    def cap_usd(self) -> float:
        caps = self.data.get("cost_cap_usd") or {}
        return float(caps.get(self.data.get("model"), 0) or 0)

    def price(self, model: str | None = None) -> dict[str, float]:
        return self.data["prices_usd_per_1m_tokens"]["batch"][model or self.model]

    def openai_effort(self, project_effort: str) -> str:
        return self.data["effort_map"][project_effort]

    def tasks(self) -> dict[str, Any]:
        return self.data.get("tasks") or {}

    def setting(self, *path: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def cost(self, input_tokens: int, cached_tokens: int, output_tokens: int, model: str | None = None) -> float:
        return cost_usd(self.price(model), input_tokens, cached_tokens, output_tokens)

    def chars_per_token(self, label: str | None = None) -> float:
        est = self.data.get("estimation") or {}
        by_label = est.get("chars_per_token_by_stage") or {}
        return float(by_label.get(label) or est.get("chars_per_token") or 3.0)

    def expected_output_tokens(self, label: str) -> int:
        est = self.data.get("estimation") or {}
        table = est.get("expected_output_tokens") or {}
        return int(table.get(label) or table.get("default") or 4000)


def cost_usd(price: dict[str, float], input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    """Batch cost from the price table (USD per 1M tokens). Cached input tokens are part of input tokens."""
    cached = max(0, min(int(cached_tokens or 0), int(input_tokens or 0)))
    fresh = max(0, int(input_tokens or 0) - cached)
    return (fresh * price["input"] + cached * price["cached_input"] + int(output_tokens or 0) * price["output"]) / 1e6
