# Generation strategies compared — run `omim100`

93 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

No draft: 3 entries for which at least one strategy wrote nothing, because the model's safety filter stopped the writer's reply or the reply came back empty (Agentic curator 2; Direct reading 3; Evidence graph 1). Entries: 609296, 620609, 621068. They are left out of the comparison with the incomplete entries listed under Completion.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 93 of the run's 100 entries qualify; left out: 118210, 300148, 609296, 617232, 620609, 621030, 621068. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 96 | 3: 118210 (1 paper), 617232 (1 paper), 621030 (1 paper) | 1: 620609 |
| Direct reading | 97 | 0 | 3: 609296, 620609, 621068 |
| Agentic curator | 98 | 0 | 2: 609296, 620609 |
| Memory only (control) | 100 | 0 | 0 |
| Recall, then verify | 100 | 0 | 0 |
| Case table first | 97 | 3: 300148 (1 paper), 617232 (2 papers), 621068 (1 paper) | 0 |

## How the scores are counted

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Evidence graph: genes 1, variants 6; Direct reading: genes 1, variants 11; Agentic curator: genes 1, variants 11; Memory only (control): genes 13, synopsis 1, variants 63; Recall, then verify: genes 14, synopsis 6, variants 70; Case table first: genes 2, variants 5.

- **n.** A value rests on all 93 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

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
| Claims supported by cited paper ↑ | 96.5% | 96.1% | 96.4% | 50.8% | 94.2% (n=92) | 94.7% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% | 0.0% | 22.7% | 0.0% (n=92) | 0.0% |
| … same, before the repair round ↓ | 0.3% | 0.2% | 0.1% | 22.7% | 0.7% (n=92) | 0.4% |
| … unsupported, before the repair round ↓ | 0.2% | 0.2% | 0.1% | 22.1% | 0.6% (n=92) | 0.4% |
| … contradicted, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 0.6% | 0.1% (n=92) | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.3% | 52.1% | 51.3% | 20.4% | 18.2% | 49.2% |
| … fully (no partial credit) ↑ | 43.1% | 43.6% | 43.1% | 12.2% | 12.1% | 41.0% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.5% | 0.5% | 0.8% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 34.6% | 35.9% | 35.6% | 30.6% | 24.9% | 34.0% |
| … precision ↑ | 40.6% | 44.1% | 45.5% | 53.5% (n=92) | 53.6% (n=87) | 40.7% |
| … recall ↑ | 37.4% | 36.2% | 34.2% | 24.1% | 18.4% | 37.7% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.7% | 56.1% | 56.2% | 48.2% | 40.5% | 53.7% |
| Clinical synopsis HPO F1, semantic ↑ | 65.0% | 66.3% | 66.0% | 62.0% | 53.3% | 64.5% |
| OMIM allelic variants recovered ↑ | 65.9% | 66.5% | 65.9% | 15.2% | 11.6% | 63.9% |
| Generated variants that are OMIM variants (precision) ↑ | 77.8% (n=87) | 88.7% (n=82) | 87.9% (n=82) | 97.2% (n=30) | 100.0% (n=23) | 72.2% (n=88) |
| Causal gene F1 ↑ | 98.2% | 97.5% | 97.5% | 83.9% | 82.8% | 93.9% |
| … recall ↑ | 98.4% | 97.3% | 97.3% | 83.9% | 82.8% | 94.1% |
| Inheritance matches OMIM ↑ | 92.5% | 93.5% | 93.5% | 82.8% | 73.1% | 91.4% |
| Inheritance error: none stated ↓ | 3.2% | 2.1% | 3.2% | 14.0% | 23.7% | 2.1% |
| Inheritance error: a mode missing ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 1.1% |
| Inheritance error: an extra mode ↓ | 3.2% | 4.3% | 3.2% | 1.1% | 1.1% | 4.3% |
| Inheritance error: a different mode ↓ | 1.1% | 0.0% | 0.0% | 2.1% | 2.1% | 1.1% |
| OMIM references used ↑ | 94.6% | 94.4% | 93.3% | 33.6% | 65.2% | 94.6% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited per entry | 113.5 | 101.0 | 97.3 | 28.2 | 26.3 | 117.9 |
| Claims that could not be audited per entry | 1.2 | 0.6 | 0.3 | 0.0 | 0.0 | 0.4 |
| Clinical-synopsis HPO terms per entry | 19.2 | 15.4 | 13.8 | 6.2 | 4.4 | 21.0 |
| Allelic variants per entry | 3.9 | 3.2 | 3.2 | 0.4 | 0.3 | 4.1 |
| … of which not in OMIM | 1.1 | 0.4 | 0.4 | 0.0 | 0.0 | 1.5 |
| Papers cited per entry | 5.0 | 4.9 | 4.8 | 1.6 | 3.2 | 5.0 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.1 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | +0.4 (-0.4 to +1.3); 42/44/7 | +0.3 (-0.4 to +1.0); 53/33/7 | -45.3 (-50.4 to -40.2); 2/90/1 | -1.9 (-3.4 to -0.4); 34/53/5 (n=92) | -1.4 (-2.6 to -0.3); 35/55/3 |
| … same, before the repair round ↓ | +0.0 (-0.3 to +0.3); 11/13/69 | -0.1 (-0.4 to +0.1); 11/8/74 | +22.4 (+18.4 to +26.7); 1/79/13 | +0.4 (-0.1 to +0.9); 10/10/72 (n=92) | +0.2 (-0.1 to +0.5); 10/19/64 |
| OMIM per-paper facts conveyed (primary) ↑ | -0.8 (-1.7 to +0.1); 43/43/7 | -0.7 (-1.6 to +0.1); 43/46/4 | -31.6 (-36.4 to -27.0); 7/86/0 | -33.9 (-38.2 to -29.5); 3/90/0 | -2.8 (-4.1 to -1.7); 28/62/3 |
| OMIM per-paper facts contradicted ↓ | +0.2 (-0.1 to +0.6); 11/11/71 | +0.0 (-0.1 to +0.2); 9/10/74 | +0.3 (-0.1 to +0.8); 16/16/61 | -0.0 (-0.3 to +0.2); 16/10/67 | +0.1 (-0.2 to +0.6); 10/11/72 |
| Clinical synopsis HPO F1, exact ↑ | -1.3 (-3.2 to +0.6); 34/45/14 | -0.3 (-1.5 to +0.8); 38/32/23 | -5.3 (-9.2 to -1.4); 41/52/0 | -11.0 (-14.5 to -7.5); 25/63/5 | -2.0 (-3.9 to -0.1); 39/45/9 |
| Clinical synopsis HPO F1, hierarchical ↑ | -1.4 (-2.8 to -0.1); 36/44/13 | +0.0 (-1.1 to +1.1); 40/35/18 | -7.9 (-12.4 to -3.6); 38/54/1 | -15.7 (-20.0 to -11.6); 21/68/4 | -2.5 (-4.0 to -1.0); 34/51/8 |
| OMIM allelic variants recovered ↑ | -0.5 (-3.1 to +2.5); 4/8/81 | -0.6 (-2.1 to +0.7); 3/3/87 | -51.3 (-59.8 to -42.4); 3/69/21 | -54.9 (-62.8 to -46.9); 0/71/22 | -2.6 (-5.2 to -0.1); 4/12/77 |
| Causal gene F1 ↑ | +0.7 (+0.0 to +2.1); 1/0/92 | +0.0 (+0.0 to +0.0); 0/0/93 | -13.6 (-21.9 to -6.1); 2/15/76 | -14.7 (-22.2 to -7.5); 1/15/77 | -3.6 (-8.6 to +0.4); 1/4/88 |
| Inheritance matches OMIM ↑ | -1.1 (-4.3 to +2.1); 1/2/90 | +0.0 (-3.2 to +3.2); 1/1/91 | -10.8 (-19.4 to -3.2); 3/13/77 | -20.4 (-29.0 to -11.8); 1/20/72 | -2.1 (-8.6 to +4.3); 4/6/83 |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Evidence graph minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 93 | 51.3% | 52.1% | -0.8 | -1.7 to +0.1 | +0.0 | 43 / 43 / 7 | 1.000 | – |
| Claims supported by cited paper (headline) ↑ | 93 | 96.5% | 96.1% | +0.4 | -0.4 to +1.3 | +0.0 | 42 / 44 / 7 | 0.914 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 93 | 0.3% | 0.2% | +0.0 | -0.3 to +0.3 | +0.0 | 11 / 13 / 69 | 0.839 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 93 | 0.7% | 0.5% | +0.2 | -0.1 to +0.6 | +0.0 | 11 / 11 / 71 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 93 | 34.6% | 35.9% | -1.3 | -3.2 to +0.6 | +0.0 | 34 / 45 / 14 | 0.260 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 93 | 54.7% | 56.1% | -1.4 | -2.8 to -0.1 | +0.0 | 36 / 44 / 13 | 0.434 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 93 | 65.9% | 66.5% | -0.5 | -3.1 to +2.5 | +0.0 | 4 / 8 / 81 | 0.388 | 1.000 |
| Causal gene F1 (headline) ↑ | 93 | 98.2% | 97.5% | +0.7 | +0.0 to +2.1 | +0.0 | 1 / 0 / 92 | 1.000 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 93 | 92.5% | 93.5% | -1.1 | -4.3 to +2.1 | +0.0 | 1 / 2 / 90 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Claims unsupported, before the repair round ↓ | 93 | 0.2% | 0.2% | -0.0 | -0.3 to +0.2 | +0.0 | 11 / 10 / 72 | 1.000 | – |
| Claims contradicted, before the repair round ↓ | 93 | 0.1% | 0.0% | +0.1 | +0.0 to +0.1 | +0.0 | 0 / 4 / 89 | 0.125 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 93 | 43.1% | 43.6% | -0.4 | -1.6 to +0.7 | +0.0 | 46 / 40 / 7 | 0.590 | – |
| Clinical synopsis HPO precision, exact ↑ | 93 | 40.6% | 44.1% | -3.5 | -6.8 to -0.5 | -1.9 | 29 / 49 / 15 | 0.031 | – |
| Clinical synopsis HPO recall, exact ↑ | 93 | 37.4% | 36.2% | +1.1 | -1.3 to +3.4 | +0.0 | 36 / 20 / 37 | 0.044 | – |
| Clinical synopsis HPO F1, semantic ↑ | 93 | 65.0% | 66.3% | -1.3 | -2.4 to -0.3 | -0.4 | 35 / 52 / 6 | 0.086 | – |
| Generated variants that are OMIM variants (precision) ↑ | 82 | 82.5% | 88.7% | -6.2 | -10.2 to -2.4 | +0.0 | 2 / 18 / 62 | <0.001 | – |
| Causal gene recall ↑ | 93 | 98.4% | 97.3% | +1.1 | +0.0 to +3.2 | +0.0 | 1 / 0 / 92 | 1.000 | – |
| Inheritance error: none stated ↓ | 93 | 3.2% | 2.1% | +1.1 | -2.1 to +5.4 | +0.0 | 1 / 2 / 90 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance error: an extra mode ↓ | 93 | 3.2% | 4.3% | -1.1 | -3.2 to +0.0 | +0.0 | 1 / 0 / 92 | 1.000 | – |
| Inheritance error: a different mode ↓ | 93 | 1.1% | 0.0% | +1.1 | +0.0 to +3.2 | +0.0 | 0 / 1 / 92 | 1.000 | – |
| OMIM references used ↑ | 93 | 94.6% | 94.4% | +0.2 | -2.2 to +2.3 | +0.0 | 9 / 5 / 79 | 0.424 | – |

