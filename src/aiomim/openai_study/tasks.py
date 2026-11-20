"""The study's tasks, and how each one runs the project's own code.

    A1:<mim>:<strategy>  fixed-fact marks on the main run's draft     facts.eval_gold_text_frozen (as `rescore`)
    A2F:<mim>            availability of every fixed fact             gaps.gap_entry_frozen (as `gaps --frozen`)
    A2C:<mim>            conveyed facts against the other papers      gaps.conveyed_entry (as `gaps --conveyed`)
    A3:<mim>:<arm>       fixed-fact marks on a hidden-full-text arm   facts.eval_gold_text_frozen (as
                                                                      `secondhand.rescore_frozen_entry` and
                                                                      `score_before_repair_entry`)
    B1:<mim>:<strategy>  a new draft, then its fixed-fact marks       pipeline.build_entries (no audit) and the
                                                                      scoring step of `pipeline.run_entry`
    B2:<mim>:<arm>       full text: as B1 direct; abstract only: `synthesize_direct` on the papers with the
                         full text hidden exactly as `secondhand.check_entry` hides it; both marked on the
                         gold paragraphs about the hidden papers

Each run starts from scratch in a fresh working folder and replays every reply the
study's cache holds; the first missing reply raises `Pending`. A task's result is
written only when its code path finishes (`private/results/<task>.json`).
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import Study, StudyPaths, read_json, write_json, write_text
from .errors import ForbiddenCall, NetworkBlocked, Pending, StudyError

log = logging.getLogger(__name__)

A3_ARMS = ("fulltext_before_repair", "abstract", "secondhand")
B2_ARMS = ("fulltext", "abstract")
B1_STRATEGIES = ("direct", "kg", "closedbook")
A1_STRATEGIES = ("direct", "agent", "kg", "cohort", "recall", "closedbook")

FINAL = ("complete", "incomplete", "stopped", "failed")

_WRITER_LABELS = {
    "direct": {"synthesize:direct", "normalize", "judge:mark"},
    "kg": {"extract", "normalize", "synthesize:kg", "judge:mark"},
    "closedbook": {"recall:closedbook", "normalize", "judge:mark"},
}


@dataclass(frozen=True)
class TaskSpec:
    kind: str
    mim: str
    variant: str = ""

    @property
    def id(self) -> str:
        return ":".join(x for x in (self.kind, self.mim, self.variant) if x)

    @property
    def file(self) -> str:
        return self.id.replace(":", "__")

    @classmethod
    def parse(cls, task_id: str) -> TaskSpec:
        parts = task_id.split(":")
        return cls(parts[0], parts[1], parts[2] if len(parts) > 2 else "")

    def allowed(self) -> frozenset[str]:
        if self.kind in ("A1", "A3"):
            return frozenset({"judge:mark"})
        if self.kind == "A2F":
            return frozenset({"judge:avail"})
        if self.kind == "A2C":
            return frozenset({"judge:avail_other"})
        if self.kind == "B1":
            return frozenset(_WRITER_LABELS[self.variant])
        if self.kind == "B2":
            return frozenset(_WRITER_LABELS["direct"])
        raise StudyError(f"unknown task kind {self.kind}")


def plan_tasks(study: Study) -> list[TaskSpec]:
    """The task list `study.json` asks for, in a fixed order."""
    t = study.tasks()
    out: list[TaskSpec] = []
    if (t.get("A1") or {}).get("enabled", True) and t.get("A1"):
        for mim in t["A1"]["entries"]:
            for s in t["A1"].get("strategies", A1_STRATEGIES):
                out.append(TaskSpec("A1", mim, s))
    a2 = t.get("A2") or {}
    if a2 and a2.get("enabled", True):
        parts = a2.get("parts", ["frozen", "conveyed"])
        for mim in a2["entries"]:
            if "frozen" in parts:
                out.append(TaskSpec("A2F", mim))
            if "conveyed" in parts:
                out.append(TaskSpec("A2C", mim))
    a3 = t.get("A3") or {}
    if a3 and a3.get("enabled", True):
        for mim in a3["entries"]:
            for arm in a3.get("arms", A3_ARMS):
                out.append(TaskSpec("A3", mim, arm))
    b1 = t.get("B1") or {}
    if b1 and b1.get("enabled", True):
        for mim in b1["entries"]:
            for s in b1.get("strategies", B1_STRATEGIES):
                out.append(TaskSpec("B1", mim, s))
    b2 = t.get("B2") or {}
    if b2 and b2.get("enabled", True):
        for mim in b2["entries"]:
            for arm in b2.get("arms", B2_ARMS):
                out.append(TaskSpec("B2", mim, arm))
    return out


# --------------------------------------------------------------------------- #
# The bundle, read side
# --------------------------------------------------------------------------- #


class Bundle:
    """Read access to the private bundle (see `bundle.py` for what it holds)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        if not (self.root / "MANIFEST.json").exists():
            raise StudyError(f"no bundle at {self.root} (MANIFEST.json missing)")
        self.manifest = json.loads((self.root / "MANIFEST.json").read_text(encoding="utf-8"))
        self._lock = threading.Lock()

    def _json(self, *parts: str) -> Any:
        return json.loads((self.root.joinpath(*parts)).read_text(encoding="utf-8"))

    def has(self, *parts: str) -> bool:
        return self.root.joinpath(*parts).exists()

    @lru_cache(maxsize=256)
    def seed(self, mim: str):
        from ..models import Seed

        return Seed.model_validate(self._json("entries", mim, "seed.json"))

    @lru_cache(maxsize=256)
    def gold(self, mim: str):
        from ..models import GoldEntry

        return GoldEntry.model_validate(self._json("entries", mim, "gold.json"))

    @lru_cache(maxsize=256)
    def paper_records(self, mim: str) -> list[dict[str, Any]]:
        return self._json("entries", mim, "papers.json")

    def levels(self, mim: str) -> dict[str, str]:
        return {r["pmid"]: r.get("content_level", "not_retrieved") for r in self.paper_records(mim)}

    @lru_cache(maxsize=128)
    def _papers(self, mim: str):
        from ..models import Paper

        return tuple(Paper.model_validate(p) for p in self._json("entries", mim, "papers.full.json"))

    def papers(self, mim: str) -> list:
        """The entry's papers in the order the original run retrieved them (copies)."""
        return [p.model_copy(deep=True) for p in self._papers(mim)]

    def hidden(self, mim: str) -> set[str]:
        return set(self._json("entries", mim, "hidden.json")["hidden_papers"])

    def main_draft(self, mim: str, strategy: str):
        from ..models import GeneratedEntry

        return GeneratedEntry.model_validate(self._json("drafts", "main", mim, f"entry.{strategy}.json"))

    def secondhand_draft(self, mim: str, arm: str):
        from ..models import GeneratedEntry

        return GeneratedEntry.model_validate(self._json("drafts", "secondhand", mim, f"entry.{arm}.json"))

    def claude_marks(self, source: str, mim: str, name: str) -> dict[str, Any] | None:
        path = self.root / "claude" / "marks" / source / mim / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def claude_availability(self, mim: str) -> dict[str, Any] | None:
        path = self.root / "claude" / "availability" / f"{mim}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def claude_conveyed(self, mim: str) -> dict[str, Any] | None:
        path = self.root / "claude" / "conveyed" / f"{mim}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def entries(self) -> list[str]:
        return sorted(p.name for p in (self.root / "entries").iterdir() if p.is_dir())


