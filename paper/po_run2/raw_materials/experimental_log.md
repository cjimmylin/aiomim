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
  title only: 74. Supplementary material was not retrieved. Papers that at least one in-scope
  curator paragraph is about (so the primary endpoint can see what a draft says about them; computed from the run's
  files): 327 of 515 (81 of
  96 readable in full, 221 of 345 abstract only,
  25 of 74 title only).
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

### 2.3a Sign tests on the 93 compared entries

Exact two-sided sign test on the paired differences from direct reading (ties dropped). The primary endpoint is not
adjusted. For the secondary headline measures the sign-test p-value was adjusted by Holm's method across those
measures within each strategy; the last column lists the measures whose adjusted p-value is below 0.05, with the mean
paired difference.

| Strategy minus direct reading | Primary endpoint: sign test p (better / worse / tied) | Secondary headline measures | … with Holm-adjusted p < 0.05 |
|---|---|---|---|
| Evidence graph | 0.213 (33 / 45 / 15) | 8 | none |
| Agentic curator | 0.242 (31 / 42 / 20) | 8 | none |
| Memory only (control) | <0.001 (7 / 85 / 1) | 8 | Claims supported by cited paper (<0.001; -45.3 points); Claims unsupported or contradicted, before the repair round (<0.001; +22.4 points); OMIM allelic variants recovered (<0.001; -51.3 points); Causal gene F1 (0.011; -13.6 points) |
| Recall, then verify | <0.001 (2 / 89 / 2) | 8 | Clinical synopsis HPO F1, exact (<0.001; -11.0 points); Clinical synopsis HPO F1, hierarchical (<0.001; -15.7 points); OMIM allelic variants recovered (<0.001; -54.9 points); Causal gene F1 (0.002; -14.7 points); Inheritance matches OMIM (<0.001; -20.4 points) |
| Case table first | 0.071 (31 / 48 / 14) | 8 | none |

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

Note (recomputed from the per-entry scores): in the table above, the evidence graph's better / worse / tied counts against direct reading are the same on OMIM facts conveyed and on HPO F1 exact (36/48/16 and 36/48/16), but the per-entry signs differ on 61 of 100 entries: the equal totals are a coincidence, not a copied row.

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

### 2.10a OMIM facts conveyed on the facts the available text states

Do the reading strategies look close only because most facts were not in the text they had? Each fixed fact carries
the stored judgement of section 3 (stated, partly stated or not stated in the text available for its paper; the same
for every strategy), so the strategies can be compared on the facts a reader of that text could have conveyed.

93 entries: those the main comparison uses (complete for every strategy). Every frozen fact a strategy was marked on is joined by fact id with the stored judgement of whether the text available for its paper states it (stated, partly stated, not stated; `gaps --frozen`, a model judgement with verified quotes, not checked by a curator). The judgement is a property of the supplied text, so every strategy is scored on the same facts in each restriction. Coverage = (present + half of partial) / facts. *Mean over entries* is over entries with at least one fact in the restriction (n entries); *pooled* is over facts. Differences are strategy minus Direct reading in percentage points, mean over the entries with such facts, with a 95% percentile bootstrap interval over entries (10,000 resamples, seed 7, as in `compare`), then entries better / worse / tied.

#### Join and sanity check

Facts without an availability judgement: 0 (excluded). The unrestricted mean recomputed from the joined fact marks against the main comparison's mean of OMIM facts conveyed:

| Strategy | Facts judged | Joined | Without availability judgement | Unrestricted mean, recomputed | Main comparison | Same to 0.1 |
|---|---|---|---|---|---|---|
| Evidence graph | 6,239 | 6,239 | 0 | 48.6% | 48.6% | yes |
| Direct reading | 6,239 | 6,239 | 0 | 49.1% | 49.1% | yes |
| Agentic curator | 6,239 | 6,239 | 0 | 48.4% | 48.4% | yes |
| Memory only (control) | 6,239 | 6,239 | 0 | 15.1% | 15.1% | yes |
| Recall, then verify | 6,239 | 6,239 | 0 | 14.6% | 14.6% | yes |
| Case table first | 6,239 | 6,239 | 0 | 47.2% | 47.2% | yes |

#### The facts, by availability

Pooled over the facts of the compared entries (identical for every strategy), by how the paragraph's paper(s) could be read.

| Paper read as | Facts | Stated | Partly stated | Not stated | Unjudged |
|---|---|---|---|---|---|
| Full text | 1,639 | 1,246 | 253 | 140 | 0 |
| Abstract only | 4,221 | 1,099 | 883 | 2,239 | 0 |
| Title only | 379 | 27 | 62 | 290 | 0 |
| All papers | 6,239 | 2,372 | 1,198 | 2,669 | 0 |

#### Summary: mean over entries

| Strategy | All facts | Stated | Stated or partly | Not stated | Stated, full-text papers | Stated, abstract-only papers |
|---|---|---|---|---|---|---|
| Evidence graph | 48.6% | 94.2% | 77.5% | 5.5% | 90.2% | 96.6% |
| Direct reading | 49.1% | 94.4% | 77.5% | 6.9% | 88.5% | 97.1% |
| Agentic curator | 48.4% | 93.6% | 76.9% | 6.3% | 88.3% | 96.3% |
| Memory only (control) | 15.1% | 23.3% | 23.3% | 8.2% | 10.9% | 28.2% |
| Recall, then verify | 14.6% | 28.8% | 26.0% | 2.1% | 13.6% | 36.5% |
| Case table first | 47.2% | 91.0% | 75.4% | 5.9% | 80.1% | 95.5% |
| Entries (n) | 93 | 89 | 93 | 90 | 40 | 79 |

| Difference from Direct reading | All facts | Stated | Stated or partly | Not stated | Stated, full-text papers | Stated, abstract-only papers |
|---|---|---|---|---|---|---|
| Evidence graph | -0.5 (-1.5 to +0.5); 33/45/15 | -0.3 (-2.1 to +1.3); 25/21/43 | -0.0 (-1.5 to +1.4); 41/41/11 | -1.4 (-3.4 to +0.7); 16/28/46 | +1.7 (-0.7 to +4.0); 18/15/7 | -0.5 (-2.5 to +1.2); 10/11/58 |
| Agentic curator | -0.6 (-1.3 to +0.0); 31/42/20 | -0.8 (-2.6 to +0.4); 20/23/46 | -0.7 (-2.0 to +0.4); 36/37/20 | -0.5 (-1.8 to +1.0); 16/27/47 | -0.2 (-1.8 to +1.2); 13/15/12 | -0.8 (-2.6 to +0.5); 11/9/59 |
| Memory only (control) | -34.0 (-39.2 to -28.7); 7/85/1 | -71.1 (-75.9 to -66.0); 0/85/4 | -54.2 (-59.2 to -48.9); 4/88/1 | +1.3 (-1.4 to +4.6); 37/30/23 | -77.6 (-82.5 to -72.3); 0/40/0 | -68.9 (-75.1 to -62.3); 0/74/5 |
| Recall, then verify | -34.5 (-39.3 to -30.0); 2/89/2 | -65.6 (-70.6 to -60.2); 0/84/5 | -51.5 (-55.9 to -47.1); 1/88/4 | -4.8 (-6.7 to -3.0); 11/50/29 | -74.9 (-80.2 to -69.3); 0/40/0 | -60.6 (-67.3 to -53.5); 0/71/8 |
| Case table first | -1.9 (-3.1 to -0.7); 31/48/14 | -3.4 (-5.6 to -1.6); 16/42/31 | -2.1 (-3.6 to -0.6); 27/48/18 | -1.0 (-3.1 to +1.2); 27/26/37 | -8.4 (-14.3 to -3.8); 9/28/3 | -1.6 (-3.6 to +0.2); 12/21/46 |

#### All facts (unrestricted), all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 48.6% | 93 | 47.6% | 6,239 | 2,562 / 811 / 2,840 / 26 | -0.5 | -1.5 to +0.5 | 33 / 45 / 15 |
| Direct reading | 49.1% | 93 | 48.6% | 6,239 | 2,620 / 820 / 2,771 / 28 | – | – | – |
| Agentic curator | 48.4% | 93 | 47.9% | 6,239 | 2,593 / 796 / 2,820 / 30 | -0.6 | -1.3 to +0.0 | 31 / 42 / 20 |
| Memory only (control) | 15.1% | 93 | 12.7% | 6,239 | 502 / 578 / 5,133 / 26 | -34.0 | -39.2 to -28.7 | 7 / 85 / 1 |
| Recall, then verify | 14.6% | 93 | 12.5% | 6,239 | 502 / 553 / 5,167 / 17 | -34.5 | -39.3 to -30.0 | 2 / 89 / 2 |
| Case table first | 47.2% | 93 | 46.1% | 6,239 | 2,490 / 769 / 2,948 / 32 | -1.9 | -3.1 to -0.7 | 31 / 48 / 14 |

#### Facts stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 94.2% | 89 | 92.9% | 2,372 | 2,144 / 121 / 106 / 1 | -0.3 | -2.1 to +1.3 | 25 / 21 / 43 |
| Direct reading | 94.4% | 89 | 91.8% | 2,372 | 2,114 / 128 / 129 / 1 | – | – | – |
| Agentic curator | 93.6% | 89 | 91.3% | 2,372 | 2,099 / 134 / 139 / 0 | -0.8 | -2.6 to +0.4 | 20 / 23 / 46 |
| Memory only (control) | 23.3% | 89 | 15.5% | 2,372 | 251 / 233 / 1,880 / 8 | -71.1 | -75.9 to -66.0 | 0 / 85 / 4 |
| Recall, then verify | 28.8% | 89 | 20.3% | 2,372 | 378 / 209 / 1,782 / 3 | -65.6 | -70.6 to -60.2 | 0 / 84 / 5 |
| Case table first | 91.0% | 89 | 87.5% | 2,372 | 2,016 / 118 / 235 / 3 | -3.4 | -5.6 to -1.6 | 16 / 42 / 31 |

#### Facts stated or partly stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 77.5% | 93 | 80.5% | 3,570 | 2,504 / 743 / 308 / 15 | -0.0 | -1.5 to +1.4 | 41 / 41 / 11 |
| Direct reading | 77.5% | 93 | 80.2% | 3,570 | 2,499 / 725 / 333 / 13 | – | – | – |
| Agentic curator | 76.9% | 93 | 79.6% | 3,570 | 2,487 / 709 / 360 / 14 | -0.7 | -2.0 to +0.4 | 36 / 37 / 20 |
| Memory only (control) | 23.3% | 93 | 17.5% | 3,570 | 398 / 452 / 2,705 / 15 | -54.2 | -59.2 to -48.9 | 4 / 88 / 1 |
| Recall, then verify | 26.0% | 93 | 20.8% | 3,570 | 488 / 506 / 2,565 / 11 | -51.5 | -55.9 to -47.1 | 1 / 88 / 4 |
| Case table first | 75.4% | 93 | 76.9% | 3,570 | 2,409 / 675 / 468 / 18 | -2.1 | -3.6 to -0.6 | 27 / 48 / 18 |

#### Facts not stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 5.5% | 90 | 3.5% | 2,669 | 58 / 68 / 2,532 / 11 | -1.4 | -3.4 to +0.7 | 16 / 28 / 46 |
| Direct reading | 6.9% | 90 | 6.3% | 2,669 | 121 / 95 / 2,438 / 15 | – | – | – |
| Agentic curator | 6.3% | 90 | 5.6% | 2,669 | 106 / 87 / 2,460 / 16 | -0.5 | -1.8 to +1.0 | 16 / 27 / 47 |
| Memory only (control) | 8.2% | 90 | 6.3% | 2,669 | 104 / 126 / 2,428 / 11 | +1.3 | -1.4 to +4.6 | 37 / 30 / 23 |
| Recall, then verify | 2.1% | 90 | 1.4% | 2,669 | 14 / 47 / 2,602 / 6 | -4.8 | -6.7 to -3.0 | 11 / 50 / 29 |
| Case table first | 5.9% | 90 | 4.8% | 2,669 | 81 / 94 / 2,480 / 14 | -1.0 | -3.1 to +1.2 | 27 / 26 / 37 |

#### Facts stated in the available text, papers readable in full

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 90.2% | 40 | 89.0% | 1,246 | 1,062 / 95 / 88 / 1 | +1.7 | -0.7 to +4.0 | 18 / 15 / 7 |
| Direct reading | 88.5% | 40 | 87.0% | 1,246 | 1,034 / 101 / 110 / 1 | – | – | – |
| Agentic curator | 88.3% | 40 | 86.5% | 1,246 | 1,025 / 106 / 115 / 0 | -0.2 | -1.8 to +1.2 | 13 / 15 / 12 |
| Memory only (control) | 10.9% | 40 | 10.4% | 1,246 | 72 / 116 / 1,055 / 3 | -77.6 | -82.5 to -72.3 | 0 / 40 / 0 |
| Recall, then verify | 13.6% | 40 | 13.0% | 1,246 | 102 / 119 / 1,024 / 1 | -74.9 | -80.2 to -69.3 | 0 / 40 / 0 |
| Case table first | 80.1% | 40 | 80.5% | 1,246 | 958 / 89 / 196 / 3 | -8.4 | -14.3 to -3.8 | 9 / 28 / 3 |

#### Facts stated in the available text, papers readable as abstract only

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 96.6% | 79 | 97.2% | 1,099 | 1,055 / 26 / 18 / 0 | -0.5 | -2.5 to +1.2 | 10 / 11 / 58 |
| Direct reading | 97.1% | 79 | 97.0% | 1,099 | 1,053 / 27 / 19 / 0 | – | – | – |
| Agentic curator | 96.3% | 79 | 96.6% | 1,099 | 1,048 / 28 / 23 / 0 | -0.8 | -2.6 to +0.5 | 11 / 9 / 59 |
| Memory only (control) | 28.2% | 79 | 20.9% | 1,099 | 173 / 113 / 808 / 5 | -68.9 | -75.1 to -62.3 | 0 / 74 / 5 |
| Recall, then verify | 36.5% | 79 | 28.3% | 1,099 | 268 / 87 / 742 / 2 | -60.6 | -67.3 to -53.5 | 0 / 71 / 8 |
| Case table first | 95.5% | 79 | 95.1% | 1,099 | 1,031 / 29 / 39 / 0 | -1.6 | -3.6 to +0.2 | 12 / 21 / 46 |

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

