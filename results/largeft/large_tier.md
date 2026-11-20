# Experiment A1: natural large-entry tier

Generated 2026-11-20T07:41:00 by `python -m aiomim.largetier analyze`. **The 12 large12 entries were scored after the audit's repair round; the new entries were generated and scored without audit or repair. The combined tier mixes the two.**

New entries run: 4 (155600, 168600, 152700, 114500), the first in rule order of `evalsets/largeft8.tsv`; the header of that file gives the rule, seed, candidates and shortlist.

Measure: OMIM facts conveyed: share of the fixed (frozen) fact list of the entry's in-scope curator paragraphs that the draft text citing the paper conveys (present = 1, partial = 0.5), mean over entries. Paired differences are strategy minus direct reading, in percentage points, with a percentile bootstrap 95% interval (10,000 resamples, seed 7; none below 3 entries) and an exact two-sided sign test on better/worse (ties dropped). No correction for multiple comparisons.

## Deviations from the design

- Sample of up to 200 eligible entries (design: 400) and 8 new entries selected (design: 16; reduced sizes: 8).
- Only the first 4 selected entries in rule order were run (reduced sizes: 8, floor 6): the 1,500-call cap allowed no more (an entry cost about 250-330 new calls, most of it per-paper extraction for the evidence graph and the case table).
- The split on facts the supplied text states was not made (reduced sizes: only if it fits).
- The selection was resolved in three passes across machine restarts; counts resolved earlier were reused from its log. The first three entries were run before it finished, each only once its place in the top 8 was certain from the bounds (times in the header of evalsets/largeft8.tsv).

## Completion

complete = draft written and every per-paper call succeeded; incomplete = draft written but a per-paper extraction call was stopped by the safety filter and the paper was dropped (evidence graph, case table); no draft = the writer (or a direct-reading batch) was stopped, or the strategy did not run.

| Group | Strategy | complete | incomplete | no draft |
|---|---|---|---|---|
| combined | Direct reading | 12 | 0 | 4 |
| combined | Agentic curator | 14 | 0 | 2 |
| combined | Evidence graph | 11 | 4 | 1 |
| combined | Case table first | 10 | 5 | 1 |
| new | Direct reading | 1 | 0 | 3 |
| new | Agentic curator | 2 | 0 | 2 |
| new | Evidence graph | 0 | 4 | 0 |
| new | Case table first | 0 | 3 | 1 |
| old | Direct reading | 11 | 0 | 1 |
| old | Agentic curator | 12 | 0 | 0 |
| old | Evidence graph | 11 | 0 | 1 |
| old | Case table first | 10 | 2 | 0 |

Safety-filter stops on the new entries (recorded, never retried):

| Strategy | writer stopped (no draft) | entries with stopped papers | papers stopped |
|---|---|---|---|
| Direct reading | 3 | 0 | 0 |
| Agentic curator | 2 | 0 | 0 |
| Evidence graph | 0 | 4 | 37 |
| Case table first | 1 | 3 | 25 |

## Facts conveyed on entries every strategy completed (the design's comparison)

