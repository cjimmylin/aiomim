"""Improving on direct reading: the pilot and evaluation runner (`docs/direct-improvements.md`).

Four arms on the same entries and papers, all without a repair round:

    direct            the baseline: direct reading's draft as it was before the repair
                      round, rebuilt from the cached writer and audit replies with no
                      model call (as `secondhand.rebuild_before_repair` does), with its
                      audit before repair.
    direct_checklist  D1, `strategies.direct_checklist`.
    direct_complete   D2, `strategies.direct_complete`.
    direct_ensemble   D3, `strategies.direct_ensemble`.

Added after those four were run (the extension; docs/direct-improvements.md):

    direct_checklist_complete  D4, `strategies.direct_checklist_complete`: D1's draft from
                      the cache, then D2's completeness pass. It is added to a finished run
                      with `run --arms direct_checklist_complete`; the four arms' files are
                      left as they are (a step whose file exists is skipped, so resuming
                      makes no call for them). Its new calls are counted in the same ledger
                      under `extensions.direct_checklist_complete` and capped there
                      (`EXTENSIONS`, 700 with its pilot); the first four arms' cap counts
                      the rest. `report` keeps the four-arm sections as they were and adds
                      a separate D4 section once D4 has results.

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
    python -m aiomim.directplus report --run NAME [--out results/direct_improve]
    python -m aiomim.directplus project-extension [--run direct_improve --pilot direct_improve_pilot]

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
# Arms added after the first four were run, each with its own cap of new calls (pilot included),
# counted in the same ledger but checked apart from the first four arms' cap.
EXTENSIONS = {"direct_checklist_complete": 700}
EXTENSION = "direct_checklist_complete"
ALL_ARMS = (*ARMS, *EXTENSIONS)
# Where an arm records the papers whose completeness check failed (an incomplete entry).
INCOMPLETE_KEY = {"direct_complete": "direct_complete", "direct_checklist_complete": "direct_checklist_complete"}
SOURCE_RUN = "omim100"
CALL_CAP = 2200
LEDGER = "direct_improve.ledger.json"
STEPS = ("generate", "audit", "score")
VERDICTS = ("supported", "partially_supported", "unsupported", "contradicted", "not_checkable")
BOOTSTRAP_SEED = 7          # as `compare`
AUDIT_SAMPLE = "audit_sample.json"
AUDIT_SEED = 20261120       # docs/direct-improvements.md, "Pilot and changes made before the test run"
AUDIT_N = 20

_ledger_backends: dict[str | None, Any] = {}
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


def draw_audit_sample(name: str, n: int = AUDIT_N, seed: int = AUDIT_SEED) -> list[str]:
    """The entries whose drafts get the claim-level audit (every arm), drawn once and written to the run.

    `random.Random(seed).sample(sorted(mims), n)` over the run's entry numbers as strings.
    """
    run_dir = run_dir_of(name)
    path = run_dir / AUDIT_SAMPLE
    mims = entries_of(run_dir)
    chosen = random.Random(seed).sample(sorted(mims), n)
    record = {"method": f"random.Random({seed}).sample(sorted(entries), {n})", "seed": seed, "n": n,
              "from_entries": sorted(mims), "entries": sorted(chosen), "drawn_order": chosen}
    if path.exists():
        old = _read(path)
        if old["entries"] != record["entries"]:
            raise RuntimeError(f"{path} exists with a different sample; not overwritten")
        return old["entries"]
    _write(path, record)
    return record["entries"]


def audit_sample(run_dir: Path) -> set[str] | None:
    """The audited entries, or None when the run audits every entry (no sample drawn, as in the pilot)."""
    path = run_dir / AUDIT_SAMPLE
    return set(_read(path)["entries"]) if path.exists() else None


def entries_of(run_dir: Path) -> list[str]:
    return sorted(p.name for p in run_dir.iterdir() if p.is_dir() and (p / "source.json").exists())


# --------------------------------------------------------------------------- #
# Model wrappers
# --------------------------------------------------------------------------- #


_LEDGER_FIELDS = ("calls", "cost_usd", "input_tokens", "output_tokens", "safety_stops", "refusals", "errors")


class LedgerBackend:
    """Counts every new call in the shared ledger and halts at a cap.

    `group` None is the first four arms: their cap (`CALL_CAP`) counts every call in
    the ledger except those of the extension arms. An extension arm (`EXTENSIONS`)
    counts its calls under `extensions.<arm>` as well as in the totals, and has its own
    cap. The ledger keeps the shape `auditstress.BudgetBackend` wrote (including its
    `by_stage`, which is keyed by effort), so the first four arms' figures are the
    totals minus the extensions. A file lock guards the ledger across processes.
    """

    def __init__(self, inner, ledger: Path, group: str | None, cap: int):
        self.inner, self.ledger, self.group, self.cap = inner, ledger, group, cap
        self.lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        if self.ledger.exists():
            return json.loads(self.ledger.read_text())
        return {**{k: 0 for k in _LEDGER_FIELDS}, "cost_usd": 0.0, "by_stage": {}}

    def _update(self, change) -> dict[str, Any]:
        import fcntl
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, open(self.ledger.with_suffix(".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            result = change(data)
            tmp = self.ledger.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1))
            tmp.replace(self.ledger)
            return result

    def _bump(self, data: dict[str, Any], **delta: float) -> None:
        targets = [data]
        if self.group:
            ext = data.setdefault("extensions", {}).setdefault(
                self.group, {**{k: 0 for k in _LEDGER_FIELDS}, "cost_usd": 0.0, "by_stage": {}, "cap": self.cap})
            targets.append(ext)
        for t in targets:
            for k, v in delta.items():
                if k == "effort":
                    t["by_stage"][v] = t["by_stage"].get(v, 0) + 1
                elif k == "cost_usd":
                    t[k] = round(t.get(k, 0.0) + v, 4)
                else:
                    t[k] = t.get(k, 0) + v

    def used(self, data: dict[str, Any]) -> int:
        ext = data.get("extensions", {})
        if self.group:
            return ext.get(self.group, {}).get("calls", 0)
        return data.get("calls", 0) - sum(v.get("calls", 0) for v in ext.values())

    def complete(self, **kw):
        from .llm import LLMLimitReached, LLMRefusal

        def take(data):
            if self.used(data) >= self.cap:
                return False
            self._bump(data, calls=1)
            return True

        if not self._update(take):
            who = self.group or "the first four arms"
            raise LLMLimitReached(f"directplus call cap of {self.cap} reached for {who}")
        try:
            out, meta = self.inner.complete(**kw)
        except LLMRefusal:
            self._update(lambda d: self._bump(d, refusals=1))
            raise
        except Exception:
            self._update(lambda d: self._bump(d, errors=1))
            raise
        self._update(lambda d: self._bump(
            d, cost_usd=float(meta.get("cost_usd") or 0), input_tokens=int(meta.get("input_tokens") or 0),
            output_tokens=int(meta.get("output_tokens") or 0), safety_stops=1 if meta.get("safety_stops") else 0,
            effort=kw.get("effort", "?")))
        return out, meta


def budget_backend(arm: str | None = None):
    """The backend for an arm: the extension arms' own, or the first four arms' shared one."""
    group = arm if arm in EXTENSIONS else None
    with _ledger_lock:
        if group not in _ledger_backends:
            from .llm import ClaudeCode
            settings = get_settings()
            _ledger_backends[group] = LedgerBackend(ClaudeCode(settings), settings.runs / LEDGER, group,
                                                    EXTENSIONS[group] if group else CALL_CAP)
        return _ledger_backends[group]


def first_four_ledger(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """The ledger as the first four arms' report reads it: totals minus the extension arms."""
    if data is None:
        return None
    out = {k: v for k, v in data.items() if k != "extensions"}
    for ext in data.get("extensions", {}).values():
        for k in _LEDGER_FIELDS:
            out[k] = round(out.get(k, 0) - ext.get(k, 0), 4) if k == "cost_usd" else out.get(k, 0) - ext.get(k, 0)
        out["by_stage"] = {e: n - ext.get("by_stage", {}).get(e, 0) for e, n in out.get("by_stage", {}).items()}
        out["by_stage"] = {e: n for e, n in out["by_stage"].items() if n}
    return out


