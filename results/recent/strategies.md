# Generation strategies compared — run `recent`

20 entries, each written in full by every strategy from the same papers and put through the same audit and scoring. Means over entries; ↑ higher is better, ↓ lower is better. The primary endpoint is **OMIM facts conveyed**; the other headline measures are secondary.

No draft: 6 entries for which at least one strategy wrote nothing, because the model's safety filter stopped the writer's reply or the reply came back empty (Agentic curator 6; Direct reading 2). Entries: 621639, 621644, 621667, 621704, 621707, 621728. They are left out of the comparison with the incomplete entries listed under Completion.

## Completion

An entry is compared only when every strategy below completed it in full: its draft exists and no per-paper call was lost. 20 of the run's 30 entries qualify; left out: 301174, 621639, 621644, 621667, 621671, 621687, 621704, 621707, 621722, 621728. One-call strategies cannot be incomplete: a failed call there leaves no draft.

| Strategy | Complete | Incomplete (a per-paper call failed) | No draft |
|---|---|---|---|
| Evidence graph | 23 | 7: 621639 (1 paper), 621644 (1 paper), 621667 (1 paper), 621671 (1 paper), 621704 (1 paper), 621707 (1 paper), 621728 (1 paper) | 0 |
| Direct reading | 28 | 0 | 2: 621639, 621728 |
| Agentic curator | 24 | 0 | 6: 621639, 621644, 621667, 621704, 621707, 621728 |
| Memory only (control) | 30 | 0 | 0 |
| Case table first | 20 | 10: 301174 (1 paper), 621639 (1 paper), 621644 (1 paper), 621667 (1 paper), 621671 (1 paper), 621687 (1 paper), 621704 (1 paper), 621707 (1 paper), 621722 (1 paper), 621728 (1 paper) | 0 |

## How the scores are counted

- **OMIM facts conveyed** is scored against one fixed list of facts per OMIM paragraph, split without sight of any draft and shared by every strategy. The earlier scoring, which split the paragraph afresh for each draft, is shown as a secondary row.

- **Empty predictions count as zero.** Where a strategy predicted nothing (no causal gene, no synopsis term, no variant) and OMIM's gold set is not empty, F1 and recall count as 0 rather than leaving the entry out of the mean; precision stays undefined. This is applied when the evaluation files are read, for genes, the clinical synopsis (exact, hierarchical, semantic) and variants. Entries affected: Direct reading: variants 2; Agentic curator: variants 2; Memory only (control): genes 14, variants 19; Case table first: variants 1.

- **n.** A value rests on all 20 entries unless marked (n=k): some measures are undefined for some entries (OMIM lists no variants, no inheritance, or a draft made no auditable claim).

- **Variant precision** is the share of a draft's allelic variants that match one of OMIM's variants for the entry, over entries for which OMIM lists any. A variant OMIM documents only from a paper outside the entry's reference list counts as unmatched here and is shown apart below.

- **Inheritance errors** compare the modes stated with OMIM's (coarse modes): none stated; a mode missing (a strict subset of OMIM's); an extra mode (a strict superset); a different mode (anything else).

## The strategies

- **Evidence graph** (`kg`): Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph.
- **Direct reading** (`direct`): All papers in one prompt; the model writes the entry straight from the text.
- **Agentic curator** (`agent`): An autonomous agent reads and searches the papers with tools, then writes the entry.
- **Memory only (control)** (`closedbook`): Written from the model's memory with no papers; nothing is grounded. A control, not a method.
- **Case table first** (`cohort`): One structured record per reported patient or family, pooled into a case table; the entry is rendered from it.

## Scores

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 95.5% | 95.8% | 26.2% | 94.5% |
| Claims unsupported or contradicted ↓ | 0.0% | 0.0% | 0.0% | 35.8% | 0.0% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 35.8% | 0.4% |
| … unsupported, before the repair round ↓ | 0.0% | 0.0% | 0.1% | 35.3% | 0.4% |
| … contradicted, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 0.5% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.5% | 52.2% | 51.1% | 7.0% | 49.4% |
| … fully (no partial credit) ↑ | 44.8% | 45.4% | 44.4% | 3.5% | 42.6% |
| OMIM per-paper facts contradicted ↓ | 1.2% | 0.8% | 1.1% | 0.1% | 0.7% |
| … conveyed anywhere in the draft, not only where the paper is cited ↑ | – | – | – | – | – |
| … facts split afresh for each draft (earlier scoring) ↑ | 52.4% | 53.0% | 52.8% | 10.2% | 51.8% |
| Clinical synopsis HPO F1, exact ↑ | 62.1% (n=1) | 42.7% (n=1) | 25.3% (n=1) | 9.0% (n=1) | 60.7% (n=1) |
| … precision ↑ | 3.4% | 3.6% | 3.1% | 4.0% (n=19) | 3.1% |
| … recall ↑ | 57.1% (n=1) | 30.2% (n=1) | 15.9% (n=1) | 4.8% (n=1) | 58.7% (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | 78.7% (n=1) | 58.3% (n=1) | 50.8% (n=1) | 14.8% (n=1) | 76.4% (n=1) |
| Clinical synopsis HPO F1, semantic ↑ | 82.9% (n=1) | 69.0% (n=1) | 60.6% (n=1) | 31.3% (n=1) | 82.2% (n=1) |
| OMIM allelic variants recovered ↑ | 70.9% | 65.5% | 62.5% | 5.0% | 68.9% |
| Generated variants that are OMIM variants (precision) ↑ | 79.8% | 87.4% (n=18) | 88.0% (n=18) | 100.0% (n=1) | 83.3% (n=19) |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 30.0% | 100.0% |
| … recall ↑ | 100.0% | 100.0% | 100.0% | 30.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |
| Inheritance error: none stated ↓ | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) |
| Inheritance error: a mode missing ↓ | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) |
| Inheritance error: an extra mode ↓ | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) |
| Inheritance error: a different mode ↓ | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) | 0.0% (n=1) |
| OMIM references used ↑ | 99.6% | 98.6% | 99.6% | 10.0% | 99.6% |

