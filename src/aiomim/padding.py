"""Experiment A2: controlled padding of the input (docs/experiments-round2.md, section A2).

Each entry, its own papers, its header (gene withheld) and its frozen fact lists are held fixed; only
the list of supplied papers grows, with unrelated full-text papers already fetched for other entries:

    P0  the entry's own papers: the existing drafts of `runs/omim100`, as they were before the repair
        round, rebuilt from the model cache with no generation call;
    P1  padded to about 500,000 characters of paper text (as direct reading counts it);
    P2  padded to about 1,200,000 characters (design: 1,800,000; reduced) (P1's added papers are a subset of P2's).

Four strategies (direct, agent, kg, cohort), no audit and no repair at any level. Every draft is
scored on the entry's own frozen fact lists, credited to draft paragraphs citing the paper, exactly
as `rescore` marks a draft.

    python -m aiomim.padding build                 choose entries and padding; write inputs and P0 drafts
    python -m aiomim.padding run --entries A,B     generate P1 and P2 drafts (resumable, cached)
    python -m aiomim.padding score                 frozen scoring, added-paper citations
    python -m aiomim.padding summarise             results/padding/padding.json and padding.md

Run files live in `runs/padding/` (git-ignored; they hold OMIM-derived marks). `results/padding/`
holds counts, percentages and entry numbers only.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import re
import shutil
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field

log = logging.getLogger("aiomim.padding")

RUN = "padding"
LEVELS = ("P0", "P1", "P2")
PADDED = ("P1", "P2")
TARGETS = {"P1": 500_000, "P2": 1_200_000}   # P2 reduced from 1,800,000 at the user's request (deviation)
STRATEGIES = ("direct", "agent", "kg", "cohort")
SOURCE_RUN = "omim100"
EVALSET = "evalsets/ablation40.tsv"
ABLATION_RESULTS = "results/ablation40/strategies.json"
N_ENTRIES = 8   # reduced from 12 at the user's request (deviation)
MIN_ENTRIES = 6
# Added papers longer than the per-paper extraction cap (extract.MAX_SOURCE_CHARS) are not used, so
# that no added paper is itself cut by the extract-then-write strategies.
MAX_ADDED_CHARS = 180_000
SEED_PREFIX = "aiomim-A2-padding"
BOOTSTRAP_SEED = 20261120
MAX_CONCURRENT_CALLS = 4
CALL_CAP = 800


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #


def select_entries(rows: list[dict[str, str]], complete: Iterable[str], n: int = N_ENTRIES) -> list[str]:
    """Entries complete for every ablation variant with at least half their papers in full text,
    in entry-number order, the first `n`."""
    ok = set(complete)
    chosen = [r["mim"] for r in rows
              if r["mim"] in ok and 2 * int(r["n_fulltext"]) >= int(r["n_papers"]) and int(r["n_papers"]) > 0]
    return sorted(chosen, key=int)[:n]


def entry_rng(mim: str) -> random.Random:
    return random.Random(f"{SEED_PREFIX}:{mim}")


def eligible_pool(pool: dict[str, dict[str, Any]], own: Iterable[str], genes: Iterable[str],
                  max_chars: int = MAX_ADDED_CHARS) -> tuple[list[str], dict[str, int]]:
    """Pool papers that may pad an entry: not its own, not cited by any entry sharing a causal gene,
    not naming one of its genes in their text, of known provenance, and no longer than `max_chars`.

    `pool` maps PMID -> {"chars": int, "entry_genes": [list of gene lists, one per citing entry],
    "mentions": set of the entry genes the text names (filled by the caller)}. Returns the eligible
    PMIDs sorted (the order is then shuffled by the caller) and counts of exclusions by reason."""
    own, genes = set(own), {g.upper() for g in genes}
    keep, why = [], {"own": 0, "shares_gene": 0, "names_gene": 0, "unknown_gene": 0, "too_long": 0}
    for pmid, info in sorted(pool.items()):
        if pmid in own:
            why["own"] += 1
        elif any(not g for g in info["entry_genes"]):
            why["unknown_gene"] += 1
        elif any(genes & {x.upper() for x in g} for g in info["entry_genes"]):
            why["shares_gene"] += 1
        elif genes & {m.upper() for m in info.get("mentions", ())}:
            why["names_gene"] += 1
        elif info["chars"] > max_chars:
            why["too_long"] += 1
        else:
            keep.append(pmid)
    return keep, why


def fill_to_target(base: int, sizes: list[int], target: int) -> int:
    """How many of `sizes` (in order) to add to `base` to come closest to `target` from a prefix.

    Papers are added until the total reaches the target; the last one is kept only if that leaves
    the total nearer the target than stopping before it."""
    total, k = base, 0
    while k < len(sizes) and total < target:
        total += sizes[k]
        k += 1
    if k and total - target >= target - (total - sizes[k - 1]):
        k -= 1
    return k


def plan_padding(own_chars: int, candidates: list[str], sizes: dict[str, int], rng: random.Random,
                 targets: dict[str, int] = TARGETS) -> dict[str, list[str]]:
    """Added papers per level: one seeded order of the candidates, each level a prefix of it, so a
    smaller level's additions are a subset of a larger one's."""
    order = list(candidates)
    rng.shuffle(order)
    out = {"order": order}
    for level, target in sorted(targets.items(), key=lambda kv: kv[1]):
        k = fill_to_target(own_chars, [sizes[p] for p in order], target)
        out[level] = order[:k]
    return out


def supplied_order(own: list[str], added_p2: list[str], level_added: list[str], rng: random.Random) -> list[str]:
    """The supplied list for one level: own and added papers shuffled together with the entry's seed.

    One permutation of P2's supplied set is drawn; each level keeps its members in that order."""
    everything = list(own) + list(added_p2)
    rng.shuffle(everything)
    wanted = set(own) | set(level_added)
    return [p for p in everything if p in wanted]


def coverage(frozen: dict[str, Any] | None) -> float | None:
    """OMIM facts conveyed: (present + half of partial) over judged facts, unrounded."""
    if not frozen or not frozen.get("n_judged"):
        return None
    return (frozen.get("present", 0) + 0.5 * frozen.get("partial", 0)) / frozen["n_judged"]