def new_llm(phase: str, arm: str | None = None):
    from .llm import LLM
    llm = LLM(get_settings())
    llm.backend = budget_backend(arm)
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
        sample = audit_sample(run_dir)
        self.audited = sample is None or mim in sample
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
    if e.audited:
        _finish_audit_meta(before)
        e.save_usage(BASELINE, "audit", audit)
    else:
        # Outside the audit subsample no arm is audited; the baseline's cached verdicts are
        # dropped too, so that no claim figure mixes audited and unaudited entries.
        for para in before.all_paragraphs():
            para.checks = []
        before.meta["audit"] = "not run (entry outside the audit subsample)"
    before.meta["before_repair_rebuild"] = exact
    before.meta["strategy"] = BASELINE
    _save_entry(e, BASELINE, before)
    e.save_usage(BASELINE, "generate", gen)


def generate_and_audit(e: Entry, arm: str) -> None:
    from .llm import LLMRefusal
    from .strategies import after_audit, audit_papers, run_strategy
    from .verify import verify_entry

    started = time.time()
    llm = new_llm("generate", arm)
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
    if not e.audited:
        entry.meta["audit"] = "not run (entry outside the audit subsample)"
        _save_entry(e, arm, entry)
        return
    t_audit = time.time()
    llm_a = new_llm("audit", arm)
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
        llm = new_llm("generate", arm)
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
    llm = new_llm("score", arm)
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
        "retrieval": "oracle", "audited": e.audited,
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
        for arm in ALL_ARMS:
            if not (d / f"eval.{arm}.json").exists():
                continue
            ev, en = _read(d / f"eval.{arm}.json"), _read(d / f"entry.{arm}.json")
            fr = ev.get("gold_text_frozen") or {}
            f = ev.get("faithfulness") or {}
            u = usage.get(arm, {})
            meta = en.get("meta") or {}
            row = {
                "mim": mim, "arm": arm, "stopped": ev.get("stopped"),
                "incomplete": (meta.get(INCOMPLETE_KEY.get(arm, "")) or {}).get("papers_failed") or [],
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
            if arm in INCOMPLETE_KEY and meta.get(INCOMPLETE_KEY[arm]):
                dc = meta[INCOMPLETE_KEY[arm]]
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


def paired(rows: list[dict[str, Any]], key: str = "coverage", arms: tuple[str, ...] | None = None
           ) -> dict[str, Any]:
    """Each arm minus the baseline over entries every arm completed; Holm across the arms (sign tests)."""
    from .compare import _holm, _pair_stats
    present = {r["arm"] for r in rows}
    arms = arms or tuple(a for a in ALL_ARMS if a != BASELINE and a in present)
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
    for arm in ALL_ARMS:
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
# The evaluation's report (results/direct_improve/)
# --------------------------------------------------------------------------- #

MEASURES = (  # (key, label, availability restriction, paper level)
    ("all", "All facts", None, "all"),
    ("stated", "Facts the supplied text states", ("yes",), "all"),
    ("stated_fulltext", "… on papers readable in full", ("yes",), "fulltext"),
    ("stated_abstract", "… on papers readable as abstract only", ("yes",), "abstract"),
    ("not_stated", "Facts the supplied text does not state", ("no",), "all"),
)
CLAIM_KINDS = ("supported", "partially_supported", "unsupported", "contradicted")


def completion(run_dir: Path, mims: list[str], arms: tuple[str, ...] = ARMS) -> dict[str, dict[str, str]]:
    """arm -> entry -> complete | incomplete | no_draft | not_run (the design's completion rule)."""
    out: dict[str, dict[str, str]] = {arm: {} for arm in arms}
    for mim in mims:
        for arm in arms:
            ev, en = run_dir / mim / f"eval.{arm}.json", run_dir / mim / f"entry.{arm}.json"
            if not ev.exists() or not en.exists():
                out[arm][mim] = "not_run"
            elif _read(ev).get("stopped"):
                out[arm][mim] = "no_draft"
            elif arm in INCOMPLETE_KEY and ((_read(en).get("meta") or {}).get(INCOMPLETE_KEY[arm]) or {}).get(
                    "papers_failed"):
                out[arm][mim] = "incomplete"
            else:
                out[arm][mim] = "complete"
    return out


def entry_measures(run_dir: Path, mim: str, arm: str) -> dict[str, Any]:
    from .gaps import availability_by_fact, join_marks, restricted_tally

    ev, en = _read(run_dir / mim / f"eval.{arm}.json"), _read(run_dir / mim / f"entry.{arm}.json")
    frozen = ev.get("gold_text_frozen") or {}
    avail = availability_by_fact(_read(run_dir / mim / "gold_facts.json"))
    rows, join = join_marks(frozen, avail)
    out: dict[str, Any] = {"coverage_main": frozen.get("coverage"), "join": join}
    for key, _, verdicts, level in MEASURES:
        cell = restricted_tally(rows, verdicts, level)
        out[key] = cell["coverage"]
        out[f"{key}_n"] = cell["n_facts"]
    f = ev.get("faithfulness") or {}
    out.update({k: f.get(k, 0) for k in (*CLAIM_KINDS, "not_checkable")})
    out["claims_checkable"] = f.get("n_claims", 0)
    out["audited"] = bool(ev.get("audited", True))
    out["chars"] = _chars(en)
    v = ev.get("variants") or {}
    n_gen, n_gold = v.get("n_generated") or 0, v.get("n_gold") or 0
    out["variant_recall"] = (0.0 if n_gold and not n_gen else v.get("recall")) if n_gold else None
    out["variant_precision"] = round(v.get("n_matched", 0) / n_gen, 4) if n_gen and n_gold else None
    out.update(variants_generated=n_gen, variants_gold=n_gold, variants_matched=v.get("n_matched", 0))
    return out


def _usage_row(run_dir: Path, mim: str, arm: str) -> dict[str, Any]:
    path = run_dir / mim / "usage.json"
    u = (_read(path).get("arms", {}) if path.exists() else {}).get(arm, {})
    row: dict[str, Any] = {"calls_new": 0, "usd_new": 0.0, "usd_method": 0.0, "wall_seconds": 0.0, "safety_stops": {}}
    for step in STEPS:
        b = u.get(step)
        if not b:
            continue
        row["calls_new"] += b.get("calls", 0) - b.get("cached", 0)
        row["usd_new"] += b.get("list_price_usd", 0.0)
        row["usd_method"] += b.get("full_list_price_usd", 0.0)
        row["wall_seconds"] += b.get("wall_seconds", 0.0)
        if b.get("safety_stops"):
            row["safety_stops"][step] = b["safety_stops"]
        row[f"calls_new_{step}"] = b.get("calls", 0) - b.get("cached", 0)
    return row


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 4) if xs else None


