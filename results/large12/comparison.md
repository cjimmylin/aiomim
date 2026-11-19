# Evidence-graph strategy vs direct baseline — run `large12`

11 entries, each written in full by both strategies from the same papers. Per-entry scores are paired; the difference is graph minus direct in percentage points, with a bootstrap 95% confidence interval over entries. ↑ higher is better, ↓ lower is better. An entry with no draft, or one for which a per-paper extraction call failed, is left out (1: 180300). Where a strategy predicted nothing against a non-empty gold set, F1 and recall count as 0.

## All entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 11 | 97.2% | 97.9% | -0.7 | -1.3 to +0.0 | -1.2 | 2 / 8 / 1 | 0.109 |
| Claims unsupported or contradicted ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 1 / 10 | 1.000 |
| … same, before the repair round ↓ | 11 | 0.1% | 0.2% | -0.1 | -0.2 to +0.1 | +0.0 | 3 / 3 / 5 | 1.000 |
| … unsupported, before the repair round ↓ | 11 | 0.1% | 0.2% | -0.0 | -0.2 to +0.1 | +0.0 | 3 / 3 / 5 | 1.000 |
| … contradicted, before the repair round ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| OMIM per-paper facts conveyed ↑ | 11 | 47.0% | 46.6% | +0.4 | -2.9 to +3.7 | +0.2 | 6 / 5 / 0 | 1.000 |
| … fully (no partial credit) ↑ | 11 | 38.1% | 38.0% | +0.1 | -3.7 to +3.6 | -0.1 | 5 / 6 / 0 | 1.000 |
| OMIM per-paper facts contradicted ↓ | 11 | 0.9% | 0.7% | +0.2 | -0.3 to +0.9 | +0.0 | 2 / 2 / 7 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 11 | 28.8% | 33.1% | -4.4 | -8.0 to -0.5 | -5.5 | 2 / 8 / 1 | 0.109 |
| … precision ↑ | 11 | 22.3% | 34.9% | -12.7 | -19.6 to -6.2 | -9.5 | 2 / 9 / 0 | 0.065 |
| … recall ↑ | 11 | 53.5% | 40.8% | +12.7 | +6.5 to +19.8 | +12.0 | 8 / 0 / 3 | 0.008 |
| Clinical synopsis HPO F1, hierarchical ↑ | 11 | 50.5% | 54.4% | -3.9 | -6.9 to -0.8 | -5.2 | 2 / 9 / 0 | 0.065 |
| Clinical synopsis HPO F1, semantic ↑ | 11 | 64.5% | 64.7% | -0.2 | -2.6 to +2.3 | +0.8 | 6 / 5 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 11 | 53.4% | 53.4% | -0.1 | -11.9 to +9.3 | +0.0 | 4 / 2 / 5 | 0.688 |
| Generated variants that are OMIM variants (precision) ↑ | 11 | 51.2% | 64.5% | -13.3 | -21.5 to -5.3 | -16.9 | 0 / 6 / 5 | 0.031 |
| Causal gene F1 ↑ | 11 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| … recall ↑ | 11 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Inheritance matches OMIM ↑ | 11 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Inheritance error: none stated ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Inheritance error: a mode missing ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Inheritance error: an extra mode ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| Inheritance error: a different mode ↓ | 11 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 11 | – |
| OMIM references used ↑ | 11 | 96.9% | 96.7% | +0.2 | -1.7 to +2.1 | +0.0 | 3 / 2 / 6 | 1.000 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## Pooled counts

| | Evidence graph | Direct |
|---|---|---|
| Claims audited | 4,457 | 3,300 |
| … supported | 4,332 | 3,225 |
| … partly supported | 124 | 75 |
| … unsupported | 1 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 1,087 | 1,089 |
| … conveyed | 429 | 420 |
| … partly conveyed | 186 | 182 |
| … missing | 466 | 480 |
| … contradicted | 6 | 7 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Facts | Evidence graph coverage | Direct coverage | Graph contradicted | Direct contradicted |
|---|---|---|---|---|---|
| fulltext | 47 | 89.4% | 80.0% | 0.0% | 0.0% |
| abstract | 920 | 47.8% | 47.8% | 0.4% | 0.5% |
| title | 120 | 33.3% | 27.0% | 1.7% | 1.6% |

## By creation era (MIM number range)

