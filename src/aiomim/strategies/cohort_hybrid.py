"""Case table plus text: the matched case table, and the writer also reads the papers.

See cohort_matched.py. Case extraction at the writer's effort, synopsis terms and
inheritance chosen by the writer, causal genes confirmed from the table's
candidates as in `cohort`, and the papers' text in the writer's prompt exactly as
direct reading gives it, with the case table after it as an aid. Paragraphs cite
supplied papers; naming records and notes is optional.
"""

from __future__ import annotations

from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from .cohort_matched import build


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    return build(seed, papers, llm, out_dir, hybrid=True, strategy="cohort_hybrid")
