# Conveyed OMIM facts: read in the supplied text, or not? — run `omim100`, strategy `direct` (frozen fact lists)

For every frozen OMIM fact the draft conveyed in full (present) or in part (partial), the judge checked whether the text the writer had for the paragraph's paper(s) states it (the stored availability judgement of `gaps --frozen`: same prompt, same per-paper cut, quotes verified in the text). A fact that text did not state, or stated only partly, was checked once more against the text of the entry's other supplied papers (cut the same way), since a later paper may describe an earlier one. These are model judgements, not a curator's. A conveyed fact stated in no supplied text was not read there: it was recalled from the model's memory, inferred from what the text does state (for example an inheritance mode from zygosity), or the judgement is wrong; this analysis does not separate the three.

97 entries, 466 OMIM paragraphs. Judge calls: 0 for the paper's own text (stored judgements were reused), 385 for the other papers (0 failed); safety stops: 0. Left out, no draft (the writer was stopped): 3 entries (609296, 620609, 621068).

**Headline.** Of the facts conveyed in full from papers readable only as an abstract or title, 24 of 1,458 (1.7%) are stated in no supplied text, and a further 241 only partly. Counting facts conveyed in part as well: 90 of 2,098 (4.3%) in no supplied text.

| Paper read as | Conveyed | Facts | Stated in its paper's text | Partly stated in its paper's text | Stated only in another supplied paper | Partly stated only in another supplied paper | In no supplied text | Unjudged |
|---|---|---|---|---|---|---|---|---|
| Full text | in full | 1,329 | 1,174 (88.3%) | 122 (9.2%) | 22 (1.7%) | 4 (0.3%) | 7 (0.5%) | 0 |
| Full text | in part | 214 | 122 (57.0%) | 86 (40.2%) | 1 (0.5%) | 1 (0.5%) | 4 (1.9%) | 0 |
| Full text | in full or in part | 1,543 | 1,296 (84.0%) | 208 (13.5%) | 23 (1.5%) | 5 (0.3%) | 11 (0.7%) | 0 |
| Abstract only | in full | 1,420 | 1,061 (74.7%) | 222 (15.6%) | 102 (7.2%) | 11 (0.8%) | 24 (1.7%) | 0 |
| Abstract only | in part | 583 | 27 (4.6%) | 462 (79.2%) | 15 (2.6%) | 21 (3.6%) | 58 (10.0%) | 0 |
| Abstract only | in full or in part | 2,003 | 1,088 (54.3%) | 684 (34.2%) | 117 (5.8%) | 32 (1.6%) | 82 (4.1%) | 0 |
| Title only | in full | 38 | 27 (71.0%) | 8 (21.1%) | 3 (7.9%) | 0 (0.0%) | 0 (0.0%) | 0 |
| Title only | in part | 57 | 0 (0.0%) | 47 (82.5%) | 1 (1.8%) | 1 (1.8%) | 8 (14.0%) | 0 |
| Title only | in full or in part | 95 | 27 (28.4%) | 55 (57.9%) | 4 (4.2%) | 1 (1.1%) | 8 (8.4%) | 0 |
| All papers | in full | 2,787 | 2,262 (81.2%) | 352 (12.6%) | 127 (4.6%) | 15 (0.5%) | 31 (1.1%) | 0 |
| All papers | in part | 854 | 149 (17.4%) | 595 (69.7%) | 17 (2.0%) | 23 (2.7%) | 70 (8.2%) | 0 |
| All papers | in full or in part | 3,641 | 2,411 (66.2%) | 947 (26.0%) | 144 (4.0%) | 38 (1.0%) | 101 (2.8%) | 0 |

Shares are of the facts judged in that row. The second check, by the paper's own-text verdict (facts conveyed in full or in part):

| Paper read as | Own text | Facts | Another paper states it | … partly | … no | No other paper supplied | Unjudged |
|---|---|---|---|---|---|---|---|
| Full text | partly stated | 223 | 15 | 37 | 171 | 0 | 0 |
| Full text | not stated | 24 | 8 | 5 | 11 | 0 | 0 |
| Abstract only | partly stated | 728 | 44 | 119 | 546 | 19 | 0 |
| Abstract only | not stated | 187 | 73 | 32 | 81 | 1 | 0 |
| Title only | partly stated | 57 | 2 | 5 | 50 | 0 | 0 |
| Title only | not stated | 11 | 2 | 1 | 8 | 0 | 0 |
| All papers | partly stated | 1,008 | 61 | 161 | 767 | 19 | 0 |
| All papers | not stated | 222 | 83 | 38 | 100 | 1 | 0 |
