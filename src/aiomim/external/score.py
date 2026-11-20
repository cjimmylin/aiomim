"""Scoring of the published systems' drafts, and the summary across systems.

Per system and entry (`score_entry`, written to `runs/external/<system>/<mim>/eval.<system>.json`):

    (a) cited    OMIM facts conveyed, credited to paragraphs citing the paper (as in the paper):
                 `facts.eval_gold_text_frozen` against the entry's fixed fact lists
    (b) whole    the same, credited anywhere in the draft (`whole=True`; uncited blocks count here)
    (c) by availability  (a) and (b) restricted by whether the supplied text states the fact
                 (the stored `gaps` availability judgements in the omim100 entry's gold_facts.json;
                 "stated" = yes, "partly" = partly, "not_stated" = no)
    (d) audit    optional (`--audit`): the claim-level audit (`verify.verify_entry`), no repair, on
                 the paragraphs with mapped citations
    (e) uncited  the share of characters in blocks with no mapped citation
    (f) usage    requests, model calls, tokens, list-price cost and seconds from the adapter's ledger

The comparison strategies (direct reading, agentic curator, evidence graph, case table first)
come from run omim100 on the same entries: (a) and (c) from their stored frozen marks, (b)
from the stored whole-draft marks where present, otherwise computed once (the same
`eval_gold_text_frozen(whole=True)` path as `rescore --whole-draft`) and stored under
`runs/external/_baselines/<mim>/whole.<strategy>.json` (run omim100 is never modified).

The fixed fact lists are only read (never split here): an entry whose lists are missing is
an error. Fact wording never leaves runs/ and data/: eval files carry fact ids and judge notes,
the summary only numbers.

    PYTHONPATH=src python -m aiomim.external.score score --system paperqa2 [--entries ...] [--audit]
    PYTHONPATH=src python -m aiomim.external.score summarize [--systems paperqa2 storm graphrag]
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Any, Iterable

from ..models import GeneratedEntry, GoldEntry
from . import runs_root
from .adapt import entry_dir, load_output, to_entry, uncited_share
from .corpus import source_dir

log = logging.getLogger(__name__)

BASELINES = ("direct", "agent", "kg", "cohort")
BASELINE_LABELS = {"direct": "Direct reading", "agent": "Agentic curator", "kg": "Evidence graph",
                   "cohort": "Case table first"}
REFERENCE = "direct"
RESTRICTIONS = {"all": None, "stated": ("yes",), "stated_or_partly": ("yes", "partly"), "not_stated": ("no",)}
SCOPES = ("cited", "whole")
RESULTS = Path("results/external")
SEED = 7     # bootstrap seed, as compare / gaps


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
    from ..pipeline import _write as write

    write(path, data)


# --------------------------------------------------------------------------- #
# Shared inputs of one entry
# --------------------------------------------------------------------------- #


class EntryInputs:
    """Gold paragraphs, frozen fact lists, paper levels and availability verdicts of one entry (read-only)."""

    def __init__(self, mim: str, llm, store=None):
        from ..facts import FactStore, frozen_facts
        from ..gaps import availability_by_fact

        self.mim = mim
        src = source_dir(mim)
        self.gold = GoldEntry.model_validate(_read(src / "gold.json"))
        self.store = store or FactStore()
        paragraphs = self.gold.scoped_paragraphs
        self.records = frozen_facts(paragraphs, llm, self.store, split_missing=False) if paragraphs else []
        if any(r is None for r in self.records):
            raise RuntimeError(f"{mim}: a fixed fact list is missing from the store; not splitting anew")
        self.levels = {r["pmid"]: r.get("content_level", "not_retrieved") for r in _read(src / "papers.json")}
        self.avail = availability_by_fact(_read(src / "gold_facts.json"))


def by_availability(score: dict[str, Any], avail: dict[str, str]) -> dict[str, Any]:
    """Coverage of one scoring restricted by whether the supplied text states the fact."""
    from ..gaps import join_marks, restricted_tally

    rows, counts = join_marks(score, avail)
    out = {name: restricted_tally(rows, verdicts) for name, verdicts in RESTRICTIONS.items()}
    out["join"] = counts
    return out


def _cov(score: dict[str, Any] | None) -> float | None:
    return None if not score else score.get("coverage")


# --------------------------------------------------------------------------- #
# Ledger usage
# --------------------------------------------------------------------------- #


def ledger_usage(system: str, mim: str, paths: Iterable[Path] | None = None) -> dict[str, Any]:
    """Sum of the adapter's ledger lines tagged `<system>/<mim>` (or `<system>/<mim>/...`).

    Reads every *.jsonl under runs/external/<system>/ unless `paths` is given. `fresh_*` is what
    this pass spent; `full_*` what the requests cost when they were made (cached ones included).
    """
    tag = f"{system}/{mim}"
    paths = list(paths) if paths is not None else sorted((runs_root() / system).rglob("*.jsonl"))
    u = {"requests": 0, "chat_requests": 0, "embedding_requests": 0, "refused": 0, "errors": 0, "model_calls": 0,
         "cached": 0, "stops": 0, "fresh_input_tokens": 0, "fresh_output_tokens": 0, "fresh_cost_usd": 0.0,
         "fresh_call_seconds": 0.0, "full_input_tokens": 0, "full_output_tokens": 0, "full_cost_usd": 0.0,
         "full_call_seconds": 0.0, "ignored_params": set()}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = row.get("tag") or ""
            if t != tag and not t.startswith(tag + "/"):
                continue
            u["requests"] += 1
            u["ignored_params"].update(row.get("ignored_params") or [])
            if row.get("endpoint") == "/v1/embeddings":
                u["embedding_requests"] += 1
                continue
            u["chat_requests"] += 1
            status = row.get("status")
            if status == 400:
                u["refused"] += 1
                continue
            if status != 200:
                u["errors"] += 1
                continue
            u["stops"] += int(bool(row.get("safety_stop")))
            for k in ("input_tokens", "output_tokens"):
                u[f"full_{k}"] += int(row.get(k) or 0)
            u["full_cost_usd"] += float(row.get("cost_usd") or 0.0)
            u["full_call_seconds"] += float(row.get("call_seconds") or 0.0)
            if row.get("cached"):
                u["cached"] += 1
            else:
                u["model_calls"] += int(row.get("model_calls") or 1)
                for k in ("input_tokens", "output_tokens"):
                    u[f"fresh_{k}"] += int(row.get(k) or 0)
                u["fresh_cost_usd"] += float(row.get("cost_usd") or 0.0)
                u["fresh_call_seconds"] += float(row.get("call_seconds") or 0.0)
    u["ignored_params"] = sorted(u["ignored_params"])
    for k in ("fresh_cost_usd", "full_cost_usd", "fresh_call_seconds", "full_call_seconds"):
        u[k] = round(u[k], 4)
    return u


# --------------------------------------------------------------------------- #
# One system, one entry
# --------------------------------------------------------------------------- #


def score_entry(system: str, mim: str, llm, store=None, *, audit: bool = False) -> dict[str, Any]:
    """Score one saved output; writes and returns `eval.<system>.json`."""
    from ..facts import eval_gold_text_frozen

    output = load_output(system, mim)
    if output is None:
        raise FileNotFoundError(f"no output.json for {system}/{mim}")
    folder = entry_dir(system, mim)
    result: dict[str, Any] = {"mim": mim, "system": system, "usage": ledger_usage(system, mim),
                              "system_meta": {k: v for k, v in (output.get("meta") or {}).items()
                                              if k in ("package", "version", "calls", "stops", "seconds", "tag")}}
    if not output["blocks"]:
        result["stopped"] = output.get("stopped") or "no output"
        _write(folder / f"eval.{system}.json", result)
        return result
    inputs = EntryInputs(mim, llm, store)
    entry = to_entry(output)
    scores = {
        "cited": eval_gold_text_frozen(entry, inputs.gold, inputs.levels, llm, inputs.store, records=inputs.records),
        "whole": eval_gold_text_frozen(entry, inputs.gold, inputs.levels, llm, inputs.store, whole=True,
                                       records=inputs.records),
    }
    result.update(gold_text_frozen=scores["cited"], gold_text_frozen_whole=scores["whole"],
                  by_availability={s: by_availability(scores[s], inputs.avail) for s in SCOPES},
                  uncited=uncited_share(output), stopped=None)
    if audit:
        result["audit"] = audit_entry(entry, mim, llm, folder / f"entry.{system}.audited.json")
    _write(folder / f"eval.{system}.json", result)
    return result


def audit_entry(entry: GeneratedEntry, mim: str, llm, path: Path) -> dict[str, Any]:
    """Claim-level audit without repair, on the paragraphs with mapped citations."""
    from ..gaps import load_entry_papers
    from ..verify import verdict_counts, verify_entry

    papers = load_entry_papers(source_dir(mim))
    verify_entry(entry, papers, llm)
    _write(path, entry.model_dump(mode="json"))
    counts = verdict_counts(entry)
    n = sum(counts.values())
    audited = [p for p in entry.all_paragraphs() if p.pmids]
    return {"paragraphs_audited": len(audited), "claims": n, "verdicts": counts,
            "supported_rate": round(counts.get("supported", 0) / n, 4) if n else None,
            "unsupported_or_contradicted_rate":
                round((counts.get("unsupported", 0) + counts.get("contradicted", 0)) / n, 4) if n else None}


# --------------------------------------------------------------------------- #
# Comparison strategies from omim100
# --------------------------------------------------------------------------- #


def baseline_whole_path(mim: str, strategy: str) -> Path:
    return runs_root() / "_baselines" / mim / f"whole.{strategy}.json"


def baseline_scores(mim: str, strategy: str, llm=None, store=None, *, compute: bool = False,
                    inputs: EntryInputs | None = None) -> dict[str, Any] | None:
    """A comparison strategy's (a), (b) and (c) on one entry; None when it wrote no draft.

    (b) is the stored whole-draft score if run omim100 has one, else the one stored by this
    module, else (with `compute`) computed now and stored; otherwise left out.
    """
    from ..facts import eval_gold_text_frozen

    src = source_dir(mim)
    path = src / f"eval.{strategy}.json"
    if not path.exists():
        return None
    evaluation = _read(path)
    if evaluation.get("stopped") or not evaluation.get("gold_text_frozen"):
        return None
    cited = evaluation["gold_text_frozen"]
    whole, whole_source = evaluation.get("gold_text_frozen_whole"), "omim100"
    if whole is None and baseline_whole_path(mim, strategy).exists():
        whole, whole_source = _read(baseline_whole_path(mim, strategy)), "external"
    if whole is None and compute:
        inputs = inputs or EntryInputs(mim, llm, store)
        entry = GeneratedEntry.model_validate(_read(src / f"entry.{strategy}.json"))
        whole = eval_gold_text_frozen(entry, inputs.gold, inputs.levels, llm, inputs.store, whole=True,
                                      records=inputs.records)
        _write(baseline_whole_path(mim, strategy), whole)
        whole_source = "external"
    from ..gaps import availability_by_fact

    avail = inputs.avail if inputs else availability_by_fact(_read(src / "gold_facts.json"))
    out = {"cited": cited, "whole": whole, "whole_source": whole_source if whole else None,
           "by_availability": {"cited": by_availability(cited, avail)}}
    if whole:
        out["by_availability"]["whole"] = by_availability(whole, avail)
    return out


def score_system(system: str, entries: Iterable[str] | None = None, *, audit: bool = False,
                 baselines: bool = True, jobs: int = 1) -> dict[str, Any]:
    """Score every saved output of a system (or the given entries) and, by default, compute the
    missing whole-draft scores of the comparison strategies on the same entries."""
    from concurrent.futures import ThreadPoolExecutor

    from ..facts import FactStore
    from ..llm import LLM

    llm, store = LLM(), FactStore()
    folder = runs_root() / system
    wanted = list(entries) if entries is not None else sorted(
        p.parent.name for p in folder.glob("*/output.json"))

    def one(mim: str) -> dict[str, Any]:
        try:
            r = score_entry(system, mim, llm, store, audit=audit)
            if baselines and not r.get("stopped"):
                inputs = EntryInputs(mim, llm, store)
                for s in BASELINES:
                    baseline_scores(mim, s, llm, store, compute=True, inputs=inputs)
            return {"mim": mim, "cited": _cov(r.get("gold_text_frozen")),
                    "whole": _cov(r.get("gold_text_frozen_whole")), "stopped": r.get("stopped")}
        except Exception as exc:  # noqa: BLE001 - report and continue with the other entries
            log.exception("[%s/%s] scoring failed", system, mim)
            return {"mim": mim, "error": f"{type(exc).__name__}: {exc}"}

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        rows = list(pool.map(one, wanted))
    return {"system": system, "entries": rows, "judge_usage": llm.usage.summary()["total"]}


# --------------------------------------------------------------------------- #
# Summary across systems
# --------------------------------------------------------------------------- #


def _measures(ev: dict[str, Any]) -> dict[str, float | None]:
    """The per-entry measures compared: (a), (b) and their restrictions by availability."""
    out: dict[str, float | None] = {"cited": _cov(ev.get("cited")), "whole": _cov(ev.get("whole"))}
    for scope in SCOPES:
        cells = (ev.get("by_availability") or {}).get(scope) or {}
        for name in ("stated", "stated_or_partly", "not_stated"):
            cell = cells.get(name)
            out[f"{scope}_{name}"] = cell.get("coverage") if cell else None
    return out


MEASURE_LABELS = {
    "cited": "(a) facts conveyed, credited to paragraphs citing the paper",
    "whole": "(b) facts conveyed, credited anywhere in the draft",
    "cited_stated": "(c) (a) on facts the supplied text states",
    "cited_stated_or_partly": "(c) (a) on facts the supplied text states or partly states",
    "cited_not_stated": "(c) (a) on facts the supplied text does not state",
    "whole_stated": "(c) (b) on facts the supplied text states",
    "whole_stated_or_partly": "(c) (b) on facts the supplied text states or partly states",
    "whole_not_stated": "(c) (b) on facts the supplied text does not state",
}


def _system_eval(system: str, mim: str) -> dict[str, Any] | None:
    path = entry_dir(system, mim) / f"eval.{system}.json"
    if not path.exists():
        return None
    ev = _read(path)
    return {**ev, "cited": ev.get("gold_text_frozen"), "whole": ev.get("gold_text_frozen_whole")}


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def summarize(systems: Iterable[str] | None = None, out_dir: Path = RESULTS) -> dict[str, Any]:
    """`external.json` and `external.md` for whatever systems have scored results."""
    from ..compare import _pair_stats

    root = runs_root()
    if systems is None:
        systems = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")
                         and p.name != "echo") if root.exists() else []
    systems = list(systems)
    report: dict[str, Any] = {
        "experiment": "B: published systems as released (docs/experiments-round2.md)",
        "reference": REFERENCE, "baselines": list(BASELINES), "baseline_run": "omim100",
        "bootstrap": {"seed": SEED, "resamples": 10_000, "interval": "percentile 95%, over entries"},
        "coverage": "present + half partial, over judged facts of the fixed lists",
        "measures": MEASURE_LABELS, "systems": {},
    }
    for system in systems:
        rng = random.Random(SEED)
        outputs = sorted(p.parent.name for p in (root / system).glob("*/output.json"))
        evals = {m: _system_eval(system, m) for m in outputs}
        completed = [m for m, ev in evals.items() if ev and not ev.get("stopped")]
        stopped = {m: ev.get("stopped") for m, ev in evals.items() if ev and ev.get("stopped")}
        unscored = [m for m, ev in evals.items() if ev is None]
        base = {s: {m: baseline_scores(m, s) for m in completed} for s in BASELINES}
        arms = {system: {m: evals[m] for m in completed}, **base}
        per_arm: dict[str, Any] = {}
        for arm, by_entry in arms.items():
            vals = {m: _measures(ev) if ev else None for m, ev in by_entry.items()}
            per_arm[arm] = {"means": {k: _mean([v[k] for v in vals.values() if v and v[k] is not None])
                                      for k in MEASURE_LABELS},
                            "n": {k: sum(1 for v in vals.values() if v and v[k] is not None) for k in MEASURE_LABELS},
                            "_vals": vals}
        paired: dict[str, Any] = {}
        ref_vals = per_arm[REFERENCE]["_vals"]
        for arm in [system, *[s for s in BASELINES if s != REFERENCE]]:
            paired[arm] = {}
            for k in MEASURE_LABELS:
                pairs = [(v[k], ref_vals[m][k]) for m, v in per_arm[arm]["_vals"].items()
                         if v and ref_vals.get(m) and v[k] is not None and ref_vals[m][k] is not None]
                paired[arm][k] = _pair_stats(pairs, True, rng) if pairs else None
        for arm in per_arm.values():
            arm.pop("_vals")
        usage_rows = [evals[m].get("usage") or {} for m in outputs if evals.get(m)]
        usage = {k: round(sum(u.get(k, 0) for u in usage_rows), 4) for k in
                 ("requests", "chat_requests", "embedding_requests", "model_calls", "cached", "stops", "refused",
                  "errors", "full_input_tokens", "full_output_tokens", "full_cost_usd", "full_call_seconds")}
        uncited = [evals[m]["uncited"]["uncited_share"] for m in completed
                   if (evals[m].get("uncited") or {}).get("uncited_share") is not None]
        audits = [evals[m]["audit"] for m in completed if evals[m].get("audit")]
        report["systems"][system] = {
            "entries_with_output": outputs, "completed": completed, "stopped": stopped, "unscored": unscored,
            "arms": per_arm, "paired_vs_direct": paired,
            "uncited_share_mean": _mean(uncited),
            "audit": _pool_audits(audits) if audits else None,
            "usage": usage, "usage_per_entry": {k: round(v / len(outputs), 2) for k, v in usage.items()} if outputs else {},
            "settings_changed": _settings(system, outputs),
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "external.json", report)
    (out_dir / "external.md").write_text(summary_markdown(report), encoding="utf-8")
    return report


def _pool_audits(audits: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts: dict[str, int] = {}
    for a in audits:
        for k, v in (a.get("verdicts") or {}).items():
            verdicts[k] = verdicts.get(k, 0) + v
    n = sum(verdicts.values())
    return {"entries": len(audits), "claims": n, "verdicts": verdicts,
            "supported_rate": round(verdicts.get("supported", 0) / n, 4) if n else None,
            "unsupported_or_contradicted_rate":
                round((verdicts.get("unsupported", 0) + verdicts.get("contradicted", 0)) / n, 4) if n else None}


def _settings(system: str, outputs: list[str]) -> dict[str, Any]:
    """Settings changed from the package's defaults, as the integration recorded them (first entry;
    entries that recorded a different list are named)."""
    lists = {}
    meta0: dict[str, Any] = {}
    for m in outputs:
        out = load_output(system, m) or {}
        meta = out.get("meta") or {}
        meta0 = meta0 or meta
        lists[m] = json.dumps(meta.get("settings_changed") or [], sort_keys=True)
    if not lists:
        return {"package": None, "version": None, "settings": [], "differs_on": []}
    first = next(iter(lists.values()))
    return {"package": meta0.get("package"), "version": meta0.get("version"),
            "settings": json.loads(first), "differs_on": [m for m, v in lists.items() if v != first]}


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def _diff(cell: dict[str, Any] | None) -> str:
    if not cell:
        return "–"
    ci = cell.get("ci95")
    ci_txt = f" ({100 * ci[0]:+.1f} to {100 * ci[1]:+.1f})" if ci else ""
    p = cell.get("sign_test_p")
    return (f"{100 * cell['difference']:+.1f}{ci_txt}; {cell['better']}/{cell['worse']}/{cell['ties']}"
            + (f"; p={p:.3f}" if p is not None else ""))


def summary_markdown(report: dict[str, Any]) -> str:
    lines = ["# Experiment B: published systems as released", "",
             "OMIM facts conveyed (present + half partial, over judged facts of the fixed lists). Comparison "
             "strategies from run omim100 on the entries each system completed. Paired differences from direct "
             "reading in points: mean (bootstrap 95% interval); better/worse/tied; sign test p.", ""]
    if not report["systems"]:
        lines.append("No system has results yet.")
    for system, s in report["systems"].items():
        arms = [system, *BASELINES]
        lines += [f"## {system}", "",
                  f"Entries with output: {len(s['entries_with_output'])}; completed: {len(s['completed'])}; "
                  f"stopped: {len(s['stopped'])}" + (f" ({', '.join(s['stopped'])})" if s["stopped"] else "")
                  + (f"; not scored: {', '.join(s['unscored'])}" if s["unscored"] else "") + ".", ""]
        lines.append("| Measure | " + " | ".join(BASELINE_LABELS.get(a, a) for a in arms) + " |")
        lines.append("|---|" + "---|" * len(arms))
        for k, label in MEASURE_LABELS.items():
            cells = []
            for a in arms:
                n = s["arms"][a]["n"][k]
                cells.append(f"{_pct(s['arms'][a]['means'][k])} (n={n})" if n else "–")
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines += ["", "Paired differences from direct reading:", "",
                  "| Measure | " + " | ".join(BASELINE_LABELS.get(a, a) for a in s["paired_vs_direct"]) + " |",
                  "|---|" + "---|" * len(s["paired_vs_direct"])]
        for k, label in MEASURE_LABELS.items():
            lines.append(f"| {label} | " + " | ".join(_diff(s["paired_vs_direct"][a][k])
                                                     for a in s["paired_vs_direct"]) + " |")
        u = s["usage"]
        lines += ["", f"(e) Share of characters in blocks with no mapped citation (mean over entries): "
                      f"{_pct(s['uncited_share_mean'])}.", ""]
        if s["audit"]:
            a = s["audit"]
            lines += [f"(d) Claim-level audit without repair, paragraphs with mapped citations: {a['claims']} claims "
                      f"on {a['entries']} entries; supported {_pct(a['supported_rate'])}, unsupported or "
                      f"contradicted {_pct(a['unsupported_or_contradicted_rate'])}.", ""]
        lines += [f"(f) Usage (all entries, from the adapter's ledger, as made): {u['chat_requests']:.0f} chat "
                  f"requests, {u['model_calls']:.0f} model calls made in this pass, {u['cached']:.0f} cached, "
                  f"{u['stops']:.0f} safety stops, {u['refused']:.0f} refused, {u['errors']:.0f} errors; "
                  f"{u['full_input_tokens']:,.0f} input and {u['full_output_tokens']:,.0f} output tokens; "
                  f"${u['full_cost_usd']:.2f} at list price; {u['full_call_seconds']:.0f} s of model time; "
                  f"{u['embedding_requests']:.0f} embedding requests.", ""]
        st = s["settings_changed"]
        lines += [f"Settings changed from the defaults of {st['package'] or system} {st['version'] or ''}".rstrip()
                  + ":", "", "| Setting | Default | Value | Reason |", "|---|---|---|---|"]
        for row in st["settings"]:
            lines.append(f"| {row.get('setting')} | {row.get('default', '')} | {row.get('value', '')} | "
                         f"{row.get('reason', '')} |")
        if st["differs_on"]:
            lines.append(f"\nEntries that recorded different settings: {', '.join(st['differs_on'])}.")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.external.score")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score", help="score a system's saved outputs")
    sc.add_argument("--system", required=True)
    sc.add_argument("--entries", nargs="*")
    sc.add_argument("--audit", action="store_true", help="(d) claim-level audit without repair (costs calls)")
    sc.add_argument("--no-baselines", action="store_true",
                    help="do not compute missing whole-draft scores of the comparison strategies")
    sc.add_argument("--jobs", type=int, default=2)
    bl = sub.add_parser("baselines", help="compute missing whole-draft scores of comparison strategies")
    bl.add_argument("--entries", nargs="+", required=True)
    bl.add_argument("--strategies", nargs="*", default=list(BASELINES))
    sm = sub.add_parser("summarize", help=f"write {RESULTS}/external.json and external.md")
    sm.add_argument("--systems", nargs="*")
    sm.add_argument("--out", default=str(RESULTS))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.cmd == "score":
        print(json.dumps(score_system(args.system, args.entries, audit=args.audit,
                                      baselines=not args.no_baselines, jobs=args.jobs), indent=1))
    elif args.cmd == "baselines":
        from ..facts import FactStore
        from ..llm import LLM

        llm, store = LLM(), FactStore()
        for mim in args.entries:
            inputs = EntryInputs(mim, llm, store)
            for strat in args.strategies:
                b = baseline_scores(mim, strat, llm, store, compute=True, inputs=inputs)
                print(mim, strat, None if b is None else (_cov(b["cited"]), _cov(b["whole"]), b["whole_source"]))
        print(json.dumps(llm.usage.summary()["total"]))
    else:
        r = summarize(args.systems, Path(args.out))
        print(json.dumps({s: {"completed": len(v["completed"]),
                              "means": v["arms"][s]["means"]} for s, v in r["systems"].items()}, indent=1))


if __name__ == "__main__":
    main()
