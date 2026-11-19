"""Stretch goal: propose updates to an existing entry, for a curator to accept or reject.

The entry's current knowledge is taken to be what its cited references establish
(the evidence graph built from OMIM's own reference list). Newer literature that
the entry does not cite is searched, screened, read, and compared with that
graph. Each paper that adds something yields a proposal: what kind of update it
is, why it matters, and draft paragraphs in OMIM style whose every claim has been
audited against the paper.

`as_of` turns this into a back-test. The entry is rolled back to the references
published before that year, and the pipeline is asked to find what came next. The
references OMIM's curators really did add from that year on are the answer key.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel

from .config import get_settings
from .evaluate import prf
from .extract import extract_papers, ground_phenotypes
from .kg import build_graph
from .llm import LLM
from .models import EntryParagraph, EntrySection, GeneratedEntry, Paper, SectionName, Seed
from .pipeline import _paper_record, _write
from .retrieve import PLAN_SYSTEM, XPlan, _header, _triage
from .synthesize import STYLE, _kg_context
from .verify import verify_entry

log = logging.getLogger(__name__)

UpdateType = Literal[
    "new_causal_gene", "new_variants", "phenotype_expansion", "new_inheritance_mode",
    "genotype_phenotype_correlation", "functional_evidence", "animal_model", "treatment_or_management",
    "natural_history", "larger_cohort", "population_data", "diagnostic_method",
]

UPDATE_SYSTEM = f"""\
You are helping a curator keep an OMIM (Online Mendelian Inheritance in Man) entry current. You are \
given (1) the evidence the entry already rests on, as an evidence graph built from the references it \
cites, and (2) quote-verified findings from one newer paper that the entry does not cite. Decide \
whether this paper warrants an update, and if so draft it.

A paper warrants an update when it adds something a curator would record: a new causal gene or locus, \
variants not yet listed, clinical features not yet described or a clearly broader or milder spectrum, a \
different mode of inheritance, genotype-phenotype correlations, functional or animal-model evidence on \
mechanism, treatment results, natural history, or a substantially larger cohort that changes the \
picture. A further case that merely repeats what is already recorded, a review, or a paper about a \
different disorder does not.

Compare against the existing evidence concretely: a variant is new only if it is absent from the \
variant table; a feature is new only if it is absent from the clinical features listed. Say in \
`rationale`, in one or two sentences, exactly what is new relative to the entry.

`priority`: high for a change to the entry's core facts (causal gene, inheritance, a major new aspect \
of the phenotype, first functional proof); medium for a substantive addition (new variants and \
families, a new cohort, model data); low for a minor addition; none if no update is warranted, in \
which case leave `update_types` and `paragraphs` empty.

Draft the `paragraphs` to add, each assigned to the section it belongs in, using only the new paper's \
findings and listing their IDs in `finding_ids`. Do not restate what the entry already says, and do \
not add anything from your own knowledge.

