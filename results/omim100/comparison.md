# Evidence-graph strategy vs direct baseline — run `omim100`

94 entries, each written in full by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better. An entry with no draft, or one for which a per-paper extraction call failed, is left out (6: 118210, 609296, 617232, 620609, 621030, 621068). Where a strategy predicted nothing against a non-empty gold set, F1 and recall count as 0.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 94 | 96.5% | 96.1% | +0.4 | -0.4 to +1.3 | +0.0 | 43 / 44 / 7 | 1.000 |
| Claims unsupported or contradicted ↓ | 94 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 94 | – |
| … same, before the repair round ↓ | 94 | 0.3% | 0.2% | +0.0 | -0.3 to +0.3 | +0.0 | 11 / 13 / 70 | 0.839 |
| … unsupported, before the repair round ↓ | 94 | 0.2% | 0.2% | -0.0 | -0.3 to +0.2 | +0.0 | 11 / 10 / 73 | 1.000 |
| … contradicted, before the repair round ↓ | 94 | 0.1% | 0.0% | +0.1 | +0.0 to +0.1 | +0.0 | 0 / 4 / 90 | 0.125 |
| OMIM per-paper facts conveyed ↑ | 94 | 51.4% | 52.1% | -0.7 | -1.7 to +0.2 | +0.0 | 44 / 43 / 7 | 1.000 |
| … fully (no partial credit) ↑ | 94 | 43.3% | 43.7% | -0.3 | -1.5 to +0.8 | +0.1 | 47 / 40 / 7 | 0.520 |
| OMIM per-paper facts contradicted ↓ | 94 | 0.7% | 0.5% | +0.1 | -0.1 to +0.5 | +0.0 | 12 / 11 / 71 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 94 | 34.4% | 35.8% | -1.4 | -3.3 to +0.5 | +0.0 | 34 / 46 / 14 | 0.218 |
| … precision ↑ | 94 | 40.3% | 44.0% | -3.6 | -6.8 to -0.6 | -2.1 | 29 / 50 / 15 | 0.024 |
| … recall ↑ | 94 | 37.4% | 36.1% | +1.2 | -1.2 to +3.4 | +0.0 | 37 / 20 / 37 | 0.033 |
| Clinical synopsis HPO F1, hierarchical ↑ | 94 | 54.6% | 56.1% | -1.5 | -2.8 to -0.1 | +0.0 | 36 / 45 / 13 | 0.374 |
| Clinical synopsis HPO F1, semantic ↑ | 94 | 65.0% | 66.3% | -1.3 | -2.4 to -0.3 | -0.5 | 35 / 53 / 6 | 0.069 |
| OMIM allelic variants recovered ↑ | 94 | 66.1% | 66.6% | -0.5 | -3.1 to +2.5 | +0.0 | 4 / 8 / 82 | 0.388 |
| Generated variants that are OMIM variants (precision) ↑ | 83 | 82.5% | 88.8% | -6.3 | -10.4 to -2.7 | +0.0 | 2 / 19 / 62 | 0.000 |
| Causal gene F1 ↑ | 94 | 98.2% | 97.5% | +0.7 | +0.0 to +2.1 | +0.0 | 1 / 0 / 93 | 1.000 |
| … recall ↑ | 94 | 98.4% | 97.3% | +1.1 | +0.0 to +3.2 | +0.0 | 1 / 0 / 93 | 1.000 |
| Inheritance matches OMIM ↑ | 94 | 92.5% | 93.6% | -1.1 | -5.3 to +2.1 | +0.0 | 1 / 2 / 91 | 1.000 |
| Inheritance error: none stated ↓ | 94 | 3.2% | 2.1% | +1.1 | -2.1 to +4.3 | +0.0 | 1 / 2 / 91 | 1.000 |
| Inheritance error: a mode missing ↓ | 94 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 94 | – |
| Inheritance error: an extra mode ↓ | 94 | 3.2% | 4.3% | -1.1 | -3.2 to +0.0 | +0.0 | 1 / 0 / 93 | 1.000 |
| Inheritance error: a different mode ↓ | 94 | 1.1% | 0.0% | +1.1 | +0.0 to +3.2 | +0.0 | 0 / 1 / 93 | 1.000 |
| OMIM references used ↑ | 94 | 94.7% | 94.4% | +0.3 | -2.0 to +2.4 | +0.0 | 10 / 5 / 79 | 0.302 |

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 10,882 | 9,625 |
| … supported | 10,553 | 9,295 |
| … partly supported | 329 | 330 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 5,404 | 5,399 |
| … conveyed | 2,295 | 2,335 |
| … partly conveyed | 882 | 913 |
| … missing | 2,196 | 2,117 |
| … contradicted | 31 | 34 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 1,415 | 79.4% | 78.6% | 0.6% | 0.4% |
| abstract | 3,645 | 42.1% | 43.9% | 0.6% | 0.8% |
| title | 344 | 22.7% | 23.1% | 0.3% | 0.0% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 19 | 95.6% | 96.0% | -0.4 | -2.3 to +1.3 | -0.2 | 8 / 11 / 0 | 0.648 |
| Claims unsupported or contradicted ↓ | 19 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |
| OMIM per-paper facts conveyed ↑ | 19 | 56.1% | 55.7% | +0.4 | -2.3 to +3.1 | +1.0 | 11 / 7 / 1 | 0.481 |
| Clinical synopsis HPO F1, exact ↑ | 19 | 40.8% | 40.0% | +0.9 | -2.9 to +5.2 | +0.0 | 5 / 9 / 5 | 0.424 |
| Clinical synopsis HPO F1, hierarchical ↑ | 19 | 61.6% | 62.3% | -0.7 | -2.3 to +0.8 | +0.0 | 7 / 9 / 3 | 0.804 |
| OMIM allelic variants recovered ↑ | 19 | 68.7% | 72.2% | -3.5 | -9.7 to +0.0 | +0.0 | 0 / 2 / 17 | 0.500 |
| Causal gene F1 ↑ | 19 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |
| Inheritance matches OMIM ↑ | 19 | 79.0% | 89.5% | -10.5 | -26.3 to +0.0 | +0.0 | 0 / 2 / 17 | 0.500 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 610000-615999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 97.0% | 95.6% | +1.4 | -0.7 to +4.3 | +0.0 | 9 / 9 / 2 | 1.000 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 52.1% | 53.4% | -1.3 | -3.9 to +1.1 | -0.7 | 9 / 11 / 0 | 0.824 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 32.1% | 36.5% | -4.4 | -9.3 to +0.7 | -6.0 | 7 / 11 / 2 | 0.481 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 50.5% | 54.2% | -3.7 | -7.1 to -0.5 | -0.1 | 6 / 10 / 4 | 0.455 |
| OMIM allelic variants recovered ↑ | 20 | 70.7% | 72.7% | -2.0 | -4.4 to +0.0 | +0.0 | 0 / 3 / 17 | 0.250 |
| Causal gene F1 ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 95.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – |

### 616000-619999 — 19 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 19 | 97.1% | 96.8% | +0.3 | -0.5 to +1.3 | +0.0 | 8 / 8 / 3 | 1.000 |
| Claims unsupported or contradicted ↓ | 19 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |
| OMIM per-paper facts conveyed ↑ | 19 | 53.6% | 53.9% | -0.3 | -1.5 to +0.7 | +0.0 | 8 / 9 / 2 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 19 | 34.3% | 35.7% | -1.5 | -5.1 to +2.1 | -1.9 | 6 / 10 / 3 | 0.455 |
| Clinical synopsis HPO F1, hierarchical ↑ | 19 | 55.0% | 55.9% | -0.9 | -3.1 to +1.6 | +0.0 | 7 / 9 / 3 | 0.804 |
| OMIM allelic variants recovered ↑ | 19 | 81.2% | 80.1% | +1.1 | +0.0 to +3.2 | +0.0 | 1 / 0 / 18 | 1.000 |
| Causal gene F1 ↑ | 19 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |
| Inheritance matches OMIM ↑ | 19 | 94.7% | 94.7% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 620000 onward — 17 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 17 | 96.3% | 96.9% | -0.6 | -2.5 to +1.1 | -0.7 | 8 / 9 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 17 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 17 | – |
| OMIM per-paper facts conveyed ↑ | 17 | 53.1% | 55.5% | -2.4 | -4.2 to -0.6 | +0.0 | 6 / 8 / 3 | 0.790 |
| Clinical synopsis HPO F1, exact ↑ | 17 | 34.1% | 33.5% | +0.5 | -2.7 to +4.0 | +0.0 | 8 / 8 / 1 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 17 | 53.5% | 52.9% | +0.6 | -2.1 to +3.9 | +0.0 | 8 / 7 / 2 | 1.000 |
| OMIM allelic variants recovered ↑ | 17 | 61.2% | 64.8% | -3.7 | -10.3 to +0.0 | +0.0 | 0 / 2 / 15 | 0.500 |
| Causal gene F1 ↑ | 17 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 17 | – |
| Inheritance matches OMIM ↑ | 17 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 17 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### classic (1xxxxx-5xxxxx) — 19 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 19 | 96.6% | 95.3% | +1.3 | -0.2 to +2.9 | +0.1 | 10 / 7 / 2 | 0.629 |
| Claims unsupported or contradicted ↓ | 19 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 19 | – |
| OMIM per-paper facts conveyed ↑ | 19 | 42.4% | 42.4% | -0.0 | -1.9 to +1.7 | +0.1 | 10 / 8 / 1 | 0.815 |
| Clinical synopsis HPO F1, exact ↑ | 19 | 31.0% | 33.0% | -2.0 | -6.5 to +1.7 | +0.0 | 8 / 8 / 3 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 19 | 52.8% | 55.0% | -2.3 | -6.2 to +1.5 | -0.7 | 8 / 10 / 1 | 0.815 |
| OMIM allelic variants recovered ↑ | 19 | 47.9% | 42.7% | +5.3 | -2.6 to +17.1 | +0.0 | 3 / 1 / 15 | 0.625 |
| Causal gene F1 ↑ | 19 | 91.2% | 87.7% | +3.5 | +0.0 to +10.5 | +0.0 | 1 / 0 / 18 | 1.000 |
| Inheritance matches OMIM ↑ | 19 | 94.7% | 89.5% | +5.3 | +0.0 to +15.8 | +0.0 | 1 / 0 / 18 | 1.000 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 46 | 95.9% | 95.0% | +0.9 | -0.6 to +2.6 | +0.0 | 20 / 21 / 5 | 1.000 |
| Claims unsupported or contradicted ↓ | 46 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 46 | – |
| OMIM per-paper facts conveyed ↑ | 46 | 39.5% | 40.1% | -0.7 | -1.8 to +0.3 | +0.0 | 21 / 21 / 4 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 46 | 30.4% | 29.9% | +0.4 | -2.5 to +3.2 | +0.0 | 20 / 15 / 11 | 0.500 |
| Clinical synopsis HPO F1, hierarchical ↑ | 46 | 49.2% | 50.0% | -0.8 | -2.7 to +0.9 | +0.0 | 19 / 16 / 11 | 0.736 |
| OMIM allelic variants recovered ↑ | 46 | 48.9% | 48.4% | +0.4 | -4.6 to +6.2 | +0.0 | 4 / 3 / 39 | 1.000 |
| Causal gene F1 ↑ | 46 | 96.4% | 94.9% | +1.5 | +0.0 to +4.3 | +0.0 | 1 / 0 / 45 | 1.000 |
| Inheritance matches OMIM ↑ | 46 | 89.1% | 91.3% | -2.2 | -10.9 to +4.3 | +0.0 | 1 / 2 / 43 | 1.000 |

