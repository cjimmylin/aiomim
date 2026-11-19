# Generation strategies compared — run `large12`

11 entries, each written by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.

Left out: 1 entries for which at least one strategy has no draft, because the model's safety filter stopped the writer's reply or the reply came back empty (Direct reading 1). Entries: 180300.

## The strategies

- **Evidence graph** (`kg`): Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph.
- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Agentic curator** (`agent`): An autonomous agent reads and searches the papers with tools, then writes the entry.
- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.
- **Reconciled case database** (`reconciled`): The case table after merging the same patient, family or variant across papers and settling conflicts.

## Scores

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.2% | 97.9% | 98.1% | 96.2% | 96.3% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% |
| … same, before the repair round ↓ | 0.1% | 0.2% | 0.2% | 0.4% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 47.0% | 46.6% | 46.5% | 48.3% | 48.4% |
| … fully (no partial credit) ↑ | 38.1% | 38.0% | 37.4% | 39.6% | 39.9% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 0.7% | 0.4% | 0.3% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 28.8% | 33.1% | 33.2% | 30.9% | 30.9% |
| … precision ↑ | 22.3% | 34.9% | 35.5% | 27.9% | 27.9% |
| … recall ↑ | 53.5% | 40.8% | 40.4% | 51.5% | 51.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.5% | 54.4% | 53.1% | 51.0% | 51.0% |
| Clinical synopsis HPO F1, semantic ↑ | 64.5% | 64.7% | 63.8% | 64.1% | 64.1% |
| OMIM allelic variants recovered ↑ | 53.4% | 53.4% | 53.7% | 55.5% | 55.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 72.7% | 72.7% |
| OMIM references used ↑ | 96.9% | 96.7% | 89.5% | 94.3% | 94.5% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims audited per entry | 405.2 | 300.0 | 283.9 | 402.5 | 401.6 |
| Claims that could not be audited per entry | 7.6 | 0.0 | 2.5 | 0.8 | 0.0 |
| Clinical-synopsis HPO terms per entry | 41.6 | 20.2 | 18.5 | 39.3 | 39.3 |
| Allelic variants per entry | 9.6 | 6.2 | 6.4 | 12.6 | 12.1 |
| Papers cited per entry | 40.5 | 40.6 | 37.0 | 39.5 | 39.7 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same.

| Metric | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.7 (-1.3 to +0.0); 2/8/1 | +0.2 (-0.4 to +0.8); 6/5/0 | -1.6 (-2.5 to -0.7); 1/10/0 | -1.6 (-2.5 to -0.5); 2/9/0 |
| … same, before the repair round ↓ | -0.1 (-0.2 to +0.1); 3/3/5 | +0.0 (-0.1 to +0.2); 2/3/6 | +0.2 (-0.1 to +0.7); 3/7/1 | +0.3 (-0.1 to +1.0); 3/6/2 |
| OMIM per-paper facts conveyed ↑ | +0.4 (-3.0 to +3.6); 6/5/0 | -0.1 (-2.1 to +1.6); 5/6/0 | +1.7 (+0.4 to +3.0); 9/2/0 | +1.8 (-0.9 to +4.8); 8/3/0 |
| OMIM per-paper facts contradicted ↓ | +0.2 (-0.3 to +0.9); 2/2/7 | -0.2 (-0.9 to +0.3); 3/2/6 | -0.4 (-0.9 to +0.0); 3/0/8 | -0.2 (-0.9 to +0.3); 2/1/8 |
| Clinical synopsis HPO F1, exact ↑ | -4.4 (-8.1 to -0.4); 2/8/1 | +0.0 (-2.3 to +2.1); 4/4/3 | -2.2 (-5.8 to +1.5); 4/7/0 | -2.2 (-5.8 to +1.7); 4/7/0 |
| Clinical synopsis HPO F1, hierarchical ↑ | -3.9 (-6.9 to -0.7); 2/9/0 | -1.3 (-5.5 to +1.6); 5/5/1 | -3.5 (-7.0 to +0.2); 4/7/0 | -3.5 (-7.0 to +0.2); 4/7/0 |
| OMIM allelic variants recovered ↑ | -0.1 (-12.0 to +9.3); 4/2/5 | +0.2 (-3.9 to +4.6); 2/2/7 | +2.0 (-3.2 to +7.3); 3/2/6 | +2.0 (-3.2 to +7.4); 3/2/6 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/11 | +0.0 (+0.0 to +0.0); 0/0/11 | +0.0 (+0.0 to +0.0); 0/0/11 | +0.0 (+0.0 to +0.0); 0/0/11 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/11 | +0.0 (+0.0 to +0.0); 0/0/11 | -27.3 (-54.5 to +0.0); 0/3/8 | -27.3 (-54.5 to +0.0); 0/3/8 |

## Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims audited | 4,457 | 3,300 | 3,123 | 4,427 | 4,418 |
| … supported | 4,332 | 3,225 | 3,062 | 4,261 | 4,258 |
| … partly supported | 124 | 75 | 60 | 165 | 160 |
| … unsupported | 1 | 0 | 1 | 1 | 0 |
| … contradicted | 0 | 0 | 0 | 0 | 0 |
| OMIM facts scored | 1,087 | 1,089 | 1,065 | 1,101 | 1,078 |
| … conveyed | 429 | 420 | 393 | 434 | 429 |
| … partly conveyed | 186 | 182 | 190 | 198 | 192 |
| … missing | 466 | 480 | 477 | 465 | 452 |
| … contradicted | 6 | 7 | 5 | 4 | 5 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| fulltext | 89.4% | 80.0% | 64.1% | 77.7% | 77.8% |
| abstract | 47.8% | 47.8% | 47.3% | 49.6% | 49.7% |
| title | 33.3% | 27.0% | 26.7% | 29.9% | 31.7% |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 5 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.7% | 98.4% | 98.7% | 96.3% | 95.8% |
| … same, before the repair round ↓ | 0.3% | 0.3% | 0.2% | 0.6% | 0.9% |
| OMIM per-paper facts conveyed ↑ | 38.6% | 37.8% | 39.5% | 40.8% | 42.6% |
| OMIM per-paper facts contradicted ↓ | 1.6% | 0.8% | 0.4% | 0.2% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 28.2% | 30.9% | 31.7% | 31.0% | 31.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.4% | 57.2% | 57.4% | 55.5% | 55.5% |
| OMIM allelic variants recovered ↑ | 31.7% | 26.3% | 27.8% | 31.7% | 31.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |

### under half full text — 6 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 97.4% | 97.5% | 96.2% | 96.7% |
| … same, before the repair round ↓ | 0.0% | 0.1% | 0.1% | 0.2% | 0.1% |
| OMIM per-paper facts conveyed ↑ | 54.0% | 53.9% | 52.3% | 54.6% | 53.3% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.5% | 0.4% | 0.4% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 29.3% | 35.0% | 34.4% | 30.8% | 30.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 46.5% | 52.2% | 49.6% | 47.2% | 47.2% |
| OMIM allelic variants recovered ↑ | 71.4% | 76.0% | 75.2% | 75.2% | 75.2% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 66.7% | 66.7% |

## By size of the reference list

### 9 or more references — 11 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.2% | 97.9% | 98.1% | 96.2% | 96.3% |
| … same, before the repair round ↓ | 0.1% | 0.2% | 0.2% | 0.4% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 47.0% | 46.6% | 46.5% | 48.3% | 48.4% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 0.7% | 0.4% | 0.3% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 28.8% | 33.1% | 33.2% | 30.9% | 30.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.5% | 54.4% | 53.1% | 51.0% | 51.0% |
| OMIM allelic variants recovered ↑ | 53.4% | 53.4% | 53.7% | 55.5% | 55.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 72.7% | 72.7% |

## By creation era (MIM number range)

### 600000-609999 — 4 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 97.1% | 97.1% | 96.1% | 96.6% |
| … same, before the repair round ↓ | 0.0% | 0.1% | 0.2% | 0.2% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 56.1% | 54.6% | 54.2% | 56.0% | 55.0% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.8% | 0.6% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 32.5% | 42.9% | 44.2% | 35.0% | 35.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 51.5% | 59.7% | 60.7% | 53.3% | 53.3% |
| OMIM allelic variants recovered ↑ | 75.9% | 75.3% | 74.1% | 74.1% | 74.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 50.0% | 50.0% |

### 610000-615999 — 3 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.6% | 98.2% | 98.5% | 96.2% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.3% | 0.3% | 0.9% | 1.4% |
| OMIM per-paper facts conveyed ↑ | 45.5% | 42.8% | 46.1% | 46.9% | 49.2% |
| OMIM per-paper facts contradicted ↓ | 2.4% | 1.4% | 0.4% | 0.4% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 32.9% | 39.3% | 38.9% | 39.5% | 39.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.4% | 58.6% | 58.1% | 60.2% | 60.2% |
| OMIM allelic variants recovered ↑ | 38.3% | 34.2% | 34.2% | 38.3% | 38.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 66.7% | 66.7% |

