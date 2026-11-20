"""`report`: the files under outputs/ that Claude Code parses (ids, statuses and counts only).

    outputs/marks/<task>/<mim>.<strategy>.json   per fixed fact: the OpenAI judge's mark and Claude's
    outputs/availability/<mim>.json              per fixed fact: availability verdicts of both judges
    outputs/drafts/<task>/<mim>/entry.<s>.json|.md  the OpenAI writer's drafts (no judge notes)
    outputs/summary.json | summary.md            completion, agreement, coverage, paired differences,
                                                 the stated-facts comparison, the hidden-full-text effect,
                                                 tokens, requests, stops and cost

See OUTPUT_SPEC.md for every field.
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import Study, StudyPaths, now, read_json, write_json, write_text
from .stats import AVAIL, MARKS, agreement, coverage, mean, paired, tally
from .tasks import FINAL, Bundle, TaskSpec, read_result
from .validate import OmimScanner, gold_texts_from_bundle

SPEC_VERSION = "1.0"
A1_ORDER = ("direct", "agent", "kg", "cohort", "recall", "closedbook")
LABELS = {"direct": "Direct reading", "agent": "Agentic curator", "kg": "Evidence graph", "cohort": "Case table first",
          "recall": "Recall, then verify", "closedbook": "Memory only (control)",
          "fulltext_before_repair": "Full text (before repair)", "abstract": "Abstract only",
          "secondhand": "Abstract plus second-hand passages", "fulltext": "Full text"}
A3_SEED = 20261119      # secondhand.BOOTSTRAP_SEED
COMPARE_SEED = 7        # compare.compare_strategies


# --------------------------------------------------------------------------- #
# Reading marks
# --------------------------------------------------------------------------- #


def _rows(score: dict[str, Any] | None) -> list[dict[str, Any]]:
    """[{id, paragraph, content_level, status}] from a gold_text_frozen-shaped block."""
    out = []
    for p in (score or {}).get("paragraphs") or []:
        key = (p.get("key") or "")[:12]
        for f in p.get("facts") or []:
            out.append({"id": f["id"], "paragraph": key, "content_level": p.get("content_level", "not_retrieved"),
                        "status": f.get("status"), "paragraph_ok": bool(p.get("facts")) and not p.get("error")})
    return out


def _by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in rows}


def _entry_cov(rows: list[dict[str, Any]], *, rounded: bool) -> float | None:
    c = coverage(r["status"] for r in rows)
    return None if c is None else (round(c, 3) if rounded else c)


class Data:
    """Every finished task's marks and verdicts, and Claude's from the bundle."""

    def __init__(self, paths: StudyPaths, study: Study, bundle: Bundle):
        self.paths, self.study, self.bundle = paths, study, bundle
        st = read_json(paths.state / "tasks.json", {"tasks": {}}) or {"tasks": {}}
        self.status = {tid: t["status"] for tid, t in st["tasks"].items()}
        self.results: dict[str, dict[str, Any]] = {}
        for tid, s in self.status.items():
            if s in FINAL:
                r = read_result(paths, TaskSpec.parse(tid))
                if r is not None:
                    self.results[tid] = r

    def openai_rows(self, tid: str) -> list[dict[str, Any]] | None:
        r = self.results.get(tid)
        if r is None or "gold_text_frozen" not in r:
            return None
        return _rows(r["gold_text_frozen"])

    def claude_rows(self, source: str, mim: str, name: str) -> list[dict[str, Any]] | None:
        m = self.bundle.claude_marks(source, mim, name)
        return _rows(m) if m else None

    def tasks(self, kind: str) -> list[TaskSpec]:
        return [TaskSpec.parse(t) for t in self.status if t.startswith(kind + ":")]


# --------------------------------------------------------------------------- #
# Per-file outputs
# --------------------------------------------------------------------------- #


def _marks_file(spec: TaskSpec, status: str, model: str, oa: list[dict] | None, cl: list[dict] | None,
                claude_of: str, claude_source: str, reps: dict[str, list[dict] | None] | None = None,
                draft: str = "") -> dict[str, Any]:
    order = oa if oa else (cl or [])
    cl_by = _by_id(cl or [])
    oa_by = _by_id(oa or [])
    rep_by = {k: _by_id(v) for k, v in (reps or {}).items() if v}
    facts = []
    for r in order:
        row = {"id": r["id"], "paragraph": r["paragraph"], "content_level": r["content_level"],
               "openai": oa_by[r["id"]]["status"] if r["id"] in oa_by else None,
               "claude": cl_by[r["id"]]["status"] if r["id"] in cl_by else None}
        for k, by in rep_by.items():
            row[f"claude_{k}"] = by[r["id"]]["status"] if r["id"] in by else None
        facts.append(row)
    return {
        "spec_version": SPEC_VERSION, "task": spec.kind, "mim": spec.mim, "strategy": spec.variant,
        "status": status, "openai_model": model, "draft": draft, "claude_marks_of": claude_of,
        "claude_source": claude_source,
        "counts": {"openai": tally(f["openai"] for f in facts) if oa is not None else None,
                   "claude": tally(f["claude"] for f in facts) if cl is not None else None},
        "facts": facts,
    }


def write_marks(data: Data, out: Path) -> dict[str, int]:
    model = data.study.model
    n = defaultdict(int)
    for kind in ("A1", "A3", "B1", "B2"):
        for spec in data.tasks(kind):
            status = data.status[spec.id]
            oa = data.openai_rows(spec.id) if status in FINAL else None
            if kind == "A1":
                cl = data.claude_rows("main", spec.mim, spec.variant)
                reps = {s: data.claude_rows(f"judge_{s}", spec.mim, spec.variant) for s in ("j1", "j2")}
                rec = _marks_file(spec, status, model, oa, cl, "same_draft",
                                  f"omim100/{spec.mim}/eval.{spec.variant}.json#gold_text_frozen", reps,
                                  draft="claude_main_run")
            elif kind == "A3":
                cl = data.claude_rows("secondhand", spec.mim, spec.variant)
                src = ("secondhand_check_omim100/<mim>/secondhand_check/coverage_frozen_before_repair.json"
                       if spec.variant == "fulltext_before_repair" else
                       "secondhand_check_omim100/<mim>/secondhand_check/coverage_frozen.json")
                rec = _marks_file(spec, status, model, oa, cl, "same_draft", src, draft="claude_hidden_fulltext")
            elif kind == "B1":
                cl = data.claude_rows("main", spec.mim, spec.variant)
                rec = _marks_file(spec, status, model, oa, cl, "claude_draft_same_strategy",
                                  f"omim100/{spec.mim}/eval.{spec.variant}.json#gold_text_frozen (Claude's draft, "
                                  "after its repair round; memory only is never repaired)", draft="openai")
            else:
                name = "fulltext_before_repair" if spec.variant == "fulltext" else "abstract"
                cl = data.claude_rows("secondhand", spec.mim, name)
                rec = _marks_file(spec, status, model, oa, cl, "claude_draft_same_arm",
                                  f"Claude's {name.replace('_', ' ')} draft (secondhand_check_omim100)",
                                  draft="openai")
            if kind in ("B1", "B2"):
                r = data.results.get(spec.id) or {}
                rec["writer_status"] = r.get("writer_status")
            write_json(out / "marks" / kind / f"{spec.mim}.{spec.variant}.json", rec)
            n[kind] += 1
    return dict(n)


def write_availability(data: Data, out: Path) -> int:
    n = 0
    for spec in data.tasks("A2F"):
        mim = spec.mim
        fr = data.results.get(spec.id)
        cv = data.results.get(f"A2C:{mim}")
        cl_av = data.bundle.claude_availability(mim) or {"paragraphs": []}
        cl_cv = data.bundle.claude_conveyed(mim) or {"paragraphs": []}
        levels = {}
        marks = data.bundle.claude_marks("main", mim, "direct") or {"paragraphs": []}
        for p in marks["paragraphs"]:
            for f in p["facts"]:
                levels[f["id"]] = (p.get("content_level"), (p.get("key") or "")[:12], f["status"])
        oa_av = {r["id"]: r["in_text"] for a in ((fr or {}).get("availability") or {}).values() for r in a["rows"]}
        cl_own = {r["id"]: r["in_text"] for p in cl_av["paragraphs"] for r in p["rows"]}
        cl_other = {f["id"]: f for p in cl_cv["paragraphs"] for f in p["facts"]}
        oa_other = {f["id"]: f for f in ((cv or {}).get("facts") or [])}
        facts = []
        for fid, (level, para, draft_status) in levels.items():
            row = {"id": fid, "paragraph": para, "content_level": level, "openai": oa_av.get(fid),
                   "claude": cl_own.get(fid), "claude_direct_mark": draft_status}
            if fid in cl_other:
                row["rechecked"] = cl_other[fid].get("own") in ("no", "partly")
                row["claude_other"] = cl_other[fid].get("other")
                row["openai_other"] = (oa_other.get(fid) or {}).get("other")
                row["claude_class"] = cl_other[fid].get("class")
                row["class_with_openai_other"] = (oa_other.get(fid) or {}).get("class")
            facts.append(row)
        rec = {"spec_version": SPEC_VERSION, "mim": mim, "openai_model": data.study.model,
               "status": {"frozen": data.status.get(spec.id), "conveyed": data.status.get(f"A2C:{mim}")},
               "counts": {"openai": _count_avail(f["openai"] for f in facts),
                          "claude": _count_avail(f["claude"] for f in facts)},
               "facts": facts}
        write_json(out / "availability" / f"{mim}.json", rec)
        n += 1
    return n


def _count_avail(values) -> dict[str, int]:
    values = list(values)
    out = {k: sum(v == k for v in values) for k in AVAIL}
    out["unjudged"] = sum(v not in AVAIL for v in values)
    return out


def write_drafts(data: Data, out: Path, scanner: OmimScanner | None) -> dict[str, Any]:
    """The OpenAI writer's drafts as the project writes them (no judge material).

    A span that matches 60 characters of OMIM's text (house-style sentences can) is
    replaced by a marker, and `meta.redactions` records pointers into the gold text
    (paragraph key or fact id, offset, length) and the span's capitals, so that
    `restore-drafts` rebuilds the draft exactly wherever the gold text is at hand. The
    Markdown is rendered from the redacted entry.
    """
    from ..models import GeneratedEntry
    from ..render import entry_markdown

    written, redacted_spans, redacted_drafts, unrestorable = 0, 0, [], 0
    for kind in ("B1", "B2"):
        for spec in data.tasks(kind):
            r = data.results.get(spec.id)
            if not r or "entry" not in r:
                continue
            entry = json.loads(json.dumps(r["entry"]))
            records: list[dict[str, Any]] = []
            spans = 0
            if scanner is not None:
                entry, spans = _redact_entry(entry, scanner, records)
            if spans:
                redacted_spans += spans
                redacted_drafts.append(spec.id)
                unrestorable += sum(1 for x in records if not x.get("segments"))
                entry.setdefault("meta", {})["redactions"] = records
                entry["meta"]["redacted_spans_matching_omim"] = spans
            md = entry_markdown(GeneratedEntry.model_validate(entry), show_flags=False)
            if scanner is not None and scanner.hits(md):
                # A window across two rendered fields (a variant's name and its paragraph): the Markdown is
                # a rendering of the JSON, so `restore-drafts` re-renders it rather than restoring it.
                md, extra = scanner.redact(md)
                redacted_spans += extra
                if spec.id not in redacted_drafts:
                    redacted_drafts.append(spec.id)
            d = out / "drafts" / kind / spec.mim
            write_json(d / f"entry.{spec.variant}.json", entry)
            write_text(d / f"entry.{spec.variant}.md", md)
            written += 1
    return {"written": written, "redacted_spans": redacted_spans, "redacted_drafts": redacted_drafts,
            "spans_without_pointers": unrestorable}


def _redact_entry(node: Any, scanner: OmimScanner, records: list[dict[str, Any]]) -> tuple[Any, int]:
    if isinstance(node, str):
        if len(node) >= scanner.window and scanner.hits(node):
            return scanner.redact(node, records)
        return node, 0
    if isinstance(node, list):
        total, out = 0, []
        for x in node:
            y, k = _redact_entry(x, scanner, records)
            out.append(y)
            total += k
        return out, total
    if isinstance(node, dict):
        total, out = 0, {}
        for key, x in node.items():
            y, k = _redact_entry(x, scanner, records)
            out[key] = y
            total += k
        return out, total
    return node, 0


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #


def completion(data: Data) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for tid, s in data.status.items():
        spec = TaskSpec.parse(tid)
        cell = out.setdefault(spec.kind, {}).setdefault(spec.variant or "all",
                                                         {k: 0 for k in (*FINAL, "unfinished")})
        cell[s if s in FINAL else "unfinished"] += 1
    return out


def _pairs_by_entry(a: list[dict] | None, b: list[dict] | None) -> list[tuple[str, str]]:
    if not a or not b:
        return []
    bb = _by_id(b)
    return [(r["status"], bb[r["id"]]["status"]) for r in a if r["id"] in bb]


def agreement_section(data: Data) -> dict[str, Any]:
    out: dict[str, Any] = {"note": "First judge OpenAI, second Claude (rows / columns of the confusion matrix). "
                                   "Facts either judge left unjudged are left out."}
    a1: dict[str, dict[str, list]] = defaultdict(dict)
    for spec in data.tasks("A1"):
        oa = data.openai_rows(spec.id)
        if oa is None:
            continue
        a1[spec.variant][spec.mim] = _pairs_by_entry(oa, data.claude_rows("main", spec.mim, spec.variant))
    pooled: dict[str, list] = defaultdict(list)
    for s, by_entry in a1.items():
        for m, pairs in by_entry.items():
            pooled[m].extend(pairs)
    out["A1"] = {"all_strategies": {"four_marks": agreement(pooled, MARKS),
                                    "present_vs_not": agreement(pooled, MARKS, binary="present")},
                 "by_strategy": {s: {"four_marks": agreement(a1[s], MARKS),
                                     "present_vs_not": agreement(a1[s], MARKS, binary="present")}
                                 for s in A1_ORDER if s in a1}}
    a3: dict[str, dict[str, list]] = defaultdict(dict)
    for spec in data.tasks("A3"):
        oa = data.openai_rows(spec.id)
        if oa is not None:
            a3[spec.variant][spec.mim] = _pairs_by_entry(oa, data.claude_rows("secondhand", spec.mim, spec.variant))
    out["A3"] = {arm: {"four_marks": agreement(v, MARKS), "present_vs_not": agreement(v, MARKS, binary="present")}
                 for arm, v in a3.items()}
    # Claude against itself: the judge replicates of the original study (same drafts, same lists).
    base: dict[str, dict[str, list]] = defaultdict(dict)
    same: dict[str, dict[str, list]] = defaultdict(dict)
    entries_a1 = {s.mim for s in data.tasks("A1")}
    for mim in sorted(entries_a1):
        for s in ("direct", "kg"):
            main = data.claude_rows("main", mim, s)
            for rep in ("j1", "j2"):
                r = data.claude_rows(f"judge_{rep}", mim, s)
                if main and r:
                    base[f"claude_main_vs_{rep}"].setdefault(mim, []).extend(_pairs_by_entry(main, r))
                    oa = data.openai_rows(f"A1:{mim}:{s}")
                    if oa is not None and rep == "j1":
                        same["openai_vs_claude_main"].setdefault(mim, []).extend(_pairs_by_entry(oa, main))
    out["claude_self_baseline"] = {
        "note": "Claude's judge replicates j1 and j2 (direct reading and evidence graph, the replicate entries), "
                "against Claude's main marks; and OpenAI against Claude's main marks on exactly those drafts.",
        **{k: {"four_marks": agreement(v, MARKS), "present_vs_not": agreement(v, MARKS, binary="present")}
           for k, v in {**base, **same}.items()}}
    fr_pairs: dict[str, list] = {}
    other_pairs: dict[str, list] = {}
    for spec in data.tasks("A2F"):
        r = data.results.get(spec.id)
        if not r:
            continue
        oa = {x["id"]: x["in_text"] for a in r["availability"].values() for x in a["rows"]}
        cl = data.bundle.claude_availability(spec.mim) or {"paragraphs": []}
        fr_pairs[spec.mim] = [(oa[x["id"]], x["in_text"]) for p in cl["paragraphs"] for x in p["rows"]
                              if x["id"] in oa]
    for spec in data.tasks("A2C"):
        r = data.results.get(spec.id)
        if not r:
            continue
        oa = {f["id"]: f.get("other") for f in r["facts"]}
        cl = data.bundle.claude_conveyed(spec.mim) or {"paragraphs": []}
        other_pairs[spec.mim] = [(oa.get(f["id"]), f.get("other")) for p in cl["paragraphs"] for f in p["facts"]
                                 if f.get("own") in ("no", "partly")]
    out["A2"] = {"own_text": {"three_verdicts": agreement(fr_pairs, AVAIL),
                              "stated_vs_not": agreement(fr_pairs, AVAIL, binary="yes")},
                 "other_papers": {"three_verdicts": agreement(other_pairs, AVAIL),
                                  "stated_vs_not": agreement(other_pairs, AVAIL, binary="yes")}}
    return out


def _complete_entries(data: Data, kind: str, variants: tuple[str, ...], ok: tuple[str, ...]) -> list[str]:
    by: dict[str, set[str]] = defaultdict(set)
    for spec in data.tasks(kind):
        if data.status.get(spec.id) in ok and spec.variant in variants:
            by[spec.mim].add(spec.variant)
    return sorted(m for m, v in by.items() if v >= set(variants))


def a1_section(data: Data) -> dict[str, Any]:
    strategies = tuple(s for s in A1_ORDER if any(t.variant == s for t in data.tasks("A1")))
    entries = _complete_entries(data, "A1", strategies, ("complete", "incomplete"))
    cov = {"openai": defaultdict(dict), "claude": defaultdict(dict)}
    for mim in entries:
        for s in strategies:
            cov["openai"][s][mim] = _entry_cov(data.openai_rows(f"A1:{mim}:{s}") or [], rounded=True)
            cov["claude"][s][mim] = _entry_cov(data.claude_rows("main", mim, s) or [], rounded=True)
    out: dict[str, Any] = {"entries": entries, "n_entries": len(entries),
                           "rule": "entries on which the OpenAI judge marked all six strategies' drafts",
                           "coverage": {}, "versus_direct": {}}
    for judge in ("openai", "claude"):
        out["coverage"][judge] = {s: {"mean_over_entries": mean(cov[judge][s].values()),
                                      "n": sum(v is not None for v in cov[judge][s].values())} for s in strategies}
        out["versus_direct"][judge] = {}
        for s in strategies:
            if s == "direct":
                continue
            pairs = [(cov[judge][s][m], cov[judge]["direct"][m]) for m in entries
                     if cov[judge][s].get(m) is not None and cov[judge]["direct"].get(m) is not None]
            out["versus_direct"][judge][s] = paired(pairs, COMPARE_SEED)
    out["note"] = ("Mean over entries of per-entry coverage, (present + half of partial) / facts judged, rounded per "
                   "entry to 0.001 as the project's evaluation files hold it; differences are strategy minus direct "
                   "reading, bootstrap 95% interval over entries (10,000 resamples, seed 7), better/worse/tied, "
                   "exact sign test.")
    return out


def b1_section(data: Data) -> dict[str, Any]:
    strategies = tuple(s for s in ("direct", "kg", "closedbook") if any(t.variant == s for t in data.tasks("B1")))
    entries = _complete_entries(data, "B1", strategies, ("complete",))
    cells = {"openai_writer_openai_judge": {}, "claude_writer_claude_judge": {}, "claude_writer_openai_judge": {}}
    for s in strategies:
        cells["openai_writer_openai_judge"][s] = {m: _entry_cov(data.openai_rows(f"B1:{m}:{s}") or [], rounded=True)
                                                  for m in entries}
        cells["claude_writer_claude_judge"][s] = {m: _entry_cov(data.claude_rows("main", m, s) or [], rounded=True)
                                                  for m in entries}
        cells["claude_writer_openai_judge"][s] = {m: _entry_cov(data.openai_rows(f"A1:{m}:{s}") or [], rounded=True)
                                                  if data.openai_rows(f"A1:{m}:{s}") is not None else None
                                                  for m in entries}
    out: dict[str, Any] = {"entries": entries, "n_entries": len(entries),
                           "rule": "entries on which every OpenAI-written draft is complete (no stop, no failed "
                                   "paper) and fully marked", "coverage": {}, "versus_direct": {}, "writer_effect": {}}
    for cell, cov in cells.items():
        out["coverage"][cell] = {s: {"mean_over_entries": mean(cov[s].values()),
                                     "n": sum(v is not None for v in cov[s].values())} for s in strategies}
        out["versus_direct"][cell] = {}
        for s in strategies:
            if s == "direct":
                continue
            pairs = [(cov[s][m], cov["direct"][m]) for m in entries
                     if cov[s].get(m) is not None and cov["direct"].get(m) is not None]
            out["versus_direct"][cell][s] = paired(pairs, COMPARE_SEED)
    for s in strategies:
        a, b = cells["openai_writer_openai_judge"][s], cells["claude_writer_openai_judge"][s]
        pairs = [(a[m], b[m]) for m in entries if a.get(m) is not None and b.get(m) is not None]
        out["writer_effect"][s] = paired(pairs, COMPARE_SEED)
    out["note"] = ("writer_effect: OpenAI-written draft minus Claude-written draft, both marked by the OpenAI judge. "
                   "Claude's direct-reading and evidence-graph drafts went through the audit's repair round, the "
                   "OpenAI drafts did not (the repair round moved direct reading's coverage by +0.2 points in the "
                   "hidden-full-text experiment). Marks of the OpenAI drafts by the Claude judge are made later, on "
                   "the Claude Code side, from outputs/drafts.")
    return out


def stated_section(data: Data) -> dict[str, Any]:
    """`gaps.compare_by_availability` recomputed: with OpenAI availability and OpenAI marks, and Claude's."""
    from ..gaps import AVAIL_LEVELS, AVAIL_RESTRICTIONS, join_marks, restricted_tally

    strategies = tuple(s for s in A1_ORDER if any(t.variant == s for t in data.tasks("A1")))
    entries = [m for m in _complete_entries(data, "A1", strategies, ("complete", "incomplete"))
               if data.status.get(f"A2F:{m}") in ("complete", "incomplete")]
    out: dict[str, Any] = {"entries": entries, "n_entries": len(entries), "baseline": "direct",
                           "rule": "entries in the A1 comparison whose availability (A2, own text) the OpenAI judge "
                                   "finished"}
    for judge in ("openai", "claude"):
        rows: dict[str, dict[str, list]] = {s: {} for s in strategies}
        for m in entries:
            if judge == "openai":
                r = data.results.get(f"A2F:{m}") or {}
                avail = {x["id"]: x["in_text"] or "unjudged" for a in (r.get("availability") or {}).values()
                         for x in a["rows"]}
            else:
                cl = data.bundle.claude_availability(m) or {"paragraphs": []}
                avail = {x["id"]: x["in_text"] or "unjudged" for p in cl["paragraphs"] for x in p["rows"]}
            for s in strategies:
                src = (data.results.get(f"A1:{m}:{s}") or {}).get("gold_text_frozen") if judge == "openai" \
                    else data.bundle.claude_marks("main", m, s)
                rows[s][m], _ = join_marks(src or {}, avail)
        cells: dict[str, Any] = {}
        for name, verdicts in AVAIL_RESTRICTIONS.items():
            for level in AVAIL_LEVELS:
                per = {s: {m: restricted_tally(rows[s][m], verdicts, level) for m in entries} for s in strategies}
                block: dict[str, Any] = {"by_strategy": {}, "versus_direct": {}}
                for s in strategies:
                    covs = [c["coverage"] for c in per[s].values() if c["coverage"] is not None]
                    block["by_strategy"][s] = {"mean_over_entries": round(sum(covs) / len(covs), 4) if covs else None,
                                               "n_entries": len(covs),
                                               "n_facts": sum(c["n_facts"] for c in per[s].values())}
                for s in strategies:
                    if s == "direct":
                        continue
                    pairs = [(per[s][m]["coverage"], per["direct"][m]["coverage"]) for m in entries
                             if per[s][m]["coverage"] is not None and per["direct"][m]["coverage"] is not None]
                    block["versus_direct"][s] = paired(pairs, COMPARE_SEED)
                cells.setdefault(name, {})[level] = block
        out[judge] = cells
    return out


