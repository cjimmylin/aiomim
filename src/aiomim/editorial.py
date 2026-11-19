"""Editorial precision: how much of what a draft says about a paper OMIM also says.

Fact coverage asks how many of OMIM's facts about a paper the draft conveys. A
draft can raise that number just by saying more. This is the reverse measure:
for every OMIM paragraph about a cited paper, what the draft says about that
same paper (found exactly as `evaluate.eval_gold_text` finds it) is split into
atomic statements, and each is marked as having a counterpart in OMIM's
paragraph (yes / partly / no). One call per paragraph, stage "judge".

    precision            share of draft statements OMIM also makes (partly counts half)
    statements per paper draft statements per OMIM paragraph, against OMIM facts per
                         paragraph (from the fact-coverage judge in eval.<strategy>.json)

A statement without a counterpart is not wrong: the OMIM text compared here is
the allelic-variant paragraph OMIM deposits in ClinVar, and OMIM may say the same
thing in a section that is not available for comparison. The number is useful
as a comparison between strategies on the same entries, not as an absolute.

    <run>/<entry>/editorial.<strategy>.json   per statement: text, counterpart
    <run>/editorial.<strategies>.json | .md   counts and rates (no OMIM wording)
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel

from .evaluate import _draft_text_for
from .models import GeneratedEntry, GoldEntry

log = logging.getLogger(__name__)

RANK = {"title": 0, "abstract": 1, "fulltext": 2}

EDITORIAL_SYSTEM = """\
You are comparing a machine-drafted OMIM entry with what OMIM's own curators wrote about the same \
paper. You are given the REFERENCE (the curators' paragraph about one or more papers), the citation \
label(s) of those papers, and the DRAFT text that cites them.

Split what the draft says about the work reported in the labelled paper(s) into atomic statements: \
single checkable assertions such as who was studied, how many patients or families, ancestry, each \
clinical, imaging or laboratory finding, each variant with its nucleotide change, protein change and \
zygosity, segregation or de novo status, each functional result, and each conclusion. Skip what the \
draft attributes to other papers that happen to share a paragraph, the bare attribution to the \
authors, and OMIM cross-reference numbers.

For each statement decide whether the reference makes the same statement:

yes     the reference states the same thing.
partly  the reference states something overlapping but less or more specific.
no      the reference does not state it.

Judge meaning, not wording, and treat equivalent notations as the same ("3697G-A", "c.3697G>A"; \
"gly131-to-ser", "p.Gly131Ser"; "mental retardation", "intellectual disability"). Keep each \
statement short and in the draft's own terms.\
"""


class XStatement(BaseModel):
    statement: str
    counterpart: Literal["yes", "partly", "no"]


class XStatements(BaseModel):
    statements: list[XStatement]


# --------------------------------------------------------------------------- #
# One entry
# --------------------------------------------------------------------------- #


