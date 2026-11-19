# Generation strategies compared — run `omim100_guided`

68 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

No draft: 2 entries for which at least one strategy wrote nothing, because the model's safety filter stopped the writer's reply or the reply came back empty (Learned curation guide 2). Entries: 118210, 615817. They are left out of the comparison with the incomplete entries listed under Completion.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 68 of the run's 70 entries qualify; left out: 118210, 615817. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Direct reading | 70 | 0 | 0 |
| Learned curation guide | 68 | 0 | 2: 118210, 615817 |

## How the scores are counted

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Direct reading: genes 1, variants 11; Learned curation guide: genes 1, variants 11.

- **n.** A value rests on all 68 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Learned curation guide** (`guided`): Direct reading with a guide to what OMIM includes, learned from the misses and extras of other entries.

## Scores

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 96.1% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% |
| … same, before the repair round ↓ | 0.2% | 0.2% |
| … unsupported, before the repair round ↓ | 0.2% | 0.2% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.2% | 51.9% |
| … fully (no partial credit) ↑ | 43.8% | 44.2% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 35.7% | 36.5% |
| … precision ↑ | 43.8% | 43.0% |
| … recall ↑ | 37.1% | 40.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.4% | 55.4% |
| Clinical synopsis HPO F1, semantic ↑ | 65.8% | 66.7% |
| OMIM allelic variants recovered ↑ | 66.6% | 65.0% |
| Generated variants that are OMIM variants (precision) ↑ | 86.8% (n=57) | 87.9% (n=57) |
| Causal gene F1 ↑ | 98.0% | 98.0% |
| … recall ↑ | 97.8% | 97.8% |
| Inheritance matches OMIM ↑ | 94.1% | 94.1% |
| Inheritance error: none stated ↓ | 2.9% | 2.9% |
| Inheritance error: a mode missing ↓ | 0.0% | 0.0% |
| Inheritance error: an extra mode ↓ | 2.9% | 2.9% |
| Inheritance error: a different mode ↓ | 0.0% | 0.0% |
| OMIM references used ↑ | 94.5% | 93.7% |