# --------------------------------------------------------------------------- #
# Running a task
# --------------------------------------------------------------------------- #


class ReadOnlyCache:
    """A model cache that is read, never written; records which keys it found (bundle verification)."""

    def __init__(self, inner):
        self.inner = inner
        self.root = getattr(inner, "root", None)
        self.hits: set[str] = set()
        self.looked_up: set[str] = set()
        self._lock = threading.Lock()

    def get_json(self, key: str, max_age_s: float | None = None):
        value = self.inner.get_json(key, max_age_s)
        with self._lock:
            self.looked_up.add(key)
            if value is not None:
                self.hits.add(key)
        return value

    def put_json(self, key: str, value: Any) -> None:
        return None

    def get_text(self, key: str, max_age_s: float | None = None):
        return self.inner.get_text(key, max_age_s)

    def put_text(self, key: str, text: str) -> None:
        return None

    def path(self, key: str):
        return self.inner.path(key)


class Context:
    """What a pass over the tasks shares: study, bundle, settings, recorder and stores."""

    def __init__(self, paths: StudyPaths, study: Study | None, bundle: Bundle, settings, recorder,
                 *, reply_cache=None):
        from ..facts import FactStore

        self.paths = paths
        self.study = study
        self.bundle = bundle
        self.settings = settings
        self.recorder = recorder
        self.reply_cache = reply_cache
        # The study's own store: the fixed lists, and the OpenAI judge's availability judgements.
        self.store = FactStore(settings.home / "gold_facts")
        # Claude's store, read only: the fixed lists and Claude's availability judgements (A2C reads them).
        self.claude_store = ReadOnlyFactStore(bundle.root / "factstore")
        self.work = paths.work / "tasks"

    def llm(self, spec: TaskSpec):
        from ..llm import LLM
        from .backend import StudyBackend

        llm = LLM(self.settings)
        if self.reply_cache is not None:
            llm.cache = self.reply_cache
        llm.backend = StudyBackend(settings=self.settings, cache=llm.cache, recorder=self.recorder,
                                   task_id=spec.id, allowed=spec.allowed())
        return llm

    def workdir(self, spec: TaskSpec) -> Path:
        d = self.work / spec.file
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        return d


