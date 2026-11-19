"""Stage 2: decide which papers the entry will be built from.

oracle  Use exactly the references OMIM cites. This isolates the question "given
        the same papers a curator read, can the entry be reproduced?".

open    Find the literature from scratch, as would be needed for a new entry:
        the model plans search queries from the entry header, PubMed and Europe
        PMC are searched, the model triages candidates on title and abstract, and
        the best candidates' reference lists and citing papers are pulled in for a
        second round. Scored against OMIM's reference list afterwards.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from .llm import LLM
from .models import Paper, Seed

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Query planning
# --------------------------------------------------------------------------- #

PLAN_SYSTEM = """\
You plan literature searches for a curator writing an OMIM (Online Mendelian Inheritance in Man) \
entry. Given the entry's header, write PubMed queries that together will find the papers a curator \
would cite: the first clinical descriptions, the reports that identified the causal gene and its \
variants, later case series, functional studies and animal models.

OMIM's titles are often coined by OMIM and do not appear in papers, so do not rely on the title as a \
phrase. Combine the gene symbol(s), where given, with the disorder's defining clinical terms, and \
include the eponyms and older names from the alternative titles. Use PubMed syntax ([tiab], [mh], \
AND/OR, quoted phrases). Give four to eight queries, from the most specific to broader ones; each \
should be able to stand alone.\
"""


class XPlan(BaseModel):
    queries: list[str]


TRIAGE_SYSTEM = """\
You are screening search results for a curator writing an OMIM (Online Mendelian Inheritance in Man) \
entry. For each numbered paper (title, journal, year, abstract) rate how likely a curator would be to \
cite it in this specific entry:

3  core: an original report of patients with this disorder, of the gene/variants causing it, or of \
functional or animal-model work directly on it.
2  useful: further cases, cohorts, genotype-phenotype or mechanistic studies that add to the entry.
1  marginal: reviews, large screens or related-disorder papers that mention it in passing.
0  not about this entry's subject.

OMIM cites primary reports rather than reviews, and cites a paper for a specific disorder, not for \
the gene's other phenotypes. Rate every paper.\
"""


class XRating(BaseModel):
    n: int
    score: int = Field(description="0, 1, 2 or 3")


class XRatings(BaseModel):
    ratings: list[XRating]


def _header(seed: Seed) -> str:
    kind = "gene" if seed.entry_type == "gene" else "phenotype (disorder)"
    lines = [f"OMIM entry ({kind}): {seed.title}"]
    if seed.symbol:
        lines.append(f"Symbol: {seed.symbol}")
    if seed.alt_titles:
        lines.append("Alternative titles: " + "; ".join(seed.alt_titles))
    if seed.gene_symbols:
        lines.append("Gene(s): " + ", ".join(seed.gene_symbols))
    return "\n".join(lines)


def _triage(seed: Seed, papers: list[Paper], llm: LLM, batch: int = 25) -> dict[str, int]:
    prompts, chunks = [], []
    for start in range(0, len(papers), batch):
        chunk = papers[start:start + batch]
        chunks.append(chunk)
        listing = "\n\n".join(
            f"{n}. {p.title} ({p.journal}, {p.year})\n{p.abstract[:1800] or '(no abstract)'}"
            for n, p in enumerate(chunk, 1)
        )
        prompts.append(f"{_header(seed)}\n\nPapers to screen:\n\n{listing}")
    scores: dict[str, int] = {}
    for chunk, reply in zip(chunks, llm.map("triage", TRIAGE_SYSTEM, prompts, XRatings)):
        if isinstance(reply, Exception):
            log.warning("triage: a batch failed (%s); its papers are scored 0", reply)
            continue
        for rating in reply.ratings:
            if 1 <= rating.n <= len(chunk):
                scores[chunk[rating.n - 1].pmid] = max(0, min(3, rating.score))
    return scores


# --------------------------------------------------------------------------- #
# Retrieval modes
# --------------------------------------------------------------------------- #