| Group | n | Strategy | mean % | vs direct (pp) | 95% CI | better / worse / tied | sign p |
|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | 10 | Direct reading | 45.5 | – | – | – | – |
| All compared entries (old + new) | 10 | Agentic curator | 44.9 | -0.6 | [-2.1, +0.7] | 2 / 6 / 2 | 0.289 |
| All compared entries (old + new) | 10 | Evidence graph | 46.3 | +0.7 | [-2.7, +3.4] | 6 / 3 / 1 | 0.508 |
| All compared entries (old + new) | 10 | Case table first | 46.0 | +0.4 | [-1.4, +2.3] | 5 / 4 / 1 | 1.000 |
| New entries alone (no audit) | 0 | Direct reading | – | – | – | – | – |
| New entries alone (no audit) | 0 | Agentic curator | – | – | – | – | – |
| New entries alone (no audit) | 0 | Evidence graph | – | – | – | – | – |
| New entries alone (no audit) | 0 | Case table first | – | – | – | – | – |
| large12 alone (after repair) | 10 | Direct reading | 45.5 | – | – | – | – |
| large12 alone (after repair) | 10 | Agentic curator | 44.9 | -0.6 | [-2.1, +0.7] | 2 / 6 / 2 | 0.289 |
| large12 alone (after repair) | 10 | Evidence graph | 46.3 | +0.7 | [-2.7, +3.4] | 6 / 3 / 1 | 0.508 |
| large12 alone (after repair) | 10 | Case table first | 46.0 | +0.4 | [-1.4, +2.3] | 5 / 4 / 1 | 1.000 |
| All compared, supplied characters at or below the median | 5 | Direct reading | 37.8 | – | – | – | – |
| All compared, supplied characters at or below the median | 5 | Agentic curator | 37.7 | -0.1 | [-0.7, +0.6] | 1 / 2 / 2 | 1.000 |
| All compared, supplied characters at or below the median | 5 | Evidence graph | 39.5 | +1.7 | [-0.1, +4.3] | 3 / 1 / 1 | 0.625 |
| All compared, supplied characters at or below the median | 5 | Case table first | 38.4 | +0.7 | [-1.4, +3.3] | 2 / 2 / 1 | 1.000 |
| All compared, supplied characters above the median | 5 | Direct reading | 53.3 | – | – | – | – |
| All compared, supplied characters above the median | 5 | Agentic curator | 52.2 | -1.1 | [-3.9, +1.6] | 1 / 4 / 0 | 0.375 |
| All compared, supplied characters above the median | 5 | Evidence graph | 53.1 | -0.2 | [-6.7, +4.4] | 3 / 2 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Case table first | 53.5 | +0.2 | [-2.6, +2.8] | 3 / 2 / 0 | 1.000 |
| New alone, at or below their median | 0 | Direct reading | – | – | – | – | – |
| New alone, at or below their median | 0 | Agentic curator | – | – | – | – | – |
| New alone, at or below their median | 0 | Evidence graph | – | – | – | – | – |
| New alone, at or below their median | 0 | Case table first | – | – | – | – | – |
| New alone, above their median | 0 | Direct reading | – | – | – | – | – |
| New alone, above their median | 0 | Agentic curator | – | – | – | – | – |
| New alone, above their median | 0 | Evidence graph | – | – | – | – | – |
| New alone, above their median | 0 | Case table first | – | – | – | – | – |

Median supplied characters of the compared entries: 56,818 (all); no new entry is compared.

## Secondary view: every strategy wrote a scored draft (stopped papers included)

Not in the design. Incomplete drafts were written without the papers whose extraction the safety filter stopped, so a strategy's score here mixes method and stops; read it as a description, not a test.

| Group | n | Strategy | mean % | vs direct (pp) | 95% CI | better / worse / tied | sign p |
|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | 11 | Direct reading | 46.2 | – | – | – | – |
| All compared entries (old + new) | 11 | Agentic curator | 45.5 | -0.6 | [-1.9, +0.5] | 2 / 7 / 2 | 0.180 |
| All compared entries (old + new) | 11 | Evidence graph | 45.7 | -0.5 | [-4.3, +2.8] | 6 / 4 / 1 | 0.754 |
| All compared entries (old + new) | 11 | Case table first | 46.3 | +0.1 | [-1.5, +1.9] | 5 / 5 / 1 | 1.000 |
| New entries alone (no audit) | 1 | Direct reading | 52.3 | – | – | – | – |
| New entries alone (no audit) | 1 | Agentic curator | 51.5 | -0.8 | – | 0 / 1 / 0 | 1.000 |
| New entries alone (no audit) | 1 | Evidence graph | 39.8 | -12.5 | – | 0 / 1 / 0 | 1.000 |
| New entries alone (no audit) | 1 | Case table first | 49.6 | -2.7 | – | 0 / 1 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Direct reading | 52.5 | – | – | – | – |
| All compared, supplied characters above the median | 5 | Agentic curator | 51.4 | -1.1 | [-3.9, +1.6] | 1 / 4 / 0 | 0.375 |
| All compared, supplied characters above the median | 5 | Evidence graph | 49.2 | -3.3 | [-10.2, +3.6] | 2 / 3 / 0 | 1.000 |
| All compared, supplied characters above the median | 5 | Case table first | 51.9 | -0.6 | [-3.2, +2.4] | 2 / 3 / 0 | 1.000 |

Median supplied characters of these entries: 59,100.

Pairwise with direct reading, on entries where both wrote a scored draft (stopped papers included):

