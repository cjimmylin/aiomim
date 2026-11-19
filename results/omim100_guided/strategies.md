# Generation strategies compared — run `omim100_guided`

68 entries, each written by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.

Left out: 2 entries for which at least one strategy has no draft, because the model's safety filter stopped the writer's reply or the reply came back empty (Learned curation guide 2). Entries: 118210, 615817.

## The strategies

- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Learned curation guide** (`guided`): Direct reading with a guide to what OMIM includes, learned from the misses and extras of other entries.

## Scores

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 96.1% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% |
| … same, before the repair round ↓ | 0.2% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 52.2% | 51.9% |
| … fully (no partial credit) ↑ | 43.8% | 44.2% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 35.7% | 36.5% |
| … precision ↑ | 43.8% | 43.0% |
| … recall ↑ | 37.1% | 40.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.4% | 55.4% |
| Clinical synopsis HPO F1, semantic ↑ | 65.8% | 66.7% |
| OMIM allelic variants recovered ↑ | 66.6% | 65.0% |
| Causal gene F1 ↑ | 99.5% | 99.5% |
| Inheritance matches OMIM ↑ | 94.1% | 94.1% |
| OMIM references used ↑ | 94.5% | 93.7% |

## How much each strategy writes

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims audited per entry | 107.1 | 96.3 |
| Claims that could not be audited per entry | 0.9 | 0.5 |
| Clinical-synopsis HPO terms per entry | 16.2 | 18.1 |
| Allelic variants per entry | 3.4 | 3.3 |
| Papers cited per entry | 4.9 | 4.8 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same.

| Metric | Learned curation guide |
|---|---|
| Claims supported by cited paper ↑ | -0.1 (-1.0 to +1.0); 29/35/4 |
| … same, before the repair round ↓ | -0.0 (-0.4 to +0.3); 6/7/55 |
| OMIM per-paper facts conveyed ↑ | -0.3 (-1.4 to +0.7); 32/36/0 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.0 to +0.3); 6/11/51 |
| Clinical synopsis HPO F1, exact ↑ | +0.8 (-0.8 to +2.4); 34/22/12 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.1 (-1.2 to +1.4); 27/31/10 |
| OMIM allelic variants recovered ↑ | -1.6 (-3.7 to +0.0); 0/3/65 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/67 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/68 |

## Pooled counts

| | Direct reading | Learned curation guide |
|---|---|---|
| Claims audited | 7,282 | 6,549 |
| … supported | 7,043 | 6,333 |
| … partly supported | 239 | 216 |
| … unsupported | 0 | 0 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 3,962 | 3,958 |
| … conveyed | 1,773 | 1,787 |
| … partly conveyed | 671 | 617 |
| … missing | 1,494 | 1,526 |
| … contradicted | 24 | 28 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Direct reading | Learned curation guide |
|---|---|---|
| fulltext | 78.2% | 78.2% |
| abstract | 43.1% | 42.8% |
| title | 23.3% | 22.9% |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 29 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 94.8% | 95.1% |
| … same, before the repair round ↓ | 0.4% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 37.1% | 37.0% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 28.1% | 28.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 46.3% | 46.8% |
| OMIM allelic variants recovered ↑ | 43.9% | 41.3% |
| Causal gene F1 ↑ | 98.8% | 98.8% |
| Inheritance matches OMIM ↑ | 93.1% | 93.1% |

### under half full text — 19 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.6% | 96.9% |
| … same, before the repair round ↓ | 0.2% | 0.0% |
| OMIM per-paper facts conveyed ↑ | 54.5% | 54.9% |
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
| OMIM per-paper facts conveyed ↑ | 71.3% | 69.6% |
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
| OMIM per-paper facts conveyed ↑ | 85.5% | 87.0% |
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
| OMIM per-paper facts conveyed ↑ | 52.5% | 51.3% |
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
| OMIM per-paper facts conveyed ↑ | 50.0% | 51.6% |
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
| OMIM per-paper facts conveyed ↑ | 54.5% | 54.1% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.1% |
| Clinical synopsis HPO F1, exact ↑ | 39.5% | 38.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.1% | 58.3% |
| OMIM allelic variants recovered ↑ | 69.6% | 69.6% |
| Causal gene F1 ↑ | 97.0% | 97.0% |
| Inheritance matches OMIM ↑ | 83.3% | 83.3% |

## By creation era (MIM number range)

### 600000-609999 — 14 entries

| Metric | Direct reading | Learned curation guide |
|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 96.9% |
| … same, before the repair round ↓ | 0.7% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 54.9% | 53.4% |
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
| OMIM per-paper facts conveyed ↑ | 56.7% | 58.2% |
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
| OMIM per-paper facts conveyed ↑ | 57.0% | 55.1% |
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
| OMIM per-paper facts conveyed ↑ | 55.0% | 54.8% |
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
| OMIM per-paper facts conveyed ↑ | 36.6% | 37.2% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 27.9% | 30.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.9% | 50.5% |
| OMIM allelic variants recovered ↑ | 32.2% | 30.3% |
| Causal gene F1 ↑ | 97.2% | 97.2% |
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
