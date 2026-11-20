"""Direct reading, then a completeness pass (D2 of `docs/direct-improvements.md`).

1. The draft is direct reading's own, taken from the cache (the writer's reply of
   the direct-reading run, the draft as it was before any repair). A miss is an
   error, not a fresh draft: the arm must start from the baseline's draft.
2. For each supplied paper, the completeness check measured in the audit stress
   test (`auditstress.COMPLETE_SYSTEM`, stage `complete`, unchanged) reads the
   paper's text, cut as the writer had it, and everything the draft says that
   cites the paper, and lists findings the paper reports that the draft leaves out,
   each with a quote. Only omissions whose quote is found in the paper's text are
   kept (`auditstress.checked_omissions`).
3. One revision call (stage `revise`) gets the papers that have kept omissions,
   the draft in its structured form and the omissions with their quotes, and
   returns the whole draft in the same form, with each finding added to the
   paragraph about its paper (or a new paragraph for it) and nothing else changed.
   The gene relationships and clinical-synopsis phrases are carried over from the
   draft unchanged whatever the reply says, and so are the allelic variants' names
   and HGVS lists where the reply keeps the same variants.
4. `draft_to_entry`, the guards every strategy shares.

A check the safety filter stopped (or that failed for good) leaves its paper
unchecked: the entry is then incomplete, and the paper is recorded in
`meta.direct_complete.papers_failed`, which `compare.completion_status` reads. A
stopped revision leaves no draft. With no kept omission there is no revision call
and the draft is the baseline's.

Working file: `direct_complete.json` in the entry folder (the omissions, with
the paper quotes; model-written, no OMIM text).
"""

from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any

from ..auditstress import COMPLETE_SYSTEM, XOmissions, checked_omissions, complete_prompt, sentences
from ..evaluate import _draft_text_for
from ..gaps import per_paper_chars
from ..llm import LLMLimitReached, LLMRefusal
from ..models import GeneratedEntry, Paper, Seed, squash
from ..synthesize import STYLE, DEntry, _header, draft_to_entry, has_content, paper_blocks
from . import direct

log = logging.getLogger(__name__)

RECORD = "direct_complete.json"

REVISE_SYSTEM = f"""\
You are a senior curator revising a draft entry for OMIM (Online Mendelian Inheritance in Man). A checker \
compared the draft with each paper it rests on and listed findings that the paper reports and that the \
draft leaves out, each with the passage of the paper that states it. You are given the text of those \
papers, the draft in the structured form you must return, and the listed omissions, numbered per paper.

Return the whole draft, in the same structured form, revised as follows.
- Add each listed finding to the paragraph about the paper that reports it, in the section where it \
belongs (clinical findings in Clinical Features, variants and functional studies in Molecular Genetics, \
and so on), attributed to that paper's citation label as the rest of the paragraph is. If the draft has \
no paragraph about that paper in that section, add one, in chronological order among the section's \
paragraphs, with the paper's PMID in `pmids`.
- Where the draft already states a listed finding, leave it as it is; where the draft states it only in \
part, complete it with the missing detail.
- Add nothing that is not in a listed finding: no other fact from the papers, nothing from your own \
memory, no interpretation. Read the paper text only to place and word each listed finding correctly \
(which patient, family or variant it concerns), and keep its numbers, ages and units as the paper gives them.
- Change nothing else. Every other paragraph, sentence, section, citation (`pmids`), gene relationship, \
allelic variant (name, `hgvs`, phenotype) and clinical-synopsis item stays exactly as it is, in the same \
order. Do not shorten, reword, merge or drop anything the draft already says.

Write the added text in the house style of the draft:

{STYLE}\
"""


# --------------------------------------------------------------------------- #
# Building the prompts
# --------------------------------------------------------------------------- #


def _ordered(papers: list[Paper]) -> list[Paper]:
    return sorted(papers, key=lambda p: (p.year or 9999, p.pmid))


def check_jobs(entry: GeneratedEntry, papers: list[Paper]) -> list[tuple[Paper, str, str]]:
    """(paper, its text as the writer had it, check prompt) for every supplied paper.

    As the natural-omission run of the audit stress test calls the check: the paper's
    text cut to direct reading's per-paper share, and the draft's text citing the paper
    (`evaluate._draft_text_for`).
    """
    cap = per_paper_chars(len(papers))
    jobs = []
    for paper in _ordered(papers):
        source = paper.source_text(cap)
        jobs.append((paper, source, complete_prompt(paper, source, _draft_text_for(entry, [paper.pmid]))))
    return jobs


