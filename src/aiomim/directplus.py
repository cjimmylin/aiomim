"""Improving on direct reading: the pilot and evaluation runner (`docs/direct-improvements.md`).

Four arms on the same entries and papers, all without a repair round:

    direct            the baseline: direct reading's draft as it was before the repair
                      round, rebuilt from the cached writer and audit replies with no
                      model call (as `secondhand.rebuild_before_repair` does), with its
                      audit before repair.
    direct_checklist  D1, `strategies.direct_checklist`.
    direct_complete   D2, `strategies.direct_complete`.
    direct_ensemble   D3, `strategies.direct_ensemble`.

Per entry and arm: generation; the claim-level audit (`verify.verify_entry`, no repair);
scoring against the frozen fact lists exactly as `rescore` marks a draft
(`facts.eval_gold_text_frozen`), plus the measures of `evaluate` that need no
curator-text judge of their own (references, genes, inheritance, synopsis, variants,
faithfulness). The adaptive fact scoring (`gold_text`) is not run. The baseline's
marks are read from the cache wherever its text equals the stored, already-scored
final draft; only text the repair round changed costs judge calls.

    python -m aiomim.directplus setup --run NAME --entries 300148,600740 | --entries-file F
    python -m aiomim.directplus run --run NAME [--arms ...] [--jobs 2] [--limit N]
    python -m aiomim.directplus summarise --run NAME
    python -m aiomim.directplus project --pilot NAME --entries-file evalsets/omim100.test.tsv

Layout (runs/ is not tracked; OMIM-derived files stay there):

    runs/<run>/<mim>/{seed,gold,papers,gold_facts}.json   copied from the source run
    runs/<run>/<mim>/entry.<arm>.json|.md                  the audited draft (no repair)
    runs/<run>/<mim>/eval.<arm>.json                       scores (fact ids, no fact wording)
    runs/<run>/<mim>/usage.json                            calls, tokens, price, seconds per arm and step
    runs/<run>/progress.log                                one line per finished step
    runs/<run>/directplus.json|.md                         the summary
    runs/direct_improve.ledger.json                        every new model call, pilot and evaluation

Every model call goes through `llm.LLM`; new calls are counted against one cap
(`CALL_CAP`) shared by the pilot and the evaluation.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import shutil
import statistics
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import get_settings
from .models import GeneratedEntry, GoldEntry, Paper, Seed

log = logging.getLogger(__name__)

BASELINE = "direct"
ARMS = ("direct", "direct_checklist", "direct_complete", "direct_ensemble")
VARIANTS = ARMS[1:]
SOURCE_RUN = "omim100"
CALL_CAP = 2200
LEDGER = "direct_improve.ledger.json"
STEPS = ("generate", "audit", "score")
VERDICTS = ("supported", "partially_supported", "unsupported", "contradicted", "not_checkable")
BOOTSTRAP_SEED = 7          # as `compare`

_ledger_backend = None
_ledger_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
    from .pipeline import _write as write
    write(path, data)


def _progress(run_dir: Path, **row: Any) -> None:
    row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **row}
    with _ledger_lock:
        with (run_dir / "progress.log").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_dir_of(name: str) -> Path:
    return get_settings().runs / name


def setup(name: str, mims: list[str], source: str = SOURCE_RUN) -> list[str]:
    """Copy each entry's seed, gold, papers and frozen fact file (with availability) from the source run."""
    src_root, out_root = run_dir_of(source), run_dir_of(name)
    done = []
    for mim in mims:
        src = src_root / mim
        if not (src / "entry.direct.json").exists():
            raise FileNotFoundError(f"{src}: no direct-reading draft")
        if _read(src / "entry.direct.json").get("meta", {}).get("stopped"):
            raise ValueError(f"{mim}: direct reading wrote no draft (stopped)")
        out = out_root / mim
        out.mkdir(parents=True, exist_ok=True)
        for name_ in ("seed.json", "gold.json", "papers.json", "gold_facts.json"):
            if not (out / name_).exists():
                shutil.copy2(src / name_, out / name_)
        (out / "source.json").write_text(json.dumps({"source_run": source, "mim": mim}), encoding="utf-8")
        done.append(mim)
    return done


def entries_of(run_dir: Path) -> list[str]:
    return sorted(p.name for p in run_dir.iterdir() if p.is_dir() and (p / "source.json").exists())


# --------------------------------------------------------------------------- #
# Model wrappers
# --------------------------------------------------------------------------- #


def budget_backend():
    """One backend for every wrapper: counts new calls in one ledger and stops at the cap."""
    global _ledger_backend
    with _ledger_lock:
        if _ledger_backend is None:
            from .auditstress import BudgetBackend
            from .llm import ClaudeCode
            settings = get_settings()
            _ledger_backend = BudgetBackend(ClaudeCode(settings), settings.runs / LEDGER, CALL_CAP)
        return _ledger_backend


