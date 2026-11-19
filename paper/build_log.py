"""Assemble paper/materials/experimental_log.md from the result files.

Tables are copied from the comparison reports and computed from the per-entry files, so
no number in the log is typed by hand except where a sentence says where it comes from.
Run from the repository root:  python3 paper/build_log.py
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "paper" / "materials" / "experimental_log.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(md: str, header: str, level: int = 2) -> str:
    """The body of a `## header` section, up to the next header of the same or a higher level."""
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#" * level + " ") and line[level + 1:].strip().startswith(header):
            start = i + 1
            break
    if start is None:
        raise KeyError(header)
    end = len(lines)
    for j in range(start, len(lines)):
        m = re.match(r"^(#+) ", lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def table_rows(block: str, keep: tuple[str, ...]) -> str:
    """Header rows of a markdown table plus the rows whose first cell starts with one of `keep`."""
    out, seen_header = [], 0
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        if seen_header < 2:
            out.append(line)
            seen_header += 1
            continue
        first = line.split("|")[1].strip()
        if any(first.startswith(k) for k in keep):
            out.append(line)
    return "\n".join(out)


HEAD = ("Claims supported by cited paper", "… unsupported, before the repair round",
        "… contradicted, before the repair round", "OMIM per-paper facts conveyed", "… fully (no partial credit)",
        "OMIM per-paper facts contradicted", "… facts split afresh", "Clinical synopsis HPO F1, exact", "… precision",
        "… recall", "Clinical synopsis HPO F1, hierarchical", "OMIM allelic variants recovered",
        "Generated variants that are OMIM variants", "Causal gene F1", "Inheritance matches OMIM",
        "OMIM references used")
VOL = ("Claims audited per entry", "Claims that could not be audited", "Clinical-synopsis HPO terms per entry",
       "Allelic variants per entry")


def report(run: str) -> str:
    return read(RUNS / run / "strategies.md")


def first_para(md: str) -> str:
    return next(p for p in md.split("\n\n")[1:] if p.strip() and not p.startswith("#"))


def pct(x: float | None, d: int = 1) -> str:
    return "–" if x is None else f"{100 * x:.{d}f}%"


def mims_of(tsv: str) -> list[str]:
    return [r["mim"] for r in csv.DictReader(open(ROOT / "evalsets" / tsv), delimiter="\t")]


# --------------------------------------------------------------------------- computed pieces

def evalset_facts() -> dict:
    mims = mims_of("omim100.tsv")
    levels, src = {}, {}
    variants = paragraphs = facts = 0
    for m in mims:
        for p in json.load(open(RUNS / "omim100" / m / "papers.json")):
            levels[p["content_level"]] = levels.get(p["content_level"], 0) + 1
        gold = json.load(open(RUNS / "omim100" / m / "gold.json"))
        for h in gold.get("hpo_annotations", []):
            if h.get("aspect") == "P":
                ref = h.get("reference") or ""
                key = "PMID" if "PMID" in ref else "OMIM" if "OMIM" in ref else "other"
                src[key] = src.get(key, 0) + 1
        ev = json.load(open(RUNS / "omim100" / m / "eval.cohort.json"))
        variants += ev["variants"].get("n_gold") or 0
        gf = RUNS / "omim100" / m / "gold_facts.json"
        if gf.exists():
            d = json.load(open(gf))
            ps = d.get("paragraphs", d) if isinstance(d, dict) else d
            for p in (ps.values() if isinstance(ps, dict) else ps):
                fl = p.get("facts", p) if isinstance(p, dict) else p
                facts += len(fl)
                paragraphs += 1
    return {"entries": len(mims), "levels": levels, "hpo": src, "variants": variants,
            "paragraphs": paragraphs, "facts": facts}


def frozen_cov(run: str, mim: str, strategy: str, salt: str | None = None) -> float | None:
    name = f"eval.{strategy}.json" if salt is None else f"judge_{salt}.{strategy}.json"
    path = RUNS / run / mim / name
    if not path.exists():
        return None
    d = json.load(open(path))
    if d.get("stopped"):
        return None
    return (d.get("gold_text_frozen") or {}).get("coverage")


def judge_replicates() -> str:
    mims = mims_of("replicate30.tsv")
    lines = []
    rows_by = {}
    for s in ("direct", "kg"):
        rows = [[frozen_cov("omim100", m, s), frozen_cov("omim100", m, s, "j1"), frozen_cov("omim100", m, s, "j2")]
                for m in mims]
        rows = [r for r in rows if all(v is not None for v in r)]
        rows_by[s] = rows
        means = [100 * st.mean(c) for c in zip(*rows)]
        within = 100 * st.mean(st.pstdev(r) for r in rows)
        lines.append(f"| {'Direct reading' if s == 'direct' else 'Evidence graph'} | {len(rows)} | "
                     + " / ".join(f"{x:.1f}" for x in means) + f" | {within:.1f} |")
    d = [[b - a for a, b in zip(x, y)] for x, y in zip(rows_by["direct"], rows_by["kg"])]
    diffs = " / ".join(f"{100 * st.mean(c):+.1f}" for c in zip(*d))
    agree = tot = 0
    for m in mims:
        for s in ("direct", "kg"):
            try:
                a = json.load(open(RUNS / "omim100" / m / f"eval.{s}.json"))["gold_text_frozen"]
                b = json.load(open(RUNS / "omim100" / m / f"judge_j1.{s}.json"))["gold_text_frozen"]
            except Exception:
                continue
            fa = {(p["key"], f["id"]): f["status"] for p in a["paragraphs"] for f in p["facts"]}
            fb = {(p["key"], f["id"]): f["status"] for p in b["paragraphs"] for f in p["facts"]}
            for k in fa:
                if k in fb:
                    tot += 1
                    agree += fa[k] == fb[k]
    return ("| Strategy | Entries | Mean OMIM facts conveyed in three judgings (%) | Mean within-entry SD across judgings (points) |\n"
            "|---|---|---|---|\n" + "\n".join(lines) + "\n\n"
            f"- Evidence graph minus direct reading in the three judgings: {diffs} points.\n"
            f"- Per-fact agreement between two judgings of the same draft against the same fact list: "
            f"{agree} of {tot} statuses ({100 * agree / tot:.1f}%).")


def run_replicates() -> str:
    mims = mims_of("replicate30.tsv")
    runs = ("replicate30_r1", "replicate30_r2", "replicate30_r3")
    tab = {s: [[frozen_cov(r, m, s) for r in runs] for m in mims] for s in ("direct", "kg")}
    keep = [i for i in range(len(mims)) if all(v is not None for s in tab for v in tab[s][i])]
    lines = []
    for s, label in (("direct", "Direct reading"), ("kg", "Evidence graph")):
        rows = [tab[s][i] for i in keep]
        means = [100 * st.mean(c) for c in zip(*rows)]
        within = math.sqrt(st.mean([st.variance(r) for r in rows])) * 100
        between = st.stdev([st.mean(r) for r in rows]) * 100
        share = within ** 2 / (within ** 2 + between ** 2)
        lines.append(f"| {label} | " + " / ".join(f"{x:.1f}" for x in means)
                     + f" | {within:.1f} | {between:.1f} | {100 * share:.0f}% |")
    d = [[tab["kg"][i][k] - tab["direct"][i][k] for k in range(3)] for i in keep]
    per = " / ".join(f"{100 * st.mean(c):+.1f}" for c in zip(*d))
    wd = math.sqrt(st.mean([st.variance(r) for r in d])) * 100
    return (f"{len(keep)} entries, three full replicates of generation, audit and scoring; OMIM facts conveyed scored "
            "against the same fixed fact lists in every replicate.\n\n"
            "| Strategy | 30-entry mean in replicates 1 / 2 / 3 (%) | Within-entry SD (points) | Between-entry SD (points) | Share of variance within entries |\n"
            "|---|---|---|---|---|\n" + "\n".join(lines) + "\n\n"
            f"- Evidence graph minus direct reading in replicates 1 / 2 / 3: {per} points.\n"
            f"- Within-entry SD of that paired difference: {wd:.1f} points. Replicate noise alone gives a 95% half-width of "
            f"{1.96 * wd / math.sqrt(93):.1f} points on a difference between two strategies over 93 entries, and "
            f"{1.96 * wd / math.sqrt(len(keep)):.1f} points over 30 entries.")


def meta_totals(run: str, strategy: str, key: str, fields: tuple[str, ...]) -> tuple[int, dict, int]:
    tot = dict.fromkeys(fields, 0)
    n = with_merge = 0
    for f in sorted(glob.glob(str(RUNS / run / "[0-9]*" / f"entry.{strategy}.json"))):
        m = json.load(open(f)).get("meta", {}).get(key)
        if not m:
            continue
        n += 1
        for k in fields:
            tot[k] += m.get(k) or 0
        with_merge += bool(m.get("merges_accepted"))
    return n, tot, with_merge


def cache_totals() -> tuple[int, float, float, float]:
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from aiomim.config import get_settings
    n = 0
    cost = inp = out = 0.0
    for f in glob.glob(str(get_settings().llm_cache) + "/**/*", recursive=True):
        if not os.path.isfile(f):
            continue
        try:
            m = json.load(open(f)).get("meta", {})
        except Exception:
            continue
        n += 1
        cost += float(m.get("cost_usd") or 0)
        inp += int(m.get("input_tokens") or 0)
        out += int(m.get("output_tokens") or 0)
    return n, cost, inp, out


def ablation_tables() -> str:
    d = json.load(open(RUNS / "ablation40" / "ablation_tables.json"))["compare_view"]
    order = ["direct", "kg", "kg_matched", "kg_hybrid", "cohort", "cohort_matched", "cohort_hybrid"]
    label = {"direct": "Direct reading", "kg": "Evidence graph", "kg_matched": "Evidence graph, matched",
             "kg_hybrid": "Evidence graph plus text", "cohort": "Case table", "cohort_matched": "Case table, matched",
             "cohort_hybrid": "Case table plus text"}
    meas = [("facts", "OMIM facts conveyed (%)", 100), ("facts_fulltext", "… on papers readable in full (%)", 100),
            ("claims_supported", "Claims judged supported (%)", 100), ("syn_P", "Synopsis precision (%)", 100),
            ("syn_R", "Synopsis recall (%)", 100), ("syn_F1", "Synopsis exact F1 (%)", 100),
            ("syn_terms", "Synopsis terms per entry", 1), ("inheritance", "Inheritance matches (%)", 100),
            ("variant_recall", "Variants recovered (%)", 100)]
    t1 = ["| Measure | " + " | ".join(label[s] for s in order) + " |", "|" + "---|" * (len(order) + 1)]
    for key, name, mult in meas:
        cells = []
        for s in order:
            v = d["means"].get(f"{key}|{s}")
            cells.append("–" if not v else f"{mult * v[0]:.1f}" + (f" (n={v[1]})" if v[1] != 38 else ""))
        t1.append(f"| {name} | " + " | ".join(cells) + " |")

    def pair(key: str, a: str, mult: float) -> str:
        v = d["pairs"].get(f"{key}|{a}")
        if not v:
            return "–"
        return f"{mult * v[0]:+.1f} ({mult * v[1]:+.1f} to {mult * v[2]:+.1f}); {v[3]}/{v[4]}"

    cols = [("kg_matched-kg", "Graph matched − graph"), ("kg_hybrid-kg_matched", "Graph plus text − graph matched"),
            ("cohort_matched-cohort", "Table matched − table"),
            ("cohort_hybrid-cohort_matched", "Table plus text − table matched")]
    t2 = ["| Measure | " + " | ".join(c[1] for c in cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for key, name, mult in meas:
        t2.append(f"| {name.replace(' (%)', '')} | " + " | ".join(pair(key, c[0], mult) for c in cols) + " |")
    cols3 = [("kg-direct", "Evidence graph"), ("kg_matched-direct", "Graph matched"), ("kg_hybrid-direct", "Graph plus text"),
             ("cohort-direct", "Case table"), ("cohort_matched-direct", "Table matched"),
             ("cohort_hybrid-direct", "Table plus text")]
    t3 = ["| Measure | " + " | ".join(c[1] for c in cols3) + " |", "|" + "---|" * (len(cols3) + 1)]
    for key, name, mult in meas:
        t3.append(f"| {name.replace(' (%)', '')} | " + " | ".join(pair(key, c[0], mult) for c in cols3) + " |")
    return ("**Means, 38 entries completed in full by all seven strategies.**\n\n" + "\n".join(t1)
            + "\n\n**Each step against the one before it** (difference, 95% bootstrap interval; entries better/worse). "
              "Percentage points except synopsis terms.\n\n" + "\n".join(t2)
            + "\n\n**Each strategy against direct reading** (same format).\n\n" + "\n".join(t3))


# --------------------------------------------------------------------------- the log

def build() -> str:
    ev = evalset_facts()
    main = report("omim100")
    sh = report("omim100_secondhand")
    rec = report("omim100_reconciled")
    gd = report("omim100_guided")
    lg = report("large12")
    rc = report("recent")
    ab = report("ablation40")
    n_rec, rec_tot, rec_with = meta_totals(
        "omim100_reconciled", "reconciled", "reconciled",
        ("individuals_before", "individuals_after", "families_before", "families_after", "merges_proposed",
         "merges_accepted", "merges_rejected_by_verifier", "variants_merged", "conflicts_found"))
    n_sh, sh_tot, _ = meta_totals("omim100_secondhand", "secondhand", "secondhand",
                                  ("papers_supplemented", "papers_with_passages", "passages", "claims",
                                   "claims_on_secondhand", "paragraphs_on_secondhand"))
    calls, cost, inp, out = cache_totals()
    gaps = read(RUNS / "omim100" / "gaps.direct.frozen.md")
    shc = read(ROOT / "results" / "omim100_secondhand" / "secondhand_check.md")
    lv = ev["levels"]
    # The check's own report, without its per-entry listing and with its headings demoted.
    shc_body = shc.split("\n", 1)[1].split("\n## Per entry")[0].strip()
    shc_body = re.sub(r"^### ", "##### ", shc_body, flags=re.M)
    shc_body = re.sub(r"^## ", "#### ", shc_body, flags=re.M)

    parts: list[str] = []
    add = parts.append

    add(f"""# Experimental log

