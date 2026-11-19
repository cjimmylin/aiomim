"""Draw a reproducible evaluation set of OMIM phenotype entries.

Entries are sampled at random (fixed seed) within strata of MIM number, which
tracks when an entry was created, so the set spans classic entries and ones
created in the last few years. An entry qualifies when there is something to
compare against:

* a causal gene recorded by OMIM (molecular basis known),
* HPO annotations of its clinical synopsis,
* at least one OMIM-authored paragraph, with its PMID, that cites a paper in the
  entry's own reference list (so per-paper accuracy can be measured),
* a reference list within a size band (2-12 for the "few references" set,
  omim100; 30-100 for the large-entry tier, large12, where the strategies have
  to cope with more text than one prompt holds).

For a large-entry draw, `prefilter` checks the reference count (one cached NCBI
elink call) and the HPO count (local) before the full gold standard is built,
which is the expensive part; `fill_short` hands the quota a stratum cannot fill
to the others, since large entries are rare among recent MIM numbers. Neither
changes which entries qualify, and both are off by default, so the draw that
produced omim100.tsv is reproduced exactly.

How much of each paper is openly readable is deliberately NOT a criterion: that
would select for the easy cases.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Iterator

log = logging.getLogger(__name__)

# (label, [(low, high), ...]) — MIM numbers are assigned in sequence within the 6xxxxx
# block, so ranges approximate creation era; 1xxxxx-5xxxxx are the classic catalogue.
STRATA: list[tuple[str, list[tuple[int, int]]]] = [
    ("classic (1xxxxx-5xxxxx)", [(100000, 599999)]),
    ("600000-609999", [(600000, 609999)]),
    ("610000-615999", [(610000, 615999)]),
    ("616000-619999", [(616000, 619999)]),
    ("620000 onward", [(620000, 629999)]),
]


def stratum_of(mim: str) -> str:
    number = int(mim)
    for label, ranges in STRATA:
        if any(low <= number <= high for low, high in ranges):
            return label
    return "other"


def qualifies(gold, min_refs: int, max_refs: int, min_hpo: int, min_paragraphs: int) -> tuple[bool, str]:
    if gold.entry_type != "phenotype":
        return False, "not a phenotype entry"
    if not gold.genes:
        return False, "no causal gene recorded"
    if not min_refs <= len(gold.cited_pmids) <= max_refs:
        return False, f"{len(gold.cited_pmids)} references"
    n_hpo = sum(1 for a in gold.hpo_annotations if a.aspect == "P")
    if n_hpo < min_hpo:
        return False, f"{n_hpo} HPO phenotype annotations"
    if len(gold.scoped_paragraphs) < min_paragraphs:
        return False, f"{len(gold.scoped_paragraphs)} OMIM paragraphs for cited papers"
    return True, ""


def _cheap_reject(mim: str, min_refs: int, max_refs: int, min_hpo: int) -> str:
    """Why `mim` cannot qualify, from the reference count and HPO count alone; "" if it may.

    Uses the same sources `build_gold` does (NCBI elink omim_pubmed_cited, the local
    HPO annotation file), so it never rejects an entry the full check would accept.
    """
    from .sources import ncbi
    from .sources.hpo import get_hpo

    n_hpo = sum(1 for a in get_hpo().annotations(mim) if a.aspect == "P")
    if n_hpo < min_hpo:
        return f"{n_hpo} HPO phenotype annotations"
    n_refs = len(ncbi.omim_cited_pmids(mim))
    if not min_refs <= n_refs <= max_refs:
        return f"{n_refs} references"
    return ""


def candidates() -> list[str]:
    """Phenotype MIM numbers that have both a gene link and HPO annotations."""
    from .sources import mim2gene
    from .sources.hpo import get_hpo

    annotated = get_hpo().annotated_mims()
    return sorted(m for m in annotated if mim2gene.mim_entry_type(m) in ("phenotype", "predominantly phenotypes")
                  and mim2gene.genes_for_phenotype(m))


def sample(
    n: int = 100, seed: int = 13, min_refs: int = 2, max_refs: int = 12, min_hpo: int = 5,
    min_paragraphs: int = 1, include: tuple[str, ...] = (), prefilter: bool = False,
    fill_short: bool = False,
) -> Iterator[dict[str, Any]]:
    """Yield `n` qualifying entries, spread evenly over the strata, as coverage rows.

    With `fill_short`, quota a stratum could not fill is handed, one entry at a
    time and in stratum order, to the strata that still have qualifying entries.
    """
    from .gold import build_gold

    rng = random.Random(seed)
    pool: dict[str, list[str]] = {label: [] for label, _ in STRATA}
    for mim in candidates():
        if stratum_of(mim) in pool:
            pool[stratum_of(mim)].append(mim)
    for mims in pool.values():
        rng.shuffle(mims)

    quota = {label: n // len(STRATA) + (1 if i < n % len(STRATA) else 0) for i, (label, _) in enumerate(STRATA)}
    taken: set[str] = set()

    def row(gold) -> dict[str, Any]:
        return {
            "mim": gold.mim, "stratum": stratum_of(gold.mim), "title": gold.title,
            "n_refs": len(gold.cited_pmids), "n_hpo": sum(1 for a in gold.hpo_annotations if a.aspect == "P"),
            "n_omim_paragraphs": len(gold.scoped_paragraphs),
            "genes": ",".join(g.symbol for g in gold.genes), "inheritance": ",".join(gold.inheritance),
        }

    # Entries the caller insists on (e.g. a worked example) count against their stratum.
    for mim in include:
        gold = build_gold(mim)
        taken.add(mim)
        quota[stratum_of(mim)] = max(0, quota.get(stratum_of(mim), 0) - 1)
        yield row(gold)

    # Each stratum's pool is walked once, in its shuffled order; a second pass
    # (fill_short) resumes where the first stopped.
    cursor = {label: iter(pool[label]) for label, _ in STRATA}

    def next_qualifying(label: str):
        for mim in cursor[label]:
            if mim in taken:
                continue
            if prefilter:
                try:
                    why = _cheap_reject(mim, min_refs, max_refs, min_hpo)
                except Exception as exc:  # noqa: BLE001 - fall through to the full check
                    log.debug("evalset: prefilter failed for %s (%s)", mim, exc)
                    why = ""
                if why:
                    log.debug("evalset: %s rejected early: %s", mim, why)
                    continue
            try:
                gold = build_gold(mim)
            except Exception as exc:  # noqa: BLE001 - a broken record just is not sampled
                log.warning("evalset: %s skipped (%s)", mim, exc)
                continue
            ok, why = qualifies(gold, min_refs, max_refs, min_hpo, min_paragraphs)
            if not ok:
                log.debug("evalset: %s rejected: %s", mim, why)
                continue
            taken.add(mim)
            return gold
        return None

    short = 0
    exhausted: set[str] = set()
    for label, _ in STRATA:
        got = 0
        while got < quota[label]:
            gold = next_qualifying(label)
            if gold is None:
                exhausted.add(label)
                break
            got += 1
            yield row(gold)
        if got < quota[label]:
            log.warning("evalset: stratum %s yielded only %d of %d", label, got, quota[label])
            short += quota[label] - got

    while fill_short and short > 0 and len(exhausted) < len(STRATA):
        for label, _ in STRATA:
            if short <= 0 or label in exhausted:
                continue
            gold = next_qualifying(label)
            if gold is None:
                exhausted.add(label)
                continue
            short -= 1
            log.info("evalset: %s added to %s in place of a short stratum", gold.mim, label)
            yield row(gold)
    if short > 0 and fill_short:
        log.warning("evalset: %d entries short; every stratum is exhausted", short)


def describe_papers(mim: str) -> dict[str, Any]:
    """How readable an entry's references are: what the pipeline would be given for it.

    Retrieves the cited papers exactly as an oracle run does (PubMed records, open
    full text where there is any) and counts them by what could be read.
    """
    from .gold import build_gold
    from .retrieve import retrieve_oracle

    gold = build_gold(mim)
    papers, retrieval = retrieve_oracle(gold.cited_pmids, with_fulltext=True)
    levels = {"fulltext": 0, "abstract": 0, "title": 0}
    for p in papers:
        levels[p.content_level] += 1
    return {
        "n_papers": len(papers), "n_missing": len(retrieval.get("missing", [])),
        "n_fulltext": levels["fulltext"], "n_abstract": levels["abstract"], "n_title": levels["title"],
        "source_chars": sum(len(p.source_text()) for p in papers),
    }