def new_llm(phase: str):
    from .llm import LLM
    llm = LLM(get_settings())
    llm.backend = budget_backend()
    llm.usage.phase = phase
    return llm


def cache_only_llm(phase: str):
    from .llm import LLM
    from .secondhand import CacheOnly
    llm = LLM(get_settings())
    llm.backend = CacheOnly()
    llm.usage.phase = phase
    return llm


def _usage(llm, started: float) -> dict[str, Any]:
    total = llm.usage.summary()["total"]
    by_stage = {k: {kk: v[kk] for kk in ("calls", "cached", "list_price_usd", "full_list_price_usd",
                                         "seconds", "full_seconds")}
                for k, v in llm.usage.summary().items() if k != "total"}
    return {**total, "wall_seconds": round(time.time() - started, 1), "by_stage": by_stage,
            "safety_stops": getattr(llm, "safety_stops", 0)}


# --------------------------------------------------------------------------- #
# One entry
# --------------------------------------------------------------------------- #


class Entry:
    def __init__(self, run_dir: Path, mim: str):
        self.dir = run_dir / mim
        self.mim = mim
        self.seed = Seed.model_validate(_read(self.dir / "seed.json"))
        self.gold = GoldEntry.model_validate(_read(self.dir / "gold.json"))
        self.records = _read(self.dir / "papers.json")
        self.source_dir = run_dir_of(_read(self.dir / "source.json")["source_run"]) / mim
        self._papers: list[Paper] | None = None

    @property
    def papers(self) -> list[Paper]:
        if self._papers is None:
            from .sources.fulltext import load_papers
            papers = load_papers([r["pmid"] for r in self.records], with_fulltext=True)
            recorded = {r["pmid"]: r.get("content_level") for r in self.records}
            wrong = {p.pmid: (p.content_level, recorded.get(p.pmid)) for p in papers
                     if p.content_level != recorded.get(p.pmid)}
            if wrong or len(papers) != len(self.records):
                raise RuntimeError(f"[{self.mim}] papers do not read as the source run read them: {wrong}")
            self._papers = papers
        return self._papers

    @property
    def by_pmid(self) -> dict[str, Paper]:
        return {p.pmid: p for p in self.papers}

    def usage(self) -> dict[str, Any]:
        path = self.dir / "usage.json"
        return _read(path) if path.exists() else {"arms": {}}

    def save_usage(self, arm: str, step: str, block: dict[str, Any]) -> None:
        with _ledger_lock:
            data = self.usage()
            data.setdefault("arms", {}).setdefault(arm, {})[step] = block
            _write(self.dir / "usage.json", data)


def _finish_audit_meta(entry: GeneratedEntry) -> None:
    from .evaluate import eval_faithfulness
    from .verify import verdict_counts
    before = eval_faithfulness(entry)
    before.pop("before_repair", None)
    entry.meta["audit_before_repair"] = before
    entry.meta["audit"] = verdict_counts(entry)
    entry.meta["repair"] = "not run (no repair for any arm)"


def _save_entry(e: Entry, arm: str, entry: GeneratedEntry) -> None:
    from .render import entry_markdown
    _write(e.dir / f"entry.{arm}.json", entry.model_dump())
    _write(e.dir / f"entry.{arm}.md", entry_markdown(entry) if not entry.meta.get("stopped")
           else f"# {e.seed.title}\n\nNo entry was written: {entry.meta['stopped']}.\n")


def rebuild_baseline(e: Entry) -> None:
    """The baseline arm: direct reading's draft before repair, with its audit, from the cache only.

    The same steps as `secondhand.rebuild_before_repair`; the cached repair round is
    then replayed on a copy and must reproduce the stored final draft, or the rebuild
    is not exact and the entry stops here.
    """
    from .strategies import after_audit, run_strategy
    from .verify import repair_entry, verify_entry

    started = time.time()
    llm = cache_only_llm("generate")
    with tempfile.TemporaryDirectory() as tmp:
        entry = run_strategy(BASELINE, e.seed, e.papers, llm, Path(tmp))
        gen = _usage(llm, started)
        t_audit = time.time()
        llm_a = cache_only_llm("audit")
        llm_a.backend = llm.backend
        verify_entry(entry, e.by_pmid, llm_a)
        audit = _usage(llm_a, t_audit)
        before = entry.model_copy(deep=True)
        replay = cache_only_llm("repair")
        replay.backend = llm.backend
        repair_entry(entry, e.by_pmid, replay)
        entry.assign_paragraph_ids()
        after_audit(BASELINE, entry, e.papers, Path(tmp))
    stored = GeneratedEntry.model_validate(_read(e.source_dir / "entry.direct.json"))
    texts = lambda x: [p.text for p in x.all_paragraphs()]  # noqa: E731
    exact = {"cache_misses": llm.backend.misses,
             "rebuilt_after_repair_matches_stored": texts(entry) == texts(stored),
             "before_equals_after": texts(before) == texts(stored)}
    if exact["cache_misses"] or not exact["rebuilt_after_repair_matches_stored"]:
        raise RuntimeError(f"[{e.mim}] the before-repair rebuild is not exact: {exact}")
    _finish_audit_meta(before)
    before.meta["before_repair_rebuild"] = exact
    before.meta["strategy"] = BASELINE
    _save_entry(e, BASELINE, before)
    e.save_usage(BASELINE, "generate", gen)
    e.save_usage(BASELINE, "audit", audit)


