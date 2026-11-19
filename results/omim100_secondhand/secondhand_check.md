# Second-hand evidence check

Source run `omim100`; 49 entries. In each, the papers read in full were hidden and the entry was written by direct reading from their abstracts, with and without second-hand passages from later open-access papers. Counts, not just rates.

## Retrieval for the hidden papers

- Hidden papers: 91; with citing papers: 91; with open-access citing papers: 89; with at least one passage: 89.
- Passages for the hidden papers: 523 (430,391 characters).
- All papers supplemented (hidden and abstract-only): 243, of which 234 got passages; 1278 passages, 1,046,654 characters; retrieval 0.1 s in all.

## OMIM-fact coverage of the gold paragraphs about the hidden papers

| Condition | Paragraphs | Facts | Present | Partial | Absent | Contradicted | Coverage |
|---|---|---|---|---|---|---|---|
| Abstract only | 142 | 1876 | 468 | 389 | 1016 | 3 | 35.3% |
| Abstract + second-hand | 142 | 1889 | 583 | 388 | 907 | 11 | 41.1% |
| Full text (source run's direct draft) | 142 | 1855 | 1268 | 243 | 334 | 10 | 74.9% |

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

## Per entry

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
| 609296 | 2 | 2 | 4 | 26.3% | 29.2% | 0.0% | 29 | 3 | 0 |
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
| 620609 | 2 | 2 | 1 | 54.5% | 57.7% | 0.0% | 51 | 0 | 0 |
| 620670 | 1 | 1 | 2 | 40.2% | 56.1% | 87.8% | 44 | 0 | 0 |
| 620851 | 2 | 2 | 2 | 40.9% | 45.5% | 75.0% | 78 | 9 | 1 |
| 621030 | 2 | 2 | 2 | 53.0% | 66.7% | 85.5% | 99 | 34 | 2 |
| 621068 | 2 | 2 | 1 | 34.0% | 38.1% | 0.0% | 35 | 0 | 0 |
| 621313 | 1 | 0 | 2 | 13.2% | 12.5% | 95.5% | 4 | 0 | 0 |
