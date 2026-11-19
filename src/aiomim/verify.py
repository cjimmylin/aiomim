"""Stage 6: audit the written entry against the papers it cites.

This is an independent second reading. The auditor is not shown the extracted
findings or the knowledge graph. It works in two steps:

1. Each paragraph is split into atomic claims, and each claim is tagged with the
   cited paper(s) the paragraph presents as its source. A summary sentence that
   draws on several papers is tagged with all of them.
2. Each paper's text is read once, together with the claims attributed to it,
   and every claim is labelled supported / partially supported / unsupported /
   contradicted, with the passage that decides it.

A claim's final verdict is the best one it earned from any paper it was
attributed to, so a sentence resting on three papers is not marked wrong because
each paper alone covers only part of it. Any quote the auditor offers as evidence
is checked against the source without a model, exactly as extraction quotes are.

`repair_entry` gives the writer one chance to fix what the audit flagged, and the
changed paragraphs are audited again.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from .grounding import SourceIndex
from .llm import LLM, LLMLimitReached
from .models import ClaimCheck, EntryParagraph, GeneratedEntry, Paper, squash

log = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 180_000
DECOMPOSE_BATCH = 25

# --------------------------------------------------------------------------- #
# Step 1: paragraphs -> attributed atomic claims
# --------------------------------------------------------------------------- #

DECOMPOSE_SYSTEM = """\
You are preparing a draft entry for OMIM (Online Mendelian Inheritance in Man) for a fact-check. For \
each paragraph you are given its text and the papers it cites. Split the paragraph into atomic factual \
claims and say which cited paper(s) each claim is attributed to.

An atomic claim is one checkable assertion: who was studied and how many, ancestry, an age, one \
clinical, imaging or laboratory finding, one variant with its nucleotide and protein change, its \
zygosity, segregation or de novo status, one functional result, one conclusion. Write each claim as a \
self-contained sentence that can be checked without the rest of the paragraph: name the patients, \
family, gene or variant it is about instead of using "they" or "the mutation". Cover everything the \
paragraph asserts, and add nothing it does not say. Do not make a claim out of the bare fact that a \
paper exists or was cited.

`pmids`: the paper(s) the paragraph presents as the source of that claim, chosen from the papers \
listed for that paragraph. When the text names the authors ("Jun et al. (1994) found ...") the claim \
belongs to that paper alone. When a statement is a general summary not tied to particular authors, or \
is explicitly attributed to several papers, list every paper it could rest on.\
"""


class XAttributedClaim(BaseModel):
    text: str
    pmids: list[str]


class XParagraphClaims(BaseModel):
    paragraph_id: str
    claims: list[XAttributedClaim]


class XClaimSets(BaseModel):
    paragraphs: list[XParagraphClaims]


def _decompose(paragraphs: list[EntryParagraph], papers: dict[str, Paper], llm: LLM) -> dict[str, list[XAttributedClaim]]:
    """paragraph id -> its claims, each attributed to a non-empty subset of the paragraph's PMIDs."""
    prompts, batches = [], []
    for start in range(0, len(paragraphs), DECOMPOSE_BATCH):
        batch = paragraphs[start:start + DECOMPOSE_BATCH]
        batches.append(batch)
        prompts.append("\n\n".join(
            f'<paragraph id="{p.id}">\n{p.text}\n</paragraph>\nPapers cited: '
            + "; ".join(f"{pmid} = {papers[pmid].label}" for pmid in p.checked_pmids if pmid in papers)
            for p in batch
        ))
    out: dict[str, list[XAttributedClaim]] = {}
    replies = llm.map("verify", DECOMPOSE_SYSTEM, prompts, XClaimSets)
    for i, (batch, reply) in enumerate(zip(batches, replies)):
        # A reply that names none of the batch's paragraphs is a reply cut short,
        # not a batch without claims. Ask once more, past the cache.
        ids = {p.id for p in batch}
        if not isinstance(reply, Exception) and not any(item.paragraph_id in ids for item in reply.paragraphs):
            try:
                replies[i] = llm.call("verify", DECOMPOSE_SYSTEM, prompts[i], XClaimSets, use_cache=False)
            except LLMLimitReached:
                raise
            except Exception as exc:  # noqa: BLE001 - recorded like any other failed batch
                replies[i] = exc
    for batch, reply in zip(batches, replies):
        if isinstance(reply, Exception):
            log.warning("verify: claim extraction failed for %d paragraphs: %s", len(batch), reply)
            continue
        by_id = {p.id: p for p in batch}
        for item in reply.paragraphs:
            para = by_id.get(item.paragraph_id)
            if para is None:
                continue
            cited = [pmid for pmid in para.checked_pmids if pmid in papers]
            claims = []
            for claim in item.claims:
                text = squash(claim.text)
                if not text:
                    continue
                # An attribution outside the paragraph's own citations is not usable;
                # fall back to checking the claim against everything the paragraph cites.
                pmids = [p for p in dict.fromkeys(claim.pmids) if p in cited] or cited
                claims.append(XAttributedClaim(text=text, pmids=pmids))
            out[para.id] = claims
    return out


