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

import base64
import gzip
import json
import logging
import re
from importlib import resources
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Per-entry files the page reads. Every one of them is optional.
ENTRY_FILES = ("seed.json", "gold.json", "retrieval.json", "papers.json", "extractions.json", "kg.json",
               "usage.json", "updates.json", "cohort.json", "recall.memory_audit.json")
KG_ENTRY_RELATIONS = ("caused_by", "has_variant", "inheritance", "has_phenotype")
# Above this many bytes of entry data the page is split: report.html + report_data/<entry>.js.
SPLIT_THRESHOLD = 5_000_000
# A single-file page with more entry data than this embeds each entry gzip-compressed (base64) and
# unpacks it in the browser when the entry is opened. Smaller pages keep plain, readable JSON.
PACK_THRESHOLD = 2_000_000
DATA_DIR = "report_data"
REGISTER = "__aiomimRegister"  # global the per-entry data files call; defined in app.js
# Order used when the strategy registry cannot be imported (the page is also built from exported results).
FALLBACK_ORDER = ("kg", "direct", "agent", "closedbook", "recall", "cohort")
# Caps on what is embedded from a strategy's working files.
COHORT_CAP_BYTES = 60_000      # the case table of one entry (cohort.json), after slimming
COHORT_MAX_PHENOTYPES = 80
MEMORY_CLAIMS_CAP = 40         # memory claims listed from recall.memory_audit.json
_CONTROL = re.compile(r"\bcontrol\b", re.I)


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


def _registry() -> dict[str, Any]:
    """The pipeline's strategy registry, or {} when it cannot be imported."""
    try:
        from ..strategies import STRATEGIES

        return dict(STRATEGIES)
    except Exception:  # noqa: BLE001 - the page must build from results alone
        return {}


def strategy_order(names) -> list[str]:
    """Registry order first (so every page lists strategies the same way), then anything else by name."""
    known = list(_registry()) or list(FALLBACK_ORDER)
    names = list(dict.fromkeys(names))
    return [n for n in known if n in names] + sorted(n for n in names if n not in known)


def _strategies_in(path: Path, prefix: str) -> list[str]:
    """Strategy names from files like `entry.kg.json` / `eval.direct.json`."""
    out = []
    for f in sorted(path.glob(f"{prefix}.*.json")):
        parts = f.name.split(".")
        if len(parts) == 3:
            out.append(parts[1])
    return strategy_order(out)


def strategy_info(names: list[str], listed: list[dict] | None = None) -> list[dict]:
    """Label, one-line summary and control flag for each strategy, in display order.

    `listed` is `strategies[]` from strategies.json (written by `aiomim compare`) and wins;
    the registry fills in what it lacks; an unknown strategy is shown under its own name.
    A strategy is a control when the data says so (`control`), or, failing that, when its
    label or summary calls it one.
    """
    listed_by = {s["name"]: s for s in listed or [] if isinstance(s, dict) and s.get("name")}
    registry = _registry()
    out = []
    for name in strategy_order([*listed_by, *names]):
        row, spec = listed_by.get(name) or {}, registry.get(name)
        label = row.get("label") or getattr(spec, "label", None) or name
        summary = row.get("summary") or getattr(spec, "summary", None) or ""
        control = row.get("control", getattr(spec, "control", None))
        if control is None:
            control = bool(_CONTROL.search(f"{label} {summary}"))
        out.append({"name": name, "label": label, "summary": summary, "control": bool(control)})
    return out


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
        # Papers the audit checked the paragraph against without it citing them (memory drafts).
        **({"audit_pmids": raw["audit_pmids"]} if raw.get("audit_pmids") else {}),
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
        _pick(i, ("category", "feature", "hpo_id", "hpo_label", "pmids", "n_papers", "n_present", "n_assessed"))
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


PHASES = ("generate", "audit", "score")


