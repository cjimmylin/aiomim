"""Stage 6: audit the written entry against the papers it cites.

This is an independent second reading. The verifier is not shown the extracted
findings or the knowledge graph; for each cited paper it gets the paper's text and
the paragraphs of the entry that cite it, breaks them into atomic claims, and
labels each claim against the text. Any quote it offers as evidence is then
checked against the source without a model, exactly as extraction quotes are.

`repair_entry` gives the writer one chance to fix what the audit flagged, and the
changed paragraphs are audited again.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from .grounding import SourceIndex
from .llm import LLM
from .models import ClaimCheck, EntryParagraph, GeneratedEntry, Paper, squash

log = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 180_000

VERIFY_SYSTEM = """\
You are auditing a draft entry for OMIM (Online Mendelian Inheritance in Man) against one of the \
papers it cites. You are given the paper's text and the draft paragraphs that cite this paper. Decide, \
claim by claim, whether the paper supports what the draft says about it.

For each paragraph, break out the atomic factual claims that the paragraph attributes to THIS paper: \
who was studied and how many, ancestry, ages, each clinical, imaging or laboratory finding, each \
variant with its nucleotide and protein change, zygosity, segregation, functional results, and the \
conclusions drawn. A paragraph may also cite other papers; skip any claim it clearly attributes to a \
different paper. Judge each claim only against the supplied text, not against what you know of the \
subject:

supported            the text states it, or it follows directly and unambiguously from what is stated.
partially_supported  the gist is there but a detail is missing, vaguer in the paper, or slightly off.
unsupported          the text supplied does not contain it.
contradicted         the text states something incompatible (a different number, variant, zygosity, \
finding or conclusion).