| Group | Strategy | n | strategy % | direct % | vs direct (pp) | 95% CI | better / worse / tied | sign p | entries |
|---|---|---|---|---|---|---|---|---|---|
| All compared entries (old + new) | Agentic curator | 12 | 44.8 | 45.5 | -0.6 | [-1.8, +0.5] | 2 / 8 / 2 | 0.109 | 128100, 152700*, 175200, 258870, 600116, 601419, 607060, 609016, 613095, 613470, 613679, 621314 |
| All compared entries (old + new) | Evidence graph | 11 | 45.7 | 46.2 | -0.5 | [-4.3, +2.8] | 6 / 4 / 1 | 0.754 | 128100, 152700*, 175200, 258870, 600116, 601419, 609016, 613095, 613470, 613679, 621314 |
| All compared entries (old + new) | Case table first | 12 | 45.7 | 45.5 | +0.2 | [-1.4, +1.9] | 6 / 5 / 1 | 1.000 | 128100, 152700*, 175200, 258870, 600116, 601419, 607060, 609016, 613095, 613470, 613679, 621314 |
| New entries alone (no audit) | Agentic curator | 1 | 51.5 | 52.3 | -0.8 | – | 0 / 1 / 0 | 1.000 | 152700* |
| New entries alone (no audit) | Evidence graph | 1 | 39.8 | 52.3 | -12.5 | – | 0 / 1 / 0 | 1.000 | 152700* |
| New entries alone (no audit) | Case table first | 1 | 49.6 | 52.3 | -2.7 | – | 0 / 1 / 0 | 1.000 | 152700* |

(* new entry)

## Per entry

refs = references; full = readable in full; chars = characters supplied (title, abstract, full text); prompts = writer prompts of direct reading (batches + merge; * planned, the writer was stopped); cut = papers/characters direct reading's prompt shortened; ext cut = papers over the 180,000-character extraction cap; paras/facts = in-scope curator paragraphs and fixed facts; refs scored = references the scored paragraphs are about (share of all references). Coverage % per strategy; (i) incomplete, with papers stopped; (–) no draft. agent unread = papers the agentic curator did not open.

| Entry | tier | refs | full | chars | prompts | cut | ext cut | paras | facts | refs scored | direct | agent | kg | cohort | agent unread |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 258870 | old | 34 | 0 | 33,745 | 1 | 0/0 | 0 | 13 | 83 | 2 (5.9%) | 11.4 | 10.2 | 10.8 | 10.8 | 0 |
| 128100 | old | 60 | 1 | 71,650 | 1 | 0/0 | 0 | 10 | 157 | 10 (16.7%) | 52.2 | 46.5 | 57.3 | 54.1 | 0 |
| 180300 | old | 73 | 16 | 648,575 | 3* | 0/0 | 0 | 10 | 90 | 9 (12.3%) | – | 47.2 | 56.1 | 58.9 (i, 9) | 4 |
| 600116 | old | 39 | 3 | 132,106 | 1 | 3/25,174 | 0 | 14 | 163 | 9 (23.1%) | 37.1 | 36.8 | 36.2 | 34.7 | 0 |
| 607060 | old | 44 | 5 | 215,334 | 1 | 4/77,703 | 0 | 16 | 150 | 14 (31.8%) | 37.7 | 37.3 | – | 38.7 (i, 2) | 0 |
| 609016 | old | 30 | 1 | 67,818 | 1 | 1/13,328 | 0 | 7 | 59 | 5 (16.7%) | 77.1 | 80.5 | 81.4 | 81.4 | 0 |
| 613679 | old | 35 | 0 | 31,849 | 1 | 0/0 | 0 | 9 | 97 | 13 (37.1%) | 52.1 | 52.1 | 58.8 | 49.5 | 0 |
| 613470 | old | 31 | 0 | 21,025 | 1 | 0/0 | 0 | 5 | 46 | 3 (9.7%) | 54.3 | 55.4 | 54.3 | 54.3 | 0 |
| 621314 | old | 45 | 2 | 108,471 | 1 | 2/29,922 | 0 | 5 | 48 | 4 (8.9%) | 43.8 | 41.7 | 31.2 | 39.6 | 0 |
| 175200 | old | 75 | 0 | 54,535 | 1 | 0/0 | 0 | 14 | 118 | 6 (8.0%) | 39.4 | 39.0 | 41.1 | 40.3 | 0 |
| 601419 | old | 37 | 1 | 59,100 | 1 | 0/0 | 0 | 18 | 256 | 19 (51.3%) | 56.4 | 55.5 | 59.4 | 57.8 | 0 |
| 613095 | old | 33 | 0 | 39,040 | 1 | 0/0 | 0 | 8 | 79 | 5 (15.2%) | 31.6 | 31.6 | 32.3 | 37.3 | 0 |
| 155600 | new | 119 | 33 | 998,176 | 3* | 0/0 | 0 | 6 | 53 | 6 (5.0%) | – | – | 48.1 (i, 20) | 52.8 (i, 18) | – |
| 168600 | new | 133 | 19 | 604,761 | 3* | 0/0 | 0 | 16 | 152 | 10 (7.5%) | – | 41.8 | 46.4 (i, 7) | 47.0 (i, 5) | 0 |
| 152700 | new | 148 | 14 | 614,865 | 3 | 0/0 | 0 | 14 | 133 | 14 (9.5%) | 52.3 | 51.5 | 39.8 (i, 3) | 49.6 (i, 2) | 13 |
| 114500 | new | 76 | 12 | 375,649 | 1* | 8/95,140 | 0 | 15 | 94 | 6 (7.9%) | – | – | 48.9 (i, 7) | – | – |