#### Agentic curator minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 93 | 51.3% | 52.1% | -0.7 | -1.6 to +0.1 | +0.0 | 43 / 46 / 4 | 0.832 | – |
| Claims supported by cited paper (headline) ↑ | 93 | 96.4% | 96.1% | +0.3 | -0.4 to +1.0 | +0.7 | 53 / 33 / 7 | 0.040 | 0.279 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 93 | 0.1% | 0.2% | -0.1 | -0.4 to +0.1 | +0.0 | 11 / 8 / 74 | 0.648 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 93 | 0.5% | 0.5% | +0.0 | -0.1 to +0.2 | +0.0 | 9 / 10 / 74 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 93 | 35.6% | 35.9% | -0.3 | -1.5 to +0.8 | +0.0 | 38 / 32 / 23 | 0.550 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 93 | 56.2% | 56.1% | +0.0 | -1.1 to +1.1 | +0.0 | 40 / 35 / 18 | 0.644 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 93 | 65.9% | 66.5% | -0.6 | -2.1 to +0.7 | +0.0 | 3 / 3 / 87 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 93 | 97.5% | 97.5% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance matches OMIM (headline) ↑ | 93 | 93.5% | 93.5% | +0.0 | -3.2 to +3.2 | +0.0 | 1 / 1 / 91 | 1.000 | 1.000 |
| Claims unsupported or contradicted ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 1 / 92 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 93 | 0.1% | 0.2% | -0.1 | -0.4 to +0.1 | +0.0 | 11 / 6 / 76 | 0.332 | – |
| Claims contradicted, before the repair round ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 2 / 91 | 0.500 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 93 | 43.1% | 43.6% | -0.5 | -1.3 to +0.3 | -0.4 | 42 / 48 / 3 | 0.598 | – |
| Clinical synopsis HPO precision, exact ↑ | 93 | 45.5% | 44.1% | +1.3 | -0.2 to +2.7 | +0.0 | 42 / 26 / 25 | 0.068 | – |
| Clinical synopsis HPO recall, exact ↑ | 93 | 34.2% | 36.2% | -2.0 | -3.5 to -0.7 | +0.0 | 17 / 30 / 46 | 0.079 | – |
| Clinical synopsis HPO F1, semantic ↑ | 93 | 66.0% | 66.3% | -0.3 | -1.3 to +0.7 | +0.0 | 32 / 45 / 16 | 0.171 | – |
| Generated variants that are OMIM variants (precision) ↑ | 82 | 87.9% | 88.7% | -0.8 | -3.6 to +2.1 | +0.0 | 3 / 7 / 72 | 0.344 | – |
| Causal gene recall ↑ | 93 | 97.3% | 97.3% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance error: none stated ↓ | 93 | 3.2% | 2.1% | +1.1 | +0.0 to +3.2 | +0.0 | 0 / 1 / 92 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance error: an extra mode ↓ | 93 | 3.2% | 4.3% | -1.1 | -3.2 to +0.0 | +0.0 | 1 / 0 / 92 | 1.000 | – |
| Inheritance error: a different mode ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| OMIM references used ↑ | 93 | 93.3% | 94.4% | -1.1 | -3.0 to +0.8 | +0.0 | 3 / 9 / 81 | 0.146 | – |

