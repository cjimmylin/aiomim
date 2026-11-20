"""Experiment A1, the natural large-entry tier (docs/experiments-round2.md, section A1).

Two jobs, each a subcommand of `python -m aiomim.largetier`:

select    Draw the new entries (8; the design said 16) by the design's rule and write evalsets/largeft8.tsv.
          Eligible: phenotype entries passing the main set's rules (causal gene recorded, at least
          5 HPO phenotype annotations, at least one OMIM paragraph about a cited paper) with 30-150
          references, in no existing evaluation set. A seeded random sample of up to 200 of them (design: 400) is
          drawn; of those, the 8 (design: 16) with the most references readable in full (ties by entry number),
          requiring at least 5 (lowered to the last selected entry's count if fewer reach 5).

          Counting full texts for hundreds of entries must be cheap, so it is done in two steps
          that together give exactly the ranking the full count would: (1) the PubMed records of
          every cited paper are fetched in batches (200 per request) and the papers with a PMC
          identifier are counted - an upper bound on what can be read in full, because the
          project's full-text sources (Europe PMC open-access JATS, NCBI BioC) serve only PMC
          articles; (2) entries are resolved with the project's own access resolution
          (`evalset.describe_papers`, which retrieves the papers exactly as a run does), in
          descending order of the bound, until no unresolved entry's bound can reach the last
          place (`exact_top_k`).

analyze   The combined analysis of the old large12 entries (runs/large12, scored after the audit's
          repair round) and the new ones (runs/largeft, generation and scoring only), written to
          results/largeft/large_tier.json and large_tier.md. Only numbers, identifiers and
          verdict counts are written: no OMIM wording.

The run itself uses the existing command line unchanged (see results/largeft/large_tier.md).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import re
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

log = logging.getLogger("aiomim.largetier")

STRATEGIES = ("direct", "agent", "kg", "cohort")
LABELS = {"direct": "Direct reading", "agent": "Agentic curator", "kg": "Evidence graph", "cohort": "Case table first"}
BASELINE = "direct"

# Selection rule (fixed by the design).
MIN_REFS, MAX_REFS = 30, 150
MIN_HPO, MIN_PARAGRAPHS = 5, 1
SAMPLE_SIZE = 200          # design: up to 400; cut to 200 at the coordinator's request (slow lookup)
N_SELECT = 8               # design: 16; reduced to 8 at the user's request (smaller budget)
MIN_FULLTEXT = 5
SELECT_SEED = 2611
RESOLVE_PARALLEL = 4          # chosen for this experiment; recorded in the evaluation set's header

# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #


def mims_in(lines: Iterable[str]) -> list[str]:
    """MIM numbers from the first column of TSV lines (header and comment lines skipped)."""
    out = []
    for line in lines:
        token = line.split("\t")[0].strip()
        if token.isdigit() and token not in out:
            out.append(token)
    return out


def seeded_order(mims: Iterable[str], seed: int) -> list[str]:
    """The candidates sorted by MIM number, then shuffled with random.Random(seed)."""
    order = sorted(set(mims), key=int)
    random.Random(seed).shuffle(order)
    return order


def rank_key(mim: str, n_fulltext: int) -> tuple[int, int]:
    """Most references readable in full first; ties by entry number (lower first)."""
    return (-n_fulltext, int(mim))


def exact_top_k(bounds: dict[str, int], resolve: Callable[[str], int], k: int, batch: int = 1,
                mapper: Callable | None = None) -> tuple[list[str], dict[str, int]]:
    """The k entries with the highest resolved count, resolving as few as possible.

    `bounds[m]` is an upper bound on `resolve(m)`. Entries are resolved in order of
    (-bound, mim); resolution stops when the next entry cannot displace the current k-th
    (its bound is lower than the k-th count, or equal with a higher MIM number, since ties
    go to the lower number). With `batch` > 1, up to `batch` entries are resolved at a time
    through `mapper` (e.g. a thread pool's map); that may resolve a few more entries than
    needed but never changes the result. Returns the top k (in rank order) and every
    resolved count.
    """
    mapper = mapper or map
    order = sorted(bounds, key=lambda m: rank_key(m, bounds[m]))
    resolved: dict[str, int] = {}

    def can_enter(mim: str) -> bool:
        if len(resolved) < k:
            return True
        kth = sorted(resolved, key=lambda m: rank_key(m, resolved[m]))[k - 1]
        return rank_key(mim, bounds[mim]) <= rank_key(kth, resolved[kth])

    i = 0
    while i < len(order) and can_enter(order[i]):
        chunk = order[i:i + max(1, batch)]
        for mim, count in zip(chunk, mapper(resolve, chunk)):
            resolved[mim] = count
        i += len(chunk)
    top = sorted(resolved, key=lambda m: rank_key(m, resolved[m]))[:k]
    return top, resolved


def threshold_used(counts_of_selected: list[int], required: int = MIN_FULLTEXT) -> int:
    """The full-text requirement actually met: `required`, or lower if the selection needs it."""
    return min([required] + list(counts_of_selected)) if counts_of_selected else required


def sign_test(wins: int, losses: int) -> float | None:
    """Exact two-sided binomial test of wins against losses (ties dropped)."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def bootstrap_ci(diffs: list[float], seed: int = 7, n: int = 10_000) -> tuple[float, float] | None:
    """Percentile bootstrap 95% interval of the mean (None below 3 values)."""
    if len(diffs) < 3:
        return None
    rng = random.Random(seed)
    k = len(diffs)
    means = sorted(sum(rng.choices(diffs, k=k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def paired(values: dict[str, tuple[float, float]], tol: float = 1e-9) -> dict[str, Any]:
    """Paired comparison of (strategy, baseline) values per entry: mean difference, interval, signs."""
    diffs = [a - b for a, b in values.values()]
    wins = sum(1 for d in diffs if d > tol)
    losses = sum(1 for d in diffs if d < -tol)
    ci = bootstrap_ci(diffs)
    return {
        "n": len(diffs),
        "mean_strategy": _r(statistics.fmean(a for a, _ in values.values())) if diffs else None,
        "mean_baseline": _r(statistics.fmean(b for _, b in values.values())) if diffs else None,
        "mean_diff": _r(statistics.fmean(diffs)) if diffs else None,
        "ci95": [_r(ci[0]), _r(ci[1])] if ci else None,
        "better": wins, "worse": losses, "tied": len(diffs) - wins - losses,
        "sign_p": _r(sign_test(wins, losses)),
    }


def median_split(sizes: dict[str, float]) -> tuple[float | None, list[str], list[str]]:
    """Entries at or below the median size, and those above it."""
    if not sizes:
        return None, [], []
    med = statistics.median(sizes.values())
    lower = sorted((m for m, v in sizes.items() if v <= med), key=int)
    upper = sorted((m for m, v in sizes.items() if v > med), key=int)
    return med, lower, upper


def direct_prompts(meta: dict[str, Any]) -> int | None:
    """Writer prompts direct reading used: 1, or one per batch plus the merge call."""
    batching = (meta or {}).get("direct_batching")
    if not isinstance(batching, dict):
        return None
    if not batching.get("used"):
        return 1
    n = len(batching.get("batches") or [])
    return n + (1 if n > 1 else 0)


def reference_share(paragraph_pmids: Iterable[Iterable[str]], cited: Iterable[str]) -> tuple[int, float | None]:
    """How many of the entry's references the scored paragraphs are about, and that share."""
    cited = set(cited)
    covered = {p for pmids in paragraph_pmids for p in pmids if p in cited}
    return len(covered), (_r(len(covered) / len(cited)) if cited else None)


_RESOLVED_LINE = re.compile(r"resolved (\d+): (\d+) of (\d+) readable in full")


def counts_from_log(lines: Iterable[str]) -> dict[str, int]:
    """Readable-in-full counts an earlier (interrupted) selection logged, so a restart need not redo them."""
    out: dict[str, int] = {}
    for line in lines:
        m = _RESOLVED_LINE.search(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


_EVENT_LINE = re.compile(r"^(\d\d:\d\d:\d\d) INFO +resolved (\d+): (\d+) of")


def resolution_events(lines: Iterable[str]) -> list[tuple[str, str, int]]:
    """(time, mim, count) for every 'resolved' line of the selection log, in log order."""
    out = []
    for line in lines:
        m = _EVENT_LINE.search(line)
        if m:
            out.append((m.group(1), m.group(2), int(m.group(3))))
    return out


def could_rank_above(bounds: dict[str, int], resolved: dict[str, int], mim: str) -> list[str]:
    """Entries that rank, or might still rank, above `mim` (its count resolved; others by count or bound)."""
    me = rank_key(mim, resolved[mim])
    return [m for m in bounds if m != mim
            and rank_key(m, resolved[m] if m in resolved else bounds[m]) < me]


def first_certain(events: list[tuple[str, str, int]], bounds: dict[str, int], mim: str,
                  k: int) -> tuple[int, str] | None:
    """The first log event after which `mim` was certain to be in the top k, whatever the unresolved
    entries turn out to be: fewer than k entries could still rank above it. (index, time) or None."""
    resolved: dict[str, int] = {}
    for i, (when, m, n) in enumerate(events):
        resolved[m] = n
        if mim in resolved and len(could_rank_above(bounds, resolved, mim)) < k:
            return i, when
    return None


def selection_state(bounds: dict[str, int], resolved: dict[str, int], k: int) -> dict[str, Any]:
    """Top k of the resolved entries, and the unresolved entries whose bound could still displace the k-th."""
    top = sorted(resolved, key=lambda m: rank_key(m, resolved[m]))[:k]
    unresolved = sorted((m for m in bounds if m not in resolved), key=int)
    if len(top) < k:
        threats = unresolved
    else:
        kth = rank_key(top[-1], resolved[top[-1]])
        threats = [m for m in unresolved if rank_key(m, bounds[m]) < kth]
    return {"top": top, "unresolved": unresolved, "could_displace": threats, "finished": not threats,
            "max_unresolved_bound": max((bounds[m] for m in unresolved), default=None)}


def text_windows(text: str, width: int = 60, stride: int = 30) -> list[str]:
    """Overlapping whitespace-normalised windows of a text (the whole text if shorter than `width`)."""
    t = " ".join(text.split())
    if len(t) <= width:
        return [t] if t else []
    return [t[i:i + width] for i in range(0, len(t) - width + 1, stride)]


def leaked(gold_texts: Iterable[str], haystack: str, width: int = 60, min_len: int = 40) -> list[str]:
    """Windows of OMIM-derived texts (at least `min_len` characters) found verbatim in `haystack`."""
    hay = " ".join(haystack.split())
    hits = []
    for text in gold_texts:
        if len(" ".join(text.split())) < min_len:
            continue
        hits += [w for w in text_windows(text, width) if w in hay]
    return hits


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(x, nd)


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #


def existing_evalset_mims(root: Path) -> set[str]:
    out: set[str] = set()
    for path in sorted((root / "evalsets").glob("*.tsv")):
        if path.name.startswith("largeft"):
            continue
        out.update(mims_in(path.read_text(encoding="utf-8").splitlines()))
    return out


def draw_sample(exclude: set[str], seed: int, size: int) -> tuple[list[str], dict[str, Any]]:
    """Walk the seeded order of candidates; keep the first `size` that qualify."""
    from .evalset import _cheap_reject, candidates, qualifies
    from .gold import build_gold
    from .sources.hpo import get_hpo

    get_hpo()
    pool = [m for m in candidates() if m not in exclude]
    order = seeded_order(pool, seed)
    kept: list[str] = []
    walked = 0
    reasons: dict[str, int] = {}
    for mim in order:
        if len(kept) >= size:
            break
        walked += 1
        try:
            why = _cheap_reject(mim, MIN_REFS, MAX_REFS, MIN_HPO)
        except Exception as exc:  # noqa: BLE001 - fall through to the full check
            log.debug("prefilter failed for %s (%s)", mim, exc)
            why = ""
        if not why:
            try:
                gold = build_gold(mim)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s skipped (%s)", mim, exc)
                why = "gold could not be built"
            else:
                ok, why = qualifies(gold, MIN_REFS, MAX_REFS, MIN_HPO, MIN_PARAGRAPHS)
        if why:
            key = re.sub(r"\d+", "N", why)
            reasons[key] = reasons.get(key, 0) + 1
            continue
        kept.append(mim)
        if len(kept) % 25 == 0:
            log.info("sample: %d eligible after %d candidates walked", len(kept), walked)
    return kept, {"candidates_in_pool": len(pool), "walked": walked, "eligible": len(kept),
                  "rejections": dict(sorted(reasons.items(), key=lambda kv: -kv[1]))}


def pmc_bounds(mims: list[str]) -> dict[str, dict[str, int]]:
    """Per entry: references, PubMed records found, and records carrying a PMC id (batch lookup)."""
    from .gold import build_gold
    from .sources.ncbi import pubmed_fetch

    cited = {m: build_gold(m).cited_pmids for m in mims}
    union = sorted({p for v in cited.values() for p in v}, key=int)
    log.info("PubMed records for %d distinct references of %d entries", len(union), len(mims))
    records = {p.pmid: p for p in pubmed_fetch(union)}
    return {m: {"n_refs": len(v), "n_records": sum(1 for p in v if p in records),
                "n_pmc": sum(1 for p in v if p in records and records[p].pmcid)} for m, v in cited.items()}


def select(root: Path, seed: int = SELECT_SEED, out: Path | None = None, sample_size: int = SAMPLE_SIZE,
           n_select: int = N_SELECT) -> dict[str, Any]:
    from .evalset import describe_papers, stratum_of
    from .gold import build_gold

    started = time.time()
    exclude = existing_evalset_mims(root)
    sample, walk = draw_sample(exclude, seed, sample_size)
    bounds = pmc_bounds(sample)
    described: dict[str, dict[str, Any]] = {}
    # Resumable: counts already resolved (persisted, or logged by an interrupted earlier pass) are reused.
    # Re-resolving costs minutes per entry (Europe PMC full-text requests that time out are not cached).
    store = root / "runs" / "largeft" / "resolved.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    if store.exists():
        described.update(json.loads(store.read_text()))
    log_path = root / "runs" / "largeft" / "select.log"
    from_log = counts_from_log(log_path.read_text().splitlines()) if log_path.exists() else {}
    import threading
    lock = threading.Lock()

    def resolve(mim: str) -> int:
        if mim in described:
            return described[mim]["n_fulltext"]
        if mim in from_log:
            return from_log[mim]
        d = describe_papers(mim)
        with lock:
            described[mim] = d
            store.write_text(json.dumps(described, indent=1))
        log.info("resolved %s: %d of %d readable in full (bound %d)", mim, d["n_fulltext"],
                 bounds[mim]["n_refs"], bounds[mim]["n_pmc"])
        return d["n_fulltext"]

    from concurrent.futures import ThreadPoolExecutor

    # Europe PMC answers a full-text request in up to ~30 s, so a few entries are resolved at once.
    with ThreadPoolExecutor(max_workers=RESOLVE_PARALLEL) as pool:
        top, resolved = exact_top_k({m: b["n_pmc"] for m, b in bounds.items()}, resolve, n_select,
                                    batch=RESOLVE_PARALLEL, mapper=pool.map)
    threshold = threshold_used([resolved[m] for m in top])
    for mim in top:                      # counts taken from the log carry no character total: describe again
        if mim not in described:
            d = describe_papers(mim)
            if d["n_fulltext"] != resolved[mim]:
                log.warning("%s: %d readable in full now, %d when first resolved", mim, d["n_fulltext"], resolved[mim])
            described[mim] = d
            store.write_text(json.dumps(described, indent=1))

    rows = []
    for mim in top:
        gold = build_gold(mim)
        rows.append({
            "mim": mim, "stratum": stratum_of(mim), "n_refs": len(gold.cited_pmids),
            "n_hpo": sum(1 for a in gold.hpo_annotations if a.aspect == "P"),
            "n_omim_paragraphs": len(gold.scoped_paragraphs), "n_pmc": bounds[mim]["n_pmc"],
            **{k: described[mim][k] for k in ("n_papers", "n_fulltext", "n_abstract", "n_title", "source_chars")},
            "genes": ",".join(g.symbol for g in gold.genes), "inheritance": ",".join(gold.inheritance),
            "title": gold.title,
        })
    shortlist = [{"mim": m, "n_refs": bounds[m]["n_refs"], "n_pmc": bounds[m]["n_pmc"],
                  "n_fulltext": resolved[m], "source_chars": (described.get(m) or {}).get("source_chars"),
                  "selected": m in top}
                 for m in sorted(resolved, key=lambda m: rank_key(m, resolved[m]))]
    pmc_hist: dict[int, int] = {}
    for b in bounds.values():
        pmc_hist[b["n_pmc"]] = pmc_hist.get(b["n_pmc"], 0) + 1
    result = {
        "rule": (f"eligible phenotype entries (causal gene recorded, >= {MIN_HPO} HPO phenotype annotations, "
                 f">= {MIN_PARAGRAPHS} OMIM paragraph about a cited paper) with {MIN_REFS}-{MAX_REFS} references, "
                 f"in no existing evaluation set; seeded random sample of up to {sample_size}; the {n_select} with "
                 f"the most references readable in full (ties by entry number), requiring >= {MIN_FULLTEXT}"),
        "seed": seed, "order": "candidates sorted by MIM number, then random.Random(seed).shuffle",
        "excluded_evalset_entries": len(exclude), **walk,
        "pmc_bound_histogram": dict(sorted(pmc_hist.items())),
        "n_resolved": len(resolved), "threshold_required": MIN_FULLTEXT, "threshold_met": threshold,
        "shortlist": shortlist, "selected": rows, "sample": sample,
        "seconds": round(time.time() - started, 1), "n_select": n_select, "sample_size": sample_size,
        "deviation": ("design: sample of up to 400, 16 entries; run: sample of up to 200 and 8 entries (smaller "
                      "budget at the user's request)"),
    }
    out = out or root / "evalsets" / f"largeft{n_select}.tsv"
    write_tsv(out, result)
    sel = root / "runs" / "largeft" / "selection.json"
    sel.parent.mkdir(parents=True, exist_ok=True)
    sel.write_text(json.dumps(result, indent=1))
    return result


COLUMNS = ["mim", "stratum", "n_refs", "n_hpo", "n_omim_paragraphs", "n_pmc", "n_papers", "n_fulltext",
           "n_abstract", "n_title", "source_chars", "genes", "inheritance", "title"]


def write_tsv(path: Path, result: dict[str, Any]) -> None:
    lowered = result["threshold_met"] < result["threshold_required"]
    head = [
        f"Experiment A1 (docs/experiments-round2.md): {result['n_select']} new entries for the natural large-entry tier.",
        f"Deviation from the design: {result['deviation']}.",
        f"Rule: {result['rule']}.",
        f"Seed {result['seed']} ({result['order']}); {result['candidates_in_pool']} candidate phenotype entries "
        f"with a gene link and HPO annotations, not in an existing evaluation set ({result['excluded_evalset_entries']} "
        f"excluded); {result['walked']} walked to find {result['eligible']} eligible (the sample).",
        "Full-text count: PubMed records of every cited paper fetched in batches; papers with a PMC id give an upper "
        "bound (n_pmc); entries resolved with the project's access resolution (evalset.describe_papers) in "
        f"descending order of the bound until no unresolved bound could reach the last selected place ({result['n_resolved']} resolved).",
        (f"Requirement of {result['threshold_required']} full texts LOWERED to {result['threshold_met']}: fewer than "
         f"{result['n_select']} entries reach {result['threshold_required']}." if lowered else
         f"Every selected entry has at least {result['threshold_required']} references readable in full "
         f"(lowest: {min(r['n_fulltext'] for r in result['selected'])})."),
    ] + list(result.get("status_lines") or []) + [
        "Shortlist (resolved entries, rank order): mim n_refs n_pmc n_fulltext source_chars selected run "
        "(source_chars '-': count reused from an interrupted pass's log, characters not recomputed; run = generated "
        "and scored in run largeft)",
    ] + [f"  {s['mim']} {s['n_refs']} {s['n_pmc']} {s['n_fulltext']} {'-' if s['source_chars'] is None else s['source_chars']} "
         f"{'yes' if s['selected'] else 'no'} {'yes' if s['mim'] in (result.get('run_entries') or []) else 'no'}"
         for s in result["shortlist"]]
    lines = [f"# {h}" for h in head] + ["\t".join(COLUMNS)]
    lines += ["\t".join(str(r[c]) for c in COLUMNS) for r in result["selected"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_entries(timing_path: Path) -> list[str]:
    """Entries with every strategy's pass finished (an eval file written) in timing.tsv, in first-run order."""
    t = read_timing(timing_path)
    order = []
    for (m, _s) in t:
        if m not in order:
            order.append(m)
    return [m for m in order if all(t.get((m, s), {}).get("ok") for s in STRATEGIES)]


def relabel(root: Path) -> dict[str, Any]:
    """Rewrite evalsets/largeft8.tsv from runs/largeft/selection.json with the run status (no network).

    Adds: which selected entries were run, whether the selection finished (no unresolved bound can
    reach the last place), and for each run entry the log time from which its place was certain.
    """
    d = root / "runs" / "largeft"
    result = _load(d / "selection.json")
    bounds = {m: v["n_pmc"] for m, v in _load(d / "bounds.json")["bounds"].items()}
    events = resolution_events((d / "select.log").read_text().splitlines())
    resolved = {m: n for _, m, n in events}
    resolved.update({s["mim"]: s["n_fulltext"] for s in result["shortlist"]})
    k = result["n_select"]
    state = selection_state(bounds, resolved, k)
    ran = [m for m in run_entries(d / "timing.tsv")]
    started = {}
    for line in (d / "timing.tsv").read_text().splitlines():
        f = line.split("\t")
        if len(f) > 3 and f[0].isdigit() and f[0] not in started:
            started[f[0]] = datetime.fromtimestamp(int(f[2])).strftime("%H:%M:%S")
    attempted = list(started)
    lines = [
        (f"Selection finished: {len(resolved)} of {len(bounds)} sampled entries resolved; the {len(state['unresolved'])} "
         f"unresolved have bounds <= {state['max_unresolved_bound']}, below the last selected count "
         f"({resolved[state['top'][-1]]}), so none can enter." if state["finished"] else
         f"Selection NOT finished: {len(state['could_displace'])} unresolved entries could still displace the last "
         f"place: {' '.join(state['could_displace'])}."),
        f"Top {k} from the resolved counts: {' '.join(state['top'])} "
        f"({'same as' if state['top'] == [r['mim'] for r in result['selected']] else 'DIFFERS FROM'} the rows below).",
    ]
    for m in attempted:
        fc = first_certain(events, bounds, m, k)
        lines.append(f"Run entry {m}: place in the top {k} certain from {fc[1] if fc else 'never'} "
                     f"(log line {fc[0] + 1 if fc else '-'} of the 'resolved' lines), run started {started[m]}"
                     f"{'' if m in ran else ' (not every strategy finished)'}; final rank "
                     f"{state['top'].index(m) + 1 if m in state['top'] else 'not selected'}.")
    lines.append(f"Run in A1 (generated and scored, run largeft), in rule order: "
                 f"{' '.join(m for m in state['top'] if m in attempted) or 'none'}; selected but not run: "
                 f"{' '.join(m for m in state['top'] if m not in attempted) or 'none'} (budget: see results/largeft/large_tier.md).")
    result["status_lines"] = lines
    result["run_entries"] = attempted
    result["selection_finished"] = state["finished"]
    write_tsv(root / "evalsets" / f"largeft{k}.tsv", result)
    (d / "selection.json").write_text(json.dumps(result, indent=1))
    return result


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

DIRECT_TOTAL = 600_000          # synthesize.DIRECT_TOTAL_CHARS (single-prompt budget; also the batch size)
EXTRACT_CAP = 180_000           # extract.MAX_SOURCE_CHARS (per-paper cap of kg and cohort extraction)
NO_DRAFT_NOTE = "no draft text cites this paper"


def direct_cut(n_chars: list[int], batched: bool) -> tuple[int, int]:
    """Papers and characters direct reading's prompt cut: a paper over its share is shortened.

    Single prompt: each paper is cut to max(20,000, 600,000 / n papers) characters
    (synthesize.paper_blocks). Batched: only a paper longer than a whole batch is cut.
    """
    cap = DIRECT_TOTAL if batched else max(20_000, DIRECT_TOTAL // max(1, len(n_chars)))
    over = [n - cap for n in n_chars if n > cap]
    return len(over), sum(over)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_timing(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """runs/largeft/timing.tsv: one row per CLI pass (mim, strategy, start, end, seconds, rc, ok, calls, cached, usd).

    A pair run more than once (a resumed pass) is summed: wall-clock and new calls add up.
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        f = line.split("\t")
        if len(f) < 10 or not f[0].isdigit():
            continue
        row = out.setdefault((f[0], f[1]), {"wall_seconds": 0, "passes": 0, "new_calls": 0, "usd_now": 0.0, "ok": False})
        row["wall_seconds"] += int(f[4])
        row["passes"] += 1
        if f[7] != "NA":
            row["new_calls"] += int(f[7]) - int(f[8])
            row["usd_now"] = round(row["usd_now"] + float(f[9]), 4)
        row["ok"] = row["ok"] or f[6] == "1"
    return out


def _usage_cell(by_strategy: dict[str, Any], strategy: str) -> dict[str, Any]:
    """Calls, list-price cost and summed call seconds per phase (as made fresh, cache hits included)."""
    s = by_strategy.get(strategy) or {}
    cell: dict[str, Any] = {}
    for phase in ("generate", "audit", "score"):
        stages = {k: v for k, v in s.items() if k.startswith(phase + "/")}
        cell[phase] = {"calls": sum(v["calls"] for v in stages.values()),
                       "usd": _r(sum(v.get("full_list_price_usd", 0) for v in stages.values()), 2),
                       "call_seconds": round(sum(v.get("full_seconds", 0) for v in stages.values()))}
        if phase == "score":
            cell[phase]["judge_calls"] = sum(v["calls"] for k, v in stages.items() if k.endswith("/judge"))
    return cell


def marking_calls(frozen: dict[str, Any]) -> int:
    """Calls the frozen-list marking needed: one per in-scope paragraph with facts that the draft wrote about."""
    n = 0
    for para in frozen.get("paragraphs") or []:
        facts = para.get("facts") or []
        if not facts or all(f.get("note") == NO_DRAFT_NOTE for f in facts):
            continue
        n += int(para.get("mark_attempts", 1))
    return n


def entry_record(run_dir: Path, mim: str, tier: str, timing: dict) -> dict[str, Any]:
    from .compare import completion_status, prepare_eval

    d = run_dir / mim
    papers = _load(d / "papers.json") if (d / "papers.json").exists() else []
    gold = _load(d / "gold.json")
    cited = gold.get("cited_pmids") or []
    n_chars = [int(p.get("n_chars") or 0) for p in papers]
    levels = [p.get("content_level") for p in papers]
    status = completion_status(run_dir, [mim])
    rec: dict[str, Any] = {
        "mim": mim, "tier": tier, "title": gold.get("title"),
        "n_refs": len(cited), "n_papers": len(papers),
        "n_fulltext": levels.count("fulltext"), "n_abstract": levels.count("abstract"), "n_title": levels.count("title"),
        "supplied_chars": sum(n_chars), "largest_paper_chars": max(n_chars, default=0),
        "extract_cut_papers": sum(1 for n in n_chars if n > EXTRACT_CAP),
        "strategies": {},
    }
    usage = _load(d / "usage.json").get("by_strategy", {}) if (d / "usage.json").exists() else {}
    if "retrieval" in usage:
        rec["fact_split_calls_cached_or_fresh"] = (usage["retrieval"].get("total") or {}).get("calls")
    facts_set = False
    for s in STRATEGIES:
        st = (status.get(s) or {}).get(mim, {"status": "no_draft", "reason": "not run"})
        cell: dict[str, Any] = {"status": st["status"]}
        if st.get("reason"):
            cell["reason"] = str(st["reason"])[:200]
        if st.get("papers_failed"):
            cell["papers_failed"] = len(st["papers_failed"])
        ep, en = d / f"eval.{s}.json", d / f"entry.{s}.json"
        meta = (_load(en).get("meta") or {}) if en.exists() else {}
        if s == "direct" and meta:
            rec["direct_prompts"] = direct_prompts(meta)
            if rec["direct_prompts"] is None:     # writer stopped before the record was made: the plan
                k = -(-sum(n_chars) // DIRECT_TOTAL)
                rec["direct_prompts"] = k + (1 if k > 1 else 0)
                rec["direct_prompts_planned_only"] = True
            batched = bool((meta.get("direct_batching") or {}).get("used", sum(n_chars) > DIRECT_TOTAL))
            rec["direct_batched"] = batched
            rec["direct_cut_papers"], rec["direct_cut_chars"] = direct_cut(n_chars, batched)
            rec["direct_truncated_recorded"] = len(meta.get("truncated_papers") or [])
            if batched:
                rec["direct_merge"] = {k: v for k, v in ((meta.get("direct_batching") or {}).get("merge") or {}).items()
                                       if k in ("merge_failed", "partial_paragraphs", "merged_paragraphs",
                                                "pmids_lost_in_merge")}
                if "pmids_lost_in_merge" in rec["direct_merge"]:
                    rec["direct_merge"]["pmids_lost_in_merge"] = len(rec["direct_merge"]["pmids_lost_in_merge"])
        if s == "agent" and meta.get("agent"):
            a = meta["agent"]
            cell["papers_read"] = len(a.get("papers_read") or [])
            cell["papers_not_read"] = len(a.get("papers_not_read") or [])
        if ep.exists():
            ev = prepare_eval(_load(ep))
            frozen = ev.get("gold_text_frozen") or {}
            if frozen.get("n_judged") and not ev.get("stopped"):
                g = ev["gold_text"]
                cell.update(coverage=g.get("coverage"), n_judged=g.get("n_judged"), unjudged=frozen.get("unjudged"),
                            marking_calls=marking_calls(frozen))
                if not facts_set:
                    paras = frozen.get("paragraphs") or []
                    rec["curator_paragraphs"] = frozen.get("n_paragraphs")
                    rec["curator_paragraphs_out_of_scope"] = frozen.get("n_out_of_scope")
                    rec["fixed_facts"] = frozen.get("n_facts")
                    rec["refs_scored"], rec["refs_scored_share"] = reference_share(
                        [p.get("pmids") or [] for p in paras], cited)
                    facts_set = True
        cell["usage"] = _usage_cell(usage, s)
        t = timing.get((mim, s))
        if t:
            cell["wall_seconds"] = t["wall_seconds"]
            cell["new_calls"] = t["new_calls"]
        rec["strategies"][s] = cell
    return rec


def compare_block(records: list[dict[str, Any]], allow_incomplete: bool = False) -> dict[str, Any]:
    """Means and paired differences from direct reading on entries every strategy completed.

    With `allow_incomplete`, on entries where every strategy wrote a scored draft, papers whose extraction
    was stopped included (a secondary view, not the design's comparison set).
    """
    ok = ("complete", "incomplete") if allow_incomplete else ("complete",)
    done = [r for r in records if all(r["strategies"][s]["status"] in ok
                                      and r["strategies"][s].get("coverage") is not None for s in STRATEGIES)]
    out: dict[str, Any] = {"n_entries": len(done), "entries": [r["mim"] for r in done], "strategies": {}}
    for s in STRATEGIES:
        vals = [r["strategies"][s]["coverage"] for r in done]
        cell: dict[str, Any] = {"mean": _r(statistics.fmean(vals)) if vals else None}
        if s != BASELINE:
            cell["vs_direct"] = paired({r["mim"]: (r["strategies"][s]["coverage"], r["strategies"][BASELINE]["coverage"])
                                        for r in done})
        out["strategies"][s] = cell
    return out


def pairwise_with_direct(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Each strategy against direct reading on the entries where both wrote a scored draft (stopped papers
    included): a secondary view that keeps an entry when another strategy was stopped."""
    out: dict[str, Any] = {}
    for s in STRATEGIES:
        if s == BASELINE:
            continue
        both = {r["mim"]: (r["strategies"][s]["coverage"], r["strategies"][BASELINE]["coverage"]) for r in records
                if all(r["strategies"][t]["status"] != "no_draft" and r["strategies"][t].get("coverage") is not None
                       for t in (s, BASELINE))}
        out[s] = {"entries": sorted(both, key=int), **paired(both)}
    return out


def completion_table(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for s in STRATEGIES:
        c = {"complete": 0, "incomplete": 0, "no_draft": 0}
        for r in records:
            c[r["strategies"][s]["status"]] += 1
        out[s] = c
    return out


def analyze(root: Path, old_run: Path, new_run: Path, old_entries: Path, new_entries: Path,
            timing_path: Path, out_dir: Path, cap: int = 1500, extra_calls: int = 0,
            deviations: list[str] | None = None) -> dict[str, Any]:
    timing = read_timing(timing_path)
    old = [entry_record(old_run, m, "large12 (audit + repair)", {}) for m in
           mims_in(old_entries.read_text().splitlines()) if (old_run / m / "gold.json").exists()]
    new_mims = mims_in(new_entries.read_text().splitlines())
    finished = set(run_entries(timing_path))      # every strategy's pass done; an entry still running is left out
    new = [entry_record(new_run, m, "largeft (no audit)", timing) for m in new_mims
           if (new_run / m / "gold.json").exists() and m in finished]
    combined = old + new
    groups: dict[str, list[dict[str, Any]]] = {"combined": combined, "new": new, "old": old}
    compared = [r for r in combined if r["mim"] in compare_block(combined)["entries"]]
    med, lower, upper = median_split({r["mim"]: r["supplied_chars"] for r in compared})
    groups["combined_lower_half_chars"] = [r for r in compared if r["mim"] in lower]
    groups["combined_upper_half_chars"] = [r for r in compared if r["mim"] in upper]
    new_compared = [r for r in new if r["mim"] in compare_block(new)["entries"]]
    med_new, lower_new, upper_new = median_split({r["mim"]: r["supplied_chars"] for r in new_compared})
    groups["new_lower_half_chars"] = [r for r in new_compared if r["mim"] in lower_new]
    groups["new_upper_half_chars"] = [r for r in new_compared if r["mim"] in upper_new]
    # Secondary view (not in the design): every strategy wrote a scored draft, stopped papers included.
    secondary: dict[str, list[dict[str, Any]]] = {"combined": combined, "new": new}
    drafted = [r for r in combined if r["mim"] in compare_block(combined, True)["entries"]]
    med_d, _, upper_d = median_split({r["mim"]: r["supplied_chars"] for r in drafted})
    secondary["combined_upper_half_chars"] = [r for r in drafted if r["mim"] in upper_d]

    stops: dict[str, Any] = {}
    for s in STRATEGIES:
        cells = [r["strategies"][s] for r in new]
        stops[s] = {"writer_stopped": sum(1 for c in cells if c["status"] == "no_draft" and "safety" in c.get("reason", "")),
                    "entries_with_stopped_papers": sum(1 for c in cells if c.get("papers_failed")),
                    "papers_stopped": sum(c.get("papers_failed", 0) for c in cells)}

    cost: dict[str, Any] = {}
    for s in STRATEGIES:
        rows = [r["strategies"][s] for r in new]
        cost[s] = {
            "entries": len(rows),
            "generate_calls": sum(c["usage"]["generate"]["calls"] for c in rows),
            "score_calls": sum(c["usage"]["score"]["calls"] for c in rows),
            "generate_usd": _r(sum(c["usage"]["generate"]["usd"] or 0 for c in rows), 2),
            "score_usd": _r(sum(c["usage"]["score"]["usd"] or 0 for c in rows), 2),
            "wall_seconds": sum(c.get("wall_seconds", 0) for c in rows),
            "new_calls_this_experiment": sum(c.get("new_calls", 0) for c in rows),
        }
    result = {
        "experiment": "A1 natural large-entry tier (docs/experiments-round2.md)",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "measure": ("OMIM facts conveyed: share of the fixed (frozen) fact list of the entry's in-scope curator "
                    "paragraphs that the draft text citing the paper conveys (present = 1, partial = 0.5), mean "
                    "over entries"),
        "note_on_tiers": ("The 12 large12 entries were scored after the audit's repair round; the new entries were "
                          "generated and scored without audit or repair. The combined tier mixes the two."),
        "completion": {name: completion_table(g) for name, g in (("combined", combined), ("new", new), ("old", old))},
        "comparison": {name: compare_block(g) for name, g in groups.items()},
        "median_supplied_chars": {"combined_compared": med, "new_compared": med_new, "combined_drafted": med_d},
        "secondary_all_drafted": {name: compare_block(g, True) for name, g in secondary.items()},
        "secondary_pairwise": {name: pairwise_with_direct(g) for name, g in secondary.items()
                               if name != "combined_upper_half_chars"},
        "stops_new_entries": stops,
        "cost_new_entries": cost,
        "total_new_calls_this_experiment": sum(t["new_calls"] for t in timing.values()) + extra_calls,
        "budget": {"cap": cap, "counted_in_timing": sum(t["new_calls"] for t in timing.values()),
                   "uncounted_interrupted_passes": extra_calls},
        "entries": combined,
        "deviations": deviations or [],
    }
    by_avail = new_run / "strategies.by_availability.json"
    if by_avail.exists():
        result["by_availability_new_run"] = _load(by_avail)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "large_tier.json").write_text(json.dumps(result, indent=1))
    md = markdown(result)
    (out_dir / "large_tier.md").write_text(md)
    result["markdown_path"] = str(out_dir / "large_tier.md")
    return result


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.1f}"


def _pp(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:+.1f}"


NAMES = {"combined": "All compared entries (old + new)", "new": "New entries alone (no audit)",
         "old": "large12 alone (after repair)",
         "combined_lower_half_chars": "All compared, supplied characters at or below the median",
         "combined_upper_half_chars": "All compared, supplied characters above the median",
         "new_lower_half_chars": "New alone, at or below their median",
         "new_upper_half_chars": "New alone, above their median"}


def _comparison_rows(blocks: dict[str, Any]) -> list[str]:
    L = ["| Group | n | Strategy | mean % | vs direct (pp) | 95% CI | better / worse / tied | sign p |",
         "|---|---|---|---|---|---|---|---|"]
    for g, block in blocks.items():
        for s in STRATEGIES:
            c = block["strategies"][s]
            v = c.get("vs_direct")
            if v is None or not block["n_entries"]:
                L.append(f"| {NAMES.get(g, g)} | {block['n_entries']} | {LABELS[s]} | {_pct(c['mean'])} | – | – | – | – |")
            else:
                ci = f"[{_pp(v['ci95'][0])}, {_pp(v['ci95'][1])}]" if v["ci95"] else "–"
                p = "–" if v["sign_p"] is None else f"{v['sign_p']:.3f}"
                L.append(f"| {NAMES.get(g, g)} | {block['n_entries']} | {LABELS[s]} | {_pct(c['mean'])} | "
                         f"{_pp(v['mean_diff'])} | {ci} | {v['better']} / {v['worse']} / {v['tied']} | {p} |")
    return L


def markdown(res: dict[str, Any]) -> str:
    new = [r for r in res["entries"] if r["tier"].startswith("largeft")]
    L = ["# Experiment A1: natural large-entry tier", "",
         f"Generated {res['generated']} by `python -m aiomim.largetier analyze`. **{res['note_on_tiers']}**", "",
         f"New entries run: {len(new)} ({', '.join(r['mim'] for r in new)}), the first in rule order of "
         "`evalsets/largeft8.tsv`; the header of that file gives the rule, seed, candidates and shortlist.", "",
         f"Measure: {res['measure']}. Paired differences are strategy minus direct reading, in percentage points, "
         "with a percentile bootstrap 95% interval (10,000 resamples, seed 7; none below 3 entries) and an exact "
         "two-sided sign test on better/worse (ties dropped). No correction for multiple comparisons.", ""]
    if res.get("deviations"):
        L += ["## Deviations from the design", ""] + [f"- {d}" for d in res["deviations"]] + [""]
    L += ["## Completion", "",
          "complete = draft written and every per-paper call succeeded; incomplete = draft written but a per-paper "
          "extraction call was stopped by the safety filter and the paper was dropped (evidence graph, case table); "
          "no draft = the writer (or a direct-reading batch) was stopped, or the strategy did not run.", "",
          "| Group | Strategy | complete | incomplete | no draft |", "|---|---|---|---|---|"]
    for g, table in res["completion"].items():
        for s, c in table.items():
            L.append(f"| {g} | {LABELS[s]} | {c['complete']} | {c['incomplete']} | {c['no_draft']} |")
    L += ["", "Safety-filter stops on the new entries (recorded, never retried):", "",
          "| Strategy | writer stopped (no draft) | entries with stopped papers | papers stopped |", "|---|---|---|---|"]
    for s, c in res["stops_new_entries"].items():
        L.append(f"| {LABELS[s]} | {c['writer_stopped']} | {c['entries_with_stopped_papers']} | {c['papers_stopped']} |")
    L += ["", "## Facts conveyed on entries every strategy completed (the design's comparison)", ""]
    L += _comparison_rows(res["comparison"])
    m = res["median_supplied_chars"]
    if m.get("combined_compared"):
        L += ["", f"Median supplied characters of the compared entries: {m['combined_compared']:,.0f} (all)"
              + (f", {m['new_compared']:,.0f} (new)." if m.get("new_compared") else "; no new entry is compared.")]
    L += ["", "## Secondary view: every strategy wrote a scored draft (stopped papers included)", "",
          "Not in the design. Incomplete drafts were written without the papers whose extraction the safety filter "
          "stopped, so a strategy's score here mixes method and stops; read it as a description, not a test.", ""]
    L += _comparison_rows(res["secondary_all_drafted"])
    if m.get("combined_drafted"):
        L += ["", f"Median supplied characters of these entries: {m['combined_drafted']:,.0f}."]
    L += ["", "Pairwise with direct reading, on entries where both wrote a scored draft (stopped papers included):", "",
          "| Group | Strategy | n | strategy % | direct % | vs direct (pp) | 95% CI | better / worse / tied | sign p | entries |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for g, block in res["secondary_pairwise"].items():
        for s, v in block.items():
            ci = f"[{_pp(v['ci95'][0])}, {_pp(v['ci95'][1])}]" if v["ci95"] else "–"
            p = "–" if v["sign_p"] is None else f"{v['sign_p']:.3f}"
            new_ids = {r["mim"] for r in new}
            ids = ", ".join(m + ("*" if m in new_ids else "") for m in v["entries"])
            L.append(f"| {NAMES.get(g, g)} | {LABELS[s]} | {v['n']} | {_pct(v['mean_strategy'])} | {_pct(v['mean_baseline'])} | "
                     f"{_pp(v['mean_diff'])} | {ci} | {v['better']} / {v['worse']} / {v['tied']} | {p} | {ids} |")
    L += ["", "(* new entry)"]
    L += ["", "## Per entry", "",
          "refs = references; full = readable in full; chars = characters supplied (title, abstract, full text); "
          "prompts = writer prompts of direct reading (batches + merge; * planned, the writer was stopped); "
          "cut = papers/characters direct reading's prompt shortened; ext cut = papers over the 180,000-character "
          "extraction cap; paras/facts = in-scope curator paragraphs and fixed facts; refs scored = references the "
          "scored paragraphs are about (share of all references). Coverage % per strategy; (i) incomplete, with "
          "papers stopped; (–) no draft. agent unread = papers the agentic curator did not open.", "",
          "| Entry | tier | refs | full | chars | prompts | cut | ext cut | paras | facts | refs scored | direct | agent | kg | cohort | agent unread |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["entries"]:
        cells = []
        for s in STRATEGIES:
            c = r["strategies"][s]
            cells.append("–" if c["status"] == "no_draft" else
                         _pct(c.get("coverage")) + (f" (i, {c.get('papers_failed', '?')})" if c["status"] == "incomplete" else ""))
        share = r.get("refs_scored_share")
        prompts = f"{r.get('direct_prompts', '–')}{'*' if r.get('direct_prompts_planned_only') else ''}"
        L.append(f"| {r['mim']} | {'old' if r['tier'].startswith('large12') else 'new'} | {r['n_refs']} | "
                 f"{r['n_fulltext']} | {r['supplied_chars']:,} | {prompts} | "
                 f"{r.get('direct_cut_papers', '–')}/{r.get('direct_cut_chars', 0):,} | {r.get('extract_cut_papers', 0)} | "
                 f"{r.get('curator_paragraphs', '–')} | {r.get('fixed_facts', '–')} | {r.get('refs_scored', '–')} "
                 f"({_pct(share)}%) | " + " | ".join(cells) + f" | {r['strategies']['agent'].get('papers_not_read', '–')} |")
    caps = [r for r in res["entries"] if r.get("direct_cut_papers") or r.get("extract_cut_papers")]
    L += ["", "## Caps that truncated the input", "",
          "Direct reading: one prompt holds 600,000 characters; above that the papers are split into batches of that "
          "size and the partial drafts merged, and only a paper longer than a whole batch is cut; in one prompt each "
          "paper is cut to max(20,000, 600,000 / papers) characters. Evidence graph and case table: each paper's "
          "extraction reads at most 180,000 characters.", ""]
    L += ([f"- {r['mim']} ({'old' if r['tier'].startswith('large12') else 'new'}): direct reading cut "
           f"{r.get('direct_cut_papers', 0)} papers by {r.get('direct_cut_chars', 0):,} characters"
           f"{' (as planned: the writer was stopped, so no draft was written from it)' if r.get('direct_prompts_planned_only') else ''}; extraction cut "
           f"{r.get('extract_cut_papers', 0)} papers" for r in caps] or ["- None."])
    L += ["", "No cap truncated a new entry's input: its papers are at most "
          f"{max((r['largest_paper_chars'] for r in new), default=0):,} characters, and direct reading was batched." if new and not
          any(r.get('direct_cut_papers') or r.get('extract_cut_papers') for r in new) else ""]
    L += ["", "## Calls, cost and time (new entries)", "",
          "Calls and list-price cost as made fresh (generation; scoring = adaptive judge, variant match and "
          "fixed-fact marking); wall-clock = the CLI pass for that entry and strategy (generation + scoring), "
          "summed over resumed passes; new calls = calls not answered from the cache in this experiment's passes.", "",
          "| Strategy | entries | generate calls | score calls | generate $ | score $ | wall-clock h | new calls here |",
          "|---|---|---|---|---|---|---|---|"]
    for s, c in res["cost_new_entries"].items():
        L.append(f"| {LABELS[s]} | {c['entries']} | {c['generate_calls']} | {c['score_calls']} | {c['generate_usd']} | "
                 f"{c['score_usd']} | {c['wall_seconds'] / 3600:.2f} | {c['new_calls_this_experiment']} |")
    b = res["budget"]
    L += ["", f"New model calls made by this experiment: {res['total_new_calls_this_experiment']} of the {b['cap']} cap "
          f"({b['counted_in_timing']} counted per pass in runs/largeft/timing.tsv, plus {b['uncounted_interrupted_passes']} "
          "made by a pass the machine restart interrupted).", "",
          "| Entry | Strategy | status | gen calls | gen $ | score calls | marking calls | wall s | new calls |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in new:
        for s in STRATEGIES:
            c = r["strategies"][s]
            u = c["usage"]
            L.append(f"| {r['mim']} | {s} | {c['status']} | {u['generate']['calls']} | {u['generate']['usd']} | "
                     f"{u['score']['calls']} | {c.get('marking_calls', '–')} | {c.get('wall_seconds', '–')} | {c.get('new_calls', '–')} |")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


DEVIATIONS = [
    "Sample of up to 200 eligible entries (design: 400) and 8 new entries selected (design: 16; reduced sizes: 8).",
    "Only the first {n_run} selected entries in rule order were run (reduced sizes: 8, floor 6): the 1,500-call cap "
    "allowed no more (an entry cost about 250-330 new calls, most of it per-paper extraction for the evidence graph "
    "and the case table).",
    "The split on facts the supplied text states was not made (reduced sizes: only if it fits).",
    "The selection was resolved in three passes across machine restarts; counts resolved earlier were reused from "
    "its log. The first three entries were run before it finished, each only once its place in the top 8 was "
    "certain from the bounds (times in the header of evalsets/largeft8.tsv).",
]


def export_checked(root: Path, run: str = "largeft", out: str = "results/largeft") -> dict[str, Any]:
    """Export the run with the project's export, then check what it wrote for OMIM-derived wording.

    No gold file may be written. Every exported text file is searched for 60-character windows of the
    entry's gold-fact paragraph texts and fact sentences (40+ characters); windows that also occur in the
    entry's supplied papers (curators often quote an abstract) are not counted. What remains is model output
    (drafts, extractions) that matches the curators' wording, reported per file.
    """
    from .export import export_run

    run_dir, out_dir = root / "runs" / run, root / out
    n = export_run(run_dir, out_dir)
    report: dict[str, Any] = {"entries_exported": n, "windows_outside_supplied_text": {}, "examples": {}}
    for entry in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        gf = run_dir / entry.name / "gold_facts.json"
        if not gf.exists():
            continue
        gold: list[str] = []
        for para in _load(gf).get("paragraphs") or []:
            gold.append(para.get("text") or "")
            gold += [f.get("fact") or "" for f in para.get("facts") or []]
        papers = run_dir / entry.name / "papers.json"
        source = " ".join(" ".join(str(p.get(k) or "") for k in ("title", "abstract", "fulltext", "text"))
                          for p in (_load(papers) if papers.exists() else []))
        source = " ".join(source.split())
        for path in sorted(entry.rglob("*")):
            if path.is_file() and path.suffix in (".json", ".md", ".tsv") and path.name != "papers.json":
                hits = [h for h in leaked(gold, path.read_text(encoding="utf-8", errors="replace")) if h not in source]
                if hits:
                    key = str(path.relative_to(root))
                    report["windows_outside_supplied_text"][key] = len(hits)
                    report["examples"][key] = hits[0][:40] + "..."
    report["forbidden_files"] = [str(p.relative_to(root)) for p in out_dir.rglob("*")
                                 if p.name in ("gold.json", "gold_facts.json")]
    top = [p for p in out_dir.glob("*") if p.is_file()]
    report["top_level_files"] = sorted(p.name for p in top)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m aiomim.largetier", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select", help="draw the new entries and write evalsets/largeft8.tsv")
    s.add_argument("--seed", type=int, default=SELECT_SEED)
    s.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    s.add_argument("-n", type=int, default=N_SELECT)
    sub.add_parser("relabel", help="rewrite evalsets/largeft8.tsv's header with the run status (no network)")
    e = sub.add_parser("export", help="export runs/largeft to results/largeft and check it for OMIM wording")
    e.add_argument("--run", default="largeft")
    e.add_argument("--out", default="results/largeft")
    a = sub.add_parser("analyze", help="combined analysis -> results/largeft/large_tier.{json,md}")
    a.add_argument("--old-run", default="large12")
    a.add_argument("--new-run", default="largeft")
    a.add_argument("--new-entries", default="evalsets/largeft8.tsv")
    a.add_argument("--old-entries", default="evalsets/large12.tsv")
    a.add_argument("--timing", default="runs/largeft/timing.tsv")
    a.add_argument("--out", default="results/largeft")
    a.add_argument("--cap", type=int, default=1500)
    a.add_argument("--extra-calls", type=int, default=0,
                   help="new calls made by passes a restart interrupted (not in timing.tsv)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    root = Path.cwd()
    if args.cmd == "select":
        result = select(root, seed=args.seed, sample_size=args.sample_size, n_select=args.n)
        for r in result["selected"]:
            print(f"{r['mim']}\trefs={r['n_refs']}\tpmc={r['n_pmc']}\tfulltext={r['n_fulltext']}\t"
                  f"chars={r['source_chars']}\t{r['title'][:60]}")
        print(f"threshold met: {result['threshold_met']}; resolved {result['n_resolved']}; "
              f"{result['seconds']} s")
    elif args.cmd == "relabel":
        result = relabel(root)
        print("\n".join(result["status_lines"]))
    elif args.cmd == "export":
        print(json.dumps(export_checked(root, args.run, args.out), indent=1))
    else:
        timing = root / args.timing
        n_run = len({m for (m, _s) in read_timing(timing)})
        result = analyze(root, Path(args.old_run if "/" in args.old_run else f"runs/{args.old_run}"),
                         Path(args.new_run if "/" in args.new_run else f"runs/{args.new_run}"),
                         root / args.old_entries, root / args.new_entries, timing, root / args.out,
                         cap=args.cap, extra_calls=args.extra_calls,
                         deviations=[d.format(n_run=n_run) for d in DEVIATIONS])
        print(result["markdown_path"])


if __name__ == "__main__":
    main()