def editorial_entry(entry_dir: Path, strategy: str, llm) -> dict[str, Any]:
    entry = GeneratedEntry.model_validate(json.loads((entry_dir / f"entry.{strategy}.json").read_text(encoding="utf-8")))
    gold = GoldEntry.model_validate(json.loads((entry_dir / "gold.json").read_text(encoding="utf-8")))
    records = {r["pmid"]: r for r in json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))}
    eval_path = entry_dir / f"eval.{strategy}.json"
    eval_paras = (json.loads(eval_path.read_text(encoding="utf-8")).get("gold_text", {}).get("paragraphs", [])
                  if eval_path.exists() else [])

    paragraphs = gold.scoped_paragraphs
    jobs: list[tuple[int, str]] = []
    out: list[dict[str, Any]] = []
    for i, para in enumerate(paragraphs):
        levels = [records[p]["content_level"] for p in para.pmids if p in records]
        level = min(levels, key=RANK.get) if levels else "not_retrieved"
        # OMIM facts for this paragraph, from the coverage judge (same order as scoped_paragraphs).
        n_facts = None
        if i < len(eval_paras) and eval_paras[i].get("pmids") == para.pmids:
            n_facts = eval_paras[i].get("n_facts")
        draft = _draft_text_for(entry, para.pmids)
        out.append({"pmids": para.pmids, "content_level": level, "n_omim_facts": n_facts, "statements": []})
        if not draft.strip():
            continue
        labels = ", ".join(f"{records[p]['label']} (PMID {p})" if p in records else f"PMID {p}" for p in para.pmids)
        jobs.append((i, f"Paper(s): {labels}\n\n<reference>\n{para.text}\n</reference>\n\n<draft>\n{draft}\n</draft>"))

    replies = llm.map("judge", EDITORIAL_SYSTEM, [p for _, p in jobs], XStatements) if jobs else []
    n_errors = 0
    for (i, _), reply in zip(jobs, replies):
        if isinstance(reply, Exception):
            n_errors += 1
            out[i]["error"] = str(reply)[:200]
            log.warning("[%s] editorial: paragraph %d failed: %s", entry_dir.name, i, reply)
            continue
        out[i]["statements"] = [s.model_dump() for s in reply.statements]
    for para in out:
        para.update(tally_statements(para["statements"]))
    result = {"mim": entry.mim or entry_dir.name, "strategy": strategy, "n_calls": len(jobs), "n_errors": n_errors,
              "paragraphs": out}
    result["summary"] = summarize_paragraphs(out)
    return result


def tally_statements(statements: list[dict[str, str]]) -> dict[str, Any]:
    counts = defaultdict(int)
    for s in statements:
        counts[s["counterpart"]] += 1
    n = len(statements)
    return {"n_statements": n, "yes": counts["yes"], "partly": counts["partly"], "no": counts["no"],
            "precision": round((counts["yes"] + 0.5 * counts["partly"]) / n, 3) if n else None}