#### Memory only (control) minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 93 | 20.4% | 52.1% | -31.6 | -36.4 to -27.0 | -31.1 | 7 / 86 / 0 | <0.001 | – |
| Claims supported by cited paper (headline) ↑ | 93 | 50.8% | 96.1% | -45.3 | -50.4 to -40.2 | -47.1 | 2 / 90 / 1 | <0.001 | <0.001 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 93 | 22.7% | 0.2% | +22.4 | +18.4 to +26.7 | +18.5 | 1 / 79 / 13 | <0.001 | <0.001 |
| OMIM per-paper facts contradicted (headline) ↓ | 93 | 0.8% | 0.5% | +0.3 | -0.1 to +0.8 | +0.0 | 16 / 16 / 61 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 93 | 30.6% | 35.9% | -5.3 | -9.2 to -1.4 | -2.9 | 41 / 52 / 0 | 0.300 | 0.599 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 93 | 48.2% | 56.1% | -7.9 | -12.4 to -3.6 | -3.8 | 38 / 54 / 1 | 0.117 | 0.352 |
| OMIM allelic variants recovered (headline) ↑ | 93 | 15.2% | 66.5% | -51.3 | -59.8 to -42.4 | -50.0 | 3 / 69 / 21 | <0.001 | <0.001 |
| Causal gene F1 (headline) ↑ | 93 | 83.9% | 97.5% | -13.6 | -21.9 to -6.1 | +0.0 | 2 / 15 / 76 | 0.002 | 0.011 |
| Inheritance matches OMIM (headline) ↑ | 93 | 82.8% | 93.5% | -10.8 | -19.4 to -3.2 | +0.0 | 3 / 13 / 77 | 0.021 | 0.085 |
| Claims unsupported or contradicted ↓ | 93 | 22.7% | 0.0% | +22.7 | +18.6 to +27.1 | +18.5 | 0 / 79 / 14 | <0.001 | – |
| Claims unsupported, before the repair round ↓ | 93 | 22.1% | 0.2% | +21.8 | +17.8 to +26.2 | +16.7 | 1 / 78 / 14 | <0.001 | – |
| Claims contradicted, before the repair round ↓ | 93 | 0.6% | 0.0% | +0.6 | +0.2 to +1.1 | +0.0 | 0 / 10 / 83 | 0.002 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 93 | 12.2% | 43.6% | -31.4 | -36.5 to -26.4 | -32.1 | 9 / 84 / 0 | <0.001 | – |
| Clinical synopsis HPO precision, exact ↑ | 92 | 53.5% | 44.2% | +9.4 | +3.9 to +15.0 | +11.5 | 61 / 31 / 0 | 0.002 | – |
| Clinical synopsis HPO recall, exact ↑ | 93 | 24.1% | 36.2% | -12.1 | -16.3 to -8.0 | -10.0 | 18 / 60 / 15 | <0.001 | – |
| Clinical synopsis HPO F1, semantic ↑ | 93 | 62.0% | 66.3% | -4.3 | -7.8 to -0.7 | -3.7 | 37 / 55 / 1 | 0.076 | – |
| Generated variants that are OMIM variants (precision) ↑ | 29 | 97.1% | 87.9% | +9.2 | -0.8 to +20.8 | +0.0 | 7 / 2 / 20 | 0.180 | – |
| Causal gene recall ↑ | 93 | 83.9% | 97.3% | -13.4 | -21.5 to -5.4 | +0.0 | 2 / 15 / 76 | 0.002 | – |
| Inheritance error: none stated ↓ | 93 | 14.0% | 2.1% | +11.8 | +4.3 to +19.4 | +0.0 | 2 / 13 / 78 | 0.007 | – |
| Inheritance error: a mode missing ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance error: an extra mode ↓ | 93 | 1.1% | 4.3% | -3.2 | -7.5 to +0.0 | +0.0 | 3 / 0 / 90 | 0.250 | – |
| Inheritance error: a different mode ↓ | 93 | 2.1% | 0.0% | +2.1 | +0.0 to +5.4 | +0.0 | 0 / 2 / 91 | 0.500 | – |
| OMIM references used ↑ | 93 | 33.6% | 94.4% | -60.9 | -66.2 to -55.3 | -63.6 | 0 / 86 / 7 | <0.001 | – |

