"""Stage 7: score a generated entry against the gold standard.

Gold comes from public, OMIM-derived sources (see gold.py):

references      OMIM's reference list for the entry              (NCBI E-utilities)
genes           OMIM's gene-phenotype links                      (NCBI mim2gene_medgen, MedGen)
inheritance     mode of inheritance                              (HPO annotations, MedGen)
synopsis        clinical synopsis as HPO terms                   (HPO phenotype.hpoa)
variants        OMIM allelic variants                            (ClinVar, submitter OMIM)
gold_text       OMIM's own per-paper paragraphs                  (ClinVar, submitter OMIM)
omim_text       full entry text, only with an OMIM API key       (api.omim.org)

plus one score that needs no gold at all:

faithfulness    share of the entry's claims the audit found supported by the cited paper.

Set metrics report precision, recall and F1. Text is compared by a judge model
that splits the curator's paragraph into atomic facts and looks for each in the
draft; wording is ignored, facts are not.
"""

from __future__ import annotations

import logging
import math
import re
from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel

from .kg import is_mito_gene, nucleotide_key, protein_key
from .llm import LLM
from .models import (
    INHERITANCE_COARSE,
    GeneratedEntry,
    GoldEntry,
    GoldParagraph,
    Paper,
)

log = logging.getLogger(__name__)

PHENOTYPE_ROOT = "HP:0000118"

# --------------------------------------------------------------------------- #
# Set metrics
# --------------------------------------------------------------------------- #


def prf(predicted: set, gold: set) -> dict[str, Any]:
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else None
    recall = tp / len(gold) if gold else None
    if precision is None or recall is None:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    rnd = lambda x: None if x is None else round(x, 3)  # noqa: E731
    return {"precision": rnd(precision), "recall": rnd(recall), "f1": rnd(f1),
            "tp": tp, "n_predicted": len(predicted), "n_gold": len(gold)}


def eval_references(entry: GeneratedEntry, gold: GoldEntry, offered: list[str] | None = None) -> dict[str, Any]:
    """Cited PMIDs against OMIM's reference list.

    With oracle retrieval the writer was handed exactly OMIM's list, so recall here
    reads as "how much of the offered literature the entry actually used". With
    open retrieval it is a genuine retrieval score, and `retrieved` scores the
    candidate set before writing.
    """
    out = {"cited": prf(set(entry.cited_pmids()), set(gold.cited_pmids))}
    if offered is not None:
        out["retrieved"] = prf(set(offered), set(gold.cited_pmids))
    return out


def eval_genes(entry: GeneratedEntry, gold: GoldEntry) -> dict[str, Any]:
    predicted = {r.gene_symbol.upper() for r in entry.relationships if r.gene_symbol}
    expected = {g.symbol.upper() for g in gold.genes if g.symbol}
    return {**prf(predicted, expected), "predicted": sorted(predicted), "gold": sorted(expected)}


def eval_inheritance(entry: GeneratedEntry, gold: GoldEntry) -> dict[str, Any]:
    coarse = lambda codes: {INHERITANCE_COARSE[c] for c in codes if c in INHERITANCE_COARSE}  # noqa: E731
    predicted, expected = coarse(entry.inheritance), coarse(gold.inheritance)
    return {**prf(predicted, expected), "predicted": sorted(entry.inheritance), "gold": sorted(gold.inheritance),
            "match": None if not expected else predicted == expected}


# --------------------------------------------------------------------------- #
# Clinical synopsis (HPO)
# --------------------------------------------------------------------------- #


def _closure(terms: set[str], hpo) -> set[str]:
    """Terms plus all their ancestors within the phenotype branch (root excluded)."""
    out: set[str] = set()
    for term in terms:
        out |= {a for a in hpo.ancestors(term, include_self=True) if hpo.is_phenotype(a)}
    out.discard(PHENOTYPE_ROOT)
    return out


