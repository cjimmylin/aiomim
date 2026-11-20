"""The private input bundle: built here from runs/ and data/, unpacked on the owner's machine.

Layout (paths inside the archive, under `bundle/`):

    MANIFEST.json                              ids, entry lists, counts, code fingerprint, sha256 of every file
    entries/<mim>/seed.json                    what every strategy was told (gene withheld)
    entries/<mim>/gold.json                    OMIM-derived gold standard              (OMIM wording)
    entries/<mim>/papers.json                  the run's paper records (content level, size)
    entries/<mim>/papers.full.json             the papers as the strategies received them: `Paper.model_dump()`
                                               in retrieval order (title, abstract, full text), so that the
                                               project's rendering rebuilds the original prompts byte for byte
    entries/<mim>/hidden.json                  the papers read in full that the hidden-full-text arms hid
    drafts/main/<mim>/entry.<s>.json           the main run's drafts of the six strategies
    drafts/secondhand/<mim>/entry.<arm>.json   abstract, secondhand, and the full-text draft before repair
                                               (rebuilt from the cached writer and audit replies, as the
                                               original before-repair scoring did; checked exact)
    claude/marks/main/<mim>/<s>.json           Claude's fixed-fact marks (fact id, status; no notes)
    claude/marks/judge_j1|judge_j2/<mim>/<s>.json  Claude's judge replicates where they exist
    claude/marks/secondhand/<mim>/<arm>.json   Claude's marks of the hidden-full-text arms
    claude/availability/<mim>.json             Claude's availability verdicts (fact id, verdict; no quotes)
    claude/conveyed/<mim>.json                 Claude's conveyed-fact re-check (fact id, classes)
    factstore/<k[:2]>/<k>.json                 the fixed fact lists                    (OMIM wording)
    factstore/avail/<k[:2]>/<k>.<src>.json     Claude's stored availability judgements (read by A2C)
    ontologies/hp.obo, phenotype.hpoa          the HPO files the runs used
    http/<k[:2]>/<k>.txt                       every HGNC response the runs cached
    hgnc/hgnc_table.json                       HGNC's complete set (symbol, ids, location, aliases, previous)
    verify/prompt_keys.json                    keys of the prompts the replay verification built
    verify/report.json                         the replay verification's counts

The archive is delivered out of band and never committed.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import shutil
import subprocess
import tarfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import CLAUDE_MODEL, Study, StudyPaths, write_json
from .errors import StudyError

log = logging.getLogger(__name__)

STRATEGIES_A1 = ("direct", "agent", "kg", "cohort", "recall", "closedbook")
SECONDHAND_RUN = "secondhand_check_omim100"
MAIN_RUN = "omim100"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _marks_only(score: dict[str, Any] | None) -> dict[str, Any] | None:
    """A gold_text_frozen block reduced to fact ids and statuses (the notes paraphrase OMIM's text)."""
    if not score:
        return None
    keep = ("n_paragraphs", "n_facts", "n_judged", "unjudged", "present", "partial", "absent", "contradicted",
            "coverage", "strict_coverage", "replicate")
    return {**{k: score.get(k) for k in keep if k in score},
            "paragraphs": [{"key": p.get("key"), "pmids": p.get("pmids"), "content_level": p.get("content_level"),
                            "error": bool(p.get("error")),
                            "facts": [{"id": f["id"], "status": f["status"]} for f in p.get("facts") or []]}
                           for p in score.get("paragraphs") or []]}


def code_fingerprint() -> dict[str, str]:
    """Hashes of every prompt constant and reply schema the study's calls use, and of the efforts."""
    from .. import config as aiomim_config
    from ..cache import stable_hash
    from ..extract import XChoices, XExtraction
    from ..facts import RETRY_NOTE, SPLIT_VERSION, XMarks
    from ..gaps import XGapVerdicts
    from ..llm import schema_for
    from ..synthesize import DEntry, XEntry
    from .backend import system_labels

    out = {label: stable_hash(system)[:16] for system, label in system_labels().items()}
    for model in (XMarks, XGapVerdicts, DEntry, XEntry, XExtraction, XChoices):
        out[f"schema:{model.__name__}"] = stable_hash(schema_for(model))[:16]
    out["retry_note"] = stable_hash(RETRY_NOTE)[:16]
    out["split_version"] = SPLIT_VERSION
    out["efforts"] = stable_hash(aiomim_config.DEFAULT_EFFORT)[:16]
    return dict(sorted(out.items()))


def study_entries(study: Study) -> dict[str, list[str]]:
    t = study.tasks()
    return {k: list((t.get(k) or {}).get("entries", [])) for k in ("A1", "A2", "A3", "B1", "B2")}


def build(repo: Path, study: Study, out_tar: Path, *, hgnc_complete: Path, work: Path, verify: bool = True,
          jobs: int = 8) -> dict[str, Any]:
    """Build the bundle from this checkout's runs/ and data/ (read only) and pack it."""
    from .offline import network_blocked

    repo = Path(repo).resolve()
    runs, data = repo / "runs", repo / "data"
    stage = Path(work) / "bundle"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    lists = study_entries(study)
    need_papers = set(lists["A2"]) | set(lists["B1"]) | set(lists["B2"])
    hidden_entries = set(lists["A3"]) | set(lists["B2"])
    all_entries = sorted(set().union(*lists.values()))
    report: dict[str, Any] = {"entries": len(all_entries), "problems": []}
    with network_blocked() as attempts, _cache_only_sources(data) as http:
        before = len(attempts)
        _copy_entries(repo, runs, stage, all_entries, need_papers, hidden_entries, report)
        _copy_fact_lists(runs, data, stage, all_entries, set(lists["A2"]), report)
        _copy_drafts_and_marks(runs, stage, lists, report)
        _rebuild_before_repair(runs, stage, lists["A3"], report)
        _copy_ontology_and_hgnc(data, stage, hgnc_complete, report)
        report["network_attempts_during_build"] = len(attempts) - before
        # Lookups the original runs answered from the network without caching the answer (Europe PMC and
        # BioC say "no open-access text" with a 404, which is not cached): answered "not found" here too,
        # which is what those runs got; the papers' text is checked against the runs' records above.
        report["uncached_lookups_answered_not_found"] = len(http.misses)
    if report["problems"]:
        raise StudyError("bundle build found problems:\n" + "\n".join(report["problems"][:50]))
    manifest = _manifest(repo, stage, study, lists, report)
    if verify:
        report["verification"] = verify_replay(stage, study, data / "cache" / "llm", Path(work) / "verify",
                                               jobs=jobs)
        manifest = _manifest(repo, stage, study, lists, report)
    _pack(stage, out_tar)
    return {"manifest": {k: v for k, v in manifest.items() if k != "files"}, "tar": str(out_tar),
            "size_bytes": out_tar.stat().st_size, "sha256": _sha256(out_tar)}


# --------------------------------------------------------------------------- #
# Pieces
# --------------------------------------------------------------------------- #


@contextlib.contextmanager
def _cache_only_sources(data: Path):
    """The project's data sources reading this checkout's HTTP cache only, writing nothing into data/.

    A lookup the cache does not hold fails as an HTTP error (the project's sources treat that
    as "not available"), never as a network call; the full-text miss cache is read, not written.
    """
    from .. import http as aiomim_http
    from ..cache import DiskCache
    from ..http import Http, HttpError
    from ..sources import fulltext as ft

    class CacheOnlyHttp(Http):
        def __init__(self):
            super().__init__(cache_dir=data / "cache" / "http")
            self.misses: list[str] = []

        def get_text(self, url, params=None, *, headers=None, cache=True, max_age_s=None, max_tries=None):
            hit = self.cache.get_text(self.cache_key(url, params))
            if hit is not None:
                return hit
            self.misses.append(url)
            raise HttpError("not in this checkout's cache (the bundle build is offline)", url=url)

        def download(self, url, dest, max_age_s=None):
            if Path(dest).exists():
                return Path(dest)
            raise HttpError("offline", url=url)

    class ReadOnlyMisses(DiskCache):
        def put_text(self, key, text):
            return None

    saved = (aiomim_http._HTTP, ft._miss_cache)
    http = CacheOnlyHttp()
    aiomim_http._HTTP = http
    ft._miss_cache = lambda: ReadOnlyMisses(data / "cache" / "http" / "fulltext_miss", suffix=".json")
    try:
        yield http
    finally:
        aiomim_http._HTTP, ft._miss_cache = saved


def _copy_entries(repo: Path, runs: Path, stage: Path, mims: list[str], need_papers: set[str],
                  hidden_entries: set[str], report: dict[str, Any]) -> None:
    """seed, gold, paper records; the papers' text through the project's own loader (from the HTTP cache)."""
    from ..sources.fulltext import load_papers

    n_papers = 0
    for mim in mims:
        src, dst = runs / MAIN_RUN / mim, stage / "entries" / mim
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("seed.json", "gold.json", "papers.json"):
            shutil.copyfile(src / name, dst / name)
        records = _read(src / "papers.json")
        if mim in need_papers or mim in hidden_entries:
            papers = load_papers([r["pmid"] for r in records], with_fulltext=True)
            same = ([p.pmid for p in papers] == [r["pmid"] for r in records]
                    and [p.content_level for p in papers] == [r.get("content_level") for r in records]
                    and [len(p.source_text()) for p in papers] == [r.get("n_chars") for r in records])
            if not same:
                report["problems"].append(f"{mim}: the papers loaded from the cache differ from the run's records")
            write_json(dst / "papers.full.json", [p.model_dump() for p in papers], indent=None)
            n_papers += len(papers)
            if mim in hidden_entries:
                result = _read(runs / SECONDHAND_RUN / mim / "secondhand_check" / "result.json")
                hidden = sorted(result["hidden_papers"])
                if hidden != sorted(p.pmid for p in papers if p.content_level == "fulltext"):
                    report["problems"].append(f"{mim}: hidden papers differ from the papers read in full")
                write_json(dst / "hidden.json", {"hidden_papers": hidden})
    report["papers"] = n_papers


def _copy_fact_lists(runs: Path, data: Path, stage: Path, mims: list[str], a2: set[str],
                     report: dict[str, Any]) -> None:
    from ..facts import paragraph_key
    from ..models import GoldEntry

    store = data / "gold_facts"
    n_lists = n_avail = 0
    for mim in mims:
        gold = GoldEntry.model_validate(_read(runs / MAIN_RUN / mim / "gold.json"))
        for para in gold.scoped_paragraphs:
            k = paragraph_key(para.text)
            src = store / k[:2] / f"{k}.json"
            if not src.exists():
                report["problems"].append(f"{mim}: fixed fact list {k[:12]} missing from data/gold_facts")
                continue
            dst = stage / "factstore" / k[:2] / f"{k}.json"
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                n_lists += 1
            if mim in a2:
                for av in (store / "avail" / k[:2]).glob(f"{k}.*.json"):
                    if av.name.count(".") != 2:     # <key>.<src16>.json only: no replicate salt
                        continue
                    d = stage / "factstore" / "avail" / k[:2] / av.name
                    if not d.exists():
                        d.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(av, d)
                        n_avail += 1
    report["fact_lists"] = n_lists
    report["claude_availability_records"] = n_avail


def _copy_drafts_and_marks(runs: Path, stage: Path, lists: dict[str, list[str]], report: dict[str, Any]) -> None:
    main = runs / MAIN_RUN
    n = defaultdict(int)
    marks_mims = sorted(set(lists["A1"]) | set(lists["B1"]))
    for mim in marks_mims:
        for s in STRATEGIES_A1:
            ev = main / mim / f"eval.{s}.json"
            if not ev.exists():
                continue
            evaluation = _read(ev)
            if mim in lists["A1"]:
                if evaluation.get("stopped"):
                    report["problems"].append(f"{mim}: {s} has no draft in the main run")
                    continue
                dst = stage / "drafts" / "main" / mim / f"entry.{s}.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(main / mim / f"entry.{s}.json", dst)
                n["drafts_main"] += 1
            marks = _marks_only(evaluation.get("gold_text_frozen"))
            if marks:
                write_json(stage / "claude" / "marks" / "main" / mim / f"{s}.json", marks)
                n["claude_marks_main"] += 1
            for salt in ("j1", "j2"):
                jf = main / mim / f"judge_{salt}.{s}.json"
                if jf.exists():
                    write_json(stage / "claude" / "marks" / f"judge_{salt}" / mim / f"{s}.json",
                               _marks_only(_read(jf).get("gold_text_frozen")))
                    n[f"claude_marks_judge_{salt}"] += 1
    for mim in lists["A2"]:
        gf = _read(main / mim / "gold_facts.json")
        rows = [{"key": p["key"], "source_key": (p.get("availability") or {}).get("source_key"),
                 "per_paper_chars": (p.get("availability") or {}).get("per_paper_chars"),
                 "rows": [{k: r.get(k) for k in ("id", "in_text", "model_in_text", "quote_verified")}
                          for r in (p.get("availability") or {}).get("rows") or []]}
                for p in gf["paragraphs"]]
        write_json(stage / "claude" / "availability" / f"{mim}.json", {"mim": mim, "paragraphs": rows})
        n["claude_availability"] += 1
        conv = main / mim / "gaps.direct.conveyed.json"
        if conv.exists():
            c = _read(conv)
            write_json(stage / "claude" / "conveyed" / f"{mim}.json", {
                "mim": mim, "per_paper_chars": c.get("per_paper_chars"),
                "paragraphs": [{"key": p["key"], "pmids": p.get("pmids"), "content_level": p.get("content_level"),
                                "facts": [{k: f.get(k) for k in ("id", "draft_status", "own", "other", "class")}
                                          for f in p.get("facts") or []]} for p in c.get("paragraphs") or []]})
            n["claude_conveyed"] += 1
        else:
            report["problems"].append(f"{mim}: no gaps.direct.conveyed.json")
    sh = runs / SECONDHAND_RUN
    for mim in sorted(set(lists["A3"]) | set(lists["B2"])):
        d = sh / mim / "secondhand_check"
        cov = _read(d / "coverage_frozen.json")
        for arm in ("abstract", "secondhand", "fulltext"):
            rows = [r.get(arm) for r in cov["paragraphs"]]
            write_json(stage / "claude" / "marks" / "secondhand" / mim / f"{arm}.json",
                       _marks_only({"paragraphs": [r for r in rows if r]}))
        before = _read(d / "coverage_frozen_before_repair.json")
        write_json(stage / "claude" / "marks" / "secondhand" / mim / "fulltext_before_repair.json",
                   _marks_only({"paragraphs": [p["before_repair"] for p in before.get("paragraphs") or []
                                               if p.get("before_repair")]}))
        if mim in lists["A3"]:
            for arm in ("abstract", "secondhand"):
                dst = stage / "drafts" / "secondhand" / mim / f"entry.{arm}.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(d / f"entry.{arm}.json", dst)
                n["drafts_secondhand"] += 1
    report.update(dict(n))


def _rebuild_before_repair(runs: Path, stage: Path, mims: list[str], report: dict[str, Any]) -> None:
    """The full-text direct draft as it was before the repair round, rebuilt from cached replies only."""
    from ..secondhand import rebuild_before_repair

    for mim in mims:
        before, after, misses = rebuild_before_repair(runs / MAIN_RUN / mim)
        stored = _read(runs / MAIN_RUN / mim / "entry.direct.json")
        same = [p.text for p in after.all_paragraphs()] == [
            p["text"] for p in ([stored["intro"]] if stored.get("intro") else [])
            + [x for s in stored["sections"] for x in s["paragraphs"]]
            + [x for av in stored["allelic_variants"] for x in av["paragraphs"]]]
        if misses or not same:
            report["problems"].append(f"{mim}: the before-repair draft could not be rebuilt exactly")
            continue
        write_json(stage / "drafts" / "secondhand" / mim / "entry.fulltext_before_repair.json", before.model_dump())
    report["drafts_before_repair"] = len(mims)


def _copy_ontology_and_hgnc(data: Path, stage: Path, hgnc_complete: Path, report: dict[str, Any]) -> None:
    from .offline import compact_hgnc

    onto = stage / "ontologies"
    onto.mkdir(parents=True, exist_ok=True)
    for name in ("hp.obo", "phenotype.hpoa"):
        shutil.copyfile(data / "ontologies" / name, onto / name)
    n = 0
    for path in (data / "cache" / "http").glob("*/*.txt"):
        with open(path, "rb") as fh:
            head = fh.read(20)
        if head.startswith(b'{"responseHeader"'):
            dst = stage / "http" / path.parent.name / path.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dst)
            n += 1
    report["hgnc_cached_responses"] = n
    table = compact_hgnc(json.loads(Path(hgnc_complete).read_text(encoding="utf-8")))
    write_json(stage / "hgnc" / "hgnc_table.json", {"source": "HGNC complete set (genenames.org public download)",
                                                    "n": len(table), "docs": table}, indent=None)
    report["hgnc_table_genes"] = len(table)