def final_report(name: str, out_dir: Path | None = None) -> dict[str, Any]:
    from .compare import _holm, _pair_stats

    run_dir = run_dir_of(name)
    out_dir = out_dir or Path("results") / "direct_improve"
    mims = entries_of(run_dir)
    sample = audit_sample(run_dir)
    audited = sorted(sample) if sample is not None else mims
    status = completion(run_dir, mims)
    common = [m for m in mims if all(status[a][m] == "complete" for a in ARMS)]
    per: dict[str, dict[str, dict[str, Any]]] = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for mim in mims:
            if status[arm][mim] in ("complete", "incomplete"):
                per[arm][mim] = {**entry_measures(run_dir, mim, arm), **_usage_row(run_dir, mim, arm)}
            elif status[arm][mim] == "no_draft":
                per[arm][mim] = {"no_draft": True, **_usage_row(run_dir, mim, arm)}

    # Facts conveyed: means and paired differences over the entries every arm completed.
    facts: dict[str, Any] = {}
    for key, label, _, _ in MEASURES:
        block: dict[str, Any] = {"label": label, "means": {}, "versus_baseline": {}}
        for arm in ARMS:
            vals = [per[arm][m][key] for m in common if per[arm][m].get(key) is not None]
            block["means"][arm] = {"mean_over_entries": _mean(vals), "n_entries": len(vals),
                                   "facts_per_entry": _mean([per[arm][m][f"{key}_n"] for m in common])}
        pvals = {}
        for arm in VARIANTS:
            pairs = [(per[arm][m][key], per[BASELINE][m][key]) for m in common
                     if per[arm][m].get(key) is not None and per[BASELINE][m].get(key) is not None]
            if not pairs:
                continue
            st = _pair_stats(pairs, True, random.Random(BOOTSTRAP_SEED))
            block["versus_baseline"][arm] = st
            if st["sign_test_p"] is not None:
                pvals[arm] = st["sign_test_p"]
        for arm, p in _holm(pvals).items():
            block["versus_baseline"][arm]["sign_test_p_holm"] = round(p, 4)
        facts[key] = block

    # Claims, on the audited entries (every arm with a draft there).
    claims: dict[str, Any] = {}
    for arm in ARMS:
        rows = [per[arm][m] for m in audited if m in per[arm] and not per[arm][m].get("no_draft")]
        pooled = {k: sum(r.get(k, 0) for r in rows) for k in (*CLAIM_KINDS, "not_checkable", "claims_checkable")}
        n = pooled["claims_checkable"]
        claims[arm] = {"n_entries": len(rows), **pooled,
                       "shares_of_checkable": {k: round(pooled[k] / n, 4) if n else None for k in CLAIM_KINDS},
                       "entries_with_not_checkable": sorted(m for m in audited if m in per[arm]
                                                            and per[arm][m].get("not_checkable")),
                       "checkable_claims_per_entry": _mean([r["claims_checkable"] for r in rows])}
    claims_common = sorted(set(audited) & set(common))

    # Size, variants, cost.
    size, variants, cost = {}, {}, {}
    for arm in ARMS:
        rows = [per[arm][m] for m in common]
        size[arm] = {"chars_per_entry": _mean([r["chars"] for r in rows]),
                     "checkable_claims_per_audited_entry": _mean([per[arm][m]["claims_checkable"]
                                                                   for m in claims_common])}
        variants[arm] = {"recall_mean": _mean([r["variant_recall"] for r in rows]),
                         "n_entries_with_omim_variants": sum(1 for r in rows if r["variant_recall"] is not None),
                         "precision_mean": _mean([r["variant_precision"] for r in rows]),
                         "n_entries_for_precision": sum(1 for r in rows if r["variant_precision"] is not None),
                         "pooled": {k: sum(r[k] for r in rows) for k in ("variants_generated", "variants_matched",
                                                                         "variants_gold")}}
        ran = [per[arm][m] for m in mims if m in per[arm]]
        cost[arm] = {"entries": len(ran), "calls_new_total": sum(r["calls_new"] for r in ran),
                     "calls_new_per_entry": _mean([r["calls_new"] for r in ran]),
                     "usd_new_total": round(sum(r["usd_new"] for r in ran), 2),
                     "usd_new_per_entry": _mean([r["usd_new"] for r in ran]),
                     "usd_method_per_entry": _mean([r["usd_method"] for r in ran]),
                     "wall_minutes_per_entry": _mean([r["wall_seconds"] / 60 for r in ran]),
                     **{f"calls_new_{s}_per_entry": _mean([r.get(f"calls_new_{s}", 0) for r in ran]) for s in STEPS},
                     "audited_entries": sum(1 for m in mims if m in per[arm] and m in set(audited))}

    # Stops and what each arm did.
    stops: dict[str, Any] = {}
    for arm in ARMS:
        st: dict[str, Any] = {"no_draft": {m: _read(run_dir / m / f"eval.{arm}.json").get("stopped")
                                           for m in mims if status[arm][m] == "no_draft"},
                              "safety_stops_by_step": defaultdict(int)}
        for m in mims:
            for step, k in (per[arm].get(m, {}).get("safety_stops") or {}).items():
                st["safety_stops_by_step"][step] += k
        st["safety_stops_by_step"] = dict(st["safety_stops_by_step"])
        if arm == "direct_complete":
            st["checks_failed"] = {m: ((_read(run_dir / m / f"entry.{arm}.json").get("meta") or {})
                                       .get("direct_complete") or {}).get("failures")
                                   for m in mims if status[arm][m] == "incomplete"}
        stops[arm] = st
    d2 = []
    for m in mims:
        if m in per["direct_complete"] and not per["direct_complete"][m].get("no_draft"):
            meta = (_read(run_dir / m / "entry.direct_complete.json").get("meta") or {}).get("direct_complete") or {}
            rev = meta.get("revision") or {}
            d2.append({"mim": m, **{k: meta.get(k) for k in ("papers_checked", "omissions_listed", "omissions_kept")},
                       "revised": rev.get("called"), "sentences_added": rev.get("sentences_added"),
                       "added_citing_other_papers_only": rev.get("added_citing_other_papers_only"),
                       "kept_fields_changed_by_model": [k for k in ("relationships_changed", "synopsis_changed",
                                                                    "variants_changed", "intro_changed") if rev.get(k)],
                       "pmids_lost": rev.get("pmids_lost")})
    d3 = []
    for m in mims:
        if m in per["direct_ensemble"] and not per["direct_ensemble"][m].get("no_draft"):
            meta = (_read(run_dir / m / "entry.direct_ensemble.json").get("meta") or {}).get("direct_ensemble") or {}
            mg = meta.get("merge") or {}
            d3.append({"mim": m, **{k: mg.get(k) for k in ("draft_paragraphs", "merged_paragraphs", "multi_source",
                                                         "rejected_longer", "unknown_ids", "unsourced_dropped",
                                                         "restored", "unused", "groups_restored", "pmids_lost")},
                       "kept_approx": {d: (meta.get("retention") or {}).get(d, {}).get("kept_approx") for d in "ABC"},
                       "sentences": {d: (meta.get("retention") or {}).get(d, {}).get("sentences") for d in "ABC"}})
    ledger_path = run_dir.parent / LEDGER
    result = {
        "run": name, "design": "docs/direct-improvements.md (evaluation design; pilot and changes before the test run)",
        "entries": mims, "n_entries": len(mims),
        "audit_subsample": {"entries": audited, "n": len(audited),
                            **({k: v for k, v in _read(run_dir / AUDIT_SAMPLE).items() if k in ("method", "seed")}
                               if (run_dir / AUDIT_SAMPLE).exists() else {})},
        "completion": {arm: {"counts": {k: sum(1 for v in status[arm].values() if v == k)
                                        for k in ("complete", "incomplete", "no_draft", "not_run")},
                             "not_complete": {m: v for m, v in status[arm].items() if v != "complete"}}
                       for arm in ARMS},
        "compared_entries": common, "n_compared": len(common),
        "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": 10_000, "interval": "percentile 95%, over entries"},
        "facts_conveyed": facts,
        "claims_audited_entries": claims,
        "size": size, "variants": variants, "cost": cost, "stops": stops,
        "d2_completeness_pass": d2, "d3_merge": d3,
        "ledger": first_four_ledger(_read(ledger_path) if ledger_path.exists() else None), "cap": CALL_CAP,
        "per_entry": {arm: {m: {k: v for k, v in r.items() if k not in ("join",)} for m, r in per[arm].items()}
                      for arm in ARMS},
    }
    if any((run_dir / m / f"eval.{EXTENSION}.json").exists() for m in mims):
        result["extension"] = extension_report(run_dir, mims, audited)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "direct_improve.json", result)
    (out_dir / "direct_improve.md").write_text(report_markdown(result), encoding="utf-8")
    return result