def _lin(a: str, b: str, hpo) -> float:
    if a == b:
        return 1.0
    common = hpo.ancestors(a, include_self=True) & hpo.ancestors(b, include_self=True)
    mica = max((hpo.information_content(t) for t in common), default=0.0)
    denom = hpo.information_content(a) + hpo.information_content(b)
    return 2 * mica / denom if denom > 0 else 0.0


def _best_match_average(source: set[str], target: set[str], hpo) -> float | None:
    if not source or not target:
        return None
    return round(sum(max(_lin(s, t, hpo) for t in target) for s in source) / len(source), 3)


def eval_synopsis(entry: GeneratedEntry, gold: GoldEntry) -> dict[str, Any]:
    """HPO terms of the generated clinical synopsis against HPO's annotations of the OMIM entry.

    exact         identical term ids.
    hierarchical  both sets expanded with their ancestors, so "optic atrophy" earns
                  credit against "abnormality of the optic nerve" and vice versa.
    semantic      best-match average of Lin similarity (information content from
                  the OMIM annotation corpus): for recall, each gold term is paired
                  with its most similar predicted term; precision is the reverse.
    """
    from .sources.hpo import get_hpo

    hpo = get_hpo()

    def clean(ids) -> set[str]:
        resolved = {hpo.resolve(i) for i in ids}
        return {i for i in resolved if i and hpo.is_phenotype(i) and i != PHENOTYPE_ROOT}

    predicted = clean(i.hpo_id for i in entry.clinical_synopsis if i.hpo_id)
    expected = clean(a.hpo_id for a in gold.hpo_annotations if a.aspect == "P" and a.qualifier.upper() != "NOT")
    semantic_p = _best_match_average(predicted, expected, hpo)
    semantic_r = _best_match_average(expected, predicted, hpo)
    semantic_f = None
    if semantic_p is not None and semantic_r is not None:
        semantic_f = round(2 * semantic_p * semantic_r / (semantic_p + semantic_r), 3) if semantic_p + semantic_r else 0.0
    return {
        "exact": prf(predicted, expected),
        "hierarchical": prf(_closure(predicted, hpo), _closure(expected, hpo)),
        "semantic": {"precision": semantic_p, "recall": semantic_r, "f1": semantic_f},
        "missed": sorted(f"{t} {hpo.label(t)}" for t in expected - predicted),
        "extra": sorted(f"{t} {hpo.label(t)}" for t in predicted - expected),
    }


# --------------------------------------------------------------------------- #
# Allelic variants
# --------------------------------------------------------------------------- #

_HGVS_PARTS = re.compile(r"([cgmnp]\.[^\s()]+)")


def _variant_keys(strings: list[str], gene: str) -> set[str]:
    """Canonical, prefix-free keys ('3697G>A', 'G131S') for any way of naming a variant."""
    mito = is_mito_gene(gene)
    keys: set[str] = set()
    for raw in strings:
        if not raw:
            continue
        # "GENE, ARG287TRP" -> "ARG287TRP"; "NM_x(GENE):c.859C>T (p.Arg287Trp)" -> both parts.
        tail = raw.split(",", 1)[1] if "," in raw and not raw.strip().startswith(("c.", "p.", "m.", "g.")) else raw
        parts = _HGVS_PARTS.findall(raw) + [tail] + re.split(r"[\s,;()/]+", tail)
        for part in parts:
            part = part.strip()
            if not part or not re.search(r"\d", part):
                continue
            for key in (nucleotide_key(part, mito), protein_key(part)):
                if key:
                    keys.add(key.split(".", 1)[1])
    return keys


MATCH_SYSTEM = """\
You are reconciling two lists of genetic variants that use different naming conventions. List A uses \
OMIM's allelic-variant names (for example "FBN1, 1-BP DEL, 1234A", "COL1A1, IVS5DS, G-A, +1", \
"SMAD3, ARG287TRP") together with ClinVar's HGVS name where there is one. List B uses HGVS-style \
names. Pair an item of A with an item of B only when they denote the same sequence change in the same \
gene: the same position and the same nucleotide or amino acid change. A different position, a \
different substituted residue, or a different gene is not a match. Leave items unpaired when unsure.\
"""