def generate_and_audit(e: Entry, arm: str) -> None:
    from .llm import LLMRefusal
    from .strategies import after_audit, audit_papers, run_strategy
    from .verify import verify_entry

    started = time.time()
    llm = new_llm("generate")
    try:
        entry = run_strategy(arm, e.seed, e.papers, llm, e.dir)
    except LLMRefusal as exc:
        log.warning("[%s] %s: no entry written: %s", e.mim, arm, exc)
        entry = GeneratedEntry(mim=e.seed.mim, entry_type=e.seed.entry_type, title=e.seed.title,
                               meta={"strategy": arm, "stopped": str(exc)})
        _save_entry(e, arm, entry)
        e.save_usage(arm, "generate", _usage(llm, started))
        return
    e.save_usage(arm, "generate", _usage(llm, started))
    t_audit = time.time()
    llm_a = new_llm("audit")
    read = audit_papers(arm, e.papers, e.dir)
    verify_entry(entry, {p.pmid: p for p in read}, llm_a)
    after_audit(arm, entry, read, e.dir)
    _finish_audit_meta(entry)
    _save_entry(e, arm, entry)
    e.save_usage(arm, "audit", _usage(llm_a, t_audit))


def draft_only(run_dir: Path, mim: str, arms: tuple[str, ...]) -> None:
    """Generation alone, for reading drafts during the pilot: `draft.<arm>.json|.md`, no audit, no score.

    The writer replies are cached, so the full run later regenerates the same drafts
    at no cost; only the audit and scoring are left for drafts that are kept.
    """
    from .llm import LLMRefusal
    from .render import entry_markdown
    from .strategies import run_strategy

    e = Entry(run_dir, mim)
    for arm in arms:
        if arm == BASELINE or (e.dir / f"draft.{arm}.json").exists():
            continue
        started = time.time()
        llm = new_llm("generate")
        try:
            entry = run_strategy(arm, e.seed, e.papers, llm, e.dir)
            _write(e.dir / f"draft.{arm}.json", entry.model_dump())
            _write(e.dir / f"draft.{arm}.md", entry_markdown(entry))
        except LLMRefusal as exc:
            _write(e.dir / f"draft.{arm}.json", {"stopped": str(exc)})
        u = _usage(llm, started)
        _progress(run_dir, mim=mim, arm=arm, step="draft only", calls=u["calls"], cached=u["cached"],
                  usd=u["list_price_usd"], seconds=u["wall_seconds"])
        log.info("[%s] %s drafted: %d calls (%d cached), $%.2f, %.0f s", mim, arm, u["calls"], u["cached"],
                 u["list_price_usd"], u["wall_seconds"])


def score(e: Entry, arm: str) -> None:
    """Scores without the adaptive curator-text judge: frozen facts as `rescore` marks them, and the rest."""
    from .evaluate import (eval_faithfulness, eval_genes, eval_inheritance, eval_references, eval_synopsis,
                           eval_variants)
    from .facts import FactStore, eval_gold_text_frozen, frozen_facts

    started = time.time()
    llm = new_llm("score")
    entry = GeneratedEntry.model_validate(_read(e.dir / f"entry.{arm}.json"))
    gold = e.gold
    levels = {r["pmid"]: r.get("content_level", "not_retrieved") for r in e.records}
    access: dict[str, int] = defaultdict(int)
    for pmid in gold.cited_pmids:
        access[levels.get(pmid, "not_retrieved")] += 1
    records = frozen_facts(gold.scoped_paragraphs, llm, FactStore(), split_missing=False) \
        if gold.scoped_paragraphs else []
    if any(r is None for r in records):
        raise RuntimeError(f"[{e.mim}] a frozen fact list is missing from the store")
    evaluation = {
        "mim": gold.mim, "title": gold.title, "strategy": arm, "gold_reference_access": dict(access),
        "references": eval_references(entry, gold, [r["pmid"] for r in e.records]),
        "genes": eval_genes(entry, gold), "inheritance": eval_inheritance(entry, gold),
        "synopsis": eval_synopsis(entry, gold), "variants": eval_variants(entry, gold, llm),
        "faithfulness": eval_faithfulness(entry),
        "gold_text_frozen": eval_gold_text_frozen(entry, gold, levels, llm, records=records),
        "retrieval": "oracle",
        "scoring": "frozen facts (as rescore); no adaptive gold_text; audit without repair",
    }
    if entry.meta.get("stopped"):
        evaluation["stopped"] = entry.meta["stopped"]
    _write(e.dir / f"eval.{arm}.json", evaluation)
    e.save_usage(arm, "score", _usage(llm, started))


