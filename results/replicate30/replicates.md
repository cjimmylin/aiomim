# Run-to-run variation: replicate30_r1, replicate30_r2, replicate30_r3

A replicate salts every model call, so it re-runs generation, the claim audit and repair, and the model-judged scoring (OMIM fact coverage, variant matching) together: the variation below is that of the whole measurement, not of the writer alone. The gold standard (public OMIM-derived records) is the same in every replicate; the facts the judge splits each OMIM paragraph into are not.

Values are in percentage points (a score of 0.53 is 53.0). Within-entry SD: the spread of one entry's score across replicates. Between-entry SD: the spread of entries' true scores, net of run noise. Within share: run noise as a share of the total variance of a single entry-run score.

## Direct reading (30 entries scored in every replicate)

| Measure | Replicate means | Range of the mean | Within-entry SD | Between-entry SD | Within share |
|---|---|---|---|---|---|
| OMIM facts conveyed | 50.0 / 46.8 / 48.3 | 3.2 | 4.0 | 19.0 | 4% |
| Claims supported | 95.8 / 95.2 / 95.4 | 0.6 | 2.9 | 4.1 | 34% |
| Claims unsupported or contradicted, before repair | 0.3 / 0.2 / 0.2 | 0.1 | 0.6 | 0.5 | 64% |
| Clinical synopsis, exact HPO F1 | 34.6 / 32.8 / 33.1 | 1.8 | 4.2 | 20.8 | 4% |
| OMIM allelic variants recovered | 60.4 / 60.1 / 59.3 | 1.1 | 4.4 | 38.9 | 1% |
| Causal gene F1 | 95.4 / 95.4 / 95.4 | 0.0 | 0.0 | 19.4 | 0% |
| Inheritance matches OMIM | 90.0 / 90.0 / 93.3 | 3.3 | 10.5 | 26.9 | 13% |

## Evidence graph (30 entries scored in every replicate)

| Measure | Replicate means | Range of the mean | Within-entry SD | Between-entry SD | Within share |
|---|---|---|---|---|---|
| OMIM facts conveyed | 50.1 / 49.6 / 48.0 | 2.1 | 4.6 | 19.9 | 5% |
| Claims supported | 96.5 / 97.0 / 97.2 | 0.7 | 2.1 | 2.1 | 49% |
| Claims unsupported or contradicted, before repair | 0.5 / 0.3 / 0.4 | 0.2 | 0.7 | 0.5 | 63% |
| Clinical synopsis, exact HPO F1 | 32.9 / 32.9 / 33.5 | 0.6 | 3.4 | 19.3 | 3% |
| OMIM allelic variants recovered | 61.8 / 61.8 / 57.8 | 4.0 | 11.9 | 37.7 | 9% |
| Causal gene F1 | 97.7 / 97.7 / 97.7 | 0.0 | 0.0 | 8.6 | 0% |
| Inheritance matches OMIM | 93.3 / 93.3 / 93.3 | 0.0 | 0.0 | 25.4 | 0% |

## Evidence graph minus direct reading, per replicate (30 entries)

| Measure | replicate30_r1 | replicate30_r2 | replicate30_r3 | Within-entry SD of the difference | Smallest difference distinguishable from run noise at n=97 |
|---|---|---|---|---|---|
| OMIM facts conveyed | 0.1 [-1.6, 1.8] | 2.8 [0.5, 5.5] | -0.3 [-3.5, 3.0] | 5.9 | ±1.2 |
| Claims supported | 0.7 [-1.0, 2.9] | 1.9 [0.5, 3.4] | 1.8 [0.1, 3.7] | 3.1 | ±0.6 |
| Claims unsupported or contradicted, before repair | 0.2 [-0.3, 0.7] | 0.1 [-0.2, 0.3] | 0.2 [-0.2, 0.5] | 1.0 | ±0.2 |
| Clinical synopsis, exact HPO F1 | -1.8 [-5.8, 2.1] | 0.1 [-4.1, 3.9] | 0.4 [-2.9, 3.8] | 6.2 | ±1.2 |
| OMIM allelic variants recovered | 1.4 [-5.0, 10.0] | 1.6 [-5.3, 10.5] | -1.5 [-7.4, 3.3] | 12.9 | ±2.6 |
| Causal gene F1 | 2.3 [0.0, 6.9] | 2.3 [0.0, 6.9] | 2.3 [0.0, 6.9] | 0.0 | ±0.0 |
| Inheritance matches OMIM | 3.3 [0.0, 10.0] | 3.3 [0.0, 10.0] | 0.0 [-10.0, 10.0] | 10.5 | ±2.1 |

Intervals are 95% bootstrap intervals over entries. The last column is 1.96 × (within-entry SD of the per-entry difference) / √97: the size a mean paired difference over 97 entries, each run once, would have to exceed for run-to-run noise alone to produce it less than 5% of the time. It is a floor, not an interval: the usual bootstrap interval over entries already contains this noise, since each entry's difference was measured once.

In plain terms: on 97 entries run once, a difference between two strategies in OMIM facts conveyed smaller than about 1.2 points could be run noise alone (on these 30 entries, about 2.1 points). Larger differences are not thereby real differences between methods: the choice of entries adds its own, larger uncertainty, which the bootstrap interval over entries measures.

## Model usage of each pass

| Run | Calls | From cache | Made afresh | List price |
|---|---|---|---|---|
| replicate30_r1 | 943 | 851 | 92 | $10.98 |
| replicate30_r2 | 1164 | 4 | 1160 | $84.78 |
| replicate30_r3 | 1172 | 7 | 1165 | $81.25 |
