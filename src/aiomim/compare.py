"""Paired comparison of generation strategies against a baseline.

All strategies are run on the same entries with the same papers, so each entry
gives a matched set of scores. For every metric this reports the means, the mean
and median paired difference from the baseline with a bootstrap 95% confidence
interval, how many entries each strategy won, an exact sign test and, for the
headline measures other than the primary endpoint, Holm-adjusted p-values.
Results are also broken down by the entry's creation-era stratum and by how much
of its literature was readable.

Three rules make the comparison fair between strategies; all are applied here,
when the evaluation files are read, and none of them changes a file on disk:

* Completion. An entry is *complete* for a strategy when its draft exists and
  every per-paper call the strategy made succeeded; *incomplete* when a draft
  exists but one or more per-paper extraction calls failed (the paper was
  dropped); *no draft* when the writer was stopped or nothing was scored. The
  comparison uses only the entries complete for every compared strategy, and an
  intention-to-treat table repeats the headline measures over all entries.
* Empty predictions. `evaluate.prf` leaves F1 undefined when nothing is
  predicted, and a mean would then drop the entry. When a strategy predicted
  nothing and the gold set is not empty, F1 and recall count as 0 here
  (precision stays undefined): genes, the clinical synopsis (exact, hierarchical,
  semantic) and allelic variants.
* Every value carries the number of entries behind it.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Callable

from .evalset import STRATA, stratum_of

# (key, label, path into eval json, higher_is_better)
METRICS: list[tuple[str, str, str, bool]] = [
    ("claim_supported_rate", "Claims supported by cited paper", "faithfulness.supported_rate", True),
    ("claim_error_rate", "Claims unsupported or contradicted", "faithfulness.error_rate", False),
    ("claim_error_rate_before_repair", "… same, before the repair round", "faithfulness.before_repair.error_rate", False),
    ("claim_unsupported_rate_before_repair", "… unsupported, before the repair round",
     "derived.claim_unsupported_rate_before_repair", False),
    ("claim_contradicted_rate_before_repair", "… contradicted, before the repair round",
     "derived.claim_contradicted_rate_before_repair", False),
    ("gold_fact_coverage", "OMIM per-paper facts conveyed", "gold_text.coverage", True),
    ("gold_fact_strict_coverage", "… fully (no partial credit)", "gold_text.strict_coverage", True),
    ("gold_fact_contradiction_rate", "OMIM per-paper facts contradicted", "gold_text.contradiction_rate", False),
    ("hpo_exact_f1", "Clinical synopsis HPO F1, exact", "synopsis.exact.f1", True),
    ("hpo_exact_precision", "… precision", "synopsis.exact.precision", True),
    ("hpo_exact_recall", "… recall", "synopsis.exact.recall", True),
    ("hpo_hierarchical_f1", "Clinical synopsis HPO F1, hierarchical", "synopsis.hierarchical.f1", True),
    ("hpo_semantic_f1", "Clinical synopsis HPO F1, semantic", "synopsis.semantic.f1", True),
    ("variant_recall", "OMIM allelic variants recovered", "variants.recall", True),
    ("variant_precision", "Generated variants that are OMIM variants (precision)", "derived.variant_precision", True),
    ("gene_f1", "Causal gene F1", "genes.f1", True),
    ("gene_recall", "… recall", "genes.recall", True),
    ("inheritance_match", "Inheritance matches OMIM", "inheritance.match", True),
    ("inheritance_error_none_stated", "Inheritance error: none stated", "derived.inheritance_error_none_stated", False),
    ("inheritance_error_mode_missing", "Inheritance error: a mode missing", "derived.inheritance_error_mode_missing", False),
    ("inheritance_error_extra_mode", "Inheritance error: an extra mode", "derived.inheritance_error_extra_mode", False),
    ("inheritance_error_different_mode", "Inheritance error: a different mode",
     "derived.inheritance_error_different_mode", False),
    ("reference_recall", "OMIM references used", "references.cited.recall", True),
]
def _full_labels(metrics) -> dict[str, str]:
    """'… precision' -> 'Clinical synopsis HPO F1, exact: precision', for tables where rows are reordered."""
    out, parent = {}, ""
    for key, label, *_ in metrics:
        if label.startswith("…"):
            out[key] = f"{parent}: {label.lstrip('… ').strip()}"
        else:
            parent = out[key] = label
    return out


FULL_LABELS = _full_labels(METRICS) | {
    "claim_error_rate_before_repair": "Claims unsupported or contradicted, before the repair round",
    "claim_unsupported_rate_before_repair": "Claims unsupported, before the repair round",
    "claim_contradicted_rate_before_repair": "Claims contradicted, before the repair round",
    "gold_fact_strict_coverage": "OMIM per-paper facts conveyed fully (no partial credit)",
    "hpo_exact_precision": "Clinical synopsis HPO precision, exact",
    "hpo_exact_recall": "Clinical synopsis HPO recall, exact",
    "gene_recall": "Causal gene recall",
}
INHERITANCE_ERRORS = ("none_stated", "mode_missing", "extra_mode", "different_mode")
PRIMARY = "gold_fact_coverage"
SMALL_N = 20     # below this many entries a percentile bootstrap interval is unreliable


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


def _holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjustment of a family of p-values."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(ordered), 0.0, {}
    for i, (key, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        out[key] = running
    return out


# --------------------------------------------------------------------------- #
# Reading the evaluation files
# --------------------------------------------------------------------------- #


def prepare_eval(evaluation: dict) -> dict:
    """Apply the empty-prediction rule and add the derived measures, in memory only.

    Records what was changed under `derived.empty_prediction` (a list of the
    fields whose F1 and recall were set to 0).
    """
    from .models import INHERITANCE_COARSE

    derived = evaluation.setdefault("derived", {})
    if derived.get("_prepared"):
        return evaluation
    empty: list[str] = []
    genes = evaluation.get("genes")
    if isinstance(genes, dict) and genes.get("n_predicted") == 0 and (genes.get("n_gold") or 0) > 0:
        genes["f1"], genes["recall"] = 0.0, 0.0
        empty.append("genes")
    syn = evaluation.get("synopsis")
    exact = (syn or {}).get("exact") if isinstance(syn, dict) else None
    if isinstance(exact, dict) and exact.get("n_predicted") == 0 and (exact.get("n_gold") or 0) > 0:
        for kind in ("exact", "hierarchical", "semantic"):
            if isinstance(syn.get(kind), dict):
                syn[kind]["f1"], syn[kind]["recall"] = 0.0, 0.0
        empty.append("synopsis")
    variants = evaluation.get("variants")
    if isinstance(variants, dict) and variants.get("n_generated") == 0 and (variants.get("n_gold") or 0) > 0:
        variants["recall"] = 0.0          # already 0 by construction; set for clarity
        empty.append("variants")
    derived["empty_prediction"] = empty

    if isinstance(variants, dict) and "n_generated" in variants:
        n_gen, n_gold = variants.get("n_generated") or 0, variants.get("n_gold") or 0
        # Only where OMIM lists variants for the entry: elsewhere every generated
        # variant would count as a miss whatever its merit.
        derived["variant_precision"] = round(variants.get("n_matched", 0) / n_gen, 4) if n_gen and n_gold else None
        derived["variants_generated"] = n_gen
        derived["variants_not_in_omim"] = len(variants.get("not_in_omim") or [])
        derived["variants_in_omim_via_other_paper"] = len(variants.get("in_omim_via_other_paper") or [])

    inh = evaluation.get("inheritance")
    if isinstance(inh, dict) and "gold" in inh:
        coarse = lambda codes: {INHERITANCE_COARSE[c] for c in codes or [] if c in INHERITANCE_COARSE}  # noqa: E731
        predicted, gold = coarse(inh.get("predicted")), coarse(inh.get("gold"))
        kind = None
        if gold and predicted != gold:
            kind = ("none_stated" if not predicted else "mode_missing" if predicted < gold
                    else "extra_mode" if predicted > gold else "different_mode")
        for k in INHERITANCE_ERRORS:
            derived[f"inheritance_error_{k}"] = None if not gold else float(kind == k)
        derived["inheritance_error"] = kind

    before = (evaluation.get("faithfulness") or {}).get("before_repair") or {}
    n = before.get("n_claims") or 0
    derived["claim_unsupported_rate_before_repair"] = round(before.get("unsupported", 0) / n, 4) if n else None
    derived["claim_contradicted_rate_before_repair"] = round(before.get("contradicted", 0) / n, 4) if n else None
    derived["_prepared"] = True
    return evaluation


def _read_eval(path: Path) -> dict:
    return prepare_eval(json.loads(path.read_text()))


def _papers_failed(meta: dict) -> list[str] | None:
    """The PMIDs whose per-paper call failed, from whichever record the strategy keeps; None if none is kept."""
    for value in meta.values():
        if isinstance(value, dict) and isinstance(value.get("papers_failed"), list):
            return value["papers_failed"]
    return None


def completion_status(run_dir: Path, entries: list[str] | None = None) -> dict[str, dict[str, dict[str, Any]]]:
    """strategy -> {entry folder -> {"status": complete | incomplete | no_draft, ...}}.

    `no_draft`: the evaluation is missing or marks the writer as stopped.
    `incomplete`: a draft exists but a per-paper call failed and its paper was
    dropped (evidence graph: meta.extraction.papers_failed; case table:
    meta.cohort.papers_failed; reconciled: meta.reconciled.papers_failed, or for
    entries written before that was recorded, the case table's record of the same
    entry, since both run the same cached case extraction).
    """
    wanted = set(entries) if entries is not None else None
    folders: dict[str, set[str]] = {}
    for path in sorted(run_dir.glob("*/eval.*.json")):
        if wanted is None or path.parent.name in wanted:
            folders.setdefault(path.parent.name, set()).add(path.name.split(".")[1])
    names = sorted({s for v in folders.values() for s in v})
    out: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in names}
    for folder, present in sorted(folders.items()):
        for s in names:
            eval_path = run_dir / folder / f"eval.{s}.json"
            if s not in present:
                out[s][folder] = {"status": "no_draft", "reason": "no evaluation file"}
                continue
            stopped = json.loads(eval_path.read_text()).get("stopped")
            if stopped:
                out[s][folder] = {"status": "no_draft", "reason": stopped}
                continue
            entry_path = run_dir / folder / f"entry.{s}.json"
            meta = (json.loads(entry_path.read_text()).get("meta") or {}) if entry_path.exists() else {}
            failed, source = _papers_failed(meta), f"entry.{s}.json"
            if failed is None and s == "reconciled":
                cohort = run_dir / folder / "entry.cohort.json"
                if cohort.exists():
                    failed = ((json.loads(cohort.read_text()).get("meta") or {}).get("cohort") or {}).get("papers_failed")
                    source = "entry.cohort.json (same case extraction)"
            row: dict[str, Any] = {"status": "incomplete" if failed else "complete"}
            if failed:
                row.update(papers_failed=list(failed), source=source)
            out[s][folder] = row
    return out


def load_evals(run_dir: Path) -> dict[str, dict[str, dict]]:
    """strategy -> {entry folder -> evaluation}, strategies in registry order.

    Drafts that were stopped are left out (see `stopped_entries`); incomplete ones
    are kept here and set aside by `compare_strategies`. The empty-prediction rule
    and the derived measures are applied (`prepare_eval`).
    """
    from .strategies import STRATEGIES

    found: dict[str, dict[str, dict]] = {}
    for path in sorted(run_dir.glob("*/eval.*.json")):
        strategy = path.name.split(".")[1]
        evaluation = json.loads(path.read_text())
        if evaluation.get("stopped"):
            continue    # no draft was written (see `stopped_entries`); not a draft that scored zero
        found.setdefault(strategy, {})[path.parent.name] = prepare_eval(evaluation)
    order = [n for n in STRATEGIES if n in found] + sorted(n for n in found if n not in STRATEGIES)
    return {n: found[n] for n in order}


def stopped_entries(run_dir: Path) -> dict[str, dict[str, str]]:
    """strategy -> {entry folder -> why no draft was written}."""
    out: dict[str, dict[str, str]] = {}
    for path in sorted(run_dir.glob("*/eval.*.json")):
        reason = json.loads(path.read_text()).get("stopped")
        if reason:
            out.setdefault(path.name.split(".")[1], {})[path.parent.name] = reason
    return out


# --------------------------------------------------------------------------- #
# Paired statistics
# --------------------------------------------------------------------------- #


def _pair_stats(values: list[tuple[float, float]], higher_better: bool, rng: random.Random) -> dict[str, Any]:
    diffs = [a - b for a, b in values]
    better = [d if higher_better else -d for d in diffs]
    wins, losses = sum(1 for d in better if d > 1e-9), sum(1 for d in better if d < -1e-9)
    ci = _bootstrap_ci(diffs, rng)
    p = _sign_test(wins, losses)
    return {
        "n": len(values),
        "difference": round(_mean(diffs), 4), "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        "median_difference": round(statistics.median(diffs), 4),
        "better": wins, "worse": losses, "ties": len(values) - wins - losses,
        "sign_test_p": round(p, 4) if p is not None else None,
        "ci_unreliable": len(values) < SMALL_N,
    }


def _paired(pairs: list[tuple[dict, dict]], rng: random.Random) -> list[dict[str, Any]]:
    """Legacy two-way rows (evidence graph first, direct second) with kg/direct key names."""
    rows = []
    for row in _paired_vs(pairs, rng, holm=False):
        rows.append({"metric": row["metric"], "label": row["label"], "higher_is_better": row["higher_is_better"],
                     "n": row["n"], "kg": row["strategy"], "direct": row["baseline"], "difference": row["difference"],
                     "ci95": row["ci95"], "median_difference": row["median_difference"],
                     "kg_better": row["better"], "direct_better": row["worse"], "ties": row["ties"],
                     "sign_test_p": row["sign_test_p"], "ci_unreliable": row["ci_unreliable"]})
    return rows


def _pooled(evals: list[dict]) -> dict[str, Any]:
    claims = {k: sum(e["faithfulness"].get(k, 0) for e in evals)
              for k in ("supported", "partially_supported", "unsupported", "contradicted")}
    facts = {k: sum(e["gold_text"].get(k, 0) or 0 for e in evals)
             for k in ("n_facts", "present", "partial", "absent", "contradicted")}
    n_claims = sum(claims.values())
    before = {k: sum(((e["faithfulness"].get("before_repair") or {}).get(k, 0) or 0) for e in evals)
              for k in ("n_claims", "supported", "partially_supported", "unsupported", "contradicted")}
    variants = {"generated": 0, "matched": 0, "matched_scoped": 0, "generated_scoped": 0,
                "not_in_omim": 0, "in_omim_via_other_paper": 0}
    inheritance = {k: 0 for k in ("scored", "match", *INHERITANCE_ERRORS)}
    empty = {"genes": 0, "synopsis": 0, "variants": 0}
    for e in evals:
        d = e.get("derived") or {}
        v = e.get("variants") or {}
        variants["generated"] += v.get("n_generated", 0) or 0
        variants["matched"] += v.get("n_matched", 0) or 0
        if v.get("n_gold"):
            variants["generated_scoped"] += v.get("n_generated", 0) or 0
            variants["matched_scoped"] += v.get("n_matched", 0) or 0
        variants["not_in_omim"] += d.get("variants_not_in_omim", 0) or 0
        variants["in_omim_via_other_paper"] += d.get("variants_in_omim_via_other_paper", 0) or 0
        match = (e.get("inheritance") or {}).get("match")
        if match is not None:
            inheritance["scored"] += 1
            inheritance["match"] += int(bool(match))
        if d.get("inheritance_error"):
            inheritance[d["inheritance_error"]] += 1
        for field in d.get("empty_prediction") or []:
            empty[field] += 1
    variants["precision"] = (round(variants["matched_scoped"] / variants["generated_scoped"], 4)
                             if variants["generated_scoped"] else None)
    return {
        "claims": {**claims, "n": n_claims,
                   "supported_rate": round(claims["supported"] / n_claims, 4) if n_claims else None,
                   "error_rate": round((claims["unsupported"] + claims["contradicted"]) / n_claims, 4) if n_claims else None},
        "claims_before_repair": {**before,
                                 "unsupported_rate": round(before["unsupported"] / before["n_claims"], 4) if before["n_claims"] else None,
                                 "contradicted_rate": round(before["contradicted"] / before["n_claims"], 4) if before["n_claims"] else None},
        "gold_facts": {**facts,
                       "coverage": round((facts["present"] + 0.5 * facts["partial"]) / facts["n_facts"], 4) if facts["n_facts"] else None,
                       "contradiction_rate": round(facts["contradicted"] / facts["n_facts"], 4) if facts["n_facts"] else None},
        "variants": variants,
        "inheritance": inheritance,
        "empty_predictions": empty,
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
LEVEL_ORDER = ("fulltext", "abstract", "title", "not_retrieved")
STRATUM_ORDER = [label for label, _ in STRATA] + ["other"]


def reference_group(evaluation: dict) -> str:
    """Size of the entry's reference list, the nearest thing here to a scaling axis."""
    n = ((evaluation.get("references") or {}).get("cited") or {}).get("n_gold") or 0
    return REFERENCE_ORDER[0] if n <= 4 else REFERENCE_ORDER[1] if n <= 8 else REFERENCE_ORDER[2]


