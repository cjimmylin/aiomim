# Evidence-graph strategy vs direct baseline — run `ablation40`

40 entries, each written in full by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better. An entry with no draft, or one for which a per-paper extraction call failed, is left out. Where a strategy predicted nothing against a non-empty gold set, F1 and recall count as 0.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 40 | 97.1% | 97.9% | -0.8 | -1.4 to -0.1 | -0.7 | 9 / 26 / 5 | 0.006 |
| Claims unsupported or contradicted ↓ | 40 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 40 | – |
| … same, before the repair round ↓ | 40 | 0.3% | 0.1% | +0.2 | +0.0 to +0.4 | +0.0 | 2 / 6 / 32 | 0.289 |
| … unsupported, before the repair round ↓ | 40 | 0.2% | 0.1% | +0.1 | +0.0 to +0.2 | +0.0 | 3 / 4 / 33 | 1.000 |
| … contradicted, before the repair round ↓ | 40 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 2 / 38 | 0.500 |
| OMIM per-paper facts conveyed ↑ | 40 | 59.8% | 59.3% | +0.5 | -1.4 to +2.4 | +0.0 | 19 / 17 / 4 | 0.868 |
| … fully (no partial credit) ↑ | 40 | 53.8% | 52.9% | +0.9 | -1.2 to +3.1 | +0.0 | 19 / 15 / 6 | 0.608 |
| OMIM per-paper facts contradicted ↓ | 40 | 0.5% | 0.4% | +0.1 | -0.2 to +0.5 | +0.0 | 5 / 4 / 31 | 1.000 |
| … facts split afresh for each draft (earlier scoring) ↑ | 40 | 61.8% | 62.1% | -0.3 | -2.0 to +1.4 | +0.0 | 18 / 19 / 3 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 40 | 38.0% | 40.6% | -2.7 | -5.2 to -0.1 | -2.4 | 11 / 25 / 4 | 0.029 |
| … precision ↑ | 40 | 40.4% | 45.3% | -4.9 | -8.5 to -1.6 | -3.9 | 9 / 26 / 5 | 0.006 |
| … recall ↑ | 40 | 45.4% | 44.7% | +0.7 | -4.0 to +4.9 | +0.0 | 16 / 9 / 15 | 0.230 |
| Clinical synopsis HPO F1, hierarchical ↑ | 40 | 57.5% | 59.7% | -2.2 | -4.7 to +0.3 | -1.2 | 16 / 22 / 2 | 0.418 |
| Clinical synopsis HPO F1, semantic ↑ | 40 | 67.0% | 69.1% | -2.1 | -3.6 to -0.5 | -2.1 | 14 / 24 / 2 | 0.143 |
| OMIM allelic variants recovered ↑ | 40 | 76.9% | 77.5% | -0.5 | -1.4 to +0.0 | +0.0 | 0 / 2 / 38 | 0.500 |
| Generated variants that are OMIM variants (precision) ↑ | 38 | 82.4% | 88.4% | -6.1 | -11.1 to -2.1 | +0.0 | 0 / 8 / 30 | 0.008 |
| Causal gene F1 ↑ | 40 | 98.3% | 96.7% | +1.7 | +0.0 to +5.0 | +0.0 | 1 / 0 / 39 | 1.000 |
| … recall ↑ | 40 | 98.8% | 96.2% | +2.5 | +0.0 to +7.5 | +0.0 | 1 / 0 / 39 | 1.000 |
| Inheritance matches OMIM ↑ | 40 | 95.0% | 97.5% | -2.5 | -7.5 to +0.0 | +0.0 | 0 / 1 / 39 | 1.000 |
| Inheritance error: none stated ↓ | 40 | 2.5% | 0.0% | +2.5 | +0.0 to +7.5 | +0.0 | 0 / 1 / 39 | 1.000 |
| Inheritance error: a mode missing ↓ | 40 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 40 | – |
| Inheritance error: an extra mode ↓ | 40 | 0.0% | 2.5% | -2.5 | -7.5 to +0.0 | +0.0 | 1 / 0 / 39 | 1.000 |
| Inheritance error: a different mode ↓ | 40 | 2.5% | 0.0% | +2.5 | +0.0 to +7.5 | +0.0 | 0 / 1 / 39 | 1.000 |
| OMIM references used ↑ | 40 | 97.5% | 96.5% | +1.0 | -0.3 to +2.6 | +0.0 | 3 / 1 / 36 | 0.625 |

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 5,682 | 5,042 |
| … supported | 5,513 | 4,930 |
| … partly supported | 169 | 112 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 2,741 | 2,741 |
| … conveyed | 1,411 | 1,400 |
| … partly conveyed | 334 | 358 |
| … missing | 985 | 972 |
| … contradicted | 11 | 11 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 1,289 | 78.9% | 77.0% | 0.5% | 0.2% |
| abstract | 1,295 | 40.9% | 42.8% | 0.4% | 0.7% |
| title | 157 | 20.1% | 20.4% | 0.0% | 0.0% |

