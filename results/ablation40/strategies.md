# Generation strategies compared — run `ablation40`

38 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 38 of the run's 40 entries qualify; left out: 613744, 619681. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 40 | 0 | 0 |
| Direct reading | 40 | 0 | 0 |
| Case table first | 40 | 0 | 0 |
| Evidence graph, matched | 39 | 1: 619681 (1 paper) | 0 |
| Evidence graph plus text | 39 | 1: 619681 (1 paper) | 0 |
| Case table, matched | 38 | 2: 613744 (1 paper), 619681 (1 paper) | 0 |
| Case table plus text | 38 | 2: 613744 (1 paper), 619681 (1 paper) | 0 |

For the reconciled case database the failed papers are read from the case table's record of the same entry (both run the same cached case extraction; drafts written before the reconciled strategy recorded them itself): 613744, 619681.

## How the scores are counted

- **OMIM facts conveyed** is scored against one fixed list of facts per OMIM paragraph, split without sight of any draft and shared by every strategy. The earlier scoring, which split the paragraph afresh for each draft, is shown as a secondary row.

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Evidence graph: variants 2; Direct reading: variants 2; Case table first: variants 2; Evidence graph, matched: variants 2; Evidence graph plus text: variants 2; Case table, matched: variants 2; Case table plus text: variants 2.

- **n.** A value rests on all 38 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Evidence graph** (`kg`): Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph.
- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.
- **Evidence graph, matched** (`kg_matched`): Evidence graph with extraction at the writer's effort and synopsis terms chosen by the writer, not by rule.
- **Evidence graph plus text** (`kg_hybrid`): As the matched evidence graph, and the writer also reads the papers' text.
- **Case table, matched** (`cohort_matched`): Case table with extraction at the writer's effort and synopsis terms and inheritance chosen by the writer.
- **Case table plus text** (`cohort_hybrid`): As the matched case table, and the writer also reads the papers' text.