def compare_run(run_dir: Path, seed: int = 7) -> dict[str, Any]:
    """The evidence graph against direct reading, over entries both completed in full."""
    status = completion_status(run_dir)
    complete = lambda s, folder: (status.get(s) or {}).get(folder, {}).get("status") == "complete"  # noqa: E731
    pairs: list[tuple[dict, dict]] = []
    left_out: list[str] = []
    for kg_path in sorted(run_dir.glob("*/eval.kg.json")):
        direct_path = kg_path.with_name("eval.direct.json")
        if direct_path.exists():
            folder = kg_path.parent.name
            if complete("kg", folder) and complete("direct", folder):
                pairs.append((_read_eval(kg_path), _read_eval(direct_path)))
            else:
                left_out.append(folder)
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
        "run": run_dir.name, "n_entries": len(pairs), "left_out": left_out,
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


def _p(value: float | None) -> str:
    return "–" if value is None else ("<0.001" if value < 0.001 else f"{value:.3f}")


def _n_note(k: int | None, n: int) -> str:
    return f" (n={k})" if k is not None and k != n else ""


def _unreliable_note(n: int) -> str:
    return (f"**Fewer than {SMALL_N} entries: the bootstrap interval is unreliable** (a percentile bootstrap over so "
            "few entries is too narrow); read the sign test and the counts instead.")


