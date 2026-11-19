"""Learn a curation guide from a training split: what OMIM chooses to say.

Drafts convey about half of OMIM's per-paper facts and list about twice as many
clinical-synopsis terms as OMIM. Part of that gap is access (the writer had only
the abstract), part is editorial choice. This module tries to learn the
editorial part from examples, in the spirit of reflective prompt optimisers
(GEPA, DSPy) but with a budget of a couple of rounds rather than thousands of
runs:

1. Feedback from the training entries only, from the baseline's results:
   facts that were in the available text but omitted (`gaps.py`), draft
   statements with no counterpart in OMIM's paragraph (`editorial.py`), and
   clinical-synopsis terms missed and extra (`eval.<strategy>.json`).
2. Reflection (stage "reflect"): the model turns the feedback into a guide of
   general, disease-independent rules (at most about 600 words).
3. Round evaluation: the training entries are regenerated with the guide in a
   separate run folder, scored (fact coverage, synopsis; no audit), compared
   with the baseline regenerated the same way, and the model reflects again on
   what is still missed and what got worse.
4. Selection by a rule fixed in advance (`SELECTION_RULE`), and two mechanical
   checks before anything is saved: the guide shares no run of 8 or more words
   with any OMIM paragraph, and names no gene of the evaluation set.

The guide and its log go to `guides/` (tracked by git), so neither may contain
OMIM-authored text: the log holds the guides, numbers and the rule, nothing else.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel

from .evalset import STRATA, stratum_of

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# The split
# --------------------------------------------------------------------------- #

SPLIT_SEED = 20261119
FORCED_TEST = ("500001",)   # the worked example stays out of training


def split_rows(lines: list[str], n_train: int = 30, seed: int = SPLIT_SEED,
               force_test: Iterable[str] = FORCED_TEST) -> tuple[list[str], list[str]]:
    """Split evaluation-set rows into train and test, stratified by MIM-range stratum.

    Each stratum contributes to training in proportion to its size (largest
    remainder), drawn with a generator seeded by `seed` and the stratum's label, so
    the split does not depend on row order. Rows keep their source order.
    """
    rows = [ln for ln in lines if ln.split("\t")[0].strip().isdigit()]
    force = set(force_test)
    by_stratum: dict[str, list[str]] = {}
    for ln in rows:
        by_stratum.setdefault(stratum_of(ln.split("\t")[0].strip()), []).append(ln.split("\t")[0].strip())
    order = [label for label, _ in STRATA if label in by_stratum] + sorted(set(by_stratum) - {lb for lb, _ in STRATA})
    total = len(rows)
    exact = {s: n_train * len(by_stratum[s]) / total for s in order}
    quota = {s: int(exact[s]) for s in order}
    for s in sorted(order, key=lambda s: (-(exact[s] - quota[s]), order.index(s)))[: n_train - sum(quota.values())]:
        quota[s] += 1
    train: set[str] = set()
    for s in order:
        pool = sorted(m for m in by_stratum[s] if m not in force)
        random.Random(f"{seed}:{s}").shuffle(pool)
        if len(pool) < quota[s]:
            raise ValueError(f"stratum {s} has {len(pool)} eligible entries for a quota of {quota[s]}")
        train.update(pool[: quota[s]])
    return ([ln for ln in rows if ln.split("\t")[0].strip() in train],
            [ln for ln in rows if ln.split("\t")[0].strip() not in train])


def write_split(source: Path, train_path: Path, test_path: Path, n_train: int = 30, seed: int = SPLIT_SEED) -> tuple[int, int]:
    lines = source.read_text(encoding="utf-8").splitlines()
    header = [ln for ln in lines[:1] if not ln.split("\t")[0].strip().isdigit()]
    train, test = split_rows(lines, n_train=n_train, seed=seed)
    for path, rows in ((train_path, train), (test_path, test)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(header + rows) + "\n", encoding="utf-8")
    return len(train), len(test)


# --------------------------------------------------------------------------- #
# Mechanical checks on a guide
# --------------------------------------------------------------------------- #

OVERLAP_WORDS = 8
_WORD = re.compile(r"[a-z0-9]+")


class GuideLeak(RuntimeError):
    """The guide contains OMIM wording or a disease-specific name; it must not be saved."""


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def shared_runs(guide: str, references: Iterable[str], n: int = OVERLAP_WORDS) -> list[str]:
    """Runs of `n` consecutive words (case and punctuation ignored) that the guide shares with any reference."""
    words = _words(guide)
    grams = {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}
    if not grams:
        return []
    hits: set[tuple[str, ...]] = set()
    for ref in references:
        rw = _words(ref)
        for i in range(len(rw) - n + 1):
            g = tuple(rw[i:i + n])
            if g in grams:
                hits.add(g)
    return sorted(" ".join(g) for g in hits)


def named_genes(guide: str, symbols: Iterable[str]) -> list[str]:
    """Gene symbols (3+ characters, matched case-sensitively as whole words) that appear in the guide."""
    found = []
    for sym in sorted({s for s in symbols if s and len(s) >= 3}):
        if re.search(rf"(?<![A-Za-z0-9-]){re.escape(sym)}(?![A-Za-z0-9-])", guide):
            found.append(sym)
    return found


def named_titles(guide: str, titles: Iterable[str]) -> list[str]:
    low = " ".join(_words(guide))
    return sorted({t for t in titles if len(_words(t)) >= 2 and " ".join(_words(t)) in low})


def check_guide(guide: str, references: Iterable[str], symbols: Iterable[str] = (),
                titles: Iterable[str] = ()) -> dict[str, Any]:
    runs = shared_runs(guide, references)
    genes = named_genes(guide, symbols)
    named = named_titles(guide, titles)
    # The report names how many runs were found, never the runs themselves (they are OMIM's wording).
    return {"ok": not (runs or genes or named), "shared_8word_runs": len(runs), "gene_symbols": genes,
            "entry_titles": len(named), "words": len(guide.split())}


def assert_clean(guide: str, references: Iterable[str], symbols: Iterable[str] = (), titles: Iterable[str] = ()) -> dict[str, Any]:
    result = check_guide(guide, references, symbols, titles)
    if not result["ok"]:
        raise GuideLeak(
            f"guide rejected: {result['shared_8word_runs']} run(s) of {OVERLAP_WORDS}+ words shared with OMIM "
            f"paragraphs, gene symbols named: {result['gene_symbols'] or 'none'}, entry titles named: "
            f"{result['entry_titles']}")
    return result


def gold_material(run_dir: Path) -> tuple[list[str], set[str], list[str]]:
    """OMIM paragraphs, gene symbols and entry titles of every entry in a run (for the checks)."""
    texts, symbols, titles = [], set(), []
    for path in sorted(run_dir.glob("*/gold.json")):
        gold = json.loads(path.read_text(encoding="utf-8"))
        texts += [p.get("text", "") for p in gold.get("gold_paragraphs", [])]
        texts += [p.get("text", "") for av in gold.get("allelic_variants", []) for p in av.get("paragraphs", [])
                  if isinstance(p, dict)]
        texts += [t for t in (gold.get("omim_text") or {}).values() if isinstance(t, str)]
        if gold.get("definition"):
            texts.append(gold["definition"])
        symbols |= {g.get("symbol", "") for g in gold.get("genes", [])}
        symbols |= {av.get("gene_symbol", "") for av in gold.get("allelic_variants", [])}
        if gold.get("title"):
            titles.append(gold["title"])
    return texts, {s for s in symbols if s}, titles


# --------------------------------------------------------------------------- #
# Feedback for the reflection
# --------------------------------------------------------------------------- #

MAX_MISSED = 14
MAX_EXTRA = 10
MAX_TERMS = 14


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _term(label: str) -> str:
    return label.split(" ", 1)[1] if label.startswith("HP:") and " " in label else label


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.0f}%"


def entry_feedback(entry_dir: Path, strategy: str, baseline_dir: Path | None = None,
                   baseline_strategy: str = "direct") -> str:
    """One entry's feedback: facts omitted though available, extras, synopsis misses and extras."""
    evaluation = _load(entry_dir / f"eval.{strategy}.json") or {}
    gaps = _load(entry_dir / f"gaps.{strategy}.json") or {"paragraphs": []}
    editorial = _load(entry_dir / f"editorial.{strategy}.json") or {"paragraphs": [], "summary": {}}
    papers = {r["pmid"]: r for r in (_load(entry_dir / "papers.json") or [])}
    levels: dict[str, int] = {}
    for r in papers.values():
        levels[r["content_level"]] = levels.get(r["content_level"], 0) + 1

    def label(pmids: list[str], level: str) -> str:
        names = ", ".join(papers[p]["label"] if p in papers else p for p in pmids)
        return f"[{names}; {level}]"

    syn = evaluation.get("synopsis", {})
    ex = syn.get("exact", {})
    gt = evaluation.get("gold_text", {})
    ed = editorial.get("summary", {})
    lines = [f"### {evaluation.get('title', entry_dir.name).title()}",
             f"Papers: {', '.join(f'{n} {lvl}' for lvl, n in sorted(levels.items()))}. "
             f"OMIM facts conveyed {_pct(gt.get('coverage'))}; synopsis terms: draft {ex.get('n_predicted', '?')}, "
             f"OMIM {ex.get('n_gold', '?')}, precision {_pct(ex.get('precision'))}, recall {_pct(ex.get('recall'))}; "
             f"draft statements per paper {ed.get('statements_per_paper', 'n/a')} against OMIM facts per paper "
             f"{ed.get('omim_facts_per_paper', 'n/a')}."]
    if baseline_dir is not None:
        base = _load(baseline_dir / f"eval.{baseline_strategy}.json") or {}
        bed = (_load(baseline_dir / f"editorial.{baseline_strategy}.json") or {}).get("summary", {})
        bex = base.get("synopsis", {}).get("exact", {})
        lines.append(f"Without the guide: facts conveyed {_pct(base.get('gold_text', {}).get('coverage'))}, "
                     f"synopsis precision {_pct(bex.get('precision'))}, recall {_pct(bex.get('recall'))}, "
                     f"{bex.get('n_predicted', '?')} terms; statements per paper {bed.get('statements_per_paper', 'n/a')}.")

    missed = [(p, f) for p in gaps["paragraphs"] for f in p["facts"] if f["in_text"] in ("yes", "partly")]
    missed.sort(key=lambda pf: (pf[1]["in_text"] != "yes", pf[1]["draft_status"] != "absent"))
    if missed:
        lines.append("OMIM states, and the available text contains, but the draft left out (absent) or blurred (partial):")
        for p, f in missed[:MAX_MISSED]:
            lines.append(f"- {label(p['pmids'], p['content_level'])} {f['fact']} "
                         f"(draft: {f['draft_status']}; in text: {f['in_text']})")
        if len(missed) > MAX_MISSED:
            lines.append(f"- … and {len(missed) - MAX_MISSED} more")
    n_unavailable = sum(1 for p in gaps["paragraphs"] for f in p["facts"] if f["in_text"] == "no")
    if n_unavailable:
        lines.append(f"({n_unavailable} further OMIM facts were not in the available text; nothing to learn there.)")

    extras = [(p, s) for p in editorial["paragraphs"] for s in p.get("statements", []) if s["counterpart"] == "no"]
    if extras:
        lines.append("The draft said, but OMIM's paragraph about the same paper does not:")
        for p, s in extras[:MAX_EXTRA]:
            lines.append(f"- {label(p['pmids'], p['content_level'])} {s['statement']}")
        if len(extras) > MAX_EXTRA:
            lines.append(f"- … and {len(extras) - MAX_EXTRA} more")

    missed_terms = [_term(t) for t in syn.get("missed", [])]
    extra_terms = [_term(t) for t in syn.get("extra", [])]
    if missed_terms:
        more = f" (+{len(missed_terms) - MAX_TERMS} more)" if len(missed_terms) > MAX_TERMS else ""
        lines.append(f"Synopsis terms OMIM lists that the draft did not: {'; '.join(missed_terms[:MAX_TERMS])}{more}.")
    if extra_terms:
        more = f" (+{len(extra_terms) - MAX_TERMS} more)" if len(extra_terms) > MAX_TERMS else ""
        lines.append(f"Synopsis terms the draft listed that OMIM does not: {'; '.join(extra_terms[:MAX_TERMS])}{more}.")
    return "\n".join(lines)


