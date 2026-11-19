# Generation strategies compared — run `large12`

10 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

No draft: 2 entries for which at least one strategy wrote nothing, because the model's safety filter stopped the writer's reply or the reply came back empty (Direct reading 1; Evidence graph 1). Entries: 180300, 607060. They are left out of the comparison with the incomplete entries listed under Completion.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 10 of the run's 12 entries qualify; left out: 180300, 607060. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 11 | 0 | 1: 607060 |
| Direct reading | 11 | 0 | 1: 180300 |
| Agentic curator | 12 | 0 | 0 |
| Case table first | 10 | 2: 180300 (9 papers), 607060 (2 papers) | 0 |
| Reconciled case database | 10 | 2: 180300 (9 papers), 607060 (2 papers) | 0 |

## How the scores are counted

- **OMIM facts conveyed** is scored against one fixed list of facts per OMIM paragraph, split without sight of any draft and shared by every strategy. The earlier scoring, which split the paragraph afresh for each draft, is shown as a secondary row.

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: none.

- **n.** A value rests on all 10 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Evidence graph** (`kg`): Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph.
- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Agentic curator** (`agent`): An autonomous agent reads and searches the papers with tools, then writes the entry.
- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.
- **Reconciled case database** (`reconciled`): The case table after merging the same patient, family or variant across papers and settling conflicts.

## Scores

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.5% | 97.9% | 98.1% | 96.7% | 96.3% |
| Claims unsupported or contradicted ↓ | 0.1% | 0.0% | 0.1% | 0.0% | 0.0% |
| … same, before the repair round ↓ | 0.2% | 0.1% | 0.2% | 0.4% | 0.5% |
| … unsupported, before the repair round ↓ | 0.2% | 0.1% | 0.2% | 0.4% | 0.5% |
| … contradicted, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 46.3% | 45.5% | 44.9% | 46.0% | 47.8% |
| … fully (no partial credit) ↑ | 39.5% | 38.6% | 37.9% | 39.2% | 41.2% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.2% | 0.1% | 0.2% |
| … conveyed anywhere in the draft, not only where the paper is cited ↑ | – | – | – | – | – |
| … facts split afresh for each draft (earlier scoring) ↑ | 47.4% | 47.4% | 47.4% | 48.6% | 49.7% |
| Clinical synopsis HPO F1, exact ↑ | 26.7% | 30.3% | 29.6% | 28.1% | 28.1% |
| … precision ↑ | 21.2% | 33.7% | 33.9% | 26.5% | 26.5% |
| … recall ↑ | 48.9% | 35.9% | 34.5% | 46.7% | 46.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.9% | 52.5% | 50.6% | 48.4% | 48.4% |
| Clinical synopsis HPO F1, semantic ↑ | 63.5% | 63.4% | 61.9% | 62.4% | 62.4% |
| OMIM allelic variants recovered ↑ | 55.8% | 54.5% | 56.2% | 58.1% | 56.1% |
| Generated variants that are OMIM variants (precision) ↑ | 52.1% | 64.9% | 66.2% | 39.0% | 46.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| … recall ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |
| Inheritance error: none stated ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Inheritance error: a mode missing ↓ | 0.0% | 0.0% | 0.0% | 10.0% | 10.0% |
| Inheritance error: an extra mode ↓ | 0.0% | 0.0% | 0.0% | 10.0% | 10.0% |
| Inheritance error: a different mode ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM references used ↑ | 96.6% | 97.2% | 89.6% | 94.8% | 94.5% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims audited per entry | 406.4 | 303.0 | 285.4 | 407.7 | 395.4 |
| Claims that could not be audited per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Clinical-synopsis HPO terms per entry | 42.8 | 20.3 | 18.5 | 40.8 | 40.8 |
| Allelic variants per entry | 10.3 | 6.3 | 6.6 | 14.5 | 12.8 |
| … of which not in OMIM | 5.5 | 2.1 | 2.2 | 9.7 | 8.1 |
| Papers cited per entry | 40.2 | 40.7 | 36.8 | 39.6 | 39.5 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.4 (-1.1 to +0.2); 2/7/1 | +0.2 (-0.5 to +0.9); 5/5/0 | -1.2 (-2.2 to -0.1); 1/9/0 | -1.6 (-2.5 to -0.6); 2/8/0 |
| … same, before the repair round ↓ | +0.0 (-0.1 to +0.2); 2/5/3 | +0.0 (-0.2 to +0.2); 2/3/5 | +0.2 (-0.1 to +0.8); 2/6/2 | +0.4 (-0.1 to +1.1); 2/6/2 |
| OMIM per-paper facts conveyed (primary) ↑ | +0.7 (-2.7 to +3.4); 6/3/1 | -0.6 (-2.1 to +0.7); 2/6/2 | +0.4 (-1.4 to +2.3); 5/4/1 | +2.3 (+0.4 to +4.2); 7/3/0 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.4); 1/2/7 | -0.1 (-0.7 to +0.3); 2/2/6 | -0.2 (-0.7 to +0.2); 2/1/7 | -0.1 (-0.7 to +0.4); 2/2/6 |
| Clinical synopsis HPO F1, exact ↑ | -3.6 (-7.3 to +0.4); 2/7/1 | -0.7 (-2.9 to +1.0); 3/4/3 | -2.1 (-6.0 to +2.1); 4/6/0 | -2.1 (-6.0 to +2.0); 4/6/0 |
| Clinical synopsis HPO F1, hierarchical ↑ | -3.6 (-6.9 to -0.2); 2/8/0 | -1.9 (-6.3 to +1.0); 4/5/1 | -4.1 (-7.7 to -0.3); 3/7/0 | -4.1 (-7.7 to -0.3); 3/7/0 |
| OMIM allelic variants recovered ↑ | +1.4 (-11.7 to +10.8); 4/1/5 | +1.7 (-1.4 to +5.7); 2/1/7 | +3.6 (-0.7 to +8.5); 3/1/6 | +1.6 (-4.9 to +7.8); 3/2/5 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 |
| Inheritance matches OMIM ↑ | +0.0 (+0.0 to +0.0); 0/0/10 | +0.0 (+0.0 to +0.0); 0/0/10 | -20.0 (-50.0 to +0.0); 0/2/8 | -20.0 (-50.0 to +0.0); 0/2/8 |