class XPair(BaseModel):
    a: int
    b: int


class XPairs(BaseModel):
    pairs: list[XPair]


def eval_variants(entry: GeneratedEntry, gold: GoldEntry, llm: LLM | None = None) -> dict[str, Any]:
    """How many of OMIM's allelic variants for this entry appear among the generated ones.

    Names are first matched on canonical keys. What that leaves unpaired (deletions,
    splice variants and other names the key parser does not cover) is offered to
    the judge model, which may pair items but cannot invent any.
    """
    gold_variants = gold.scoped_variants()
    generated = [(av, _variant_keys([av.name, *av.hgvs], av.gene_symbol)) for av in entry.allelic_variants]
    pairs: dict[int, int] = {}
    for gi, gv in enumerate(gold_variants):
        gkeys = _variant_keys([gv.name, gv.clinvar_name, gv.protein_change], gv.gene_symbol)
        hit = next((i for i, (_, keys) in enumerate(generated) if gkeys & keys and i not in pairs.values()), None)
        if hit is not None:
            pairs[gi] = hit

    open_gold = [gi for gi in range(len(gold_variants)) if gi not in pairs]
    open_generated = [i for i in range(len(generated)) if i not in pairs.values()]
    judged = 0
    if llm is not None and open_gold and open_generated:
        list_a = "\n".join(f"A{n}. {gold_variants[gi].name} | ClinVar: {gold_variants[gi].clinvar_name or 'n/a'}"
                           for n, gi in enumerate(open_gold, 1))
        list_b = "\n".join(f"B{n}. {generated[i][0].gene_symbol} {'; '.join(generated[i][0].hgvs) or ''} | "
                           f"{generated[i][0].name}" for n, i in enumerate(open_generated, 1))
        try:
            reply = llm.call("judge", MATCH_SYSTEM, f"List A\n{list_a}\n\nList B\n{list_b}", XPairs)
        except Exception as exc:  # noqa: BLE001 - fall back to key matching alone
            log.warning("variant matching by judge failed: %s", exc)
            reply = XPairs(pairs=[])
        for pair in reply.pairs:
            if 1 <= pair.a <= len(open_gold) and 1 <= pair.b <= len(open_generated):
                gi, i = open_gold[pair.a - 1], open_generated[pair.b - 1]
                if gi not in pairs and i not in pairs.values():
                    pairs[gi] = i
                    judged += 1

    # A generated variant that OMIM does list, but documents from a paper outside this
    # entry's reference list, is not "new": keep it apart from the genuinely unlisted.
    scoped_ids = {id(av) for av in gold_variants}
    other_keys = [_variant_keys([av.name, av.clinvar_name, av.protein_change], av.gene_symbol)
                  for av in gold.allelic_variants if id(av) not in scoped_ids]
    unmatched = [i for i in range(len(generated)) if i not in pairs.values()]
    listed_elsewhere = [i for i in unmatched if any(generated[i][1] & keys for keys in other_keys)]

    n_gold = len(gold_variants)
    return {
        "recall": round(len(pairs) / n_gold, 3) if n_gold else None,
        "n_gold": n_gold, "n_gold_out_of_scope": len(gold.allelic_variants) - n_gold,
        "n_generated": len(generated), "n_matched": len(pairs), "n_matched_by_judge": judged,
        "matched": [{"gold": f"{gold_variants[gi].omim_id} {gold_variants[gi].name}", "generated": generated[i][0].name}
                    for gi, i in sorted(pairs.items())],
        "missed": [f"{gv.omim_id} {gv.name}" for gi, gv in enumerate(gold_variants) if gi not in pairs],
        "in_omim_via_other_paper": [generated[i][0].name for i in listed_elsewhere],
        "not_in_omim": [generated[i][0].name for i in unmatched if i not in listed_elsewhere],
    }


# --------------------------------------------------------------------------- #
# Curator text: fact coverage by a judge model
# --------------------------------------------------------------------------- #

