# Generation strategies compared — run `omim100_reconciled`

100 entries, each written by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.

## The strategies

- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.
- **Reconciled case database** (`reconciled`): The case table after merging the same patient, family or variant across papers and settling conflicts.

## Scores

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.5% | 94.5% |
| Claims unsupported or contradicted ↓ | 0.2% | 0.2% |
| … same, before the repair round ↓ | 0.8% | 0.8% |
| OMIM per-paper facts conveyed ↑ | 49.0% | 49.1% |
| … fully (no partial credit) ↑ | 41.1% | 41.4% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 34.0% | 33.9% |
| … precision ↑ | 40.6% | 40.6% |
| … recall ↑ | 36.8% | 36.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.0% | 54.0% |
| Clinical synopsis HPO F1, semantic ↑ | 64.7% | 64.7% |
| OMIM allelic variants recovered ↑ | 63.5% | 63.6% |
| Causal gene F1 ↑ | 96.2% | 96.2% |
| Inheritance matches OMIM ↑ | 90.0% | 90.0% |
| OMIM references used ↑ | 93.5% | 93.2% |

## How much each strategy writes

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims audited per entry | 116.5 | 116.4 |
| Claims that could not be audited per entry | 2.3 | 3.4 |
| Clinical-synopsis HPO terms per entry | 21.3 | 21.2 |
| Allelic variants per entry | 4.0 | 4.0 |
| Papers cited per entry | 4.9 | 4.8 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 |

## Paired differences from the baseline (Case table first)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same.

| Metric | Reconciled case database |
|---|---|
| Claims supported by cited paper ↑ | +0.0 (-0.4 to +0.4); 14/14/71 |
| … same, before the repair round ↓ | +0.1 (-0.1 to +0.2); 4/13/82 |
| OMIM per-paper facts conveyed ↑ | +0.1 (-0.2 to +0.3); 15/9/76 |
| OMIM per-paper facts contradicted ↓ | +0.0 (-0.0 to +0.1); 4/4/92 |
| Clinical synopsis HPO F1, exact ↑ | -0.1 (-0.4 to +0.3); 6/5/87 |
| Clinical synopsis HPO F1, hierarchical ↑ | +0.0 (-0.0 to +0.1); 2/1/95 |
| OMIM allelic variants recovered ↑ | +0.1 (+0.0 to +0.3); 1/0/99 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/96 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/100 |

## Pooled counts

| | Case table first | Reconciled case database |
|---|---|---|
| Claims audited | 11,650 | 11,643 |
| … supported | 11,162 | 11,152 |
| … partly supported | 487 | 489 |
| … unsupported | 1 | 2 |
| … contradicted | 0 | 0 |
| OMIM facts scored | 5,677 | 5,685 |
| … conveyed | 2,286 | 2,313 |
| … partly conveyed | 883 | 864 |
| … missing | 2,471 | 2,470 |
| … contradicted | 37 | 38 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Case table first | Reconciled case database |
|---|---|---|
| fulltext | 67.4% | 67.9% |
| abstract | 42.2% | 42.3% |
| title | 24.4% | 24.3% |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 93.7% | 93.7% |
| … same, before the repair round ↓ | 0.5% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 40.0% | 39.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 29.9% | 29.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.1% | 49.1% |
| OMIM allelic variants recovered ↑ | 47.8% | 47.8% |
| Causal gene F1 ↑ | 91.7% | 91.7% |
| Inheritance matches OMIM ↑ | 87.0% | 87.0% |

### under half full text — 28 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.1% | 94.9% |
| … same, before the repair round ↓ | 0.5% | 0.6% |
| OMIM per-paper facts conveyed ↑ | 51.2% | 51.5% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 35.0% | 34.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.9% | 57.8% |
| OMIM allelic variants recovered ↑ | 72.7% | 72.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 92.9% | 92.9% |

### half or more full text — 23 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.6% | 95.8% |
| … same, before the repair round ↓ | 1.7% | 1.7% |
| OMIM per-paper facts conveyed ↑ | 63.3% | 63.6% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 39.5% | 39.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.8% | 58.0% |
| OMIM allelic variants recovered ↑ | 83.5% | 83.9% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.7% | 95.7% |

### all full text — 3 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.7% |
| … same, before the repair round ↓ | 0.0% | 0.0% |
| OMIM per-paper facts conveyed ↑ | 58.2% | 58.2% |
| OMIM per-paper facts contradicted ↓ | 5.6% | 5.6% |
| Clinical synopsis HPO F1, exact ↑ | 51.9% | 51.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 72.0% | 72.0% |
| OMIM allelic variants recovered ↑ | 66.7% | 66.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 66.7% | 66.7% |

## By size of the reference list

