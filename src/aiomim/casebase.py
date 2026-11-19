"""The case database as a product: scoring it, exporting it, and checking reconciliation.

Three things, all over a finished run directory:

* frequency agreement: OMIM's HPO annotations (gold.json → hpo_annotations) carry a
  frequency such as "3/7" for many terms. For every HPO term that has such a
  fraction and is in a strategy's case table, the table's individuals present /
  assessed are compared with it: how often the denominators agree, how often the
  fractions agree (equal as fractions), how often both counts agree, and the mean
  absolute difference of the two proportions. Computed for `cohort` (cohort.json)
  and `reconciled` (casebase.json, after reconciliation), so the effect of
  reconciliation shows. Several fraction annotations of one term are summed.
* export: individuals.tsv, variants.tsv and phenotypes.tsv pooled over all entries,
  with a summary .json and .md, under <run>/casebase/.
* reconcile-check: plant a re-report (one paper's records copied under a made-up
  later paper that says it follows those patients up) and see whether the
  reconciliation merges each copy with its original, and whether merges among the
  original records change. An easy case: it shows the step catches an explicit,
  verbatim re-report, nothing more.
"""

from __future__ import annotations

import copy
import json
import logging
import random
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CORE = ("primary", "supporting")
_FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

# --------------------------------------------------------------------------- #
# Frequency agreement
# --------------------------------------------------------------------------- #


def gold_frequencies(gold: dict[str, Any]) -> dict[str, tuple[int, int]]:
    """HPO term -> (affected, assessed) from OMIM's phenotype annotations with an "n/m" frequency."""
    out: dict[str, tuple[int, int]] = {}
    for a in gold.get("hpo_annotations", []):
        if a.get("aspect", "P") != "P" or (a.get("qualifier") or "").upper() == "NOT":
            continue
        m = _FRACTION.match(a.get("frequency") or "")
        if not m or int(m.group(2)) == 0:
            continue
        n, d = out.get(a["hpo_id"], (0, 0))
        out[a["hpo_id"]] = (n + int(m.group(1)), d + int(m.group(2)))
    return out


def frequency_agreement(table: dict[str, dict[str, Any]], gold: dict[str, tuple[int, int]]) -> dict[str, Any]:
    """Compare a case table's per-term counts with OMIM's fractions, over the terms both have."""
    terms = []
    for hpo_id, (n, m) in sorted(gold.items()):
        row = table.get(hpo_id)
        if not row or not row.get("assessed"):
            continue
        p, a = int(row["present"]), int(row["assessed"])
        terms.append({"hpo_id": hpo_id, "label": row.get("label", ""), "table": f"{p}/{a}", "omim": f"{n}/{m}",
                      "denominator_agrees": a == m, "fraction_agrees": p * m == n * a,
                      "counts_agree": p == n and a == m, "abs_diff": round(abs(p / a - n / m), 4)})
    return _rates(terms, n_gold=len(gold), n_table=len(table))


def _rates(terms: list[dict[str, Any]], **extra: int) -> dict[str, Any]:
    k = len(terms)

    def rate(key: str):
        return round(sum(t[key] for t in terms) / k, 3) if k else None
    return {**extra, "n_compared": k, "denominator_agreement": rate("denominator_agrees"),
            "fraction_agreement": rate("fraction_agrees"), "count_agreement": rate("counts_agree"),
            "mean_abs_diff": round(sum(t["abs_diff"] for t in terms) / k, 4) if k else None, "terms": terms}


# --------------------------------------------------------------------------- #
# Reading a strategy's case table from an entry directory
# --------------------------------------------------------------------------- #


