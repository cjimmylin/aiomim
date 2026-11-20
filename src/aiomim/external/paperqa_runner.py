"""PaperQA2 driver script that runs INSIDE the package's own environment (`.venvs/paperqa/`).

Started by `sys_paperqa.py` as a subprocess with `.venvs/paperqa/bin/python`; it imports nothing
from the project. For one entry it builds a `paperqa.Docs` from exactly the exported papers
(one document per `<pmid>.txt`, citation and document name supplied, no metadata lookup) and asks
each question with the package's public document-set query pipeline, `Docs.aquery` (embedding
retrieval of `evidence_k` chunks -> contextual summary of each by `summary_llm` -> answer by `llm`
from the top-ranked summaries), every other setting at the package default.

    .venvs/paperqa/bin/python -I src/aiomim/external/paperqa_runner.py \
        --base-url http://127.0.0.1:PORT/v1 --corpus DIR --questions Q.json --out OUT.json
    .venvs/paperqa/bin/python -I src/aiomim/external/paperqa_runner.py --base-url URL --probe --out OUT.json
    .venvs/paperqa/bin/python -I src/aiomim/external/paperqa_runner.py --print-defaults

The settings changed from the package's defaults are exactly those in `changed_settings()`;
`sys_paperqa.py` copies the list it prints into `meta.settings_changed`.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
import time
from pathlib import Path

MODEL = "openai/claude-opus-5-5"          # LiteLLM name: OpenAI wire format; the adapter serves the project model
EMBEDDING = "openai/bge-small-en-v1.5"    # the adapter's local embedding endpoint (the name is only echoed)
DUMMY_KEY = "sk-local-dummy"
CLIENT_TIMEOUT = 900                      # seconds; the adapter's guidance (>= 900 s)


def router_config(name: str, base_url: str) -> dict:
    """The package's own default LiteLLM router layout (`make_default_litellm_model_list_settings`)
    with only the endpoint, a dummy key and the client timeout added."""
    from paperqa.settings import make_default_litellm_model_list_settings

    cfg = make_default_litellm_model_list_settings(name)          # temperature 0.0, as the default Settings
    cfg["model_list"][0]["litellm_params"].update(
        {"api_base": base_url, "api_key": DUMMY_KEY, "timeout": CLIENT_TIMEOUT})
    return cfg


def build_settings(base_url: str):
    from lmi.utils import get_litellm_retrying_config
    from paperqa import Settings

    llm_cfg = router_config(MODEL, base_url)
    return Settings(
        llm=MODEL, llm_config=llm_cfg,
        summary_llm=MODEL, summary_llm_config=router_config(MODEL, base_url),
        embedding=EMBEDDING,
        # lmi's default embedding kwargs (num_retries 3, timeout 120 s) plus the endpoint and a dummy key
        embedding_config={"kwargs": {**get_litellm_retrying_config(timeout=120),
                                     "api_base": base_url, "api_key": DUMMY_KEY}},
        agent={"agent_llm": MODEL, "agent_llm_config": router_config(MODEL, base_url)},
        parsing={"use_doc_details": False,
                 "enrichment_llm": MODEL, "enrichment_llm_config": router_config(MODEL, base_url)},
    )


def changed_settings() -> list[dict]:
    """Every setting changed from the package default: (setting, default, value, reason)."""
    from paperqa import Settings

    d = Settings()
    adapter = "the local adapter in front of the project's one model (no other provider)"
    return [
        {"setting": "llm", "default": d.llm, "value": MODEL,
         "reason": "answer writing; " + adapter},
        {"setting": "llm_config (api_base, api_key, timeout)", "default": "None (router built from llm, provider "
         "endpoint, provider key from env, LiteLLM default timeout)",
         "value": f"package's default router layout + api_base=<adapter>, api_key={DUMMY_KEY}, timeout={CLIENT_TIMEOUT}",
         "reason": "point the answer role at the adapter; dummy key; adapter asks for a client timeout >= 900 s "
                   "(its queue is capped at 3 concurrent calls)"},
        {"setting": "summary_llm (+ summary_llm_config, same router change)", "default": d.summary_llm,
         "value": MODEL, "reason": "contextual summaries of evidence; " + adapter},
        {"setting": "agent.agent_llm (+ agent_llm_config)", "default": d.agent.agent_llm, "value": MODEL,
         "reason": "pointed at the adapter for safety; not used by Docs.aquery (no call was made in this role)"},
        {"setting": "parsing.enrichment_llm (+ enrichment_llm_config)", "default": d.parsing.enrichment_llm,
         "value": MODEL, "reason": "media enrichment of PDFs; pointed at the adapter for safety; not used for .txt "
                                    "papers (no call was made in this role)"},
        {"setting": "embedding (+ embedding_config kwargs api_base, api_key)", "default": d.embedding,
         "value": EMBEDDING + " via adapter /v1/embeddings (fastembed BAAI/bge-small-en-v1.5, 384 dims)",
         "reason": "the one local embedding model shared by all systems; no hosted embedding"},
        {"setting": "parsing.use_doc_details", "default": d.parsing.use_doc_details, "value": False,
         "reason": "no outside metadata lookup (Crossref, Semantic Scholar, Unpaywall, OpenAlex, retractions, "
                   "journal quality); citation and title are supplied instead"},
        {"setting": "Docs.aadd(citation=, docname=, title=)", "default": "None: citation inferred by `llm` from "
         "the first chunk; docname derived from it (Author+Year)",
         "value": "citation = the paper's reference line (first line of <pmid>.txt, from the export); "
                  "docname = <Surname><Year>-<PMID> from papers.csv; title from papers.csv",
         "reason": "corpus = exactly the entry's papers, one document each; no call or lookup spent on metadata; "
                   "citations in answers map back to the PubMed id unambiguously"},
        {"setting": "entry point", "default": "agent_query with agent_type 'ToolSelector' (pqa ask)",
         "value": "Docs.aadd per paper, then Docs.aquery per question (the README's 'Manual (No Agent)' usage)",
         "reason": "the default agent selects tools by function calling, which the adapter refuses; the 'fake' "
                   "agent also ends with a function-calling Complete step (select_tool with tool_choice) that the "
                   "adapter refuses; Docs.aquery needs none and keeps retrieval, contextual summaries and answer"},
        {"setting": "environment", "default": "LiteLLM fetches its model cost map from GitHub; telemetry defaults",
         "value": "LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, DO_NOT_TRACK=1, "
                  "ANONYMIZED_TELEMETRY=False, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=<local>; "
                  "outbound proxy = a local logger that refuses and records every non-local connection",
         "reason": "no outside service is contacted; any attempt is logged"},
    ]


# --------------------------------------------------------------------------- #
# Corpus
# --------------------------------------------------------------------------- #


def docname_for(first_author: str, year: str, pmid: str) -> str:
    """`Rutten2024-38430071`: PaperQA's own Author+Year style, made unique by the PubMed id."""
    tokens = [t for t in re.split(r"\s+", first_author.strip()) if t]
    if len(tokens) > 1 and re.fullmatch(r"[A-Z]{1,4}", tokens[-1]):     # drop trailing initials ("Rutten JW")
        tokens = tokens[:-1]
    surname = re.sub(r"[^A-Za-z0-9]", "", "".join(t[:1].upper() + t[1:] for t in tokens)) or "Paper"
    return f"{surname}{year or ''}-{pmid}"