def conveyed_section(data: Data) -> dict[str, Any]:
    """Facts direct reading conveyed from abstract- or title-only papers that no supplied text states:
    Claude's stored classes, and the same with OpenAI's re-check against the other papers."""
    from ..gaps import classify_conveyed

    cells = {"claude": defaultdict(int), "claude_own_openai_other": defaultdict(int)}
    n_entries = 0
    for spec in data.tasks("A2C"):
        r = data.results.get(spec.id)
        cl = data.bundle.claude_conveyed(spec.mim)
        if not r or not cl:
            continue
        n_entries += 1
        oa = {f["id"]: f for f in r["facts"]}
        for p in cl["paragraphs"]:
            if p.get("content_level") not in ("abstract", "title"):
                continue
            for f in p["facts"]:
                if f.get("draft_status") != "present":
                    continue
                cells["claude"]["n"] += 1
                cells["claude"][f.get("class") or "unjudged"] += 1
                other = (oa.get(f["id"]) or {}).get("other") if f.get("own") != "yes" else None
                cls = classify_conveyed(f.get("own") or "unjudged", other)
                cells["claude_own_openai_other"]["n"] += 1
                cells["claude_own_openai_other"][cls] += 1
    out: dict[str, Any] = {"n_entries": n_entries,
                           "scope": "facts direct reading conveyed in full (Claude's marks) from papers readable "
                                    "only as abstract or title; own-text verdict is Claude's in both rows"}
    for k, c in cells.items():
        judged = c["n"] - c.get("unjudged", 0)
        out[k] = {**dict(c), "share_not_in_supplied_text": round(c.get("not_in_supplied_text", 0) / judged, 4)
                  if judged else None}
    return out