## Scores

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 97.9% | 96.0% | 96.8% | 98.3% | 97.0% | 98.1% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.1% | 0.0% |
| … same, before the repair round ↓ | 0.3% | 0.1% | 0.3% | 0.2% | 0.1% | 0.4% | 0.1% |
| … unsupported, before the repair round ↓ | 0.2% | 0.1% | 0.2% | 0.1% | 0.1% | 0.4% | 0.1% |
| … contradicted, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 59.4% | 58.4% | 56.1% | 60.2% | 60.2% | 58.2% | 59.1% |
| … fully (no partial credit) ↑ | 53.2% | 51.8% | 50.3% | 54.2% | 53.8% | 52.7% | 52.8% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.4% | 0.7% | 0.5% | 0.6% | 0.5% | 0.6% |
| … conveyed anywhere in the draft, not only where the paper is cited ↑ | – | – | – | – | – | – | – |
| … facts split afresh for each draft (earlier scoring) ↑ | 61.5% | 61.5% | 57.6% | 61.7% | 61.9% | 59.4% | 61.0% |
| Clinical synopsis HPO F1, exact ↑ | 37.6% | 40.1% | 37.3% | 37.8% | 39.5% | 38.3% | 39.4% |
| … precision ↑ | 40.5% | 45.2% | 40.6% | 39.4% | 42.6% | 41.2% | 42.0% |
| … recall ↑ | 44.5% | 43.8% | 46.3% | 44.9% | 44.1% | 44.1% | 44.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.1% | 59.2% | 55.8% | 56.2% | 58.1% | 56.9% | 59.4% |
| Clinical synopsis HPO F1, semantic ↑ | 66.6% | 68.7% | 66.6% | 67.0% | 68.5% | 67.6% | 68.5% |
| OMIM allelic variants recovered ↑ | 76.8% | 77.3% | 74.4% | 77.0% | 77.4% | 73.7% | 72.7% |
| Generated variants that are OMIM variants (precision) ↑ | 81.4% (n=36) | 87.8% (n=36) | 76.8% (n=36) | 81.8% (n=36) | 84.4% (n=36) | 76.5% (n=36) | 85.0% (n=36) |
| Causal gene F1 ↑ | 98.2% | 96.5% | 98.2% | 98.2% | 98.2% | 98.2% | 98.2% |
| … recall ↑ | 98.7% | 96.0% | 98.7% | 98.7% | 98.7% | 98.7% | 98.7% |
| Inheritance matches OMIM ↑ | 94.7% | 97.4% | 94.7% | 94.7% | 94.7% | 97.4% | 97.4% |
| Inheritance error: none stated ↓ | 2.6% | 0.0% | 2.6% | 2.6% | 2.6% | 0.0% | 0.0% |
| Inheritance error: a mode missing ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Inheritance error: an extra mode ↓ | 0.0% | 2.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Inheritance error: a different mode ↓ | 2.6% | 0.0% | 2.6% | 2.6% | 2.6% | 2.6% | 2.6% |
| OMIM references used ↑ | 97.9% | 96.9% | 97.5% | 97.4% | 96.5% | 97.5% | 96.4% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims audited per entry | 141.6 | 124.7 | 146.9 | 157.1 | 147.6 | 157.8 | 135.0 |
| Claims that could not be audited per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Clinical-synopsis HPO terms per entry | 25.2 | 19.0 | 29.9 | 24.0 | 21.2 | 22.5 | 20.3 |
| Allelic variants per entry | 4.6 | 3.7 | 4.7 | 4.6 | 4.0 | 4.7 | 3.7 |
| … of which not in OMIM | 1.6 | 0.6 | 1.7 | 1.6 | 0.9 | 1.8 | 0.8 |
| Papers cited per entry | 4.9 | 4.8 | 4.9 | 4.9 | 4.8 | 4.9 | 4.8 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.8 (-1.4 to -0.1); 8/25/5 | -1.8 (-3.2 to -0.6); 11/25/2 | -1.0 (-1.8 to -0.2); 12/24/2 | +0.4 (-0.3 to +1.2); 20/11/7 | -0.9 (-2.1 to +0.2); 14/22/2 | +0.3 (-0.5 to +1.1); 21/14/3 |
| … same, before the repair round ↓ | +0.2 (+0.0 to +0.4); 2/6/30 | +0.2 (+0.0 to +0.4); 4/8/26 | +0.1 (-0.0 to +0.2); 4/6/28 | +0.0 (-0.2 to +0.1); 2/5/31 | +0.3 (+0.0 to +0.7); 3/10/25 | -0.1 (-0.2 to +0.1); 3/2/33 |
| OMIM per-paper facts conveyed (primary) ↑ | +1.0 (-0.9 to +2.9); 19/15/4 | -2.3 (-4.5 to +0.0); 13/24/1 | +1.8 (+0.4 to +3.3); 24/10/4 | +1.8 (+0.5 to +3.2); 24/10/4 | -0.2 (-2.4 to +2.2); 16/20/2 | +0.6 (-1.2 to +2.6); 18/15/5 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.3 to +0.5); 5/3/30 | +0.3 (-0.1 to +0.7); 3/5/30 | +0.1 (-0.2 to +0.4); 4/3/31 | +0.1 (-0.1 to +0.4); 3/4/31 | +0.1 (-0.1 to +0.4); 3/4/31 | +0.1 (-0.1 to +0.4); 1/4/33 |
| Clinical synopsis HPO F1, exact ↑ | -2.5 (-5.1 to +0.2); 10/24/4 | -2.8 (-5.7 to +0.3); 15/21/2 | -2.3 (-4.6 to -0.1); 11/24/3 | -0.6 (-2.5 to +1.4); 14/20/4 | -1.8 (-4.6 to +1.1); 16/21/1 | -0.7 (-3.2 to +1.7); 17/16/5 |
| Clinical synopsis HPO F1, hierarchical ↑ | -2.1 (-4.7 to +0.4); 15/21/2 | -3.4 (-6.1 to -0.7); 12/24/2 | -3.0 (-5.3 to -0.6); 10/26/2 | -1.1 (-2.9 to +0.8); 15/22/1 | -2.3 (-6.3 to +1.1); 13/20/5 | +0.2 (-1.8 to +2.2); 13/19/6 |
| OMIM allelic variants recovered ↑ | -0.6 (-1.5 to +0.0); 0/2/36 | -3.0 (-7.2 to -0.2); 0/4/34 | -0.3 (-1.0 to +0.0); 0/1/37 | +0.1 (-1.0 to +1.1); 1/1/36 | -3.6 (-8.4 to -0.2); 0/4/34 | -4.7 (-10.5 to -0.1); 1/4/33 |
| Causal gene F1 ↑ | +1.8 (+0.0 to +5.3); 1/0/37 | +1.8 (+0.0 to +5.3); 1/0/37 | +1.8 (+0.0 to +5.3); 1/0/37 | +1.8 (+0.0 to +5.3); 1/0/37 | +1.8 (+0.0 to +5.3); 1/0/37 | +1.8 (+0.0 to +5.3); 1/0/37 |
| Inheritance matches OMIM ↑ | -2.6 (-7.9 to +0.0); 0/1/37 | -2.6 (-7.9 to +0.0); 0/1/37 | -2.6 (-7.9 to +0.0); 0/1/37 | -2.6 (-7.9 to +0.0); 0/1/37 | +0.0 (+0.0 to +0.0); 0/0/38 | +0.0 (+0.0 to +0.0); 0/0/38 |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Evidence graph minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 59.4% | 58.4% | +1.0 | -0.9 to +2.9 | +0.1 | 19 / 15 / 4 | 0.608 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 97.1% | 97.9% | -0.8 | -1.4 to -0.1 | -0.7 | 8 / 25 / 5 | 0.005 | 0.037 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.3% | 0.1% | +0.2 | +0.0 to +0.4 | +0.0 | 2 / 6 / 30 | 0.289 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.5% | 0.4% | +0.1 | -0.3 to +0.5 | +0.0 | 5 / 3 / 30 | 0.727 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 37.6% | 40.1% | -2.5 | -5.1 to +0.2 | -2.4 | 10 / 24 / 4 | 0.024 | 0.170 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 57.1% | 59.2% | -2.1 | -4.7 to +0.4 | -1.2 | 15 / 21 / 2 | 0.405 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 76.8% | 77.3% | -0.6 | -1.5 to +0.0 | +0.0 | 0 / 2 / 36 | 0.500 | 1.000 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 94.7% | 97.4% | -2.6 | -7.9 to +0.0 | +0.0 | 0 / 1 / 37 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.2% | 0.1% | +0.1 | +0.0 to +0.3 | +0.0 | 3 / 4 / 31 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 2 / 36 | 0.500 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 53.2% | 51.8% | +1.4 | -0.7 to +3.5 | +0.4 | 19 / 13 / 6 | 0.377 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 61.5% | 61.5% | -0.0 | -1.8 to +1.7 | +0.0 | 18 / 17 / 3 | 1.000 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 40.5% | 45.2% | -4.6 | -8.3 to -1.2 | -3.2 | 9 / 24 / 5 | 0.013 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 44.5% | 43.8% | +0.8 | -4.0 to +4.9 | +0.0 | 15 / 8 / 15 | 0.210 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 66.6% | 68.7% | -2.1 | -3.8 to -0.4 | -2.1 | 13 / 23 / 2 | 0.133 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 81.4% | 87.8% | -6.4 | -11.5 to -2.2 | +0.0 | 0 / 8 / 28 | 0.008 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 97.9% | 96.9% | +1.0 | -0.3 to +2.7 | +0.0 | 3 / 1 / 34 | 0.625 | – |

#### Case table first minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 56.1% | 58.4% | -2.3 | -4.5 to +0.0 | -3.7 | 13 / 24 / 1 | 0.099 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 96.0% | 97.9% | -1.8 | -3.2 to -0.6 | -1.1 | 11 / 25 / 2 | 0.029 | 0.230 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.3% | 0.1% | +0.2 | +0.0 to +0.4 | +0.0 | 4 / 8 / 26 | 0.388 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.7% | 0.4% | +0.3 | -0.1 to +0.7 | +0.0 | 3 / 5 / 30 | 0.727 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 37.3% | 40.1% | -2.8 | -5.7 to +0.3 | -1.8 | 15 / 21 / 2 | 0.405 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 55.8% | 59.2% | -3.4 | -6.1 to -0.7 | -1.6 | 12 / 24 / 2 | 0.065 | 0.456 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 74.4% | 77.3% | -3.0 | -7.2 to -0.2 | +0.0 | 0 / 4 / 34 | 0.125 | 0.750 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 94.7% | 97.4% | -2.6 | -7.9 to +0.0 | +0.0 | 0 / 1 / 37 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.2% | 0.1% | +0.1 | -0.0 to +0.3 | +0.0 | 4 / 6 / 28 | 0.754 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 2 / 36 | 0.500 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 50.3% | 51.8% | -1.6 | -4.1 to +1.1 | -1.6 | 12 / 19 / 7 | 0.281 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 57.6% | 61.5% | -3.9 | -6.0 to -1.8 | -2.7 | 9 / 28 / 1 | 0.003 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 40.6% | 45.2% | -4.5 | -8.4 to -0.4 | -5.2 | 9 / 26 / 3 | 0.006 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 46.3% | 43.8% | +2.6 | -2.5 to +7.7 | +0.0 | 17 / 12 / 9 | 0.458 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 66.6% | 68.7% | -2.1 | -4.2 to +0.0 | -2.4 | 13 / 24 / 1 | 0.099 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 76.8% | 87.8% | -11.0 | -18.1 to -4.9 | +0.0 | 0 / 11 / 25 | 0.001 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 97.5% | 96.9% | +0.7 | -0.5 to +2.1 | +0.0 | 2 / 1 / 35 | 1.000 | – |