**Fewer than 20 entries: the bootstrap interval is unreliable** (a percentile bootstrap over so few entries is too narrow); read the sign test and the counts instead.

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Evidence graph minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 10 | 46.3% | 45.5% | +0.7 | -2.7 to +3.4 | +1.2 | 6 / 3 / 1 | 0.508 | – |
| Claims supported by cited paper (headline) ↑ | 10 | 97.5% | 97.9% | -0.4 | -1.1 to +0.2 | -0.1 | 2 / 7 / 1 | 0.180 | 0.898 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 10 | 0.2% | 0.1% | +0.0 | -0.1 to +0.2 | +0.1 | 2 / 5 / 3 | 0.453 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 10 | 0.4% | 0.3% | +0.1 | -0.2 to +0.4 | +0.0 | 1 / 2 / 7 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 10 | 26.7% | 30.3% | -3.6 | -7.3 to +0.4 | -4.8 | 2 / 7 / 1 | 0.180 | 0.898 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 10 | 48.9% | 52.5% | -3.6 | -6.9 to -0.2 | -3.4 | 2 / 8 / 0 | 0.109 | 0.656 |
| OMIM allelic variants recovered (headline) ↑ | 10 | 55.8% | 54.5% | +1.4 | -11.7 to +10.8 | +0.0 | 4 / 1 / 5 | 0.375 | 1.000 |
| Causal gene F1 (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance matches OMIM (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Claims unsupported or contradicted ↓ | 10 | 0.1% | 0.0% | +0.1 | +0.0 to +0.1 | +0.0 | 0 / 2 / 8 | 0.500 | – |
| Claims unsupported, before the repair round ↓ | 10 | 0.2% | 0.1% | +0.0 | -0.1 to +0.2 | +0.1 | 2 / 5 / 3 | 0.453 | – |
| Claims contradicted, before the repair round ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 10 | 39.5% | 38.6% | +0.9 | -2.7 to +3.7 | +1.3 | 5 / 2 / 3 | 0.453 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 10 | 47.4% | 47.4% | -0.0 | -4.5 to +3.9 | +1.2 | 6 / 4 / 0 | 0.754 | – |
| Clinical synopsis HPO precision, exact ↑ | 10 | 21.2% | 33.7% | -12.5 | -20.4 to -5.3 | -8.9 | 2 / 8 / 0 | 0.109 | – |
| Clinical synopsis HPO recall, exact ↑ | 10 | 48.9% | 35.9% | +12.9 | +6.2 to +20.9 | +12.0 | 7 / 0 / 3 | 0.016 | – |
| Clinical synopsis HPO F1, semantic ↑ | 10 | 63.5% | 63.4% | +0.1 | -2.5 to +2.9 | +0.9 | 6 / 4 / 0 | 0.754 | – |
| Generated variants that are OMIM variants (precision) ↑ | 10 | 52.1% | 64.9% | -12.8 | -22.5 to -4.2 | -3.9 | 0 / 5 / 5 | 0.062 | – |
| Causal gene recall ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: none stated ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a mode missing ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: an extra mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a different mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM references used ↑ | 10 | 96.6% | 97.2% | -0.7 | -2.3 to +0.5 | +0.0 | 1 / 2 / 7 | 1.000 | – |

#### Agentic curator minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 10 | 44.9% | 45.5% | -0.6 | -2.1 to +0.7 | -0.4 | 2 / 6 / 2 | 0.289 | – |
| Claims supported by cited paper (headline) ↑ | 10 | 98.1% | 97.9% | +0.2 | -0.5 to +0.9 | +0.1 | 5 / 5 / 0 | 1.000 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 10 | 0.2% | 0.1% | +0.0 | -0.2 to +0.2 | +0.0 | 2 / 3 / 5 | 1.000 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 10 | 0.2% | 0.3% | -0.1 | -0.7 to +0.3 | +0.0 | 2 / 2 / 6 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 10 | 29.6% | 30.3% | -0.7 | -2.9 to +1.0 | +0.0 | 3 / 4 / 3 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 10 | 50.6% | 52.5% | -1.9 | -6.3 to +1.0 | -0.4 | 4 / 5 / 1 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 10 | 56.2% | 54.5% | +1.7 | -1.4 to +5.7 | +0.0 | 2 / 1 / 7 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance matches OMIM (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Claims unsupported or contradicted ↓ | 10 | 0.1% | 0.0% | +0.1 | +0.0 to +0.1 | +0.0 | 0 / 1 / 9 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 10 | 0.2% | 0.1% | +0.0 | -0.2 to +0.2 | +0.0 | 2 / 3 / 5 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 10 | 37.9% | 38.6% | -0.8 | -2.4 to +0.8 | -0.7 | 3 / 5 / 2 | 0.727 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 10 | 47.4% | 47.4% | +0.0 | -2.1 to +1.9 | +0.4 | 5 / 5 / 0 | 1.000 | – |
| Clinical synopsis HPO precision, exact ↑ | 10 | 33.9% | 33.7% | +0.2 | -1.1 to +1.6 | +0.0 | 4 / 3 / 3 | 1.000 | – |
| Clinical synopsis HPO recall, exact ↑ | 10 | 34.5% | 35.9% | -1.5 | -3.6 to +0.0 | +0.0 | 0 / 2 / 8 | 0.500 | – |
| Clinical synopsis HPO F1, semantic ↑ | 10 | 61.9% | 63.4% | -1.5 | -4.0 to +0.7 | -0.8 | 3 / 7 / 0 | 0.344 | – |
| Generated variants that are OMIM variants (precision) ↑ | 10 | 66.2% | 64.9% | +1.3 | -2.5 to +5.7 | +0.0 | 2 / 2 / 6 | 1.000 | – |
| Causal gene recall ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: none stated ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a mode missing ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: an extra mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a different mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM references used ↑ | 10 | 89.6% | 97.2% | -7.6 | -14.3 to -1.7 | +0.0 | 0 / 4 / 6 | 0.125 | – |

#### Case table first minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 10 | 46.0% | 45.5% | +0.4 | -1.4 to +2.3 | +0.4 | 5 / 4 / 1 | 1.000 | – |
| Claims supported by cited paper (headline) ↑ | 10 | 96.7% | 97.9% | -1.2 | -2.2 to -0.1 | -1.4 | 1 / 9 / 0 | 0.021 | 0.150 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 10 | 0.4% | 0.1% | +0.2 | -0.1 to +0.8 | +0.2 | 2 / 6 / 2 | 0.289 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 10 | 0.1% | 0.3% | -0.2 | -0.7 to +0.2 | +0.0 | 2 / 1 / 7 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 10 | 28.1% | 30.3% | -2.1 | -6.0 to +2.1 | -3.1 | 4 / 6 / 0 | 0.754 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 10 | 48.4% | 52.5% | -4.1 | -7.7 to -0.3 | -5.2 | 3 / 7 / 0 | 0.344 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 10 | 58.1% | 54.5% | +3.6 | -0.7 to +8.5 | +0.0 | 3 / 1 / 6 | 0.625 | 1.000 |
| Causal gene F1 (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance matches OMIM (headline) ↑ | 10 | 80.0% | 100.0% | -20.0 | -50.0 to +0.0 | +0.0 | 0 / 2 / 8 | 0.500 | 1.000 |
| Claims unsupported or contradicted ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Claims unsupported, before the repair round ↓ | 10 | 0.4% | 0.1% | +0.2 | -0.1 to +0.7 | +0.2 | 2 / 6 / 2 | 0.289 | – |
| Claims contradicted, before the repair round ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 10 | 39.2% | 38.6% | +0.5 | -2.1 to +3.5 | -0.3 | 5 / 5 / 0 | 1.000 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 10 | 48.6% | 47.4% | +1.3 | -1.1 to +3.0 | +1.9 | 8 / 2 / 0 | 0.109 | – |
| Clinical synopsis HPO precision, exact ↑ | 10 | 26.5% | 33.7% | -7.2 | -12.1 to -2.3 | -8.1 | 3 / 7 / 0 | 0.344 | – |
| Clinical synopsis HPO recall, exact ↑ | 10 | 46.7% | 35.9% | +10.8 | +3.8 to +19.4 | +8.6 | 7 / 1 / 2 | 0.070 | – |
| Clinical synopsis HPO F1, semantic ↑ | 10 | 62.4% | 63.4% | -0.9 | -3.6 to +2.0 | -1.4 | 4 / 6 / 0 | 0.754 | – |
| Generated variants that are OMIM variants (precision) ↑ | 10 | 39.0% | 64.9% | -25.9 | -41.4 to -10.9 | -24.0 | 0 / 7 / 3 | 0.016 | – |
| Causal gene recall ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: none stated ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a mode missing ↓ | 10 | 10.0% | 0.0% | +10.0 | +0.0 to +30.0 | +0.0 | 0 / 1 / 9 | 1.000 | – |
| Inheritance error: an extra mode ↓ | 10 | 10.0% | 0.0% | +10.0 | +0.0 to +30.0 | +0.0 | 0 / 1 / 9 | 1.000 | – |
| Inheritance error: a different mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM references used ↑ | 10 | 94.8% | 97.2% | -2.4 | -5.7 to +0.1 | +0.0 | 1 / 4 / 5 | 0.375 | – |

#### Reconciled case database minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 10 | 47.8% | 45.5% | +2.3 | +0.4 to +4.2 | +2.1 | 7 / 3 / 0 | 0.344 | – |
| Claims supported by cited paper (headline) ↑ | 10 | 96.3% | 97.9% | -1.6 | -2.5 to -0.6 | -1.5 | 2 / 8 / 0 | 0.109 | 0.766 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 10 | 0.5% | 0.1% | +0.4 | -0.1 to +1.1 | +0.2 | 2 / 6 / 2 | 0.289 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 10 | 0.2% | 0.3% | -0.1 | -0.7 to +0.4 | +0.0 | 2 / 2 / 6 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 10 | 28.1% | 30.3% | -2.1 | -6.0 to +2.0 | -3.1 | 4 / 6 / 0 | 0.754 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 10 | 48.4% | 52.5% | -4.1 | -7.7 to -0.3 | -5.2 | 3 / 7 / 0 | 0.344 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 10 | 56.1% | 54.5% | +1.6 | -4.9 to +7.8 | +0.0 | 3 / 2 / 5 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance matches OMIM (headline) ↑ | 10 | 80.0% | 100.0% | -20.0 | -50.0 to +0.0 | +0.0 | 0 / 2 / 8 | 0.500 | 1.000 |
| Claims unsupported or contradicted ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Claims unsupported, before the repair round ↓ | 10 | 0.5% | 0.1% | +0.4 | -0.1 to +1.1 | +0.3 | 2 / 6 / 2 | 0.289 | – |
| Claims contradicted, before the repair round ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 10 | 41.2% | 38.6% | +2.5 | -0.1 to +5.4 | +1.4 | 6 / 3 / 1 | 0.508 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 10 | 49.7% | 47.4% | +2.3 | -0.1 to +5.2 | +1.8 | 7 / 3 / 0 | 0.344 | – |
| Clinical synopsis HPO precision, exact ↑ | 10 | 26.5% | 33.7% | -7.2 | -12.1 to -2.4 | -8.1 | 3 / 7 / 0 | 0.344 | – |
| Clinical synopsis HPO recall, exact ↑ | 10 | 46.7% | 35.9% | +10.8 | +4.0 to +19.4 | +8.6 | 7 / 1 / 2 | 0.070 | – |
| Clinical synopsis HPO F1, semantic ↑ | 10 | 62.4% | 63.4% | -0.9 | -3.7 to +2.0 | -1.4 | 4 / 6 / 0 | 0.754 | – |
| Generated variants that are OMIM variants (precision) ↑ | 10 | 46.7% | 64.9% | -18.3 | -30.5 to -6.4 | -13.9 | 1 / 6 / 3 | 0.125 | – |
| Causal gene recall ↑ | 10 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: none stated ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| Inheritance error: a mode missing ↓ | 10 | 10.0% | 0.0% | +10.0 | +0.0 to +30.0 | +0.0 | 0 / 1 / 9 | 1.000 | – |
| Inheritance error: an extra mode ↓ | 10 | 10.0% | 0.0% | +10.0 | +0.0 to +30.0 | +0.0 | 0 / 1 / 9 | 1.000 | – |
| Inheritance error: a different mode ↓ | 10 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 10 | – | – |
| OMIM references used ↑ | 10 | 94.5% | 97.2% | -2.8 | -6.0 to -0.2 | -0.7 | 1 / 5 / 4 | 0.219 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 12 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Evidence graph 1; Direct reading 1.

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 89.3% | 89.7% | 98.2% | 96.6% | 96.3% |
| … same, before the repair round ↓ | 0.2% (n=11) | 0.2% (n=11) | 0.2% | 0.3% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 43.2% | 41.1% | 44.5% | 46.5% | 48.0% |
| OMIM per-paper facts contradicted ↓ | 0.4% (n=11) | 0.4% (n=11) | 0.3% | 0.2% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 25.0% | 30.4% | 31.6% | 30.2% | 30.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 44.9% | 49.9% | 51.5% | 48.9% | 48.9% |
| OMIM allelic variants recovered ↑ | 52.5% | 49.0% | 50.4% | 52.0% | 50.3% |
| Causal gene F1 ↑ | 86.0% | 91.7% | 94.3% | 91.7% | 91.7% |
| Inheritance matches OMIM ↑ | 90.9% (n=11) | 100.0% (n=11) | 100.0% (n=11) | 72.7% (n=11) | 72.7% (n=11) |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | -0.4 (-24.6 to +23.9); median -0.1; 3/8/1; p 0.227 | +8.4 (-0.2 to +25.1); median +0.5; 7/5/0; p 0.774 | +6.9 (-2.0 to +23.7); median -1.4; 2/10/0; p 0.039 | +6.6 (-2.3 to +23.5); median -1.5; 3/9/0; p 0.146 |
| … same, before the repair round ↓ | +0.0 (-0.1 to +0.2); median +0.1; 2/5/3; p 0.453 (n=10) | +0.0 (-0.2 to +0.2); median +0.0; 2/3/6; p 1.000 (n=11) | +0.2 (-0.2 to +0.7); median +0.2; 3/6/2; p 0.508 (n=11) | +0.3 (-0.1 to +1.0); median +0.2; 3/6/2; p 0.508 (n=11) |
| OMIM per-paper facts conveyed (primary) ↑ | +2.1 (-8.4 to +14.6); median +1.2; 7/4/1; p 0.549 | +3.4 (-1.5 to +11.8); median -0.4; 3/7/2; p 0.344 | +5.4 (-0.7 to +15.8); median +0.9; 7/4/1; p 0.549 | +6.9 (+0.9 to +17.1); median +2.1; 9/3/0; p 0.146 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.4); median +0.0; 1/2/7; p 1.000 (n=10) | -0.1 (-0.6 to +0.3); median +0.0; 2/2/7; p 1.000 (n=11) | -0.2 (-0.7 to +0.2); median +0.0; 2/1/8; p 1.000 (n=11) | -0.1 (-0.6 to +0.4); median +0.0; 2/3/6; p 1.000 (n=11) |
| Clinical synopsis HPO F1, exact ↑ | -5.4 (-18.3 to +5.5); median -4.8; 3/8/1; p 0.227 | +1.2 (-1.7 to +4.5); median +0.0; 5/4/3; p 1.000 | -0.2 (-5.0 to +5.4); median -2.5; 5/7/0; p 0.774 | -0.2 (-4.9 to +5.5); median -2.5; 5/7/0; p 0.774 |
| Clinical synopsis HPO F1, hierarchical ↑ | -5.1 (-20.8 to +9.2); median -3.4; 3/9/0; p 0.146 | +1.6 (-4.2 to +8.7); median +0.2; 6/5/1; p 1.000 | -1.0 (-6.0 to +5.2); median -2.4; 5/7/0; p 0.774 | -1.0 (-6.0 to +5.1); median -2.4; 5/7/0; p 0.774 |
| OMIM allelic variants recovered ↑ | +3.5 (-12.7 to +20.5); median +0.0; 5/2/5; p 0.453 | +1.4 (-3.0 to +6.0); median +0.0; 3/2/7; p 1.000 | +3.0 (-2.3 to +8.1); median +0.0; 4/2/6; p 0.688 | +1.4 (-5.0 to +7.6); median +0.0; 4/3/5; p 1.000 |
| Causal gene F1 ↑ | -5.7 (-25.0 to +7.9); median +0.0; 1/1/10; p 1.000 | +2.6 (+0.0 to +7.9); median +0.0; 1/0/11; p 1.000 | +0.0 (+0.0 to +0.0); median +0.0; 0/0/12; p – | +0.0 (+0.0 to +0.0); median +0.0; 0/0/12; p – |
| Inheritance matches OMIM ↑ | -9.1 (-27.3 to +0.0); median +0.0; 0/1/10; p 1.000 (n=11) | +0.0 (+0.0 to +0.0); median +0.0; 0/0/11; p – (n=11) | -27.3 (-54.5 to +0.0); median +0.0; 0/3/8; p 0.250 (n=11) | -27.3 (-54.5 to +0.0); median +0.0; 0/3/8; p 0.250 (n=11) |

## Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims audited | 4,064 | 3,030 | 2,854 | 4,077 | 3,954 |
| … supported | 3,963 | 2,962 | 2,799 | 3,944 | 3,810 |
| … partly supported | 99 | 68 | 54 | 133 | 144 |
| … unsupported | 2 | 0 | 1 | 0 | 0 |
| … contradicted | 0 | 0 | 0 | 0 | 0 |
| Claims audited before repair | 4,056 | 3,025 | 2,852 | 4,084 | 3,972 |
| … unsupported before repair | 7 | 3 | 4 | 16 | 21 |
| … contradicted before repair | 0 | 0 | 0 | 0 | 0 |
| OMIM facts scored | 1,106 | 1,106 | 1,106 | 1,106 | 1,106 |
| … conveyed | 456 | 435 | 422 | 441 | 461 |
| … partly conveyed | 146 | 150 | 152 | 149 | 148 |
| … missing | 501 | 518 | 530 | 515 | 495 |
| … contradicted | 3 | 3 | 2 | 1 | 2 |

## Allelic variants: precision and variants not in OMIM

| | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Variants generated | 103 | 63 | 66 | 145 | 128 |
| … matching an OMIM variant of the entry | 45 | 41 | 43 | 45 | 44 |
| … listed by OMIM only from a paper outside the entry's references | 3 | 1 | 1 | 3 | 3 |
| … not in OMIM | 55 | 21 | 22 | 97 | 81 |
| Pooled precision (entries where OMIM lists variants) | 43.7% | 65.1% | 65.1% | 31.0% | 34.4% |

## Inheritance errors by kind

| | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Entries with an OMIM mode of inheritance | 10 | 10 | 10 | 10 | 10 |
| … matched | 10 | 10 | 10 | 8 | 8 |
| … none stated | 0 | 0 | 0 | 0 | 0 |
| … a mode missing | 0 | 0 | 0 | 1 | 1 |
| … an extra mode | 0 | 0 | 0 | 1 | 1 |
| … a different mode | 0 | 0 | 0 | 0 | 0 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| fulltext | 89.1% (46) | 81.5% (46) | 63.0% (46) | 76.1% (46) | 75.0% (46) |
| abstract | 48.1% (942) | 46.9% (942) | 46.9% (942) | 47.7% (942) | 49.3% (942) |
| title | 29.2% (118) | 26.3% (118) | 23.3% (118) | 26.3% (118) | 30.5% (118) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies. Facts are split from the gold paragraph separately for each draft, so the fact counts differ slightly.

| Paper readable as | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|
| fulltext | +7.6; n=3 | -18.5; n=3 | -5.4; n=3 | -6.5; n=3 |
| abstract | +1.3 (-0.9 to +3.0) †; n=10 | +0.0 (-0.5 to +0.9) †; n=10 | +0.9 (-0.7 to +2.5) †; n=10 | +2.4 (+1.1 to +4.4) †; n=10 |
| title | +3.0 (+0.0 to +5.7) †; n=5 | -3.0 (-7.0 to +1.2) †; n=5 | +0.0 (-4.3 to +5.4) †; n=5 | +4.2 (+0.0 to +6.8) †; n=5 |

† fewer than 20 entries: the interval is unreliable.

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| no full text (abstracts only) | 5 | +1.7 (-0.1 to +4.3) †; n=5 | -0.1 (-0.7 to +0.6) †; n=5 | +0.7 (-1.5 to +3.4) †; n=5 | +3.6 (+0.9 to +6.3) †; n=5 |
| under half full text | 5 | -0.2 (-6.7 to +4.4) †; n=5 | -1.1 (-3.8 to +1.4) †; n=5 | +0.2 (-2.4 to +2.8) †; n=5 | +1.0 (-1.5 to +3.0) †; n=5 |

### OMIM allelic variants recovered

| Access group | Entries | Evidence graph | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| no full text (abstracts only) | 5 | +5.4 (+0.0 to +11.1) †; n=5 | +1.4 (+0.0 to +4.3) †; n=5 | +5.4 (+0.0 to +11.1) †; n=5 | +5.4 (+0.0 to +11.1) †; n=5 |
| under half full text | 5 | -2.7 (-26.7 to +15.3) †; n=5 | +1.9 (-4.3 to +10.0) †; n=5 | +1.9 (-4.3 to +10.0) †; n=5 | -2.1 (-12.3 to +8.6) †; n=5 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 620000 onward |
|---|---|---|---|---|
| fulltext | 75.0% (26 facts, 1 entry) | 84.6% (13 facts, 1 entry) | – | 100.0% (7 facts, 1 entry) |
| abstract | 37.3% (307 facts, 3 entries) | 51.8% (439 facts, 3 entries) | 55.2% (155 facts, 3 entries) | 34.2% (41 facts, 1 entry) |
| title | 16.0% (25 facts, 1 entry) | 46.2% (26 facts, 1 entry) | 22.4% (67 facts, 3 entries) | – |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 5 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.7% | 98.4% | 98.7% | 96.3% | 95.8% |
| … same, before the repair round ↓ | 0.3% | 0.3% | 0.2% | 0.6% | 0.9% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 39.5% | 37.8% | 37.7% | 38.4% | 41.3% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 0.4% | 0.4% | 0.2% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 28.2% | 30.9% | 31.7% | 31.0% | 31.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.4% | 57.2% | 57.4% | 55.5% | 55.5% |
| OMIM allelic variants recovered ↑ | 31.7% | 26.3% | 27.8% | 31.7% | 31.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |

### under half full text — 5 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.3% | 97.4% | 97.5% | 97.0% | 96.8% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 0.1% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.1% | 53.3% | 52.2% | 53.5% | 54.3% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.2% | 0.0% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 25.1% | 29.6% | 27.4% | 25.2% | 25.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 42.5% | 47.9% | 43.8% | 41.3% | 41.3% |
| OMIM allelic variants recovered ↑ | 80.0% | 82.7% | 84.6% | 84.6% | 80.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |

## By size of the reference list

### 9 or more references — 10 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.5% | 97.9% | 98.1% | 96.7% | 96.3% |
| … same, before the repair round ↓ | 0.2% | 0.1% | 0.2% | 0.4% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 46.3% | 45.5% | 44.9% | 46.0% | 47.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.2% | 0.1% | 0.2% |
| Clinical synopsis HPO F1, exact ↑ | 26.7% | 30.3% | 29.6% | 28.1% | 28.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 48.9% | 52.5% | 50.6% | 48.4% | 48.4% |
| OMIM allelic variants recovered ↑ | 55.8% | 54.5% | 56.2% | 58.1% | 56.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 80.0% | 80.0% |

## By creation era (MIM number range)

### 600000-609999 — 3 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.0% | 97.0% | 96.8% | 97.1% | 96.8% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 0.1% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 59.0% | 56.9% | 57.6% | 58.0% | 58.8% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.3% | 0.0% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 26.6% | 36.5% | 35.9% | 27.1% | 27.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 46.5% | 55.0% | 54.8% | 45.4% | 45.4% |
| OMIM allelic variants recovered ↑ | 91.7% | 86.1% | 89.3% | 89.3% | 89.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 66.7% | 66.7% |

### 610000-615999 — 3 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.6% | 98.2% | 98.5% | 96.2% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.3% | 0.3% | 0.9% | 1.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 48.5% | 46.0% | 46.4% | 47.0% | 51.0% |
| OMIM per-paper facts contradicted ↓ | 1.1% | 0.7% | 0.3% | 0.3% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 32.9% | 39.3% | 38.9% | 39.5% | 39.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.4% | 58.6% | 58.1% | 60.2% | 60.2% |
| OMIM allelic variants recovered ↑ | 38.3% | 34.2% | 34.2% | 38.3% | 38.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 66.7% | 66.7% |

### 620000 onward — 1 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.5% | 97.6% | 99.1% | 96.8% | 96.9% |
| … same, before the repair round ↓ | 0.2% | 0.0% | 0.0% | 0.2% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 31.2% | 43.8% | 41.7% | 39.6% | 40.6% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | 11.7% | 4.3% | 4.4% | 9.9% | 9.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 21.6% | 28.9% | 28.2% | 19.9% | 19.9% |
| OMIM allelic variants recovered ↑ | 25.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

### classic (1xxxxx-5xxxxx) — 3 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.8% | 98.6% | 98.7% | 96.7% | 96.5% |
| … same, before the repair round ↓ | 0.1% | 0.2% | 0.1% | 0.2% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 36.4% | 34.3% | 31.9% | 35.1% | 36.0% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.0% | 0.3% | 0.0% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 25.4% | 23.7% | 22.3% | 23.8% | 23.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.1% | 51.8% | 46.4% | 49.1% | 49.1% |
| OMIM allelic variants recovered ↑ | 47.8% | 36.4% | 38.8% | 41.1% | 34.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Case table first | Reconciled case database |
|---|---|---|---|---|---|
| Generation: model calls | 43.9 | 2.0 | 2.0 | 44.0 | 45.9 |
| Generation: list price | $2.38 | $0.59 | $0.90 | $2.55 | $2.81 |
| Generation: input / output tokens | 273,265 / 67,321 | 34,086 / 17,083 | 169,973 / 27,350 | 338,163 / 72,294 | 362,469 / 76,857 |
| Generation: model time (s) | 577 | 132 | 213 | 639 | 686 |
| Audit and repair: list price | $2.83 | $2.32 | $2.19 | $2.88 | $2.84 |
| Scoring against OMIM: list price | $0.68 | $0.33 | $0.33 | $0.68 | $0.67 |
| Everything: list price | $5.89 | $3.24 | $3.42 | $6.11 | $6.32 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 13 | 24 | 16 | 54.2% | 81.2% | 65.0% |
| Disease → causal gene | Direct reading | 11 | 11 | 16 | 100.0% | 68.8% | 81.5% |
| Disease → causal gene | Agentic curator | 14 | 25 | 16 | 56.0% | 87.5% | 68.3% |
| Disease → causal gene | Case table first | 11 | 13 | 16 | 84.6% | 68.8% | 75.9% |
| Disease → causal gene | Reconciled case database | 11 | 13 | 16 | 84.6% | 68.8% | 75.9% |
| Disease → mode of inheritance | Evidence graph | 11 | 12 | 12 | 91.7% | 91.7% | 91.7% |
| Disease → mode of inheritance | Direct reading | 12 | 12 | 12 | 100.0% | 100.0% | 100.0% |
| Disease → mode of inheritance | Agentic curator | 12 | 13 | 12 | 92.3% | 100.0% | 96.0% |
| Disease → mode of inheritance | Case table first | 11 | 15 | 12 | 73.3% | 91.7% | 81.5% |
| Disease → mode of inheritance | Reconciled case database | 11 | 15 | 12 | 73.3% | 91.7% | 81.5% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 91 | 468 | 198 | 19.4% | 46.0% | 27.3% |
| Disease → phenotype (HPO, exact id) | Direct reading | 69 | 231 | 193 | 29.9% | 35.8% | 32.6% |
| Disease → phenotype (HPO, exact id) | Agentic curator | 72 | 227 | 196 | 31.7% | 36.7% | 34.0% |
| Disease → phenotype (HPO, exact id) | Case table first | 90 | 454 | 195 | 19.8% | 46.2% | 27.7% |
| Disease → phenotype (HPO, exact id) | Reconciled case database | 90 | 454 | 195 | 19.8% | 46.2% | 27.7% |
| Disease → allelic variant | Evidence graph | 55 | 121 | 104 | 45.5% | 52.9% | 48.9% |
| Disease → allelic variant | Direct reading | 46 | 68 | 101 | 67.7% | 45.5% | 54.4% |
| Disease → allelic variant | Agentic curator | 48 | 71 | 101 | 67.6% | 47.5% | 55.8% |
| Disease → allelic variant | Case table first | 65 | 155 | 116 | 41.9% | 56.0% | 48.0% |
| Disease → allelic variant | Reconciled case database | 52 | 138 | 104 | 37.7% | 50.0% | 43.0% |
