"""Second-hand evidence: direct reading, with each paper that could not be read in
full supplemented by what later open-access papers say it reported.

    run           supplement the papers, write `secondhand.json`, write the entry
                  directly from the supplemented papers.
    audit_papers  the same supplemented papers, so the audit reads what the writer read.
    after_audit   for every audited claim, whether its evidence lies in the paper's
                  own text or in a later paper's description of it, and whose.

The passages come from `sources.citing`; see there for how they are found,
ranked and capped.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..grounding import GROUNDED, SourceIndex
from ..models import GeneratedEntry, Paper, SecondhandPassage, Seed
from ..sources import citing
from ..synthesize import synthesize_direct

log = logging.getLogger(__name__)

RECORD = "secondhand.json"
WORKERS = 4

RULES = """\
Second-hand descriptions. Some papers that could be read only as an abstract or a title are followed by a \
block headed "SECOND-HAND DESCRIPTIONS OF THIS PAPER": passages from later open-access papers that cite \
that paper, where [*] marks the citation. Use them as follows.
- You may use a passage for what the cited paper reported, when the passage clearly attributes it to \
that paper (the [*] stands at the statement). Where the passage cites several papers together, use only \
what it plainly attributes to this one.
- Cite the original paper (its PMID and label), never the later paper, unless the later paper is itself \
one of the supplied papers.
- Never name the later papers or their authors in the entry text: no "according to Smith et al. (2015)", \
"as later summarised by ...", "(Smith et al., 2015)" or similar. Write the statement as the original \
paper's finding, attributed to the original paper's label, exactly as for its own text. The entry marks \
paragraphs that rest on these descriptions separately.
- Where the paper's own title or abstract and a second-hand passage disagree, follow the paper's own words.
- Do not attribute to the original paper the later authors' own patients, data, interpretations or \
conclusions; only what they say the original paper reported.\
"""


# --------------------------------------------------------------------------- #
# Supplementing the papers
# --------------------------------------------------------------------------- #


def supplement(papers: list[Paper], exclude: set[str] | None = None,
               targets: set[str] | None = None) -> tuple[list[Paper], dict[str, Any]]:
    """Attach second-hand passages to every paper not read in full (or to `targets`).

    Papers that are themselves part of the entry (`exclude`, default: all of
    `papers`) are never used as citing sources.
    """
    exclude = set(exclude if exclude is not None else (p.pmid for p in papers))
    chosen = [p for p in papers if (p.pmid in targets if targets is not None else p.content_level != "fulltext")]
    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        records = dict(zip([p.pmid for p in chosen],
                           pool.map(lambda p: citing.secondhand_for(p, frozenset(exclude)), chosen)))
    augmented = []
    for p in papers:
        record = records.get(p.pmid)
        augmented.append(p.model_copy(update={"secondhand": citing.passages_of(record)}) if record else p)
    by_pmid = {p.pmid: p for p in papers}
    summary = {
        "caps": {"citing_papers_fetched": citing.MAX_CITING_FETCH, "passages": citing.MAX_PASSAGES,
                 "per_citing_paper": citing.MAX_PER_CITING, "passage_chars": citing.PASSAGE_CHARS,
                 "total_chars": citing.TOTAL_CHARS},
        "seconds": round(time.time() - started, 1),
        "targets": [{
            "pmid": pmid, "label": by_pmid[pmid].label, "content_level": by_pmid[pmid].content_level,
            "n_citing": r["n_citing"], "n_open_access": r["n_open_access"], "n_eligible": r["n_eligible"],
            "n_fetched": sum(1 for f in r["fetched"] if f["source"]), "fetched": r["fetched"],
            "n_passages": len(r["passages"]), "n_chars": r["n_chars"], "seconds": r["seconds"],
            "cached": r.get("cached", False), "error": r["error"],
            "passages": [{**{k: v for k, v in p.items()}, "chars": len(p["text"])} for p in r["passages"]],
        } for pmid, r in records.items()],
    }
    summary["totals"] = totals(summary)
    return augmented, summary


