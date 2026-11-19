# Generation strategies compared — run `omim100_secondhand`

96 entries, each written by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.

Left out: 4 entries for which at least one strategy has no draft, because the model's safety filter stopped the writer's reply or the reply came back empty (Second-hand evidence 4; Direct reading 3). Entries: 278750, 609296, 620609, 621068.

## The strategies

- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Second-hand evidence** (`secondhand`): Direct reading; a paper not readable in full is supplemented with what later open-access papers say it reported.

## Scores

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 94.4% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.2% |
| … same, before the repair round ↓ | 0.4% | 3.9% |
| OMIM per-paper facts conveyed ↑ | 53.2% | 54.0% |
| … fully (no partial credit) ↑ | 44.8% | 46.3% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.9% | 37.0% |
| … precision ↑ | 43.7% | 43.2% |
| … recall ↑ | 36.2% | 37.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.7% | 58.9% |
| Clinical synopsis HPO F1, semantic ↑ | 66.5% | 68.7% |
| OMIM allelic variants recovered ↑ | 68.2% | 73.2% |
| Causal gene F1 ↑ | 98.6% | 98.6% |
| Inheritance matches OMIM ↑ | 93.8% | 95.8% |
| OMIM references used ↑ | 94.6% | 94.5% |

## How much each strategy writes

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims audited per entry | 103.6 | 107.9 |
| Claims that could not be audited per entry | 1.3 | 3.0 |
| Clinical-synopsis HPO terms per entry | 15.8 | 16.4 |
| Allelic variants per entry | 3.2 | 3.4 |
| Papers cited per entry | 4.8 | 4.9 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same.

| Metric | Second-hand evidence |
|---|---|
| Claims supported by cited paper ↑ | -1.8 (-2.9 to -0.8); 31/60/5 |
| … same, before the repair round ↓ | +3.6 (+2.2 to +5.1); 8/51/37 |
| OMIM per-paper facts conveyed ↑ | +0.8 (-0.3 to +1.9); 50/41/5 |
| OMIM per-paper facts contradicted ↓ | +0.4 (+0.1 to +0.9); 9/19/68 |
| Clinical synopsis HPO F1, exact ↑ | +1.1 (-0.7 to +2.9); 42/36/18 |
| Clinical synopsis HPO F1, hierarchical ↑ | +2.2 (+0.4 to +4.3); 50/36/10 |
| OMIM allelic variants recovered ↑ | +5.0 (+1.3 to +9.2); 13/2/81 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/95 |
| Inheritance matches OMIM ↑ | +2.1 (+0.0 to +5.2); 2/0/94 |

## Pooled counts

| | Direct reading | Second-hand evidence |
|---|---|---|
| Claims audited | 9,943 | 10,357 |
| … supported | 9,614 | 9,913 |
| … partly supported | 329 | 431 |
| … unsupported | 0 | 13 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 5,462 | 5,453 |
| … conveyed | 2,421 | 2,484 |
| … partly conveyed | 912 | 849 |
| … missing | 2,093 | 2,074 |
| … contradicted | 36 | 46 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Direct reading | Second-hand evidence |
|---|---|---|
| fulltext | 79.1% | 78.1% |
| abstract | 44.2% | 45.0% |
| title | 23.1% | 30.1% |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 45 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 95.1% | 92.3% |
| … same, before the repair round ↓ | 0.4% | 7.3% |
| OMIM per-paper facts conveyed ↑ | 40.4% | 41.2% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 30.4% | 33.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.7% | 55.2% |
| OMIM allelic variants recovered ↑ | 49.1% | 58.9% |
| Causal gene F1 ↑ | 97.0% | 97.0% |
| Inheritance matches OMIM ↑ | 91.1% | 95.6% |

### under half full text — 27 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.7% |
| … same, before the repair round ↓ | 0.6% | 1.1% |
| OMIM per-paper facts conveyed ↑ | 55.9% | 58.6% |
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
| OMIM per-paper facts conveyed ↑ | 73.7% | 72.8% |
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
| OMIM per-paper facts conveyed ↑ | 77.8% | 71.3% |
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
| OMIM per-paper facts conveyed ↑ | 54.8% | 55.1% |
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
| OMIM per-paper facts conveyed ↑ | 49.9% | 51.8% |
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
| OMIM per-paper facts conveyed ↑ | 53.4% | 53.9% |
| OMIM per-paper facts contradicted ↓ | 1.0% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 42.7% | 41.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 62.5% | 63.7% |
| OMIM allelic variants recovered ↑ | 73.1% | 73.1% |
| Causal gene F1 ↑ | 97.8% | 97.8% |
| Inheritance matches OMIM ↑ | 87.5% | 87.5% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | Direct reading | Second-hand evidence |
|---|---|---|
| Claims supported by cited paper ↑ | 96.0% | 95.2% |
| … same, before the repair round ↓ | 0.5% | 2.7% |
| OMIM per-paper facts conveyed ↑ | 55.7% | 58.4% |
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
| OMIM per-paper facts conveyed ↑ | 53.4% | 54.5% |
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
| OMIM per-paper facts conveyed ↑ | 55.4% | 55.6% |
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
| OMIM per-paper facts conveyed ↑ | 57.2% | 56.8% |
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
| OMIM per-paper facts conveyed ↑ | 44.2% | 44.5% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.5% |
| Clinical synopsis HPO F1, exact ↑ | 33.5% | 36.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.2% | 60.1% |
| OMIM allelic variants recovered ↑ | 47.1% | 55.0% |
| Causal gene F1 ↑ | 92.6% | 92.6% |
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