# --------------------------------------------------------------------------- #
# Step 2: one paper, the claims attributed to it
# --------------------------------------------------------------------------- #

VERIFY_SYSTEM = """\
You are fact-checking a draft entry for OMIM (Online Mendelian Inheritance in Man) against one of the \
papers it cites. You are given the paper's text and a numbered list of claims that the draft \
attributes to this paper, each shown under the draft paragraph it comes from. Decide for every claim \
whether the paper supports it. Judge only against the supplied text, not against what you know of the \
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
place of an alias, a gene's MIM number or chromosomal location) is supported. A claim may also rest on \
other papers; if this paper simply does not address it, answer unsupported. If only the abstract was \
supplied, a detail that would be in the full text but is absent from the abstract is unsupported: say \
so in the explanation.

Return one verdict for every claim id you were given. For supported and partially_supported claims, \
give in `evidence_quote` the passage that supports the claim, copied character for character from the \
paper text (one continuous span, at most about 50 words). For unsupported and contradicted claims, \
`explanation` says briefly what is missing or what the paper says instead; for contradicted claims \
also quote the conflicting passage.\
"""

VerdictName = Literal["supported", "partially_supported", "unsupported", "contradicted"]


class XVerdict(BaseModel):
    claim_id: str = Field(description='The id shown in brackets before the claim, e.g. "clinical_features.2#3"')
    verdict: VerdictName
    evidence_quote: str
    explanation: str


class XAudit(BaseModel):
    verdicts: list[XVerdict]


def _audit_prompt(paper: Paper, items: list[tuple[EntryParagraph, list[tuple[str, str]]]]) -> tuple[str, str]:
    source = paper.source_text(MAX_SOURCE_CHARS)
    available = {"fulltext": "full text", "abstract": "abstract only", "title": "title only"}[paper.content_level]
    blocks = []
    for para, claims in items:
        listing = "\n".join(f"[{claim_id}] {text}" for claim_id, text in claims)
        blocks.append(f'<paragraph id="{para.id}">\n{para.text}\n</paragraph>\nClaims attributed to this paper:\n{listing}')
    prompt = (
        f"Paper: {paper.label}, PMID {paper.pmid} (text supplied: {available}).\n\n"
        f"<paper>\n{source}\n</paper>\n\n" + "\n\n".join(blocks)
    )
    return prompt, source


_RANK = {"supported": 3, "partially_supported": 2, "contradicted": 1, "unsupported": 0}


