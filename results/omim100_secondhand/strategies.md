# Generation strategies compared — run `omim100_secondhand`

96 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

No draft: 4 entries for which at least one strategy wrote nothing, because the model's safety filter stopped the writer's reply or the reply came back empty (Second-hand evidence 4; Direct reading 3). Entries: 278750, 609296, 620609, 621068. They are left out of the comparison with the incomplete entries listed under Completion.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 96 of the run's 100 entries qualify; left out: 278750, 609296, 620609, 621068. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Direct reading | 97 | 0 | 3: 609296, 620609, 621068 |
| Second-hand evidence | 96 | 0 | 4: 278750, 609296, 620609, 621068 |

## How the scores are counted

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Direct reading: genes 1, variants 11; Second-hand evidence: genes 1, variants 7.

- **n.** A value rests on all 96 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Second-hand evidence** (`secondhand`): Direct reading; a paper not readable in full is supplemented with what later open-access papers say it reported.

## Scores

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 94.4% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.2% |
| … same, before the repair round ↓ | 0.4% | 3.9% |
| … unsupported, before the repair round ↓ | 0.4% | 3.9% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.2% | 54.0% |
| … fully (no partial credit) ↑ | 44.8% | 46.3% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.9% | 37.0% |
| … precision ↑ | 43.7% | 43.2% |
| … recall ↑ | 36.2% | 37.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.7% | 58.9% |
| Clinical synopsis HPO F1, semantic ↑ | 66.5% | 68.7% |
| OMIM allelic variants recovered ↑ | 68.2% | 73.2% |
| Generated variants that are OMIM variants (precision) ↑ | 88.4% (n=85) | 86.8% (n=89) |
| Causal gene F1 ↑ | 97.6% | 97.6% |
| … recall ↑ | 97.4% | 97.4% |
| Inheritance matches OMIM ↑ | 93.8% | 95.8% |
| Inheritance error: none stated ↓ | 2.1% | 1.0% |
| Inheritance error: a mode missing ↓ | 0.0% | 0.0% |
| Inheritance error: an extra mode ↓ | 4.2% | 3.1% |
| Inheritance error: a different mode ↓ | 0.0% | 0.0% |
| OMIM references used ↑ | 94.6% | 94.5% |

