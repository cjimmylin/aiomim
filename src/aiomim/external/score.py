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


def ledger_usage(system: str, mim: str, paths: Iterable[Path] | None = None, *,
                 skip_steps: Iterable[str] = ()) -> dict[str, Any]:
    """Sum of the adapter's ledger lines tagged `<system>/<mim>` (or `<system>/<mim>/...`).

    Reads every *.jsonl under runs/external/<system>/ unless `paths` is given. `fresh_*` is what
    this pass spent; `full_*` what the requests cost when they were made (cached ones included).
    """
    tag = f"{system}/{mim}"
    skip = {f"{tag}/{step}" for step in skip_steps}
    paths = list(paths) if paths is not None else sorted((runs_root() / system).rglob("*.jsonl"))
    u = {"requests": 0, "chat_requests": 0, "embedding_requests": 0, "refused": 0, "errors": 0, "model_calls": 0,
         "cached": 0, "stops": 0, "fresh_input_tokens": 0, "fresh_output_tokens": 0, "fresh_cost_usd": 0.0,
         "fresh_call_seconds": 0.0, "full_input_tokens": 0, "full_output_tokens": 0, "full_cost_usd": 0.0,
         "full_call_seconds": 0.0, "distinct_requests": 0, "distinct_stops": 0, "distinct_input_tokens": 0,
         "distinct_output_tokens": 0, "distinct_cost_usd": 0.0, "distinct_call_seconds": 0.0,
         "ignored_params": set()}
    # `distinct_*`: each distinct request (the adapter's cache key) counted once, with the figures it
    # had when it was made. A re-run or re-save of an entry from the cache repeats its requests as
    # cached lines; `full_*` counts them again, `distinct_*` does not. Requests first made by another
    # run (a cached line whose key never appears fresh here) are counted too: they are calls the
    # system needed, paid earlier. `model_calls` / `fresh_*` are the calls paid in these ledgers.
    seen: set[str] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = row.get("tag") or ""
            if t != tag and not t.startswith(tag + "/"):
                continue
            if skip and any(t == x or t.startswith(x + "/") for x in skip):
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
            key = row.get("key") or f"line:{path}:{u['requests']}"
            if key not in seen:
                seen.add(key)
                u["distinct_requests"] += 1
                u["distinct_stops"] += int(bool(row.get("safety_stop")))
                for k in ("input_tokens", "output_tokens"):
                    u[f"distinct_{k}"] += int(row.get(k) or 0)
                u["distinct_cost_usd"] += float(row.get("cost_usd") or 0.0)
                u["distinct_call_seconds"] += float(row.get("call_seconds") or 0.0)
            if row.get("cached"):
                u["cached"] += 1
            else:
                u["model_calls"] += int(row.get("model_calls") or 1)
                for k in ("input_tokens", "output_tokens"):
                    u[f"fresh_{k}"] += int(row.get(k) or 0)
                u["fresh_cost_usd"] += float(row.get("cost_usd") or 0.0)
                u["fresh_call_seconds"] += float(row.get("call_seconds") or 0.0)
    u["ignored_params"] = sorted(u["ignored_params"])
    for k in ("fresh_cost_usd", "full_cost_usd", "fresh_call_seconds", "full_call_seconds", "distinct_cost_usd",
              "distinct_call_seconds"):
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
            + (f"; p={p:.3f}" if p is not None else "") + f"; n={cell['n']}")


SYSTEM_LABELS = {
    "paperqa_pooled": "PaperQA2",
    "paperqa": "PaperQA2, 512-token embedding cut",
    "graphrag": "GraphRAG local",
    "graphrag_global": "GraphRAG global",
    "storm": "STORM",
}
SYSTEM_ROLES = {
    "paperqa_pooled": "main PaperQA2 result (whole-chunk embeddings)",
    "paperqa": "sensitivity result (the shared embedder's 512-token cut)",
    "graphrag": "main GraphRAG result (local search, the CLI's default)",
    "graphrag_global": "GraphRAG global search on the same indexes",
    "storm": "no article produced",
}
ENTRY_POINTS = {
    "graphrag": "`graphrag index --method standard` (CLI), then `graphrag.cli.query.run_local_search` per question "
                "with the CLI's defaults",
    "graphrag_global": "the same indexes as GraphRAG local; `graphrag.cli.query.run_global_search` per question "
                       "with the CLI's defaults",
    "storm": "`STORMWikiRunner.run` (research, outline, article, polish) with its default arguments",
}
#: Systems whose index is shared: (system) -> (system that holds the index ledger, steps that are not index)
SHARED_INDEX = {"graphrag_global": ("graphrag", ("local_search", "global_search"))}
AUDITED = ("paperqa_pooled", "graphrag")
_GRAPHRAG_KINDS = {"share_sources": "sources", "share_entities_relationships": "entities/relationships only",
                   "share_reports_only": "community reports only", "share_none": "none"}


