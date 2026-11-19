# Generation strategies compared — run `omim100`

97 entries, each written by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better.

Left out: 3 entries for which at least one strategy has no draft, because the model's safety filter stopped the writer's reply or the reply came back empty (Agentic curator 2; Direct reading 3; Evidence graph 1). Entries: 609296, 620609, 621068.

## The strategies

- **Evidence graph** (`kg`): Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph.
- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Agentic curator** (`agent`): An autonomous agent reads and searches the papers with tools, then writes the entry.
- **Memory only (control)** (`closedbook`): Written from the model's memory with no papers; nothing is grounded. A control, not a method.
- **Recall, then verify** (`recall`): A draft from memory is checked claim by claim against the papers; unsupported claims are deleted.
- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.

## Scores

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.6% | 96.1% | 96.5% | 51.5% | 94.3% | 94.5% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% | 0.0% | 22.3% | 0.0% | 0.2% |
| … same, before the repair round ↓ | 0.3% | 0.4% | 0.2% | 22.3% | 0.6% | 0.8% |
| OMIM per-paper facts conveyed ↑ | 50.8% | 52.9% | 52.3% | 20.4% | 18.1% | 49.1% |
| … fully (no partial credit) ↑ | 42.8% | 44.5% | 44.0% | 12.1% | 11.9% | 41.0% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.5% | 0.6% | 0.8% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 34.2% | 35.6% | 35.3% | 30.4% | 26.1% | 33.9% |
| … precision ↑ | 40.0% | 43.6% | 44.9% | 53.1% | 53.3% | 40.4% |
| … recall ↑ | 37.0% | 35.9% | 33.9% | 23.6% | 18.0% | 37.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.6% | 56.3% | 56.3% | 48.1% | 42.7% | 53.8% |
| Clinical synopsis HPO F1, semantic ↑ | 64.9% | 66.3% | 66.0% | 62.3% | 56.6% | 64.5% |
| OMIM allelic variants recovered ↑ | 65.6% | 67.6% | 67.1% | 15.6% | 11.7% | 63.4% |
| Causal gene F1 ↑ | 99.3% | 98.6% | 98.6% | 97.6% | 97.6% | 96.1% |
| Inheritance matches OMIM ↑ | 92.8% | 93.8% | 93.8% | 83.5% | 74.2% | 90.7% |
| OMIM references used ↑ | 93.8% | 94.5% | 93.6% | 33.9% | 65.7% | 94.0% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited per entry | 115.6 | 103.5 | 100.1 | 28.4 | 26.6 | 117.4 |
| Claims that could not be audited per entry | 1.1 | 1.3 | 1.0 | 0.0 | 0.0 | 1.3 |
| Clinical-synopsis HPO terms per entry | 19.7 | 15.6 | 14.1 | 6.1 | 4.4 | 21.4 |
| Allelic variants per entry | 3.9 | 3.2 | 3.3 | 0.5 | 0.3 | 4.0 |
| Papers cited per entry | 4.9 | 4.9 | 4.8 | 1.6 | 3.2 | 4.9 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.1 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same.

