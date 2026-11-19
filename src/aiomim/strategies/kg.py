"""Evidence graph: extract quote-backed findings, build the knowledge graph, write from it."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..extract import extract_papers, ground_phenotypes
from ..kg import build_graph
from ..models import GeneratedEntry, Paper, Seed
from ..synthesize import synthesize_from_graph

log = logging.getLogger(__name__)


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    from ..pipeline import _write

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
    return entry