## How much each strategy writes

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims audited per entry | 107.1 | 96.3 |
| Claims that could not be audited per entry | 0.9 | 0.5 |
| Clinical-synopsis HPO terms per entry | 16.2 | 18.1 |
| Allelic variants per entry | 3.4 | 3.3 |
| … of which not in OMIM | 0.5 | 0.5 |
| Papers cited per entry | 4.9 | 4.8 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Learned curation guide |
|---|---|
| Claims supported by cited paper ↑ | -0.1 (-1.0 to +1.0); 29/35/4 |
| … same, before the repair round ↓ | -0.0 (-0.4 to +0.3); 6/7/55 |
| OMIM per-paper facts conveyed (primary) ↑ | -0.3 (-1.4 to +0.7); 32/36/0 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.0 to +0.3); 6/11/51 |
| Clinical synopsis HPO F1, exact ↑ | +0.8 (-0.8 to +2.4); 34/22/12 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.1 (-1.3 to +1.3); 27/31/10 |
| OMIM allelic variants recovered ↑ | -1.6 (-3.7 to +0.0); 0/3/65 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/68 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/68 |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Learned curation guide minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 68 | 51.9% | 52.2% | -0.3 | -1.4 to +0.7 | -0.8 | 32 / 36 / 0 | 0.716 | – |
| Claims supported by cited paper (headline) ↑ | 68 | 96.1% | 96.2% | -0.1 | -1.0 to +1.0 | -0.1 | 29 / 35 / 4 | 0.532 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 68 | 0.2% | 0.2% | -0.0 | -0.4 to +0.3 | +0.0 | 6 / 7 / 55 | 1.000 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 68 | 0.7% | 0.5% | +0.1 | -0.0 to +0.3 | +0.0 | 6 / 11 / 51 | 0.332 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 68 | 36.5% | 35.7% | +0.8 | -0.8 to +2.4 | +0.1 | 34 / 22 / 12 | 0.141 | 0.845 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 68 | 55.4% | 55.4% | +0.1 | -1.3 to +1.3 | +0.0 | 27 / 31 / 10 | 0.694 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 68 | 65.0% | 66.6% | -1.6 | -3.7 to +0.0 | +0.0 | 0 / 3 / 65 | 0.250 | 1.000 |
| Causal gene F1 (headline) ↑ | 68 | 98.0% | 98.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Inheritance matches OMIM (headline) ↑ | 68 | 94.1% | 94.1% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Claims unsupported or contradicted ↓ | 68 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Claims unsupported, before the repair round ↓ | 68 | 0.2% | 0.2% | -0.0 | -0.4 to +0.3 | +0.0 | 6 / 7 / 55 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 68 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 1 / 67 | 1.000 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 68 | 44.2% | 43.8% | +0.4 | -0.8 to +1.6 | -0.2 | 30 / 35 / 3 | 0.620 | – |
| Clinical synopsis HPO precision, exact ↑ | 68 | 43.0% | 43.8% | -0.8 | -3.4 to +1.9 | +0.0 | 26 / 29 / 13 | 0.788 | – |
| Clinical synopsis HPO recall, exact ↑ | 68 | 40.0% | 37.1% | +2.9 | +0.9 to +4.7 | +0.0 | 29 / 7 / 32 | <0.001 | – |
| Clinical synopsis HPO F1, semantic ↑ | 68 | 66.7% | 65.8% | +0.9 | -0.3 to +2.2 | +0.3 | 35 / 25 / 8 | 0.245 | – |
| Generated variants that are OMIM variants (precision) ↑ | 57 | 87.9% | 86.8% | +1.1 | -2.4 to +5.1 | +0.0 | 4 / 3 / 50 | 1.000 | – |
| Causal gene recall ↑ | 68 | 97.8% | 97.8% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Inheritance error: none stated ↓ | 68 | 2.9% | 2.9% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Inheritance error: a mode missing ↓ | 68 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Inheritance error: an extra mode ↓ | 68 | 2.9% | 2.9% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| Inheritance error: a different mode ↓ | 68 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 68 | – | – |
| OMIM references used ↑ | 68 | 93.7% | 94.5% | -0.7 | -2.8 to +0.9 | +0.0 | 2 / 4 / 62 | 0.688 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 70 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Learned curation guide 2.

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 93.4% |
| … same, before the repair round ↓ | 0.4% | 0.2% (n=68) |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.4% | 50.4% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.7% (n=68) |
| Clinical synopsis HPO F1, exact ↑ | 35.3% | 35.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.3% | 53.8% |
| OMIM allelic variants recovered ↑ | 67.3% | 63.1% |
| Causal gene F1 ↑ | 98.1% | 95.2% |
| Inheritance matches OMIM ↑ | 94.3% | 91.4% |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Learned curation guide |
|---|---|
| Claims supported by cited paper ↑ | -2.8 (-7.1 to +0.3); median -0.2; 29/37/4; p 0.389 |
| … same, before the repair round ↓ | -0.0 (-0.4 to +0.3); median +0.0; 6/7/55; p 1.000 (n=68) |
| OMIM per-paper facts conveyed (primary) ↑ | -2.0 (-4.8 to +0.2); median -0.8; 32/38/0; p 0.550 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.0 to +0.3); median +0.0; 6/11/51; p 0.332 (n=68) |
| Clinical synopsis HPO F1, exact ↑ | +0.2 (-1.7 to +1.9); median +0.0; 34/24/12; p 0.237 |
| Clinical synopsis HPO F1, hierarchical ↑ | -1.5 (-4.1 to +0.7); median +0.0; 27/33/10; p 0.519 |
| OMIM allelic variants recovered ↑ | -4.2 (-8.6 to -0.7); median +0.0; 0/5/65; p 0.062 |
| Causal gene F1 ↑ | -2.9 (-7.1 to +0.0); median +0.0; 0/2/68; p 0.500 |
| Inheritance matches OMIM ↑ | -2.9 (-7.1 to +0.0); median +0.0; 0/2/68; p 0.500 |

## Pooled counts

| | Direct reading | Learned curation guide |
|---|---|---|
| Claims audited | 7,282 | 6,549 |
| … supported | 7,043 | 6,333 |
| … partly supported | 239 | 216 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| Claims audited before repair | 7,260 | 6,537 |
| … unsupported before repair | 11 | 15 |
| … contradicted before repair | 0 | 1 |
| OMIM facts scored | 3,962 | 3,958 |
| … conveyed | 1,773 | 1,787 |
| … partly conveyed | 671 | 617 |
| … missing | 1,494 | 1,526 |
| … contradicted | 24 | 28 |

