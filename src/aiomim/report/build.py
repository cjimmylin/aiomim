"""Collect a run directory into one self-contained HTML review page.

The page is a single file: CSS, JavaScript and the run's data (as JSON in a
`<script type="application/json">` block) are all inlined, so it opens offline
and under a strict Content-Security-Policy. Paper full text is never embedded;
only what the page shows is kept.

    build_report(run_dir)  ->  run_dir / "report.html"
"""

from __future__ import annotations

import json
import logging
from importlib import resources
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Per-entry files the page reads. Every one of them is optional.
ENTRY_FILES = ("seed.json", "gold.json", "retrieval.json", "papers.json", "extractions.json", "kg.json",
               "usage.json", "updates.json")
KG_ENTRY_RELATIONS = ("caused_by", "has_variant", "inheritance", "has_phenotype")


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("report: could not read %s: %s", path, exc)
        return None


def _is_entry_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any((path / name).is_file() for name in ENTRY_FILES) or any(path.glob("entry.*.json"))


def _strategies_in(path: Path, prefix: str) -> list[str]:
    """Strategy names from files like `entry.kg.json` / `eval.direct.json`."""
    out = []
    for f in sorted(path.glob(f"{prefix}.*.json")):
        parts = f.name.split(".")
        if len(parts) == 3:
            out.append(parts[1])
    # Evidence graph first: it is the main method, the direct draft is the baseline.
    return sorted(out, key=lambda s: (s != "kg", s != "direct", s))


# --------------------------------------------------------------------------- #
# Slimming: keep what the page shows, nothing else
# --------------------------------------------------------------------------- #


def _pick(d: dict | None, keys: tuple[str, ...]) -> dict:
    if not isinstance(d, dict):
        return {}
    return {k: d[k] for k in keys if k in d and d[k] not in (None, "", [], {})}


def _paragraph_status(raw: dict) -> str:
    """Same rule as `EntryParagraph.status` (a computed property, absent from the JSON)."""
    try:
        from ..models import EntryParagraph

        return EntryParagraph.model_validate(raw).status
    except Exception:  # noqa: BLE001 - a malformed paragraph is shown as not audited
        return "unverified"


def _slim_paragraph(raw: dict) -> dict:
    return {
        "id": raw.get("id", ""),
        "text": raw.get("text", ""),
        "pmids": raw.get("pmids") or [],
        "finding_ids": raw.get("finding_ids") or [],
        "checks": [_pick(c, ("claim", "pmid", "verdict", "evidence_quote", "explanation"))
                   for c in raw.get("checks") or []],
        "status": _paragraph_status(raw),
    }


def _slim_entry(raw: dict) -> dict:
    meta = dict(raw.get("meta") or {})
    # Long internal lists become counts.
    for key in ("dropped_ungrounded", "truncated_papers"):
        if isinstance(meta.get(key), list):
            meta[key + "_count"] = len(meta.pop(key))
    out = _pick(raw, ("mim", "prefix", "entry_type", "title", "alt_titles", "symbol", "inheritance"))
    out["relationships"] = [
        _pick(r, ("phenotype", "phenotype_mim", "gene_symbol", "gene_mim", "location", "inheritance",
                  "mapping_key", "pmids"))
        for r in raw.get("relationships") or []
    ]
    out["intro"] = _slim_paragraph(raw["intro"]) if raw.get("intro") else None
    out["sections"] = [
        {"name": s.get("name", ""), "heading": s.get("heading", ""),
         "paragraphs": [_slim_paragraph(p) for p in s.get("paragraphs") or []]}
        for s in raw.get("sections") or []
    ]
    out["clinical_synopsis"] = [
        _pick(i, ("category", "feature", "hpo_id", "hpo_label", "pmids", "n_papers"))
        for i in raw.get("clinical_synopsis") or []
    ]
    out["allelic_variants"] = [
        {**_pick(av, ("number", "gene_symbol", "name", "hgvs", "phenotype")),
         "paragraphs": [_slim_paragraph(p) for p in av.get("paragraphs") or []]}
        for av in raw.get("allelic_variants") or []
    ]
    out["references"] = [_pick(r, ("pmid", "label", "citation", "content_level")) for r in raw.get("references") or []]
    out["meta"] = meta
    out["audit"] = _audit(raw)
    return out


def _audit(raw: dict) -> dict | None:
    """Claim-level audit tally (needs no gold), recomputed so entries without an eval have it too."""
    try:
        from ..evaluate import eval_faithfulness
        from ..models import GeneratedEntry

        return eval_faithfulness(GeneratedEntry.model_validate(raw))
    except Exception as exc:  # noqa: BLE001
        log.warning("report: could not tally audit: %s", exc)
        return None