## By creation era (MIM number range)

### 600000-609999 — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 97.3% | 98.1% | -0.8 | -2.2 to +0.7 | -0.5 | 2 / 6 / 0 | 0.289 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 60.7% | 57.8% | +2.9 | -0.3 to +6.4 | +2.1 | 5 / 3 / 0 | 0.727 |
| Clinical synopsis HPO F1, exact ↑ | 8 | 44.4% | 43.3% | +1.1 | -3.5 to +7.1 | -1.7 | 2 / 5 / 1 | 0.453 |
| Clinical synopsis HPO F1, hierarchical ↑ | 8 | 64.1% | 65.3% | -1.1 | -3.9 to +1.3 | -1.2 | 3 / 5 / 0 | 0.727 |
| OMIM allelic variants recovered ↑ | 8 | 83.3% | 83.3% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Causal gene F1 ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Inheritance matches OMIM ↑ | 8 | 87.5% | 100.0% | -12.5 | -37.5 to +0.0 | +0.0 | 0 / 1 / 7 | 1.000 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 610000-615999 — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 96.6% | 97.8% | -1.2 | -2.5 to +0.0 | -1.2 | 1 / 6 / 1 | 0.125 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 69.7% | 69.4% | +0.3 | -6.6 to +7.4 | -1.2 | 3 / 4 / 1 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 8 | 37.9% | 46.1% | -8.1 | -13.2 to -2.9 | -9.7 | 2 / 5 / 1 | 0.453 |
| Clinical synopsis HPO F1, hierarchical ↑ | 8 | 58.6% | 65.3% | -6.8 | -13.6 to -0.6 | -5.3 | 2 / 5 / 1 | 0.453 |
| OMIM allelic variants recovered ↑ | 8 | 84.5% | 85.6% | -1.1 | -3.4 to +0.0 | +0.0 | 0 / 1 / 7 | 1.000 |
| Causal gene F1 ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Inheritance matches OMIM ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 616000-619999 — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 98.2% | 97.9% | +0.4 | -0.7 to +1.7 | +0.0 | 3 / 3 / 2 | 1.000 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 63.8% | 63.0% | +0.8 | -1.7 to +3.1 | +1.0 | 5 / 3 / 0 | 0.727 |
| Clinical synopsis HPO F1, exact ↑ | 8 | 39.6% | 42.5% | -2.8 | -7.1 to +2.2 | -4.2 | 2 / 5 / 1 | 0.453 |
| Clinical synopsis HPO F1, hierarchical ↑ | 8 | 57.8% | 58.0% | -0.3 | -3.8 to +4.0 | -0.7 | 3 / 4 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 8 | 80.9% | 80.9% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Causal gene F1 ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Inheritance matches OMIM ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 620000 onward — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 96.1% | 98.2% | -2.1 | -3.2 to -1.1 | -2.2 | 1 / 7 / 0 | 0.070 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 68.1% | 71.0% | -2.8 | -6.1 to +0.1 | -2.2 | 2 / 5 / 1 | 0.453 |
| Clinical synopsis HPO F1, exact ↑ | 8 | 40.5% | 39.5% | +1.0 | -4.5 to +7.0 | -1.4 | 3 / 5 / 0 | 0.727 |
| Clinical synopsis HPO F1, hierarchical ↑ | 8 | 58.4% | 56.4% | +2.0 | -3.3 to +8.3 | +0.9 | 5 / 3 / 0 | 0.727 |
| OMIM allelic variants recovered ↑ | 8 | 87.5% | 89.1% | -1.6 | -4.7 to +0.0 | +0.0 | 0 / 1 / 7 | 1.000 |
| Causal gene F1 ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Inheritance matches OMIM ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### classic (1xxxxx-5xxxxx) — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 97.3% | 97.4% | -0.1 | -1.4 to +1.4 | -0.3 | 2 / 4 / 2 | 0.688 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 36.8% | 35.3% | +1.5 | -0.4 to +3.6 | +0.7 | 4 / 2 / 2 | 0.688 |
| Clinical synopsis HPO F1, exact ↑ | 8 | 27.6% | 31.9% | -4.4 | -9.8 to +0.3 | -2.2 | 2 / 5 / 1 | 0.453 |
| Clinical synopsis HPO F1, hierarchical ↑ | 8 | 48.7% | 53.3% | -4.6 | -10.6 to +0.2 | -3.0 | 3 / 5 / 0 | 0.727 |
| OMIM allelic variants recovered ↑ | 8 | 48.4% | 48.4% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| Causal gene F1 ↑ | 8 | 91.7% | 83.3% | +8.3 | +0.0 to +25.0 | +0.0 | 1 / 0 / 7 | 1.000 |
| Inheritance matches OMIM ↑ | 8 | 87.5% | 87.5% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## By share of the entry's references readable as full text

