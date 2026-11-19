# Plan: fig_missed_facts

Source: raw_materials/experimental_log.md, Section 3 "Where the missed facts went (direct reading, fixed
fact lists)", first table. Scope line: 97 entries, 466 OMIM paragraphs, 437 judge calls (0 failed); 3 entries
left out (no draft, writer stopped). The check of each missed fact against the available text is a model judgement.

## Chart
100%-stacked horizontal bar chart (horizontal so the long category names and segment text fit a single column).
- y (categorical, top to bottom): "Full text", "Abstract only", "Title only" (log column "Paper read as").
  The "All papers" row is not drawn as a bar (it is the pooled total; mentioned in the caption only via the
  log's own percentages if needed).
- x: share of the access level's OMIM facts, 0-100%.
- hue (segments, left to right):
  1. Conveyed
  2. Missed, stated in the available text ("... in text")
  3. Missed, partly stated in the available text ("... partly in text")
  4. Missed, not in the available text ("... not in text")
  5. Contradicted (remainder) = OMIM facts - Conveyed - Not fully conveyed. The log says "the remainder were
     contradicted"; this is arithmetic on log values, not a new number.
- Right of each bar: "n = <OMIM facts>" and "in text: <share> of missed" copied from the log column
  "In text, share of missed".

## Data points (copied exactly from the log table)
| Paper read as | OMIM facts | Conveyed | Not fully conveyed | in text | partly | not in text | In text, share of missed |
|---|---|---|---|---|---|---|---|
| Full text     | 1,837 | 1,329 | 501   | 245 | 134 | 122   | 49% |
| Abstract only | 4,282 | 1,420 | 2,837 | 46  | 632 | 2,159 | 2%  |
| Title only    | 379   | 38    | 341   | 0   | 53  | 288   | 0%  |

Checks: 245+134+122 = 501; 46+632+2159 = 2837; 0+53+288 = 341.
Derived remainder (contradicted): Full text 1837-1329-501 = 7; Abstract only 4282-1420-2837 = 25; Title only
379-38-341 = 0.
Segment shares (of OMIM facts, computed in plot.py):
- Full text: 72.3 / 13.3 / 7.3 / 6.6 / 0.4 %
- Abstract only: 33.2 / 1.1 / 14.8 / 50.4 / 0.6 %
- Title only: 10.0 / 0.0 / 14.0 / 76.0 / 0.0 %

## Style (stylist)
- Single column, 3.4 in wide, 4:3 -> 3.4 x 2.55 in. White background, no grid except light vertical x grid, no
  top/right spines.
- Colours (Okabe-Ito, colour-blind safe): Conveyed #009E73 (green); Missed, in text #D55E00 (vermilion, the
  focus: facts the reader had but dropped); Missed, partly in text #E69F00 (orange); Missed, not in text
  #BBBBBB light grey (unavailable to the reader); Contradicted #000000.
- Sans-serif, 8 pt minimum (tick and legend 7.5-8 pt rendered at 3.4 in -> keep >= 8 where possible, legend 7.5
  acceptable only if needed; target 8).
- Percent labels inside segments only when the segment is >= 8% wide; white text on dark fills, black on light.
- Legend above the plot in two columns, no frame.
- No title, no caption in the image.

## Revisions after critic rounds (final state)
- n per access level moved into the y tick labels ("Full text\nn = 1,837"); y-axis title dropped (tick labels are
  self-explanatory).
- Right-hand column headed "In text, share of missed" (log column name) with 49% / 2% / 0%, drawn inside an
  x range of 0-115 with the x spine and ticks bounded at 100%.
- Constrained layout and a figure-level legend (7 pt, two columns) so the whole image is about 3.5 in wide and
  needs no down-scaling at column width.
- Percent labels only inside segments >= 9.5% wide (8 pt if >= 12%, else 7 pt); the Full-text 7% / 7% segments and
  the thin segments are unlabelled.

## Legibility revision (print size)
- 2.4 x 2.3 in (beside fig_hidden_fulltext, same height). Access level and n on a line above each bar, 'in text: X% of missed' right-aligned on the same line. Legend labels shortened ('Missed, in text', 'Missed, partly in text', 'Missed, not in text').
- Font Liberation Sans in all five figures; every text element 7 pt at print size (panel headers 7.5 pt); figsize equals printed width; saved at dpi 300 without bbox cropping so the PNG is exactly the printed size. Strategy colours shared by all figures (Okabe-Ito): direct reading #0072B2, agentic curator #56B4E9, evidence graph #009E73, case table first #D55E00, recall then verify #E69F00, memory only #000000. Outcome categories (fig_hidden_fulltext, fig_missed_facts) use greys plus #F0E442 (missed although in text) and #CC79A7 (contradicted), so no strategy colour means anything else. Data values unchanged.
