# Second-hand evidence check

Source run `omim100`; 49 entries. In each, the papers read in full were hidden and the entry was written by direct reading from their abstracts, with and without second-hand passages from later open-access papers. Counts, not just rates.

## Retrieval for the hidden papers

- Hidden papers: 91; with citing papers: 91; with open-access citing papers: 89; with at least one passage: 89.
- Passages for the hidden papers: 523 (430,391 characters).
- All papers supplemented (hidden and abstract-only): 243, of which 234 got passages; 1278 passages, 1,046,654 characters; retrieval 0.1 s in all.

## OMIM-fact coverage on the frozen fact lists (main measure)

Scoring: **frozen fact lists**. Each gold paragraph about a hidden paper was split into facts once, without sight of any draft (the same lists as the main runs), and the two new drafts were marked against them; the full-text row is the source run's existing frozen scoring of its direct draft (`eval.direct.json`, `gold_text_frozen`) restricted to the same paragraphs. 46 entries with a full-text draft in the source run, 136 paragraphs scored under all three conditions (the same entries, paragraphs and fact lists in every row). Coverage = (present + half of partial) / facts judged, pooled over facts; the last column is the mean of per-entry coverage over the same entries, the unit of the paired differences below.

| Condition | Entries | Paragraphs | Facts judged | Present | Partial | Absent | Contradicted | Coverage (frozen), pooled over facts | Coverage (old scoring), pooled over facts | Coverage (frozen), mean over entries |
|---|---|---|---|---|---|---|---|---|---|---|
| Abstract only | 46 | 136 | 2120 | 495 | 331 | 1290 | 4 | 31.2% | 35.5% | 36.1% |
| Abstract + second-hand | 46 | 136 | 2120 | 629 | 297 | 1184 | 10 | 36.7% | 41.4% | 40.9% |
| Full text (source run's direct draft) | 46 | 136 | 2120 | 1513 | 254 | 343 | 10 | 77.4% | 78.6% | 79.9% |

Paired differences, mean over entries (percentage points of per-entry coverage), bootstrap 95% interval over entries (10,000 resamples, seed 20261119); the old-scoring column uses the same entries.

| Difference | Entries | Frozen: mean (95% CI) | better / worse / tied | Old scoring: mean (95% CI) | better / worse / tied |
|---|---|---|---|---|---|
| Abstract + second-hand minus abstract only | 46 | +4.9 (+2.8 to +7.1) | 33 / 9 / 4 | +5.3 (+3.6 to +7.2) | 36 / 7 / 3 |
| Full text minus abstract only | 46 | +43.9 (+38.5 to +49.3) | 45 / 0 / 1 | +41.7 (+36.7 to +46.6) | 46 / 0 / 0 |

## Repair parity: what the repair round changed in the full-text drafts

The full-text row is the source run's direct-reading draft, which went through the audit's repair round; the two abstract drafts did not. Over the 46 entries compared, the audit before repair flagged 13 of 6,609 audited claims (13 unsupported, 0 contradicted) in 11 paragraphs of 8 entries; the repair revised 11 paragraphs and deleted 0. 11 of the 11 revised paragraphs were located in the final drafts, and 11 of them cite a hidden paper; 13 of the flagged claims lie in paragraphs citing a hidden paper. After repair the drafts hold 6,637 audited claims, 5,328 of them in paragraphs citing a hidden paper.

The pipeline does not keep the draft as it was before repair, so the full-text draft could not be scored before repair; no draft was regenerated.

## OMIM-fact coverage of the gold paragraphs about the hidden papers (old scoring: facts split afresh for each draft)

Pooled over the 46 entries that have a full-text draft in the source run, the same entries for all three conditions; left out: 3 entries whose full-text direct draft was not written (the writer's reply was stopped), so they have no full-text coverage to compare: 609296, 620609, 621068.

| Condition | Paragraphs | Facts | Present | Partial | Absent | Contradicted | Coverage, pooled over facts |
|---|---|---|---|---|---|---|---|
| Abstract only | 136 | 1783 | 452 | 362 | 966 | 3 | 35.5% |
| Abstract + second-hand | 136 | 1802 | 565 | 362 | 864 | 11 | 41.4% |
| Full text (source run's direct draft) | 136 | 1767 | 1268 | 243 | 246 | 10 | 78.6% |

Over all 49 entries the two new conditions convey 35.3% (abstract only, 1876 facts) and 41.1% (abstract + second-hand, 1889 facts), pooled over facts.

Facts are split from the gold paragraph separately for each condition, so the fact counts differ slightly. The full-text draft went through the audit's repair round; the two new drafts did not.

## Claims about the hidden papers in the second-hand draft

2308 claims (2208 after collapsing the same statement made in two paragraphs), each audited against what the writer saw (abstract plus passages) and against the paper's full text.

**Caveat: our full texts exclude supplementary material.** A detail a paper gives only in a supplementary table counts as unsupported here, so "unsupported by the primary text" is an upper bound on the error of second-hand claims; "contradicted" is not affected in the same way.

| Evidence (audit of what the writer saw) | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| none | 340 (338) | 191 (191) | 59 (59) | 55 (55) | 8 (8) | 27 (25) |
| own | 1856 (1764) | 1688 (1598) | 136 (134) | 8 (8) | 6 (6) | 18 (18) |
| secondhand | 112 (106) | 74 (68) | 24 (24) | 11 (11) | 3 (3) | 0 (0) |

`own`: the auditor's evidence quote is in the paper's title or abstract; `secondhand`: in a later paper's passage; `unlocated`: a quote found in neither (already downgraded); `none`: no quote (claim judged unsupported or contradicted against what the writer saw). Figures in brackets count a statement repeated in two paragraphs once.

### Claims resting on second-hand text, by passage

| Passage kind | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| paragraph | 91 (86) | 68 (63) | 18 (18) | 2 (2) | 3 (3) | 0 (0) |
| table | 21 (20) | 6 (5) | 6 (6) | 9 (9) | 0 (0) | 0 (0) |

| Other references cited by the passage (few = at most 2) | Claims (collapsed) | Full text: supported | partial | unsupported | contradicted | no verdict |
|---|---|---|---|---|---|---|
| few | 87 (83) | 55 (51) | 20 (20) | 11 (11) | 1 (1) | 0 (0) |
| many | 25 (23) | 19 (17) | 4 (4) | 0 (0) | 2 (2) | 0 (0) |

## Per entry (coverage columns: old scoring)

| MIM | Hidden | With passages | Gold paragraphs | Abstract | Second-hand | Full text | Claims | On second-hand | of which not supported by full text |
|---|---|---|---|---|---|---|---|---|---|
| 118210 | 1 | 1 | 1 | 35.7% | 32.1% | 87.5% | 18 | 0 | 0 |
| 251950 | 4 | 4 | 5 | 60.8% | 53.8% | 87.8% | 70 | 0 | 0 |
| 300148 | 3 | 3 | 3 | 38.9% | 47.9% | 76.2% | 80 | 0 | 0 |
| 600740 | 3 | 3 | 3 | 37.9% | 44.3% | 85.5% | 42 | 0 | 0 |
| 603552 | 1 | 1 | 1 | 35.0% | 40.5% | 89.1% | 30 | 0 | 0 |
| 603689 | 1 | 1 | 1 | 75.0% | 75.0% | 81.2% | 41 | 0 | 0 |
| 604307 | 2 | 2 | 2 | 84.1% | 89.1% | 91.7% | 55 | 0 | 0 |
| 604928 | 1 | 1 | 1 | 39.3% | 50.0% | 78.6% | 37 | 0 | 0 |
| 606763 | 1 | 1 | 3 | 20.8% | 28.1% | 76.0% | 26 | 8 | 0 |
| 607721 | 3 | 3 | 3 | 56.1% | 58.3% | 67.6% | 66 | 0 | 0 |
| 607734 | 1 | 1 | 1 | 65.8% | 66.7% | 92.1% | 35 | 0 | 0 |
| 607876 | 2 | 2 | 4 | 53.7% | 50.0% | 77.5% | 34 | 0 | 0 |
| 608133 | 1 | 1 | 2 | 0.0% | 15.9% | 75.0% | 8 | 0 | 0 |
| 609296 | 2 | 2 | 4 | 26.3% | 29.2% | no draft | 29 | 3 | 0 |
| 611521 | 4 | 4 | 8 | 23.1% | 35.3% | 82.8% | 93 | 0 | 0 |
| 613730 | 1 | 1 | 3 | 43.6% | 55.1% | 91.7% | 58 | 0 | 0 |
| 613744 | 3 | 3 | 3 | 35.8% | 38.9% | 75.5% | 55 | 0 | 0 |
| 614501 | 2 | 2 | 1 | 14.7% | 17.6% | 70.0% | 40 | 0 | 0 |
| 614651 | 2 | 2 | 3 | 35.4% | 64.0% | 88.5% | 69 | 11 | 0 |
| 614856 | 1 | 1 | 2 | 70.0% | 70.8% | 93.2% | 34 | 0 | 0 |
| 615073 | 1 | 1 | 6 | 29.5% | 29.3% | 87.8% | 13 | 0 | 0 |
| 615268 | 1 | 1 | 1 | 75.0% | 75.0% | 93.3% | 23 | 0 | 0 |
| 615582 | 2 | 2 | 5 | 16.5% | 19.9% | 44.0% | 59 | 0 | 0 |
| 615710 | 3 | 3 | 8 | 30.6% | 38.2% | 67.2% | 53 | 14 | 9 |
| 615972 | 2 | 1 | 2 | 40.9% | 50.0% | 90.5% | 35 | 0 | 0 |
| 616151 | 1 | 1 | 1 | 25.0% | 27.3% | 70.8% | 21 | 0 | 0 |
| 617153 | 3 | 3 | 3 | 26.3% | 32.5% | 52.8% | 58 | 0 | 0 |
| 617232 | 2 | 2 | 7 | 32.5% | 38.0% | 82.9% | 72 | 0 | 0 |
| 617927 | 1 | 1 | 1 | 32.5% | 47.8% | 97.7% | 27 | 0 | 0 |
| 618343 | 2 | 2 | 2 | 57.1% | 60.0% | 81.5% | 53 | 0 | 0 |
| 618400 | 2 | 2 | 2 | 25.0% | 29.2% | 76.0% | 24 | 0 | 0 |
| 618808 | 1 | 1 | 2 | 25.0% | 31.0% | 45.5% | 7 | 0 | 0 |
| 618875 | 1 | 1 | 2 | 8.3% | 24.0% | 76.1% | 19 | 16 | 1 |
| 619124 | 2 | 2 | 9 | 20.8% | 27.6% | 70.2% | 57 | 0 | 0 |
| 619201 | 1 | 1 | 2 | 27.8% | 32.1% | 78.2% | 24 | 0 | 0 |
| 619681 | 2 | 2 | 4 | 43.9% | 43.9% | 87.7% | 49 | 0 | 0 |
| 620022 | 3 | 3 | 6 | 39.2% | 44.9% | 89.4% | 79 | 14 | 1 |
| 620029 | 2 | 2 | 4 | 33.3% | 35.0% | 84.5% | 82 | 0 | 0 |
| 620098 | 2 | 2 | 2 | 18.2% | 15.8% | 69.6% | 38 | 0 | 0 |
| 620249 | 3 | 3 | 3 | 66.7% | 66.2% | 88.2% | 102 | 3 | 0 |
| 620402 | 2 | 2 | 2 | 43.1% | 48.2% | 85.2% | 79 | 0 | 0 |
| 620457 | 1 | 1 | 1 | 69.4% | 71.1% | 97.4% | 41 | 0 | 0 |
| 620481 | 2 | 2 | 3 | 34.3% | 38.5% | 82.9% | 62 | 0 | 0 |
| 620609 | 2 | 2 | 1 | 54.5% | 57.7% | no draft | 51 | 0 | 0 |
| 620670 | 1 | 1 | 2 | 40.2% | 56.1% | 87.8% | 44 | 0 | 0 |
| 620851 | 2 | 2 | 2 | 40.9% | 45.5% | 75.0% | 78 | 9 | 1 |
| 621030 | 2 | 2 | 2 | 53.0% | 66.7% | 85.5% | 99 | 34 | 2 |
| 621068 | 2 | 2 | 1 | 34.0% | 38.1% | no draft | 35 | 0 | 0 |
| 621313 | 1 | 0 | 2 | 13.2% | 12.5% | 95.5% | 4 | 0 | 0 |