def _omission_row(run_dir: Path, mim: str, arm: str) -> dict[str, Any] | None:
    path = run_dir / mim / f"entry.{arm}.json"
    if not path.exists():
        return None
    meta = (_read(path).get("meta") or {})
    if meta.get("stopped"):
        return {"no_draft": True}
    rec = meta.get(INCOMPLETE_KEY[arm]) or {}
    rev = rec.get("revision") or {}
    return {"papers_checked": rec.get("papers_checked"), "papers_failed": rec.get("papers_failed") or [],
            "omissions_listed": rec.get("omissions_listed"), "omissions_kept": rec.get("omissions_kept"),
            "revised": rev.get("called"), "sentences_added": rev.get("sentences_added"),
            "sentences_completed_or_removed": rev.get("sentences_removed"),
            "added_citing_other_papers_only": rev.get("added_citing_other_papers_only"),
            "kept_fields_changed_by_model": [k for k in ("relationships_changed", "synopsis_changed",
                                                         "variants_changed", "intro_changed") if rev.get(k)],
            "pmids_lost": rev.get("pmids_lost") or [], "chars_before": rev.get("chars_before"),
            "chars_after": rev.get("chars_after")}


def extension_report(run_dir: Path, mims: list[str], audited: list[str]) -> dict[str, Any]:
    """D4 against the first four arms, on the entries complete for all five (the symmetric rule).

    Primary: D4 minus the baseline. Secondary: D4 minus D2 and D4 minus D1. Each with
    the bootstrap interval, better / worse / tied and the exact sign test (unadjusted;
    the primary is a single comparison).
    """
    from .compare import _pair_stats

    arms = ALL_ARMS
    status = completion(run_dir, mims, arms)
    common = [m for m in mims if all(status[a][m] == "complete" for a in arms)]
    per: dict[str, dict[str, dict[str, Any]]] = {a: {} for a in arms}
    for a in arms:
        for m in mims:
            if status[a][m] in ("complete", "incomplete"):
                per[a][m] = {**entry_measures(run_dir, m, a), **_usage_row(run_dir, m, a)}
            elif status[a][m] == "no_draft":
                per[a][m] = {"no_draft": True, **_usage_row(run_dir, m, a)}
    comparisons = (("D4_minus_baseline", BASELINE, "primary"), ("D4_minus_D2", "direct_complete", "secondary"),
                   ("D4_minus_D1", "direct_checklist", "secondary"))
    facts: dict[str, Any] = {}
    for key, label, _, _ in MEASURES:
        block: dict[str, Any] = {"label": label, "means": {}, "comparisons": {}}
        for a in arms:
            vals = [per[a][m][key] for m in common if per[a][m].get(key) is not None]
            block["means"][a] = {"mean_over_entries": _mean(vals), "n_entries": len(vals)}
        for name, other, role in comparisons:
            pairs = [(per[EXTENSION][m][key], per[other][m][key]) for m in common
                     if per[EXTENSION][m].get(key) is not None and per[other][m].get(key) is not None]
            if pairs:
                block["comparisons"][name] = {"role": role, "versus": other,
                                              **_pair_stats(pairs, True, random.Random(BOOTSTRAP_SEED))}
        facts[key] = block

    claims = {}
    for a in arms:
        rows = [per[a][m] for m in audited if m in per[a] and not per[a][m].get("no_draft")]
        pooled = {k: sum(r.get(k, 0) for r in rows) for k in (*CLAIM_KINDS, "not_checkable", "claims_checkable")}
        n = pooled["claims_checkable"]
        claims[a] = {"n_entries": len(rows), **pooled,
                     "shares_of_checkable": {k: round(pooled[k] / n, 4) if n else None for k in CLAIM_KINDS},
                     "entries_with_not_checkable": sorted(m for m in audited if m in per[a]
                                                          and per[a][m].get("not_checkable"))}
    claims_common = sorted(set(audited) & set(common))
    size, variants, cost = {}, {}, {}
    for a in arms:
        rows = [per[a][m] for m in common]
        size[a] = {"chars_per_entry": _mean([r["chars"] for r in rows]),
                   "checkable_claims_per_audited_entry": _mean([per[a][m]["claims_checkable"] for m in claims_common])}
        variants[a] = {"recall_mean": _mean([r["variant_recall"] for r in rows]),
                       "n_entries_with_omim_variants": sum(1 for r in rows if r["variant_recall"] is not None),
                       "precision_mean": _mean([r["variant_precision"] for r in rows]),
                       "n_entries_for_precision": sum(1 for r in rows if r["variant_precision"] is not None)}
        ran = [per[a][m] for m in mims if m in per[a]]
        cost[a] = {"entries": len(ran), "calls_new_total": sum(r["calls_new"] for r in ran),
                   "calls_new_per_entry": _mean([r["calls_new"] for r in ran]),
                   "usd_new_total": round(sum(r["usd_new"] for r in ran), 2),
                   "usd_new_per_entry": _mean([r["usd_new"] for r in ran]),
                   "usd_method_per_entry": _mean([r["usd_method"] for r in ran]),
                   "wall_minutes_per_entry": _mean([r["wall_seconds"] / 60 for r in ran])}

    # Omissions: D4 against D2 on the entries where both wrote a draft.
    pairs = []
    for m in mims:
        d4, d2 = _omission_row(run_dir, m, EXTENSION), _omission_row(run_dir, m, "direct_complete")
        if d4 and d2 and not d4.get("no_draft") and not d2.get("no_draft"):
            pairs.append({"mim": m, "d4": d4, "d2": d2})
    tot = lambda arm, k: sum((p[arm][k] or 0) for p in pairs)  # noqa: E731
    kept_diff = [(p["d4"]["omissions_kept"] or 0) - (p["d2"]["omissions_kept"] or 0) for p in pairs]
    omissions = {
        "n_entries": len(pairs),
        "totals": {arm: {k: tot(arm, k) for k in ("omissions_listed", "omissions_kept", "sentences_added",
                                                  "sentences_completed_or_removed")} for arm in ("d4", "d2")},
        "kept_d4_fewer_more_equal": [sum(1 for d in kept_diff if d < 0), sum(1 for d in kept_diff if d > 0),
                                     sum(1 for d in kept_diff if d == 0)],
        "d4_added_citing_other_papers_only": tot("d4", "added_citing_other_papers_only"),
        "d4_entries_model_changed_carried_over_field": [p["mim"] for p in pairs if p["d4"]["kept_fields_changed_by_model"]],
        "d4_entries_citations_lost": [p["mim"] for p in pairs if p["d4"]["pmids_lost"]],
        "per_entry": pairs,
    }
    stops = {"no_draft": {m: _read(run_dir / m / f"eval.{EXTENSION}.json").get("stopped")
                          for m in mims if status[EXTENSION][m] == "no_draft"},
             "checks_failed": {m: ((_read(run_dir / m / f"entry.{EXTENSION}.json").get("meta") or {})
                                   .get(EXTENSION) or {}).get("failures")
                               for m in mims if status[EXTENSION][m] == "incomplete"},
             "safety_stops_by_step": {}}
    for m in mims:
        for step, k in (per[EXTENSION].get(m, {}).get("safety_stops") or {}).items():
            stops["safety_stops_by_step"][step] = stops["safety_stops_by_step"].get(step, 0) + k
    ledger_path = run_dir.parent / LEDGER
    ledger = (_read(ledger_path).get("extensions", {}).get(EXTENSION) if ledger_path.exists() else None)
    return {
        "arm": EXTENSION, "design": "docs/direct-improvements.md, 'Extension: checklist and completeness pass "
                                    "together (D4)'",
        "completion": {a: {"counts": {k: sum(1 for v in status[a].values() if v == k)
                                      for k in ("complete", "incomplete", "no_draft", "not_run")},
                           "not_complete": {m: v for m, v in status[a].items() if v != "complete"}} for a in arms},
        "compared_entries": common, "n_compared": len(common),
        "sign_tests": "unadjusted (primary: one comparison; secondaries reported as such)",
        "facts_conveyed": facts, "claims_audited_entries": claims, "audited_entries": audited,
        "size": size, "variants": variants, "cost": cost, "omissions_d4_vs_d2": omissions, "stops": stops,
        "ledger": ledger, "cap": EXTENSIONS[EXTENSION],
    }