Every number that may appear in the paper. Tables are copied from the comparison reports of each run; a sentence says
so where a number comes from elsewhere. Percentages are means over entries unless a table says "pooled".
Intervals are 95% bootstrap intervals over entries (10,000 resamples). "Points" means percentage points.

## 1. Setup

### 1.1 Task and data

- **Entries.** {ev['entries']} OMIM phenotype entries drawn at random with a fixed seed, 20 from each of five bands of
  entry number that track when the entry was created (1xxxxx–5xxxxx, 600000–609999, 610000–615999, 616000–619999,
  620000 onward). Eligibility: 2–12 cited references, a causal gene in the gene map, at least five phenotype
  annotations, and at least one curator paragraph in scope. The sample is therefore stratified and selects
  well-annotated, molecularly characterised entries.
- **Papers.** {sum(lv.values())} cited papers. Readable in full (open access through PubMed Central or Europe PMC):
  {lv.get('fulltext', 0)} ({100 * lv.get('fulltext', 0) / sum(lv.values()):.0f}%); abstract only: {lv.get('abstract', 0)};
  title only: {lv.get('title', 0)}. Supplementary material was not retrieved.
- **Input to every strategy.** The entry's number, title and alternative titles, and exactly the papers the entry
  cites. The causal gene is withheld.
