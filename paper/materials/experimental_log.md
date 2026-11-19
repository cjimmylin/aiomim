# Experimental log

Every number that may appear in the paper. Tables are copied from the comparison reports of each run; a sentence says
so where a number comes from elsewhere. Percentages are means over entries unless a table says "pooled".
Intervals are 95% bootstrap intervals over entries (10,000 resamples). "Points" means percentage points.

## 1. Setup

### 1.1 Task and data

- **Entries.** 100 OMIM phenotype entries drawn at random with a fixed seed, 20 from each of five bands of
  entry number that track when the entry was created (1xxxxx–5xxxxx, 600000–609999, 610000–615999, 616000–619999,
  620000 onward). Eligibility: 2–12 cited references, a causal gene in the gene map, at least five phenotype
  annotations, and at least one curator paragraph in scope. The sample is therefore stratified and selects
  well-annotated, molecularly characterised entries.
- **Papers.** 515 cited papers. Readable in full (open access through PubMed Central or Europe PMC):
  96 (19%); abstract only: 345;
  title only: 74. Supplementary material was not retrieved.
- **Input to every strategy.** The entry's number, title and alternative titles, and exactly the papers the entry
  cites. The causal gene is withheld.
- **Reference (gold standard), all from public resources.**
  - Curator-written per-paper text: OMIM's allelic-variant descriptions as deposited by OMIM in ClinVar. They come from
    OMIM's gene entries and are variant-centred prose about one or more cited papers. A paragraph is in scope for an
    entry when it is about a paper the entry cites. 476 paragraphs are in scope across the 100 entries.
    The narrative sections of the phenotype entries (clinical features, description) are not available publicly and
    are not compared.
  - Fixed fact lists: each in-scope paragraph was split once into atomic facts, without sight of any draft:
    6,652 facts in all.
  - Clinical synopsis: the Human Phenotype Ontology disease annotations for the entry (phenotype aspect):
    2,311 annotations, of which 1,835 are the HPO team's own curation from
    papers (they carry a PubMed reference) and 476 are taken from OMIM. (That this count equals
    the number of in-scope paragraphs is a coincidence.)
  - Causal gene: OMIM's gene map via MedGen and mim2gene. Inheritance: HPO and MedGen modes, compared as coarse classes
    (autosomal dominant, autosomal recessive, X-linked, mitochondrial, and others), requiring the sets to be equal.
  - Allelic variants: the entry's OMIM-submitted ClinVar records in scope: 427.
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

Three paradigms, a control, and three add-ons each tested against its parent.

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

93 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

### 2.1 Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 93 of the run's 100 entries qualify; left out: 118210, 300148, 609296, 617232, 620609, 621030, 621068. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 96 | 3: 118210 (1 paper), 617232 (1 paper), 621030 (1 paper) | 1: 620609 |
| Direct reading | 97 | 0 | 3: 609296, 620609, 621068 |
| Agentic curator | 98 | 0 | 2: 609296, 620609 |
| Memory only (control) | 100 | 0 | 0 |
| Recall, then verify | 100 | 0 | 0 |
| Case table first | 97 | 3: 300148 (1 paper), 617232 (2 papers), 621068 (1 paper) | 0 |

### 2.2 Scores (means over the compared entries)

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 96.1% | 96.4% | 50.8% | 94.2% (n=92) | 94.7% |
| … unsupported, before the repair round ↓ | 0.2% | 0.2% | 0.1% | 22.1% | 0.6% (n=92) | 0.3% |
| … contradicted, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 0.6% | 0.1% (n=92) | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 48.6% | 49.1% | 48.4% | 15.1% | 14.6% | 47.2% |
| … fully (no partial credit) ↑ | 42.0% | 42.4% | 41.9% | 10.2% | 10.1% | 40.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% | 0.4% | 0.5% | 0.3% | 0.5% |
| … facts split afresh for each draft (earlier scoring) ↑ | 51.5% | 52.1% | 51.3% | 20.4% | 18.2% | 49.3% |
| Clinical synopsis HPO F1, exact ↑ | 34.6% | 35.9% | 35.6% | 30.6% | 24.9% | 34.0% |
| … precision ↑ | 40.6% | 44.1% | 45.5% | 53.5% (n=92) | 53.6% (n=87) | 40.7% |
| … recall ↑ | 37.4% | 36.2% | 34.2% | 24.1% | 18.4% | 37.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.7% | 56.1% | 56.2% | 48.2% | 40.5% | 53.7% |
| OMIM allelic variants recovered ↑ | 65.9% | 66.5% | 65.9% | 15.2% | 11.6% | 64.3% |
| Generated variants that are OMIM variants (precision) ↑ | 76.9% (n=87) | 88.7% (n=82) | 87.9% (n=82) | 97.2% (n=30) | 100.0% (n=23) | 72.9% (n=88) |
| Causal gene F1 ↑ | 98.2% | 97.5% | 97.5% | 83.9% | 82.8% | 93.9% |
| … recall ↑ | 98.4% | 97.3% | 97.3% | 83.9% | 82.8% | 94.1% |
| Inheritance matches OMIM ↑ | 92.5% | 93.5% | 93.5% | 82.8% | 73.1% | 91.4% |
| OMIM references used ↑ | 94.6% | 94.4% | 93.3% | 33.6% | 65.2% | 94.6% |

Volume per entry:

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited per entry | 113.5 | 101.0 | 97.3 | 28.2 | 26.3 | 117.9 |
| Claims that could not be audited per entry | 1.2 | 0.6 | 0.3 | 0.0 | 0.0 | 0.4 |
| Clinical-synopsis HPO terms per entry | 19.2 | 15.4 | 13.8 | 6.2 | 4.4 | 21.0 |
| Allelic variants per entry | 3.9 | 3.2 | 3.2 | 0.4 | 0.3 | 4.1 |

### 2.3 Paired differences from direct reading

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | +0.4 (-0.4 to +1.3); 41/45/7 | +0.3 (-0.4 to +1.0); 53/33/7 | -45.3 (-50.3 to -40.3); 2/90/1 | -1.9 (-3.5 to -0.4); 34/53/5 (n=92) | -1.4 (-2.7 to -0.4); 34/56/3 |
| … same, before the repair round ↓ | +0.0 (-0.3 to +0.2); 10/12/71 | -0.1 (-0.4 to +0.1); 11/8/74 | +22.4 (+18.3 to +26.7); 1/79/13 | +0.4 (-0.0 to +0.9); 10/10/72 (n=92) | +0.1 (-0.2 to +0.4); 12/18/63 |
| OMIM per-paper facts conveyed (primary) ↑ | -0.5 (-1.5 to +0.5); 33/45/15 | -0.6 (-1.3 to +0.0); 31/42/20 | -34.0 (-39.3 to -28.7); 7/85/1 | -34.5 (-39.2 to -29.9); 2/89/2 | -1.9 (-3.1 to -0.8); 31/48/14 |
| OMIM per-paper facts contradicted ↓ | +0.0 (-0.1 to +0.2); 8/5/80 | +0.0 (-0.1 to +0.2); 3/5/85 | +0.1 (-0.2 to +0.5); 17/14/62 | -0.1 (-0.2 to +0.2); 16/7/70 | +0.1 (-0.1 to +0.3); 5/8/80 |
| Clinical synopsis HPO F1, exact ↑ | -1.3 (-3.3 to +0.6); 34/45/14 | -0.3 (-1.5 to +0.8); 38/32/23 | -5.3 (-9.2 to -1.5); 41/52/0 | -11.0 (-14.4 to -7.6); 25/63/5 | -2.0 (-3.9 to -0.1); 39/45/9 |
| Clinical synopsis HPO F1, hierarchical ↑ | -1.4 (-2.8 to -0.1); 36/44/13 | +0.0 (-1.0 to +1.1); 40/35/18 | -7.9 (-12.3 to -3.5); 38/54/1 | -15.7 (-19.9 to -11.5); 21/68/4 | -2.5 (-4.1 to -0.9); 34/51/8 |
| OMIM allelic variants recovered ↑ | -0.5 (-3.1 to +2.5); 4/8/81 | -0.6 (-2.2 to +0.7); 3/3/87 | -51.3 (-60.0 to -42.4); 3/69/21 | -54.9 (-62.8 to -47.0); 0/71/22 | -2.2 (-4.9 to +0.3); 6/11/76 |
| Causal gene F1 ↑ | +0.7 (+0.0 to +2.1); 1/0/92 | +0.0 (+0.0 to +0.0); 0/0/93 | -13.6 (-21.5 to -6.1); 2/15/76 | -14.7 (-22.6 to -7.5); 1/15/77 | -3.6 (-8.6 to +0.4); 1/4/88 |
| Inheritance matches OMIM ↑ | -1.1 (-5.4 to +2.1); 1/2/90 | +0.0 (-3.2 to +3.2); 1/1/91 | -10.8 (-19.4 to -2.1); 3/13/77 | -20.4 (-29.0 to -11.8); 1/20/72 | -2.1 (-8.6 to +4.3); 4/6/83 |

