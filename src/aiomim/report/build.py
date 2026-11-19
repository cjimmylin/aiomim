"""Collect a run directory into one self-contained HTML review page.

Small runs give one file: CSS, JavaScript and the run's data (as JSON in a
`<script type="application/json">` block) are all inlined, so it opens offline
and under a strict Content-Security-Policy. Large runs are split: the page keeps
only what the overview needs (scores and an index of entries) and each entry's
data goes into `report_data/<entry>.js`, which the page loads with a <script>
element when the entry is opened (this works from file://, where fetch() does
not). Paper full text is never embedded; only what the page shows is kept.

    build_report(run_dir)  ->  run_dir / "report.html"  [+ run_dir / "report_data/*.js"]
"""

from __future__ import annotations

import json
import logging
import re
from importlib import resources
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Per-entry files the page reads. Every one of them is optional.
ENTRY_FILES = ("seed.json", "gold.json", "retrieval.json", "papers.json", "extractions.json", "kg.json",
               "usage.json", "updates.json")
KG_ENTRY_RELATIONS = ("caused_by", "has_variant", "inheritance", "has_phenotype")
# Above this many bytes of entry data the page is split: report.html + report_data/<entry>.js.
SPLIT_THRESHOLD = 5_000_000
DATA_DIR = "report_data"
REGISTER = "__aiomimRegister"  # global the per-entry data files call; defined in app.js


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
         "n_paragraphs": len(av.get("paragraphs") or [])}
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
    """Graph statistics plus the entity nodes hanging off the entry node, with their papers.

    Variants also carry `gene_id`, from their `in_gene` edge, so the page can draw variant -> gene.
    """
    if not isinstance(raw, dict):
        return None
    nodes = {n.get("id"): n for n in raw.get("nodes") or [] if isinstance(n, dict)}
    in_gene: dict[str, str] = {}
    for e in raw.get("edges") or []:
        if isinstance(e, dict) and e.get("rel") == "in_gene":
            in_gene.setdefault(e.get("src", ""), e.get("dst", ""))
    entities = []
    for e in raw.get("edges") or []:
        if not isinstance(e, dict) or e.get("src") != "entry" or e.get("rel") not in KG_ENTRY_RELATIONS:
            continue
        dst = e.get("dst", "")
        node = nodes.get(dst, {})
        ent = {
            "rel": e["rel"], "id": dst, "label": node.get("label") or dst,
            **_pick(node, ("hpo_id", "gene", "omim_name")),
            "pmids": e.get("pmids") or ([e["pmid"]] if e.get("pmid") else []),
            **_pick(e, ("absent_in", "n_variants")),
        }
        if dst in in_gene:
            ent["gene_id"] = in_gene[dst]
        entities.append(ent)
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