def read_corpus(corpus_dir: Path) -> list[dict]:
    rows = []
    with (corpus_dir / "papers.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            path = corpus_dir / r["file"]
            reference = path.read_text(encoding="utf-8").split("\n", 1)[0].strip()
            rows.append({"pmid": r["pmid"], "path": str(path), "title": r["title"], "citation": reference,
                         "docname": docname_for(r["first_author"], r["year"], r["pmid"])})
    return rows


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #


def session_record(session, question: dict, seconds: float) -> dict:
    return {
        "key": question["key"], "section": question["section"], "question": question["question"],
        "answer": session.answer, "raw_answer": session.raw_answer, "references": session.references,
        "has_successful_answer": session.has_successful_answer,
        "token_counts": {k: list(v) for k, v in (session.token_counts or {}).items()},
        "cost": session.cost, "seconds": round(seconds, 1),
        "contexts": [{"id": c.id, "name": c.text.name, "docname": c.text.doc.docname, "score": c.score,
                      "context": c.context} for c in session.contexts],
        "context_str": session.context,
    }


async def run(args) -> dict:
    from paperqa import Docs, __version__

    settings = build_settings(args.base_url)
    papers = read_corpus(Path(args.corpus))
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    docs = Docs()
    added = []
    for p in papers:
        name = await docs.aadd(p["path"], citation=p["citation"], docname=p["docname"], title=p["title"],
                               settings=settings)
        added.append({"pmid": p["pmid"], "docname": name, "requested_docname": p["docname"]})
    chunks = {}
    for t in docs.texts:
        chunks[t.doc.docname] = chunks.get(t.doc.docname, 0) + 1
    out = {"version": __version__, "papers": added, "chunks": chunks, "answers": []}
    for q in questions:
        started = time.time()
        session = await docs.aquery(q["question"], settings=settings)
        out["answers"].append(session_record(session, q, time.time() - started))
        Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


async def probe(args) -> dict:
    """One tiny chat call and one embedding through the package's own model classes."""
    from paperqa import __version__
    from aviary.core import Message

    settings = build_settings(args.base_url)
    result = await settings.get_llm().call_single(messages=[Message(content="Reply with the single word: ready")])
    emb = await settings.get_embedding_model().embed_documents(["probe sentence"])
    return {"version": __version__, "reply": result.text, "embedding_dims": len(emb[0])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url")
    ap.add_argument("--corpus")
    ap.add_argument("--questions")
    ap.add_argument("--out")
    ap.add_argument("--log")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--print-defaults", action="store_true")
    args = ap.parse_args()
    if args.print_defaults:
        print(json.dumps(changed_settings(), indent=1, default=str))
        return
    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO,
                            format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.probe:
        res = asyncio.run(probe(args))
        Path(args.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps(res))
        return
    asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
