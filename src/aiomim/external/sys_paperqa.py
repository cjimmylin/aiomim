"""PaperQA2 (`paper-qa` from PyPI) as released, for Experiment B (docs/experiments-round2.md, section B).

The package runs in its own environment `.venvs/paperqa/` as a subprocess (`paperqa_runner.py`), against the
local adapter (`shim.ShimServer`, one per entry, concurrency 3) for every model role and for embeddings. Its
environment is built from scratch (dummy key, telemetry off, no hub downloads) and its outbound proxy is a
local logger that refuses and records every connection to a non-local host (`outbound.log`), so any attempt
to reach an outside service is visible and fails.

Per entry: export the corpus, ask the six section questions (`tasks.section_questions`) one query each with
`Docs.aquery`, split each answer at blank lines into blocks (text unedited), map the answer's citations
(PaperQA's `(<docname> chunk n)` parentheticals, docname `<Surname><Year>-<PMID>`) to PubMed ids, save with
`adapt.save_output` under system `paperqa`.

    PYTHONPATH=src python -m aiomim.external.sys_paperqa probe              # one tiny call + one embedding
    PYTHONPATH=src python -m aiomim.external.sys_paperqa run 621313 ...     # entries (default: first 10)
    PYTHONPATH=src python -m aiomim.external.sys_paperqa run --force 621313 # redo (the adapter cache makes it free)
    PYTHONPATH=src python -m aiomim.external.score score --system paperqa --no-baselines
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

SYSTEM = "paperqa"
SYSTEM_POOLED = "paperqa_pooled"     # the same run with the adapter's opt-in pooling of long embedding inputs
POOLED_SETTING = {
    "setting": "embedding input length (adapter /v1/embeddings, long_inputs='pool')",
    "default": "bge-small-en-v1.5 truncates every input at 512 tokens, so a default 5,000-character PaperQA chunk "
               "(about 1,100-1,300 tokens) is embedded from its first ~510 tokens only",
    "value": "an input over 510 tokens (model tokenizer, without [CLS]/[SEP]) is split into consecutive "
             "non-overlapping windows of at most 510 tokens; each is embedded, the vectors are averaged "
             "(unweighted) and re-normalised; shorter inputs are embedded exactly as before",
    "reason": "the 512-token cut is an artefact of the shared local embedding model, not of PaperQA2 (whose "
              "default embedding, text-embedding-3-small, takes 8,191 tokens); pooling embeds the whole chunk",
}
PACKAGE = "paper-qa"
ROOT = Path(__file__).resolve().parents[3]
VENV_PY = ROOT / ".venvs" / "paperqa" / "bin" / "python"
RUNNER = Path(__file__).with_name("paperqa_runner.py")
MAX_CONCURRENCY = 3
KEY_PACKAGES = ("paper-qa", "paper-qa-pypdf", "fhlmi", "fhaviary", "litellm", "openai", "tantivy", "numpy",
                "pydantic", "tiktoken")

# A parenthetical as PaperQA writes it after replacing its context ids with chunk names.
_PAREN = re.compile(r"\([^()]*\)")
_KEY = re.compile(r"\bpqac-[a-zA-Z0-9]{8}\b")   # PaperQA's context key (paperqa.utils.get_citation_ids)


# --------------------------------------------------------------------------- #
# Citation mapping and output conversion (no network, no model; unit-tested)
# --------------------------------------------------------------------------- #


def map_paragraph(text: str, docname_to_pmid: dict[str, str],
                  key_to_pmid: dict[str, str] | None = None) -> tuple[list[str], list[str]]:
    """(supplied PMIDs the paragraph's citations map to, raw citation markers).

    A citation is a parenthetical naming one or more of the entry's documents (PaperQA's formatted
    answer replaces `(pqac-xxxxxxxx, ...)` keys by `(<docname> chunk n, ...)`). PaperQA replaces keys
    only inside parentheticals; a context key the model wrote outside one stays in the text as
    `pqac-xxxxxxxx` and is mapped through the session's own contexts (`key_to_pmid`). Only documents
    of the entry map; other parentheticals are ignored."""
    pmids: list[str] = []
    raw: list[str] = []
    names = sorted(docname_to_pmid, key=len, reverse=True)
    for m in _PAREN.finditer(text):
        inner = m.group(0)
        hit = [docname_to_pmid[n] for n in names if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", inner)]
        if hit:
            raw.append(inner)
            pmids.extend(hit)
    for key in _KEY.findall(text):
        if key_to_pmid and key in key_to_pmid:
            raw.append(key)
            pmids.append(key_to_pmid[key])
    return list(dict.fromkeys(pmids)), raw


def answer_blocks(section: str, answer: str, docname_to_pmid: dict[str, str],
                  key_to_pmid: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """One block per paragraph of the answer (split at blank lines; text otherwise unedited)."""
    blocks = []
    for para in re.split(r"\n\s*\n", answer or ""):
        if not para.strip():
            continue
        pmids, raw = map_paragraph(para, docname_to_pmid, key_to_pmid)
        blocks.append({"section": section, "text": para.strip(), "pmids": pmids, "citations": raw})
    return blocks


def convert(mim: str, result: dict[str, Any], supplied: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Runner result -> (blocks, per-question notes). Docnames map to PMIDs through the runner's own
    record of the documents it added (and only to supplied PMIDs)."""
    docname_to_pmid = {p["docname"]: p["pmid"] for p in result.get("papers", [])
                       if p.get("docname") and p["pmid"] in supplied}
    blocks: list[dict[str, Any]] = []
    notes = []
    for a in result.get("answers", []):
        key_to_pmid = {c["id"]: docname_to_pmid[c["docname"]] for c in a.get("contexts") or []
                       if c.get("docname") in docname_to_pmid}
        b = answer_blocks(a["section"], a.get("answer") or "", docname_to_pmid, key_to_pmid)
        blocks.extend(b)
        notes.append({"key": a["key"], "blocks": len(b), "chars": sum(len(x["text"]) for x in b),
                      "cannot_answer": "I cannot answer" in (a.get("answer") or ""),
                      "bare_keys": len(_KEY.findall(a.get("answer") or "")),
                      "contexts": len(a.get("contexts") or []), "has_successful_answer": a.get("has_successful_answer")})
    return blocks, {"questions": notes}


