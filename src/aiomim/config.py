"""Runtime settings, read once from the environment.

Everything has a working default, so `aiomim run 500001` needs no configuration
beyond a logged-in Claude Code CLI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# Stages that call the LLM. Each can be pointed at a different model / effort.
STAGES = ("plan", "triage", "extract", "normalize", "synthesize", "verify", "judge", "update",
          "agent", "recall", "cases", "reconcile", "reflect")

DEFAULT_MODEL = "claude-opus-5-5"

# Effort is the main quality/cost dial on current Claude models. Extraction and
# judging are bounded reading tasks; synthesis is where the reasoning happens.
DEFAULT_EFFORT = {
    "plan": "low",
    "triage": "low",
    "extract": "medium",
    "normalize": "low",
    "synthesize": "high",
    "verify": "medium",
    "judge": "medium",
    "update": "medium",
    "agent": "high",    # the autonomous curator: reads, checks and writes in one session
    "recall": "high",   # writing from memory
    "cases": "medium",  # per-paper case-record extraction
    "reconcile": "high",  # deciding which records across papers are the same patient, family or variant
    "reflect": "high",    # turning a training split's misses and extras into a curation guide
}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    home: Path
    runs: Path
    claude_bin: str
    models: dict[str, str] = field(default_factory=dict)
    efforts: dict[str, str] = field(default_factory=dict)
    llm_concurrency: int = 4
    llm_timeout_s: int = 900
    agent_timeout_s: int = 2400
    ncbi_api_key: str | None = None
    ncbi_email: str | None = None
    omim_api_key: str | None = None

    @property
    def http_cache(self) -> Path:
        return self.home / "cache" / "http"

    @property
    def llm_cache(self) -> Path:
        return self.home / "cache" / "llm"

    @property
    def ontology_dir(self) -> Path:
        return self.home / "ontologies"

    def model_for(self, stage: str) -> str:
        return self.models.get(stage, DEFAULT_MODEL)

    def effort_for(self, stage: str) -> str:
        return self.efforts.get(stage, DEFAULT_EFFORT.get(stage, "medium"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    base_model = _env("AIOMIM_MODEL", DEFAULT_MODEL)
    models = {s: _env(f"AIOMIM_MODEL_{s.upper()}", base_model) for s in STAGES}
    efforts = {s: _env(f"AIOMIM_EFFORT_{s.upper()}", DEFAULT_EFFORT[s]) for s in STAGES}
    return Settings(
        home=Path(_env("AIOMIM_HOME", "data")).resolve(),
        runs=Path(_env("AIOMIM_RUNS", "runs")).resolve(),
        claude_bin=_env("AIOMIM_CLAUDE_BIN", "claude"),
        models=models,
        efforts=efforts,
        llm_concurrency=int(_env("AIOMIM_LLM_CONCURRENCY", "4")),
        llm_timeout_s=int(_env("AIOMIM_LLM_TIMEOUT", "900")),
        agent_timeout_s=int(_env("AIOMIM_AGENT_TIMEOUT", "2400")),
        ncbi_api_key=_env("NCBI_API_KEY"),
        ncbi_email=_env("NCBI_EMAIL"),
        omim_api_key=_env("OMIM_API_KEY"),
    )
