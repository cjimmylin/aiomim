"""Paired comparison of the knowledge-graph strategy against the direct baseline.

Both strategies are run on the same entries with the same papers, so each entry
gives a matched pair of scores. For every metric this reports the two means, the
mean paired difference with a bootstrap 95% confidence interval, how many entries
each strategy won, and an exact sign test. Results are also broken down by the
entry's creation-era stratum and by how much of its literature was readable.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Callable

from .evalset import stratum_of

# (key, label, path into eval json, higher_is_better)
METRICS: list[tuple[str, str, str, bool]] = [
    ("claim_supported_rate", "Claims supported by cited paper", "faithfulness.supported_rate", True),
    ("claim_error_rate", "Claims unsupported or contradicted", "faithfulness.error_rate", False),
    ("claim_error_rate_before_repair", "… same, before the repair round", "faithfulness.before_repair.error_rate", False),
    ("gold_fact_coverage", "OMIM per-paper facts conveyed", "gold_text.coverage", True),
    ("gold_fact_strict_coverage", "… fully (no partial credit)", "gold_text.strict_coverage", True),
    ("gold_fact_contradiction_rate", "OMIM per-paper facts contradicted", "gold_text.contradiction_rate", False),
    ("hpo_exact_f1", "Clinical synopsis HPO F1, exact", "synopsis.exact.f1", True),
    ("hpo_exact_precision", "… precision", "synopsis.exact.precision", True),
    ("hpo_exact_recall", "… recall", "synopsis.exact.recall", True),
    ("hpo_hierarchical_f1", "Clinical synopsis HPO F1, hierarchical", "synopsis.hierarchical.f1", True),
    ("hpo_semantic_f1", "Clinical synopsis HPO F1, semantic", "synopsis.semantic.f1", True),
    ("variant_recall", "OMIM allelic variants recovered", "variants.recall", True),
    ("gene_f1", "Causal gene F1", "genes.f1", True),
    ("inheritance_match", "Inheritance matches OMIM", "inheritance.match", True),
    ("reference_recall", "OMIM references used", "references.cited.recall", True),
]


def _get(node: Any, path: str) -> float | None:
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, bool):
        return float(node)
    return node if isinstance(node, (int, float)) else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _bootstrap_ci(diffs: list[float], rng: random.Random, n: int = 10_000) -> tuple[float, float] | None:
    if len(diffs) < 5:
        return None
    k = len(diffs)
    means = sorted(sum(rng.choices(diffs, k=k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def _sign_test(wins: int, losses: int) -> float | None:
    """Exact two-sided binomial test of wins against losses (ties dropped)."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def _paired(pairs: list[tuple[dict, dict]], rng: random.Random) -> list[dict[str, Any]]:
    rows = []
    for key, label, path, higher_better in METRICS:
        values = [(a, b) for a, b in ((_get(k, path), _get(d, path)) for k, d in pairs) if a is not None and b is not None]
        if not values:
            continue
        diffs = [a - b for a, b in values]
        better = [d if higher_better else -d for d in diffs]
        wins, losses = sum(1 for d in better if d > 1e-9), sum(1 for d in better if d < -1e-9)
        ci = _bootstrap_ci(diffs, rng)
        rows.append({
            "metric": key, "label": label, "higher_is_better": higher_better, "n": len(values),
            "kg": round(_mean([a for a, _ in values]), 4), "direct": round(_mean([b for _, b in values]), 4),
            "difference": round(_mean(diffs), 4),
            "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
            "kg_better": wins, "direct_better": losses, "ties": len(values) - wins - losses,
            "sign_test_p": round(p, 4) if (p := _sign_test(wins, losses)) is not None else None,
        })
    return rows