def build_feedback(run_dir: Path, strategy: str, entries: list[str], baseline_run: Path | None = None,
                   baseline_strategy: str = "direct") -> str:
    blocks = []
    for mim in entries:
        d = run_dir / mim
        if not (d / f"eval.{strategy}.json").exists():
            continue
        blocks.append(entry_feedback(d, strategy, baseline_run / mim if baseline_run else None, baseline_strategy))
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# Reflection
# --------------------------------------------------------------------------- #

REFLECT_SYSTEM = """\
You are improving the instructions given to a model that drafts entries for OMIM (Online Mendelian \
Inheritance in Man) from the papers OMIM cites. The writer already follows OMIM house style, gives \
each paper its own paragraph, and writes only what the supplied papers say; every sentence is then \
audited against the papers. Its drafts were compared with what OMIM's curators wrote about the same \
papers. For a set of training entries you are given: facts OMIM reports that were in the text the \
writer had but that the draft left out or blurred; statements the draft made that OMIM's paragraph \
about the same paper does not make; and the clinical-synopsis terms OMIM lists that the draft did \
not, and those the draft listed that OMIM does not. (Facts that were not in the writer's text are \
counted but not listed: the writer could not have known them.)

Write a CURATION GUIDE: general rules that will bring the writer's choices closer to OMIM's on \
entries it has not seen. Cover:
- what OMIM reports about each paper: which kinds of facts it keeps, and in what order;
- the level of detail: which numbers, ages, measurements, zygosity, segregation and functional \
results it gives, and how precisely;
- what OMIM leaves out;
- how OMIM chooses clinical-synopsis terms: how many, how specific, which kinds of findings become \
terms and which do not.

Requirements:
- Every rule must be general and disease-independent, applicable to any Mendelian disorder. Do not \
name any disease, gene, protein, variant, population, author or paper, and do not copy phrases from \
the feedback; describe kinds of facts instead ("the age at onset", "residual enzyme activity as a \
percentage of control").
- Never tell the writer to state anything the supplied papers do not say. The guide is about which of \
the papers' statements to choose and how to phrase them.
- Prefer patterns the feedback shows across several entries over ones driven by a single entry. A \
rule that makes the writer say more must say what to drop in exchange: a draft that only grows is \
not closer to OMIM.
- At most 600 words: a markdown list under a few short headings, starting with the heading \
"## Curation guide", written as instructions to the writer.

If a previous guide is supplied, you are also given its scores on the training entries against the \
writer without a guide, and feedback on the drafts written with it. Revise it: keep what helped, \
change or drop what did not, and correct what made the scores worse. Return the complete revised \
guide, not a list of changes.

In `rationale` (not part of the guide), say briefly which patterns in the feedback each part of the \
guide answers.\
"""


