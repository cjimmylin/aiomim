# Evidence-graph strategy vs direct baseline — run `omim100`

100 entries, each written by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97 | 96.5% | 96.1% | +0.4 | -0.4 to +1.3 | 44 / 47 / 6 | 0.834 |
| Claims unsupported or contradicted ↓ | 97 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 1 / 96 | 1.000 |
| … same, before the repair round ↓ | 97 | 0.3% | 0.4% | -0.1 | -0.4 to +0.2 | 13 / 13 / 71 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 100 | 50.9% | 51.4% | -0.4 | -3.3 to +2.8 | 44 / 49 / 7 | 0.678 |
| … fully (no partial credit) ↑ | 100 | 43.2% | 43.2% | +0.0 | -2.8 to +3.1 | 49 / 43 / 8 | 0.602 |
| OMIM per-paper facts contradicted ↓ | 100 | 0.8% | 0.5% | +0.2 | -0.1 to +0.7 | 12 / 14 / 74 | 0.845 |
| Clinical synopsis HPO F1, exact ↑ | 97 | 34.2% | 35.6% | -1.5 | -3.3 to +0.4 | 34 / 48 / 15 | 0.151 |
| … precision ↑ | 97 | 40.1% | 43.6% | -3.5 | -6.7 to -0.6 | 29 / 52 / 16 | 0.014 |
| … recall ↑ | 100 | 37.1% | 34.8% | +2.3 | -0.3 to +4.9 | 40 / 21 / 39 | 0.020 |
| Clinical synopsis HPO F1, hierarchical ↑ | 97 | 54.6% | 56.3% | -1.7 | -3.0 to -0.4 | 36 / 48 / 13 | 0.230 |
| Clinical synopsis HPO F1, semantic ↑ | 97 | 64.9% | 66.3% | -1.4 | -2.4 to -0.4 | 36 / 55 / 6 | 0.059 |
| OMIM allelic variants recovered ↑ | 100 | 65.8% | 65.6% | +0.2 | -4.2 to +4.7 | 7 / 11 / 82 | 0.481 |
| Causal gene F1 ↑ | 96 | 99.3% | 98.6% | +0.7 | +0.0 to +2.1 | 1 / 0 / 95 | 1.000 |
| Inheritance matches OMIM ↑ | 100 | 92.0% | 91.0% | +1.0 | -3.0 to +6.0 | 3 / 2 / 95 | 1.000 |
| OMIM references used ↑ | 100 | 93.0% | 91.4% | +1.7 | -1.8 to +5.6 | 11 / 9 / 80 | 0.824 |

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 11,120 | 10,040 |
| … supported | 10,786 | 9,694 |
| … partly supported | 333 | 346 |
| … unsupported | 1 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 5,663 | 5,663 |
| … conveyed | 2,411 | 2,431 |
| … partly conveyed | 879 | 932 |
| … missing | 2,330 | 2,263 |
| … contradicted | 43 | 37 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 1,565 | 75.8% | 77.2% | 0.8% | 0.5% |
| abstract | 3,728 | 42.1% | 43.0% | 0.8% | 0.8% |
| title | 370 | 25.4% | 21.5% | 0.5% | 0.0% |

## By creation era (MIM number range)

### 600000-609999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 19 | 95.6% | 96.0% | -0.4 | -2.3 to +1.3 | 9 / 10 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 19 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | 0 / 1 / 18 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 20 | 56.6% | 52.9% | +3.7 | -1.7 to +11.8 | 12 / 7 / 1 | 0.359 |
| Clinical synopsis HPO F1, exact ↑ | 19 | 40.8% | 40.0% | +0.9 | -3.0 to +5.1 | 5 / 9 / 5 | 0.424 |
| Clinical synopsis HPO F1, hierarchical ↑ | 19 | 61.6% | 62.3% | -0.7 | -2.3 to +0.8 | 7 / 9 / 3 | 0.804 |
| OMIM allelic variants recovered ↑ | 20 | 70.3% | 68.6% | +1.7 | -7.5 to +14.2 | 1 / 2 / 17 | 1.000 |
| Causal gene F1 ↑ | 19 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 19 | – |
| Inheritance matches OMIM ↑ | 20 | 80.0% | 85.0% | -5.0 | -20.0 to +10.0 | 1 / 2 / 17 | 1.000 |