def _label(arm: str) -> str:
    return SYSTEM_LABELS.get(arm) or BASELINE_LABELS.get(arm, arm)


def _arm_eval(arm: str, mim: str) -> dict[str, Any] | None:
    if arm in BASELINES:
        return baseline_scores(mim, arm)
    ev = _system_eval(arm, mim)
    return None if ev is None or ev.get("stopped") else ev


def _compare(arms: list[str], entries: list[str]) -> dict[str, Any]:
    """Means of every measure per arm and paired differences from direct reading, on `entries`."""
    rng = random.Random(SEED)
    vals = {a: {m: (_measures(ev) if (ev := _arm_eval(a, m)) else None) for m in entries} for a in arms}
    out: dict[str, Any] = {"entries": list(entries), "arms": {}, "paired_vs_direct": {}, "per_entry": {}}
    for a in arms:
        out["arms"][a] = {"means": {k: _mean([v[k] for v in vals[a].values() if v and v[k] is not None])
                                    for k in MEASURE_LABELS},
                          "n": {k: sum(1 for v in vals[a].values() if v and v[k] is not None) for k in MEASURE_LABELS}}
        out["per_entry"][a] = {m: ({k: v[k] for k in ("cited", "whole")} if v else None) for m, v in vals[a].items()}
    ref = vals.get(REFERENCE) or {m: (_measures(ev) if (ev := _arm_eval(REFERENCE, m)) else None) for m in entries}
    for a in arms:
        if a == REFERENCE:
            continue
        out["paired_vs_direct"][a] = {}
        for k in MEASURE_LABELS:
            pairs = [(v[k], ref[m][k]) for m, v in vals[a].items()
                     if v and ref.get(m) and v[k] is not None and ref[m][k] is not None]
            out["paired_vs_direct"][a][k] = _pair(pairs, rng) if pairs else None
    return out


def _pair(pairs: list[tuple[float, float]], rng: random.Random, resamples: int = 10_000) -> dict[str, Any]:
    """`compare._pair_stats`, with the percentile bootstrap interval computed also below 5 entries
    (where `compare` leaves it out): the design asks for it at every size. With 4 entries the
    resampling distribution has at most 35 distinct means; `ci_unreliable` marks n < 20."""
    from ..compare import _pair_stats

    stats = _pair_stats(pairs, True, rng)
    if stats.get("ci95") is None and len(pairs) >= 2:
        diffs = [a - b for a, b in pairs]
        k = len(diffs)
        means = sorted(sum(rng.choices(diffs, k=k)) / k for _ in range(resamples))
        stats["ci95"] = [round(means[int(0.025 * resamples)], 4), round(means[int(0.975 * resamples) - 1], 4)]
    return stats