def added_citations(entry: dict[str, Any], added: set[str]) -> dict[str, Any]:
    """Paragraphs of a draft (with text) and how many cite an added paper; which added papers are cited."""
    paras = []
    if entry.get("intro"):
        paras.append(("intro", entry["intro"]))
    for s in entry.get("sections", []):
        paras.extend((s.get("name", ""), p) for p in s.get("paragraphs", []))
    for v in entry.get("allelic_variants", []):
        paras.extend(("allelic_variants", p) for p in v.get("paragraphs", []))
    with_text = [(where, p) for where, p in paras if (p.get("text") or "").strip()]
    citing = [(where, p) for where, p in with_text if added & set(p.get("pmids", []))]
    cited = sorted({x for _, p in citing for x in p.get("pmids", []) if x in added})
    rel = sorted({x for r in entry.get("relationships", []) for x in r.get("pmids", []) if x in added})
    syn = sorted({x for s in entry.get("clinical_synopsis", []) for x in s.get("pmids", []) if x in added})
    return {"n_paragraphs": len(with_text), "n_citing_added": len(citing),
            "share_citing_added": round(len(citing) / len(with_text), 4) if with_text else None,
            "added_cited": cited, "added_in_relationships": rel, "added_in_synopsis": syn}


def classify(eval_row: dict[str, Any] | None, entry_meta: dict[str, Any] | None) -> str:
    """complete / incomplete / no_draft, as `compare.completion_status` decides it."""
    if eval_row is None or entry_meta is None or eval_row.get("stopped") or entry_meta.get("stopped"):
        return "no_draft"
    for value in entry_meta.values():
        if isinstance(value, dict) and isinstance(value.get("papers_failed"), list) and value["papers_failed"]:
            return "incomplete"
    return "complete"


def complete_sets(status: dict[str, dict[str, dict[str, str]]], entries: list[str],
                  strategies: Iterable[str] = STRATEGIES) -> dict[str, list[str]]:
    """Entries every strategy completed: at each level on its own, and at every level ("all").

    `status[level][strategy][mim]` is a completion class."""
    out: dict[str, list[str]] = {}
    for level, by_s in status.items():
        out[level] = [m for m in entries if all(by_s.get(s, {}).get(m) == "complete" for s in strategies)]
    out["all"] = [m for m in entries if all(m in out[level] for level in status)]
    return out


def paired(values: list[tuple[float, float]], seed: int = BOOTSTRAP_SEED) -> dict[str, Any] | None:
    """Mean of a - b with a percentile bootstrap 95% interval over entries, better/worse/tied, sign test."""
    from .compare import _pair_stats

    if not values:
        return None
    return _pair_stats(values, True, random.Random(seed))


# --------------------------------------------------------------------------- #
# Paths and small I/O
# --------------------------------------------------------------------------- #


def _settings():
    from .config import get_settings

    return get_settings()


def run_dir() -> Path:
    return _settings().runs / RUN


def results_dir() -> Path:
    return Path("results") / RUN


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
    from .pipeline import _write as write

    write(path, data)


def _evalset_rows() -> list[dict[str, str]]:
    with open(EVALSET, encoding="utf-8") as fh:
        return list(csv.DictReader((line for line in fh if not line.startswith("#")), delimiter="\t"))


def _ablation_complete() -> list[str]:
    data = _read(Path(ABLATION_RESULTS))
    by_s = data["completion"]
    sets = [set(v["complete"]) for v in by_s.values()]
    return sorted(set.intersection(*sets))


# --------------------------------------------------------------------------- #
# Throttle: at most four model calls at once, across every thread
# --------------------------------------------------------------------------- #

_SLOTS = threading.Semaphore(MAX_CONCURRENT_CALLS)
_ABORT = threading.Event()


class Throttled:
    """A backend wrapper: every live model call waits for one of the shared slots."""

    def __init__(self, inner):
        self.inner = inner

    def complete(self, **kw):
        from .llm import LLMLimitReached

        if _ABORT.is_set():
            raise LLMLimitReached("aborted: an earlier call reported an exhausted usage limit")
        with _SLOTS:
            return self.inner.complete(**kw)


def throttled_llm():
    from .llm import LLM

    llm = LLM()
    llm.backend = Throttled(llm.backend)
    return llm


# --------------------------------------------------------------------------- #
# Build: entries, pool, padded inputs, P0 drafts
# --------------------------------------------------------------------------- #


def _entry_genes(entry_dir: Path) -> list[str]:
    for name in ("gold.json",):
        p = entry_dir / name
        if p.exists():
            try:
                return sorted({g["symbol"] for g in _read(p).get("genes", []) if g.get("symbol")})
            except (json.JSONDecodeError, KeyError, TypeError):
                return []
    return []


def collect_pool(runs_root: Path, exclude_run: str = RUN) -> dict[str, dict[str, Any]]:
    """Full-text papers already fetched for entries in existing runs, with the genes of every citing entry."""
    pool: dict[str, dict[str, Any]] = {}
    for papers_json in sorted(runs_root.glob("*/*/papers.json")):
        entry_dir = papers_json.parent
        if entry_dir.parent.name == exclude_run:
            continue
        try:
            records = _read(papers_json)
        except (json.JSONDecodeError, OSError):
            continue
        genes = _entry_genes(entry_dir)
        for r in records:
            if r.get("content_level") != "fulltext":
                continue
            info = pool.setdefault(r["pmid"], {"entry_genes": [], "entries": set()})
            key = f"{entry_dir.parent.name}/{entry_dir.name}"
            if key not in info["entries"]:
                info["entries"].add(key)
                info["entry_genes"].append(genes)
    # Every entry that cites a pool paper counts, whatever level it read the paper at.
    for papers_json in sorted(runs_root.glob("*/*/papers.json")):
        entry_dir = papers_json.parent
        if entry_dir.parent.name == exclude_run:
            continue
        try:
            records = _read(papers_json)
        except (json.JSONDecodeError, OSError):
            continue
        key = f"{entry_dir.parent.name}/{entry_dir.name}"
        for r in records:
            info = pool.get(r["pmid"])
            if info is not None and key not in info["entries"]:
                info["entries"].add(key)
                info["entry_genes"].append(_entry_genes(entry_dir))
    return pool


def _names_gene(text: str, genes: list[str]) -> set[str]:
    return {g for g in genes if re.search(rf"(?<![A-Za-z0-9]){re.escape(g)}(?![A-Za-z0-9])", text)}