## Allelic variants: precision and variants not in OMIM

| | Direct reading | Learned curation guide |
|---|---|---|
| Variants generated | 230 | 223 |
| … matching an OMIM variant of the entry | 194 | 191 |
| … listed by OMIM only from a paper outside the entry's references | 1 | 1 |
| … not in OMIM | 35 | 31 |
| Pooled precision (entries where OMIM lists variants) | 84.4% | 85.7% |

## Inheritance errors by kind

| | Direct reading | Learned curation guide |
|---|---|---|
| Entries with an OMIM mode of inheritance | 68 | 68 |
| … matched | 64 | 64 |
| … none stated | 2 | 2 |
| … a mode missing | 0 | 0 |
| … an extra mode | 2 | 2 |
| … a different mode | 0 | 0 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Direct reading | Learned curation guide |
|---|---|---|
| fulltext | 78.2% (1,310) | 78.2% (1,298) |
| abstract | 43.1% (2,356) | 42.8% (2,368) |
| title | 23.3% (296) | 22.9% (292) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies. Facts are split from the gold paragraph separately for each draft, so the fact counts differ slightly.

| Paper readable as | Learned curation guide |
|---|---|
| fulltext | +0.0 (-1.7 to +2.1); n=36 |
| abstract | -0.3 (-1.4 to +0.9); n=60 |
| title | -0.4 (-2.4 to +1.3) †; n=16 |

† fewer than 20 entries: the interval is unreliable.

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Learned curation guide |
|---|---|---|
| no full text (abstracts only) | 29 | -0.1 (-1.8 to +1.7); n=29 |
| under half full text | 19 | +0.5 (-1.1 to +2.3) †; n=19 |
| half or more full text | 19 | -1.7 (-3.3 to +0.1) †; n=19 |
| all full text | 1 | +1.5 †; n=1 |

### OMIM allelic variants recovered

| Access group | Entries | Learned curation guide |
|---|---|---|
| no full text (abstracts only) | 29 | -2.6 (-6.9 to +0.0); n=29 |
| under half full text | 19 | +0.0 (+0.0 to +0.0) †; n=19 |
| half or more full text | 19 | -1.8 (-5.3 to +0.0) †; n=19 |
| all full text | 1 | +0.0 †; n=1 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 89.1% (23 facts, 1 entry) | 79.1% (151 facts, 8 entries) | 75.5% (364 facts, 9 entries) | 73.2% (433 facts, 10 entries) | 86.3% (339 facts, 8 entries) |
| abstract | 33.3% (607 facts, 13 entries) | 52.4% (420 facts, 14 entries) | 48.7% (492 facts, 12 entries) | 44.4% (447 facts, 9 entries) | 39.7% (390 facts, 12 entries) |
| title | 35.9% (32 facts, 2 entries) | 25.6% (45 facts, 3 entries) | 32.1% (42 facts, 3 entries) | 15.0% (60 facts, 4 entries) | 20.1% (117 facts, 4 entries) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 29 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 94.8% | 95.1% |
| … same, before the repair round ↓ | 0.4% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 37.1% | 37.0% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 28.1% | 28.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 46.3% | 46.8% |
| OMIM allelic variants recovered ↑ | 43.9% | 41.3% |
| Causal gene F1 ↑ | 95.4% | 95.4% |
| Inheritance matches OMIM ↑ | 93.1% | 93.1% |

### under half full text — 19 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.6% | 96.9% |
| … same, before the repair round ↓ | 0.2% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 54.5% | 54.9% |
| OMIM per-paper facts contradicted ↓ | 1.0% | 1.1% |
| Clinical synopsis HPO F1, exact ↑ | 40.5% | 41.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.9% | 61.6% |
| OMIM allelic variants recovered ↑ | 78.3% | 78.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 89.5% | 89.5% |

### half or more full text — 19 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 97.9% | 96.8% |
| … same, before the repair round ↓ | 0.1% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 71.3% | 69.6% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 41.7% | 42.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.5% | 61.5% |
| OMIM allelic variants recovered ↑ | 87.8% | 86.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### all full text — 1 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 97.8% | 98.1% |
| … same, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 85.5% | 87.0% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 50.0% | 51.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 76.5% | 70.9% |
| OMIM allelic variants recovered ↑ | 100.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 38 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 96.2% |
| … same, before the repair round ↓ | 0.2% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.5% | 51.3% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 34.7% | 34.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.0% | 54.3% |
| OMIM allelic variants recovered ↑ | 65.1% | 62.9% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 97.4% | 97.4% |