### 2.4 Sensitivity: all 100 entries, a missing draft counted as zero

All 100 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Evidence graph 1; Direct reading 3; Agentic curator 2.

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 93.2% | 94.5% (n=99) | 51.5% | 94.4% (n=98) | 94.5% (n=99) |
| … same, before the repair round ↓ | 0.3% (n=99) | 0.4% (n=97) | 0.2% (n=97) | 22.8% | 0.7% (n=98) | 0.7% (n=99) |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 48.4% | 48.5% | 48.9% | 14.8% | 14.2% | 47.1% |
| OMIM per-paper facts contradicted ↓ | 0.5% (n=99) | 0.4% (n=97) | 0.4% (n=98) | 0.5% | 0.3% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 33.8% | 34.6% | 34.8% | 29.4% | 23.9% | 33.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.1% | 54.6% | 55.3% | 46.7% | 39.4% | 52.9% |
| OMIM allelic variants recovered ↑ | 65.8% | 65.6% | 66.1% | 15.1% | 11.3% | 63.9% |
| Causal gene F1 ↑ | 97.3% | 94.7% | 95.7% | 83.0% | 82.0% | 92.3% |
| Inheritance matches OMIM ↑ | 91.0% | 91.0% | 91.0% | 82.0% | 73.0% | 90.0% |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | +2.4 (+0.1 to +5.6); median +0.0; 46/46/8; p 1.000 | +0.3 (-0.4 to +1.0); median +0.7; 56/34/9; p 0.026 (n=99) | -41.8 (-47.5 to -35.8); median -44.5; 4/94/2; p <0.001 | +0.2 (-2.5 to +3.7); median -1.2; 38/55/5; p 0.097 (n=98) | +0.3 (-2.2 to +3.6); median -1.0; 36/60/3; p 0.018 (n=99) |
| … same, before the repair round ↓ | -0.1 (-0.4 to +0.2); median +0.0; 11/12/74; p 1.000 (n=97) | -0.2 (-0.5 to +0.1); median +0.0; 12/9/76; p 0.664 (n=97) | +21.9 (+18.0 to +26.1); median +17.2; 1/82/14; p <0.001 (n=97) | +0.3 (-0.2 to +0.8); median +0.0; 11/10/75; p 1.000 (n=96) | +0.4 (-0.3 to +1.3); median +0.0; 13/19/65; p 0.377 (n=97) |
| OMIM per-paper facts conveyed (primary) ↑ | -0.2 (-3.0 to +3.1); median +0.0; 36/48/16; p 0.230 | +0.4 (-1.0 to +2.7); median +0.0; 34/43/23; p 0.362 | -33.7 (-38.9 to -28.5); median -34.4; 9/89/2; p <0.001 | -34.3 (-39.2 to -29.6); median -32.9; 4/93/3; p <0.001 | -1.4 (-4.2 to +1.4); median -0.7; 34/51/15; p 0.082 |
| OMIM per-paper facts contradicted ↓ | +0.0 (-0.1 to +0.2); median +0.0; 9/6/82; p 0.607 (n=97) | +0.0 (-0.1 to +0.1); median +0.0; 4/5/88; p 1.000 (n=97) | +0.1 (-0.3 to +0.4); median +0.0; 19/14/64; p 0.487 (n=97) | -0.1 (-0.3 to +0.1); median +0.0; 18/8/71; p 0.075 (n=97) | +0.1 (-0.1 to +0.3); median +0.0; 7/8/82; p 1.000 (n=97) |
| Clinical synopsis HPO F1, exact ↑ | -0.8 (-2.8 to +1.3); median +0.0; 36/48/16; p 0.230 | +0.2 (-1.2 to +1.8); median +0.0; 40/35/25; p 0.644 | -5.2 (-8.9 to -1.5); median -2.7; 44/55/1; p 0.315 | -10.6 (-14.1 to -7.3); median -8.6; 27/67/6; p <0.001 | -1.3 (-3.5 to +0.9); median +0.0; 42/48/10; p 0.598 |
| Clinical synopsis HPO F1, hierarchical ↑ | -0.5 (-2.4 to +1.8); median +0.0; 38/48/14; p 0.332 | +0.7 (-0.8 to +2.5); median +0.0; 44/36/20; p 0.434 | -7.9 (-12.3 to -3.6); median -5.0; 40/58/2; p 0.085 | -15.3 (-19.5 to -11.1); median -11.6; 23/72/5; p <0.001 | -1.7 (-4.1 to +1.0); median -0.7; 36/55/9; p 0.059 |
| OMIM allelic variants recovered ↑ | +0.2 (-4.0 to +4.9); median +0.0; 7/10/83; p 0.629 | +0.5 (-1.6 to +3.1); median +0.0; 4/3/93; p 1.000 | -50.5 (-58.7 to -41.9); median -50.0; 3/73/24; p <0.001 | -54.3 (-62.1 to -46.4); median -60.0; 0/75/25; p <0.001 | -1.7 (-6.0 to +2.7); median +0.0; 8/14/78; p 0.286 |
| Causal gene F1 ↑ | +2.7 (+0.0 to +6.0); median +0.0; 3/0/97; p 0.250 | +1.0 (+0.0 to +3.0); median +0.0; 1/0/99; p 1.000 | -11.7 (-19.7 to -4.0); median +0.0; 3/15/82; p 0.007 | -12.7 (-20.0 to -5.7); median +0.0; 2/15/83; p 0.002 | -2.3 (-8.0 to +3.0); median +0.0; 3/5/92; p 0.727 |
| Inheritance matches OMIM ↑ | +0.0 (-4.0 to +4.0); median +0.0; 2/2/96; p 1.000 | +0.0 (-3.0 to +3.0); median +0.0; 1/1/98; p 1.000 | -9.0 (-17.0 to -1.0); median +0.0; 4/13/83; p 0.049 | -18.0 (-27.0 to -10.0); median +0.0; 2/20/78; p <0.001 | -1.0 (-8.0 to +6.0); median +0.0; 6/7/87; p 1.000 |

### 2.5 Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited | 10,552 | 9,390 | 9,051 | 2,624 | 2,448 | 10,969 |
| … supported | 10,227 | 9,069 | 8,802 | 1,343 | 2,308 | 10,497 |
| … partly supported | 325 | 321 | 248 | 687 | 140 | 472 |
| … unsupported | 0 | 0 | 1 | 576 | 0 | 0 |
| … contradicted | 0 | 0 | 0 | 18 | 0 | 0 |
| Claims audited before repair | 10,526 | 9,371 | 9,056 | 2,624 | 2,448 | 10,945 |
| … unsupported before repair | 20 | 17 | 10 | 576 | 13 | 21 |
| … contradicted before repair | 8 | 0 | 2 | 18 | 4 | 4 |
| OMIM facts scored | 6,239 | 6,239 | 6,239 | 6,239 | 6,239 | 6,239 |
| … conveyed | 2,562 | 2,620 | 2,593 | 502 | 502 | 2,490 |
| … partly conveyed | 811 | 820 | 796 | 578 | 553 | 769 |
| … missing | 2,840 | 2,771 | 2,820 | 5,133 | 5,167 | 2,948 |
| … contradicted | 26 | 28 | 30 | 26 | 17 | 32 |