### 610000-615999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 96.8% | 95.6% | +1.2 | -0.9 to +4.2 | 9 / 9 / 2 | 1.000 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 51.9% | 53.4% | -1.5 | -4.7 to +1.3 | 8 / 12 / 0 | 0.503 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 32.1% | 36.5% | -4.4 | -9.2 to +0.6 | 7 / 11 / 2 | 0.481 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 50.5% | 54.2% | -3.7 | -7.2 to -0.6 | 6 / 10 / 4 | 0.455 |
| OMIM allelic variants recovered ↑ | 20 | 69.9% | 72.7% | -2.8 | -5.7 to -0.6 | 0 / 4 / 16 | 0.125 |
| Causal gene F1 ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 95.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |

### 616000-619999 — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 96.7% | 96.5% | +0.2 | -0.9 to +1.4 | 6 / 11 / 3 | 0.332 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 53.4% | 55.4% | -2.0 | -6.0 to +0.7 | 9 / 10 / 1 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 33.6% | 35.0% | -1.4 | -4.7 to +1.9 | 6 / 11 / 3 | 0.332 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 54.1% | 55.7% | -1.6 | -4.3 to +1.1 | 7 / 10 / 3 | 0.629 |
| OMIM allelic variants recovered ↑ | 20 | 82.1% | 81.1% | +1.0 | +0.0 to +3.0 | 1 / 0 / 19 | 1.000 |
| Causal gene F1 ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 95.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |

### 620000 onward — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 18 | 96.7% | 96.9% | -0.2 | -1.9 to +1.5 | 8 / 10 / 0 | 0.815 |
| Claims unsupported or contradicted ↓ | 18 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 18 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 51.7% | 51.6% | +0.1 | -9.5 to +12.7 | 6 / 10 / 4 | 0.455 |
| Clinical synopsis HPO F1, exact ↑ | 18 | 35.0% | 34.4% | +0.5 | -2.6 to +3.8 | 8 / 8 / 2 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 18 | 54.5% | 54.2% | +0.3 | -2.2 to +3.4 | 8 / 8 / 2 | 1.000 |
| OMIM allelic variants recovered ↑ | 20 | 61.2% | 60.1% | +1.0 | -10.6 to +14.4 | 2 / 3 / 15 | 1.000 |
| Causal gene F1 ↑ | 18 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 18 | – |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 90.0% | +5.0 | +0.0 to +15.0 | 1 / 0 / 19 | 1.000 |

### classic (1xxxxx-5xxxxx) — 20 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 20 | 96.6% | 95.4% | +1.2 | -0.1 to +2.8 | 12 / 7 / 1 | 0.359 |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 20 | – |
| OMIM per-paper facts conveyed ↑ | 20 | 41.0% | 43.4% | -2.5 | -8.9 to +1.6 | 9 / 10 / 1 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 20 | 29.9% | 32.4% | -2.5 | -6.9 to +1.2 | 8 / 9 / 3 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 20 | 52.8% | 55.2% | -2.5 | -6.2 to +1.1 | 8 / 11 / 1 | 0.648 |
| OMIM allelic variants recovered ↑ | 20 | 45.6% | 45.6% | +0.0 | -14.4 to +14.4 | 3 / 2 / 15 | 1.000 |
| Causal gene F1 ↑ | 19 | 96.5% | 93.0% | +3.5 | +0.0 to +10.5 | 1 / 0 / 18 | 1.000 |
| Inheritance matches OMIM ↑ | 20 | 95.0% | 90.0% | +5.0 | +0.0 to +15.0 | 1 / 0 / 19 | 1.000 |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 46 | 95.9% | 95.0% | +0.9 | -0.6 to +2.5 | 21 / 21 / 4 | 1.000 |
| Claims unsupported or contradicted ↓ | 46 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 46 | – |
| OMIM per-paper facts conveyed ↑ | 46 | 39.8% | 40.1% | -0.3 | -1.5 to +0.8 | 21 / 21 / 4 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 46 | 30.4% | 29.9% | +0.4 | -2.5 to +3.2 | 20 / 15 / 11 | 0.500 |
| Clinical synopsis HPO F1, hierarchical ↑ | 46 | 49.2% | 50.0% | -0.8 | -2.7 to +1.0 | 19 / 16 / 11 | 0.736 |
| OMIM allelic variants recovered ↑ | 46 | 48.9% | 48.4% | +0.4 | -4.6 to +6.5 | 4 / 3 / 39 | 1.000 |
| Causal gene F1 ↑ | 45 | 98.5% | 97.0% | +1.5 | +0.0 to +4.5 | 1 / 0 / 44 | 1.000 |
| Inheritance matches OMIM ↑ | 46 | 89.1% | 91.3% | -2.2 | -8.7 to +4.3 | 1 / 2 / 43 | 1.000 |

