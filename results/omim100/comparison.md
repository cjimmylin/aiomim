# Evidence-graph strategy vs direct baseline — run `omim100`

97 entries, each written by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97 | 96.6% | 96.1% | +0.5 | -0.3 to +1.3 | 45 / 45 / 7 | 1.000 |
| Claims unsupported or contradicted ↓ | 97 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 97 | – |
| … same, before the repair round ↓ | 97 | 0.3% | 0.4% | -0.1 | -0.4 to +0.2 | 12 / 13 / 72 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 97 | 50.8% | 52.9% | -2.1 | -4.1 to -0.4 | 44 / 46 / 7 | 0.916 |
| … fully (no partial credit) ↑ | 97 | 42.8% | 44.5% | -1.7 | -3.7 to +0.1 | 47 / 43 / 7 | 0.752 |
| OMIM per-paper facts contradicted ↓ | 97 | 0.7% | 0.5% | +0.1 | -0.2 to +0.5 | 13 / 12 / 72 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 97 | 34.2% | 35.6% | -1.5 | -3.3 to +0.4 | 34 / 48 / 15 | 0.151 |
| … precision ↑ | 97 | 40.0% | 43.6% | -3.6 | -6.7 to -0.7 | 29 / 52 / 16 | 0.014 |
| … recall ↑ | 97 | 37.0% | 35.9% | +1.1 | -1.3 to +3.3 | 37 / 21 / 39 | 0.048 |
| Clinical synopsis HPO F1, hierarchical ↑ | 97 | 54.6% | 56.3% | -1.7 | -3.0 to -0.4 | 36 / 48 / 13 | 0.230 |
| Clinical synopsis HPO F1, semantic ↑ | 97 | 64.9% | 66.3% | -1.4 | -2.4 to -0.3 | 36 / 55 / 6 | 0.059 |
| OMIM allelic variants recovered ↑ | 97 | 65.6% | 67.6% | -2.1 | -5.5 to +1.4 | 4 / 10 / 83 | 0.180 |
| Causal gene F1 ↑ | 96 | 99.3% | 98.6% | +0.7 | +0.0 to +2.1 | 1 / 0 / 95 | 1.000 |
| Inheritance matches OMIM ↑ | 97 | 92.8% | 93.8% | -1.0 | -5.1 to +2.1 | 1 / 2 / 94 | 1.000 |
| OMIM references used ↑ | 97 | 93.8% | 94.5% | -0.8 | -3.4 to +1.6 | 10 / 8 / 79 | 0.815 |

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 11,218 | 10,038 |
| … supported | 10,883 | 9,698 |
| … partly supported | 335 | 340 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 5,525 | 5,530 |
| … conveyed | 2,333 | 2,429 |
| … partly conveyed | 897 | 934 |
| … missing | 2,262 | 2,131 |
| … contradicted | 33 | 36 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 1,524 | 76.5% | 79.1% | 0.7% | 0.5% |
| abstract | 3,657 | 42.0% | 43.9% | 0.6% | 0.8% |
| title | 344 | 22.7% | 23.1% | 0.3% | 0.0% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 19 | 95.6% | 96.0% | -0.4 | -2.4 to +1.4 | 8 / 11 / 0 | 0.648 |
| Claims unsupported or contradicted ↓ | 19 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 19 | – |
| OMIM per-paper facts conveyed ↑ | 19 | 56.1% | 55.7% | +0.4 | -2.2 to +3.0 | 11 / 7 / 1 | 0.481 |
| Clinical synopsis HPO F1, exact ↑ | 19 | 40.8% | 40.0% | +0.9 | -3.0 to +5.1 | 5 / 9 / 5 | 0.424 |
| Clinical synopsis HPO F1, hierarchical ↑ | 19 | 61.6% | 62.3% | -0.7 | -2.3 to +0.8 | 7 / 9 / 3 | 0.804 |
| OMIM allelic variants recovered ↑ | 19 | 68.7% | 72.2% | -3.5 | -9.7 to +0.0 | 0 / 2 / 17 | 0.500 |
| Causal gene F1 ↑ | 19 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 19 | – |
| Inheritance matches OMIM ↑ | 19 | 79.0% | 89.5% | -10.5 | -26.3 to +0.0 | 0 / 2 / 17 | 0.500 |

