# aiomim

Automated, evidence-grounded curation of [OMIM](https://www.omim.org)-style entries from the published literature.

OMIM is the reference catalogue of human genes and genetic disorders. It is written by hand: roughly one new entry and
ten updates a day. `aiomim` is a proof of concept that an entry can be drafted automatically from the papers a curator
would read, with every sentence traceable to a quote in a cited paper, and that the result can be scored against the
entry OMIM's curators actually wrote.

Given a MIM number, the pipeline:

1. assembles a **gold standard** for that entry from public, OMIM-derived sources;
2. **retrieves** the literature (OMIM's own reference list, or a search from scratch);
3. **writes** the entry in OMIM's layout and style with one of nine generation strategies, from reading all the
   papers in one prompt to building an evidence knowledge graph or a table of reported cases first;
4. **audits** every claim against the cited paper, and revises what the audit flags;
5. **scores** the entry against the gold standard;
6. builds a **review page** where a curator accepts, edits or rejects each paragraph.

## What the study shows

Nine ways of generating an entry were run on the same entries and scored against what OMIM's curators wrote. The full
write-up is the conference paper draft [`paper/po_run1/final_paper.pdf`](paper/po_run1/final_paper.pdf), built from
the result files through [`paper/materials/experimental_log.md`](paper/materials/experimental_log.md) (the earlier
markdown draft in [`docs/paper-draft.md`](docs/paper-draft.md) predates the corrected analysis); a survey of published approaches is in
[`docs/approach-survey.md`](docs/approach-survey.md).

**The entries.** 100 OMIM phenotype entries drawn at random (fixed seed, 20 from each of five creation-era bands, 2–12
references each; [`evalsets/omim100.tsv`](evalsets/omim100.tsv)), 515 papers, of which 96 were openly readable in
full, 345 as an abstract and 74 as a title only. Each strategy got exactly the references OMIM cites, with the causal
gene withheld. Twelve further entries with 30–75 references ([`evalsets/large12.tsv`](evalsets/large12.tsv)) test
larger entries.

**The strategies.** Six were compared head to head; three more are built on them.

| Strategy (`--strategy`) | What it does |
|---|---|
| Direct reading (`direct`) | All papers in one prompt; the model writes the entry. |
| Evidence graph (`kg`) | Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph. |
| Agentic curator (`agent`) | The model reads and searches a folder of the papers with tools, then writes with a quote for every paragraph. |
| Case table first (`cohort`) | One record per reported patient or family, pooled into a table; the entry is rendered from it. |
| Recall, then verify (`recall`) | A draft from memory is checked against the papers; unsupported claims are deleted. |
| Memory only (`closedbook`) | Written from memory with no papers. A control. |
| Second-hand evidence (`secondhand`) | Direct reading, with unreadable papers supplemented by what later open-access papers say they reported. |
| Reconciled case database (`reconciled`) | The case table after merging the same patient, family or variant across papers. |
| Learned curation guide (`guided`) | Direct reading with a guide learned from other entries' omissions and extras. |

**Six strategies on 93 entries.** An entry is compared only when every strategy completed it in full: seven entries
are left out because the model's safety filter stopped a writer or a per-paper call. OMIM's per-paper text is scored
against fact lists fixed in advance and reused for every strategy. Means over entries.

| | Direct reading | Agentic curator | Evidence graph | Case table first | Recall, then verify | Memory only |
|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed (primary measure) | 49.1% | 48.4% | 48.6% | 47.2% | 14.6% | 15.1% |
| … paper readable in full (pooled over facts) | 77.6% | 76.7% | 78.8% | 71.7% | 13.3% | 11.5% |
| … abstract only (pooled over facts) | 40.1% | 39.6% | 38.1% | 38.7% | 12.9% | 13.3% |
| Claims judged supported by the cited paper | 96.1% | 96.4% | 96.5% | 94.7% | 94.2% | 50.8% |
| Unsupported, before repair | 0.2% | 0.1% | 0.2% | 0.3% | 0.6% | 22.1% |
| Clinical synopsis, exact HPO F1 | 35.9% | 35.6% | 34.6% | 34.0% | 24.9% | 30.6% |
| OMIM allelic variants recovered | 66.5% | 65.9% | 65.9% | 64.3% | 11.6% | 15.2% |
| Generated variants that are OMIM variants | 88.7% | 87.9% | 76.9% | 72.9% | 100.0% | 97.2% |
| Causal gene F1 | 97.5% | 97.5% | 98.2% | 93.9% | 82.8% | 83.9% |
| Inheritance matches OMIM | 93.5% | 93.5% | 92.5% | 91.4% | 73.1% | 82.8% |
| Generation cost per entry (list price) | $0.26 | $0.28 | $0.56 | $0.61 | $0.70 | $0.07 |

The full comparison, with paired differences, confidence intervals, completion and breakdowns, is in
[`results/omim100/strategies.md`](results/omim100/strategies.md). One model wrote, audited and scored everything, and
no curator has read any draft or judgement.

1. **The reading strategies are close at today's open access.** Against direct reading, the agent conveys 0.6 points
   fewer OMIM facts (95% interval −1.3 to 0.0), the evidence graph 0.5 fewer (−1.5 to +0.5) and the case table 1.9
   fewer (−3.1 to −0.8). Repeating generation, audit and scoring moves a difference between two strategies by about
   ±1.0 point over 93 entries. For the case table the interval excludes zero but the sign test does not reach 0.05
   (p = 0.071). Structure costs about twice as much to generate and lowers variant precision.
2. **Differences grow where more full text is readable.** Among the 21 entries with half or more of their papers in
   full text, the case table is 6.1 points below direct reading (−8.3 to −3.6) and the agent 2.0 below (−3.4 to
   −0.7); among the 46 entries with no full text all are within noise. This comparison across entries is
   observational. In an ablation on 38 entries, running per-paper extraction at the writers' effort and letting the
   writer choose the synopsis terms put the evidence graph 1.8 points above direct reading (+0.4 to +3.3) and the
   case table level with it (−0.2, −2.4 to +2.2), so the deficit depends on how the strategies were implemented
   ([`results/ablation40/`](results/ablation40/)).
3. **Access, not method, limits a replica of OMIM.** With the same papers and their full text hidden, direct reading
   conveyed 31.2% of OMIM's facts from the abstract and 77.4% from the full text (paired difference 43.9 points, 45 of
   46 entries higher; 43.7 points when no arm goes through the repair round). When the text given to the model states
   a fact, direct reading, the evidence graph and the agent convey 93.6–94.4% of such facts and the case table 91.0%;
   when it does not, 5.5–6.9% ([`strategies.by_availability.md`](results/omim100/strategies.by_availability.md)). Of
   the facts conveyed in full from papers readable only as an abstract or title, 1.7% are stated in no supplied text
   ([`gaps.direct.conveyed.md`](results/omim100/gaps.direct.conveyed.md)). Of all OMIM facts, 43% were conveyed, 4% were stated in the text we had and left out, 13% were
   partly stated, and 40% were in no text we could read
   ([`gaps.direct.frozen.md`](results/omim100/gaps.direct.frozen.md)).
4. **The drafts are faithful to their sources, as far as the audit can see.** About 96% of claims were judged fully
   supported by the cited paper and nearly all the rest partly; after one repair round one unsupported claim remained
   among the reading strategies' drafts. The audit flagged all 60 errors planted in paragraphs it had passed
   ([`audit_check.json`](results/omim100/audit_check.json)) and none of the 361 claims in the same paragraphs when
   they were audited again unaltered ([`audit_control.json`](results/omim100/audit_control.json)). It checks fidelity
   to the cited text, not correctness.
5. **The model's memory is not a source.** Written from memory, 22% of claims were unsupported by the cited papers,
   and for entries numbered 620000 onward memory conveyed 5.7% of OMIM's facts against 53.5% for reading. Checking a
   memory draft against the papers left no more than memory alone.
6. **Second-hand evidence gives leads, not text.** Open-access papers describing the target were found for 473 of the
   515 papers. With a paper's full text hidden, they closed 4.9 points of the 43.9-point gap; claims taken from a later
   paper's running text were unsupported or contradicted in 5 of 91 cases and rows from review tables were unsupported
   in 9 of 21. In use it raised variant recall by 5.0 points and also raised unsupported claims before repair and
   contradictions with OMIM ([`results/omim100_secondhand/`](results/omim100_secondhand/)).
7. **Reconciliation changes the database, not the entry.** It merged 40 re-reported patient or family records in 27
   of 100 entries (individuals counted fell from 2,580 to 2,413) and changed no entry-level score. The merges were not
   checked by a person. The pooled case
   database is in [`results/omim100_reconciled/casebase/`](results/omim100_reconciled/casebase/).
8. **A learned curation guide changed nothing measurable** on 68 held-out entries
   ([`results/omim100_guided/`](results/omim100_guided/)).
9. **Entries with 30–75 papers are exploratory.** Ten entries are comparable, nearly all their papers are abstracts,
   and stopped replies are common. The case table conveyed 1.8 points more facts than direct reading there, with its
   rule-computed inheritance wrong on two or three entries, at several times the cost
   ([`results/large12/`](results/large12/)).
10. **Disagreements with OMIM are leads for a curator.** Of 37 facts on which a direct-reading draft contradicted
    OMIM's paragraph, the same model judged the paper to support the draft in 22, OMIM in 1 and both in 1; 13 could
    not be decided. None has been confirmed by a person. An earlier list from the evidence-graph drafts is in
    [`candidate_corrections.md`](results/omim100/candidate_corrections.md).
11. **Updates can be proposed (stretch goal).** With ten entries rolled back to earlier references, a search found all
    28 references OMIM later added and 21 became update proposals.
12. **The literature can be found without OMIM's reference list, in part.** For ten entries a search selected 56 of
    the 85 references OMIM cites, and 47% of what it selected is in OMIM's list
    ([`results/open10/`](results/open10/)).

**A second round of experiments** tested three objections to the study at small scale (4 to 10 entries each;
design, results and deviations in [`docs/experiments-round2.md`](docs/experiments-round2.md)):

- **Larger inputs.** Padding an entry's own papers with up to thirty times as much unrelated full text did not lower
  any strategy's coverage, and direct reading across three prompts lost nothing
  ([`results/padding/`](results/padding/)). On four real entries with 76–148 references and much readable text, the
  model's safety filter stopped at least one strategy every time, so no comparison could be made there
  ([`results/largeft/`](results/largeft/)).
- **Published systems.** On the same papers and model, PaperQA2's document-query pipeline conveyed 14.5 points fewer
  OMIM facts than direct reading on 10 entries and GraphRAG about 13 fewer on 4, at 5 to 33 times the cost; STORM
  could not be run with this model ([`results/external/`](results/external/)). Each system ran at one setting, and
  PaperQA2 without its agent.
- **Audit coverage.** The audit caught every planted wrong citation and every sentence moved between papers, and
  flagged no unaltered paragraph. It cannot see an added irrelevant citation or an omission, and it caught a dropped
  qualifier 11 times in 30 ([`audit_stress.md`](results/omim100/audit_stress.md)).

**Improving on direct reading.** Of ten approaches reviewed ([`docs/direct-improvements.md`](docs/direct-improvements.md)),
the three tested on 41 held-out entries with full text all helped a little, within the 3–5 points that reading the
supplied text better can add: a completeness pass (check each paper for omissions, then revise) conveyed 2.6 more
points of curator facts with no loss of fidelity at about twice the cost; merging three drafts conveyed 3.1 more but
partly from outside the papers and with more unsupported claims; a curator checklist in the prompt added 1.6 at no
cost; the checklist and the completeness pass together conveyed 3.3 more on 35 entries, little more than the
completeness pass alone ([`results/direct_improve/`](results/direct_improve/)). Access to full text remains the
larger lever.

A curator reviews a run on a single page: the draft in OMIM's layout, the audit's verdict and evidence for every
claim, the comparison with OMIM, the evidence graph, and accept / edit / reject for each paragraph. To browse the
results in this repository:

```bash
AIOMIM_RUNS=results aiomim report omim100
```

This writes `results/omim100/report.html` (with a `report_data/` folder beside it); open it in a browser.

## Quick start

```bash
pip install -e ".[dev]"
```

The model is called through the [Claude Code](https://claude.com/claude-code) CLI in headless mode, so the pipeline
runs on a Claude subscription and needs no API key. Install the CLI and log in once (`claude`, then `/login`).

```bash
aiomim gold 500001                       # what gold-standard material exists for this entry
```

```bash
aiomim run 500001 --run demo             # replicate the entry and score it
```

```bash
aiomim report demo                       # build runs/demo/report.html, the curator review page
```

Everything is cached under `data/` (HTTP responses, model replies, ontologies), so re-running a command repeats no
network or model calls. Outputs go to `runs/<run>/<mim>/`.

## Commands

| Command | What it does |
|---|---|
| `aiomim gold MIM…` | Show the gold standard available for each entry. |
| `aiomim select --from 2026/01/01 --to 2026/11/30` | List entries created in a date window with their gold coverage, to build an evaluation set (entries newer than the model's training data are the cleanest test). |
| `aiomim run MIM… [--retrieval oracle\|open] [--strategy NAMES\|all] [--jobs N]` | Replicate existing entries and score them. `NAMES` is a comma-separated list of strategies; `all` means the six compared head to head. |
| `aiomim create --title "…" --gene SYMBOL [--pmid …]` | Draft a **new** entry from a title, gene and optional seed papers. |
| `aiomim update MIM… [--as-of YEAR]` | Propose **updates** to an existing entry from literature it does not cite; `--as-of` back-tests against the references OMIM later added. |
| `aiomim backtest MIM…` | Back-test update discovery over several entries and pool the result. |
| `aiomim evalset -n 100 --out FILE` | Draw a reproducible, stratified evaluation set. |
| `aiomim compare RUN [--baseline NAME] [--entries-file F --tag T]` | Every strategy of a run side by side, with paired differences from the baseline; optionally on a subset of entries. |
| `aiomim audit-check RUN` | Plant known errors in passed paragraphs and count how many the audit catches. |
| `aiomim adjudicate RUN` | Where a draft and OMIM disagree, check which one the paper supports. |
| `aiomim report RUN` | Build the HTML review page for a run (one file, or page plus per-entry data for large runs). |
| `aiomim export RUN --out DIR` | Copy a run for sharing, without gold-standard wording. |
| `aiomim summary RUN` | Recompute and print the score table for a run. |
| `aiomim gaps RUN` | For OMIM facts a draft missed, check whether they were in the text available. |
| `aiomim secondhand-fetch` / `secondhand-check` | Fetch later papers' descriptions of each paper; test second-hand evidence by hiding full texts. |
| `aiomim casebase RUN` / `reconcile-check RUN` | Export the pooled case database and score its frequencies; plant re-reports to test reconciliation. |
| `aiomim guide-split` / `guide-learn` / `editorial` | Split entries into training and test, learn a curation guide, and measure how much of a draft OMIM also says. |

`--retrieval oracle` (default) gives the pipeline exactly the references OMIM cites and withholds the causal gene, which
must be recovered from the papers. `--retrieval open` gives it the entry's title and gene and has it find the
literature itself. `--strategy direct` is the baseline with no extraction and no graph: the papers go straight into
one prompt. The strategies are listed in the table near the top; `guided` needs a learned guide
(`guides/omim100.guide.md`, or `AIOMIM_GUIDE`).

## How it works

```
 MIM number
     │
     ▼
 gold.py ───────────────► GoldEntry (public sources; used only for scoring and, in oracle mode, the PMID list)
     │
     ▼
 retrieve.py   oracle: OMIM's reference list        open: plan queries → PubMed + Europe PMC → triage → citation hop
     │         abstracts from PubMed; full text from Europe PMC / PMC where open access
     ▼
 extract.py    one call per paper → findings: OMIM-style statement + verbatim quotes + genes, variants, phenotypes
     │         grounding.py checks every quote against the paper text; no quote found → finding discarded
     │         phenotype phrases → HPO terms (exact match, else model picks among ontology search hits)
     ▼
 kg.py         evidence graph: Paper─reports▶Finding─▶Gene / Variant / Phenotype / Inheritance, provenance on every edge
     │         gene aliases → approved symbol; "G14459A", "m.14459G>A", "A72V", "p.Ala72Val" → one variant node
     ▼
 synthesize.py writer sees only verified findings, arranged by the graph; each paragraph must name its findings
     │         clinical synopsis computed from the graph; inheritance stated by the writer per gene link
     │         (graph's best-supported mode only when the writer states none)
     ▼
 verify.py     independent audit: per cited paper, each claim → supported / partial / unsupported / contradicted
     │         one repair round on flagged paragraphs, then re-audit
     ▼
 evaluate.py   scores against GoldEntry           report/  curator review page (accept / edit / reject, export)
```

### Guards against hallucination

The design assumes the model will sometimes be wrong and places a check after each step that does not depend on the
model being right:

- **Quotes are checked without a model.** Each finding carries verbatim quotes; a token-level matcher looks for them
  in the paper. A changed number, residue or gene symbol fails the match, and the finding is dropped.
- **The writer cannot cite what it was not given.** A paragraph must list finding IDs; paragraphs with none, or with
  IDs that do not exist, are deleted. Author–year citations in the text that match no supplied paper are reported.
- **HPO IDs cannot be invented.** The model may only choose among candidates returned by a search of the ontology.
- **Structured fields are computed or checked, not taken on trust.** The clinical synopsis comes from counting
  support in the graph, restricted to papers that are about the entry's subject. Gene links and their modes of
  inheritance are stated by the writer, and a gene link survives only if the findings it cites are about that gene;
  the graph supplies the mode of inheritance only when the writer states none.
- **A second reader audits the result** against the paper text, without seeing the findings or the graph. An audit
  verdict of "supported" whose own evidence quote is not in the paper is downgraded.
- **A curator has the last word.** The review page shows, for each paragraph, the claims, verdicts, quotes and papers.

### The knowledge graph as retrieval index

The writer's context is assembled from the graph rather than from text chunks ranked by embedding similarity. For
each section it receives the findings filed there, oldest first, and alongside them the cross-paper tables the graph
makes possible: which papers report variants in each gene, the distinct variants after merging the different ways
papers name them, which modes of inheritance are asserted and by whom, and which clinical features are reported
present or absent in how many papers. `--strategy both` runs the no-graph baseline on the same papers so the two can
be compared on the same scores.

## The gold standard

OMIM's site forbids crawling and its full text requires a licensed API key, so the default gold standard is built
from sources that redistribute OMIM-derived data publicly:

| Part of the entry | Source |
|---|---|
| Title, symbol, alternative titles, entry type | NCBI E-utilities (`db=omim`), MedGen, OMIM's public `mim2gene.txt` |
| Reference list | NCBI E-utilities link `omim_pubmed_cited` |
| Gene–phenotype links | NCBI `mim2gene_medgen` (GeneMap rows), MedGen |
| Mode of inheritance | HPO annotations (`phenotype.hpoa`), MedGen |
| Clinical synopsis as HPO terms | HPO annotations (`phenotype.hpoa`) |
| Allelic variants and **OMIM's own per-paper text** | ClinVar, submitter "OMIM": each allelic-variant paragraph with the PMID it summarises |
| Full entry text (optional) | OMIM API, if `OMIM_API_KEY` is set |

The ClinVar submissions are the important one: they are paragraphs written by OMIM's curators, each tied to the
paper it summarises, which lets "is each paper portrayed accurately?" be measured directly.

Gold material is fetched at run time into `data/` and is not committed to this repository.

## Scores

| Score | Meaning |
|---|---|
| **Claims supported** | Of the atomic claims in the generated entry, the share the audit found stated in the cited paper. Needs no gold. *Claim error rate* is the share found unsupported or contradicted. |
| **Gold-fact coverage** | OMIM's per-paper paragraphs are split into atomic facts; the share the draft conveys (a partial match counts half). *Contradicted* counts facts the draft gets wrong. |
| **HPO exact F1** | Generated clinical-synopsis HPO terms against HPO's annotations of the entry, identical IDs only. |
| **HPO hierarchical F1** | The same after adding every ancestor of each term to both sets, so a near miss in the ontology earns partial credit. |
| **HPO semantic F1** | Best-match average of Lin similarity between the two term sets. |
| **Variant recall** | Share of OMIM's allelic variants for the entry that appear among the generated ones, matched across notations. |
| **Gene F1 / inheritance match** | Causal gene(s) and mode(s) of inheritance against OMIM's. |
| **Reference recall / precision** | Cited PMIDs against OMIM's reference list (a retrieval score in `open` mode). |

## Layout

```
src/aiomim/
  config.py  cache.py  llm.py  models.py     settings, disk cache, Claude Code wrapper, shared data model
  sources/                                   NCBI, Europe PMC, full text, HPO, HGNC, ClinVar, MedGen, OMIM API
  gold.py  retrieve.py  extract.py  grounding.py  kg.py  synthesize.py  verify.py  evaluate.py  update.py
  evalset.py  compare.py  auditcheck.py  adjudicate.py  export.py
  pipeline.py  cli.py  render.py  report/
evalsets/                                    the evaluation sets used
results/                                     generated entries, evidence and scores from the runs reported above
tests/                                       offline unit and end-to-end tests; live tests marked `network`
```

```bash
python -m pytest -m "not network and not llm"
```

## Limits of this proof of concept

- **The comparison with OMIM is partial.** OMIM's full entry text needs a licensed API key, so the text comparison
  rests on the allelic-variant paragraphs OMIM deposits in ClinVar (476 paragraphs here), and the clinical synopsis,
  genes and inheritance on HPO, MedGen and NCBI files derived from OMIM. The Clinical Features and other narrative
  sections were audited against their papers but not compared with OMIM's wording. Scoring against full OMIM text is
  implemented (`OMIM_API_KEY`) but has never been run.
- **The audit and the judges are the same model family as the writer.** The planted-error test covers blunt
  single-fact substitutions; it says nothing about omissions, misplaced emphasis or subtle misreadings. No human
  curator has reviewed any of these entries.
- **Mostly small entries.** The main comparison has 2–12 references per entry. The large tier has twelve entries
  with 30–75 references, nearly all of whose papers were abstracts, so inputs too large for one prompt were not
  tested.
- **Stopped replies.** The model's safety filter stopped some replies, for reasons that are not visible. Such an
  entry is recorded as having no draft and is left out of comparisons; it is never retried with a changed prompt.
- **The model may know OMIM.** The memory-only control measures this: for entries numbered 620000 onward memory
  conveys 10% of OMIM's facts and reading 57%, so the reading results do not rest on memorised text. There is still no
  test restricted to entries created after the model's training cut-off.
- **The HPO comparison has a soft ceiling.** HPO's annotations are themselves a curated reading of OMIM's synopsis,
  made with the full papers; a term the draft reports and OMIM does not is counted against precision whether or not it
  is correct.
- **One run.** Model output varies between runs; nothing here was repeated to measure that variance.
- **Cost.** Everything reported here (nine strategies, the audits, scoring, the experiments and their pilots) took
  about 21,800 model calls: 152M input and 42M output tokens, about $1,700 at API list prices. It was run on a Claude
  subscription, part of it on paid overage. One entry of typical size costs about $1.20 with direct reading: $0.27 to
  write, $0.75 to audit and $0.20 to score.
- **Not exercised:** drafting a brand-new entry (`aiomim create`) has not been run.
