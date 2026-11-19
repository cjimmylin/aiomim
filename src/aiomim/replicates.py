"""Run-to-run variation: the same strategies on the same entries, run several times.

Every model reply is cached, so a second run of an entry normally replays the
first. A replicate run sets AIOMIM_REPLICATE to a new salt, which is mixed into
every cache key (see `aiomim.llm.cache_key`): all calls are made afresh. That
re-runs generation, the claim audit and repair, and the LLM-judged parts of the
scoring (OMIM fact coverage, variant matching) together, so the variation
measured here is that of the whole measurement, not of the writer alone. The
gold standard itself is built from public records and is the same in every
replicate.

`select_entries` draws the replicate set; `analyse` takes the run folders of the
replicates and reports, per strategy and measure, how much of the variance lies
between runs of the same entry and how much between entries, and whether the
paired difference between two strategies holds in each replicate.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from .evalset import STRATA, stratum_of

# (key, label, path into eval.<strategy>.json, higher_is_better)
MEASURES: list[tuple[str, str, str, bool]] = [
    ("gold_fact_coverage", "OMIM facts conveyed", "gold_text.coverage", True),
    ("claim_supported_rate", "Claims supported", "faithfulness.supported_rate", True),
    ("claim_error_rate_before_repair", "Claims unsupported or contradicted, before repair",
     "faithfulness.before_repair.error_rate", False),
    ("hpo_exact_f1", "Clinical synopsis, exact HPO F1", "synopsis.exact.f1", True),
    ("variant_recall", "OMIM allelic variants recovered", "variants.recall", True),
    ("gene_f1", "Causal gene F1", "genes.f1", True),
    ("inheritance_match", "Inheritance matches OMIM", "inheritance.match", True),
]

NOTE = ("A replicate salts every model call, so it re-runs generation, the claim audit and repair, and the "
        "model-judged scoring (OMIM fact coverage, variant matching) together: the variation below is that of "
        "the whole measurement, not of the writer alone. The gold standard (public OMIM-derived records) is "
        "the same in every replicate; the facts the judge splits each OMIM paragraph into are not.")


# --------------------------------------------------------------------------- #
# Selecting the replicate set
# --------------------------------------------------------------------------- #


def completed_in_full(entry_dir: Path, strategies: tuple[str, ...] = ("direct", "kg")) -> bool:
    """Every strategy wrote and was scored (no "stopped"), and the graph's extraction lost no paper."""
    for s in strategies:
        path = entry_dir / f"eval.{s}.json"
        if not path.exists() or json.loads(path.read_text(encoding="utf-8")).get("stopped"):
            return False
    if "kg" in strategies:
        path = entry_dir / "entry.kg.json"
        if not path.exists():
            return False
        meta = json.loads(path.read_text(encoding="utf-8")).get("meta", {})
        if (meta.get("extraction") or {}).get("papers_failed"):
            return False
    return True