def build(entries: list[str] | None = None, n: int = N_ENTRIES) -> dict[str, Any]:
    from .sources.fulltext import load_papers

    root = run_dir()
    src_root = _settings().runs / SOURCE_RUN
    complete = _ablation_complete()
    rows = _evalset_rows()
    entries = entries or select_entries(rows, complete, n)
    log.info("entries: %s", ", ".join(entries))

    pool = collect_pool(_settings().runs)
    pool_pmids = sorted(pool)
    log.info("pool: %d full-text papers cited in existing runs; loading their text (cached)", len(pool_pmids))
    texts = {p.pmid: p for p in load_papers(pool_pmids, with_fulltext=True)}
    for pmid in list(pool):
        paper = texts.get(pmid)
        if paper is None or paper.content_level != "fulltext":
            pool.pop(pmid)      # no longer reads as full text: not used
            continue
        pool[pmid]["chars"] = len(paper.source_text())

    inputs: dict[str, Any] = {"targets": TARGETS, "max_added_chars": MAX_ADDED_CHARS, "seed_prefix": SEED_PREFIX,
                              "pool_size": len(pool), "source_run": SOURCE_RUN, "entries": {}}
    for mim in entries:
        src = src_root / mim
        own_records = _read(src / "papers.json")
        own = [r["pmid"] for r in own_records]
        own_papers = {p.pmid: p for p in load_papers(own, with_fulltext=True)}
        own_chars = sum(len(own_papers[p].source_text()) for p in own)
        genes = _entry_genes(src)
        for pmid, info in pool.items():
            info["mentions"] = _names_gene(texts[pmid].source_text(), genes)
        candidates, excluded = eligible_pool(pool, own, genes)
        plan = plan_padding(own_chars, candidates, {p: pool[p]["chars"] for p in candidates}, entry_rng(mim))
        rec: dict[str, Any] = {"own": own, "own_chars": own_chars, "genes": genes,
                               "own_levels": {r["pmid"]: r.get("content_level") for r in own_records},
                               "candidates": len(candidates), "excluded": excluded, "levels": {}}
        for level in LEVELS:
            added = plan.get(level, []) if level != "P0" else []
            # P0 keeps the source run's paper order: its drafts are the existing ones.
            supplied = own if level == "P0" else supplied_order(
                own, plan["P2"], added, random.Random(f"{SEED_PREFIX}:order:{mim}"))
            chars = own_chars + sum(pool[p]["chars"] for p in added)
            rec["levels"][level] = {"added": added, "supplied": supplied, "n_papers": len(supplied),
                                    "n_added": len(added), "chars": chars,
                                    "own_share_of_chars": round(own_chars / chars, 4)}
        inputs["entries"][mim] = rec

        # Entry folders: the header, gold standard and fact lists exactly as in the source run.
        for level in LEVELS:
            out = root / level / mim
            out.mkdir(parents=True, exist_ok=True)
            for name in ("seed.json", "gold.json", "gold_facts.json"):
                shutil.copyfile(src / name, out / name)
            supplied = rec["levels"][level]["supplied"]
            by_pmid = {**{p: texts[p] for p in rec["levels"][level]["added"]}, **own_papers}
            from .pipeline import _paper_record

            _write(out / "papers.json", [{**_paper_record(by_pmid[p]), "added": p not in own} for p in supplied])
        log.info("[%s] own %d papers %d chars; P1 +%d papers -> %d chars; P2 +%d papers -> %d chars", mim,
                 len(own), own_chars, rec["levels"]["P1"]["n_added"], rec["levels"]["P1"]["chars"],
                 rec["levels"]["P2"]["n_added"], rec["levels"]["P2"]["chars"])
    _write(root / "inputs.json", inputs)
    return inputs


def load_inputs() -> dict[str, Any]:
    return _read(run_dir() / "inputs.json")


def level_papers(mim: str, level: str, inputs: dict[str, Any]):
    """The supplied papers for an entry at a level, in the supplied (shuffled) order."""
    from .sources.fulltext import load_papers

    supplied = inputs["entries"][mim]["levels"][level]["supplied"]
    papers = {p.pmid: p for p in load_papers(supplied, with_fulltext=True)}
    missing = [p for p in supplied if p not in papers]
    if missing:
        raise RuntimeError(f"[{mim}] {level}: papers not loaded: {missing}")
    return [papers[p] for p in supplied]


def check_inputs(mim: str, level: str, inputs: dict[str, Any], papers) -> dict[str, Any]:
    """The header, gold standard and fact lists are byte-for-byte those of the source run; the papers
    read at the level recorded at build time."""
    src, out = _settings().runs / SOURCE_RUN / mim, run_dir() / level / mim
    same = {name: (src / name).read_bytes() == (out / name).read_bytes()
            for name in ("seed.json", "gold.json", "gold_facts.json")}
    recorded = {r["pmid"]: r["content_level"] for r in _read(out / "papers.json")}
    level_changed = [p.pmid for p in papers if recorded.get(p.pmid) != p.content_level]
    chars = sum(len(p.source_text()) for p in papers)
    return {"same_as_source": same, "content_level_changed": level_changed, "chars": chars}


# --------------------------------------------------------------------------- #
# P0: the existing drafts before repair, rebuilt from the cache
# --------------------------------------------------------------------------- #


def rebuild_p0(mim: str) -> dict[str, Any]:
    """Rebuild each strategy's source-run draft as written (before audit and repair) from cached replies,
    with a cache-only backend: any live call would be a miss and fail. The cached audit and repair are
    replayed too, and the result compared with the stored final draft, to show the rebuild is exact."""
    from .llm import LLM
    from .models import GeneratedEntry, Seed
    from .secondhand import CacheOnly
    from .sources.fulltext import load_papers
    from .strategies import after_audit, audit_papers, run_strategy
    from .verify import repair_entry, verify_entry

    src, out = _settings().runs / SOURCE_RUN / mim, run_dir() / "P0" / mim
    seed = Seed.model_validate_json((src / "seed.json").read_text(encoding="utf-8"))
    papers = load_papers([r["pmid"] for r in _read(src / "papers.json")], with_fulltext=True)
    report: dict[str, Any] = {}
    for strategy in STRATEGIES:
        llm = LLM()
        backend = CacheOnly()
        llm.backend = backend
        with tempfile.TemporaryDirectory() as tmp:
            entry = run_strategy(strategy, seed, papers, llm, Path(tmp))
            gen_usage = llm.usage.summary()
            gen_misses = backend.misses
            entry.meta["papers_by_content_level"] = _count(p.content_level for p in papers)
            before = entry.model_copy(deep=True)
            read = audit_papers(strategy, papers, Path(tmp))
            by_pmid = {p.pmid: p for p in read}
            verify_entry(entry, by_pmid, llm)
            repair_entry(entry, by_pmid, llm)
            entry.assign_paragraph_ids()
            after_audit(strategy, entry, read, Path(tmp))
        stored = GeneratedEntry.model_validate_json((src / f"entry.{strategy}.json").read_text(encoding="utf-8"))
        texts = lambda e: [p.text for p in e.all_paragraphs()]  # noqa: E731
        row = {"generation_cache_misses": gen_misses, "all_cache_misses": backend.misses,
               "replayed_final_matches_stored": texts(entry) == texts(stored),
               "before_repair_equals_final": texts(before) == texts(stored)}
        before.meta["p0_rebuild"] = row
        _write(out / f"entry.{strategy}.json", before.model_dump())
        _write(out / f"usage.{strategy}.json", {"usage": gen_usage, "wall_seconds": None,
                                                "note": "rebuilt from cache; full_* fields are the original cost"})
        report[strategy] = row
    return report


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