def load_table(entry_dir: Path, strategy: str) -> dict[str, Any] | None:
    """Units (individuals, families, groups), variants and per-term counts of one entry's case table."""
    if strategy == "reconciled":
        path = entry_dir / "casebase.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"units": data["units"], "variants": data["variants"], "phenotypes": data["phenotypes"]["after"],
                "phenotypes_before": data["phenotypes"]["before"], "totals": data["totals"]["after"],
                "totals_before": data["totals"]["before"]}
    path = entry_dir / "cohort.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    relevance = {p["pmid"]: p["relevance"] for p in data["papers"]}
    units = []
    for r in data["records"]:
        if relevance.get(r["pmid"]) not in CORE or r.get("followup_of"):
            continue
        size = 1 if r["kind"] == "individual" else max(1, r.get("n_affected") or 1)
        units.append({
            "id": r["id"], "kind": r["kind"], "label": r["label"], "n_affected": size,
            "n_families": r.get("n_families") or 1, "sex": r["sex"], "ancestry": r["ancestry"],
            "consanguinity": r["consanguinity"], "onset": r["onset"], "age_last": r["age_last"],
            "inheritance_stated": r["inheritance"], "genotype_mode": r.get("genotype_mode", ""),
            "sources": [r["id"]], "pmids": [r["pmid"]], "relations": [],
            "variants": [{"id": v.get("key", ""), "gene": v["gene"], "as_reported": v["as_reported"],
                          "zygosity": v["zygosity"], "origin": v["origin"]} for v in r["variants"]],
        })
    return {"units": units, "variants": data["variants"], "phenotypes": data["phenotypes"], "totals": data["totals"]}


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def _tsv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    def cell(v: Any) -> str:
        if isinstance(v, (list, tuple)):
            v = "; ".join(str(x) for x in v)
        elif isinstance(v, dict):
            v = "; ".join(f"{k}:{x}" for k, x in v.items())
        return re.sub(r"[\t\r\n]+", " ", "" if v is None else str(v))
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(columns) + "\n")
        for row in rows:
            fh.write("\t".join(cell(row.get(c)) for c in columns) + "\n")


def build_casebase(run_dir: Path, strategy: str = "reconciled") -> dict[str, Any]:
    """Per-entry frequency agreement for cohort and reconciled, and the pooled export of `strategy`."""
    out_dir = run_dir / "casebase"
    out_dir.mkdir(parents=True, exist_ok=True)
    individuals, variants, phenotypes, entries = [], [], [], []
    pooled_terms: dict[str, list[dict[str, Any]]] = {"cohort": [], "reconciled": [], "reconciled_before": []}

    for entry_dir in sorted(p for p in run_dir.iterdir() if p.is_dir() and (p / "gold.json").exists()):
        mim = entry_dir.name
        gold = json.loads((entry_dir / "gold.json").read_text(encoding="utf-8"))
        freq = gold_frequencies(gold)
        row: dict[str, Any] = {"mim": mim, "title": gold.get("title", ""), "gold_terms_with_frequency": len(freq)}
        for name in ("cohort", "reconciled"):
            table = load_table(entry_dir, name)
            if table is None:
                continue
            agreement = frequency_agreement(table["phenotypes"], freq)
            pooled_terms[name] += agreement["terms"]
            row[name] = {**{k: v for k, v in agreement.items() if k != "terms"},
                         "individuals": table["totals"]["individuals"], "families": table["totals"]["families"],
                         "units": len(table["units"])}
            if name == "reconciled":
                before = frequency_agreement(table["phenotypes_before"], freq)
                pooled_terms["reconciled_before"] += before["terms"]
                row["reconciled"]["before_reconciliation"] = {k: v for k, v in before.items() if k != "terms"}
                row["reconciled"]["individuals_before"] = table["totals_before"]["individuals"]
                row["reconciled"]["families_before"] = table["totals_before"]["families"]
        table = load_table(entry_dir, strategy)
        if table is None:
            continue
        entries.append(row)
        for u in table["units"]:
            individuals.append({"mim": mim, **u, "variants": [f"{v['id']} {v['gene']} {v['as_reported']} "
                                                             f"({v['zygosity']})" for v in u["variants"]]})
        for v in table["variants"]:
            variants.append({"mim": mim, **v})
        for hpo_id, p in table["phenotypes"].items():
            n_m = freq.get(hpo_id)
            phenotypes.append({"mim": mim, "hpo_id": hpo_id, **p, "n_papers": len(p.get("pmids", [])),
                               "omim_frequency": f"{n_m[0]}/{n_m[1]}" if n_m else ""})

    _tsv(out_dir / "individuals.tsv",
         ["mim", "id", "kind", "label", "n_affected", "n_families", "sex", "ancestry", "consanguinity", "onset",
          "age_last", "inheritance_stated", "genotype_mode", "variants", "sources", "pmids", "relations"], individuals)
    _tsv(out_dir / "variants.tsv",
         ["mim", "id", "gene", "keys", "omim_name", "as_reported", "individuals", "zygosity", "origin", "authors",
          "records", "pmids"], variants)
    _tsv(out_dir / "phenotypes.tsv",
         ["mim", "hpo_id", "label", "text", "present", "absent", "assessed", "n_papers", "omim_frequency",
          "lower_bound", "pmids"], phenotypes)
    pooled = {name: {k: v for k, v in _rates(terms).items() if k != "terms"}
              for name, terms in pooled_terms.items() if terms}
    summary = {"run": run_dir.name, "strategy": strategy, "entries": entries, "pooled_agreement": pooled,
               "totals": {"entries": len(entries), "units": len(individuals),
                          "individuals": sum(int(u.get("n_affected") or 0) for u in individuals),
                          "variants": len(variants), "phenotype_rows": len(phenotypes)}}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(summary_markdown(summary), encoding="utf-8")
    return summary