#### Evidence graph, matched minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 60.2% | 58.4% | +1.8 | +0.4 to +3.3 | +1.6 | 24 / 10 / 4 | 0.024 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 96.8% | 97.9% | -1.0 | -1.8 to -0.2 | -1.3 | 12 / 24 / 2 | 0.065 | 0.391 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.2% | 0.1% | +0.1 | -0.0 to +0.2 | +0.0 | 4 / 6 / 28 | 0.754 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.5% | 0.4% | +0.1 | -0.2 to +0.4 | +0.0 | 4 / 3 / 31 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 37.8% | 40.1% | -2.3 | -4.6 to -0.1 | -1.9 | 11 / 24 / 3 | 0.041 | 0.287 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 56.2% | 59.2% | -3.0 | -5.3 to -0.6 | -1.6 | 10 / 26 / 2 | 0.011 | 0.090 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 77.0% | 77.3% | -0.3 | -1.0 to +0.0 | +0.0 | 0 / 1 / 37 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 94.7% | 97.4% | -2.6 | -7.9 to +0.0 | +0.0 | 0 / 1 / 37 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 38 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.1% | 0.1% | +0.0 | -0.1 to +0.1 | +0.0 | 4 / 3 / 31 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.1% | 0.0% | +0.1 | +0.0 to +0.1 | +0.0 | 0 / 3 / 35 | 0.250 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 54.2% | 51.8% | +2.3 | +0.7 to +4.1 | +2.2 | 21 / 8 / 9 | 0.024 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 61.7% | 61.5% | +0.3 | -1.2 to +2.0 | +0.3 | 19 / 16 / 3 | 0.736 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 39.4% | 45.2% | -5.7 | -9.5 to -2.2 | -4.9 | 7 / 29 / 2 | <0.001 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 44.9% | 43.8% | +1.1 | -2.5 to +4.5 | +0.0 | 15 / 10 / 13 | 0.424 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 67.0% | 68.7% | -1.7 | -3.5 to +0.2 | -1.6 | 12 / 25 / 1 | 0.047 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 81.8% | 87.8% | -6.0 | -11.1 to -2.0 | +0.0 | 0 / 9 / 27 | 0.004 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 97.4% | 96.9% | +0.5 | -1.4 to +2.4 | +0.0 | 3 / 2 / 33 | 1.000 | – |

#### Evidence graph plus text minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 60.2% | 58.4% | +1.8 | +0.5 to +3.2 | +1.1 | 24 / 10 / 4 | 0.024 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 98.3% | 97.9% | +0.4 | -0.3 to +1.2 | +0.2 | 20 / 11 / 7 | 0.150 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.1% | 0.1% | +0.0 | -0.2 to +0.1 | +0.0 | 2 / 5 / 31 | 0.453 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.6% | 0.4% | +0.1 | -0.1 to +0.4 | +0.0 | 3 / 4 / 31 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 39.5% | 40.1% | -0.6 | -2.5 to +1.4 | -0.8 | 14 / 20 / 4 | 0.392 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 58.1% | 59.2% | -1.1 | -2.9 to +0.8 | -0.4 | 15 / 22 / 1 | 0.324 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 77.4% | 77.3% | +0.1 | -1.0 to +1.1 | +0.0 | 1 / 1 / 36 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 94.7% | 97.4% | -2.6 | -7.9 to +0.0 | +0.0 | 0 / 1 / 37 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.1% | 0.1% | -0.0 | -0.2 to +0.1 | +0.0 | 2 / 5 / 31 | 0.453 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 53.8% | 51.8% | +2.0 | +0.5 to +3.7 | +1.2 | 20 / 8 / 10 | 0.036 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 61.9% | 61.5% | +0.4 | -0.8 to +1.8 | +0.0 | 17 / 18 / 3 | 1.000 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 42.6% | 45.2% | -2.5 | -5.6 to +0.4 | -3.0 | 12 / 22 / 4 | 0.121 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 44.1% | 43.8% | +0.3 | -2.9 to +3.1 | +0.0 | 12 / 9 / 17 | 0.664 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 68.5% | 68.7% | -0.2 | -1.7 to +1.3 | -0.2 | 17 / 20 / 1 | 0.743 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 84.4% | 87.8% | -3.4 | -7.4 to -0.3 | +0.0 | 0 / 5 / 31 | 0.062 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 96.5% | 96.9% | -0.3 | -1.8 to +1.2 | +0.0 | 1 / 2 / 35 | 1.000 | – |