def _pooled(evals: list[dict]) -> dict[str, Any]:
    claims = {k: sum(e["faithfulness"].get(k, 0) for e in evals)
              for k in ("supported", "partially_supported", "unsupported", "contradicted")}
    facts = {k: sum(e["gold_text"].get(k, 0) or 0 for e in evals)
             for k in ("n_facts", "present", "partial", "absent", "contradicted")}
    n_claims = sum(claims.values())
    return {
        "claims": {**claims, "n": n_claims,
                   "supported_rate": round(claims["supported"] / n_claims, 4) if n_claims else None,
                   "error_rate": round((claims["unsupported"] + claims["contradicted"]) / n_claims, 4) if n_claims else None},
        "gold_facts": {**facts,
                       "coverage": round((facts["present"] + 0.5 * facts["partial"]) / facts["n_facts"], 4) if facts["n_facts"] else None,
                       "contradiction_rate": round(facts["contradicted"] / facts["n_facts"], 4) if facts["n_facts"] else None},
    }


def access_group(evaluation: dict) -> str:
    """How much of the entry's cited literature could be read as full text."""
    access = evaluation.get("gold_reference_access") or {}
    total = sum(access.values())
    full = access.get("fulltext", 0)
    if not total:
        return "unknown"
    share = full / total
    if share == 0:
        return "no full text (abstracts only)"
    if share < 0.5:
        return "under half full text"
    if share < 1:
        return "half or more full text"
    return "all full text"


ACCESS_ORDER = ["no full text (abstracts only)", "under half full text", "half or more full text", "all full text"]
REFERENCE_ORDER = ["2-4 references", "5-8 references", "9 or more references"]


def reference_group(evaluation: dict) -> str:
    """Size of the entry's reference list, the nearest thing here to a scaling axis."""
    n = ((evaluation.get("references") or {}).get("cited") or {}).get("n_gold") or 0
    return REFERENCE_ORDER[0] if n <= 4 else REFERENCE_ORDER[1] if n <= 8 else REFERENCE_ORDER[2]


def compare_run(run_dir: Path, seed: int = 7) -> dict[str, Any]:
    pairs: list[tuple[dict, dict]] = []
    for kg_path in sorted(run_dir.glob("*/eval.kg.json")):
        direct_path = kg_path.with_name("eval.direct.json")
        if direct_path.exists():
            pairs.append((json.loads(kg_path.read_text()), json.loads(direct_path.read_text())))
    rng = random.Random(seed)

    def breakdown(group_of: Callable[[dict], str], order: list[str] | None = None) -> dict[str, Any]:
        groups: dict[str, list[tuple[dict, dict]]] = {}
        for pair in pairs:
            groups.setdefault(group_of(pair[0]), []).append(pair)
        keys = [g for g in (order or sorted(groups)) if g in groups]
        headline = ("claim_supported_rate", "claim_error_rate", "gold_fact_coverage", "hpo_exact_f1",
                    "hpo_hierarchical_f1", "variant_recall", "gene_f1", "inheritance_match")
        return {g: {"n": len(groups[g]),
                    "metrics": [r for r in _paired(groups[g], rng) if r["metric"] in headline]} for g in keys}

    return {
        "run": run_dir.name, "n_entries": len(pairs),
        "overall": _paired(pairs, rng),
        "pooled": {"kg": _pooled([k for k, _ in pairs]), "direct": _pooled([d for _, d in pairs])},
        "by_stratum": breakdown(lambda e: stratum_of(e["mim"])),
        "by_access": breakdown(access_group, ACCESS_ORDER),
        "by_gold_text_content_level": _by_content_level(pairs),
    }