def run_entry(run_dir: Path, mim: str, arms: tuple[str, ...]) -> dict[str, Any]:
    e = Entry(run_dir, mim)
    done = {}
    for arm in arms:
        for step in ("generate", "score"):
            target = e.dir / (f"entry.{arm}.json" if step == "generate" else f"eval.{arm}.json")
            if target.exists():
                continue
            t0 = time.time()
            calls_before = budget_backend()._read()["calls"]
            if step == "generate":
                rebuild_baseline(e) if arm == BASELINE else generate_and_audit(e, arm)
            else:
                score(e, arm)
            calls = budget_backend()._read()["calls"] - calls_before
            _progress(run_dir, mim=mim, arm=arm, step="generate+audit" if step == "generate" else step,
                      seconds=round(time.time() - t0, 1), new_calls_all_threads=calls)
            log.info("[%s] %s %s done in %.0f s", mim, arm, step, time.time() - t0)
        done[arm] = True
    return done


def run(name: str, arms: tuple[str, ...] = ARMS, mims: list[str] | None = None, jobs: int = 1,
        limit: int | None = None) -> dict[str, Any]:
    from .llm import LLMLimitReached
    from .sources.hpo import get_hpo

    run_dir = run_dir_of(name)
    todo = [m for m in (mims or entries_of(run_dir))]
    if limit:
        todo = todo[:limit]
    get_hpo()
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(run_entry, run_dir, mim, arms): mim for mim in todo}
        for future in as_completed(futures):
            mim = futures[future]
            try:
                future.result()
            except LLMLimitReached as exc:
                failures[mim] = f"usage limit or call cap: {exc}"
                _progress(run_dir, mim=mim, error=failures[mim])
                for f in futures:
                    f.cancel()
            except Exception as exc:  # noqa: BLE001 - one entry must not lose the others
                log.exception("[%s] failed", mim)
                failures[mim] = f"{type(exc).__name__}: {exc}"
                _progress(run_dir, mim=mim, error=failures[mim][:300])
    return {"entries": todo, "failures": failures, "ledger": budget_backend()._read()}


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #


def _chars(entry: dict) -> int:
    paras = []
    if entry.get("intro"):
        paras.append(entry["intro"])
    for s in entry.get("sections", []):
        paras.extend(s["paragraphs"])
    for v in entry.get("allelic_variants", []):
        paras.extend(v["paragraphs"])
    return sum(len(p.get("text") or "") for p in paras)


def _fresh(usage_arm: dict, key: str) -> float:
    return sum((usage_arm.get(step) or {}).get(key, 0) for step in STEPS)


