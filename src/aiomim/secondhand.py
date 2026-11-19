"""How accurate is second-hand evidence, and how much of the access gap does it close?

For entries with at least one paper read in full, the full text of those papers
is hidden and the entry is written by direct reading twice:

    abstract     the hidden papers as abstracts only (the plain direct prompt);
    secondhand   the same, with every paper not read in full supplemented by
                 later open-access papers' descriptions of it.

Then, for the hidden papers only:

* OMIM-fact coverage of the gold paragraphs about them, under both conditions,
  next to what the existing full-text direct draft of the source run achieved
  for the same paragraphs (`eval.direct.json`);
* the claims the secondhand draft makes about them, audited twice: against what
  the writer saw (abstract plus passages), which tells whether a claim's evidence
  lay in the paper's own text or in a later paper's description; and against the
  true full text, which says whether the claim is right. No repair round.

    runs/<run>/<mim>/secondhand_check/
        secondhand.json             passages found for the supplemented papers
        entry.abstract.json|.md     the abstract-only draft
        entry.secondhand.json|.md   the abstract + second-hand draft
        coverage.json               per gold paragraph, both conditions and the full-text draft
        claims.json                 per claim about a hidden paper: both audits
        result.json                 the counts for this entry
    runs/<run>/secondhand_check.json|.md   pooled over entries

The source run is only read, never written.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import get_settings
from .evaluate import eval_gold_text
from .grounding import SourceIndex
from .llm import LLM
from .models import EntryParagraph, GeneratedEntry, GoldEntry, Paper, Seed, squash
from .render import entry_markdown
from .strategies import secondhand as sh
from .synthesize import synthesize_direct
from .verify import VERIFY_SYSTEM, XAudit, _audit_prompt, _decompose

log = logging.getLogger(__name__)

VERDICTS = ("supported", "partially_supported", "unsupported", "contradicted", "no_verdict")


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False, default=str)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def eligible_entries(source_dir: Path) -> list[str]:
    """Entries of a run with a paper read in full that a gold paragraph is about."""
    out = []
    for d in sorted(p for p in source_dir.iterdir() if p.is_dir() and p.name.isdigit()):
        papers, ev = d / "papers.json", d / "eval.direct.json"
        if not papers.exists() or not ev.exists():
            continue
        full = {p["pmid"] for p in json.loads(papers.read_text()) if p.get("content_level") == "fulltext"}
        paras = json.loads(ev.read_text()).get("gold_text", {}).get("paragraphs", [])
        if full and any(set(p["pmids"]) & full for p in paras):
            out.append(d.name)
    return out


def restrict_gold(gold: GoldEntry, pmids: set[str]) -> GoldEntry:
    """The gold entry with only the paragraphs about `pmids` left."""
    g = gold.model_copy(deep=True)
    for av in g.allelic_variants:
        av.paragraphs = [p for p in av.paragraphs if set(p.pmids) & pmids]
    return g


# --------------------------------------------------------------------------- #
# The double audit
# --------------------------------------------------------------------------- #


def _verdicts(reply, source: str, wanted: set[str]) -> dict[str, dict[str, str]]:
    """claim id -> verdict, quote, explanation; the same quote rule as `verify_entry`."""
    out: dict[str, dict[str, str]] = {}
    if isinstance(reply, Exception):
        return out
    index = SourceIndex(source)
    for v in reply.verdicts:
        claim_id = v.claim_id.strip().strip("[]")
        if claim_id not in wanted:
            continue
        verdict, quote, explanation = v.verdict, squash(v.evidence_quote), squash(v.explanation)
        if verdict == "supported" and (not quote or not index.contains(quote)):
            verdict = "partially_supported"
            explanation = (explanation + " " if explanation else "") + \
                "[auditor's evidence quote was not found verbatim in the source]"
        out[claim_id] = {"verdict": verdict, "quote": quote, "explanation": explanation}
    return out


def audit_hidden(entry: GeneratedEntry, seen: list[Paper], truth: dict[str, Paper], hidden: set[str],
                 llm) -> list[dict[str, Any]]:
    """Each claim about a hidden paper, judged against what the writer saw and against the full text."""
    seen_by = {p.pmid: p for p in seen}
    targets: list[EntryParagraph] = [p for p in entry.all_paragraphs() if set(p.checked_pmids) & hidden]
    if not targets:
        return []
    claims_by_para = _decompose(targets, seen_by, llm)
    by_id = {p.id: p for p in targets}
    per_paper: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for para_id, claims in claims_by_para.items():
        for n, claim in enumerate(claims, 1):
            claim_id = f"{para_id}#{n}"
            for pmid in claim.pmids:
                if pmid in hidden:
                    per_paper[pmid][para_id].append((claim_id, claim.text))
                    rows[(claim_id, pmid)] = {"claim_id": claim_id, "paragraph_id": para_id, "pmid": pmid,
                                              "claim": claim.text, "n_papers_attributed": len(claim.pmids)}
    pmids = sorted(per_paper)
    built = []
    for pmid in pmids:
        items = [(by_id[pid], claims) for pid, claims in per_paper[pmid].items()]
        built.append((pmid, "seen", *_audit_prompt(seen_by[pmid], items)))
        built.append((pmid, "primary", *_audit_prompt(truth[pmid], items)))
    replies = llm.map("verify", VERIFY_SYSTEM, [b[2] for b in built], XAudit)
    where = sh.Attributor(seen)
    for (pmid, kind, _, source), reply in zip(built, replies):
        wanted = {cid for pid in per_paper[pmid] for cid, _ in per_paper[pmid][pid]}
        got = _verdicts(reply, source, wanted)
        for cid in wanted:
            v = got.get(cid, {"verdict": "no_verdict", "quote": "", "explanation": ""})
            rows[(cid, pmid)][kind] = v
    for row in rows.values():
        seen_v = row.get("seen", {})
        found_in, citing_pmid = where.locate(row["pmid"], seen_v.get("quote", ""))
        row["evidence_in"], row["citing_pmid"] = found_in, citing_pmid
    return list(rows.values())


def _claim_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def tally(subset, key):
        c = {v: 0 for v in VERDICTS}
        for r in subset:
            c[r.get(key, {}).get("verdict", "no_verdict")] += 1
        return c

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r["evidence_in"]].append(r)
    return {
        "n_claims": len(rows),
        "against_what_writer_saw": tally(rows, "seen"),
        "against_full_text": tally(rows, "primary"),
        "by_evidence_location": {
            loc: {"n": len(sub), "against_what_writer_saw": tally(sub, "seen"), "against_full_text": tally(sub, "primary")}
            for loc, sub in sorted(groups.items())
        },
    }


# --------------------------------------------------------------------------- #
# One entry
# --------------------------------------------------------------------------- #


def _fulltext_coverage(source_entry: Path, hidden: set[str]) -> dict[tuple, dict[str, Any]]:
    path = source_entry / "eval.direct.json"
    if not path.exists():
        return {}
    paras = json.loads(path.read_text()).get("gold_text", {}).get("paragraphs", [])
    return {(tuple(p["pmids"]), p["reference"]): p for p in paras if set(p["pmids"]) & hidden}


_TALLY = ("n_facts", "present", "partial", "absent", "contradicted", "coverage")


def check_entry(mim: str, source_dir: Path, run_dir: Path, llm: LLM) -> dict[str, Any]:
    from .retrieve import retrieve_oracle

    src = source_dir / mim
    out = run_dir / mim / "secondhand_check"
    seed = Seed.model_validate_json((src / "seed.json").read_text(encoding="utf-8"))
    gold = GoldEntry.model_validate_json((src / "gold.json").read_text(encoding="utf-8"))
    papers, _ = retrieve_oracle(gold.cited_pmids)
    truth = {p.pmid: p for p in papers}
    hidden = {p.pmid for p in papers if p.content_level == "fulltext"}
    if not hidden:
        return {"mim": mim, "skipped": "no paper read in full"}
    blind = [p.model_copy(update={"fulltext": None, "fulltext_source": None}) if p.pmid in hidden else p
             for p in papers]
    by_blind = {p.pmid: p for p in blind}

    entry_a = synthesize_direct(seed, blind, llm)
    entry_a.meta["condition"] = "abstract"
    augmented, retrieval = sh.supplement(blind, exclude=set(truth))
    _write(out / "secondhand.json", retrieval)
    entry_b = synthesize_direct(seed, augmented, llm, extra_rules=sh.RULES, strategy="secondhand",
                                meta={"secondhand_retrieval": retrieval["totals"], "condition": "secondhand"})
    for name, entry in (("abstract", entry_a), ("secondhand", entry_b)):
        _write(out / f"entry.{name}.json", entry.model_dump())
        _write(out / f"entry.{name}.md", entry_markdown(entry, show_flags=False))

    gold_h = restrict_gold(gold, hidden)
    cov = {name: eval_gold_text(entry, gold_h, by_blind, llm) for name, entry in
           (("abstract", entry_a), ("secondhand", entry_b))}
    full = _fulltext_coverage(src, hidden)
    paragraphs = []
    for i, para in enumerate(gold_h.scoped_paragraphs):
        row = {"pmids": para.pmids}
        for name in ("abstract", "secondhand"):
            got = cov[name].get("paragraphs", [])
            row[name] = {k: got[i][k] for k in _TALLY} if i < len(got) else None
        ft = full.get((tuple(para.pmids), para.text))
        row["fulltext"] = {k: ft[k] for k in _TALLY} if ft else None
        paragraphs.append(row)
    _write(out / "coverage.json", {"conditions": cov, "paragraphs": paragraphs})

    claims = audit_hidden(entry_b, augmented, truth, hidden, llm)
    _write(out / "claims.json", claims)

    hidden_targets = [t for t in retrieval["targets"] if t["pmid"] in hidden]
    result = {
        "mim": mim, "title": gold.title,
        "papers": len(papers), "hidden_papers": sorted(hidden),
        "retrieval": {
            "hidden_with_citing": sum(1 for t in hidden_targets if t["n_citing"]),
            "hidden_with_open_access_citing": sum(1 for t in hidden_targets if t["n_open_access"]),
            "hidden_with_passages": sum(1 for t in hidden_targets if t["n_passages"]),
            "hidden_passages": sum(t["n_passages"] for t in hidden_targets),
            "hidden_chars": sum(t["n_chars"] for t in hidden_targets),
            **retrieval["totals"],
        },
        "gold_paragraphs": len(paragraphs),
        "coverage": {
            name: _pool([p[name] for p in paragraphs if p[name]]) for name in ("abstract", "secondhand", "fulltext")
        },
        "coverage_same_paragraphs": _same_paragraphs(paragraphs),
        "claims": _claim_counts(claims),
    }
    _write(out / "result.json", result)
    return result


def _pool(tallies: list[dict[str, Any]]) -> dict[str, Any]:
    n = sum(t["n_facts"] for t in tallies)
    present = sum(t["present"] for t in tallies)
    partial = sum(t["partial"] for t in tallies)
    return {"paragraphs": len(tallies), "n_facts": n, "present": present, "partial": partial,
            "absent": sum(t["absent"] for t in tallies), "contradicted": sum(t["contradicted"] for t in tallies),
            "coverage": round((present + 0.5 * partial) / n, 3) if n else None}


def _same_paragraphs(paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Coverage over the paragraphs scored under all three conditions."""
    both = [p for p in paragraphs if p["abstract"] and p["secondhand"] and p["fulltext"]]
    return {"paragraphs": len(both), **{name: _pool([p[name] for p in both])["coverage"]
                                        for name in ("abstract", "secondhand", "fulltext")}}