| Metric | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | +0.5 (-0.3 to +1.3); 45/45/7 | +0.3 (-0.4 to +1.0); 56/34/7 | -44.6 (-49.5 to -39.8); 2/94/1 | -1.8 (-3.3 to -0.4); 36/55/5 | -1.6 (-2.8 to -0.6); 35/59/3 |
| … same, before the repair round ↓ | -0.1 (-0.4 to +0.2); 12/13/72 | -0.2 (-0.5 to +0.1); 12/9/76 | +21.9 (+18.1 to +26.1); 1/82/14 | +0.3 (-0.2 to +0.8); 11/10/75 | +0.4 (-0.2 to +1.3); 11/20/66 |
| OMIM per-paper facts conveyed ↑ | -2.1 (-4.1 to -0.4); 44/46/7 | -0.6 (-1.5 to +0.2); 45/48/4 | -32.6 (-37.2 to -27.9); 7/90/0 | -34.8 (-39.1 to -30.5); 3/94/0 | -3.8 (-6.0 to -2.0); 29/65/3 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.5); 13/12/72 | +0.0 (-0.1 to +0.2); 11/11/75 | +0.2 (-0.2 to +0.8); 18/17/62 | -0.1 (-0.3 to +0.2); 18/11/68 | +0.1 (-0.2 to +0.5); 12/12/73 |
| Clinical synopsis HPO F1, exact ↑ | -1.5 (-3.3 to +0.4); 34/48/15 | -0.3 (-1.5 to +0.8); 39/35/23 | -5.4 (-9.3 to -1.4); 42/54/0 | -10.7 (-14.3 to -7.2); 25/62/4 | -1.9 (-3.8 to -0.1); 40/47/9 |
| Clinical synopsis HPO F1, hierarchical ↑ | -1.7 (-3.0 to -0.4); 36/48/13 | +0.0 (-1.0 to +1.1); 43/36/18 | -8.3 (-12.7 to -4.0); 38/57/1 | -14.6 (-18.7 to -10.7); 21/66/4 | -2.5 (-4.1 to -1.0); 34/54/8 |
| OMIM allelic variants recovered ↑ | -2.1 (-5.5 to +1.4); 4/10/83 | -0.5 (-2.1 to +0.7); 3/3/91 | -52.0 (-60.5 to -43.5); 3/73/21 | -56.0 (-63.5 to -48.2); 0/75/22 | -4.2 (-7.8 to -1.1); 4/15/78 |
| Causal gene F1 ↑ | +0.7 (+0.0 to +2.1); 1/0/95 | +0.0 (+0.0 to +0.0); 0/0/96 | -0.8 (-4.0 to +2.0); 1/2/80 | -0.8 (-4.0 to +2.0); 1/2/80 | -2.5 (-6.4 to +1.1); 1/3/90 |
| Inheritance matches OMIM ↑ | -1.0 (-5.1 to +2.1); 1/2/94 | +0.0 (-3.1 to +3.1); 1/1/95 | -10.3 (-18.6 to -3.1); 3/13/81 | -19.6 (-27.8 to -11.3); 1/20/76 | -3.1 (-9.3 to +3.1); 4/7/86 |

## Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited | 11,218 | 10,038 | 9,705 | 2,753 | 2,581 | 11,388 |
| … supported | 10,883 | 9,698 | 9,442 | 1,429 | 2,437 | 10,908 |
| … partly supported | 335 | 340 | 262 | 714 | 144 | 479 |
| … unsupported | 0 | 0 | 1 | 590 | 0 | 1 |
| … contradicted | 0 | 0 | 0 | 20 | 0 | 0 |
| OMIM facts scored | 5,525 | 5,530 | 5,572 | 5,477 | 5,462 | 5,542 |
| … conveyed | 2,333 | 2,429 | 2,436 | 564 | 549 | 2,214 |
| … partly conveyed | 897 | 934 | 918 | 926 | 683 | 871 |
| … missing | 2,262 | 2,131 | 2,183 | 3,949 | 4,205 | 2,424 |
| … contradicted | 33 | 36 | 35 | 38 | 25 | 33 |

## OMIM-fact coverage by how much of the paper was readable

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| fulltext | 76.5% | 79.1% | 77.9% | 17.5% | 17.1% | 68.2% |
| abstract | 42.0% | 43.9% | 43.7% | 19.2% | 17.0% | 41.7% |
| title | 22.7% | 23.1% | 22.0% | 19.3% | 4.9% | 22.1% |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.9% | 95.0% | 94.8% | 42.4% | 93.3% | 93.7% |
| … same, before the repair round ↓ | 0.4% | 0.4% | 0.2% | 24.3% | 0.8% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 39.5% | 40.1% | 39.3% | 22.2% | 20.9% | 40.0% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.4% | 0.8% | 0.5% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 30.4% | 29.9% | 30.0% | 31.7% | 26.5% | 29.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.2% | 50.0% | 50.3% | 51.1% | 44.7% | 49.1% |
| OMIM allelic variants recovered ↑ | 48.9% | 48.4% | 48.1% | 15.8% | 9.8% | 47.8% |
| Causal gene F1 ↑ | 98.5% | 97.0% | 97.0% | 97.6% | 97.6% | 91.7% |
| Inheritance matches OMIM ↑ | 89.1% | 91.3% | 91.3% | 89.1% | 71.7% | 87.0% |