#### Case table, matched minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 58.2% | 58.4% | -0.2 | -2.4 to +2.2 | -0.8 | 16 / 20 / 2 | 0.618 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 97.0% | 97.9% | -0.9 | -2.1 to +0.2 | -0.7 | 14 / 22 / 2 | 0.243 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.4% | 0.1% | +0.3 | +0.0 to +0.7 | +0.0 | 3 / 10 / 25 | 0.092 | 0.646 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.5% | 0.4% | +0.1 | -0.1 to +0.4 | +0.0 | 3 / 4 / 31 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 38.3% | 40.1% | -1.8 | -4.6 to +1.1 | -1.4 | 16 / 21 / 1 | 0.511 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 56.9% | 59.2% | -2.3 | -6.3 to +1.1 | -0.7 | 13 / 20 / 5 | 0.296 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 73.7% | 77.3% | -3.6 | -8.4 to -0.2 | +0.0 | 0 / 4 / 34 | 0.125 | 0.750 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 97.4% | 97.4% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported or contradicted ↓ | 38 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.4% | 0.1% | +0.3 | +0.0 to +0.6 | +0.0 | 3 / 9 / 26 | 0.146 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 2 / 36 | 0.500 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 52.7% | 51.8% | +0.9 | -1.6 to +3.5 | +0.0 | 17 / 17 / 4 | 1.000 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 59.4% | 61.5% | -2.1 | -4.0 to -0.1 | -1.9 | 11 / 26 / 1 | 0.020 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 41.2% | 45.2% | -3.9 | -7.9 to +0.0 | -3.0 | 13 / 24 / 1 | 0.099 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 44.1% | 43.8% | +0.3 | -4.0 to +4.3 | +0.0 | 15 / 11 / 12 | 0.557 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 67.6% | 68.7% | -1.1 | -4.0 to +1.6 | -0.4 | 17 / 20 / 1 | 0.743 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 76.5% | 87.8% | -11.3 | -18.5 to -5.3 | +0.0 | 0 / 12 / 24 | <0.001 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 97.5% | 96.9% | +0.7 | -0.5 to +2.1 | +0.0 | 2 / 1 / 35 | 1.000 | – |

#### Case table plus text minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 38 | 59.1% | 58.4% | +0.6 | -1.2 to +2.6 | +0.0 | 18 / 15 / 5 | 0.728 | – |
| Claims supported by cited paper (headline) ↑ | 38 | 98.1% | 97.9% | +0.3 | -0.5 to +1.1 | +0.2 | 21 / 14 / 3 | 0.310 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 38 | 0.1% | 0.1% | -0.1 | -0.2 to +0.1 | +0.0 | 3 / 2 / 33 | 1.000 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 38 | 0.6% | 0.4% | +0.1 | -0.1 to +0.4 | +0.0 | 1 / 4 / 33 | 0.375 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 38 | 39.4% | 40.1% | -0.7 | -3.2 to +1.7 | +0.0 | 17 / 16 / 5 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 38 | 59.4% | 59.2% | +0.2 | -1.8 to +2.2 | -0.4 | 13 / 19 / 6 | 0.377 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 38 | 72.7% | 77.3% | -4.7 | -10.5 to -0.1 | +0.0 | 1 / 4 / 33 | 0.375 | 1.000 |
| Causal gene F1 (headline) ↑ | 38 | 98.2% | 96.5% | +1.8 | +0.0 to +5.3 | +0.0 | 1 / 0 / 37 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 38 | 97.4% | 97.4% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported or contradicted ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Claims unsupported, before the repair round ↓ | 38 | 0.1% | 0.1% | -0.0 | -0.2 to +0.1 | +0.0 | 3 / 2 / 33 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 38 | 52.8% | 51.8% | +1.0 | -1.1 to +3.3 | +1.1 | 20 / 14 / 4 | 0.392 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 38 | 61.0% | 61.5% | -0.5 | -2.1 to +1.0 | +0.5 | 20 / 18 / 0 | 0.871 | – |
| Clinical synopsis HPO precision, exact ↑ | 38 | 42.0% | 45.2% | -3.1 | -7.3 to +0.5 | -0.1 | 14 / 19 / 5 | 0.487 | – |
| Clinical synopsis HPO recall, exact ↑ | 38 | 44.4% | 43.8% | +0.6 | -2.1 to +3.3 | +0.0 | 11 / 9 / 18 | 0.824 | – |
| Clinical synopsis HPO F1, semantic ↑ | 38 | 68.5% | 68.7% | -0.3 | -2.3 to +1.8 | -0.3 | 17 / 20 / 1 | 0.743 | – |
| Generated variants that are OMIM variants (precision) ↑ | 36 | 85.0% | 87.8% | -2.8 | -5.9 to -0.4 | +0.0 | 1 / 5 / 30 | 0.219 | – |
| Causal gene recall ↑ | 38 | 98.7% | 96.0% | +2.6 | +0.0 to +7.9 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: none stated ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: a mode missing ↓ | 38 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 38 | – | – |
| Inheritance error: an extra mode ↓ | 38 | 0.0% | 2.6% | -2.6 | -7.9 to +0.0 | +0.0 | 1 / 0 / 37 | 1.000 | – |
| Inheritance error: a different mode ↓ | 38 | 2.6% | 0.0% | +2.6 | +0.0 to +7.9 | +0.0 | 0 / 1 / 37 | 1.000 | – |
| OMIM references used ↑ | 38 | 96.4% | 96.9% | -0.5 | -1.7 to +0.5 | +0.0 | 1 / 2 / 35 | 1.000 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 40 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: none.

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 97.9% | 96.1% | 96.9% | 98.3% | 97.0% | 98.2% |
| … same, before the repair round ↓ | 0.3% | 0.1% | 0.3% | 0.2% | 0.1% | 0.4% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 59.8% | 59.3% | 56.9% | 60.3% | 60.8% | 58.2% | 59.8% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.4% | 0.7% | 0.5% | 0.6% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 38.0% | 40.6% | 37.8% | 37.8% | 39.9% | 37.9% | 39.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.5% | 59.7% | 56.5% | 56.5% | 58.6% | 56.9% | 60.1% |
| OMIM allelic variants recovered ↑ | 76.9% | 77.5% | 74.7% | 77.2% | 77.5% | 74.0% | 73.0% |
| Causal gene F1 ↑ | 98.3% | 96.7% | 98.3% | 98.3% | 98.3% | 98.3% | 98.3% |
| Inheritance matches OMIM ↑ | 95.0% | 97.5% | 95.0% | 95.0% | 95.0% | 97.5% | 97.5% |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Evidence graph | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.8 (-1.4 to -0.1); median -0.7; 9/26/5; p 0.006 | -1.8 (-3.1 to -0.6); median -1.1; 11/27/2; p 0.014 | -1.0 (-1.8 to -0.1); median -1.3; 13/25/2; p 0.073 | +0.4 (-0.3 to +1.1); median +0.2; 21/12/7; p 0.163 | -0.9 (-2.0 to +0.2); median -0.7; 15/23/2; p 0.256 | +0.3 (-0.4 to +1.1); median +0.4; 23/14/3; p 0.188 |
| … same, before the repair round ↓ | +0.2 (+0.0 to +0.4); median +0.0; 2/6/32; p 0.289 | +0.2 (+0.0 to +0.4); median +0.0; 4/9/27; p 0.267 | +0.1 (-0.0 to +0.2); median +0.0; 4/6/30; p 0.754 | +0.0 (-0.2 to +0.1); median +0.0; 2/5/33; p 0.453 | +0.3 (+0.0 to +0.6); median +0.0; 3/10/27; p 0.092 | -0.0 (-0.2 to +0.1); median +0.0; 3/2/35; p 1.000 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.5 (-1.4 to +2.4); median +0.0; 19/17/4; p 0.868 | -2.5 (-4.5 to -0.3); median -3.7; 13/26/1; p 0.053 | +1.0 (-1.0 to +2.8); median +1.4; 24/12/4; p 0.065 | +1.5 (+0.3 to +2.9); median +0.9; 24/12/4; p 0.065 | -1.1 (-3.7 to +1.5); median -0.9; 16/22/2; p 0.418 | +0.5 (-1.2 to +2.4); median +0.0; 18/17/5; p 1.000 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.5); median +0.0; 5/4/31; p 1.000 | +0.2 (-0.1 to +0.7); median +0.0; 3/5/32; p 0.727 | +0.1 (-0.2 to +0.4); median +0.0; 4/3/33; p 1.000 | +0.2 (-0.1 to +0.5); median +0.0; 3/5/32; p 0.727 | +0.1 (-0.1 to +0.4); median +0.0; 3/5/32; p 0.727 | +0.1 (-0.1 to +0.4); median +0.0; 1/4/35; p 0.375 |
| Clinical synopsis HPO F1, exact ↑ | -2.7 (-5.2 to +0.0); median -2.4; 11/25/4; p 0.029 | -2.9 (-5.7 to +0.0); median -1.8; 15/23/2; p 0.256 | -2.8 (-5.1 to -0.6); median -2.3; 11/26/3; p 0.020 | -0.8 (-2.7 to +1.1); median -0.8; 15/21/4; p 0.405 | -2.8 (-5.8 to +0.2); median -2.9; 16/23/1; p 0.337 | -0.8 (-3.2 to +1.5); median +0.0; 18/17/5; p 1.000 |
| Clinical synopsis HPO F1, hierarchical ↑ | -2.2 (-4.7 to +0.3); median -1.2; 16/22/2; p 0.418 | -3.2 (-5.9 to -0.7); median -1.6; 13/25/2; p 0.073 | -3.2 (-5.4 to -0.9); median -1.7; 10/28/2; p 0.005 | -1.1 (-2.9 to +0.7); median -0.4; 16/23/1; p 0.337 | -2.8 (-6.7 to +0.5); median -1.0; 13/22/5; p 0.175 | +0.4 (-1.6 to +2.3); median +0.0; 15/19/6; p 0.608 |
| OMIM allelic variants recovered ↑ | -0.5 (-1.4 to +0.0); median +0.0; 0/2/38; p 0.500 | -2.8 (-6.9 to -0.2); median +0.0; 0/4/36; p 0.125 | -0.3 (-0.9 to +0.0); median +0.0; 0/1/39; p 1.000 | +0.1 (-0.9 to +1.1); median +0.0; 1/1/38; p 1.000 | -3.5 (-7.9 to -0.2); median +0.0; 0/4/36; p 0.125 | -4.4 (-9.9 to -0.1); median +0.0; 1/4/35; p 0.375 |
| Causal gene F1 ↑ | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 | +1.7 (+0.0 to +5.0); median +0.0; 1/0/39; p 1.000 |
| Inheritance matches OMIM ↑ | -2.5 (-7.5 to +0.0); median +0.0; 0/1/39; p 1.000 | -2.5 (-7.5 to +0.0); median +0.0; 0/1/39; p 1.000 | -2.5 (-7.5 to +0.0); median +0.0; 0/1/39; p 1.000 | -2.5 (-7.5 to +0.0); median +0.0; 0/1/39; p 1.000 | +0.0 (+0.0 to +0.0); median +0.0; 0/0/40; p – | +0.0 (+0.0 to +0.0); median +0.0; 0/0/40; p – |