def _slim_usage(raw: Any) -> dict | None:
    """Totals, plus what each strategy cost for this entry by phase (generation, audit, scoring).

    Phases follow `compare.usage_by_strategy`: a stage is named "<phase>/<step>", and the
    `full_*` tallies count a call whether or not the last pass took it from cache.
    """
    if not isinstance(raw, dict):
        return None
    out = _pick(raw, ("total", "wall_seconds"))
    by_strategy = {}
    for strategy, stages in (raw.get("by_strategy") or {}).items():
        if not isinstance(stages, dict):
            continue
        phases = {ph: {"calls": 0, "turns": 0, "usd": 0.0, "seconds": 0.0} for ph in PHASES}
        for stage, tally in stages.items():
            if stage == "total" or not isinstance(tally, dict):
                continue
            phase = stage.split("/", 1)[0] if "/" in stage else "generate"
            b = phases[phase if phase in PHASES else "generate"]
            b["calls"] += tally.get("calls", 0) or 0
            b["turns"] += tally.get("turns", 0) or 0
            b["usd"] += tally.get("full_list_price_usd", tally.get("list_price_usd", 0.0)) or 0.0
            b["seconds"] += tally.get("full_seconds", tally.get("seconds", 0.0)) or 0.0
        by_strategy[strategy] = {ph: {"calls": b["calls"], "turns": b["turns"], "usd": round(b["usd"], 3),
                                      "seconds": round(b["seconds"], 1)} for ph, b in phases.items()}
    if by_strategy:
        out["by_strategy"] = by_strategy
    return out