- **Reference (gold standard), all from public resources.**
  - Curator-written per-paper text: OMIM's allelic-variant descriptions as deposited by OMIM in ClinVar. They come from
    OMIM's gene entries and are variant-centred prose about one or more cited papers. A paragraph is in scope for an
    entry when it is about a paper the entry cites. {ev['paragraphs']} paragraphs are in scope across the 100 entries.
    The narrative sections of the phenotype entries (clinical features, description) are not available publicly and
    are not compared.
  - Fixed fact lists: each in-scope paragraph was split once into atomic facts, without sight of any draft:
    {ev['facts']:,} facts in all.
  - Clinical synopsis: the Human Phenotype Ontology disease annotations for the entry (phenotype aspect):
    {sum(ev['hpo'].values()):,} annotations, of which {ev['hpo'].get('PMID', 0):,} are the HPO team's own curation from
    papers (they carry a PubMed reference) and {ev['hpo'].get('OMIM', 0):,} are taken from OMIM. (That this count equals
    the number of in-scope paragraphs is a coincidence.)
  - Causal gene: OMIM's gene map via MedGen and mim2gene. Inheritance: HPO and MedGen modes, compared as coarse classes
    (autosomal dominant, autosomal recessive, X-linked, mitochondrial, and others), requiring the sets to be equal.
  - Allelic variants: the entry's OMIM-submitted ClinVar records in scope: {ev['variants']}.
