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
    for strategy in ("kg", "direct"):
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
    names = {"kg": "Evidence graph", "direct": "Direct"}
    lines = ["## Knowledge-graph edges against OMIM (all entries pooled)",
             "Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the "
             "share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. "
             "A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.",
             "| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|"]
    for relation in EDGE_RELATIONS:
        for strategy in ("kg", "direct"):
            s = scores.get(strategy, {}).get(relation)
            if s:
                lines.append(f"| {labels[relation]} | {names[strategy]} | {s['in_both']:,} | {s['generated']:,} | {s['omim']:,} | "
                             f"{_pct(s['precision'])} | {_pct(s['recall'])} | {_pct(s['f1'])} |")
    return "\n\n".join(lines[:2]) + "\n\n" + "\n".join(lines[2:]) + "\n"