# --------------------------------------------------------------------------- #
# Run: P1 and P2 drafts
# --------------------------------------------------------------------------- #


def _generate(mim: str, level: str, strategy: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from .llm import LLMLimitReached
    from .models import Seed
    from .pipeline import RunConfig, build_entries

    out = run_dir() / level / mim
    entry_path, usage_path = out / f"entry.{strategy}.json", out / f"usage.{strategy}.json"
    if entry_path.exists() and usage_path.exists():
        return {"skipped": True}
    seed = Seed.model_validate_json((out / "seed.json").read_text(encoding="utf-8"))
    papers = level_papers(mim, level, inputs)
    check = check_inputs(mim, level, inputs, papers)
    cfg = RunConfig(run=RUN, strategies=(strategy,), verify=False, repair=False, evaluate=False)
    llm = throttled_llm()
    started = time.time()
    error = None
    try:
        build_entries(seed, papers, cfg, llm, out, {strategy: llm})
    except LLMLimitReached as exc:
        _ABORT.set()
        error = f"LLMLimitReached: {exc}"
    except Exception as exc:  # noqa: BLE001 - recorded; the draft is missing
        log.exception("[%s] %s %s failed", mim, level, strategy)
        error = f"{type(exc).__name__}: {exc}"[:500]
    wall = round(time.time() - started, 1)
    record = {"usage": llm.usage.summary(), "wall_seconds": wall, "started": started, "error": error,
              "safety_stops": llm.safety_stops, "input_check": check}
    if error and not entry_path.exists():
        _write(out / f"error.{strategy}.json", record)   # no usage file: the task is retried next time
        return record
    _write(usage_path, record)
    log.info("[%s] %s %s: %.0fs, %d calls (%d cached)", mim, level, strategy, wall,
             record["usage"]["total"]["calls"], record["usage"]["total"]["cached"])
    return record


def run(entries: list[str], strategies: Iterable[str] = STRATEGIES, levels: Iterable[str] = PADDED,
        workers: int = 6) -> None:
    inputs = load_inputs()
    levels = [lv for lv in PADDED if lv in set(levels)]

    def task(mim: str, strategy: str) -> None:
        # One task per entry and strategy runs the levels in order, so P2 reuses P1's cached per-paper calls.
        for level in levels:
            if _ABORT.is_set():
                return
            _generate(mim, level, strategy, inputs)

    from .sources.hpo import get_hpo

    get_hpo()   # load once, before threads race to do it
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(task, m, s) for m in entries for s in strategies]
        for f in futures:
            f.result()
    if _ABORT.is_set():
        raise SystemExit("stopped: the subscription's usage limit was reported; resume later")


# --------------------------------------------------------------------------- #
# Score
# --------------------------------------------------------------------------- #

ABOUT_SYSTEM = """\
You are checking citations in a draft encyclopedia entry about one genetic disorder. Some papers \
supplied to the writer were unrelated to the disorder; each paragraph below cites at least one of \
them (marked UNRELATED with its title). For each numbered paragraph, say whether the paragraph \
attributes to an UNRELATED paper a statement about the entry's disorder: its clinical features, \
patients, genetics, variants, inheritance, mechanism or management. A paragraph that cites an \
UNRELATED paper only for a statement about some other condition or gene, clearly presented as \
such, is not one. Give every paragraph number exactly once.\
"""


class XAbout(BaseModel):
    n: int
    about_disorder: bool
    reason: str = Field(description="One short sentence")


class XAbouts(BaseModel):
    verdicts: list[XAbout]


def _about_prompt(title: str, paragraphs: list[dict[str, Any]], titles: dict[str, str], added: set[str]) -> str:
    blocks = []
    for n, p in enumerate(paragraphs, 1):
        cites = "; ".join(f"PMID {x}" + (f" (UNRELATED: {titles.get(x, '')})" if x in added else "")
                          for x in p.get("pmids", []))
        blocks.append(f"{n}. [cites {cites}]\n{p['text']}")
    return f"Entry: {title}\n\n" + "\n\n".join(blocks)


def judge_added(entry: dict[str, Any], title: str, titles: dict[str, str], added: set[str], llm) -> dict[str, Any]:
    paras = []
    if entry.get("intro"):
        paras.append(entry["intro"])
    paras += [p for s in entry.get("sections", []) for p in s.get("paragraphs", [])]
    paras += [p for v in entry.get("allelic_variants", []) for p in v.get("paragraphs", [])]
    citing = [p for p in paras if (p.get("text") or "").strip() and added & set(p.get("pmids", []))]
    if not citing:
        return {"n_judged": 0, "n_about_disorder": 0, "verdicts": []}
    reply = llm.call("judge", ABOUT_SYSTEM, _about_prompt(title, citing, titles, added), XAbouts)
    by_n = {v.n: v for v in reply.verdicts}
    verdicts = [{"pmids": [x for x in p.get("pmids", []) if x in added],
                 "about_disorder": (by_n[n].about_disorder if n in by_n else None),
                 "reason": by_n[n].reason if n in by_n else ""} for n, p in enumerate(citing, 1)]
    return {"n_judged": len(citing), "n_about_disorder": sum(1 for v in verdicts if v["about_disorder"]),
            "n_unjudged": sum(1 for v in verdicts if v["about_disorder"] is None), "verdicts": verdicts}