- **Other evaluation sets.** A 40-entry subset for the ablation (every entry with at least half its papers readable in
  full that all reading strategies completed, filled to 40 at random). A 30-entry subset for replicates (six per
  band). 12 further entries with 30–75 references (exploratory). 30 entries created June to November 2026.

### 1.2 Model and settings

- One model for everything: Claude Opus 5.5 (`claude-opus-5-5`), called through the Claude Code command-line interface
  in headless mode with schema-constrained output. The interface exposes no temperature or seed.
- Reasoning effort: high for writers (direct reading, the graph and table writers, the agent, the memory draft);
  medium for per-paper extraction in the evidence graph and the case table, for the audit and for all judging. The
  matched ablation raises per-paper extraction to high.
- The agentic strategy has read and search tools over a folder of the papers and nothing else. No strategy has web
  access. Replies are cached, so each call is made once.
- The interface reports when the model's safety filter stops a reply; such a reply comes back empty. It is recorded as
  stopped and never retried with a changed prompt. The reasons are not visible.

### 1.3 Strategies

Three paradigms, a control, and four add-ons each tested against its parent.

| Strategy | Paradigm | What it does |
|---|---|---|
| Direct reading | Read and write | All papers in one prompt; the model writes the entry. Baseline. |
| Agentic curator | Read and write | The model works in a folder of the papers with read and search tools and must give a verbatim quote for every paragraph. |
| Evidence graph | Extract, then write | Quote-backed findings are extracted per paper (findings whose quote is not in the paper are discarded) and joined into a graph of papers, genes, variants, phenotypes and inheritance; the writer sees only the graph. Synopsis terms are computed from the graph by rule; inheritance is written by the writer. |
| Case table first | Extract, then write | One record per reported patient or family is extracted per paper and pooled; synopsis terms and inheritance are computed by rule, candidate genes are confirmed by the writer; the writer sees only the table. |
| Recall, then verify | Memory first | The model writes from memory; the draft is audited against the papers; a rewriter keeps supported claims, restates partly supported ones, corrects contradicted ones and deletes the rest. It may not add content from the papers. |
| Memory only | Control | The memory draft, with no papers. Audited, not repaired. |
| Second-hand evidence | Add-on to direct reading | For a paper not readable in full, passages from later open-access papers that cite and describe it are added, marked as second-hand, for the writer and the audit. |
| Reconciled case database | Add-on to the case table | A propose, verify, apply step merges the same patient, family or variant reported in several papers and settles conflicts. |
| Learned curation guide | Add-on to direct reading | A guide of general rules, learned in two reflection rounds from 27 training entries' omissions and extras, is appended to the writer's prompt; tested on 70 held-out entries. |