def summarize_paragraphs(paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Pooled counts over paragraphs (OMIM paragraphs about a cited paper)."""
    valid = [p for p in paragraphs if "error" not in p]
    n_st = sum(p["n_statements"] for p in valid)
    yes, partly = sum(p["yes"] for p in valid), sum(p["partly"] for p in valid)
    with_facts = [p for p in valid if p.get("n_omim_facts") is not None]
    n_facts = sum(p["n_omim_facts"] for p in with_facts)
    st_with_facts = sum(p["n_statements"] for p in with_facts)
    return {
        "n_paragraphs": len(valid), "n_failed": len(paragraphs) - len(valid),
        "n_statements": n_st, "yes": yes, "partly": partly, "no": sum(p["no"] for p in valid),
        "precision": round((yes + 0.5 * partly) / n_st, 3) if n_st else None,
        "strict_precision": round(yes / n_st, 3) if n_st else None,
        "statements_per_paper": round(n_st / len(valid), 2) if valid else None,
        "omim_facts_per_paper": round(n_facts / len(with_facts), 2) if with_facts else None,
        "statements_per_omim_fact": round(st_with_facts / n_facts, 3) if n_facts else None,
    }


# --------------------------------------------------------------------------- #
# Aggregation over entries
# --------------------------------------------------------------------------- #


def _mean(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return round(sum(kept) / len(kept), 3) if kept else None


def summarize_editorial(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pooled and per-entry-mean editorial precision, overall and by content level."""
    paragraphs = [p for r in results for p in r["paragraphs"]]
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in paragraphs:
        by_level[p["content_level"]].append(p)
    order = [lvl for lvl in ("fulltext", "abstract", "title", "not_retrieved") if lvl in by_level]
    return {
        "n_entries": len(results),
        "n_calls": sum(r.get("n_calls", 0) for r in results),
        "n_errors": sum(r.get("n_errors", 0) for r in results),
        "pooled": summarize_paragraphs(paragraphs),
        "entry_mean": {
            "precision": _mean([r["summary"]["precision"] for r in results]),
            "statements_per_paper": _mean([r["summary"]["statements_per_paper"] for r in results]),
            "omim_facts_per_paper": _mean([r["summary"]["omim_facts_per_paper"] for r in results]),
        },
        "by_content_level": {lvl: summarize_paragraphs(by_level[lvl]) for lvl in order},
    }


def editorial_markdown(summary: dict[str, Any]) -> str:
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    num = lambda x: "-" if x is None else f"{x:.1f}"  # noqa: E731
    ratio = lambda x: "-" if x is None else f"{x:.2f}"  # noqa: E731
    lines = [
        f"# Editorial precision — run `{summary['run']}`",
        "What a draft says about each paper that has an OMIM paragraph, split into atomic statements and checked "
        "against that paragraph. *Precision* is the share of draft statements OMIM's paragraph also makes (partly "
        "counts half). The OMIM paragraph compared is the allelic-variant text deposited in ClinVar; a statement "
        "with no counterpart there may still be in another section of the OMIM entry, so the rate is for "
        "comparing strategies on the same entries.",
        f"Entries common to all strategies: {summary['n_entries']}.",
        "| Strategy | Statements | Precision (pooled) | Precision (entry mean) | Statements per paper | "
        "OMIM facts per paper | Statements per OMIM fact |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in summary["strategies"].items():
        p, m = s["pooled"], s["entry_mean"]
        lines.append(f"| {name} | {p['n_statements']:,} | {pct(p['precision'])} | {pct(m['precision'])} | "
                     f"{num(p['statements_per_paper'])} | {num(p['omim_facts_per_paper'])} | "
                     f"{ratio(p['statements_per_omim_fact'])} |")
    lines.append("")
    lines.append("| Strategy | Paper read as | Paragraphs | Statements | Precision | Statements per paper |")
    lines.append("|---|---|---|---|---|---|")
    for name, s in summary["strategies"].items():
        for level, c in s["by_content_level"].items():
            lines.append(f"| {name} | {level} | {c['n_paragraphs']} | {c['n_statements']:,} | {pct(c['precision'])} | "
                         f"{num(c['statements_per_paper'])} |")
    return "\n\n".join(lines[:3]) + "\n\n" + "\n".join(lines[3:]) + "\n"


# --------------------------------------------------------------------------- #
# A run
# --------------------------------------------------------------------------- #


def editorial_run(
    run_dir: Path, strategies: tuple[str, ...], entries: Iterable[str] | None = None, jobs: int = 1,
    llm=None, write_run_files: bool = True,
) -> dict[str, Any]:
    """Editorial precision for each strategy, over the entries every strategy has a scored draft for."""
    from .llm import LLM
    from .pipeline import _write

    llm = llm or LLM()
    wanted = set(entries) if entries is not None else None
    have = [{p.parent.name for p in run_dir.glob(f"*/entry.{s}.json")} for s in strategies]
    common = sorted(set.intersection(*have) if have else set())
    if wanted is not None:
        common = [e for e in common if e in wanted]

    out: dict[str, Any] = {"run": run_dir.name, "n_entries": len(common), "strategies": {}}
    for strategy in strategies:
        def one(folder: str) -> dict[str, Any] | None:
            entry_dir = run_dir / folder
            try:
                result = editorial_entry(entry_dir, strategy, llm)
            except Exception as exc:  # noqa: BLE001
                log.exception("[%s] editorial failed: %s", folder, exc)
                return None
            _write(entry_dir / f"editorial.{strategy}.json", result)
            return result

        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            results = [r for r in pool.map(one, common) if r is not None]
        out["strategies"][strategy] = {
            **summarize_editorial(results),
            "entries": {r["mim"]: r["summary"] for r in results},
        }
    if write_run_files:
        tag = "_".join(strategies)
        _write(run_dir / f"editorial.{tag}.json", out)
        _write(run_dir / f"editorial.{tag}.md", editorial_markdown(out))
    return out
