"""Direct reading with a curator's checklist (D1 of `docs/direct-improvements.md`).

The same single writer call as direct reading, with one change to the system
prompt: the house style's per-paper guidance ("State who was studied (...), then
the salient findings") becomes an explicit list of what a curator records about
each paper, and "Do not pad" is narrowed so that it forbids background and
speculation but not the specifics a paper reports. Everything else (user prompt,
paper layout and truncation, schema, stage, effort, guards) is direct reading's.
Above the one-prompt budget the papers are read in direct reading's batches, each
batch with this system prompt.

The list describes the curator's task; it was not derived from OMIM text or from
the fixed fact lists.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import DIRECT_SYSTEM, STYLE, draft_to_entry
from . import direct

# The two passages of the house style that change, as they read in `synthesize.STYLE`.
WHO_THEN_SALIENT = ("State who was studied (number of patients and families, ancestry, consanguinity), then the "
                    "salient findings. Keep the numbers, ages and units exactly as given.")
NO_PAD = ("Do not pad, do not speculate, do not add general background knowledge, and do not smooth over "
          "disagreements between reports: describe them.")

CHECKLIST = """\
For each paper, record what a curator records about it, wherever the paper reports it:
  - who was studied: the number of patients and the number of families; their sex; their age at \
examination and at onset; their ancestry and country of origin; whether the parents were consanguineous;
  - the clinical findings and the investigations (imaging, laboratory, histologic, electrophysiologic and \
other tests) with their results, as the paper reports them;
  - for each variant: its nucleotide change and its protein change; its zygosity; how it was found (the \
method, such as exome sequencing, linkage and candidate-gene sequencing, or a screen of a cohort); whether it \
segregated with the disorder in the family, or occurred de novo; whether it was absent from controls or from \
population databases, with the numbers the paper gives (how many control chromosomes or individuals, which \
database); and functional studies (in patient cells, in cell or biochemical assays, or in animal models) \
with their result.
  Keep the numbers, ages and units exactly as given.\
"""

NO_PAD_NARROWED = ("Do not add general background knowledge, do not speculate beyond what the papers report, and "
                   "do not smooth over disagreements between reports: describe them. The specifics a paper reports "
                   "about its own patients, variants and experiments (the items listed above) are not padding: "
                   "record them.")


def checklist_style(style: str = STYLE) -> str:
    """The house style with the per-paper checklist and the narrowed padding rule."""
    if WHO_THEN_SALIENT not in style or NO_PAD not in style:
        # The house style changed: rebuild the checklist against it rather than run a
        # prompt that silently equals direct reading's.
        raise ValueError("synthesize.STYLE no longer contains the passages the checklist replaces")
    return style.replace(WHO_THEN_SALIENT, CHECKLIST).replace(NO_PAD, NO_PAD_NARROWED)


CHECKLIST_SYSTEM = DIRECT_SYSTEM.replace(STYLE, checklist_style())
assert CHECKLIST_SYSTEM != DIRECT_SYSTEM


def system_info() -> dict:
    return {"sha256": hashlib.sha256(CHECKLIST_SYSTEM.encode("utf-8")).hexdigest()[:16],
            "chars": len(CHECKLIST_SYSTEM)}


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    raw, gene_facts, meta = direct.draft(seed, papers, llm, system=CHECKLIST_SYSTEM)
    return draft_to_entry(seed, papers, raw, llm, strategy="direct_checklist", gene_facts=gene_facts,
                          meta={**meta, "checklist_system": system_info()})
