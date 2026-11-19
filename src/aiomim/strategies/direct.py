"""Direct reading: the baseline. See `synthesize.synthesize_direct`."""

from __future__ import annotations

from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import synthesize_direct


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    return synthesize_direct(seed, papers, llm)