def totals(summary: dict[str, Any]) -> dict[str, Any]:
    t = summary["targets"]
    return {
        "papers_supplemented": len(t),
        "with_citing_papers": sum(1 for r in t if r["n_citing"]),
        "with_open_access_citing": sum(1 for r in t if r["n_open_access"]),
        "with_passages": sum(1 for r in t if r["n_passages"]),
        "lookup_failed": sum(1 for r in t if r["error"]),
        "citing_papers_fetched": sum(r["n_fetched"] for r in t),
        "passages": sum(r["n_passages"] for r in t),
        "chars": sum(r["n_chars"] for r in t),
        "retrieval_seconds": summary.get("seconds"),
    }


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_augmented(papers: list[Paper], record_path: Path) -> list[Paper]:
    """Rebuild the supplemented papers from a `secondhand.json`."""
    if not record_path.exists():
        return papers
    summary = json.loads(record_path.read_text(encoding="utf-8"))
    by_pmid = {r["pmid"]: r for r in summary.get("targets", [])}
    return [p.model_copy(update={"secondhand": citing.passages_of(by_pmid[p.pmid])}) if p.pmid in by_pmid else p
            for p in papers]


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    augmented, summary = supplement(papers)
    _write_json(Path(out_dir) / RECORD, summary)
    t = summary["totals"]
    log.info("[%s] secondhand: %d of %d papers supplemented got passages (%d passages, %d chars) in %.0f s",
             seed.mim or seed.title, t["with_passages"], t["papers_supplemented"], t["passages"], t["chars"],
             summary["seconds"])
    entry = synthesize_direct(seed, augmented, llm, extra_rules=RULES, strategy="secondhand",
                              meta={"secondhand_retrieval": t})
    entry.meta["named_citing_papers"] = named_citing_papers(entry, augmented)
    return entry


def named_citing_papers(entry: GeneratedEntry, papers: list[Paper]) -> list[str]:
    """Author-year citations in the text that name a citing paper (the rules forbid it)."""
    from ..synthesize import _fold

    labels = {_fold(re.sub(r" \((\d{4}|n\.d\.)\)$", "", s.citing_label)) for p in papers for s in p.secondhand
              if s.citing_label}
    return [c for c in entry.meta.get("unknown_citations", [])
            if _fold(re.sub(r" \((\d{4})\)$", "", c)) in labels]


def audit_papers(papers: list[Paper], out_dir: Path) -> list[Paper]:
    return load_augmented(papers, Path(out_dir) / RECORD)


# --------------------------------------------------------------------------- #
# Where each audited claim's evidence lies
# --------------------------------------------------------------------------- #

# A passage whose paragraph or row cites at most this many other references "cites few".
FEW_COCITED = 2


def cocited(n_other_refs: int) -> str:
    return "few" if n_other_refs <= FEW_COCITED else "many"


class Attributor:
    """Places an evidence quote in a paper's own text or in one of its second-hand passages."""

    def __init__(self, papers: list[Paper]):
        self.papers = {p.pmid: p for p in papers}
        self._own: dict[str, SourceIndex] = {}
        self._passages: dict[str, list[tuple[SecondhandPassage, SourceIndex]]] = {}
        self._block: dict[str, SourceIndex] = {}

    def _indexes(self, pmid: str):
        if pmid not in self._own:
            paper = self.papers[pmid]
            self._own[pmid] = SourceIndex(paper.model_copy(update={"secondhand": []}).source_text())
            self._passages[pmid] = [(s, SourceIndex(s.text)) for s in paper.secondhand]
            self._block[pmid] = SourceIndex(paper.secondhand_block())
        return self._own[pmid], self._passages[pmid], self._block[pmid]

    def locate_passage(self, pmid: str, quote: str) -> tuple[str, SecondhandPassage | None]:
        """("own" | "secondhand" | "unlocated" | "none", the passage the quote lies in).

        A quote found in the paper's own text counts as own even if a passage repeats it.
        """
        if not quote or pmid not in self.papers:
            return ("none", None)
        own, passages, block = self._indexes(pmid)
        if own.score(quote) >= GROUNDED:
            return ("own", None)
        if passages:
            best, i = max((idx.score(quote), -n) for n, (_, idx) in enumerate(passages))
            passage = passages[-i][0]
            if best >= GROUNDED or block.score(quote) >= GROUNDED:   # the latter: spans a passage header
                return ("secondhand", passage)
        return ("unlocated", None)

    def locate(self, pmid: str, quote: str) -> tuple[str, str]:
        """("own" | "secondhand" | "unlocated" | "none", citing PMID or "")."""
        kind, passage = self.locate_passage(pmid, quote)
        return (kind, passage.citing_pmid if passage else "")