def _arm_cov(rows_by_arm: dict[str, list[dict] | None], arms: tuple[str, ...]) -> dict[str, float | None] | None:
    """Coverage per arm over the paragraphs every arm has (scored, no error): `secondhand.pool_frozen`'s rule."""
    if any(not rows_by_arm.get(a) for a in arms):
        return None
    paras = None
    for a in arms:
        ok = {r["paragraph"] for r in rows_by_arm[a] if r["paragraph_ok"]}
        paras = ok if paras is None else paras & ok
    if not paras:
        return None
    return {a: coverage(r["status"] for r in rows_by_arm[a] if r["paragraph"] in paras) for a in arms}


def hidden_section(data: Data) -> dict[str, Any]:
    out: dict[str, Any] = {"note": "Per entry, coverage over the gold paragraphs about the hidden papers that every "
                                   "arm has scored; paired differences over entries, bootstrap seed 20261119 as in "
                                   "secondhand.pool_frozen."}
    arms3 = ("fulltext_before_repair", "abstract", "secondhand")
    mims = sorted({s.mim for s in data.tasks("A3")})
    for judge in ("openai", "claude"):
        per = {}
        for m in mims:
            rows = {a: (data.openai_rows(f"A3:{m}:{a}") if judge == "openai"
                        else data.claude_rows("secondhand", m, a)) for a in arms3}
            if judge == "openai" and any(data.status.get(f"A3:{m}:{a}") not in ("complete", "incomplete")
                                         for a in arms3):
                continue
            c = _arm_cov(rows, arms3)
            if c:
                per[m] = c
        out.setdefault("A3", {})[judge] = _hidden_block(per, arms3, "abstract")
    # B2: the OpenAI writer, judged by OpenAI; Claude's writer and judge on the same entries for reference.
    arms2 = ("fulltext", "abstract")
    per_oa, per_cl = {}, {}
    for m in sorted({s.mim for s in data.tasks("B2")}):
        if any(data.status.get(f"B2:{m}:{a}") != "complete" for a in arms2):
            continue
        c = _arm_cov({a: data.openai_rows(f"B2:{m}:{a}") for a in arms2}, arms2)
        if c:
            per_oa[m] = c
        cl = _arm_cov({"fulltext": data.claude_rows("secondhand", m, "fulltext_before_repair"),
                       "abstract": data.claude_rows("secondhand", m, "abstract")}, arms2)
        if cl:
            per_cl[m] = cl
    out["B2"] = {"openai_writer_openai_judge": _hidden_block(per_oa, arms2, "abstract"),
                 "claude_writer_claude_judge_same_entries": _hidden_block(per_cl, arms2, "abstract"),
                 "rule": "entries where both OpenAI drafts are complete and fully marked"}
    return out


