"""Frozen gold facts: one fact list per OMIM paragraph, reused for every draft.

`evaluate.eval_gold_text` asks the judge, in one call per draft, to split OMIM's
paragraph into atomic facts *and* to mark each against the draft. The judge sees
the draft while splitting, so the same paragraph yields a different fact list for
every strategy, facts cannot be aligned across strategies, and a difference of a
point or two between strategies sits on unmeasured splitting variation.

Here the two steps are separate:

split   one call per gold paragraph (stage "judge") splits it into atomic facts
        without seeing any draft. The list is stored under the paragraph's content
        in the data home (`<home>/gold_facts/`) and reused for every strategy,
        run and judge replicate. It is never split under a replicate salt: a
        missing list is split by an unsalted wrapper, so it is the same list a
        main run would have made.
mark    one call per paragraph and draft marks every frozen fact present, partial,
        absent or contradicted in the draft text about that paper. The reply must
        cover every fact number exactly once; a reply that does not is asked again
        once, and facts still not covered are recorded as `unjudged`.
avail   one call per paragraph and paper text (the gap analysis): is the fact
        stated in the text the writer had for the paper? This does not depend on
        the strategy, so it is judged once and stored with the frozen list.

Files:

    <home>/gold_facts/<k[:2]>/<k>.json                     the frozen list (OMIM-derived)
    <home>/gold_facts/avail/<k[:2]>/<k>.<src>[.<salt>].json  availability per source text
    <run>/<entry>/gold_facts.json                         the entry's lists (OMIM-derived)
    <run>/<entry>/eval.<s>.json  gold_text_frozen[_whole]  marks: fact id, status, note
    <run>/<entry>/judge_<salt>.<s>.json                   the same marks under a judge replicate

Fact wording lives only in the store and in `gold_facts.json`, both outside git
(data/ and runs/ are ignored); the eval files carry fact ids, never wording, and
`export` drops the notes as well.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from pydantic import BaseModel

from .cache import stable_hash
from .evaluate import _draft_text_for, _tally
from .models import GeneratedEntry, GoldEntry, GoldParagraph, squash

log = logging.getLogger(__name__)

SPLIT_VERSION = "gold-facts-v1"
STATUSES = ("present", "partial", "absent", "contradicted")
LEVEL_RANK = {"title": 0, "abstract": 1, "fulltext": 2}
NO_DRAFT_NOTE = "no draft text cites this paper"

# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

SPLIT_SYSTEM = """\
You are preparing a reference for scoring machine-drafted OMIM entries. You are given a REFERENCE \
passage written by OMIM's curators, summarising one or more papers. No draft is shown: your list \
will be used, unchanged, to score many different drafts.

Split the reference into atomic facts: single checkable assertions such as who was studied, how many \
patients or families, ancestry, each clinical, imaging or laboratory finding, each variant with its \
nucleotide change, protein change and zygosity, segregation or de novo status, each functional \
result, and each conclusion. Cover everything the passage asserts, each fact once, in the order of \
the passage. Keep each fact short, and make it readable on its own: name the subject where the \
passage makes it clear ("the proband had seizures", not "had seizures"). Do not make facts out of \
OMIM's own cross-reference numbers in parentheses such as "(540000)" or "(590050.0001)", or out of \
the bare attribution to the authors; a draft is not expected to reproduce those.\
"""

_MARK_TEMPLATE = """\
You are scoring a machine-drafted OMIM entry against facts taken from text written by OMIM's own \
curators. You are given the REFERENCE passage (the curators' summary of one or more papers, shown for \
context), a numbered list of FACTS drawn from it, and {draft}.

For every numbered fact, decide whether the draft conveys it:

present       the draft states the same fact.
partial       the draft conveys the fact less precisely or incompletely.
absent        the draft does not mention it.
contradicted  the draft states something incompatible with it.

Judge meaning, not wording. Treat equivalent notations as the same fact ("3697G-A", "c.3697G>A" and \
"m.3697G>A"; "gly131-to-ser", "G131S" and "p.Gly131Ser"; a gene's alias and its approved symbol; \
"mental retardation" and "intellectual disability"). Judge the listed facts as they are: do not add, \
split, merge or reword them. Give exactly one verdict for every fact number, each number once. Add a \
brief `note` only for partial and contradicted facts, saying what differs; otherwise leave it empty.\
"""

