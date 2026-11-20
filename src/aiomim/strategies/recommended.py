"""The recommended way to write an entry (adopted 20 November 2026; `docs/direct-improvements.md`).

Where at least one supplied paper is readable in full, the curator-checklist draft
(`direct_checklist`) followed by the completeness pass (`direct_complete`'s procedure,
with the checklist house style in the revision prompt): the arm D4 that conveyed the
most curator facts in the evaluation, at the completeness pass's cost. Where no paper
is readable in full, plain direct reading: on abstract-only papers no variant helped,
and the extra calls only add chances of a stopped reply.

Unlike the evaluated arm, this is a way of producing entries, so a revision the
model's safety filter stopped does not cost the entry: the checklist draft is kept,
unrevised, and `meta["recommended"]` says so. Nothing is retried or reworded; the
stopped reply's content is not obtained by other means. A stopped writer still leaves
no draft, as for every strategy. Like every strategy, the entry then goes through the
claim-level audit and its repair round.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..llm import LLMLimitReached, LLMRefusal
from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import draft_to_entry
from . import direct
from .direct_checklist import CHECKLIST_SYSTEM, system_info
from .direct_checklist_complete import REVISE_CHECKLIST_SYSTEM
from .direct_complete import completeness_pass

log = logging.getLogger(__name__)

NAME = "recommended"
RECORD = f"{NAME}.json"


def has_fulltext(papers: list[Paper]) -> bool:
    return any(p.content_level == "fulltext" for p in papers)


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    if not has_fulltext(papers):
        entry = direct.run(seed, papers, llm, out_dir)
        entry.meta[NAME] = {"route": "direct reading", "reason": "no supplied paper is readable in full"}
        return entry

    raw, gene_facts, meta = direct.draft(seed, papers, llm, system=CHECKLIST_SYSTEM)
    meta = {**meta, "checklist_system": system_info()}
    try:
        entry = completeness_pass(seed, papers, llm, out_dir, raw, gene_facts, meta, strategy=NAME,
                                  draft_strategy=NAME, revise=REVISE_CHECKLIST_SYSTEM, record_file=RECORD)
    except LLMLimitReached:
        raise
    except LLMRefusal as exc:
        log.warning("[%s] %s: the revision was stopped (%s); the checklist draft is kept unrevised",
                    seed.mim or seed.title, NAME, exc)
        entry = draft_to_entry(seed, papers, raw, llm, strategy=NAME, gene_facts=dict(gene_facts), meta=meta)
        entry.meta[NAME] = {"route": "checklist draft, unrevised",
                            "reason": "the completeness pass's revision was stopped by the model's safety filter"}
        return entry
    record = entry.meta.get(NAME) if isinstance(entry.meta.get(NAME), dict) else {}
    entry.meta[NAME] = {**record, "route": "checklist draft with the completeness pass"}
    return entry