def _slim_eval(raw: dict) -> dict:
    """The eval as written, minus the draft text the page recomputes from the entry (see `_draft_text_for`)."""
    ev = dict(raw)
    gt = ev.get("gold_text")
    if isinstance(gt, dict) and isinstance(gt.get("paragraphs"), list):
        ev["gold_text"] = {**gt, "paragraphs": [{k: v for k, v in p.items() if k != "draft"}
                                                for p in gt["paragraphs"] if isinstance(p, dict)]}
    return ev


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
            evals[s] = _slim_eval(raw)
    seed = _read_json(path / "seed.json")
    seed = seed if isinstance(seed, dict) else None
    gold = _slim_gold(_read_json(path / "gold.json"))
    updates = _read_json(path / "updates.json")
    title = (seed or {}).get("title") or (gold or {}).get("title")
    if not title:
        title = next((e.get("title") for e in entries.values() if e.get("title")), None) or path.name
    mim = (seed or {}).get("mim") or (gold or {}).get("mim") or next(
        (e.get("mim") for e in entries.values() if e.get("mim")), None)
    return {
        "dir": path.name,
        "mim": mim,
        "title": title,
        "seed": seed,
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


def _get(node: Any, path: str) -> Any:
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _row(item: dict, s: str) -> dict:
    """One score-table row (what the overview shows) for one strategy of one entry."""
    ev = item["evals"].get(s)
    en = item["entries"].get(s)
    aud = (ev or {}).get("faithfulness") or (en or {}).get("audit") or {}
    gt = (ev or {}).get("gold_text") or {}
    n_facts = gt.get("n_facts")
    return {
        "has_eval": ev is not None,
        "claim_supported_rate": aud.get("supported_rate"),
        "claim_error_rate": aud.get("error_rate"),
        "claims": aud.get("n_claims"),
        "gold_fact_coverage": gt.get("coverage") if ev else None,
        "gold_fact_contradicted": gt.get("contradicted") if ev and n_facts else None,
        "gold_facts": n_facts if ev else None,
        "hpo_exact_f1": _get(ev, "synopsis.exact.f1"),
        "hpo_hier_f1": _get(ev, "synopsis.hierarchical.f1"),
        "variant_recall": _get(ev, "variants.recall"),
        "gene_f1": _get(ev, "genes.f1"),
        "inheritance_match": _get(ev, "inheritance.match"),
        "ref_recall": _get(ev, "references.cited.recall"),
        "access": (ev or {}).get("gold_reference_access"),
    }


def _paragraph_ids(entry: dict) -> list[str]:
    """Same order and fallback ids as the page's `paragraphsOf` / `pidOf`."""
    paras = ([entry["intro"]] if entry.get("intro") else [])
    paras += [p for s in entry.get("sections") or [] for p in s.get("paragraphs") or []]
    paras += [p for av in entry.get("allelic_variants") or [] for p in av.get("paragraphs") or []]
    return [p.get("id") or f"p{i}" for i, p in enumerate(paras)]


def _index_row(item: dict, file: str) -> dict:
    """What the overview needs about an entry without loading the entry itself."""
    prefix = (item["gold"] or {}).get("prefix") or (item["seed"] or {}).get("prefix") or next(
        (e.get("prefix") for e in item["entries"].values() if e.get("prefix")), "")
    return {
        "dir": item["dir"], "file": file, "mim": item["mim"], "title": item["title"], "prefix": prefix,
        "strategies": item["strategies"],
        "has_gold": item["gold"] is not None,
        "has_updates": item["updates"] is not None,
        "n_proposals": len((item["updates"] or {}).get("proposals") or []),
        "pids": {s: _paragraph_ids(e) for s, e in item["entries"].items()},
        "rows": {s: _row(item, s) for s in item["strategies"]},
        "generated": sorted({e["meta"].get("generated") for e in item["entries"].values() if e["meta"].get("generated")}),
        "retrieval_mode": (item["retrieval"] or {}).get("mode"),
    }


def _payload(item: dict) -> dict:
    keep = ("seed", "gold", "retrieval", "papers", "extractions", "kg", "entries", "evals", "usage", "updates")
    return {k: item[k] for k in keep}


def _file_names(dirs: list[str]) -> list[str]:
    used: set[str] = set()
    out = []
    for d in dirs:
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", d).strip("-.") or "entry"
        name, n = base, 2
        while name.lower() in used:
            name = f"{base}-{n}"
            n += 1
        used.add(name.lower())
        out.append(name + ".js")
    return out


def collect_report_data(run_dir: Path) -> dict[str, Any]:
    """Run-level data plus `payloads` ({file name: one entry's payload}) for every entry."""
    run_dir = Path(run_dir)
    summary = _read_json(run_dir / "summary.json")
    if not isinstance(summary, dict):
        summary = None
    comparison = _read_json(run_dir / "comparison.json")
    items = [_collect_entry(p) for p in sorted(run_dir.iterdir()) if _is_entry_dir(p)]
    files = _file_names([i["dir"] for i in items])
    index = [_index_row(item, f) for item, f in zip(items, files)]
    config = (summary or {}).get("config") or {}
    strategies: list[str] = []
    for item in items:
        for s in item["strategies"]:
            if s not in strategies:
                strategies.append(s)
    retrieval = config.get("retrieval") or next((r["retrieval_mode"] for r in index if r["retrieval_mode"]), None)
    return {
        "format": 2,
        "run": (summary or {}).get("run") or run_dir.name,
        "retrieval": retrieval,
        "strategies": sorted(strategies, key=lambda s: (s != "kg", s != "direct", s)),
        "generated": sorted({d for r in index for d in r["generated"]}),
        "usage_total": (summary or {}).get("usage_total") or {},
        "failures": (summary or {}).get("failures") or {},
        "comparison": comparison if isinstance(comparison, dict) and comparison.get("overall") else None,
        "data_dir": DATA_DIR,
        "entries": index,
        "payloads": {f: _payload(item) for item, f in zip(items, files)},
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


def entry_script(file: str, payload: dict) -> str:
    """One entry's data file: a single call to the page's registration function."""
    return f"window.{REGISTER}({json_for_script(file)},{json_for_script(payload)});\n"


def build_report(run_dir: Path, out: str | None = None, split: bool | None = None) -> Path:
    """Write the review page for `run_dir` and return its path (default `run_dir/report.html`).

    split=None decides by size: one self-contained file while the embedded data stays under
    SPLIT_THRESHOLD bytes, otherwise `report.html` plus `report_data/<entry>.js`, loaded on demand.
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")
    path = Path(out) if out else run_dir / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = collect_report_data(run_dir)
    payloads = data.pop("payloads")
    scripts = {f: entry_script(f, p) for f, p in payloads.items()}
    if split is None:
        split = sum(len(s.encode("utf-8")) for s in scripts.values()) > SPLIT_THRESHOLD
    data["split"] = bool(split)
    if split:
        data_dir = path.parent / DATA_DIR
        data_dir.mkdir(exist_ok=True)
        for stale in data_dir.glob("*.js"):
            if stale.name not in scripts:
                stale.unlink()
        for f, text in scripts.items():
            (data_dir / f).write_text(text, encoding="utf-8")
    else:
        data["payloads"] = payloads
    path.write_text(render_html(data), encoding="utf-8")
    return path