def retrieve_oracle(pmids: list[str], with_fulltext: bool = True) -> tuple[list[Paper], dict[str, Any]]:
    from .sources.fulltext import load_papers

    papers = load_papers(pmids, with_fulltext=with_fulltext)
    found = {p.pmid for p in papers}
    return papers, {"mode": "oracle", "requested": pmids, "missing": [p for p in pmids if p not in found]}


def retrieve_open(
    seed: Seed,
    llm: LLM,
    max_papers: int = 25,
    pool_size: int = 120,
    with_fulltext: bool = True,
) -> tuple[list[Paper], dict[str, Any]]:
    from .sources import europepmc, ncbi
    from .sources.fulltext import load_papers

    plan = llm.call("plan", PLAN_SYSTEM, _header(seed), XPlan)
    queries = [q.strip() for q in plan.queries if q.strip()][:8]

    # Round 1: run every query on PubMed and Europe PMC; rank candidates by how
    # many queries found them and how high.
    votes: dict[str, float] = {}
    per_query: dict[str, int] = {}
    for query in queries:
        hits: list[str] = []
        for search, label in ((ncbi.pubmed_search, "pubmed"), (europepmc.search, "europepmc")):
            try:
                found = search(query, 60, max_year=seed.max_year)
            except Exception as exc:  # noqa: BLE001 - one failing search must not stop retrieval
                log.warning("open retrieval: %s search failed for %r: %s", label, query, exc)
                found = []
            hits.extend(found)
            for rank, pmid in enumerate(found):
                votes[pmid] = votes.get(pmid, 0.0) + 1.0 / (10 + rank)
        per_query[query] = len(set(hits))
    for pmid in seed.seed_pmids:
        votes[pmid] = votes.get(pmid, 0.0) + 10.0

    pool = [pmid for pmid, _ in sorted(votes.items(), key=lambda kv: -kv[1])][:pool_size]
    candidates = {p.pmid: p for p in ncbi.pubmed_fetch(pool)}
    if seed.max_year:
        candidates = {k: p for k, p in candidates.items() if not p.year or p.year <= seed.max_year}
    scores = _triage(seed, list(candidates.values()), llm)

    # Round 2: follow the citation graph one hop out from the core papers. First
    # reports are often old and poorly indexed; the papers that cite them, and the
    # papers they cite, are the reliable way to reach them.
    core = [pmid for pmid, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s >= 3][:8]
    neighbour_votes: dict[str, int] = {}
    for pmid in core:
        for fetch in (europepmc.references, europepmc.citations):
            try:
                linked = fetch(pmid)
            except Exception as exc:  # noqa: BLE001
                log.warning("open retrieval: citation lookup failed for %s: %s", pmid, exc)
                linked = []
            for other in linked:
                if other not in candidates:
                    neighbour_votes[other] = neighbour_votes.get(other, 0) + 1
    # A paper linked to two or more core papers is a strong candidate; cap the round.
    expansion = [p for p, n in sorted(neighbour_votes.items(), key=lambda kv: -kv[1]) if n >= 2][:80]
    if expansion:
        extra = {p.pmid: p for p in ncbi.pubmed_fetch(expansion)}
        if seed.max_year:
            extra = {k: p for k, p in extra.items() if not p.year or p.year <= seed.max_year}
        scores.update(_triage(seed, list(extra.values()), llm))
        candidates.update(extra)

    ranked = sorted(
        (pmid for pmid in candidates if scores.get(pmid, 0) >= 2),
        key=lambda pmid: (-scores[pmid], -votes.get(pmid, 0.0) - 0.05 * neighbour_votes.get(pmid, 0)),
    )
    selected = ranked[:max_papers]
    papers = load_papers(selected, with_fulltext=with_fulltext)
    info = {
        "mode": "open", "queries": queries, "hits_per_query": per_query,
        "n_candidates": len(candidates), "n_expansion": len(expansion),
        "scores": {pmid: scores.get(pmid, 0) for pmid in candidates},
        "selected": selected, "max_year": seed.max_year,
    }
    return papers, info