### 600000-609999 — 4 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 4 | 96.9% | 97.1% | -0.2 | – | -0.7 | 1 / 3 / 0 | 0.625 |
| Claims unsupported or contradicted ↓ | 4 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 4 | – |
| OMIM per-paper facts conveyed ↑ | 4 | 56.1% | 54.6% | +1.5 | – | +1.6 | 3 / 1 / 0 | 0.625 |
| Clinical synopsis HPO F1, exact ↑ | 4 | 32.5% | 42.9% | -10.4 | – | -11.2 | 0 / 4 / 0 | 0.125 |
| Clinical synopsis HPO F1, hierarchical ↑ | 4 | 51.5% | 59.7% | -8.2 | – | -8.5 | 0 / 4 / 0 | 0.125 |
| OMIM allelic variants recovered ↑ | 4 | 75.9% | 75.3% | +0.6 | – | +0.0 | 1 / 1 / 2 | 1.000 |
| Causal gene F1 ↑ | 4 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 4 | – |
| Inheritance matches OMIM ↑ | 4 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 4 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 610000-615999 — 3 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 3 | 97.6% | 98.2% | -0.6 | – | -0.1 | 0 / 2 / 1 | 0.500 |
| Claims unsupported or contradicted ↓ | 3 | 0.1% | 0.0% | +0.1 | – | +0.0 | 0 / 1 / 2 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 3 | 45.5% | 42.8% | +2.7 | – | -1.5 | 1 / 2 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 3 | 32.9% | 39.3% | -6.3 | – | -5.5 | 0 / 3 / 0 | 0.250 |
| Clinical synopsis HPO F1, hierarchical ↑ | 3 | 59.4% | 58.6% | +0.7 | – | -0.6 | 1 / 2 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 3 | 38.3% | 34.2% | +4.2 | – | +0.0 | 1 / 0 / 2 | 1.000 |
| Causal gene F1 ↑ | 3 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 3 | – |
| Inheritance matches OMIM ↑ | 3 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 3 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### 620000 onward — 1 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 1 | 95.9% | 97.6% | -1.7 | – | -1.7 | 0 / 1 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| OMIM per-paper facts conveyed ↑ | 1 | 41.0% | 52.4% | -11.4 | – | -11.4 | 0 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 1 | 11.7% | 4.3% | +7.4 | – | +7.4 | 1 / 0 / 0 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 1 | 21.6% | 28.9% | -7.3 | – | -7.3 | 0 / 1 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 1 | 25.0% | 75.0% | -50.0 | – | -50.0 | 0 / 1 / 0 | 1.000 |
| Causal gene F1 ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |
| Inheritance matches OMIM ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### classic (1xxxxx-5xxxxx) — 3 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 3 | 97.6% | 98.6% | -1.0 | – | -1.2 | 1 / 2 / 0 | 1.000 |
| Claims unsupported or contradicted ↓ | 3 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 3 | – |
| OMIM per-paper facts conveyed ↑ | 3 | 38.4% | 37.8% | +0.6 | – | +0.6 | 2 / 1 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 3 | 25.4% | 23.7% | +1.7 | – | +0.0 | 1 / 1 / 1 | 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | 3 | 50.1% | 51.8% | -1.8 | – | -1.6 | 1 / 2 / 0 | 1.000 |
| OMIM allelic variants recovered ↑ | 3 | 47.8% | 36.4% | +11.4 | – | +14.3 | 2 / 0 / 1 | 0.500 |
| Causal gene F1 ↑ | 3 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 3 | – |
| Inheritance matches OMIM ↑ | 3 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 3 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## By share of the entry's references readable as full text

### no full text (abstracts only) — 5 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 5 | 97.7% | 98.4% | -0.8 | -1.6 to +0.0 | -0.1 | 1 / 3 / 1 | 0.625 |
| Claims unsupported or contradicted ↓ | 5 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 1 / 4 | 1.000 |
| OMIM per-paper facts conveyed ↑ | 5 | 38.6% | 37.8% | +0.9 | -2.9 to +6.2 | -1.5 | 2 / 3 / 0 | 1.000 |
| Clinical synopsis HPO F1, exact ↑ | 5 | 28.2% | 30.9% | -2.7 | -6.8 to +1.7 | -4.1 | 1 / 3 / 1 | 0.625 |
| Clinical synopsis HPO F1, hierarchical ↑ | 5 | 55.4% | 57.2% | -1.8 | -6.0 to +1.7 | -0.8 | 1 / 4 / 0 | 0.375 |
| OMIM allelic variants recovered ↑ | 5 | 31.7% | 26.3% | +5.4 | +0.0 to +11.1 | +0.0 | 2 / 0 / 3 | 0.500 |
| Causal gene F1 ↑ | 5 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 5 | – |
| Inheritance matches OMIM ↑ | 5 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 5 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### under half full text — 6 entries

| Metric | n | Evidence graph | Direct | Difference (pp) | 95% CI (pp) | Median difference (pp) | Graph better / direct better / tie | Sign test p |
|---|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 6 | 96.8% | 97.4% | -0.7 | -1.5 to +0.5 | -1.2 | 1 / 5 / 0 | 0.219 |
| Claims unsupported or contradicted ↓ | 6 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 6 | – |
| OMIM per-paper facts conveyed ↑ | 6 | 54.0% | 53.9% | +0.0 | -4.8 to +3.7 | +1.6 | 4 / 2 / 0 | 0.688 |
| Clinical synopsis HPO F1, exact ↑ | 6 | 29.3% | 35.0% | -5.8 | -11.1 to +0.4 | -8.5 | 1 / 5 / 0 | 0.219 |
| Clinical synopsis HPO F1, hierarchical ↑ | 6 | 46.5% | 52.2% | -5.7 | -9.2 to -0.9 | -7.1 | 1 / 5 / 0 | 0.219 |
| OMIM allelic variants recovered ↑ | 6 | 71.4% | 76.0% | -4.6 | -24.6 to +12.2 | +0.0 | 2 / 2 / 2 | 1.000 |
| Causal gene F1 ↑ | 6 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 6 | – |
| Inheritance matches OMIM ↑ | 6 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 6 | – |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 14 | 25 | 16 | 56.0% | 87.5% | 68.3% |
| Disease → causal gene | Direct reading | 11 | 11 | 16 | 100.0% | 68.8% | 81.5% |
| Disease → mode of inheritance | Evidence graph | 12 | 13 | 12 | 92.3% | 100.0% | 96.0% |
| Disease → mode of inheritance | Direct reading | 12 | 12 | 12 | 100.0% | 100.0% | 100.0% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 102 | 499 | 199 | 20.4% | 51.3% | 29.2% |
| Disease → phenotype (HPO, exact id) | Direct reading | 69 | 231 | 193 | 29.9% | 35.8% | 32.6% |
| Disease → allelic variant | Evidence graph | 54 | 124 | 101 | 43.5% | 53.5% | 48.0% |
| Disease → allelic variant | Direct reading | 46 | 68 | 101 | 67.7% | 45.5% | 54.4% |
