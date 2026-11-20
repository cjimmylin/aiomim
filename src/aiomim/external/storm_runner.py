"""STORM (`knowledge-storm`) on one entry, run INSIDE the system's own environment `.venvs/storm/`.

Started as a subprocess by `sys_storm.py` (project environment), never imported by the project:

    .venvs/storm/bin/python src/aiomim/external/storm_runner.py \
        --corpus runs/external/storm/<mim>/corpus --work runs/external/storm/<mim>/work \
        --topic "Atrial standstill 1" --base-url http://127.0.0.1:<port>/v1 --tag storm/<mim>

What it does, all with the package's own code:

1. Builds the package's user-supplied corpus (a CSV with content / title / url / description columns, as
   `examples/storm_examples/run_storm_wiki_gpt_with_VectorRM.py` expects) from the exported `papers.csv` and
   `<pmid>.txt` files: one row per paper, url `https://pubmed.ncbi.nlm.nih.gov/<pmid>/` (an identifier only,
   never fetched), and indexes it with `QdrantVectorStoreManager.create_or_update_vector_store` (offline
   Qdrant on disk; the package's own chunking, 500 characters with 100 overlap) and the local
   `BAAI/bge-small-en-v1.5`.
2. Runs `STORMWikiRunner` with its default arguments and all four stages, every LM role a `LitellmModel`
   pointed at the local adapter.

Instrumentation that does not change what the package does: each stage method is wrapped to tag its
requests (`X-Aiomim-Tag: storm/<mim>/<stage>`) and to keep the polished article's own reference list (the
runner writes the polished text but only the draft's reference list, whose numbering the polishing step
changes); the Wikipedia page reader used for perspective discovery is wrapped to record what it fetched;
an audit hook records every outbound connection the process opens.

Settings changed from the package defaults are listed in `SETTINGS_CHANGED` (sys_storm.py copies them
into `meta.settings_changed`).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
COLLECTION = "my_documents"          # the example script's default collection name
MODEL = "openai/claude-opus-5-5"
PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

# Per-role max_tokens of the package's own default configuration (STORMWikiLMConfigs.init_openai_model), with
# its temperature 1.0 and top_p 0.9. The adapter ignores all three; they are sent as the package would.
ROLE_MAX_TOKENS = {"conv_simulator_lm": 500, "question_asker_lm": 500, "outline_gen_lm": 400,
                   "article_gen_lm": 700, "article_polish_lm": 4000}
CLIENT_TIMEOUT = 1800

STAGES = {"run_knowledge_curation_module": "research", "run_outline_generation_module": "outline",
          "run_article_generation_module": "article", "run_article_polishing_module": "polish"}

SETTINGS_CHANGED = [
    {"setting": "LM, all five roles (conv_simulator_lm, question_asker_lm, outline_gen_lm, article_gen_lm, "
                "article_polish_lm)",
     "default": "STORMWikiLMConfigs.init_openai_model: LitellmModel gpt-4o-mini-2024-07-18 (conversation, "
                "question asking), gpt-4-0125-preview (outline), gpt-4o-2024-05-13 (article, polish)",
     "value": f"LitellmModel {MODEL}, api_base = local adapter, api_key = dummy",
     "reason": "the local adapter in front of the project's one model (Claude Opus 5.5, effort medium)"},
    {"setting": "LM temperature / top_p / max_tokens",
     "default": "temperature 1.0, top_p 0.9; max_tokens 500 / 500 / 400 / 700 / 4000 per role",
     "value": "sent unchanged, but ignored by the adapter (the command-line model takes no sampling or "
              "length parameters; replies are not cut at max_tokens)",
     "reason": "the adapter cannot pass them to the model; recorded, not chosen"},
    {"setting": "LM request timeout", "default": "LiteLLM default (600 s)", "value": f"{CLIENT_TIMEOUT} s",
     "reason": "adapter calls queue behind a concurrency cap of 3 and can take minutes; the harness asks for "
               ">= 900 s"},
    {"setting": "retriever (rm)", "default": "a web search API (YouRM / BingSearch / ... in the examples)",
     "value": "VectorRM over the entry's supplied papers only (offline Qdrant on disk), k = search_top_k = 3",
     "reason": "the papers may not go to an outside service; the corpus is exactly the supplied papers"},
    {"setting": "VectorRM corpus CSV", "default": "user supplied (content, title, url, description)",
     "value": "one row per supplied paper: content = the exported <pmid>.txt (reference line, title, abstract, "
              "full text as the entry's access level allows); title = paper title; url = "
              "https://pubmed.ncbi.nlm.nih.gov/<pmid>/ (identifier only, never fetched); description = the "
              "reference line",
     "reason": "the corpus is exactly the supplied papers; the url identifies the PubMed id for citation mapping"},
    {"setting": "VectorRM / QdrantVectorStoreManager embedding_model", "default": "BAAI/bge-m3 (1024 dims)",
     "value": f"{EMBEDDING_MODEL} (384 dims), loaded locally by the package's own HuggingFaceEmbeddings",
     "reason": "the small local embedding model used by all three systems"},
    {"setting": "VectorRM / QdrantVectorStoreManager device", "default": "mps", "value": "cpu",
     "reason": "no Apple GPU (or any GPU) on this machine"},
    {"setting": "Qdrant collection vector size", "default": "1024 (hard-coded in "
                "QdrantVectorStoreManager._check_create_collection)",
     "value": f"{EMBEDDING_DIM}: the collection is created with this size before the package's own builder "
              "is called (the builder then loads it instead of creating it)",
     "reason": "a hard-coded 1024 cannot hold 384-dimensional vectors; smallest change"},
    {"setting": "qdrant_client.Document",
     "default": "`from qdrant_client import Document` in QdrantVectorStoreManager.create_or_update_vector_store "
                "(fails: qdrant-client has no such name in any release checked, 1.7-1.20)",
     "value": "the name is set to langchain_core.documents.Document (the class the code uses: page_content, "
              "metadata, split by the LangChain text splitter) before the builder is called",
     "reason": "the released corpus builder cannot run otherwise; smallest change, no behaviour added"},
    {"setting": "dependency versions (unpinned by knowledge-storm 1.1.1)",
     "default": "whatever the resolver picks: uv picked sentence-transformers 2.2.2 + transformers 4.17.0 "
                "(fails to import: huggingface_hub has no cached_download) and qdrant-client 1.20.0 (no "
                "QdrantClient.search, which langchain_qdrant.Qdrant, used by VectorRM, calls)",
     "value": "sentence-transformers 5.7.0 (newest), transformers 4.57.6; qdrant-client 1.15.1 (newest release "
              "with QdrantClient.search); torch 2.15.0+cpu",
     "reason": "the newest versions with which the released VectorRM path imports and runs"},
    {"setting": "telemetry / outside calls",
     "default": "LiteLLM telemetry off (set by the package); cost map local (set by the package); "
                "Hugging Face hub online",
     "value": "also LITELLM_TELEMETRY=False, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1, "
              "ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1; models fetched once beforehand; no other provider "
              "key in the environment",
     "reason": "nothing but the adapter and the Wikipedia pages of the perspective step may be reached"},
    {"setting": "LiteLLM disk cache location", "default": "~/.storm_local_cache",
     "value": "HOME set to runs/external/storm/_home, so the cache is runs/external/storm/_home/.storm_local_cache",
     "reason": "keep the run's files inside the run folder; caching behaviour unchanged"},
]


# --------------------------------------------------------------------------- outbound record

class Outbound:
    """Records every outbound connection the process opens (audit hook) and the Wikipedia pages read."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def write(self, row: dict) -> None:
        row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **row}
        with self.lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def hook(self, event: str, args) -> None:
        try:
            if event == "socket.getaddrinfo":
                self.write({"event": "getaddrinfo", "host": args[0], "port": args[1]})
            elif event == "socket.connect":
                addr = args[1]
                if isinstance(addr, tuple):
                    self.write({"event": "connect", "address": list(addr[:2])})
        except Exception:  # never let the record break the run
            pass