# --------------------------------------------------------------------------- #
# Outbound logger: the subprocess's only proxy
# --------------------------------------------------------------------------- #


class OutboundLogger:
    """A local 'proxy' that answers every request with 403 and records its first line."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.attempts: list[str] = []
        logger = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    line = self.rfile.readline(4096).decode("latin-1").strip()
                except Exception:  # noqa: BLE001
                    line = "<unreadable>"
                logger.attempts.append(line)
                with logger.log_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "request": line}) + "\n")
                try:
                    self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                except Exception:  # noqa: BLE001
                    pass

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> OutboundLogger:
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()


def subprocess_env(base_url: str, proxy_url: str) -> dict[str, str]:
    """Built from scratch: no provider key or endpoint from the parent environment."""
    env = {
        "PATH": f"{VENV_PY.parent}:/usr/local/bin:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/root"), "LANG": "C.UTF-8", "VIRTUAL_ENV": str(VENV_PY.parent.parent),
        "OPENAI_API_KEY": "sk-local-dummy", "OPENAI_BASE_URL": base_url, "OPENAI_API_BASE": base_url,
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "HTTP_PROXY": proxy_url, "HTTPS_PROXY": proxy_url, "ALL_PROXY": proxy_url,
        "http_proxy": proxy_url, "https_proxy": proxy_url, "all_proxy": proxy_url,
        "LITELLM_LOCAL_MODEL_COST_MAP": "True", "LITELLM_TELEMETRY": "False",
        "ANONYMIZED_TELEMETRY": "False", "DO_NOT_TRACK": "1", "OTEL_SDK_DISABLED": "true",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "TIKTOKEN_CACHE_DIR": str(ROOT / "data" / "cache" / "tiktoken"),
        "PQA_INDEX_DISABLE_PROGRESS_BAR": "1",
    }
    return env


def package_versions() -> dict[str, str]:
    out = subprocess.run([str(VENV_PY), "-I", "-c",
                          "import json, importlib.metadata as m, sys\n"
                          f"names={list(KEY_PACKAGES)!r}\n"
                          "print(json.dumps({'python': sys.version.split()[0], "
                          "**{n: m.version(n) for n in names}}))"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def changed_settings() -> list[dict[str, Any]]:
    out = subprocess.run([str(VENV_PY), "-I", str(RUNNER), "--print-defaults"], capture_output=True, text=True,
                         check=True, env={"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/root"),
                                          "LITELLM_LOCAL_MODEL_COST_MAP": "True", "NO_PROXY": "*",
                                          "HTTPS_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9"})
    return json.loads(out.stdout)


def _ledger_rows(path: Path, tag: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("tag") == tag or str(r.get("tag", "")).startswith(tag + "/"):
            rows.append(r)
    return rows


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #


def probe() -> dict[str, Any]:
    from .adapt import entry_dir
    from .shim import ShimServer

    folder = entry_dir(SYSTEM, "_probe")
    folder.mkdir(parents=True, exist_ok=True)
    tag = f"{SYSTEM}/probe"
    with ShimServer(tag=tag, ledger=folder / "ledger.jsonl", max_concurrency=MAX_CONCURRENCY) as base_url, \
            OutboundLogger(folder / "outbound.log") as proxy:
        proc = subprocess.run([str(VENV_PY), "-I", str(RUNNER), "--probe", "--base-url", base_url,
                               "--out", str(folder / "probe.json"), "--log", str(folder / "paperqa.log")],
                              env=subprocess_env(base_url, proxy.url), capture_output=True, text=True, timeout=1800)
        attempts = list(proxy.attempts)
    (folder / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "outbound_attempts": attempts,
            "ledger": [{k: r.get(k) for k in ("endpoint", "status", "cached", "model_calls", "requested_model",
                                              "ignored_params", "rendering", "error")}
                       for r in _ledger_rows(folder / "ledger.jsonl", tag)],
            "stderr_tail": proc.stderr[-2000:]}


def run_entry(mim: str, *, force: bool = False, pooled: bool = False) -> dict[str, Any]:
    from .adapt import entry_dir, load_output, save_output
    from .corpus import export_entry
    from .embed import LocalEmbedder
    from .shim import Shim, ShimServer
    from .tasks import section_questions

    SYSTEM = SYSTEM_POOLED if pooled else globals()["SYSTEM"]  # noqa: N806

    folder = entry_dir(SYSTEM, mim)
    if not force and load_output(SYSTEM, mim) is not None:
        return {"mim": mim, "skipped": "output.json exists"}
    corpus = export_entry(mim, folder / "corpus")
    questions = section_questions(json.loads((folder / "corpus" / "entry.json").read_text(encoding="utf-8"))["title"])
    (folder / "questions.json").write_text(json.dumps(questions, indent=1), encoding="utf-8")
    tag = f"{SYSTEM}/{mim}"
    ledger = folder / "ledger.jsonl"
    n_before = len(_ledger_rows(ledger, tag))
    result_path = folder / "paperqa_result.json"
    started = time.time()
    shim = Shim(tag=tag, ledger=ledger, max_concurrency=MAX_CONCURRENCY,
                embedder=LocalEmbedder(long_inputs="pool") if pooled else None)
    with ShimServer(shim=shim) as base_url, \
            OutboundLogger(folder / "outbound.log") as proxy:
        proc = subprocess.run([str(VENV_PY), "-I", str(RUNNER), "--base-url", base_url,
                               "--corpus", str(folder / "corpus"), "--questions", str(folder / "questions.json"),
                               "--out", str(result_path), "--log", str(folder / "paperqa.log")],
                              env=subprocess_env(base_url, proxy.url), capture_output=True, text=True,
                              timeout=7000)
        attempts = list(proxy.attempts)
    seconds = round(time.time() - started, 1)
    (folder / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    rows = _ledger_rows(ledger, tag)[n_before:]
    chat = [r for r in rows if r.get("endpoint") == "/v1/chat/completions"]
    refused = [r for r in chat if r.get("status") == 400]
    errors = [r for r in chat if r.get("status") not in (200, 400)]
    stops = sum(1 for r in chat if r.get("safety_stop"))
    if proc.returncode != 0:
        if any(r.get("status") == 503 for r in chat):
            raise SystemExit(f"[{mim}] adapter reported an exhausted usage limit (503): stop the run")
        raise RuntimeError(f"[{mim}] runner failed ({proc.returncode}): {proc.stderr[-3000:]}")
    if refused:
        raise RuntimeError(f"[{mim}] the adapter refused {len(refused)} request(s) (HTTP 400): "
                           f"{[r.get('error') for r in refused][:3]} -- fix the configuration")
    if attempts:
        raise RuntimeError(f"[{mim}] outbound connection attempts to non-local hosts: {attempts[:5]}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    supplied = set(corpus.pmids)
    blocks, notes = convert(mim, result, supplied)
    versions = package_versions()
    output = {
        "system": SYSTEM, "mim": mim, "blocks": blocks,
        "stopped": None if blocks else (f"safety stop on {stops} of {len(chat)} model replies; no answer text"
                                        if stops else "no answer text"),
        "meta": {
            "package": PACKAGE, "version": result.get("version"), "versions": versions,
            "entry_point": "paperqa.Docs.aadd (one document per paper) + Docs.aquery (one per question)",
            "settings_changed": changed_settings() + ([POOLED_SETTING] if pooled else []),
            # fresh model calls ever made for this entry (all runs; a re-run is served from the cache)
            "calls": sum(int(r.get("model_calls") or 1) for r in _ledger_rows(ledger, tag)
                         if r.get("endpoint") == "/v1/chat/completions" and r.get("status") == 200
                         and not r.get("cached")),
            "chat_requests_this_run": len(chat), "cached_requests_this_run": sum(1 for r in chat if r.get("cached")),
            "embedding_requests": sum(1 for r in rows if r.get("endpoint") == "/v1/embeddings"),
            "refused": len(refused), "errors": len(errors), "stops": stops, "seconds": seconds,
            "outbound_attempts": len(attempts), "papers": result.get("papers"), "chunks": result.get("chunks"),
            **notes, "tag": tag, "ledgers": [str(ledger.relative_to(ROOT))],
        },
    }
    save_output(output)
    return {"mim": mim, "blocks": len(blocks), "cited_blocks": sum(1 for b in blocks if b["pmids"]),
            "calls": output["meta"]["calls"], "requests": len(chat), "stops": stops, "seconds": seconds}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.external.sys_paperqa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    sub.add_parser("versions")
    r = sub.add_parser("run")
    r.add_argument("entries", nargs="*")
    r.add_argument("--force", action="store_true")
    r.add_argument("--pooled-embeddings", action="store_true",
                   help=f"adapter pools long embedding inputs; saved as system {SYSTEM_POOLED}")
    args = ap.parse_args(argv)
    if args.cmd == "probe":
        print(json.dumps(probe(), indent=1))
    elif args.cmd == "versions":
        print(json.dumps(package_versions(), indent=1))
    else:
        from .corpus import main_set

        for mim in args.entries or main_set():
            print(json.dumps(run_entry(mim, force=args.force, pooled=args.pooled_embeddings)), flush=True)


if __name__ == "__main__":
    main()
