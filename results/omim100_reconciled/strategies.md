# Generation strategies compared — run `omim100_reconciled`

97 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 97 of the run's 100 entries qualify; left out: 300148, 617232, 621068. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Case table first | 97 | 3: 300148 (1 paper), 617232 (2 papers), 621068 (1 paper) | 0 |
| Reconciled case database | 97 | 3: 300148 (1 paper), 617232 (2 papers), 621068 (1 paper) | 0 |

For the reconciled case database the failed papers are read from the case table's record of the same entry (both run the same cached case extraction; drafts written before the reconciled strategy recorded them itself): 300148, 617232, 621068.

## How the scores are counted

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Case table first: genes 2, variants 5; Reconciled case database: genes 2, variants 5.

- **n.** A value rests on all 97 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.
- **Reconciled case database** (`reconciled`): The case table after merging the same patient, family or variant across papers and settling conflicts.

## Scores

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.7% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% |
| … same, before the repair round ↓ | 0.4% | 0.5% |
| … unsupported, before the repair round ↓ | 0.4% | 0.5% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 50.1% | 50.2% |
| … fully (no partial credit) ↑ | 42.0% | 42.3% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 34.1% | 34.1% |
| … precision ↑ | 40.8% | 40.8% |
| … recall ↑ | 37.6% | 37.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.1% | 54.1% |
| Clinical synopsis HPO F1, semantic ↑ | 64.7% | 64.7% |
| OMIM allelic variants recovered ↑ | 64.9% | 65.0% |
| Generated variants that are OMIM variants (precision) ↑ | 72.8% (n=92) | 73.7% (n=92) |
| Causal gene F1 ↑ | 94.2% | 94.2% |
| … recall ↑ | 94.3% | 94.3% |
| Inheritance matches OMIM ↑ | 91.8% | 91.8% |
| Inheritance error: none stated ↓ | 2.1% | 2.1% |
| Inheritance error: a mode missing ↓ | 1.0% | 1.0% |
| Inheritance error: an extra mode ↓ | 4.1% | 4.1% |
| Inheritance error: a different mode ↓ | 1.0% | 1.0% |
| OMIM references used ↑ | 94.7% | 94.3% |

