"""STORM (`knowledge-storm`, Stanford OVAL) as released, for Experiment B (docs/experiments-round2.md, section B).

Per entry: export the supplied papers, start the adapter (concurrency 3), run `storm_runner.py` in the
system's own environment `.venvs/storm/` (STORMWikiRunner, default arguments, all four stages, VectorRM over
exactly the entry's papers), take the final polished article, cut it into one block per paragraph with the
text unedited, map its `[n]` markers through STORM's own reference list (the polished article's) to the
supplied papers' PubMed ids, and save the intermediate format under system name `storm`.

    PYTHONPATH=src python -m aiomim.external.sys_storm smoke             # one tiny call through the package
    PYTHONPATH=src python -m aiomim.external.sys_storm run 621313 ...    # given entries
    PYTHONPATH=src python -m aiomim.external.sys_storm run --first 10 --budget 800
    PYTHONPATH=src python -m aiomim.external.sys_storm report            # per-entry usage table (JSON)

Resumable: an entry whose output.json exists is skipped (unless --force); a re-run of an unfinished entry
repeats the pipeline, and the adapter's cache answers every request it already answered.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SYSTEM = "storm"
PACKAGE = "knowledge-storm"
MAX_CONCURRENCY = 3
REPO = Path(__file__).resolve().parents[3]
VENV_PY = REPO / ".venvs" / SYSTEM / "bin" / "python"
RUNNER = Path(__file__).resolve().with_name("storm_runner.py")
STAGE_NAMES = ("research", "outline", "article", "polish")

_HEADING = re.compile(r"^(#+)\s*(.*?)\s*$")
_MARKER = re.compile(r"\[(\d+)\]")
_PUBMED = re.compile(r"^https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?$")


# --------------------------------------------------------------------------- conversion (pure)

def parse_article(text: str) -> list[dict[str, str]]:
    """The polished article as [{section, text}], one item per paragraph, text unedited.

    `#`-headings set the section (the nearest heading, as written; STORM's lead section is its `# summary`);
    paragraphs are separated by blank lines; within a chunk, each non-empty line is its own paragraph
    (STORM writes one paragraph per line). Heading lines are not paragraphs. Text before any heading gets
    section "(no heading)"."""
    blocks: list[dict[str, str]] = []
    section = "(no heading)"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = _HEADING.match(stripped)
        if m:
            section = m.group(2) or section
            continue
        blocks.append({"section": section, "text": stripped})
    return blocks


def index_to_pmid(reference: dict[str, Any], supplied: set[str]) -> dict[int, str]:
    """STORM's reference list (`url_to_unified_index`: url -> [n]) to {n: pmid} for supplied papers only."""
    out: dict[int, str] = {}
    for url, idx in (reference.get("url_to_unified_index") or {}).items():
        m = _PUBMED.match(str(url).strip())
        if m and m.group(1) in supplied:
            out[int(idx)] = m.group(1)
    return out


def map_citations(text: str, mapping: dict[int, str]) -> tuple[list[str], list[str]]:
    """(mapped PMIDs in order of first citation, raw markers in order) of one paragraph."""
    raw = [m.group(0) for m in _MARKER.finditer(text)]
    pmids = [mapping[int(m.group(1))] for m in _MARKER.finditer(text) if int(m.group(1)) in mapping]
    return list(dict.fromkeys(pmids)), raw


def article_blocks(text: str, reference: dict[str, Any], supplied: set[str]) -> list[dict[str, Any]]:
    mapping = index_to_pmid(reference, supplied)
    blocks = []
    for b in parse_article(text):
        pmids, raw = map_citations(b["text"], mapping)
        blocks.append({"section": b["section"], "text": b["text"], "pmids": pmids, "citations": raw})
    return blocks


def unmapped_markers(blocks: list[dict[str, Any]], reference: dict[str, Any], supplied: set[str]) -> list[str]:
    """Markers whose number is not in the reference list (or not a supplied paper)."""
    mapping = index_to_pmid(reference, supplied)
    return sorted({c for b in blocks for c in b["citations"] if int(c.strip("[]")) not in mapping},
                  key=lambda c: int(c.strip("[]")))


# --------------------------------------------------------------------------- ledger

def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def ledger_summary(rows: list[dict[str, Any]], tag: str) -> dict[str, Any]:
    """Fresh model calls, tokens, cost and seconds per stage, from the adapter's ledger lines."""
    stages: dict[str, dict[str, Any]] = {}
    tot = {"requests": 0, "fresh_calls": 0, "cached": 0, "refused": 0, "errors": 0, "stops": 0,
           "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "call_seconds": 0.0, "json_invalid": 0}
    for r in rows:
        t = r.get("tag") or ""
        if r.get("endpoint") != "/v1/chat/completions" or not (t == tag or t.startswith(tag + "/")):
            continue
        stage = t[len(tag) + 1:] if t != tag else "(untagged)"
        s = stages.setdefault(stage, {k: 0 for k in tot} | {"cost_usd": 0.0, "call_seconds": 0.0})
        for d in (s, tot):
            d["requests"] += 1
            if r.get("status") == 400:
                d["refused"] += 1
                continue
            if r.get("status") != 200:
                d["errors"] += 1
                continue
            d["stops"] += int(bool(r.get("safety_stop")))
            if r.get("cached"):
                d["cached"] += 1
                continue
            d["fresh_calls"] += int(r.get("model_calls") or 1)
            d["input_tokens"] += int(r.get("input_tokens") or 0)
            d["output_tokens"] += int(r.get("output_tokens") or 0)
            d["cost_usd"] += float(r.get("cost_usd") or 0.0)
            d["call_seconds"] += float(r.get("call_seconds") or 0.0)
    for d in [tot, *stages.values()]:
        d["cost_usd"] = round(d["cost_usd"], 4)
        d["call_seconds"] = round(d["call_seconds"], 1)
    return {"total": tot, "stages": stages}


def budget_used() -> int:
    """Fresh model calls through the adapter so far, over every ledger of this system (smoke and pilot included)."""
    from .adapt import entry_dir

    root = entry_dir(SYSTEM, "0").parent
    n = 0
    for path in root.rglob("ledger.jsonl"):
        for r in read_ledger(path):
            if r.get("endpoint") == "/v1/chat/completions" and r.get("status") == 200 and not r.get("cached"):
                n += int(r.get("model_calls") or 1)
    return n


# --------------------------------------------------------------------------- subprocess

def subprocess_env(base_url: str) -> dict[str, str]:
    """A clean environment: no provider key from the parent; the HTTPS proxy only for the Wikipedia pages."""
    from .adapt import entry_dir

    home = entry_dir(SYSTEM, "_home")
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": f"{VENV_PY.parent}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "VIRTUAL_ENV": str(VENV_PY.parent.parent),
        "HF_HOME": str(Path.home() / ".cache" / "huggingface"),
        "OPENAI_API_KEY": "sk-local-dummy", "OPENAI_BASE_URL": base_url, "OPENAI_API_BASE": base_url,
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True", "LITELLM_TELEMETRY": "False",
        "ANONYMIZED_TELEMETRY": "False", "DO_NOT_TRACK": "1", "OTEL_SDK_DISABLED": "true",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "TIKTOKEN_CACHE_DIR": str(REPO / "data" / "cache" / "tiktoken"),
        "PYTHONUNBUFFERED": "1",
    }
    for k in ("HTTPS_PROXY", "https_proxy", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def run_runner(args: list[str], base_url: str, log_path: Path, timeout: int = 6000) -> int:
    cmd = [str(VENV_PY), "-P", str(RUNNER), *args]
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n=== {time.strftime('%Y-%m-%dT%H:%M:%S')} {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, env=subprocess_env(base_url), stdout=log, stderr=subprocess.STDOUT,
                              timeout=timeout, cwd=str(log_path.parent))
    return proc.returncode


def static_info() -> dict[str, Any]:
    """Versions and changed settings, from the system's environment (no model, no network)."""
    out = subprocess.run([str(VENV_PY), "-P", str(RUNNER), "--versions", "--work", "-", "--base-url", "-",
                          "--tag", "-"], env=subprocess_env("http://127.0.0.1:9/v1"), capture_output=True,
                         text=True, timeout=600)
    return json.loads(out.stdout.strip().splitlines()[-1])


def smoke() -> dict[str, Any]:
    from .adapt import entry_dir
    from .shim import ShimServer

    folder = entry_dir(SYSTEM, "_smoke")
    folder.mkdir(parents=True, exist_ok=True)
    with ShimServer(tag=f"{SYSTEM}/_smoke", ledger=folder / "ledger.jsonl", max_concurrency=MAX_CONCURRENCY) as url:
        rc = run_runner(["--work", str(folder / "work"), "--base-url", url, "--tag", f"{SYSTEM}/_smoke", "--smoke"],
                        url, folder / "runner.log", timeout=1200)
    return {"returncode": rc, "ledger": read_ledger(folder / "ledger.jsonl")[-1:]}


# --------------------------------------------------------------------------- one entry

def run_entry(mim: str, force: bool = False) -> dict[str, Any]:
    from .adapt import entry_dir, save_output
    from .corpus import export_entry
    from .shim import ShimServer
    from .tasks import storm_topic

    folder = entry_dir(SYSTEM, mim)
    if (folder / "output.json").exists() and not force:
        return {"mim": mim, "skipped": "output.json exists"}
    corpus = export_entry(mim, folder / "corpus")
    topic = storm_topic(corpus.title)
    tag = f"{SYSTEM}/{mim}"
    work = folder / "work"
    ledger = folder / "ledger.jsonl"
    started = time.time()
    with ShimServer(tag=tag, ledger=ledger, max_concurrency=MAX_CONCURRENCY) as base_url:
        rc = run_runner(["--corpus", str(folder / "corpus"), "--work", str(work), "--topic", topic,
                         "--base-url", base_url, "--tag", tag], base_url, folder / "runner.log")
    seconds = round(time.time() - started, 1)
    stats_path = work / "run_stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
    if not stats.get("versions") or not stats.get("settings_changed"):   # the runner stopped before writing them
        stats = {**static_info(), **stats}
    usage = ledger_summary(read_ledger(ledger), tag)
    supplied = set(corpus.pmids)

    article_dir = Path(stats["article_dir"]) if stats.get("article_dir") else None
    polished = article_dir / "storm_gen_article_polished.txt" if article_dir else None
    refs = article_dir / "url_to_info_polished.json" if article_dir else None
    blocks: list[dict[str, Any]] = []
    unmapped: list[str] = []
    if rc == 0 and polished and polished.exists() and refs and refs.exists():
        reference = json.loads(refs.read_text(encoding="utf-8"))
        blocks = article_blocks(polished.read_text(encoding="utf-8"), reference, supplied)
        unmapped = unmapped_markers(blocks, reference, supplied)

    stops = usage["total"]["stops"]
    stopped = None
    if not blocks:
        stopped = (f"safety stop ({stops} stopped replies); no usable article" if stops
                   else f"no usable article (runner exit code {rc}; see runner.log)")
    output = {
        "system": SYSTEM, "mim": mim, "stopped": stopped, "blocks": blocks,
        "meta": {
            "package": PACKAGE, "version": (stats.get("versions") or {}).get("knowledge-storm"),
            "versions": stats.get("versions"),
            "settings_changed": stats.get("settings_changed") or [],
            "topic": topic,
            "calls": usage["total"]["fresh_calls"], "requests": usage["total"]["requests"],
            "stops": stops, "refused": usage["total"]["refused"], "seconds": seconds,
            "stage_seconds": stats.get("stage_seconds"), "index_seconds": stats.get("index_seconds"),
            "usage_by_stage": usage["stages"], "chunks": stats.get("chunks"),
            "wikipedia_pages": stats.get("wikipedia_pages"),
            "unmapped_markers": unmapped, "runner_exit_code": rc,
            "tag": tag, "ledgers": [str(ledger.relative_to(REPO)) if ledger.is_relative_to(REPO) else str(ledger)],
        },
    }
    save_output(output)
    chars = sum(len(b["text"]) for b in blocks)
    uncited = sum(len(b["text"]) for b in blocks if not b["pmids"])
    return {"mim": mim, "rc": rc, "blocks": len(blocks), "cited_blocks": sum(1 for b in blocks if b["pmids"]),
            "chars": chars, "uncited_share": round(uncited / chars, 3) if chars else None,
            "calls": usage["total"]["fresh_calls"], "stops": stops, "refused": usage["total"]["refused"],
            "seconds": seconds, "unmapped": unmapped, "stopped": stopped}


def report(entries: list[str]) -> list[dict[str, Any]]:
    from .adapt import entry_dir, load_output

    rows = []
    for mim in entries:
        out = load_output(SYSTEM, mim)
        if not out:
            continue
        m = out["meta"]
        blocks = out["blocks"]
        chars = sum(len(b["text"]) for b in blocks)
        uncited = sum(len(b["text"]) for b in blocks if not b["pmids"])
        usage = ledger_summary(read_ledger(entry_dir(SYSTEM, mim) / "ledger.jsonl"), f"{SYSTEM}/{mim}")
        rows.append({
            "mim": mim, "stopped": out["stopped"], "blocks": len(blocks), "chars": chars,
            "uncited_share": round(uncited / chars, 3) if chars else None,
            "calls": usage["total"]["fresh_calls"], "stops": usage["total"]["stops"],
            "refused": usage["total"]["refused"],
            "calls_by_stage": {s: usage["stages"].get(s, {}).get("fresh_calls", 0) for s in STAGE_NAMES},
            "tokens_in": usage["total"]["input_tokens"], "tokens_out": usage["total"]["output_tokens"],
            "cost_usd": usage["total"]["cost_usd"], "seconds": m.get("seconds"),
            "stage_seconds": m.get("stage_seconds"),
            "wikipedia_pages": [(p.get("title") or p.get("url"), p.get("ok")) for p in m.get("wikipedia_pages") or []],
            "unmapped_markers": m.get("unmapped_markers"),
        })
    return rows


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="STORM as released, Experiment B")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("smoke")
    r = sub.add_parser("run")
    r.add_argument("entries", nargs="*")
    r.add_argument("--first", type=int, help="the first N entries of the seeded order")
    r.add_argument("--budget", type=int, default=800, help="stop before an entry once this many calls are spent")
    r.add_argument("--per-entry", type=int, default=70, help="projected calls per entry, for the budget check")
    r.add_argument("--force", action="store_true")
    rep = sub.add_parser("report")
    rep.add_argument("entries", nargs="*")
    args = p.parse_args(argv)

    from .corpus import entry_order

    if args.cmd == "smoke":
        print(json.dumps(smoke(), indent=1))
    elif args.cmd == "run":
        entries = args.entries or entry_order()[: args.first or 10]
        for mim in entries:
            used = budget_used()
            if used + args.per_entry > args.budget:
                print(json.dumps({"mim": mim, "skipped": f"budget: {used} calls used, cap {args.budget}"}))
                break
            print(json.dumps(run_entry(mim, force=args.force)), flush=True)
        print(json.dumps({"budget_used": budget_used()}))
    else:
        print(json.dumps(report(args.entries or entry_order()[:10]), indent=1))


if __name__ == "__main__":
    main()