### under half full text — 26 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 26 | 97.2% | 96.5% | +0.7 | -0.3 to +1.7 | +1.1 | 17 / 9 / 0 | 0.169 |
| Claims unsupported or contradicted ↓ | 26 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 26 | – |
| OMIM per-paper facts conveyed ↑ | 26 | 56.1% | 55.7% | +0.4 | -1.6 to +2.5 | +0.9 | 16 / 9 / 1 | 0.230 |
| Clinical synopsis HPO F1, exact ↑ | 26 | 36.6% | 40.1% | -3.5 | -6.0 to -0.9 | -4.2 | 7 / 17 / 2 | 0.064 |
| Clinical synopsis HPO F1, hierarchical ↑ | 26 | 58.9% | 61.2% | -2.3 | -3.9 to -0.6 | -1.2 | 7 / 18 / 1 | 0.043 |
| OMIM allelic variants recovered ↑ | 26 | 77.6% | 79.4% | -1.8 | -4.0 to +0.0 | +0.0 | 0 / 3 / 23 | 0.250 |
| Causal gene F1 ↑ | 26 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 26 | – |
| Inheritance matches OMIM ↑ | 26 | 92.3% | 92.3% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 26 | – |

### half or more full text — 21 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 21 | 96.9% | 97.9% | -1.0 | -1.9 to -0.1 | -1.1 | 6 / 14 / 1 | 0.115 |
| Claims unsupported or contradicted ↓ | 21 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |
| OMIM per-paper facts conveyed ↑ | 21 | 70.5% | 73.2% | -2.7 | -4.9 to -0.6 | -1.2 | 6 / 13 / 2 | 0.167 |
| Clinical synopsis HPO F1, exact ↑ | 21 | 39.9% | 42.0% | -2.1 | -6.2 to +2.2 | -2.6 | 7 / 13 / 1 | 0.263 |
| Clinical synopsis HPO F1, hierarchical ↑ | 21 | 60.6% | 62.0% | -1.3 | -5.1 to +2.4 | +0.0 | 10 / 10 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 21 | 87.9% | 88.9% | -1.0 | -2.6 to +0.0 | +0.0 | 0 / 2 / 19 | 0.500 |
| Causal gene F1 ↑ | 21 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |
| Inheritance matches OMIM ↑ | 21 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |

### all full text — 1 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 1 | 99.3% | 99.3% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Claims unsupported or contradicted ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| OMIM per-paper facts conveyed ↑ | 1 | 80.8% | 70.0% | +10.8 | – | +10.8 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 1 | 49.5% | 63.8% | -14.3 | – | -14.3 | 0 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 1 | 67.7% | 82.8% | -15.1 | – | -15.1 | 0 / 1 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Causal gene F1 ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance matches OMIM ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 102 | 103 | 105 | 99.0% | 97.1% | 98.1% |
| Disease → causal gene | Direct reading | 99 | 100 | 105 | 99.0% | 94.3% | 96.6% |
| Disease → mode of inheritance | Evidence graph | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → mode of inheritance | Direct reading | 98 | 102 | 103 | 96.1% | 95.2% | 95.6% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 749 | 2,015 | 2,326 | 37.2% | 32.2% | 34.5% |
| Disease → phenotype (HPO, exact id) | Direct reading | 689 | 1,559 | 2,344 | 44.2% | 29.4% | 35.3% |
| Disease → allelic variant | Evidence graph | 271 | 381 | 428 | 71.1% | 63.3% | 67.0% |
| Disease → allelic variant | Direct reading | 274 | 314 | 428 | 87.3% | 64.0% | 73.9% |
