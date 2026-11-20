# Improving on direct reading: evaluation (run `direct_improve`)

41 entries with at least one paper readable in full and a direct-reading draft; 38 complete for every arm are compared. No repair round for any arm. Facts conveyed = (present + half of partial) / judged frozen facts, mean over entries. Differences are arm minus baseline in percentage points with a 95% percentile bootstrap interval over entries (10,000 resamples, seed 7), entries better/worse/tied, exact sign test, Holm-adjusted across the three arms. Whether the supplied text states a fact is the stored availability judgement (a model judgement with verified quotes, not checked by a curator).

## Completion

| Arm | Complete | Incomplete | No draft | Not run | Entries not complete |
|---|---|---|---|---|---|
| Baseline (direct, before repair) | 41 | 0 | 0 | 0 | – |
| D1 checklist | 41 | 0 | 0 | 0 | – |
| D2 completeness pass | 38 | 0 | 3 | 0 | 118210 (no_draft), 617232 (no_draft), 621030 (no_draft) |
| D3 three-draft merge | 41 | 0 | 0 | 0 | – |

## All facts

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 60.3% | 38 | 80.7 | – | – | – | – | – |
| D1 checklist | 61.9% | 38 | 80.7 | +1.6 | +0.5 to +2.7 | 23/11/4 | 0.058 | 0.058 |
| D2 completeness pass | 62.9% | 38 | 80.7 | +2.6 | +1.7 to +3.6 | 28/4/6 | 0.000 | 0.000 |
| D3 three-draft merge | 63.4% | 38 | 80.7 | +3.1 | +2.1 to +4.2 | 31/3/4 | 0.000 | 0.000 |

## Facts the supplied text states

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.3% | 38 | 40.2 | – | – | – | – | – |
| D1 checklist | 92.7% | 38 | 40.2 | +1.4 | +0.0 to +2.7 | 17/9/12 | 0.169 | 0.169 |
| D2 completeness pass | 94.7% | 38 | 40.2 | +3.4 | +2.1 to +4.8 | 24/3/11 | 0.000 | 0.000 |
| D3 three-draft merge | 94.2% | 38 | 40.2 | +2.9 | +1.7 to +4.2 | 23/1/14 | 0.000 | 0.000 |

## … on papers readable in full

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.5% | 34 | 28.0 | – | – | – | – | – |
| D1 checklist | 90.5% | 34 | 28.0 | +2.0 | +0.4 to +3.7 | 16/7/11 | 0.093 | 0.093 |
| D2 completeness pass | 93.0% | 34 | 28.0 | +4.5 | +2.9 to +6.3 | 22/1/11 | 0.000 | 0.000 |
| D3 three-draft merge | 92.1% | 34 | 28.0 | +3.7 | +2.1 to +5.5 | 23/3/8 | 0.000 | 0.000 |

## … on papers readable as abstract only

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | 11.9 | – | – | – | – | – |
| D1 checklist | 97.0% | 31 | 11.9 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 | 1.000 |
| D2 completeness pass | 97.8% | 31 | 11.9 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | 11.9 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 | 0.867 |

## Facts the supplied text does not state

| Arm | Mean over entries | Entries | Facts per entry | Difference | 95% CI | Better/worse/tied | Sign p | Holm p |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 10.5% | 36 | 25.5 | – | – | – | – | – |
| D1 checklist | 10.2% | 36 | 25.5 | -0.3 | -1.9 to +1.3 | 11/9/16 | 0.824 | 1.000 |
| D2 completeness pass | 10.3% | 36 | 25.5 | -0.1 | -1.3 to +0.7 | 6/3/27 | 0.508 | 1.000 |
| D3 three-draft merge | 12.0% | 36 | 25.5 | +1.5 | +0.4 to +2.7 | 17/2/17 | 0.001 | 0.002 |

## Claims judged by the audit (20 audited entries)

Audited entries (random.Random(20261120).sample(sorted(entries), 20)): 604928, 606763, 607602, 607734, 607876, 608133, 611521, 614651, 614856, 615710, 617927, 618400, 618808, 618875, 619201, 620022, 620029, 620098, 620481, 620662. Shares are over checkable claims; a stopped audit call leaves its paper's claims not checkable and does not affect completion.

| Arm | Entries | Checkable claims | Supported | Partly | Unsupported | Contradicted | Not checkable | Entries with not-checkable claims |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 20 | 2,578 | 2,501 (97.0%) | 71 (2.8%) | 6 (0.2%) | 0 (0.0%) | 67 | 615710 |
| D1 checklist | 20 | 2,969 | 2,889 (97.3%) | 70 (2.4%) | 8 (0.3%) | 2 (0.1%) | 87 | 615710 |
| D2 completeness pass | 20 | 3,278 | 3,185 (97.2%) | 89 (2.7%) | 4 (0.1%) | 0 (0.0%) | 85 | 615710 |
| D3 three-draft merge | 20 | 3,225 | 3,091 (95.8%) | 116 (3.6%) | 14 (0.4%) | 4 (0.1%) | 106 | 615710 |

## Size, variants, calls and price

| Arm | Characters per entry | Checkable claims per audited entry | Variant recall (entries) | Variant precision (entries) | New calls per entry (generate / audit / score) | List price per entry, new | List price per entry, method | Wall minutes per entry |
|---|---|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 10,802 | 129 | 82.6% (38) | 87.1% (38) | 0.2 (0.0 / 0.0 / 0.2) | $0.01 | $1.09 | 0.4 |
| D1 checklist | 11,837 | 148 | 81.7% (38) | 87.5% (38) | 10.1 (1.8 / 2.9 / 5.5) | $1.14 | $1.15 | 2.6 |
| D2 completeness pass | 14,412 | 164 | 82.6% (38) | 87.1% (38) | 12.9 (6.1 / 2.9 / 3.9) | $1.62 | $2.10 | 3.1 |
| D3 three-draft merge | 14,245 | 161 | 82.2% (38) | 83.4% (38) | 11.9 (3.5 / 2.8 / 5.6) | $1.82 | $2.32 | 3.8 |

Characters and variants are over the compared entries; calls and price over every entry the arm ran. 'New' counts calls made in this run (the baseline's draft and audit come from the cache); 'method' is what the arm costs from scratch, including the cached baseline draft that D2 and D3 start from.

## Stops

- Baseline (direct, before repair): no draft 0; safety stops by step {'audit': 1}
- D1 checklist: no draft 0; safety stops by step {'audit': 1}
- D2 completeness pass: no draft 3 (118210, 617232, 621030); safety stops by step {'generate': 3, 'audit': 1}
- D3 three-draft merge: no draft 0; safety stops by step {'audit': 1}

## D2: what the completeness pass did

Entries 38; omissions listed 768, kept (quote verified) 767; revision called on 38; sentences added 959, of which citing only papers without listed omissions 0; entries where the model changed a carried-over field: none; citations lost: none.

## D3: what the merge did

Entries 41; draft paragraphs 2,486 merged into 852 (807 from more than one draft); rejected as longer than their sources 0; unknown IDs 0; unsourced paragraphs dropped 0; draft paragraphs left out and put back 0, left out and not put back (their papers cited elsewhere) 0; variant groups restored 0; citations lost: none. Sentences of each draft with at least 85% of their content words in the merged draft (rough): A 3,454 of 3,550; B 3,401 of 3,556; C 3,324 of 3,479.

Calls: 1,624 new model calls of the 2,200 cap (pilot included), $217.54 list price; safety stops 7, refusals 0, errors 1.