## How much each strategy writes

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims audited per entry | 103.6 | 107.9 |
| Claims that could not be audited per entry | 1.3 | 3.0 |
| Clinical-synopsis HPO terms per entry | 15.8 | 16.4 |
| Allelic variants per entry | 3.2 | 3.4 |
| … of which not in OMIM | 0.4 | 0.4 |
| Papers cited per entry | 4.8 | 4.9 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Second-hand evidence |
|---|---|
| Claims supported by cited paper ↑ | -1.8 (-2.9 to -0.8); 31/60/5 |
| … same, before the repair round ↓ | +3.6 (+2.2 to +5.1); 8/51/37 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.8 (-0.2 to +1.9); 50/41/5 |
| OMIM per-paper facts contradicted ↓ | +0.4 (+0.1 to +0.9); 9/19/68 |
| Clinical synopsis HPO F1, exact ↑ | +1.1 (-0.7 to +3.0); 42/36/18 |
| Clinical synopsis HPO F1, hierarchical ↑ | +2.2 (+0.4 to +4.3); 50/36/10 |
| OMIM allelic variants recovered ↑ | +5.0 (+1.3 to +9.2); 13/2/81 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/96 |
| Inheritance matches OMIM ↑ | +2.1 (+0.0 to +5.2); 2/0/94 |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Second-hand evidence minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 96 | 54.0% | 53.2% | +0.8 | -0.2 to +1.9 | +0.5 | 50 / 41 / 5 | 0.402 | – |
| Claims supported by cited paper (headline) ↑ | 96 | 94.4% | 96.2% | -1.8 | -2.9 to -0.8 | -0.8 | 31 / 60 / 5 | 0.003 | 0.019 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 96 | 3.9% | 0.4% | +3.6 | +2.2 to +5.1 | +0.9 | 8 / 51 / 37 | <0.001 | <0.001 |
| OMIM per-paper facts contradicted (headline) ↓ | 96 | 1.0% | 0.5% | +0.4 | +0.1 to +0.9 | +0.0 | 9 / 19 / 68 | 0.087 | 0.349 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 96 | 37.0% | 35.9% | +1.1 | -0.7 to +3.0 | +0.0 | 42 / 36 / 18 | 0.572 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 96 | 58.9% | 56.7% | +2.2 | +0.4 to +4.3 | +0.4 | 50 / 36 / 10 | 0.161 | 0.482 |
| OMIM allelic variants recovered (headline) ↑ | 96 | 73.2% | 68.2% | +5.0 | +1.3 to +9.2 | +0.0 | 13 / 2 / 81 | 0.007 | 0.037 |
| Causal gene F1 (headline) ↑ | 96 | 97.6% | 97.6% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 96 | – | – |
| Inheritance matches OMIM (headline) ↑ | 96 | 95.8% | 93.8% | +2.1 | +0.0 to +5.2 | +0.0 | 2 / 0 / 94 | 0.500 | 1.000 |
| Claims unsupported or contradicted ↓ | 96 | 0.2% | 0.0% | +0.2 | +0.1 to +0.3 | +0.0 | 0 / 9 / 87 | 0.004 | – |
| Claims unsupported, before the repair round ↓ | 96 | 3.9% | 0.4% | +3.6 | +2.2 to +5.1 | +0.9 | 8 / 50 / 38 | <0.001 | – |
| Claims contradicted, before the repair round ↓ | 96 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 1 / 95 | 1.000 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 96 | 46.3% | 44.8% | +1.4 | +0.2 to +2.7 | +0.2 | 48 / 42 / 6 | 0.598 | – |
| Clinical synopsis HPO precision, exact ↑ | 96 | 43.2% | 43.7% | -0.5 | -3.3 to +2.2 | +0.0 | 37 / 41 / 18 | 0.734 | – |
| Clinical synopsis HPO recall, exact ↑ | 96 | 37.5% | 36.2% | +1.3 | -0.7 to +3.4 | +0.0 | 33 / 21 / 42 | 0.134 | – |
| Clinical synopsis HPO F1, semantic ↑ | 96 | 68.7% | 66.5% | +2.1 | +0.4 to +4.1 | +0.1 | 48 / 41 / 7 | 0.525 | – |
| Generated variants that are OMIM variants (precision) ↑ | 85 | 88.5% | 88.4% | +0.1 | -2.3 to +3.3 | +0.0 | 4 / 4 / 77 | 1.000 | – |
| Causal gene recall ↑ | 96 | 97.4% | 97.4% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 96 | – | – |
| Inheritance error: none stated ↓ | 96 | 1.0% | 2.1% | -1.0 | -3.1 to +0.0 | +0.0 | 1 / 0 / 95 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 96 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 96 | – | – |
| Inheritance error: an extra mode ↓ | 96 | 3.1% | 4.2% | -1.0 | -3.1 to +0.0 | +0.0 | 1 / 0 / 95 | 1.000 | – |
| Inheritance error: a different mode ↓ | 96 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 96 | – | – |
| OMIM references used ↑ | 96 | 94.5% | 94.6% | -0.0 | -2.0 to +1.9 | +0.0 | 4 / 4 / 88 | 1.000 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 100 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Direct reading 3; Second-hand evidence 4.

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 93.2% | 90.6% |
| … same, before the repair round ↓ | 0.4% (n=97) | 3.9% (n=96) |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.3% | 51.8% |
| OMIM per-paper facts contradicted ↓ | 0.5% (n=97) | 1.0% (n=96) |
| Clinical synopsis HPO F1, exact ↑ | 34.6% | 35.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.6% | 56.6% |
| OMIM allelic variants recovered ↑ | 65.6% | 70.2% |
| Causal gene F1 ↑ | 94.7% | 93.7% |
| Inheritance matches OMIM ↑ | 91.0% | 92.0% |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Second-hand evidence |
|---|---|
| Claims supported by cited paper ↑ | -2.6 (-4.9 to -1.0); median -0.7; 31/61/8; p 0.002 |
| … same, before the repair round ↓ | +3.6 (+2.2 to +5.1); median +0.9; 8/51/37; p <0.001 (n=96) |
| OMIM per-paper facts conveyed (primary) ↑ | +0.5 (-0.7 to +1.7); median +0.1; 50/42/8; p 0.466 |
| OMIM per-paper facts contradicted ↓ | +0.4 (+0.1 to +0.9); median +0.0; 9/19/68; p 0.087 (n=96) |
| Clinical synopsis HPO F1, exact ↑ | +0.9 (-0.8 to +2.8); median +0.0; 42/37/21; p 0.653 |
| Clinical synopsis HPO F1, hierarchical ↑ | +1.9 (+0.2 to +4.0); median +0.2; 50/37/13; p 0.198 |
| OMIM allelic variants recovered ↑ | +4.6 (+1.0 to +8.7); median +0.0; 13/3/84; p 0.021 |
| Causal gene F1 ↑ | -1.0 (-3.0 to +0.0); median +0.0; 0/1/99; p 1.000 |
| Inheritance matches OMIM ↑ | +1.0 (-2.0 to +5.0); median +0.0; 2/1/97; p 1.000 |

## Pooled counts