def extension_markdown(x: dict[str, Any]) -> list[str]:
    pct = lambda v: "–" if v is None else f"{100 * v:.1f}%"  # noqa: E731
    pp = lambda v: "–" if v is None else f"{100 * v:+.1f}"  # noqa: E731
    lab = {**LABELS, EXTENSION: "D4 checklist + completeness pass"}
    L = ["", "---", "", "# Extension: D4, the checklist draft with the completeness pass", "",
         f"Designed after the first four arms were run ({x['design']}). D4 starts from D1's checklist draft (from the "
         "cache) and applies D2's completeness pass. The first four arms are not re-run; the sections above are "
         f"unchanged. Comparisons use the {x['n_compared']} entries complete for all five arms (the symmetric rule). "
         "Primary: D4 minus the baseline; secondary: D4 minus D2 and D4 minus D1. Differences in percentage points with "
         "a 95% percentile bootstrap interval over entries (seed 7, 10,000 resamples), better/worse/tied and an exact "
         "sign test, unadjusted.", "",
         "## Completion, all five arms", "", "| Arm | Complete | Incomplete | No draft | Not run | Entries not complete |",
         "|---|---|---|---|---|---|"]
    for a, c in x["completion"].items():
        k = c["counts"]
        L.append(f"| {lab[a]} | {k['complete']} | {k['incomplete']} | {k['no_draft']} | {k['not_run']} | "
                 f"{', '.join(f'{m} ({v})' for m, v in c['not_complete'].items()) or '–'} |")
    names = {"D4_minus_baseline": "D4 − baseline (primary)", "D4_minus_D2": "D4 − D2 (secondary)",
             "D4_minus_D1": "D4 − D1 (secondary)"}
    for key, block in x["facts_conveyed"].items():
        means = "; ".join(f"{lab[a]} {pct(block['means'][a]['mean_over_entries'])}" for a in ALL_ARMS)
        L += ["", f"## D4: {block['label']}", "", f"Means over the compared entries: {means}.", "",
              "| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |", "|---|---|---|---|---|---|"]
        for name, v in block["comparisons"].items():
            ci = f"{pp(v['ci95'][0])} to {pp(v['ci95'][1])}" if v.get("ci95") else "–"
            L.append(f"| {names[name]} | {v['n']} | {pp(v['difference'])} | {ci} | {v['better']}/{v['worse']}/"
                     f"{v['ties']} | {_p(v['sign_test_p'])} |")
    L += ["", f"## D4: claims judged by the audit ({len(x['audited_entries'])} audited entries, as above)", "",
          "| Arm | Entries | Checkable claims | Supported | Partly | Unsupported | Contradicted | Not checkable |",
          "|---|---|---|---|---|---|---|---|"]
    for a, c in x["claims_audited_entries"].items():
        sh = c["shares_of_checkable"]
        L.append(f"| {lab[a]} | {c['n_entries']} | {c['claims_checkable']:,} | {c['supported']:,} ({pct(sh['supported'])}) "
                 f"| {c['partially_supported']:,} ({pct(sh['partially_supported'])}) | {c['unsupported']:,} "
                 f"({pct(sh['unsupported'])}) | {c['contradicted']:,} ({pct(sh['contradicted'])}) | {c['not_checkable']:,} |")
    L += ["", "## D4: size, variants, calls and price", "",
          "| Arm | Characters per entry | Checkable claims per audited entry | Variant recall | Variant precision | "
          "New calls per entry | List price per entry, new | List price per entry, method |",
          "|---|---|---|---|---|---|---|---|"]
    for a in ALL_ARMS:
        sz, v, c = x["size"][a], x["variants"][a], x["cost"][a]
        L.append(f"| {lab[a]} | {sz['chars_per_entry'] or 0:,.0f} | {sz['checkable_claims_per_audited_entry'] or 0:.0f} | "
                 f"{pct(v['recall_mean'])} | {pct(v['precision_mean'])} | {c['calls_new_per_entry'] or 0:.1f} | "
                 f"${c['usd_new_per_entry'] or 0:.2f} | ${c['usd_method_per_entry'] or 0:.2f} |")
    o = x["omissions_d4_vs_d2"]
    t4, t2 = o["totals"]["d4"], o["totals"]["d2"]
    f, mo, eq = o["kept_d4_fewer_more_equal"]
    L += ["", "## D4 and D2: omissions listed and added", "",
          f"On the {o['n_entries']} entries where both wrote a draft: omissions listed D4 {t4['omissions_listed']:,} vs D2 "
          f"{t2['omissions_listed']:,}; kept (quote verified) D4 {t4['omissions_kept']:,} vs D2 {t2['omissions_kept']:,} "
          f"(D4 fewer on {f} entries, more on {mo}, equal on {eq}); sentences added by the revision D4 "
          f"{t4['sentences_added']:,} vs D2 {t2['sentences_added']:,}; existing sentences completed D4 "
          f"{t4['sentences_completed_or_removed']:,} vs D2 {t2['sentences_completed_or_removed']:,}. D4 sentences added that "
          f"cite only papers without listed omissions: {o['d4_added_citing_other_papers_only']}; entries where the model "
          f"changed a carried-over field: {', '.join(o['d4_entries_model_changed_carried_over_field']) or 'none'}; "
          f"citations lost: {', '.join(o['d4_entries_citations_lost']) or 'none'}."]
    st = x["stops"]
    L += ["", "## D4: stops and calls", "",
          f"No draft: {', '.join(f'{m} ({v})' for m, v in st['no_draft'].items()) or 'none'}. Completeness checks failed: "
          f"{st['checks_failed'] or 'none'}. Safety stops by step: {st['safety_stops_by_step'] or 'none'}."]
    lg = x.get("ledger")
    if lg:
        L.append(f"D4 calls in the ledger (pilot included): {lg['calls']:,} of its {x['cap']:,} cap, ${lg['cost_usd']:.2f} "
                 f"list price; safety stops {lg['safety_stops']}, refusals {lg['refusals']}, errors {lg['errors']}.")
    return L