## How much each strategy writes

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims audited per entry | 117.8 | 117.2 |
| Claims that could not be audited per entry | 2.1 | 3.3 |
| Clinical-synopsis HPO terms per entry | 21.2 | 21.1 |
| Allelic variants per entry | 4.1 | 4.1 |
| … of which not in OMIM | 1.4 | 1.4 |
| Papers cited per entry | 4.9 | 4.9 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Case table first)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Reconciled case database |
|---|---|
| Claims supported by cited paper ↑ | +0.0 (-0.4 to +0.4); 14/13/70 |
| … same, before the repair round ↓ | +0.1 (-0.1 to +0.2); 4/12/81 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.1 (-0.2 to +0.3); 15/9/73 |
| OMIM per-paper facts contradicted ↓ | +0.0 (-0.0 to +0.1); 3/4/90 |
| Clinical synopsis HPO F1, exact ↑ | -0.1 (-0.4 to +0.3); 6/5/86 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.0 (-0.0 to +0.1); 2/1/94 |
| OMIM allelic variants recovered ↑ | +0.1 (+0.0 to +0.3); 1/0/96 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/97 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/97 |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Reconciled case database minus Case table first

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 97 | 50.2% | 50.1% | +0.1 | -0.2 to +0.3 | +0.0 | 15 / 9 / 73 | 0.307 | – |
| Claims supported by cited paper (headline) ↑ | 97 | 94.7% | 94.7% | +0.0 | -0.4 to +0.4 | +0.0 | 14 / 13 / 70 | 1.000 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 97 | 0.5% | 0.4% | +0.1 | -0.1 to +0.2 | +0.0 | 4 / 12 / 81 | 0.077 | 0.461 |
| OMIM per-paper facts contradicted (headline) ↓ | 97 | 0.7% | 0.7% | +0.0 | -0.0 to +0.1 | +0.0 | 3 / 4 / 90 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 97 | 34.1% | 34.1% | -0.1 | -0.4 to +0.3 | +0.0 | 6 / 5 / 86 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 97 | 54.1% | 54.1% | +0.0 | -0.0 to +0.1 | +0.0 | 2 / 1 / 94 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 97 | 65.0% | 64.9% | +0.1 | +0.0 to +0.3 | +0.0 | 1 / 0 / 96 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 97 | 94.2% | 94.2% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Inheritance matches OMIM (headline) ↑ | 97 | 91.8% | 91.8% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Claims unsupported or contradicted ↓ | 97 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 1 / 96 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 97 | 0.5% | 0.4% | +0.1 | -0.1 to +0.2 | +0.0 | 3 / 11 / 83 | 0.057 | – |
| Claims contradicted, before the repair round ↓ | 97 | 0.0% | 0.0% | +0.0 | -0.0 to +0.0 | +0.0 | 1 / 1 / 95 | 1.000 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 97 | 42.3% | 42.0% | +0.3 | -0.0 to +0.8 | +0.0 | 16 / 6 / 75 | 0.052 | – |
| Clinical synopsis HPO precision, exact ↑ | 97 | 40.8% | 40.8% | +0.0 | -0.3 to +0.3 | +0.0 | 6 / 4 / 87 | 0.754 | – |
| Clinical synopsis HPO recall, exact ↑ | 97 | 37.4% | 37.6% | -0.2 | -0.6 to +0.1 | +0.0 | 1 / 4 / 92 | 0.375 | – |
| Clinical synopsis HPO F1, semantic ↑ | 97 | 64.7% | 64.7% | +0.0 | -0.1 to +0.2 | +0.0 | 4 / 7 / 86 | 0.549 | – |
| Generated variants that are OMIM variants (precision) ↑ | 92 | 73.7% | 72.8% | +0.8 | -0.3 to +2.3 | +0.0 | 3 / 2 / 87 | 1.000 | – |
| Causal gene recall ↑ | 97 | 94.3% | 94.3% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Inheritance error: none stated ↓ | 97 | 2.1% | 2.1% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Inheritance error: a mode missing ↓ | 97 | 1.0% | 1.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Inheritance error: an extra mode ↓ | 97 | 4.1% | 4.1% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| Inheritance error: a different mode ↓ | 97 | 1.0% | 1.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 97 | – | – |
| OMIM references used ↑ | 97 | 94.3% | 94.7% | -0.3 | -0.8 to +0.0 | +0.0 | 0 / 2 / 95 | 0.500 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 100 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: none.

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.5% (n=99) | 94.5% (n=99) |
| … same, before the repair round ↓ | 0.8% (n=99) | 0.8% (n=99) |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 49.0% | 49.1% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.3% | 33.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.9% | 53.0% |
| OMIM allelic variants recovered ↑ | 63.5% | 63.6% |
| Causal gene F1 ↑ | 92.3% | 92.3% |
| Inheritance matches OMIM ↑ | 90.0% | 90.0% |

Paired differences from Case table first over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Reconciled case database |
|---|---|
| Claims supported by cited paper ↑ | +0.0 (-0.4 to +0.4); median +0.0; 14/14/71; p 1.000 (n=99) |
| … same, before the repair round ↓ | +0.1 (-0.1 to +0.2); median +0.0; 4/13/82; p 0.049 (n=99) |
| OMIM per-paper facts conveyed (primary) ↑ | +0.1 (-0.2 to +0.3); median +0.0; 15/9/76; p 0.307 |
| OMIM per-paper facts contradicted ↓ | +0.0 (-0.0 to +0.1); median +0.0; 4/4/92; p 1.000 |
| Clinical synopsis HPO F1, exact ↑ | -0.1 (-0.4 to +0.3); median +0.0; 6/5/89; p 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.0 (-0.0 to +0.1); median +0.0; 2/1/97; p 1.000 |
| OMIM allelic variants recovered ↑ | +0.1 (+0.0 to +0.3); median +0.0; 1/0/99; p 1.000 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); median +0.0; 0/0/100; p – |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); median +0.0; 0/0/100; p – |

## Pooled counts

| | Case table first | Reconciled case database |
|---|---|---|
| Claims audited | 11,427 | 11,371 |
| … supported | 10,953 | 10,904 |
| … partly supported | 474 | 466 |
| … unsupported | 0 | 1 |
| … contradicted | 0 | 0 |
| Claims audited before repair | 11,384 | 11,340 |
| … unsupported before repair | 25 | 32 |
| … contradicted before repair | 4 | 4 |
| OMIM facts scored | 5,514 | 5,517 |
| … conveyed | 2,260 | 2,284 |
| … partly conveyed | 876 | 859 |
| … missing | 2,342 | 2,337 |
| … contradicted | 36 | 37 |