### under half full text — 27 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.3% | 96.5% | 97.6% | 51.9% | 94.8% | 95.0% |
| … same, before the repair round ↓ | 0.1% | 0.6% | 0.1% | 24.4% | 0.8% | 0.5% |
| OMIM per-paper facts conveyed ↑ | 54.5% | 55.9% | 56.7% | 18.9% | 14.8% | 50.5% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 1.0% | 0.8% | 1.1% | 0.6% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 35.6% | 39.3% | 38.1% | 30.8% | 25.6% | 35.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.7% | 61.1% | 60.8% | 46.1% | 40.0% | 58.2% |
| OMIM allelic variants recovered ↑ | 74.7% | 80.2% | 80.1% | 17.4% | 14.0% | 71.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 95.5% | 95.5% | 100.0% |
| Inheritance matches OMIM ↑ | 92.6% | 92.6% | 92.6% | 74.1% | 70.4% | 92.6% |

### half or more full text — 22 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 97.9% | 98.4% | 67.1% | 95.8% | 95.6% |
| … same, before the repair round ↓ | 0.3% | 0.0% | 0.1% | 17.0% | 0.1% | 1.7% |
| OMIM per-paper facts conveyed ↑ | 69.5% | 73.7% | 71.7% | 18.4% | 16.4% | 63.1% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.5% | 0.5% | 0.4% | 0.2% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 39.0% | 41.1% | 40.6% | 29.2% | 27.5% | 38.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.5% | 61.5% | 61.5% | 46.8% | 44.3% | 56.8% |
| OMIM allelic variants recovered ↑ | 88.4% | 89.4% | 87.9% | 9.7% | 9.3% | 82.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 81.8% | 81.8% | 95.5% |

### all full text — 2 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 99.2% | 98.6% | 98.2% | 81.9% | 95.0% | 94.7% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.9% | 6.7% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed ↑ | 57.0% | 77.8% | 79.0% | 18.9% | 18.1% | 87.4% |
| OMIM per-paper facts contradicted ↓ | 7.7% | 0.0% | 2.6% | 0.0% | 0.0% | 8.3% |
| Clinical synopsis HPO F1, exact ↑ | 49.8% | 56.9% | 62.4% | 8.8% | 9.3% | 51.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 69.9% | 79.7% | 78.8% | 20.1% | 17.5% | 72.0% |
| OMIM allelic variants recovered ↑ | 75.0% | 100.0% | 100.0% | 50.0% | 50.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 53 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.4% | 96.2% | 96.5% | 53.1% | 94.0% | 93.8% |
| … same, before the repair round ↓ | 0.2% | 0.2% | 0.1% | 22.7% | 0.3% | 1.1% |
| OMIM per-paper facts conveyed ↑ | 52.2% | 54.8% | 53.7% | 20.6% | 18.8% | 50.1% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 0.4% | 0.5% | 1.2% | 0.4% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.5% | 33.7% | 33.7% | 27.2% | 23.9% | 33.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.0% | 54.3% | 54.3% | 44.6% | 39.4% | 52.9% |
| OMIM allelic variants recovered ↑ | 65.0% | 67.4% | 66.2% | 14.5% | 12.7% | 63.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 97.6% | 97.6% | 96.1% |
| Inheritance matches OMIM ↑ | 94.3% | 98.1% | 96.2% | 79.2% | 71.7% | 92.5% |

### 5-8 references — 27 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 96.1% | 95.9% | 49.6% | 93.9% | 95.4% |
| … same, before the repair round ↓ | 0.3% | 0.7% | 0.1% | 21.0% | 0.8% | 0.3% |
| OMIM per-paper facts conveyed ↑ | 48.2% | 49.9% | 49.9% | 21.0% | 17.8% | 46.9% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.6% | 0.5% | 0.4% | 0.7% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 33.5% | 36.1% | 35.7% | 30.7% | 27.2% | 32.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.3% | 58.0% | 57.5% | 47.9% | 43.5% | 54.2% |
| OMIM allelic variants recovered ↑ | 65.0% | 66.7% | 67.2% | 19.2% | 12.3% | 59.9% |
| Causal gene F1 ↑ | 98.8% | 96.3% | 96.3% | 97.4% | 97.4% | 98.8% |
| Inheritance matches OMIM ↑ | 88.9% | 88.9% | 92.6% | 88.9% | 77.8% | 85.2% |