# --------------------------------------------------------------------------- corpus

def build_corpus_csv(corpus_dir: Path, out_csv: Path) -> list[str]:
    """The package's CSV (content, title, url, description) from papers.csv and <pmid>.txt; returns the PMIDs."""
    rows, pmids = [], []
    with (corpus_dir / "papers.csv").open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            text = (corpus_dir / rec["file"]).read_text(encoding="utf-8")
            reference = text.split("\n", 1)[0].strip()
            rows.append({"content": text, "title": rec["title"], "url": PUBMED_URL.format(pmid=rec["pmid"]),
                         "description": reference})
            pmids.append(rec["pmid"])
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["content", "title", "url", "description"])
        w.writeheader()
        w.writerows(rows)
    return pmids


def build_vector_store(csv_path: Path, store: Path) -> int:
    """Index the CSV with the package's own builder; skipped when the store already holds the corpus."""
    from qdrant_client import QdrantClient, models

    client = QdrantClient(path=str(store))
    try:
        if client.collection_exists(COLLECTION):
            n = client.count(collection_name=COLLECTION).count
            if n > 0:
                return n
            client.delete_collection(COLLECTION)
        # Changed setting: the package hard-codes size=1024 (bge-m3); create the collection at 384 first.
        client.create_collection(collection_name=COLLECTION,
                                 vectors_config=models.VectorParams(size=EMBEDDING_DIM,
                                                                    distance=models.Distance.COSINE))
    finally:
        client.close()

    # Changed setting: the released builder imports `Document` from qdrant_client, which has none.
    import qdrant_client
    from langchain_core.documents import Document

    if not hasattr(qdrant_client, "Document"):
        qdrant_client.Document = Document
    from knowledge_storm.utils import QdrantVectorStoreManager

    QdrantVectorStoreManager.create_or_update_vector_store(
        collection_name=COLLECTION, vector_db_mode="offline", file_path=str(csv_path),
        content_column="content", title_column="title", url_column="url", desc_column="description",
        batch_size=64, vector_store_path=str(store), embedding_model=EMBEDDING_MODEL, device="cpu")
    client = QdrantClient(path=str(store))
    try:
        return client.count(collection_name=COLLECTION).count
    finally:
        client.close()