### 2.6 Allelic variants: precision

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Variants generated | 365 | 295 | 300 | 40 | 28 | 381 |
| … matching an OMIM variant of the entry | 253 | 258 | 259 | 38 | 28 | 250 |
| … listed by OMIM only from a paper outside the entry's references | 1 | 1 | 1 | 1 | 0 | 1 |
| … not in OMIM | 111 | 36 | 40 | 1 | 0 | 130 |
| Pooled precision (entries where OMIM lists variants) | 69.3% | 87.5% | 86.3% | 95.0% | 100.0% | 65.6% |

### 2.7 Inheritance errors by kind

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Entries with an OMIM mode of inheritance | 93 | 93 | 93 | 93 | 93 | 93 |
| … matched | 86 | 87 | 87 | 77 | 68 | 85 |
| … none stated | 3 | 2 | 3 | 13 | 22 | 2 |
| … a mode missing | 0 | 0 | 0 | 0 | 0 | 1 |
| … an extra mode | 3 | 4 | 3 | 1 | 1 | 4 |
| … a different mode | 1 | 0 | 0 | 2 | 2 | 1 |

### 2.8 OMIM facts conveyed by how the paper was readable (pooled over facts)

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| fulltext | 78.8% (1,639) | 77.6% (1,639) | 76.7% (1,639) | 11.5% (1,639) | 13.3% (1,639) | 71.7% (1,639) |
| abstract | 38.1% (4,221) | 40.1% (4,221) | 39.6% (4,221) | 13.3% (4,221) | 12.9% (4,221) | 38.7% (4,221) |
| title | 17.5% (379) | 17.5% (379) | 16.9% (379) | 11.1% (379) | 4.0% (379) | 17.3% (379) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies.

| Paper readable as | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| fulltext | +1.2 (-1.8 to +3.8); n=40 | -0.9 (-2.5 to +0.4); n=40 | -66.1 (-73.2 to -58.6); n=40 | -64.3 (-72.4 to -56.5); n=40 | -5.9 (-9.0 to -2.9); n=40 |
| abstract | -1.9 (-3.6 to -0.6); n=85 | -0.5 (-1.2 to +0.1); n=85 | -26.8 (-31.4 to -22.2); n=85 | -27.2 (-31.2 to -22.9); n=85 | -1.4 (-2.8 to -0.1); n=85 |
| title | +0.0 (-2.1 to +2.0); n=21 | -0.7 (-1.8 to +0.3); n=21 | -6.5 (-13.7 to +0.9); n=21 | -13.6 (-18.2 to -9.4); n=21 | -0.3 (-1.7 to +1.1); n=21 |

### 2.9 Paired differences from direct reading within strata of entries by access

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| no full text (abstracts only) | 46 | -0.2 (-1.1 to +0.8); n=46 | -0.1 (-1.1 to +0.7); n=46 | -18.1 (-23.9 to -12.3); n=46 | -19.1 (-23.2 to -15.2); n=46 | +0.6 (-0.3 to +1.6); n=46 |
| under half full text | 25 | -0.7 (-2.6 to +1.3); n=25 | -0.4 (-1.6 to +0.8); n=25 | -41.7 (-49.3 to -34.4); n=25 | -42.5 (-49.6 to -35.5); n=25 | -4.0 (-6.3 to -2.0); n=25 |
| half or more full text | 21 | -1.8 (-4.4 to +0.7); n=21 | -2.0 (-3.4 to -0.7); n=21 | -59.6 (-68.1 to -51.0); n=21 | -58.7 (-66.6 to -51.0); n=21 | -6.1 (-8.3 to -3.6); n=21 |
| all full text | 1 | +17.8 †; n=1 | +0.0 †; n=1 | -32.2 †; n=1 | -33.9 †; n=1 | +21.4 †; n=1 |

### OMIM allelic variants recovered

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| no full text (abstracts only) | 46 | +0.4 (-4.6 to +6.4); n=46 | -0.4 (-3.0 to +1.6); n=46 | -32.6 (-45.4 to -20.1); n=46 | -38.7 (-49.5 to -28.1); n=46 | -0.4 (-4.1 to +3.3); n=46 |
| under half full text | 25 | -1.9 (-4.2 to +0.0); n=25 | -0.1 (-2.0 to +1.7); n=25 | -64.2 (-76.3 to -51.1); n=25 | -66.0 (-78.1 to -52.8); n=25 | -5.5 (-12.7 to +0.0); n=25 |
| half or more full text | 21 | -1.0 (-2.6 to +0.0); n=21 | -1.6 (-4.8 to +0.0); n=21 | -79.5 (-91.7 to -65.4); n=21 | -79.9 (-92.1 to -65.6); n=21 | -2.2 (-5.2 to +0.0); n=21 |
| all full text | 1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 |

### 2.10 OMIM facts conveyed by creation era within each access level (direct reading and the memory-only control)

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 88.6% (22 facts, 1 entry) | 79.8% (225 facts, 10 entries) | 74.1% (526 facts, 11 entries) | 71.2% (450 facts, 10 entries) | 87.4% (416 facts, 8 entries) |
| abstract | 33.0% (1,022 facts, 18 entries) | 49.8% (656 facts, 19 entries) | 42.0% (1,055 facts, 18 entries) | 40.2% (859 facts, 15 entries) | 37.9% (629 facts, 15 entries) |
| title | 23.2% (41 facts, 3 entries) | 14.9% (67 facts, 4 entries) | 23.7% (57 facts, 4 entries) | 19.9% (83 facts, 5 entries) | 13.0% (131 facts, 5 entries) |

### Memory only (control)

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 0.0% (22 facts, 1 entry) | 14.2% (225 facts, 10 entries) | 14.6% (526 facts, 11 entries) | 11.3% (450 facts, 10 entries) | 7.0% (416 facts, 8 entries) |
| abstract | 12.8% (1,022 facts, 18 entries) | 22.9% (656 facts, 19 entries) | 14.0% (1,055 facts, 18 entries) | 10.8% (859 facts, 15 entries) | 6.0% (629 facts, 15 entries) |
| title | 9.8% (41 facts, 3 entries) | 15.7% (67 facts, 4 entries) | 14.0% (57 facts, 4 entries) | 12.7% (83 facts, 5 entries) | 6.9% (131 facts, 5 entries) |

### 2.11 Memory-only control and direct reading by creation era (entry means)

| Creation era | Entries | Facts conveyed: memory / direct | Claims judged supported: memory | Gene F1: memory / direct | Inheritance match: memory / direct | Synopsis exact F1: memory / direct |
|---|---|---|---|---|---|---|
| classic (1xxxxx-5xxxxx) | 18 | 14.5% / 34.9% | 40.4% | 88.9% / 87.0% | 88.9% / 88.9% | 38.2% / 33.4% |
| 600000-609999 | 19 | 24.1% / 53.9% | 52.4% | 94.7% / 100.0% | 94.7% / 89.5% | 38.4% / 40.0% |
| 610000-615999 | 20 | 17.5% / 51.2% | 53.5% | 100.0% / 100.0% | 100.0% / 95.0% | 31.6% / 36.5% |
| 616000-619999 | 19 | 12.6% / 51.4% | 59.0% | 89.5% / 100.0% | 84.2% / 94.7% | 27.5% / 35.7% |
| 620000 onward | 17 | 5.7% / 53.5% | 47.8% | 41.2% / 100.0% | 41.2% / 100.0% | 16.3% / 33.5% |

