# OMIM facts conveyed, by whether the available text states the fact — run `omim100`

93 entries: those the main comparison uses (complete for every strategy). Every frozen fact a strategy was marked on is joined by fact id with the stored judgement of whether the text available for its paper states it (stated, partly stated, not stated; `gaps --frozen`, a model judgement with verified quotes, not checked by a curator). The judgement is a property of the supplied text, so every strategy is scored on the same facts in each restriction. Coverage = (present + half of partial) / facts. *Mean over entries* is over entries with at least one fact in the restriction (n entries); *pooled* is over facts. Differences are strategy minus Direct reading in percentage points, mean over the entries with such facts, with a 95% percentile bootstrap interval over entries (10,000 resamples, seed 7, as in `compare`), then entries better / worse / tied.

## Join and sanity check

Facts without an availability judgement: 0 (excluded). The unrestricted mean recomputed from the joined fact marks against the main comparison's mean of OMIM facts conveyed:

| Strategy | Facts judged | Joined | Without availability judgement | Unrestricted mean, recomputed | Main comparison | Same to 0.1 |
|---|---|---|---|---|---|---|
| Evidence graph | 6,239 | 6,239 | 0 | 48.6% | 48.6% | yes |
| Direct reading | 6,239 | 6,239 | 0 | 49.1% | 49.1% | yes |
| Agentic curator | 6,239 | 6,239 | 0 | 48.4% | 48.4% | yes |
| Memory only (control) | 6,239 | 6,239 | 0 | 15.1% | 15.1% | yes |
| Recall, then verify | 6,239 | 6,239 | 0 | 14.6% | 14.6% | yes |
| Case table first | 6,239 | 6,239 | 0 | 47.2% | 47.2% | yes |

## The facts, by availability

Pooled over the facts of the compared entries (identical for every strategy), by how the paragraph's paper(s) could be read.

| Paper read as | Facts | Stated | Partly stated | Not stated | Unjudged |
|---|---|---|---|---|---|
| Full text | 1,639 | 1,246 | 253 | 140 | 0 |
| Abstract only | 4,221 | 1,099 | 883 | 2,239 | 0 |
| Title only | 379 | 27 | 62 | 290 | 0 |
| All papers | 6,239 | 2,372 | 1,198 | 2,669 | 0 |

## Summary: mean over entries

| Strategy | All facts | Stated | Stated or partly | Not stated | Stated, full-text papers | Stated, abstract-only papers |
|---|---|---|---|---|---|---|
| Evidence graph | 48.6% | 94.2% | 77.5% | 5.5% | 90.2% | 96.6% |
| Direct reading | 49.1% | 94.4% | 77.5% | 6.9% | 88.5% | 97.1% |
| Agentic curator | 48.4% | 93.6% | 76.9% | 6.3% | 88.3% | 96.3% |
| Memory only (control) | 15.1% | 23.3% | 23.3% | 8.2% | 10.9% | 28.2% |
| Recall, then verify | 14.6% | 28.8% | 26.0% | 2.1% | 13.6% | 36.5% |
| Case table first | 47.2% | 91.0% | 75.4% | 5.9% | 80.1% | 95.5% |
| Entries (n) | 93 | 89 | 93 | 90 | 40 | 79 |