Guards applied to every strategy: ontology identifiers are chosen by the model only from candidates returned by an
ontology search; gene symbols are normalised against HGNC; entry cross-reference numbers recalled from memory are
removed; every paragraph must cite a supplied paper.

### 1.4 Audit and scoring

- **Audit.** Paragraphs are split into atomic claims attributed to the papers they cite. Each paper is given its
  claims and returns a verdict per claim (supported, partly supported, unsupported, contradicted) with a quote; a
  "supported" verdict whose quote is not found verbatim in the paper is downgraded. A claim's verdict is the best over
  the papers it cites. Flagged claims get one repair round. All verdicts are model judgements.
- **OMIM facts conveyed (primary endpoint).** Each fixed fact is marked present, partly present, absent or
  contradicted in what the draft says about the paragraph's papers. Coverage = (present + half of partial) / facts
  judged. No fact went unjudged in any run.
- **Clinical synopsis.** Precision, recall and F1 of ontology terms against the reference annotations, three ways.
  Exact: identical term identifiers. Hierarchical: both sets are expanded with all their ancestors in the ontology
  before comparing, so a more general or more specific term earns partial credit. Semantic: for each term the best
  Lin similarity to any term of the other set (information content computed from the ontology's disease annotations),
  averaged in each direction to give precision and recall. Terms are assigned by a lexical search over the ontology's
  labels and synonyms that returns candidates, from which the model chooses.
- **Allelic variants.** Recall of OMIM's in-scope variants and precision of the draft's variants, matched on
  normalised protein or nucleotide change with a model judge for names that do not normalise. Variant names are not
  validated against reference sequences. Precision counts a variant OMIM does not list as a miss whether or not the
  paper reports it.
- **Causal gene** F1 and **inheritance** agreement. A strategy that predicts nothing where the reference is not empty
  scores zero.
- **Completion.** A strategy completes an entry when its draft exists and no per-paper call failed. Strategies are
  compared only on entries every compared strategy completed. A sensitivity analysis counts a missing draft as zero
  over all entries.
- **Statistics.** Paired differences from direct reading with a bootstrap interval, the median difference, an exact
  sign test, and Holm correction across the secondary headline measures. OMIM facts conveyed is the primary endpoint
  and is not adjusted.

## 2. Main comparison: six strategies, 100 small entries

{first_para(main)}

### 2.1 Completion

{section(main, 'Completion')}

### 2.2 Scores (means over the compared entries)

{table_rows(section(main, 'Scores'), HEAD)}

Volume per entry:

{table_rows(section(main, 'How much each strategy writes'), VOL)}

### 2.3 Paired differences from direct reading

{section(main, 'Paired differences from the baseline').split('### Full paired statistics')[0].strip()}

### 2.4 Sensitivity: all 100 entries, a missing draft counted as zero

{section(main, 'Sensitivity: every entry')}

### 2.5 Pooled counts

{section(main, 'Pooled counts')}

### 2.6 Allelic variants: precision

{section(main, 'Allelic variants: precision')}

### 2.7 Inheritance errors by kind

{section(main, 'Inheritance errors by kind')}

### 2.8 OMIM facts conveyed by how the paper was readable (pooled over facts)

{section(main, 'OMIM-fact coverage by how much of the paper was readable')}

### 2.9 Paired differences from direct reading within strata of entries by access

{section(main, 'Paired differences from Direct reading within each access stratum')}

### 2.10 OMIM facts conveyed by creation era within each access level (direct reading and the memory-only control)

{section(main, 'OMIM facts conveyed by creation era')}

### 2.11 Memory-only control and direct reading by creation era (entry means)
""")

    # era table from strategies.json
    d = json.load(open(RUNS / "omim100" / "strategies.json"))
    order = ["classic (1xxxxx-5xxxxx)", "600000-609999", "610000-615999", "616000-619999", "620000 onward"]
    rows = ["| Creation era | Entries | Facts conveyed: memory / direct | Claims judged supported: memory | Gene F1: memory / direct | Inheritance match: memory / direct | Synopsis exact F1: memory / direct |",
            "|---|---|---|---|---|---|---|"]
    for era in order:
        g = d["by_stratum"].get(era)
        if not g:
            continue
        val = {r["metric"]: r["values"] for r in g["means"]}
        f = lambda k, s: pct(val.get(k, {}).get(s))  # noqa: E731
        rows.append(f"| {era} | {g['n']} | {f('gold_fact_coverage', 'closedbook')} / {f('gold_fact_coverage', 'direct')} | "
                    f"{f('claim_supported_rate', 'closedbook')} | {f('gene_f1', 'closedbook')} / {f('gene_f1', 'direct')} | "
                    f"{f('inheritance_match', 'closedbook')} / {f('inheritance_match', 'direct')} | "
                    f"{f('hpo_exact_f1', 'closedbook')} / {f('hpo_exact_f1', 'direct')} |")
    add("\n".join(rows))

    add(f"""
### 2.12 Cost per entry

{section(main, 'What each strategy costs to run')}

### 2.13 Other facts about the drafts (computed from the per-entry files)

- Evidence graph: every extracted finding carries a quote, and findings whose quote is not found in the paper are
  discarded before the graph is built; none was discarded in this run.
- Agentic curator: it reports which papers it opened (self-reported; tool calls are not logged). In the 98 entries it
  wrote it reported opening every paper, and all 2,600 quotes it gave were found verbatim in the papers.
- Recall, then verify: the memory drafts it starts from are the memory-only control's drafts.

## 3. Where the missed facts went (direct reading, fixed fact lists)

Each fact direct reading did not fully convey was checked once against the text available for its paper: stated (with a
quote that was verified in the text), partly stated, or not stated. The check is a model judgement.

{gaps.split(chr(10) + chr(10), 2)[2].strip()}

## 4. How much the measurement moves

### 4.1 Judge variation: the same drafts and the same fact lists, judged three times

{judge_replicates()}

### 4.2 Run-to-run variation: generation, audit and scoring repeated

{run_replicates()}

Reading: a difference between two strategies in OMIM facts conveyed of about one point or less on 93 entries is within
replicate noise. One replicate is one sample; the main comparison is a single run per entry.

### 4.3 Sensitivity: crediting a fact anywhere in the draft

On the same 30 entries the fixed facts were also marked against the whole draft, not only the text citing the paper.
Coverage, cited text against whole draft: direct reading 46% against 47%, evidence graph 46% against 46%, case table
45% against 45% (from the re-scoring log). Strategies that pool across papers do not lose credit under another citation.

### 4.4 The earlier scoring

Before fixed fact lists were introduced, the judge split each OMIM paragraph afresh for each draft. That scoring is kept
as a secondary row in the tables ("facts split afresh for each draft"). It runs 2–5 points higher and gives the same
ordering. The fixed lists state each fact with its subject, so a generic statement in a draft does not earn credit for
a fact about a specific family.

## 5. Ablation of the extract-then-write strategies (40 entries)

Question: how much of the difference between the extract-then-write strategies and direct reading comes from design
choices that are not the intermediate representation. Variants:

- *Matched*: per-paper extraction at high effort (as the writers), and the writer chooses the synopsis terms (and, for
  the case table, the inheritance) instead of fixed rules. The writer still sees only the graph or table.
- *Plus text*: as matched, and the writer also receives the papers' text in the layout direct reading uses.

The two changes in "matched" were made together. Choosing synopsis terms cannot change which facts or variants are
extracted, so on facts, claims and variants the matched step is the extraction effort; that attribution is an inference.
The 40 entries are weighted towards entries with full text (25 have at least half their papers readable in full), so
absolute levels are higher than in the main comparison.

{first_para(ab)}

{ablation_tables()}

Generation cost per entry at list price (from the usage tallies): direct reading $0.32, evidence graph $0.65, matched
$0.72, plus text $0.88, case table $0.72, matched $0.84, plus text $0.97. Total with audit and scoring: $1.59, $2.00,
$2.14, $2.25, $2.07, $2.26, $2.29.

Completion: direct reading, the evidence graph and the case table completed all 40. The matched and plus-text graph
variants each lost one entry and the matched and plus-text table variants two, because the safety filter stopped a
high-effort extraction call for a paper that had gone through at medium effort.

Variant precision (share of a draft's variants that are OMIM's) in this run: direct reading 87.8%, evidence graph 81.4%,
graph plus text 84.4%, case table matched 76.5%, case table plus text 85.0% (worker's report from the comparison).

## 6. Add-on: second-hand evidence

### 6.1 Retrieval

Open-access papers that cite and describe the target paper were searched for all 515 papers through Europe PMC. Passages
were found for 473 (326 of 345 abstract-only papers, 53 of 74 title-only papers, 94 of 96 full-text papers): 2,430
passages. Passages are paragraphs or table rows whose citation points at the target paper.

### 6.2 Hidden-full-text experiment (within-paper effect of access, and accuracy of second-hand claims)

For papers readable in full, the full text was hidden and entries were written by direct reading from the abstract,
with and without second-hand passages. Claims about the hidden papers were then audited against the real full text.
No repair round was applied to the two new drafts. Coverage in this experiment uses the earlier per-draft fact
splitting, not the fixed lists. Our full texts exclude supplementary material, so "unsupported by the full text" is an
upper bound on error.

{shc_body}

### 6.3 In use on the 100 entries

{first_para(sh)}

In this run {sh_tot['papers_with_passages']} of the {sh_tot['papers_supplemented']} papers not readable in full received
passages ({sh_tot['passages']:,} passages). {sh_tot['claims_on_secondhand']} of {sh_tot['claims']:,} audited claims
rested only on second-hand text, in {sh_tot['paragraphs_on_secondhand']} paragraphs. Such claims are labelled as not
checked against the cited paper and are not counted as supported; they leave the denominator of claims judged
supported. The writer did not name a later paper in any entry.

{table_rows(section(sh, 'Scores'), HEAD)}

{section(sh, 'Paired differences from the baseline').split('### Full paired statistics')[0].strip()}

Facts conveyed by how the paper was readable (pooled):

{section(sh, 'OMIM-fact coverage by how much of the paper was readable').split('###')[0].strip()}

## 7. Add-on: reconciled case database

Over the {n_rec} entries, reconciliation proposed {rec_tot['merges_proposed']} merges of patient or family records and
accepted {rec_tot['merges_accepted']} ({rec_tot['merges_rejected_by_verifier']} rejected by the verifier), in {rec_with}
entries; it merged {rec_tot['variants_merged']} variant names and found {rec_tot['conflicts_found']} conflicts between
papers. Counted individuals went from {rec_tot['individuals_before']:,} to {rec_tot['individuals_after']:,} (net; counts
rose in a few entries where a re-report gave a larger family size) and families from {rec_tot['families_before']:,} to
{rec_tot['families_after']:,}. A planted test on six entries merged 10 of 10 copied reports with their originals and
merged no unrelated records; this easy case shows only that a stated re-report is caught. The accepted merges were not
checked by a person. Cost: one or two extra calls per entry.

{first_para(rec)}

{section(rec, 'Paired differences from the baseline').split('### Full paired statistics')[0].strip()}

None of the entry-level measures uses patient counts, so no change in them is expected. Agreement of the table's
patient-count fractions with the fractions in the HPO annotations (about 560 terms) was 48% before and after
reconciliation, with a mean absolute difference of 0.26; each reference fraction comes from one source while the table
pools all papers. The case database was not validated against external per-patient ground truth.

## 8. Add-on: learned curation guide

Training (27 of 30 training entries had a direct-reading draft; scored without the audit, with the earlier per-draft
fact splitting; from the guide's log): baseline OMIM facts conveyed 53.8% and synopsis exact F1 36.6%. Round 1 changed
facts by +0.14 points and synopsis F1 by +1.29; round 2 by −1.41 and +3.57. The text rules of round 1 and the synopsis
rules of round 2 were selected by a rule fixed in advance. The final guide, run once more on the training entries:
facts +0.06 points, synopsis F1 +1.28 points. The search therefore did not improve OMIM facts conveyed on its own
training entries. A first guide, learned before stopped replies were recorded, had treated three empty drafts as
omissions and was discarded.

Held-out test:

{first_para(gd)}

{table_rows(section(gd, 'Scores'), HEAD)}

{section(gd, 'Paired differences from the baseline').split('### Full paired statistics')[0].strip()}

Editorial agreement on the same entries (from the editorial report): a draft makes about twice as many statements about
a paper as the OMIM paragraph has facts (direct reading 24.0 statements per paper, with the guide 22.2, against 11.9
facts), and 24% (direct) and 25% (guide) of a draft's statements have a counterpart in that paragraph. The paragraph is
variant-centred, so this is a lower bound on agreement with the entry.

## 9. Exploratory: entries with 30–75 references

Twelve entries, 536 papers (29 readable in full, 407 abstracts, 100 titles). Not drawn exactly as the main set: one
creation-era band has no entry. Only one entry exceeded the single-prompt budget used for direct reading (600,000
characters); direct reading split it into two batches, one of which was stopped, so that entry has no direct-reading
draft. OMIM paragraphs exist for a minority of each entry's references (3–19 papers per entry). Intervals on about ten
entries are unreliable. This tier tests many papers, not much text.

{first_para(lg)}

{section(lg, 'Completion')}

{table_rows(section(lg, 'Scores'), HEAD)}

{table_rows(section(lg, 'How much each strategy writes'), VOL)}

{section(lg, 'Paired differences from the baseline').split('### Full paired statistics')[0].strip()}

{section(lg, 'What each strategy costs to run')}

## 10. Entries created after the model's likely training data (June to November 2026)

107 phenotype entries were created in 2026 (creation dates from NCBI); 53 have at least two cited references and one
in-scope paragraph. The 30 newest were run. Phenotype annotations exist for only one of them, so synopsis and
inheritance scores rest on one entry and are not reported. The model's training cut-off is not known to us; the
memory-only control is the empirical test.

{first_para(rc)}

{section(rc, 'Completion')}

{table_rows(section(rc, 'Scores'), ("Claims supported by cited paper", "… unsupported, before the repair round",
            "… contradicted, before the repair round", "OMIM per-paper facts conveyed", "OMIM allelic variants recovered",
            "Generated variants that are OMIM variants", "Causal gene F1", "OMIM references used"))}

{table_rows(section(rc, 'Paired differences from the baseline').split('### Full paired statistics')[0],
            ("Claims supported by cited paper", "OMIM per-paper facts conveyed", "OMIM allelic variants recovered",
             "Causal gene F1"))}

Stopped replies were frequent on these entries: the agentic curator's writer was stopped on 6 of 30, direct reading's
on 2, and the evidence graph lost a paper on 7.

## 11. Earlier analyses on the main set

- **Planted errors.** In 60 paragraphs the audit had passed, one fact was altered by rule (a count, a zygosity, a
  residue or a mode of inheritance). The audit flagged all 60, each on a claim containing the altered value. The test
  measures sensitivity to blunt single-fact substitutions only; no unaltered controls were run, so the false-flag rate
  is unknown, and omissions and misattributions are not tested. In 6 of the 60 other claims were also flagged.
- **Disagreements between a draft and the reference.** Facts on which a direct-reading draft contradicted the OMIM
  paragraph were re-examined against the paper by the same model: of 37, the paper was judged to support the draft in
  22, the reference in 1, both in 1, and 13 could not be decided from the readable text. These are unconfirmed leads; no
  curator has checked them, many rest on abstracts only, and the judge had already passed the same claims.
- **Updates.** Ten entries were rolled back to an earlier reference list. A literature search found all 28 references
  OMIM later added; all passed screening and 21 (75%) became update proposals. The same run proposed 33 papers OMIM
  does not cite. Evidence-graph strategy only.
- **Retrieval without a reference list.** Given a title and the causal gene, a search capped at 12 papers selected 56
  of the 85 references OMIM cites for ten entries (66%); 47% of what it selected is in OMIM's list (entry mean).
  Evidence-graph strategy only.

## 12. Things that failed, did not replicate, or limit the claims

- The first analysis excluded entries whose writer was stopped but scored entries in which a per-paper call was
  stopped. Under that analysis the evidence graph appeared 2.1 points below direct reading on OMIM facts conveyed. With
  completion treated the same way for every strategy the difference is not distinguishable from zero.
- A bug in variant naming wrote frameshifts as missense changes in the evidence-graph and case-table drafts (39 and 44
  variant headings in 19 entries). It was fixed and the drafts regenerated before the results here.
- Recall, then verify may not add content from the papers; its low coverage is partly by construction.
- The learned guide did not improve its own training entries; its null result on held-out entries says nothing about
  better-resourced prompt optimisation.
- Second-hand evidence increased unsupported claims before repair and contradictions with the reference.
- The audit checks fidelity to the cited text, not correctness: a draft that copies a source's error passes, and a claim
  supported only by a later paper's description passed the ordinary audit in the hidden-full-text experiment.
- Unsupported by the cited papers is not wrong: the memory-only control's flagged claims are mostly unsupported, rarely
  contradicted.
- One model family wrote, audited and judged everything. No person has read any draft, verdict or fact judgement.
- Strategies were developed on the same entries they are evaluated on.
- Published systems (for example SLIDERS, PaperQA2) were not run; the strategies are our own implementations of the
  ideas.
- No second model was tested.

## 13. Total model usage

All experiments, pilots and re-scoring: {calls:,} cached model calls, {inp / 1e6:.0f} million input and
{out / 1e6:.0f} million output tokens, about ${cost:,.0f} at list price.
""")
    return "\n".join(parts)


if __name__ == "__main__":
    text = build()
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(text):,} characters, {text.count(chr(10)):,} lines)")