def _read_only_store_class():
    from ..facts import FactStore

    class _ReadOnlyFactStore(FactStore):
        def put(self, record):
            raise ForbiddenCall("the bundle's fact store is read only (a fixed fact list would be re-split)")

        def put_avail(self, record, salt: str = ""):
            raise ForbiddenCall("the bundle's fact store is read only (Claude's availability judgement missing)")

    return _ReadOnlyFactStore


def ReadOnlyFactStore(root: Path):
    return _read_only_store_class()(root)


# ----------------------------------------------------------------- helpers


def _marks_status(score: dict[str, Any], stops: int) -> tuple[str, dict[str, Any]]:
    paragraphs = score.get("paragraphs") or []
    errors = sum(1 for p in paragraphs if p.get("error"))
    detail = {"n_paragraphs": score.get("n_paragraphs", 0), "n_facts": score.get("n_facts", 0),
              "n_judged": score.get("n_judged", 0), "unjudged": score.get("unjudged", 0),
              "paragraphs_with_error": errors, "mark_retries": score.get("n_mark_retries", 0), "safety_stops": stops,
              "coverage": score.get("coverage")}
    if stops:
        return "stopped", detail
    if errors:
        return "failed", detail
    if detail["unjudged"]:
        return "incomplete", detail
    return "complete", detail


def _claude_eval_file(bundle: Bundle, mim: str) -> dict[str, Any]:
    marks = bundle.claude_marks("main", mim, "direct")
    if marks is None:
        raise StudyError(f"{mim}: Claude's marks of the direct draft are not in the bundle")
    return {"mim": mim, "strategy": "direct", "gold_text_frozen": {"paragraphs": marks["paragraphs"]}}


def _entry_folder(ctx: Context, spec: TaskSpec) -> Path:
    """A working entry folder in the layout `gaps` reads: gold.json, papers.json, eval.direct.json."""
    d = ctx.workdir(spec)
    src = ctx.bundle.root / "entries" / spec.mim
    for name in ("gold.json", "papers.json", "seed.json"):
        shutil.copyfile(src / name, d / name)
    write_json(d / "eval.direct.json", _claude_eval_file(ctx.bundle, spec.mim))
    return d


def _stops(llm) -> int:
    return int(getattr(llm, "safety_stops", 0) or 0)


# ----------------------------------------------------------------- runners