class XGuide(BaseModel):
    guide: str
    rationale: str


def _scores_text(scores: dict[str, Any], baseline: dict[str, Any]) -> str:
    rows = [("OMIM facts conveyed (coverage)", "gold_fact_coverage"),
            ("Synopsis exact F1", "synopsis_exact_f1"), ("Synopsis exact precision", "synopsis_exact_precision"),
            ("Synopsis exact recall", "synopsis_exact_recall"), ("Synopsis terms per entry", "synopsis_terms"),
            ("Draft statements per paper", "statements_per_paper"),
            ("Draft statements with an OMIM counterpart", "editorial_precision")]
    out = ["| Score | Without guide | With previous guide |", "|---|---|---|"]
    for name, key in rows:
        a, b = baseline.get(key), scores.get(key)
        out.append(f"| {name} | {'n/a' if a is None else a} | {'n/a' if b is None else b} |")
    return "\n".join(out)


def reflect(llm, feedback: str, previous: str | None = None, scores: dict[str, Any] | None = None,
            baseline: dict[str, Any] | None = None, max_words: int = 700) -> XGuide:
    parts = []
    if previous:
        parts.append(f"<previous_guide>\n{previous}\n</previous_guide>")
        parts.append(f"<scores on the training entries>\n{_scores_text(scores or {}, baseline or {})}\n</scores on the training entries>")
        parts.append(f"<feedback on drafts written with the previous guide>\n{feedback}\n</feedback on drafts written with the previous guide>")
    else:
        parts.append(f"<feedback on drafts written without a guide>\n{feedback}\n</feedback on drafts written without a guide>")
    prompt = "\n\n".join(parts)
    reply = llm.call("reflect", REFLECT_SYSTEM, prompt, XGuide)
    if len(reply.guide.split()) > max_words:
        log.warning("guide has %d words; asking for a shorter one", len(reply.guide.split()))
        reply = llm.call("reflect", REFLECT_SYSTEM,
                         prompt + f"\n\nYour previous answer was {len(reply.guide.split())} words long. Keep the guide "
                                  "under 600 words.", XGuide)
    return reply