## Pooled counts

| | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims audited | 5,381 | 4,738 | 5,581 | 5,970 | 5,608 | 5,998 | 5,130 |
| … supported | 5,220 | 4,632 | 5,389 | 5,809 | 5,528 | 5,844 | 5,038 |
| … partly supported | 161 | 106 | 192 | 157 | 80 | 153 | 92 |
| … unsupported | 0 | 0 | 0 | 4 | 0 | 1 | 0 |
| … contradicted | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Claims audited before repair | 5,363 | 4,738 | 5,575 | 5,942 | 5,599 | 5,993 | 5,132 |
| … unsupported before repair | 11 | 4 | 8 | 4 | 8 | 13 | 6 |
| … contradicted before repair | 6 | 0 | 2 | 4 | 0 | 2 | 0 |
| OMIM facts scored | 2,593 | 2,593 | 2,593 | 2,593 | 2,593 | 2,593 | 2,593 |
| … conveyed | 1,319 | 1,295 | 1,224 | 1,338 | 1,343 | 1,284 | 1,288 |
| … partly conveyed | 326 | 350 | 311 | 326 | 355 | 309 | 351 |
| … missing | 938 | 937 | 1,044 | 917 | 882 | 987 | 940 |
| … contradicted | 10 | 11 | 14 | 12 | 13 | 13 | 14 |

## Allelic variants: precision and variants not in OMIM

| | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Variants generated | 176 | 141 | 177 | 175 | 153 | 179 | 142 |
| … matching an OMIM variant of the entry | 115 | 117 | 112 | 116 | 117 | 112 | 112 |
| … listed by OMIM only from a paper outside the entry's references | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| … not in OMIM | 61 | 24 | 65 | 59 | 36 | 67 | 30 |
| Pooled precision (entries where OMIM lists variants) | 65.3% | 83.0% | 63.3% | 66.3% | 76.5% | 62.6% | 78.9% |

## Inheritance errors by kind

| | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Entries with an OMIM mode of inheritance | 38 | 38 | 38 | 38 | 38 | 38 | 38 |
| … matched | 36 | 37 | 36 | 36 | 36 | 37 | 37 |
| … none stated | 1 | 0 | 1 | 1 | 1 | 0 | 0 |
| … a mode missing | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| … an extra mode | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| … a different mode | 1 | 0 | 1 | 1 | 1 | 1 | 1 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| fulltext | 79.9% (1,186) | 76.9% (1,186) | 72.5% (1,186) | 80.9% (1,186) | 80.7% (1,186) | 76.0% (1,186) | 76.2% (1,186) |
| abstract | 40.2% (1,250) | 42.1% (1,250) | 39.2% (1,250) | 40.9% (1,250) | 42.5% (1,250) | 40.4% (1,250) | 42.3% (1,250) |
| title | 20.1% (157) | 20.4% (157) | 18.8% (157) | 19.8% (157) | 20.4% (157) | 20.1% (157) | 20.1% (157) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies.