Replicate 1 is the main run for these 30 entries (its direct-reading and evidence-graph drafts are the same text as
the main run's, 60 of 60); replicates 2 and 3 were generated, audited and scored afresh.

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
The 40 entries are weighted towards entries with full text (22 have at least half their papers readable in full and 29 have at least one; the others were drawn at random to bring each creation-era band to 8 entries), so
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

**The ablation set and the main comparison** (computed from the per-entry files of both runs; OMIM facts conveyed, differences from direct reading in points with a bootstrap interval over entries as in the comparison reports).

- The 38 ablation entries by the main comparison's access groups: 11 no full text (abstracts only), 7 under half full text, 19 half or more full text, 1 all full text; 0 outside the main comparison's 93 entries.
- Stored drafts of run `ablation40` against run `omim100` for the same entries (run metadata aside): direct reading 38 of 38 drafts identical, fact marks identical on 38; evidence graph 38 of 38 drafts identical, fact marks identical on 38; case table 38 of 38 drafts identical, fact marks identical on 38.
- Main run on the 38 ablation entries: evidence graph +1.0 (38 entries, -0.8 to +2.9; better/worse/tied 19/15/4), case table -2.3 (38 entries, -4.5 to +0.0; better/worse/tied 13/24/1).
- Main run on its 21 entries with half or more of their papers in full text: evidence graph -1.8 (21 entries, -4.4 to +0.6; better/worse/tied 7/12/2), case table -6.1 (21 entries, -8.3 to -3.7; better/worse/tied 3/18/0). 19 of them are in the ablation set (the other 2, 613744, 619681, are among the entries a matched or plus-text variant did not complete); ablation run on those 19: evidence graph -1.2 (19 entries, -3.8 to +1.3; better/worse/tied 7/10/2), case table -6.2 (19 entries, -8.6 to -3.5; better/worse/tied 3/16/0).
- Ablation run on its other 19 entries (no full text, under half, or all full text): evidence graph +3.1 (19 entries, +1.0 to +5.6; better/worse/tied 12/5/2), case table +1.5 (19 entries, -1.1 to +4.7; better/worse/tied 10/8/1).

Reading: the three arms' drafts and fact scores in the ablation are the main run's, so the two estimates differ only in the entries they average over: on the evidence graph against direct reading, -1.2 points on the ablation's entries with half or more full text and +3.1 on its other entries.

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
an upper bound on error. The entries used are the 49 with a paper read in full that an in-scope curator
paragraph is about; all their full-text papers were hidden (91 papers). The other 5
full-text papers (in 5 entries) have no in-scope curator paragraph, so hiding them could not
change the score (computed from the run's files).

Which facts count as about a full-text paper differs between this experiment and the by-access tables. Here every
in-scope paragraph about a hidden paper is scored: 2,120 facts in 46 entries with a
direct-reading draft. In the by-access tables (sections 2.8, 2.10a, 3) a paragraph about several papers is classed by
its least readable paper, so a paragraph about a full-text paper and an abstract-only paper counts as abstract only:
1,837 facts in 44 entries are classed as full text on that rule, and 283 facts
of this experiment are classed abstract or title only there (computed from direct reading's stored scores; the
by-access tables are further restricted to the 93 entries every strategy completed).

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
  measures sensitivity to blunt single-fact substitutions only; misattributed citations, conflation, dropped
  qualifiers and omissions were tested later (section 14.4). In 6 of
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
- Published systems: PaperQA2 (its document-query pipeline, without its agent) and GraphRAG were run as released on
  10 and 4 entries, and STORM could not be run with this model (section 14). SLIDERS and others were not run. The
  strategies are our own implementations of the ideas.
- No second model was tested.

## 13. Total model usage

All experiments, pilots and re-scoring: 45,291 cached model calls, 338 million input and
82 million output tokens, about $3,587 at list price.

## 14. Second round of experiments (20-21 November 2026)

Design, reduced sizes, summary and deviations: `docs/experiments-round2.md`. Sizes are small (4 to 10 entries per
experiment, 30 planted items per class): the results show directions and large effects only. The result files are
reproduced below with their headings lowered. Where they say "strategy" names in code form: `direct` direct reading,
`agent` agentic curator, `kg` evidence graph, `cohort` case table first, `closedbook` memory only, `recall` recall,
then verify.

### 14.1 Natural large-entry tier (A1)

From `results/largeft/large_tier.md`.

#### Experiment A1: natural large-entry tier

Generated 2026-11-20T07:41:00 by `python -m aiomim.largetier analyze`. **The 12 large12 entries were scored after the audit's repair round; the new entries were generated and scored without audit or repair. The combined tier mixes the two.**

New entries run: 4 (155600, 168600, 152700, 114500), the first in rule order of `evalsets/largeft8.tsv`; the header of that file gives the rule, seed, candidates and shortlist.

Measure: OMIM facts conveyed: share of the fixed (frozen) fact list of the entry's in-scope curator paragraphs that the draft text citing the paper conveys (present = 1, partial = 0.5), mean over entries. Paired differences are strategy minus direct reading, in percentage points, with a percentile bootstrap 95% interval (10,000 resamples, seed 7; none below 3 entries) and an exact two-sided sign test on better/worse (ties dropped). No correction for multiple comparisons.

##### Deviations from the design

- Sample of up to 200 eligible entries (design: 400) and 8 new entries selected (design: 16; reduced sizes: 8).
- Only the first 4 selected entries in rule order were run (reduced sizes: 8, floor 6): the 1,500-call cap allowed no more (an entry cost about 250-330 new calls, most of it per-paper extraction for the evidence graph and the case table).
- The split on facts the supplied text states was not made (reduced sizes: only if it fits).
- The selection was resolved in three passes across machine restarts; counts resolved earlier were reused from its log. The first three entries were run before it finished, each only once its place in the top 8 was certain from the bounds (times in the header of evalsets/largeft8.tsv).

##### Completion

complete = draft written and every per-paper call succeeded; incomplete = draft written but a per-paper extraction call was stopped by the safety filter and the paper was dropped (evidence graph, case table); no draft = the writer (or a direct-reading batch) was stopped, or the strategy did not run.

| Group | Strategy | complete | incomplete | no draft |
|---|---|---|---|---|
| combined | Direct reading | 12 | 0 | 4 |
| combined | Agentic curator | 14 | 0 | 2 |
| combined | Evidence graph | 11 | 4 | 1 |
| combined | Case table first | 10 | 5 | 1 |
| new | Direct reading | 1 | 0 | 3 |
| new | Agentic curator | 2 | 0 | 2 |
| new | Evidence graph | 0 | 4 | 0 |
| new | Case table first | 0 | 3 | 1 |
| old | Direct reading | 11 | 0 | 1 |
| old | Agentic curator | 12 | 0 | 0 |
| old | Evidence graph | 11 | 0 | 1 |
| old | Case table first | 10 | 2 | 0 |

Safety-filter stops on the new entries (recorded, never retried):

| Strategy | writer stopped (no draft) | entries with stopped papers | papers stopped |
|---|---|---|---|
| Direct reading | 3 | 0 | 0 |
| Agentic curator | 2 | 0 | 0 |
| Evidence graph | 0 | 4 | 37 |
| Case table first | 1 | 3 | 25 |

##### Facts conveyed on entries every strategy completed (the design's comparison)

| Group | n | Strategy | mean % | vs direct (pp) | 95% CI | better / worse / tied | sign p |
|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | 10 | Direct reading | 45.5 | – | – | – | – |
| All compared entries (old + new) | 10 | Agentic curator | 44.9 | -0.6 | [-2.1, +0.7] | 2 / 6 / 2 | 0.289 |
| All compared entries (old + new) | 10 | Evidence graph | 46.3 | +0.7 | [-2.7, +3.4] | 6 / 3 / 1 | 0.508 |
| All compared entries (old + new) | 10 | Case table first | 46.0 | +0.4 | [-1.4, +2.3] | 5 / 4 / 1 | 1.000 |
| New entries alone (no audit) | 0 | Direct reading | – | – | – | – | – |
| New entries alone (no audit) | 0 | Agentic curator | – | – | – | – | – |
| New entries alone (no audit) | 0 | Evidence graph | – | – | – | – | – |
| New entries alone (no audit) | 0 | Case table first | – | – | – | – | – |
| large12 alone (after repair) | 10 | Direct reading | 45.5 | – | – | – | – |
| large12 alone (after repair) | 10 | Agentic curator | 44.9 | -0.6 | [-2.1, +0.7] | 2 / 6 / 2 | 0.289 |
| large12 alone (after repair) | 10 | Evidence graph | 46.3 | +0.7 | [-2.7, +3.4] | 6 / 3 / 1 | 0.508 |
| large12 alone (after repair) | 10 | Case table first | 46.0 | +0.4 | [-1.4, +2.3] | 5 / 4 / 1 | 1.000 |
| All compared, supplied characters at or below the median | 5 | Direct reading | 37.8 | – | – | – | – |
| All compared, supplied characters at or below the median | 5 | Agentic curator | 37.7 | -0.1 | [-0.7, +0.6] | 1 / 2 / 2 | 1.000 |
| All compared, supplied characters at or below the median | 5 | Evidence graph | 39.5 | +1.7 | [-0.1, +4.3] | 3 / 1 / 1 | 0.625 |
| All compared, supplied characters at or below the median | 5 | Case table first | 38.4 | +0.7 | [-1.4, +3.3] | 2 / 2 / 1 | 1.000 |
| All compared, supplied characters above the median | 5 | Direct reading | 53.3 | – | – | – | – |
| All compared, supplied characters above the median | 5 | Agentic curator | 52.2 | -1.1 | [-3.9, +1.6] | 1 / 4 / 0 | 0.375 |
| All compared, supplied characters above the median | 5 | Evidence graph | 53.1 | -0.2 | [-6.7, +4.4] | 3 / 2 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Case table first | 53.5 | +0.2 | [-2.6, +2.8] | 3 / 2 / 0 | 1.000 |
| New alone, at or below their median | 0 | Direct reading | – | – | – | – | – |
| New alone, at or below their median | 0 | Agentic curator | – | – | – | – | – |
| New alone, at or below their median | 0 | Evidence graph | – | – | – | – | – |
| New alone, at or below their median | 0 | Case table first | – | – | – | – | – |
| New alone, above their median | 0 | Direct reading | – | – | – | – | – |
| New alone, above their median | 0 | Agentic curator | – | – | – | – | – |
| New alone, above their median | 0 | Evidence graph | – | – | – | – | – |
| New alone, above their median | 0 | Case table first | – | – | – | – | – |

Median supplied characters of the compared entries: 56,818 (all); no new entry is compared.

##### Secondary view: every strategy wrote a scored draft (stopped papers included)

Not in the design. Incomplete drafts were written without the papers whose extraction the safety filter stopped, so a strategy's score here mixes method and stops; read it as a description, not a test.

| Group | n | Strategy | mean % | vs direct (pp) | 95% CI | better / worse / tied | sign p |
|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | 11 | Direct reading | 46.2 | – | – | – | – |
| All compared entries (old + new) | 11 | Agentic curator | 45.5 | -0.6 | [-1.9, +0.5] | 2 / 7 / 2 | 0.180 |
| All compared entries (old + new) | 11 | Evidence graph | 45.7 | -0.5 | [-4.3, +2.8] | 6 / 4 / 1 | 0.754 |
| All compared entries (old + new) | 11 | Case table first | 46.3 | +0.1 | [-1.5, +1.9] | 5 / 5 / 1 | 1.000 |
| New entries alone (no audit) | 1 | Direct reading | 52.3 | – | – | – | – |
| New entries alone (no audit) | 1 | Agentic curator | 51.5 | -0.8 | – | 0 / 1 / 0 | 1.000 |
| New entries alone (no audit) | 1 | Evidence graph | 39.8 | -12.5 | – | 0 / 1 / 0 | 1.000 |
| New entries alone (no audit) | 1 | Case table first | 49.6 | -2.7 | – | 0 / 1 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Direct reading | 52.5 | – | – | – | – |
| All compared, supplied characters above the median | 5 | Agentic curator | 51.4 | -1.1 | [-3.9, +1.6] | 1 / 4 / 0 | 0.375 |
| All compared, supplied characters above the median | 5 | Evidence graph | 49.2 | -3.3 | [-10.2, +3.6] | 2 / 3 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Case table first | 51.9 | -0.6 | [-3.2, +2.4] | 2 / 3 / 0 | 1.000 |

Median supplied characters of these entries: 59,100.

Pairwise with direct reading, on entries where both wrote a scored draft (stopped papers included):

| Group | Strategy | n | strategy % | direct % | vs direct (pp) | 95% CI | better / worse / tied | sign p | entries |
|---|---|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | Agentic curator | 12 | 44.8 | 45.5 | -0.6 | [-1.8, +0.5] | 2 / 8 / 2 | 0.109 | 128100, 152700*, 175200, 258870, 600116, 601419, 607060, 609016, 613095, 613470, 613679, 621314 |
| All compared entries (old + new) | Evidence graph | 11 | 45.7 | 46.2 | -0.5 | [-4.3, +2.8] | 6 / 4 / 1 | 0.754 | 128100, 152700*, 175200, 258870, 600116, 601419, 609016, 613095, 613470, 613679, 621314 |
| All compared entries (old + new) | Case table first | 12 | 45.7 | 45.5 | +0.2 | [-1.4, +1.9] | 6 / 5 / 1 | 1.000 | 128100, 152700*, 175200, 258870, 600116, 601419, 607060, 609016, 613095, 613470, 613679, 621314 |
| New entries alone (no audit) | Agentic curator | 1 | 51.5 | 52.3 | -0.8 | – | 0 / 1 / 0 | 1.000 | 152700* |
| New entries alone (no audit) | Evidence graph | 1 | 39.8 | 52.3 | -12.5 | – | 0 / 1 / 0 | 1.000 | 152700* |
| New entries alone (no audit) | Case table first | 1 | 49.6 | 52.3 | -2.7 | – | 0 / 1 / 0 | 1.000 | 152700* |

(* new entry)

##### Per entry

refs = references; full = readable in full; chars = characters supplied (title, abstract, full text); prompts = writer prompts of direct reading (batches + merge; * planned, the writer was stopped); cut = papers/characters direct reading's prompt shortened; ext cut = papers over the 180,000-character extraction cap; paras/facts = in-scope curator paragraphs and fixed facts; refs scored = references the scored paragraphs are about (share of all references). Coverage % per strategy; (i) incomplete, with papers stopped; (–) no draft. agent unread = papers the agentic curator did not open.

| Entry | tier | refs | full | chars | prompts | cut | ext cut | paras | facts | refs scored | direct | agent | kg | cohort | agent unread |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 258870 | old | 34 | 0 | 33,745 | 1 | 0/0 | 0 | 13 | 83 | 2 (5.9%) | 11.4 | 10.2 | 10.8 | 10.8 | 0 |
| 128100 | old | 60 | 1 | 71,650 | 1 | 0/0 | 0 | 10 | 157 | 10 (16.7%) | 52.2 | 46.5 | 57.3 | 54.1 | 0 |
| 180300 | old | 73 | 16 | 648,575 | 3* | 0/0 | 0 | 10 | 90 | 9 (12.3%) | – | 47.2 | 56.1 | 58.9 (i, 9) | 4 |
| 600116 | old | 39 | 3 | 132,106 | 1 | 3/25,174 | 0 | 14 | 163 | 9 (23.1%) | 37.1 | 36.8 | 36.2 | 34.7 | 0 |
| 607060 | old | 44 | 5 | 215,334 | 1 | 4/77,703 | 0 | 16 | 150 | 14 (31.8%) | 37.7 | 37.3 | – | 38.7 (i, 2) | 0 |
| 609016 | old | 30 | 1 | 67,818 | 1 | 1/13,328 | 0 | 7 | 59 | 5 (16.7%) | 77.1 | 80.5 | 81.4 | 81.4 | 0 |
| 613679 | old | 35 | 0 | 31,849 | 1 | 0/0 | 0 | 9 | 97 | 13 (37.1%) | 52.1 | 52.1 | 58.8 | 49.5 | 0 |
| 613470 | old | 31 | 0 | 21,025 | 1 | 0/0 | 0 | 5 | 46 | 3 (9.7%) | 54.3 | 55.4 | 54.3 | 54.3 | 0 |
| 621314 | old | 45 | 2 | 108,471 | 1 | 2/29,922 | 0 | 5 | 48 | 4 (8.9%) | 43.8 | 41.7 | 31.2 | 39.6 | 0 |
| 175200 | old | 75 | 0 | 54,535 | 1 | 0/0 | 0 | 14 | 118 | 6 (8.0%) | 39.4 | 39.0 | 41.1 | 40.3 | 0 |
| 601419 | old | 37 | 1 | 59,100 | 1 | 0/0 | 0 | 18 | 256 | 19 (51.3%) | 56.4 | 55.5 | 59.4 | 57.8 | 0 |
| 613095 | old | 33 | 0 | 39,040 | 1 | 0/0 | 0 | 8 | 79 | 5 (15.2%) | 31.6 | 31.6 | 32.3 | 37.3 | 0 |
| 155600 | new | 119 | 33 | 998,176 | 3* | 0/0 | 0 | 6 | 53 | 6 (5.0%) | – | – | 48.1 (i, 20) | 52.8 (i, 18) | – |
| 168600 | new | 133 | 19 | 604,761 | 3* | 0/0 | 0 | 16 | 152 | 10 (7.5%) | – | 41.8 | 46.4 (i, 7) | 47.0 (i, 5) | 0 |
| 152700 | new | 148 | 14 | 614,865 | 3 | 0/0 | 0 | 14 | 133 | 14 (9.5%) | 52.3 | 51.5 | 39.8 (i, 3) | 49.6 (i, 2) | 13 |
| 114500 | new | 76 | 12 | 375,649 | 1* | 8/95,140 | 0 | 15 | 94 | 6 (7.9%) | – | – | 48.9 (i, 7) | – | – |

##### Caps that truncated the input

Direct reading: one prompt holds 600,000 characters; above that the papers are split into batches of that size and the partial drafts merged, and only a paper longer than a whole batch is cut; in one prompt each paper is cut to max(20,000, 600,000 / papers) characters. Evidence graph and case table: each paper's extraction reads at most 180,000 characters.

- 600116 (old): direct reading cut 3 papers by 25,174 characters; extraction cut 0 papers
- 607060 (old): direct reading cut 4 papers by 77,703 characters; extraction cut 0 papers
- 609016 (old): direct reading cut 1 papers by 13,328 characters; extraction cut 0 papers
- 621314 (old): direct reading cut 2 papers by 29,922 characters; extraction cut 0 papers
- 114500 (new): direct reading cut 8 papers by 95,140 characters (as planned: the writer was stopped, so no draft was written from it); extraction cut 0 papers



##### Calls, cost and time (new entries)

Calls and list-price cost as made fresh (generation; scoring = adaptive judge, variant match and fixed-fact marking); wall-clock = the CLI pass for that entry and strategy (generation + scoring), summed over resumed passes; new calls = calls not answered from the cache in this experiment's passes.

| Strategy | entries | generate calls | score calls | generate $ | score $ | wall-clock h | new calls here |
|---|---|---|---|---|---|---|---|
| Direct reading | 4 | 9 | 66 | 17.19 | 1.49 | 0.61 | 126 |
| Agentic curator | 4 | 6 | 81 | 9.03 | 1.99 | 0.83 | 64 |
| Evidence graph | 4 | 484 | 105 | 35.64 | 2.73 | 0.98 | 589 |
| Case table first | 4 | 484 | 90 | 35.92 | 2.28 | 0.92 | 559 |

New model calls made by this experiment: 1338 of the 1500 cap (1338 counted per pass in runs/largeft/timing.tsv, plus 0 made by a pass the machine restart interrupted).

| Entry | Strategy | status | gen calls | gen $ | score calls | marking calls | wall s | new calls |
|---|---|---|---|---|---|---|---|---|
| 155600 | direct | no_draft | 2 | 6.91 | 6 | – | 577 | 14 |
| 155600 | agent | no_draft | 1 | 1.77 | 6 | – | 653 | 1 |
| 155600 | kg | incomplete | 121 | 11.9 | 12 | 6 | 981 | 133 |
| 155600 | cohort | incomplete | 121 | 11.18 | 13 | 6 | 999 | 134 |
| 168600 | direct | no_draft | 2 | 4.1 | 16 | – | 454 | 34 |
| 168600 | agent | complete | 2 | 2.54 | 31 | 14 | 883 | 31 |
| 168600 | kg | incomplete | 135 | 8.81 | 33 | 16 | 971 | 168 |
| 168600 | cohort | incomplete | 135 | 9.25 | 33 | 16 | 813 | 168 |
| 152700 | direct | complete | 4 | 3.68 | 29 | 14 | 644 | 47 |
| 152700 | agent | complete | 2 | 2.89 | 29 | 14 | 793 | 31 |
| 152700 | kg | incomplete | 150 | 9.44 | 29 | 14 | 930 | 179 |
| 152700 | cohort | incomplete | 150 | 9.7 | 29 | 14 | 916 | 179 |
| 114500 | direct | no_draft | 1 | 2.5 | 15 | – | 511 | 31 |
| 114500 | agent | no_draft | 1 | 1.83 | 15 | – | 671 | 1 |
| 114500 | kg | incomplete | 78 | 5.49 | 31 | 15 | 658 | 109 |
| 114500 | cohort | no_draft | 78 | 5.79 | 15 | – | 588 | 78 |

### 14.2 Controlled padding of the input (A2)

From `results/padding/padding.md`.

#### A2. Controlled padding of the input

Design: `docs/experiments-round2.md`, section A2. Generated by `python -m aiomim.padding summarise`. Coverage is the share of the entry's own frozen OMIM facts conveyed (present + half of partial, over judged facts), credited to draft paragraphs citing the paper. No audit and no repair at any level.

Entries (6): 606763, 611521, 613730, 614501, 614651, 615073.

##### Input sizes

| Level | Characters (min / median / max) | Papers (min / median / max) | Added papers (median) | Own text share (median) |
|---|---|---|---|---|
| P0 | 18,467 / 39,450 / 177,882 | 2 / 2.0 / 8 | 0.0 | 100.0% |
| P1 | 485,611 / 498,324 / 523,126 | 9 / 14.0 / 18 | 9.5 | 8.0% |
| P2 | 1,174,338 / 1,190,742 / 1,237,103 | 27 / 32.5 / 37 | 28.0 | 3.3% |

Per entry (papers / characters):

| Entry | Own papers | P0 chars | P1 papers | P1 chars | P2 papers | P2 chars |
|---|---|---|---|---|---|---|
| 606763 | 2 | 50,324 | 9 | 485,611 | 27 | 1,174,338 |
| 611521 | 8 | 177,882 | 18 | 497,146 | 35 | 1,237,103 |
| 613730 | 2 | 28,577 | 18 | 499,502 | 37 | 1,223,212 |
| 614501 | 2 | 100,676 | 10 | 507,075 | 33 | 1,192,908 |
| 614651 | 4 | 18,467 | 13 | 523,126 | 32 | 1,181,234 |
| 615073 | 2 | 22,540 | 15 | 496,427 | 30 | 1,188,576 |

##### Completion

| Level | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| P0 | 6 / 0 / 0 | 6 / 0 / 0 | 6 / 0 / 0 | 6 / 0 / 0 |
| P1 | 6 / 0 / 0 | 6 / 0 / 0 | 5 / 1 / 0 (611521) | 3 / 3 / 0 (606763, 611521, 615073) |
| P2 | 6 / 0 / 0 | 6 / 0 / 0 | 3 / 3 / 0 (606763, 611521, 614501) | 3 / 3 / 0 (606763, 611521, 615073) |

Complete / incomplete / no draft. Entries every strategy completed at every level: 2 (613730, 614651).

##### Coverage on the 2 entries every strategy completed at every level (symmetric rule of compare.py)

Entries: 613730, 614651.

| Strategy | P0 | P1 | P2 | P1 − P0 [95% CI]; better/worse/tied | P2 − P0 [95% CI]; better/worse/tied |
|---|---|---|---|---|---|
| Direct reading | 73.4% | 78.1% | 76.9% | +4.7 [n<5]; 2/0/0; p=0.5 | +3.5 [n<5]; 2/0/0; p=0.5 |
| Agentic curator | 70.6% | 71.0% | 72.7% | +0.4 [n<5]; 1/0/1; p=1.0 | +2.1 [n<5]; 2/0/0; p=0.5 |
| Evidence graph | 64.8% | 65.6% | 63.5% | +0.8 [n<5]; 1/0/1; p=1.0 | -1.2 [n<5]; 0/1/1; p=1.0 |
| Case table first | 62.8% | 59.8% | 59.8% | -3.0 [n<5]; 0/2/0; p=0.5 | -3.0 [n<5]; 0/2/0; p=0.5 |

Differences in percentage points; bootstrap interval over entries (10,000 resamples; none below 5 entries); with 2 entries the intervals are indicative only.

Difference from direct reading at each level:

| Strategy | P0 | P1 | P2 |
|---|---|---|---|
| Agentic curator | -2.9 [n<5]; 0/1/1; p=1.0 | -7.1 [n<5]; 0/2/0; p=0.5 | -4.2 [n<5]; 0/2/0; p=0.5 |
| Evidence graph | -8.7 [n<5]; 0/2/0; p=0.5 | -12.6 [n<5]; 0/2/0; p=0.5 | -13.4 [n<5]; 0/2/0; p=0.5 |
| Case table first | -10.7 [n<5]; 0/2/0; p=0.5 | -18.3 [n<5]; 0/2/0; p=0.5 | -17.1 [n<5]; 0/2/0; p=0.5 |

Strategy-by-size interaction (change from P0 minus direct reading's change from P0):

| Strategy | P1 | P2 |
|---|---|---|
| Agentic curator | -4.3 [n<5]; 0/2/0; p=0.5 | -1.4 [n<5]; 1/1/0; p=1.0 |
| Evidence graph | -3.9 [n<5]; 0/2/0; p=0.5 | -4.7 [n<5]; 0/2/0; p=0.5 |
| Case table first | -7.7 [n<5]; 0/2/0; p=0.5 | -6.4 [n<5]; 0/2/0; p=0.5 |

Ranking by mean coverage: P0: Direct reading > Agentic curator > Evidence graph > Case table first; P1: Direct reading > Agentic curator > Evidence graph > Case table first; P2: Direct reading > Agentic curator > Evidence graph > Case table first

##### Secondary: coverage on the 6 entries complete at every level when a per-paper failure on an added (off-topic) paper is allowed

Entries: 606763, 611521, 613730, 614501, 614651, 615073.

| Strategy | P0 | P1 | P2 | P1 − P0 [95% CI]; better/worse/tied | P2 − P0 [95% CI]; better/worse/tied |
|---|---|---|---|---|---|
| Direct reading | 71.3% | 74.9% | 74.5% | +3.6 [+1.0, +5.9]; 5/1/0; p=0.2188 | +3.2 [-0.7, +6.8]; 5/1/0; p=0.2188 |
| Agentic curator | 69.8% | 70.6% | 70.3% | +0.8 [-0.4, +2.1]; 3/1/2; p=0.625 | +0.5 [-3.4, +4.4]; 4/2/0; p=0.6875 |
| Evidence graph | 73.5% | 73.3% | 74.1% | -0.1 [-2.1, +1.8]; 2/2/2; p=1.0 | +0.7 [-1.0, +2.5]; 3/2/1; p=1.0 |
| Case table first | 70.0% | 69.0% | 69.1% | -1.0 [-2.1, +0.0]; 0/2/4; p=0.5 | -0.9 [-2.1, +0.1]; 1/2/3; p=1.0 |

Differences in percentage points; bootstrap interval over entries (10,000 resamples; none below 5 entries); with 6 entries the intervals are indicative only.

Difference from direct reading at each level:

| Strategy | P0 | P1 | P2 |
|---|---|---|---|
| Agentic curator | -1.5 [-3.7, +0.8]; 1/3/2; p=0.625 | -4.2 [-7.0, -1.3]; 1/5/0; p=0.2188 | -4.2 [-9.9, -0.2]; 2/4/0; p=0.6875 |
| Evidence graph | +2.2 [-5.9, +9.9]; 4/2/0; p=0.6875 | -1.6 [-10.8, +7.7]; 2/4/0; p=0.6875 | -0.4 [-9.2, +7.0]; 4/2/0; p=0.6875 |
| Case table first | -1.2 [-9.8, +9.2]; 2/4/0; p=0.6875 | -5.8 [-15.0, +4.6]; 2/4/0; p=0.6875 | -5.4 [-13.6, +2.8]; 2/4/0; p=0.6875 |

Strategy-by-size interaction (change from P0 minus direct reading's change from P0):

| Strategy | P1 | P2 |
|---|---|---|
| Agentic curator | -2.8 [-4.3, -1.1]; 1/5/0; p=0.2188 | -2.7 [-9.1, +2.0]; 3/3/0; p=1.0 |
| Evidence graph | -3.8 [-7.5, -0.3]; 1/4/1; p=0.375 | -2.5 [-5.7, +1.2]; 2/4/0; p=0.6875 |
| Case table first | -4.6 [-7.2, -1.5]; 1/5/0; p=0.2188 | -4.2 [-7.7, +0.1]; 1/5/0; p=0.2188 |

Ranking by mean coverage: P0: Evidence graph > Direct reading > Case table first > Agentic curator; P1: Direct reading > Evidence graph > Agentic curator > Case table first; P2: Direct reading > Evidence graph > Agentic curator > Case table first

###### Each level on its own complete set

| Level | Entries | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| P0 | 6 | 71.3% | 69.8% | 73.5% | 70.0% |
| P1 | 3 | 74.7% | 68.8% | 72.3% | 68.5% |
| P2 | 2 | 76.9% | 72.7% | 63.5% | 59.8% |

##### Citations of added papers

| Level | Strategy | Mean share of paragraphs citing an added paper | Paragraphs citing added / all | Paragraphs attributing a statement about the disorder to an added paper | Drafts with one |
|---|---|---|---|---|---|
| P1 | Direct reading | 0.0% | 0 / 115 | 0 | none |
| P1 | Agentic curator | 0.0% | 0 / 115 | 0 | none |
| P1 | Evidence graph | 0.0% | 0 / 137 | 0 | none |
| P1 | Case table first | 0.0% | 0 / 127 | 0 | none |
| P2 | Direct reading | 0.0% | 0 / 118 | 0 | none |
| P2 | Agentic curator | 0.0% | 0 / 117 | 0 | none |
| P2 | Evidence graph | 0.0% | 0 / 140 | 0 | none |
| P2 | Case table first | 0.0% | 0 / 131 | 0 | none |

##### Caps that applied

```
{
 "P0": {
  "direct": {
   "drafts": 6,
   "batched": 0,
   "prompts": {
    "1": 6
   },
   "per_paper_cap_range": [
    75000,
    300000
   ],
   "drafts_with_own_paper_truncated": [
    "611521"
   ],
   "own_papers_truncated": 1,
   "added_papers_truncated": 0,
   "drafts_losing_a_pmid_in_merge": []
  },
  "agent": {
   "drafts": 6,
   "own_papers_not_opened": 0,
   "drafts_with_own_paper_not_opened": [],
   "added_papers_opened": 0,
   "added_papers_not_opened": 0
  },
  "kg": {
   "drafts": 6,
   "papers_failed": 0,
   "relevance": {
    "primary": 17,
    "supporting": 3
   }
  },
  "cohort": {
   "drafts": 6,
   "papers_failed": 0,
   "relevance": {
    "primary": 17,
    "supporting": 3
   }
  }
 },
 "P1": {
  "direct": {
   "drafts": 6,
   "batched": 0,
   "prompts": {
    "1": 6
   },
   "per_paper_cap_range": [
    33333,
    66666
   ],
   "drafts_with_own_paper_truncated": [
    "611521"
   ],
   "own_papers_truncated": 2,
   "added_papers_truncated": 24,
   "drafts_losing_a_pmid_in_merge": []
  },
  "agent": {
   "drafts": 6,
   "own_papers_not_opened": 0,
   "drafts_with_own_paper_not_opened": [],
   "added_papers_opened": 5,
   "added_papers_not_opened": 58
  },
  "kg": {
   "drafts": 6,
   "papers_failed": 1,
   "relevance": {
    "not_relevant": 59,
    "primary": 18,
    "background": 3,
    "supporting": 3
   }
  },
  "cohort": {
   "drafts": 6,
   "papers_failed": 3,
   "relevance": {
    "not_relevant": 59,
    "primary": 18,
    "background": 3,
    "supporting": 3
   }
  }
 },
 "P2": {
  "direct": {
   "drafts": 6,
   "batched": 6,
   "prompts": {
    "3": 6
   },
   "per_paper_cap_range": [
    null,
    null
   ],
   "drafts_with_own_paper_truncated": [],
   "own_papers_truncated": 0,
   "added_papers_truncated": 0,
   "drafts_losing_a_pmid_in_merge": []
  },
  "agent": {
   "drafts": 6,
   "own_papers_not_opened": 0,
   "drafts_with_own_paper_not_opened": [],
   "added_papers_opened": 0,
   "added_papers_not_opened": 174
  },
  "kg": {
   "drafts": 6,
   "papers_failed": 3,
   "relevance": {
    "not_relevant": 159,
    "primary": 22,
    "background": 9,
    "supporting": 4
   }
  },
  "cohort": {
   "drafts": 6,
   "papers_failed": 5,
   "relevance": {
    "not_relevant": 163,
    "primary": 22,
    "background": 6,
    "supporting": 3
   }
  }
 }
}
```

##### Calls, cost and time

| Level | Strategy | Drafts | Generation calls (new) | Generation list price, as if fresh | Scoring calls (new) | Wall-clock per entry (median, s) |
|---|---|---|---|---|---|---|
| P0 | Direct reading | 6 | 12 (0) | $2.41 | 34 (1) | – |
| P0 | Agentic curator | 6 | 11 (0) | $2.57 | 34 (0) | – |
| P0 | Evidence graph | 6 | 32 (0) | $4.24 | 34 (1) | – |
| P0 | Case table first | 6 | 31 (0) | $4.58 | 34 (0) | – |
| P1 | Direct reading | 6 | 12 (11) | $9.15 | 34 (34) | 116.4 |
| P1 | Agentic curator | 6 | 12 (12) | $2.51 | 34 (34) | 124.4 |
| P1 | Evidence graph | 6 | 95 (74) | $14.32 | 34 (34) | 211.6 |
| P1 | Case table first | 6 | 94 (73) | $14.85 | 34 (20) | 171.2 |
| P2 | Direct reading | 6 | 29 (29) | $25.14 | 34 (34) | 149.4 |
| P2 | Agentic curator | 6 | 10 (10) | $2.74 | 34 (34) | 143.9 |
| P2 | Evidence graph | 6 | 206 (119) | $30.59 | 34 (34) | 205.7 |
| P2 | Case table first | 6 | 205 (114) | $31.05 | 34 (15) | 155.8 |

New model calls in all (these entries): 683.

##### Decisions and deviations

- Deviation (user's request, smaller budget): 8 entries planned instead of 12, P2 at about 1,200,000 characters instead of 1,800,000, at most 800 new model calls. The pilot (first 2 entries) cost about 125 new calls per entry, projecting about 1,000 for 8, so the entries were reduced in order to 6 (the floor allowed).
- Entries: ablation40 entries complete for every ablation variant (results/ablation40/strategies.json) with at least half their papers in full text, in entry-number order; all four strategies completed them in runs/omim100.
- Added papers: full-text papers already fetched for entries of existing runs; excluded: the entry's own papers, papers cited by any entry sharing a causal gene with it, papers whose text names one of its genes, papers whose citing entry has no gold record (gene unknown), and papers over 180,000 characters (the extraction cap). Seeded per entry; P1's additions are a prefix of P2's seeded order; each level stops at the paper that brings the total nearest the target.
- Supplied order is shuffled with the entry's seed, but direct reading and the agent's index sort papers by year and the extract-then-write strategies read each paper separately, so the order has little effect.
- P0: the runs/omim100 drafts before repair, rebuilt from the model cache with a cache-only backend (0 misses for every draft; the cached audit and repair replayed on the rebuild reproduce the stored final drafts exactly). Scoring P0 needed new judge calls only where the cited draft text differs from the scored final draft.
- No audit and no repair at any level. Coverage = (present + 0.5 partial) / judged facts of the entry's own frozen lists, credited to paragraphs citing the paper (eval_gold_text_frozen, as rescore).
- Completion follows compare.py: a per-paper extraction failure makes a draft incomplete. Every such failure here was a safety-filter stop on an added (off-topic) paper, so a secondary analysis allows failures on added papers.
- P1/P2 drafts are fresh generations; P0 drafts were generated earlier. A change from P0 therefore mixes input size with run-to-run variation (within-entry SD of single-entry coverage in results/replicate30: 2.5 points for direct reading, 4.0 for the evidence graph); there is no P0 replicate, so a rise of a few points over 6 entries is not read as a gain.
- Wall-clock is per task with at most 4 model calls in flight across all tasks, so it includes waiting for a slot.

### 14.3 Published systems as released (B)

From `results/external/external.md`.

#### Experiment B: published systems as released

Design: `docs/experiments-round2.md`, section B, at the reduced sizes. OMIM facts conveyed (present + half partial, over judged facts of the fixed lists); comparison strategies from run omim100 on the same entries. Paired differences from direct reading are in points: mean (bootstrap 95% interval over entries); better/worse/tied; exact sign test p. With 4 or 10 entries the intervals are wide and the sign test cannot reach p < 0.05 with 4 entries (the smallest possible p is 0.125): every result here is exploratory.

##### What was run

| System | Package and version | Entry point | Entries attempted | Completed | Safety stops | Role |
|---|---|---|---|---|---|---|
| PaperQA2 | paper-qa 2026.8.12 | paperqa.Docs.aadd (one document per paper) + Docs.aquery (one per question) | 10 | 10 | 0 | main PaperQA2 result (whole-chunk embeddings) |
| PaperQA2, 512-token embedding cut | paper-qa 2026.8.12 | paperqa.Docs.aadd (one document per paper) + Docs.aquery (one per question) | 10 | 10 | 0 | sensitivity result (the shared embedder's 512-token cut) |
| GraphRAG local | graphrag 3.3.0 | `graphrag index --method standard` (CLI), then `graphrag.cli.query.run_local_search` per question with the CLI's defaults | 4 | 4 | 0 | main GraphRAG result (local search, the CLI's default) |
| GraphRAG global | graphrag 3.3.0 | the same indexes as GraphRAG local; `graphrag.cli.query.run_global_search` per question with the CLI's defaults | 4 | 4 | 0 | GraphRAG global search on the same indexes |
| STORM | knowledge-storm 1.1.1 | `STORMWikiRunner.run` (research, outline, article, polish) with its default arguments | 10 | 0 | 30 | no article produced |

STORM: completion 0 of 10. The model's safety filter stopped every chain-of-thought prompt of STORM's research stage (30 of 30 fresh requests; the 20 plain outline prompts were answered), so no article was produced; nothing was retried or reworded. There is nothing to score.

GraphRAG ran on 4 entries: the fixed rule takes entries in the seeded order while they fit in 1,000 model calls; the fifth entry (611521) did not fit in what was left, so the run stopped below the design's floor of 6.

##### Side by side on the 4 entries every system completed

Entries: 615582, 616326, 620029, 621313.

| Measure | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 49.6% (n=4) | 49.6% (n=4) | 46.2% (n=4) | 46.0% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 51.6% (n=4) | 51.3% (n=4) | 47.3% (n=4) | 47.7% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 73.9% (n=4) | 75.2% (n=4) | 65.8% (n=4) | 68.2% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 2.1% (n=4) | 3.1% (n=4) | 4.1% (n=4) | 20.5% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 76.4% (n=4) | 76.5% (n=4) | 68.0% (n=4) | 67.4% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 4.5% (n=4) | 5.2% (n=4) | 4.8% (n=4) | 21.5% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 70.0% (n=4) | 70.3% (n=4) | 61.9% (n=4) | 61.0% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 72.0% (n=4) | 72.3% (n=4) | 63.8% (n=4) | 62.3% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -10.0 (-18.5 to -2.8); 0/4/0; p=0.125; n=4 | -10.0 (-20.2 to +0.2); 1/3/0; p=0.625; n=4 | -13.4 (-25.3 to -1.5); 1/3/0; p=0.625; n=4 | -13.6 (-27.1 to -5.4); 0/4/0; p=0.125; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -9.8 (-19.6 to -2.9); 0/4/0; p=0.125; n=4 | -10.1 (-21.8 to -0.2); 1/3/0; p=0.625; n=4 | -14.2 (-26.8 to -2.0); 1/3/0; p=0.625; n=4 | -13.8 (-27.8 to -2.9); 0/4/0; p=0.125; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -14.9 (-25.6 to -5.0); 0/4/0; p=0.125; n=4 | -13.6 (-27.4 to +0.2); 1/3/0; p=0.625; n=4 | -23.0 (-45.8 to -1.8); 1/3/0; p=0.625; n=4 | -20.6 (-33.9 to -7.3); 0/4/0; p=0.125; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | -0.9 (-5.4 to +2.8); 1/1/2; p=1.000; n=4 | +0.1 (-3.4 to +3.8); 1/1/2; p=1.000; n=4 | +1.1 (+0.0 to +2.1); 2/0/2; p=0.500; n=4 | +17.5 (+0.4 to +50.2); 3/0/1; p=0.250; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -14.1 (-24.6 to -5.9); 0/4/0; p=0.125; n=4 | -13.9 (-27.2 to -0.7); 1/3/0; p=0.625; n=4 | -22.4 (-41.4 to -3.4); 1/3/0; p=0.625; n=4 | -23.0 (-40.8 to -5.2); 0/4/0; p=0.125; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | -0.0 (-2.0 to +1.9); 1/1/2; p=1.000; n=4 | +0.6 (+0.0 to +1.9); 1/0/3; p=1.000; n=4 | +0.2 (-1.3 to +1.9); 1/1/2; p=1.000; n=4 | +16.9 (+0.0 to +50.0); 2/0/2; p=0.500; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |

Per entry, (a) / (b):

| Entry | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|---|
| 615582 | 37.5% / 41.8% | 33.2% / 38.5% | 42.4% / 43.8% | 41.8% / 46.1% | 48.7% / 50.3% | 51.3% / 53.6% | 54.3% / 57.6% | 45.4% / 44.4% |
| 616326 | 36.2% / 40.1% | 42.1% / 45.4% | 18.4% / 24.3% | 30.3% / 29.6% | 40.1% / 43.4% | 37.5% / 43.4% | 41.4% / 43.4% | 41.4% / 43.4% |
| 620029 | 59.4% / 59.4% | 57.8% / 56.2% | 53.9% / 50.8% | 78.9% / 82.8% | 82.8% / 84.4% | 83.6% / 80.5% | 75.8% / 74.2% | 75.0% / 77.3% |
| 621313 | 65.3% / 65.3% | 65.3% / 65.3% | 70.3% / 70.3% | 33.1% / 32.2% | 66.9% / 67.8% | 66.1% / 66.1% | 66.9% / 67.8% | 64.4% / 61.0% |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2 | 15,445 | 1.9% | 57.0 | 199,000 | 28,972 | $2.17 | 490 | 165 (n=3) |
| PaperQA2, 512-token embedding cut | 15,002 | 1.0% | 57.0 | 190,249 | 28,044 | $2.08 | 481 | 245 (n=4) |
| GraphRAG local | 37,932 | 19.5% | 134.8 | 699,331 | 199,975 | $9.29 | 1,990 | 962 (n=4) |
| GraphRAG global | 63,752 | 13.7% | 165.2 | 1,288,343 | 289,518 | $12.14 | 2,844 | 1,328 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG local: share of characters by kind of mapping: sources 68.9%, entities/relationships only 11.6%, community reports only 0.0%, none 19.5%.
- GraphRAG global: share of characters by kind of mapping: sources 0.0%, entities/relationships only 0.0%, community reports only 86.3%, none 13.7%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

##### PaperQA2 on its own entries

Role: main PaperQA2 result (whole-chunk embeddings). Entries attempted: 10; completed: 10.

| Measure | PaperQA2 | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 47.4% (n=10) | 61.9% (n=10) | 61.9% (n=10) | 61.7% (n=10) | 57.6% (n=10) |
| (b) facts conveyed, credited anywhere in the draft | 50.8% (n=10) | 63.7% (n=10) | 62.2% (n=10) | 63.1% (n=10) | 57.7% (n=10) |
| (c) (a) on facts the supplied text states | 70.4% (n=10) | 88.8% (n=10) | 89.5% (n=10) | 92.1% (n=10) | 84.8% (n=10) |
| (c) (a) on facts the supplied text does not state | 6.2% (n=10) | 11.8% (n=10) | 10.6% (n=10) | 5.5% (n=10) | 6.4% (n=10) |
| (c) (b) on facts the supplied text states | 72.8% (n=10) | 90.3% (n=10) | 90.5% (n=10) | 92.7% (n=10) | 84.4% (n=10) |
| (c) (b) on facts the supplied text does not state | 11.5% (n=10) | 13.6% (n=10) | 11.7% (n=10) | 7.3% (n=10) | 7.0% (n=10) |
| (c) (a) on facts the supplied text states or partly states | 64.3% (n=10) | 81.7% (n=10) | 82.0% (n=10) | 84.2% (n=10) | 77.9% (n=10) |
| (c) (b) on facts the supplied text states or partly states | 67.2% (n=10) | 83.4% (n=10) | 82.4% (n=10) | 85.4% (n=10) | 77.6% (n=10) |

Paired differences from direct reading:

| Measure | PaperQA2 | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -14.5 (-21.8 to -7.0); 1/9/0; p=0.021; n=10 | -0.1 (-2.2 to +1.9); 5/5/0; p=1.000; n=10 | -0.2 (-4.1 to +3.4); 4/4/2; p=1.000; n=10 | -4.4 (-8.6 to -0.2); 3/7/0; p=0.344; n=10 |
| (b) facts conveyed, credited anywhere in the draft | -12.8 (-19.2 to -6.1); 1/9/0; p=0.021; n=10 | -1.5 (-3.1 to +0.1); 1/5/4; p=0.219; n=10 | -0.6 (-4.4 to +3.2); 4/4/2; p=1.000; n=10 | -6.0 (-9.7 to -2.2); 1/7/2; p=0.070; n=10 |
| (c) (a) on facts the supplied text states | -18.4 (-25.5 to -10.7); 1/9/0; p=0.021; n=10 | +0.7 (-2.0 to +3.3); 4/4/2; p=1.000; n=10 | +3.3 (-1.4 to +8.0); 6/3/1; p=0.508; n=10 | -4.0 (-7.6 to +0.0); 2/7/1; p=0.180; n=10 |
| (c) (a) on facts the supplied text does not state | -5.7 (-11.5 to -0.4); 2/6/2; p=0.289; n=10 | -1.2 (-3.3 to +0.6); 3/4/3; p=1.000; n=10 | -6.3 (-16.4 to +1.6); 1/6/3; p=0.125; n=10 | -5.4 (-14.8 to +1.4); 3/5/2; p=0.727; n=10 |
| (c) (b) on facts the supplied text states | -17.5 (-24.4 to -9.9); 1/9/0; p=0.021; n=10 | +0.2 (-2.0 to +2.3); 5/5/0; p=1.000; n=10 | +2.4 (-2.2 to +6.8); 6/3/1; p=0.508; n=10 | -5.9 (-9.7 to -1.5); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text does not state | -2.0 (-4.7 to +0.4); 2/6/2; p=0.289; n=10 | -1.9 (-4.7 to +0.4); 2/4/4; p=0.688; n=10 | -6.2 (-14.4 to -0.1); 1/7/2; p=0.070; n=10 | -6.6 (-15.3 to -0.7); 1/5/4; p=0.219; n=10 |
| (c) (a) on facts the supplied text states or partly states | -17.4 (-24.9 to -9.0); 1/9/0; p=0.021; n=10 | +0.3 (-2.5 to +2.8); 6/4/0; p=0.754; n=10 | +2.4 (-1.4 to +6.2); 5/4/1; p=1.000; n=10 | -3.8 (-7.7 to +0.4); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text states or partly states | -16.2 (-23.2 to -8.6); 1/9/0; p=0.021; n=10 | -1.1 (-3.2 to +1.0); 4/6/0; p=0.754; n=10 | +2.0 (-2.5 to +6.2); 5/4/1; p=1.000; n=10 | -5.8 (-9.8 to -1.5); 2/7/1; p=0.180; n=10 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2 | 14,849 | 1.6% | 57.6 | 202,536 | 27,790 | $2.18 | 480 | 167 (n=8) |
| Direct reading | 12,143 | 0.0% | 2.0 | 34,447 | 9,128 | $0.43 | 73 | not recorded |
| Agentic curator | 11,675 | 0.0% | 2.0 | 103,517 | 14,026 | $0.46 | 114 | not recorded |
| Evidence graph | 14,406 | 0.0% | 7.6 | 73,145 | 24,773 | $0.89 | 190 | not recorded |
| Case table first | 13,776 | 0.0% | 7.6 | 82,262 | 26,849 | $0.97 | 208 | not recorded |

- Direct reading: audit and repair round 8.4 calls, $1.20, 243 model seconds per entry (not included above).
- Agentic curator: audit and repair round 7.7 calls, $1.10, 237 model seconds per entry (not included above).
- Evidence graph: audit and repair round 8.9 calls, $1.33, 294 model seconds per entry (not included above).
- Case table first: audit and repair round 7.4 calls, $1.26, 289 model seconds per entry (not included above).

Settings changed from the defaults of paper-qa 2026.8.12:

| Setting | Default | Value | Reason |
|---|---|---|---|
| llm | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | answer writing; the local adapter in front of the project's one model (no other provider) |
| llm_config (api_base, api_key, timeout) | None (router built from llm, provider endpoint, provider key from env, LiteLLM default timeout) | package's default router layout + api_base=<adapter>, api_key=sk-local-dummy, timeout=900 | point the answer role at the adapter; dummy key; adapter asks for a client timeout >= 900 s (its queue is capped at 3 concurrent calls) |
| summary_llm (+ summary_llm_config, same router change) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | contextual summaries of evidence; the local adapter in front of the project's one model (no other provider) |
| agent.agent_llm (+ agent_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | pointed at the adapter for safety; not used by Docs.aquery (no call was made in this role) |
| parsing.enrichment_llm (+ enrichment_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | media enrichment of PDFs; pointed at the adapter for safety; not used for .txt papers (no call was made in this role) |
| embedding (+ embedding_config kwargs api_base, api_key) | text-embedding-3-small | openai/bge-small-en-v1.5 via adapter /v1/embeddings (fastembed BAAI/bge-small-en-v1.5, 384 dims) | the one local embedding model shared by all systems; no hosted embedding |
| parsing.use_doc_details | True | False | no outside metadata lookup (Crossref, Semantic Scholar, Unpaywall, OpenAlex, retractions, journal quality); citation and title are supplied instead |
| Docs.aadd(citation=, docname=, title=) | None: citation inferred by `llm` from the first chunk; docname derived from it (Author+Year) | citation = the paper's reference line (first line of <pmid>.txt, from the export); docname = <Surname><Year>-<PMID> from papers.csv; title from papers.csv | corpus = exactly the entry's papers, one document each; no call or lookup spent on metadata; citations in answers map back to the PubMed id unambiguously |
| entry point | agent_query with agent_type 'ToolSelector' (pqa ask) | Docs.aadd per paper, then Docs.aquery per question (the README's 'Manual (No Agent)' usage) | the default agent selects tools by function calling, which the adapter refuses; the 'fake' agent also ends with a function-calling Complete step (select_tool with tool_choice) that the adapter refuses; Docs.aquery needs none and keeps retrieval, contextual summaries and answer |
| environment | LiteLLM fetches its model cost map from GitHub; telemetry defaults | LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, DO_NOT_TRACK=1, ANONYMIZED_TELEMETRY=False, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=<local>; outbound proxy = a local logger that refuses and records every non-local connection | no outside service is contacted; any attempt is logged |
| embedding input length (adapter /v1/embeddings, long_inputs='pool') | bge-small-en-v1.5 truncates every input at 512 tokens, so a default 5,000-character PaperQA chunk (about 1,100-1,300 tokens) is embedded from its first ~510 tokens only | an input over 510 tokens (model tokenizer, without [CLS]/[SEP]) is split into consecutive non-overlapping windows of at most 510 tokens; each is embedded, the vectors are averaged (unweighted) and re-normalised; shorter inputs are embedded exactly as before | the 512-token cut is an artefact of the shared local embedding model, not of PaperQA2 (whose default embedding, text-embedding-3-small, takes 8,191 tokens); pooling embeds the whole chunk |

##### PaperQA2, 512-token embedding cut on its own entries

Role: sensitivity result (the shared embedder's 512-token cut). Entries attempted: 10; completed: 10.

| Measure | PaperQA2, 512-token embedding cut | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 49.1% (n=10) | 61.9% (n=10) | 61.9% (n=10) | 61.7% (n=10) | 57.6% (n=10) |
| (b) facts conveyed, credited anywhere in the draft | 51.5% (n=10) | 63.7% (n=10) | 62.2% (n=10) | 63.1% (n=10) | 57.7% (n=10) |
| (c) (a) on facts the supplied text states | 72.4% (n=10) | 88.8% (n=10) | 89.5% (n=10) | 92.1% (n=10) | 84.8% (n=10) |
| (c) (a) on facts the supplied text does not state | 7.1% (n=10) | 11.8% (n=10) | 10.6% (n=10) | 5.5% (n=10) | 6.4% (n=10) |
| (c) (b) on facts the supplied text states | 74.0% (n=10) | 90.3% (n=10) | 90.5% (n=10) | 92.7% (n=10) | 84.4% (n=10) |
| (c) (b) on facts the supplied text does not state | 10.6% (n=10) | 13.6% (n=10) | 11.7% (n=10) | 7.3% (n=10) | 7.0% (n=10) |
| (c) (a) on facts the supplied text states or partly states | 66.5% (n=10) | 81.7% (n=10) | 82.0% (n=10) | 84.2% (n=10) | 77.9% (n=10) |
| (c) (b) on facts the supplied text states or partly states | 68.6% (n=10) | 83.4% (n=10) | 82.4% (n=10) | 85.4% (n=10) | 77.6% (n=10) |

Paired differences from direct reading:

| Measure | PaperQA2, 512-token embedding cut | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -12.9 (-21.5 to -4.9); 2/8/0; p=0.109; n=10 | -0.1 (-2.2 to +1.9); 5/5/0; p=1.000; n=10 | -0.2 (-4.1 to +3.4); 4/4/2; p=1.000; n=10 | -4.4 (-8.6 to -0.2); 3/7/0; p=0.344; n=10 |
| (b) facts conveyed, credited anywhere in the draft | -12.2 (-19.7 to -4.7); 2/8/0; p=0.109; n=10 | -1.5 (-3.1 to +0.1); 1/5/4; p=0.219; n=10 | -0.6 (-4.4 to +3.2); 4/4/2; p=1.000; n=10 | -6.0 (-9.7 to -2.2); 1/7/2; p=0.070; n=10 |
| (c) (a) on facts the supplied text states | -16.4 (-25.1 to -7.9); 2/8/0; p=0.109; n=10 | +0.7 (-2.0 to +3.3); 4/4/2; p=1.000; n=10 | +3.3 (-1.4 to +8.0); 6/3/1; p=0.508; n=10 | -4.0 (-7.6 to +0.0); 2/7/1; p=0.180; n=10 |
| (c) (a) on facts the supplied text does not state | -4.7 (-13.6 to +2.3); 4/4/2; p=1.000; n=10 | -1.2 (-3.3 to +0.6); 3/4/3; p=1.000; n=10 | -6.3 (-16.4 to +1.6); 1/6/3; p=0.125; n=10 | -5.4 (-14.8 to +1.4); 3/5/2; p=0.727; n=10 |
| (c) (b) on facts the supplied text states | -16.3 (-24.5 to -7.8); 2/8/0; p=0.109; n=10 | +0.2 (-2.0 to +2.3); 5/5/0; p=1.000; n=10 | +2.4 (-2.2 to +6.8); 6/3/1; p=0.508; n=10 | -5.9 (-9.7 to -1.5); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text does not state | -3.0 (-8.9 to +1.2); 3/3/4; p=1.000; n=10 | -1.9 (-4.7 to +0.4); 2/4/4; p=0.688; n=10 | -6.2 (-14.4 to -0.1); 1/7/2; p=0.070; n=10 | -6.6 (-15.3 to -0.7); 1/5/4; p=0.219; n=10 |
| (c) (a) on facts the supplied text states or partly states | -15.2 (-23.9 to -6.4); 1/9/0; p=0.021; n=10 | +0.3 (-2.5 to +2.8); 6/4/0; p=0.754; n=10 | +2.4 (-1.4 to +6.2); 5/4/1; p=1.000; n=10 | -3.8 (-7.7 to +0.4); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text states or partly states | -14.8 (-22.9 to -6.4); 2/8/0; p=0.109; n=10 | -1.1 (-3.2 to +1.0); 4/6/0; p=0.754; n=10 | +2.0 (-2.5 to +6.2); 5/4/1; p=1.000; n=10 | -5.8 (-9.8 to -1.5); 2/7/1; p=0.180; n=10 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2, 512-token embedding cut | 14,633 | 1.4% | 57.6 | 194,940 | 27,094 | $2.10 | 472 | 244 (n=10) |
| Direct reading | 12,143 | 0.0% | 2.0 | 34,447 | 9,128 | $0.43 | 73 | not recorded |
| Agentic curator | 11,675 | 0.0% | 2.0 | 103,517 | 14,026 | $0.46 | 114 | not recorded |
| Evidence graph | 14,406 | 0.0% | 7.6 | 73,145 | 24,773 | $0.89 | 190 | not recorded |
| Case table first | 13,776 | 0.0% | 7.6 | 82,262 | 26,849 | $0.97 | 208 | not recorded |

- Direct reading: audit and repair round 8.4 calls, $1.20, 243 model seconds per entry (not included above).
- Agentic curator: audit and repair round 7.7 calls, $1.10, 237 model seconds per entry (not included above).
- Evidence graph: audit and repair round 8.9 calls, $1.33, 294 model seconds per entry (not included above).
- Case table first: audit and repair round 7.4 calls, $1.26, 289 model seconds per entry (not included above).

Settings changed from the defaults of paper-qa 2026.8.12:

| Setting | Default | Value | Reason |
|---|---|---|---|
| llm | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | answer writing; the local adapter in front of the project's one model (no other provider) |
| llm_config (api_base, api_key, timeout) | None (router built from llm, provider endpoint, provider key from env, LiteLLM default timeout) | package's default router layout + api_base=<adapter>, api_key=sk-local-dummy, timeout=900 | point the answer role at the adapter; dummy key; adapter asks for a client timeout >= 900 s (its queue is capped at 3 concurrent calls) |
| summary_llm (+ summary_llm_config, same router change) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | contextual summaries of evidence; the local adapter in front of the project's one model (no other provider) |
| agent.agent_llm (+ agent_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | pointed at the adapter for safety; not used by Docs.aquery (no call was made in this role) |
| parsing.enrichment_llm (+ enrichment_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | media enrichment of PDFs; pointed at the adapter for safety; not used for .txt papers (no call was made in this role) |
| embedding (+ embedding_config kwargs api_base, api_key) | text-embedding-3-small | openai/bge-small-en-v1.5 via adapter /v1/embeddings (fastembed BAAI/bge-small-en-v1.5, 384 dims) | the one local embedding model shared by all systems; no hosted embedding |
| parsing.use_doc_details | True | False | no outside metadata lookup (Crossref, Semantic Scholar, Unpaywall, OpenAlex, retractions, journal quality); citation and title are supplied instead |
| Docs.aadd(citation=, docname=, title=) | None: citation inferred by `llm` from the first chunk; docname derived from it (Author+Year) | citation = the paper's reference line (first line of <pmid>.txt, from the export); docname = <Surname><Year>-<PMID> from papers.csv; title from papers.csv | corpus = exactly the entry's papers, one document each; no call or lookup spent on metadata; citations in answers map back to the PubMed id unambiguously |
| entry point | agent_query with agent_type 'ToolSelector' (pqa ask) | Docs.aadd per paper, then Docs.aquery per question (the README's 'Manual (No Agent)' usage) | the default agent selects tools by function calling, which the adapter refuses; the 'fake' agent also ends with a function-calling Complete step (select_tool with tool_choice) that the adapter refuses; Docs.aquery needs none and keeps retrieval, contextual summaries and answer |
| environment | LiteLLM fetches its model cost map from GitHub; telemetry defaults | LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, DO_NOT_TRACK=1, ANONYMIZED_TELEMETRY=False, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=<local>; outbound proxy = a local logger that refuses and records every non-local connection | no outside service is contacted; any attempt is logged |

##### GraphRAG local on its own entries

Role: main GraphRAG result (local search, the CLI's default). Entries attempted: 4; completed: 4.

| Measure | GraphRAG local | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 46.2% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 47.3% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 65.8% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 4.1% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 68.0% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 4.8% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 61.9% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 63.8% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | GraphRAG local | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -13.4 (-25.3 to -1.5); 1/3/0; p=0.625; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -14.2 (-26.8 to -2.0); 1/3/0; p=0.625; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -23.0 (-45.8 to -1.8); 1/3/0; p=0.625; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | +1.1 (+0.0 to +2.1); 2/0/2; p=0.500; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -22.4 (-41.4 to -3.4); 1/3/0; p=0.625; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | +0.2 (-1.3 to +1.9); 1/1/2; p=1.000; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (a) on facts the supplied text states or partly states | -21.3 (-39.5 to -3.1); 1/3/0; p=0.625; n=4 | -0.2 (-2.9 to +2.4); 2/2/0; p=1.000; n=4 | +2.3 (-4.5 to +9.4); 2/1/1; p=1.000; n=4 | -2.8 (-7.0 to +2.2); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text states or partly states | -21.1 (-39.1 to -2.9); 1/3/0; p=0.625; n=4 | -0.2 (-3.2 to +2.8); 2/2/0; p=1.000; n=4 | +1.2 (-7.3 to +9.4); 2/1/1; p=1.000; n=4 | -5.5 (-8.7 to -0.8); 1/3/0; p=0.625; n=4 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| GraphRAG local | 37,932 | 19.5% | 134.8 | 699,331 | 199,975 | $9.29 | 1,990 | 962 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG local: share of characters by kind of mapping: sources 68.9%, entities/relationships only 11.6%, community reports only 0.0%, none 19.5%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

Settings changed from the defaults of graphrag 3.3.0:

| Setting | Default | Value | Reason |
|---|---|---|---|
| completion_models.default_completion_model.model | gpt-4.1 | openai/claude-opus-5-5 | the project's one model through the local adapter |
| completion_models.default_completion_model.api_base | (none: the provider's public endpoint) | ${GRAPHRAG_API_BASE} = http://127.0.0.1:<port>/v1 | the local adapter (127.0.0.1 only) |
| completion_models.default_completion_model.api_key | ${GRAPHRAG_API_KEY} (.env: <API_KEY>) | sk-local-dummy (in .env) | dummy key; the adapter needs none and no real key is passed to the package |
| completion_models.default_completion_model.call_args | {} (LiteLLM/OpenAI client defaults: its own timeout and retries) | {"extra_headers": {"X-Aiomim-Tag": "<system>/<mim>/<step>"}, "max_retries": 0, "timeout": 1800} | client timeout 1800 s (a call can take minutes); the OpenAI client's own retries off (GraphRAG's retry and the adapter's retry remain); ledger tag header (bookkeeping only) |
| completion_models.default_completion_model.retry | {"max_retries": "(unset: package default 7)", "type": "exponential_backoff"} | {"max_retries": 2, "type": "exponential_backoff"} | few client retries: the adapter already retries transient failures with back-off; max_retries must be > 1 for this retry type |
| embedding_models.default_embedding_model.model | text-embedding-3-large | openai/bge-small-en-v1.5 | the adapter's local embedding model (BAAI/bge-small-en-v1.5, 384 dimensions), the same for all systems |
| embedding_models.default_embedding_model.api_base | (none: the provider's public endpoint) | ${GRAPHRAG_API_BASE} = http://127.0.0.1:<port>/v1 | the local adapter (127.0.0.1 only) |
| embedding_models.default_embedding_model.api_key | ${GRAPHRAG_API_KEY} (.env: <API_KEY>) | sk-local-dummy (in .env) | dummy key; the adapter needs none and no real key is passed to the package |
| embedding_models.default_embedding_model.call_args | {} (LiteLLM/OpenAI client defaults: its own timeout and retries) | {"extra_headers": {"X-Aiomim-Tag": "<system>/<mim>/<step>"}, "max_retries": 0, "timeout": 1800} | client timeout 1800 s (a call can take minutes); the OpenAI client's own retries off (GraphRAG's retry and the adapter's retry remain); ledger tag header (bookkeeping only) |
| embedding_models.default_embedding_model.retry | {"max_retries": "(unset: package default 7)", "type": "exponential_backoff"} | {"max_retries": 2, "type": "exponential_backoff"} | few client retries: the adapter already retries transient failures with back-off; max_retries must be > 1 for this retry type |
| extract_graph.completion_model_id | default_completion_model | completion_extract_graph | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/extract_graph), to count calls by workflow step; requests are otherwise identical |
| summarize_descriptions.completion_model_id | default_completion_model | completion_summarize_descriptions | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/summarize_descriptions), to count calls by workflow step; requests are otherwise identical |
| community_reports.completion_model_id | default_completion_model | completion_community_reports | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/community_reports), to count calls by workflow step; requests are otherwise identical |
| local_search.completion_model_id | default_completion_model | completion_local_search | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/local_search), to count calls by workflow step; requests are otherwise identical |
| global_search.completion_model_id | default_completion_model | completion_global_search | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/global_search), to count calls by workflow step; requests are otherwise identical |
| concurrent_requests | 25 | 3 | the adapter's concurrency cap (3), so GraphRAG does not flood it |
| input/ (input_storage.base_dir, input.type text) | (empty folder) | the entry's exported papers, one <pmid>.txt per paper | the corpus: exactly the supplied papers; GraphRAG's text reader titles each document by its file name, which maps it back to the PubMed id |
| environment | (inherited) | fresh environment: no proxy variables, no provider keys; LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=data/cache/tiktoken | telemetry off, nothing reaches an outside service; tiktoken encodings filled once beforehand |
| vector_store.vector_size (effective; not set by us) | 3072 | 384 | a consequence of the embedding model, not a change in settings.yaml: the package's own validate_config detects the model's 384-dimensional vectors and overrides vector_size (logged as a warning) |

##### GraphRAG global on its own entries

Role: GraphRAG global search on the same indexes. Entries attempted: 4; completed: 4.

| Measure | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 46.0% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 47.7% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 68.2% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 20.5% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 67.4% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 21.5% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 61.0% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 62.3% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | GraphRAG global | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -13.6 (-27.1 to -5.4); 0/4/0; p=0.125; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -13.8 (-27.8 to -2.9); 0/4/0; p=0.125; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -20.6 (-33.9 to -7.3); 0/4/0; p=0.125; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | +17.5 (+0.4 to +50.2); 3/0/1; p=0.250; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -23.0 (-40.8 to -5.2); 0/4/0; p=0.125; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | +16.9 (+0.0 to +50.0); 2/0/2; p=0.500; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (a) on facts the supplied text states or partly states | -22.2 (-37.8 to -9.4); 0/4/0; p=0.125; n=4 | -0.2 (-2.9 to +2.4); 2/2/0; p=1.000; n=4 | +2.3 (-4.5 to +9.4); 2/1/1; p=1.000; n=4 | -2.8 (-7.0 to +2.2); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text states or partly states | -22.6 (-39.0 to -6.1); 0/4/0; p=0.125; n=4 | -0.2 (-3.2 to +2.8); 2/2/0; p=1.000; n=4 | +1.2 (-7.3 to +9.4); 2/1/1; p=1.000; n=4 | -5.5 (-8.7 to -0.8); 1/3/0; p=0.625; n=4 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| GraphRAG global | 63,752 | 13.7% | 165.2 | 1,288,343 | 289,518 | $12.14 | 2,844 | 1,328 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG global: share of characters by kind of mapping: sources 0.0%, entities/relationships only 0.0%, community reports only 86.3%, none 13.7%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

Settings changed from the defaults of graphrag 3.3.0:

The same table as GraphRAG local.

##### STORM on its own entries

Role: no article produced. Entries attempted: 10; completed: 0; stopped: 10.

Requests per entry: 5.0 distinct (50 fresh in all), $0.07 at list price.

Settings changed from the defaults of knowledge-storm 1.1.1:

| Setting | Default | Value | Reason |
|---|---|---|---|
| LM, all five roles (conv_simulator_lm, question_asker_lm, outline_gen_lm, article_gen_lm, article_polish_lm) | STORMWikiLMConfigs.init_openai_model: LitellmModel gpt-4o-mini-2024-07-18 (conversation, question asking), gpt-4-0125-preview (outline), gpt-4o-2024-05-13 (article, polish) | LitellmModel openai/claude-opus-5-5, api_base = local adapter, api_key = dummy | the local adapter in front of the project's one model (Claude Opus 5.5, effort medium) |
| LM temperature / top_p / max_tokens | temperature 1.0, top_p 0.9; max_tokens 500 / 500 / 400 / 700 / 4000 per role | sent unchanged, but ignored by the adapter (the command-line model takes no sampling or length parameters; replies are not cut at max_tokens) | the adapter cannot pass them to the model; recorded, not chosen |
| LM request timeout | LiteLLM default (600 s) | 1800 s | adapter calls queue behind a concurrency cap of 3 and can take minutes; the harness asks for >= 900 s |
| retriever (rm) | a web search API (YouRM / BingSearch / ... in the examples) | VectorRM over the entry's supplied papers only (offline Qdrant on disk), k = search_top_k = 3 | the papers may not go to an outside service; the corpus is exactly the supplied papers |
| VectorRM corpus CSV | user supplied (content, title, url, description) | one row per supplied paper: content = the exported <pmid>.txt (reference line, title, abstract, full text as the entry's access level allows); title = paper title; url = https://pubmed.ncbi.nlm.nih.gov/<pmid>/ (identifier only, never fetched); description = the reference line | the corpus is exactly the supplied papers; the url identifies the PubMed id for citation mapping |
| VectorRM / QdrantVectorStoreManager embedding_model | BAAI/bge-m3 (1024 dims) | BAAI/bge-small-en-v1.5 (384 dims), loaded locally by the package's own HuggingFaceEmbeddings | the small local embedding model used by all three systems |
| VectorRM / QdrantVectorStoreManager device | mps | cpu | no Apple GPU (or any GPU) on this machine |
| Qdrant collection vector size | 1024 (hard-coded in QdrantVectorStoreManager._check_create_collection) | 384: the collection is created with this size before the package's own builder is called (the builder then loads it instead of creating it) | a hard-coded 1024 cannot hold 384-dimensional vectors; smallest change |
| qdrant_client.Document | `from qdrant_client import Document` in QdrantVectorStoreManager.create_or_update_vector_store (fails: qdrant-client has no such name in any release checked, 1.7-1.20) | the name is set to langchain_core.documents.Document (the class the code uses: page_content, metadata, split by the LangChain text splitter) before the builder is called | the released corpus builder cannot run otherwise; smallest change, no behaviour added |
| dependency versions (unpinned by knowledge-storm 1.1.1) | whatever the resolver picks: uv picked sentence-transformers 2.2.2 + transformers 4.17.0 (fails to import: huggingface_hub has no cached_download) and qdrant-client 1.20.0 (no QdrantClient.search, which langchain_qdrant.Qdrant, used by VectorRM, calls) | sentence-transformers 5.7.0 (newest), transformers 4.57.6; qdrant-client 1.15.1 (newest release with QdrantClient.search); torch 2.15.0+cpu | the newest versions with which the released VectorRM path imports and runs |
| telemetry / outside calls | LiteLLM telemetry off (set by the package); cost map local (set by the package); Hugging Face hub online | also LITELLM_TELEMETRY=False, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1, ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1; models fetched once beforehand; no other provider key in the environment | nothing but the adapter and the Wikipedia pages of the perspective step may be reached |
| LiteLLM disk cache location | ~/.storm_local_cache | HOME set to runs/external/storm/_home, so the cache is runs/external/storm/_home/.storm_local_cache | keep the run's files inside the run folder; caching behaviour unchanged |

##### Claim-level audit without repair (4 common entries)

Systems: paragraphs with mapped citations, audited here. Comparison strategies: the stored audit of their drafts before their repair round (run omim100), on the same entries.

| Arm | Paragraphs | Claims | Supported | Partly supported | Unsupported | Contradicted | Not checkable |
|---|---|---|---|---|---|---|---|
| PaperQA2 | 128 | 853 | 780 (91.4%) | 66 (7.7%) | 2 (0.2%) | 5 (0.6%) | 0 (0.0%) |
| GraphRAG local | 283 | 1382 | 1241 (89.8%) | 107 (7.7%) | 33 (2.4%) | 1 (0.1%) | 0 (0.0%) |
| Direct reading | 87 | 581 | 571 (98.3%) | 10 (1.7%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Agentic curator | 92 | 644 | 635 (98.6%) | 9 (1.4%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Evidence graph | 127 | 770 | 746 (96.9%) | 21 (2.7%) | 3 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| Case table first | 125 | 866 | 836 (96.5%) | 29 (3.4%) | 1 (0.1%) | 0 (0.0%) | 0 (0.0%) |

##### Deviations from the design

1. Reduced sizes (decided before any run finished, at the project owner's request): PaperQA2 and STORM on the first 10 entries of the seeded order instead of 24; GraphRAG within 1,000 model calls (floor 6 entries) instead of 3,000 (floor 12). Every result here is exploratory.
2. PaperQA2 was run without its agent: `Docs.aadd` per paper and `Docs.aquery` per question (the README's 'Manual (No Agent)' usage) instead of the default `agent_query` (`pqa ask`). The default agent selects tools by function calling, and the 'fake' agent ends with a function-calling Complete step; the adapter in front of the project's command-line model cannot serve tool calls. Retrieval, contextual summaries and the answer step are PaperQA2's own; the agent's iterative search and its decision to stop are not exercised.
3. Embedding cut and re-run: the shared local embedder (bge-small-en-v1.5) truncates at 512 tokens, so the first PaperQA2 run (`paperqa`) embedded only the first ~510 tokens of each ~5,000-character chunk. PaperQA2 was re-run with whole-chunk embeddings (windows of 510 tokens averaged; `paperqa_pooled`), which is reported as the main result; the first run is kept as a sensitivity result. Requests identical between the two runs were served from the cache in the second, so its fresh calls understate what a stand-alone run costs (calls here count every distinct request once, wherever it was first made).
4. GraphRAG on 4 entries (621313, 615582, 616326, 620029), below the design's floor of 6: the fixed in-order rule stopped when the fifth entry (611521) did not fit in what was left of the 1,000-call cap (the operator's projection; the tally in the ledgers is 698 calls, including the global-search queries and a smoke test).
5. GraphRAG global search was added on the same 4 indexes (the CLI default is local search, which is the main GraphRAG result). Its citations name community reports only; a report is mapped to the papers of the text units its community's entities came from, a looser mapping than PaperQA2's (named papers) or local search's (text units, entities, relationships; a block's papers are the union over every record it cites, counting only records the query showed the model).
6. STORM did not complete any entry: the model's safety filter stopped every chain-of-thought prompt of its research stage (30 of 30 fresh requests stopped; the 20 plain outline prompts were answered), so no article was produced. Per the rules, nothing was retried or reworded. STORM is reported as completion 0 of 10.
7. The comparison strategies' drafts (run omim100) are the published drafts, after their one audit-and-repair round; the systems' drafts had none. The design treats every arm alike without repair; the repair round moved coverage by about 0.2 points in the hidden-full-text experiment, so this favours the comparison strategies very slightly at most. Their (a) and (c) come from stored marks; (b) from stored whole-draft marks where present, otherwise scored here once (the same path).
8. Bookkeeping corrected in this summary: calls, tokens and cost count each distinct request once with the figures it had when made (the ledgers' `full_*` totals count cached re-runs again; PaperQA2's first-run entry 621313 was re-saved from the cache twice, tripling its `full_*` figures); the saved `seconds` of that entry (6.9 s) is a cached re-save and its real wall time (177.2 s) is taken from `runs/external/paperqa/pilot.log`; GraphRAG local's query seconds are the sum of per-question seconds in `meta` (no query-run record), added to the recorded index time. PaperQA2 (whole-chunk) entries 301059 and 621313 were served entirely from the cache (all requests identical to the first run) and have no wall time of their own; its other entries' wall times understate a stand-alone run for the same reason.
9. Wall-clock time is not recorded per strategy in run omim100 (only per entry for all strategies together); for the comparison strategies, time is the sum of model-call seconds (`model_seconds`), which is also given for the systems. Systems ran with the adapter's concurrency cap of 3; the comparison strategies' generation is mostly one or a few calls.
10. Systems were asked six fixed section questions (PaperQA2, GraphRAG) and their answers concatenated; the comparison strategies write an OMIM-style entry in one pass. GraphRAG's answers include headings and framing lines as separate blocks; all text counts for (b) and the uncited share.
11. The claim-level audit without repair was run on the 4 entries both PaperQA2 and GraphRAG completed, not on every entry of each system, on every paragraph with mapped citations.
12. Judge noise: (b) credits facts anywhere in the draft and should not fall below (a), but it does on 5 system entries (paperqa/620029, paperqa/620249, graphrag/620029, graphrag_global/616326, graphrag_global/621313): the two are separate judge passes, so differences of a few points between them are within the judge's noise.
13. Extent of the comparison strategies' repair round on these 10 entries (paragraphs revised / deleted / in the final drafts): Direct reading 3 / 0 / 234; Agentic curator 2 / 0 / 240; Evidence graph 5 / 0 / 317; Case table first 1 / 0 / 291.

### 14.4 Audit coverage: planted errors beyond single values (C)

From `results/omim100/audit_stress.md`.

#### Audit coverage: planted errors beyond single values (Experiment C, run omim100)

Planted in the 'kg' drafts; natural omissions from the 'direct' drafts. Seed 23, replicate salt 'auditstress-1'. Pool of passed single-paper paragraphs: 1494.

##### Audit on planted errors

| Class | Items | Truth known | Paragraph flagged | Planted claim flagged | Control paragraph flagged | Control planted-claim analogue flagged |
|---|---|---|---|---|---|---|
| C1 citation swap, other entry | 30 | 30 | 30/30 (100%) | 30/30 (100%) | 0/30 (0%) | 0/30 (0%) |
| C2 citation swap, same entry | 30 | 26 | 26/26 (100%) | 26/26 (100%) | 0/26 (0%) | 0/26 (0%) |
| C3 conflation | 30 | 25 | 25/25 (100%) | 25/25 (100%) | 0/25 (0%) | 0/25 (0%) |
| C4 over-citation | 30 | 30 | 0/30 (0%) | 0/30 (0%) | 0/30 (0%) | 0/30 (0%) |
| C5 dropped qualifier | 30 | 30 | 11/30 (37%) | 11/30 (37%) | 0/30 (0%) | 0/30 (0%) |
| C6 omitted finding | 30 | 30 | 0/30 (0%) | 0/0 (n/a) | 0/30 (0%) | 0/0 (n/a) |

Counts are over truth-known items. 'Planted claim flagged': at least one planted claim unsupported or contradicted, over items where a planted claim was identified. C4's expected outcome is a pass (the claim takes the best cited paper's verdict); C6's is a pass (the audit judges only what is written).

- C2 truth unknown (variant occurs in the new paper's text): 4 items, paragraph flagged 4, planted-claim-analogue flagged 0/0.
- C3 truth unknown (variant occurs in the new paper's text): 5 items, paragraph flagged 5, planted-claim-analogue flagged 4/5.

###### Verdict on the planted claim (worst planted claim per item, truth-known items)

| Class | contradicted | unsupported | partially supported | supported | not checkable |
|---|---|---|---|---|---|
| C1 | 5 | 25 | 0 | 0 | 0 |
| C2 | 10 | 16 | 0 | 0 | 0 |
| C3 | 2 | 23 | 0 | 0 | 0 |
| C4 | 0 | 0 | 1 | 29 | 0 |
| C5 | 11 | 0 | 4 | 15 | 0 |
| C6 | 0 | 0 | 0 | 0 | 0 |

Claim level (C1, C4: every claim is planted):

- C1: 173 of 173 claims flagged (100%).
- C4: 0 of 178 claims flagged (0%).

###### C4: the added paper's own verdicts

Of 178 claims, the decomposer attributed 176 to the added paper. Its own verdicts: not_attributed 2, unsupported 176. Share judged supported or partly by the added (unrelated) paper: 0%; flagged: 100%.

###### C5 by deletion rule

| Rule | Items | Paragraph flagged | Planted claim flagged | Worst verdict |
|---|---|---|---|---|
| count | 4 | 1 | 1/4 | contradicted 1, partially_supported 1, supported 2 |
| hedge | 8 | 2 | 2/8 | contradicted 2, partially_supported 2, supported 4 |
| negation | 8 | 8 | 8/8 | contradicted 8 |
| single family or patient | 2 | 0 | 0/2 | supported 2 |
| zygosity | 8 | 0 | 0/8 | partially_supported 1, supported 7 |

###### Control (all unaltered paragraphs, re-audited fresh)

113 paragraphs, 0 flagged (0%); 733 claims, 0 flagged (0.0), 15 partly supported.

##### C6 completeness check

###### Planted deletions

| | Items | Omissions listed (mean / median) | Deleted sentence listed: mechanical | judge full | judge full or partial |
|---|---|---|---|---|---|
| Sentence deleted | 30 | 6.03 / 5 | 22/29 (76%) | 16/29 (55%) | 24/29 (83%) |
| Unaltered (false-alarm side) | 30 | 5.59 / 3 | 4/29 (14%) | 0/29 (0%) | 2/29 (7%) |

Quotes verified: 175 of 175 omissions (deleted), 162 of 162 (unaltered). Judge full matches with a verified quote: 16 (deleted), 0 (unaltered).

###### Natural omissions (direct-reading drafts)

28 papers (0 failed), 60 curator facts stated in the text the writer had but absent from the draft. Listed by the check (judge 'states it'): 24 (40%); including 'states part': 28 (47%); with a verified quote: 24 (40%).

Omissions listed: 284 (10.14 per paper; 284 with a verified quote). Matching any curator fact about the paper: 56 (20%); including partial matches 83 (29%).

##### Citation precision (stored audits, no new calls)

Paragraphs citing two or more papers; each (claim, paper the claim is attributed to) pair's own verdict.

| Strategy | Entries replayed | Multi-citation paragraphs (replayed / all) | Pairs | Not supported | Supported or partly | Claims passing with a non-supporting cited paper |
|---|---|---|---|---|---|---|
| kg | 80 | 209 / 272 | 1438 | 6% | 94% | 76 of 991 |
| direct | 84 | 338 / 442 | 2493 | 7% | 93% | 142 of 1782 |
| agent | 87 | 335 / 400 | 2262 | 4% | 96% | 78 of 1772 |
| cohort | 78 | 242 / 306 | 1846 | 7% | 93% | 118 of 1254 |
| recall | 88 | 137 / 165 | 830 | 3% | 97% | 25 of 708 |
| closedbook | 100 | 39 / 39 | 166 | 27% | 73% | 17 of 121 |

##### Calls and cost

New model calls: 540 (cap 600); safety-filter stops: 2; refusals raised: 0; failed calls: 0; list-price cost $43.7849.

##### Decisions

- Strategy planted in: the evidence-graph drafts ('kg') of run omim100, as the single-value planted test, with its selection rule (paragraphs passed as fully supported, citing one paper, longer than 150 characters); at most 3 items per entry per class. One seeded order of that pool serves all classes, so classes share paragraphs and one control audit of the union of their unaltered paragraphs serves every class.
- C3 is planted in the same 'kg' drafts, not the direct-reading drafts: its truth (the moved variant does not occur in paper B's text) is decided mechanically from the paper text, so it needs no stored omission judgement, and keeping one strategy keeps the classes comparable. The moved sentence names a variant and carries no author citation (so it is not explicitly attributed to paper A); it is inserted at a seeded sentence boundary after B's first sentence; B must not already name that variant.
- C6's planted deletions are in the 'kg' drafts; C6's natural omissions use the direct-reading drafts ('direct'), where the stored judgements are: curator facts of gold paragraphs citing one paper, marked absent from the draft and stated (verdict 'yes', quote verified) in the text the writer had. Facts marked partly conveyed or partly stated are not targets.
- Citation swaps (C1, C2) and over-citation (C4) change the in-text author-year label as well as the cited PMID (only paragraphs whose label occurs in the text are used): 'A et al. (2000)' -> 'B et al. (2010)' for swaps, 'A et al. (2000) and B et al. (2010)' or '(A et al., 2000; B et al., 2010)' for over-citation. The new paper of C1 and C4 is a random readable paper (abstract or full text) of another entry; of C2 a random readable other paper of the same entry.
- Variant occurrence (C2, C3) is decided on the text the auditor reads (title, abstract and full text cut at 180,000 characters). A variant occurs if any of its protein or nucleotide keys (kg.protein_key / nucleotide_key, so one- and three-letter, 'arg123-to-trp', p. and c. forms meet), its residue or nucleotide position, or its raw name occurs in the paper. C2 items are truth-known when the paragraph names at least one variant that does not occur in the new paper; C3 items when none of the moved sentence's variants occurs in B.
- Planted claim: C1 and C4 every claim; C2 claims naming a variant absent from the new paper; C3 claims naming the moved variant; C5 claims taken from the altered sentence (at least 60% of a claim's content words in the sentence, or at least two of the content words next to the deletion point, else the best-overlapping claim); C6 none. An item counts as 'planted claim flagged' when any planted claim is unsupported or contradicted. Control analogue: the same rule on the unaltered paragraph (for C3, the moved sentence's claims in paper A's own paragraph, against paper A).
- C6 deleted sentence: not the first sentence, carrying a variant or a number (years and MIM numbers aside) that appears nowhere else in the draft's text citing that paper. Mechanical match: a listed omission names one of the sentence's variants (by key) or carries all its numbers (number words read as digits). Judge match: stage 'judge'. The draft text given to the check is all paragraphs of the entry citing the paper (as in scoring).
- The audit is run on items in fixed chunks of 5 (one claim-decomposition call per chunk, then one call per cited paper), not on one 60-paragraph holder as the single-value test did (decomposition batches of 25); this lets the pilot's calls be reused and the run resume. All calls are made under the replicate salt 'auditstress-1', so altered and control audits are fresh and from the same run.
- Per-paper verdicts are kept by `auditstress.audit_paragraphs`, which runs the audit's own prompts and best-verdict rule (verify._decompose, verify._audit_prompt); a unit test checks it agrees with verify.verify_entry.
- Citation precision: the run's entry files keep only each claim's best verdict, not every paper's. Per-paper verdicts were recovered by replaying the stored audit from the model-reply cache with a backend that refuses any uncached call (no new calls). That is possible only for entries the repair round left unchanged; entries with a revised or deleted paragraph are excluded, and a paragraph is kept only if the replayed best verdict of every claim equals the stored one.

##### Pilot review

- Pilot: 5 items of each class, 20 controls, 5 C6 completeness items, 5 natural papers: 94 calls; estimate for the full run about 555 calls (under the 600 cap), so 30 per class were kept.
- C5 rules were tightened once before the pilot after reading the built edits (no calls involved): zygosity no longer deletes before 'for'/'in ... state' (left no sentence), counts must end in a people noun or a clause boundary, sentence-initial 'In 2 of 5' is not taken, 'more/less likely' and 'likely to/than' are not taken, 'as in one patient' is not taken.
- All 30 C5 edits were then read. hedge (8): 5 change the claim (e.g. 'possibly transient' -> 'transient', 'likely pathogenic' -> 'pathogenic'), 2 are nearly meaning-preserving because the sentence still reads 'suggested that', 1 degenerate ('pathogenic or likely pathogenic' -> 'pathogenic or pathogenic'). negation (8): all grammatical, all reverse the claim (so they plant contradictions, not broadening). zygosity (8): all grammatical; about 3 nearly meaning-preserving where de novo or dominant inheritance implies heterozygosity. count (4): 2 clean, 1 ungrammatical ('Variants were familial in which inheritance could be determined'), 1 awkward. single family/patient (2): both clean. No rule mostly produced ungrammatical or meaning-preserving edits, so all five survive.
- C6 mechanical matching was corrected after the pilot (no new calls; recomputed at summary time): number words and thousands separators are read as digits, and a listed omission matches on all the sentence's numbers even when the sentence also names a variant (variant names written with a hyphen, 'p.P102-V104del', do not parse as keys).
- After the main run, the C5 planted-claim selector was widened (no new calls; recomputed at summary time): a claim also counts as taken from the altered sentence when it contains two of the content words next to the deletion point. Two flagged negation items (C5.5, C5.18) had been missed by the overlap rule alone because the decomposer had added context words to the claim.

##### Deviations from the design

- Size: 30 items per class instead of the design's 'about 60', and at most 600 new model calls instead of 1,200 (pilot included), at the user's request for a smaller budget. Items were built and run as 30 per class from the start (seeded order).
- Natural omissions capped at 60 curator facts (seeded sample, facts of papers readable in full taken first): 60 of the 130 eligible facts, on 28 papers. The design did not set a cap.
- Audit grouping: items are audited in fixed chunks of 5 (one claim-decomposition call per chunk), where the single-value test audited all 60 in one holder (decomposition batches of 25). Prompts and verdict rules are otherwise the audit's own.
- Citation precision could not be read from 'the existing audit files': the entry files keep only each claim's best verdict. Per-paper verdicts were recovered without new calls by replaying the audit from the model-reply cache, which is possible only for entries whose paragraphs the repair round left unchanged (about 80-88% of entries per strategy; all closed-book entries, which have no repair).
- Unaltered controls are one audit of the union of all classes' unaltered paragraphs (113 paragraphs), not a separate control per class; each class's control figures are read from it for that class's own paragraphs.
- Papers are loaded at the access level the run recorded, from cached responses only (no new fetches); every paper's access level matched papers.json.
- Safety-filter stops: 2, both on the completeness check of item C6.24 (the altered and the unaltered draft text of the same paper). Recorded, not retried; C6 completeness figures are over 29 items.

## 15. Improving on direct reading (20 November 2026)

Ten approaches were reviewed (`docs/direct-improvements.md`, evidence in `docs/direct-improvements-evidence.md`);
the three judged most likely to help at feasible cost were implemented, piloted on three training entries with the
prompts then frozen, and evaluated on the 41 entries of the held-out test split that have at least one paper
readable in full; a fourth arm combining the first two was designed and run afterwards (the "Extension" below).
Arms: D1, direct reading with a curator checklist in the house style (what a curator records about each paper);
D2, a completeness pass (for each paper, a check listing findings the paper states that the draft omits, each with a
quote verified in the paper, then one revision adding only those); D3, three direct-reading drafts merged keeping
every distinct statement; D4, the checklist draft followed by the completeness pass. No repair round for any arm; the
baseline is direct reading's draft before repair. Claim-level audit without repair on a seeded sample of 20 of the
41 entries. The approach with the largest expected effect, reading papers that are free to read but not openly
licensed (about a third of all curator facts concern such papers), could not be tested under the project's access
rules. After the evaluation, D4 was adopted as the pipeline's default way of writing an entry where a paper is
readable in full; that is a project decision, not a result. The result file is reproduced below with its headings
lowered. Code names: `direct` direct reading; `direct_checklist` D1; `direct_complete` D2; `direct_ensemble` D3;
`direct_checklist_complete` D4.

The analysis that chose the arms, copied from `docs/direct-improvements.md` (its sections "Where direct reading loses facts", "Ten approaches" and "Ranking and choice", headings lowered; its figures come from the stored files of the main run, no new model calls; expected effects in the ranking are estimates, not measurements).

### Where direct reading loses facts

All figures are for direct reading on the main set, scored against the fixed fact lists, from files already in
`results/` and `runs/` (no new model calls).

1. **What was not in the text it was given.** Of 6,498 curator facts (97 entries), 40% are not stated in the text the
   model had (gap analysis, log section 3). On facts the supplied text states, direct reading conveys 94.4% (mean over
   entries; 97.1% for abstract-only papers, 88.5% for full-text papers), and on facts it does not state, 6.9%
   (log 2.10a). Hiding the full text of the same papers costs 43.7 points (log 6.2).
2. **Free to read but not openly licensed.** Europe PMC lists a free-to-read copy (in PMC outside the open-access
   subset, at the publisher, or through Unpaywall) for 130 of the 342 abstract-only papers and 30 of the 74 title-only
   papers. The curator paragraphs about those papers hold 2,223 of the 6,498 facts (34%), of which direct reading now
   conveys 36.8%. Were they read at the coverage the hidden-full-text experiment shows for full text, coverage would
   rise by about 15 points (pooled; a rough projection). The pipeline cannot fetch them: PMC and Europe PMC permit bulk
   retrieval only of the open-access subset, the publisher sites refuse this environment, and the services that
   locate legal copies (Unpaywall, OpenAlex) now require an e-mail address or a key.
3. **What was in the text and was missed.** 291 facts are stated in full in the supplied text and were missed or
   conveyed in part (245 of them in full-text papers, where 49% of missed facts were in the text), and 210 more are
   partly stated and were missed entirely. Conveying all of them would add about 3.5 points, and about 5 with the
   partly stated ones: the ceiling for any change to how the papers are read. The kinds of fact most often missed
   although stated are functional studies and model organisms, population controls, counts of patients and families,
   zygosity, ancestry and consanguinity, and age, sex and onset (keyword classes; a fact can fall in several).
4. **Run-to-run variation.** On the 30 replicate entries, single direct-reading runs convey 44.7–45.9%; the union of
   the facts conveyed by any of three runs is 48.7% (two runs: 47.5%). This is an upper bound for a sampling ensemble
   with a perfect merge, and it includes judge variation.

So the largest lever is access, which cannot be pulled here; among changes to how the supplied text is read, the
ceiling is about 3.5–5 points overall and larger on entries with full text.

### Ten approaches

| # | Approach | What it targets | Added calls per entry |
|---|---|---|---|
| 1 | Expanded legal access (OA copies elsewhere, institutional access, user-supplied text) | facts not in the supplied text (item 2) | none to write; retrieval only |
| 2 | Supplementary material (variant and patient tables) | variant facts held only in supplements | 0 to write; parsing |
| 3 | Completeness pass: per-paper omission check, then revision | stated facts missed (item 3) | about one per paper plus one |
| 4 | Long-context layout: papers first, instructions last, quotes extracted before writing | attention over long input | 0 |
| 5 | Curator checklist: the fields a curator records about each paper | the missed kinds in item 3 | 0 |
| 6 | Per-paper writing, then assembly (map, then reduce) | attention per paper | about one per paper plus one |
| 7 | Sampling ensemble with a merge | run-to-run variation (item 4) | two to four |
| 8 | More reasoning effort for the writer | depth of reading | 0 (longer calls) |
| 9 | Few-shot examples of curated paragraphs | granularity of what is recorded | 0 |
| 10 | Second-hand descriptions from citing papers | unreadable papers | retrieval; tested before (+0.8, not distinguishable from zero) |

Ranking and choice: below, after the evidence review.

### Ranking and choice

From the evidence review (expected effects are estimates, not measurements):

| Rank | Approach | Expected effect on facts conveyed | Decision |
|---|---|---|---|
| 1 | Expanded legal access | large (up to about +12–15 points) | not testable here: the copies cannot be fetched under the terms the project keeps to (see above); needs a licence review and either institutional access or a key for a service that locates legal copies; the pipeline already reads text a user supplies for papers they have the right to read |
| 2 | Curator checklist in the prompt | small (+0.5–2), at no added call | **tested (D1)** |
| 3 | Completeness pass, then revision | small (+1–2), one call per paper plus one | **tested (D2)** |
| 4 | Second-hand descriptions | small; already measured (+1.8 on 96 entries, with more unsupported claims) | not repeated |
| 5 | Sampling ensemble with a merge | small to moderate (+1.5–2.5; oracle ceiling +3.3) | **tested (D3)** |
| 6 | Per-paper writing, then assembly | none to small; measured as the matched evidence graph (+1.8) | not repeated |
| 7–10 | Layout and quotes first; more effort; few-shot examples; question-driven filling | none to small | not tested |

The three tested approaches act on different causes of a miss: D1 on what the writer thinks a curator records, D2 on
attention to each paper, D3 on which facts a single run happens to pick.

From `results/direct_improve/direct_improve.md`.

### Improving on direct reading: evaluation (run `direct_improve`)

41 entries with at least one paper readable in full and a direct-reading draft; 38 complete for every arm are compared. No repair round for any arm. Facts conveyed = (present + half of partial) / judged frozen facts, mean over entries. Differences are arm minus baseline in percentage points with a 95% percentile bootstrap interval over entries (10,000 resamples, seed 7), entries better/worse/tied, exact sign test, Holm-adjusted across the three arms. Whether the supplied text states a fact is the stored availability judgement (a model judgement with verified quotes, not checked by a curator).

#### Completion

| Arm | Complete | Incomplete | No draft | Not run | Entries not complete |
|---|---|---|---|---|---|
| Baseline (direct, before repair) | 41 | 0 | 0 | 0 | – |
| D1 checklist | 41 | 0 | 0 | 0 | – |
| D2 completeness pass | 38 | 0 | 3 | 0 | 118210 (no_draft), 617232 (no_draft), 621030 (no_draft) |
| D3 three-draft merge | 41 | 0 | 0 | 0 | – |

#### All facts

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 60.3% | 38 | 80.7 | – | – | – | – | – |
| D1 checklist | 61.9% | 38 | 80.7 | +1.6 | +0.5 to +2.7 | 23/11/4 | 0.058 | 0.058 |
| D2 completeness pass | 62.9% | 38 | 80.7 | +2.6 | +1.7 to +3.6 | 28/4/6 | 0.000 | 0.000 |
| D3 three-draft merge | 63.4% | 38 | 80.7 | +3.1 | +2.1 to +4.2 | 31/3/4 | 0.000 | 0.000 |

#### Facts the supplied text states

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.3% | 38 | 40.2 | – | – | – | – | – |
| D1 checklist | 92.7% | 38 | 40.2 | +1.4 | +0.0 to +2.7 | 17/9/12 | 0.169 | 0.169 |
| D2 completeness pass | 94.7% | 38 | 40.2 | +3.4 | +2.1 to +4.8 | 24/3/11 | 0.000 | 0.000 |
| D3 three-draft merge | 94.2% | 38 | 40.2 | +2.9 | +1.7 to +4.2 | 23/1/14 | 0.000 | 0.000 |

#### … on papers readable in full

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.5% | 34 | 28.0 | – | – | – | – | – |
| D1 checklist | 90.5% | 34 | 28.0 | +2.0 | +0.4 to +3.7 | 16/7/11 | 0.093 | 0.093 |
| D2 completeness pass | 93.0% | 34 | 28.0 | +4.5 | +2.9 to +6.3 | 22/1/11 | 0.000 | 0.000 |
| D3 three-draft merge | 92.1% | 34 | 28.0 | +3.7 | +2.1 to +5.5 | 23/3/8 | 0.000 | 0.000 |

#### … on papers readable as abstract only

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | 11.9 | – | – | – | – | – |
| D1 checklist | 97.0% | 31 | 11.9 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 | 1.000 |
| D2 completeness pass | 97.8% | 31 | 11.9 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | 11.9 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 | 0.867 |

#### Facts the supplied text does not state

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 10.5% | 36 | 25.5 | – | – | – | – | – |
| D1 checklist | 10.2% | 36 | 25.5 | -0.3 | -1.9 to +1.3 | 11/9/16 | 0.824 | 1.000 |
| D2 completeness pass | 10.3% | 36 | 25.5 | -0.1 | -1.3 to +0.7 | 6/3/27 | 0.508 | 1.000 |
| D3 three-draft merge | 12.0% | 36 | 25.5 | +1.5 | +0.4 to +2.7 | 17/2/17 | 0.001 | 0.002 |

#### Claims judged by the audit (20 audited entries)

Audited entries (random.Random(20261120).sample(sorted(entries), 20)): 604928, 606763, 607602, 607734, 607876, 608133, 611521, 614651, 614856, 615710, 617927, 618400, 618808, 618875, 619201, 620022, 620029, 620098, 620481, 620662. Shares are over checkable claims; a stopped audit call leaves its paper's claims not checkable and does not affect completion.

| Arm | Entries | Checkable claims | Supported | Partly | Unsupported | Contradicted | Not checkable | Entries with not-checkable claims |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 20 | 2,578 | 2,501 (97.0%) | 71 (2.8%) | 6 (0.2%) | 0 (0.0%) | 67 | 615710 |
| D1 checklist | 20 | 2,969 | 2,889 (97.3%) | 70 (2.4%) | 8 (0.3%) | 2 (0.1%) | 87 | 615710 |
| D2 completeness pass | 20 | 3,278 | 3,185 (97.2%) | 89 (2.7%) | 4 (0.1%) | 0 (0.0%) | 85 | 615710 |
| D3 three-draft merge | 20 | 3,225 | 3,091 (95.8%) | 116 (3.6%) | 14 (0.4%) | 4 (0.1%) | 106 | 615710 |

#### Size, variants, calls and price

| Arm | Characters per entry | Checkable claims per audited entry | Variant recall (entries) | Variant precision (entries) | New calls per entry (generate / audit / score) | List price per entry, new | List price per entry, method | Wall minutes per entry |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 10,802 | 129 | 82.6% (38) | 87.1% (38) | 0.2 (0.0 / 0.0 / 0.2) | $0.01 | $1.09 | 0.4 |
| D1 checklist | 11,837 | 148 | 81.7% (38) | 87.5% (38) | 10.1 (1.8 / 2.9 / 5.5) | $1.14 | $1.15 | 2.6 |
| D2 completeness pass | 14,412 | 164 | 82.6% (38) | 87.1% (38) | 12.9 (6.1 / 2.9 / 3.9) | $1.62 | $2.10 | 3.1 |
| D3 three-draft merge | 14,245 | 161 | 82.2% (38) | 83.4% (38) | 11.9 (3.5 / 2.8 / 5.6) | $1.82 | $2.32 | 3.8 |

Characters and variants are over the compared entries; calls and price over every entry the arm ran. 'New' counts calls made in this run (the baseline's draft and audit come from the cache); 'method' is what the arm costs from scratch, including the cached baseline draft that D2 and D3 start from.

#### Stops

- Baseline (direct, before repair): no draft 0; safety stops by step {'audit': 1}
- D1 checklist: no draft 0; safety stops by step {'audit': 1}
- D2 completeness pass: no draft 3 (118210, 617232, 621030); safety stops by step {'generate': 3, 'audit': 1}
- D3 three-draft merge: no draft 0; safety stops by step {'audit': 1}

#### D2: what the completeness pass did

Entries 38; omissions listed 768, kept (quote verified) 767; revision called on 38; sentences added 959, of which citing only papers without listed omissions 0; entries where the model changed a carried-over field: none; citations lost: none.

#### D3: what the merge did

Entries 41; draft paragraphs 2,486 merged into 852 (807 from more than one draft); rejected as longer than their sources 0; unknown IDs 0; unsourced paragraphs dropped 0; draft paragraphs left out and put back 0, left out and not put back (their papers cited elsewhere) 0; variant groups restored 0; citations lost: none. Sentences of each draft with at least 85% of their content words in the merged draft (rough): A 3,454 of 3,550; B 3,401 of 3,556; C 3,324 of 3,479.

Calls: 1,624 new model calls of the 2,200 cap (pilot included), $217.54 list price; safety stops 7, refusals 0, errors 1.

---

### Extension: D4, the checklist draft with the completeness pass

Designed after the first four arms were run (docs/direct-improvements.md, 'Extension: checklist and completeness pass together (D4)'). D4 starts from D1's checklist draft (from the cache) and applies D2's completeness pass. The first four arms are not re-run; the sections above are unchanged. Comparisons use the 35 entries complete for all five arms (the symmetric rule). Primary: D4 minus the baseline; secondary: D4 minus D2 and D4 minus D1. Differences in percentage points with a 95% percentile bootstrap interval over entries (seed 7, 10,000 resamples), better/worse/tied and an exact sign test, unadjusted.

#### Completion, all five arms

| Arm | Complete | Incomplete | No draft | Not run | Entries not complete |
|---|---|---|---|---|---|
| Baseline (direct, before repair) | 41 | 0 | 0 | 0 | – |
| D1 checklist | 41 | 0 | 0 | 0 | – |
| D2 completeness pass | 38 | 0 | 3 | 0 | 118210 (no_draft), 617232 (no_draft), 621030 (no_draft) |
| D3 three-draft merge | 41 | 0 | 0 | 0 | – |
| D4 checklist + completeness pass | 35 | 2 | 4 | 0 | 118210 (no_draft), 613744 (incomplete), 615817 (incomplete), 617232 (no_draft), 620249 (no_draft), 621030 (no_draft) |

#### D4: All facts

Means over the compared entries: Baseline (direct, before repair) 60.1%; D1 checklist 61.8%; D2 completeness pass 62.6%; D3 three-draft merge 63.2%; D4 checklist + completeness pass 63.4%.

| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|
| D4 − baseline (primary) | 35 | +3.3 | +2.0 to +4.7 | 27/6/2 | 0.000 |
| D4 − D2 (secondary) | 35 | +0.8 | -0.4 to +1.8 | 19/10/6 | 0.136 |
| D4 − D1 (secondary) | 35 | +1.6 | +0.7 to +2.5 | 27/6/2 | 0.000 |

#### D4: Facts the supplied text states

Means over the compared entries: Baseline (direct, before repair) 91.1%; D1 checklist 92.6%; D2 completeness pass 94.4%; D3 three-draft merge 94.1%; D4 checklist + completeness pass 95.6%.

| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|
| D4 − baseline (primary) | 35 | +4.6 | +2.6 to +6.6 | 24/4/7 | 0.000 |
| D4 − D2 (secondary) | 35 | +1.2 | -0.2 to +2.6 | 18/9/8 | 0.122 |
| D4 − D1 (secondary) | 35 | +3.0 | +1.7 to +4.6 | 22/2/11 | 0.000 |

#### D4: … on papers readable in full

Means over the compared entries: Baseline (direct, before repair) 88.4%; D1 checklist 90.6%; D2 completeness pass 92.8%; D3 three-draft merge 92.2%; D4 checklist + completeness pass 94.7%.

| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|
| D4 − baseline (primary) | 32 | +6.3 | +4.0 to +8.7 | 23/4/5 | 0.000 |
| D4 − D2 (secondary) | 32 | +1.8 | +0.1 to +3.7 | 16/9/7 | 0.230 |
| D4 − D1 (secondary) | 32 | +4.1 | +2.2 to +6.2 | 21/3/8 | 0.000 |

#### D4: … on papers readable as abstract only

Means over the compared entries: Baseline (direct, before repair) 96.5%; D1 checklist 96.7%; D2 completeness pass 97.6%; D3 three-draft merge 97.6%; D4 checklist + completeness pass 98.0%.

| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|
| D4 − baseline (primary) | 28 | +1.5 | -0.6 to +3.9 | 7/3/18 | 0.344 |
| D4 − D2 (secondary) | 28 | +0.4 | -0.9 to +1.5 | 7/4/17 | 0.549 |
| D4 − D1 (secondary) | 28 | +1.3 | -0.3 to +3.5 | 5/2/21 | 0.453 |

#### D4: Facts the supplied text does not state

Means over the compared entries: Baseline (direct, before repair) 9.8%; D1 checklist 9.6%; D2 completeness pass 9.7%; D3 three-draft merge 11.2%; D4 checklist + completeness pass 10.1%.

| Comparison | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|
| D4 − baseline (primary) | 33 | +0.2 | -1.2 to +1.8 | 10/8/15 | 0.815 |
| D4 − D2 (secondary) | 33 | +0.4 | -1.3 to +2.3 | 11/10/12 | 1.000 |
| D4 − D1 (secondary) | 33 | +0.4 | -0.7 to +1.8 | 5/7/21 | 0.774 |

#### D4: claims judged by the audit (20 audited entries, as above)

| Arm | Entries | Checkable claims | Supported | Partly | Unsupported | Contradicted | Not checkable |
|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 20 | 2,578 | 2,501 (97.0%) | 71 (2.8%) | 6 (0.2%) | 0 (0.0%) | 67 |
| D1 checklist | 20 | 2,969 | 2,889 (97.3%) | 70 (2.4%) | 8 (0.3%) | 2 (0.1%) | 87 |
| D2 completeness pass | 20 | 3,278 | 3,185 (97.2%) | 89 (2.7%) | 4 (0.1%) | 0 (0.0%) | 85 |
| D3 three-draft merge | 20 | 3,225 | 3,091 (95.8%) | 116 (3.6%) | 14 (0.4%) | 4 (0.1%) | 106 |
| D4 checklist + completeness pass | 20 | 3,217 | 3,126 (97.2%) | 81 (2.5%) | 9 (0.3%) | 1 (0.0%) | 182 |

#### D4: size, variants, calls and price

| Arm | Characters per entry | Checkable claims per audited entry | Variant recall | Variant precision | New calls per entry | List price per entry, new | List price per entry, method |
|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 10,826 | 129 | 82.7% | 85.9% | 0.2 | $0.01 | $1.09 |
| D1 checklist | 11,927 | 148 | 81.8% | 86.5% | 10.1 | $1.14 | $1.15 |
| D2 completeness pass | 14,357 | 164 | 82.7% | 85.9% | 12.9 | $1.62 | $2.10 |
| D3 three-draft merge | 14,309 | 161 | 82.2% | 82.0% | 11.9 | $1.82 | $2.32 |
| D4 checklist + completeness pass | 14,963 | 161 | 81.8% | 86.5% | 12.5 | $1.61 | $2.11 |

#### D4 and D2: omissions listed and added

On the 37 entries where both wrote a draft: omissions listed D4 600 vs D2 736; kept (quote verified) D4 600 vs D2 735 (D4 fewer on 27 entries, more on 6, equal on 4); sentences added by the revision D4 730 vs D2 908; existing sentences completed D4 118 vs D2 126. D4 sentences added that cite only papers without listed omissions: 0; entries where the model changed a carried-over field: none; citations lost: none.

#### D4: stops and calls

No draft: 118210 (the model's safety filter stopped this reply), 617232 (the model's safety filter stopped this reply), 620249 (the model's safety filter stopped this reply), 621030 (the model's safety filter stopped this reply). Completeness checks failed: {'613744': {'30127434': "stopped: LLMRefusal: the model's safety filter stopped this reply"}, '615817': {'33749590': "stopped: LLMRefusal: the model's safety filter stopped this reply"}}. Safety stops by step: {'generate': 6, 'audit': 2}.
D4 calls in the ledger (pilot included): 572 of its 700 cap, $74.53 list price; safety stops 9, refusals 0, errors 0.

### 15.1 Sensitivity: every entry, stopped entries put back

Added after the paper's first review round (not in the evaluation design; stored scores only, no new model calls).
The comparison above uses only the entries complete for every arm, as the design specified; this one keeps all 41
entries and puts back the entries the completeness-pass arms lost to a stopped revision, in two ways. The result file
is reproduced below with its headings lowered (its title dropped).

From `results/direct_improve/sensitivity.md`.

All 41 entries of the run (the baseline completed every one). Two rules for an entry an arm lost to a stopped reply: counted as zero (as in the main comparison's sensitivity analysis), or, for the completeness-pass arms, the draft the revision would have revised is scored in its place (the baseline's draft for D2, D1's checklist draft for D4; the same text, taken from the cache). The second is what the adopted `recommended` strategy does when its revision is stopped. Incomplete drafts (a stopped check on one paper) are kept as scored under both rules. Differences are arm minus baseline in percentage points, mean over entries, 95% percentile bootstrap interval (10,000 resamples, seed 7), entries better / worse / tied, exact sign test, unadjusted. Stored scores only; no model call.

Entries lost to a stopped reply: D2 completeness pass 3 (118210, 617232, 621030); D4 checklist + completeness pass 4 (118210, 617232, 620249, 621030).
Incomplete, kept as scored: D4 checklist + completeness pass 2 (613744, 615817).

#### All facts

##### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 61.9% | 41 | – | – | – | – |
| D1 checklist | 63.6% | 41 | +1.7 | +0.7 to +2.8 | 26/11/4 | 0.020 |
| D2 completeness pass | 58.3% | 41 | -3.5 | -11.1 to +2.6 | 28/7/6 | <0.001 |
| D3 three-draft merge | 64.9% | 41 | +3.0 | +2.1 to +4.1 | 34/3/4 | <0.001 |
| D4 checklist + completeness pass | 57.0% | 41 | -4.8 | -13.2 to +1.9 | 28/11/2 | 0.009 |

##### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 61.9% | 41 | – | – | – | – |
| D1 checklist | 63.6% | 41 | +1.7 | +0.7 to +2.8 | 26/11/4 | 0.020 |
| D2 completeness pass | 64.3% | 41 | +2.4 | +1.5 to +3.4 | 28/4/9 | <0.001 |
| D3 three-draft merge | 64.9% | 41 | +3.0 | +2.1 to +4.1 | 34/3/4 | <0.001 |
| D4 checklist + completeness pass | 64.9% | 41 | +3.1 | +1.8 to +4.3 | 32/7/2 | <0.001 |

#### Facts the supplied text states

##### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.0% | 41 | – | – | – | – |
| D1 checklist | 92.5% | 41 | +1.5 | +0.2 to +2.7 | 20/9/12 | 0.061 |
| D2 completeness pass | 87.7% | 41 | -3.3 | -11.5 to +3.4 | 24/6/11 | 0.001 |
| D3 three-draft merge | 94.0% | 41 | +2.9 | +1.8 to +4.2 | 26/1/14 | <0.001 |
| D4 checklist + completeness pass | 86.1% | 41 | -4.9 | -14.8 to +3.0 | 24/8/9 | 0.007 |

##### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.0% | 41 | – | – | – | – |
| D1 checklist | 92.5% | 41 | +1.5 | +0.2 to +2.7 | 20/9/12 | 0.061 |
| D2 completeness pass | 94.2% | 41 | +3.1 | +1.9 to +4.5 | 24/3/14 | <0.001 |
| D3 three-draft merge | 94.0% | 41 | +2.9 | +1.8 to +4.2 | 26/1/14 | <0.001 |
| D4 checklist + completeness pass | 95.1% | 41 | +4.1 | +2.3 to +5.9 | 27/5/9 | <0.001 |

#### … on papers readable in full

##### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.4% | 37 | – | – | – | – |
| D1 checklist | 90.5% | 37 | +2.1 | +0.6 to +3.6 | 19/7/11 | 0.029 |
| D2 completeness pass | 85.5% | 37 | -3.0 | -12.4 to +4.4 | 22/4/11 | <0.001 |
| D3 three-draft merge | 92.1% | 37 | +3.6 | +2.1 to +5.3 | 26/3/8 | <0.001 |
| D4 checklist + completeness pass | 84.1% | 37 | -4.3 | -15.4 to +4.7 | 23/8/6 | 0.011 |

##### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.4% | 37 | – | – | – | – |
| D1 checklist | 90.5% | 37 | +2.1 | +0.6 to +3.6 | 19/7/11 | 0.029 |
| D2 completeness pass | 92.6% | 37 | +4.2 | +2.6 to +5.8 | 22/1/14 | <0.001 |
| D3 three-draft merge | 92.1% | 37 | +3.6 | +2.1 to +5.3 | 26/3/8 | <0.001 |
| D4 checklist + completeness pass | 94.0% | 37 | +5.6 | +3.5 to +7.8 | 26/5/6 | <0.001 |

#### … on papers readable as abstract only

##### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | – | – | – | – |
| D1 checklist | 97.0% | 31 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 |
| D2 completeness pass | 97.8% | 31 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 |
| D4 checklist + completeness pass | 94.9% | 31 | -1.9 | -9.4 to +3.0 | 7/4/20 | 0.549 |

##### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | – | – | – | – |
| D1 checklist | 97.0% | 31 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 |
| D2 completeness pass | 97.8% | 31 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 |
| D4 checklist + completeness pass | 98.2% | 31 | +1.3 | -0.5 to +3.5 | 7/3/21 | 0.344 |

#### Facts the supplied text does not state

##### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 11.6% | 38 | – | – | – | – |
| D1 checklist | 11.3% | 38 | -0.2 | -1.8 to +1.3 | 11/9/18 | 0.824 |
| D2 completeness pass | 9.8% | 38 | -1.8 | -5.6 to +0.5 | 6/4/28 | 0.754 |
| D3 three-draft merge | 13.0% | 38 | +1.4 | +0.4 to +2.6 | 17/2/19 | <0.001 |
| D4 checklist + completeness pass | 9.7% | 38 | -1.9 | -5.9 to +0.9 | 11/11/16 | 1.000 |

##### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 11.6% | 38 | – | – | – | – |
| D1 checklist | 11.3% | 38 | -0.2 | -1.8 to +1.3 | 11/9/18 | 0.824 |
| D2 completeness pass | 11.4% | 38 | -0.1 | -1.3 to +0.7 | 6/3/29 | 0.508 |
| D3 three-draft merge | 13.0% | 38 | +1.4 | +0.4 to +2.6 | 17/2/19 | <0.001 |
| D4 checklist + completeness pass | 11.6% | 38 | +0.0 | -1.3 to +1.4 | 11/10/17 | 1.000 |