# --------------------------------------------------------------------------- LMs

def make_lm(base_url: str, max_tokens: int, tag: str):
    from knowledge_storm.lm import LitellmModel

    return LitellmModel(model=MODEL, max_tokens=max_tokens, api_key="sk-local-dummy", api_base=base_url,
                        temperature=1.0, top_p=0.9, timeout=CLIENT_TIMEOUT,
                        extra_headers={"X-Aiomim-Tag": tag})


def smoke(base_url: str, tag: str) -> dict:
    lm = make_lm(base_url, 50, f"{tag}/smoke")
    out = lm("Reply with the single word OK.")
    return {"outputs": out, "usage": lm.get_usage_and_reset()}


# --------------------------------------------------------------------------- run

def run(args) -> dict:
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    outbound = Outbound(work / "outbound.jsonl")
    sys.addaudithook(outbound.hook)
    logging.basicConfig(filename=str(work / "storm.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("urllib3").setLevel(logging.DEBUG)       # records the Wikipedia requests

    if args.smoke:
        res = smoke(args.base_url, args.tag)
        print(json.dumps(res))
        return res

    started = time.time()
    csv_path = work / "storm_corpus.csv"
    pmids = build_corpus_csv(Path(args.corpus), csv_path)
    n_chunks = build_vector_store(csv_path, work / "vector_store")
    t_index = time.time() - started

    from knowledge_storm import STORMWikiLMConfigs, STORMWikiRunner, STORMWikiRunnerArguments
    from knowledge_storm.rm import VectorRM
    from knowledge_storm.storm_wiki.modules import persona_generator

    lm_configs = STORMWikiLMConfigs()
    lms = {role: make_lm(args.base_url, mt, f"{args.tag}/research") for role, mt in ROLE_MAX_TOKENS.items()}
    lm_configs.set_conv_simulator_lm(lms["conv_simulator_lm"])
    lm_configs.set_question_asker_lm(lms["question_asker_lm"])
    lm_configs.set_outline_gen_lm(lms["outline_gen_lm"])
    lm_configs.set_article_gen_lm(lms["article_gen_lm"])
    lm_configs.set_article_polish_lm(lms["article_polish_lm"])

    engine_args = STORMWikiRunnerArguments(output_dir=str(work / "storm_out"))   # every other argument default
    rm = VectorRM(collection_name=COLLECTION, embedding_model=EMBEDDING_MODEL, device="cpu",
                  k=engine_args.search_top_k)
    rm.init_offline_vector_db(vector_store_path=str(work / "vector_store"))
    runner = STORMWikiRunner(engine_args, lm_configs, rm)

    # Instrumentation: record the Wikipedia pages the perspective step reads.
    wiki_pages: list[dict] = []
    original_reader = persona_generator.get_wiki_page_title_and_toc

    def recording_reader(url):
        row = {"url": url}
        try:
            title, toc = original_reader(url)
            row.update(title=title, ok=True, toc_lines=len(toc.splitlines()))
            return title, toc
        except Exception as exc:
            row.update(ok=False, error=f"{type(exc).__name__}: {exc}"[:300])
            raise
        finally:
            wiki_pages.append(row)
            outbound.write({"event": "wikipedia_page", **row})

    persona_generator.get_wiki_page_title_and_toc = recording_reader

    # Instrumentation: tag each stage's requests, time it, keep the polished article's own references.
    captured: dict = {}
    stage_seconds: dict = {}
    for method, stage in STAGES.items():
        original = getattr(runner, method)

        def wrapped(*a, _original=original, _stage=stage, **kw):
            for lm in lms.values():
                lm.kwargs["extra_headers"] = {"X-Aiomim-Tag": f"{args.tag}/{_stage}"}
            t0 = time.time()
            result = _original(*a, **kw)
            stage_seconds[_stage] = round(time.time() - t0, 1)
            captured[_stage] = result
            return result

        setattr(runner, method, wrapped)

    runner.run(topic=args.topic, do_research=True, do_generate_outline=True, do_generate_article=True,
               do_polish_article=True)
    runner.post_run()
    runner.summary()

    article_dir = Path(runner.article_output_dir)
    polished = captured.get("polish")
    if polished is not None:
        polished.dump_reference_to_file(str(article_dir / "url_to_info_polished.json"))
    stats = {"topic": args.topic, "article_dir": str(article_dir), "pmids": pmids, "chunks": n_chunks,
             "index_seconds": round(t_index, 1), "stage_seconds": stage_seconds,
             "storm_time": runner.time, "lm_cost": runner.lm_cost, "rm_cost": runner.rm_cost,
             "wikipedia_pages": wiki_pages, "seconds": round(time.time() - started, 1),
             "settings_changed": SETTINGS_CHANGED, "versions": versions()}
    (work / "run_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str),
                                         encoding="utf-8")
    return stats


def versions() -> dict:
    from importlib.metadata import version

    out = {}
    for pkg in ("knowledge-storm", "dspy-ai", "litellm", "qdrant-client", "langchain-qdrant",
                "langchain-huggingface", "langchain-text-splitters", "sentence-transformers", "transformers",
                "torch", "openai", "requests"):
        try:
            out[pkg] = version(pkg)
        except Exception:
            out[pkg] = None
    out["python"] = sys.version.split()[0]
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--corpus", help="the exported corpus folder (papers.csv, <pmid>.txt)")
    p.add_argument("--work", required=True)
    p.add_argument("--topic")
    p.add_argument("--base-url", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--smoke", action="store_true", help="one tiny call through the package's LitellmModel")
    p.add_argument("--versions", action="store_true")
    args = p.parse_args(argv)
    if args.versions:
        print(json.dumps({"versions": versions(), "settings_changed": SETTINGS_CHANGED}))
        return
    run(args)


if __name__ == "__main__":
    main()