#### Recall, then verify minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 93 | 18.2% | 52.1% | -33.9 | -38.2 to -29.5 | -30.5 | 3 / 90 / 0 | <0.001 | – |
| Claims supported by cited paper (headline) ↑ | 92 | 94.2% | 96.1% | -1.9 | -3.4 to -0.4 | -1.5 | 34 / 53 / 5 | 0.053 | 0.159 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 92 | 0.7% | 0.2% | +0.4 | -0.1 to +0.9 | +0.0 | 10 / 10 / 72 | 1.000 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 93 | 0.5% | 0.5% | -0.0 | -0.3 to +0.2 | +0.0 | 16 / 10 / 67 | 0.327 | 0.654 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 93 | 24.9% | 35.9% | -11.0 | -14.5 to -7.5 | -9.3 | 25 / 63 / 5 | <0.001 | <0.001 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 93 | 40.5% | 56.1% | -15.7 | -20.0 to -11.6 | -11.5 | 21 / 68 / 4 | <0.001 | <0.001 |
| OMIM allelic variants recovered (headline) ↑ | 93 | 11.6% | 66.5% | -54.9 | -62.8 to -46.9 | -60.0 | 0 / 71 / 22 | <0.001 | <0.001 |
| Causal gene F1 (headline) ↑ | 93 | 82.8% | 97.5% | -14.7 | -22.2 to -7.5 | +0.0 | 1 / 15 / 77 | <0.001 | 0.002 |
| Inheritance matches OMIM (headline) ↑ | 93 | 73.1% | 93.5% | -20.4 | -29.0 to -11.8 | +0.0 | 1 / 20 / 72 | <0.001 | <0.001 |
| Claims unsupported or contradicted ↓ | 92 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 92 | – | – |
| Claims unsupported, before the repair round ↓ | 92 | 0.6% | 0.2% | +0.3 | -0.1 to +0.8 | +0.0 | 12 / 8 / 72 | 0.503 | – |
| Claims contradicted, before the repair round ↓ | 92 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 3 / 89 | 0.250 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 93 | 12.1% | 43.6% | -31.5 | -36.0 to -27.0 | -29.7 | 3 / 88 / 2 | <0.001 | – |
| Clinical synopsis HPO precision, exact ↑ | 87 | 53.6% | 44.6% | +9.0 | +2.9 to +15.1 | +10.0 | 55 / 28 / 4 | 0.004 | – |
| Clinical synopsis HPO recall, exact ↑ | 93 | 18.4% | 36.2% | -17.9 | -21.5 to -14.3 | -15.3 | 5 / 72 / 16 | <0.001 | – |
| Clinical synopsis HPO F1, semantic ↑ | 93 | 53.3% | 66.3% | -13.0 | -17.0 to -9.3 | -10.8 | 25 / 66 / 2 | <0.001 | – |
| Generated variants that are OMIM variants (precision) ↑ | 23 | 100.0% | 92.5% | +7.5 | +0.9 to +16.8 | +0.0 | 4 / 0 / 19 | 0.125 | – |
| Causal gene recall ↑ | 93 | 82.8% | 97.3% | -14.5 | -22.6 to -7.0 | +0.0 | 1 / 15 / 77 | <0.001 | – |
| Inheritance error: none stated ↓ | 93 | 23.7% | 2.1% | +21.5 | +12.9 to +30.1 | +0.0 | 0 / 20 / 73 | <0.001 | – |
| Inheritance error: a mode missing ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Inheritance error: an extra mode ↓ | 93 | 1.1% | 4.3% | -3.2 | -7.5 to +0.0 | +0.0 | 3 / 0 / 90 | 0.250 | – |
| Inheritance error: a different mode ↓ | 93 | 2.1% | 0.0% | +2.1 | +0.0 to +5.4 | +0.0 | 0 / 2 / 91 | 0.500 | – |
| OMIM references used ↑ | 93 | 65.2% | 94.4% | -29.2 | -34.2 to -24.2 | -25.0 | 2 / 71 / 20 | <0.001 | – |