def _manifest(repo: Path, stage: Path, study: Study, lists: dict[str, list[str]], report: dict[str, Any]
              ) -> dict[str, Any]:
    files = {}
    for path in sorted(p for p in stage.rglob("*") if p.is_file() and p.name != "MANIFEST.json"):
        files[str(path.relative_to(stage))] = _sha256(path)
    bundle_id = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    try:
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=False).stdout.strip()
    except OSError:
        commit = ""
    manifest = {
        "bundle_id": bundle_id, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builder_commit": commit, "note": "Private: contains OMIM-derived text and paper text. Never commit.",
        "entries": lists, "counts": {k: v for k, v in report.items() if k not in ("problems", "verification")},
        "verification": report.get("verification"), "code_fingerprint": code_fingerprint(), "files": files,
    }
    write_json(stage / "MANIFEST.json", manifest)
    return manifest


def _pack(stage: Path, out_tar: Path) -> None:
    out_tar.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_tar.with_suffix(".part")
    with tarfile.open(tmp, "w:gz", compresslevel=9) as tar:
        tar.add(stage, arcname="bundle")
    tmp.replace(out_tar)
    (out_tar.parent / (out_tar.name + ".sha256")).write_text(f"{_sha256(out_tar)}  {out_tar.name}\n")


# --------------------------------------------------------------------------- #
# Verification: rebuild the prompts from the bundle and look them up in the original runs' cache
# --------------------------------------------------------------------------- #