### no full text (abstracts only) — 11 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 11 | 97.6% | 97.9% | -0.4 | -1.5 to +0.8 | -0.1 | 2 / 6 / 3 | 0.289 |
| Claims unsupported or contradicted ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| OMIM per-paper facts conveyed ↑ | 11 | 40.0% | 37.6% | +2.4 | +0.4 to +4.6 | +1.4 | 7 / 2 / 2 | 0.180 |
| Clinical synopsis HPO F1, exact ↑ | 11 | 32.7% | 36.1% | -3.4 | -7.5 to -0.1 | -1.8 | 2 / 6 / 3 | 0.289 |
| Clinical synopsis HPO F1, hierarchical ↑ | 11 | 52.1% | 55.2% | -3.1 | -7.8 to +0.6 | -1.3 | 4 / 6 / 1 | 0.754 |
| OMIM allelic variants recovered ↑ | 11 | 51.1% | 51.1% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Causal gene F1 ↑ | 11 | 94.0% | 87.9% | +6.1 | +0.0 to +18.2 | +0.0 | 1 / 0 / 10 | 1.000 |
| Inheritance matches OMIM ↑ | 11 | 81.8% | 90.9% | -9.1 | -27.3 to +0.0 | +0.0 | 0 / 1 / 10 | 1.000 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### under half full text — 7 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 7 | 97.5% | 97.5% | +0.0 | -1.5 to +1.5 | -0.3 | 3 / 4 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 7 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |
| OMIM per-paper facts conveyed ↑ | 7 | 57.4% | 55.2% | +2.2 | -0.9 to +5.7 | +1.3 | 4 / 3 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 7 | 38.9% | 40.4% | -1.5 | -4.2 to +1.6 | -1.8 | 2 / 5 / 0 | 0.453 |
| Clinical synopsis HPO F1, hierarchical ↑ | 7 | 55.2% | 56.6% | -1.4 | -4.5 to +1.8 | -1.2 | 2 / 5 / 0 | 0.453 |
| OMIM allelic variants recovered ↑ | 7 | 81.3% | 81.3% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |
| Causal gene F1 ↑ | 7 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |
| Inheritance matches OMIM ↑ | 7 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### half or more full text — 21 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 21 | 96.6% | 97.9% | -1.3 | -2.1 to -0.4 | -1.3 | 4 / 16 / 1 | 0.012 |
| Claims unsupported or contradicted ↓ | 21 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |
| OMIM per-paper facts conveyed ↑ | 21 | 70.0% | 71.8% | -1.8 | -4.4 to +0.6 | -1.1 | 7 / 12 / 2 | 0.359 |
| Clinical synopsis HPO F1, exact ↑ | 21 | 39.9% | 42.0% | -2.1 | -6.2 to +2.4 | -2.6 | 7 / 13 / 1 | 0.263 |
| Clinical synopsis HPO F1, hierarchical ↑ | 21 | 60.6% | 62.0% | -1.3 | -5.1 to +2.5 | +0.0 | 10 / 10 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 21 | 87.9% | 88.9% | -1.0 | -2.6 to +0.0 | +0.0 | 0 / 2 / 19 | 0.500 |
| Causal gene F1 ↑ | 21 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |
| Inheritance matches OMIM ↑ | 21 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 21 | – |

### all full text — 1 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 1 | 99.3% | 99.3% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Claims unsupported or contradicted ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| OMIM per-paper facts conveyed ↑ | 1 | 82.1% | 64.3% | +17.8 | – | +17.8 | 1 / 0 / 0 | 1.000 |
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
| Disease → causal gene | Evidence graph | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Direct reading | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Evidence graph | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Direct reading | 41 | 42 | 41 | 97.6% | 100.0% | 98.8% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 384 | 1,031 | 943 | 37.2% | 40.7% | 38.9% |
| Disease → phenotype (HPO, exact id) | Direct reading | 354 | 783 | 950 | 45.2% | 37.3% | 40.8% |
| Disease → allelic variant | Evidence graph | 121 | 182 | 171 | 66.5% | 70.8% | 68.6% |
| Disease → allelic variant | Direct reading | 123 | 147 | 171 | 83.7% | 71.9% | 77.4% |