def verify_entry(
    entry: GeneratedEntry, papers: dict[str, Paper], llm: LLM, only: set[str] | None = None
) -> dict[str, int]:
    """Attach `checks` to each paragraph (all of them, or just the ids in `only`).

    Returns verdict counts for the claims judged in this call.
    """
    targets = [p for p in entry.all_paragraphs()
               if (only is None or p.id in only) and any(pmid in papers for pmid in p.checked_pmids)]
    for para in targets:
        para.checks = []
    if not targets:
        return {}
    claims_by_para = _decompose(targets, papers, llm)

    # Regroup: for each paper, the claims attributed to it, kept under their paragraph.
    per_paper: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    claim_text: dict[str, str] = {}
    claim_pmids: dict[str, list[str]] = {}
    by_id = {p.id: p for p in targets}
    for para_id, claims in claims_by_para.items():
        for n, claim in enumerate(claims, 1):
            claim_id = f"{para_id}#{n}"
            claim_text[claim_id], claim_pmids[claim_id] = claim.text, claim.pmids
            for pmid in claim.pmids:
                per_paper[pmid][para_id].append((claim_id, claim.text))

    pmids = sorted(per_paper)
    built = [
        _audit_prompt(papers[pmid], [(by_id[para_id], claims) for para_id, claims in per_paper[pmid].items()])
        for pmid in pmids
    ]
    replies = llm.map("verify", VERIFY_SYSTEM, [b[0] for b in built], XAudit)

    # Collect every paper's verdict on every claim, then keep the best per claim.
    judged: dict[str, list[ClaimCheck]] = defaultdict(list)
    for pmid, (_, source), reply in zip(pmids, built, replies):
        if isinstance(reply, Exception):
            log.warning("verify: PMID %s failed: %s", pmid, reply)
            continue
        index = SourceIndex(source)
        for v in reply.verdicts:
            claim_id = v.claim_id.strip().strip("[]")
            if claim_id not in claim_text or pmid not in claim_pmids[claim_id]:
                continue
            verdict, explanation, quote = v.verdict, squash(v.explanation), squash(v.evidence_quote)
            # A "supported" verdict resting on a quote that is not in the paper is
            # itself unverified; downgrade it rather than trust it.
            if verdict == "supported" and (not quote or not index.contains(quote)):
                verdict = "partially_supported"
                explanation = (explanation + " " if explanation else "") + \
                    "[auditor's evidence quote was not found verbatim in the source]"
            judged[claim_id].append(ClaimCheck(claim=claim_text[claim_id], pmid=pmid, verdict=verdict,
                                               evidence_quote=quote, explanation=explanation))

    counts: dict[str, int] = defaultdict(int)
    for para in targets:
        claims = claims_by_para.get(para.id)
        if claims is None:
            para.checks.append(ClaimCheck(claim="(this paragraph could not be audited)", verdict="not_checkable"))
            counts["not_checkable"] += 1
            continue
        for n, claim in enumerate(claims, 1):
            results = judged.get(f"{para.id}#{n}", [])
            if not results:
                check = ClaimCheck(claim=claim.text, pmid=claim.pmids[0] if claim.pmids else "",
                                   verdict="not_checkable", explanation="the audit returned no verdict for this claim")
            else:
                check = max(results, key=lambda c: _RANK[c.verdict])
                if check.verdict in ("unsupported", "contradicted") and len(claim.pmids) > 1:
                    check.explanation = (f"not supported by any of the {len(claim.pmids)} cited papers. "
                                         + check.explanation).strip()
            para.checks.append(check)
            counts[check.verdict] += 1
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
You are revising paragraphs of a draft OMIM entry after a fact-check against the cited papers. For \
each paragraph you are given its text and the checker's notes on the claims that the cited paper(s) \
did not support or that they contradicted.

Rewrite each paragraph so that every flagged claim is either corrected to what the checker reports the \
paper says, or removed. Change nothing else: keep the supported content, the attribution and the OMIM \
style, and do not add any fact that is not already in the paragraph or in the checker's notes. If \
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
        entry.meta["repair"] = {"flagged": 0, "revised": 0, "deleted": 0}
        return entry.meta["repair"]

    blocks = []
    for para in flagged:
        notes = "\n".join(
            f"- [{c.verdict}] {c.claim} :: {c.explanation}"
            + (f' :: paper says: "{c.evidence_quote}"' if c.evidence_quote else "")
            for c in para.checks if c.verdict in ("unsupported", "contradicted")
        )
        blocks.append(f'<paragraph id="{para.id}">\n{para.text}\n</paragraph>\nChecker notes:\n{notes}')
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