def verify_replay(bundle_dir: Path, study: Study, claude_cache: Path, work: Path, *, jobs: int = 8,
                  specs: list | None = None) -> dict[str, Any]:
    """Run every task over the bundle with the original runs' model name, reading replies from their cache.

    A call whose key is in that cache was built byte for byte as the original run built it
    (the key hashes model, effort, system prompt, prompt and schema). The replay stops a
    task at its first call the cache does not hold (it records it; nothing is sent and
    nothing is written to that cache). For the judge tasks the replayed marks and
    verdicts must equal the stored ones fact by fact.
    """
    from ..cache import DiskCache
    from .backend import Recorder
    from .offline import activate, deactivate, network_blocked
    from .tasks import Bundle, Context, ReadOnlyCache, plan_tasks, run_all

    if work.exists():
        shutil.rmtree(work)
    paths = StudyPaths(work)
    recorder = Recorder(study, None, model=CLAUDE_MODEL)
    reply_cache = ReadOnlyCache(DiskCache(Path(claude_cache)))
    specs = specs if specs is not None else plan_tasks(study)
    bundle = Bundle(bundle_dir)
    started = time.time()
    with network_blocked() as attempts:
        before = len(attempts)
        settings = activate(paths, study, model=CLAUDE_MODEL, bundle_dir=bundle_dir)
        ctx = Context(paths, study, bundle, settings, recorder, reply_cache=reply_cache)
        outcomes = run_all(ctx, specs, jobs)
        network = len(attempts) - before
    from .. import http as aiomim_http

    emulated = list(getattr(aiomim_http._HTTP, "emulated", []))
    deactivate()
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for o in outcomes:
        by_kind[o.spec.kind][o.status] += 1
    misses: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    miss_keys = []
    for e in recorder.entries.values():
        kinds = sorted({t.split(":")[0] for t in e["tasks"]})
        misses[",".join(kinds)][e["label"]] += 1
        miss_keys.append(e["claude_key"])
    equal = _compare_replayed(bundle, outcomes)
    write_json(bundle_dir / "verify" / "prompt_keys.json",
               {"model": CLAUDE_MODEL, "hit": sorted(reply_cache.hits), "miss": sorted(set(miss_keys))}, indent=None)
    report = {"tasks": len(specs), "seconds": round(time.time() - started, 1), "network_attempts": network,
              "outcomes_by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
              "calls_found_in_original_cache": len(reply_cache.hits),
              "calls_not_in_original_cache_by_kind_and_label": {k: dict(v) for k, v in sorted(misses.items())},
              "hgnc_lookups_emulated": len(emulated), "replayed_equals_stored": equal,
              "task_errors": [f"{o.spec.id}: {o.message}" for o in outcomes if o.status == "error"][:20]}
    write_json(bundle_dir / "verify" / "report.json", report)
    return report