JUDGE_SYSTEM = """\
You are scoring a machine-drafted OMIM entry against text written by OMIM's own curators. You are \
given a REFERENCE passage (the curators' summary of one or more papers) and the DRAFT text that cites \
the same paper(s).

Split the reference into atomic facts: single checkable assertions such as who was studied, how many \
patients or families, ancestry, each clinical, imaging or laboratory finding, each variant with its \
nucleotide change, protein change and zygosity, segregation or de novo status, each functional \
result, and each conclusion. Then decide for every fact whether the draft conveys it:

present       the draft states the same fact.
partial       the draft conveys the fact less precisely or incompletely.
absent        the draft does not mention it.
contradicted  the draft states something incompatible with it.

Judge meaning, not wording. Treat equivalent notations as the same fact ("3697G-A", "c.3697G>A" and \
"m.3697G>A"; "gly131-to-ser", "G131S" and "p.Gly131Ser"; a gene's alias and its approved symbol; \
"mental retardation" and "intellectual disability"). Do not make facts out of OMIM's own cross-reference \
numbers in parentheses such as "(540000)" or "(590050.0001)", or out of the bare attribution to the \
authors; the draft is not expected to reproduce those. Keep each fact short, and add a brief `note` \
only for partial and contradicted facts, saying what differs.\
"""


class XFact(BaseModel):
    fact: str
    status: Literal["present", "partial", "absent", "contradicted"]
    note: str


class XFacts(BaseModel):
    facts: list[XFact]


def _tally(facts: list[dict[str, str]]) -> dict[str, Any]:
    counts = defaultdict(int)
    for f in facts:
        counts[f["status"]] += 1
    n = len(facts)
    return {
        "n_facts": n, "present": counts["present"], "partial": counts["partial"],
        "absent": counts["absent"], "contradicted": counts["contradicted"],
        "coverage": round((counts["present"] + 0.5 * counts["partial"]) / n, 3) if n else None,
        "strict_coverage": round(counts["present"] / n, 3) if n else None,
        "contradiction_rate": round(counts["contradicted"] / n, 3) if n else None,
    }


def fact_coverage(pairs: list[tuple[str, str]], llm: LLM) -> list[list[dict[str, str]]]:
    """For each (reference, draft) pair, the reference's facts labelled against the draft."""
    prompts = [
        f"<reference>\n{reference}\n</reference>\n\n<draft>\n{draft or '(the draft has no text citing these papers)'}\n</draft>"
        for reference, draft in pairs
    ]
    replies = llm.map("judge", JUDGE_SYSTEM, prompts, XFacts)
    out = []
    for reply in replies:
        if isinstance(reply, Exception):
            log.warning("judge: comparison failed: %s", reply)
            out.append([])
        else:
            out.append([f.model_dump() for f in reply.facts])
    return out


def _draft_text_for(entry: GeneratedEntry, pmids: list[str]) -> str:
    wanted = set(pmids)
    chunks = []
    for section in entry.sections:
        for para in section.paragraphs:
            if wanted & set(para.checked_pmids):
                chunks.append(f"[{section.heading}] {para.text}")
    for av in entry.allelic_variants:
        for para in av.paragraphs:
            if wanted & set(para.checked_pmids):
                chunks.append(f"[Allelic variant {av.name}] {para.text}")
    return "\n\n".join(chunks)


