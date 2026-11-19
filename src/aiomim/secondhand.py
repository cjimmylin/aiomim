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
import re
import threading
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
        found_in, passage = where.locate_passage(row["pmid"], seen_v.get("quote", ""))
        row["evidence_in"] = found_in
        row["citing_pmid"] = passage.citing_pmid if passage else ""
        row["passage_kind"] = passage.kind if passage else ""
        row["passage_n_other_refs"] = passage.n_other_refs if passage else None
        row["passage_cocited"] = sh.cocited(passage.n_other_refs) if passage else ""
    return list(rows.values())


_PRIMARY_RANK = {"supported": 4, "partially_supported": 3, "contradicted": 2, "unsupported": 1, "no_verdict": 0}


def collapse(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per distinct statement about a paper: the same claim made in two paragraphs
    (say Molecular Genetics and an allelic variant) counts once. Where the copies were
    judged differently, the best verdict against the full text is kept."""
    best: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        key = (r["pmid"], r["evidence_in"], re.sub(r"[^a-z0-9]+", " ", r["claim"].lower()).strip())
        cur = best.get(key)
        if cur is None or _PRIMARY_RANK[r.get("primary", {}).get("verdict", "no_verdict")] > \
                _PRIMARY_RANK[cur.get("primary", {}).get("verdict", "no_verdict")]:
            best[key] = r
    return list(best.values())


def _tally(subset, key) -> dict[str, int]:
    c = {v: 0 for v in VERDICTS}
    for r in subset:
        c[r.get(key, {}).get("verdict", "no_verdict")] += 1
    return c


def _group(rows, field) -> dict[str, Any]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r[field]].append(r)
    return {k: {"n": len(sub), "against_what_writer_saw": _tally(sub, "seen"),
                "against_full_text": _tally(sub, "primary")} for k, sub in sorted(groups.items())}


def _claim_counts(rows: list[dict[str, Any]], with_collapsed: bool = True) -> dict[str, Any]:
    on_secondhand = [r for r in rows if r["evidence_in"] == "secondhand"]
    out = {
        "n_claims": len(rows),
        "against_what_writer_saw": _tally(rows, "seen"),
        "against_full_text": _tally(rows, "primary"),
        "by_evidence_location": _group(rows, "evidence_in"),
        # Claims resting on second-hand text, by the kind of passage and by how many
        # other references the passage's paragraph or row cites.
        "secondhand_by_passage_kind": _group(on_secondhand, "passage_kind"),
        "secondhand_by_cocited": _group(on_secondhand, "passage_cocited"),
    }
    if with_collapsed:
        out["collapsed"] = _claim_counts(collapse(rows), with_collapsed=False)
    return out


def _add(into: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """Sum nested count dictionaries."""
    for k, v in other.items():
        if isinstance(v, dict):
            _add(into.setdefault(k, {}), v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            into[k] = into.get(k, 0) + v
    return into


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
    summary = pool_results(results, fulltext_draft_missing(source_dir, [r["mim"] for r in results]))
    summary.update(source=source, run=run, failures=failures, usage=llm.usage.summary())
    _write(run_dir / "secondhand_check.json", summary)
    _write(run_dir / "secondhand_check.md", check_markdown(summary))
    return summary


def fulltext_draft_missing(source_dir: Path, mims: list[str]) -> list[str]:
    """Entries whose full-text direct draft in the source run does not exist (writer stopped, or not scored).

    Their "full text" coverage in `coverage.json` is the score of an empty draft, not
    a measurement of full-text reading, so they must not be pooled as zeros.
    """
    missing = []
    for mim in mims:
        path = source_dir / mim / "eval.direct.json"
        if not path.exists() or json.loads(path.read_text()).get("stopped"):
            missing.append(mim)
    return sorted(missing)


def pool_results(results: list[dict[str, Any]], no_fulltext_draft: list[str] | None = None) -> dict[str, Any]:
    """Pool the per-entry results.

    Coverage is pooled, for all three conditions alike, only over entries that have
    a full-text draft in the source run (`no_fulltext_draft` lists those that do
    not), so the three rows compare the same paragraphs. Retrieval and the claim
    audit do not depend on the full-text draft and are pooled over every entry.
    """
    done = [r for r in results if "skipped" not in r]
    left_out = sorted(set(no_fulltext_draft or []) & {r["mim"] for r in done})
    with_full = [r for r in done if r["mim"] not in left_out]
    keys = ("hidden_with_citing", "hidden_with_open_access_citing", "hidden_with_passages", "hidden_passages",
            "hidden_chars", "papers_supplemented", "with_passages", "passages", "chars")
    retrieval = {k: sum(r["retrieval"].get(k, 0) for r in done) for k in keys}
    retrieval["hidden_papers"] = sum(len(r["hidden_papers"]) for r in done)
    retrieval["retrieval_seconds"] = round(sum(r["retrieval"].get("retrieval_seconds") or 0 for r in done), 1)
    def pooled(entries):
        out = {}
        for name in ("abstract", "secondhand", "fulltext"):
            rows = [r["coverage"][name] for r in entries if r["coverage"][name]["n_facts"]]
            out[name] = _pool(rows) | {"paragraphs": sum(r["paragraphs"] for r in rows)}
        return out

    coverage = pooled(with_full)
    everything = pooled(done)
    same = [r["coverage_same_paragraphs"] for r in with_full]
    claims: dict[str, Any] = {}
    for r in done:
        _add(claims, r["claims"])
    return {"n_entries": len(done), "entries": results, "retrieval": retrieval, "coverage": coverage,
            "n_entries_coverage": len(with_full), "left_out_no_fulltext_draft": left_out,
            # abstract and second-hand coverage over every entry, for reference (no full-text row: see above)
            "coverage_all_entries": {k: everything[k] for k in ("abstract", "secondhand")},
            "coverage_same_paragraphs_n": sum(s["paragraphs"] for s in same), "claims": claims}


def reaggregate(run: str, source: str | None = None) -> dict[str, Any]:
    """Rebuild secondhand_check.json/.md from the per-entry result files, without any model call.

    Reads runs/<run>/<mim>/secondhand_check/result.json and the source run's
    eval.direct.json files; keeps the failures and usage recorded by the original run.
    """
    settings = get_settings()
    run_dir = settings.runs / run
    old_path = run_dir / "secondhand_check.json"
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    source = source or old.get("source")
    if not source:
        raise ValueError("name the source run: the old summary does not record it")
    results = [json.loads(p.read_text()) for p in sorted(run_dir.glob("*/secondhand_check/result.json"))]
    have = {r["mim"] for r in results}
    results += [e for e in old.get("entries", []) if "skipped" in e and e["mim"] not in have]
    results.sort(key=lambda r: r["mim"])
    summary = pool_results(results, fulltext_draft_missing(settings.runs / source, [r["mim"] for r in results]))
    summary.update(source=source, run=run, failures=old.get("failures", {}), usage=old.get("usage", {}),
                   reaggregated_from_entry_files=True)
    _write(run_dir / "secondhand_check.json", summary)
    _write(run_dir / "secondhand_check.md", check_markdown(summary))
    return summary


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
        f"Pooled over the {s.get('n_entries_coverage', s['n_entries'])} entries that have a full-text draft in the "
        "source run, the same entries for all three conditions"
        + (f"; left out: {len(s['left_out_no_fulltext_draft'])} entries whose full-text direct draft was not written "
           f"(the writer's reply was stopped), so they have no full-text coverage to compare: "
           f"{', '.join(s['left_out_no_fulltext_draft'])}" if s.get("left_out_no_fulltext_draft") else "") + ".",
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
    if s.get("left_out_no_fulltext_draft") and s.get("coverage_all_entries"):
        a = s["coverage_all_entries"]
        lines += ["", f"Over all {s['n_entries']} entries the two new conditions convey "
                  f"{_pct(a['abstract']['coverage'])} (abstract only, {a['abstract']['n_facts']} facts) and "
                  f"{_pct(a['secondhand']['coverage'])} (abstract + second-hand, {a['secondhand']['n_facts']} facts)."]
    lines += ["", "Facts are split from the gold paragraph separately for each condition, so the fact counts "
              "differ slightly. The full-text draft went through the audit's repair round; the two new drafts did not.",
              "", "## Claims about the hidden papers in the second-hand draft", "",
              f"{s['claims'].get('n_claims', 0)} claims ({s['claims'].get('collapsed', {}).get('n_claims', 0)} after "
              "collapsing the same "
              "statement made in two paragraphs), each audited against what the writer saw (abstract plus passages) "
              "and against the paper's full text.", "",
              "**Caveat: our full texts exclude supplementary material.** A detail a paper gives only in a "
              "supplementary table counts as unsupported here, so \"unsupported by the primary text\" is an upper "
              "bound on the error of second-hand claims; \"contradicted\" is not affected in the same way.", ""]

    def table(title: str, groups: dict[str, Any], collapsed: dict[str, Any]) -> list[str]:
        rows = [f"| {title} | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | "
                "no verdict |", "|---|---|---|---|---|---|---|"]
        for key, row in sorted(groups.items()):
            f = row["against_full_text"]
            n_c = collapsed.get(key, {}).get("n", 0)
            fc = collapsed.get(key, {}).get("against_full_text", {})
            cell = lambda v: f"{f.get(v, 0)} ({fc.get(v, 0)})"  # noqa: E731
            rows.append(f"| {key or '-'} | {row['n']} ({n_c}) | {cell('supported')} | {cell('partially_supported')} | "
                        f"{cell('unsupported')} | {cell('contradicted')} | {cell('no_verdict')} |")
        return rows + [""]

    cl = s["claims"]
    co = cl.get("collapsed", {})
    lines += table("Evidence (audit of what the writer saw)", cl.get("by_evidence_location", {}),
                   co.get("by_evidence_location", {}))
    lines += ["`own`: the auditor's evidence quote is in the paper's title or abstract; `secondhand`: in a later "
              "paper's passage; `unlocated`: a quote found in neither (already downgraded); `none`: no quote "
              "(claim judged unsupported or contradicted against what the writer saw). Figures in brackets count "
              "a statement repeated in two paragraphs once.", "",
              "### Claims resting on second-hand text, by passage", ""]
    lines += table("Passage kind", cl.get("secondhand_by_passage_kind", {}), co.get("secondhand_by_passage_kind", {}))
    lines += table(f"Other references cited by the passage (few = at most {sh.FEW_COCITED})",
                   cl.get("secondhand_by_cocited", {}), co.get("secondhand_by_cocited", {}))
    lines += [
              "## Per entry", "",
              "| MIM | Hidden | With passages | Gold paragraphs | Abstract | Second-hand | Full text | "
              "Claims | On second-hand | of which not supported by full text |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    no_full = set(s.get("left_out_no_fulltext_draft") or [])
    for e in s["entries"]:
        if "skipped" in e:
            continue
        full = "no draft" if e["mim"] in no_full else _pct(e['coverage']['fulltext']['coverage'])
        sec = e["claims"]["by_evidence_location"].get("secondhand", {"n": 0, "against_full_text": {}})
        bad = sum(sec["against_full_text"].get(v, 0) for v in ("unsupported", "contradicted"))
        lines.append(f"| {e['mim']} | {len(e['hidden_papers'])} | {e['retrieval']['hidden_with_passages']} | "
                     f"{e['gold_paragraphs']} | {_pct(e['coverage']['abstract']['coverage'])} | "
                     f"{_pct(e['coverage']['secondhand']['coverage'])} | {full} | "
                     f"{e['claims']['n_claims']} | {sec['n']} | {bad} |")
    if s.get("failures"):
        lines += ["", f"Failed: {s['failures']}"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Filling the retrieval cache without generating anything
# --------------------------------------------------------------------------- #


def fetch_entries(mims: list[str], include_fulltext: bool = False, jobs: int = 4,
                  echo=print) -> dict[str, Any]:
    """Run only the citing-paper retrieval for the papers of `mims`, so later runs hit the cache.

    Targets are the papers not readable in full (what the strategy supplements), and
    with `include_fulltext` the full-text papers too (what `secondhand-check` hides).
    The cache key is the same as in the strategy and the check: the target's PMID and
    the entry's own papers as exclusions.
    """
    import time

    from .gold import build_gold
    from .retrieve import retrieve_oracle
    from .sources import citing

    started = time.time()
    failures: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    futures = []

    def one(mim, paper, own):
        return mim, paper, citing.secondhand_for(paper, own)

    lock = threading.Lock()

    def report(future):
        mim, paper, r = future.result()
        r = {**r, "mim": mim, "content_level": paper.content_level}
        with lock:
            records.append(r)
            n = len(records)
        echo(f"  ({n}/{len(futures)}+) {mim} PMID {paper.pmid} [{paper.content_level}]: {r['n_citing']} citing, "
             f"{r['n_open_access']} open access, {len(r['passages'])} passages, {r['n_chars']} chars, "
             f"{'cached' if r.get('cached') else str(r['seconds']) + ' s'}"
             + (f"  ERROR {r['error']}" if r["error"] else ""))

    # Targets are submitted as each entry's papers load, so fetching starts at once.
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for i, mim in enumerate(mims, 1):
            try:
                papers, _ = retrieve_oracle(build_gold(mim).cited_pmids)
            except Exception as exc:  # noqa: BLE001 - one bad entry should not stop the rest
                failures[mim] = f"{type(exc).__name__}: {exc}"
                echo(f"[{i}/{len(mims)}] {mim}: could not load papers: {exc}")
                continue
            own = frozenset(p.pmid for p in papers)
            chosen = [p for p in papers if include_fulltext or p.content_level != "fulltext"]
            for p in chosen:
                future = pool.submit(one, mim, p, own)
                futures.append(future)
                future.add_done_callback(report)   # progress as each lookup finishes
            echo(f"[{i}/{len(mims)}] {mim}: {len(chosen)} target papers of {len(papers)}")

    def yield_of(rs):
        return {"targets": len(rs), "with_citing": sum(1 for r in rs if r["n_citing"]),
                "with_open_access_citing": sum(1 for r in rs if r["n_open_access"]),
                "with_passages": sum(1 for r in rs if r["passages"]),
                "passages": sum(len(r["passages"]) for r in rs), "chars": sum(r["n_chars"] for r in rs),
                "lookup_failed": sum(1 for r in rs if r["error"])}

    levels = sorted({r["content_level"] for r in records})
    return {"entries": len(mims), "failures": failures, "seconds": round(time.time() - started, 1),
            "total": yield_of(records),
            "by_content_level": {lv: yield_of([r for r in records if r["content_level"] == lv]) for lv in levels}}


if __name__ == "__main__":
    # python -m aiomim.secondhand reaggregate <run> [<source run>]: re-pool from the per-entry files; no model calls.
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "reaggregate":
        reaggregate(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print((get_settings().runs / sys.argv[2] / "secondhand_check.md").read_text())
    else:
        sys.exit("usage: python -m aiomim.secondhand reaggregate <run> [<source run>]")
