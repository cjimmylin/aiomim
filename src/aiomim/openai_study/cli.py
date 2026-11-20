"""Command line: `python -m aiomim.openai_study <command> --study studies/openai_second_model`.

    check      environment, bundle, API key (never printed), packages, study.json, cost cap
    plan       the task list from study.json -> state/tasks.json
    collect    run unfinished tasks offline; write the next wave's request files (no network)
    submit     upload the wave and create its batch(es) (24h window); refuses past the cost cap
    poll       check open batches; download their output and error files
    ingest     write downloaded replies into the study's cache; update the ledger
    step       poll -> ingest -> collect -> submit; one line of status; state/status.json
    smoke      a batch of at most 8 requests, one per kind of call, to check format and parsing
    status     print state/status.json
    report     write outputs/ from the finished tasks
    validate   check outputs/ against the JSON Schemas and for OMIM wording; non-zero exit on a problem

The Claude Code side, afterwards (not for the OpenAI run):

    restore-drafts put back the spans `report` redacted from the drafts (they match OMIM's wording)
    bundle         build the private input bundle from runs/ and data/
    verify-bundle  replay every task over an unpacked bundle against the original runs' cache
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import platform
import sys
from pathlib import Path

from . import STUDY_DIR_DEFAULT
from .config import Study, StudyPaths, read_json, write_json
from .errors import StudyError


def _paths(args) -> StudyPaths:
    return StudyPaths(Path(args.study).resolve())


def _fake(args) -> dict | None:
    if not getattr(args, "fake_provider", None):
        return None
    faults = json.loads(args.fake_faults) if args.fake_faults else None
    return {"claude_cache": args.fake_provider if args.fake_provider != "none" else None, "faults": faults,
            "polls": args.fake_polls}


def _provider(paths: StudyPaths, study: Study, args):
    from .providers import make_provider

    return make_provider(paths, study, _fake(args))


def _print(obj) -> None:
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


def cmd_check(args) -> int:
    from .bundle import check_files, code_fingerprint, unpack

    paths = _paths(args)
    report: dict = {"python": platform.python_version(), "problems": [], "warnings": []}
    if sys.version_info < (3, 10):
        report["problems"].append("Python 3.10 or newer is needed (3.13 recommended)")
    for mod, need in (("pydantic", True), ("requests", True), ("lxml", True), ("openai", False),
                      ("jsonschema", True)):
        try:
            m = importlib.import_module(mod)
            report[f"package:{mod}"] = getattr(m, "__version__", "installed")
        except ImportError:
            (report["problems"] if need else report["warnings"]).append(
                f"package `{mod}` is not installed" + ("" if need else " (needed by submit, poll, step, smoke)"))
    report["OPENAI_API_KEY"] = "present" if os.environ.get("OPENAI_API_KEY") else "missing"
    if report["OPENAI_API_KEY"] == "missing":
        report["warnings"].append("OPENAI_API_KEY is not set (needed by submit, poll, step, smoke)")
    try:
        study = Study.load(paths)
        report["model"] = study.model
        report["cap_usd"] = study.cap_usd
        report["batch_price"] = study.price()
    except StudyError as exc:
        report["problems"].append(str(exc))
        study = None
    if not (paths.bundle / "MANIFEST.json").exists():
        if paths.bundle_tar.exists():
            try:
                unpack(paths)
                report["bundle_unpacked"] = True
            except StudyError as exc:
                report["problems"].append(str(exc))
        else:
            report["problems"].append(f"no bundle: place the archive at {paths.bundle_tar} (and its .sha256)")
    if (paths.bundle / "MANIFEST.json").exists():
        manifest = read_json(paths.bundle / "MANIFEST.json")
        report["bundle_id"] = manifest.get("bundle_id")
        missing = check_files(paths.bundle)
        if missing:
            report["problems"].append(f"bundle incomplete or changed: {len(missing)} file(s), e.g. {missing[:3]}")
        else:
            report["bundle_files"] = len(manifest["files"])
        fp_now, fp_bundle = code_fingerprint(), manifest.get("code_fingerprint") or {}
        diff = sorted(k for k in set(fp_now) | set(fp_bundle) if fp_now.get(k) != fp_bundle.get(k))
        if diff:
            report["problems"].append("this checkout's prompts, schemas or efforts differ from those the bundle "
                                      f"was built for: {diff}. Check out commit {manifest.get('builder_commit')}")
        if study is not None:
            have = set((manifest.get("entries") or {}).get("A1", [])) | set().union(
                *[set(v) for v in (manifest.get("entries") or {}).values()])
            want = set().union(*[set((study.tasks().get(k) or {}).get("entries", []))
                                 for k in ("A1", "A2", "A3", "B1", "B2")])
            if want - have:
                report["problems"].append(f"study.json names entries the bundle lacks: {sorted(want - have)[:5]}")
        ver = manifest.get("verification") or {}
        report["bundle_verification"] = {"replayed_equals_stored": ver.get("replayed_equals_stored"),
                                         "network_attempts": ver.get("network_attempts")}
    report["ok"] = not report["problems"]
    write_json(paths.state / "check.json", {k: v for k, v in report.items()})
    _print(report)
    return 0 if report["ok"] else 1


# --------------------------------------------------------------------------- #
# the wave commands
# --------------------------------------------------------------------------- #


def cmd_plan(args) -> int:
    from .waves import plan

    paths = _paths(args)
    st = plan(paths, Study.load(paths))
    _print({"tasks": len(st["tasks"]), "counts": st["counts"], "dropped_from_plan": st["dropped_from_plan"]})
    return 0


def cmd_collect(args) -> int:
    from .waves import collect

    paths = _paths(args)
    out = collect(paths, Study.load(paths), jobs=args.jobs, force=args.force,
                  kinds=args.kinds.split(",") if args.kinds else None, retry_failed=args.retry_failed)
    _print(out)
    return 0 if not out.get("task_errors") and not out.get("network_attempts") else 1


def cmd_submit(args) -> int:
    from .waves import submit

    paths = _paths(args)
    study = Study.load(paths)
    out = submit(paths, study, _provider(paths, study, args))
    _print(out)
    return 1 if out.get("blocked") and not out["submitted"] else 0


def cmd_poll(args) -> int:
    from .waves import poll

    paths = _paths(args)
    study = Study.load(paths)
    _print(poll(paths, _provider(paths, study, args)))
    return 0


def cmd_ingest(args) -> int:
    from .waves import ingest

    paths = _paths(args)
    out = ingest(paths, Study.load(paths))
    _print(out)
    return 1 if out.get("blocked") else 0


def cmd_step(args) -> int:
    from .waves import status_line, step

    paths = _paths(args)
    study = Study.load(paths)
    status = step(paths, study, _provider(paths, study, args), jobs=args.jobs)
    print(status_line(status))
    return {"blocked": 2}.get(status["phase"], 0)


def cmd_smoke(args) -> int:
    from .waves import reset_smoke, smoke

    paths = _paths(args)
    study = Study.load(paths)
    if args.reset:
        reset_smoke(paths)
    st = smoke(paths, study, _provider(paths, study, args), jobs=args.jobs)
    _print({k: v for k, v in st.items() if k != "results"} | {"results": st.get("results")})
    if st.get("ended"):
        return 0 if st.get("passed") else 1
    return 0


def cmd_status(args) -> int:
    from .waves import status_line

    paths = _paths(args)
    st = read_json(paths.state / "status.json")
    if not st:
        print("no status yet: run step")
        return 0
    print(status_line(st))
    if args.verbose:
        _print(st)
    return 0


def cmd_report(args) -> int:
    from .report import report

    paths = _paths(args)
    s = report(paths, Study.load(paths))
    print(f"wrote {paths.outputs}: {s['files']}; redacted spans {s['redactions']['spans']}")
    return 0


def cmd_validate(args) -> int:
    from .validate import (
        OmimScanner,
        gold_texts_from_bundle,
        gold_texts_from_runs,
        validate_dir,
    )

    paths = _paths(args)
    if args.gold_runs:
        texts = gold_texts_from_runs(Path(args.gold_runs))
    elif (paths.bundle / "MANIFEST.json").exists():
        texts = gold_texts_from_bundle(paths.bundle)
    else:
        print("validate needs the bundle (or --gold-runs DIR) to scan for OMIM wording", file=sys.stderr)
        return 1
    scanner = OmimScanner(texts)
    out = validate_dir(paths.outputs, paths.schemas, scanner, also=[paths.state])
    _print({k: v for k, v in out.items() if k != "problems"} | {"problems": out["problems"][:50],
                                                                "n_problems": len(out["problems"])})
    return 0 if out["ok"] else 1


def cmd_restore_drafts(args) -> int:
    """Claude Code side: the OpenAI drafts with redacted spans put back from the local gold text.

    `--layout run` writes run folders that `aiomim rescore` can score with the Claude judge:
    <out>/<task>/<mim>/ with the entry's gold.json, papers.json and seed.json from the gold run
    folder, entry.<strategy>.json, and an eval stub (`AIOMIM_RUNS=<out> aiomim rescore <task>`).
    """
    import shutil

    from ..models import GeneratedEntry
    from ..render import entry_markdown
    from .validate import gold_texts_from_runs, resolver, restore_entry

    paths = _paths(args)
    gold_runs = Path(args.gold_runs)
    resolve = resolver(gold_texts_from_runs(gold_runs))
    out_dir = Path(args.out)
    n = restored = 0
    for path in sorted((paths.outputs / "drafts").rglob("entry.*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        had = bool((entry.get("meta") or {}).get("redactions"))
        entry = restore_entry(entry, resolve)
        rel = path.relative_to(paths.outputs / "drafts")       # <task>/<mim>/entry.<s>.json
        write_json(out_dir / rel, entry)
        (out_dir / rel.with_suffix(".md")).write_text(
            entry_markdown(GeneratedEntry.model_validate(entry), show_flags=False), encoding="utf-8")
        if args.layout == "run":
            mim, strategy = rel.parts[1], rel.name.split(".")[1]
            for name in ("gold.json", "papers.json", "seed.json"):
                src = gold_runs / mim / name
                if src.exists():
                    shutil.copyfile(src, out_dir / rel.parent / name)
            stopped = (entry.get("meta") or {}).get("stopped")
            write_json(out_dir / rel.parent / f"eval.{strategy}.json",
                       {"mim": mim, "strategy": strategy, "openai_draft": True, **({"stopped": stopped} if stopped else {})})
        n += 1
        restored += had
    print(f"wrote {n} drafts to {out_dir} ({restored} had redacted spans, now restored); keep them out of git")
    return 0


# --------------------------------------------------------------------------- #
# kit maintenance
# --------------------------------------------------------------------------- #


def cmd_bundle(args) -> int:
    from .bundle import build

    repo = Path(args.repo).resolve()
    os.environ["AIOMIM_HOME"] = str(repo / "data")
    os.environ["AIOMIM_RUNS"] = str(repo / "runs")
    os.chdir(repo)
    from ..config import get_settings

    get_settings.cache_clear()
    paths = _paths(args)
    out = build(repo, Study.load(paths), Path(args.out).resolve(), hgnc_complete=Path(args.hgnc).resolve(),
                work=Path(args.work).resolve(), verify=not args.no_verify, jobs=args.jobs)
    _print(out)
    return 0


def cmd_verify_bundle(args) -> int:
    from .bundle import verify_replay

    paths = _paths(args)
    study = Study.load(paths)
    out = verify_replay(Path(args.bundle).resolve(), study, Path(args.claude_cache).resolve(),
                        Path(args.work).resolve(), jobs=args.jobs)
    _print(out)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m aiomim.openai_study", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", default="WARNING", help="log level (default WARNING)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--study", default=STUDY_DIR_DEFAULT, help="the study directory")
        sp.add_argument("--jobs", type=int, default=None, help="tasks run at once (default from study.json)")
        sp.add_argument("--fake-provider", default=None, help=argparse.SUPPRESS)
        sp.add_argument("--fake-faults", default=None, help=argparse.SUPPRESS)
        sp.add_argument("--fake-polls", type=int, default=1, help=argparse.SUPPRESS)
        sp.set_defaults(fn=fn)
        return sp

    add("check", cmd_check, "environment, bundle, API key, packages, study.json, cost cap")
    add("plan", cmd_plan, "build state/tasks.json from study.json")
    c = add("collect", cmd_collect, "run unfinished tasks offline and write the wave's request files")
    c.add_argument("--force", action="store_true", help="collect although a batch is open")
    c.add_argument("--kinds", default=None, help="only these task kinds (comma-separated)")
    c.add_argument("--retry-failed", action="store_true", help="run failed tasks again")
    add("submit", cmd_submit, "upload the wave and create its batch(es)")
    add("poll", cmd_poll, "check open batches; download finished ones")
    add("ingest", cmd_ingest, "write downloaded replies into the cache; update the ledger")
    add("step", cmd_step, "poll -> ingest -> collect -> submit (the only command a driver repeats)")
    s = add("smoke", cmd_smoke, "a tiny batch that checks request format and parsing end to end")
    s.add_argument("--reset", action="store_true", help="discard an earlier smoke batch and start again")
    st = add("status", cmd_status, "print the current status")
    st.add_argument("--verbose", action="store_true")
    add("report", cmd_report, "write outputs/ from the finished tasks")
    v = add("validate", cmd_validate, "validate outputs/ (schemas, OMIM wording)")
    v.add_argument("--gold-runs", default=None, help="scan against gold.json/gold_facts.json under this run folder")
    r = add("restore-drafts", cmd_restore_drafts, "Claude Code side: put redacted spans back from the gold text")
    r.add_argument("--gold-runs", required=True, help="a run folder with gold.json and gold_facts.json per entry")
    r.add_argument("--out", required=True, help="where to write the restored drafts (outside git)")
    r.add_argument("--layout", choices=("flat", "run"), default="flat",
                   help="run: folders `aiomim rescore` can score with the Claude judge")
    b = add("bundle", cmd_bundle, "build the private bundle (kit maintenance)")
    b.add_argument("--out", required=True)
    b.add_argument("--repo", default=".")
    b.add_argument("--hgnc", required=True, help="HGNC complete set (hgnc_complete_set.json)")
    b.add_argument("--work", required=True, help="a scratch folder")
    b.add_argument("--no-verify", action="store_true")
    vb = add("verify-bundle", cmd_verify_bundle, "replay the tasks over a bundle against a Claude cache")
    vb.add_argument("--bundle", required=True)
    vb.add_argument("--claude-cache", required=True)
    vb.add_argument("--work", required=True)

    args = p.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.WARNING),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.jobs is None and args.cmd in ("bundle", "verify-bundle"):
        args.jobs = 8
    try:
        return args.fn(args)
    except StudyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