def eval_gold_text(
    entry: GeneratedEntry, gold: GoldEntry, papers: dict[str, Paper], llm: LLM
) -> dict[str, Any]:
    """Coverage of OMIM's per-paper paragraphs (as deposited in ClinVar) by the draft.

    Only paragraphs about papers in the entry's own reference list are scored; see
    `GoldEntry.scoped_paragraphs`.
    """
    paragraphs: list[GoldParagraph] = gold.scoped_paragraphs
    out_of_scope = len(gold.gold_paragraphs) - len(paragraphs)
    if not paragraphs:
        return {"n_paragraphs": 0, "n_out_of_scope": out_of_scope}
    pairs = [(p.text, _draft_text_for(entry, p.pmids)) for p in paragraphs]
    judged = fact_coverage(pairs, llm)

    rank = {"title": 0, "abstract": 1, "fulltext": 2}
    per_paragraph, by_level = [], defaultdict(list)
    all_facts: list[dict[str, str]] = []
    for para, (_, draft), facts in zip(paragraphs, pairs, judged):
        levels = [papers[p].content_level for p in para.pmids if p in papers]
        level = min(levels, key=rank.get) if levels else "not_retrieved"
        all_facts.extend(facts)
        by_level[level].extend(facts)
        per_paragraph.append({
            "pmids": para.pmids, "content_level": level, "reference": para.text,
            "draft": draft, "facts": facts, **_tally(facts),
        })
    return {
        "n_paragraphs": len(paragraphs), "n_out_of_scope": out_of_scope,
        **_tally(all_facts),
        "by_content_level": {level: _tally(facts) for level, facts in sorted(by_level.items())},
        "paragraphs": per_paragraph,
    }


def eval_omim_text(entry: GeneratedEntry, gold: GoldEntry, llm: LLM) -> dict[str, Any] | None:
    """Section-by-section coverage of the full OMIM text (needs an OMIM API key)."""
    if not gold.omim_text:
        return None
    draft_sections = {s.name: "\n\n".join(p.text for p in s.paragraphs) for s in entry.sections}
    if entry.intro:
        draft_sections["intro"] = entry.intro.text
    whole = entry.plain_text()
    names = [n for n, text in gold.omim_text.items() if text.strip()]
    # Curators and the pipeline may file the same fact under different headings, so
    # each gold section is compared with the whole draft, not just its namesake.
    judged = fact_coverage([(gold.omim_text[n], whole) for n in names], llm)
    sections = {n: {**_tally(facts), "has_namesake_section": n in draft_sections} for n, facts in zip(names, judged)}
    return {**_tally([f for facts in judged for f in facts]), "sections": sections}


# --------------------------------------------------------------------------- #
# Faithfulness (no gold needed)
# --------------------------------------------------------------------------- #


def eval_faithfulness(entry: GeneratedEntry) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    statuses: dict[str, int] = defaultdict(int)
    for para in entry.all_paragraphs():
        statuses[para.status] += 1
        for check in para.checks:
            counts[check.verdict] += 1
    judged = sum(counts[v] for v in ("supported", "partially_supported", "unsupported", "contradicted"))
    return {
        "n_claims": judged,
        "supported": counts["supported"], "partially_supported": counts["partially_supported"],
        "unsupported": counts["unsupported"], "contradicted": counts["contradicted"],
        "not_checkable": counts["not_checkable"],
        "supported_rate": round(counts["supported"] / judged, 3) if judged else None,
        "supported_or_partial_rate": round((counts["supported"] + counts["partially_supported"]) / judged, 3) if judged else None,
        "error_rate": round((counts["unsupported"] + counts["contradicted"]) / judged, 3) if judged else None,
        "paragraphs": dict(statuses),
        "dropped_ungrounded_paragraphs": len(entry.meta.get("dropped_ungrounded", [])),
        "unknown_citations": entry.meta.get("unknown_citations", []),
        "removed_cross_references": len(entry.meta.get("removed_cross_references", [])),
        # The same tally taken before the repair round: what the writer produced unaided.
        "before_repair": {k: v for k, v in entry.meta.get("audit_before_repair", {}).items()
                          if k in ("n_claims", "supported", "partially_supported", "unsupported", "contradicted",
                                   "supported_rate", "error_rate")} or None,
    }


# --------------------------------------------------------------------------- #
# Everything together
# --------------------------------------------------------------------------- #