def _slim_retrieval(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return _pick(raw, ("mode", "missing", "queries"))


def _size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _slim_cohort(raw: Any, cap: int = COHORT_CAP_BYTES) -> dict | None:
    """The case table behind a "case table first" draft (cohort.json), cut down to what the page shows.

    Kept in full when small. Above `cap` bytes it is reduced in steps, and `trimmed` says how:
    per-record feature lists become counts, then each record and note keeps one quote, then the
    record and note lists are cut short (the frequency tables are computed from all of them and stay).
    """
    if not isinstance(raw, dict):
        return None
    phenotypes = [
        {"hpo_id": hpo_id, **_pick(row, ("label", "present", "absent", "assessed", "lower_bound", "from_follow_up", "pmids")),
         "n_records": len(row.get("records") or [])}
        for hpo_id, row in (raw.get("phenotypes") or {}).items() if isinstance(row, dict)
    ]
    phenotypes.sort(key=lambda r: (-(r.get("present") or 0), r.get("label") or ""))
    n_phenotypes = len(phenotypes)
    variants = [
        {**_pick(v, ("id", "gene", "keys", "omim_name", "individuals", "zygosity", "origin", "consequence", "authors", "pmids")),
         "n_records": len(v.get("records") or [])}
        for v in raw.get("variants") or [] if isinstance(v, dict)
    ]
    records = []
    for r in raw.get("records") or []:
        if not isinstance(r, dict):
            continue
        records.append({
            **_pick(r, ("id", "pmid", "label", "kind", "family", "n_affected", "n_families", "sex", "ancestry",
                        "consanguinity", "onset", "age_last", "segregation", "inheritance", "previously_reported",
                        "mixed_genotypes", "followup_of", "genotype_mode", "genotype_reason", "quotes", "quote_grounding")),
            "phenotypes": [_pick(ph, ("text", "hpo_label", "hpo_id", "present", "n_with", "n_assessed", "some_only", "other_cause"))
                           for ph in r.get("phenotypes") or [] if isinstance(ph, dict)],
            "variants": [_pick(v, ("gene", "as_reported", "zygosity", "origin", "key")) for v in r.get("variants") or []
                         if isinstance(v, dict)],
            **({"variant_roles": r["variant_roles"]} if r.get("variant_roles") else {}),
        })
    notes = [_pick(n, ("id", "pmid", "section", "statement", "inheritance", "quotes", "quote_grounding"))
             for n in raw.get("notes") or [] if isinstance(n, dict)]
    dropped = raw.get("dropped") or {}
    out: dict[str, Any] = {
        "totals": raw.get("totals") or {},
        "papers": [_pick(p, ("pmid", "relevance", "records", "notes", "dropped_records", "dropped_notes", "error"))
                   for p in raw.get("papers") or [] if isinstance(p, dict)],
        "phenotypes": phenotypes[:COHORT_MAX_PHENOTYPES],
        "variants": variants,
        "genes": {g: {**_pick(row, ("individuals", "pmids")), "n_variants": len(row.get("variants") or [])}
                  for g, row in (raw.get("genes") or {}).items() if isinstance(row, dict)},
        "inheritance": _pick(raw.get("inheritance"), ("chosen", "per_gene", "support", "stated_fallback")),
        "gene_decisions": raw.get("gene_decisions") or {},
        "possible_duplicates": raw.get("possible_duplicates") or [],
        "n_dropped": {"records": len(dropped.get("records") or []), "notes": len(dropped.get("notes") or [])},
        "records": records,
        "notes": notes,
    }
    for support in (out["inheritance"].get("support") or {}).values():
        if isinstance(support, dict) and isinstance(support.get("records"), list):
            support["n_records"] = len(support.pop("records"))
    trimmed: dict[str, Any] = {}
    if n_phenotypes > COHORT_MAX_PHENOTYPES:
        trimmed["phenotypes"] = {"shown": COHORT_MAX_PHENOTYPES, "of": n_phenotypes}
    if _size(out) > cap:
        for r in records:
            r["n_phenotypes"] = len(r.pop("phenotypes"))
        trimmed["record_features"] = "counts"
    if _size(out) > cap:
        for row in (*records, *notes):
            if len(row.get("quotes") or []) > 1:
                row["n_quotes"] = len(row["quotes"])
                row["quotes"], row["quote_grounding"] = row["quotes"][:1], (row.get("quote_grounding") or [])[:1]
        trimmed["quotes"] = "first only"
    while _size(out) > cap and (len(out["records"]) > 5 or len(out["notes"]) > 5):
        out["records"] = out["records"][: max(5, len(out["records"]) * 2 // 3)]
        out["notes"] = out["notes"][: max(5, len(out["notes"]) * 2 // 3)]
    if len(out["records"]) < len(records):
        trimmed["records"] = {"shown": len(out["records"]), "of": len(records)}
    if len(out["notes"]) < len(notes):
        trimmed["notes"] = {"shown": len(out["notes"]), "of": len(notes)}
    if trimmed:
        out["trimmed"] = trimmed
    return out


def _slim_memory_audit(raw: Any, cap: int = MEMORY_CLAIMS_CAP) -> dict | None:
    """What the audit made of the from-memory draft behind a "recall, then verify" entry.

    recall.memory_audit.json is that whole draft with its audit. The page needs the tally, and the
    claims that did not stand (the ones the rewrite restated, corrected or deleted), capped at `cap`.
    """
    if not isinstance(raw, dict):
        return None
    paragraphs = []
    if isinstance(raw.get("intro"), dict):
        paragraphs.append(("Text", raw["intro"]))
    for section in raw.get("sections") or []:
        paragraphs += [(section.get("heading") or section.get("name") or "", p) for p in section.get("paragraphs") or []]
    for av in raw.get("allelic_variants") or []:
        paragraphs += [("Allelic variant " + (av.get("name") or ""), p) for p in av.get("paragraphs") or []]
    by_verdict: dict[str, int] = {}
    not_standing = []
    for where, para in paragraphs:
        for check in (para or {}).get("checks") or []:
            verdict = check.get("verdict") or "not_checkable"
            by_verdict[verdict] = by_verdict.get(verdict, 0) + 1
            if verdict != "supported":
                not_standing.append({"where": where, **_pick(check, ("claim", "pmid", "verdict", "evidence_quote", "explanation"))})
    order = {"contradicted": 0, "unsupported": 1, "not_checkable": 2, "partially_supported": 3}
    not_standing.sort(key=lambda c: order.get(c.get("verdict"), 2))
    return {"paragraphs": len(paragraphs), "claims": sum(by_verdict.values()), "by_verdict": by_verdict,
            "not_standing": not_standing[:cap], "n_not_standing": len(not_standing)}


# --------------------------------------------------------------------------- #
# Collecting
# --------------------------------------------------------------------------- #

_PARAGRAPH_TALLY = ("n_facts", "present", "partial", "absent", "contradicted", "coverage", "strict_coverage",
                    "contradiction_rate")


def _slim_eval(raw: dict, gold_refs: list[str]) -> dict:
    """The eval as written, minus what the page can work out again.

    Dropped: the draft text of each gold paragraph (recomputed from the entry, as `_draft_text_for`
    does) and the per-paragraph tallies (recounted from the facts). OMIM's paragraph text is the same
    in every strategy's eval, so it is stored once per entry in `gold_refs` and referred to by index.
    """
    ev = dict(raw)
    gt = ev.get("gold_text")
    if isinstance(gt, dict) and isinstance(gt.get("paragraphs"), list):
        paragraphs = []
        for p in gt["paragraphs"]:
            if not isinstance(p, dict):
                continue
            q = {k: v for k, v in p.items() if k != "draft"}
            facts = q.get("facts")
            if isinstance(facts, list) and q.get("n_facts") == len(facts):
                for key in _PARAGRAPH_TALLY:
                    q.pop(key, None)
            reference = q.pop("reference", None)
            if isinstance(reference, str) and reference:
                if reference not in gold_refs:
                    gold_refs.append(reference)
                q["ref"] = gold_refs.index(reference)
            paragraphs.append(q)
        ev["gold_text"] = {**gt, "paragraphs": paragraphs}
    return ev


def _dedupe_references(entry: dict, papers: list[dict]) -> None:
    """A reference that repeats the paper list word for word is cut down to its PMID; the page fills it back in."""
    by_pmid = {str(p.get("pmid")): p for p in papers}
    for ref in entry.get("references") or []:
        paper = by_pmid.get(str(ref.get("pmid")))
        if not paper:
            continue
        for key, paper_key in (("citation", "reference"), ("label", "label"), ("content_level", "content_level")):
            if key in ref and ref[key] == paper.get(paper_key):
                del ref[key]


def _collect_entry(path: Path) -> dict:
    papers = _slim_papers(_read_json(path / "papers.json"))
    entries = {}
    for s in _strategies_in(path, "entry"):
        raw = _read_json(path / f"entry.{s}.json")
        if isinstance(raw, dict):
            entries[s] = _slim_entry(raw)
            _dedupe_references(entries[s], papers)
    gold_refs: list[str] = []
    evals = {}
    for s in _strategies_in(path, "eval"):
        raw = _read_json(path / f"eval.{s}.json")
        if isinstance(raw, dict):
            evals[s] = _slim_eval(raw, gold_refs)
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
        "gold_refs": gold_refs,
        "retrieval": _slim_retrieval(_read_json(path / "retrieval.json")),
        "papers": papers,
        "extractions": _slim_extractions(_read_json(path / "extractions.json")),
        "kg": _slim_kg(_read_json(path / "kg.json")),
        "cohort": _slim_cohort(_read_json(path / "cohort.json")),
        "recall_memory": _slim_memory_audit(_read_json(path / "recall.memory_audit.json")),
        "strategies": strategy_order([*entries, *evals]),
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
        "has_draft": en is not None,
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
    keep = ("seed", "gold", "gold_refs", "retrieval", "papers", "extractions", "kg", "cohort", "recall_memory",
            "entries", "evals", "usage", "updates")
    return {k: item[k] for k in keep if item[k] not in (None, [], {}) or k in ("entries", "evals", "papers")}


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
    compared = _read_json(run_dir / "strategies.json")
    compared = compared if isinstance(compared, dict) and compared.get("means") else None
    items = [_collect_entry(p) for p in sorted(run_dir.iterdir()) if _is_entry_dir(p)]
    files = _file_names([i["dir"] for i in items])
    index = [_index_row(item, f) for item, f in zip(items, files)]
    config = (summary or {}).get("config") or {}
    names = strategy_order(s for item in items for s in item["strategies"])
    info = strategy_info(names, (compared or {}).get("strategies"))
    for row in info:
        row["n_drafts"] = sum(1 for r in index if (r["rows"].get(row["name"]) or {}).get("has_draft"))
        row["n_scored"] = sum(1 for r in index if (r["rows"].get(row["name"]) or {}).get("has_eval"))
    baseline = (compared or {}).get("baseline")
    if baseline not in names:
        baseline = "direct" if "direct" in names and len(names) > 1 else None
    retrieval = config.get("retrieval") or next((r["retrieval_mode"] for r in index if r["retrieval_mode"]), None)
    return {
        "format": 3,
        "run": (summary or {}).get("run") or run_dir.name,
        "retrieval": retrieval,
        "strategies": names,
        "strategy_info": info,
        "baseline": baseline,
        "generated": sorted({d for r in index for d in r["generated"]}),
        "usage_total": (summary or {}).get("usage_total") or {},
        "failures": (summary or {}).get("failures") or {},
        # strategies.json covers any number of strategies; comparison.json is the older kg-vs-direct file.
        "compared": compared,
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


def pack(payload: Any) -> str:
    """One entry's payload as base64 of gzip of JSON; the page unpacks it with DecompressionStream."""
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return base64.b64encode(gzip.compress(text, compresslevel=9, mtime=0)).decode("ascii")


def unpack(packed: str) -> Any:
    return json.loads(gzip.decompress(base64.b64decode(packed)).decode("utf-8"))


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


def build_report(run_dir: Path, out: str | None = None, split: bool | None = None, fragment: bool = False,
                 packed: bool | None = None) -> Path:
    """Write the review page for `run_dir` and return its path (default `run_dir/report.html`).

    split=None decides by size: one self-contained file while the entry data stays under
    SPLIT_THRESHOLD bytes, otherwise `report.html` plus `report_data/<entry>.js`, loaded on demand.
    A single file holding more than PACK_THRESHOLD bytes of entry data embeds each entry
    gzip-compressed (`packed=None`); `packed` forces that on or off. Split pages are never packed.
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")
    path = Path(out) if out else run_dir / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = collect_report_data(run_dir)
    payloads = data.pop("payloads")
    scripts = {f: entry_script(f, p) for f, p in payloads.items()}
    size = sum(len(s.encode("utf-8")) for s in scripts.values())
    if split is None:
        split = size > SPLIT_THRESHOLD
    data["split"] = bool(split)
    if split:
        data_dir = path.parent / DATA_DIR
        data_dir.mkdir(exist_ok=True)
        for stale in data_dir.glob("*.js"):
            if stale.name not in scripts:
                stale.unlink()
        for f, text in scripts.items():
            (data_dir / f).write_text(text, encoding="utf-8")
    elif packed or (packed is None and size > PACK_THRESHOLD):
        data["packed"] = {f: pack(p) for f, p in payloads.items()}
    else:
        data["payloads"] = payloads
    html = render_html(data)
    path.write_text(html, encoding="utf-8")
    if fragment:
        path.with_name(path.stem + ".fragment.html").write_text(as_fragment(html), encoding="utf-8")
    return path


_SKELETON = re.compile(
    r"<!doctype html>\s*|</?html[^>]*>\s*|</?head>\s*|</?body>\s*|"
    r"<meta (?:charset|name=\"viewport\"|http-equiv=\"Content-Security-Policy\"|name=\"referrer\")[^>]*>\s*",
    re.I,
)


def as_fragment(html: str) -> str:
    """The same page without its document skeleton and CSP tag.

    Hosts that wrap a page in their own <html>/<head>/<body> and apply their own
    content-security policy (a Claude Artifact, for one) take this form. Only the
    part of the file before the embedded data is touched.
    """
    cut = html.index('<script type="application/json"')
    head, rest = html[:cut], html[cut:]
    rest = re.sub(r"\s*</body>\s*</html>\s*$", "\n", rest, flags=re.I)
    return _SKELETON.sub("", head) + rest