| Difference from Direct reading | All facts | Stated | Stated or partly | Not stated | Stated, full-text papers | Stated, abstract-only papers |
|---|---|---|---|---|---|---|
| Evidence graph | -0.5 (-1.5 to +0.5); 33/45/15 | -0.3 (-2.1 to +1.3); 25/21/43 | -0.0 (-1.5 to +1.4); 41/41/11 | -1.4 (-3.4 to +0.7); 16/28/46 | +1.7 (-0.7 to +4.0); 18/15/7 | -0.5 (-2.5 to +1.2); 10/11/58 |
| Agentic curator | -0.6 (-1.3 to +0.0); 31/42/20 | -0.8 (-2.6 to +0.4); 20/23/46 | -0.7 (-2.0 to +0.4); 36/37/20 | -0.5 (-1.8 to +1.0); 16/27/47 | -0.2 (-1.8 to +1.2); 13/15/12 | -0.8 (-2.6 to +0.5); 11/9/59 |
| Memory only (control) | -34.0 (-39.2 to -28.7); 7/85/1 | -71.1 (-75.9 to -66.0); 0/85/4 | -54.2 (-59.2 to -48.9); 4/88/1 | +1.3 (-1.4 to +4.6); 37/30/23 | -77.6 (-82.5 to -72.3); 0/40/0 | -68.9 (-75.1 to -62.3); 0/74/5 |
| Recall, then verify | -34.5 (-39.3 to -30.0); 2/89/2 | -65.6 (-70.6 to -60.2); 0/84/5 | -51.5 (-55.9 to -47.1); 1/88/4 | -4.8 (-6.7 to -3.0); 11/50/29 | -74.9 (-80.2 to -69.3); 0/40/0 | -60.6 (-67.3 to -53.5); 0/71/8 |
| Case table first | -1.9 (-3.1 to -0.7); 31/48/14 | -3.4 (-5.6 to -1.6); 16/42/31 | -2.1 (-3.6 to -0.6); 27/48/18 | -1.0 (-3.1 to +1.2); 27/26/37 | -8.4 (-14.3 to -3.8); 9/28/3 | -1.6 (-3.6 to +0.2); 12/21/46 |

## All facts (unrestricted), all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 48.6% | 93 | 47.6% | 6,239 | 2,562 / 811 / 2,840 / 26 | -0.5 | -1.5 to +0.5 | 33 / 45 / 15 |
| Direct reading | 49.1% | 93 | 48.6% | 6,239 | 2,620 / 820 / 2,771 / 28 | – | – | – |
| Agentic curator | 48.4% | 93 | 47.9% | 6,239 | 2,593 / 796 / 2,820 / 30 | -0.6 | -1.3 to +0.0 | 31 / 42 / 20 |
| Memory only (control) | 15.1% | 93 | 12.7% | 6,239 | 502 / 578 / 5,133 / 26 | -34.0 | -39.2 to -28.7 | 7 / 85 / 1 |
| Recall, then verify | 14.6% | 93 | 12.5% | 6,239 | 502 / 553 / 5,167 / 17 | -34.5 | -39.3 to -30.0 | 2 / 89 / 2 |
| Case table first | 47.2% | 93 | 46.1% | 6,239 | 2,490 / 769 / 2,948 / 32 | -1.9 | -3.1 to -0.7 | 31 / 48 / 14 |

## Facts stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 94.2% | 89 | 92.9% | 2,372 | 2,144 / 121 / 106 / 1 | -0.3 | -2.1 to +1.3 | 25 / 21 / 43 |
| Direct reading | 94.4% | 89 | 91.8% | 2,372 | 2,114 / 128 / 129 / 1 | – | – | – |
| Agentic curator | 93.6% | 89 | 91.3% | 2,372 | 2,099 / 134 / 139 / 0 | -0.8 | -2.6 to +0.4 | 20 / 23 / 46 |
| Memory only (control) | 23.3% | 89 | 15.5% | 2,372 | 251 / 233 / 1,880 / 8 | -71.1 | -75.9 to -66.0 | 0 / 85 / 4 |
| Recall, then verify | 28.8% | 89 | 20.3% | 2,372 | 378 / 209 / 1,782 / 3 | -65.6 | -70.6 to -60.2 | 0 / 84 / 5 |
| Case table first | 91.0% | 89 | 87.5% | 2,372 | 2,016 / 118 / 235 / 3 | -3.4 | -5.6 to -1.6 | 16 / 42 / 31 |

## Facts stated or partly stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 77.5% | 93 | 80.5% | 3,570 | 2,504 / 743 / 308 / 15 | -0.0 | -1.5 to +1.4 | 41 / 41 / 11 |
| Direct reading | 77.5% | 93 | 80.2% | 3,570 | 2,499 / 725 / 333 / 13 | – | – | – |
| Agentic curator | 76.9% | 93 | 79.6% | 3,570 | 2,487 / 709 / 360 / 14 | -0.7 | -2.0 to +0.4 | 36 / 37 / 20 |
| Memory only (control) | 23.3% | 93 | 17.5% | 3,570 | 398 / 452 / 2,705 / 15 | -54.2 | -59.2 to -48.9 | 4 / 88 / 1 |
| Recall, then verify | 26.0% | 93 | 20.8% | 3,570 | 488 / 506 / 2,565 / 11 | -51.5 | -55.9 to -47.1 | 1 / 88 / 4 |
| Case table first | 75.4% | 93 | 76.9% | 3,570 | 2,409 / 675 / 468 / 18 | -2.1 | -3.6 to -0.6 | 27 / 48 / 18 |