# --------------------------------------------------------------------------- #
# A run
# --------------------------------------------------------------------------- #


def check_run(source: str, run: str, mims: list[str] | None = None, limit: int | None = None,
              jobs: int = 1) -> dict[str, Any]:
    settings = get_settings()
    source_dir, run_dir = settings.runs / source, settings.runs / run
    if source_dir.resolve() == run_dir.resolve():
        raise ValueError("write the check to a run other than the one it reads from")
    eligible = eligible_entries(source_dir)
    chosen = [m for m in (mims or eligible)]
    if limit:
        chosen = chosen[:limit]
    llm = LLM(settings)
    results, failures = [], {}
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(check_entry, mim, source_dir, run_dir, llm): mim for mim in chosen}
        for future in as_completed(futures):
            mim = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - one bad entry should not lose the rest
                log.exception("[%s] secondhand check failed", mim)
                failures[mim] = f"{type(exc).__name__}: {exc}"
    results.sort(key=lambda r: r["mim"])
    summary = pool_results(results)
    summary.update(source=source, run=run, failures=failures, usage=llm.usage.summary())
    _write(run_dir / "secondhand_check.json", summary)
    _write(run_dir / "secondhand_check.md", check_markdown(summary))
    return summary


def pool_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    done = [r for r in results if "skipped" not in r]
    keys = ("hidden_with_citing", "hidden_with_open_access_citing", "hidden_with_passages", "hidden_passages",
            "hidden_chars", "papers_supplemented", "with_passages", "passages", "chars")
    retrieval = {k: sum(r["retrieval"].get(k, 0) for r in done) for k in keys}
    retrieval["hidden_papers"] = sum(len(r["hidden_papers"]) for r in done)
    retrieval["retrieval_seconds"] = round(sum(r["retrieval"].get("retrieval_seconds") or 0 for r in done), 1)
    coverage = {}
    for name in ("abstract", "secondhand", "fulltext"):
        rows = [r["coverage"][name] for r in done if r["coverage"][name]["n_facts"]]
        coverage[name] = _pool(rows) | {"paragraphs": sum(r["paragraphs"] for r in rows)}
    same = [r["coverage_same_paragraphs"] for r in done]
    claims: dict[str, Any] = {"n_claims": sum(r["claims"]["n_claims"] for r in done)}
    for key in ("against_what_writer_saw", "against_full_text"):
        claims[key] = {v: sum(r["claims"][key][v] for r in done) for v in VERDICTS}
    locs: dict[str, Any] = {}
    for r in done:
        for loc, row in r["claims"]["by_evidence_location"].items():
            cur = locs.setdefault(loc, {"n": 0, "against_what_writer_saw": dict.fromkeys(VERDICTS, 0),
                                        "against_full_text": dict.fromkeys(VERDICTS, 0)})
            cur["n"] += row["n"]
            for key in ("against_what_writer_saw", "against_full_text"):
                for v in VERDICTS:
                    cur[key][v] += row[key][v]
    claims["by_evidence_location"] = locs
    return {"n_entries": len(done), "entries": results, "retrieval": retrieval, "coverage": coverage,
            "coverage_same_paragraphs_n": sum(s["paragraphs"] for s in same), "claims": claims}


