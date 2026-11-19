# Evidence-graph strategy vs direct baseline — run `recent`

23 entries, each written in full by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better. An entry with no draft, or one for which a per-paper extraction call failed, is left out (7: 621639, 621644, 621667, 621671, 621704, 621707, 621728). Where a strategy predicted nothing against a non-empty gold set, F1 and recall count as 0.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 23 | 95.9% | 95.9% | -0.1 | -1.2 to +1.4 | -0.1 | 10 / 13 / 0 | 0.678 |
| Claims unsupported or contradicted ↓ | 23 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 23 | – |
| … same, before the repair round ↓ | 23 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 3 / 20 | 0.250 |
| … unsupported, before the repair round ↓ | 23 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 1 / 22 | 1.000 |
| … contradicted, before the repair round ↓ | 23 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 2 / 21 | 0.500 |
| OMIM per-paper facts conveyed ↑ | 23 | 53.6% | 53.9% | -0.2 | -2.2 to +1.8 | -0.3 | 7 / 12 / 4 | 0.359 |
| … fully (no partial credit) ↑ | 23 | 47.1% | 47.3% | -0.2 | -2.6 to +2.2 | -1.3 | 6 / 12 / 5 | 0.238 |
| OMIM per-paper facts contradicted ↓ | 23 | 1.1% | 0.8% | +0.3 | -0.2 to +0.9 | +0.0 | 4 / 5 / 14 | 1.000 |
| … facts split afresh for each draft (earlier scoring) ↑ | 23 | 54.4% | 54.2% | +0.2 | -1.8 to +2.3 | -1.3 | 10 / 13 / 0 | 0.678 |
| Clinical synopsis HPO F1, exact ↑ | 1 | 62.1% | 42.7% | +19.4 | – | +19.4 | 1 / 0 / 0 | 1.000 |
| … precision ↑ | 23 | 2.9% | 3.2% | -0.2 | -0.7 to +0.0 | +0.0 | 0 / 1 / 22 | 1.000 |
| … recall ↑ | 1 | 57.1% | 30.2% | +26.9 | – | +26.9 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 1 | 78.7% | 58.3% | +20.4 | – | +20.4 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, semantic ↑ | 1 | 82.9% | 69.0% | +13.9 | – | +13.9 | 1 / 0 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 23 | 73.1% | 66.1% | +7.0 | -0.0 to +15.2 | +0.0 | 6 / 1 / 16 | 0.125 |
| Generated variants that are OMIM variants (precision) ↑ | 21 | 84.5% | 84.9% | -0.4 | -6.4 to +4.7 | +0.0 | 4 / 3 / 14 | 1.000 |
| Causal gene F1 ↑ | 23 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 23 | – |
| … recall ↑ | 23 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 23 | – |
| Inheritance matches OMIM ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance error: none stated ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance error: a mode missing ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance error: an extra mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance error: a different mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| OMIM references used ↑ | 23 | 98.8% | 98.8% | +0.0 | -2.6 to +2.6 | +0.0 | 1 / 1 / 21 | 1.000 |

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 3,240 | 2,771 |
| … supported | 3,131 | 2,690 |
| … partly supported | 109 | 81 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 1,718 | 1,718 |
| … conveyed | 796 | 787 |
| … partly conveyed | 234 | 232 |
| … missing | 673 | 685 |
| … contradicted | 15 | 14 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 533 | 83.2% | 78.9% | 1.3% | 1.1% |
| abstract | 1,124 | 40.0% | 40.8% | 0.7% | 0.7% |
| title | 61 | 33.6% | 39.3% | 0.0% | 0.0% |

## By creation era (MIM number range)

### 620000 onward — 22 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 22 | 95.8% | 95.8% | -0.0 | -1.3 to +1.4 | -0.1 | 10 / 12 / 0 | 0.832 |
| Claims unsupported or contradicted ↓ | 22 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 22 | – |
| OMIM per-paper facts conveyed ↑ | 22 | 52.7% | 53.6% | -0.9 | -2.6 to +0.7 | -0.5 | 6 / 12 / 4 | 0.238 |
| Clinical synopsis HPO F1, exact ↑ | 1 | 62.1% | 42.7% | +19.4 | – | +19.4 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 1 | 78.7% | 58.3% | +20.4 | – | +20.4 | 1 / 0 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 22 | 71.9% | 66.1% | +5.8 | -1.2 to +14.2 | +0.0 | 5 / 1 / 16 | 0.219 |
| Causal gene F1 ↑ | 22 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 22 | – |
| Inheritance matches OMIM ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |

### classic (1xxxxx-5xxxxx) — 1 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 1 | 98.4% | 99.0% | -0.6 | – | -0.6 | 0 / 1 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| OMIM per-paper facts conveyed ↑ | 1 | 74.0% | 59.8% | +14.2 | – | +14.2 | 1 / 0 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 1 | 100.0% | 66.7% | +33.3 | – | +33.3 | 1 / 0 / 0 | 1.000 |
| Causal gene F1 ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## By share of the entry's references readable as full text

### no full text (abstracts only) — 6 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 6 | 93.5% | 92.6% | +0.9 | -2.2 to +5.1 | +0.1 | 3 / 3 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 6 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 6 | – |
| OMIM per-paper facts conveyed ↑ | 6 | 38.4% | 38.0% | +0.4 | -1.9 to +3.0 | -0.1 | 2 / 3 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 6 | 51.2% | 35.3% | +15.9 | +0.0 to +38.1 | +0.0 | 2 / 0 / 4 | 0.500 |
| Causal gene F1 ↑ | 6 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 6 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### under half full text — 8 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 8 | 96.1% | 96.7% | -0.6 | -1.7 to +0.7 | -1.1 | 3 / 5 / 0 | 0.727 |
| Claims unsupported or contradicted ↓ | 8 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |
| OMIM per-paper facts conveyed ↑ | 8 | 48.3% | 50.1% | -1.8 | -4.7 to +0.4 | -0.4 | 2 / 4 / 2 | 0.688 |
| OMIM allelic variants recovered ↑ | 8 | 72.2% | 70.6% | +1.6 | -10.9 to +12.5 | +0.0 | 2 / 1 / 5 | 1.000 |
| Causal gene F1 ↑ | 8 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 8 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### half or more full text — 7 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 7 | 97.3% | 97.1% | +0.2 | -1.5 to +1.8 | -0.1 | 3 / 4 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 7 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |
| OMIM per-paper facts conveyed ↑ | 7 | 64.3% | 64.4% | -0.2 | -4.3 to +5.2 | -1.1 | 2 / 4 / 1 | 0.688 |
| OMIM allelic variants recovered ↑ | 7 | 87.6% | 80.0% | +7.6 | +0.0 to +18.1 | +0.0 | 2 / 0 / 5 | 0.500 |
| Causal gene F1 ↑ | 7 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 7 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### all full text — 2 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 2 | 97.1% | 99.0% | -1.8 | – | -1.8 | 1 / 1 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 2 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 2 | – |
| OMIM per-paper facts conveyed ↑ | 2 | 83.5% | 80.0% | +3.5 | – | +3.5 | 1 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 1 | 62.1% | 42.7% | +19.4 | – | +19.4 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 1 | 78.7% | 58.3% | +20.4 | – | +20.4 | 1 / 0 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 2 | 91.6% | 91.6% | +0.0 | – | +0.0 | 0 / 0 / 2 | – |
| Causal gene F1 ↑ | 2 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 2 | – |
| Inheritance matches OMIM ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 28 | 28 | 30 | 100.0% | 93.3% | 96.5% |
| Disease → causal gene | Direct reading | 28 | 28 | 30 | 100.0% | 93.3% | 96.5% |
| Disease → mode of inheritance | Evidence graph | 1 | 30 | 1 | 3.3% | 100.0% | 6.5% |
| Disease → mode of inheritance | Direct reading | 1 | 28 | 1 | 3.6% | 100.0% | 6.9% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 40 | 624 | 67 | 6.4% | 59.7% | 11.6% |
| Disease → phenotype (HPO, exact id) | Direct reading | 25 | 538 | 69 | 4.7% | 36.2% | 8.2% |
| Disease → allelic variant | Evidence graph | 82 | 130 | 118 | 63.1% | 69.5% | 66.1% |
| Disease → allelic variant | Direct reading | 75 | 99 | 119 | 75.8% | 63.0% | 68.8% |