def _compare_replayed(bundle, outcomes) -> dict[str, Any]:
    """Replayed judge outputs against the stored Claude ones, fact by fact."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for o in outcomes:
        if o.status not in ("complete", "incomplete", "stopped", "failed") or not o.payload:
            continue
        kind, mim, var = o.spec.kind, o.spec.mim, o.spec.variant
        if kind in ("A1", "A3"):
            stored = bundle.claude_marks("main" if kind == "A1" else "secondhand", mim, var)
            if not stored:
                continue
            want = {f["id"]: f["status"] for p in stored["paragraphs"] for f in p["facts"]}
            got = {f["id"]: f["status"] for p in o.payload["gold_text_frozen"].get("paragraphs", [])
                   for f in p.get("facts", [])}
        elif kind == "A2F":
            stored = bundle.claude_availability(mim) or {"paragraphs": []}
            want = {r["id"]: r["in_text"] for p in stored["paragraphs"] for r in p["rows"]}
            got = {r["id"]: r["in_text"] for a in o.payload["availability"].values() for r in a["rows"]}
        elif kind == "A2C":
            stored = bundle.claude_conveyed(mim) or {"paragraphs": []}
            want = {f["id"]: (f["own"], f["other"]) for p in stored["paragraphs"] for f in p["facts"]}
            got = {f["id"]: (f["own"], f["other"]) for f in o.payload["facts"]}
        else:
            continue
        cell = out[kind]
        for fid, status in want.items():
            cell["facts"] += 1
            if got.get(fid) == status:
                cell["equal"] += 1
        cell["tasks"] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


# --------------------------------------------------------------------------- #
# Owner's side
# --------------------------------------------------------------------------- #


def unpack(paths: StudyPaths, tar_path: Path | None = None) -> Path:
    """Extract the archive into private/bundle (safely: no absolute paths, no links out)."""
    tar_path = Path(tar_path or paths.bundle_tar)
    if not tar_path.exists():
        raise StudyError(f"no bundle archive at {tar_path}")
    sha_file = tar_path.parent / (tar_path.name + ".sha256")
    if sha_file.exists():
        want = sha_file.read_text().split()[0]
        if _sha256(tar_path) != want:
            raise StudyError("the bundle archive does not match its .sha256 file")
    tmp = paths.private / ".unpack"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        try:
            tar.extractall(tmp, filter="data")
        except TypeError:  # pragma: no cover - Python without extraction filters
            for m in tar.getmembers():
                if m.name.startswith("/") or ".." in Path(m.name).parts or m.issym() or m.islnk():
                    raise StudyError(f"unsafe member in the bundle: {m.name}")
            tar.extractall(tmp)
    if paths.bundle.exists():
        shutil.rmtree(paths.bundle)
    (tmp / "bundle").rename(paths.bundle)
    shutil.rmtree(tmp)
    return paths.bundle


def check_files(bundle_dir: Path) -> list[str]:
    """Every file the manifest lists is there with its sha256; returns the problems."""
    manifest = _read(bundle_dir / "MANIFEST.json")
    problems = []
    for rel, digest in manifest["files"].items():
        p = bundle_dir / rel
        if not p.exists():
            problems.append(f"missing: {rel}")
        elif _sha256(p) != digest:
            problems.append(f"changed: {rel}")
    return problems