def _entry_hash(path: Path) -> str:
    from .cache import stable_hash

    return stable_hash(path.read_text(encoding="utf-8"))[:16]


def score_one(mim: str, level: str, strategy: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
    from .facts import FactStore, eval_gold_text_frozen, frozen_facts
    from .models import GeneratedEntry, GoldEntry

    out = run_dir() / level / mim
    entry_path, eval_path = out / f"entry.{strategy}.json", out / f"eval.{strategy}.json"
    if not entry_path.exists():
        return None
    digest = _entry_hash(entry_path)
    if eval_path.exists() and _read(eval_path).get("entry_hash") == digest:
        return {"skipped": True}
    raw = _read(entry_path)
    meta = raw.get("meta") or {}
    rec = inputs["entries"][mim]
    added = set(rec["levels"][level]["added"])
    llm = throttled_llm()
    evaluation: dict[str, Any] = {"mim": mim, "level": level, "strategy": strategy, "entry_hash": digest}
    if meta.get("stopped"):
        evaluation["stopped"] = meta["stopped"]
    else:
        entry = GeneratedEntry.model_validate(raw)
        gold = GoldEntry.model_validate(_read(out / "gold.json"))
        levels = {r["pmid"]: r.get("content_level", "not_retrieved") for r in _read(out / "papers.json")}
        records = frozen_facts(gold.scoped_paragraphs, llm, FactStore(), split_missing=False) \
            if gold.scoped_paragraphs else []
        if any(r is None for r in records):
            raise RuntimeError(f"[{mim}] a frozen fact list is missing from the store")
        evaluation["gold_text_frozen"] = eval_gold_text_frozen(entry, gold, levels, llm, records=records)
        evaluation["added_citations"] = added_citations(raw, added)
        if added:
            titles = {r["pmid"]: r.get("title", "") for r in _read(out / "papers.json")}
            evaluation["added_about_disorder"] = judge_added(raw, gold.title, titles, added, llm)
        if level == "P0":
            evaluation["changed_vs_final"] = _changed_vs_final(mim, strategy, entry, gold)
    evaluation["score_usage"] = llm.usage.summary()["total"]
    _write(eval_path, evaluation)
    return evaluation


def _changed_vs_final(mim: str, strategy: str, before, gold) -> dict[str, Any]:
    """Gold paragraphs whose cited draft text differs between the before-repair draft and the scored final."""
    from .evaluate import _draft_text_for
    from .models import GeneratedEntry

    final = GeneratedEntry.model_validate(_read(_settings().runs / SOURCE_RUN / mim / f"entry.{strategy}.json"))
    changed = [_draft_text_for(before, p.pmids) != _draft_text_for(final, p.pmids) for p in gold.scoped_paragraphs]
    return {"paragraphs": len(changed), "changed": sum(changed)}


def score(entries: list[str] | None = None, levels: Iterable[str] = LEVELS, workers: int = 4) -> None:
    inputs = load_inputs()
    entries = entries or list(inputs["entries"])
    tasks = [(m, lv, s) for m in entries for lv in levels for s in STRATEGIES]

    def one(t):
        try:
            return score_one(*t, inputs)
        except Exception as exc:  # noqa: BLE001
            log.exception("[%s] scoring %s %s failed", *t)
            return {"error": str(exc)}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, tasks))


# --------------------------------------------------------------------------- #
# Summarise
# --------------------------------------------------------------------------- #


def _usage_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = ("calls", "cached", "list_price_usd", "full_list_price_usd", "seconds", "full_seconds",
            "input_tokens", "output_tokens", "full_input_tokens", "full_output_tokens", "turns")
    cell = {k: round(sum((r or {}).get(k, 0) for r in rows), 4) for k in keys}
    cell["new_calls"] = int(cell["calls"] - cell["cached"])
    return cell