def summary_markdown(summary: dict[str, Any]) -> str:
    def fmt(a: dict[str, Any] | None) -> str:
        if not a or not a.get("n_compared"):
            return "–"
        return (f"{a['n_compared']} terms; denominators {a['denominator_agreement']:.0%}, fractions "
                f"{a['fraction_agreement']:.0%}, |Δ| {a['mean_abs_diff']:.2f}")
    lines = [f"# Case database: {summary['run']} ({summary['strategy']})", "",
             f"{summary['totals']['entries']} entries, {summary['totals']['units']} units "
             f"({summary['totals']['individuals']} affected individuals), {summary['totals']['variants']} variants.", "",
             "## Frequency agreement with OMIM's HPO annotation fractions (pooled over terms)", ""]
    for name, a in summary["pooled_agreement"].items():
        lines.append(f"- {name}: {fmt(a)}")
    lines += ["", "| MIM | title | OMIM fractions | cohort | reconciled | individuals cohort → reconciled |",
              "|---|---|---|---|---|---|"]
    for e in summary["entries"]:
        c, r = e.get("cohort"), e.get("reconciled")
        ind = f"{c['individuals'] if c else '–'} → {r['individuals'] if r else '–'}"
        lines.append(f"| {e['mim']} | {e['title'][:50]} | {e['gold_terms_with_frequency']} | {fmt(c)} | {fmt(r)} | {ind} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Planted re-reports
# --------------------------------------------------------------------------- #


def plant_rereport(papers: list, cases: list, source_pmid: str):
    """A made-up later paper that re-reports `source_pmid`'s patients, and its copied records."""
    from .models import Paper

    src = next(p for p in papers if p.pmid == source_pmid)
    src_cases = next(c for c in cases if c.pmid == source_pmid)
    year = max((p.year or 0) for p in papers) + 2
    fake = Paper(
        pmid=f"PLANT{source_pmid}", title=f"Follow-up of patients with {src.title[:80]}",
        authors=["Plantedauthor A", "Fictive B", "Madeup C"], year=year, journal="Planted Journal",
        abstract=(f"We report follow-up of the patients previously described by {src.label}. "
                  + (src.abstract or "")),
        fulltext=src.fulltext,
    )
    copied = src_cases.model_copy(deep=True)
    copied.pmid = fake.pmid
    pairs = []
    for n, rec in enumerate(copied.records, 1):
        orig = rec.id
        rec.id = f"R:{fake.pmid}:{n}"
        rec.pmid = fake.pmid
        rec.label = f"Case {chr(64 + n) if n <= 26 else n}"
        rec.family = f"Kindred {n}" if rec.family else ""
        rec.previously_reported = ""
        pairs.append((orig, rec.id))
    copied.notes, copied.dropped_records, copied.dropped_notes = [], [], []
    return fake, copied, pairs


def reconcile_check(run_dir: Path, n: int = 20, seed: int = 1, llm=None) -> dict[str, Any]:
    from .llm import LLM
    from .models import Seed
    from .sources.fulltext import load_papers
    from .strategies.cohort import extract_cases, ground_case_phenotypes
    from .strategies.reconciled import reconcile

    llm = llm or LLM()
    rng = random.Random(seed)
    candidates = []
    for entry_dir in sorted(p for p in run_dir.iterdir() if (p / "casebase.json").exists()):
        data = json.loads((entry_dir / "casebase.json").read_text(encoding="utf-8"))
        if len({r["pmid"] for r in data["records"]}) >= 2:
            candidates.append(entry_dir)
    chosen = rng.sample(candidates, min(n, len(candidates)))
    results = []
    for entry_dir in chosen:
        seed_ = Seed(**json.loads((entry_dir / "seed.json").read_text(encoding="utf-8")))
        pmids = [p["pmid"] for p in json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))]
        loaded = {p.pmid: p for p in load_papers(pmids, with_fulltext=True)}
        papers = [loaded[p] for p in pmids if p in loaded]
        cases = extract_cases(seed_, papers, llm)          # cache hits: the prompts of the run
        ground_case_phenotypes(cases, llm)
        with_records = [c.pmid for c in cases if c.records and c.relevance in CORE]
        if not with_records:
            continue
        source = rng.choice(with_records)
        fake, copied, pairs = plant_rereport(papers, cases, source)
        table, rlog = reconcile(seed_, {p.pmid: p for p in papers + [fake]}, copy.deepcopy(cases) + [copied], llm)

        merged_pairs = [(o, c) for o, c in pairs if o in table.absorbed and table.absorbed.get(c) == table.absorbed[o]]
        wrong = [c for o, c in pairs if c in table.absorbed and table.absorbed[c] != table.absorbed.get(o)]
        original_ids = {r["id"] for r in json.loads((entry_dir / "casebase.json").read_text())["records"]}
        before = {frozenset(ids) for ids in json.loads((entry_dir / "casebase.json").read_text())["log"]
                  .get("clusters", {}).values()}
        after = {frozenset(i for i in m.sources if i in original_ids) for m in table.merged.values()}
        after = {c for c in after if len(c) >= 2}
        results.append({
            "mim": entry_dir.name, "planted_from": source, "planted": len(pairs), "merged": len(merged_pairs),
            "wrong_merges_of_copies": wrong, "original_merges_in_run": sorted(sorted(c) for c in before),
            "original_merges_with_plant": sorted(sorted(c) for c in after),
            "original_merges_changed": before != after,
            "proposed": len(rlog["proposed"]), "rejected": rlog["rejected"],
        })
        log.info("[%s] planted %d, merged %d", entry_dir.name, len(pairs), len(merged_pairs))
    total = {"entries": len(results), "planted": sum(r["planted"] for r in results),
             "merged": sum(r["merged"] for r in results),
             "wrong_merges_of_copies": sum(len(r["wrong_merges_of_copies"]) for r in results),
             "entries_where_original_merges_changed": sum(r["original_merges_changed"] for r in results)}
    report = {"run": run_dir.name, "n": n, "seed": seed, "total": total, "entries": results,
              "usage": llm.usage.summary()["total"],
              "caveat": "A planted copy is an easy re-report: identical records and an explicit sentence naming "
                        "the earlier paper. Merging it shows only that the step finds a stated re-report."}
    out = run_dir / "casebase"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconcile_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [f"# Reconciliation check: {run_dir.name}", "", report["caveat"], "",
             f"Planted {total['planted']} records in {total['entries']} entries; merged with their original: "
             f"{total['merged']}; copies merged with the wrong record: {total['wrong_merges_of_copies']}; entries "
             f"whose merges among the original records changed: {total['entries_where_original_merges_changed']}.", "",
             "| MIM | planted from | planted | merged | original merges changed |", "|---|---|---|---|---|"]
    lines += [f"| {r['mim']} | {r['planted_from']} | {r['planted']} | {r['merged']} | {r['original_merges_changed']} |"
              for r in results]
    (out / "reconcile_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