#### Case table first minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 93 | 49.2% | 52.1% | -2.8 | -4.1 to -1.7 | -2.5 | 28 / 62 / 3 | <0.001 | – |
| Claims supported by cited paper (headline) ↑ | 93 | 94.7% | 96.1% | -1.4 | -2.6 to -0.3 | -0.8 | 35 / 55 / 3 | 0.045 | 0.357 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 93 | 0.4% | 0.2% | +0.2 | -0.1 to +0.5 | +0.0 | 10 / 19 / 64 | 0.136 | 0.680 |
| OMIM per-paper facts contradicted (headline) ↓ | 93 | 0.6% | 0.5% | +0.1 | -0.2 to +0.6 | +0.0 | 10 / 11 / 72 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 93 | 34.0% | 35.9% | -2.0 | -3.9 to -0.1 | +0.0 | 39 / 45 / 9 | 0.586 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 93 | 53.7% | 56.1% | -2.5 | -4.0 to -1.0 | -0.6 | 34 / 51 / 8 | 0.082 | 0.538 |
| OMIM allelic variants recovered (headline) ↑ | 93 | 63.9% | 66.5% | -2.6 | -5.2 to -0.1 | +0.0 | 4 / 12 / 77 | 0.077 | 0.538 |
| Causal gene F1 (headline) ↑ | 93 | 93.9% | 97.5% | -3.6 | -8.6 to +0.4 | +0.0 | 1 / 4 / 88 | 0.375 | 1.000 |
| Inheritance matches OMIM (headline) ↑ | 93 | 91.4% | 93.5% | -2.1 | -8.6 to +4.3 | +0.0 | 4 / 6 / 83 | 0.754 | 1.000 |
| Claims unsupported or contradicted ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 93 | – | – |
| Claims unsupported, before the repair round ↓ | 93 | 0.4% | 0.2% | +0.1 | -0.2 to +0.4 | +0.0 | 12 / 16 / 65 | 0.572 | – |
| Claims contradicted, before the repair round ↓ | 93 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 4 / 89 | 0.125 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 93 | 41.0% | 43.6% | -2.6 | -4.0 to -1.2 | -1.8 | 29 / 59 / 5 | 0.002 | – |
| Clinical synopsis HPO precision, exact ↑ | 93 | 40.7% | 44.1% | -3.4 | -6.8 to -0.3 | -1.8 | 32 / 50 / 11 | 0.060 | – |
| Clinical synopsis HPO recall, exact ↑ | 93 | 37.7% | 36.2% | +1.4 | -1.1 to +4.0 | +0.0 | 38 / 26 / 29 | 0.169 | – |
| Clinical synopsis HPO F1, semantic ↑ | 93 | 64.5% | 66.3% | -1.8 | -3.2 to -0.5 | -1.0 | 35 / 56 / 2 | 0.035 | – |
| Generated variants that are OMIM variants (precision) ↑ | 82 | 77.5% | 88.7% | -11.3 | -16.6 to -6.0 | +0.0 | 2 / 26 / 54 | <0.001 | – |
| Causal gene recall ↑ | 93 | 94.1% | 97.3% | -3.2 | -8.6 to +1.1 | +0.0 | 1 / 4 / 88 | 0.375 | – |
| Inheritance error: none stated ↓ | 93 | 2.1% | 2.1% | +0.0 | -4.3 to +4.3 | +0.0 | 2 / 2 / 89 | 1.000 | – |
| Inheritance error: a mode missing ↓ | 93 | 1.1% | 0.0% | +1.1 | +0.0 to +3.2 | +0.0 | 0 / 1 / 92 | 1.000 | – |
| Inheritance error: an extra mode ↓ | 93 | 4.3% | 4.3% | +0.0 | -5.4 to +5.4 | +0.0 | 3 / 3 / 87 | 1.000 | – |
| Inheritance error: a different mode ↓ | 93 | 1.1% | 0.0% | +1.1 | +0.0 to +3.2 | +0.0 | 0 / 1 / 92 | 1.000 | – |
| OMIM references used ↑ | 93 | 94.6% | 94.4% | +0.1 | -2.2 to +2.5 | +0.0 | 10 / 10 / 73 | 1.000 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 100 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Evidence graph 1; Direct reading 3; Agentic curator 2.

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 93.2% | 94.5% (n=99) | 51.5% | 94.4% (n=98) | 94.5% (n=99) |
| … same, before the repair round ↓ | 0.3% (n=99) | 0.4% (n=97) | 0.2% (n=97) | 22.8% | 0.7% (n=98) | 0.8% (n=99) |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.0% | 51.3% | 51.7% | 20.1% | 17.9% | 49.0% |
| OMIM per-paper facts contradicted ↓ | 0.7% (n=99) | 0.5% (n=97) | 0.6% (n=98) | 0.8% | 0.5% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.8% | 34.6% | 34.8% | 29.4% | 23.9% | 33.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 54.1% | 54.6% | 55.3% | 46.7% | 39.4% | 52.9% |
| OMIM allelic variants recovered ↑ | 65.6% | 65.6% | 66.1% | 15.1% | 11.3% | 63.5% |
| Causal gene F1 ↑ | 97.3% | 94.7% | 95.7% | 83.0% | 82.0% | 92.3% |
| Inheritance matches OMIM ↑ | 91.0% | 91.0% | 91.0% | 82.0% | 73.0% | 90.0% |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | +2.4 (+0.1 to +5.6); median +0.0; 47/45/8; p 0.917 | +0.3 (-0.4 to +1.0); median +0.7; 56/34/9; p 0.026 (n=99) | -41.8 (-47.6 to -35.6); median -44.5; 4/94/2; p <0.001 | +0.2 (-2.5 to +3.8); median -1.2; 38/55/5; p 0.097 (n=98) | +0.4 (-2.2 to +3.6); median -0.8; 37/59/3; p 0.032 (n=99) |
| … same, before the repair round ↓ | -0.1 (-0.4 to +0.2); median +0.0; 12/13/72; p 1.000 (n=97) | -0.2 (-0.5 to +0.1); median +0.0; 12/9/76; p 0.664 (n=97) | +21.9 (+18.2 to +26.1); median +17.2; 1/82/14; p <0.001 (n=97) | +0.3 (-0.2 to +0.8); median +0.0; 11/10/75; p 1.000 (n=96) | +0.4 (-0.2 to +1.3); median +0.0; 11/20/66; p 0.150 (n=97) |
| OMIM per-paper facts conveyed (primary) ↑ | -0.4 (-3.2 to +2.7); median +0.0; 46/46/8; p 1.000 | +0.4 (-1.2 to +2.8); median +0.0; 46/48/6; p 0.918 | -31.2 (-36.0 to -26.5); median -32.0; 10/90/0; p <0.001 | -33.4 (-37.9 to -29.0); median -31.2; 5/94/1; p <0.001 | -2.3 (-5.1 to +0.6); median -2.4; 31/65/4; p <0.001 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.2 to +0.5); median +0.0; 13/12/72; p 1.000 (n=97) | +0.0 (-0.1 to +0.2); median +0.0; 11/11/75; p 1.000 (n=97) | +0.2 (-0.2 to +0.8); median +0.0; 18/17/62; p 1.000 (n=97) | -0.1 (-0.3 to +0.2); median +0.0; 18/11/68; p 0.265 (n=97) | +0.1 (-0.2 to +0.5); median +0.0; 12/12/73; p 1.000 (n=97) |
| Clinical synopsis HPO F1, exact ↑ | -0.8 (-2.8 to +1.3); median +0.0; 36/48/16; p 0.230 | +0.2 (-1.2 to +1.7); median +0.0; 40/35/25; p 0.644 | -5.2 (-9.0 to -1.4); median -2.7; 44/55/1; p 0.315 | -10.6 (-14.0 to -7.3); median -8.6; 27/67/6; p <0.001 | -1.3 (-3.5 to +1.0); median +0.0; 42/48/10; p 0.598 |
| Clinical synopsis HPO F1, hierarchical ↑ | -0.5 (-2.4 to +1.8); median +0.0; 38/48/14; p 0.332 | +0.7 (-0.8 to +2.6); median +0.0; 44/36/20; p 0.434 | -7.9 (-12.3 to -3.4); median -5.0; 40/58/2; p 0.085 | -15.3 (-19.5 to -11.1); median -11.6; 23/72/5; p <0.001 | -1.7 (-4.1 to +1.0); median -0.7; 36/55/9; p 0.059 |
| OMIM allelic variants recovered ↑ | +0.0 (-4.2 to +4.6); median +0.0; 6/10/84; p 0.455 | +0.5 (-1.7 to +3.2); median +0.0; 4/3/93; p 1.000 | -50.5 (-58.9 to -42.0); median -50.0; 3/73/24; p <0.001 | -54.3 (-62.1 to -46.5); median -60.0; 0/75/25; p <0.001 | -2.1 (-6.3 to +2.3); median +0.0; 6/15/79; p 0.078 |
| Causal gene F1 ↑ | +2.7 (+0.0 to +6.0); median +0.0; 3/0/97; p 0.250 | +1.0 (+0.0 to +3.0); median +0.0; 1/0/99; p 1.000 | -11.7 (-19.3 to -4.3); median +0.0; 3/15/82; p 0.007 | -12.7 (-20.3 to -5.3); median +0.0; 2/15/83; p 0.002 | -2.3 (-8.0 to +2.7); median +0.0; 3/5/92; p 0.727 |
| Inheritance matches OMIM ↑ | +0.0 (-4.0 to +4.0); median +0.0; 2/2/96; p 1.000 | +0.0 (-3.0 to +3.0); median +0.0; 1/1/98; p 1.000 | -9.0 (-17.0 to -1.0); median +0.0; 4/13/83; p 0.049 | -18.0 (-27.0 to -10.0); median +0.0; 2/20/78; p <0.001 | -1.0 (-8.0 to +6.0); median +0.0; 6/7/87; p 1.000 |

## Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims audited | 10,556 | 9,390 | 9,051 | 2,624 | 2,448 | 10,964 |
| … supported | 10,232 | 9,069 | 8,802 | 1,343 | 2,308 | 10,510 |
| … partly supported | 324 | 321 | 248 | 687 | 140 | 454 |
| … unsupported | 0 | 0 | 1 | 576 | 0 | 0 |
| … contradicted | 0 | 0 | 0 | 18 | 0 | 0 |
| Claims audited before repair | 10,534 | 9,371 | 9,056 | 2,624 | 2,448 | 10,922 |
| … unsupported before repair | 16 | 17 | 10 | 576 | 13 | 24 |
| … contradicted before repair | 12 | 0 | 2 | 18 | 4 | 4 |
| OMIM facts scored | 5,333 | 5,324 | 5,363 | 5,272 | 5,256 | 5,346 |
| … conveyed | 2,252 | 2,296 | 2,302 | 540 | 529 | 2,151 |
| … partly conveyed | 873 | 902 | 879 | 895 | 652 | 857 |
| … missing | 2,177 | 2,093 | 2,150 | 3,801 | 4,053 | 2,306 |
| … contradicted | 31 | 33 | 32 | 36 | 22 | 32 |

## Allelic variants: precision and variants not in OMIM

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Variants generated | 360 | 295 | 300 | 40 | 28 | 384 |
| … matching an OMIM variant of the entry | 253 | 258 | 259 | 38 | 28 | 247 |
| … listed by OMIM only from a paper outside the entry's references | 1 | 1 | 1 | 1 | 0 | 1 |
| … not in OMIM | 106 | 36 | 40 | 1 | 0 | 136 |
| Pooled precision (entries where OMIM lists variants) | 70.3% | 87.5% | 86.3% | 95.0% | 100.0% | 64.3% |

## Inheritance errors by kind

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Entries with an OMIM mode of inheritance | 93 | 93 | 93 | 93 | 93 | 93 |
| … matched | 86 | 87 | 87 | 77 | 68 | 85 |
| … none stated | 3 | 2 | 3 | 13 | 22 | 2 |
| … a mode missing | 0 | 0 | 0 | 0 | 0 | 1 |
| … an extra mode | 3 | 4 | 3 | 1 | 1 | 4 |
| … a different mode | 1 | 0 | 0 | 2 | 2 | 1 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| fulltext | 79.0% (1,374) | 78.7% (1,377) | 77.5% (1,401) | 17.4% (1,373) | 17.0% (1,351) | 71.6% (1,380) |
| abstract | 42.2% (3,615) | 44.0% (3,603) | 43.7% (3,619) | 19.2% (3,565) | 17.1% (3,568) | 41.8% (3,627) |
| title | 22.7% (344) | 23.1% (344) | 22.0% (343) | 19.3% (334) | 4.9% (337) | 22.1% (339) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies. Facts are split from the gold paragraph separately for each draft, so the fact counts differ slightly.

| Paper readable as | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|
| fulltext | +0.3 (-2.2 to +2.5); n=40 | -1.2 (-2.8 to +0.4); n=40 | -61.3 (-68.3 to -54.5); n=40 | -61.8 (-69.5 to -54.1); n=40 | -7.1 (-10.0 to -4.3); n=40 |
| abstract | -1.8 (-3.3 to -0.4); n=85 | -0.3 (-1.1 to +0.5); n=85 | -24.8 (-28.5 to -20.8); n=85 | -26.9 (-30.4 to -23.4); n=85 | -2.1 (-3.4 to -0.8); n=85 |
| title | -0.4 (-3.0 to +1.5); n=21 | -1.1 (-3.2 to +1.0); n=21 | -3.8 (-10.7 to +4.2); n=21 | -18.2 (-22.4 to -13.4); n=21 | -1.0 (-3.8 to +1.4); n=21 |

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| no full text (abstracts only) | 46 | -0.7 (-1.8 to +0.3); n=46 | -0.8 (-2.3 to +0.5); n=46 | -17.9 (-23.0 to -12.8); n=46 | -19.2 (-22.9 to -15.5); n=46 | -0.1 (-1.4 to +1.0); n=46 |
| under half full text | 25 | +0.1 (-1.8 to +2.2); n=25 | +0.7 (-0.5 to +1.9); n=25 | -36.9 (-44.0 to -30.3); n=25 | -40.8 (-47.4 to -34.7); n=25 | -4.9 (-7.3 to -2.6); n=25 |
| half or more full text | 21 | -2.7 (-5.0 to -0.7); n=21 | -2.0 (-3.2 to -0.8); n=21 | -55.3 (-63.4 to -47.7); n=21 | -57.2 (-65.0 to -49.9); n=21 | -7.1 (-9.4 to -4.8); n=21 |
| all full text | 1 | +10.8 †; n=1 | -4.2 †; n=1 | -33.9 †; n=1 | -42.2 †; n=1 | +13.3 †; n=1 |

### OMIM allelic variants recovered

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| no full text (abstracts only) | 46 | +0.4 (-4.6 to +6.2); n=46 | -0.4 (-3.3 to +1.6); n=46 | -32.6 (-44.9 to -19.9); n=46 | -38.7 (-49.9 to -27.7); n=46 | -0.7 (-4.3 to +2.9); n=46 |
| under half full text | 25 | -1.9 (-4.1 to +0.0); n=25 | -0.1 (-2.0 to +1.7); n=25 | -64.2 (-76.5 to -51.3); n=25 | -66.0 (-78.2 to -52.8); n=25 | -6.4 (-13.5 to -1.1); n=25 |
| half or more full text | 21 | -1.0 (-2.6 to +0.0); n=21 | -1.6 (-4.8 to +0.0); n=21 | -79.5 (-91.8 to -65.3); n=21 | -79.9 (-92.0 to -65.8); n=21 | -2.2 (-5.2 to +0.0); n=21 |
| all full text | 1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 | +0.0 †; n=1 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 89.1% (23 facts, 1 entry) | 80.7% (192 facts, 10 entries) | 76.8% (415 facts, 11 entries) | 72.4% (398 facts, 10 entries) | 86.5% (349 facts, 8 entries) |
| abstract | 40.1% (884 facts, 18 entries) | 51.6% (568 facts, 19 entries) | 44.7% (899 facts, 18 entries) | 43.7% (728 facts, 15 entries) | 41.4% (524 facts, 15 entries) |
| title | 30.8% (39 facts, 3 entries) | 21.8% (55 facts, 4 entries) | 29.8% (52 facts, 4 entries) | 21.2% (73 facts, 5 entries) | 19.6% (125 facts, 5 entries) |

### Memory only (control)