def summarise() -> dict[str, Any]:
    inputs = load_inputs()
    entries = list(inputs["entries"])
    root = run_dir()

    status: dict[str, dict[str, dict[str, str]]] = {lv: {s: {} for s in STRATEGIES} for lv in LEVELS}
    cov: dict[str, dict[str, dict[str, float | None]]] = {lv: {s: {} for s in STRATEGIES} for lv in LEVELS}
    reasons: dict[str, Any] = {}
    gen_usage: dict[str, dict[str, list]] = {lv: {s: [] for s in STRATEGIES} for lv in LEVELS}
    score_usage: dict[str, dict[str, list]] = {lv: {s: [] for s in STRATEGIES} for lv in LEVELS}
    wall: dict[str, dict[str, list]] = {lv: {s: [] for s in STRATEGIES} for lv in LEVELS}
    citations: dict[str, dict[str, list]] = {lv: {s: [] for s in STRATEGIES} for lv in PADDED}
    caps: dict[str, dict[str, list]] = {lv: {s: [] for s in STRATEGIES} for lv in LEVELS}
    p0_rebuild: dict[str, Any] = {}
    stops: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for mim in entries:
        rec = inputs["entries"][mim]
        own = set(rec["own"])
        for level in LEVELS:
            out = root / level / mim
            added = set(rec["levels"][level]["added"])
            for s in STRATEGIES:
                entry_path, eval_path = out / f"entry.{s}.json", out / f"eval.{s}.json"
                entry = _read(entry_path) if entry_path.exists() else None
                ev = _read(eval_path) if eval_path.exists() else None
                meta = (entry or {}).get("meta") or {}
                if entry is None and (out / f"error.{s}.json").exists():
                    errors.append({"mim": mim, "level": level, "strategy": s,
                                   "error": _read(out / f"error.{s}.json").get("error")})
                cls = classify(ev, meta if entry is not None else None)
                status[level][s][mim] = cls
                if meta.get("stopped"):
                    stops.append({"mim": mim, "level": level, "strategy": s, "reason": str(meta["stopped"])[:200]})
                if cls == "incomplete":
                    reasons.setdefault(level, {}).setdefault(s, {})[mim] = next(
                        v["papers_failed"] for v in meta.values()
                        if isinstance(v, dict) and isinstance(v.get("papers_failed"), list) and v["papers_failed"])
                if ev and not ev.get("stopped"):
                    cov[level][s][mim] = coverage(ev.get("gold_text_frozen"))
                    score_usage[level][s].append(ev.get("score_usage"))
                    if level in PADDED and ev.get("added_citations"):
                        citations[level][s].append({"mim": mim, **ev["added_citations"],
                                                    "n_about_disorder": (ev.get("added_about_disorder") or {})
                                                    .get("n_about_disorder", 0)})
                    if level == "P0":
                        p0_rebuild.setdefault(s, {})[mim] = {**meta.get("p0_rebuild", {}),
                                                             "changed_paragraphs": ev.get("changed_vs_final")}
                usage_path = out / f"usage.{s}.json"
                if usage_path.exists():
                    u = _read(usage_path)
                    gen_usage[level][s].append(u["usage"]["total"])
                    if u.get("wall_seconds") is not None:
                        wall[level][s].append(u["wall_seconds"])
                if entry is not None:
                    caps[level][s].append({"mim": mim, **_caps(s, meta, own, added, rec["levels"][level])})

    sets = complete_sets(status, entries)
    result: dict[str, Any] = {
        "experiment": "A2 controlled padding of the input (docs/experiments-round2.md)",
        "entries": entries,
        "inputs": {m: {"own_papers": len(r["own"]), "genes_withheld": r["genes"], "candidates": r["candidates"],
                       "excluded": r["excluded"],
                       "levels": {lv: {k: r["levels"][lv][k] for k in ("n_papers", "n_added", "chars",
                                                                       "own_share_of_chars")}
                                  for lv in LEVELS}}
                   for m, r in inputs["entries"].items()},
        "input_summary": {lv: _input_summary([inputs["entries"][m]["levels"][lv] for m in entries]) for lv in LEVELS},
        "completion": {lv: {s: _count(status[lv][s].values()) | {"not_complete": sorted(
            m for m, c in status[lv][s].items() if c != "complete")} for s in STRATEGIES} for lv in LEVELS},
        "incomplete_papers_failed": reasons,
        "stops": stops,
        "errors": errors,
        "complete_sets": sets,
    }

    def mean(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    analyses: dict[str, Any] = {}
    for name, members in (("all_levels", sets["all"]),):
        a: dict[str, Any] = {"n_entries": len(members), "entries": members, "coverage": {}, "change_from_P0": {},
                             "difference_from_direct": {}}
        for lv in LEVELS:
            a["coverage"][lv] = {s: mean(cov[lv][s].get(m) for m in members) for s in STRATEGIES}
        for s in STRATEGIES:
            a["change_from_P0"][s] = {lv: paired([(cov[lv][s][m], cov["P0"][s][m]) for m in members])
                                      for lv in PADDED}
        for lv in LEVELS:
            a["difference_from_direct"][lv] = {s: paired([(cov[lv][s][m], cov[lv]["direct"][m]) for m in members])
                                               for s in STRATEGIES if s != "direct"}
        # Interaction: does a strategy's change from P0 differ from direct reading's change?
        a["change_minus_direct_change"] = {
            lv: {s: paired([(cov[lv][s][m] - cov["P0"][s][m], cov[lv]["direct"][m] - cov["P0"]["direct"][m])
                            for m in members]) for s in STRATEGIES if s != "direct"} for lv in PADDED}
        a["ranking"] = {lv: sorted(STRATEGIES, key=lambda s: -(a["coverage"][lv][s] or -1)) for lv in LEVELS}
        analyses[name] = a
    per_level = {}
    for lv in LEVELS:
        members = sets[lv]
        per_level[lv] = {"n_entries": len(members), "entries": members,
                         "coverage": {s: mean(cov[lv][s].get(m) for m in members) for s in STRATEGIES},
                         "difference_from_direct": {s: paired([(cov[lv][s][m], cov[lv]["direct"][m])
                                                               for m in members]) for s in STRATEGIES
                                                    if s != "direct"}}
    analyses["each_level_own_complete_set"] = per_level
    # Each strategy's change from P0 on the entries it completed at both levels (not symmetric).
    analyses["change_from_P0_per_strategy_completed"] = {
        s: {lv: paired([(cov[lv][s][m], cov["P0"][s][m]) for m in entries
                        if status[lv][s][m] == "complete" and status["P0"][s][m] == "complete"
                        and cov[lv][s].get(m) is not None and cov["P0"][s].get(m) is not None])
            for lv in PADDED} for s in STRATEGIES}
    result["analysis"] = analyses
    result["per_entry_coverage"] = {lv: {s: {m: (round(v, 4) if v is not None else None)
                                             for m, v in cov[lv][s].items()} for s in STRATEGIES} for lv in LEVELS}

    result["added_paper_citations"] = {lv: {s: _citation_summary(citations[lv][s]) for s in STRATEGIES}
                                       for lv in PADDED}
    result["caps"] = {lv: {s: _caps_summary(s, caps[lv][s]) for s in STRATEGIES} for lv in LEVELS}
    result["p0_rebuild"] = p0_rebuild
    result["cost"] = {lv: {s: {"generation": _usage_cell(gen_usage[lv][s]), "scoring": _usage_cell(score_usage[lv][s]),
                               "n_entries": len(gen_usage[lv][s]),
                               "wall_seconds_total": round(sum(wall[lv][s]), 1),
                               "wall_seconds_median_per_entry": (round(statistics.median(wall[lv][s]), 1)
                                                                 if wall[lv][s] else None)}
                           for s in STRATEGIES} for lv in LEVELS}
    totals = [result["cost"][lv][s][k]["new_calls"] for lv in LEVELS for s in STRATEGIES
              for k in ("generation", "scoring")]
    result["new_calls_total"] = sum(totals)
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "padding.json", result)
    (out / "padding.md").write_text(markdown(result), encoding="utf-8")
    return result


def _input_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    chars = [r["chars"] for r in rows]
    n = [r["n_papers"] for r in rows]
    return {"chars_min": min(chars), "chars_median": int(statistics.median(chars)), "chars_max": max(chars),
            "papers_min": min(n), "papers_median": statistics.median(n), "papers_max": max(n),
            "added_median": statistics.median([r["n_added"] for r in rows]),
            "own_share_median": round(statistics.median([r["own_share_of_chars"] for r in rows]), 4)}


