"""Why a draft misses OMIM's facts: access or omission.

Gold-fact coverage says how many of the facts in OMIM's paragraph about a paper
the draft conveys. A fact can be missing for two quite different reasons:

access     the fact was not in the text the writer was given (OMIM's curators
           read the whole paper; the writer often had only the abstract).
omission   the fact was in that text and the writer left it out (an editorial
           choice that might be learned).

For every scored OMIM paragraph, the facts the draft did not fully convey
(status absent or partial in `eval.<strategy>.json`) go to a judge together with
the text that was available for that paper, truncated exactly as the writer saw
it. The judge says for each fact whether the text states it (yes / partly / no)
and quotes the passage; a "yes" whose quote is not found in the text is
downgraded to "partly". One call per paragraph, stage "judge".

    <run>/<entry>/gaps.<strategy>.json   per fact: draft status, in text or not, quote
    <run>/gaps.<strategy>.json | .md     counts by how the paper could be read

The run-level files hold counts only, never fact wording.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from pydantic import BaseModel

from .grounding import SourceIndex
from .models import Paper, squash

log = logging.getLogger(__name__)

LEVELS = ("fulltext", "abstract", "title", "not_retrieved")
NOT_CONVEYED = ("absent", "partial")
VERDICTS = ("yes", "partly", "no", "unjudged")

# The direct writer's per-paper budget (see synthesize.synthesize_direct); the judge
# reads each paper cut at the same point, so "available" means available to the writer.
DIRECT_TOTAL_CHARS = 600_000
MIN_PER_PAPER = 20_000

GAPS_SYSTEM = """\
You are checking whether facts are stated in the text of a published paper. You are given a numbered \
list of FACTS, taken from a curator's summary of the paper (the summary itself is shown for context), \
and the TEXT of the paper as it was available to a writer: the full text where it could be read, \
otherwise only the abstract, or only the title.

For each fact, decide whether the supplied text states it:

yes     the text states the fact, in any wording or notation.
partly  the text states part of the fact, or states it less precisely (the finding without its \
number, the variant without its zygosity, the patients without their ages).
no      the supplied text does not state it.

Go by the supplied text alone, not by your own knowledge of the paper, the gene or the disorder. A \
fact that the full paper might contain but the supplied text does not is "no". Treat equivalent \
notations as the same ("3697G-A", "c.3697G>A" and "m.3697G>A"; "gly131-to-ser", "G131S" and \
"p.Gly131Ser"; "mental retardation" and "intellectual disability"). A number the text gives in a table \
or figure legend counts. For yes and partly, copy into `quote` the passage of the text that states \
it, character for character (one continuous span, at most about 40 words); for no, leave it empty. \
Give one verdict per fact, using the fact's number.\
"""


class XGapVerdict(BaseModel):
    n: int
    in_text: Literal["yes", "partly", "no"]
    quote: str


class XGapVerdicts(BaseModel):
    verdicts: list[XGapVerdict]


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