### under half full text — 28 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 27 | 97.0% | 96.5% | +0.6 | -0.4 to +1.5 | 17 / 10 / 0 | 0.248 |
| Claims unsupported or contradicted ↓ | 27 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | 0 / 1 / 26 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 28 | 54.6% | 54.0% | +0.7 | -5.7 to +7.6 | 15 / 13 / 0 | 0.851 |
| Clinical synopsis HPO F1, exact ↑ | 27 | 35.6% | 39.3% | -3.8 | -6.3 to -1.3 | 7 / 18 / 2 | 0.043 |
| Clinical synopsis HPO F1, hierarchical ↑ | 27 | 58.7% | 61.1% | -2.4 | -4.1 to -0.8 | 7 / 19 / 1 | 0.029 |
| OMIM allelic variants recovered ↑ | 28 | 76.8% | 77.3% | -0.5 | -11.3 to +10.1 | 2 / 4 / 22 | 0.688 |
| Causal gene F1 ↑ | 27 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 27 | – |
| Inheritance matches OMIM ↑ | 28 | 92.9% | 89.3% | +3.6 | +0.0 to +10.7 | 1 / 0 / 27 | 1.000 |

### half or more full text — 23 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 22 | 96.9% | 97.6% | -0.8 | -1.7 to +0.4 | 5 / 16 / 1 | 0.027 |
| Claims unsupported or contradicted ↓ | 22 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 22 | – |
| OMIM per-paper facts conveyed ↑ | 23 | 66.0% | 70.5% | -4.5 | -8.3 to -1.5 | 6 / 14 / 3 | 0.115 |
| Clinical synopsis HPO F1, exact ↑ | 22 | 39.1% | 41.1% | -2.0 | -6.0 to +2.1 | 7 / 14 / 1 | 0.189 |
| Clinical synopsis HPO F1, hierarchical ↑ | 22 | 59.5% | 61.5% | -2.0 | -5.8 to +1.9 | 10 / 11 / 1 | 1.000 |
| OMIM allelic variants recovered ↑ | 23 | 83.9% | 85.5% | -1.7 | -3.7 to +0.0 | 0 / 3 / 20 | 0.250 |
| Causal gene F1 ↑ | 22 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | 0 / 0 / 22 | – |
| Inheritance matches OMIM ↑ | 23 | 100.0% | 95.7% | +4.3 | +0.0 to +13.0 | 1 / 0 / 22 | 1.000 |

### all full text — 3 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 2 | 99.2% | 97.6% | +1.7 | – | 1 / 0 / 1 | 1.000 |
| Claims unsupported or contradicted ↓ | 2 | 0.0% | 0.0% | +0.0 | – | 0 / 0 / 2 | – |
| OMIM per-paper facts conveyed ↑ | 3 | 71.0% | 52.6% | +18.3 | – | 2 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 2 | 49.8% | 56.9% | -7.1 | – | 0 / 1 / 1 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 2 | 69.9% | 79.7% | -9.8 | – | 0 / 2 / 0 | 0.500 |
| OMIM allelic variants recovered ↑ | 3 | 83.3% | 66.7% | +16.7 | – | 1 / 1 / 1 | 1.000 |
| Causal gene F1 ↑ | 2 | 100.0% | 100.0% | +0.0 | – | 0 / 0 / 2 | – |
| Inheritance matches OMIM ↑ | 3 | 66.7% | 66.7% | +0.0 | – | 0 / 0 / 3 | – |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 102 | 103 | 105 | 99.0% | 97.1% | 98.1% |
| Disease → causal gene | Direct | 99 | 100 | 105 | 99.0% | 94.3% | 96.6% |
| Disease → mode of inheritance | Evidence graph | 98 | 103 | 103 | 95.2% | 95.2% | 95.2% |
| Disease → mode of inheritance | Direct | 98 | 102 | 103 | 96.1% | 95.2% | 95.6% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 767 | 2,042 | 2,327 | 37.6% | 33.0% | 35.1% |
| Disease → phenotype (HPO, exact id) | Direct | 689 | 1,559 | 2,344 | 44.2% | 29.4% | 35.3% |
| Disease → allelic variant | Evidence graph | 271 | 382 | 428 | 70.9% | 63.3% | 66.9% |
| Disease → allelic variant | Direct | 274 | 314 | 428 | 87.3% | 64.0% | 73.9% |