### 610000-615999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 97.0% | 95.6% | +1.4 | -0.7 to +4.3 | 9 / 9 / 2 | 1.000 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 52.1% | 53.4% | -1.3 | -4.0 to +1.1 | 9 / 11 / 0 | 0.824 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 32.1% | 36.5% | -4.4 | -9.3 to +0.7 | 7 / 11 / 2 | 0.481 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 50.5% | 54.2% | -3.7 | -7.1 to -0.5 | 6 / 10 / 4 | 0.455 |
| OMIM allelic variants recovered ↑ | 20 | 70.7% | 72.7% | -2.0 | -4.4 to +0.0 | 0 / 3 / 17 | 0.250 |
| Causal gene F1 ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 95.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |

### 616000-619999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 97.1% | 96.8% | +0.3 | -0.5 to +1.2 | 8 / 9 / 3 | 1.000 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 53.4% | 55.4% | -2.0 | -6.0 to +0.4 | 8 / 10 / 2 | 0.815 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 33.5% | 35.0% | -1.6 | -5.0 to +1.7 | 6 / 11 / 3 | 0.332 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 54.0% | 55.7% | -1.7 | -4.4 to +1.0 | 7 / 10 / 3 | 0.629 |
| OMIM allelic variants recovered ↑ | 20 | 82.1% | 81.1% | +1.0 | +0.0 to +3.0 | 1 / 0 / 19 | 1.000 |
| Causal gene F1 ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 95.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |

### 620000 onward — 18 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 18 | 96.5% | 97.0% | -0.5 | -2.2 to +1.1 | 9 / 9 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 18 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 18 | – |
| OMIM per-paper facts conveyed ↑ | 18 | 52.0% | 57.2% | -5.1 | -11.5 to -1.0 | 6 / 9 / 3 | 0.607 |
| Clinical synopsis HPO F1, exact ↑ | 18 | 35.0% | 34.4% | +0.5 | -2.6 to +3.8 | 8 / 8 / 2 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 18 | 54.5% | 54.2% | +0.3 | -2.3 to +3.5 | 8 / 8 / 2 | 1.000 |
| OMIM allelic variants recovered ↑ | 18 | 60.6% | 66.8% | -6.2 | -14.6 to +0.0 | 0 / 3 / 15 | 0.250 |
| Causal gene F1 ↑ | 18 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 18 | – |
| Inheritance matches OMIM ↑ | 18 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 18 | – |

### classic (1xxxxx-5xxxxx) — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 96.8% | 95.4% | +1.4 | -0.1 to +3.0 | 11 / 7 / 2 | 0.481 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 40.9% | 43.4% | -2.5 | -8.3 to +1.2 | 10 / 9 / 1 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 29.9% | 32.4% | -2.5 | -6.8 to +1.3 | 8 / 9 / 3 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 52.8% | 55.2% | -2.5 | -6.2 to +1.1 | 8 / 11 / 1 | 0.648 |
| OMIM allelic variants recovered ↑ | 20 | 45.6% | 45.6% | +0.0 | -14.4 to +15.0 | 3 / 2 / 15 | 1.000 |
| Causal gene F1 ↑ | 19 | 96.5% | 93.0% | +3.5 | +0.0 to +10.5 | 1 / 0 / 18 | 1.000 |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 90.0% | +5.0 | +0.0 to +15.0 | 1 / 0 / 19 | 1.000 |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 46 | 95.9% | 95.0% | +0.9 | -0.5 to +2.6 | 20 / 21 / 5 | 1.000 |
| Claims unsupported or contradicted ↓ | 46 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 46 | – |
| OMIM per-paper facts conveyed ↑ | 46 | 39.5% | 40.1% | -0.7 | -1.8 to +0.3 | 21 / 21 / 4 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 46 | 30.4% | 29.9% | +0.4 | -2.5 to +3.3 | 20 / 15 / 11 | 0.500 |
| Clinical synopsis HPO F1, hierarchical ↑ | 46 | 49.2% | 50.0% | -0.8 | -2.7 to +0.9 | 19 / 16 / 11 | 0.736 |
| OMIM allelic variants recovered ↑ | 46 | 48.9% | 48.4% | +0.4 | -4.6 to +6.4 | 4 / 3 / 39 | 1.000 |
| Causal gene F1 ↑ | 45 | 98.5% | 97.0% | +1.5 | +0.0 to +4.5 | 1 / 0 / 44 | 1.000 |
| Inheritance matches OMIM ↑ | 46 | 89.1% | 91.3% | -2.2 | -8.7 to +4.3 | 1 / 2 / 43 | 1.000 |