def entry_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for mim in entries_of(run_dir):
        d = run_dir / mim
        usage = _read(d / "usage.json").get("arms", {}) if (d / "usage.json").exists() else {}
        for arm in ARMS:
            if not (d / f"eval.{arm}.json").exists():
                continue
            ev, en = _read(d / f"eval.{arm}.json"), _read(d / f"entry.{arm}.json")
            fr = ev.get("gold_text_frozen") or {}
            f = ev.get("faithfulness") or {}
            u = usage.get(arm, {})
            meta = en.get("meta") or {}
            row = {
                "mim": mim, "arm": arm, "stopped": ev.get("stopped"),
                "incomplete": (meta.get("direct_complete") or {}).get("papers_failed") or [],
                "coverage": fr.get("coverage"), "n_facts": fr.get("n_judged"),
                "by_level": {k: v.get("coverage") for k, v in (fr.get("by_content_level") or {}).items()},
                "chars": _chars(en), "claims": f.get("n_claims"),
                **{v: f.get(v, 0) for v in VERDICTS},
                "variants_generated": (ev.get("variants") or {}).get("n_generated"),
                "variants_matched": (ev.get("variants") or {}).get("n_matched"),
                "variants_gold": (ev.get("variants") or {}).get("n_gold"),
                "calls_new": int(_fresh(u, "calls") - _fresh(u, "cached")),
                "calls_method": int(_fresh(u, "calls")),
                "usd_new": round(_fresh(u, "list_price_usd"), 4),
                "usd_method": round(_fresh(u, "full_list_price_usd"), 4),
                "wall_seconds": round(_fresh(u, "wall_seconds"), 1),
                "call_seconds_method": round(_fresh(u, "full_seconds"), 1),
                "by_step": {s: {k: (u.get(s) or {}).get(k) for k in ("calls", "cached", "list_price_usd",
                                                                    "full_list_price_usd", "wall_seconds")}
                            for s in STEPS if s in u},
            }
            if arm == "direct_complete" and meta.get("direct_complete"):
                dc = meta["direct_complete"]
                rev = dc.get("revision") or {}
                row["d2"] = {k: dc.get(k) for k in ("papers_checked", "omissions_listed", "omissions_kept",
                                                    "papers_failed")}
                row["d2"].update({k: rev.get(k) for k in ("called", "sentences_added", "sentences_removed",
                                                          "added_citing_papers_with_omissions",
                                                          "added_citing_other_papers_only", "relationships_changed",
                                                          "synopsis_changed", "variants_changed", "intro_changed",
                                                          "pmids_lost", "chars_before", "chars_after")})
            if arm == "direct_ensemble" and meta.get("direct_ensemble"):
                de = meta["direct_ensemble"]
                row["d3"] = {"retention": de.get("retention"), "merge": de.get("merge"),
                             "variant_groups": de.get("variant_groups"),
                             "variants_per_draft": de.get("variants_per_draft")}
            rows.append(row)
    return rows


def paired(rows: list[dict[str, Any]], key: str = "coverage", arms: tuple[str, ...] = VARIANTS
           ) -> dict[str, Any]:
    """Each arm minus the baseline over entries every arm completed; Holm across the arms (sign tests)."""
    from .compare import _holm, _pair_stats
    by = defaultdict(dict)
    for r in rows:
        by[r["mim"]][r["arm"]] = r
    ok = [m for m, a in by.items() if all(x in a and not a[x]["stopped"] and not a[x]["incomplete"]
                                          and a[x].get(key) is not None for x in (BASELINE, *arms))]
    out = {"n_entries": len(ok), "entries": sorted(ok), "arms": {}}
    pvals = {}
    for arm in arms:
        pairs = [(by[m][arm][key], by[m][BASELINE][key]) for m in ok]
        if not pairs:
            continue
        stats = _pair_stats(pairs, True, random.Random(BOOTSTRAP_SEED))
        stats["mean_arm"] = round(statistics.mean(a for a, _ in pairs), 4)
        stats["mean_baseline"] = round(statistics.mean(b for _, b in pairs), 4)
        out["arms"][arm] = stats
        if stats["sign_test_p"] is not None:
            pvals[arm] = stats["sign_test_p"]
    for arm, p in _holm(pvals).items():
        out["arms"][arm]["sign_test_p_holm"] = round(p, 4)
    return out


def summarise(name: str) -> dict[str, Any]:
    from .gaps import compare_by_availability

    run_dir = run_dir_of(name)
    rows = entry_rows(run_dir)
    result: dict[str, Any] = {"run": name, "rows": rows, "primary": paired(rows)}
    means = {}
    for arm in ARMS:
        mine = [r for r in rows if r["arm"] == arm and not r["stopped"]]
        if not mine:
            continue
        mean = lambda k: round(statistics.mean(r[k] for r in mine if r[k] is not None), 4) \
            if any(r[k] is not None for r in mine) else None  # noqa: E731
        means[arm] = {"n": len(mine), **{k: mean(k) for k in ("coverage", "chars", "claims", "calls_new",
                                                               "calls_method", "usd_new", "usd_method",
                                                               "wall_seconds", "call_seconds_method")},
                      **{v: sum(r[v] for r in mine) for v in VERDICTS}}
    result["means"] = means
    try:
        result["by_availability"] = compare_by_availability(run_dir, baseline=BASELINE)
    except Exception as exc:  # noqa: BLE001 - reported, the rest of the summary stands
        result["by_availability"] = {"error": f"{type(exc).__name__}: {exc}"}
    ledger = run_dir.parent / LEDGER
    result["ledger"] = _read(ledger) if ledger.exists() else None
    _write(run_dir / "directplus.json", result)
    (run_dir / "directplus.md").write_text(markdown(result), encoding="utf-8")
    return result