| Paper readable as | Evidence graph | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|
| fulltext | +3.0 (-0.1 to +5.7); n=25 | -4.4 (-7.9 to -1.2); n=25 | +4.0 (+1.5 to +6.4); n=25 | +3.8 (+0.8 to +6.3); n=25 | -0.9 (-4.9 to +2.5); n=25 | -0.7 (-3.2 to +1.8); n=25 |
| abstract | -1.9 (-5.1 to +0.9); n=31 | -2.9 (-6.5 to +0.2); n=31 | -1.2 (-4.0 to +1.0); n=31 | +0.4 (-0.5 to +1.3); n=31 | -1.6 (-5.1 to +1.3); n=31 | +0.2 (-1.9 to +1.9); n=31 |
| title | -0.3 (-6.7 to +4.3) †; n=7 | -1.6 (-5.1 to +0.4) †; n=7 | -0.6 (-4.3 to +1.8) †; n=7 | +0.0 (-1.6 to +1.5) †; n=7 | -0.3 (-4.5 to +1.9) †; n=7 | -0.3 (-3.5 to +2.1) †; n=7 |

† fewer than 20 entries: the interval is unreliable.

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Evidence graph | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| no full text (abstracts only) | 11 | +2.4 (+0.5 to +4.5) †; n=11 | +1.9 (-0.5 to +4.4) †; n=11 | +1.9 (+0.4 to +3.8) †; n=11 | +0.7 (-1.2 to +3.0) †; n=11 | +2.8 (+0.9 to +4.9) †; n=11 | +2.1 (+0.1 to +4.3) †; n=11 |
| under half full text | 7 | +2.2 (-0.9 to +5.7) †; n=7 | -2.0 (-4.5 to +0.8) †; n=7 | +2.5 (+0.4 to +5.2) †; n=7 | +1.8 (-0.0 to +4.3) †; n=7 | +0.2 (-2.8 to +3.1) †; n=7 | -0.5 (-3.1 to +1.6) †; n=7 |
| half or more full text | 19 | -1.2 (-3.8 to +1.4) †; n=19 | -6.2 (-8.6 to -3.5) †; n=19 | +0.4 (-1.3 to +1.8) †; n=19 | +1.5 (+0.2 to +2.6) †; n=19 | -3.3 (-6.3 to -0.5) †; n=19 | -1.0 (-3.2 to +0.9) †; n=19 |
| all full text | 1 | +17.8 †; n=1 | +21.4 †; n=1 | +21.4 †; n=1 | +19.6 †; n=1 | +25.0 †; n=1 | +25.0 †; n=1 |

### OMIM allelic variants recovered

| Access group | Entries | Evidence graph | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| no full text (abstracts only) | 11 | +0.0 (+0.0 to +0.0) †; n=11 | +0.0 (+0.0 to +0.0) †; n=11 | +0.0 (+0.0 to +0.0) †; n=11 | +0.0 (+0.0 to +0.0) †; n=11 | -4.5 (-13.6 to +0.0) †; n=11 | +0.0 (+0.0 to +0.0) †; n=11 |
| under half full text | 7 | +0.0 (+0.0 to +0.0) †; n=7 | -9.5 (-28.6 to +0.0) †; n=7 | +0.0 (+0.0 to +0.0) †; n=7 | +2.0 (+0.0 to +6.1) †; n=7 | -9.5 (-28.6 to +0.0) †; n=7 | -17.0 (-38.1 to +4.1) †; n=7 |
| half or more full text | 19 | -1.1 (-2.8 to +0.0) †; n=19 | -2.5 (-5.7 to +0.0) †; n=19 | -0.7 (-2.0 to +0.0) †; n=19 | -0.7 (-2.0 to +0.0) †; n=19 | -1.1 (-2.9 to +0.0) †; n=19 | -3.1 (-7.9 to +0.0) †; n=19 |
| all full text | 1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 88.6% (22 facts, 1 entry) | 79.2% (113 facts, 5 entries) | 70.9% (380 facts, 7 entries) | 70.9% (311 facts, 5 entries) | 86.9% (360 facts, 7 entries) |
| abstract | 29.7% (397 facts, 8 entries) | 49.8% (245 facts, 8 entries) | 53.2% (174 facts, 5 entries) | 36.2% (167 facts, 3 entries) | 49.8% (267 facts, 7 entries) |
| title | 20.0% (25 facts, 1 entry) | 13.8% (29 facts, 1 entry) | 61.1% (9 facts, 1 entry) | 23.9% (46 facts, 3 entries) | 13.5% (48 facts, 1 entry) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 11 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.6% | 97.9% | 96.1% | 96.5% | 97.8% | 96.2% | 97.7% |
| … same, before the repair round ↓ | 0.4% | 0.2% | 0.5% | 0.5% | 0.1% | 0.9% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 40.0% | 37.6% | 39.6% | 39.5% | 38.3% | 40.4% | 39.7% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 32.7% | 36.1% | 34.4% | 35.9% | 34.8% | 34.9% | 33.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.1% | 55.2% | 55.1% | 55.2% | 53.4% | 56.2% | 55.7% |
| OMIM allelic variants recovered ↑ | 51.1% | 51.1% | 51.1% | 51.1% | 51.1% | 46.6% | 51.1% |
| Causal gene F1 ↑ | 94.0% | 87.9% | 94.0% | 94.0% | 94.0% | 94.0% | 94.0% |
| Inheritance matches OMIM ↑ | 81.8% | 90.9% | 81.8% | 81.8% | 81.8% | 90.9% | 90.9% |