### 2-4 references — 55 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 93.8% | 94.0% |
| … same, before the repair round ↓ | 1.1% | 1.1% |
| OMIM per-paper facts conveyed ↑ | 49.5% | 49.5% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.9% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.4% | 53.5% |
| OMIM allelic variants recovered ↑ | 63.2% | 63.2% |
| Causal gene F1 ↑ | 96.2% | 96.2% |
| Inheritance matches OMIM ↑ | 90.9% | 90.9% |

### 5-8 references — 28 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.4% | 95.1% |
| … same, before the repair round ↓ | 0.3% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 47.7% | 47.8% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 31.9% | 32.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.0% | 54.0% |
| OMIM allelic variants recovered ↑ | 61.3% | 61.7% |
| Causal gene F1 ↑ | 98.8% | 98.8% |
| Inheritance matches OMIM ↑ | 85.7% | 85.7% |

### 9 or more references — 17 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 95.3% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.4% |
| OMIM per-paper facts conveyed ↑ | 49.7% | 50.2% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 37.5% | 37.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.9% | 55.9% |
| OMIM allelic variants recovered ↑ | 68.3% | 68.3% |
| Causal gene F1 ↑ | 91.7% | 91.7% |
| Inheritance matches OMIM ↑ | 94.1% | 94.1% |

## By creation era (MIM number range)

### 600000-609999 — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 92.7% | 92.9% |
| … same, before the repair round ↓ | 0.4% | 0.4% |
| OMIM per-paper facts conveyed ↑ | 53.6% | 53.7% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 37.9% | 37.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 60.2% | 60.2% |
| OMIM allelic variants recovered ↑ | 68.2% | 68.2% |
| Causal gene F1 ↑ | 94.7% | 94.7% |
| Inheritance matches OMIM ↑ | 90.0% | 90.0% |

### 610000-615999 — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.3% | 94.7% |
| … same, before the repair round ↓ | 0.7% | 0.6% |
| OMIM per-paper facts conveyed ↑ | 51.2% | 51.7% |
| OMIM per-paper facts contradicted ↓ | 1.3% | 1.3% |
| Clinical synopsis HPO F1, exact ↑ | 33.8% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.5% | 49.4% |
| OMIM allelic variants recovered ↑ | 70.3% | 70.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% |

### 616000-619999 — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.7% |
| … same, before the repair round ↓ | 2.1% | 2.2% |
| OMIM per-paper facts conveyed ↑ | 48.9% | 48.9% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 32.3% | 31.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.4% | 52.4% |
| OMIM allelic variants recovered ↑ | 73.6% | 73.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 85.0% | 85.0% |

### 620000 onward — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.9% |
| … same, before the repair round ↓ | 0.1% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 50.3% | 50.3% |
| OMIM per-paper facts contradicted ↓ | 0.1% | 0.1% |
| Clinical synopsis HPO F1, exact ↑ | 35.2% | 35.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.6% | 54.8% |
| OMIM allelic variants recovered ↑ | 64.5% | 64.5% |
| Causal gene F1 ↑ | 94.7% | 94.7% |
| Inheritance matches OMIM ↑ | 90.0% | 90.0% |

### classic (1xxxxx-5xxxxx) — 20 entries

| Metric | Case table first | Reconciled case database |
|---|---|---|
| Claims supported by cited paper ↑ | 94.7% | 94.6% |
| … same, before the repair round ↓ | 0.4% | 0.7% |
| OMIM per-paper facts conveyed ↑ | 41.2% | 41.0% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 30.6% | 30.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.3% | 53.3% |
| OMIM allelic variants recovered ↑ | 41.0% | 41.0% |
| Causal gene F1 ↑ | 91.2% | 91.2% |
| Inheritance matches OMIM ↑ | 85.0% | 85.0% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Case table first | Reconciled case database |
|---|---|---|
| Generation: model calls | 7.0 | 8.3 |
| Generation: list price | $0.64 | $0.74 |
| Generation: input / output tokens | 66,884 / 17,590 | 77,173 / 19,223 |
| Generation: model time (s) | 146 | 166 |
| Audit and repair: list price | $0.81 | $0.83 |
| Scoring against OMIM: list price | $0.20 | $0.20 |
| Everything: list price | $1.64 | $1.76 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Case table first | 97 | 102 | 105 | 95.1% | 92.4% | 93.7% |
| Disease → causal gene | Reconciled case database | 97 | 102 | 105 | 95.1% | 92.4% | 93.7% |
| Disease → mode of inheritance | Case table first | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → mode of inheritance | Reconciled case database | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → phenotype (HPO, exact id) | Case table first | 750 | 2,139 | 2,311 | 35.1% | 32.5% | 33.7% |
| Disease → phenotype (HPO, exact id) | Reconciled case database | 746 | 2,127 | 2,311 | 35.1% | 32.3% | 33.6% |
| Disease → allelic variant | Case table first | 262 | 399 | 428 | 65.7% | 61.2% | 63.4% |
| Disease → allelic variant | Reconciled case database | 263 | 398 | 428 | 66.1% | 61.5% | 63.7% |