def read_entries_file(path: str | Path) -> list[str]:
    """MIM numbers from the first column of a TSV (header and comments skipped)."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        token = line.split("\t")[0].strip()
        if token.isdigit():
            out.append(token)
    return out


def entry_dirs(run_dir: Path, strategy: str, entries: Iterable[str] | None = None) -> list[Path]:
    """Entry folders of a run that have a scored draft for `strategy`, optionally restricted."""
    wanted = set(entries) if entries is not None else None
    return [p.parent for p in sorted(run_dir.glob(f"*/eval.{strategy}.json"))
            if wanted is None or p.parent.name in wanted]


def per_paper_chars(n_papers: int) -> int:
    return max(MIN_PER_PAPER, DIRECT_TOTAL_CHARS // max(1, n_papers))


def load_entry_papers(entry_dir: Path) -> dict[str, Paper]:
    """The papers of an entry with their text, from the same (cached) sources the run used."""
    from .sources.fulltext import load_papers

    records = json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))
    papers = load_papers([r["pmid"] for r in records], with_fulltext=True)
    # The run recorded how much of each paper it could read; a later fetch that finds
    # more (or less) would judge against text the writer never had.
    recorded = {r["pmid"]: r.get("content_level") for r in records}
    for p in papers:
        if recorded.get(p.pmid) and p.content_level != recorded[p.pmid]:
            log.warning("[%s] paper %s now reads as %s, run had %s", entry_dir.name, p.pmid,
                        p.content_level, recorded[p.pmid])
    return {p.pmid: p for p in papers}


# --------------------------------------------------------------------------- #
# One entry
# --------------------------------------------------------------------------- #


def _prompt(reference: str, facts: list[str], source: str) -> str:
    listed = "\n".join(f"{i}. {fact}" for i, fact in enumerate(facts, 1))
    return (f"<summary>\n{reference}\n</summary>\n\n<facts>\n{listed}\n</facts>\n\n{source}")


def gap_entry(entry_dir: Path, strategy: str, llm, papers: dict[str, Paper]) -> dict[str, Any]:
    """Judge, for one entry, which of the facts the draft missed were in the available text."""
    evaluation = json.loads((entry_dir / f"eval.{strategy}.json").read_text(encoding="utf-8"))
    paragraphs = evaluation.get("gold_text", {}).get("paragraphs", [])
    n_papers = len(json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))) \
        if (entry_dir / "papers.json").exists() else len(papers)
    cap = per_paper_chars(n_papers)

    jobs: list[tuple[int, list[int], str, str]] = []   # paragraph index, fact indexes, prompt, source text
    out_paragraphs: list[dict[str, Any]] = []
    for pi, para in enumerate(paragraphs):
        facts = para.get("facts", [])
        missed = [fi for fi, f in enumerate(facts) if f["status"] in NOT_CONVEYED]
        record = {
            "pmids": para["pmids"], "content_level": para.get("content_level", "not_retrieved"),
            "n_facts": len(facts),
            "draft_status": _count(f["status"] for f in facts),
            "facts": [],
        }
        out_paragraphs.append(record)
        if not missed:
            continue
        blocks = []
        for pmid in para["pmids"]:
            paper = papers.get(pmid)
            if paper is None:
                continue
            blocks.append(f'<paper pmid="{pmid}" available="{paper.content_level}">\n'
                          f"{paper.source_text(cap)}\n</paper>")
        if not blocks:
            record["facts"] = [{"fact": facts[fi]["fact"], "draft_status": facts[fi]["status"],
                                "in_text": "no", "model_in_text": None, "quote": "", "quote_verified": False}
                               for fi in missed]
            continue
        source = "\n\n".join(blocks)
        jobs.append((pi, missed, _prompt(para.get("reference", ""), [facts[fi]["fact"] for fi in missed], source),
                     source))

    replies = llm.map("judge", GAPS_SYSTEM, [j[2] for j in jobs], XGapVerdicts) if jobs else []
    n_errors = 0
    for (pi, missed, _, source), reply in zip(jobs, replies):
        facts = paragraphs[pi]["facts"]
        by_n: dict[int, XGapVerdict] = {}
        if isinstance(reply, Exception):
            n_errors += 1
            log.warning("[%s] gaps: paragraph %d failed: %s", entry_dir.name, pi, reply)
        else:
            for v in reply.verdicts:
                by_n.setdefault(v.n, v)
        index = SourceIndex(source)
        rows = []
        for k, fi in enumerate(missed, 1):
            v = by_n.get(k)
            row = {"fact": facts[fi]["fact"], "draft_status": facts[fi]["status"]}
            if v is None:
                row.update(in_text="unjudged", model_in_text=None, quote="", quote_verified=False)
            else:
                quote = squash(v.quote)
                verified = bool(quote) and index.contains(quote)
                final = v.in_text
                # A "yes" must point at the passage; one we cannot find is not a yes.
                if final == "yes" and not verified:
                    final = "partly"
                row.update(in_text=final, model_in_text=v.in_text, quote=quote, quote_verified=verified)
            rows.append(row)
        out_paragraphs[pi]["facts"] = rows

    result = {"mim": evaluation.get("mim", entry_dir.name), "strategy": strategy, "per_paper_chars": cap,
              "n_calls": len(jobs), "n_errors": n_errors, "paragraphs": out_paragraphs}
    result["tally"] = tally_entry(result)
    return result


def _count(values: Iterable[str]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for v in values:
        out[v] += 1
    return dict(out)


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def _empty_cell() -> dict[str, Any]:
    return {"n_gold_facts": 0, "present": 0, "contradicted": 0, "n_not_conveyed": 0,
            "by_draft_status": {s: {v: 0 for v in VERDICTS} for s in NOT_CONVEYED},
            **{v: 0 for v in VERDICTS}}


def _finish(cell: dict[str, Any]) -> dict[str, Any]:
    n = cell["n_not_conveyed"]
    judged = n - cell["unjudged"]
    cell["share_in_text"] = round(cell["yes"] / judged, 3) if judged else None
    cell["share_in_text_or_partly"] = round((cell["yes"] + cell["partly"]) / judged, 3) if judged else None
    cell["share_not_in_text"] = round(cell["no"] / judged, 3) if judged else None
    g = cell["n_gold_facts"]
    # The same facts as shares of everything OMIM said: conveyed / omitted though available / not available.
    cell["of_gold"] = {
        "present": round(cell["present"] / g, 3) if g else None,
        "missed_in_text": round(cell["yes"] / g, 3) if g else None,
        "missed_partly_in_text": round(cell["partly"] / g, 3) if g else None,
        "missed_not_in_text": round(cell["no"] / g, 3) if g else None,
    }
    return cell


def _add_paragraph(cell: dict[str, Any], para: dict[str, Any]) -> None:
    status = para.get("draft_status", {})
    cell["n_gold_facts"] += para.get("n_facts", 0)
    cell["present"] += status.get("present", 0)
    cell["contradicted"] += status.get("contradicted", 0)
    for f in para["facts"]:
        cell["n_not_conveyed"] += 1
        cell[f["in_text"]] += 1
        cell["by_draft_status"][f["draft_status"]][f["in_text"]] += 1


def tally_entry(result: dict[str, Any]) -> dict[str, Any]:
    cell = _empty_cell()
    for para in result["paragraphs"]:
        _add_paragraph(cell, para)
    return _finish(cell)


def summarize_gaps(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-entry gap results by how the paper could be read (counts only, no wording)."""
    by_level: dict[str, dict[str, Any]] = {}
    overall = _empty_cell()
    for result in results:
        for para in result["paragraphs"]:
            level = para.get("content_level", "not_retrieved")
            _add_paragraph(by_level.setdefault(level, _empty_cell()), para)
            _add_paragraph(overall, para)
    order = [lvl for lvl in LEVELS if lvl in by_level] + sorted(set(by_level) - set(LEVELS))
    return {
        "n_entries": len(results),
        "n_paragraphs": sum(len(r["paragraphs"]) for r in results),
        "n_calls": sum(r.get("n_calls", 0) for r in results),
        "n_errors": sum(r.get("n_errors", 0) for r in results),
        "quotes_verified": sum(1 for r in results for p in r["paragraphs"] for f in p["facts"] if f["quote_verified"]),
        "yes_downgraded": sum(1 for r in results for p in r["paragraphs"] for f in p["facts"]
                              if f.get("model_in_text") == "yes" and f["in_text"] != "yes"),
        "overall": _finish(overall),
        "by_content_level": {lvl: _finish(by_level[lvl]) for lvl in order},
    }