| Paper readable as | classic (1xxxxx-5xxxxx) | 600000-609999 | 610000-615999 | 616000-619999 | 620000 onward |
|---|---|---|---|---|---|
| fulltext | 6.8% (22 facts, 1 entry) | 19.1% (189 facts, 10 entries) | 20.2% (430 facts, 11 entries) | 17.1% (391 facts, 10 entries) | 13.9% (341 facts, 8 entries) |
| abstract | 18.8% (875 facts, 18 entries) | 28.4% (570 facts, 19 entries) | 20.4% (884 facts, 18 entries) | 16.5% (720 facts, 15 entries) | 11.2% (516 facts, 15 entries) |
| title | 11.8% (38 facts, 3 entries) | 25.9% (54 facts, 4 entries) | 24.5% (53 facts, 4 entries) | 22.0% (75 facts, 5 entries) | 14.5% (114 facts, 5 entries) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 46 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.9% | 95.0% | 94.8% | 42.4% | 93.3% | 93.7% |
| … same, before the repair round ↓ | 0.4% | 0.4% | 0.2% | 24.3% | 0.8% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 39.5% | 40.1% | 39.3% | 22.2% | 20.9% | 40.0% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.4% | 0.8% | 0.5% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 30.4% | 29.9% | 30.0% | 31.7% | 24.2% | 29.9% |
| Clinical synopsis HPO F1, hierarchical ↑ | 49.2% | 50.0% | 50.3% | 51.1% | 40.8% | 49.1% |
| OMIM allelic variants recovered ↑ | 48.9% | 48.4% | 48.1% | 15.8% | 9.8% | 47.8% |
| Causal gene F1 ↑ | 96.4% | 94.9% | 94.9% | 89.1% | 87.0% | 87.7% |
| Inheritance matches OMIM ↑ | 89.1% | 91.3% | 91.3% | 89.1% | 71.7% | 87.0% |

### under half full text — 25 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.2% | 96.5% | 97.6% | 51.9% | 94.8% (n=24) | 95.3% |
| … same, before the repair round ↓ | 0.1% | 0.2% | 0.1% | 24.8% | 0.9% (n=24) | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.7% | 55.5% | 56.2% | 18.7% | 14.7% | 50.7% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.9% | 0.7% | 1.1% | 0.5% | 0.6% |
| Clinical synopsis HPO F1, exact ↑ | 37.2% | 40.6% | 39.6% | 29.5% | 24.0% | 36.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 59.4% | 61.5% | 61.1% | 44.5% | 37.0% | 58.7% |
| OMIM allelic variants recovered ↑ | 77.5% | 79.4% | 79.3% | 15.2% | 13.5% | 73.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 76.0% | 76.0% | 100.0% |
| Inheritance matches OMIM ↑ | 92.0% | 92.0% | 92.0% | 72.0% | 68.0% | 92.0% |

### half or more full text — 21 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.9% | 97.9% | 98.4% | 66.0% | 95.6% | 96.3% |
| … same, before the repair round ↓ | 0.3% | 0.0% | 0.1% | 17.8% | 0.1% | 0.2% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 70.5% | 73.2% | 71.2% | 17.9% | 16.1% | 66.1% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% | 0.4% | 0.4% | 0.2% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 39.9% | 42.0% | 41.5% | 30.6% | 28.3% | 38.6% |
| Clinical synopsis HPO F1, hierarchical ↑ | 60.6% | 62.0% | 62.1% | 47.7% | 44.9% | 56.8% |
| OMIM allelic variants recovered ↑ | 87.9% | 88.9% | 87.3% | 9.5% | 9.0% | 86.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 81.0% | 81.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 81.0% | 81.0% | 100.0% |

### all full text — 1 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 99.3% | 99.3% | 98.9% | 90.5% | 95.5% | 94.3% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 80.8% | 70.0% | 65.8% | 36.1% | 27.8% | 83.3% |
| OMIM per-paper facts contradicted ↓ | 15.4% | 0.0% | 5.3% | 0.0% | 0.0% | 16.7% |
| Clinical synopsis HPO F1, exact ↑ | 49.5% | 63.8% | 67.7% | 11.4% | 11.8% | 56.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 67.7% | 82.8% | 80.3% | 16.2% | 16.4% | 73.0% |
| OMIM allelic variants recovered ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## By size of the reference list

### 2-4 references — 51 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.3% | 96.1% | 96.4% | 52.0% | 93.9% (n=50) | 94.0% |
| … same, before the repair round ↓ | 0.2% | 0.2% | 0.1% | 23.3% | 0.3% (n=50) | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.6% | 53.6% | 52.4% | 20.8% | 18.9% | 50.3% |
| OMIM per-paper facts contradicted ↓ | 0.8% | 0.4% | 0.5% | 1.2% | 0.4% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 33.4% | 33.7% | 33.5% | 27.6% | 21.7% | 33.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 52.9% | 53.9% | 53.9% | 44.5% | 35.3% | 52.6% |
| OMIM allelic variants recovered ↑ | 64.6% | 66.1% | 64.9% | 14.8% | 12.9% | 64.2% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 76.5% | 76.5% | 94.1% |
| Inheritance matches OMIM ↑ | 94.1% | 98.0% | 96.1% | 78.4% | 70.6% | 94.1% |

### 5-8 references — 25 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.7% | 96.1% | 95.8% | 49.3% | 93.7% | 95.7% |
| … same, before the repair round ↓ | 0.2% | 0.4% | 0.1% | 21.2% | 0.9% | 0.3% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 48.9% | 49.0% | 48.9% | 20.9% | 18.0% | 46.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.4% | 0.4% | 0.4% | 0.5% | 0.4% |
| Clinical synopsis HPO F1, exact ↑ | 35.0% | 37.2% | 37.0% | 30.6% | 27.8% | 33.2% |
| Clinical synopsis HPO F1, hierarchical ↑ | 56.8% | 58.2% | 57.5% | 48.3% | 44.0% | 54.4% |
| OMIM allelic variants recovered ↑ | 67.0% | 64.8% | 65.4% | 17.2% | 11.7% | 60.3% |
| Causal gene F1 ↑ | 98.7% | 96.0% | 96.0% | 93.3% | 93.3% | 98.7% |
| Inheritance matches OMIM ↑ | 88.0% | 88.0% | 92.0% | 88.0% | 76.0% | 84.0% |