### under half full text — 7 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.5% | 97.5% | 96.9% | 96.9% | 98.0% | 97.3% | 97.9% |
| … same, before the repair round ↓ | 0.1% | 0.1% | 0.4% | 0.0% | 0.1% | 0.7% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 57.4% | 55.2% | 53.3% | 57.7% | 57.0% | 55.4% | 54.7% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 1.2% | 1.4% | 0.9% | 0.9% | 1.2% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | 38.9% | 40.4% | 38.1% | 39.2% | 42.1% | 40.4% | 42.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.2% | 56.6% | 55.2% | 55.9% | 57.5% | 57.0% | 59.0% |
| OMIM allelic variants recovered ↑ | 81.3% | 81.3% | 71.8% | 81.3% | 83.3% | 71.8% | 64.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### half or more full text — 19 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 97.9% | 95.8% | 96.9% | 98.6% | 97.2% | 98.4% |
| … same, before the repair round ↓ | 0.4% | 0.1% | 0.1% | 0.1% | 0.1% | 0.1% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 70.2% | 71.4% | 65.2% | 71.7% | 72.8% | 68.0% | 70.3% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% | 0.5% | 0.5% | 0.5% | 0.4% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 39.4% | 41.1% | 37.8% | 38.1% | 40.3% | 38.5% | 40.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 60.1% | 61.3% | 55.6% | 56.7% | 60.3% | 56.5% | 60.7% |
| OMIM allelic variants recovered ↑ | 88.7% | 89.9% | 87.4% | 89.2% | 89.2% | 88.7% | 86.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### all full text — 1 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 99.3% | 99.3% | 94.3% | 97.9% | 99.6% | 97.8% | 99.5% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 82.1% | 64.3% | 85.7% | 85.7% | 83.9% | 89.3% | 89.3% |
| OMIM per-paper facts contradicted ↓ | 7.1% | 0.0% | 7.1% | 3.6% | 3.6% | 3.6% | 3.6% |
| Clinical synopsis HPO F1, exact ↑ | 49.5% | 63.8% | 56.2% | 44.6% | 58.5% | 56.8% | 66.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 67.7% | 82.8% | 73.0% | 61.4% | 72.4% | 71.5% | 79.3% |
| OMIM allelic variants recovered ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 23 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 97.9% | 95.3% | 96.7% | 98.3% | 96.7% | 98.2% |
| … same, before the repair round ↓ | 0.3% | 0.0% | 0.2% | 0.1% | 0.0% | 0.4% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 64.9% | 63.7% | 61.9% | 66.0% | 66.2% | 64.2% | 65.4% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.3% | 0.7% | 0.5% | 0.7% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 39.4% | 42.6% | 39.9% | 39.8% | 42.0% | 38.8% | 40.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.1% | 60.8% | 57.9% | 57.9% | 60.0% | 57.9% | 61.2% |
| OMIM allelic variants recovered ↑ | 77.6% | 77.6% | 76.5% | 77.6% | 77.6% | 77.6% | 75.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.7% | 100.0% | 95.7% | 95.7% | 95.7% | 100.0% | 100.0% |

### 5-8 references — 8 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 98.1% | 97.4% | 96.7% | 97.8% | 97.3% | 97.7% |
| … same, before the repair round ↓ | 0.4% | 0.4% | 0.5% | 0.4% | 0.3% | 0.4% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 56.7% | 56.5% | 51.2% | 57.2% | 57.4% | 52.9% | 55.4% |
| OMIM per-paper facts contradicted ↓ | 0.1% | 0.5% | 0.7% | 0.4% | 0.1% | 0.7% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 29.0% | 29.6% | 27.1% | 28.4% | 29.6% | 31.2% | 30.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.0% | 53.1% | 48.1% | 48.9% | 51.9% | 51.8% | 52.0% |
| OMIM allelic variants recovered ↑ | 75.4% | 78.1% | 67.1% | 76.6% | 78.4% | 67.1% | 71.6% |
| Causal gene F1 ↑ | 95.8% | 87.5% | 95.8% | 95.8% | 95.8% | 95.8% | 95.8% |
| Inheritance matches OMIM ↑ | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% |

### 9 or more references — 7 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.7% | 97.2% | 96.9% | 97.5% | 98.8% | 97.5% | 98.3% |
| … same, before the repair round ↓ | 0.3% | 0.1% | 0.2% | 0.3% | 0.1% | 0.3% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 44.5% | 43.4% | 42.9% | 44.5% | 43.7% | 45.0% | 42.5% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.7% | 0.7% | 0.7% | 0.7% | 0.4% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 41.8% | 43.8% | 40.6% | 42.0% | 42.7% | 45.0% | 45.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.6% | 61.0% | 57.9% | 59.1% | 59.0% | 59.7% | 61.8% |
| OMIM allelic variants recovered ↑ | 75.6% | 75.6% | 75.6% | 75.6% | 75.6% | 68.5% | 66.1% |
| Causal gene F1 ↑ | 95.2% | 95.2% | 95.2% | 95.2% | 95.2% | 95.2% | 95.2% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## By creation era (MIM number range)

### 600000-609999 — 8 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.3% | 98.1% | 93.6% | 96.4% | 97.7% | 96.0% | 97.8% |
| … same, before the repair round ↓ | 0.1% | 0.1% | 0.4% | 0.1% | 0.0% | 1.3% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 60.7% | 57.8% | 58.1% | 60.1% | 59.4% | 59.5% | 59.6% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.5% | 0.7% | 0.2% | 0.2% | 0.7% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 44.4% | 43.3% | 43.2% | 42.6% | 42.9% | 39.2% | 41.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 64.1% | 65.3% | 64.1% | 64.2% | 64.5% | 57.2% | 63.4% |
| OMIM allelic variants recovered ↑ | 83.3% | 83.3% | 75.0% | 83.3% | 83.3% | 68.8% | 66.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 87.5% | 100.0% | 87.5% | 87.5% | 87.5% | 100.0% | 100.0% |

