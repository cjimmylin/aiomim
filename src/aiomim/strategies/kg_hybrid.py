"""Evidence graph plus text: the matched evidence graph, and the writer also reads the papers.

See kg_matched.py. Extraction at the writer's effort, synopsis terms chosen by the
writer, and the papers' text in the writer's prompt exactly as direct reading
gives it, with the graph after it as an aid. Paragraphs cite supplied papers;
naming graph findings is optional.
"""

from __future__ import annotations

from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from .kg_matched import build


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    return build(seed, papers, llm, out_dir, hybrid=True, strategy="kg_hybrid")