## How much each strategy writes

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims audited per entry | 122.8 | 111.6 | 103.6 | 15.3 | 110.8 |
| Claims that could not be audited per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Clinical-synopsis HPO terms per entry | 21.1 | 14.3 | 12.8 | 3.6 | 22.7 |
| Allelic variants per entry | 3.4 | 3.0 | 2.8 | 0.1 | 3.2 |
| … of which not in OMIM | 0.7 | 0.7 | 0.6 | 0.0 | 0.7 |
| Papers cited per entry | 3.8 | 3.7 | 3.8 | 0.4 | 3.8 |
| Paragraphs dropped by the grounding guards per entry | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired differences from the baseline (Direct reading)

Percentage points, strategy minus baseline, with a bootstrap 95% interval over entries; then the number of entries on which the strategy scored better / worse / the same. The full statistics for every measure follow per strategy.

| Metric | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | +0.2 (-1.1 to +1.7); 10/10/0 | +0.2 (-1.1 to +1.6); 9/10/1 | -69.3 (-83.1 to -54.4); 0/20/0 | -1.1 (-3.1 to +1.1); 7/13/0 |
| … same, before the repair round ↓ | +0.1 (+0.0 to +0.2); 0/2/18 | +0.1 (+0.0 to +0.3); 0/2/18 | +35.8 (+21.6 to +51.0); 0/16/4 | +0.4 (+0.0 to +0.9); 0/4/16 |
| OMIM per-paper facts conveyed (primary) ↑ | -0.7 (-2.4 to +1.0); 5/11/4 | -1.1 (-1.8 to -0.3); 2/12/6 | -45.2 (-52.4 to -38.0); 0/20/0 | -2.8 (-5.4 to -0.7); 5/11/4 |
| OMIM per-paper facts contradicted ↓ | +0.3 (-0.3 to +1.0); 4/5/11 | +0.3 (-0.4 to +1.4); 3/2/15 | -0.8 (-1.3 to -0.3); 8/0/12 | -0.1 (-0.6 to +0.4); 5/2/13 |
| Clinical synopsis HPO F1, exact ↑ | +19.4; 1/0/0 (n=1) | -17.4; 0/1/0 (n=1) | -33.7; 0/1/0 (n=1) | +18.0; 1/0/0 (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | +20.4; 1/0/0 (n=1) | -7.5; 0/1/0 (n=1) | -43.5; 0/1/0 (n=1) | +18.1; 1/0/0 (n=1) |
| OMIM allelic variants recovered ↑ | +5.4 (-1.9 to +14.3); 4/1/15 | -3.1 (-7.8 to +0.0); 0/2/18 | -60.6 (-75.5 to -45.5); 0/17/3 | +3.3 (-3.3 to +11.7); 2/1/17 |
| Causal gene F1 ↑ | +0.0 (+0.0 to +0.0); 0/0/20 | +0.0 (+0.0 to +0.0); 0/0/20 | -70.0 (-90.0 to -50.0); 0/14/6 | +0.0 (+0.0 to +0.0); 0/0/20 |
| Inheritance matches OMIM ↑ | +0.0; 0/0/1 (n=1) | +0.0; 0/0/1 (n=1) | +0.0; 0/0/1 (n=1) | +0.0; 0/0/1 (n=1) |

### Full paired statistics

Mean and median paired difference (pp), bootstrap 95% interval, entries better / worse / tied, the exact two-sided sign test (ties dropped) and, for the headline measures other than the primary endpoint, the sign-test p-value after a Holm correction across those measures within the strategy. OMIM facts conveyed is the primary endpoint and is not adjusted. Rows below the headline measures are descriptive.

#### Evidence graph minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 20 | 51.5% | 52.2% | -0.7 | -2.4 to +1.0 | -0.5 | 5 / 11 / 4 | 0.210 | – |
| Claims supported by cited paper (headline) ↑ | 20 | 95.7% | 95.5% | +0.2 | -1.1 to +1.7 | +0.1 | 10 / 10 / 0 | 1.000 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 20 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 2 / 18 | 0.500 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 20 | 1.2% | 0.8% | +0.3 | -0.3 to +1.0 | +0.0 | 4 / 5 / 11 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 1 | 62.1% | 42.7% | +19.4 | – | +19.4 | 1 / 0 / 0 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 1 | 78.7% | 58.3% | +20.4 | – | +20.4 | 1 / 0 / 0 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 20 | 70.9% | 65.5% | +5.4 | -1.9 to +14.3 | +0.0 | 4 / 1 / 15 | 0.375 | 1.000 |
| Causal gene F1 (headline) ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance matches OMIM (headline) ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Claims unsupported, before the repair round ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Claims contradicted, before the repair round ↓ | 20 | 0.1% | 0.0% | +0.1 | +0.0 to +0.2 | +0.0 | 0 / 2 / 18 | 0.500 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 20 | 44.8% | 45.4% | -0.6 | -2.8 to +1.8 | -1.5 | 5 / 11 / 4 | 0.210 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 20 | 52.4% | 53.0% | -0.5 | -2.3 to +1.3 | -1.5 | 8 / 12 / 0 | 0.503 | – |
| Clinical synopsis HPO precision, exact ↑ | 20 | 3.4% | 3.6% | -0.3 | -0.8 to +0.0 | +0.0 | 0 / 1 / 19 | 1.000 | – |
| Clinical synopsis HPO recall, exact ↑ | 1 | 57.1% | 30.2% | +26.9 | – | +26.9 | 1 / 0 / 0 | 1.000 | – |
| Clinical synopsis HPO F1, semantic ↑ | 1 | 82.9% | 69.0% | +13.9 | – | +13.9 | 1 / 0 / 0 | 1.000 | – |
| Generated variants that are OMIM variants (precision) ↑ | 18 | 88.7% | 87.4% | +1.3 | -1.8 to +5.0 | +0.0 | 3 / 1 / 14 | 0.625 | – |
| Causal gene recall ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance error: none stated ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a mode missing ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: an extra mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a different mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| OMIM references used ↑ | 20 | 99.6% | 98.6% | +1.0 | +0.0 to +3.0 | +0.0 | 1 / 0 / 19 | 1.000 | – |

#### Agentic curator minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 20 | 51.1% | 52.2% | -1.1 | -1.8 to -0.3 | -0.9 | 2 / 12 / 6 | 0.013 | – |
| Claims supported by cited paper (headline) ↑ | 20 | 95.8% | 95.5% | +0.2 | -1.1 to +1.6 | -0.4 | 9 / 10 / 1 | 1.000 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 20 | 0.1% | 0.0% | +0.1 | +0.0 to +0.3 | +0.0 | 0 / 2 / 18 | 0.500 | 1.000 |
| OMIM per-paper facts contradicted (headline) ↓ | 20 | 1.1% | 0.8% | +0.3 | -0.4 to +1.4 | +0.0 | 3 / 2 / 15 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 1 | 25.3% | 42.7% | -17.4 | – | -17.4 | 0 / 1 / 0 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 1 | 50.8% | 58.3% | -7.5 | – | -7.5 | 0 / 1 / 0 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 20 | 62.5% | 65.5% | -3.1 | -7.8 to +0.0 | +0.0 | 0 / 2 / 18 | 0.500 | 1.000 |
| Causal gene F1 (headline) ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance matches OMIM (headline) ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.1 | +0.0 | 0 / 1 / 19 | 1.000 | – |
| Claims unsupported, before the repair round ↓ | 20 | 0.1% | 0.0% | +0.1 | +0.0 to +0.3 | +0.0 | 0 / 2 / 18 | 0.500 | – |
| Claims contradicted, before the repair round ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 20 | 44.4% | 45.4% | -1.0 | -2.3 to +0.3 | +0.0 | 3 / 9 / 8 | 0.146 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 20 | 52.8% | 53.0% | -0.2 | -1.1 to +0.8 | -0.4 | 7 / 12 / 1 | 0.359 | – |
| Clinical synopsis HPO precision, exact ↑ | 20 | 3.1% | 3.6% | -0.5 | -1.6 to +0.0 | +0.0 | 0 / 1 / 19 | 1.000 | – |
| Clinical synopsis HPO recall, exact ↑ | 1 | 15.9% | 30.2% | -14.3 | – | -14.3 | 0 / 1 / 0 | 1.000 | – |
| Clinical synopsis HPO F1, semantic ↑ | 1 | 60.6% | 69.0% | -8.4 | – | -8.4 | 0 / 1 / 0 | 1.000 | – |
| Generated variants that are OMIM variants (precision) ↑ | 18 | 88.0% | 87.4% | +0.5 | +0.0 to +1.6 | +0.0 | 1 / 0 / 17 | 1.000 | – |
| Causal gene recall ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance error: none stated ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a mode missing ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: an extra mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a different mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| OMIM references used ↑ | 20 | 99.6% | 98.6% | +1.0 | +0.0 to +3.0 | +0.0 | 1 / 0 / 19 | 1.000 | – |

#### Memory only (control) minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 20 | 7.0% | 52.2% | -45.2 | -52.4 to -38.0 | -45.0 | 0 / 20 / 0 | <0.001 | – |
| Claims supported by cited paper (headline) ↑ | 20 | 26.2% | 95.5% | -69.3 | -83.1 to -54.4 | -88.5 | 0 / 20 / 0 | <0.001 | <0.001 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 20 | 35.8% | 0.0% | +35.8 | +21.6 to +51.0 | +33.3 | 0 / 16 / 4 | <0.001 | <0.001 |
| OMIM per-paper facts contradicted (headline) ↓ | 20 | 0.1% | 0.8% | -0.8 | -1.3 to -0.3 | +0.0 | 8 / 0 / 12 | 0.008 | 0.023 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 1 | 9.0% | 42.7% | -33.7 | – | -33.7 | 0 / 1 / 0 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 1 | 14.8% | 58.3% | -43.5 | – | -43.5 | 0 / 1 / 0 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 20 | 5.0% | 65.5% | -60.6 | -75.5 to -45.5 | -69.0 | 0 / 17 / 3 | <0.001 | <0.001 |
| Causal gene F1 (headline) ↑ | 20 | 30.0% | 100.0% | -70.0 | -90.0 to -50.0 | -100.0 | 0 / 14 / 6 | <0.001 | <0.001 |
| Inheritance matches OMIM (headline) ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Claims unsupported or contradicted ↓ | 20 | 35.8% | 0.0% | +35.8 | +21.4 to +51.4 | +33.3 | 0 / 16 / 4 | <0.001 | – |
| Claims unsupported, before the repair round ↓ | 20 | 35.3% | 0.0% | +35.3 | +20.8 to +50.9 | +33.3 | 0 / 15 / 5 | <0.001 | – |
| Claims contradicted, before the repair round ↓ | 20 | 0.5% | 0.0% | +0.5 | +0.0 to +1.5 | +0.0 | 0 / 1 / 19 | 1.000 | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 20 | 3.5% | 45.4% | -41.9 | -50.2 to -34.1 | -40.4 | 0 / 20 / 0 | <0.001 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 20 | 10.2% | 53.0% | -42.8 | -49.4 to -36.8 | -40.0 | 0 / 20 / 0 | <0.001 | – |
| Clinical synopsis HPO precision, exact ↑ | 19 | 4.0% | 3.9% | +0.1 | +0.0 to +0.3 | +0.0 | 1 / 0 / 18 | 1.000 | – |
| Clinical synopsis HPO recall, exact ↑ | 1 | 4.8% | 30.2% | -25.4 | – | -25.4 | 0 / 1 / 0 | 1.000 | – |
| Clinical synopsis HPO F1, semantic ↑ | 1 | 31.3% | 69.0% | -37.7 | – | -37.7 | 0 / 1 / 0 | 1.000 | – |
| Generated variants that are OMIM variants (precision) ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Causal gene recall ↑ | 20 | 30.0% | 100.0% | -70.0 | -90.0 to -50.0 | -100.0 | 0 / 14 / 6 | <0.001 | – |
| Inheritance error: none stated ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a mode missing ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: an extra mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a different mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| OMIM references used ↑ | 20 | 10.0% | 98.6% | -88.6 | -96.8 to -77.3 | -100.0 | 0 / 19 / 1 | <0.001 | – |

#### Case table first minus Direct reading

| Metric | n | Strategy | Baseline | Mean diff | 95% CI | Median diff | Better / worse / tie | Sign test p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| OMIM per-paper facts conveyed **(primary)** ↑ | 20 | 49.4% | 52.2% | -2.8 | -5.4 to -0.7 | -1.0 | 5 / 11 / 4 | 0.210 | – |
| Claims supported by cited paper (headline) ↑ | 20 | 94.5% | 95.5% | -1.1 | -3.1 to +1.1 | -1.6 | 7 / 13 / 0 | 0.263 | 1.000 |
| Claims unsupported or contradicted, before the repair round (headline) ↓ | 20 | 0.4% | 0.0% | +0.4 | +0.0 to +0.9 | +0.0 | 0 / 4 / 16 | 0.125 | 0.750 |
| OMIM per-paper facts contradicted (headline) ↓ | 20 | 0.7% | 0.8% | -0.1 | -0.6 to +0.4 | +0.0 | 5 / 2 / 13 | 0.453 | 1.000 |
| Clinical synopsis HPO F1, exact (headline) ↑ | 1 | 60.7% | 42.7% | +18.0 | – | +18.0 | 1 / 0 / 0 | 1.000 | 1.000 |
| Clinical synopsis HPO F1, hierarchical (headline) ↑ | 1 | 76.4% | 58.3% | +18.1 | – | +18.1 | 1 / 0 / 0 | 1.000 | 1.000 |
| OMIM allelic variants recovered (headline) ↑ | 20 | 68.9% | 65.5% | +3.3 | -3.3 to +11.7 | +0.0 | 2 / 1 / 17 | 1.000 | 1.000 |
| Causal gene F1 (headline) ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance matches OMIM (headline) ↑ | 1 | 100.0% | 100.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Claims unsupported or contradicted ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Claims unsupported, before the repair round ↓ | 20 | 0.4% | 0.0% | +0.4 | +0.1 to +0.9 | +0.0 | 0 / 4 / 16 | 0.125 | – |
| Claims contradicted, before the repair round ↓ | 20 | 0.0% | 0.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| OMIM per-paper facts conveyed fully (no partial credit) ↑ | 20 | 42.6% | 45.4% | -2.8 | -5.5 to -0.6 | -0.4 | 4 / 10 / 6 | 0.180 | – |
| OMIM per-paper facts contradicted: facts split afresh for each draft (earlier scoring) ↑ | 20 | 51.8% | 53.0% | -1.2 | -2.9 to +0.4 | -0.8 | 7 / 11 / 2 | 0.481 | – |
| Clinical synopsis HPO precision, exact ↑ | 20 | 3.1% | 3.6% | -0.5 | -1.6 to +0.0 | +0.0 | 0 / 1 / 19 | 1.000 | – |
| Clinical synopsis HPO recall, exact ↑ | 1 | 58.7% | 30.2% | +28.5 | – | +28.5 | 1 / 0 / 0 | 1.000 | – |
| Clinical synopsis HPO F1, semantic ↑ | 1 | 82.2% | 69.0% | +13.2 | – | +13.2 | 1 / 0 / 0 | 1.000 | – |
| Generated variants that are OMIM variants (precision) ↑ | 18 | 87.9% | 87.4% | +0.5 | -2.8 to +4.2 | +0.0 | 1 / 1 / 16 | 1.000 | – |
| Causal gene recall ↑ | 20 | 100.0% | 100.0% | +0.0 | +0.0 to +0.0 | +0.0 | 0 / 0 / 20 | – | – |
| Inheritance error: none stated ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a mode missing ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: an extra mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| Inheritance error: a different mode ↓ | 1 | 0.0% | 0.0% | +0.0 | – | +0.0 | 0 / 0 / 1 | – | – |
| OMIM references used ↑ | 20 | 99.6% | 98.6% | +1.0 | +0.0 to +3.0 | +0.0 | 1 / 0 / 19 | 1.000 | – |

## Sensitivity: every entry, a missing draft counted as zero (intention to treat)

All 30 entries of the run. A strategy's missing draft scores 0 on each higher-is-better measure the entry has a gold set for; incomplete drafts are kept as scored. Lower-is-better measures cannot be zero-filled (a missing draft has no errors) and are averaged over the drafts that exist. Missing drafts counted as zero: Direct reading 2; Agentic curator 6.

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.4% | 88.9% | 77.1% | 32.1% (n=29) | 94.9% |
| … same, before the repair round ↓ | 0.9% | 0.0% (n=28) | 0.1% (n=24) | 34.0% (n=29) | 1.1% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 46.1% | 50.9% | 43.6% | 5.9% | 39.8% |
| OMIM per-paper facts contradicted ↓ | 1.5% | 1.5% (n=28) | 1.1% (n=24) | 0.0% | 1.1% |
| Clinical synopsis HPO F1, exact ↑ | 62.1% (n=1) | 42.7% (n=1) | 25.3% (n=1) | 9.0% (n=1) | 60.7% (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | 78.7% (n=1) | 58.3% (n=1) | 50.8% (n=1) | 14.8% (n=1) | 76.4% (n=1) |
| OMIM allelic variants recovered ↑ | 66.5% | 62.9% | 52.5% | 3.3% | 57.1% |
| Causal gene F1 ↑ | 93.3% | 93.3% | 80.0% | 23.3% | 96.7% |
| Inheritance matches OMIM ↑ | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |

Paired differences from Direct reading over all entries (mean, interval, median, better/worse/tie, sign test):

| Metric | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|
| Claims supported by cited paper ↑ | +7.5 (+0.1 to +17.5); median +0.2; 16/14/0; p 0.856 | -11.8 (-23.9 to -2.2); median -0.2; 12/15/3; p 0.701 | -56.4 (-71.8 to -39.3); median -75.0; 2/26/1; p <0.001 (n=29) | +6.1 (-1.2 to +15.8); median -0.9; 12/18/0; p 0.362 |
| … same, before the repair round ↓ | +0.7 (+0.0 to +1.8); median +0.0; 0/4/24; p 0.125 (n=28) | +0.1 (-0.1 to +0.2); median +0.0; 1/3/20; p 0.625 (n=24) | +32.8 (+20.7 to +45.7); median +19.0; 1/22/4; p <0.001 (n=27) | +0.6 (+0.1 to +1.3); median +0.0; 0/6/22; p 0.031 (n=28) |
| OMIM per-paper facts conveyed (primary) ↑ | -4.8 (-12.8 to +2.3); median -0.5; 8/16/6; p 0.152 | -7.3 (-14.8 to -1.4); median -0.9; 5/16/9; p 0.027 | -45.0 (-52.4 to -37.4); median -46.1; 1/28/1; p <0.001 | -11.1 (-19.9 to -3.0); median -1.4; 6/18/6; p 0.023 |
| OMIM per-paper facts contradicted ↓ | +0.1 (-0.4 to +0.7); median +0.0; 6/5/17; p 1.000 (n=28) | +0.1 (-0.5 to +1.1); median +0.0; 4/3/17; p 1.000 (n=24) | -1.4 (-2.9 to -0.5); median +0.0; 13/0/15; p <0.001 (n=28) | -0.3 (-0.7 to +0.2); median +0.0; 8/2/18; p 0.109 (n=28) |
| Clinical synopsis HPO F1, exact ↑ | +19.4; median +19.4; 1/0/0; p 1.000 (n=1) | -17.4; median -17.4; 0/1/0; p 1.000 (n=1) | -33.7; median -33.7; 0/1/0; p 1.000 (n=1) | +18.0; median +18.0; 1/0/0; p 1.000 (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | +20.4; median +20.4; 1/0/0; p 1.000 (n=1) | -7.5; median -7.5; 0/1/0; p 1.000 (n=1) | -43.5; median -43.5; 0/1/0; p 1.000 (n=1) | +18.1; median +18.1; 1/0/0; p 1.000 (n=1) |
| OMIM allelic variants recovered ↑ | +3.6 (-8.6 to +15.4); median +0.0; 8/3/19; p 0.227 | -10.4 (-21.2 to -1.5); median +0.0; 1/5/24; p 0.219 | -59.5 (-72.4 to -46.6); median -69.0; 0/24/6; p <0.001 | -5.7 (-18.5 to +7.2); median +0.0; 3/7/20; p 0.344 |
| Causal gene F1 ↑ | +0.0 (-10.0 to +10.0); median +0.0; 1/1/28; p 1.000 | -13.3 (-26.7 to -3.3); median +0.0; 0/4/26; p 0.125 | -70.0 (-86.7 to -53.3); median -100.0; 0/21/9; p <0.001 | +3.3 (+0.0 to +10.0); median +0.0; 1/0/29; p 1.000 |
| Inheritance matches OMIM ↑ | +0.0; median +0.0; 0/0/1; p – (n=1) | +0.0; median +0.0; 0/0/1; p – (n=1) | +0.0; median +0.0; 0/0/1; p – (n=1) | +0.0; median +0.0; 0/0/1; p – (n=1) |

## Pooled counts

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims audited | 2,455 | 2,232 | 2,072 | 307 | 2,216 |
| … supported | 2,367 | 2,158 | 2,002 | 147 | 2,098 |
| … partly supported | 88 | 74 | 69 | 92 | 118 |
| … unsupported | 0 | 0 | 1 | 65 | 0 |
| … contradicted | 0 | 0 | 0 | 3 | 0 |
| Claims audited before repair | 2,446 | 2,232 | 2,070 | 307 | 2,202 |
| … unsupported before repair | 0 | 0 | 3 | 65 | 7 |
| … contradicted before repair | 2 | 0 | 0 | 3 | 0 |
| OMIM facts scored | 1,407 | 1,407 | 1,407 | 1,407 | 1,407 |
| … conveyed | 605 | 607 | 594 | 49 | 584 |
| … partly conveyed | 199 | 200 | 194 | 111 | 192 |
| … missing | 590 | 588 | 607 | 1,246 | 623 |
| … contradicted | 13 | 12 | 12 | 1 | 8 |

## Allelic variants: precision and variants not in OMIM

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Variants generated | 68 | 60 | 56 | 1 | 65 |
| … matching an OMIM variant of the entry | 54 | 47 | 44 | 1 | 51 |
| … listed by OMIM only from a paper outside the entry's references | 0 | 0 | 0 | 0 | 0 |
| … not in OMIM | 14 | 13 | 12 | 0 | 14 |
| Pooled precision (entries where OMIM lists variants) | 79.4% | 78.3% | 78.6% | 100.0% | 78.5% |

## Inheritance errors by kind

| | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Entries with an OMIM mode of inheritance | 1 | 1 | 1 | 1 | 1 |
| … matched | 1 | 1 | 1 | 1 | 1 |
| … none stated | 0 | 0 | 0 | 0 | 0 |
| … a mode missing | 0 | 0 | 0 | 0 | 0 |
| … an extra mode | 0 | 0 | 0 | 0 | 0 |
| … a different mode | 0 | 0 | 0 | 0 | 0 |

## OMIM-fact coverage by how much of the paper was readable

Pooled over facts. Each cell: coverage, then the number of facts scored.

| Paper readable as | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| fulltext | 86.0% (328) | 83.4% (328) | 82.2% (328) | 10.5% (328) | 81.1% (328) |
| abstract | 39.5% (1,018) | 40.2% (1,018) | 39.1% (1,018) | 6.9% (1,018) | 39.1% (1,018) |
| title | 33.6% (61) | 39.3% (61) | 39.3% (61) | 0.0% (61) | 26.2% (61) |

### Difference from Direct reading, by how the paper was readable

Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together); n is the number of entries with facts at that level for both strategies.

| Paper readable as | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|
| fulltext | +2.6 (-0.4 to +5.5) †; n=11 | -1.2 (-3.4 to +1.5) †; n=11 | -72.9 (-81.4 to -66.1) †; n=11 | -2.3 (-6.1 to +0.7) †; n=11 |
| abstract | -0.7 (-2.8 to +1.0) †; n=16 | -1.2 (-1.8 to -0.5) †; n=16 | -33.4 (-39.8 to -27.4) †; n=16 | -1.1 (-3.7 to +0.7) †; n=16 |
| title | -5.7; n=3 | +0.0; n=3 | -39.3; n=3 | -13.1; n=3 |

† fewer than 20 entries: the interval is unreliable.

## Paired differences from Direct reading within each access stratum

Entries grouped by the share of their references readable as full text (as in the breakdown below); within each group, the paired difference from the baseline in percentage points with its bootstrap 95% interval and the number of entries. † fewer than 20 entries: the interval is unreliable; no interval is computed below 5 entries.

### OMIM facts conveyed

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| no full text (abstracts only) | 6 | +0.4 (-1.9 to +3.0) †; n=6 | -1.2 (-2.0 to -0.4) †; n=6 | -35.2 (-44.6 to -27.8) †; n=6 | -0.1 (-0.5 to +0.3) †; n=6 |
| under half full text | 7 | -2.1 (-5.3 to +0.4) †; n=7 | -0.3 (-1.3 to +0.8) †; n=7 | -41.1 (-49.7 to -30.6) †; n=7 | -4.4 (-10.6 to +0.2) †; n=7 |
| half or more full text | 5 | -1.6 (-3.9 to +0.4) †; n=5 | -1.6 (-3.4 to +0.1) †; n=5 | -53.5 (-70.0 to -37.4) †; n=5 | -4.0 (-6.9 to -1.1) †; n=5 |
| all full text | 2 | +3.5 †; n=2 | -2.2 †; n=2 | -68.2 †; n=2 | -2.1 †; n=2 |

### OMIM allelic variants recovered

| Access group | Entries | Evidence graph | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| no full text (abstracts only) | 6 | +15.9 (+0.0 to +38.1) †; n=6 | +0.0 (+0.0 to +0.0) †; n=6 | -35.3 (-63.9 to -10.3) †; n=6 | +11.1 (+0.0 to +33.4) †; n=6 |
| under half full text | 7 | +1.8 (-12.5 to +14.9) †; n=7 | -8.8 (-19.0 to +0.0) †; n=7 | -57.5 (-76.5 to -34.7) †; n=7 | +0.0 (-14.3 to +14.3) †; n=7 |
| half or more full text | 5 | +0.0 (+0.0 to +0.0) †; n=5 | +0.0 (+0.0 to +0.0) †; n=5 | -82.7 (-100.0 to -56.0) †; n=5 | +0.0 (+0.0 to +0.0) †; n=5 |
| all full text | 2 | +0.0 †; n=2 | +0.0 †; n=2 | -91.6 †; n=2 | +0.0 †; n=2 |

## OMIM facts conveyed by creation era within each level of paper access

Pooled over facts; each cell: coverage, then facts scored and entries contributing. The era is the MIM-number range of the entry; the level is how much of the paper the fact summarises was readable.

### Direct reading

| Paper readable as | 620000 onward |
|---|---|
| fulltext | 83.4% (328 facts, 11 entries) |
| abstract | 40.2% (1,018 facts, 16 entries) |
| title | 39.3% (61 facts, 3 entries) |

### Memory only (control)

| Paper readable as | 620000 onward |
|---|---|
| fulltext | 10.5% (328 facts, 11 entries) |
| abstract | 6.9% (1,018 facts, 16 entries) |
| title | 0.0% (61 facts, 3 entries) |

## By share of the entry's references readable as full text

### no full text (abstracts only) — 6 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 93.5% | 92.6% | 94.4% | 3.7% | 93.6% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 52.2% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 38.4% | 38.0% | 36.8% | 2.7% | 37.9% |
| OMIM per-paper facts contradicted ↓ | 0.4% | 0.1% | 0.5% | 0.0% | 0.0% |
| Clinical synopsis HPO F1, exact ↑ | – | – | – | – | – |
| Clinical synopsis HPO F1, hierarchical ↑ | – | – | – | – | – |
| OMIM allelic variants recovered ↑ | 51.2% | 35.3% | 35.3% | 0.0% | 46.4% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| Inheritance matches OMIM ↑ | – | – | – | – | – |

### under half full text — 7 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.0% | 96.4% | 96.5% | 16.6% | 94.7% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.3% | 26.6% | 0.8% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 47.4% | 49.6% | 49.3% | 8.4% | 45.1% |
| OMIM per-paper facts contradicted ↓ | 1.4% | 1.1% | 0.9% | 0.0% | 1.0% |
| Clinical synopsis HPO F1, exact ↑ | – | – | – | – | – |
| Clinical synopsis HPO F1, hierarchical ↑ | – | – | – | – | – |
| OMIM allelic variants recovered ↑ | 73.6% | 71.8% | 62.9% | 14.3% | 71.8% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 28.6% | 100.0% |
| Inheritance matches OMIM ↑ | – | – | – | – | – |

### half or more full text — 5 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.3% | 96.4% | 95.4% | 42.4% | 94.8% |
| … same, before the repair round ↓ | 0.2% | 0.0% | 0.0% | 42.5% | 0.5% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 60.2% | 61.7% | 60.2% | 8.2% | 57.7% |
| OMIM per-paper facts contradicted ↓ | 1.6% | 0.8% | 2.2% | 0.2% | 0.9% |
| Clinical synopsis HPO F1, exact ↑ | – | – | – | – | – |
| Clinical synopsis HPO F1, hierarchical ↑ | – | – | – | – | – |
| OMIM allelic variants recovered ↑ | 82.7% | 82.7% | 82.7% | 0.0% | 82.7% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 40.0% | 100.0% |
| Inheritance matches OMIM ↑ | – | – | – | – | – |

### all full text — 2 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 97.1% | 99.0% | 98.2% | 87.4% | 95.5% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.0% | 2.1% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 83.5% | 80.0% | 77.8% | 11.8% | 77.9% |
| OMIM per-paper facts contradicted ↓ | 1.4% | 2.1% | 1.4% | 0.0% | 1.4% |
| Clinical synopsis HPO F1, exact ↑ | 62.1% (n=1) | 42.7% (n=1) | 25.3% (n=1) | 9.0% (n=1) | 60.7% (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | 78.7% (n=1) | 58.3% (n=1) | 50.8% (n=1) | 14.8% (n=1) | 76.4% (n=1) |
| OMIM allelic variants recovered ↑ | 91.6% | 91.6% | 91.6% | 0.0% | 91.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |

## By size of the reference list

### 2-4 references — 14 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.9% | 95.3% | 95.8% | 30.4% | 95.4% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 39.3% | 0.3% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 55.0% | 55.5% | 54.1% | 5.9% | 52.2% |
| OMIM per-paper facts contradicted ↓ | 1.2% | 0.8% | 1.4% | 0.1% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | 62.1% (n=1) | 42.7% (n=1) | 25.3% (n=1) | 9.0% (n=1) | 60.7% (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | 78.7% (n=1) | 58.3% (n=1) | 50.8% (n=1) | 14.8% (n=1) | 76.4% (n=1) |
| OMIM allelic variants recovered ↑ | 70.3% | 68.0% | 65.6% | 0.0% | 70.3% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 28.6% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |

### 5-8 references — 5 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.0% | 95.8% | 95.0% | 14.9% | 91.8% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.0% | 26.4% | 0.9% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 45.7% | 47.0% | 46.6% | 8.2% | 44.5% |
| OMIM per-paper facts contradicted ↓ | 1.3% | 0.9% | 0.7% | 0.0% | 0.5% |
| Clinical synopsis HPO F1, exact ↑ | – | – | – | – | – |
| Clinical synopsis HPO F1, hierarchical ↑ | – | – | – | – | – |
| OMIM allelic variants recovered ↑ | 74.3% | 61.9% | 56.2% | 20.0% | 68.6% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 20.0% | 100.0% |
| Inheritance matches OMIM ↑ | – | – | – | – | – |

### 9 or more references — 1 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 96.2% | 96.8% | 98.9% | 25.0% | 94.8% |
| … same, before the repair round ↓ | 0.0% | 0.0% | 0.4% | 33.3% | 0.0% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 31.3% | 31.3% | 31.3% | 16.7% | 34.6% |
| OMIM per-paper facts contradicted ↓ | 0.0% | 0.0% | 0.0% | 0.0% | 0.8% |
| Clinical synopsis HPO F1, exact ↑ | – | – | – | – | – |
| Clinical synopsis HPO F1, hierarchical ↑ | – | – | – | – | – |
| OMIM allelic variants recovered ↑ | 62.5% | 50.0% | 50.0% | 0.0% | 50.0% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Inheritance matches OMIM ↑ | – | – | – | – | – |

## By creation era (MIM number range)

### 620000 onward — 20 entries

| Metric | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Claims supported by cited paper ↑ | 95.7% | 95.5% | 95.8% | 26.2% | 94.5% |
| … same, before the repair round ↓ | 0.1% | 0.0% | 0.1% | 35.8% | 0.4% |
| OMIM per-paper facts conveyed (primary endpoint) ↑ | 51.5% | 52.2% | 51.1% | 7.0% | 49.4% |
| OMIM per-paper facts contradicted ↓ | 1.2% | 0.8% | 1.1% | 0.1% | 0.7% |
| Clinical synopsis HPO F1, exact ↑ | 62.1% (n=1) | 42.7% (n=1) | 25.3% (n=1) | 9.0% (n=1) | 60.7% (n=1) |
| Clinical synopsis HPO F1, hierarchical ↑ | 78.7% (n=1) | 58.3% (n=1) | 50.8% (n=1) | 14.8% (n=1) | 76.4% (n=1) |
| OMIM allelic variants recovered ↑ | 70.9% | 65.5% | 62.5% | 5.0% | 68.9% |
| Causal gene F1 ↑ | 100.0% | 100.0% | 100.0% | 30.0% | 100.0% |
| Inheritance matches OMIM ↑ | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |

## What each strategy costs to run

Per entry, from scratch, at API list prices (a measure of consumption; these runs used a Claude subscription). Generation is the strategy itself; the audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.

| Per entry | Evidence graph | Direct reading | Agentic curator | Memory only (control) | Case table first |
|---|---|---|---|---|---|
| Generation: model calls | 5.7 | 1.9 | 1.9 | 1.6 | 5.7 |
| Generation: list price | $0.60 | $0.32 | $0.34 | $0.05 | $0.66 |
| Generation: input / output tokens | 50,993 / 16,281 | 26,183 / 6,733 | 75,964 / 9,602 | 5,999 / 1,449 | 61,882 / 18,274 |
| Generation: model time (s) | 133 | 57 | 81 | 19 | 148 |
| Audit and repair: list price | $0.84 | $0.78 | $0.76 | $0.39 | $0.79 |
| Scoring against OMIM: list price | $0.39 | $0.38 | $0.38 | $0.27 | $0.38 |
| Everything: list price | $1.83 | $1.47 | $1.48 | $0.71 | $1.83 |

## Knowledge-graph edges against OMIM (all entries pooled)

Each generated entry is reduced to its edges and set against the same edges in OMIM. Precision is the share of generated edges that OMIM also has; recall is the share of OMIM's edges that were generated. A generated edge absent from OMIM is not necessarily wrong: it is one OMIM does not record.

| Edge type | Strategy | In both | Generated | In OMIM | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Disease → causal gene | Evidence graph | 28 | 28 | 30 | 100.0% | 93.3% | 96.5% |
| Disease → causal gene | Direct reading | 28 | 28 | 30 | 100.0% | 93.3% | 96.5% |
| Disease → causal gene | Agentic curator | 24 | 24 | 30 | 100.0% | 80.0% | 88.9% |
| Disease → causal gene | Memory only (control) | 7 | 7 | 30 | 100.0% | 23.3% | 37.8% |
| Disease → causal gene | Case table first | 29 | 29 | 30 | 100.0% | 96.7% | 98.3% |
| Disease → mode of inheritance | Evidence graph | 1 | 30 | 1 | 3.3% | 100.0% | 6.5% |
| Disease → mode of inheritance | Direct reading | 1 | 28 | 1 | 3.6% | 100.0% | 6.9% |
| Disease → mode of inheritance | Agentic curator | 1 | 24 | 1 | 4.2% | 100.0% | 8.0% |
| Disease → mode of inheritance | Memory only (control) | 1 | 7 | 1 | 14.3% | 100.0% | 25.0% |
| Disease → mode of inheritance | Case table first | 1 | 28 | 1 | 3.6% | 100.0% | 6.9% |
| Disease → phenotype (HPO, exact id) | Evidence graph | 40 | 624 | 67 | 6.4% | 59.7% | 11.6% |
| Disease → phenotype (HPO, exact id) | Direct reading | 25 | 538 | 69 | 4.7% | 36.2% | 8.2% |
| Disease → phenotype (HPO, exact id) | Agentic curator | 16 | 345 | 69 | 4.6% | 23.2% | 7.7% |
| Disease → phenotype (HPO, exact id) | Memory only (control) | 7 | 103 | 67 | 6.8% | 10.4% | 8.2% |
| Disease → phenotype (HPO, exact id) | Case table first | 41 | 657 | 67 | 6.2% | 61.2% | 11.3% |
| Disease → allelic variant | Evidence graph | 82 | 130 | 118 | 63.1% | 69.5% | 66.1% |
| Disease → allelic variant | Direct reading | 75 | 99 | 119 | 75.8% | 63.0% | 68.8% |
| Disease → allelic variant | Agentic curator | 59 | 77 | 118 | 76.6% | 50.0% | 60.5% |
| Disease → allelic variant | Memory only (control) | 1 | 1 | 118 | 100.0% | 0.9% | 1.7% |
| Disease → allelic variant | Case table first | 65 | 86 | 118 | 75.6% | 55.1% | 63.7% |