def _by_content_level(pairs: list[tuple[dict, dict]]) -> dict[str, Any]:
    """Gold-fact coverage pooled by how much of the summarised paper was readable."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for which, index in (("kg", 0), ("direct", 1)):
        for pair in pairs:
            for level, tally in (pair[index]["gold_text"].get("by_content_level") or {}).items():
                cell = out.setdefault(level, {}).setdefault(which, {"n_facts": 0, "present": 0, "partial": 0, "contradicted": 0})
                for key in cell:
                    cell[key] += tally.get(key, 0) or 0
    for cells in out.values():
        for cell in cells.values():
            n = cell["n_facts"]
            cell["coverage"] = round((cell["present"] + 0.5 * cell["partial"]) / n, 4) if n else None
            cell["contradiction_rate"] = round(cell["contradicted"] / n, 4) if n else None
    return out


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{100 * value:.1f}%"


def _pp(value: float | None) -> str:
    return "–" if value is None else f"{100 * value:+.1f}"


def comparison_markdown(result: dict[str, Any]) -> str:
    def table(rows: list[dict[str, Any]]) -> str:
        lines = ["| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |",
                 "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            ci = f"{_pp(r['ci95'][0])} to {_pp(r['ci95'][1])}" if r["ci95"] else "–"
            arrow = "↑" if r["higher_is_better"] else "↓"
            p = "–" if r["sign_test_p"] is None else f"{r['sign_test_p']:.3f}"
            lines.append(f"| {r['label']} {arrow} | {r['n']} | {_pct(r['kg'])} | {_pct(r['direct'])} | {_pp(r['difference'])} | "
                         f"{ci} | {r['kg_better']} / {r['direct_better']} / {r['ties']} | {p} |")
        return "\n".join(lines)

    out = [f"# Evidence-graph strategy vs direct baseline — run `{result['run']}`",
           f"{result['n_entries']} entries, each written by both strategies from the same papers. Per-entry scores are "
           "paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence "
           "interval over entries. ↑ higher is better, ↓ lower is better.",
           "## All entries", table(result["overall"])]
    pooled = result["pooled"]
    out.append("## Pooled counts")
    lines = ["| | Evidence graph | Direct |", "|---|---|---|"]
    for label, group, key in (("Claims audited", "claims", "n"), ("… supported", "claims", "supported"),
                              ("… partly supported", "claims", "partially_supported"),
                              ("… unsupported", "claims", "unsupported"), ("… contradicted", "claims", "contradicted"),
                              ("OMIM facts scored", "gold_facts", "n_facts"), ("… conveyed", "gold_facts", "present"),
                              ("… partly conveyed", "gold_facts", "partial"), ("… missing", "gold_facts", "absent"),
                              ("… contradicted", "gold_facts", "contradicted")):
        lines.append(f"| {label} | {pooled['kg'][group][key]:,} | {pooled['direct'][group][key]:,} |")
    out.append("\n".join(lines))

    levels = result["by_gold_text_content_level"]
    if levels:
        out.append("## OMIM-fact coverage by how much of the paper was readable")
        lines = ["| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |",
                 "|---|---|---|---|---|---|"]
        for level in ("fulltext", "abstract", "title", "not_retrieved"):
            if level in levels:
                kg, direct = levels[level].get("kg", {}), levels[level].get("direct", {})
                lines.append(f"| {level} | {kg.get('n_facts', 0):,} | {_pct(kg.get('coverage'))} | {_pct(direct.get('coverage'))} | "
                             f"{_pct(kg.get('contradiction_rate'))} | {_pct(direct.get('contradiction_rate'))} |")
        out.append("\n".join(lines))

    for title, key in (("## By creation era (MIM number range)", "by_stratum"),
                       ("## By share of the entry's references readable as full text", "by_access")):
        out.append(title)
        for group, block in result[key].items():
            out.append(f"### {group} — {block['n']} entries")
            out.append(table(block["metrics"]))
    return "\n\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Any number of strategies
# --------------------------------------------------------------------------- #

VOLUME = [
    ("claims", "Claims audited per entry", "faithfulness.n_claims"),
    ("synopsis_terms", "Clinical-synopsis HPO terms per entry", "synopsis.exact.n_predicted"),
    ("variants", "Allelic variants per entry", "variants.n_generated"),
    ("references", "Papers cited per entry", "references.cited.n_predicted"),
    ("dropped_paragraphs", "Paragraphs dropped by the grounding guards per entry", "faithfulness.dropped_ungrounded_paragraphs"),
]
HEADLINE = ("claim_supported_rate", "claim_error_rate_before_repair", "gold_fact_coverage", "gold_fact_contradiction_rate",
            "hpo_exact_f1", "hpo_hierarchical_f1", "variant_recall", "gene_f1", "inheritance_match")
PHASES = ("generate", "audit", "score")


def load_evals(run_dir: Path) -> dict[str, dict[str, dict]]:
    """strategy -> {entry folder -> evaluation}, strategies in registry order."""
    from .strategies import STRATEGIES

    found: dict[str, dict[str, dict]] = {}
    for path in sorted(run_dir.glob("*/eval.*.json")):
        strategy = path.name.split(".")[1]
        found.setdefault(strategy, {})[path.parent.name] = json.loads(path.read_text())
    order = [n for n in STRATEGIES if n in found] + sorted(n for n in found if n not in STRATEGIES)
    return {n: found[n] for n in order}


def _paired_vs(pairs: list[tuple[dict, dict]], rng: random.Random, metrics=METRICS) -> list[dict[str, Any]]:
    """Paired comparison of a strategy (first of each pair) against the baseline (second)."""
    rows = []
    for key, label, path, higher_better in metrics:
        values = [(a, b) for a, b in ((_get(x, path), _get(y, path)) for x, y in pairs) if a is not None and b is not None]
        if not values:
            continue
        diffs = [a - b for a, b in values]
        better = [d if higher_better else -d for d in diffs]
        wins, losses = sum(1 for d in better if d > 1e-9), sum(1 for d in better if d < -1e-9)
        ci = _bootstrap_ci(diffs, rng)
        rows.append({
            "metric": key, "label": label, "higher_is_better": higher_better, "n": len(values),
            "strategy": round(_mean([a for a, _ in values]), 4), "baseline": round(_mean([b for _, b in values]), 4),
            "difference": round(_mean(diffs), 4), "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
            "better": wins, "worse": losses, "ties": len(values) - wins - losses,
            "sign_test_p": round(pv, 4) if (pv := _sign_test(wins, losses)) is not None else None,
        })
    return rows


def _means(evals_by_strategy: dict[str, list[dict]], metrics) -> list[dict[str, Any]]:
    rows = []
    for item in metrics:
        key, label, path = item[0], item[1], item[2]
        values, counts = {}, {}
        for strategy, evals in evals_by_strategy.items():
            got = [v for v in (_get(e, path) for e in evals) if v is not None]
            values[strategy] = round(_mean(got), 4) if got else None
            counts[strategy] = len(got)
        rows.append({"metric": key, "label": label, "higher_is_better": item[3] if len(item) > 3 else None,
                     "values": values, "n": counts})
    return rows


def usage_by_strategy(run_dir: Path, entries: list[str]) -> dict[str, dict[str, Any]]:
    """What each strategy costs to run from scratch, per entry and in total, split by phase.

    Read from the `full_*` tallies, which record a call's cost whether or not the
    last pass took it from cache. List price is the API price of the tokens; on a
    subscription it is a measure of consumption, not a bill.
    """
    out: dict[str, dict[str, Any]] = {}
    for folder in entries:
        path = run_dir / folder / "usage.json"
        if not path.exists():
            continue
        for strategy, summary in (json.loads(path.read_text()).get("by_strategy") or {}).items():
            acc = out.setdefault(strategy, {"entries": 0, **{ph: {"calls": 0, "turns": 0, "input_tokens": 0, "output_tokens": 0,
                                                                "list_price_usd": 0.0, "seconds": 0.0} for ph in (*PHASES, "total")}})
            acc["entries"] += 1
            for stage, tally in summary.items():
                if stage == "total":
                    continue
                phase = stage.split("/", 1)[0] if "/" in stage else "generate"
                for bucket in (phase if phase in PHASES else "generate", "total"):
                    b = acc[bucket]
                    b["calls"] += tally.get("calls", 0)
                    b["turns"] += tally.get("turns", 0)
                    b["input_tokens"] += tally.get("full_input_tokens", 0)
                    b["output_tokens"] += tally.get("full_output_tokens", 0)
                    b["list_price_usd"] += tally.get("full_list_price_usd", 0.0)
                    b["seconds"] += tally.get("full_seconds", 0.0)
    for acc in out.values():
        n = acc["entries"] or 1
        for bucket in (*PHASES, "total"):
            b = acc[bucket]
            b["list_price_usd"] = round(b["list_price_usd"], 2)
            b["seconds"] = round(b["seconds"], 1)
            b["per_entry"] = {"calls": round(b["calls"] / n, 1), "list_price_usd": round(b["list_price_usd"] / n, 3),
                              "input_tokens": round(b["input_tokens"] / n), "output_tokens": round(b["output_tokens"] / n),
                              "seconds": round(b["seconds"] / n, 1)}
    return out


def compare_strategies(run_dir: Path, baseline: str = "direct", seed: int = 7,
                       entries: list[str] | None = None) -> dict[str, Any]:
    """All strategies of a run side by side, over the entries every one of them completed.

    `entries` restricts the comparison to those entry folders (e.g. a held-out test split).
    """
    from .strategies import STRATEGIES

    evals = load_evals(run_dir)
    if entries is not None:
        wanted = set(entries)
        evals = {s: kept for s, items in evals.items() if (kept := {e: v for e, v in items.items() if e in wanted})}
    if not evals:
        return {}
    common = sorted(set.intersection(*(set(v) for v in evals.values())))
    if baseline not in evals:
        baseline = next(iter(evals))
    rng = random.Random(seed)
    by_strategy = {s: [evals[s][e] for e in common] for s in evals}

    def breakdown(group_of: Callable[[dict], str], order: list[str] | None = None) -> dict[str, Any]:
        groups: dict[str, list[str]] = {}
        for folder in common:
            groups.setdefault(group_of(evals[baseline][folder]), []).append(folder)
        keys = [g for g in (order or sorted(groups)) if g in groups]
        headline = [m for m in METRICS if m[0] in HEADLINE]
        return {g: {"n": len(groups[g]),
                    "means": _means({s: [evals[s][e] for e in groups[g]] for s in evals}, headline)} for g in keys}

    levels: dict[str, dict[str, dict[str, Any]]] = {}
    for strategy, items in by_strategy.items():
        for e in items:
            for level, tally in (e["gold_text"].get("by_content_level") or {}).items():
                cell = levels.setdefault(level, {}).setdefault(strategy, {"n_facts": 0, "present": 0, "partial": 0, "contradicted": 0})
                for k in cell:
                    cell[k] += tally.get(k, 0) or 0
    for cells in levels.values():
        for cell in cells.values():
            n = cell["n_facts"]
            cell["coverage"] = round((cell["present"] + 0.5 * cell["partial"]) / n, 4) if n else None
            cell["contradiction_rate"] = round(cell["contradicted"] / n, 4) if n else None

    return {
        "run": run_dir.name, "baseline": baseline, "n_entries": len(common),
        "strategies": [{"name": s, "label": STRATEGIES[s].label if s in STRATEGIES else s,
                        "summary": STRATEGIES[s].summary if s in STRATEGIES else "",
                        "control": bool(s in STRATEGIES and STRATEGIES[s].control), "n_entries": len(evals[s])}
                       for s in evals],
        "means": _means(by_strategy, METRICS),
        "volume": _means(by_strategy, VOLUME),
        "versus_baseline": {s: _paired_vs(list(zip(by_strategy[s], by_strategy[baseline])), rng)
                            for s in evals if s != baseline},
        "pooled": {s: _pooled(items) for s, items in by_strategy.items()},
        "by_content_level": levels,
        "by_stratum": breakdown(lambda e: stratum_of(e["mim"])),
        "by_access": breakdown(access_group, ACCESS_ORDER),
        "by_reference_count": breakdown(reference_group, REFERENCE_ORDER),
        "cost": usage_by_strategy(run_dir, common),
    }


def strategies_markdown(result: dict[str, Any]) -> str:
    names = [s["name"] for s in result["strategies"]]
    labels = {s["name"]: s["label"] for s in result["strategies"]}
    head = "| " + " | ".join(["Metric", *[labels[n] for n in names]]) + " |\n|" + "---|" * (len(names) + 1)

    def means_table(rows: list[dict[str, Any]], as_pct: bool = True) -> str:
        lines = [head]
        for r in rows:
            arrow = {True: " ↑", False: " ↓", None: ""}[r.get("higher_is_better")]
            cells = [(_pct(r["values"][n]) if as_pct else ("–" if r["values"][n] is None else f"{r['values'][n]:.1f}")) for n in names]
            lines.append(f"| {r['label']}{arrow} | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    out = [f"# Generation strategies compared — run `{result['run']}`",
           f"{result['n_entries']} entries, each written by every strategy from the same papers and put through the same "
           "audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.",
           "## The strategies",
           "\n".join(f"- **{s['label']}** (`{s['name']}`): {s['summary']}" for s in result["strategies"]),
           "## Scores", means_table(result["means"]),
           "## How much each strategy writes", means_table(result["volume"], as_pct=False)]

    base = labels[result["baseline"]]
    out.append(f"## Paired differences from the baseline ({base})")
    out.append("Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number "
               "of entries on which the strategy scored better / worse / the same.")
    wanted = [m for m in METRICS if m[0] in HEADLINE]
    lines = ["| Metric | " + " | ".join(labels[n] for n in names if n != result["baseline"]) + " |",
             "|" + "---|" * len(names)]
    for key, label, _, higher in wanted:
        cells = []
        for n in names:
            if n == result["baseline"]:
                continue
            row = next((r for r in result["versus_baseline"][n] if r["metric"] == key), None)
            if row is None:
                cells.append("–")
                continue
            ci = f" ({_pp(row['ci95'][0])} to {_pp(row['ci95'][1])})" if row["ci95"] else ""
            cells.append(f"{_pp(row['difference'])}{ci}; {row['better']}/{row['worse']}/{row['ties']}")
        lines.append(f"| {label} {'↑' if higher else '↓'} | " + " | ".join(cells) + " |")
    out.append("\n".join(lines))

    out.append("## Pooled counts")
    lines = ["| | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
    for label, group, key in (("Claims audited", "claims", "n"), ("… supported", "claims", "supported"),
                              ("… partly supported", "claims", "partially_supported"),
                              ("… unsupported", "claims", "unsupported"), ("… contradicted", "claims", "contradicted"),
                              ("OMIM facts scored", "gold_facts", "n_facts"), ("… conveyed", "gold_facts", "present"),
                              ("… partly conveyed", "gold_facts", "partial"), ("… missing", "gold_facts", "absent"),
                              ("… contradicted", "gold_facts", "contradicted")):
        lines.append(f"| {label} | " + " | ".join(f"{result['pooled'][n][group][key]:,}" for n in names) + " |")
    out.append("\n".join(lines))

    if result["by_content_level"]:
        out.append("## OMIM-fact coverage by how much of the paper was readable")
        lines = ["| Paper readable as | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
        for level in ("fulltext", "abstract", "title", "not_retrieved"):
            cells = result["by_content_level"].get(level)
            if cells:
                lines.append(f"| {level} | " + " | ".join(_pct((cells.get(n) or {}).get("coverage")) for n in names) + " |")
        out.append("\n".join(lines))

    for title, key in (("## By share of the entry's references readable as full text", "by_access"),
                       ("## By size of the reference list", "by_reference_count"),
                       ("## By creation era (MIM number range)", "by_stratum")):
        out.append(title)
        for group, block in result[key].items():
            out.append(f"### {group} — {block['n']} entries")
            out.append(means_table(block["means"]))

    cost = result.get("cost") or {}
    if cost:
        out.append("## What each strategy costs to run")
        out.append("Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude "
                   "subscription). Generation is the strategy itself; the audit and the scoring are the same procedure "
                   "for every strategy and cost more or less with the amount of text produced.")
        lines = ["| Per entry | " + " | ".join(labels[n] for n in names if n in cost) + " |",
                 "|" + "---|" * (len([n for n in names if n in cost]) + 1)]
        present = [n for n in names if n in cost]
        for label, getter in (
            ("Generation: model calls", lambda c: f"{c['generate']['per_entry']['calls']:.1f}"),
            ("Generation: list price", lambda c: f"${c['generate']['per_entry']['list_price_usd']:.2f}"),
            ("Generation: input / output tokens", lambda c: f"{c['generate']['per_entry']['input_tokens']:,} / {c['generate']['per_entry']['output_tokens']:,}"),
            ("Generation: model time (s)", lambda c: f"{c['generate']['per_entry']['seconds']:.0f}"),
            ("Audit and repair: list price", lambda c: f"${c['audit']['per_entry']['list_price_usd']:.2f}"),
            ("Scoring against OMIM: list price", lambda c: f"${c['score']['per_entry']['list_price_usd']:.2f}"),
            ("Everything: list price", lambda c: f"${c['total']['per_entry']['list_price_usd']:.2f}"),
        ):
            lines.append(f"| {label} | " + " | ".join(getter(cost[n]) for n in present) + " |")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Edge-level comparison of the generated knowledge with OMIM's
# --------------------------------------------------------------------------- #

EDGE_RELATIONS = ("caused_by", "inheritance", "has_phenotype", "has_variant")


def graph_edges(run_dir: Path, strategy: str) -> list[dict[str, str]]:
    """Every entry-level edge, generated or OMIM's, labelled by who has it.

    One row per (disease, relation, object): the causal genes, modes of
    inheritance, HPO phenotypes and allelic variants of each entry. `source` is
    "both" when the generated entry and OMIM agree, "generated_only" or
    "omim_only" otherwise. Phenotypes are compared by exact HPO id; variants by
    the matching done in the evaluation; only OMIM variants documented from a
    paper the entry cites are counted.
    """
    from .models import INHERITANCE_COARSE

    rows: list[dict[str, str]] = []
    for entry_path in sorted(run_dir.glob(f"*/entry.{strategy}.json")):
        folder = entry_path.parent
        eval_path, gold_path = folder / f"eval.{strategy}.json", folder / "gold.json"
        if not (eval_path.exists() and gold_path.exists()):
            continue
        entry, evaluation, gold = (json.loads(p.read_text()) for p in (entry_path, eval_path, gold_path))
        mim, title = gold["mim"], gold["title"]

        def add(relation: str, object_id: str, label: str, source: str, pmids: list[str] | None = None) -> None:
            rows.append({"mim": mim, "disease": title, "relation": relation, "object_id": object_id,
                         "object_label": label, "source": source, "pmids": ",".join(pmids or [])})

        gold_genes = {g["symbol"].upper() for g in gold["genes"] if g["symbol"]}
        seen = set()
        for rel in entry["relationships"]:
            symbol = rel["gene_symbol"].upper()
            seen.add(symbol)
            add("caused_by", symbol, symbol, "both" if symbol in gold_genes else "generated_only", rel["pmids"])
        for symbol in sorted(gold_genes - seen):
            add("caused_by", symbol, symbol, "omim_only")

        coarse = lambda codes: {INHERITANCE_COARSE[c] for c in codes if c in INHERITANCE_COARSE}  # noqa: E731
        predicted, expected = coarse(entry["inheritance"]), coarse(gold["inheritance"])
        for code in sorted(predicted | expected):
            add("inheritance", code, code,
                "both" if code in predicted and code in expected else "generated_only" if code in predicted else "omim_only")

        missed = {s.split(" ", 1)[0]: s.split(" ", 1)[-1] for s in evaluation["synopsis"]["missed"]}
        extra = {s.split(" ", 1)[0] for s in evaluation["synopsis"]["extra"]}
        for item in entry["clinical_synopsis"]:
            if item["hpo_id"]:
                add("has_phenotype", item["hpo_id"], item["hpo_label"],
                    "generated_only" if item["hpo_id"] in extra else "both", item["pmids"])
        for hpo_id, label in sorted(missed.items()):
            add("has_phenotype", hpo_id, label, "omim_only")

        variants = evaluation["variants"]
        matched = {m["generated"] for m in variants["matched"]} | set(variants.get("in_omim_via_other_paper", []))
        for av in entry["allelic_variants"]:
            pmids = list(dict.fromkeys(p for para in av["paragraphs"] for p in para["pmids"]))
            add("has_variant", "; ".join(av["hgvs"]) or av["name"], av["name"],
                "both" if av["name"] in matched else "generated_only", pmids)
        for name in variants["missed"]:
            add("has_variant", name.split(" ", 1)[0], name.split(" ", 1)[-1], "omim_only")
    return rows


def edge_scores(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Micro-averaged precision, recall and F1 per relation over all entries."""
    out: dict[str, dict[str, Any]] = {}
    for relation in EDGE_RELATIONS:
        subset = [r for r in rows if r["relation"] == relation]
        both = sum(1 for r in subset if r["source"] == "both")
        generated = both + sum(1 for r in subset if r["source"] == "generated_only")
        omim = both + sum(1 for r in subset if r["source"] == "omim_only")
        precision = both / generated if generated else None
        recall = both / omim if omim else None
        f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
        out[relation] = {"in_both": both, "generated": generated, "omim": omim,
                         "precision": round(precision, 4) if precision is not None else None,
                         "recall": round(recall, 4) if recall is not None else None,
                         "f1": round(f1, 4) if f1 is not None else None}
    return out