Be exact about details that matter in genetics: a wrong nucleotide position, amino acid, zygosity, \
patient count or age is a contradiction, not a partial match. Equivalent notations for the same variant \
(for example "c.367C-T" and "c.367C>T", or "arg123-to-trp", "R123W" and "p.Arg123Trp") are the same \
claim. Standard nomenclature in the draft that merely restates the paper (a gene's approved symbol in \
place of an alias) is supported. If only the abstract was supplied, a detail that would be in the full \
text but is absent from the abstract is unsupported: say so in the explanation.

For supported and partially_supported claims, give in `evidence_quote` the passage that supports the \
claim, copied character for character from the paper text (one continuous span, at most about 50 \
words). For unsupported and contradicted claims, `explanation` says briefly what is missing or what \
the paper says instead; for contradicted claims also quote the conflicting passage.\
"""


class XClaim(BaseModel):
    claim: str
    verdict: Literal["supported", "partially_supported", "unsupported", "contradicted"]
    evidence_quote: str
    explanation: str


class XParagraphAudit(BaseModel):
    paragraph_id: str
    claims: list[XClaim]


class XAudit(BaseModel):
    paragraphs: list[XParagraphAudit]


def _audit_prompt(paper: Paper, paragraphs: list[EntryParagraph]) -> tuple[str, str]:
    source = paper.source_text(MAX_SOURCE_CHARS)
    available = {"fulltext": "full text", "abstract": "abstract only", "title": "title only"}[paper.content_level]
    listing = "\n\n".join(f'<paragraph id="{p.id}">\n{p.text}\n</paragraph>' for p in paragraphs)
    prompt = (
        f"Paper under audit: {paper.label}, PMID {paper.pmid} (text supplied: {available}).\n\n"
        f"<paper>\n{source}\n</paper>\n\n"
        f"Draft paragraphs citing this paper:\n\n{listing}"
    )
    return prompt, source


def verify_entry(
    entry: GeneratedEntry, papers: dict[str, Paper], llm: LLM, only: set[str] | None = None
) -> dict[str, int]:
    """Attach `checks` to each paragraph (all of them, or just the ids in `only`).

    Returns verdict counts for the claims judged in this call.
    """
    by_pmid: dict[str, list[EntryParagraph]] = defaultdict(list)
    for para in entry.all_paragraphs():
        if only is not None and para.id not in only:
            continue
        para.checks = []
        for pmid in para.pmids:
            if pmid in papers:
                by_pmid[pmid].append(para)

    pmids = sorted(by_pmid)
    built = [_audit_prompt(papers[pmid], by_pmid[pmid]) for pmid in pmids]
    replies = llm.map("verify", VERIFY_SYSTEM, [b[0] for b in built], XAudit)

    counts: dict[str, int] = defaultdict(int)
    for pmid, (_, source), reply in zip(pmids, built, replies):
        paras = {p.id: p for p in by_pmid[pmid]}
        if isinstance(reply, Exception):
            log.warning("verify: PMID %s failed: %s", pmid, reply)
            for para in paras.values():
                para.checks.append(ClaimCheck(claim="(audit failed for this paper)", pmid=pmid,
                                              verdict="not_checkable", explanation=str(reply)[:200]))
                counts["not_checkable"] += 1
            continue
        index = SourceIndex(source)
        for audit in reply.paragraphs:
            para = paras.get(audit.paragraph_id)
            if para is None:
                continue
            for c in audit.claims:
                verdict, explanation = c.verdict, squash(c.explanation)
                quote = squash(c.evidence_quote)
                # A "supported" verdict resting on a quote that is not in the paper is
                # itself unverified; downgrade it rather than trust it.
                if verdict == "supported" and (not quote or not index.contains(quote)):
                    verdict = "partially_supported"
                    explanation = (explanation + " " if explanation else "") + \
                        "[auditor's evidence quote was not found verbatim in the source]"
                para.checks.append(ClaimCheck(claim=squash(c.claim), pmid=pmid, verdict=verdict,
                                              evidence_quote=quote, explanation=explanation))
                counts[verdict] += 1
    return dict(counts)


def verdict_counts(entry: GeneratedEntry) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for para in entry.all_paragraphs():
        for check in para.checks:
            counts[check.verdict] += 1
    return dict(counts)


# --------------------------------------------------------------------------- #
# Repair
# --------------------------------------------------------------------------- #

REPAIR_SYSTEM = """\
You are revising paragraphs of a draft OMIM entry after an audit against the cited papers. For each \
paragraph you are given its text and the auditor's notes on the claims that the paper did not support \
or that it contradicted.

Rewrite each paragraph so that every flagged claim is either corrected to what the auditor reports the \
paper says, or removed. Change nothing else: keep the supported content, the attribution and the OMIM \
style, and do not add any fact that is not already in the paragraph or in the auditor's notes. If \
nothing supported remains, return an empty text for that paragraph.\
"""


class XRevision(BaseModel):
    paragraph_id: str
    text: str = Field(description="The revised paragraph, or an empty string to delete it")


class XRevisions(BaseModel):
    paragraphs: list[XRevision]


def repair_entry(entry: GeneratedEntry, papers: dict[str, Paper], llm: LLM) -> dict[str, int]:
    """One revise-and-recheck round over paragraphs with unsupported or contradicted claims."""
    flagged = [p for p in entry.all_paragraphs() if p.status == "flagged"]
    if not flagged:
        return {"flagged": 0, "revised": 0, "deleted": 0}

    blocks = []
    for para in flagged:
        notes = "\n".join(
            f"- [{c.verdict}] {c.claim} :: {c.explanation}"
            + (f' :: paper says: "{c.evidence_quote}"' if c.evidence_quote else "")
            for c in para.checks if c.verdict in ("unsupported", "contradicted")
        )
        blocks.append(f'<paragraph id="{para.id}">\n{para.text}\n</paragraph>\nAuditor notes:\n{notes}')
    reply = llm.call("synthesize", REPAIR_SYSTEM, "\n\n".join(blocks), XRevisions)

    by_id = {p.id: p for p in flagged}
    revised: set[str] = set()
    deleted: set[str] = set()
    for rev in reply.paragraphs:
        para = by_id.get(rev.paragraph_id)
        if para is None:
            continue
        text = squash(rev.text)
        if not text:
            deleted.add(para.id)
        elif text != para.text:
            para.text = text
            revised.add(para.id)

    if deleted:
        if entry.intro and entry.intro.id in deleted:
            entry.intro = None
        for section in entry.sections:
            section.paragraphs = [p for p in section.paragraphs if p.id not in deleted]
        entry.sections = [s for s in entry.sections if s.paragraphs]
        for av in entry.allelic_variants:
            av.paragraphs = [p for p in av.paragraphs if p.id not in deleted]
        entry.allelic_variants = [av for av in entry.allelic_variants if av.paragraphs]
    if revised:
        verify_entry(entry, papers, llm, only=revised)
    entry.meta["repair"] = {"flagged": len(flagged), "revised": len(revised), "deleted": len(deleted)}
    return entry.meta["repair"]