### 2.12 Cost per entry

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Generation: model calls | 7.1 | 1.8 | 1.8 | 1.6 | 9.2 | 7.1 |
| Generation: list price | $0.56 | $0.26 | $0.28 | $0.07 | $0.70 | $0.61 |
| Generation: input / output tokens | 53,475 / 15,321 | 20,241 / 6,185 | 57,445 / 8,735 | 6,187 / 2,286 | 56,342 / 18,505 | 62,392 / 17,152 |
| Generation: model time (s) | 124 | 50 | 73 | 24 | 174 | 142 |
| Audit and repair: list price | $0.78 | $0.72 | $0.68 | $0.50 | $0.30 | $0.77 |
| Scoring against OMIM: list price | $0.39 | $0.20 | $0.19 | $0.15 | $0.14 | $0.39 |
| Everything: list price | $1.72 | $1.18 | $1.15 | $0.72 | $1.13 | $1.78 |

### 2.13 Other facts about the drafts (computed from the per-entry files)

- Evidence graph: every extracted finding carries a quote, and findings whose quote is not found in the paper are
  discarded before the graph is built; none was discarded in this run.
- Agentic curator: it reports which papers it opened (self-reported; tool calls are not logged). In the 98 entries it
  wrote it reported opening every paper, and all 2,600 quotes it gave were found verbatim in the papers.
- Recall, then verify: the memory drafts it starts from are the memory-only control's drafts.

## 3. Where the missed facts went (direct reading, fixed fact lists)

Each fact direct reading did not fully convey was checked once against the text available for its paper: stated (with a
quote that was verified in the text), partly stated, or not stated. The check is a model judgement. Counts and shares in
this section are pooled over facts.

97 entries, 466 OMIM paragraphs, 437 judge calls (0 failed). Left out, no draft (the writer was stopped): 3 entries (609296, 620609, 621068).

| Paper read as | OMIM facts | Conveyed | Not fully conveyed | … in text | … partly in text | … not in text | Unjudged | In text, share of missed |
|---|---|---|---|---|---|---|---|---|
| Full text | 1,837 | 1,329 | 501 | 245 | 134 | 122 | 0 | 49% |
| Abstract only | 4,282 | 1,420 | 2,837 | 46 | 632 | 2,159 | 0 | 2% |
| Title only | 379 | 38 | 341 | 0 | 53 | 288 | 0 | 0% |
| All papers | 6,498 | 2,787 | 3,679 | 291 | 819 | 2,569 | 0 | 8% |

By how much of the fact the draft conveyed (absent: not at all; partial: less precisely):

| Paper read as | Draft | Missed | … in text | … partly | … not in text |
|---|---|---|---|---|---|
| Full text | absent | 287 | 123 | 47 | 117 |
| Full text | partial | 214 | 122 | 87 | 5 |
| Abstract only | absent | 2,254 | 19 | 158 | 2,077 |
| Abstract only | partial | 583 | 27 | 474 | 82 |
| Title only | absent | 284 | 0 | 5 | 279 |
| Title only | partial | 57 | 0 | 48 | 9 |
| All papers | absent | 2,825 | 142 | 210 | 2,473 |
| All papers | partial | 854 | 149 | 609 | 96 |

Of all OMIM facts: 43% conveyed, 4% omitted though stated in the available text, 13% omitted and partly stated, 40% not in the available text; the remainder were contradicted. (Facts the draft conveyed partly are counted with the missed ones.)

Facts contradicted by the draft (not in the columns above): 7 for full-text papers, 25 for abstract-only papers, 0 for title-only papers, 32 in all.

### 3.1 Where the conveyed facts came from: the supplied text or elsewhere

For every frozen OMIM fact the draft conveyed in full (present) or in part (partial), the judge checked whether the text the writer had for the paragraph's paper(s) states it (the stored availability judgement of `gaps --frozen`: same prompt, same per-paper cut, quotes verified in the text). A fact that text did not state, or stated only partly, was checked once more against the text of the entry's other supplied papers (cut the same way), since a later paper may describe an earlier one. These are model judgements, not a curator's. A conveyed fact stated in no supplied text was not read there: it was recalled from the model's memory, inferred from what the text does state (for example an inheritance mode from zygosity), or the judgement is wrong; this analysis does not separate the three.

97 entries, 466 OMIM paragraphs. Judge calls: 0 for the paper's own text (stored judgements were reused), 385 for the other papers (0 failed); safety stops: 0. Left out, no draft (the writer was stopped): 3 entries (609296, 620609, 621068).

**Headline.** Of the facts conveyed in full from papers readable only as an abstract or title, 24 of 1,458 (1.7%) are stated in no supplied text, and a further 241 only partly. Counting facts conveyed in part as well: 90 of 2,098 (4.3%) in no supplied text.

| Paper read as | Conveyed | Facts | Stated in its paper's text | Partly stated in its paper's text | Stated only in another supplied paper | Partly stated only in another supplied paper | In no supplied text | Unjudged |
|---|---|---|---|---|---|---|---|---|
| Full text | in full | 1,329 | 1,174 (88.3%) | 122 (9.2%) | 22 (1.7%) | 4 (0.3%) | 7 (0.5%) | 0 |
| Full text | in part | 214 | 122 (57.0%) | 86 (40.2%) | 1 (0.5%) | 1 (0.5%) | 4 (1.9%) | 0 |
| Full text | in full or in part | 1,543 | 1,296 (84.0%) | 208 (13.5%) | 23 (1.5%) | 5 (0.3%) | 11 (0.7%) | 0 |
| Abstract only | in full | 1,420 | 1,061 (74.7%) | 222 (15.6%) | 102 (7.2%) | 11 (0.8%) | 24 (1.7%) | 0 |
| Abstract only | in part | 583 | 27 (4.6%) | 462 (79.2%) | 15 (2.6%) | 21 (3.6%) | 58 (10.0%) | 0 |
| Abstract only | in full or in part | 2,003 | 1,088 (54.3%) | 684 (34.2%) | 117 (5.8%) | 32 (1.6%) | 82 (4.1%) | 0 |
| Title only | in full | 38 | 27 (71.0%) | 8 (21.1%) | 3 (7.9%) | 0 (0.0%) | 0 (0.0%) | 0 |
| Title only | in part | 57 | 0 (0.0%) | 47 (82.5%) | 1 (1.8%) | 1 (1.8%) | 8 (14.0%) | 0 |
| Title only | in full or in part | 95 | 27 (28.4%) | 55 (57.9%) | 4 (4.2%) | 1 (1.1%) | 8 (8.4%) | 0 |
| All papers | in full | 2,787 | 2,262 (81.2%) | 352 (12.6%) | 127 (4.6%) | 15 (0.5%) | 31 (1.1%) | 0 |
| All papers | in part | 854 | 149 (17.4%) | 595 (69.7%) | 17 (2.0%) | 23 (2.7%) | 70 (8.2%) | 0 |
| All papers | in full or in part | 3,641 | 2,411 (66.2%) | 947 (26.0%) | 144 (4.0%) | 38 (1.0%) | 101 (2.8%) | 0 |

Shares are of the facts judged in that row. The second check, by the paper's own-text verdict (facts conveyed in full or in part):

| Paper read as | Own text | Facts | Another paper states it | … partly | … no | No other paper supplied | Unjudged |
|---|---|---|---|---|---|---|---|
| Full text | partly stated | 223 | 15 | 37 | 171 | 0 | 0 |
| Full text | not stated | 24 | 8 | 5 | 11 | 0 | 0 |
| Abstract only | partly stated | 728 | 44 | 119 | 546 | 19 | 0 |
| Abstract only | not stated | 187 | 73 | 32 | 81 | 1 | 0 |
| Title only | partly stated | 57 | 2 | 5 | 50 | 0 | 0 |
| Title only | not stated | 11 | 2 | 1 | 8 | 0 | 0 |
| All papers | partly stated | 1,008 | 61 | 161 | 767 | 19 | 0 |
| All papers | not stated | 222 | 83 | 38 | 100 | 1 | 0 |

## 4. How much the measurement moves

### 4.1 Judge variation: the same drafts and the same fact lists, judged three times