def _slim_gold(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    out = _pick(raw, ("mim", "prefix", "entry_type", "title", "alt_titles", "symbol", "cited_pmids", "inheritance",
                      "definition", "definition_source", "omim_text"))
    out["genes"] = [_pick(g, ("symbol", "mim", "location")) for g in raw.get("genes") or []]
    out["hpo_annotations"] = [_pick(a, ("hpo_id", "label", "aspect", "qualifier", "frequency", "onset"))
                              for a in raw.get("hpo_annotations") or []]
    out["allelic_variants"] = [
        {**_pick(av, ("omim_id", "gene_symbol", "name", "clinvar_name", "protein_change", "phenotypes")),
         "paragraphs": [_pick(p, ("text", "pmids", "mims")) for p in av.get("paragraphs") or []]}
        for av in raw.get("allelic_variants") or []
    ]
    return out


def _slim_papers(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    return [_pick(p, ("pmid", "pmcid", "label", "title", "year", "journal", "reference", "content_level",
                      "pub_types")) for p in raw if isinstance(p, dict)]


def _slim_extractions(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out = []
    for ex in raw:
        if not isinstance(ex, dict):
            continue
        out.append({
            **_pick(ex, ("pmid", "relevance", "relevance_reason", "study_types", "content_level", "error")),
            "findings": [_pick(f, ("id", "pmid", "section", "statement", "quotes", "quote_grounding"))
                         for f in ex.get("findings") or []],
            "n_dropped": len(ex.get("dropped_findings") or []),
        })
    return out


def _slim_kg(raw: Any) -> dict | None:
    """Graph statistics plus the entity nodes hanging off the entry node, with their papers."""
    if not isinstance(raw, dict):
        return None
    nodes = {n.get("id"): n for n in raw.get("nodes") or [] if isinstance(n, dict)}
    entities = []
    for e in raw.get("edges") or []:
        if not isinstance(e, dict) or e.get("src") != "entry" or e.get("rel") not in KG_ENTRY_RELATIONS:
            continue
        node = nodes.get(e.get("dst"), {})
        entities.append({
            "rel": e["rel"], "id": e.get("dst", ""), "label": node.get("label") or e.get("dst", ""),
            **_pick(node, ("hpo_id", "gene", "omim_name", "keys")),
            "pmids": e.get("pmids") or ([e["pmid"]] if e.get("pmid") else []),
            **_pick(e, ("absent_in", "n_variants")),
        })
    return {"stats": raw.get("stats") or {}, "entities": entities}


def _slim_usage(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return _pick(raw, ("total", "wall_seconds"))


def _slim_retrieval(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return _pick(raw, ("mode", "missing", "queries"))


# --------------------------------------------------------------------------- #
# Collecting
# --------------------------------------------------------------------------- #


def _collect_entry(path: Path) -> dict:
    entries = {}
    for s in _strategies_in(path, "entry"):
        raw = _read_json(path / f"entry.{s}.json")
        if isinstance(raw, dict):
            entries[s] = _slim_entry(raw)
    evals = {}
    for s in _strategies_in(path, "eval"):
        raw = _read_json(path / f"eval.{s}.json")
        if isinstance(raw, dict):
            evals[s] = raw
    seed = _read_json(path / "seed.json")
    gold = _slim_gold(_read_json(path / "gold.json"))
    updates = _read_json(path / "updates.json")
    title = ((seed or {}).get("title") if isinstance(seed, dict) else None) or (gold or {}).get("title")
    if not title:
        title = next((e.get("title") for e in entries.values() if e.get("title")), None) or path.name
    mim = (seed or {}).get("mim") if isinstance(seed, dict) else None
    mim = mim or (gold or {}).get("mim") or next((e.get("mim") for e in entries.values() if e.get("mim")), None)
    return {
        "dir": path.name,
        "mim": mim,
        "title": title,
        "seed": seed if isinstance(seed, dict) else None,
        "gold": gold,
        "retrieval": _slim_retrieval(_read_json(path / "retrieval.json")),
        "papers": _slim_papers(_read_json(path / "papers.json")),
        "extractions": _slim_extractions(_read_json(path / "extractions.json")),
        "kg": _slim_kg(_read_json(path / "kg.json")),
        "strategies": list(entries) or list(evals),
        "entries": entries,
        "evals": evals,
        "usage": _slim_usage(_read_json(path / "usage.json")),
        "updates": updates if isinstance(updates, dict) else None,
    }


def collect_report_data(run_dir: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    summary = _read_json(run_dir / "summary.json")
    if not isinstance(summary, dict):
        summary = None
    entries = [_collect_entry(p) for p in sorted(run_dir.iterdir()) if _is_entry_dir(p)]
    generated = sorted({e["meta"].get("generated") for item in entries for e in item["entries"].values()
                        if e["meta"].get("generated")})
    config = (summary or {}).get("config") or {}
    strategies: list[str] = []
    for item in entries:
        for s in item["strategies"]:
            if s not in strategies:
                strategies.append(s)
    retrieval = config.get("retrieval") or next(
        (item["retrieval"]["mode"] for item in entries if item.get("retrieval") and item["retrieval"].get("mode")), None)
    return {
        "format": 1,
        "run": (summary or {}).get("run") or run_dir.name,
        "retrieval": retrieval,
        "strategies": sorted(strategies, key=lambda s: (s != "kg", s != "direct", s)),
        "generated": generated,
        "usage_total": (summary or {}).get("usage_total") or {},
        "failures": (summary or {}).get("failures") or {},
        "summary_strategies": (summary or {}).get("strategies") or {},
        "entries": entries,
    }


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def json_for_script(data: Any) -> str:
    """JSON that is safe inside a <script> element: no `</script>`, `<!--` or line separators survive."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _asset(name: str) -> str:
    return resources.files(__package__).joinpath(name).read_text(encoding="utf-8")


def render_html(data: dict[str, Any]) -> str:
    template, style, app = _asset("template.html"), _asset("style.css"), _asset("app.js")
    for name, text in (("style.css", style), ("app.js", app)):
        if "</" + "style" in text.lower() or "</" + "script" in text.lower():
            raise ValueError(f"report asset {name} must not contain a closing tag")
    # Data goes in last, so nothing in it can be mistaken for a placeholder.
    html = template.replace("/*@STYLE@*/", style, 1).replace("/*@APP@*/", app, 1)
    return html.replace("@DATA@", json_for_script(data), 1)


def build_report(run_dir: Path, out: str | None = None) -> Path:
    """Write the review page for `run_dir` and return its path (default `run_dir/report.html`)."""
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")
    path = Path(out) if out else run_dir / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(collect_report_data(run_dir)), encoding="utf-8")
    return path