def _quote(text: str) -> str:
    return text.replace('"', "'")


def revise_prompt(seed: Seed, papers: list[Paper], raw: DEntry, kept: dict[str, list[dict[str, Any]]]) -> str:
    """Papers with kept omissions (laid out and cut exactly as the writer had them), the draft, the omissions."""
    blocks, _ = paper_blocks(papers)
    by_block = dict(zip([p.pmid for p in _ordered(papers)], blocks))
    labels = {p.pmid: p.label for p in papers}
    listed = []
    for paper in _ordered(papers):
        rows = kept.get(paper.pmid)
        if not rows:
            continue
        lines = [f'<omissions pmid="{paper.pmid}" label="{labels[paper.pmid]}">']
        for n, row in enumerate(rows, 1):
            lines.append(f"{n}. {row['finding']}\n   Paper's words: \"{_quote(row['quote'])}\"")
        lines.append("</omissions>")
        listed.append("\n".join(lines))
    return (
        f"{_header(seed)}\n\n"
        + "\n\n".join(by_block[p.pmid] for p in _ordered(papers) if kept.get(p.pmid))
        + f"\n\n<draft>\n{raw.model_dump_json(indent=1)}\n</draft>\n\n"
        + "Listed omissions, per paper:\n\n" + "\n\n".join(listed)
    )


# --------------------------------------------------------------------------- #
# What the revision changed
# --------------------------------------------------------------------------- #


def _paragraphs(raw: DEntry) -> list:
    return [raw.intro, *(x for s in raw.sections for x in s.paragraphs),
            *(x for v in raw.allelic_variants for x in v.paragraphs)]


def _sentences(raw: DEntry) -> list[tuple[str, tuple[str, ...]]]:
    out = []
    for x in _paragraphs(raw):
        pmids = tuple(dict.fromkeys(str(p).strip() for p in x.pmids))
        out.extend((squash(s), pmids) for s in sentences(squash(x.text)) if squash(s))
    return out


def _variant_identity(raw: DEntry) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(v.gene_symbol.strip().upper(), squash(v.name).upper(), tuple(squash(h) for h in v.hgvs))
            for v in raw.allelic_variants]


def enforce_unchanged(before: DEntry, after: DEntry) -> tuple[DEntry, dict[str, Any]]:
    """Carry over what the revision may not change; report what it tried to change."""
    out = after.model_copy(deep=True)
    notes: dict[str, Any] = {
        "relationships_changed": [r.model_dump() for r in after.relationships] != [r.model_dump() for r in before.relationships],
        "synopsis_changed": [i.model_dump() for i in after.clinical_synopsis] != [i.model_dump() for i in before.clinical_synopsis],
        "variants_changed": _variant_identity(after) != _variant_identity(before),
        "intro_changed": squash(after.intro.text) != squash(before.intro.text),
    }
    out.relationships = copy.deepcopy(before.relationships)
    out.clinical_synopsis = copy.deepcopy(before.clinical_synopsis)
    if len(after.allelic_variants) == len(before.allelic_variants):
        for v_new, v_old in zip(out.allelic_variants, before.allelic_variants):
            v_new.gene_symbol, v_new.name = v_old.gene_symbol, v_old.name
            v_new.hgvs, v_new.phenotype = list(v_old.hgvs), v_old.phenotype
    else:
        notes["variant_count"] = [len(before.allelic_variants), len(after.allelic_variants)]
    return out, notes