def after_audit(entry: GeneratedEntry, papers: list[Paper], out_dir: Path) -> None:
    """Mark claims that rest on second-hand text, and take them out of the audit's verdicts.

    A later paper's description of a paper is not that paper: a claim whose
    evidence is found only in a second-hand passage becomes `not_checkable`, which
    the faithfulness score leaves out of its denominator. Its original verdict is
    kept in `entry.meta["secondhand"]`. A claim found in the paper's own text keeps
    its verdict.
    """
    where = Attributor(papers)
    supplemented = {p.pmid for p in papers if p.secondhand}
    counts: dict[str, int] = defaultdict(int)
    verdicts_secondhand: dict[str, int] = defaultdict(int)
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_cocited: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for para in entry.all_paragraphs():
        used: list[str] = []
        for check in para.checks:
            if check.verdict == "not_checkable":
                continue
            counts["claims"] += 1
            kind, passage = where.locate_passage(check.pmid, check.evidence_quote)
            counts[kind] += 1
            if kind != "secondhand":
                continue
            verdicts_secondhand[check.verdict] += 1
            by_kind[passage.kind][check.verdict] += 1
            by_cocited[cocited(passage.n_other_refs)][check.verdict] += 1
            used.append(passage.citing_pmid)
            row = "table row" if passage.kind == "table" else "paragraph"
            check.explanation = (
                f"Second-hand: the evidence is a {row} of {passage.citing_label or 'a later paper'} "
                f"(PMID {passage.citing_pmid}) describing PMID {check.pmid}, not the paper's own text; the claim "
                f"was not checked against PMID {check.pmid} itself. Verdict on the later paper's description: "
                f"{check.verdict}." + (f" {check.explanation}" if check.explanation else ""))
            check.verdict = "not_checkable"
        para.secondhand_pmids = list(dict.fromkeys(used))
    record_path = Path(out_dir) / RECORD
    retrieval = {}
    if record_path.exists():
        retrieval = json.loads(record_path.read_text(encoding="utf-8")).get("totals", {})
    labels = {s.citing_pmid: s.citing_label for p in papers for s in p.secondhand}
    entry.meta["secondhand"] = {
        "papers_supplemented": retrieval.get("papers_supplemented", 0),
        "papers_with_passages": len(supplemented),
        "passages": sum(len(p.secondhand) for p in papers),
        "chars": sum(len(s.text) for p in papers for s in p.secondhand),
        "claims": counts["claims"],
        "claims_on_own_text": counts["own"],
        "claims_on_secondhand": counts["secondhand"],
        "claims_quote_not_located": counts["unlocated"],
        "claims_without_quote": counts["none"],
        # The audit's verdicts on claims resting on second-hand text, before they were
        # set to not_checkable: how well the writer followed the later descriptions.
        "secondhand_verdicts": dict(verdicts_secondhand),
        "secondhand_verdicts_by_passage_kind": {k: dict(v) for k, v in by_kind.items()},
        "secondhand_verdicts_by_cocited": {k: dict(v) for k, v in by_cocited.items()},
        "few_cocited_means_at_most": FEW_COCITED,
        "paragraphs_on_secondhand": sum(1 for p in entry.all_paragraphs() if p.secondhand_pmids),
        "named_citing_papers": entry.meta.get("named_citing_papers", []),
        "citing_labels": {pmid: labels.get(pmid, "") for p in entry.all_paragraphs() for pmid in p.secondhand_pmids},
    }