def _hidden_block(per: dict[str, dict[str, float | None]], arms: tuple[str, ...], base: str) -> dict[str, Any]:
    block: dict[str, Any] = {"n_entries": len(per), "entries": sorted(per),
                             "mean_over_entries": {a: mean(v[a] for v in per.values()) for a in arms}}
    for a in arms:
        if a == base:
            continue
        pairs = [(v[a], v[base]) for v in per.values() if v[a] is not None and v[base] is not None]
        block[f"{a}_minus_{base}"] = paired(pairs, A3_SEED)
    return block


def usage_section(paths: StudyPaths) -> dict[str, Any]:
    led = read_json(paths.state / "ledger.json", {"waves": {}, "totals": {}}) or {"waves": {}, "totals": {}}
    waves = {}
    kinds: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for w, cell in sorted(led["waves"].items()):
        waves[w] = {"batches": cell.get("batches", []), **(cell.get("total") or {})}
        for k, c in (cell.get("by_task_kind") or {}).items():
            for key, v in c.items():
                kinds[k][key] += v
    return {"by_wave": waves, "by_task_kind": {k: {kk: round(vv, 4) for kk, vv in v.items()}
                                               for k, v in sorted(kinds.items())},
            "totals": led.get("totals", {}),
            "note": "Requests shared by several tasks are counted once, under the first task kind in sort order."}


