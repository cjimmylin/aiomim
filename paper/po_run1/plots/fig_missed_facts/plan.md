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
