"""Microsoft GraphRAG (`graphrag` on PyPI) as released, for Experiment B (docs/experiments-round2.md, section B).

Runs in the project environment. The package itself runs in its own virtual environment
(`.venvs/graphrag/`) as subprocesses: its own command line `graphrag init` / `graphrag index`, and for
queries `graphrag_runner.py`, which calls the same functions `graphrag query` calls (so that the context
tables behind the answer's data references can be kept).

Per entry and indexing method:

1. export the entry's supplied papers (`corpus.export_entry`) and copy the `<pmid>.txt` files into the
   GraphRAG project's `input/` folder (GraphRAG's text reader names each document after its file);
2. `graphrag init`, keeping the generated `settings.yaml` as `settings.generated.yaml`; then change only
   what the experiment requires (`configure`; every change is listed in `meta.settings_changed`);
3. `graphrag index --method standard|fast` behind the adapter (one adapter per entry, concurrency 3);
4. the six section questions (`tasks.section_questions`) with local search (system `graphrag`, or
   `graphrag_fast` on the fast index) and, as a second priority, global search (system `graphrag_global`);
5. each answer split at blank lines into blocks, text unedited; each block's `[Data: ...]` references
   mapped to PubMed ids through the index tables (`map_block`), and saved with `adapt.save_output`.

    PYTHONPATH=src python -m aiomim.external.sys_graphrag smoke
    PYTHONPATH=src python -m aiomim.external.sys_graphrag run 621313 [--method standard|fast] [--search local|global]
    PYTHONPATH=src python -m aiomim.external.sys_graphrag budget
    PYTHONPATH=src python -m aiomim.external.sys_graphrag report 621313 ...
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .adapt import entry_dir, save_output
from .tasks import section_questions

PACKAGE = "graphrag"
REPO = Path(__file__).resolve().parents[3]
VENV = REPO / ".venvs" / "graphrag"
RUNNER = Path(__file__).with_name("graphrag_runner.py")
TIKTOKEN_DIR = REPO / "data" / "cache" / "tiktoken"

SYSTEMS = {("standard", "local"): "graphrag", ("fast", "local"): "graphrag_fast",
           ("standard", "global"): "graphrag_global", ("fast", "global"): "graphrag_fast_global"}
INDEX_SYSTEM = {"standard": "graphrag", "fast": "graphrag_fast"}

CHAT_MODEL = "claude-opus-5-5"
EMBED_MODEL = "bge-small-en-v1.5"
DUMMY_KEY = "sk-local-dummy"
CONCURRENCY = 3            # the adapter's cap, and GraphRAG's own `concurrent_requests`
TIMEOUT_S = 1800           # client timeout per request (a call can take minutes)
RETRIES = 2                # GraphRAG's retry count (its validator requires > 1); adapter retries itself
BUDGET = 1000              # model calls through the adapter, all GraphRAG runs together, pilot included
CONNECTIVITY_TEST = "This is an LLM connectivity test. Say Hello World"   # graphrag/index/validate_config.py

#: Per-workflow copies of the one chat model, identical except for the ledger tag header, so the
#: adapter's ledger can report calls, tokens and seconds by workflow step. (setting key, model id)
STEP_MODELS = {
    "extract_graph": "extract_graph",
    "summarize_descriptions": "summarize_descriptions",
    "community_reports": "community_reports",
    "local_search": "local_search",
    "global_search": "global_search",
}
TAG_HEADER = "X-Aiomim-Tag"


# --------------------------------------------------------------------------- #
# Settings: the generated settings.yaml, changed only where the experiment requires
# --------------------------------------------------------------------------- #


def _model_overrides(kind: str, step: str) -> dict[str, Any]:
    call_args: dict[str, Any] = {"timeout": TIMEOUT_S, "max_retries": 0,
                                 "extra_headers": {TAG_HEADER: "${AIOMIM_TAG}/" + step}}
    return {"model": CHAT_MODEL if kind == "chat" else EMBED_MODEL, "api_base": "${GRAPHRAG_API_BASE}",
            "call_args": call_args}


def configure(generated: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(settings, changes): the generated settings with the experiment's changes, and the list of
    changes for `meta.settings_changed`. Pure; does not touch the prompts or any workflow parameter."""
    s = copy.deepcopy(generated)
    changes: list[dict[str, Any]] = []

    def change(setting: str, default: Any, value: Any, reason: str) -> None:
        changes.append({"setting": setting, "default": default, "value": value, "reason": reason})

    chat = s["completion_models"]["default_completion_model"]
    emb = s["embedding_models"]["default_embedding_model"]
    retry_default = chat.get("retry")

    for name, model, kind in (("default_completion_model", chat, "chat"), ("default_embedding_model", emb, "embed")):
        prefix = ("completion_models." if kind == "chat" else "embedding_models.") + name
        over = _model_overrides(kind, "connectivity" if kind == "chat" else "embeddings")
        change(f"{prefix}.model", model.get("model"), f"{model.get('model_provider')}/{over['model']}",
               "the project's one model through the local adapter" if kind == "chat" else
               "the adapter's local embedding model (BAAI/bge-small-en-v1.5, 384 dimensions), the same for all systems")
        change(f"{prefix}.api_base", "(none: the provider's public endpoint)", "${GRAPHRAG_API_BASE} = "
               "http://127.0.0.1:<port>/v1", "the local adapter (127.0.0.1 only)")
        change(f"{prefix}.api_key", "${GRAPHRAG_API_KEY} (.env: <API_KEY>)", DUMMY_KEY + " (in .env)",
               "dummy key; the adapter needs none and no real key is passed to the package")
        change(f"{prefix}.call_args", {}, {"timeout": TIMEOUT_S, "max_retries": 0,
                                           "extra_headers": {TAG_HEADER: "<system>/<mim>/<step>"}},
               "client timeout 1800 s (a call can take minutes); the OpenAI client's own retries off "
               "(GraphRAG's retry and the adapter's retry remain); ledger tag header (bookkeeping only)")
        model.update(over)
        model["retry"] = {"type": "exponential_backoff", "max_retries": RETRIES}
        change(f"{prefix}.retry", retry_default, model["retry"],
               "few client retries: the adapter already retries transient failures with back-off; "
               "max_retries must be > 1 for this retry type")

    # One copy of the chat model per workflow step that calls it (bookkeeping only: identical requests).
    for setting, step in STEP_MODELS.items():
        model_id = f"completion_{step}"
        m = copy.deepcopy(chat)
        m["call_args"]["extra_headers"] = {TAG_HEADER: "${AIOMIM_TAG}/" + step}
        s["completion_models"][model_id] = m
        section = s.setdefault(setting, {})
        old = section.get("completion_model_id", "default_completion_model")
        section["completion_model_id"] = model_id
        change(f"{setting}.completion_model_id", old, model_id,
               "a copy of default_completion_model that differs only in the ledger tag header "
               f"(<system>/<mim>/{step}), to count calls by workflow step; requests are otherwise identical")

    old = s.get("concurrent_requests", 25)
    s["concurrent_requests"] = CONCURRENCY
    change("concurrent_requests", old, CONCURRENCY, "the adapter's concurrency cap (3), so GraphRAG does not flood it")
    return s, changes