LABELS = {"direct": "Baseline (direct, before repair)", "direct_checklist": "D1 checklist",
          "direct_complete": "D2 completeness pass", "direct_ensemble": "D3 three-draft merge"}


def _p(x) -> str:
    return "–" if x is None else f"{x:.3f}"


def report_markdown(r: dict[str, Any]) -> str:
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}%"  # noqa: E731
    pp = lambda x: "–" if x is None else f"{100 * x:+.1f}"  # noqa: E731
    L = [f"# Improving on direct reading: evaluation (run `{r['run']}`)", "",
         f"{r['n_entries']} entries with at least one paper readable in full and a direct-reading draft; "
         f"{r['n_compared']} complete for every arm are compared. No repair round for any arm. Facts conveyed = "
         "(present + half of partial) / judged frozen facts, mean over entries. Differences are arm minus baseline in "
         f"percentage points with a 95% percentile bootstrap interval over entries ({r['bootstrap']['resamples']:,} "
         f"resamples, seed {r['bootstrap']['seed']}), entries better/worse/tied, exact sign test, Holm-adjusted across "
         "the three arms. Whether the supplied text states a fact is the stored availability judgement (a model "
         "judgement with verified quotes, not checked by a curator).", "",
         "## Completion", "", "| Arm | Complete | Incomplete | No draft | Not run | Entries not complete |",
         "|---|---|---|---|---|---|"]
    for arm, c in r["completion"].items():
        k = c["counts"]
        L.append(f"| {LABELS[arm]} | {k['complete']} | {k['incomplete']} | {k['no_draft']} | {k['not_run']} | "
                 f"{', '.join(f'{m} ({v})' for m, v in c['not_complete'].items()) or '–'} |")
    for key, block in r["facts_conveyed"].items():
        L += ["", f"## {block['label']}", "", "| Arm | Mean over entries | Entries | Facts per entry | Difference | "
              "95% CI | Better/worse/tied | Sign p | Holm p |", "|---|---|---|---|---|---|---|---|---|"]
        for arm in ARMS:
            m = block["means"][arm]
            v = block["versus_baseline"].get(arm)
            ci = f"{pp(v['ci95'][0])} to {pp(v['ci95'][1])}" if v and v.get("ci95") else "–"
            diff = (f"{pp(v['difference'])} | {ci} | "
                    f"{v['better']}/{v['worse']}/{v['ties']} | {_p(v['sign_test_p'])} | {_p(v.get('sign_test_p_holm'))}"
                    if v else "– | – | – | – | –")
            L.append(f"| {LABELS[arm]} | {pct(m['mean_over_entries'])} | {m['n_entries']} | "
                     f"{m['facts_per_entry'] if m['facts_per_entry'] is None else round(m['facts_per_entry'], 1)} | {diff} |")
    a = r["audit_subsample"]
    L += ["", f"## Claims judged by the audit ({a['n']} audited entries)", "",
          f"Audited entries ({a.get('method', 'all entries')}): {', '.join(a['entries'])}. Shares are over checkable "
          "claims; a stopped audit call leaves its paper's claims not checkable and does not affect completion.", "",
          "| Arm | Entries | Checkable claims | Supported | Partly | Unsupported | Contradicted | Not checkable | "
          "Entries with not-checkable claims |", "|---|---|---|---|---|---|---|---|---|"]
    for arm, c in r["claims_audited_entries"].items():
        sh = c["shares_of_checkable"]
        L.append(f"| {LABELS[arm]} | {c['n_entries']} | {c['claims_checkable']:,} | {c['supported']:,} "
                 f"({pct(sh['supported'])}) | {c['partially_supported']:,} ({pct(sh['partially_supported'])}) | "
                 f"{c['unsupported']:,} ({pct(sh['unsupported'])}) | {c['contradicted']:,} ({pct(sh['contradicted'])}) | "
                 f"{c['not_checkable']:,} | {', '.join(c['entries_with_not_checkable']) or '–'} |")
    L += ["", "## Size, variants, calls and price", "",
          "| Arm | Characters per entry | Checkable claims per audited entry | Variant recall (entries) | Variant "
          "precision (entries) | New calls per entry (generate / audit / score) | List price per entry, new | List "
          "price per entry, method | Wall minutes per entry |", "|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        s, v, c = r["size"][arm], r["variants"][arm], r["cost"][arm]
        L.append(f"| {LABELS[arm]} | {s['chars_per_entry']:,.0f} | {s['checkable_claims_per_audited_entry'] or 0:.0f} | "
                 f"{pct(v['recall_mean'])} ({v['n_entries_with_omim_variants']}) | {pct(v['precision_mean'])} "
                 f"({v['n_entries_for_precision']}) | {c['calls_new_per_entry'] or 0:.1f} "
                 f"({c['calls_new_generate_per_entry'] or 0:.1f} / {c['calls_new_audit_per_entry'] or 0:.1f} / "
                 f"{c['calls_new_score_per_entry'] or 0:.1f}) | ${c['usd_new_per_entry'] or 0:.2f} | "
                 f"${c['usd_method_per_entry'] or 0:.2f} | {c['wall_minutes_per_entry'] or 0:.1f} |")
    L += ["", "Characters and variants are over the compared entries; calls and price over every entry the arm ran. "
          "'New' counts calls made in this run (the baseline's draft and audit come from the cache); 'method' is "
          "what the arm costs from scratch, including the cached baseline draft that D2 and D3 start from.", "",
          "## Stops", ""]
    for arm, st in r["stops"].items():
        L.append(f"- {LABELS[arm]}: no draft {len(st['no_draft'])}"
                 + (f" ({', '.join(st['no_draft'])})" if st["no_draft"] else "")
                 + f"; safety stops by step {st['safety_stops_by_step'] or 'none'}"
                 + (f"; completeness checks failed: {st['checks_failed']}" if st.get("checks_failed") else ""))
    d2 = r["d2_completeness_pass"]
    if d2:
        L += ["", "## D2: what the completeness pass did", "",
              f"Entries {len(d2)}; omissions listed {sum(x['omissions_listed'] or 0 for x in d2):,}, kept (quote "
              f"verified) {sum(x['omissions_kept'] or 0 for x in d2):,}; revision called on "
              f"{sum(1 for x in d2 if x['revised'])}; sentences added {sum(x['sentences_added'] or 0 for x in d2):,}, "
              f"of which citing only papers without listed omissions {sum(x['added_citing_other_papers_only'] or 0 for x in d2)}; "
              f"entries where the model changed a carried-over field: "
              f"{', '.join(x['mim'] for x in d2 if x['kept_fields_changed_by_model']) or 'none'}; citations lost: "
              f"{', '.join(x['mim'] for x in d2 if x['pmids_lost']) or 'none'}."]
    d3 = r["d3_merge"]
    if d3:
        tot = lambda k: sum(x[k] or 0 for x in d3)  # noqa: E731
        L += ["", "## D3: what the merge did", "",
              f"Entries {len(d3)}; draft paragraphs {tot('draft_paragraphs'):,} merged into {tot('merged_paragraphs'):,} "
              f"({tot('multi_source'):,} from more than one draft); rejected as longer than their sources "
              f"{tot('rejected_longer')}; unknown IDs {tot('unknown_ids')}; unsourced paragraphs dropped "
              f"{tot('unsourced_dropped')}; draft paragraphs left out and put back {tot('restored')}, left out and not "
              f"put back (their papers cited elsewhere) {tot('unused')}; variant groups restored {tot('groups_restored')}; "
              f"citations lost: {', '.join(x['mim'] for x in d3 if x['pmids_lost']) or 'none'}. Sentences of each "
              "draft with at least 85% of their content words in the merged draft (rough): "
              + "; ".join(f"{d} {sum(x['kept_approx'][d] or 0 for x in d3):,} of {sum(x['sentences'][d] or 0 for x in d3):,}"
                          for d in "ABC") + "."]
    lg = r.get("ledger")
    if lg:
        L += ["", f"Calls: {lg['calls']:,} new model calls of the {r['cap']:,} cap (pilot included), ${lg['cost_usd']:.2f} "
                  f"list price; safety stops {lg['safety_stops']}, refusals {lg['refusals']}, errors {lg['errors']}."]
    if r.get("extension"):
        L += extension_markdown(r["extension"])
    return "\n".join(L) + "\n"


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


def project_extension(run: str, pilot: str, arm: str = EXTENSION, like: str = "direct_complete") -> dict[str, Any]:
    """New calls, list price and time for an extension arm on a finished run, without a model call.

    `like` is the arm whose procedure the extension repeats (D4 repeats D2's). Its actual
    usage per entry and step in `run` is scaled, step by step, by the ratio of the
    extension's usage to `like`'s on the pilot's entries. In the pilot, `like`'s
    generation was first made in the draft step (`progress.log`), the extension's in
    its run. An entry where `like` wrote no draft gets the mean of `like`'s drafted
    entries with the same audit status (audited or not).
    """
    run_dir, pilot_dir = run_dir_of(run), run_dir_of(pilot)
    first = {}
    for line in (pilot_dir / "progress.log").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("step") == "draft only":
            first[(row["mim"], row["arm"])] = row
    pilot_sum: dict[str, dict[str, float]] = {a: defaultdict(float) for a in (arm, like)}
    for mim in entries_of(pilot_dir):
        u = _read(pilot_dir / mim / "usage.json")["arms"]
        if arm not in u or like not in u:
            continue
        for a in (arm, like):
            for step in STEPS:
                b = u[a].get(step) or {}
                calls, usd = b.get("calls", 0) - b.get("cached", 0), b.get("list_price_usd", 0.0)
                if step == "generate" and (mim, a) in first:
                    calls = first[(mim, a)]["calls"] - first[(mim, a)]["cached"]
                    usd = first[(mim, a)]["usd"]
                pilot_sum[a][f"{step}_calls"] += calls
                pilot_sum[a][f"{step}_usd"] += usd
                pilot_sum[a][f"{step}_minutes"] += (first[(mim, a)]["seconds"] if step == "generate" and (mim, a) in first
                                                    else b.get("wall_seconds", 0)) / 60
    ratio = {k: (pilot_sum[arm][k] / pilot_sum[like][k] if pilot_sum[like][k] else 1.0) for k in pilot_sum[like]}

    mims = entries_of(run_dir)
    sample = audit_sample(run_dir)
    audited = sample if sample is not None else set(mims)
    rows = {}
    for mim in mims:
        u = (_read(run_dir / mim / "usage.json").get("arms", {}) if (run_dir / mim / "usage.json").exists() else {})
        stopped = _read(run_dir / mim / f"eval.{like}.json").get("stopped") if (run_dir / mim / f"eval.{like}.json").exists() else "not run"
        if stopped or like not in u:
            rows[mim] = None
            continue
        rows[mim] = {f"{step}_{k}": ((u[like].get(step) or {}).get(src, 0) - ((u[like].get(step) or {}).get("cached", 0)
                                                                                if k == "calls" else 0)) / (60 if k == "minutes" else 1)
                     for step in STEPS for k, src in (("calls", "calls"), ("usd", "list_price_usd"),
                                                      ("minutes", "wall_seconds"))}
    keys = [f"{step}_{k}" for step in STEPS for k in ("calls", "usd", "minutes")]
    for mim, r in rows.items():
        if r is None:
            peers = [rows[m] for m in mims if rows[m] is not None and ((m in audited) == (mim in audited))]
            rows[mim] = {k: statistics.mean(p[k] for p in peers) for k in keys}
            rows[mim]["imputed"] = True
    projected = {k: sum(r[k] * ratio.get(k, 1.0) for r in rows.values()) for k in keys}
    calls = sum(projected[f"{s}_calls"] for s in STEPS)
    usd = sum(projected[f"{s}_usd"] for s in STEPS)
    minutes = sum(projected[f"{s}_minutes"] for s in STEPS)
    like_calls = sum(r[f"{s}_calls"] for r in rows.values() for s in STEPS)
    ledger_path = run_dir.parent / LEDGER
    used = (_read(ledger_path).get("extensions", {}).get(arm, {}).get("calls", 0) if ledger_path.exists() else 0)
    return {
        "arm": arm, "like": like, "run": run, "pilot": pilot, "n_entries": len(mims),
        "entries_imputed": sorted(m for m, r in rows.items() if r.get("imputed")),
        "pilot_ratio_by_step": {k: round(v, 3) for k, v in ratio.items()},
        "like_actual_new_calls_with_imputation": round(like_calls),
        "projected": {"new_calls": round(calls), "list_price_usd": round(usd, 2),
                      "minutes_one_entry_at_a_time": round(minutes), "hours_with_3_jobs_approx": round(minutes / 60 / 3, 1),
                      **{k: round(v, 1) for k, v in projected.items()}},
        "extension_calls_used_so_far": used, "extension_cap": EXTENSIONS.get(arm),
        "headroom_after": EXTENSIONS.get(arm, 0) - used - round(calls),
    }


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
    s.add_argument("--audit-sample", type=int, default=0,
                   help=f"Audit only this many entries, drawn with random.Random({AUDIT_SEED}) (0: audit all).")
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
    fr = sub.add_parser("report")
    fr.add_argument("--run", required=True)
    fr.add_argument("--out", default="results/direct_improve")
    pe = sub.add_parser("project-extension")
    pe.add_argument("--run", default="direct_improve")
    pe.add_argument("--pilot", default="direct_improve_pilot")
    p = sub.add_parser("project")
    p.add_argument("--pilot", required=True)
    p.add_argument("--entries-file", required=True)
    p.add_argument("--source", default=SOURCE_RUN)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.cmd == "setup":
        print(setup(args.run, _mims(args.entries, args.entries_file) or [], args.source))
        if args.audit_sample:
            print("audit sample:", draw_audit_sample(args.run, args.audit_sample))
    elif args.cmd == "run":
        arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
        unknown = set(arms) - set(ALL_ARMS)
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
    elif args.cmd == "report":
        final_report(args.run, Path(args.out))
        print((Path(args.out) / "direct_improve.md").read_text())
    elif args.cmd == "project-extension":
        result = project_extension(args.run, args.pilot)
        _write(run_dir_of(args.pilot) / "projection.extension.json", result)
        print(json.dumps(result, indent=1))
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