def write_graph_comparison(run_dir: Path) -> dict[str, Any]:
    """Write knowledge_graph.<strategy>.tsv for each strategy and return the edge scores."""
    columns = ["mim", "disease", "relation", "object_id", "object_label", "source", "pmids"]
    scores: dict[str, Any] = {}
    for strategy in load_evals(run_dir):
        rows = graph_edges(run_dir, strategy)
        if not rows:
            continue
        with (run_dir / f"knowledge_graph.{strategy}.tsv").open("w", encoding="utf-8") as fh:
            fh.write("\t".join(columns) + "\n")
            for row in rows:
                fh.write("\t".join(row[c].replace("\t", " ") for c in columns) + "\n")
        scores[strategy] = edge_scores(rows)
    return scores


def edge_markdown(scores: dict[str, Any]) -> str:
    labels = {"caused_by": "Disease → causal gene", "inheritance": "Disease → mode of inheritance",
              "has_phenotype": "Disease → phenotype (HPO, exact id)", "has_variant": "Disease → allelic variant"}
    from .strategies import STRATEGIES

    names = {n: (STRATEGIES[n].label if n in STRATEGIES else n) for n in scores}
    lines = ["## Knowledge-graph edges against OMIM (all entries pooled)",
             "Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the "
             "share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. "
             "A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.",
             "| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|"]
    for relation in EDGE_RELATIONS:
        for strategy in scores:
            s = scores.get(strategy, {}).get(relation)
            if s:
                lines.append(f"| {labels[relation]} | {names[strategy]} | {s['in_both']:,} | {s['generated']:,} | {s['omim']:,} | "
                             f"{_pct(s['precision'])} | {_pct(s['recall'])} | {_pct(s['f1'])} |")
    return "\n\n".join(lines[:2]) + "\n\n" + "\n".join(lines[2:]) + "\n"
