# aiomim

Automated, evidence-grounded curation of [OMIM](https://www.omim.org)-style entries from the published literature.

OMIM is the reference catalogue of human genes and genetic disorders. It is written by hand: roughly one new entry and
ten updates a day. `aiomim` is a proof of concept that an entry can be drafted automatically from the papers a curator
would read, with every sentence traceable to a quote in a cited paper, and that the result can be scored against the
entry OMIM's curators actually wrote.

Given a MIM number, the pipeline:

1. assembles a **gold standard** for that entry from public, OMIM-derived sources;
2. **retrieves** the literature (OMIM's own reference list, or a search from scratch);
3. **extracts** quote-backed findings from each paper and discards any whose quote is not in the paper;
4. joins the findings into an **evidence knowledge graph** (papers, genes, variants, HPO phenotypes, inheritance);
5. **writes** the entry from the graph in OMIM's layout and style;
6. **audits** every claim against the cited paper, and revises what the audit flags;
7. **scores** the entry against the gold standard;
8. builds a **review page** where a curator accepts, edits or rejects each paragraph.

## What the study shows

Nine ways of generating an entry were run on the same entries and scored against what OMIM's curators wrote. The full
write-up, with methods, tables, figures and limitations, is the paper draft in
[`docs/paper-draft.md`](docs/paper-draft.md); a survey of published approaches is in
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

**Six strategies on 97 entries** (three entries are left out because the model's safety filter stopped a writer).
Means over entries.

| | Direct reading | Agentic curator | Evidence graph | Case table first | Recall, then verify | Memory only |
|---|---|---|---|---|---|---|
| Claims supported by the cited paper | 96.1% | 96.5% | 96.6% | 94.5% | 94.3% | 51.5% |
| Unsupported or contradicted, before repair | 0.4% | 0.2% | 0.3% | 0.8% | 0.6% | 22.3% |
| OMIM per-paper facts conveyed | 52.9% | 52.3% | 50.8% | 49.1% | 18.1% | 20.4% |
| … paper readable in full | 79.1% | 77.9% | 76.5% | 68.2% | 17.1% | 17.5% |
| … abstract only | 43.9% | 43.7% | 42.0% | 41.7% | 17.0% | 19.2% |
| Clinical synopsis, exact HPO F1 | 35.6% | 35.3% | 34.2% | 33.9% | 26.1% | 30.4% |
| OMIM allelic variants recovered | 67.6% | 67.1% | 65.6% | 63.4% | 11.7% | 15.6% |
| Causal gene F1 | 98.6% | 98.6% | 99.3% | 96.1% | 97.6% | 97.6% |
| Inheritance matches OMIM | 93.8% | 93.8% | 92.8% | 90.7% | 74.2% | 83.5% |
| Generation cost per entry (list price) | $0.27 | $0.29 | $0.58 | $0.63 | $0.71 | $0.07 |

The full comparison, with paired differences, confidence intervals and breakdowns, is in
[`results/omim100/strategies.md`](results/omim100/strategies.md).

1. **Reading the papers directly is the best and the cheapest for a typical entry.** Direct reading and the agent are
   level. Extracting into a graph or a case table first conveys 2.1 and 3.8 points fewer OMIM facts (95% intervals
   0.4–4.1 and 2.0–6.0) at twice the generation cost, with no gain in faithfulness.
2. **The drafts are faithful to their sources.** About 96% of claims were fully supported by the cited paper and the
   rest partly; after one repair round at most one unsupported claim remained in about 10,000. The audit flagged all
   60 errors planted in paragraphs it had passed ([`audit_check.json`](results/omim100/audit_check.json)).
3. **Access, not method, limits a replica of OMIM.** From a full text 79% of OMIM's facts are conveyed, from an
   abstract 44%. Of all OMIM facts, 44% were conveyed, 5% were in the text we had and left out, 12% were partly there,
   and 38% were in no text we could read ([`gaps.direct.md`](results/omim100/gaps.direct.md)).
4. **The model's memory is not a source.** Written from memory, 22% of claims were unsupported or contradicted by the
   cited papers, and for entries numbered 620000 onward memory conveyed 10% of OMIM's facts against 57% for reading.
   Checking a memory draft against the papers left less than any reading strategy.
5. **Second-hand evidence gives leads, not text.** Open-access papers describing the target were found for 473 of the
   515 papers. With a paper's full text hidden, they closed about 6 points of a 43-point gap; claims taken from a later
   paper's running text were unsupported or contradicted in 5% of cases and rows from review tables in 9 of 21. In use
   it raised variant recall by 5 points and doubled contradictions with OMIM
   ([`results/omim100_secondhand/`](results/omim100_secondhand/)).
6. **Reconciliation fixes the database, not the entry.** It merged 40 re-reported patients or families in 26 of 100
   entries (6% fewer individuals counted) and changed no entry-level score. The pooled case database is in
   [`results/omim100_reconciled/casebase/`](results/omim100_reconciled/casebase/).
7. **A learned curation guide changed nothing measurable** on 68 held-out entries
   ([`results/omim100_guided/`](results/omim100_guided/)).
8. **With 30–75 papers the balance shifts a little.** The reading strategies stay level; the case table conveys 1.7
   points more facts than direct reading but its rule-computed inheritance was wrong on 3 of 11 entries, structure
   costs four times as much, and stopped replies become common ([`results/large12/`](results/large12/)).
9. **Where a draft and OMIM disagree, the paper usually sides with the draft.** Of 43 facts on which an
   evidence-graph draft contradicted OMIM's paragraph, the paper supported the draft in 29, OMIM in 1 and both in 5; 8
   could not be decided. They are listed in
   [`candidate_corrections.md`](results/omim100/candidate_corrections.md) as leads for a curator.
10. **Updates can be proposed (stretch goal).** With ten entries rolled back to earlier references, a search found all
    28 references OMIM later added and 21 became update proposals; of 165 drafted paragraphs the audit flagged 2.
11. **The literature can be found without OMIM's reference list, in part.** For ten entries a search selected 56 of
    the 85 references OMIM cites, and 47% of what it selected is in OMIM's list
    ([`results/open10/`](results/open10/)).

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
     │         clinical synopsis, inheritance and the gene–phenotype table are computed from the graph
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
- **Structured fields are computed, not written.** Clinical synopsis, inheritance and gene links come from counting
  support in the graph, restricted to papers that are about the entry's subject.
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