## Allelic variants: precision and variants not in OMIM

| | Case table first | Reconciled case database |
|---|---|---|
| Variants generated | 396 | 395 |
| … matching an OMIM variant of the entry | 258 | 259 |
| … listed by OMIM only from a paper outside the entry's references | 1 | 1 |
| … not in OMIM | 137 | 135 |
| Pooled precision (entries where OMIM lists variants) | 65.1% | 65.6% |

## Inheritance errors by kind

| | Case table first | Reconciled case database |
|---|---|---|
| Entries with an OMIM mode of inheritance | 97 | 97 |
| … matched | 89 | 89 |
| … none stated | 2 | 2 |
| … a mode missing | 1 | 1 |
| … an extra mode | 4 | 4 |
| … a different mode | 1 | 1 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Case table first | Reconciled case database |
|---|---|---|
| fulltext | 72.3% (1,435) | 72.8% (1,444) |
| abstract | 42.3% (3,713) | 42.4% (3,711) |
| title | 24.4% (366) | 24.3% (362) |

### Difference from Case table first, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies. Facts are split from the gold paragraph separately for each draft, so the fact counts differ slightly.

| Paper readable as | Reconciled case database |
|---|---|
| fulltext | +0.5 (+0.0 to +1.0); n=43 |
| abstract | +0.1 (-0.3 to +0.5); n=88 |
| title | -0.1 (-0.4 to +0.2); n=22 |

## Paired differences from Case table first within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Reconciled case database |
|---|---|---|
| no full text (abstracts only) | 46 | -0.2 (-0.6 to +0.2); n=46 |
| under half full text | 27 | +0.4 (-0.2 to +0.9); n=27 |
| half or more full text | 22 | +0.3 (-0.0 to +0.7); n=22 |
| all full text | 2 | +0.0 †; n=2 |

### OMIM allelic variants recovered

| Access group | Entries | Reconciled case database |
|---|---|---|
| no full text (abstracts only) | 46 | +0.0 (+0.0 to +0.0); n=46 |
| under half full text | 27 | +0.0 (+0.0 to +0.0); n=27 |
| half or more full text | 22 | +0.4 (+0.0 to +1.2); n=22 |
| all full text | 2 | +0.0 †; n=2 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Case table first

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 81.6% (38 facts, 2 entries) | 74.7% (186 facts, 10 entries) | 71.5% (418 facts, 11 entries) | 66.9% (406 facts, 10 entries) | 76.6% (387 facts, 10 entries) |
| abstract | 39.3% (900 facts, 19 entries) | 50.9% (616 facts, 20 entries) | 40.7% (917 facts, 18 entries) | 43.2% (731 facts, 15 entries) | 39.3% (549 facts, 16 entries) |
| title | 26.9% (39 facts, 3 entries) | 31.5% (81 facts, 5 entries) | 27.8% (54 facts, 4 entries) | 21.9% (73 facts, 5 entries) | 18.9% (119 facts, 5 entries) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 93.7% | 93.7% |
| … same, before the repair round ↓ | 0.5% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 40.0% | 39.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 29.9% | 29.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.1% | 49.1% |
| OMIM allelic variants recovered ↑ | 47.8% | 47.8% |
| Causal gene F1 ↑ | 87.7% | 87.7% |
| Inheritance matches OMIM ↑ | 87.0% | 87.0% |

### under half full text — 27 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.2% | 95.0% |
| … same, before the repair round ↓ | 0.5% | 0.7% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.6% | 51.9% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.5% | 35.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.2% | 58.2% |
| OMIM allelic variants recovered ↑ | 73.2% | 73.2% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 92.6% | 92.6% |

### half or more full text — 22 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 96.3% | 96.5% |
| … same, before the repair round ↓ | 0.2% | 0.3% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 66.2% | 66.5% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 39.5% | 39.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.8% | 58.0% |
| OMIM allelic variants recovered ↑ | 87.3% | 87.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### all full text — 2 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.7% |
| … same, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 87.4% | 87.4% |
| OMIM per-paper facts contradicted ↓ | 8.3% | 8.3% |
| Clinical synopsis HPO F1, exact ↑ | 51.9% | 51.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 72.0% | 72.0% |
| OMIM allelic variants recovered ↑ | 100.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 53 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.1% | 94.3% |
| … same, before the repair round ↓ | 0.5% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.4% | 51.3% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.9% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.4% | 53.5% |
| OMIM allelic variants recovered ↑ | 65.5% | 65.5% |
| Causal gene F1 ↑ | 94.3% | 94.3% |
| Inheritance matches OMIM ↑ | 94.3% | 94.3% |