## Facts not stated in the available text, all papers

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 5.5% | 90 | 3.5% | 2,669 | 58 / 68 / 2,532 / 11 | -1.4 | -3.4 to +0.7 | 16 / 28 / 46 |
| Direct reading | 6.9% | 90 | 6.3% | 2,669 | 121 / 95 / 2,438 / 15 | – | – | – |
| Agentic curator | 6.3% | 90 | 5.6% | 2,669 | 106 / 87 / 2,460 / 16 | -0.5 | -1.8 to +1.0 | 16 / 27 / 47 |
| Memory only (control) | 8.2% | 90 | 6.3% | 2,669 | 104 / 126 / 2,428 / 11 | +1.3 | -1.4 to +4.6 | 37 / 30 / 23 |
| Recall, then verify | 2.1% | 90 | 1.4% | 2,669 | 14 / 47 / 2,602 / 6 | -4.8 | -6.7 to -3.0 | 11 / 50 / 29 |
| Case table first | 5.9% | 90 | 4.8% | 2,669 | 81 / 94 / 2,480 / 14 | -1.0 | -3.1 to +1.2 | 27 / 26 / 37 |

## Facts stated in the available text, papers readable in full

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 90.2% | 40 | 89.0% | 1,246 | 1,062 / 95 / 88 / 1 | +1.7 | -0.7 to +4.0 | 18 / 15 / 7 |
| Direct reading | 88.5% | 40 | 87.0% | 1,246 | 1,034 / 101 / 110 / 1 | – | – | – |
| Agentic curator | 88.3% | 40 | 86.5% | 1,246 | 1,025 / 106 / 115 / 0 | -0.2 | -1.8 to +1.2 | 13 / 15 / 12 |
| Memory only (control) | 10.9% | 40 | 10.4% | 1,246 | 72 / 116 / 1,055 / 3 | -77.6 | -82.5 to -72.3 | 0 / 40 / 0 |
| Recall, then verify | 13.6% | 40 | 13.0% | 1,246 | 102 / 119 / 1,024 / 1 | -74.9 | -80.2 to -69.3 | 0 / 40 / 0 |
| Case table first | 80.1% | 40 | 80.5% | 1,246 | 958 / 89 / 196 / 3 | -8.4 | -14.3 to -3.8 | 9 / 28 / 3 |

## Facts stated in the available text, papers readable as abstract only

| Strategy | Mean over entries | Entries | Pooled over facts | Facts | Present / partial / absent / contradicted | Difference from Direct reading | 95% interval | Better / worse / tied |
|---|---|---|---|---|---|---|---|---|
| Evidence graph | 96.6% | 79 | 97.2% | 1,099 | 1,055 / 26 / 18 / 0 | -0.5 | -2.5 to +1.2 | 10 / 11 / 58 |
| Direct reading | 97.1% | 79 | 97.0% | 1,099 | 1,053 / 27 / 19 / 0 | – | – | – |
| Agentic curator | 96.3% | 79 | 96.6% | 1,099 | 1,048 / 28 / 23 / 0 | -0.8 | -2.6 to +0.5 | 11 / 9 / 59 |
| Memory only (control) | 28.2% | 79 | 20.9% | 1,099 | 173 / 113 / 808 / 5 | -68.9 | -75.1 to -62.3 | 0 / 74 / 5 |
| Recall, then verify | 36.5% | 79 | 28.3% | 1,099 | 268 / 87 / 742 / 2 | -60.6 | -67.3 to -53.5 | 0 / 71 / 8 |
| Case table first | 95.5% | 79 | 95.1% | 1,099 | 1,031 / 29 / 39 / 0 | -1.6 | -3.6 to +0.2 | 12 / 21 / 46 |