### 9 or more references — 17 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.8% | 96.1% | 97.2% | 49.6% | 96.1% | 95.3% |
| … same, before the repair round ↓ | 0.4% | 0.2% | 0.5% | 23.0% | 1.4% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 50.6% | 51.9% | 51.8% | 18.6% | 16.7% | 49.7% |
| OMIM per-paper facts contradicted ↓ | 0.6% | 0.9% | 0.8% | 0.2% | 0.5% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 37.5% | 40.8% | 39.7% | 39.7% | 30.4% | 37.5% |
| Clinical synopsis HPO F1, hierarchical ↑ | 57.1% | 59.9% | 60.9% | 59.2% | 50.6% | 55.9% |
| OMIM allelic variants recovered ↑ | 68.5% | 69.8% | 69.6% | 13.1% | 7.5% | 68.3% |
| Causal gene F1 ↑ | 92.2% | 92.2% | 92.2% | 92.2% | 86.3% | 86.3% |
| Inheritance matches OMIM ↑ | 94.1% | 88.2% | 88.2% | 88.2% | 76.5% | 94.1% |

## By creation era (MIM number range)

### 600000-609999 — 19 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.6% | 96.0% | 96.2% | 52.4% | 93.2% | 92.4% |
| … same, before the repair round ↓ | 0.1% | 0.5% | 0.1% | 19.9% | 0.4% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 56.1% | 55.7% | 55.4% | 29.1% | 24.8% | 52.8% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.3% | 0.3% | 0.9% | 0.4% | 0.3% |
| Clinical synopsis HPO F1, exact ↑ | 40.8% | 40.0% | 39.2% | 38.4% | 32.7% | 39.0% |
| Clinical synopsis HPO F1, hierarchical ↑ | 61.6% | 62.3% | 62.3% | 59.2% | 49.5% | 60.9% |
| OMIM allelic variants recovered ↑ | 68.7% | 72.2% | 71.4% | 27.8% | 17.5% | 66.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 94.7% | 94.7% | 89.5% |
| Inheritance matches OMIM ↑ | 79.0% | 89.5% | 84.2% | 94.7% | 73.7% | 89.5% |

### 610000-615999 — 20 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.0% | 95.6% | 96.0% | 53.5% | 94.6% | 94.3% |
| … same, before the repair round ↓ | 0.3% | 0.2% | 0.2% | 21.9% | 0.9% | 0.7% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 52.1% | 53.4% | 53.5% | 23.2% | 18.8% | 51.2% |
| OMIM per-paper facts contradicted ↓ | 1.2% | 0.6% | 0.8% | 0.5% | 0.4% | 1.3% |
| Clinical synopsis HPO F1, exact ↑ | 32.1% | 36.5% | 35.9% | 31.6% | 24.0% | 33.8% |
| Clinical synopsis HPO F1, hierarchical ↑ | 50.5% | 54.2% | 54.4% | 46.3% | 36.3% | 49.5% |
| OMIM allelic variants recovered ↑ | 70.7% | 72.7% | 73.4% | 18.5% | 13.1% | 70.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 95.0% | 95.0% | 95.0% | 100.0% | 100.0% | 100.0% |

### 616000-619999 — 19 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 96.8% | 97.0% | 59.0% | 94.7% | 95.5% |
| … same, before the repair round ↓ | 0.4% | 0.1% | 0.0% | 17.1% | 0.0% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.6% | 53.9% | 53.4% | 17.9% | 19.4% | 51.4% |
| OMIM per-paper facts contradicted ↓ | 0.7% | 0.8% | 0.8% | 2.2% | 0.6% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | 34.3% | 35.7% | 35.5% | 27.5% | 21.5% | 32.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 55.0% | 55.9% | 55.0% | 44.3% | 39.4% | 52.4% |
| OMIM allelic variants recovered ↑ | 81.2% | 80.1% | 79.4% | 12.7% | 12.7% | 77.5% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 89.5% | 89.5% | 100.0% |
| Inheritance matches OMIM ↑ | 94.7% | 94.7% | 94.7% | 84.2% | 68.4% | 89.5% |

### 620000 onward — 17 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.3% | 96.9% | 97.9% | 47.8% | 94.5% (n=16) | 96.6% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 27.7% | 0.0% (n=16) | 0.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 53.1% | 55.5% | 54.7% | 10.8% | 7.9% | 49.9% |
| OMIM per-paper facts contradicted ↓ | 0.5% | 0.1% | 0.1% | 0.3% | 0.2% | 0.1% |
| Clinical synopsis HPO F1, exact ↑ | 34.1% | 33.5% | 32.5% | 16.3% | 13.4% | 33.1% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.5% | 52.9% | 51.4% | 29.4% | 22.2% | 52.1% |
| OMIM allelic variants recovered ↑ | 61.2% | 64.8% | 61.9% | 8.2% | 8.2% | 64.1% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 41.2% | 41.2% | 94.1% |
| Inheritance matches OMIM ↑ | 100.0% | 100.0% | 100.0% | 41.2% | 41.2% | 94.1% |

### classic (1xxxxx-5xxxxx) — 18 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.5% | 95.3% | 95.1% | 40.4% | 94.2% | 95.0% |
| … same, before the repair round ↓ | 0.5% | 0.4% | 0.4% | 27.7% | 1.9% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 41.0% | 41.5% | 39.4% | 20.0% | 19.2% | 40.4% |
| OMIM per-paper facts contradicted ↓ | 0.3% | 0.5% | 0.5% | 0.1% | 0.6% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | 31.5% | 33.4% | 34.3% | 38.2% | 32.2% | 31.3% |
| Clinical synopsis HPO F1, hierarchical ↑ | 53.1% | 55.1% | 57.5% | 60.7% | 54.0% | 53.5% |
| OMIM allelic variants recovered ↑ | 46.2% | 40.6% | 41.3% | 7.1% | 5.6% | 39.5% |
| Causal gene F1 ↑ | 90.7% | 87.0% | 87.0% | 88.9% | 83.3% | 85.2% |
| Inheritance matches OMIM ↑ | 94.4% | 88.9% | 94.4% | 88.9% | 77.8% | 83.3% |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Recall, then verify | Case table first |
|---|---|---|---|---|---|---|
| Generation: model calls | 7.1 | 1.8 | 1.8 | 1.6 | 9.2 | 7.1 |
| Generation: list price | $0.56 | $0.26 | $0.28 | $0.07 | $0.70 | $0.61 |
| Generation: input / output tokens | 53,482 / 15,316 | 20,241 / 6,185 | 57,445 / 8,735 | 6,187 / 2,286 | 56,342 / 18,505 | 62,167 / 17,120 |
| Generation: model time (s) | 123 | 50 | 73 | 24 | 174 | 142 |
| Audit and repair: list price | $0.78 | $0.72 | $0.68 | $0.50 | $0.30 | $0.78 |
| Scoring against OMIM: list price | $0.20 | $0.20 | $0.19 | $0.15 | $0.14 | $0.20 |
| Everything: list price | $1.53 | $1.18 | $1.15 | $0.72 | $1.13 | $1.59 |

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