### 5-8 references — 27 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.5% | 95.2% |
| … same, before the repair round ↓ | 0.3% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 48.0% | 48.0% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 32.4% | 32.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.2% | 54.2% |
| OMIM allelic variants recovered ↑ | 61.4% | 61.7% |
| Causal gene F1 ↑ | 98.8% | 98.8% |
| Inheritance matches OMIM ↑ | 85.2% | 85.2% |

### 9 or more references — 17 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.3% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 49.7% | 50.2% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 37.5% | 37.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.9% | 55.9% |
| OMIM allelic variants recovered ↑ | 68.3% | 68.3% |
| Causal gene F1 ↑ | 86.3% | 86.3% |
| Inheritance matches OMIM ↑ | 94.1% | 94.1% |

## By creation era (MIM number range)

### 600000-609999 — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 92.7% | 92.9% |
| … same, before the repair round ↓ | 0.4% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.6% | 53.7% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 37.9% | 37.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 60.2% | 60.2% |
| OMIM allelic variants recovered ↑ | 68.2% | 68.2% |
| Causal gene F1 ↑ | 90.0% | 90.0% |
| Inheritance matches OMIM ↑ | 90.0% | 90.0% |

### 610000-615999 — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.3% | 94.7% |
| … same, before the repair round ↓ | 0.7% | 0.6% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.2% | 51.7% |
| OMIM per-paper facts contradicted ↓ | 1.3% | 1.3% |
| Clinical synopsis HPO F1, exact ↑ | 33.8% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.5% | 49.4% |
| OMIM allelic variants recovered ↑ | 70.3% | 70.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### 616000-619999 — 19 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.5% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.4% | 51.4% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 32.3% | 31.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.4% | 52.4% |
| OMIM allelic variants recovered ↑ | 77.5% | 77.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 89.5% | 89.5% |

### 620000 onward — 19 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.9% |
| … same, before the repair round ↓ | 0.1% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.9% | 52.9% |
| OMIM per-paper facts contradicted ↓ | 0.1% | 0.1% |
| Clinical synopsis HPO F1, exact ↑ | 35.2% | 35.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.6% | 54.8% |
| OMIM allelic variants recovered ↑ | 67.9% | 67.9% |
| Causal gene F1 ↑ | 94.7% | 94.7% |
| Inheritance matches OMIM ↑ | 94.7% | 94.7% |

### classic (1xxxxx-5xxxxx) — 19 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.8% |
| … same, before the repair round ↓ | 0.4% | 0.7% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 41.2% | 41.0% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 31.2% | 31.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.7% | 53.7% |
| OMIM allelic variants recovered ↑ | 40.0% | 40.0% |
| Causal gene F1 ↑ | 86.0% | 86.0% |
| Inheritance matches OMIM ↑ | 84.2% | 84.2% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Case table first | Reconciled case database |
|---|---|---|
| Generation: model calls | 7.0 | 8.4 |
| Generation: list price | $0.63 | $0.73 |
| Generation: input / output tokens | 64,481 / 17,320 | 74,888 / 18,969 |
| Generation: model time (s) | 144 | 163 |
| Audit and repair: list price | $0.81 | $0.83 |
| Scoring against OMIM: list price | $0.20 | $0.20 |
| Everything: list price | $1.64 | $1.76 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Case table first | 97 | 102 | 105 | 95.1% | 92.4% | 93.7% |
| Disease → causal gene | Reconciled case database | 97 | 102 | 105 | 95.1% | 92.4% | 93.7% |
| Disease → mode of inheritance | Case table first | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → mode of inheritance | Reconciled case database | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → phenotype (HPO, exact id) | Case table first | 750 | 2,139 | 2,311 | 35.1% | 32.5% | 33.7% |
| Disease → phenotype (HPO, exact id) | Reconciled case database | 746 | 2,127 | 2,311 | 35.1% | 32.3% | 33.6% |
| Disease → allelic variant | Case table first | 262 | 399 | 428 | 65.7% | 61.2% | 63.4% |
| Disease → allelic variant | Reconciled case database | 263 | 398 | 428 | 66.1% | 61.5% | 63.7% |
