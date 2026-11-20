"""The curator checklist, then the completeness pass (D4 of `docs/direct-improvements.md`).

1. The draft is D1's (`direct_checklist`): direct reading's writer call with the
   checklist system prompt, taken from the cache only, exactly as `direct_complete`
   takes direct reading's draft. A miss is an error, never a fresh draft.
2. Then D2's procedure unchanged (`direct_complete.completeness_pass`): the
   completeness check per paper (`auditstress.COMPLETE_SYSTEM`, stage `complete`),
   omissions kept only where their quote is found in the paper, one revision call
   (stage `revise`) and `draft_to_entry`. The revision prompt is D2's, except that
   the house-style block it embeds is the checklist style the draft was written in
   (`direct_checklist.checklist_style()`).

Completion as for D2: a check the safety filter stopped leaves the entry
incomplete (`meta.direct_checklist_complete.papers_failed`); a stopped revision
leaves no draft. Working file: `direct_checklist_complete.json` in the entry folder.
"""

from __future__ import annotations

from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from .direct_checklist import CHECKLIST_SYSTEM, checklist_style, system_info
from .direct_complete import cached_draft, completeness_pass, revise_system

NAME = "direct_checklist_complete"
RECORD = f"{NAME}.json"
REVISE_CHECKLIST_SYSTEM = revise_system(checklist_style())


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    raw, gene_facts, meta = cached_draft(seed, papers, llm, system=CHECKLIST_SYSTEM, source="direct_checklist")
    return completeness_pass(seed, papers, llm, out_dir, raw, gene_facts,
                             {**meta, "checklist_system": system_info()}, strategy=NAME,
                             draft_strategy="direct_checklist", revise=REVISE_CHECKLIST_SYSTEM, record_file=RECORD)