def report(paths: StudyPaths, study: Study) -> dict[str, Any]:
    bundle = Bundle(paths.bundle)
    data = Data(paths, study, bundle)
    out = paths.outputs
    for sub in ("marks", "availability", "drafts"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    scanner = OmimScanner(gold_texts_from_bundle(bundle.root))
    files = {"marks": write_marks(data, out), "availability": write_availability(data, out)}
    drafts = write_drafts(data, out, scanner)
    status = read_json(paths.state / "status.json", {}) or {}
    summary = {
        "spec_version": SPEC_VERSION, "study": "openai_second_model", "openai_model": study.model,
        "generated_at": now(), "phase": status.get("phase"), "bundle_id": bundle.manifest.get("bundle_id"),
        "files": {**files, "drafts": drafts["written"]},
        "completion": completion(data),
        "agreement": agreement_section(data),
        "A1": a1_section(data),
        "B1": b1_section(data),
        "stated_facts": stated_section(data),
        "conveyed_facts": conveyed_section(data),
        "hidden_fulltext": hidden_section(data),
        "usage": usage_section(paths),
        "redactions": {"drafts": drafts["redacted_drafts"], "spans": drafts["redacted_spans"],
                       "spans_without_pointers": drafts["spans_without_pointers"],
                       "note": "Spans of the OpenAI drafts that match 60 characters of OMIM's text are replaced by "
                               "a marker; `restore-drafts` puts them back from the gold text (Claude Code side)."},
    }
    write_json(out / "summary.json", summary)
    write_text(out / "summary.md", summary_markdown(summary))
    return summary


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def _pp(row: dict[str, Any] | None) -> str:
    if not row:
        return "–"
    ci = row.get("ci95")
    ci_s = f" ({100 * ci[0]:+.1f} to {100 * ci[1]:+.1f})" if ci else ""
    p = row.get("sign_test_p")
    return (f"{100 * row['difference']:+.1f}{ci_s}; {row['better']}/{row['worse']}/{row['ties']}"
            + (f"; p {p:.3f}" if p is not None else ""))


def _agr(a: dict[str, Any] | None) -> str:
    if not a or not a.get("n_facts"):
        return "–"
    ci = a.get("kappa_ci95")
    k = a.get("kappa")
    return (f"{_pct(a['raw_agreement'])}; κ {k:.3f}" + (f" ({ci[0]:.3f} to {ci[1]:.3f})" if ci else "")
            + f"; {a['n_facts']:,} facts, {a['n_entries']} entries") if k is not None else f"{_pct(a['raw_agreement'])}"


def summary_markdown(s: dict[str, Any]) -> str:
    L = [f"# Second model family: {s['openai_model']}", "",
         f"Generated {s['generated_at']} from bundle `{s['bundle_id']}`; phase `{s.get('phase')}`. "
         "Ids, statuses and counts only; every number is recomputable from the files under `outputs/`.", "",
         "## Completion", "", "| Task | Variant | Complete | Incomplete | Stopped | Failed | Unfinished |",
         "|---|---|---|---|---|---|---|"]
    for kind, by in s["completion"].items():
        for var, c in by.items():
            L.append(f"| {kind} | {var} | {c['complete']} | {c['incomplete']} | {c['stopped']} | {c['failed']} | "
                     f"{c['unfinished']} |")
    ag = s["agreement"]
    L += ["", "## Agreement between the judges (OpenAI vs Claude, same drafts, same fact lists)", "",
          "| Comparison | Four marks: raw; kappa (95% CI) | Present vs not: raw; kappa (95% CI) |", "|---|---|---|",
          f"| A1, all strategies | {_agr(ag['A1']['all_strategies']['four_marks'])} | "
          f"{_agr(ag['A1']['all_strategies']['present_vs_not'])} |"]
    for st, v in ag["A1"]["by_strategy"].items():
        L.append(f"| A1, {LABELS.get(st, st)} | {_agr(v['four_marks'])} | {_agr(v['present_vs_not'])} |")
    for arm, v in ag["A3"].items():
        L.append(f"| A3, {LABELS.get(arm, arm)} | {_agr(v['four_marks'])} | {_agr(v['present_vs_not'])} |")
    for k, v in ag["claude_self_baseline"].items():
        if isinstance(v, dict):
            L.append(f"| Baseline: {k.replace('_', ' ')} | {_agr(v['four_marks'])} | {_agr(v['present_vs_not'])} |")
    L += ["", "| Availability | Three verdicts: raw; kappa | Stated vs not: raw; kappa |", "|---|---|---|",
          f"| Own text (gaps --frozen) | {_agr(ag['A2']['own_text']['three_verdicts'])} | "
          f"{_agr(ag['A2']['own_text']['stated_vs_not'])} |",
          f"| Other papers (gaps --conveyed) | {_agr(ag['A2']['other_papers']['three_verdicts'])} | "
          f"{_agr(ag['A2']['other_papers']['stated_vs_not'])} |"]
    a1 = s["A1"]
    L += ["", f"## A1: OMIM facts conveyed under each judge ({a1['n_entries']} entries)", "",
          "| Strategy | OpenAI judge | Claude judge | Minus direct, OpenAI judge | Minus direct, Claude judge |",
          "|---|---|---|---|---|"]
    for st, c in a1["coverage"].get("openai", {}).items():
        L.append(f"| {LABELS.get(st, st)} | {_pct(c['mean_over_entries'])} | "
                 f"{_pct(a1['coverage']['claude'][st]['mean_over_entries'])} | "
                 f"{_pp(a1['versus_direct']['openai'].get(st))} | {_pp(a1['versus_direct']['claude'].get(st))} |")
    b1 = s["B1"]
    L += ["", f"## B1: the OpenAI writer ({b1['n_entries']} entries)", "",
          "| Strategy | OpenAI writer, OpenAI judge | Claude writer, Claude judge | Claude writer, OpenAI judge | "
          "OpenAI minus Claude writer (OpenAI judge) |", "|---|---|---|---|---|"]
    for st, c in b1["coverage"].get("openai_writer_openai_judge", {}).items():
        L.append(f"| {LABELS.get(st, st)} | {_pct(c['mean_over_entries'])} | "
                 f"{_pct(b1['coverage']['claude_writer_claude_judge'][st]['mean_over_entries'])} | "
                 f"{_pct(b1['coverage']['claude_writer_openai_judge'][st]['mean_over_entries'])} | "
                 f"{_pp(b1['writer_effect'].get(st))} |")
    L += ["", "| Minus direct reading | OpenAI writer, OpenAI judge | Claude writer, Claude judge |", "|---|---|---|"]
    for st, row in b1["versus_direct"].get("openai_writer_openai_judge", {}).items():
        L.append(f"| {LABELS.get(st, st)} | {_pp(row)} | "
                 f"{_pp(b1['versus_direct']['claude_writer_claude_judge'].get(st))} |")
    sf = s["stated_facts"]
    L += ["", f"## Facts the available text states ({sf['n_entries']} entries; mean over entries)", "",
          "| Strategy | All, OpenAI | All, Claude | Stated, OpenAI | Stated, Claude | Not stated, OpenAI | "
          "Not stated, Claude |", "|---|---|---|---|---|---|---|"]
    if sf["n_entries"]:
        for st in sf["openai"]["all"]["all"]["by_strategy"]:
            def cell(j: str, r: str, st: str = st) -> str:
                return _pct(sf[j][r]["all"]["by_strategy"][st]["mean_over_entries"])

            L.append(f"| {LABELS.get(st, st)} | {cell('openai', 'all')} | {cell('claude', 'all')} | "
                     f"{cell('openai', 'stated')} | {cell('claude', 'stated')} | {cell('openai', 'not_stated')} | "
                     f"{cell('claude', 'not_stated')} |")
    cf = s["conveyed_facts"]
    L += ["", "## Conveyed facts in no supplied text (abstract- or title-only papers, conveyed in full)", "",
          f"Claude's stored classes: {_pct(cf.get('claude', {}).get('share_not_in_supplied_text'))}; with OpenAI's "
          f"re-check against the other papers: "
          f"{_pct(cf.get('claude_own_openai_other', {}).get('share_not_in_supplied_text'))} "
          f"({cf['n_entries']} entries)."]
    hf = s["hidden_fulltext"]
    L += ["", "## Hidden-full-text effect", "", "| | Entries | Full text | Abstract | Second-hand | Full text minus "
          "abstract | Second-hand minus abstract |", "|---|---|---|---|---|---|---|"]
    for judge in ("openai", "claude"):
        b = hf["A3"][judge]
        m = b["mean_over_entries"]
        L.append(f"| A3, {judge} judge | {b['n_entries']} | {_pct(m.get('fulltext_before_repair'))} | "
                 f"{_pct(m.get('abstract'))} | {_pct(m.get('secondhand'))} | "
                 f"{_pp(b.get('fulltext_before_repair_minus_abstract'))} | {_pp(b.get('secondhand_minus_abstract'))} |")
    for name, b in (("B2, OpenAI writer and judge", hf["B2"]["openai_writer_openai_judge"]),
                    ("B2 entries, Claude writer and judge", hf["B2"]["claude_writer_claude_judge_same_entries"])):
        m = b["mean_over_entries"]
        L.append(f"| {name} | {b['n_entries']} | {_pct(m.get('fulltext'))} | {_pct(m.get('abstract'))} | – | "
                 f"{_pp(b.get('fulltext_minus_abstract'))} | – |")
    u = s["usage"]
    L += ["", "## Requests, tokens, stops and cost", "",
          "| Wave | Requests | Replies | Stops | Invalid | Input tokens | Output tokens | Cost (USD) |",
          "|---|---|---|---|---|---|---|---|"]
    for w, c in u["by_wave"].items():
        L.append(f"| {w} | {c.get('requests', 0)} | {c.get('replies', 0)} | {c.get('stops', 0)} | "
                 f"{c.get('invalid', 0) + c.get('incomplete', 0)} | {c.get('input_tokens', 0):,} | "
                 f"{c.get('output_tokens', 0):,} | {c.get('cost_usd', 0):.2f} |")
    L += ["", "| Task | Requests | Stops | Input tokens | Output tokens | Cost (USD) |", "|---|---|---|---|---|---|"]
    for k, c in u["by_task_kind"].items():
        L.append(f"| {k} | {int(c.get('requests', 0))} | {int(c.get('stops', 0))} | {int(c.get('input_tokens', 0)):,} | "
                 f"{int(c.get('output_tokens', 0)):,} | {c.get('cost_usd', 0):.2f} |")
    r = s["redactions"]
    L += ["", f"Drafts written: {s['files']['drafts']}; spans replaced because they match OMIM's text: {r['spans']} "
          f"(in {len(r['drafts'])} drafts).", ""]
    return "\n".join(L)