# --------------------------------------------------------------------------- #
# Scores on the training entries
# --------------------------------------------------------------------------- #

SELECTION_RULE = (
    "Objective = (mean gold-fact coverage with the guide - without) + (mean clinical-synopsis exact F1 with the "
    "guide - without), over the training entries, both scored without the audit. A round is eligible only if its "
    "guide passes the mechanical checks (no run of 8+ words shared with any OMIM paragraph, no gene symbol or "
    "entry title of the evaluation set) and its draft statements per paper are at most 1.25 times the baseline's "
    "(a guide must not raise coverage by writing more). The eligible round with the highest objective is kept; "
    "if no round has a positive objective, the best is still saved and the log says there was no gain."
)
MAX_GROWTH = 1.25


def _mean(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return round(sum(kept) / len(kept), 4) if kept else None


def training_scores(run_dir: Path, strategy: str, entries: list[str]) -> dict[str, Any]:
    """Mean scores over `entries` that have a scored draft (numbers only)."""
    evals, editorials = [], []
    for mim in entries:
        e = _load(run_dir / mim / f"eval.{strategy}.json")
        if e is None:
            continue
        evals.append(e)
        ed = _load(run_dir / mim / f"editorial.{strategy}.json")
        if ed is not None:
            editorials.append(ed)
    pick = lambda path: [_get(e, path) for e in evals]  # noqa: E731
    paragraphs = [p for ed in editorials for p in ed["paragraphs"] if "error" not in p]
    n_st = sum(p["n_statements"] for p in paragraphs)
    yes, partly = sum(p["yes"] for p in paragraphs), sum(p["partly"] for p in paragraphs)
    return {
        "n_entries": len(evals),
        "entries": sorted(e["mim"] for e in evals),
        "gold_fact_coverage": _mean(pick("gold_text.coverage")),
        "gold_fact_contradiction_rate": _mean(pick("gold_text.contradiction_rate")),
        "synopsis_exact_f1": _mean(pick("synopsis.exact.f1")),
        "synopsis_exact_precision": _mean(pick("synopsis.exact.precision")),
        "synopsis_exact_recall": _mean(pick("synopsis.exact.recall")),
        "synopsis_hierarchical_f1": _mean(pick("synopsis.hierarchical.f1")),
        "synopsis_terms": _mean(pick("synopsis.exact.n_predicted")),
        "variant_recall": _mean(pick("variants.recall")),
        "statements_per_paper": round(n_st / len(paragraphs), 3) if paragraphs else None,
        "editorial_precision": round((yes + 0.5 * partly) / n_st, 4) if n_st else None,
    }


def _get(node: Any, path: str) -> Any:
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def objective(scores: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    dc = (scores["gold_fact_coverage"] or 0) - (baseline["gold_fact_coverage"] or 0)
    df = (scores["synopsis_exact_f1"] or 0) - (baseline["synopsis_exact_f1"] or 0)
    growth = (scores["statements_per_paper"] / baseline["statements_per_paper"]
              if scores.get("statements_per_paper") and baseline.get("statements_per_paper") else None)
    return {"coverage_gain": round(dc, 4), "synopsis_f1_gain": round(df, 4), "objective": round(dc + df, 4),
            "statements_growth": None if growth is None else round(growth, 3),
            "grows_too_much": growth is not None and growth > MAX_GROWTH}


def choose_round(rounds: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [r for r in rounds if r["checks"]["ok"] and not r["selection"]["grows_too_much"]]
    return max(eligible, key=lambda r: (r["selection"]["objective"], -r["round"]), default=None)


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #


def _ensure_analyses(run_dir: Path, strategy: str, entries: list[str], jobs: int, llm) -> None:
    """Gap and editorial files for the given entries, computed where missing (run-level summaries untouched)."""
    from .editorial import editorial_run
    from .gaps import gaps_run

    missing_gaps = [m for m in entries if not (run_dir / m / f"gaps.{strategy}.json").exists()]
    if missing_gaps:
        log.info("gap analysis for %d entries of %s", len(missing_gaps), run_dir.name)
        gaps_run(run_dir, strategy, entries=missing_gaps, jobs=jobs, llm=llm, write_run_files=False)
    missing_ed = [m for m in entries if not (run_dir / m / f"editorial.{strategy}.json").exists()]
    if missing_ed:
        log.info("editorial precision for %d entries of %s", len(missing_ed), run_dir.name)
        editorial_run(run_dir, (strategy,), entries=missing_ed, jobs=jobs, llm=llm, write_run_files=False)


def _generate(run_name: str, strategy: str, entries: list[str], jobs: int) -> None:
    from .pipeline import RunConfig, run_many

    cfg = RunConfig(run=run_name, retrieval="oracle", strategies=(strategy,), verify=False, repair=False)
    summary = run_many(entries, cfg, jobs=jobs)
    if summary.get("failures"):
        log.warning("%s: %d entries failed: %s", run_name, len(summary["failures"]), summary["failures"])


def learn_guide(
    run: str, train_file: Path, out: Path, rounds: int = 2, work: str | None = None, strategy: str = "direct",
    jobs: int = 3,
) -> dict[str, Any]:
    from .config import get_settings
    from .gaps import read_entries_file
    from .llm import LLM
    from .pipeline import _write

    settings = get_settings()
    base_dir = settings.runs / run
    work = work or f"{run}_guide_train"
    work_dir = settings.runs / work
    train = read_entries_file(train_file)
    llm = LLM(settings)
    references, symbols, titles = gold_material(base_dir)
    if not references:
        raise RuntimeError(f"no gold paragraphs found under {base_dir}; the overlap check would be vacuous")

    # 1. Baseline analyses on the training entries, from the main run.
    _ensure_analyses(base_dir, strategy, train, jobs, llm)

    # The baseline regenerated without the audit, so that it is scored exactly as the guided drafts will be.
    # Its generation call is the main run's, from cache.
    _generate(f"{work}/baseline", strategy, train, jobs)
    _ensure_analyses(work_dir / "baseline", strategy, train, jobs, llm)
    baseline = training_scores(work_dir / "baseline", strategy, train)
    log.info("baseline on %d training entries: %s", baseline["n_entries"], baseline)

    history: list[dict[str, Any]] = []
    feedback = build_feedback(base_dir, strategy, train)
    previous: str | None = None
    prev_scores: dict[str, Any] | None = None
    for k in range(1, rounds + 1):
        round_dir = work_dir / f"round{k}"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "feedback.txt").write_text(feedback, encoding="utf-8")   # git-ignored; holds OMIM facts
        reply = reflect(llm, feedback, previous, prev_scores, baseline)
        guide = reply.guide.strip()
        (round_dir / "guide.md").write_text(guide + "\n", encoding="utf-8")
        (round_dir / "rationale.txt").write_text(reply.rationale, encoding="utf-8")
        checks = check_guide(guide, references, symbols, titles)
        log.info("round %d: guide of %d words, checks %s", k, checks["words"], checks)

        os.environ["AIOMIM_GUIDE"] = str(round_dir / "guide.md")
        _generate(f"{work}/round{k}", "guided", train, jobs)
        common = [m for m in train if (round_dir / m / "eval.guided.json").exists()
                  and (work_dir / "baseline" / m / f"eval.{strategy}.json").exists()]
        from .editorial import editorial_run
        editorial_run(round_dir, ("guided",), entries=common, jobs=jobs, llm=llm, write_run_files=False)
        scores = training_scores(round_dir, "guided", common)
        base_same = training_scores(work_dir / "baseline", strategy, common)
        selection = objective(scores, base_same)
        log.info("round %d scores: %s; selection %s", k, scores, selection)
        history.append({
            "round": k, "guide": guide, "words": checks["words"],
            "sha256": hashlib.sha256(guide.encode("utf-8")).hexdigest(),
            "checks": checks, "scores": scores, "baseline_same_entries": base_same, "selection": selection,
        })
        if k < rounds:
            from .gaps import gaps_run
            gaps_run(round_dir, "guided", entries=common, jobs=jobs, llm=llm, write_run_files=False)
            feedback = build_feedback(round_dir, "guided", common, baseline_run=work_dir / "baseline",
                                      baseline_strategy=strategy)
            previous, prev_scores = guide, scores

    chosen = choose_round(history)
    if chosen is None:
        raise GuideLeak("no round produced an eligible guide (see the checks in the run folder); nothing saved")
    assert_clean(chosen["guide"], references, symbols, titles)   # again, right before saving
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(chosen["guide"] + "\n", encoding="utf-8")
    record = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_run": run, "work_run": work, "train_file": str(train_file), "n_train": len(train),
        "train_entries": train, "strategy": strategy, "rounds": rounds,
        "selection_rule": SELECTION_RULE, "max_statements_growth": MAX_GROWTH,
        "models": {"reflect": settings.model_for("reflect"), "synthesize": settings.model_for("synthesize"),
                   "judge": settings.model_for("judge")},
        "baseline": baseline,
        # A guide that failed the checks may hold OMIM wording: its text stays in the git-ignored run folder.
        "history": [{**r, "guide": r["guide"] if r["checks"]["ok"] else "(withheld: failed the checks)"}
                    for r in history],
        "chosen_round": chosen["round"],
        "no_gain": chosen["selection"]["objective"] <= 0,
        "guide_path": str(out), "guide_sha256": chosen["sha256"],
    }
    log_path = out.with_name(out.name[:-3] + ".log.json" if out.name.endswith(".md") else out.name + ".log.json")
    _write(log_path, record)
    _write(work_dir / "guide_learn.json", record)
    return record