def _pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def markdown(r: dict[str, Any]) -> str:
    out = [f"# Improving direct reading — run `{r['run']}`", ""]
    out.append("| Entry | Arm | Facts conveyed | FT papers | Abstract papers | Chars | Claims | Sup / part / unsup / contra "
               "| Calls new (method) | USD new (method) | Wall s |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for x in r["rows"]:
        if x["stopped"]:
            out.append(f"| {x['mim']} | {x['arm']} | stopped: {x['stopped'][:60]} |||||||||")
            continue
        out.append(f"| {x['mim']} | {x['arm']} | {_pct(x['coverage'])} | {_pct(x['by_level'].get('fulltext'))} | "
                   f"{_pct(x['by_level'].get('abstract'))} | {x['chars']:,} | {x['claims']} | "
                   f"{x['supported']} / {x['partially_supported']} / {x['unsupported']} / {x['contradicted']} | "
                   f"{x['calls_new']} ({x['calls_method']}) | {x['usd_new']:.2f} ({x['usd_method']:.2f}) | "
                   f"{x['wall_seconds']:.0f} |")
    out += ["", "## Means over entries", "",
            "| Arm | n | Facts conveyed | Chars | Claims | Calls new | Calls (method) | USD new | USD (method) | Wall s |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for arm, m in r["means"].items():
        out.append(f"| {arm} | {m['n']} | {_pct(m['coverage'])} | {m['chars']:,.0f} | {m['claims']:.0f} | "
                   f"{m['calls_new']:.1f} | {m['calls_method']:.1f} | {m['usd_new']:.2f} | {m['usd_method']:.2f} | "
                   f"{m['wall_seconds']:.0f} |")
    p = r["primary"]
    out += ["", f"## Primary: facts conveyed, arm minus baseline ({p['n_entries']} entries complete for every arm)", "",
            "| Arm | Difference | 95% CI | Better / worse / tied | Sign p | Holm p |", "|---|---|---|---|---|---|"]
    for arm, s in p["arms"].items():
        ci = f"{100 * s['ci95'][0]:+.1f} to {100 * s['ci95'][1]:+.1f}" if s.get("ci95") else "–"
        out.append(f"| {arm} | {100 * s['difference']:+.1f} | {ci} | {s['better']}/{s['worse']}/{s['ties']} | "
                   f"{s['sign_test_p']} | {s.get('sign_test_p_holm')} |")
    ba = r.get("by_availability") or {}
    if "cells" in ba:
        out += ["", "## Facts conveyed by whether the supplied text states them (mean over entries)", "",
                "| Arm | All | Stated | Stated, full text | Stated, abstract | Not stated |", "|---|---|---|---|---|---|"]
        for s in [x["name"] for x in ba["strategies"]]:
            cell = lambda rr, lv: ba["cells"][rr][lv]["by_strategy"][s]["mean_over_entries"]  # noqa: E731
            out.append(f"| {s} | {_pct(cell('all', 'all'))} | {_pct(cell('stated', 'all'))} | "
                       f"{_pct(cell('stated', 'fulltext'))} | {_pct(cell('stated', 'abstract'))} | "
                       f"{_pct(cell('not_stated', 'all'))} |")
    elif ba:
        out += ["", f"By availability: {ba.get('error')}"]
    if r.get("ledger"):
        lg = r["ledger"]
        out += ["", f"Ledger (pilot and evaluation): {lg['calls']} new calls of the {CALL_CAP} cap, "
                    f"${lg['cost_usd']:.2f} list price, {lg['safety_stops']} safety stops, {lg['refusals']} refusals, "
                    f"{lg['errors']} errors."]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Projection to the evaluation entries (no model call)
# --------------------------------------------------------------------------- #


def _stage_calls(block: dict[str, Any]) -> dict[str, dict[str, float]]:
    """stage -> fresh calls, list price and call seconds of one step's usage block."""
    out = {}
    for key, v in (block.get("by_stage") or {}).items():
        stage = key.split("/", 1)[-1]
        out[stage] = {"calls": v["calls"] - v["cached"], "usd": v["list_price_usd"], "seconds": v["seconds"]}
    return out


def project(pilot: str, mims: list[str], source: str = SOURCE_RUN) -> dict[str, Any]:
    """New calls, list price and time for the evaluation entries, from the pilot (no model call).

    Per arm, each step's fresh calls are modelled on what drives them:
      generation   D1: per entry; D2: the checks per paper, the revision per entry;
                   D3: per entry (two drafts, the merge); HPO resolution per entry.
      audit        the source run's audit calls on direct reading's draft of the same
                   entry (claim extraction plus one call per paper), times the arm's
                   ratio to them in the pilot.
      scoring      one mark call per gold paragraph in scope, times the pilot's ratio,
                   plus the variant judge at the pilot's rate.
    Price per call is the pilot's mean for that arm and stage; time is the pilot's
    mean wall time per entry and arm (entries run one at a time).
    """
    run_dir, src_root = run_dir_of(pilot), run_dir_of(source)
    usage_of = lambda mim: _read(src_root / mim / "usage.json")["by_strategy"]["direct"]  # noqa: E731
    n_marks_of = lambda root, mim: len(GoldEntry.model_validate(_read(root / mim / "gold.json")).scoped_paragraphs)  # noqa: E731

    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    price: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))   # arm -> stage -> usd per call
    # Generation as first made (the pilot's draft step): the run's own generation step
    # replays those replies from the cache. D2's checks scale with the papers.
    first: dict[tuple[str, str], dict[str, Any]] = {}
    log_path = run_dir / "progress.log"
    for line in (log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []):
        row = json.loads(line)
        if row.get("step") == "draft only":
            first[(row["mim"], row["arm"])] = row
    for (mim, arm), row in first.items():
        n_papers = len(_read(run_dir / mim / "papers.json"))
        new_calls = row["calls"] - row["cached"]
        scale = n_papers if arm == "direct_complete" else 1
        acc[arm]["gen_calls"].append(new_calls / scale)
        acc[arm]["gen_usd"].append(row["usd"] / scale)
        acc[arm]["gen_seconds"].append(row["seconds"])
    for mim in entries_of(run_dir):
        d = run_dir / mim
        if not (d / "usage.json").exists():
            continue
        usage = _read(d / "usage.json")["arms"]
        n_papers = len(_read(d / "papers.json"))
        src_audit = (usage_of(mim).get("audit/verify") or {}).get("calls", 0)
        n_marks = n_marks_of(run_dir, mim)
        for arm in VARIANTS:
            u = usage.get(arm) or {}
            if not all(step in u for step in STEPS):
                continue
            aud, sco = _stage_calls(u["audit"]), _stage_calls(u["score"])
            for stage_map in (aud, sco):
                for stage, v in stage_map.items():
                    if v["calls"]:
                        price[arm][stage].append(v["usd"] / v["calls"])
            acc[arm]["audit_ratio"].append(aud.get("verify", {}).get("calls", 0) / max(1, src_audit))
            acc[arm]["mark_ratio"].append(sco.get("judge", {}).get("calls", 0) / max(1, n_marks))
            acc[arm]["audit_score_wall"].append(u["audit"].get("wall_seconds", 0) + u["score"].get("wall_seconds", 0))
    mean = lambda xs: statistics.mean(xs) if xs else 0.0  # noqa: E731

    per_arm: dict[str, dict[str, float]] = {}
    for arm in VARIANTS:
        if not acc[arm]:
            continue
        calls_by_stage: dict[str, float] = defaultdict(float)
        for mim in mims:
            n_papers = len(_read(src_root / mim / "papers.json"))
            src_audit = (usage_of(mim).get("audit/verify") or {}).get("calls", 0)
            n_marks = n_marks_of(src_root, mim)
            scale = n_papers if arm == "direct_complete" else 1
            calls_by_stage["generate"] += mean(acc[arm]["gen_calls"]) * scale
            usd_gen = mean(acc[arm]["gen_usd"]) * scale
            calls_by_stage["audit/verify"] += mean(acc[arm]["audit_ratio"]) * src_audit
            calls_by_stage["score/judge"] += mean(acc[arm]["mark_ratio"]) * n_marks
            calls_by_stage["usd"] += usd_gen
        usd = calls_by_stage.pop("usd") + sum(c * mean(price[arm][key.split("/", 1)[1]])
                                              for key, c in calls_by_stage.items() if "/" in key)
        wall = mean(acc[arm]["gen_seconds"]) + mean(acc[arm]["audit_score_wall"])
        per_arm[arm] = {"calls": round(sum(calls_by_stage.values()), 1),
                        "calls_by_stage": {k: round(v, 1) for k, v in calls_by_stage.items()},
                        "usd": round(usd, 2), "hours_one_entry_at_a_time": round(wall * len(mims) / 3600, 1),
                        "pilot_wall_seconds_per_entry": round(wall),
                        "pilot": {k: round(mean(v), 3) for k, v in acc[arm].items()}}
    ledger = run_dir.parent / LEDGER
    used = _read(ledger)["calls"] if ledger.exists() else 0
    variants_total = round(sum(a["calls"] for a in per_arm.values()))
    return {"pilot": pilot, "n_entries": len(mims), "per_arm": per_arm,
            "variant_arms_calls": variants_total, "calls_used_so_far": used, "cap": CALL_CAP,
            "headroom_after_evaluation": CALL_CAP - used - variants_total}