### 9 or more references — 17 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 96.1% | 97.2% | 49.6% | 96.1% | 95.3% |
| … same, before the repair round ↓ | 0.4% | 0.2% | 0.5% | 23.0% | 1.4% | 0.4% |
| OMIM per-paper facts conveyed ↑ | 50.6% | 51.9% | 51.8% | 18.6% | 16.7% | 49.7% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.9% | 0.8% | 0.2% | 0.5% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 37.5% | 40.8% | 39.7% | 39.7% | 30.4% | 37.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.1% | 59.9% | 60.9% | 59.2% | 50.6% | 55.9% |
| OMIM allelic variants recovered ↑ | 68.5% | 69.8% | 69.6% | 13.1% | 7.5% | 68.3% |
| Causal gene F1 ↑ | 97.9% | 97.9% | 97.9% | 97.9% | 97.8% | 91.7% |
| Inheritance matches OMIM ↑ | 94.1% | 88.2% | 88.2% | 88.2% | 76.5% | 94.1% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.6% | 96.0% | 96.2% | 52.4% | 93.2% | 92.4% |
| … same, before the repair round ↓ | 0.1% | 0.5% | 0.1% | 19.9% | 0.4% | 0.4% |
| OMIM per-paper facts conveyed ↑ | 56.1% | 55.7% | 55.4% | 29.1% | 24.8% | 52.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.3% | 0.9% | 0.4% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 40.8% | 40.0% | 39.2% | 38.4% | 32.7% | 39.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.6% | 62.3% | 62.3% | 59.2% | 49.5% | 60.9% |
| OMIM allelic variants recovered ↑ | 68.7% | 72.2% | 71.4% | 27.8% | 17.5% | 66.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 94.7% | 94.7% | 94.4% |
| Inheritance matches OMIM ↑ | 79.0% | 89.5% | 84.2% | 94.7% | 73.7% | 89.5% |

### 610000-615999 — 20 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.0% | 95.6% | 96.0% | 53.5% | 94.6% | 94.3% |
| … same, before the repair round ↓ | 0.3% | 0.2% | 0.2% | 21.9% | 0.9% | 0.7% |
| OMIM per-paper facts conveyed ↑ | 52.1% | 53.4% | 53.5% | 23.2% | 18.8% | 51.2% |
| OMIM per-paper facts contradicted ↓ | 1.2% | 0.6% | 0.8% | 0.5% | 0.4% | 1.3% |
| Clinical synopsis HPO F1, exact ↑ | 32.1% | 36.5% | 35.9% | 31.6% | 26.6% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.5% | 54.2% | 54.4% | 46.3% | 40.3% | 49.5% |
| OMIM allelic variants recovered ↑ | 70.7% | 72.7% | 73.4% | 18.5% | 13.1% | 70.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.0% | 95.0% | 95.0% | 100.0% | 100.0% | 100.0% |

### 616000-619999 — 20 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 96.8% | 97.1% | 60.6% | 95.0% | 94.7% |
| … same, before the repair round ↓ | 0.3% | 0.1% | 0.0% | 16.3% | 0.0% | 2.1% |
| OMIM per-paper facts conveyed ↑ | 53.4% | 55.4% | 54.8% | 18.4% | 19.6% | 48.9% |
| OMIM per-paper facts contradicted ↓ | 0.9% | 0.9% | 0.9% | 2.1% | 0.6% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 33.5% | 35.0% | 34.8% | 26.1% | 21.0% | 32.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.0% | 55.7% | 54.7% | 43.5% | 39.0% | 52.4% |
| OMIM allelic variants recovered ↑ | 82.1% | 81.1% | 80.4% | 12.8% | 12.8% | 73.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.0% | 95.0% | 95.0% | 85.0% | 70.0% | 85.0% |

### 620000 onward — 18 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 97.0% | 97.9% | 49.2% | 94.5% | 96.5% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.2% | 26.9% | 0.0% | 0.1% |
| OMIM per-paper facts conveyed ↑ | 52.0% | 57.2% | 56.8% | 10.3% | 8.0% | 52.2% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.1% | 0.1% | 0.2% | 0.2% | 0.1% |
| Clinical synopsis HPO F1, exact ↑ | 35.0% | 34.4% | 33.9% | 16.6% | 16.8% | 33.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.5% | 54.2% | 52.8% | 30.8% | 28.3% | 53.2% |
| OMIM allelic variants recovered ↑ | 60.6% | 66.8% | 64.0% | 7.8% | 7.8% | 66.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 94.4% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 44.4% | 44.4% | 94.4% |