### 620000 onward — 1 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.9% | 97.6% | 99.1% | 96.9% | 96.4% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed ↑ | 41.0% | 52.4% | 51.4% | 48.8% | 44.7% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 11.7% | 4.3% | 4.4% | 9.9% | 9.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 21.6% | 28.9% | 28.2% | 19.9% | 19.9% |
| OMIM allelic variants recovered ↑ | 25.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### classic (1xxxxx-5xxxxx) — 3 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.6% | 98.6% | 98.7% | 96.3% | 96.7% |
| … same, before the repair round ↓ | 0.1% | 0.2% | 0.1% | 0.2% | 0.2% |
| OMIM per-paper facts conveyed ↑ | 38.4% | 37.8% | 34.8% | 39.4% | 40.2% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.0% | 0.3% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 25.4% | 23.7% | 22.3% | 23.8% | 23.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.1% | 51.8% | 46.4% | 49.1% | 49.1% |
| OMIM allelic variants recovered ↑ | 47.8% | 36.4% | 38.8% | 41.1% | 41.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Generation: model calls | 44.1 | 2.0 | 2.0 | 44.2 | 46.1 |
| Generation: list price | $2.48 | $0.65 | $0.93 | $2.59 | $2.85 |
| Generation: input / output tokens | 283,979 / 69,551 | 45,247 / 18,451 | 205,458 / 28,207 | 342,147 / 72,584 | 367,284 / 76,495 |
| Generation: model time (s) | 594 | 142 | 220 | 646 | 688 |
| Audit and repair: list price | $2.92 | $2.37 | $2.26 | $2.90 | $2.88 |
| Scoring against OMIM: list price | $0.35 | $0.34 | $0.34 | $0.35 | $0.35 |
| Everything: list price | $5.75 | $3.37 | $3.53 | $5.84 | $6.09 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 14 | 25 | 16 | 56.0% | 87.5% | 68.3% |
| Disease → causal gene | Direct reading | 11 | 11 | 16 | 100.0% | 68.8% | 81.5% |
| Disease → causal gene | Agentic curator | 14 | 25 | 16 | 56.0% | 87.5% | 68.3% |
| Disease → causal gene | Case table first | 11 | 13 | 16 | 84.6% | 68.8% | 75.9% |
| Disease → causal gene | Reconciled case database | 11 | 13 | 16 | 84.6% | 68.8% | 75.9% |
| Disease → mode of inheritance | Evidence graph | 12 | 13 | 12 | 92.3% | 100.0% | 96.0% |
| Disease → mode of inheritance | Direct reading | 12 | 12 | 12 | 100.0% | 100.0% | 100.0% |
| Disease → mode of inheritance | Agentic curator | 12 | 13 | 12 | 92.3% | 100.0% | 96.0% |
| Disease → mode of inheritance | Case table first | 11 | 15 | 12 | 73.3% | 91.7% | 81.5% |
| Disease → mode of inheritance | Reconciled case database | 11 | 15 | 12 | 73.3% | 91.7% | 81.5% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 102 | 499 | 199 | 20.4% | 51.3% | 29.2% |
| Disease → phenotype (HPO, exact id) | Direct reading | 69 | 231 | 193 | 29.9% | 35.8% | 32.6% |
| Disease → phenotype (HPO, exact id) | Agentic curator | 72 | 227 | 196 | 31.7% | 36.7% | 34.0% |
| Disease → phenotype (HPO, exact id) | Case table first | 90 | 454 | 195 | 19.8% | 46.2% | 27.7% |
| Disease → phenotype (HPO, exact id) | Reconciled case database | 90 | 454 | 195 | 19.8% | 46.2% | 27.7% |
| Disease → allelic variant | Evidence graph | 54 | 124 | 101 | 43.5% | 53.5% | 48.0% |
| Disease → allelic variant | Direct reading | 46 | 68 | 101 | 67.7% | 45.5% | 54.4% |
| Disease → allelic variant | Agentic curator | 48 | 71 | 101 | 67.6% | 47.5% | 55.8% |
| Disease → allelic variant | Case table first | 60 | 145 | 111 | 41.4% | 54.0% | 46.9% |
| Disease → allelic variant | Reconciled case database | 51 | 139 | 102 | 36.7% | 50.0% | 42.3% |