def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def check_markdown(s: dict[str, Any]) -> str:
    r, c = s["retrieval"], s["coverage"]
    lines = [
        "# Second-hand evidence check",
        "",
        f"Source run `{s['source']}`; {s['n_entries']} entries. In each, the papers read in full were hidden and the "
        "entry was written by direct reading from their abstracts, with and without second-hand passages from later "
        "open-access papers. Counts, not just rates.",
        "",
        "## Retrieval for the hidden papers",
        "",
        f"- Hidden papers: {r['hidden_papers']}; with citing papers: {r['hidden_with_citing']}; with open-access "
        f"citing papers: {r['hidden_with_open_access_citing']}; with at least one passage: {r['hidden_with_passages']}.",
        f"- Passages for the hidden papers: {r['hidden_passages']} ({r['hidden_chars']:,} characters).",
        f"- All papers supplemented (hidden and abstract-only): {r['papers_supplemented']}, of which "
        f"{r['with_passages']} got passages; {r['passages']} passages, {r['chars']:,} characters; retrieval "
        f"{r['retrieval_seconds']} s in all.",
        "",
        "## OMIM-fact coverage of the gold paragraphs about the hidden papers",
        "",
        "| Condition | Paragraphs | Facts | Present | Partial | Absent | Contradicted | Coverage |",
        "|---|---|---|---|---|---|---|---|",
    ]
    names = {"abstract": "Abstract only", "secondhand": "Abstract + second-hand",
             "fulltext": "Full text (source run's direct draft)"}
    for name in ("abstract", "secondhand", "fulltext"):
        x = c[name]
        lines.append(f"| {names[name]} | {x['paragraphs']} | {x['n_facts']} | {x['present']} | {x['partial']} | "
                     f"{x['absent']} | {x['contradicted']} | {_pct(x['coverage'])} |")
    lines += ["", "Facts are split from the gold paragraph separately for each condition, so the fact counts "
              "differ slightly. The full-text draft went through the audit's repair round; the two new drafts did not.",
              "", "## Claims about the hidden papers in the second-hand draft", "",
              f"{s['claims']['n_claims']} claims, each audited against what the writer saw (abstract plus passages) "
              "and against the paper's full text.", "",
              "| Evidence (audit of what the writer saw) | Claims | Full text: supported | partial | unsupported | "
              "contradicted | no verdict |",
              "|---|---|---|---|---|---|---|"]
    for loc, row in sorted(s["claims"]["by_evidence_location"].items()):
        f = row["against_full_text"]
        lines.append(f"| {loc} | {row['n']} | {f['supported']} | {f['partially_supported']} | {f['unsupported']} | "
                     f"{f['contradicted']} | {f['no_verdict']} |")
    lines += ["", "`own`: the auditor's evidence quote is in the paper's title or abstract; `secondhand`: in a later "
              "paper's passage; `unlocated`: a quote found in neither (already downgraded); `none`: no quote "
              "(claim judged unsupported or contradicted against what the writer saw).", "",
              "## Per entry", "",
              "| MIM | Hidden | With passages | Gold paragraphs | Abstract | Second-hand | Full text | "
              "Claims | On second-hand | of which not supported by full text |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for e in s["entries"]:
        if "skipped" in e:
            continue
        sec = e["claims"]["by_evidence_location"].get("secondhand", {"n": 0, "against_full_text": {}})
        bad = sum(sec["against_full_text"].get(v, 0) for v in ("unsupported", "contradicted"))
        lines.append(f"| {e['mim']} | {len(e['hidden_papers'])} | {e['retrieval']['hidden_with_passages']} | "
                     f"{e['gold_paragraphs']} | {_pct(e['coverage']['abstract']['coverage'])} | "
                     f"{_pct(e['coverage']['secondhand']['coverage'])} | {_pct(e['coverage']['fulltext']['coverage'])} | "
                     f"{e['claims']['n_claims']} | {sec['n']} | {bad} |")
    if s.get("failures"):
        lines += ["", f"Failed: {s['failures']}"]
    return "\n".join(lines) + "\n"