{STYLE}\
"""


class XProposalParagraph(BaseModel):
    section: SectionName
    text: str
    finding_ids: list[str]


class XProposal(BaseModel):
    priority: Literal["high", "medium", "low", "none"]
    update_types: list[UpdateType]
    rationale: str
    paragraphs: list[XProposalParagraph]


def _candidates(seed: Seed, baseline: list[Paper], llm: LLM, since: int, until: int | None,
                exclude: set[str], pool_size: int = 100) -> tuple[list[Paper], dict[str, int], list[str]]:
    """Uncited papers from `since` on: searched, then pulled from the citing literature, then screened."""
    from .sources import europepmc, ncbi

    plan = llm.call("plan", PLAN_SYSTEM, _header(seed), XPlan)
    queries = [q.strip() for q in plan.queries if q.strip()][:8]
    votes: dict[str, float] = {}
    for query in queries:
        for search in (ncbi.pubmed_search, europepmc.search):
            try:
                found = search(query, 50, min_year=since, max_year=until)
            except Exception as exc:  # noqa: BLE001
                log.warning("update: search failed for %r: %s", query, exc)
                continue
            for rank, pmid in enumerate(found):
                votes[pmid] = votes.get(pmid, 0.0) + 1.0 / (10 + rank)
    # Papers that cite the entry's existing references are the likeliest follow-ups.
    for paper in baseline:
        try:
            citing = europepmc.citations(paper.pmid, limit=200)
        except Exception as exc:  # noqa: BLE001
            log.warning("update: citation lookup failed for %s: %s", paper.pmid, exc)
            continue
        for pmid in citing:
            votes[pmid] = votes.get(pmid, 0.0) + 0.05

    pool = [p for p, _ in sorted(votes.items(), key=lambda kv: -kv[1]) if p not in exclude][:pool_size]
    papers = [p for p in ncbi.pubmed_fetch(pool)
              if p.year and p.year >= since and (until is None or p.year <= until)]
    scores = _triage(seed, papers, llm)
    return papers, scores, queries


def propose_updates(
    mim: str, run_name: str = "updates", since: int | None = None, max_papers: int = 15,
    as_of: int | None = None,
) -> dict[str, Any]:
    from .gold import build_gold, seed_from_gold
    from .sources.fulltext import load_papers

    settings = get_settings()
    out_dir = settings.runs / run_name / (f"{mim}-asof{as_of}" if as_of else mim)
    llm = LLM(settings)

    gold = build_gold(mim)
    seed = seed_from_gold(gold)
    cited = load_papers(gold.cited_pmids, with_fulltext=True)

    if as_of:
        # Back-test: the entry as it stood before `as_of`; the later references are held out.
        baseline = [p for p in cited if p.year and p.year < as_of]
        held_out = [p.pmid for p in cited if p.year and p.year >= as_of]
        since, until, exclude = as_of, seed.max_year, {p.pmid for p in baseline}
    else:
        baseline, held_out = cited, []
        since = since or seed.max_year or 0
        until, exclude = None, set(gold.cited_pmids)
    if not baseline:
        raise ValueError(f"{mim}: no baseline references before {as_of}; choose a later --as-of year")

    seed.max_year = None
    log.info("[%s] baseline: %d references; screening literature from %s", mim, len(baseline), since)
    base_extractions = extract_papers(seed, baseline, llm)
    ground_phenotypes(base_extractions, llm)
    base_kg = build_graph(seed, baseline, base_extractions)
    known, _ = _kg_context(base_kg)

    screened, scores, queries = _candidates(seed, baseline, llm, since, until, exclude)
    chosen_ids = [p.pmid for p in sorted(screened, key=lambda p: -scores.get(p.pmid, 0))
                  if scores.get(p.pmid, 0) >= 2][:max_papers]
    chosen = load_papers(chosen_ids, with_fulltext=True)
    log.info("[%s] %d papers screened, %d read in full", mim, len(screened), len(chosen))

    new_extractions = extract_papers(seed, chosen, llm)
    ground_phenotypes(new_extractions, llm)
    by_pmid = {p.pmid: p for p in chosen}

    prompts, subjects = [], []
    for ex in new_extractions:
        if ex.relevance == "not_relevant" or not ex.findings:
            continue
        paper = by_pmid[ex.pmid]
        findings = "\n".join(f"[{f.id}] ({f.section}) {f.statement}" for f in ex.findings)
        prompts.append(
            f"{_header(seed)}\n\n<existing_evidence>\n{known}\n</existing_evidence>\n\n"
            f"New paper: {paper.label}, PMID {paper.pmid} ({paper.content_level}). {paper.title}\n"
            f"<new_findings>\n{findings}\n</new_findings>"
        )
        subjects.append(ex)
    replies = llm.map("update", UPDATE_SYSTEM, prompts, XProposal)

    proposals: list[dict[str, Any]] = []
    draft = GeneratedEntry(mim=mim, title=seed.title, entry_type=seed.entry_type)
    for ex, reply in zip(subjects, replies):
        if isinstance(reply, Exception) or reply.priority == "none":
            continue
        valid_ids = {f.id for f in ex.findings}
        paragraphs = []
        for n, xp in enumerate(reply.paragraphs, 1):
            ids = [i for i in xp.finding_ids if i in valid_ids]
            if not ids or not xp.text.strip():
                continue  # same rule as the writer: no finding, no paragraph
            para = EntryParagraph(id=f"{ex.pmid}.{n}", text=xp.text.strip(), pmids=[ex.pmid], finding_ids=ids)
            paragraphs.append((xp.section, para))
            draft.sections.append(EntrySection(name=xp.section, paragraphs=[para]))
        if not paragraphs:
            continue
        paper = by_pmid[ex.pmid]
        proposals.append({
            "pmid": ex.pmid, "citation": paper.reference, "label": paper.label, "year": paper.year,
            "content_level": paper.content_level, "priority": reply.priority,
            "update_types": reply.update_types, "rationale": reply.rationale,
            "paragraphs": paragraphs,
            "evidence": [{"id": f.id, "statement": f.statement, "quotes": f.quotes} for f in ex.findings],
        })

    # Audit every drafted paragraph against its paper, exactly as for a full entry.
    verify_entry(draft, by_pmid, llm)
    for proposal in proposals:
        proposal["paragraphs"] = [
            {"section": section, "text": para.text, "finding_ids": para.finding_ids, "status": para.status,
             "checks": [c.model_dump() for c in para.checks]}
            for section, para in proposal["paragraphs"]
        ]
    order = {"high": 0, "medium": 1, "low": 2}
    proposals.sort(key=lambda p: (order[p["priority"]], -(p["year"] or 0)))

    result: dict[str, Any] = {
        "mim": mim, "title": gold.title, "since": since, "as_of": as_of, "queries": queries,
        "n_baseline": len(baseline), "n_screened": len(screened), "n_read": len(chosen),
        "proposals": proposals,
    }
    if as_of:
        proposed = {p["pmid"] for p in proposals}
        result["backtest"] = {
            "held_out": held_out,
            "screened": prf({p.pmid for p in screened}, set(held_out)),
            "read": prf(set(chosen_ids), set(held_out)),
            "proposed": prf(proposed, set(held_out)),
            "found": sorted(proposed & set(held_out)),
            "missed": sorted(set(held_out) - proposed),
        }
    _write(out_dir / "updates.json", result)
    _write(out_dir / "updates.md", updates_markdown(result))
    _write(out_dir / "papers.json", [_paper_record(p) for p in chosen])
    _write(out_dir / "usage.json", llm.usage.summary())
    result["path"] = str(out_dir / "updates.md")
    return result


def suggest_as_of(years: list[int]) -> int | None:
    """A cut-off year for a back-test: hold out roughly the latest third of the references.

    Needs at least two references before the cut-off (something to build the
    baseline from) and at least one from the cut-off year on (something to find).
    """
    years = sorted(y for y in years if y)
    if len(years) < 3:
        return None
    for cut in sorted(set(years), key=lambda y: abs(sum(1 for x in years if x >= y) - len(years) / 3)):
        before, after = sum(1 for x in years if x < cut), sum(1 for x in years if x >= cut)
        if before >= 2 and after >= 1:
            return cut
    return None


def backtest(mims: list[str], run_name: str = "backtest", max_papers: int = 10) -> dict[str, Any]:
    """Back-test update discovery over several entries and pool the result."""
    from .gold import build_gold
    from .sources.ncbi import pubmed_fetch

    rows, held, found, proposed = [], 0, 0, 0
    for mim in mims:
        gold = build_gold(mim)
        cut = suggest_as_of([p.year for p in pubmed_fetch(gold.cited_pmids) if p.year])
        if cut is None:
            log.info("[%s] skipped: references do not span enough years for a back-test", mim)
            continue
        try:
            result = propose_updates(mim, run_name, max_papers=max_papers, as_of=cut)
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            log.warning("[%s] back-test failed: %s", mim, exc)
            continue
        b = result["backtest"]
        held += len(b["held_out"])
        found += len(b["found"])
        proposed += len(result["proposals"])
        rows.append({"mim": mim, "title": result["title"], "as_of": cut, "n_baseline": result["n_baseline"],
                     "held_out": len(b["held_out"]), "found": len(b["found"]),
                     "screened_recall": b["screened"]["recall"], "n_screened": result["n_screened"],
                     "n_proposals": len(result["proposals"]),
                     "paragraphs_flagged": sum(1 for p in result["proposals"] for x in p["paragraphs"]
                                               if x["status"] == "flagged")})
    summary = {
        "entries": rows, "n_entries": len(rows), "held_out": held, "found": found,
        "recall": round(found / held, 3) if held else None,
        "n_proposals": proposed, "proposals_not_in_omim": proposed - found,
    }
    _write(get_settings().runs / run_name / "backtest.json", summary)
    return summary


def updates_markdown(result: dict[str, Any]) -> str:
    out = [f"# Proposed updates for OMIM {result['mim']}: {result['title']}",
           f"Literature from {result['since']} onwards that the entry does not cite: {result['n_screened']} papers "
           f"screened, {result['n_read']} read, {len(result['proposals'])} proposal(s). Each proposal is a draft for "
           f"a curator to accept, edit or reject."]
    if result.get("backtest"):
        b = result["backtest"]
        out.append(f"**Back-test as of {result['as_of']}.** OMIM's curators later added {len(b['held_out'])} "
                   f"reference(s) from that year on; this run proposed {len(b['found'])} of them "
                   f"(recall {b['proposed']['recall']}), and {b['proposed']['n_predicted'] - b['proposed']['tp']} "
                   f"paper(s) OMIM does not cite.")
    badge = {"supported": "", "partial": " ⚠︎", "flagged": " ✗", "unverified": " (unverified)"}
    for p in result["proposals"]:
        out.append(f"## [{p['priority'].upper()}] {p['label']} — {', '.join(p['update_types'])}")
        out.append(f"{p['citation']} *(read: {p['content_level']})*")
        out.append(f"**Why:** {p['rationale']}")
        for para in p["paragraphs"]:
            out.append(f"*{para['section']}*{badge.get(para['status'], '')}: {para['text']}")
    return "\n\n".join(out) + "\n"
