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

## What the proof of concept shows

The pipeline was run on **100 OMIM phenotype entries** drawn at random (fixed seed, 20 from each of five
creation-era bands, 2–12 references each; list in [`evalsets/omim100.tsv`](evalsets/omim100.tsv)). Each entry was
given exactly the references OMIM cites, 515 papers in all, with the causal gene withheld, and was written twice from
the same papers: once from the evidence knowledge graph and once directly, with no extraction or graph. Every draft was
audited and scored against OMIM. Generated entries, evidence and scores are in [`results/omim100/`](results/omim100/).

Means over the 100 entries, except where a count is given.

| | Evidence graph | Direct baseline |
|---|---|---|
| Claims the audit found supported by the cited paper | 96.5% (11,120 claims) | 96.1% (10,040 claims) |
| Claims unsupported or contradicted, before the repair round → after | 0.3% → 1 claim | 0.4% → 0 |
| Causal gene, against OMIM's gene map (F1) | 99.3% | 98.6% |
| Mode of inheritance matches | 92% | 91% |
| OMIM's allelic variants recovered | 65.8% | 65.6% |
| Clinical synopsis as HPO terms: exact / hierarchical / semantic F1 | 34% / 55% / 65% | 36% / 56% / 66% |
| Facts in OMIM's own per-paper paragraphs that the draft conveys | 50.9% | 51.4% |
| … when the paper could be read in full | 76% | 77% |
| … when only the abstract could be read | 42% | 43% |
| OMIM facts the draft contradicts | 0.8% (43 of 5,663) | 0.7% (37) |

The full paired comparison, with confidence intervals and breakdowns, is in
[`results/omim100/comparison.md`](results/omim100/comparison.md).

**1. The drafts are faithful to their sources.** About 96% of the claims in a draft were judged fully supported by the
cited paper, the rest partly supported; after one repair round, one unsupported claim remained in 21,160. Every
extracted finding carried a quote that was found in its paper (3,650 of 3,652 quotes verbatim). The audit itself was
tested by altering one fact (a count, a zygosity, a residue, a mode of inheritance) in 60 paragraphs it had passed: it
flagged all 60, each on the altered fact ([`audit_check.json`](results/omim100/audit_check.json)).

**2. What limits a replica of OMIM is access to the papers, not accuracy.** OMIM's curators read whole papers. Only 96
of the 515 cited papers (19%) were openly readable in full; 345 were abstract only and 74 title only. Where the full
text was available the draft conveyed about three quarters of the facts in OMIM's paragraph about that paper; from an
abstract, about two fifths. Variant recovery follows the same line: 49% for entries with abstracts only, 84% where at
least half the references were readable in full.

**3. The knowledge graph did not make the entries more accurate at this scale.** With 2–12 papers per entry, a model
that can hold all of them in context writes an equally faithful entry directly. No score differs by more than a few
points. The graph draft finds more (about 30% more clinical-synopsis terms and 20% more variants; HPO recall +2.3 points,
95% interval −0.3 to +4.9) at lower agreement with OMIM (HPO precision −3.5 points, interval −6.7 to −0.6;
hierarchical F1 −1.7, interval −3.0 to −0.4). Where most papers were readable in full, the direct draft conveyed more
of OMIM's facts (70.5% against 66.0% over 23 entries), which points to detail lost in the extraction step. What the
graph does provide is structure and provenance: each paragraph lists the findings it rests on, each finding its
quotes, and the gene, inheritance and variant tables are computed rather than written.
Whether it helps for entries with hundreds of references, which no context window holds, was not tested.

**4. Where a draft and OMIM disagree, the paper usually sides with the draft.** Each of the 43 facts on which the graph
draft contradicted OMIM's paragraph was taken back to the paper. The paper supported the draft in 29, OMIM in 1 and
both in 5; 8 could not be decided from the readable text. Of the 13 cases with full text, the draft was right in 9 and
OMIM in 1. Typical cases are transposed digits or a changed base or residue in a variant name. These are listed in
[`candidate_corrections.md`](results/omim100/candidate_corrections.md) as leads for a curator; they compare against
the copy of OMIM's text in ClinVar and have not been checked against the live entries. One inheritance annotation in
the gold standard was also found to be wrong (entry 621068 is recessive in the paper and the draft, dominant in the
HPO annotation file).

**5. Updates can be proposed (stretch goal).** Ten entries were rolled back to their earlier references and the later
literature was searched. All 28 references that OMIM's curators went on to add were found by the search, and 21 of
them (75%) came through screening and were turned into update proposals; of 165 drafted paragraphs the audit flagged
2. The same run proposed 33 papers OMIM does not cite.

**6. The literature can be found without OMIM's reference list, in part.** For ten entries the pipeline was given
only the title and the causal gene and searched PubMed and Europe PMC itself (`--retrieval open`, capped at 12 papers
per entry). It selected 56 of the 85 references OMIM cites (66%), and just under half of what it selected (47%) is in
OMIM's list. Entries written from that literature were as faithful as the rest (97% of claims supported) and matched
OMIM's mode of inheritance in all ten ([`results/open10/`](results/open10/)).

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
| `aiomim run MIM… [--retrieval oracle\|open] [--strategy kg\|direct\|both] [--jobs N]` | Replicate existing entries and score them. |
| `aiomim create --title "…" --gene SYMBOL [--pmid …]` | Draft a **new** entry from a title, gene and optional seed papers. |
| `aiomim update MIM… [--as-of YEAR]` | Propose **updates** to an existing entry from literature it does not cite; `--as-of` back-tests against the references OMIM later added. |
| `aiomim backtest MIM…` | Back-test update discovery over several entries and pool the result. |
| `aiomim evalset -n 100 --out FILE` | Draw a reproducible, stratified evaluation set. |
| `aiomim compare RUN` | Paired comparison of the two strategies, and the edge-level graph comparison with OMIM. |
| `aiomim audit-check RUN` | Plant known errors in passed paragraphs and count how many the audit catches. |
| `aiomim adjudicate RUN` | Where a draft and OMIM disagree, check which one the paper supports. |
| `aiomim report RUN` | Build the HTML review page for a run (one file, or page plus per-entry data for large runs). |
| `aiomim export RUN --out DIR` | Copy a run for sharing, without gold-standard wording. |
| `aiomim summary RUN` | Recompute and print the score table for a run. |

`--retrieval oracle` (default) gives the pipeline exactly the references OMIM cites and withholds the causal gene, which
must be recovered from the papers. `--retrieval open` gives it the entry's title and gene and has it find the
literature itself. `--strategy direct` is the baseline with no extraction and no graph: the papers go straight into
one prompt.

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
- **Small entries only.** Entries had 2–12 references. Large entries were not attempted.
- **The model may know OMIM.** Guards (quote checks, citation checks, stripping of recalled OMIM numbers) limit what
  memory can contribute, and scores for the most recently created fifth of the set (MIM 620000 onward) are in line with the rest, but there
  is no clean test on entries created after the model's training cut-off.
- **The HPO comparison has a soft ceiling.** HPO's annotations are themselves a curated reading of OMIM's synopsis,
  made with the full papers; a term the draft reports and OMIM does not is counted against precision whether or not it
  is correct.
- **One run.** Model output varies between runs; nothing here was repeated to measure that variance.
- **Cost.** The 100 entries, written both ways, audited, scored and once re-scored, took about 3,300 fresh model calls
  (23.6M input and 7.5M output tokens; about $290 at API list prices, run here on a Claude subscription).
- **Not exercised:** drafting a brand-new entry (`aiomim create`) has not been run.