def select_entries(source_tsv: Path, run_dir: Path, per_stratum: int = 6, seed: int = 30) -> list[str]:
    """Header and rows of `source_tsv` for `per_stratum` entries per creation-era band.

    Only entries that direct reading and the evidence graph completed in full in
    `run_dir` are eligible; within a band they are drawn at random with `seed`.
    """
    lines = source_tsv.read_text(encoding="utf-8").splitlines()
    header, rows = lines[0], [line for line in lines[1:] if line.strip()]
    by_band: dict[str, list[str]] = {label: [] for label, _ in STRATA}
    for line in rows:
        mim = line.split("\t")[0]
        if completed_in_full(run_dir / mim):
            by_band.setdefault(stratum_of(mim), []).append(line)
    rng = random.Random(seed)
    out = [header]
    for label, _ in STRATA:
        pool = sorted(by_band.get(label, []))
        if len(pool) < per_stratum:
            raise ValueError(f"band {label} has only {len(pool)} eligible entries")
        out += sorted(rng.sample(pool, per_stratum), key=lambda l: l.split("\t")[0])
    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def _get(node: Any, path: str) -> float | None:
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, bool):
        return float(node)
    return float(node) if isinstance(node, (int, float)) else None


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _var(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _bootstrap_ci(diffs: list[float], seed: int = 7, n: int = 10_000) -> list[float] | None:
    if len(diffs) < 5:
        return None
    rng = random.Random(seed)
    k = len(diffs)
    means = sorted(sum(rng.choices(diffs, k=k)) / k for _ in range(n))
    return [means[int(0.025 * n)], means[int(0.975 * n) - 1]]


def variance_components(matrix: list[list[float]]) -> dict[str, Any]:
    """One-way random-effects decomposition of an entries x replicates table (balanced).

    Within-entry variance is the mean of each entry's variance across replicates
    (MSW). The between-entry variance is (MSB - MSW) / k, where MSB is k times the
    variance of the entry means: the spread of true entry scores, net of run noise.
    """
    n = len(matrix)
    k = len(matrix[0]) if matrix else 0
    if n < 2 or k < 2:
        return {"n_entries": n, "n_replicates": k}
    msw = sum(_var(row) for row in matrix) / n
    entry_means = [sum(row) / k for row in matrix]
    msb = k * _var(entry_means)
    between = max(0.0, (msb - msw) / k)
    total = msw + between
    return {
        "n_entries": n, "n_replicates": k,
        "within_sd": math.sqrt(msw), "between_sd": math.sqrt(between),
        "within_share": (msw / total) if total > 0 else None,
        "sd_of_entry_means": math.sqrt(_var(entry_means)),
    }


def load_run(run_dir: Path) -> dict[str, dict[str, dict]]:
    """strategy -> {mim -> evaluation}, written drafts only; stopped ones under the key "_stopped"."""
    out: dict[str, dict[str, dict]] = {}
    for path in sorted(run_dir.glob("*/eval.*.json")):
        strategy = path.name.split(".")[1]
        evaluation = json.loads(path.read_text(encoding="utf-8"))
        bucket = "_stopped" if evaluation.get("stopped") else strategy
        out.setdefault(bucket, {})[path.parent.name if bucket != "_stopped" else f"{path.parent.name}.{strategy}"] = evaluation
    return out


def usage_of_run(run_dir: Path) -> dict[str, float]:
    """What a pass spent: calls made afresh, calls read from cache, tokens and list price (this pass only)."""
    total: dict[str, float] = {}
    for path in run_dir.glob("*/usage.json"):
        for key, value in json.loads(path.read_text(encoding="utf-8")).get("total", {}).items():
            total[key] = total.get(key, 0) + value
    full = 0.0
    for path in run_dir.glob("*/usage.json"):
        for summary in json.loads(path.read_text(encoding="utf-8")).get("by_strategy", {}).values():
            full += summary.get("total", {}).get("full_list_price_usd", 0.0)
    calls, cached = total.get("calls", 0), total.get("cached", 0)
    return {"calls": int(calls), "from_cache": int(cached), "fresh_calls": int(calls - cached),
            "input_tokens": int(total.get("input_tokens", 0)), "output_tokens": int(total.get("output_tokens", 0)),
            "list_price_usd": round(total.get("list_price_usd", 0.0), 2),
            # What the calls cost when they were made, whichever pass made them.
            "full_list_price_usd": round(full, 2)}


def analyse(run_dirs: list[Path], strategies: tuple[str, ...] = ("direct", "kg"),
            baseline: str = "direct", other: str = "kg", n_target: int = 97) -> dict[str, Any]:
    runs = [load_run(d) for d in run_dirs]
    k = len(runs)
    result: dict[str, Any] = {
        "runs": [d.name for d in run_dirs], "note": NOTE, "n_target": n_target,
        "usage": {d.name: usage_of_run(d) for d in run_dirs},
        "stopped": {d.name: sorted(r.get("_stopped", {})) for d, r in zip(run_dirs, runs)},
        "entries": {}, "strategies": {}, "paired": {},
    }
    for s in strategies:
        common = sorted(set.intersection(*(set(r.get(s, {})) for r in runs))) if runs else []
        result["entries"][s] = len(common)
        rows = {}
        for key, label, path, higher in MEASURES:
            matrix = []
            for mim in common:
                vals = [_get(r[s][mim], path) for r in runs]
                if all(v is not None for v in vals):
                    matrix.append(vals)
            comp = variance_components(matrix)
            rep_means = [sum(row[j] for row in matrix) / len(matrix) for j in range(k)] if matrix else []
            rows[key] = {
                "label": label, "higher_is_better": higher, **comp,
                "replicate_means": rep_means,
                "mean_range": (max(rep_means) - min(rep_means)) if rep_means else None,
                "mean_sd": math.sqrt(_var(rep_means)) if len(rep_means) > 1 else None,
            }
        result["strategies"][s] = rows

    if baseline in strategies and other in strategies:
        both = sorted(set.intersection(*(set(r.get(baseline, {})) & set(r.get(other, {})) for r in runs)))
        result["paired_entries"] = len(both)
        for key, label, path, higher in MEASURES:
            per_rep = []
            d_matrix = []
            for mim in both:
                row = []
                for r in runs:
                    a, b = _get(r[other][mim], path), _get(r[baseline][mim], path)
                    row.append(None if a is None or b is None else a - b)
                if all(x is not None for x in row):
                    d_matrix.append(row)
            for j in range(k):
                diffs = [row[j] for row in d_matrix]
                per_rep.append({"run": run_dirs[j].name, "n": len(diffs), "difference": _mean(diffs),
                                "ci95": _bootstrap_ci(diffs)})
            comp = variance_components(d_matrix)
            within_sd = comp.get("within_sd")
            # A difference between two strategies' means over n entries, each run once, carries
            # replicate noise with standard error within_sd / sqrt(n); 1.96 times that is the
            # smallest difference run-to-run noise alone would produce less than 5% of the time.
            threshold = 1.96 * within_sd / math.sqrt(n_target) if within_sd is not None else None
            total_var = _var([x for row in d_matrix for x in row]) if d_matrix else None
            result["paired"][key] = {
                "label": label, "higher_is_better": higher, "replicates": per_rep,
                "difference_within_sd": within_sd, "difference_between_sd": comp.get("between_sd"),
                "difference_within_share": comp.get("within_share"),
                "difference_total_sd": math.sqrt(total_var) if total_var else None,
                "noise_threshold_at_n": threshold,
                "noise_threshold_at_30": 1.96 * within_sd / math.sqrt(len(d_matrix)) if within_sd and d_matrix else None,
            }
    return result


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def _pct(x: float | None, digits: int = 1) -> str:
    return "–" if x is None else f"{100 * x:.{digits}f}"


def replicates_markdown(r: dict[str, Any]) -> str:
    names = {"direct": "Direct reading", "kg": "Evidence graph"}
    lines = [f"# Run-to-run variation: {', '.join(r['runs'])}", "", r["note"], ""]
    lines += ["Values are in percentage points (a score of 0.53 is 53.0). Within-entry SD: the spread of one entry's "
              "score across replicates. Between-entry SD: the spread of entries' true scores, net of run noise. "
              "Within share: run noise as a share of the total variance of a single entry-run score.", ""]
    for s, rows in r["strategies"].items():
        lines += [f"## {names.get(s, s)} ({r['entries'][s]} entries scored in every replicate)", "",
                  "| Measure | Replicate means | Range of the mean | Within-entry SD | Between-entry SD | Within share |",
                  "|---|---|---|---|---|---|"]
        for key, row in rows.items():
            means = " / ".join(_pct(m) for m in row.get("replicate_means", []))
            lines.append(f"| {row['label']} | {means} | {_pct(row.get('mean_range'))} | {_pct(row.get('within_sd'))} | "
                         f"{_pct(row.get('between_sd'))} | {_pct(row.get('within_share'), 0)}% |")
        lines.append("")
    if r.get("paired"):
        lines += [f"## Evidence graph minus direct reading, per replicate ({r.get('paired_entries')} entries)", "",
                  "| Measure | " + " | ".join(x["run"] for x in next(iter(r["paired"].values()))["replicates"])
                  + " | Within-entry SD of the difference | Smallest difference distinguishable from run noise "
                    f"at n={r['n_target']} |",
                  "|---|" + "---|" * len(r["runs"]) + "---|---|"]
        for key, row in r["paired"].items():
            cells = []
            for x in row["replicates"]:
                ci = x.get("ci95")
                cells.append(f"{_pct(x['difference'])} [{_pct(ci[0])}, {_pct(ci[1])}]" if ci else _pct(x["difference"]))
            lines.append(f"| {row['label']} | " + " | ".join(cells) + f" | {_pct(row['difference_within_sd'])} | "
                         f"±{_pct(row['noise_threshold_at_n'])} |")
        lines += ["", "Intervals are 95% bootstrap intervals over entries. The last column is 1.96 × (within-entry SD "
                  f"of the per-entry difference) / √{r['n_target']}: the size a mean paired difference over "
                  f"{r['n_target']} entries, each run once, would have to exceed for run-to-run noise alone to "
                  "produce it less than 5% of the time. It is a floor, not an interval: the usual bootstrap interval "
                  "over entries already contains this noise, since each entry's difference was measured once.", ""]
        cov = r["paired"].get("gold_fact_coverage", {})
        if cov.get("noise_threshold_at_n") is not None:
            lines += [f"In plain terms: on {r['n_target']} entries run once, a difference between two strategies in "
                      f"OMIM facts conveyed smaller than about {_pct(cov['noise_threshold_at_n'])} points could be run "
                      f"noise alone (on these {r.get('paired_entries')} entries, about "
                      f"{_pct(cov.get('noise_threshold_at_30'))} points). Larger differences are not thereby real "
                      "differences between methods: the choice of entries adds its own, larger uncertainty, which the "
                      "bootstrap interval over entries measures.", ""]
    lines += ["## Model usage of each pass", "", "| Run | Calls | From cache | Made afresh | List price |",
              "|---|---|---|---|---|"]
    for name, u in r["usage"].items():
        lines.append(f"| {name} | {u['calls']} | {u['from_cache']} | {u['fresh_calls']} | ${u['list_price_usd']:.2f} |")
    stopped = {k: v for k, v in r["stopped"].items() if v}
    if stopped:
        lines += ["", "Stopped drafts (left out of the tables): "
                  + "; ".join(f"{k}: {', '.join(v)}" for k, v in stopped.items())]
    return "\n".join(lines) + "\n"


def write_replicates(run_dirs: list[Path]) -> dict[str, Any]:
    result = analyse(run_dirs)
    out = run_dirs[0]
    (out / "replicates.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "replicates.md").write_text(replicates_markdown(result), encoding="utf-8")
    return result