| | Direct reading | Second-hand evidence |
|---|---|---|
| Claims audited | 9,943 | 10,357 |
| … supported | 9,614 | 9,913 |
| … partly supported | 329 | 431 |
| … unsupported | 0 | 13 |
| … contradicted | 0 | 0 |
| Claims audited before repair | 9,919 | 10,766 |
| … unsupported before repair | 22 | 305 |
| … contradicted before repair | 0 | 1 |
| OMIM facts scored | 5,462 | 5,453 |
| … conveyed | 2,421 | 2,484 |
| … partly conveyed | 912 | 849 |
| … missing | 2,093 | 2,074 |
| … contradicted | 36 | 46 |

## Allelic variants: precision and variants not in OMIM

| | Direct reading | Second-hand evidence |
|---|---|---|
| Variants generated | 312 | 328 |
| … matching an OMIM variant of the entry | 271 | 285 |
| … listed by OMIM only from a paper outside the entry's references | 1 | 1 |
| … not in OMIM | 40 | 42 |
| Pooled precision (entries where OMIM lists variants) | 86.9% | 86.9% |

## Inheritance errors by kind

| | Direct reading | Second-hand evidence |
|---|---|---|
| Entries with an OMIM mode of inheritance | 96 | 96 |
| … matched | 90 | 92 |
| … none stated | 2 | 1 |
| … a mode missing | 0 | 0 |
| … an extra mode | 4 | 3 |
| … a different mode | 0 | 0 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Direct reading | Second-hand evidence |
|---|---|---|
| fulltext | 79.1% (1,538) | 78.1% (1,531) |
| abstract | 44.2% (3,580) | 45.0% (3,581) |
| title | 23.1% (344) | 30.1% (341) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies. Facts are split from the gold paragraph separately for each draft, so the fact counts differ slightly.

| Paper readable as | Second-hand evidence |
|---|---|
| fulltext | -1.0 (-2.5 to +0.5); n=44 |
| abstract | +0.8 (-0.1 to +1.7); n=86 |
| title | +7.0 (+0.5 to +14.5); n=21 |

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Second-hand evidence |
|---|---|---|
| no full text (abstracts only) | 45 | +0.8 (-0.7 to +2.2); n=45 |
| under half full text | 27 | +2.7 (+0.9 to +4.8); n=27 |
| half or more full text | 22 | -0.9 (-2.7 to +0.9); n=22 |
| all full text | 2 | -6.5 †; n=2 |

### OMIM allelic variants recovered

| Access group | Entries | Second-hand evidence |
|---|---|---|
| no full text (abstracts only) | 45 | +9.7 (+2.8 to +18.1); n=45 |
| under half full text | 27 | +0.3 (-4.6 to +4.6); n=27 |
| half or more full text | 22 | +1.5 (+0.0 to +4.5); n=22 |
| all full text | 2 | +0.0 †; n=2 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 81.8% (77 facts, 3 entries) | 80.7% (192 facts, 10 entries) | 76.8% (415 facts, 11 entries) | 74.1% (474 facts, 11 entries) | 86.5% (380 facts, 9 entries) |
| abstract | 40.9% (861 facts, 19 entries) | 51.6% (568 facts, 19 entries) | 44.7% (899 facts, 18 entries) | 43.7% (728 facts, 15 entries) | 41.4% (524 facts, 15 entries) |
| title | 30.8% (39 facts, 3 entries) | 21.8% (55 facts, 4 entries) | 29.8% (52 facts, 4 entries) | 21.2% (73 facts, 5 entries) | 19.6% (125 facts, 5 entries) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 45 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 95.1% | 92.3% |
| … same, before the repair round ↓ | 0.4% | 7.3% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 40.4% | 41.2% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 30.4% | 33.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.7% | 55.2% |
| OMIM allelic variants recovered ↑ | 49.1% | 58.9% |
| Causal gene F1 ↑ | 94.8% | 94.8% |
| Inheritance matches OMIM ↑ | 91.1% | 95.6% |

### under half full text — 27 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.7% |
| … same, before the repair round ↓ | 0.6% | 1.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.9% | 58.6% |
| OMIM per-paper facts contradicted ↓ | 1.0% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 39.3% | 38.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.1% | 61.1% |
| OMIM allelic variants recovered ↑ | 80.2% | 80.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 92.6% | 92.6% |

