"""Direct reading with a learned curation guide appended to the writer's instructions.

The guide is a short set of general rules about what an OMIM entry reports about
a paper, learned from the misses and extras of a training split (see
`aiomim.guide`). It is read from `AIOMIM_GUIDE` (default
`guides/omim100.guide.md`); its path, SHA-256 and length are recorded in the
entry's `meta` so a result can be traced to the guide that produced it.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import synthesize_direct

DEFAULT_GUIDE = "guides/omim100.guide.md"


def guide_path() -> Path:
    return Path(os.environ.get("AIOMIM_GUIDE") or DEFAULT_GUIDE)


def load_guide(path: Path | None = None) -> tuple[str, dict]:
    path = path or guide_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"curation guide not found at {path}: learn one with `aiomim guide-learn` or point AIOMIM_GUIDE at it")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"curation guide {path} is empty")
    info = {"path": str(path), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "words": len(text.split())}
    return text, info


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    guide, info = load_guide()
    return synthesize_direct(seed, papers, llm, extra_rules=guide, strategy="guided", meta={"guide": info})
