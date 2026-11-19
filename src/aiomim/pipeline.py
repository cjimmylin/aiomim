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
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import get_settings
from .evaluate import eval_faithfulness, evaluate_entry, summarize
from .llm import LLM
from .models import GeneratedEntry, GoldEntry, Paper, PaperExtraction, Seed
from .render import entry_markdown
from .retrieve import retrieve_open, retrieve_oracle
from .strategies import STRATEGIES, after_audit, audit_papers, run_strategy
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
    """Write a result file atomically: entries run in parallel while the summary reads them."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False, default=str)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _paper_record(paper: Paper) -> dict[str, Any]:
    record = paper.model_dump(exclude={"fulltext"})
    record.update(content_level=paper.content_level, label=paper.label, reference=paper.reference,
                  n_chars=len(paper.source_text()))
    return record


def _phase(llm, name: str) -> None:
    """Tell the usage ledger which phase the coming calls belong to (generate / audit / score)."""
    usage = getattr(llm, "usage", None)
    if usage is not None:
        usage.phase = name


def build_entries(
    seed: Seed, papers: list[Paper], cfg: RunConfig, llm: LLM, out_dir: Path,
    llms: dict[str, LLM] | None = None,
) -> tuple[dict[str, GeneratedEntry], list[PaperExtraction]]:
    """Stages 3-6 for one seed and one set of papers, for each requested strategy.

    `llms` gives each strategy its own model wrapper so that calls and tokens are
    tallied per strategy; without it everything goes through `llm`.
    """
    by_pmid = {p.pmid: p for p in papers}
    entries: dict[str, GeneratedEntry] = {}
    name_ = seed.mim or seed.title

    for strategy in cfg.strategies:
        spec = STRATEGIES[strategy]
        s_llm = (llms or {}).get(strategy, llm)
        _phase(s_llm, "generate")
        log.info("[%s] %s: generating from %d papers", name_, strategy, len(papers))
        entry = run_strategy(strategy, seed, papers, s_llm, out_dir)
        entry.meta["papers_by_content_level"] = _count(p.content_level for p in papers)
        if cfg.verify and spec.audit:
            _phase(s_llm, "audit")
            log.info("[%s] %s: auditing %d paragraphs", name_, strategy, len(entry.all_paragraphs()))
            # A strategy that wrote from more text than the papers as retrieved
            # (second-hand evidence) is audited against that same text.
            read = audit_papers(strategy, papers, out_dir)
            audit_by_pmid = by_pmid if read is papers else {p.pmid: p for p in read}
            verify_entry(entry, audit_by_pmid, s_llm)
            before = eval_faithfulness(entry)
            before.pop("before_repair", None)
            entry.meta["audit_before_repair"] = before
            if cfg.repair and spec.repair:
                repair_entry(entry, audit_by_pmid, s_llm)
                entry.assign_paragraph_ids()
            entry.meta["audit"] = verdict_counts(entry)
            after_audit(strategy, entry, read, out_dir)
        _write(out_dir / f"entry.{strategy}.json", entry.model_dump())
        _write(out_dir / f"entry.{strategy}.md", entry_markdown(entry))
        entries[strategy] = entry

    extractions: list[PaperExtraction] = []
    if "kg" in entries and (out_dir / "extractions.json").exists():
        extractions = [PaperExtraction.model_validate(x)
                       for x in json.loads((out_dir / "extractions.json").read_text(encoding="utf-8"))]
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
    # One wrapper per strategy: same cache, separate tallies of calls and tokens.
    llms = {name: LLM(settings) for name in cfg.strategies}
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

    entries, _ = build_entries(seed, papers, cfg, llm, out_dir, llms)

    result: dict[str, Any] = {"mim": mim, "title": gold.title, "evals": {}}
    if cfg.evaluate:
        # Gold paragraphs can cite papers that open retrieval did not select; the
        # judge still needs to know how much of them was readable.
        by_pmid = {p.pmid: p for p in papers}
        offered = [p.pmid for p in papers]
        for strategy, entry in entries.items():
            _phase(llms[strategy], "score")
            evaluation = evaluate_entry(entry, gold, by_pmid, llms[strategy], offered_pmids=offered)
            evaluation["retrieval"] = cfg.retrieval
            _write(out_dir / f"eval.{strategy}.json", evaluation)
            result["evals"][strategy] = evaluation

    usage = merge_usage(out_dir / "usage.json", {"retrieval": llm.usage.summary(),
                                                 **{name: w.usage.summary() for name, w in llms.items()}})
    usage["wall_seconds"] = round(time.time() - started, 1)
    _write(out_dir / "usage.json", usage)
    result["usage"] = usage
    return result


def merge_usage(path: Path, fresh: dict[str, Any]) -> dict[str, Any]:
    """Per-strategy usage for an entry, keeping the strategies an earlier pass ran.

    `total` adds up this pass only (what was actually spent now); `by_strategy`
    keeps each strategy's latest tally, whose `full_*` fields say what the strategy
    costs to run from scratch whether or not this pass hit the cache.
    """
    by_strategy: dict[str, Any] = {}
    if path.exists():
        try:
            by_strategy = json.loads(path.read_text(encoding="utf-8")).get("by_strategy", {})
        except (json.JSONDecodeError, OSError):
            by_strategy = {}
    for name, summary in fresh.items():
        if summary["total"]["calls"]:
            by_strategy[name] = summary
    keys = ("calls", "cached", "input_tokens", "output_tokens", "list_price_usd", "seconds")
    total = {k: round(sum(s["total"].get(k, 0) for s in fresh.values()), 4) for k in keys}
    return {"by_strategy": by_strategy, "total": total}


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