MARK_SYSTEM = _MARK_TEMPLATE.format(draft="the DRAFT text that cites the same paper(s)")
MARK_WHOLE_SYSTEM = _MARK_TEMPLATE.format(
    draft="the WHOLE DRAFT entry (the fact may be stated anywhere in it, under any citation or none)")

RETRY_NOTE = ("\n\nYour verdicts must cover every fact number from 1 to {n}, each number exactly once, "
              "and no other numbers.")


class XSplit(BaseModel):
    facts: list[str]


class XMark(BaseModel):
    n: int
    status: Literal["present", "partial", "absent", "contradicted"]
    note: str


class XMarks(BaseModel):
    marks: list[XMark]


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #


def paragraph_key(text: str) -> str:
    """The store key of an OMIM paragraph: its content (whitespace-normalised) and the split version."""
    return stable_hash(SPLIT_VERSION, squash(text))


def fact_id(key: str, n: int) -> str:
    """A fact's id: the paragraph key's first 12 hex digits and the fact's position (1-based)."""
    return f"{key[:12]}.{n}"


def _exclusive_write(path: Path, data: Any) -> bool:
    """Write `data` to `path` unless it exists; True when this call wrote it (first writer wins)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


class FactStore:
    """Frozen fact lists keyed by paragraph content, and availability judgements per source text."""

    def __init__(self, root: Path | str | None = None):
        if root is None:
            from .config import get_settings

            root = get_settings().home / "gold_facts"
        self.root = Path(root)

    def path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self.path(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def put(self, record: dict[str, Any]) -> dict[str, Any]:
        """Store a frozen list; if one is already stored for the key, keep and return that one."""
        if _exclusive_write(self.path(record["key"]), record):
            return record
        return self.get(record["key"]) or record

    def avail_path(self, key: str, source_key: str, salt: str = "") -> Path:
        name = f"{key}.{source_key[:16]}" + (f".{salt}" if salt else "") + ".json"
        return self.root / "avail" / key[:2] / name

    def get_avail(self, key: str, source_key: str, salt: str = "") -> dict[str, Any] | None:
        try:
            return json.loads(self.avail_path(key, source_key, salt).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def put_avail(self, record: dict[str, Any], salt: str = "") -> dict[str, Any]:
        path = self.avail_path(record["key"], record["source_key"], salt)
        if _exclusive_write(path, record):
            return record
        return self.get_avail(record["key"], record["source_key"], salt) or record


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def replicate_salt(llm) -> str:
    settings = getattr(llm, "settings", None)
    return getattr(settings, "replicate", "") or ""


_unsalted: dict[int, Any] = {}


def splitter(llm):
    """The wrapper that splits: `llm` itself, or under a replicate salt an unsalted copy of it.

    A frozen list must not depend on the replicate, so a list missing from the
    store is split exactly as a main run would split it (and usually read back from
    the model cache).
    """
    if not replicate_salt(llm):
        return llm
    with _locks_guard:
        clone = _unsalted.get(id(llm))
        if clone is None:
            from .llm import LLM

            clone = LLM(replace(llm.settings, replicate=""))
            _unsalted[id(llm)] = clone
        return clone


# --------------------------------------------------------------------------- #
# Split
# --------------------------------------------------------------------------- #


def _split_prompt(text: str) -> str:
    return f"<reference>\n{text}\n</reference>"


def frozen_facts(paragraphs: list[GoldParagraph], llm, store: FactStore | None = None,
                 *, split_missing: bool = True) -> list[dict[str, Any] | None]:
    """The frozen fact list of each paragraph, from the store or split now (and stored).

    A paragraph whose split failed (or is missing with `split_missing` off) comes
    back as None; it is retried next time.
    """
    store = store or FactStore()
    keys = [paragraph_key(p.text) for p in paragraphs]
    out: dict[str, dict[str, Any] | None] = {k: store.get(k) for k in set(keys)}
    missing = sorted(k for k, rec in out.items() if rec is None)
    if missing and split_missing:
        text_of = {k: p for k, p in zip(keys, paragraphs)}
        locks = [_lock_for(k) for k in missing]   # sorted order: no deadlock between threads
        for lock in locks:
            lock.acquire()
        try:
            for k in missing:   # another thread may have split it while we waited
                out[k] = store.get(k)
            todo = [k for k in missing if out[k] is None]
            split_llm = splitter(llm)
            replies = split_llm.map("judge", SPLIT_SYSTEM, [_split_prompt(text_of[k].text) for k in todo], XSplit) \
                if todo else []
            for k, reply in zip(todo, replies):
                if isinstance(reply, Exception):
                    log.warning("frozen facts: split of paragraph %s failed: %s", k[:12], reply)
                    continue
                facts = [squash(f) for f in reply.facts if squash(f)]
                settings = split_llm.settings
                out[k] = store.put({
                    "key": k, "version": SPLIT_VERSION, "text": text_of[k].text, "pmids": text_of[k].pmids,
                    "facts": [{"id": fact_id(k, n), "n": n, "fact": f} for n, f in enumerate(facts, 1)],
                    "split": {"stage": "judge", "model": settings.model_for("judge"),
                              "effort": settings.effort_for("judge"),
                              "system_hash": stable_hash(SPLIT_SYSTEM)[:16],
                              "created": time.strftime("%Y-%m-%dT%H:%M:%S")},
                })
        finally:
            for lock in locks:
                lock.release()
    return [out[k] for k in keys]


# --------------------------------------------------------------------------- #
# Calls whose reply must cover every numbered item exactly once
# --------------------------------------------------------------------------- #


def _unique(items: Iterable[Any], n_items: int) -> tuple[dict[int, Any], bool]:
    """Items by number where the number occurs once; and whether the reply covered 1..n exactly."""
    items = list(items)
    counts = Counter(i.n for i in items)
    by_n = {i.n: i for i in items if counts[i.n] == 1 and 1 <= i.n <= n_items}
    complete = len(items) == n_items and set(counts) == set(range(1, n_items + 1))
    return by_n, complete


def map_covering(llm, system: str, prompts: list[str], output: type[BaseModel], sizes: list[int],
                 items: Callable[[Any], Iterable[Any]]) -> list[tuple[dict[int, Any], int, str | None]]:
    """Run each prompt; a reply that does not cover 1..size exactly once is asked again once.

    Returns, per prompt, the usable items by number (the retry's, completed by the
    first reply's where the retry left a number out), how many attempts were made,
    and the error if every attempt failed.
    """
    first = llm.map("judge", system, prompts, output) if prompts else []
    results: list[tuple[dict[int, Any], int, str | None]] = []
    retry_idx: list[int] = []
    for i, (reply, size) in enumerate(zip(first, sizes)):
        if isinstance(reply, Exception):
            results.append(({}, 1, str(reply)))
            retry_idx.append(i)
            continue
        by_n, complete = _unique(items(reply), size)
        results.append((by_n, 1, None))
        if not complete:
            retry_idx.append(i)
    if retry_idx:
        again = llm.map("judge", system, [prompts[i] + RETRY_NOTE.format(n=sizes[i]) for i in retry_idx], output)
        for i, reply in zip(retry_idx, again):
            earlier, _, err = results[i]
            if isinstance(reply, Exception):
                results[i] = (earlier, 2, None) if earlier else \
                    ({}, 2, f"{err}; retry: {reply}" if err else f"retry: {reply}")
                continue
            by_n, _ = _unique(items(reply), sizes[i])
            results[i] = ({**earlier, **by_n}, 2, None)
    return results


# --------------------------------------------------------------------------- #
# Mark
# --------------------------------------------------------------------------- #


def _mark_prompt(reference: str, facts: list[str], draft: str, whole: bool) -> str:
    listed = "\n".join(f"{n}. {f}" for n, f in enumerate(facts, 1))
    empty = "(the draft is empty)" if whole else "(the draft has no text citing these papers)"
    return (f"<reference>\n{reference}\n</reference>\n\n<facts>\n{listed}\n</facts>\n\n"
            f"<draft>\n{draft or empty}\n</draft>")


def whole_draft_text(entry: GeneratedEntry) -> str:
    chunks = []
    if entry.intro:
        chunks.append(f"[Introduction] {entry.intro.text}")
    for section in entry.sections:
        for para in section.paragraphs:
            chunks.append(f"[{section.heading}] {para.text}")
    for av in entry.allelic_variants:
        for para in av.paragraphs:
            chunks.append(f"[Allelic variant {av.name}] {para.text}")
    return "\n\n".join(chunks)


def mark_facts(records: list[dict[str, Any]], drafts: list[str], llm, *, whole: bool = False
               ) -> list[dict[str, Any]]:
    """Mark each record's frozen facts against the matching draft text.

    Returns per record {"facts": [{id, status, note}], "attempts", "error"}; every
    frozen fact appears once, with status `unjudged` where no verdict was obtained.
    A record with no draft text (cited-text mode) needs no call: nothing about the
    paper was written, so every fact is absent.
    """
    out: list[dict[str, Any] | None] = [None] * len(records)
    jobs = []
    for i, (rec, draft) in enumerate(zip(records, drafts)):
        if not rec["facts"]:
            out[i] = {"facts": [], "attempts": 0, "error": None}
        elif not draft.strip() and not whole:
            out[i] = {"facts": [{"id": f["id"], "status": "absent", "note": NO_DRAFT_NOTE} for f in rec["facts"]],
                      "attempts": 0, "error": None}
        else:
            jobs.append(i)
    prompts = [_mark_prompt(records[i]["text"], [f["fact"] for f in records[i]["facts"]], drafts[i], whole)
               for i in jobs]
    replies = map_covering(llm, MARK_WHOLE_SYSTEM if whole else MARK_SYSTEM, prompts, XMarks,
                           [len(records[i]["facts"]) for i in jobs], lambda r: r.marks)
    for i, (by_n, attempts, error) in zip(jobs, replies):
        facts = []
        for f in records[i]["facts"]:
            m = by_n.get(f["n"])
            facts.append({"id": f["id"], "status": m.status, "note": squash(m.note)} if m is not None
                         else {"id": f["id"], "status": "unjudged", "note": ""})
        out[i] = {"facts": facts, "attempts": attempts, "error": error}
    return out  # type: ignore[return-value]


def tally(facts: list[dict[str, str]]) -> dict[str, Any]:
    """`evaluate._tally` over the judged facts, plus the frozen total and the unjudged count.

    `n_facts` is the frozen list's length (identical for every strategy); rates are
    over the facts that received a verdict, `n_judged`.
    """
    judged = [f for f in facts if f["status"] != "unjudged"]
    return {**_tally(judged), "n_facts": len(facts), "n_judged": len(judged),
            "unjudged": len(facts) - len(judged)}


def paragraph_level(pmids: list[str], levels: dict[str, str]) -> str:
    found = [levels[p] for p in pmids if p in levels]
    return min(found, key=LEVEL_RANK.get) if found else "not_retrieved"


def eval_gold_text_frozen(
    entry: GeneratedEntry, gold: GoldEntry, levels: dict[str, str], llm,
    store: FactStore | None = None, *, whole: bool = False,
    records: list[dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Coverage of OMIM's in-scope paragraphs, marked against frozen fact lists.

    Same shape as `evaluate.eval_gold_text` (without the reference and draft
    wording): per paragraph the paragraph key, pmids, content level, facts with id,
    status and note, counts and coverage; totals; by content level. `levels` maps
    PMID to how much of the paper could be read. With `whole`, every paragraph's
    facts are marked against the whole draft instead of the text citing the paper.
    """
    paragraphs = gold.scoped_paragraphs
    out_of_scope = len(gold.gold_paragraphs) - len(paragraphs)
    base = {"n_paragraphs": len(paragraphs), "n_out_of_scope": out_of_scope, "split_version": SPLIT_VERSION,
            "draft_scope": "whole" if whole else "cited", "replicate": replicate_salt(llm) or None}
    if not paragraphs:
        return base
    if records is None:
        records = frozen_facts(paragraphs, llm, store)
    ok = [i for i, rec in enumerate(records) if rec is not None]
    whole_text = whole_draft_text(entry) if whole else ""
    drafts = [whole_text if whole else _draft_text_for(entry, paragraphs[i].pmids) for i in ok]
    marks = dict(zip(ok, mark_facts([records[i] for i in ok], drafts, llm, whole=whole)))  # type: ignore[misc]

    per_paragraph, by_level, all_facts = [], defaultdict(list), []
    for i, para in enumerate(paragraphs):
        level = paragraph_level(para.pmids, levels)
        rec = records[i]
        row: dict[str, Any] = {"key": rec["key"] if rec else paragraph_key(para.text), "pmids": para.pmids,
                               "content_level": level}
        if rec is None:
            row.update(facts=[], error="no frozen fact list (split failed)", **tally([]))
        else:
            m = marks[i]
            row.update(facts=m["facts"], **tally(m["facts"]))
            if m["attempts"] > 1:
                row["mark_attempts"] = m["attempts"]
            if m["error"]:
                row["error"] = m["error"]
            all_facts.extend(m["facts"])
            by_level[level].extend(m["facts"])
        per_paragraph.append(row)
    return {
        **base, **tally(all_facts),
        "n_paragraphs_without_facts": sum(1 for r in records if r is None),
        "n_mark_retries": sum(1 for r in per_paragraph if r.get("mark_attempts", 1) > 1),
        "by_content_level": {lvl: tally(facts) for lvl, facts in sorted(by_level.items())},
        "paragraphs": per_paragraph,
    }


# --------------------------------------------------------------------------- #
# Per-entry fact file
# --------------------------------------------------------------------------- #


def write_gold_facts(entry_dir: Path, mim: str, records: list[dict[str, Any] | None],
                     paragraphs: list[GoldParagraph], availability: dict[str, Any] | None = None) -> None:
    """`<entry>/gold_facts.json`: the entry's frozen lists (OMIM-derived; never exported).

    Availability judgements already in the file are kept unless new ones replace them.
    """
    from .pipeline import _write

    path = entry_dir / "gold_facts.json"
    old: dict[str, Any] = {}
    if path.exists():
        try:
            old = {p["key"]: p.get("availability") for p in json.loads(path.read_text(encoding="utf-8"))["paragraphs"]}
        except (json.JSONDecodeError, KeyError, OSError):
            old = {}
    availability = availability or {}
    rows = []
    for para, rec in zip(paragraphs, records):
        key = rec["key"] if rec else paragraph_key(para.text)
        row = {"key": key, "pmids": para.pmids, "text": para.text,
               "facts": [{"id": f["id"], "fact": f["fact"]} for f in rec["facts"]] if rec else None}
        avail = availability.get(key) or old.get(key)
        if avail:
            row["availability"] = avail
        rows.append(row)
    _write(path, {"mim": mim, "split_version": SPLIT_VERSION, "note": "OMIM-derived text: do not commit or export.",
                  "paragraphs": rows})


# --------------------------------------------------------------------------- #
# Re-scoring existing drafts
# --------------------------------------------------------------------------- #


def judge_file(strategy: str, salt: str) -> str:
    """Where a judge replicate's marks go. Not `eval.*.json`: summaries and comparisons glob that."""
    return f"judge_{salt}.{strategy}.json"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rescore_entry(entry_dir: Path, strategies: Iterable[str], llm, store: FactStore | None = None,
                  *, whole: bool = False) -> dict[str, Any]:
    """Frozen scoring of the drafts already in an entry folder; nothing is regenerated or re-audited."""
    from .pipeline import _write

    store = store or FactStore()
    salt = replicate_salt(llm)
    gold = GoldEntry.model_validate(_read(entry_dir / "gold.json"))
    paragraphs = gold.scoped_paragraphs
    levels = {r["pmid"]: r.get("content_level", "not_retrieved") for r in _read(entry_dir / "papers.json")} \
        if (entry_dir / "papers.json").exists() else {}
    records = frozen_facts(paragraphs, llm, store) if paragraphs else []
    write_gold_facts(entry_dir, gold.mim, records, paragraphs)

    done: dict[str, Any] = {}
    for strategy in strategies:
        eval_path, entry_path = entry_dir / f"eval.{strategy}.json", entry_dir / f"entry.{strategy}.json"
        if not eval_path.exists() or not entry_path.exists():
            continue
        evaluation = _read(eval_path)
        if evaluation.get("stopped"):
            done[strategy] = {"stopped": True}
            continue
        entry = GeneratedEntry.model_validate(_read(entry_path))
        scores = {"gold_text_frozen": eval_gold_text_frozen(entry, gold, levels, llm, store, records=records)}
        if whole:
            scores["gold_text_frozen_whole"] = eval_gold_text_frozen(entry, gold, levels, llm, store, whole=True,
                                                                     records=records)
        if salt:
            _write(entry_dir / judge_file(strategy, salt),
                   {"mim": gold.mim, "strategy": strategy, "replicate": salt, **scores})
        else:
            evaluation.update(scores)
            _write(eval_path, evaluation)
        done[strategy] = {k: _brief(v) for k, v in scores.items()}
        done[strategy]["gold_text"] = _brief(evaluation.get("gold_text") or {})
    return {"mim": gold.mim, "strategies": done}


def _brief(score: dict[str, Any]) -> dict[str, Any]:
    keys = ("n_paragraphs", "n_facts", "n_judged", "unjudged", "present", "partial", "absent", "contradicted",
            "coverage", "n_paragraphs_without_facts", "n_mark_retries")
    return {k: score.get(k) for k in keys if k in score}


def rescore_run(run_dir: Path, strategies: Iterable[str] | None = None, *, whole: bool = False, jobs: int = 1,
                entries: Iterable[str] | None = None, llm=None, store: FactStore | None = None) -> dict[str, Any]:
    """Frozen scoring of every scored draft of a run. Returns per-entry briefs, means and model usage."""
    from .llm import LLM
    from .pipeline import _write

    llm = llm or LLM()
    store = store or FactStore()
    wanted = set(entries) if entries is not None else None
    dirs = sorted(p for p in run_dir.iterdir() if p.is_dir() and (p / "gold.json").exists()
                  and (wanted is None or p.name in wanted))
    if strategies is None:
        strategies = sorted({p.name.split(".")[1] for d in dirs for p in d.glob("eval.*.json")})
    strategies = list(strategies)

    def one(entry_dir: Path) -> dict[str, Any] | None:
        try:
            result = rescore_entry(entry_dir, strategies, llm, store, whole=whole)
        except Exception as exc:  # noqa: BLE001 - one broken entry must not lose the rest
            log.exception("[%s] rescore failed: %s", entry_dir.name, exc)
            return {"mim": entry_dir.name, "error": f"{type(exc).__name__}: {exc}"}
        log.info("[%s] rescored %s", entry_dir.name, ", ".join(
            f"{s} {v.get('gold_text_frozen', {}).get('coverage')}" for s, v in result["strategies"].items()))
        return result

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        results = [r for r in pool.map(one, dirs) if r is not None]

    means: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        rows = [r["strategies"][strategy] for r in results
                if strategy in r.get("strategies", {}) and not r["strategies"][strategy].get("stopped")]
        if not rows:
            continue
        cell: dict[str, Any] = {"n_entries": len(rows)}
        for key in ("gold_text", "gold_text_frozen", "gold_text_frozen_whole"):
            vals = [row[key]["coverage"] for row in rows if key in row and row[key].get("coverage") is not None]
            if vals:
                cell[f"{key}_coverage_mean"] = round(sum(vals) / len(vals), 4)
                cell[f"{key}_n_facts"] = sum(row[key].get("n_facts") or 0 for row in rows if key in row)
        cell["unjudged"] = sum(row["gold_text_frozen"].get("unjudged", 0) for row in rows if "gold_text_frozen" in row)
        means[strategy] = cell
    usage = llm.usage.summary()["total"]
    split_llm = _unsalted.get(id(llm))   # only if a list had to be split under a replicate salt
    if split_llm is not None:
        extra = split_llm.usage.summary()["total"]
        usage = {k: round(usage.get(k, 0) + extra.get(k, 0), 4) for k in usage}
    summary = {"run": run_dir.name, "replicate": replicate_salt(llm) or None, "whole_draft": whole,
               "strategies": strategies, "n_entries": len(results),
               "failures": {r["mim"]: r["error"] for r in results if "error" in r},
               "means": means, "usage": usage, "entries": results}
    salt = replicate_salt(llm)
    _write(run_dir / (f"rescore.judge_{salt}.json" if salt else "rescore.json"), summary)
    return summary


# --------------------------------------------------------------------------- #
# Availability (gap analysis on frozen facts)
# --------------------------------------------------------------------------- #


def availability(records: list[dict[str, Any]], sources: list[str], llm, store: FactStore, *,
                 per_paper_chars: int) -> tuple[list[dict[str, Any]], int]:
    """Whether each frozen fact is stated in its paragraph's source (the paper text the writer had).

    Judged once per (paragraph, source text) and stored. Returns per record
    {key, source_key, per_paper_chars, rows: [{id, in_text, model_in_text, quote,
    quote_verified}]} and the number of paragraphs that needed judge calls.
    """
    from .gaps import GAPS_SYSTEM, XGapVerdicts, _prompt, verdict_row
    from .grounding import SourceIndex

    salt = replicate_salt(llm)
    out: list[dict[str, Any] | None] = [None] * len(records)
    jobs = []
    for i, (rec, source) in enumerate(zip(records, sources)):
        source_key = stable_hash(source)
        base = {"key": rec["key"], "source_key": source_key, "per_paper_chars": per_paper_chars}
        hit = store.get_avail(rec["key"], source_key, salt)
        if hit is not None:
            out[i] = hit
        elif not source.strip():
            # Nothing of the paper was retrieved: no fact can be in the text.
            out[i] = {**base, "rows": [{"id": f["id"], "in_text": "no", "model_in_text": None, "quote": "",
                                        "quote_verified": False} for f in rec["facts"]]}
        elif not rec["facts"]:
            out[i] = {**base, "rows": []}
        else:
            jobs.append((i, base))
    prompts = [_prompt(records[i]["text"], [f["fact"] for f in records[i]["facts"]], sources[i]) for i, _ in jobs]
    replies = map_covering(llm, GAPS_SYSTEM, prompts, XGapVerdicts, [len(records[i]["facts"]) for i, _ in jobs],
                           lambda r: r.verdicts)
    for (i, base), (by_n, attempts, error) in zip(jobs, replies):
        index = SourceIndex(sources[i])
        rows = [{"id": f["id"], **verdict_row(by_n.get(f["n"]), index)} for f in records[i]["facts"]]
        record = {**base, "attempts": attempts, "error": error, "rows": rows}
        out[i] = store.put_avail(record, salt) if error is None else record
    return out, len(jobs)  # type: ignore[return-value]