### 610000-615999 — 7 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 97.9% | 95.8% | 96.0% | 99.0% | 97.5% | 98.2% |
| … same, before the repair round ↓ | 0.0% | 0.1% | 0.1% | 0.2% | 0.2% | 0.1% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 72.3% | 70.4% | 68.7% | 75.1% | 75.5% | 71.6% | 74.5% |
| OMIM per-paper facts contradicted ↓ | 1.6% | 0.9% | 1.6% | 1.1% | 1.3% | 1.1% | 1.4% |
| Clinical synopsis HPO F1, exact ↑ | 34.3% | 43.8% | 35.0% | 35.3% | 37.3% | 35.1% | 42.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.6% | 64.4% | 52.9% | 54.6% | 58.4% | 56.1% | 61.9% |
| OMIM allelic variants recovered ↑ | 88.0% | 89.3% | 84.4% | 89.3% | 91.3% | 88.0% | 91.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### 616000-619999 — 7 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 98.1% | 97.7% | 97.6% | 97.6% | 98.8% | 98.5% | 98.9% |
| … same, before the repair round ↓ | 0.6% | 0.0% | 0.3% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 60.9% | 59.2% | 57.0% | 60.4% | 61.0% | 58.4% | 56.7% |
| OMIM per-paper facts contradicted ↓ | 0.2% | 0.2% | 0.3% | 0.3% | 0.4% | 0.6% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 41.4% | 42.8% | 41.8% | 42.0% | 43.3% | 43.0% | 42.4% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.6% | 57.0% | 52.9% | 55.6% | 56.3% | 55.0% | 56.7% |
| OMIM allelic variants recovered ↑ | 78.2% | 78.2% | 78.2% | 78.2% | 78.2% | 78.2% | 73.4% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### 620000 onward — 8 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.1% | 98.2% | 96.9% | 97.3% | 98.3% | 96.2% | 98.3% |
| … same, before the repair round ↓ | 0.2% | 0.1% | 0.1% | 0.1% | 0.2% | 0.1% | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 68.1% | 71.0% | 62.9% | 70.5% | 71.4% | 66.0% | 70.2% |
| OMIM per-paper facts contradicted ↓ | 0.2% | 0.2% | 0.6% | 0.5% | 0.5% | 0.2% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 40.5% | 39.5% | 38.3% | 36.0% | 41.8% | 42.2% | 40.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 58.4% | 56.4% | 56.5% | 52.9% | 58.5% | 59.0% | 57.4% |
| OMIM allelic variants recovered ↑ | 87.5% | 89.1% | 87.5% | 87.5% | 87.5% | 87.5% | 85.9% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### classic (1xxxxx-5xxxxx) — 8 entries

| Metric | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.3% | 97.4% | 96.6% | 96.8% | 97.9% | 96.9% | 97.7% |
| … same, before the repair round ↓ | 0.4% | 0.3% | 0.6% | 0.6% | 0.1% | 0.5% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 36.8% | 35.3% | 35.5% | 36.8% | 35.7% | 37.5% | 36.0% |
| OMIM per-paper facts contradicted ↓ | 0.2% | 0.4% | 0.4% | 0.4% | 0.4% | 0.2% | 0.2% |
| Clinical synopsis HPO F1, exact ↑ | 27.6% | 31.9% | 28.6% | 33.4% | 32.4% | 32.2% | 30.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.7% | 53.3% | 52.0% | 53.5% | 52.6% | 57.0% | 57.5% |
| OMIM allelic variants recovered ↑ | 48.4% | 48.4% | 48.4% | 48.4% | 48.4% | 48.4% | 48.4% |
| Causal gene F1 ↑ | 91.7% | 83.3% | 91.7% | 91.7% | 91.7% | 91.7% | 91.7% |
| Inheritance matches OMIM ↑ | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Case table first | Evidence graph, matched | Evidence graph plus text | Case table, matched | Case table plus text |
|---|---|---|---|---|---|---|---|
| Generation: model calls | 6.9 | 1.9 | 6.9 | 7.2 | 7.2 | 7.1 | 7.2 |
| Generation: list price | $0.65 | $0.32 | $0.72 | $0.72 | $0.88 | $0.84 | $0.97 |
| Generation: input / output tokens | 58,301 / 17,845 | 25,777 / 7,142 | 67,537 / 20,153 | 59,231 / 22,158 | 78,188 / 22,381 | 70,065 / 25,457 | 89,695 / 24,549 |
| Generation: model time (s) | 140 | 58 | 162 | 193 | 197 | 203 | 198 |
| Audit and repair: list price | $0.95 | $0.86 | $0.94 | $0.99 | $0.94 | $1.00 | $0.91 |
| Scoring against OMIM: list price | $0.41 | $0.41 | $0.41 | $0.43 | $0.43 | $0.43 | $0.41 |
| Everything: list price | $2.00 | $1.59 | $2.07 | $2.14 | $2.25 | $2.26 | $2.29 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Direct reading | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → causal gene | Case table first | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Evidence graph, matched | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Evidence graph plus text | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Case table, matched | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → causal gene | Case table plus text | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → mode of inheritance | Evidence graph | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Direct reading | 41 | 42 | 41 | 97.6% | 100.0% | 98.8% |
| Disease → mode of inheritance | Case table first | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Evidence graph, matched | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Evidence graph plus text | 39 | 40 | 41 | 97.5% | 95.1% | 96.3% |
| Disease → mode of inheritance | Case table, matched | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → mode of inheritance | Case table plus text | 40 | 41 | 41 | 97.6% | 97.6% | 97.6% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 384 | 1,031 | 943 | 37.2% | 40.7% | 38.9% |
| Disease → phenotype (HPO, exact id) | Direct reading | 354 | 783 | 950 | 45.2% | 37.3% | 40.8% |
| Disease → phenotype (HPO, exact id) | Case table first | 408 | 1,201 | 937 | 34.0% | 43.5% | 38.2% |
| Disease → phenotype (HPO, exact id) | Evidence graph, matched | 359 | 966 | 946 | 37.2% | 38.0% | 37.5% |
| Disease → phenotype (HPO, exact id) | Evidence graph plus text | 373 | 869 | 946 | 42.9% | 39.4% | 41.1% |
| Disease → phenotype (HPO, exact id) | Case table, matched | 359 | 901 | 941 | 39.8% | 38.1% | 39.0% |
| Disease → phenotype (HPO, exact id) | Case table plus text | 369 | 833 | 945 | 44.3% | 39.1% | 41.5% |
| Disease → allelic variant | Evidence graph | 121 | 182 | 171 | 66.5% | 70.8% | 68.6% |
| Disease → allelic variant | Direct reading | 123 | 147 | 171 | 83.7% | 71.9% | 77.4% |
| Disease → allelic variant | Case table first | 118 | 183 | 171 | 64.5% | 69.0% | 66.7% |
| Disease → allelic variant | Evidence graph, matched | 122 | 181 | 171 | 67.4% | 71.4% | 69.3% |
| Disease → allelic variant | Evidence graph plus text | 123 | 159 | 171 | 77.4% | 71.9% | 74.6% |
| Disease → allelic variant | Case table, matched | 118 | 185 | 171 | 63.8% | 69.0% | 66.3% |
| Disease → allelic variant | Case table plus text | 118 | 148 | 171 | 79.7% | 69.0% | 74.0% |