| Strategy | Entries | Mean OMIM facts conveyed in three judgings (%) | Mean within-entry SD across judgings (points) |
|---|---|---|---|
| Direct reading | 30 | 45.6 / 45.7 / 45.3 | 0.9 |
| Evidence graph | 30 | 46.3 / 46.2 / 46.6 | 0.8 |

- Evidence graph minus direct reading in the three judgings: +0.7 / +0.5 / +1.3 points.
- Per-fact agreement between two judgings of the same draft against the same fact list: 3498 of 3654 statuses (95.7%).

### 4.2 Run-to-run variation: generation, audit and scoring repeated

30 entries, three full replicates of generation, audit and scoring; OMIM facts conveyed scored against the same fixed fact lists in every replicate.

| Strategy | 30-entry mean in replicates 1 / 2 / 3 (%) | Within-entry SD (points) | Between-entry SD (points) | Share of variance within entries |
|---|---|---|---|---|
| Direct reading | 45.6 / 44.7 / 45.9 | 2.5 | 21.0 | 1% |
| Evidence graph | 46.3 / 46.6 / 46.4 | 4.0 | 22.1 | 3% |

- Evidence graph minus direct reading in replicates 1 / 2 / 3: +0.7 / +1.9 / +0.5 points.
- Within-entry SD of that paired difference: 5.0 points. Replicate noise alone gives a 95% half-width of 1.0 points on a difference between two strategies over 93 entries, and 1.8 points over 30 entries.

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

38 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

**Means, 38 entries completed in full by all seven strategies.**

| Measure | Direct reading | Evidence graph | Evidence graph, matched | Evidence graph plus text | Case table | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| OMIM facts conveyed (%) | 58.4 | 59.4 | 60.2 | 60.2 | 56.1 | 58.3 | 59.1 |
| … on papers readable in full (%) | 80.4 (n=25) | 82.7 (n=25) | 83.7 (n=25) | 83.0 (n=25) | 75.4 (n=25) | 78.8 (n=25) | 79.9 (n=25) |
| Claims judged supported (%) | 97.9 | 97.1 | 96.8 | 98.3 | 96.0 | 97.0 | 98.1 |
| Synopsis precision (%) | 45.2 | 40.5 | 39.4 | 42.6 | 40.6 | 41.2 | 42.0 |
| Synopsis recall (%) | 43.8 | 44.5 | 44.9 | 44.1 | 46.3 | 44.1 | 44.4 |
| Synopsis exact F1 (%) | 40.1 | 37.6 | 37.8 | 39.5 | 37.3 | 38.3 | 39.4 |
| Synopsis terms per entry | 19.0 | 25.2 | 24.0 | 21.2 | 29.9 | 22.5 | 20.3 |
| Inheritance matches (%) | 97.4 | 94.7 | 94.7 | 94.7 | 94.7 | 97.4 | 97.4 |
| Variants recovered (%) | 77.3 | 76.8 | 77.0 | 77.4 | 74.4 | 73.7 | 72.7 |

**Each step against the one before it** (difference, 95% bootstrap interval; entries better/worse). Percentage points except synopsis terms.

| Measure | Graph matched − graph | Graph plus text − graph matched | Table matched − table | Table plus text − table matched |
|---|---|---|---|---|
| OMIM facts conveyed | +0.8 (-0.5 to +2.1); 18/12 | +0.0 (-0.8 to +0.9); 16/16 | +2.1 (+1.1 to +3.2); 25/8 | +0.8 (-0.8 to +2.6); 21/13 |
| … on papers readable in full | +1.0 (-1.0 to +3.0); 13/8 | -0.7 (-1.9 to +0.6); 8/15 | +3.3 (+1.6 to +5.1); 17/4 | +1.1 (-1.6 to +3.8); 13/9 |
| Claims judged supported | -0.3 (-0.9 to +0.4); 15/22 | +1.5 (+0.9 to +2.1); 31/6 | +0.9 (-0.3 to +2.4); 22/15 | +1.2 (+0.3 to +2.2); 23/12 |
| Synopsis precision | -1.1 (-3.7 to +1.5); 12/19 | +3.2 (+1.2 to +5.4); 21/7 | +0.6 (-3.9 to +4.8); 17/11 | +0.8 (-1.9 to +3.2); 17/10 |
| Synopsis recall | +0.4 (-2.8 to +3.6); 10/14 | -0.8 (-3.2 to +1.6); 6/10 | -2.3 (-5.6 to +0.8); 9/10 | +0.3 (-2.1 to +3.2); 7/10 |
| Synopsis exact F1 | +0.2 (-2.2 to +2.8); 15/18 | +1.7 (-0.1 to +3.6); 17/11 | +1.0 (-2.0 to +3.5); 18/11 | +1.1 (-0.8 to +3.1); 15/12 |
| Synopsis terms per entry | -1.2 (-3.6 to +0.8); 16/14 | -2.8 (-5.4 to -0.5); 9/20 | -7.4 (-13.7 to -2.2); 10/18 | -2.2 (-3.7 to -0.7); 8/17 |
| Inheritance matches | +0.0 (+0.0 to +0.0); 0/0 | +0.0 (+0.0 to +0.0); 0/0 | +2.6 (+0.0 to +7.9); 1/0 | +0.0 (+0.0 to +0.0); 0/0 |
| Variants recovered | +0.2 (+0.0 to +0.7); 1/0 | +0.4 (+0.0 to +1.1); 1/0 | -0.7 (-3.9 to +2.0); 1/1 | -1.0 (-6.3 to +3.6); 4/3 |

**Each strategy against direct reading** (same format).

| Measure | Evidence graph | Graph matched | Graph plus text | Case table | Table matched | Table plus text |
|---|---|---|---|---|---|---|
| OMIM facts conveyed | +1.0 (-0.9 to +2.8); 19/15 | +1.8 (+0.4 to +3.3); 24/10 | +1.8 (+0.5 to +3.2); 24/10 | -2.3 (-4.5 to +0.1); 13/24 | -0.2 (-2.4 to +2.1); 16/20 | +0.6 (-1.1 to +2.6); 18/15 |
| … on papers readable in full | +2.3 (-0.2 to +5.0); 13/11 | +3.3 (+1.2 to +5.6); 17/6 | +2.7 (+0.5 to +5.0); 16/5 | -4.9 (-8.0 to -1.4); 6/19 | -1.6 (-4.8 to +1.9); 7/16 | -0.5 (-3.7 to +2.8); 11/9 |
| Claims judged supported | -0.8 (-1.4 to -0.1); 8/25 | -1.0 (-1.8 to -0.2); 12/24 | +0.4 (-0.3 to +1.2); 20/11 | -1.8 (-3.3 to -0.6); 11/25 | -0.9 (-2.1 to +0.2); 14/22 | +0.3 (-0.4 to +1.1); 21/14 |
| Synopsis precision | -4.6 (-8.3 to -1.1); 9/24 | -5.7 (-9.2 to -2.1); 7/29 | -2.6 (-5.5 to +0.4); 12/22 | -4.5 (-8.5 to -0.5); 9/26 | -3.9 (-8.1 to -0.1); 13/24 | -3.1 (-7.2 to +0.3); 14/19 |
| Synopsis recall | +0.8 (-3.9 to +5.0); 15/8 | +1.1 (-2.3 to +4.5); 15/10 | +0.3 (-3.0 to +3.1); 12/9 | +2.6 (-2.4 to +7.7); 17/12 | +0.3 (-3.9 to +4.4); 15/11 | +0.6 (-2.0 to +3.3); 11/9 |
| Synopsis exact F1 | -2.5 (-5.1 to +0.1); 10/24 | -2.3 (-4.5 to -0.1); 11/24 | -0.6 (-2.6 to +1.2); 14/20 | -2.8 (-5.6 to +0.2); 15/21 | -1.8 (-4.8 to +1.0); 16/21 | -0.7 (-3.2 to +1.6); 17/16 |
| Synopsis terms per entry | +6.2 (+3.1 to +9.8); 25/7 | +5.0 (+2.3 to +8.1); 27/8 | +2.2 (+0.7 to +3.8); 21/12 | +10.8 (+4.6 to +18.1); 22/10 | +3.5 (+1.5 to +5.8); 24/10 | +1.3 (-0.0 to +2.6); 19/11 |
| Inheritance matches | -2.6 (-7.9 to +0.0); 0/1 | -2.6 (-7.9 to +0.0); 0/1 | -2.6 (-7.9 to +0.0); 0/1 | -2.6 (-7.9 to +0.0); 0/1 | +0.0 (+0.0 to +0.0); 0/0 | +0.0 (+0.0 to +0.0); 0/0 |
| Variants recovered | -0.6 (-1.5 to +0.0); 0/2 | -0.3 (-1.0 to +0.0); 0/1 | +0.0 (-1.0 to +1.1); 1/1 | -3.0 (-7.2 to -0.2); 0/4 | -3.6 (-8.2 to -0.2); 0/4 | -4.7 (-10.9 to -0.3); 1/4 |

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
No repair round was applied to the two new drafts; the full-text draft is the main run's and went through repair.
Coverage is scored against the fixed fact lists (the main measure, first table below); the earlier per-draft scoring is
kept beside it. Each coverage level below is labelled as pooled over facts or as a mean over entries; the paired
differences are means over entries. Our full texts exclude supplementary material, so "unsupported by the full text" is
an upper bound on error.

