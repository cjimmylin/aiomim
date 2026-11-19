# fig_hidden_fulltext: plan

## Planner

Source: `raw_materials/experimental_log.md`, Sec. 6.2, table "OMIM-fact coverage on the frozen fact lists (main
measure)" (NOT the old-scoring table below it), and the paired-differences table directly under it.

Population: 46 entries, 136 paragraphs; the same entries, paragraphs and fact lists in every row; 2,120 facts judged in
each condition. Coverage = (present + half of partial) / facts judged.

Plot type: horizontal stacked bars, one bar per condition, x = number of facts (0 to 2,120), segments = judgement.
Rows top to bottom in order of increasing access: Abstract only; Abstract + second-hand passages; Full text.

Data points (copied exactly):

| Condition | Present | Partial | Absent | Contradicted | Facts | Coverage |
|---|---|---|---|---|---|---|
| Abstract only | 495 | 331 | 1290 | 4 | 2120 | 31.2% |
| Abstract + second-hand | 629 | 297 | 1184 | 10 | 2120 | 36.7% |
| Full text (source run's direct draft) | 1513 | 254 | 343 | 10 | 2120 | 77.4% |

Checks: each row sums to 2120; (495+331/2)/2120 = 31.16%, (629+297/2)/2120 = 36.67%, (1513+254/2)/2120 = 77.36%,
matching the log's 31.2 / 36.7 / 77.4.

Paired differences over entries (frozen scoring), bootstrap 95% interval, annotated at the right of the bars:
- Abstract + second-hand minus abstract only: +4.9 pp (+2.8 to +7.1); better / worse / tied 33 / 9 / 4.
- Full text minus abstract only: +43.9 pp (+38.5 to +49.3); better / worse / tied 45 / 0 / 1.

Coverage printed at the bar end. Segment counts printed inside segments wide enough to hold them; the contradicted
counts (4 / 10 / 10) are too narrow to draw legibly, so they are listed in a small column at the right instead.

Wording (notes.md): "second-hand" passages; "OMIM facts". No claim that the abstract drafts are wrong; contradicted is
reported separately. The full-text draft went through the repair round, the two new drafts did not: stated in the
caption, and the full-text row label carries a dagger explained in the caption... (decided in Stylist: label it
"Full text" and put the repair note in the caption only, to keep the image free of caption text).

## Stylist

- Colours matched to `fig_missed_facts` for the corresponding categories: Present = #009E73 (its "Conveyed"),
  Partly present = #E69F00 (its "Missed, partly stated"), Absent = #BBBBBB (its "Missed, not in available text"),
  Contradicted = #000000. Its vermilion #D55E00 has no counterpart here and is not used.
- In-segment labels: white on green and black, black on orange and grey (same as fig_missed_facts).
- Size: ICLR text width is 5.5 in; aspect 16:9 -> 5.5 x 3.1 in. Sans-serif (DejaVu Sans), 8-9 pt.
- Legend above the plot, one row, no frame. No grid. Top/right spines off. y tick labels are the condition names.
- Coverage at bar end in bold black; paired difference vs abstract only in a right-hand column, grey text.
- x axis: "OMIM facts judged (same 2,120 facts in each condition)".
- No project, package or author names anywhere.

## Final (after critic rounds)

Right-hand column shows coverage (bold) and the paired difference from abstract only with its 95% CI, with the
entry counts below as "entries: 33 better, 9 worse, 4 tied" / "45 better, 0 worse, 1 tied". Segment counts under 300
facts are set at 7 pt. Contradicted counts (4 / 10 / 10) are stated in the caption because the segments are sub-pixel.
