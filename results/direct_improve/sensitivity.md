# Improving on direct reading: every entry, stopped entries put back

All 41 entries of the run (the baseline completed every one). Two rules for an entry an arm lost to a stopped reply: counted as zero (as in the main comparison's sensitivity analysis), or, for the completeness-pass arms, the draft the revision would have revised is scored in its place (the baseline's draft for D2, D1's checklist draft for D4; the same text, taken from the cache). The second is what the adopted `recommended` strategy does when its revision is stopped. Incomplete drafts (a stopped check on one paper) are kept as scored under both rules. Differences are arm minus baseline in percentage points, mean over entries, 95% percentile bootstrap interval (10,000 resamples, seed 7), entries better / worse / tied, exact sign test, unadjusted. Stored scores only; no model call.

Entries lost to a stopped reply: D2 completeness pass 3 (118210, 617232, 621030); D4 checklist + completeness pass 4 (118210, 617232, 620249, 621030).
Incomplete, kept as scored: D4 checklist + completeness pass 2 (613744, 615817).

## All facts

### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 61.9% | 41 | – | – | – | – |
| D1 checklist | 63.6% | 41 | +1.7 | +0.7 to +2.8 | 26/11/4 | 0.020 |
| D2 completeness pass | 58.3% | 41 | -3.5 | -11.1 to +2.6 | 28/7/6 | <0.001 |
| D3 three-draft merge | 64.9% | 41 | +3.0 | +2.1 to +4.1 | 34/3/4 | <0.001 |
| D4 checklist + completeness pass | 57.0% | 41 | -4.8 | -13.2 to +1.9 | 28/11/2 | 0.009 |

### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 61.9% | 41 | – | – | – | – |
| D1 checklist | 63.6% | 41 | +1.7 | +0.7 to +2.8 | 26/11/4 | 0.020 |
| D2 completeness pass | 64.3% | 41 | +2.4 | +1.5 to +3.4 | 28/4/9 | <0.001 |
| D3 three-draft merge | 64.9% | 41 | +3.0 | +2.1 to +4.1 | 34/3/4 | <0.001 |
| D4 checklist + completeness pass | 64.9% | 41 | +3.1 | +1.8 to +4.3 | 32/7/2 | <0.001 |

## Facts the supplied text states

### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.0% | 41 | – | – | – | – |
| D1 checklist | 92.5% | 41 | +1.5 | +0.2 to +2.7 | 20/9/12 | 0.061 |
| D2 completeness pass | 87.7% | 41 | -3.3 | -11.5 to +3.4 | 24/6/11 | 0.001 |
| D3 three-draft merge | 94.0% | 41 | +2.9 | +1.8 to +4.2 | 26/1/14 | <0.001 |
| D4 checklist + completeness pass | 86.1% | 41 | -4.9 | -14.8 to +3.0 | 24/8/9 | 0.007 |

### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 91.0% | 41 | – | – | – | – |
| D1 checklist | 92.5% | 41 | +1.5 | +0.2 to +2.7 | 20/9/12 | 0.061 |
| D2 completeness pass | 94.2% | 41 | +3.1 | +1.9 to +4.5 | 24/3/14 | <0.001 |
| D3 three-draft merge | 94.0% | 41 | +2.9 | +1.8 to +4.2 | 26/1/14 | <0.001 |
| D4 checklist + completeness pass | 95.1% | 41 | +4.1 | +2.3 to +5.9 | 27/5/9 | <0.001 |

## … on papers readable in full

### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.4% | 37 | – | – | – | – |
| D1 checklist | 90.5% | 37 | +2.1 | +0.6 to +3.6 | 19/7/11 | 0.029 |
| D2 completeness pass | 85.5% | 37 | -3.0 | -12.4 to +4.4 | 22/4/11 | <0.001 |
| D3 three-draft merge | 92.1% | 37 | +3.6 | +2.1 to +5.3 | 26/3/8 | <0.001 |
| D4 checklist + completeness pass | 84.1% | 37 | -4.3 | -15.4 to +4.7 | 23/8/6 | 0.011 |

### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 88.4% | 37 | – | – | – | – |
| D1 checklist | 90.5% | 37 | +2.1 | +0.6 to +3.6 | 19/7/11 | 0.029 |
| D2 completeness pass | 92.6% | 37 | +4.2 | +2.6 to +5.8 | 22/1/14 | <0.001 |
| D3 three-draft merge | 92.1% | 37 | +3.6 | +2.1 to +5.3 | 26/3/8 | <0.001 |
| D4 checklist + completeness pass | 94.0% | 37 | +5.6 | +3.5 to +7.8 | 26/5/6 | <0.001 |

## … on papers readable as abstract only

### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | – | – | – | – |
| D1 checklist | 97.0% | 31 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 |
| D2 completeness pass | 97.8% | 31 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 |
| D4 checklist + completeness pass | 94.9% | 31 | -1.9 | -9.4 to +3.0 | 7/4/20 | 0.549 |

### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 96.9% | 31 | – | – | – | – |
| D1 checklist | 97.0% | 31 | +0.2 | -1.0 to +1.3 | 4/4/23 | 1.000 |
| D2 completeness pass | 97.8% | 31 | +1.0 | -0.3 to +2.9 | 5/4/22 | 1.000 |
| D3 three-draft merge | 97.8% | 31 | +1.0 | +0.1 to +2.1 | 6/2/23 | 0.289 |
| D4 checklist + completeness pass | 98.2% | 31 | +1.3 | -0.5 to +3.5 | 7/3/21 | 0.344 |

## Facts the supplied text does not state

### A missing draft counted as zero

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 11.6% | 38 | – | – | – | – |
| D1 checklist | 11.3% | 38 | -0.2 | -1.8 to +1.3 | 11/9/18 | 0.824 |
| D2 completeness pass | 9.8% | 38 | -1.8 | -5.6 to +0.5 | 6/4/28 | 0.754 |
| D3 three-draft merge | 13.0% | 38 | +1.4 | +0.4 to +2.6 | 17/2/19 | <0.001 |
| D4 checklist + completeness pass | 9.7% | 38 | -1.9 | -5.9 to +0.9 | 11/11/16 | 1.000 |

### A stopped revision replaced by the draft it would have revised (as `recommended` does)

| Arm | Mean over entries | Entries | Difference | 95% CI | Better/worse/tied | Sign p |
|---|---|---|---|---|---|---|
| Baseline (direct, before repair) | 11.6% | 38 | – | – | – | – |
| D1 checklist | 11.3% | 38 | -0.2 | -1.8 to +1.3 | 11/9/18 | 0.824 |
| D2 completeness pass | 11.4% | 38 | -0.1 | -1.3 to +0.7 | 6/3/29 | 0.508 |
| D3 three-draft merge | 13.0% | 38 | +1.4 | +0.4 to +2.6 | 17/2/19 | <0.001 |
| D4 checklist + completeness pass | 11.6% | 38 | +0.0 | -1.3 to +1.4 | 11/10/17 | 1.000 |