ENV_CHANGES = [
    {"setting": "input/ (input_storage.base_dir, input.type text)", "default": "(empty folder)",
     "value": "the entry's exported papers, one <pmid>.txt per paper",
     "reason": "the corpus: exactly the supplied papers; GraphRAG's text reader titles each document by its "
               "file name, which maps it back to the PubMed id"},
    {"setting": "environment", "default": "(inherited)",
     "value": "fresh environment: no proxy variables, no provider keys; LITELLM_LOCAL_MODEL_COST_MAP=True, "
              "LITELLM_TELEMETRY=False, ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1, OTEL_SDK_DISABLED=true, "
              "HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=data/cache/tiktoken",
     "reason": "telemetry off, nothing reaches an outside service; tiktoken encodings filled once beforehand"},
]


def _subprocess_env(base_url: str, tag: str) -> dict[str, str]:
    """Built from scratch: no provider keys and no proxy, so the package can reach only 127.0.0.1."""
    local = "127.0.0.1,localhost"
    return {
        "PATH": f"{VENV / 'bin'}:/usr/local/bin:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/root"),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "VIRTUAL_ENV": str(VENV), "PYTHONNOUSERSITE": "1",
        "GRAPHRAG_API_KEY": DUMMY_KEY, "GRAPHRAG_API_BASE": base_url, "AIOMIM_TAG": tag,
        "OPENAI_API_KEY": DUMMY_KEY, "OPENAI_BASE_URL": base_url, "OPENAI_API_BASE": base_url,
        "NO_PROXY": local, "no_proxy": local,
        "LITELLM_LOCAL_MODEL_COST_MAP": "True", "LITELLM_TELEMETRY": "False",
        "ANONYMIZED_TELEMETRY": "False", "DO_NOT_TRACK": "1", "OTEL_SDK_DISABLED": "true",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TIKTOKEN_CACHE_DIR": str(TIKTOKEN_DIR),
    }