### classic (1xxxxx-5xxxxx) — 20 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 95.4% | 95.3% | 41.6% | 94.4% | 94.7% |
| … same, before the repair round ↓ | 0.6% | 0.9% | 0.4% | 26.8% | 1.7% | 0.4% |
| OMIM per-paper facts conveyed ↑ | 40.9% | 43.4% | 41.7% | 20.2% | 18.8% | 41.2% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.8% | 0.7% | 0.2% | 0.7% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 29.9% | 32.4% | 32.8% | 37.5% | 31.0% | 30.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.8% | 55.2% | 57.4% | 58.9% | 52.3% | 53.3% |
| OMIM allelic variants recovered ↑ | 45.6% | 45.6% | 46.2% | 10.9% | 7.0% | 41.0% |
| Causal gene F1 ↑ | 96.5% | 93.0% | 93.0% | 94.7% | 94.5% | 91.2% |
| Inheritance matches OMIM ↑ | 95.0% | 90.0% | 95.0% | 90.0% | 80.0% | 85.0% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Generation: model calls | 7.0 | 1.8 | 1.8 | 1.6 | 9.2 | 7.0 |
| Generation: list price | $0.58 | $0.27 | $0.29 | $0.07 | $0.71 | $0.63 |
| Generation: input / output tokens | 56,792 / 15,574 | 21,786 / 6,340 | 61,203 / 9,013 | 6,209 / 2,293 | 57,840 / 18,521 | 65,793 / 17,512 |
| Generation: model time (s) | 125 | 52 | 76 | 24 | 174 | 145 |
| Audit and repair: list price | $0.79 | $0.75 | $0.71 | $0.51 | $0.31 | $0.79 |
| Scoring against OMIM: list price | $0.20 | $0.20 | $0.19 | $0.15 | $0.13 | $0.20 |
| Everything: list price | $1.56 | $1.23 | $1.20 | $0.73 | $1.16 | $1.62 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 102 | 103 | 105 | 99.0% | 97.1% | 98.1% |
| Disease → causal gene | Direct reading | 99 | 100 | 105 | 99.0% | 94.3% | 96.6% |
| Disease → causal gene | Agentic curator | 100 | 101 | 105 | 99.0% | 95.2% | 97.1% |
| Disease → causal gene | Memory only (control) | 86 | 88 | 105 | 97.7% | 81.9% | 89.1% |
| Disease → causal gene | Recall, then verify | 85 | 87 | 105 | 97.7% | 81.0% | 88.5% |
| Disease → causal gene | Case table first | 97 | 102 | 105 | 95.1% | 92.4% | 93.7% |
| Disease → mode of inheritance | Evidence graph | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → mode of inheritance | Direct reading | 98 | 102 | 103 | 96.1% | 95.2% | 95.6% |
| Disease → mode of inheritance | Agentic curator | 97 | 101 | 103 | 96.0% | 94.2% | 95.1% |
| Disease → mode of inheritance | Memory only (control) | 85 | 88 | 103 | 96.6% | 82.5% | 89.0% |
| Disease → mode of inheritance | Recall, then verify | 76 | 79 | 103 | 96.2% | 73.8% | 83.5% |
| Disease → mode of inheritance | Case table first | 97 | 102 | 103 | 95.1% | 94.2% | 94.6% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 749 | 2,015 | 2,326 | 37.2% | 32.2% | 34.5% |
| Disease → phenotype (HPO, exact id) | Direct reading | 689 | 1,559 | 2,344 | 44.2% | 29.4% | 35.3% |
| Disease → phenotype (HPO, exact id) | Agentic curator | 667 | 1,441 | 2,339 | 46.3% | 28.5% | 35.3% |
| Disease → phenotype (HPO, exact id) | Memory only (control) | 362 | 644 | 2,332 | 56.2% | 15.5% | 24.3% |
| Disease → phenotype (HPO, exact id) | Recall, then verify | 269 | 466 | 2,322 | 57.7% | 11.6% | 19.3% |
| Disease → phenotype (HPO, exact id) | Case table first | 750 | 2,139 | 2,311 | 35.1% | 32.5% | 33.7% |
| Disease → allelic variant | Evidence graph | 271 | 381 | 428 | 71.1% | 63.3% | 67.0% |
| Disease → allelic variant | Direct reading | 274 | 314 | 428 | 87.3% | 64.0% | 73.9% |
| Disease → allelic variant | Agentic curator | 276 | 320 | 428 | 86.2% | 64.5% | 73.8% |
| Disease → allelic variant | Memory only (control) | 43 | 44 | 428 | 97.7% | 10.1% | 18.2% |
| Disease → allelic variant | Recall, then verify | 31 | 31 | 427 | 100.0% | 7.3% | 13.5% |
| Disease → allelic variant | Case table first | 262 | 399 | 428 | 65.7% | 61.2% | 63.4% |