def gaps_markdown(summary: dict[str, Any], run: str, strategy: str) -> str:
    names = {"fulltext": "Full text", "abstract": "Abstract only", "title": "Title only",
             "not_retrieved": "Not retrieved", "all": "All papers"}
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    lines = [
        f"# Missed OMIM facts: access or omission — run `{run}`, strategy `{strategy}`",
        "For every OMIM paragraph about a cited paper, the facts the draft did not fully convey (judged absent or "
        "partial) were checked against the text the writer had for that paper. *In text* means the judge found "
        "the fact stated and quoted the passage (the quote was verified in the text); *partly* means part of it "
        "is stated, or a claimed quote could not be found; *not in text* means the available text does not state "
        "it, so a writer reading only that text could not have conveyed it.",
        f"{summary['n_entries']} entries, {summary['n_paragraphs']} OMIM paragraphs, {summary['n_calls']} judge "
        f"calls ({summary['n_errors']} failed).",
        "| Paper read as | OMIM facts | Conveyed | Not fully conveyed | … in text | … partly in text | … not in text "
        "| Unjudged | In text, share of missed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    rows = list(summary["by_content_level"].items()) + [("all", summary["overall"])]
    for level, c in rows:
        lines.append(f"| {names.get(level, level)} | {c['n_gold_facts']:,} | {c['present']:,} | {c['n_not_conveyed']:,} | "
                     f"{c['yes']:,} | {c['partly']:,} | {c['no']:,} | {c['unjudged']:,} | {pct(c['share_in_text'])} |")
    lines.append("")
    lines.append("By how much of the fact the draft conveyed (absent: not at all; partial: less precisely):")
    lines.append("")
    lines.append("| Paper read as | Draft | Missed | … in text | … partly | … not in text |")
    lines.append("|---|---|---|---|---|---|")
    for level, c in rows:
        for status in NOT_CONVEYED:
            s = c["by_draft_status"][status]
            n = sum(s.values())
            if n:
                lines.append(f"| {names.get(level, level)} | {status} | {n:,} | {s['yes']:,} | {s['partly']:,} | {s['no']:,} |")
    lines.append("")
    o = summary["overall"]["of_gold"]
    lines.append(f"Of all OMIM facts: {pct(o['present'])} conveyed, {pct(o['missed_in_text'])} omitted though stated in "
                 f"the available text, {pct(o['missed_partly_in_text'])} omitted and partly stated, "
                 f"{pct(o['missed_not_in_text'])} not in the available text; the remainder were contradicted. "
                 f"(Facts the draft conveyed partly are counted with the missed ones.)")
    return "\n\n".join(lines[:3]) + "\n\n" + "\n".join(lines[3:]) + "\n"


# --------------------------------------------------------------------------- #
# A run
# --------------------------------------------------------------------------- #


def gaps_run(
    run_dir: Path, strategy: str = "direct", entries: Iterable[str] | None = None, jobs: int = 1,
    llm=None, load: Callable[[Path], dict[str, Paper]] | None = None, write_run_files: bool = True,
) -> dict[str, Any]:
    """Gap analysis for every scored entry of a run; writes per-entry and run-level files."""
    from .llm import LLM
    from .pipeline import _write

    llm = llm or LLM()
    load = load or load_entry_papers
    dirs = entry_dirs(run_dir, strategy, entries)

    def one(entry_dir: Path) -> dict[str, Any] | None:
        try:
            result = gap_entry(entry_dir, strategy, llm, load(entry_dir))
        except Exception as exc:  # noqa: BLE001 - one broken entry must not lose the rest
            log.exception("[%s] gaps failed: %s", entry_dir.name, exc)
            return None
        _write(entry_dir / f"gaps.{strategy}.json", result)
        log.info("[%s] gaps: %d facts missed, %d in text", entry_dir.name, result["tally"]["n_not_conveyed"],
                 result["tally"]["yes"])
        return result

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        results = [r for r in pool.map(one, dirs) if r is not None]
    summary = {"run": run_dir.name, "strategy": strategy, **summarize_gaps(results),
               "entries": {r["mim"]: r["tally"] for r in results}}
    if write_run_files:
        _write(run_dir / f"gaps.{strategy}.json", summary)
        _write(run_dir / f"gaps.{strategy}.md", gaps_markdown(summary, run_dir.name, strategy))
    return summary


def load_entry_gaps(entry_dir: Path, strategy: str) -> dict[str, Any] | None:
    path = entry_dir / f"gaps.{strategy}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