def _run_log_seconds(system: str) -> dict[str, float]:
    """Wall seconds per entry from the run logs (one JSON object per line with `mim` and `seconds`):
    the record the run printed when it made the calls. The first record of an entry wins."""
    out: dict[str, float] = {}
    for path in sorted((runs_root() / system).glob("*.log")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and str(row.get("mim", "")) and row.get("seconds") and row.get("calls"):
                out.setdefault(str(row["mim"]), float(row["seconds"]))
    return out


def wall_seconds(system: str, mim: str, output: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wall-clock seconds of one entry, with where the figure comes from.

    - GraphRAG: indexing (every recorded index attempt) + querying. Querying is the query run's own
      wall time where recorded, otherwise the sum of the per-question seconds the integration kept.
    - A saved output whose run asked every request from the cache (a re-save) has no real wall time
      of its own: the run log's record of the run that made the calls is used where there is one,
      otherwise none is given.
    """
    output = output or load_output(system, mim) or {}
    meta = output.get("meta") or {}
    if "index_status" in meta:
        index = sum(float(a.get("seconds") or 0) for a in (meta.get("index_status") or {}).get("attempts") or [])
        run = meta.get("query_run") or {}
        if run.get("seconds"):
            return {"seconds": round(index + float(run["seconds"]), 1), "index_seconds": round(index, 1),
                    "source": "index attempts + query run"}
        return {"seconds": round(index + float(meta.get("seconds") or 0), 1), "index_seconds": round(index, 1),
                "source": "index attempts + sum of per-question seconds in meta"}
    chat, cached = meta.get("chat_requests_this_run"), meta.get("cached_requests_this_run")
    logged = _run_log_seconds(system).get(mim)
    all_cached = bool(chat) and chat == cached
    if logged is not None and (all_cached or abs(logged - float(meta.get("seconds") or 0)) > 0.5):
        return {"seconds": logged, "source": "run log (the saved output's own seconds are a cached re-save)"
                if all_cached else "run log"}
    if all_cached:
        return {"seconds": None, "source": "every request served from the cache; no wall time of its own"}
    if chat and cached:
        return {"seconds": meta.get("seconds"),
                "source": f"recorded; {cached} of {chat} requests served from the cache (understates)"}
    return {"seconds": meta.get("seconds"), "source": "recorded"}


def system_usage(system: str, mim: str) -> dict[str, Any]:
    """Calls, tokens, list-price cost and model seconds one entry needed, each distinct request once.

    GraphRAG: indexing (every step but the searches, from `graphrag`'s ledger) plus the search the
    system used (local search from `graphrag`'s ledger; global search from `graphrag_global`'s)."""
    graph_steps = ("connectivity", "extract_graph", "summarize_descriptions", "community_reports", "embeddings")
    if system == "graphrag":
        parts = {"index": ledger_usage(system, mim, skip_steps=("local_search", "global_search")),
                 "query": ledger_usage(system, mim, skip_steps=(*graph_steps, "global_search"))}
    elif system in SHARED_INDEX:
        holder, skip = SHARED_INDEX[system]
        parts = {"index": ledger_usage(holder, mim, skip_steps=skip), "query": ledger_usage(system, mim)}
    else:
        parts = {"all": ledger_usage(system, mim)}
    total = {"calls": sum(p["distinct_requests"] for p in parts.values()),
             "fresh_calls": sum(p["model_calls"] for p in parts.values()),
             "stops": sum(p["distinct_stops"] for p in parts.values()),
             "input_tokens": sum(p["distinct_input_tokens"] for p in parts.values()),
             "output_tokens": sum(p["distinct_output_tokens"] for p in parts.values()),
             "cost_usd": round(sum(p["distinct_cost_usd"] for p in parts.values()), 4),
             "model_seconds": round(sum(p["distinct_call_seconds"] for p in parts.values()), 1),
             "ledger_chat_lines": sum(p["chat_requests"] - p["refused"] - p["errors"] for p in parts.values()),
             "ledger_full_cost_usd": round(sum(p["full_cost_usd"] for p in parts.values()), 4)}
    if len(parts) > 1:
        total["parts"] = {k: {"calls": p["distinct_requests"], "cost_usd": p["distinct_cost_usd"]}
                          for k, p in parts.items()}
    return total


def baseline_usage(mim: str, strategy: str) -> dict[str, Any] | None:
    """A comparison strategy's generation cost on one entry from run omim100 (`usage.json`, figures as made);
    the audit and repair round (`audit/*`) separately. Wall time is recorded per entry, not per strategy."""
    path = source_dir(mim) / "usage.json"
    if not path.exists():
        return None
    stages = ((_read(path).get("by_strategy") or {}).get(strategy)) or {}

    def tally(prefix: str) -> dict[str, Any]:
        rows = [v for k, v in stages.items() if k.startswith(prefix)]
        return {"calls": sum(int(r.get("calls") or 0) for r in rows),
                "input_tokens": sum(int(r.get("full_input_tokens") or 0) for r in rows),
                "output_tokens": sum(int(r.get("full_output_tokens") or 0) for r in rows),
                "cost_usd": round(sum(float(r.get("full_list_price_usd") or 0) for r in rows), 4),
                "model_seconds": round(sum(float(r.get("full_seconds") or 0) for r in rows), 1)}

    return {**tally("generate/"), "audit_repair": tally("audit/")}


def text_stats(arm: str, mim: str) -> dict[str, Any] | None:
    """Characters written and the share with no mapped citation (GraphRAG: by kind of mapping)."""
    if arm in BASELINES:
        path = source_dir(mim) / f"entry.{arm}.json"
        if not path.exists():
            return None
        entry = GeneratedEntry.model_validate(_read(path))
        paras = entry.all_paragraphs()
        total = sum(len(p.text) for p in paras)
        unc = sum(len(p.text) for p in paras if not p.pmids)
        return {"chars": total, "uncited_share": round(unc / total, 4) if total else None}
    output = load_output(arm, mim)
    if not output or not output.get("blocks"):
        return None
    u = uncited_share(output)
    out = {"chars": u["chars"], "uncited_share": u["uncited_share"]}
    mapping = (output.get("meta") or {}).get("mapping")
    if mapping and "share_none" in mapping:
        out["by_kind"] = {label: mapping.get(k) for k, label in _GRAPHRAG_KINDS.items()}
    return out


def length_cost(arms: list[str], entries: list[str]) -> dict[str, Any]:
    """Per arm: per-entry text, calls, tokens, cost and time, and their means over `entries`."""
    out: dict[str, Any] = {}
    for a in arms:
        rows = {}
        for m in entries:
            text = text_stats(a, m)
            if a in BASELINES:
                rows[m] = {"text": text, "usage": baseline_usage(m, a), "wall": None}
            else:
                rows[m] = {"text": text, "usage": system_usage(a, m), "wall": wall_seconds(a, m)}

        def mean(get) -> float | None:
            vals = [x for r in rows.values() if (x := get(r)) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        means = {
            "chars": mean(lambda r: (r["text"] or {}).get("chars")),
            "uncited_share": mean(lambda r: (r["text"] or {}).get("uncited_share")),
            "calls": mean(lambda r: (r["usage"] or {}).get("calls")),
            "input_tokens": mean(lambda r: (r["usage"] or {}).get("input_tokens")),
            "output_tokens": mean(lambda r: (r["usage"] or {}).get("output_tokens")),
            "cost_usd": mean(lambda r: (r["usage"] or {}).get("cost_usd")),
            "model_seconds": mean(lambda r: (r["usage"] or {}).get("model_seconds")),
            "wall_seconds": mean(lambda r: (r["wall"] or {}).get("seconds")),
            "wall_n": sum(1 for r in rows.values() if (r["wall"] or {}).get("seconds") is not None),
        }
        if a in BASELINES:
            for k in ("calls", "cost_usd", "model_seconds"):
                means[f"audit_repair_{k}"] = mean(lambda r, k=k: ((r["usage"] or {}).get("audit_repair") or {}).get(k))
        else:
            means["fresh_calls_total"] = sum((r["usage"] or {}).get("fresh_calls", 0) for r in rows.values())
        kinds = [r["text"]["by_kind"] for r in rows.values() if r["text"] and r["text"].get("by_kind")]
        if kinds:
            means["by_kind"] = {k: _mean([x[k] for x in kinds if x.get(k) is not None]) for k in kinds[0]}
        out[a] = {"means": means, "per_entry": rows}
    return out


def audit_figures(entries: list[str], systems: Iterable[str] = AUDITED) -> dict[str, Any]:
    """The claim-level audit without repair of the systems (step (d)) and, for comparison, the stored
    before-repair audit of the comparison strategies from run omim100, on the same entries."""
    out: dict[str, Any] = {"entries": list(entries), "arms": {}}
    keys = ("supported", "partially_supported", "unsupported", "contradicted", "not_checkable")
    for s in systems:
        per = {}
        for m in entries:
            ev = _system_eval(s, m) or {}
            if ev.get("audit"):
                per[m] = ev["audit"]
        if per:
            pooled = _pool_audits(list(per.values()))
            pooled["paragraphs_audited"] = sum(a.get("paragraphs_audited", 0) for a in per.values())
            pooled["sampled"] = {m: a["sample"] for m, a in per.items() if a.get("sample")}
            out["arms"][s] = {"pooled": pooled, "per_entry": {m: {"claims": a["claims"], "verdicts": a["verdicts"],
                                                                  "paragraphs_audited": a["paragraphs_audited"]}
                                                              for m, a in per.items()}}
    for b in BASELINES:
        per = {}
        for m in entries:
            path = source_dir(m) / f"entry.{b}.json"
            if not path.exists():
                continue
            before = (_read(path).get("meta") or {}).get("audit_before_repair")
            if before:
                per[m] = {"claims": before.get("n_claims", 0), "verdicts": {k: before.get(k, 0) for k in keys},
                          "paragraphs_audited": sum((before.get("paragraphs") or {}).values())}
        if per:
            pooled = _pool_audits(list(per.values()))
            pooled["paragraphs_audited"] = sum(a["paragraphs_audited"] for a in per.values())
            out["arms"][b] = {"pooled": pooled, "per_entry": per,
                              "source": "run omim100, entry meta audit_before_repair"}
    for arm in out["arms"].values():
        p = arm["pooled"]
        n = p["claims"]
        p["rates"] = {k: round(p["verdicts"].get(k, 0) / n, 4) if n else None for k in keys}
    return out


#: Deviations from the design (docs/experiments-round2.md, B), as run. Facts checked against the run
#: folders; the dynamic ones (entry counts, audit sample) are added by `summarize`.
DEVIATIONS = [
    "Reduced sizes (decided before any run finished, at the project owner's request): PaperQA2 and STORM on the "
    "first 10 entries of the seeded order instead of 24; GraphRAG within 1,000 model calls (floor 6 entries) "
    "instead of 3,000 (floor 12). Every result here is exploratory.",
    "PaperQA2 was run without its agent: `Docs.aadd` per paper and `Docs.aquery` per question (the README's "
    "'Manual (No Agent)' usage) instead of the default `agent_query` (`pqa ask`). The default agent selects tools "
    "by function calling, and the 'fake' agent ends with a function-calling Complete step; the adapter in front "
    "of the project's command-line model cannot serve tool calls. Retrieval, contextual summaries and the answer "
    "step are PaperQA2's own; the agent's iterative search and its decision to stop are not exercised.",
    "Embedding cut and re-run: the shared local embedder (bge-small-en-v1.5) truncates at 512 tokens, so the first "
    "PaperQA2 run (`paperqa`) embedded only the first ~510 tokens of each ~5,000-character chunk. PaperQA2 was "
    "re-run with whole-chunk embeddings (windows of 510 tokens averaged; `paperqa_pooled`), which is reported as "
    "the main result; the first run is kept as a sensitivity result. Requests identical between the two runs were "
    "served from the cache in the second, so its fresh calls understate what a stand-alone run costs (calls here "
    "count every distinct request once, wherever it was first made).",
    "GraphRAG on 4 entries (621313, 615582, 616326, 620029), below the design's floor of 6: the fixed in-order "
    "rule stopped when the fifth entry (611521) did not fit in what was left of the 1,000-call cap (the operator's "
    "projection; the tally in the ledgers is 698 calls, including the global-search queries and a smoke test).",
    "GraphRAG global search was added on the same 4 indexes (the CLI default is local search, which is the main "
    "GraphRAG result). Its citations name community reports only; a report is mapped to the papers of the text "
    "units its community's entities came from, a looser mapping than PaperQA2's (named papers) or local search's "
    "(text units, entities, relationships; a block's papers are the union over every record it cites, counting "
    "only records the query showed the model).",
    "STORM did not complete any entry: the model's safety filter stopped every chain-of-thought prompt of its "
    "research stage (30 of 30 fresh requests stopped; the 20 plain outline prompts were answered), so no article "
    "was produced. Per the rules, nothing was retried or reworded. STORM is reported as completion 0 of 10.",
    "The comparison strategies' drafts (run omim100) are the published drafts, after their one audit-and-repair "
    "round; the systems' drafts had none. The design treats every arm alike without repair; the repair round "
    "moved coverage by about 0.2 points in the hidden-full-text experiment, so this favours the comparison "
    "strategies very slightly at most. Their (a) and (c) come from stored marks; (b) from stored whole-draft "
    "marks where present, otherwise scored here once (the same path).",
    "Bookkeeping corrected in this summary: calls, tokens and cost count each distinct request once with the "
    "figures it had when made (the ledgers' `full_*` totals count cached re-runs again; PaperQA2's first-run "
    "entry 621313 was re-saved from the cache twice, tripling its `full_*` figures); the saved `seconds` of that "
    "entry (6.9 s) is a cached re-save and its real wall time (177.2 s) is taken from `runs/external/paperqa/"
    "pilot.log`; GraphRAG local's query seconds are the sum of per-question seconds in `meta` (no query-run "
    "record), added to the recorded index time. PaperQA2 (whole-chunk) entries 301059 and 621313 were served "
    "entirely from the cache (all requests identical to the first run) and have no wall time of their own; its "
    "other entries' wall times understate a stand-alone run for the same reason.",
    "Wall-clock time is not recorded per strategy in run omim100 (only per entry for all strategies together); "
    "for the comparison strategies, time is the sum of model-call seconds (`model_seconds`), which is also given "
    "for the systems. Systems ran with the adapter's concurrency cap of 3; the comparison strategies' generation "
    "is mostly one or a few calls.",
    "Systems were asked six fixed section questions (PaperQA2, GraphRAG) and their answers concatenated; the "
    "comparison strategies write an OMIM-style entry in one pass. GraphRAG's answers include headings and "
    "framing lines as separate blocks; all text counts for (b) and the uncited share.",
]


def summarize(systems: Iterable[str] | None = None, out_dir: Path = RESULTS) -> dict[str, Any]:
    """`external.json` and `external.md` for whatever systems have scored results."""
    root = runs_root()
    if systems is None:
        systems = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")
                         and p.name != "echo") if root.exists() else []
    order = [s for s in SYSTEM_LABELS if s in systems] + [s for s in systems if s not in SYSTEM_LABELS]
    report: dict[str, Any] = {
        "experiment": "B: published systems as released (docs/experiments-round2.md)",
        "reference": REFERENCE, "baselines": list(BASELINES), "baseline_run": "omim100",
        "bootstrap": {"seed": SEED, "resamples": 10_000, "interval": "percentile 95%, over entries"},
        "coverage": "present + half partial, over judged facts of the fixed lists",
        "measures": MEASURE_LABELS, "labels": {a: _label(a) for a in [*order, *BASELINES]}, "systems": {},
    }
    for system in order:
        outputs = sorted(p.parent.name for p in (root / system).glob("*/output.json"))
        evals = {m: _system_eval(system, m) for m in outputs}
        completed = [m for m, ev in evals.items() if ev and not ev.get("stopped")]
        stopped = {m: ev.get("stopped") for m, ev in evals.items() if ev and ev.get("stopped")}
        unscored = [m for m, ev in evals.items() if ev is None]
        meta0 = ((load_output(system, outputs[0]) or {}).get("meta") or {}) if outputs else {}
        stops = {m: system_usage(system, m)["stops"] for m in outputs}
        entry: dict[str, Any] = {
            "label": _label(system), "role": SYSTEM_ROLES.get(system),
            "package": meta0.get("package"), "version": meta0.get("version"),
            "entry_point": meta0.get("entry_point") or ENTRY_POINTS.get(system),
            "entries_attempted": outputs, "completed": completed, "stopped": stopped, "unscored": unscored,
            "safety_stops": sum(stops.values()), "safety_stops_by_entry": {m: n for m, n in stops.items() if n},
            "settings_changed": _settings(system, outputs),
        }
        if completed:
            cmp_ = _compare([system, *BASELINES], completed)
            entry.update(arms=cmp_["arms"], paired_vs_direct=cmp_["paired_vs_direct"], per_entry=cmp_["per_entry"],
                         length_cost=length_cost([system, *BASELINES], completed))
        else:
            entry["length_cost"] = length_cost([system], outputs)
        report["systems"][system] = entry
    producing = [s for s in order if report["systems"][s]["completed"]]
    common = sorted(set.intersection(*(set(report["systems"][s]["completed"]) for s in producing))) \
        if producing else []
    if common:
        arms = [*producing, *BASELINES]
        cmp_ = _compare(arms, common)
        report["common"] = {**cmp_, "systems": producing, "length_cost": length_cost(arms, common)}
        report["audit"] = audit_figures(common)
    deviations = list(DEVIATIONS)
    audit = report.get("audit") or {}
    sampled = {s: a["pooled"].get("sampled") for s, a in (audit.get("arms") or {}).items()
               if a["pooled"].get("sampled")}
    if audit.get("arms"):
        deviations.append(
            f"The claim-level audit without repair was run on the {len(common)} entries both PaperQA2 and GraphRAG "
            "completed, not on every entry of each system, "
            + ("on a seeded sample of paragraphs per entry (the same number for both systems): "
               + json.dumps(sampled) if sampled else "on every paragraph with mapped citations") + ".")
    inverted = []
    for s in producing:
        for m in report["systems"][s]["completed"]:
            pe = report["systems"][s]["per_entry"][s][m]
            if pe and pe["whole"] is not None and pe["cited"] is not None and pe["whole"] + 1e-9 < pe["cited"]:
                inverted.append(f"{s}/{m}")
    if inverted:
        deviations.append("Judge noise: (b) credits facts anywhere in the draft and should not fall below (a), but "
                          f"it does on {len(inverted)} system entr{'y' if len(inverted) == 1 else 'ies'} "
                          f"({', '.join(inverted)}): the two are separate judge passes, so differences of a few "
                          "points between them are within the judge's noise.")
    union = sorted({m for s in producing for m in report["systems"][s]["completed"]})
    repairs = {}
    for b in BASELINES:
        tally = {"flagged": 0, "revised": 0, "deleted": 0, "paragraphs": 0}
        for m in union:
            path = source_dir(m) / f"entry.{b}.json"
            if path.exists():
                data = _read(path)
                for k in ("flagged", "revised", "deleted"):
                    tally[k] += int(((data.get("meta") or {}).get("repair") or {}).get(k) or 0)
                tally["paragraphs"] += len(GeneratedEntry.model_validate(data).all_paragraphs())
        repairs[b] = tally
    report["baseline_repair"] = {"entries": union, "by_strategy": repairs}
    if union:
        deviations.append(
            f"Extent of the comparison strategies' repair round on these {len(union)} entries (paragraphs revised / "
            "deleted / in the final drafts): " + "; ".join(
                f"{_label(b)} {t['revised']} / {t['deleted']} / {t['paragraphs']}" for b, t in repairs.items()) + ".")
    report["deviations"] = deviations
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "external.json", report)
    (out_dir / "external.md").write_text(summary_markdown(report), encoding="utf-8")
    return report


def _num(x: float | None, fmt: str = "{:,.0f}") -> str:
    return "–" if x is None else fmt.format(x)


def _means_table(cmp_: dict[str, Any], arms: list[str], keys: Iterable[str]) -> list[str]:
    lines = ["| Measure | " + " | ".join(_label(a) for a in arms) + " |", "|---|" + "---|" * len(arms)]
    for k in keys:
        cells = []
        for a in arms:
            n = cmp_["arms"][a]["n"][k]
            cells.append(f"{_pct(cmp_['arms'][a]['means'][k])} (n={n})" if n else "–")
        lines.append(f"| {MEASURE_LABELS[k]} | " + " | ".join(cells) + " |")
    return lines


def _paired_table(cmp_: dict[str, Any], arms: list[str], keys: Iterable[str]) -> list[str]:
    arms = [a for a in arms if a in cmp_["paired_vs_direct"]]
    lines = ["| Measure | " + " | ".join(_label(a) for a in arms) + " |", "|---|" + "---|" * len(arms)]
    for k in keys:
        lines.append(f"| {MEASURE_LABELS[k]} | " + " | ".join(_diff(cmp_["paired_vs_direct"][a][k]) for a in arms)
                     + " |")
    return lines


_MAIN_KEYS = ("cited", "whole")
_SPLIT_KEYS = ("cited_stated", "cited_not_stated", "whole_stated", "whole_not_stated", "cited_stated_or_partly",
               "whole_stated_or_partly")


def _cost_table(lc: dict[str, Any], arms: list[str]) -> list[str]:
    lines = ["| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | "
             "Model seconds | Wall seconds |", "|---|---|---|---|---|---|---|---|---|"]
    for a in arms:
        m = lc[a]["means"]
        wall = (f"{_num(m['wall_seconds'])} (n={m['wall_n']})" if m["wall_seconds"] is not None else "not recorded")
        lines.append(f"| {_label(a)} | {_num(m['chars'])} | {_pct(m['uncited_share'])} | {_num(m['calls'], '{:,.1f}')} "
                     f"| {_num(m['input_tokens'])} | {_num(m['output_tokens'])} | "
                     f"{_num(m['cost_usd'], '${:,.2f}')} | {_num(m['model_seconds'])} | {wall} |")
    extra = []
    for a in arms:
        m = lc[a]["means"]
        if a in BASELINES and m.get("audit_repair_calls") is not None:
            extra.append(f"{_label(a)}: audit and repair round {_num(m['audit_repair_calls'], '{:,.1f}')} calls, "
                         f"{_num(m['audit_repair_cost_usd'], '${:,.2f}')}, {_num(m['audit_repair_model_seconds'])} "
                         "model seconds per entry (not included above)")
        if m.get("by_kind"):
            extra.append(f"{_label(a)}: share of characters by kind of mapping: "
                         + ", ".join(f"{k} {_pct(v)}" for k, v in m["by_kind"].items()))
    if extra:
        lines += [""] + [f"- {x}." for x in extra]
    return lines


def summary_markdown(report: dict[str, Any]) -> str:
    systems = report["systems"]
    lines = ["# Experiment B: published systems as released", "",
             "Design: `docs/experiments-round2.md`, section B, at the reduced sizes. OMIM facts conveyed "
             "(present + half partial, over judged facts of the fixed lists); comparison strategies from run "
             "omim100 on the same entries. Paired differences from direct reading are in points: mean (bootstrap "
             "95% interval over entries); better/worse/tied; exact sign test p. With 4 or 10 entries the intervals "
             "are wide and the sign test cannot reach p < 0.05 with 4 entries (the smallest possible p is 0.125): "
             "every result here is exploratory.", "",
             "## What was run", "",
             "| System | Package and version | Entry point | Entries attempted | Completed | Safety stops | Role |",
             "|---|---|---|---|---|---|---|"]
    for s, v in systems.items():
        lines.append(f"| {v['label']} | {v['package']} {v['version']} | {v['entry_point'] or ''} | "
                     f"{len(v['entries_attempted'])} | {len(v['completed'])} | {v['safety_stops']} | {v['role'] or ''} |")
    if "storm" in systems:
        st = systems["storm"]
        lines += ["", f"STORM: completion {len(st['completed'])} of {len(st['entries_attempted'])}. The model's safety "
                  "filter stopped every chain-of-thought prompt of STORM's research stage (30 of 30 fresh requests; "
                  "the 20 plain outline prompts were answered), so no article was produced; nothing was retried or "
                  "reworded. There is nothing to score."]
    lines += ["", "GraphRAG ran on 4 entries: the fixed rule takes entries in the seeded order while they fit in "
              "1,000 model calls; the fifth entry (611521) did not fit in what was left, so the run stopped below "
              "the design's floor of 6.", ""]
    common = report.get("common")
    if common:
        arms = [*common["systems"], *BASELINES]
        lines += [f"## Side by side on the {len(common['entries'])} entries every system completed", "",
                  f"Entries: {', '.join(common['entries'])}.", ""]
        lines += _means_table(common, arms, (*_MAIN_KEYS, *_SPLIT_KEYS))
        lines += ["", "Paired differences from direct reading:", ""]
        lines += _paired_table(common, arms, (*_MAIN_KEYS, "cited_stated", "cited_not_stated", "whole_stated",
                                               "whole_not_stated"))
        lines += ["", "Per entry, (a) / (b):", "", "| Entry | " + " | ".join(_label(a) for a in arms) + " |",
                  "|---|" + "---|" * len(arms)]
        for m in common["entries"]:
            cells = []
            for a in arms:
                pe = common["per_entry"][a].get(m)
                cells.append(f"{_pct(pe['cited'])} / {_pct(pe['whole'])}" if pe else "–")
            lines.append(f"| {m} | " + " | ".join(cells) + " |")
        lines += ["", "Text, calls, cost and time per entry (means over these entries):", ""]
        lines += _cost_table(common["length_cost"], arms)
        lines.append("")
    for s, v in systems.items():
        lines += [f"## {v['label']} on its own entries", ""]
        lines.append(f"Role: {v['role']}. Entries attempted: {len(v['entries_attempted'])}; completed: "
                     f"{len(v['completed'])}" + (f"; stopped: {len(v['stopped'])}" if v["stopped"] else "")
                     + (f"; not scored: {', '.join(v['unscored'])}" if v["unscored"] else "") + ".")
        lines.append("")
        if v["completed"]:
            arms = [s, *BASELINES]
            lines += _means_table(v, arms, (*_MAIN_KEYS, *_SPLIT_KEYS))
            lines += ["", "Paired differences from direct reading:", ""]
            lines += _paired_table(v, arms, (*_MAIN_KEYS, *_SPLIT_KEYS))
            lines += ["", "Text, calls, cost and time per entry (means over these entries):", ""]
            lines += _cost_table(v["length_cost"], arms)
            lines.append("")
        else:
            m = v["length_cost"][s]["means"]
            lines += [f"Requests per entry: {_num(m['calls'], '{:,.1f}')} distinct ({m.get('fresh_calls_total', 0)} "
                      f"fresh in all), {_num(m['cost_usd'], '${:,.2f}')} at list price.", ""]
        st = v["settings_changed"]
        lines += [f"Settings changed from the defaults of {st['package'] or s} {st['version'] or ''}".rstrip() + ":", ""]
        same = next((o for o in systems if o != s and systems[o]["settings_changed"]["settings"] == st["settings"]
                     and list(systems).index(o) < list(systems).index(s)), None)
        if same:
            lines += [f"The same table as {systems[same]['label']}.", ""]
        else:
            lines += ["| Setting | Default | Value | Reason |", "|---|---|---|---|"]
            for row in st["settings"]:
                cells = [row.get("setting"), row.get("default", ""), row.get("value", ""), row.get("reason", "")]
                cells = [json.dumps(c) if isinstance(c, (dict, list)) else str(c) for c in cells]
                lines.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
            if st["differs_on"]:
                lines.append(f"\nEntries that recorded a different list: {', '.join(st['differs_on'])}.")
            lines.append("")
    audit = report.get("audit")
    if audit and audit.get("arms"):
        lines += [f"## Claim-level audit without repair ({len(audit['entries'])} common entries)", "",
                  "Systems: paragraphs with mapped citations, audited here. Comparison strategies: the stored audit "
                  "of their drafts before their repair round (run omim100), on the same entries.", "",
                  "| Arm | Paragraphs | Claims | Supported | Partly supported | Unsupported | Contradicted | "
                  "Not checkable |", "|---|---|---|---|---|---|---|---|"]
        for a, v in audit["arms"].items():
            p = v["pooled"]
            vd, r = p["verdicts"], p["rates"]
            cells = [f"{vd.get(k, 0)} ({_pct(r[k])})" for k in
                     ("supported", "partially_supported", "unsupported", "contradicted", "not_checkable")]
            lines.append(f"| {_label(a)} | {p.get('paragraphs_audited', '–')} | {p['claims']} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Deviations from the design", ""] + [f"{i}. {d}" for i, d in enumerate(report["deviations"], 1)]
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
                              "means": (v.get("arms") or {}).get(s, {}).get("means")}
                          for s, v in r["systems"].items()}, indent=1))


if __name__ == "__main__":
    main()