### half or more full text — 22 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 97.9% | 96.7% |
| … same, before the repair round ↓ | 0.0% | 0.8% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 73.7% | 72.8% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 41.1% | 41.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.5% | 62.5% |
| OMIM allelic variants recovered ↑ | 89.4% | 91.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### all full text — 2 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 98.6% | 98.2% |
| … same, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 77.8% | 71.3% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 7.1% |
| Clinical synopsis HPO F1, exact ↑ | 56.9% | 52.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 79.7% | 74.6% |
| OMIM allelic variants recovered ↑ | 100.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 53 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 93.9% |
| … same, before the repair round ↓ | 0.2% | 4.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 54.8% | 55.1% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 33.7% | 35.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.3% | 57.5% |
| OMIM allelic variants recovered ↑ | 67.4% | 70.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 98.1% | 100.0% |

### 5-8 references — 27 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.1% | 94.9% |
| … same, before the repair round ↓ | 0.7% | 5.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 49.9% | 51.8% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 1.1% |
| Clinical synopsis HPO F1, exact ↑ | 36.1% | 37.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.0% | 58.9% |
| OMIM allelic variants recovered ↑ | 66.7% | 78.1% |
| Causal gene F1 ↑ | 96.3% | 96.3% |
| Inheritance matches OMIM ↑ | 88.9% | 92.6% |

### 9 or more references — 16 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.4% |
| … same, before the repair round ↓ | 0.3% | 1.7% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.4% | 53.9% |
| OMIM per-paper facts contradicted ↓ | 1.0% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 42.7% | 41.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 62.5% | 63.7% |
| OMIM allelic variants recovered ↑ | 73.1% | 73.1% |
| Causal gene F1 ↑ | 91.7% | 91.7% |
| Inheritance matches OMIM ↑ | 87.5% | 87.5% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.0% | 95.2% |
| … same, before the repair round ↓ | 0.5% | 2.7% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.7% | 58.4% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 40.0% | 42.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 62.3% | 66.9% |
| OMIM allelic variants recovered ↑ | 72.2% | 80.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 89.5% | 94.7% |

### 610000-615999 — 20 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 95.6% | 93.2% |
| … same, before the repair round ↓ | 0.2% | 6.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.4% | 54.5% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 1.4% |
| Clinical synopsis HPO F1, exact ↑ | 36.5% | 38.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.2% | 58.1% |
| OMIM allelic variants recovered ↑ | 72.7% | 82.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.0% | 100.0% |

### 616000-619999 — 20 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 94.4% |
| … same, before the repair round ↓ | 0.1% | 2.8% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.4% | 55.6% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.0% | 33.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.7% | 56.1% |
| OMIM allelic variants recovered ↑ | 81.1% | 82.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.0% | 95.0% |

### 620000 onward — 18 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 97.0% | 94.2% |
| … same, before the repair round ↓ | 0.0% | 2.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 57.2% | 56.8% |
| OMIM per-paper facts contradicted ↓ | 0.1% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 34.4% | 33.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.2% | 53.3% |
| OMIM allelic variants recovered ↑ | 66.8% | 64.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### classic (1xxxxx-5xxxxx) — 19 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 95.2% |
| … same, before the repair round ↓ | 0.9% | 5.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 44.2% | 44.5% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.5% |
| Clinical synopsis HPO F1, exact ↑ | 33.5% | 36.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.2% | 60.1% |
| OMIM allelic variants recovered ↑ | 47.1% | 55.0% |
| Causal gene F1 ↑ | 87.7% | 87.7% |
| Inheritance matches OMIM ↑ | 89.5% | 89.5% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Direct reading | Second-hand evidence |
|---|---|---|
| Generation: model calls | 1.8 | 1.8 |
| Generation: list price | $0.28 | $0.36 |
| Generation: input / output tokens | 21,893 / 6,348 | 31,395 / 7,729 |
| Generation: model time (s) | 52 | 64 |
| Audit and repair: list price | $0.75 | $0.93 |
| Scoring against OMIM: list price | $0.20 | $0.20 |
| Everything: list price | $1.23 | $1.49 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Direct reading | 99 | 100 | 105 | 99.0% | 94.3% | 96.6% |
| Disease → causal gene | Second-hand evidence | 98 | 99 | 105 | 99.0% | 93.3% | 96.1% |
| Disease → mode of inheritance | Direct reading | 98 | 102 | 103 | 96.1% | 95.2% | 95.6% |
| Disease → mode of inheritance | Second-hand evidence | 98 | 101 | 103 | 97.0% | 95.2% | 96.1% |
| Disease → phenotype (HPO, exact id) | Direct reading | 689 | 1,559 | 2,344 | 44.2% | 29.4% | 35.3% |
| Disease → phenotype (HPO, exact id) | Second-hand evidence | 720 | 1,624 | 2,347 | 44.3% | 30.7% | 36.3% |
| Disease → allelic variant | Direct reading | 274 | 314 | 428 | 87.3% | 64.0% | 73.9% |
| Disease → allelic variant | Second-hand evidence | 286 | 328 | 428 | 87.2% | 66.8% | 75.7% |