def _caps(strategy: str, meta: dict[str, Any], own: set[str], added: set[str], level: dict[str, Any]) -> dict[str, Any]:
    """What the caps built into a strategy did to one draft's input."""
    from .synthesize import DIRECT_TOTAL_CHARS

    row: dict[str, Any] = {}
    if strategy == "direct":
        b = meta.get("direct_batching") or {}
        trunc = meta.get("truncated_papers") or []
        row.update(batched=bool(b.get("used")), prompts=len(b.get("batches", [])) or 1,
                   merge_call=bool(b.get("used")) and len(b.get("batches", [])) > 1,
                   per_paper_cap=(None if b.get("used") else max(20_000, DIRECT_TOTAL_CHARS // max(1, level["n_papers"]))),
                   truncated_own=sorted(set(trunc) & own), truncated_added=sorted(set(trunc) & added),
                   pmids_lost_in_merge=(b.get("merge") or {}).get("pmids_lost_in_merge", []))
    elif strategy == "agent":
        a = meta.get("agent") or {}
        not_read = a.get("papers_not_read") or []
        row.update(own_not_read=sorted(set(not_read) & own), added_not_read=len(set(not_read) & added),
                   added_read=len(set(a.get("papers_read") or []) & added))
    elif strategy in ("kg", "cohort"):
        key = "extraction" if strategy == "kg" else "cohort"
        info = meta.get(key) or {}
        row.update(papers_failed=info.get("papers_failed", []),
                   relevance=info.get("papers_by_relevance") or info.get("relevance"))
    return row


def _caps_summary(strategy: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    if strategy == "direct":
        return {"drafts": len(rows), "batched": sum(r["batched"] for r in rows),
                "prompts": _count(str(r["prompts"]) for r in rows),
                "per_paper_cap_range": [min((r["per_paper_cap"] for r in rows if r["per_paper_cap"]), default=None),
                                        max((r["per_paper_cap"] for r in rows if r["per_paper_cap"]), default=None)],
                "drafts_with_own_paper_truncated": sorted(r["mim"] for r in rows if r["truncated_own"]),
                "own_papers_truncated": sum(len(r["truncated_own"]) for r in rows),
                "added_papers_truncated": sum(len(r["truncated_added"]) for r in rows),
                "drafts_losing_a_pmid_in_merge": sorted(r["mim"] for r in rows if r["pmids_lost_in_merge"])}
    if strategy == "agent":
        return {"drafts": len(rows), "own_papers_not_opened": sum(len(r["own_not_read"]) for r in rows),
                "drafts_with_own_paper_not_opened": sorted(r["mim"] for r in rows if r["own_not_read"]),
                "added_papers_opened": sum(r["added_read"] for r in rows),
                "added_papers_not_opened": sum(r["added_not_read"] for r in rows)}
    return {"drafts": len(rows), "papers_failed": sum(len(r["papers_failed"] or []) for r in rows),
            "relevance": _sum_counts(r["relevance"] for r in rows)}


def _sum_counts(dicts) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in dicts:
        for k, v in (d or {}).items():
            if isinstance(v, int):
                out[k] = out.get(k, 0) + v
    return out


def _citation_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    shares = [r["share_citing_added"] for r in rows if r["share_citing_added"] is not None]
    return {"drafts": len(rows),
            "mean_share_of_paragraphs_citing_added": round(sum(shares) / len(shares), 4) if shares else None,
            "paragraphs": sum(r["n_paragraphs"] for r in rows),
            "paragraphs_citing_added": sum(r["n_citing_added"] for r in rows),
            "drafts_citing_added": sorted(r["mim"] for r in rows if r["n_citing_added"]),
            "drafts_with_added_in_relationships_or_synopsis": sorted(
                r["mim"] for r in rows if r["added_in_relationships"] or r["added_in_synopsis"]),
            "paragraphs_attributing_disorder_statement_to_added": sum(r["n_about_disorder"] for r in rows),
            "drafts_attributing_disorder_statement_to_added": sorted(r["mim"] for r in rows if r["n_about_disorder"])}


# --------------------------------------------------------------------------- #
# Markdown (counts, percentages and entry numbers only)
# --------------------------------------------------------------------------- #

LABELS = {"direct": "Direct reading", "agent": "Agentic curator", "kg": "Evidence graph", "cohort": "Case table first"}


def _pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def _pp(row) -> str:
    if not row:
        return "–"
    ci = row.get("ci95")
    ci_s = f" [{100 * ci[0]:+.1f}, {100 * ci[1]:+.1f}]" if ci else " [n<5]"
    return (f"{100 * row['difference']:+.1f}{ci_s}; {row['better']}/{row['worse']}/{row['ties']}"
            + (f"; p={row['sign_test_p']}" if row.get("sign_test_p") is not None else ""))


def markdown(r: dict[str, Any]) -> str:
    a = r["analysis"]["all_levels"]
    lines = [
        "# A2. Controlled padding of the input",
        "",
        "Design: `docs/experiments-round2.md`, section A2. Generated by `python -m aiomim.padding summarise`. "
        "Coverage is the share of the entry's own frozen OMIM facts conveyed (present + half of partial, over "
        "judged facts), credited to draft paragraphs citing the paper. No audit and no repair at any level.",
        "",
        f"Entries ({len(r['entries'])}): {', '.join(r['entries'])}.",
        "",
        "## Input sizes",
        "",
        "| Level | Characters (min / median / max) | Papers (min / median / max) | Added papers (median) | "
        "Own text share (median) |",
        "|---|---|---|---|---|",
    ]
    for lv in LEVELS:
        s = r["input_summary"][lv]
        lines.append(f"| {lv} | {s['chars_min']:,} / {s['chars_median']:,} / {s['chars_max']:,} | "
                     f"{s['papers_min']} / {s['papers_median']} / {s['papers_max']} | {s['added_median']} | "
                     f"{_pct(s['own_share_median'])} |")
    lines += ["", "Per entry (papers / characters):", "",
              "| Entry | Own papers | P0 chars | P1 papers | P1 chars | P2 papers | P2 chars |", "|---|---|---|---|---|---|---|"]
    for m, e in r["inputs"].items():
        L = e["levels"]
        lines.append(f"| {m} | {e['own_papers']} | {L['P0']['chars']:,} | {L['P1']['n_papers']} | {L['P1']['chars']:,} | "
                     f"{L['P2']['n_papers']} | {L['P2']['chars']:,} |")
    lines += ["", "## Completion", "",
              "| Level | " + " | ".join(LABELS[s] for s in STRATEGIES) + " |",
              "|---|" + "---|" * len(STRATEGIES)]
    for lv in LEVELS:
        cells = []
        for s in STRATEGIES:
            c = r["completion"][lv][s]
            cells.append(f"{c.get('complete', 0)} / {c.get('incomplete', 0)} / {c.get('no_draft', 0)}"
                         + (f" ({', '.join(c['not_complete'])})" if c["not_complete"] else ""))
        lines.append(f"| {lv} | " + " | ".join(cells) + " |")
    lines += ["", "Complete / incomplete / no draft. "
              f"Entries every strategy completed at every level: {len(r['complete_sets']['all'])} "
              f"({', '.join(r['complete_sets']['all'])}).", ""]
    if r["stops"]:
        lines += ["Safety-filter stops: " + "; ".join(f"{x['mim']} {x['level']} {x['strategy']}" for x in r["stops"]), ""]
    if r["errors"]:
        lines += ["Errors (no draft): " + "; ".join(f"{x['mim']} {x['level']} {x['strategy']}: {x['error'][:80]}"
                                                    for x in r["errors"]), ""]
    lines += [f"## Coverage on the {a['n_entries']} entries every strategy completed at every level", "",
              "| Strategy | P0 | P1 | P2 | P1 − P0 [95% CI]; better/worse/tied | P2 − P0 [95% CI]; better/worse/tied |",
              "|---|---|---|---|---|---|"]
    for s in STRATEGIES:
        lines.append(f"| {LABELS[s]} | {_pct(a['coverage']['P0'][s])} | {_pct(a['coverage']['P1'][s])} | "
                     f"{_pct(a['coverage']['P2'][s])} | {_pp(a['change_from_P0'][s]['P1'])} | "
                     f"{_pp(a['change_from_P0'][s]['P2'])} |")
    lines += ["", "Differences in percentage points; bootstrap interval over entries (10,000 resamples); "
              f"with {a['n_entries']} entries the intervals are indicative only.", "",
              "### Difference from direct reading at each level", "",
              "| Strategy | P0 | P1 | P2 |", "|---|---|---|---|"]
    for s in STRATEGIES:
        if s == "direct":
            continue
        lines.append(f"| {LABELS[s]} | " + " | ".join(_pp(a["difference_from_direct"][lv][s]) for lv in LEVELS) + " |")
    lines += ["", "### Strategy-by-size interaction: change from P0 minus direct reading's change from P0", "",
              "| Strategy | P1 | P2 |", "|---|---|---|"]
    for s in STRATEGIES:
        if s == "direct":
            continue
        lines.append(f"| {LABELS[s]} | " + " | ".join(_pp(a["change_minus_direct_change"][lv][s]) for lv in PADDED) + " |")
    lines += ["", "Ranking by mean coverage: " + "; ".join(
        f"{lv}: " + " > ".join(LABELS[s] for s in a["ranking"][lv]) for lv in LEVELS), ""]
    lines += ["### Each level on its own complete set", "", "| Level | Entries | " +
              " | ".join(LABELS[s] for s in STRATEGIES) + " |", "|---|---|" + "---|" * len(STRATEGIES)]
    for lv in LEVELS:
        p = r["analysis"]["each_level_own_complete_set"][lv]
        lines.append(f"| {lv} | {p['n_entries']} | " + " | ".join(_pct(p["coverage"][s]) for s in STRATEGIES) + " |")
    lines += ["", "## Citations of added papers", "",
              "| Level | Strategy | Mean share of paragraphs citing an added paper | Paragraphs citing added / all | "
              "Paragraphs attributing a statement about the disorder to an added paper | Drafts with one |",
              "|---|---|---|---|---|---|"]
    for lv in PADDED:
        for s in STRATEGIES:
            c = r["added_paper_citations"][lv][s]
            if not c:
                continue
            lines.append(f"| {lv} | {LABELS[s]} | {_pct(c['mean_share_of_paragraphs_citing_added'])} | "
                         f"{c['paragraphs_citing_added']} / {c['paragraphs']} | "
                         f"{c['paragraphs_attributing_disorder_statement_to_added']} | "
                         f"{', '.join(c['drafts_attributing_disorder_statement_to_added']) or 'none'} |")
    lines += ["", "## Caps that applied", "", "```", json.dumps(r["caps"], indent=1), "```", "",
              "## Calls, cost and time", "",
              "| Level | Strategy | Drafts | Generation calls (new) | Generation list price, as if fresh | "
              "Scoring calls (new) | Wall-clock per entry (median, s) |", "|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        for s in STRATEGIES:
            c = r["cost"][lv][s]
            g, sc = c["generation"], c["scoring"]
            lines.append(f"| {lv} | {LABELS[s]} | {c['n_entries']} | {int(g['calls'])} ({g['new_calls']}) | "
                         f"${g['full_list_price_usd']:.2f} | {int(sc['calls'])} ({sc['new_calls']}) | "
                         f"{c['wall_seconds_median_per_entry'] if c['wall_seconds_median_per_entry'] is not None else '–'} |")
    lines += ["", f"New model calls in all: {r['new_calls_total']}.", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m aiomim.padding", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="choose entries and padding; write inputs and the P0 drafts")
    b.add_argument("--entries", default=None)
    b.add_argument("-n", type=int, default=N_ENTRIES)
    b.add_argument("--no-p0", action="store_true")
    r = sub.add_parser("run", help="generate P1/P2 drafts")
    r.add_argument("--entries", default=None)
    r.add_argument("--strategies", default=",".join(STRATEGIES))
    r.add_argument("--levels", default=",".join(PADDED))
    r.add_argument("--workers", type=int, default=6)
    s = sub.add_parser("score", help="frozen scoring of every draft")
    s.add_argument("--entries", default=None)
    s.add_argument("--levels", default=",".join(LEVELS))
    s.add_argument("--workers", type=int, default=4)
    sub.add_parser("summarise", help="write results/padding/")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()] if v else None  # noqa: E731

    if args.cmd == "build":
        inputs = build(split(args.entries), args.n)
        if not args.no_p0:
            for mim in inputs["entries"]:
                rep = rebuild_p0(mim)
                log.info("[%s] P0 rebuilt: %s", mim, rep)
    elif args.cmd == "run":
        entries = split(args.entries) or list(load_inputs()["entries"])
        run(entries, split(args.strategies), split(args.levels), args.workers)
    elif args.cmd == "score":
        score(split(args.entries), split(args.levels), args.workers)
    elif args.cmd == "summarise":
        result = summarise()
        print(markdown(result))


if __name__ == "__main__":
    main()
