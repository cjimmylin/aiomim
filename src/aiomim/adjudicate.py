"""When a draft and OMIM disagree, ask the paper.

The gold-text comparison labels a fact "contradicted" when the draft states
something incompatible with OMIM's paragraph about the same paper. That does not
say which of the two is right. This module takes every such disagreement back to
the source: the paper's text, OMIM's statement and the draft's statement go to a
judge, which must say which one the paper supports and quote the passage that
decides it. The quote is then checked against the paper without a model.

A disagreement the paper settles in the draft's favour is a candidate correction
to the OMIM text, to be confirmed by a curator against the live entry.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .grounding import SourceIndex
from .llm import LLM
from .models import squash

log = logging.getLogger(__name__)

PER_PAPER_CHARS = 120_000

ADJUDICATE_SYSTEM = """\
You are settling a disagreement between two summaries of the same published paper. One is a \
REFERENCE statement from the OMIM database, written by a curator. The other is a DRAFT written by a \
machine. An earlier comparison found that they state incompatible things on one point. You are given \
that point, both texts for context, and the text of the paper (the full text where available, \
otherwise only the abstract). Decide which of the two the paper supports on that point.

paper_supports
draft        the paper states what the draft states, and not what the reference states.
reference    the paper states what the reference states, and not what the draft states.
both         the paper supports both: they are not really in conflict (different patients or \
families, two notations or numbering systems for the same variant, a detail one of them omits).
neither      the paper states something different from both.
cannot_tell  the supplied text does not cover the point. With only an abstract supplied, this is the \
right answer whenever the detail could be in the full text.

Go by the supplied paper text alone, not by your own knowledge of the gene or disorder, and do not \
give either side the benefit of the doubt: curators make transcription slips and machines misread. In \
`quote`, copy character for character the passage of the paper that decides the point (one continuous \
span, at most about 50 words), or leave it empty for cannot_tell. In `explanation`, say in one or two \
sentences what the paper says on the point.\
"""


class XRuling(BaseModel):
    paper_supports: Literal["draft", "reference", "both", "neither", "cannot_tell"]
    quote: str
    explanation: str


def adjudicate_run(run_dir: Path) -> dict[str, Any]:
    from .sources.fulltext import load_papers

    cases: list[dict[str, Any]] = []
    for eval_path in sorted(run_dir.glob("*/eval.*.json")):
        strategy = eval_path.name.split(".")[1]
        evaluation = json.loads(eval_path.read_text())
        for para in evaluation.get("gold_text", {}).get("paragraphs", []):
            for fact in para["facts"]:
                if fact["status"] == "contradicted":
                    cases.append({
                        "mim": evaluation["mim"], "title": evaluation["title"], "strategy": strategy,
                        "pmids": para["pmids"], "content_level": para["content_level"],
                        "omim_states": fact["fact"], "difference": fact["note"],
                        "reference": para["reference"], "draft": para["draft"],
                    })
    papers = {p.pmid: p for p in load_papers(sorted({pmid for c in cases for pmid in c["pmids"]}), with_fulltext=True)}

    prompts, sources = [], []
    for case in cases:
        blocks = []
        for pmid in case["pmids"]:
            paper = papers.get(pmid)
            if paper is None:
                continue
            blocks.append(f'<paper pmid="{pmid}" label="{paper.label}" available="{paper.content_level}">\n'
                          f"{paper.source_text(PER_PAPER_CHARS)}\n</paper>")
        source = "\n\n".join(blocks)
        sources.append(source)
        prompts.append(
            f"Point of disagreement\nThe reference states: {case['omim_states']}\n"
            f"How the draft differs: {case['difference']}\n\n"
            f"<reference>\n{case['reference']}\n</reference>\n\n<draft>\n{case['draft']}\n</draft>\n\n{source}"
        )

    replies = LLM().map("judge", ADJUDICATE_SYSTEM, prompts, XRuling)
    for case, source, reply in zip(cases, sources, replies):
        if isinstance(reply, Exception):
            log.warning("adjudicate: %s failed: %s", case["mim"], reply)
            case.update(ruling="error", quote="", explanation=str(reply)[:200], quote_verified=False)
            continue
        quote = squash(reply.quote)
        verified = bool(quote) and SourceIndex(source).contains(quote)
        ruling = reply.paper_supports
        # A ruling for one side that rests on a quote we cannot find is not a ruling.
        if ruling in ("draft", "reference", "neither") and not verified:
            ruling = "cannot_tell"
        case.update(ruling=ruling, model_ruling=reply.paper_supports, quote=quote,
                    explanation=squash(reply.explanation), quote_verified=verified)
        case.pop("reference"); case.pop("draft")

    def tally(items: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(c["ruling"] for c in items)
        return {"n": len(items), **{k: counts.get(k, 0) for k in ("draft", "reference", "both", "neither", "cannot_tell", "error")}}

    result = {
        "run": run_dir.name,
        "by_strategy": {s: tally([c for c in cases if c["strategy"] == s]) for s in sorted({c["strategy"] for c in cases})},
        "by_content_level": {
            s: {lvl: tally([c for c in cases if c["strategy"] == s and c["content_level"] == lvl])
                for lvl in sorted({c["content_level"] for c in cases})}
            for s in sorted({c["strategy"] for c in cases})},
        "cases": cases,
    }
    (run_dir / "adjudication.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def corrections_markdown(result: dict[str, Any]) -> str:
    """The disagreements the paper settled in the draft's favour, as a list for a curator to check."""
    level_name = {"fulltext": "full text", "abstract": "abstract only", "title": "title only"}
    seen: set[tuple[str, str]] = set()
    cases = []
    for case in sorted(result["cases"], key=lambda c: (c["content_level"] != "fulltext", c["mim"])):
        key = (case["mim"], case["omim_states"].lower()[:60])
        if case["ruling"] != "draft" or key in seen:
            continue
        seen.add(key)
        cases.append(case)
    out = [
        f"# Candidate corrections to OMIM text — run `{result['run']}`",
        "Points where a generated draft and OMIM's own paragraph about the same paper state incompatible things, "
        "and the paper's text supports the draft. Each was decided by a judge model that had to quote the deciding "
        "passage, and the quote was verified to be in the paper.",
        "**These are leads, not findings.** The OMIM wording compared here is the copy OMIM deposited in ClinVar, "
        "which may lag the live entry. Where only the abstract could be read, OMIM's version may come from the full "
        "text. A curator should confirm each one against the paper and the current entry before anything is changed.",
        f"{len(cases)} distinct points, full-text cases first.",
        "| Entry | Paper | Read as | OMIM states | What the paper says | Deciding quote |",
        "|---|---|---|---|---|---|",
    ]
    cell = lambda text: squash(text).replace("|", "\\|")  # noqa: E731
    for case in cases:
        papers = ", ".join(f"[{p}](https://pubmed.ncbi.nlm.nih.gov/{p}/)" for p in case["pmids"])
        out.append(f"| [{case['mim']}](https://omim.org/entry/{case['mim']}) {cell(case['title'].title())} | {papers} | "
                   f"{level_name.get(case['content_level'], case['content_level'])} | {cell(case['omim_states'])} | "
                   f"{cell(case['explanation'])} | “{cell(case['quote'])}” |")
    return "\n\n".join(out[:4]) + "\n\n" + "\n".join(out[4:]) + "\n"