def diff_stats(before: DEntry, after: DEntry, with_omissions: set[str]) -> dict[str, Any]:
    """Sentences added and removed, and whether the added ones cite a paper that had listed omissions."""
    old, new = _sentences(before), _sentences(after)
    old_texts, new_texts = {s for s, _ in old}, {s for s, _ in new}
    added = [(s, p) for s, p in new if s not in old_texts]
    removed = [(s, p) for s, p in old if s not in new_texts]
    old_paras = {squash(x.text) for x in _paragraphs(before) if squash(x.text)}
    new_paras = [x for x in _paragraphs(after) if squash(x.text)]
    return {
        "sentences_before": len(old), "sentences_after": len(new),
        "sentences_added": len(added), "sentences_removed": len(removed),
        "added_citing_papers_with_omissions": sum(1 for _, p in added if set(p) & with_omissions),
        "added_citing_other_papers_only": sum(1 for _, p in added if p and not set(p) & with_omissions),
        "paragraphs_before": len(old_paras), "paragraphs_after": len(new_paras),
        "paragraphs_unchanged": sum(1 for x in new_paras if squash(x.text) in old_paras),
        "chars_before": sum(len(squash(x.text)) for x in _paragraphs(before)),
        "chars_after": sum(len(squash(x.text)) for x in _paragraphs(after)),
        "removed_sentences": [s for s, _ in removed][:20],
        "pmids_lost": sorted(direct.cited_in(before) - direct.cited_in(after)),
    }


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def cache_only(llm):
    """The same model wrapper (cache, settings, usage ledger) with no way to make a call."""
    if not hasattr(llm, "backend"):
        return llm   # a scripted test double
    from ..secondhand import CacheOnly

    clone = copy.copy(llm)
    clone.backend = CacheOnly()
    return clone


def baseline_draft(seed: Seed, papers: list[Paper], llm) -> tuple[DEntry, dict, dict]:
    """Direct reading's draft (the writer's reply), from the cache only."""
    try:
        return direct.draft(seed, papers, cache_only(llm))
    except LLMRefusal:
        raise
    except Exception as exc:  # noqa: BLE001 - a miss must not turn into a fresh, different draft
        raise RuntimeError(f"direct reading's draft is not in the cache ({exc}); run `direct` first") from exc


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    raw, gene_facts, meta = baseline_draft(seed, papers, llm)
    # The draft as scored: the guards applied (citations from the text attached, uncited
    # paragraphs dropped). The check reads what this draft says about each paper.
    base_entry = draft_to_entry(seed, papers, raw, llm, strategy="direct", gene_facts=dict(gene_facts))

    jobs = check_jobs(base_entry, papers)
    replies = llm.map("complete", COMPLETE_SYSTEM, [j[2] for j in jobs], XOmissions)
    per_paper, kept, failed, failures = [], {}, [], {}
    for (paper, source, _), reply in zip(jobs, replies):
        if isinstance(reply, LLMLimitReached):
            raise reply
        row = checked_omissions(reply, source)
        if row["error"]:
            failed.append(paper.pmid)
            failures[paper.pmid] = ("stopped: " if isinstance(reply, LLMRefusal) else "failed: ") + row["error"]
        verified = [o for o in row["omissions"] if o["quote_verified"]]
        if verified:
            kept[paper.pmid] = verified
        per_paper.append({"pmid": paper.pmid, "label": paper.label, "content_level": paper.content_level,
                          "draft_chars": len(_draft_text_for(base_entry, [paper.pmid])),
                          "listed": len(row["omissions"]), "verified": len(verified), "error": row["error"],
                          "omissions": row["omissions"]})

    record: dict[str, Any] = {
        "papers_checked": len(jobs), "papers_failed": failed, "failures": failures,
        "omissions_listed": sum(r["listed"] for r in per_paper),
        "omissions_kept": sum(r["verified"] for r in per_paper),
        "papers_with_kept_omissions": sorted(kept),
    }
    if kept:
        prompt = revise_prompt(seed, papers, raw, kept)
        # A stopped revision raises LLMRefusal: no draft.
        revised = llm.call("revise", REVISE_SYSTEM, prompt, DEntry, accept=has_content)
        revised, enforced = enforce_unchanged(raw, revised)
        record["revision"] = {"called": True, "prompt_chars": len(prompt), **enforced,
                              **diff_stats(raw, revised, set(kept))}
    else:
        revised = raw
        record["revision"] = {"called": False}
    _write_json(Path(out_dir) / RECORD, {**record, "per_paper": per_paper})
    log.info("[%s] direct_complete: %d omissions listed, %d kept on %d papers%s", seed.mim or seed.title,
             record["omissions_listed"], record["omissions_kept"], len(kept),
             f"; {len(failed)} checks failed" if failed else "")
    return draft_to_entry(seed, papers, revised, llm, strategy="direct_complete", gene_facts=gene_facts,
                          meta={**meta, "direct_complete": record})