def evaluate_entry(
    entry: GeneratedEntry,
    gold: GoldEntry,
    papers: dict[str, Paper],
    llm: LLM,
    offered_pmids: list[str] | None = None,
) -> dict[str, Any]:
    levels: dict[str, int] = defaultdict(int)
    for pmid in gold.cited_pmids:
        levels[papers[pmid].content_level if pmid in papers else "not_retrieved"] += 1
    result: dict[str, Any] = {
        "mim": gold.mim, "title": gold.title, "strategy": entry.meta.get("strategy"),
        "gold_reference_access": dict(levels),
        "references": eval_references(entry, gold, offered_pmids),
        "genes": eval_genes(entry, gold),
        "inheritance": eval_inheritance(entry, gold),
        "synopsis": eval_synopsis(entry, gold),
        "variants": eval_variants(entry, gold, llm),
        "gold_text": eval_gold_text(entry, gold, papers, llm),
        "faithfulness": eval_faithfulness(entry),
    }
    omim = eval_omim_text(entry, gold, llm)
    if omim is not None:
        result["omim_text"] = omim
    return result


def _mean(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return round(sum(kept) / len(kept), 3) if kept else None


def summarize(evals: list[dict[str, Any]]) -> dict[str, Any]:
    """Macro-averages over entries, plus pooled counts where pooling is meaningful."""
    def pick(path: str) -> list[float | None]:
        out = []
        for e in evals:
            node: Any = e
            for key in path.split("."):
                node = node.get(key) if isinstance(node, dict) else None
            out.append(node)
        return out

    pooled = defaultdict(int)
    for e in evals:
        for key in ("supported", "partially_supported", "unsupported", "contradicted"):
            pooled[f"claims_{key}"] += e["faithfulness"].get(key, 0)
        for key in ("n_facts", "present", "partial", "absent", "contradicted"):
            pooled[f"gold_{key}"] += e["gold_text"].get(key, 0) or 0
    claims = sum(pooled[f"claims_{k}"] for k in ("supported", "partially_supported", "unsupported", "contradicted"))
    return {
        "n_entries": len(evals),
        "reference_recall": _mean(pick("references.cited.recall")),
        "reference_precision": _mean(pick("references.cited.precision")),
        "retrieval_recall": _mean(pick("references.retrieved.recall")),
        "retrieval_precision": _mean(pick("references.retrieved.precision")),
        "gene_f1": _mean(pick("genes.f1")),
        "gene_recall": _mean(pick("genes.recall")),
        "inheritance_match": _mean([None if m is None else float(m) for m in pick("inheritance.match")]),
        "synopsis_exact_f1": _mean(pick("synopsis.exact.f1")),
        "synopsis_exact_precision": _mean(pick("synopsis.exact.precision")),
        "synopsis_exact_recall": _mean(pick("synopsis.exact.recall")),
        "synopsis_hierarchical_f1": _mean(pick("synopsis.hierarchical.f1")),
        "synopsis_hierarchical_precision": _mean(pick("synopsis.hierarchical.precision")),
        "synopsis_hierarchical_recall": _mean(pick("synopsis.hierarchical.recall")),
        "synopsis_semantic_f1": _mean(pick("synopsis.semantic.f1")),
        "variant_recall": _mean(pick("variants.recall")),
        "gold_fact_coverage": _mean(pick("gold_text.coverage")),
        "gold_fact_strict_coverage": _mean(pick("gold_text.strict_coverage")),
        "gold_fact_contradiction_rate": _mean(pick("gold_text.contradiction_rate")),
        "omim_text_coverage": _mean(pick("omim_text.coverage")),
        "claim_supported_rate": _mean(pick("faithfulness.supported_rate")),
        "claim_error_rate": _mean(pick("faithfulness.error_rate")),
        "claim_supported_rate_before_repair": _mean(pick("faithfulness.before_repair.supported_rate")),
        "claim_error_rate_before_repair": _mean(pick("faithfulness.before_repair.error_rate")),
        "pooled": {
            **dict(pooled),
            "claim_supported_rate": round(pooled["claims_supported"] / claims, 3) if claims else None,
            "claim_error_rate": round((pooled["claims_unsupported"] + pooled["claims_contradicted"]) / claims, 3) if claims else None,
            "gold_fact_coverage": round((pooled["gold_present"] + 0.5 * pooled["gold_partial"]) / pooled["gold_n_facts"], 3)
            if pooled["gold_n_facts"] else None,
        },
    }
