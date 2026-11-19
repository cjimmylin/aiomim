"""Runs the stages end to end for one entry and writes every intermediate to disk.

    runs/<run>/<mim>/
        seed.json            what the pipeline was told about the entry
        gold.json            the public gold standard it is scored against
        retrieval.json       how the papers were chosen
        papers.json          the papers and how much of each could be read
        extractions.json     per-paper findings with quotes and grounding scores
        kg.json              the evidence knowledge graph
        entry.<s>.json|.md   the generated entry, per strategy, with audit verdicts
        eval.<s>.json        scores against gold, per strategy
        usage.json           model calls and tokens per stage
    runs/<run>/summary.json  scores for every entry plus averages
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import get_settings
from .evaluate import eval_faithfulness, evaluate_entry, summarize
from .extract import extract_papers, ground_phenotypes
from .kg import build_graph
from .llm import LLM
from .models import GeneratedEntry, GoldEntry, Paper, PaperExtraction, Seed
from .render import entry_markdown
from .retrieve import retrieve_open, retrieve_oracle
from .synthesize import synthesize_direct, synthesize_from_graph
from .verify import repair_entry, verdict_counts, verify_entry

log = logging.getLogger(__name__)


@dataclass
class RunConfig:
    run: str = "default"
    retrieval: str = "oracle"            # "oracle" | "open"
    strategies: tuple[str, ...] = ("kg",)  # any of "kg", "direct"
    verify: bool = True
    repair: bool = True
    evaluate: bool = True
    fulltext: bool = True
    max_papers: int = 25
    # With oracle retrieval the reference list already pins down the subject, so the
    # gene is withheld and must be recovered from the literature. Open retrieval
    # needs the gene to search with, as a curator starting a new entry would have it.
    blind_gene: bool | None = None

    def gene_is_blind(self) -> bool:
        return self.retrieval == "oracle" if self.blind_gene is None else self.blind_gene


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _paper_record(paper: Paper) -> dict[str, Any]:
    record = paper.model_dump(exclude={"fulltext"})
    record.update(content_level=paper.content_level, label=paper.label, reference=paper.reference,
                  n_chars=len(paper.source_text()))
    return record


def build_entries(
    seed: Seed, papers: list[Paper], cfg: RunConfig, llm: LLM, out_dir: Path
) -> tuple[dict[str, GeneratedEntry], list[PaperExtraction]]:
    """Stages 3-6 for one seed and one set of papers."""
    by_pmid = {p.pmid: p for p in papers}
    entries: dict[str, GeneratedEntry] = {}
    extractions: list[PaperExtraction] = []

    if "kg" in cfg.strategies:
        log.info("[%s] extracting findings from %d papers", seed.mim or seed.title, len(papers))
        extractions = extract_papers(seed, papers, llm)
        hpo_stats = ground_phenotypes(extractions, llm)
        _write(out_dir / "extractions.json", [e.model_dump() for e in extractions])
        kg = build_graph(seed, papers, extractions)
        _write(out_dir / "kg.json", kg.to_json())
        _write(out_dir / "kg_triples.tsv",
               "subject\tpredicate\tobject\tpmids\n" + "\n".join("\t".join(row) for row in kg.triples()) + "\n")
        log.info("[%s] graph: %s", seed.mim or seed.title, kg.stats()["nodes"])
        entry = synthesize_from_graph(seed, kg, llm)
        n_found = sum(len(e.findings) for e in extractions)
        n_dropped = sum(len(e.dropped_findings) for e in extractions)
        entry.meta["extraction"] = {
            "findings_kept": n_found, "findings_dropped_ungrounded": n_dropped,
            "quote_grounding_rate": round(n_found / (n_found + n_dropped), 3) if n_found + n_dropped else None,
            "papers_by_relevance": _count(e.relevance for e in extractions),
            "papers_failed": [e.pmid for e in extractions if e.error and not e.findings],
            "hpo_resolution": hpo_stats,
        }
        entries["kg"] = entry

    if "direct" in cfg.strategies:
        log.info("[%s] writing direct baseline", seed.mim or seed.title)
        entries["direct"] = synthesize_direct(seed, papers, llm)

    for strategy, entry in entries.items():
        entry.meta["papers_by_content_level"] = _count(p.content_level for p in papers)
        if cfg.verify:
            log.info("[%s] auditing %s entry (%d paragraphs)", seed.mim or seed.title, strategy,
                     len(entry.all_paragraphs()))
            verify_entry(entry, by_pmid, llm)
            before = eval_faithfulness(entry)
            before.pop("before_repair", None)
            entry.meta["audit_before_repair"] = before
            if cfg.repair:
                repair_entry(entry, by_pmid, llm)
                entry.assign_paragraph_ids()
            entry.meta["audit"] = verdict_counts(entry)
        _write(out_dir / f"entry.{strategy}.json", entry.model_dump())
        _write(out_dir / f"entry.{strategy}.md", entry_markdown(entry))
    return entries, extractions


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def run_entry(mim: str, cfg: RunConfig) -> dict[str, Any]:
    """Replicate one existing OMIM entry and score it against its gold standard."""
    from .gold import build_gold, seed_from_gold

    settings = get_settings()
    out_dir = settings.runs / cfg.run / mim
    llm = LLM(settings)
    started = time.time()

    gold: GoldEntry = build_gold(mim)
    seed = seed_from_gold(gold)
    if cfg.gene_is_blind() and seed.entry_type == "phenotype":
        seed.gene_symbols = []
    _write(out_dir / "gold.json", gold.model_dump())
    _write(out_dir / "seed.json", seed.model_dump())
    log.info("[%s] %s%s — %d cited references, %d gold paragraphs, %d HPO annotations",
             mim, gold.prefix, gold.title, len(gold.cited_pmids), len(gold.gold_paragraphs),
             len(gold.hpo_annotations))

    if cfg.retrieval == "oracle":
        papers, retrieval = retrieve_oracle(gold.cited_pmids, with_fulltext=cfg.fulltext)
    else:
        papers, retrieval = retrieve_open(seed, llm, max_papers=cfg.max_papers, with_fulltext=cfg.fulltext)
    _write(out_dir / "retrieval.json", retrieval)
    _write(out_dir / "papers.json", [_paper_record(p) for p in papers])
    log.info("[%s] %d papers (%s)", mim, len(papers), _count(p.content_level for p in papers))

    entries, _ = build_entries(seed, papers, cfg, llm, out_dir)

    result: dict[str, Any] = {"mim": mim, "title": gold.title, "evals": {}}
    if cfg.evaluate:
        # Gold paragraphs can cite papers that open retrieval did not select; the
        # judge still needs to know how much of them was readable.
        by_pmid = {p.pmid: p for p in papers}
        offered = [p.pmid for p in papers]
        for strategy, entry in entries.items():
            evaluation = evaluate_entry(entry, gold, by_pmid, llm, offered_pmids=offered)
            evaluation["retrieval"] = cfg.retrieval
            _write(out_dir / f"eval.{strategy}.json", evaluation)
            result["evals"][strategy] = evaluation

    usage = llm.usage.summary()
    usage["wall_seconds"] = round(time.time() - started, 1)
    _write(out_dir / "usage.json", usage)
    result["usage"] = usage
    return result


def run_seed(seed: Seed, cfg: RunConfig, name: str) -> dict[str, GeneratedEntry]:
    """Draft a new entry from a curator-supplied seed. There is no gold to score against."""
    settings = get_settings()
    out_dir = settings.runs / cfg.run / name
    llm = LLM(settings)
    _write(out_dir / "seed.json", seed.model_dump())
    papers, retrieval = retrieve_open(seed, llm, max_papers=cfg.max_papers, with_fulltext=cfg.fulltext)
    _write(out_dir / "retrieval.json", retrieval)
    _write(out_dir / "papers.json", [_paper_record(p) for p in papers])
    entries, _ = build_entries(seed, papers, cfg, llm, out_dir)
    _write(out_dir / "usage.json", llm.usage.summary())
    return entries


def run_many(mims: list[str], cfg: RunConfig, jobs: int = 1) -> dict[str, Any]:
    """Run several entries, `jobs` at a time. Each entry also fans out its own model calls."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    settings = get_settings()
    run_dir = settings.runs / cfg.run
    failures: dict[str, str] = {}
    if jobs > 1:
        from .sources.hpo import get_hpo
        get_hpo()  # load the ontology once, before worker threads race to do it

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(run_entry, mim, cfg): mim for mim in mims}
        for future in as_completed(futures):
            mim = futures[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - one bad entry should not lose the rest of a batch
                log.exception("[%s] failed", mim)
                failures[mim] = f"{type(exc).__name__}: {exc}"
            _write(run_dir / "summary.json", collect_summary(run_dir, cfg, failures))
    return collect_summary(run_dir, cfg, failures)


def collect_summary(run_dir: Path, cfg: RunConfig | None = None, failures: dict[str, str] | None = None) -> dict[str, Any]:
    """Rebuild the run summary from the per-entry files on disk."""
    by_strategy: dict[str, list[dict[str, Any]]] = {}
    usage_total: dict[str, float] = {}
    for eval_path in sorted(run_dir.glob("*/eval.*.json")):
        strategy = eval_path.name.split(".")[1]
        by_strategy.setdefault(strategy, []).append(json.loads(eval_path.read_text()))
    for usage_path in run_dir.glob("*/usage.json"):
        for key, value in json.loads(usage_path.read_text()).get("total", {}).items():
            usage_total[key] = round(usage_total.get(key, 0) + value, 4)
    summary: dict[str, Any] = {
        "run": run_dir.name,
        "config": asdict(cfg) if cfg else None,
        "strategies": {s: summarize(evals) for s, evals in by_strategy.items()},
        "entries": {
            s: [_entry_row(e) for e in evals] for s, evals in by_strategy.items()
        },
        "usage_total": usage_total,
        "failures": failures or {},
    }
    return summary


def _entry_row(e: dict[str, Any]) -> dict[str, Any]:
    g = e.get("gold_text", {})
    return {
        "mim": e["mim"], "title": e["title"],
        "refs_gold": e["references"]["cited"]["n_gold"],
        "ref_recall": e["references"]["cited"]["recall"],
        "retrieval_recall": e["references"].get("retrieved", {}).get("recall"),
        "access": e.get("gold_reference_access"),
        "gene_f1": e["genes"]["f1"], "inheritance_match": e["inheritance"]["match"],
        "hpo_exact_f1": e["synopsis"]["exact"]["f1"],
        "hpo_hier_f1": e["synopsis"]["hierarchical"]["f1"],
        "hpo_semantic_f1": e["synopsis"]["semantic"]["f1"],
        "variant_recall": e["variants"]["recall"],
        "gold_facts": g.get("n_facts"), "gold_fact_coverage": g.get("coverage"),
        "gold_fact_contradicted": g.get("contradicted"),
        "claims": e["faithfulness"]["n_claims"],
        "claim_supported_rate": e["faithfulness"]["supported_rate"],
        "claim_error_rate": e["faithfulness"]["error_rate"],
    }