### under half full text — 27 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 27 | 97.3% | 96.5% | +0.8 | -0.1 to +1.8 | 18 / 9 / 0 | 0.122 |
| Claims unsupported or contradicted ↓ | 27 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 27 | – |
| OMIM per-paper facts conveyed ↑ | 27 | 54.5% | 55.9% | -1.5 | -6.1 to +2.0 | 16 / 10 / 1 | 0.327 |
| Clinical synopsis HPO F1, exact ↑ | 27 | 35.6% | 39.3% | -3.8 | -6.3 to -1.3 | 7 / 18 / 2 | 0.043 |
| Clinical synopsis HPO F1, hierarchical ↑ | 27 | 58.7% | 61.1% | -2.4 | -4.0 to -0.9 | 7 / 19 / 1 | 0.029 |
| OMIM allelic variants recovered ↑ | 27 | 74.7% | 80.2% | -5.5 | -13.6 to -0.5 | 0 / 4 / 23 | 0.125 |
| Causal gene F1 ↑ | 27 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 27 | – |
| Inheritance matches OMIM ↑ | 27 | 92.6% | 92.6% | +0.0 | +0.0 to +0.0 | 0 / 0 / 27 | – |

### half or more full text — 22 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 22 | 96.9% | 97.9% | -1.0 | -1.8 to -0.1 | 6 / 15 / 1 | 0.078 |
| Claims unsupported or contradicted ↓ | 22 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 22 | – |
| OMIM per-paper facts conveyed ↑ | 22 | 69.5% | 73.7% | -4.2 | -7.9 to -1.2 | 6 / 14 / 2 | 0.115 |
| Clinical synopsis HPO F1, exact ↑ | 22 | 39.0% | 41.1% | -2.1 | -6.1 to +2.1 | 7 / 14 / 1 | 0.189 |
| Clinical synopsis HPO F1, hierarchical ↑ | 22 | 59.5% | 61.5% | -2.0 | -5.9 to +1.9 | 10 / 11 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 22 | 88.4% | 89.4% | -1.0 | -2.5 to +0.0 | 0 / 2 / 20 | 0.500 |
| Causal gene F1 ↑ | 22 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 22 | – |
| Inheritance matches OMIM ↑ | 22 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 22 | – |

### all full text — 2 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 2 | 99.2% | 98.6% | +0.7 | – | 1 / 0 / 1 | 1.000 |
| Claims unsupported or contradicted ↓ | 2 | 0.0% | 0.0% | +0.0 | – | 0 / 0 / 2 | – |
| OMIM per-paper facts conveyed ↑ | 2 | 57.0% | 77.8% | -20.7 | – | 1 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 2 | 49.8% | 56.9% | -7.1 | – | 0 / 1 / 1 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 2 | 69.9% | 79.7% | -9.8 | – | 0 / 2 / 0 | 0.500 |
| OMIM allelic variants recovered ↑ | 2 | 75.0% | 100.0% | -25.0 | – | 0 / 1 / 1 | 1.000 |
| Causal gene F1 ↑ | 2 | 100.0% | 100.0% | +0.0 | – | 0 / 0 / 2 | – |
| Inheritance matches OMIM ↑ | 2 | 100.0% | 100.0% | +0.0 | – | 0 / 0 / 2 | – |

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