def comparison_markdown(result: dict[str, Any]) -> str:
    def table(rows: list[dict[str, Any]], n_total: int) -> str:
        lines = ["| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | "
                 "Graph better / direct better / tie | Sign test p |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            ci = f"{_pp(r['ci95'][0])} to {_pp(r['ci95'][1])}" if r["ci95"] else "–"
            arrow = "↑" if r["higher_is_better"] else "↓"
            p = "–" if r["sign_test_p"] is None else f"{r['sign_test_p']:.3f}"
            lines.append(f"| {r['label']} {arrow} | {r['n']} | {_pct(r['kg'])} | {_pct(r['direct'])} | {_pp(r['difference'])} | "
                         f"{ci} | {_pp(r.get('median_difference'))} | {r['kg_better']} / {r['direct_better']} / {r['ties']} | {p} |")
        out = "\n".join(lines)
        return (out + "\n\n" + _unreliable_note(n_total)) if 0 < n_total < SMALL_N else out

    out = [f"# Evidence-graph strategy vs direct baseline — run `{result['run']}`",
           f"{result['n_entries']} entries, each written in full by both strategies from the same papers. Per-entry "
           "scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% "
           "confidence interval over entries. ↑ higher is better, ↓ lower is better. An entry with no draft, or one "
           "for which a per-paper extraction call failed, is left out"
           + (f" ({len(result.get('left_out') or [])}: {', '.join(result['left_out'])})" if result.get("left_out") else "")
           + ". Where a strategy predicted nothing against a non-empty gold set, F1 and recall count as 0.",
           "## All entries", table(result["overall"], result["n_entries"])]
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
        for level in LEVEL_ORDER:
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
            out.append(table(block["metrics"], block["n"]))
    return "\n\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Any number of strategies
# --------------------------------------------------------------------------- #

VOLUME = [
    ("claims", "Claims audited per entry", "faithfulness.n_claims"),
    ("claims_not_checkable", "Claims that could not be audited per entry", "faithfulness.not_checkable"),
    ("synopsis_terms", "Clinical-synopsis HPO terms per entry", "synopsis.exact.n_predicted"),
    ("variants", "Allelic variants per entry", "variants.n_generated"),
    ("variants_not_in_omim", "… of which not in OMIM", "derived.variants_not_in_omim"),
    ("references", "Papers cited per entry", "references.cited.n_predicted"),
    ("dropped_paragraphs", "Paragraphs dropped by the grounding guards per entry", "faithfulness.dropped_ungrounded_paragraphs"),
]
HEADLINE = ("claim_supported_rate", "claim_error_rate_before_repair", "gold_fact_coverage", "gold_fact_contradiction_rate",
            "hpo_exact_f1", "hpo_hierarchical_f1", "variant_recall", "gene_f1", "inheritance_match")
PHASES = ("generate", "audit", "score")


def _paired_vs(pairs: list[tuple[dict, dict]], rng: random.Random, metrics=METRICS, holm: bool = True) -> list[dict[str, Any]]:
    """Paired comparison of a strategy (first of each pair) against the baseline (second).

    Each row has the mean and median difference, a bootstrap interval, the
    better / worse / tie counts and the exact sign test. The primary endpoint is
    marked; across the other headline measures the sign-test p-values are
    Holm-adjusted (`sign_test_p_holm`).
    """
    rows = []
    for key, label, path, higher_better in metrics:
        values = [(a, b) for a, b in ((_get(x, path), _get(y, path)) for x, y in pairs) if a is not None and b is not None]
        if not values:
            continue
        stats = _pair_stats(values, higher_better, rng)
        rows.append({
            "metric": key, "label": label, "higher_is_better": higher_better, "n": stats["n"],
            "strategy": round(_mean([a for a, _ in values]), 4), "baseline": round(_mean([b for _, b in values]), 4),
            **{k: v for k, v in stats.items() if k != "n"},
            "primary": key == PRIMARY, "headline": key in HEADLINE,
        })
    if holm:
        family = {r["metric"]: r["sign_test_p"] for r in rows
                  if r["headline"] and not r["primary"] and r["sign_test_p"] is not None}
        adjusted = _holm(family)
        for r in rows:
            if r["metric"] in adjusted:
                r["sign_test_p_holm"] = round(adjusted[r["metric"]], 4)
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


def _level_tallies(evaluation: dict) -> dict[str, tuple[float, int]]:
    """content level -> (facts conveyed with partial as half, facts scored) for one entry."""
    out = {}
    for level, tally in ((evaluation.get("gold_text") or {}).get("by_content_level") or {}).items():
        n = tally.get("n_facts", 0) or 0
        out[level] = ((tally.get("present", 0) or 0) + 0.5 * (tally.get("partial", 0) or 0), n)
    return out


def _level_differences(by_strategy: dict[str, list[dict]], baseline: str, rng: random.Random,
                       n_boot: int = 2000) -> dict[str, dict[str, Any]]:
    """Paper-level coverage by readable level, pooled over facts, minus the baseline's.

    The interval resamples entries (all of an entry's facts move together).
    """
    tallies = {s: [_level_tallies(e) for e in items] for s, items in by_strategy.items()}
    levels = sorted({lv for items in tallies.values() for t in items for lv in t},
                    key=lambda lv: LEVEL_ORDER.index(lv) if lv in LEVEL_ORDER else 99)
    k = len(tallies[baseline])
    out: dict[str, dict[str, Any]] = {}

    def cov(items, idx, level):
        got = sum(items[i].get(level, (0, 0))[0] for i in idx)
        n = sum(items[i].get(level, (0, 0))[1] for i in idx)
        return (got / n if n else None), n

    for level in levels:
        row: dict[str, Any] = {}
        base_cov, base_n = cov(tallies[baseline], range(k), level)
        row[baseline] = {"coverage": round(base_cov, 4) if base_cov is not None else None, "n_facts": base_n}
        for s in by_strategy:
            if s == baseline:
                continue
            s_cov, s_n = cov(tallies[s], range(k), level)
            n_entries = sum(1 for i in range(k) if tallies[s][i].get(level, (0, 0))[1] and tallies[baseline][i].get(level, (0, 0))[1])
            cell: dict[str, Any] = {"coverage": round(s_cov, 4) if s_cov is not None else None, "n_facts": s_n,
                                    "n_entries": n_entries,
                                    "difference": round(s_cov - base_cov, 4) if s_cov is not None and base_cov is not None else None,
                                    "ci95": None}
            if cell["difference"] is not None and n_entries >= 5:
                diffs = []
                for _ in range(n_boot):
                    idx = rng.choices(range(k), k=k)
                    a, _ = cov(tallies[s], idx, level)
                    b, _ = cov(tallies[baseline], idx, level)
                    if a is not None and b is not None:
                        diffs.append(a - b)
                diffs.sort()
                if diffs:
                    cell["ci95"] = [round(diffs[int(0.025 * len(diffs))], 4), round(diffs[int(0.975 * len(diffs)) - 1], 4)]
            cell["ci_unreliable"] = n_entries < SMALL_N
            row[s] = cell
        out[level] = row
    return out


def _era_by_access(by_strategy: dict[str, list[dict]], strategies: list[str]) -> dict[str, Any]:
    """OMIM facts conveyed by creation era within each readable level, pooled over facts."""
    out: dict[str, Any] = {}
    for s in strategies:
        cells: dict[str, dict[str, dict[str, Any]]] = {}
        for e in by_strategy[s]:
            era = stratum_of(e["mim"])
            for level, (got, n) in _level_tallies(e).items():
                cell = cells.setdefault(level, {}).setdefault(era, {"n_facts": 0, "conveyed": 0.0, "n_entries": 0})
                cell["n_facts"] += n
                cell["conveyed"] += got
                cell["n_entries"] += 1 if n else 0
        for level in cells.values():
            for cell in level.values():
                cell["coverage"] = round(cell["conveyed"] / cell["n_facts"], 4) if cell["n_facts"] else None
                cell["conveyed"] = round(cell["conveyed"], 1)
        out[s] = {lv: {era: cells[lv][era] for era in STRATUM_ORDER if era in cells[lv]}
                  for lv in sorted(cells, key=lambda x: LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 99)}
    return out


# Where no strategy has a draft for an entry, whether a measure has a gold set is read
# from the stopped evaluation (which records the gold counts) or, for the synopsis, gold.json.
_GOLD_INDICATOR = {
    "claim_supported_rate": None,                     # needs no gold
    "gold_fact_coverage": "gold_text.n_facts", "variant_recall": "variants.n_gold",
    "gene_f1": "genes.n_gold", "inheritance_match": "inheritance.n_gold",
}


def _gold_defined(run_dir: Path | None, folder: str, metric: str) -> bool:
    if run_dir is None:
        return False
    if metric in _GOLD_INDICATOR:
        path = _GOLD_INDICATOR[metric]
        if path is None:
            return True
        for eval_path in sorted((run_dir / folder).glob("eval.*.json")):
            if (_get(json.loads(eval_path.read_text()), path) or 0) > 0:
                return True
        return False
    if metric.startswith("hpo_"):
        gold = run_dir / folder / "gold.json"
        if gold.exists():
            annotations = json.loads(gold.read_text()).get("hpo_annotations") or []
            return any(a.get("aspect") == "P" and str(a.get("qualifier", "")).upper() != "NOT" for a in annotations)
    return False


def _intention_to_treat(evals: dict[str, dict[str, dict]], folders: list[str], baseline: str,
                        rng: random.Random, run_dir: Path | None = None) -> dict[str, Any]:
    """Headline measures over every entry: a missing draft counts as zero, incomplete drafts stay in.

    A missing draft scores 0 on a higher-is-better measure wherever that measure is
    defined for the entry (some other strategy has a value for it, so the gold
    set exists; where no strategy drafted the entry, from the gold counts the stopped
    evaluation records, or gold.json for the synopsis). Lower-is-better measures
    cannot be zero-filled meaningfully (a missing draft has no errors); they are
    averaged over the drafts that exist.
    """
    wanted = [m for m in METRICS if m[0] in HEADLINE]
    values: dict[str, dict[str, list[float | None]]] = {s: {} for s in evals}
    zero_filled: dict[str, int] = {s: 0 for s in evals}
    for key, _, path, higher in wanted:
        for s in evals:
            column = []
            for folder in folders:
                if folder in evals[s]:
                    column.append(_get(evals[s][folder], path))
                    continue
                drafted = [other[folder] for other in evals.values() if folder in other]
                defined = (any(_get(e, path) is not None for e in drafted) if drafted
                           else _gold_defined(run_dir, folder, key))
                column.append(0.0 if higher and defined else None)
            values[s][key] = column
    for s in evals:
        zero_filled[s] = sum(1 for f in folders if f not in evals[s])
    means = []
    for key, label, _, higher in wanted:
        row = {"metric": key, "label": label, "higher_is_better": higher, "values": {}, "n": {}}
        for s in evals:
            got = [v for v in values[s][key] if v is not None]
            row["values"][s] = round(_mean(got), 4) if got else None
            row["n"][s] = len(got)
        means.append(row)
    versus = {}
    for s in evals:
        if s == baseline:
            continue
        rows = []
        for key, label, _, higher in wanted:
            pairs = [(a, b) for a, b in zip(values[s][key], values[baseline][key]) if a is not None and b is not None]
            if pairs:
                rows.append({"metric": key, "label": label, "higher_is_better": higher, "primary": key == PRIMARY,
                             "strategy": round(_mean([a for a, _ in pairs]), 4),
                             "baseline": round(_mean([b for _, b in pairs]), 4),
                             **_pair_stats(pairs, higher, rng)})
        versus[s] = rows
    return {"n_entries": len(folders), "missing_drafts_counted_as_zero": zero_filled, "means": means,
            "versus_baseline": versus}


def compare_strategies(run_dir: Path, baseline: str = "direct", seed: int = 7,
                       entries: list[str] | None = None) -> dict[str, Any]:
    """All strategies of a run side by side, over the entries every one of them completed in full.

    `entries` restricts the comparison to those entry folders (e.g. a held-out test split).
    """
    from .strategies import STRATEGIES

    evals = load_evals(run_dir)
    if entries is not None:
        wanted = set(entries)
        evals = {s: kept for s, items in evals.items() if (kept := {e: v for e, v in items.items() if e in wanted})}
    if not evals:
        return {}
    status = completion_status(run_dir, entries)
    # An entry is compared only when every strategy wrote it and none of them lost a
    # paper to a failed per-paper call: the same rule for one-call and multi-call strategies.
    complete = {s: {e for e in v if (status.get(s) or {}).get(e, {}).get("status", "complete") == "complete"}
                for s, v in evals.items()}
    common = sorted(set.intersection(*complete.values()))
    all_folders = sorted({e for v in status.values() for e in v})
    stopped = {s: sorted(e for e in v if entries is None or e in set(entries))
               for s, v in stopped_entries(run_dir).items()}
    stopped = {s: v for s, v in stopped.items() if v}
    completion = {}
    for s in evals:
        rows = status.get(s) or {}
        completion[s] = {
            "complete": sorted(e for e, r in rows.items() if r["status"] == "complete"),
            "incomplete": {e: r.get("papers_failed", []) for e, r in sorted(rows.items()) if r["status"] == "incomplete"},
            "incomplete_source": {e: r.get("source") for e, r in sorted(rows.items()) if r["status"] == "incomplete"},
            "no_draft": sorted(e for e, r in rows.items() if r["status"] == "no_draft"),
        }
    left_out = sorted(set(all_folders) - set(common))
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

    def paired_breakdown(group_of: Callable[[dict], str], order: list[str], metrics: tuple[str, ...]) -> dict[str, Any]:
        groups: dict[str, list[str]] = {}
        for folder in common:
            groups.setdefault(group_of(evals[baseline][folder]), []).append(folder)
        chosen = [m for m in METRICS if m[0] in metrics]
        return {g: {"n": len(groups[g]),
                    "versus_baseline": {s: _paired_vs([(evals[s][e], evals[baseline][e]) for e in groups[g]], rng,
                                                      chosen, holm=False)
                                        for s in evals if s != baseline}}
                for g in [g for g in order if g in groups]}

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

    controls = [s for s in evals if s in STRATEGIES and STRATEGIES[s].control]
    return {
        "run": run_dir.name, "baseline": baseline, "n_entries": len(common),
        "primary_endpoint": PRIMARY,
        "stopped": stopped,
        "completion": completion,
        "n_entries_in_run": len(all_folders),
        "left_out": left_out,
        "strategies": [{"name": s, "label": STRATEGIES[s].label if s in STRATEGIES else s,
                        "summary": STRATEGIES[s].summary if s in STRATEGIES else "",
                        "control": bool(s in STRATEGIES and STRATEGIES[s].control), "n_entries": len(evals[s])}
                       for s in evals],
        "means": _means(by_strategy, METRICS),
        "volume": _means(by_strategy, VOLUME),
        "versus_baseline": {s: _paired_vs(list(zip(by_strategy[s], by_strategy[baseline])), rng)
                            for s in evals if s != baseline},
        "intention_to_treat": _intention_to_treat(
            {s: {e: v for e, v in items.items() if e in set(all_folders)} for s, items in evals.items()},
            all_folders, baseline, rng, run_dir),
        "pooled": {s: _pooled(items) for s, items in by_strategy.items()},
        "by_content_level": levels,
        "by_content_level_vs_baseline": _level_differences(by_strategy, baseline, rng),
        "by_stratum": breakdown(lambda e: stratum_of(e["mim"])),
        "by_access": breakdown(access_group, ACCESS_ORDER),
        "by_access_paired": paired_breakdown(access_group, ACCESS_ORDER, ("gold_fact_coverage", "variant_recall")),
        "era_by_access": _era_by_access(by_strategy, [baseline, *[c for c in controls if c != baseline]]),
        "by_reference_count": breakdown(reference_group, REFERENCE_ORDER),
        "cost": usage_by_strategy(run_dir, common),
    }


def _stopped_note(result: dict[str, Any]) -> str:
    labels = {s["name"]: s["label"] for s in result["strategies"]}
    all_stopped = sorted({e for v in result["stopped"].values() for e in v})
    per = "; ".join(f"{labels.get(s, s)} {len(v)}" for s, v in result["stopped"].items())
    return (f"No draft: {len(all_stopped)} entries for which at least one strategy wrote nothing, because the model's "
            f"safety filter stopped the writer's reply or the reply came back empty ({per}). "
            f"Entries: {', '.join(all_stopped)}. They are left out of the comparison with the incomplete entries "
            "listed under Completion.")


def _completion_section(result: dict[str, Any], names: list[str], labels: dict[str, str]) -> list[str]:
    comp = result.get("completion") or {}
    if not comp:
        return []
    lines = ["| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |", "|---|---|---|---|"]
    for n in names:
        c = comp.get(n) or {"complete": [], "incomplete": {}, "no_draft": []}
        inc = ", ".join(f"{e} ({len(p)} paper{'s' if len(p) != 1 else ''})" for e, p in c["incomplete"].items())
        lines.append(f"| {labels[n]} | {len(c['complete'])} | {len(c['incomplete'])}{': ' + inc if inc else ''} | "
                     f"{len(c['no_draft'])}{': ' + ', '.join(c['no_draft']) if c['no_draft'] else ''} |")
    fallback = sorted({e for n in names for e, src in ((comp.get(n) or {}).get("incomplete_source") or {}).items()
                       if src and "cohort" in src and n != "cohort"})
    text = ["## Completion",
            f"An entry is compared only when every strategy below completed it in full: its draft exists and no "
            f"per-paper call was lost. {result['n_entries']} of the run's {result.get('n_entries_in_run', result['n_entries'])} "
            f"entries qualify; left out: {', '.join(result.get('left_out') or []) or 'none'}. One-call strategies "
            "cannot be incomplete: a failed call there leaves no draft.", "\n".join(lines)]
    if fallback:
        text.append("For the reconciled case database the failed papers are read from the case table's record of the "
                    "same entry (both run the same cached case extraction; drafts written before the reconciled "
                    f"strategy recorded them itself): {', '.join(fallback)}.")
    return text


def strategies_markdown(result: dict[str, Any]) -> str:
    names = [s["name"] for s in result["strategies"]]
    labels = {s["name"]: s["label"] for s in result["strategies"]}
    n_all = result["n_entries"]
    head = "| " + " | ".join(["Metric", *[labels[n] for n in names]]) + " |\n|" + "---|" * (len(names) + 1)

    def means_table(rows: list[dict[str, Any]], as_pct: bool = True, n_total: int = n_all) -> str:
        lines = [head]
        for r in rows:
            arrow = {True: " ↑", False: " ↓", None: ""}[r.get("higher_is_better")]
            mark = " (primary endpoint)" if r["metric"] == PRIMARY else ""
            cells = []
            for n in names:
                v = r["values"].get(n)
                cell = _pct(v) if as_pct else ("–" if v is None else f"{v:.1f}")
                cells.append(cell + (_n_note((r.get("n") or {}).get(n), n_total) if v is not None else ""))
            lines.append(f"| {r['label']}{mark}{arrow} | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    empty_counts = {n: (result["pooled"].get(n) or {}).get("empty_predictions") or {} for n in names}
    empty_text = "; ".join(f"{labels[n]}: " + ", ".join(f"{k} {v}" for k, v in c.items() if v)
                           for n, c in empty_counts.items() if any(c.values()))
    out = [f"# Generation strategies compared — run `{result['run']}`",
           f"{n_all} entries, each written in full by every strategy from the same papers and put through the same "
           "audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. "
           f"The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.",
           *([_stopped_note(result)] if result.get("stopped") else []),
           *_completion_section(result, names, labels),
           "## How the scores are counted",
           "- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis "
           "term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the "
           "entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, "
           "for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected"
           + (f": {empty_text}." if empty_text else ": none."),
           f"- **n.** A value rests on all {n_all} entries unless marked (n=k): some measures are undefined for some "
           "entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).",
           "- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants "
           "for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside "
           "the entry's reference list counts as unmatched here and is shown apart below.",
           "- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode "
           "missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).",
           "## The strategies",
           "\n".join(f"- **{s['label']}** (`{s['name']}`): {s['summary']}" for s in result["strategies"]),
           "## Scores", means_table(result["means"]),
           "## How much each strategy writes", means_table(result["volume"], as_pct=False)]

    base_name = result["baseline"]
    base = labels[base_name]
    out.append(f"## Paired differences from the baseline ({base})")
    out.append("Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number "
               "of entries on which the strategy scored better / worse / the same. The full statistics for every "
               "measure follow per strategy.")
    wanted = [m for m in METRICS if m[0] in HEADLINE]
    lines = ["| Metric | " + " | ".join(labels[n] for n in names if n != base_name) + " |",
             "|" + "---|" * len(names)]
    for key, label, _, higher in wanted:
        cells = []
        for n in names:
            if n == base_name:
                continue
            row = next((r for r in result["versus_baseline"][n] if r["metric"] == key), None)
            if row is None:
                cells.append("–")
                continue
            ci = f" ({_pp(row['ci95'][0])} to {_pp(row['ci95'][1])})" if row["ci95"] else ""
            cells.append(f"{_pp(row['difference'])}{ci}; {row['better']}/{row['worse']}/{row['ties']}"
                         + _n_note(row["n"], n_all))
        mark = " (primary)" if key == PRIMARY else ""
        lines.append(f"| {label}{mark} {'↑' if higher else '↓'} | " + " | ".join(cells) + " |")
    out.append("\n".join(lines))
    if 0 < n_all < SMALL_N:
        out.append(_unreliable_note(n_all))

    out.append("### Full paired statistics")
    out.append("Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the "
               "exact two-sided sign test (ties dropped) and, for the headline measures other than the primary "
               "endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. "
               "OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are "
               "descriptive.")
    for n in names:
        if n == base_name:
            continue
        rows = result["versus_baseline"].get(n) or []
        if not rows:
            continue
        out.append(f"#### {labels[n]} minus {base}")
        lines = ["| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | "
                 "Sign test p | Holm p |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: (not r.get("primary"), not r.get("headline"))):
            label = FULL_LABELS.get(r["metric"], r["label"])
            ci = f"{_pp(r['ci95'][0])} to {_pp(r['ci95'][1])}" if r["ci95"] else "–"
            mark = " **(primary)**" if r.get("primary") else (" (headline)" if r.get("headline") else "")
            lines.append(f"| {label}{mark} {'↑' if r['higher_is_better'] else '↓'} | {r['n']} | {_pct(r['strategy'])} | "
                         f"{_pct(r['baseline'])} | {_pp(r['difference'])} | {ci} | {_pp(r.get('median_difference'))} | "
                         f"{r['better']} / {r['worse']} / {r['ties']} | {_p(r['sign_test_p'])} | "
                         f"{_p(r.get('sign_test_p_holm')) if 'sign_test_p_holm' in r else '–'} |")
        out.append("\n".join(lines))

    itt = result.get("intention_to_treat")
    if itt:
        out.append("## Sensitivity: every entry, a missing draft counted as zero (intention to treat)")
        zf = "; ".join(f"{labels[n]} {itt['missing_drafts_counted_as_zero'].get(n, 0)}" for n in names
                       if itt["missing_drafts_counted_as_zero"].get(n))
        out.append(f"All {itt['n_entries']} entries of the run. A strategy's missing draft scores 0 on each "
                   "higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. "
                   "Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged "
                   "over the drafts that exist. Missing drafts counted as zero: " + (zf or "none") + ".")
        out.append(means_table(itt["means"], n_total=itt["n_entries"]))
        lines = ["| Metric | " + " | ".join(labels[n] for n in names if n != base_name) + " |",
                 "|" + "---|" * len(names)]
        for key, label, _, higher in wanted:
            cells = []
            for n in names:
                if n == base_name:
                    continue
                row = next((r for r in itt["versus_baseline"].get(n, []) if r["metric"] == key), None)
                if row is None:
                    cells.append("–")
                    continue
                ci = f" ({_pp(row['ci95'][0])} to {_pp(row['ci95'][1])})" if row["ci95"] else ""
                cells.append(f"{_pp(row['difference'])}{ci}; median {_pp(row['median_difference'])}; "
                             f"{row['better']}/{row['worse']}/{row['ties']}; p {_p(row['sign_test_p'])}"
                             + _n_note(row["n"], itt["n_entries"]))
            mark = " (primary)" if key == PRIMARY else ""
            lines.append(f"| {label}{mark} {'↑' if higher else '↓'} | " + " | ".join(cells) + " |")
        out.append(f"Paired differences from {base} over all entries (mean, interval, median, better/worse/tie, sign test):")
        out.append("\n".join(lines))

    out.append("## Pooled counts")
    lines = ["| | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
    for label, group, key in (("Claims audited", "claims", "n"), ("… supported", "claims", "supported"),
                              ("… partly supported", "claims", "partially_supported"),
                              ("… unsupported", "claims", "unsupported"), ("… contradicted", "claims", "contradicted"),
                              ("Claims audited before repair", "claims_before_repair", "n_claims"),
                              ("… unsupported before repair", "claims_before_repair", "unsupported"),
                              ("… contradicted before repair", "claims_before_repair", "contradicted"),
                              ("OMIM facts scored", "gold_facts", "n_facts"), ("… conveyed", "gold_facts", "present"),
                              ("… partly conveyed", "gold_facts", "partial"), ("… missing", "gold_facts", "absent"),
                              ("… contradicted", "gold_facts", "contradicted")):
        lines.append(f"| {label} | " + " | ".join(f"{(result['pooled'][n].get(group) or {}).get(key, 0):,}" for n in names) + " |")
    out.append("\n".join(lines))

    out.append("## Allelic variants: precision and variants not in OMIM")
    lines = ["| | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
    for label, key, fmt in (("Variants generated", "generated", "{:,}"), ("… matching an OMIM variant of the entry", "matched", "{:,}"),
                            ("… listed by OMIM only from a paper outside the entry's references", "in_omim_via_other_paper", "{:,}"),
                            ("… not in OMIM", "not_in_omim", "{:,}"),
                            ("Pooled precision (entries where OMIM lists variants)", "precision", None)):
        cells = []
        for n in names:
            v = (result["pooled"][n].get("variants") or {}).get(key)
            cells.append(_pct(v) if fmt is None else fmt.format(v or 0))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    out.append("\n".join(lines))

    out.append("## Inheritance errors by kind")
    lines = ["| | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
    for label, key in (("Entries with an OMIM mode of inheritance", "scored"), ("… matched", "match"),
                       ("… none stated", "none_stated"), ("… a mode missing", "mode_missing"),
                       ("… an extra mode", "extra_mode"), ("… a different mode", "different_mode")):
        lines.append(f"| {label} | " + " | ".join(str((result["pooled"][n].get("inheritance") or {}).get(key, 0))
                                                  for n in names) + " |")
    out.append("\n".join(lines))

    if result["by_content_level"]:
        out.append("## OMIM-fact coverage by how much of the paper was readable")
        out.append("Pooled over facts. Each cell: coverage, then the number of facts scored.")
        lines = ["| Paper readable as | " + " | ".join(labels[n] for n in names) + " |", "|" + "---|" * (len(names) + 1)]
        for level in LEVEL_ORDER:
            cells = result["by_content_level"].get(level)
            if cells:
                lines.append(f"| {level} | " + " | ".join(
                    f"{_pct((cells.get(n) or {}).get('coverage'))} ({(cells.get(n) or {}).get('n_facts', 0):,})" for n in names) + " |")
        out.append("\n".join(lines))
        diff = result.get("by_content_level_vs_baseline") or {}
        if diff:
            out.append(f"### Difference from {base}, by how the paper was readable")
            out.append("Coverage pooled over the facts of all papers at that level, strategy minus baseline in "
                       "percentage points, with a 95% interval from resampling entries (all of an entry's facts move "
                       "together); n is the number of entries with facts at that level for both strategies. Facts "
                       "are split from the gold paragraph separately for each draft, so the fact counts differ slightly.")
            lines = ["| Paper readable as | " + " | ".join(labels[n] for n in names if n != base_name) + " |",
                     "|" + "---|" * len(names)]
            for level in LEVEL_ORDER:
                row = diff.get(level)
                if not row:
                    continue
                cells = []
                for n in names:
                    if n == base_name:
                        continue
                    c = row.get(n) or {}
                    ci = f" ({_pp(c['ci95'][0])} to {_pp(c['ci95'][1])})" if c.get("ci95") else ""
                    flag = " †" if c.get("ci_unreliable") and c.get("ci95") else ""
                    cells.append(f"{_pp(c.get('difference'))}{ci}{flag}; n={c.get('n_entries', 0)}")
                lines.append(f"| {level} | " + " | ".join(cells) + " |")
            out.append("\n".join(lines))
            if any((c or {}).get("ci_unreliable") and (c or {}).get("ci95") for row in diff.values() for c in row.values()
                   if isinstance(c, dict)):
                out.append(f"† fewer than {SMALL_N} entries: the interval is unreliable.")

    paired = result.get("by_access_paired") or {}
    if paired:
        out.append(f"## Paired differences from {base} within each access stratum")
        out.append("Entries grouped by the share of their references readable as full text (as in the breakdown "
                   "below); within each group, the paired difference from the baseline in percentage points with its "
                   f"bootstrap 95% interval and the number of entries. † fewer than {SMALL_N} entries: the interval "
                   "is unreliable; no interval is computed below 5 entries.")
        for key, label in (("gold_fact_coverage", "OMIM facts conveyed"), ("variant_recall", "OMIM allelic variants recovered")):
            out.append(f"### {label}")
            lines = ["| Access group | Entries | " + " | ".join(labels[n] for n in names if n != base_name) + " |",
                     "|" + "---|" * (len(names) + 1)]
            for group, block in paired.items():
                cells = []
                for n in names:
                    if n == base_name:
                        continue
                    r = next((x for x in block["versus_baseline"].get(n, []) if x["metric"] == key), None)
                    if r is None:
                        cells.append("–")
                        continue
                    ci = f" ({_pp(r['ci95'][0])} to {_pp(r['ci95'][1])})" if r["ci95"] else ""
                    flag = " †" if r["ci_unreliable"] else ""
                    cells.append(f"{_pp(r['difference'])}{ci}{flag}; n={r['n']}")
                lines.append(f"| {group} | {block['n']} | " + " | ".join(cells) + " |")
            out.append("\n".join(lines))

    era = result.get("era_by_access") or {}
    if era:
        out.append("## OMIM facts conveyed by creation era within each level of paper access")
        out.append("Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the "
                   "MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.")
        eras = [e for e in STRATUM_ORDER if any(e in lv for s in era.values() for lv in s.values())]
        for s, by_level in era.items():
            out.append(f"### {labels.get(s, s)}")
            lines = ["| Paper readable as | " + " | ".join(eras) + " |", "|" + "---|" * (len(eras) + 1)]
            for level, cells in by_level.items():
                lines.append(f"| {level} | " + " | ".join(
                    (f"{_pct(cells[e]['coverage'])} ({cells[e]['n_facts']:,} facts, {cells[e]['n_entries']} "
                     f"entr{'y' if cells[e]['n_entries'] == 1 else 'ies'})"
                     if e in cells else "–") for e in eras) + " |")
            out.append("\n".join(lines))

    for title, key in (("## By share of the entry's references readable as full text", "by_access"),
                       ("## By size of the reference list", "by_reference_count"),
                       ("## By creation era (MIM number range)", "by_stratum")):
        out.append(title)
        for group, block in result[key].items():
            out.append(f"### {group} — {block['n']} entries")
            out.append(means_table(block["means"], n_total=block["n"]))

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