OMIM facts conveyed on the fixed fact lists: abstract only 36.1% mean over entries (n = 46), 31.2% pooled over facts (2,120 facts); abstract plus second-hand 40.9% mean over entries (n = 46), 36.7% pooled over facts (2,120 facts); full text (main run's direct draft) 79.9% mean over entries (n = 46), 77.4% pooled over facts (2,120 facts); full text before the repair round 79.8% mean over entries (n = 46), 77.3% pooled over facts (2,120 facts).

Source run `omim100`; 49 entries. In each, the papers read in full were hidden and the entry was written by direct reading from their abstracts, with and without second-hand passages from later open-access papers. Counts, not just rates.

#### Retrieval for the hidden papers

- Hidden papers: 91; with citing papers: 91; with open-access citing papers: 89; with at least one passage: 89.
- Passages for the hidden papers: 523 (430,391 characters).
- All papers supplemented (hidden and abstract-only): 243, of which 234 got passages; 1278 passages, 1,046,654 characters; retrieval 0.1 s in all.

#### OMIM-fact coverage on the frozen fact lists (main measure)

Scoring: **frozen fact lists**. Each gold paragraph about a hidden paper was split into facts once, without sight of any draft (the same lists as the main runs), and the two new drafts were marked against them; the full-text row is the source run's existing frozen scoring of its direct draft (`eval.direct.json`, `gold_text_frozen`) restricted to the same paragraphs. 46 entries with a full-text draft in the source run, 136 paragraphs scored under all three conditions (the same entries, paragraphs and fact lists in every row). Coverage = (present + half of partial) / facts judged, pooled over facts; the last column is the mean of per-entry coverage over the same entries, the unit of the paired differences below.

| Condition | Entries | Paragraphs | Facts judged | Present | Partial | Absent | Contradicted | Coverage (frozen), pooled over facts | Coverage (old scoring), pooled over facts | Coverage (frozen), mean over entries |
|---|---|---|---|---|---|---|---|---|---|---|
| Abstract only | 46 | 136 | 2120 | 495 | 331 | 1290 | 4 | 31.2% | 35.5% | 36.1% |
| Abstract + second-hand | 46 | 136 | 2120 | 629 | 297 | 1184 | 10 | 36.7% | 41.4% | 40.9% |
| Full text (source run's direct draft) | 46 | 136 | 2120 | 1513 | 254 | 343 | 10 | 77.4% | 78.6% | 79.9% |

Paired differences, mean over entries (percentage points of per-entry coverage), bootstrap 95% interval over entries (10,000 resamples, seed 20261119); the old-scoring column uses the same entries.

| Difference | Entries | Frozen: mean (95% CI) | better / worse / tied | Old scoring: mean (95% CI) | better / worse / tied |
|---|---|---|---|---|---|
| Abstract + second-hand minus abstract only | 46 | +4.9 (+2.8 to +7.1) | 33 / 9 / 4 | +5.3 (+3.6 to +7.2) | 36 / 7 / 3 |
| Full text minus abstract only | 46 | +43.9 (+38.5 to +49.3) | 45 / 0 / 1 | +41.7 (+36.7 to +46.6) | 46 / 0 / 0 |

#### Repair parity: what the repair round changed in the full-text drafts

The full-text row is the source run's direct-reading draft, which went through the audit's repair round; the two abstract drafts did not. Over the 46 entries compared, the audit before repair flagged 13 of 6,609 audited claims (13 unsupported, 0 contradicted) in 11 paragraphs of 8 entries; the repair revised 11 paragraphs and deleted 0. 11 of the 11 revised paragraphs were located in the final drafts, and 11 of them cite a hidden paper; 13 of the flagged claims lie in paragraphs citing a hidden paper. After repair the drafts hold 6,637 audited claims, 5,328 of them in paragraphs citing a hidden paper.

The draft before repair is not kept by the pipeline; it was rebuilt from the cached writer and audit replies (no generation call), and carrying the rebuilt draft through the cached repair round reproduces the stored final draft exactly. It was scored on the same fixed fact lists with the same judge procedure as `rescore`; only the 27 gold paragraphs whose cited draft text the repair changed needed new judge calls, the rest are the original judgements read from the cache.

Full text before repair, 46 entries, 136 paragraphs, 2,120 facts: coverage 77.3% pooled over facts (1511 present, 255 partial, 344 absent, 10 contradicted); 79.8% mean over entries.

| Difference (mean over entries) | Entries | Mean (95% CI) | better / worse / tied |
|---|---|---|---|
| Full text before repair minus abstract only | 46 | +43.7 (+38.3 to +49.1) | 45 / 0 / 1 |
| Full text after repair minus before repair | 46 | +0.2 (-0.1 to +0.4) | 6 / 2 / 38 |

#### OMIM-fact coverage of the gold paragraphs about the hidden papers (old scoring: facts split afresh for each draft)

Pooled over the 46 entries that have a full-text draft in the source run, the same entries for all three conditions; left out: 3 entries whose full-text direct draft was not written (the writer's reply was stopped), so they have no full-text coverage to compare: 609296, 620609, 621068.

| Condition | Paragraphs | Facts | Present | Partial | Absent | Contradicted | Coverage, pooled over facts |
|---|---|---|---|---|---|---|---|
| Abstract only | 136 | 1783 | 452 | 362 | 966 | 3 | 35.5% |
| Abstract + second-hand | 136 | 1802 | 565 | 362 | 864 | 11 | 41.4% |
| Full text (source run's direct draft) | 136 | 1767 | 1268 | 243 | 246 | 10 | 78.6% |

Over all 49 entries the two new conditions convey 35.3% (abstract only, 1876 facts) and 41.1% (abstract + second-hand, 1889 facts), pooled over facts.

Facts are split from the gold paragraph separately for each condition, so the fact counts differ slightly. The full-text draft went through the audit's repair round; the two new drafts did not.

#### Claims about the hidden papers in the second-hand draft

2308 claims (2208 after collapsing the same statement made in two paragraphs), each audited against what the writer saw (abstract plus passages) and against the paper's full text.

**Caveat: our full texts exclude supplementary material.** A detail a paper gives only in a supplementary table counts as unsupported here, so "unsupported by the primary text" is an upper bound on the error of second-hand claims; "contradicted" is not affected in the same way.

| Evidence (audit of what the writer saw) | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| none | 340 (338) | 191 (191) | 59 (59) | 55 (55) | 8 (8) | 27 (25) |
| own | 1856 (1764) | 1688 (1598) | 136 (134) | 8 (8) | 6 (6) | 18 (18) |
| secondhand | 112 (106) | 74 (68) | 24 (24) | 11 (11) | 3 (3) | 0 (0) |

`own`: the auditor's evidence quote is in the paper's title or abstract; `secondhand`: in a later paper's passage; `unlocated`: a quote found in neither (already downgraded); `none`: no quote (claim judged unsupported or contradicted against what the writer saw). Figures in brackets count a statement repeated in two paragraphs once.

##### Claims resting on second-hand text, by passage

| Passage kind | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| paragraph | 91 (86) | 68 (63) | 18 (18) | 2 (2) | 3 (3) | 0 (0) |
| table | 21 (20) | 6 (5) | 6 (6) | 9 (9) | 0 (0) | 0 (0) |

| Other references cited by the passage (few = at most 2) | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| few | 87 (83) | 55 (51) | 20 (20) | 11 (11) | 1 (1) | 0 (0) |
| many | 25 (23) | 19 (17) | 4 (4) | 0 (0) | 2 (2) | 0 (0) |

### 6.3 In use on the 100 entries

96 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

In this run 361 of the 401 papers not readable in full received
passages (1,808 passages). 240 of 10,597 audited claims
rested only on second-hand text, in 92 paragraphs. Such claims are labelled as not
checked against the cited paper and are not counted as supported; they leave the denominator of claims judged
supported. The writer did not name a later paper in any entry.

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 94.4% |
| … unsupported, before the repair round ↓ | 0.4% | 3.9% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 50.4% | 52.2% |
| … fully (no partial credit) ↑ | 43.7% | 45.9% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.7% |
| … facts split afresh for each draft (earlier scoring) ↑ | 53.2% | 54.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.9% | 37.0% |
| … precision ↑ | 43.7% | 43.2% |
| … recall ↑ | 36.2% | 37.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.7% | 58.9% |
| OMIM allelic variants recovered ↑ | 68.2% | 73.2% |
| Generated variants that are OMIM variants (precision) ↑ | 88.4% (n=85) | 86.8% (n=89) |
| Causal gene F1 ↑ | 97.6% | 97.6% |
| … recall ↑ | 97.4% | 97.4% |
| Inheritance matches OMIM ↑ | 93.8% | 95.8% |
| OMIM references used ↑ | 94.6% | 94.5% |

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Second-hand evidence |
|---|---|
| Claims supported by cited paper ↑ | -1.8 (-2.9 to -0.8); 31/60/5 |
| … same, before the repair round ↓ | +3.6 (+2.2 to +5.1); 8/51/37 |
| OMIM per-paper facts conveyed (primary) ↑ | +1.8 (+1.0 to +2.8); 49/31/16 |
| OMIM per-paper facts contradicted ↓ | +0.2 (+0.0 to +0.5); 4/11/81 |
| Clinical synopsis HPO F1, exact ↑ | +1.1 (-0.7 to +3.0); 42/36/18 |
| Clinical synopsis HPO F1, hierarchical ↑ | +2.2 (+0.4 to +4.3); 50/36/10 |
| OMIM allelic variants recovered ↑ | +5.0 (+1.3 to +9.2); 13/2/81 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/96 |
| Inheritance matches OMIM ↑ | +2.1 (+0.0 to +5.2); 2/0/94 |

Facts conveyed by how the paper was readable (pooled):

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Direct reading | Second-hand evidence |
|---|---|---|
| fulltext | 78.2% (1,837) | 78.0% (1,837) |
| abstract | 40.4% (4,205) | 41.7% (4,205) |
| title | 17.5% (379) | 26.7% (379) |

## 7. Add-on: reconciled case database

Over the 100 entries, reconciliation proposed 57 merges of patient or family records and
accepted 40 (17 rejected by the verifier), in 27
entries; it merged 11 variant names and found 57 conflicts between
papers. Counted individuals went from 2,580 to 2,413 (net; counts
rose in a few entries where a re-report gave a larger family size) and families from 1,126 to
1,092. A planted test on six entries merged 10 of 10 copied reports with their originals and
merged no unrelated records; this easy case shows only that a stated re-report is caught. The accepted merges were not
checked by a person. Cost: one or two extra calls per entry.

97 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Reconciled case database |
|---|---|
| Claims supported by cited paper ↑ | +0.0 (-0.4 to +0.4); 15/13/69 |
| … same, before the repair round ↓ | +0.1 (-0.0 to +0.3); 4/12/81 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.1 (-0.1 to +0.4); 12/10/75 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.0 to +0.2); 2/4/91 |
| Clinical synopsis HPO F1, exact ↑ | -0.1 (-0.4 to +0.3); 6/5/86 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.0 (-0.0 to +0.1); 2/1/94 |
| OMIM allelic variants recovered ↑ | +0.1 (+0.0 to +0.3); 1/0/96 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/97 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/97 |

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

68 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 96.1% |
| … unsupported, before the repair round ↓ | 0.2% | 0.2% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 49.3% | 50.3% |
| … fully (no partial credit) ↑ | 42.5% | 43.9% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% |
| … facts split afresh for each draft (earlier scoring) ↑ | 52.2% | 51.9% |
| Clinical synopsis HPO F1, exact ↑ | 35.7% | 36.5% |
| … precision ↑ | 43.8% | 43.0% |
| … recall ↑ | 37.1% | 40.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.4% | 55.4% |
| OMIM allelic variants recovered ↑ | 66.6% | 65.0% |
| Generated variants that are OMIM variants (precision) ↑ | 86.8% (n=57) | 87.9% (n=57) |
| Causal gene F1 ↑ | 98.0% | 98.0% |
| … recall ↑ | 97.8% | 97.8% |
| Inheritance matches OMIM ↑ | 94.1% | 94.1% |
| OMIM references used ↑ | 94.5% | 93.7% |

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Learned curation guide |
|---|---|
| Claims supported by cited paper ↑ | -0.1 (-1.0 to +1.0); 29/35/4 |
| … same, before the repair round ↓ | -0.0 (-0.4 to +0.3); 6/7/55 |
| OMIM per-paper facts conveyed (primary) ↑ | +1.0 (+0.0 to +2.0); 30/25/13 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.1 to +0.2); 3/3/62 |
| Clinical synopsis HPO F1, exact ↑ | +0.8 (-0.8 to +2.4); 34/22/12 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.1 (-1.3 to +1.4); 27/31/10 |
| OMIM allelic variants recovered ↑ | -1.6 (-3.7 to +0.0); 0/3/65 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/68 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/68 |

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

10 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 10 of the run's 12 entries qualify; left out: 180300, 607060. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 11 | 0 | 1: 607060 |
| Direct reading | 11 | 0 | 1: 180300 |
| Agentic curator | 12 | 0 | 0 |
| Case table first | 10 | 2: 180300 (9 papers), 607060 (2 papers) | 0 |
| Reconciled case database | 10 | 2: 180300 (9 papers), 607060 (2 papers) | 0 |

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.5% | 97.9% | 98.1% | 96.7% | 96.3% |
| … unsupported, before the repair round ↓ | 0.2% | 0.1% | 0.2% | 0.4% | 0.5% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 46.3% | 45.5% | 44.9% | 46.0% | 47.8% |
| … fully (no partial credit) ↑ | 39.5% | 38.6% | 37.9% | 39.2% | 41.2% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.2% | 0.1% | 0.2% |
| … facts split afresh for each draft (earlier scoring) ↑ | 47.4% | 47.4% | 47.4% | 48.6% | 49.7% |
| Clinical synopsis HPO F1, exact ↑ | 26.7% | 30.3% | 29.6% | 28.1% | 28.1% |
| … precision ↑ | 21.2% | 33.7% | 33.9% | 26.5% | 26.5% |
| … recall ↑ | 48.9% | 35.9% | 34.5% | 46.7% | 46.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.9% | 52.5% | 50.6% | 48.4% | 48.4% |
| OMIM allelic variants recovered ↑ | 55.8% | 54.5% | 56.2% | 58.1% | 56.1% |
| Generated variants that are OMIM variants (precision) ↑ | 52.1% | 64.9% | 66.2% | 39.0% | 46.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| … recall ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |
| OMIM references used ↑ | 96.6% | 97.2% | 89.6% | 94.8% | 94.5% |

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims audited per entry | 406.4 | 303.0 | 285.4 | 407.7 | 395.4 |
| Claims that could not be audited per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Clinical-synopsis HPO terms per entry | 42.8 | 20.3 | 18.5 | 40.8 | 40.8 |
| Allelic variants per entry | 10.3 | 6.3 | 6.6 | 14.5 | 12.8 |

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.4 (-1.1 to +0.2); 2/7/1 | +0.2 (-0.5 to +0.9); 5/5/0 | -1.2 (-2.2 to -0.1); 1/9/0 | -1.6 (-2.5 to -0.6); 2/8/0 |
| … same, before the repair round ↓ | +0.0 (-0.1 to +0.2); 2/5/3 | +0.0 (-0.2 to +0.2); 2/3/5 | +0.2 (-0.1 to +0.8); 2/6/2 | +0.4 (-0.1 to +1.1); 2/6/2 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.7 (-2.7 to +3.4); 6/3/1 | -0.6 (-2.1 to +0.7); 2/6/2 | +0.4 (-1.4 to +2.3); 5/4/1 | +2.3 (+0.4 to +4.2); 7/3/0 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.4); 1/2/7 | -0.1 (-0.7 to +0.3); 2/2/6 | -0.2 (-0.7 to +0.2); 2/1/7 | -0.1 (-0.7 to +0.4); 2/2/6 |
| Clinical synopsis HPO F1, exact ↑ | -3.6 (-7.3 to +0.4); 2/7/1 | -0.7 (-2.9 to +1.0); 3/4/3 | -2.1 (-6.0 to +2.1); 4/6/0 | -2.1 (-6.0 to +2.0); 4/6/0 |
| Clinical synopsis HPO F1, hierarchical ↑ | -3.6 (-6.9 to -0.2); 2/8/0 | -1.9 (-6.3 to +1.0); 4/5/1 | -4.1 (-7.7 to -0.3); 3/7/0 | -4.1 (-7.7 to -0.3); 3/7/0 |
| OMIM allelic variants recovered ↑ | +1.4 (-11.7 to +10.8); 4/1/5 | +1.7 (-1.4 to +5.7); 2/1/7 | +3.6 (-0.7 to +8.5); 3/1/6 | +1.6 (-4.9 to +7.8); 3/2/5 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | -20.0 (-50.0 to +0.0); 0/2/8 | -20.0 (-50.0 to +0.0); 0/2/8 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Generation: model calls | 43.9 | 2.0 | 2.0 | 44.0 | 45.9 |
| Generation: list price | $2.38 | $0.59 | $0.90 | $2.55 | $2.81 |
| Generation: input / output tokens | 273,265 / 67,321 | 34,086 / 17,083 | 169,973 / 27,350 | 338,163 / 72,294 | 362,469 / 76,857 |
| Generation: model time (s) | 577 | 132 | 213 | 639 | 686 |
| Audit and repair: list price | $2.83 | $2.32 | $2.19 | $2.88 | $2.84 |
| Scoring against OMIM: list price | $0.68 | $0.33 | $0.33 | $0.68 | $0.67 |
| Everything: list price | $5.89 | $3.24 | $3.42 | $6.11 | $6.32 |

## 10. Entries created after the model's likely training data (June to November 2026)

107 phenotype entries were created in 2026 (creation dates from NCBI); 53 have at least two cited references and one
in-scope paragraph. The 30 newest were run. Phenotype annotations exist for only one of them, so synopsis and
inheritance scores rest on one entry and are not reported. The model's training cut-off is not known to us; the
memory-only control is the empirical test.

20 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 20 of the run's 30 entries qualify; left out: 301174, 621639, 621644, 621667, 621671, 621687, 621704, 621707, 621722, 621728. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 23 | 7: 621639 (1 paper), 621644 (1 paper), 621667 (1 paper), 621671 (1 paper), 621704 (1 paper), 621707 (1 paper), 621728 (1 paper) | 0 |
| Direct reading | 28 | 0 | 2: 621639, 621728 |
| Agentic curator | 24 | 0 | 6: 621639, 621644, 621667, 621704, 621707, 621728 |
| Memory only (control) | 30 | 0 | 0 |
| Case table first | 20 | 10: 301174 (1 paper), 621639 (1 paper), 621644 (1 paper), 621667 (1 paper), 621671 (1 paper), 621687 (1 paper), 621704 (1 paper), 621707 (1 paper), 621722 (1 paper), 621728 (1 paper) | 0 |

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 95.5% | 95.8% | 26.2% | 94.5% |
| … unsupported, before the repair round ↓ | 0.0% | 0.0% | 0.1% | 35.3% | 0.4% |
| … contradicted, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 0.5% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.5% | 52.2% | 51.1% | 7.0% | 49.4% |
| OMIM allelic variants recovered ↑ | 70.9% | 65.5% | 62.5% | 5.0% | 68.9% |
| Generated variants that are OMIM variants (precision) ↑ | 79.8% | 87.4% (n=18) | 88.0% (n=18) | 100.0% (n=1) | 83.3% (n=19) |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 30.0% | 100.0% |
| OMIM references used ↑ | 99.6% | 98.6% | 99.6% | 10.0% | 99.6% |

| Metric | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | +0.2 (-1.1 to +1.7); 10/10/0 | +0.2 (-1.1 to +1.6); 9/10/1 | -69.3 (-83.1 to -54.4); 0/20/0 | -1.1 (-3.1 to +1.1); 7/13/0 |
| OMIM per-paper facts conveyed (primary) ↑ | -0.7 (-2.4 to +1.0); 5/11/4 | -1.1 (-1.8 to -0.3); 2/12/6 | -45.2 (-52.4 to -38.0); 0/20/0 | -2.8 (-5.4 to -0.7); 5/11/4 |
| OMIM allelic variants recovered ↑ | +5.4 (-1.9 to +14.3); 4/1/15 | -3.1 (-7.8 to +0.0); 0/2/18 | -60.6 (-75.5 to -45.5); 0/17/3 | +3.3 (-3.3 to +11.7); 2/1/17 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/20 | +0.0 (+0.0 to +0.0); 0/0/20 | -70.0 (-90.0 to -50.0); 0/14/6 | +0.0 (+0.0 to +0.0); 0/0/20 |

Stopped replies were frequent on these entries: the agentic curator's writer was stopped on 6 of 30, direct reading's
on 2, and the evidence graph lost a paper on 7.

The 30 entries were chosen by creation date alone: the newest qualifying entries, by creation month and then entry number (`evalset.recent_entries`). They were used in no other run, and no code that shapes how the strategies write, audit or repair a draft changed after their drafts were generated: run with the final code, the 5 strategies run on them make only calls answered from the cache of the original calls and reproduce the stored drafts exactly (recall, then verify was not run on these entries).

## 11. Earlier analyses on the main set

- **Planted errors.** In 60 paragraphs the audit had passed, one fact was altered by rule (a count, a zygosity, a
  residue or a mode of inheritance). The audit flagged all 60, each on a claim containing the altered value. The test
  measures sensitivity to blunt single-fact substitutions only; omissions and misattributions are not tested. In 6 of
  the 60 other claims were also flagged.
- **Audit control: the same paragraphs unaltered.** The 60 paragraphs were audited again as written, with fresh model calls (replicate salt `auditctl1`) and the procedure of the planted test. 0 of 60 had at least one claim flagged; 0 of 361 claims were flagged (0 unsupported, 0 contradicted) and 6 came back partly supported; 3 could not be audited. Safety stops: 0. The paragraphs were selected for having passed the audit once, so this is the rate at which a re-audit flags a paragraph that passed before, not the false-flag rate on arbitrary paragraphs.
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

All experiments, pilots and re-scoring: 38,505 cached model calls, 260 million input and
69 million output tokens, about $2,896 at list price.