## Caps that truncated the input

Direct reading: one prompt holds 600,000 characters; above that the papers are split into batches of that size and the partial drafts merged, and only a paper longer than a whole batch is cut; in one prompt each paper is cut to max(20,000, 600,000 / papers) characters. Evidence graph and case table: each paper's extraction reads at most 180,000 characters.

- 600116 (old): direct reading cut 3 papers by 25,174 characters; extraction cut 0 papers
- 607060 (old): direct reading cut 4 papers by 77,703 characters; extraction cut 0 papers
- 609016 (old): direct reading cut 1 papers by 13,328 characters; extraction cut 0 papers
- 621314 (old): direct reading cut 2 papers by 29,922 characters; extraction cut 0 papers
- 114500 (new): direct reading cut 8 papers by 95,140 characters (as planned: the writer was stopped, so no draft was written from it); extraction cut 0 papers



## Calls, cost and time (new entries)

Calls and list-price cost as made fresh (generation; scoring = adaptive judge, variant match and fixed-fact marking); wall-clock = the CLI pass for that entry and strategy (generation + scoring), summed over resumed passes; new calls = calls not answered from the cache in this experiment's passes.

| Strategy | entries | generate calls | score calls | generate $ | score $ | wall-clock h | new calls here |
|---|---|---|---|---|---|---|---|
| Direct reading | 4 | 9 | 66 | 17.19 | 1.49 | 0.61 | 126 |
| Agentic curator | 4 | 6 | 81 | 9.03 | 1.99 | 0.83 | 64 |
| Evidence graph | 4 | 484 | 105 | 35.64 | 2.73 | 0.98 | 589 |
| Case table first | 4 | 484 | 90 | 35.92 | 2.28 | 0.92 | 559 |

New model calls made by this experiment: 1338 of the 1500 cap (1338 counted per pass in runs/largeft/timing.tsv, plus 0 made by a pass the machine restart interrupted).

| Entry | Strategy | status | gen calls | gen $ | score calls | marking calls | wall s | new calls |
|---|---|---|---|---|---|---|---|---|
| 155600 | direct | no_draft | 2 | 6.91 | 6 | – | 577 | 14 |
| 155600 | agent | no_draft | 1 | 1.77 | 6 | – | 653 | 1 |
| 155600 | kg | incomplete | 121 | 11.9 | 12 | 6 | 981 | 133 |
| 155600 | cohort | incomplete | 121 | 11.18 | 13 | 6 | 999 | 134 |
| 168600 | direct | no_draft | 2 | 4.1 | 16 | – | 454 | 34 |
| 168600 | agent | complete | 2 | 2.54 | 31 | 14 | 883 | 31 |
| 168600 | kg | incomplete | 135 | 8.81 | 33 | 16 | 971 | 168 |
| 168600 | cohort | incomplete | 135 | 9.25 | 33 | 16 | 813 | 168 |
| 152700 | direct | complete | 4 | 3.68 | 29 | 14 | 644 | 47 |
| 152700 | agent | complete | 2 | 2.89 | 29 | 14 | 793 | 31 |
| 152700 | kg | incomplete | 150 | 9.44 | 29 | 14 | 930 | 179 |
| 152700 | cohort | incomplete | 150 | 9.7 | 29 | 14 | 916 | 179 |
| 114500 | direct | no_draft | 1 | 2.5 | 15 | – | 511 | 31 |
| 114500 | agent | no_draft | 1 | 1.83 | 15 | – | 671 | 1 |
| 114500 | kg | incomplete | 78 | 5.49 | 31 | 15 | 658 | 109 |
| 114500 | cohort | no_draft | 78 | 5.79 | 15 | – | 588 | 78 |