### 5-8 references — 18 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.0% | 96.0% |
| … same, before the repair round ↓ | 0.3% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 50.0% | 51.6% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 35.3% | 38.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.3% | 55.8% |
| OMIM allelic variants recovered ↑ | 67.8% | 66.4% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 94.4% | 94.4% |

### 9 or more references — 12 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 95.9% |
| … same, before the repair round ↓ | 0.2% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 54.5% | 54.1% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.1% |
| Clinical synopsis HPO F1, exact ↑ | 39.5% | 38.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.1% | 58.3% |
| OMIM allelic variants recovered ↑ | 69.6% | 69.6% |
| Causal gene F1 ↑ | 88.9% | 88.9% |
| Inheritance matches OMIM ↑ | 83.3% | 83.3% |

## By creation era (MIM number range)

### 600000-609999 — 14 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 96.9% |
| … same, before the repair round ↓ | 0.7% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 54.9% | 53.4% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 40.7% | 40.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 64.1% | 63.3% |
| OMIM allelic variants recovered ↑ | 69.5% | 69.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 85.7% | 85.7% |

### 610000-615999 — 13 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 95.2% | 96.9% |
| … same, before the repair round ↓ | 0.2% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 56.7% | 58.2% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 37.2% | 35.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.0% | 51.4% |
| OMIM allelic variants recovered ↑ | 77.7% | 77.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### 616000-619999 — 14 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.4% | 96.6% |
| … same, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 57.0% | 55.1% |
| OMIM per-paper facts contradicted ↓ | 1.1% | 1.4% |
| Clinical synopsis HPO F1, exact ↑ | 38.3% | 40.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.3% | 58.5% |
| OMIM allelic variants recovered ↑ | 86.8% | 84.4% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 92.9% | 92.9% |

### 620000 onward — 14 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 97.8% | 96.6% |
| … same, before the repair round ↓ | 0.0% | 0.6% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.0% | 54.8% |
| OMIM per-paper facts contradicted ↓ | 0.1% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 34.1% | 34.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 51.7% | 52.7% |
| OMIM allelic variants recovered ↑ | 65.2% | 61.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### classic (1xxxxx-5xxxxx) — 13 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 94.6% | 93.4% |
| … same, before the repair round ↓ | 0.2% | 0.3% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 36.6% | 37.2% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 27.9% | 30.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.9% | 50.5% |
| OMIM allelic variants recovered ↑ | 32.2% | 30.3% |
| Causal gene F1 ↑ | 89.8% | 89.8% |
| Inheritance matches OMIM ↑ | 92.3% | 92.3% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Direct reading | Learned curation guide |
|---|---|---|
| Generation: model calls | 1.9 | 1.9 |
| Generation: list price | $0.28 | $0.29 |
| Generation: input / output tokens | 22,400 / 6,560 | 24,844 / 6,645 |
| Generation: model time (s) | 53 | 55 |
| Audit and repair: list price | $0.77 | $0.70 |
| Scoring against OMIM: list price | $0.20 | $0.20 |
| Everything: list price | $1.26 | $1.18 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Direct reading | 73 | 73 | 75 | 100.0% | 97.3% | 98.7% |
| Disease → causal gene | Learned curation guide | 71 | 71 | 75 | 100.0% | 94.7% | 97.3% |
| Disease → mode of inheritance | Direct reading | 71 | 73 | 73 | 97.3% | 97.3% | 97.3% |
| Disease → mode of inheritance | Learned curation guide | 69 | 71 | 73 | 97.2% | 94.5% | 95.8% |
| Disease → phenotype (HPO, exact id) | Direct reading | 514 | 1,158 | 1,679 | 44.4% | 30.6% | 36.2% |
| Disease → phenotype (HPO, exact id) | Learned curation guide | 546 | 1,249 | 1,669 | 43.7% | 32.7% | 37.4% |
| Disease → allelic variant | Direct reading | 202 | 237 | 308 | 85.2% | 65.6% | 74.1% |
| Disease → allelic variant | Learned curation guide | 192 | 223 | 308 | 86.1% | 62.3% | 72.3% |