def baseline_judge_calls(mims: list[str], source: str = SOURCE_RUN) -> dict[str, Any]:
    """Judge calls the baseline needs: gold paragraphs whose cited draft text the repair round changed (no model call)."""
    from .evaluate import _draft_text_for
    src_root = run_dir_of(source)
    out = {}
    for mim in mims:
        stored = GeneratedEntry.model_validate(_read(src_root / mim / "entry.direct.json"))
        rep = stored.meta.get("repair") or {}
        if not (rep.get("revised") or rep.get("deleted")):
            out[mim] = 0
            continue
        tmp_run = Path(tempfile.mkdtemp())
        e_dir = tmp_run / mim
        e_dir.mkdir()
        for f in ("seed.json", "gold.json", "papers.json"):
            shutil.copy2(src_root / mim / f, e_dir / f)
        (e_dir / "source.json").write_text(json.dumps({"source_run": source, "mim": mim}))
        e = Entry(tmp_run, mim)
        from .strategies import run_strategy
        from .verify import verify_entry
        llm = cache_only_llm("generate")
        with tempfile.TemporaryDirectory() as tmp:
            entry = run_strategy(BASELINE, e.seed, e.papers, llm, Path(tmp))
            verify_entry(entry, e.by_pmid, llm)
        gold = e.gold
        out[mim] = sum(1 for p in gold.scoped_paragraphs
                       if _draft_text_for(entry, p.pmids) != _draft_text_for(stored, p.pmids)
                       and _draft_text_for(entry, p.pmids))
        shutil.rmtree(tmp_run, ignore_errors=True)
    return {"per_entry": out, "total": sum(out.values())}


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def _mims(entries: str | None, entries_file: str | None) -> list[str] | None:
    if entries:
        return [m.strip() for m in entries.split(",") if m.strip()]
    if entries_file:
        lines = Path(entries_file).read_text(encoding="utf-8").splitlines()
        return [ln.split("\t")[0].strip() for ln in lines[1:] if ln.strip() and ln.split("\t")[0].strip().isdigit()]
    return None


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.directplus")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("--run", required=True)
    s.add_argument("--entries")
    s.add_argument("--entries-file")
    s.add_argument("--source", default=SOURCE_RUN)
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--arms", default=",".join(ARMS))
    r.add_argument("--entries")
    r.add_argument("--jobs", type=int, default=1)
    r.add_argument("--limit", type=int)
    d = sub.add_parser("draft")
    d.add_argument("--run", required=True)
    d.add_argument("--arms", default=",".join(VARIANTS))
    d.add_argument("--entries")
    d.add_argument("--jobs", type=int, default=1)
    m = sub.add_parser("summarise")
    m.add_argument("--run", required=True)
    p = sub.add_parser("project")
    p.add_argument("--pilot", required=True)
    p.add_argument("--entries-file", required=True)
    p.add_argument("--source", default=SOURCE_RUN)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.cmd == "setup":
        print(setup(args.run, _mims(args.entries, args.entries_file) or [], args.source))
    elif args.cmd == "run":
        arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
        unknown = set(arms) - set(ARMS)
        if unknown:
            raise SystemExit(f"unknown arms: {unknown}")
        print(json.dumps(run(args.run, arms, _mims(args.entries, None), args.jobs, args.limit), indent=1))
    elif args.cmd == "draft":
        arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
        run_dir = run_dir_of(args.run)
        todo = _mims(args.entries, None) or entries_of(run_dir)
        from .sources.hpo import get_hpo
        get_hpo()
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            for mim, fut in [(m_, pool.submit(draft_only, run_dir, m_, arms)) for m_ in todo]:
                try:
                    fut.result()
                except Exception as exc:  # noqa: BLE001
                    log.exception("[%s] drafting failed", mim)
                    _progress(run_dir, mim=mim, error=f"{type(exc).__name__}: {exc}"[:300])
        print(json.dumps(budget_backend()._read(), indent=1))
    elif args.cmd == "summarise":
        result = summarise(args.run)
        print((run_dir_of(args.run) / "directplus.md").read_text())
        del result
    elif args.cmd == "project":
        mims = _mims(None, args.entries_file) or []
        src_root = run_dir_of(args.source)
        eligible = [m for m in mims
                    if any(r.get("content_level") == "fulltext" for r in _read(src_root / m / "papers.json"))
                    and not _read(src_root / m / "entry.direct.json").get("meta", {}).get("stopped")]
        result = project(args.pilot, eligible, args.source)
        result["baseline_judge_calls"] = baseline_judge_calls(eligible, args.source)
        result["headroom_after_evaluation"] -= result["baseline_judge_calls"]["total"]
        _write(run_dir_of(args.pilot) / "projection.json", result)
        print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