def versions() -> dict[str, str]:
    code = ("import importlib.metadata as m, json, sys\n"
            "names = ['graphrag','graphrag-llm','graphrag-cache','graphrag-chunking','graphrag-input',"
            "'graphrag-storage','graphrag-vectors','graphrag-common','litellm','openai','lancedb','pandas',"
            "'networkx','graspologic-native','tiktoken','pydantic','numpy','pyarrow']\n"
            "out = {'python': sys.version.split()[0]}\n"
            "for n in names:\n"
            "    try: out[n] = m.version(n)\n"
            "    except Exception: out[n] = None\n"
            "print(json.dumps(out))")
    r = subprocess.run([str(VENV / "bin" / "python"), "-I", "-c", code], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


# --------------------------------------------------------------------------- #
# Project preparation
# --------------------------------------------------------------------------- #


def prepare_project(folder: Path, texts: dict[str, str]) -> tuple[Path, list[dict[str, Any]]]:
    """Create (or reuse) the GraphRAG project under `folder/project`; returns (root, settings changes)."""
    import yaml

    root = folder / "project"
    generated = root / "settings.generated.yaml"
    if not generated.exists():
        root.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([str(VENV / "bin" / "graphrag"), "init", "--root", str(root), "--force"],
                           input="\n\n", capture_output=True, text=True,
                           env=_subprocess_env("http://127.0.0.1:9/v1", "init"))
        if r.returncode != 0 or not (root / "settings.yaml").exists():
            raise RuntimeError(f"graphrag init failed: {r.stdout[-2000:]} {r.stderr[-2000:]}")
        shutil.copy(root / "settings.yaml", generated)
        shutil.copy(root / ".env", root / ".env.generated")
    settings, changes = configure(yaml.safe_load(generated.read_text(encoding="utf-8")))
    (root / "settings.yaml").write_text(
        "# Generated by `graphrag init` (see settings.generated.yaml), changed by aiomim.external.sys_graphrag."
        "\n# Every change is listed in output.json meta.settings_changed.\n"
        + yaml.safe_dump(settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (root / ".env").write_text(f"GRAPHRAG_API_KEY={DUMMY_KEY}\n", encoding="utf-8")
    inp = root / "input"
    inp.mkdir(exist_ok=True)
    for old in inp.glob("*"):
        if old.stem not in texts:
            old.unlink()
    for pmid, text in texts.items():
        p = inp / f"{pmid}.txt"
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
    return root, changes + ENV_CHANGES


# --------------------------------------------------------------------------- #
# Budget
# --------------------------------------------------------------------------- #


def ledger_rows(paths: list[Path] | None = None) -> list[dict[str, Any]]:
    if paths is None:
        paths = [p for d in (entry_dir("x", "0").parents[1]).glob("graphrag*") for p in d.rglob("ledger*.jsonl")]
    rows = []
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def calls_spent(rows: list[dict[str, Any]] | None = None) -> int:
    """Model calls made through the adapter by every GraphRAG run so far (fresh replies; JSON re-asks counted)."""
    rows = ledger_rows() if rows is None else rows
    return sum(int(r.get("model_calls") or 0) for r in rows
               if r.get("endpoint") == "/v1/chat/completions" and r.get("status") == 200 and not r.get("cached"))


class BudgetGuard:
    """Stops the subprocess if the calls of all GraphRAG runs would pass the cap."""

    def __init__(self, shim, before: int, cap: int = BUDGET):
        self.shim, self.before, self.cap = shim, before, cap
        self.tripped = False

    def watch(self, proc: subprocess.Popen) -> threading.Thread:
        def run() -> None:
            while proc.poll() is None:
                if self.before + self.shim.stats["model_calls"] >= self.cap:
                    self.tripped = True
                    proc.terminate()
                    return
                time.sleep(2)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t


# --------------------------------------------------------------------------- #
# Running the package
# --------------------------------------------------------------------------- #


def _run_sub(cmd: list[str], env: dict[str, str], log: Path, guard: BudgetGuard | None) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n===== {time.strftime('%Y-%m-%dT%H:%M:%S')} {' '.join(cmd)}\n")
        fh.flush()
        proc = subprocess.Popen(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT, cwd=str(log.parent))
        if guard:
            guard.watch(proc)
        return proc.wait()


def index_entry(mim: str, method: str = "standard") -> dict[str, Any]:
    from .corpus import export_entry

    system = INDEX_SYSTEM[method]
    folder = entry_dir(system, mim)
    corpus = export_entry(mim, folder / "corpus")
    root, _ = prepare_project(folder, corpus.texts)
    status_path = folder / "index_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"attempts": []}
    if status.get("ok"):
        return status
    before = calls_spent()
    if before >= BUDGET:
        raise RuntimeError(f"budget spent ({before} calls)")
    started = time.time()
    with _adapter(f"{system}/{mim}", folder / "ledger.jsonl") as (base, srv):
        guard = BudgetGuard(srv.shim, before)
        code = _run_sub([str(VENV / "bin" / "graphrag"), "index", "--root", str(root), "--method", method],
                        _subprocess_env(base, f"{system}/{mim}"), folder / "index.log", guard)
        server_stats = dict(srv.shim.stats)
    attempt = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "exit_code": code,
               "seconds": round(time.time() - started, 1), "adapter": server_stats,
               "budget_stop": bool(guard and guard.tripped)}
    status["attempts"].append(attempt)
    status["ok"] = code == 0 and (root / "output" / "stats.json").exists()
    status["method"] = method
    status_path.write_text(json.dumps(status, indent=1), encoding="utf-8")
    return status


@contextlib.contextmanager
def _adapter(tag: str, ledger: Path):
    """The adapter for one entry (its own ledger and tag); yields (base_url, server)."""
    from .shim import ShimServer

    srv = ShimServer(tag=tag, ledger=ledger, max_concurrency=CONCURRENCY)
    base = srv.start()
    try:
        yield base, srv
    finally:
        srv.stop()


def export_tables(index_folder: Path) -> dict[str, Any]:
    out = index_folder / "tables.json"
    r = subprocess.run([str(VENV / "bin" / "python"), "-I", str(RUNNER), "export", str(index_folder / "project"),
                        str(out)], capture_output=True, text=True, env=_subprocess_env("http://127.0.0.1:9/v1", "x"))
    if r.returncode != 0:
        raise RuntimeError(f"export failed: {r.stderr[-3000:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def query_entry(mim: str, method: str = "standard", search: str = "local") -> dict[str, Any]:
    from .corpus import load_entry

    system = SYSTEMS[(method, search)]
    index_folder = entry_dir(INDEX_SYSTEM[method], mim)
    folder = entry_dir(system, mim)
    folder.mkdir(parents=True, exist_ok=True)
    corpus = load_entry(mim)
    questions = section_questions(corpus.title)
    qpath = folder / "questions.json"
    qpath.write_text(json.dumps(questions, indent=1, ensure_ascii=False), encoding="utf-8")
    apath = folder / f"answers.{search}.json"
    before = calls_spent()
    if before >= BUDGET:
        raise RuntimeError(f"budget spent ({before} calls)")
    started = time.time()
    with _adapter(f"{system}/{mim}", folder / "ledger.jsonl") as (base, srv):
        guard = BudgetGuard(srv.shim, before)
        code = _run_sub([str(VENV / "bin" / "python"), "-I", str(RUNNER), "query", str(index_folder / "project"),
                         search, str(qpath), str(apath)], _subprocess_env(base, f"{system}/{mim}"),
                        folder / "query.log", guard)
        stats = dict(srv.shim.stats)
    return {"exit_code": code, "seconds": round(time.time() - started, 1), "adapter": stats,
            "budget_stop": bool(guard and guard.tripped)}


# --------------------------------------------------------------------------- #
# Data references -> PubMed ids
# --------------------------------------------------------------------------- #

_DATA_REF = re.compile(r"\[Data:[^\[\]]*\]", re.IGNORECASE)
_KIND = re.compile(r"(Sources|Source|Entities|Entity|Relationships|Relationship|Reports|Report|Claims|Claim)"
                   r"\s*\(([^()]*)\)", re.IGNORECASE)
_CANON = {"source": "sources", "entity": "entities", "relationship": "relationships", "report": "reports",
          "claim": "claims"}


def parse_refs(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """(raw markers, {kind: [record ids]}) of one block. Kinds: sources, entities, relationships, reports, claims.
    '+more' is dropped (it names no record)."""
    raw: list[str] = []
    ids: dict[str, list[str]] = defaultdict(list)
    for m in _DATA_REF.finditer(text):
        raw.append(m.group(0))
        for k in _KIND.finditer(m.group(0)):
            kind = k.group(1).lower()
            kind = _CANON.get(kind.rstrip("s"), _CANON.get(kind, kind))
            for tok in re.split(r"[,\s]+", k.group(2)):
                tok = tok.strip()
                if tok.isdigit():
                    ids[kind].append(tok)
    return raw, {k: list(dict.fromkeys(v)) for k, v in ids.items()}


class IndexMap:
    """The index tables, as lookups from the record ids a query shows the model to PubMed ids."""

    def __init__(self, tables: dict[str, Any]):
        docs = tables.get("documents") or []
        self.doc_pmid = {d["id"]: _pmid_of(d["title"]) for d in docs}
        self.unit_doc = {u["id"]: u.get("document_id") for u in tables.get("text_units") or []}
        self.unit_by_short = {str(u["human_readable_id"]): u["id"] for u in tables.get("text_units") or []}
        ents = tables.get("entities") or []
        self.entity_units = {e["id"]: list(e.get("text_unit_ids") or []) for e in ents}
        self.entity_by_short = {str(e["human_readable_id"]): e["id"] for e in ents}
        rels = tables.get("relationships") or []
        self.rel_by_short = {str(r["human_readable_id"]): list(r.get("text_unit_ids") or []) for r in rels}
        self.community_entities: dict[str, list[str]] = {}
        for c in tables.get("communities") or []:
            self.community_entities[str(c["community"])] = list(c.get("entity_ids") or [])

    def units_to_pmids(self, units: list[str]) -> list[str]:
        out = []
        for u in units:
            p = self.doc_pmid.get(self.unit_doc.get(u))
            if p:
                out.append(p)
        return list(dict.fromkeys(out))

    def pmids(self, kind: str, short_id: str) -> list[str]:
        if kind == "sources":
            u = self.unit_by_short.get(short_id)
            return self.units_to_pmids([u]) if u else []
        if kind == "entities":
            e = self.entity_by_short.get(short_id)
            return self.units_to_pmids(self.entity_units.get(e, [])) if e else []
        if kind == "relationships":
            return self.units_to_pmids(self.rel_by_short.get(short_id, []))
        if kind == "reports":
            units = [u for e in self.community_entities.get(short_id, []) for u in self.entity_units.get(e, [])]
            return self.units_to_pmids(units)
        return []


def _pmid_of(title: Any) -> str | None:
    m = re.fullmatch(r"(\d{5,9})\.txt", str(title or ""))
    return m.group(1) if m else None


def context_ids(context: dict[str, Any] | None) -> dict[str, set[str]]:
    """Record ids per kind that the query actually put in front of the model (its context tables)."""
    out: dict[str, set[str]] = {}
    for key, rows in (context or {}).items():
        kind = _CANON.get(key.lower().rstrip("s"), key.lower())
        if isinstance(rows, list):
            out[kind] = {str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id") not in (None, "")}
    return out


def map_block(text: str, imap: IndexMap, shown: dict[str, set[str]]) -> dict[str, Any]:
    """Map one block's data references to PubMed ids. A record id is mapped only if the query showed that
    record to the model (it is in the context table of that kind); others are counted as not shown."""
    raw, refs = parse_refs(text)
    by_kind: dict[str, list[str]] = {}
    not_shown: dict[str, list[str]] = {}
    for kind, ids in refs.items():
        got: list[str] = []
        for i in ids:
            if i not in shown.get(kind, set()):
                not_shown.setdefault(kind, []).append(i)
                continue
            got.extend(imap.pmids(kind, i))
        by_kind[kind] = list(dict.fromkeys(got))
    pmids = list(dict.fromkeys(p for k in ("sources", "entities", "relationships", "reports")
                               for p in by_kind.get(k, [])))
    if by_kind.get("sources"):
        basis = "sources"
    elif by_kind.get("entities") or by_kind.get("relationships"):
        basis = "entities_relationships"
    elif by_kind.get("reports"):
        basis = "reports_only"
    else:
        basis = "none"
    return {"pmids": pmids, "citations": raw, "refs": refs, "by_kind": by_kind, "not_shown": not_shown,
            "basis": basis}


def split_paragraphs(response: str) -> list[str]:
    """Paragraphs at blank lines, text unedited. A paragraph that consists only of data references (GraphRAG
    often puts the `[Data: ...]` line after a list, separated by a blank line) belongs to the paragraph before
    it and is joined to it with the blank line it had; nothing else is merged."""
    parts = re.split(r"(\n[ \t]*\n)", response or "")
    out: list[str] = []
    sep = ""
    for i, piece in enumerate(parts):
        if i % 2:
            sep = piece
            continue
        if not piece.strip():
            continue
        if out and _DATA_REF.sub("", piece).strip() == "":
            out[-1] = out[-1] + sep + piece
        else:
            out.append(piece)
    return [p.strip("\n") for p in out]


def answers_to_blocks(answers: list[dict[str, Any]], imap: IndexMap) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(blocks for the intermediate format, per-block mapping records for meta)."""
    blocks, records = [], []
    for a in answers:
        shown = context_ids(a.get("context") if isinstance(a.get("context"), dict) else None)
        for para in split_paragraphs(a.get("response") or ""):
            m = map_block(para, imap, shown)
            blocks.append({"section": a["section"], "text": para, "pmids": m["pmids"], "citations": m["citations"]})
            records.append({"section": a["section"], "chars": len(para), "basis": m["basis"], "refs": m["refs"],
                            "by_kind": m["by_kind"], "not_shown": m["not_shown"]})
    return blocks, records


def mapping_shares(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(r["chars"] for r in records)
    by = Counter()
    for r in records:
        by[r["basis"]] += r["chars"]
    return {"chars": total, **{f"chars_{k}": by.get(k, 0) for k in ("sources", "entities_relationships",
                                                                     "reports_only", "none")},
            **{f"share_{k}": round(by.get(k, 0) / total, 4) if total else None
               for k in ("sources", "entities_relationships", "reports_only", "none")},
            "ids_not_shown": sum(len(v) for r in records for v in r["not_shown"].values())}


# --------------------------------------------------------------------------- #
# Ledger by workflow step
# --------------------------------------------------------------------------- #


def step_of(row: dict[str, Any]) -> str:
    tag = row.get("tag") or ""
    parts = tag.split("/")
    step = parts[2] if len(parts) > 2 else "(untagged)"
    if row.get("endpoint") == "/v1/embeddings":
        return "embeddings"
    if row.get("prompt_chars") is not None and step != "embeddings" and row.get("rendering") == "single" \
            and row.get("prompt_chars", 0) <= len(CONNECTIVITY_TEST) + 40 and step in ("connectivity",) + tuple(STEP_MODELS.values()):
        return "connectivity_test"
    if step == "extract_graph" and row.get("rendering") == "transcript":
        return "extract_graph_gleaning"
    return step


def usage_by_step(rows: list[dict[str, Any]], tag_prefix: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        t = r.get("tag") or ""
        if t != tag_prefix and not t.startswith(tag_prefix + "/"):
            continue
        s = out.setdefault(step_of(r), {"requests": 0, "fresh_calls": 0, "cached": 0, "refused_400": 0, "errors": 0,
                                        "stops": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                                        "call_seconds": 0.0, "json_invalid": 0})
        s["requests"] += 1
        if r.get("endpoint") == "/v1/embeddings":
            continue
        if r.get("status") == 400:
            s["refused_400"] += 1
            continue
        if r.get("status") != 200:
            s["errors"] += 1
            continue
        s["stops"] += int(bool(r.get("safety_stop")))
        s["json_invalid"] += int(r.get("json_valid") is False)
        if r.get("cached"):
            s["cached"] += 1
            continue
        s["fresh_calls"] += int(r.get("model_calls") or 0)
        s["input_tokens"] += int(r.get("input_tokens") or 0)
        s["output_tokens"] += int(r.get("output_tokens") or 0)
        s["cost_usd"] = round(s["cost_usd"] + float(r.get("cost_usd") or 0.0), 6)
        s["call_seconds"] = round(s["call_seconds"] + float(r.get("call_seconds") or 0.0), 1)
    return out


# --------------------------------------------------------------------------- #
# Index facts, losses, log errors
# --------------------------------------------------------------------------- #


def index_facts(tables: dict[str, Any]) -> dict[str, Any]:
    units = tables.get("text_units") or []
    ents = tables.get("entities") or []
    rels = tables.get("relationships") or []
    covered = {u for e in ents for u in (e.get("text_unit_ids") or [])} | \
              {u for r in rels for u in (r.get("text_unit_ids") or [])}
    docs = {d["id"]: _pmid_of(d["title"]) for d in tables.get("documents") or []}
    empty_units = [u["id"] for u in units if u["id"] not in covered]
    per_doc = Counter(docs.get(u.get("document_id")) for u in units)
    return {"documents": len(docs), "chunks": len(units), "entities": len(ents), "relationships": len(rels),
            "communities": len(tables.get("communities") or []),
            "community_reports": len(tables.get("community_reports") or []),
            "chunks_per_pmid": dict(per_doc),
            "chunks_without_entities_or_relationships": [
                {"text_unit": u, "pmid": docs.get(next((x.get("document_id") for x in units if x["id"] == u), None))}
                for u in empty_units]}


def log_errors(root: Path) -> list[str]:
    out = []
    for p in sorted((root / "logs").glob("*.log")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if " ERROR " in line or "Traceback" in line or "error extracting" in line.lower():
                out.append(f"{p.name}: {line[:400]}")
    return out


# --------------------------------------------------------------------------- #
# One entry, end to end
# --------------------------------------------------------------------------- #


def convert_and_save(mim: str, method: str, search: str, query_run: dict[str, Any] | None = None) -> dict[str, Any]:
    from .corpus import load_entry

    system = SYSTEMS[(method, search)]
    index_system = INDEX_SYSTEM[method]
    index_folder, folder = entry_dir(index_system, mim), entry_dir(system, mim)
    root = index_folder / "project"
    corpus = load_entry(mim)
    import yaml

    changes = configure(yaml.safe_load((root / "settings.generated.yaml").read_text(encoding="utf-8")))[1] + ENV_CHANGES
    if method == "fast":
        changes.append({"setting": "graphrag index --method", "default": "standard", "value": "fast",
                        "reason": "budget rule of the design: the package's own fast method (noun-phrase graph, "
                                  "model only for community reports and queries)"})
    status = json.loads((index_folder / "index_status.json").read_text(encoding="utf-8"))
    tables = export_tables(index_folder) if status.get("ok") else {}
    facts = index_facts(tables) if tables else {}
    answers_path = folder / f"answers.{search}.json"
    answers = json.loads(answers_path.read_text(encoding="utf-8")) if answers_path.exists() else []
    rows = ledger_rows([index_folder / "ledger.jsonl"] + ([folder / "ledger.jsonl"] if folder != index_folder else []))
    steps_index = usage_by_step(rows, f"{index_system}/{mim}")
    steps = usage_by_step(rows, f"{system}/{mim}")
    own = [r for r in rows if (r.get("tag") or "").startswith(f"{system}/{mim}")]
    stops = sum(1 for r in own if r.get("safety_stop"))
    calls = sum(int(r.get("model_calls") or 0) for r in own if r.get("status") == 200 and not r.get("cached"))
    imap = IndexMap(tables) if tables else None
    blocks, records = answers_to_blocks(answers, imap) if imap else ([], [])
    failed = [a["key"] for a in answers if a.get("error")]
    empty = [a["key"] for a in answers if not a.get("error") and not (a.get("response") or "").strip()]
    missing = [q["key"] for q in section_questions(corpus.title) if q["key"] not in {a["key"] for a in answers}]
    stopped = None
    if not status.get("ok"):
        stopped = f"indexing did not complete ({method})"
    elif failed or missing:
        stopped = f"{search} search did not complete for: {', '.join(failed + missing)}"
    elif not blocks:
        stopped = "no answer text (every question stopped or empty)"
    meta = {
        "package": PACKAGE, "version": versions().get("graphrag"), "versions": versions(),
        "indexing_method": method, "search_method": search,
        "query_cli_defaults": {"community_level": 2, "response_type": "Multiple Paragraphs", "streaming": False,
                               "dynamic_community_selection": False},
        "settings_changed": changes,
        "calls": calls, "stops": stops, "seconds": round(sum(float(a.get("seconds") or 0) for a in answers), 1),
        "tag": f"{system}/{mim}", "ledgers": [str(p.relative_to(REPO)) for p in
                                               {index_folder / "ledger.jsonl", folder / "ledger.jsonl"} if p.exists()],
        "index": facts, "index_status": status, "index_log_errors": log_errors(root)[:50],
        "usage_by_step": steps, "index_usage_by_step": steps_index if index_system != system else None,
        "empty_answers": empty, "failed_questions": failed,
        "query_errors": {a["key"]: a.get("error") for a in answers if a.get("error")},
        "mapping": mapping_shares(records), "block_mapping": records, "query_run": query_run,
    }
    output = {"system": system, "mim": mim, "stopped": stopped, "blocks": blocks, "meta": meta}
    save_output(output)
    return {"system": system, "mim": mim, "stopped": stopped, "blocks": len(blocks), "calls": calls,
            "stops": stops, "mapping": meta["mapping"], "index": {k: v for k, v in facts.items()
                                                                     if k != "chunks_without_entities_or_relationships"}}


def run(mim: str, method: str = "standard", search: str = "local") -> dict[str, Any]:
    status = index_entry(mim, method)
    qrun = None
    if status.get("ok"):
        qrun = query_entry(mim, method, search)
    return convert_and_save(mim, method, search, qrun)


# --------------------------------------------------------------------------- #
# Smoke test: a tiny index, to see that the package reaches the adapter and nothing else
# --------------------------------------------------------------------------- #

SMOKE_TEXTS = {
    "11111111": "Smith J. A family with a rare disorder. J Test. 2001.\n\nTITLE: A family with a rare disorder\n\n"
                "ABSTRACT: The Acme Hospital in Boston examined five members of the Jones family. Dr. Mary Lee led "
                "the study, which the Boston Genetics Society funded.",
    "22222222": "Brown K. Follow-up. J Test. 2003.\n\nTITLE: Follow-up of the Jones family\n\nABSTRACT: Dr. Mary "
                "Lee and Dr. Ken Brown of the Acme Hospital re-examined the Jones family at the 2002 Boston meeting.",
}


def smoke() -> dict[str, Any]:
    folder = entry_dir("graphrag", "_smoke")
    root, _ = prepare_project(folder, SMOKE_TEXTS)
    before = calls_spent()
    with _adapter("graphrag/_smoke", folder / "ledger.jsonl") as (base, srv):
        guard = BudgetGuard(srv.shim, before)
        code = _run_sub([str(VENV / "bin" / "graphrag"), "index", "--root", str(root), "--method", "standard"],
                        _subprocess_env(base, "graphrag/_smoke"), folder / "index.log", guard)
        q = [{"key": "description", "section": "Description", "question": "Who examined the Jones family?"}]
        (folder / "questions.json").write_text(json.dumps(q), encoding="utf-8")
        qcode = _run_sub([str(VENV / "bin" / "python"), "-I", str(RUNNER), "query", str(root), "local",
                          str(folder / "questions.json"), str(folder / "answers.local.json")],
                         _subprocess_env(base, "graphrag/_smoke"), folder / "query.log", guard)
        stats = dict(srv.shim.stats)
    return {"index_exit": code, "query_exit": qcode, "adapter": stats,
            "by_step": usage_by_step(ledger_rows([folder / "ledger.jsonl"]), "graphrag/_smoke"),
            "log_errors": log_errors(root)[:20]}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.external.sys_graphrag")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("smoke")
    sub.add_parser("budget")
    sub.add_parser("versions")
    r = sub.add_parser("run")
    r.add_argument("mims", nargs="+")
    r.add_argument("--method", default="standard", choices=["standard", "fast"])
    r.add_argument("--search", default="local", choices=["local", "global"])
    c = sub.add_parser("convert")
    c.add_argument("mims", nargs="+")
    c.add_argument("--method", default="standard", choices=["standard", "fast"])
    c.add_argument("--search", default="local", choices=["local", "global"])
    args = ap.parse_args(argv)
    if args.cmd == "smoke":
        print(json.dumps(smoke(), indent=1))
    elif args.cmd == "budget":
        rows = ledger_rows()
        by_tag = Counter()
        for row in rows:
            if row.get("endpoint") == "/v1/chat/completions" and row.get("status") == 200 and not row.get("cached"):
                by_tag["/".join((row.get("tag") or "").split("/")[:2])] += int(row.get("model_calls") or 0)
        print(json.dumps({"spent": calls_spent(rows), "cap": BUDGET, "by_entry": dict(by_tag)}, indent=1))
    elif args.cmd == "versions":
        print(json.dumps(versions(), indent=1))
    elif args.cmd == "run":
        for mim in args.mims:
            print(json.dumps(run(mim, args.method, args.search)), flush=True)
    elif args.cmd == "convert":
        for mim in args.mims:
            print(json.dumps(convert_and_save(mim, args.method, args.search)), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