def run_a1(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """`facts.rescore_entry` for one strategy, without writing into the source folder."""
    from ..facts import eval_gold_text_frozen, frozen_facts

    gold = ctx.bundle.gold(spec.mim)
    levels = ctx.bundle.levels(spec.mim)
    entry = ctx.bundle.main_draft(spec.mim, spec.variant)
    paragraphs = gold.scoped_paragraphs
    records = frozen_facts(paragraphs, llm, ctx.store) if paragraphs else []
    score = eval_gold_text_frozen(entry, gold, levels, llm, ctx.store, records=records)
    status, detail = _marks_status(score, _stops(llm))
    return status, {"detail": detail, "gold_text_frozen": score}


def run_a3(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """`secondhand.rescore_frozen_entry` (abstract, secondhand) or `score_before_repair_entry` (full text)."""
    from ..facts import eval_gold_text_frozen, frozen_facts
    from ..secondhand import restrict_gold

    gold = ctx.bundle.gold(spec.mim)
    hidden = ctx.bundle.hidden(spec.mim)
    gold_h = restrict_gold(gold, hidden)
    paragraphs = gold_h.scoped_paragraphs
    levels = ctx.bundle.levels(spec.mim)
    if spec.variant != "fulltext_before_repair":
        levels = {k: ("abstract" if k in hidden and v == "fulltext" else v) for k, v in levels.items()}
    entry = ctx.bundle.secondhand_draft(spec.mim, spec.variant)
    records = frozen_facts(paragraphs, llm, ctx.store) if paragraphs else []
    score = eval_gold_text_frozen(entry, gold_h, levels, llm, ctx.store, records=records)
    status, detail = _marks_status(score, _stops(llm))
    return status, {"detail": detail, "gold_text_frozen": score}


def _avail_rows(entry_dir: Path) -> dict[str, Any]:
    data = read_json(entry_dir / "gold_facts.json", {}) or {}
    out = {}
    for para in data.get("paragraphs") or []:
        a = para.get("availability")
        if a:
            out[para["key"]] = {"source_key": a.get("source_key"), "per_paper_chars": a.get("per_paper_chars"),
                                "rows": [{k: r.get(k) for k in ("id", "in_text", "model_in_text", "quote_verified")}
                                         for r in a.get("rows") or []]}
    return out


def run_a2f(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """`gaps.gap_entry_frozen` for direct reading, judged by this study's model into the study's store."""
    from ..gaps import gap_entry_frozen

    d = _entry_folder(ctx, spec)
    papers = {p.pmid: p for p in ctx.bundle.papers(spec.mim)}
    result = gap_entry_frozen(d, "direct", llm, papers, ctx.store)
    avail = _avail_rows(d)
    rows = [r for a in avail.values() for r in a["rows"]]
    unjudged = sum(1 for r in rows if r.get("in_text") == "unjudged")
    stops = _stops(llm)
    detail = {"n_facts": len(rows), "unjudged": unjudged, "n_calls": result.get("n_calls"),
              "n_errors": result.get("n_errors"), "safety_stops": stops}
    status = ("stopped" if stops else "failed" if result.get("n_errors") else
              "incomplete" if unjudged else "complete")
    return status, {"detail": detail, "availability": avail, "tally": result.get("tally")}


def run_a2c(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """`gaps.conveyed_entry` for direct reading: Claude's marks and own-text verdicts select the facts and
    the prompts (exactly the prompts of the original run); this study's model answers them."""
    from ..gaps import conveyed_entry

    d = _entry_folder(ctx, spec)
    papers = {p.pmid: p for p in ctx.bundle.papers(spec.mim)}
    result = conveyed_entry(d, "direct", llm, papers, ctx.claude_store)
    facts = [{k: f.get(k) for k in ("id", "draft_status", "own", "other", "other_model", "other_quote_verified",
                                     "class")}
             for para in result.get("paragraphs") or [] for f in para.get("facts") or []]
    checked = [f for f in facts if f.get("own") in ("no", "partly")]
    unjudged = sum(1 for f in checked if f.get("other") in (None, "unjudged"))
    stops = _stops(llm)
    detail = {"n_conveyed": len(facts), "n_rechecked": len(checked), "unjudged": unjudged,
              "n_calls": result.get("n_calls"), "n_errors": result.get("n_errors"), "safety_stops": stops}
    status = ("stopped" if stops else "failed" if result.get("n_errors") else
              "incomplete" if unjudged else "complete")
    return status, {"detail": detail, "facts": facts, "tally": result.get("tally")}


def _writer_status(entry) -> tuple[str, str]:
    from ..llm import EMPTY_REPLY, SAFETY_STOP

    stopped = entry.meta.get("stopped")
    if not stopped:
        failed = (entry.meta.get("extraction") or {}).get("papers_failed") or []
        return ("incomplete", f"{len(failed)} paper(s) failed in extraction") if failed else ("complete", "")
    if SAFETY_STOP in stopped:
        return "stopped", "the writer's reply was stopped by the safety filter"
    if EMPTY_REPLY in stopped:
        return "failed", "the writer returned an empty reply twice"
    return "failed", "no draft"


def _score_new_draft(ctx: Context, spec: TaskSpec, llm, entry, gold, levels) -> tuple[str, dict[str, Any]]:
    """The scoring step of `pipeline.run_entry` (frozen lists, cited-text marks)."""
    from ..facts import eval_gold_text_frozen, frozen_facts
    from ..pipeline import _phase

    _phase(llm, "score")
    records = frozen_facts(gold.scoped_paragraphs, llm, ctx.store) if gold.scoped_paragraphs else None
    score = eval_gold_text_frozen(entry, gold, levels, llm, ctx.store, records=records)
    return score


def _writer_result(ctx: Context, spec: TaskSpec, llm, entry, gold, levels, workdir: Path) -> tuple[str, dict]:
    from ..render import entry_markdown

    writer_status, why = _writer_status(entry)
    stops_writing = _stops(llm)
    result: dict[str, Any] = {"writer_status": writer_status, "writer_note": why, "entry": entry.model_dump(),
                              "markdown": entry_markdown(entry, show_flags=False)}
    if entry.meta.get("stopped"):
        result["detail"] = {"writer_status": writer_status, "safety_stops": stops_writing}
        return writer_status, result
    score = _score_new_draft(ctx, spec, llm, entry, gold, levels)
    judge_status, detail = _marks_status(score, _stops(llm) - stops_writing)
    detail.update(writer_status=writer_status, writer_safety_stops=stops_writing,
                  papers_failed=(entry.meta.get("extraction") or {}).get("papers_failed") or [])
    result.update(detail=detail, judge_status=judge_status, gold_text_frozen=score)
    status = writer_status if writer_status != "complete" else judge_status
    return status, result


def run_b1(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """`pipeline.build_entries` for one strategy with the audit off, then `run_entry`'s scoring."""
    from ..pipeline import RunConfig, build_entries

    seed, gold = ctx.bundle.seed(spec.mim), ctx.bundle.gold(spec.mim)
    papers = ctx.bundle.papers(spec.mim)
    d = ctx.workdir(spec)
    cfg = RunConfig(run="openai_study", strategies=(spec.variant,), verify=False, repair=False, evaluate=False)
    entries, _ = build_entries(seed, papers, cfg, llm, d)
    levels = {p.pmid: p.content_level for p in papers}
    return _writer_result(ctx, spec, llm, entries[spec.variant], gold, levels, d)


def run_b2(ctx: Context, spec: TaskSpec, llm) -> tuple[str, dict[str, Any]]:
    """Direct reading from the full text (as B1) or with the full text hidden (as `secondhand.check_entry`),
    scored on the gold paragraphs about the hidden papers (as `secondhand.rescore_frozen_entry`)."""
    from ..llm import LLMRefusal
    from ..models import GeneratedEntry
    from ..pipeline import RunConfig, build_entries
    from ..secondhand import restrict_gold
    from ..synthesize import synthesize_direct

    seed, gold = ctx.bundle.seed(spec.mim), ctx.bundle.gold(spec.mim)
    papers = ctx.bundle.papers(spec.mim)
    hidden = ctx.bundle.hidden(spec.mim)
    gold_h = restrict_gold(gold, hidden)
    levels = {p.pmid: p.content_level for p in papers}
    d = ctx.workdir(spec)
    if spec.variant == "fulltext":
        cfg = RunConfig(run="openai_study", strategies=("direct",), verify=False, repair=False, evaluate=False)
        entries, _ = build_entries(seed, papers, cfg, llm, d)
        entry = entries["direct"]
    else:
        blind = [p.model_copy(update={"fulltext": None, "fulltext_source": None}) if p.pmid in hidden else p
                 for p in papers]
        try:
            entry = synthesize_direct(seed, blind, llm)
            entry.meta["condition"] = "abstract"
        except LLMRefusal as exc:
            entry = GeneratedEntry(mim=seed.mim, entry_type=seed.entry_type, title=seed.title,
                                   meta={"strategy": "direct", "condition": "abstract", "stopped": str(exc)})
        levels = {k: ("abstract" if k in hidden and v == "fulltext" else v) for k, v in levels.items()}
    return _writer_result(ctx, spec, llm, entry, gold_h, levels, d)


RUNNERS: dict[str, Callable] = {"A1": run_a1, "A2F": run_a2f, "A2C": run_a2c, "A3": run_a3, "B1": run_b1,
                                "B2": run_b2}


@dataclass
class Outcome:
    spec: TaskSpec
    status: str                 # a FINAL status, "waiting" (Pending) or "error" (kit / environment problem)
    payload: dict[str, Any] | None = None
    message: str = ""
    requests: int = 0
    stops_not_sent: int = 0


def run_one(ctx: Context, spec: TaskSpec) -> Outcome:
    llm = ctx.llm(spec)
    try:
        status, payload = RUNNERS[spec.kind](ctx, spec, llm)
        return Outcome(spec, status, payload, requests=llm.backend.requests,
                       stops_not_sent=llm.backend.stops_not_sent)
    except Pending as exc:
        return Outcome(spec, "waiting", message=str(exc), requests=llm.backend.requests)
    except (ForbiddenCall, NetworkBlocked) as exc:
        return Outcome(spec, "error", message=f"{type(exc).__name__}: {exc}", requests=llm.backend.requests)
    except StudyError as exc:
        return Outcome(spec, "error", message=f"StudyError: {exc}", requests=llm.backend.requests)
    except Exception as exc:  # noqa: BLE001 - the project's own failure (e.g. two bad replies): final
        log.warning("%s failed: %s", spec.id, exc)
        return Outcome(spec, "failed", {"detail": {"exception": type(exc).__name__},
                                        "traceback": traceback.format_exc(limit=8)},
                       message=type(exc).__name__, requests=llm.backend.requests)


def run_all(ctx: Context, specs: list[TaskSpec], jobs: int = 8,
            on_done: Callable[[Outcome], None] | None = None) -> list[Outcome]:
    """Run tasks concurrently. Each task's own model calls fan out further inside the project's code."""
    out: list[Outcome] = []
    lock = threading.Lock()

    def one(spec: TaskSpec) -> None:
        o = run_one(ctx, spec)
        with lock:
            out.append(o)
        if on_done:
            on_done(o)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for fut in [pool.submit(one, s) for s in specs]:
            fut.result()
    order = {s.id: i for i, s in enumerate(specs)}
    return sorted(out, key=lambda o: order[o.spec.id])


def write_result(paths: StudyPaths, outcome: Outcome) -> None:
    """A finished task's result, private (it holds judge notes and paper-derived text)."""
    payload = dict(outcome.payload or {})
    record = {"task": outcome.spec.id, "kind": outcome.spec.kind, "mim": outcome.spec.mim,
              "variant": outcome.spec.variant, "status": outcome.status, **payload}
    write_json(paths.results / f"{outcome.spec.file}.json", record, indent=None)
    if outcome.spec.kind in ("B1", "B2") and "entry" in payload:
        d = paths.results / "drafts" / outcome.spec.kind / outcome.spec.mim
        write_json(d / f"entry.{outcome.spec.variant}.json", payload["entry"])
        write_text(d / f"entry.{outcome.spec.variant}.md", payload.get("markdown", ""))


def read_result(paths: StudyPaths, spec: TaskSpec) -> dict[str, Any] | None:
    return read_json(paths.results / f"{spec.file}.json")
