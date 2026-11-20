# Plan: fig_missed_facts (Appendix D)

Source: `raw_materials/experimental_log.md`, Section 3 "Where the missed facts went (direct reading, fixed fact
lists)", first table, plus the line "Facts contradicted by the draft (not in the columns above)" below the second
table. Scope line of Sec. 3: 97 entries, 466 OMIM paragraphs, 437 judge calls (0 failed); 3 entries left out (no
draft, writer stopped). Counts are POOLED OVER FACTS (log: "Counts and shares in this section are pooled over facts").
Whether a missed fact is stated in the text available for its paper is a model judgement (log Sec. 3, first paragraph);
stated facts carry a quote verified in the text.

## Planner

Chart type: horizontal 100%-stacked bars, one bar per access level ("Paper read as"), direct reading only.

- y (categorical, top to bottom): Full text, Abstract only, Title only. The log's "All papers" row is not drawn
  (it is the pooled total of the three bars). Row tick label = access level + fact count ("Full text" / "1,837 facts").
- x: share of the access level's OMIM facts, 0-100 %.
- hue (segments, left to right):
  1. Conveyed (in full) = log column "Conveyed".
  2. Missed, stated in the available text = "... in text".
  3. Missed, partly stated = "... partly in text".
  4. Missed, not stated = "... not in text".
  "Missed" = log "Not fully conveyed": facts conveyed partly count as missed, as in the log.
  Contradicted facts (log: "not in the columns above") are NOT drawn as a segment: they are under 1 % of each bar
  (would be < 0.03 in wide, invisible at print size); each bar therefore ends just short of 100 % and the caption
  says the remainder were contradicted.
- Right-hand column, header "Stated, share of missed" (outline wording) = log column "In text, share of missed".
- Value labels inside segments: the log COUNTS (copied, not derived percentages), only where the segment is wide
  enough to hold the number at print size.

### Every data point (log Sec. 3, first table; contradicted from the line below the second table)

| Paper read as | OMIM facts | Conveyed | Not fully conveyed | stated (in text) | partly | not stated | contradicted | stated, share of missed |
|---|---|---|---|---|---|---|---|---|
| Full text     | 1,837 | 1,329 | 501   | 245 | 134 | 122   | 7  | 49% |
| Abstract only | 4,282 | 1,420 | 2,837 | 46  | 632 | 2,159 | 25 | 2%  |
| Title only    | 379   | 38    | 341   | 0   | 53  | 288   | 0  | 0%  |

Checks (asserted in plot.py): 245+134+122 = 501; 46+632+2,159 = 2,837; 0+53+288 = 341;
1,329+501+7 = 1,837; 1,420+2,837+25 = 4,282; 38+341+0 = 379.
Bar geometry (computed in plot.py from the counts, not printed): Full text 72.3 / 13.3 / 7.3 / 6.6 %;
Abstract only 33.2 / 1.1 / 14.8 / 50.4 %; Title only 10.0 / 0.0 / 14.0 / 76.0 %.
Segments labelled with counts: all except Abstract-only "stated" (46, about 1 % wide) and Title-only "stated" (0, no
segment).

## Stylist

- Printed width: full text width of the ICLR template, 5.5 in; aspect 16:9 -> figsize 5.5 x 3.09 in. Saved at
  exactly that size (no tight-bbox cropping) at 300 dpi, PNG + PDF, so 1 pt in the file = 1 pt on the page when
  included at `width=\linewidth`.
- Font: Liberation Sans (sans-serif) as in every figure of the paper; 8 pt for tick labels, legend, column and segment
  labels; nothing below 7 pt.
- Colours: greys only, from fig_access_bound panel (b) for the availability categories, plus direct reading's black
  for conveyed facts (every bar is direct reading, so black is used only for direct reading's own output; no other
  strategy colour appears):
  - Conveyed: #000000 (white count labels)
  - Missed, stated: #3B3B3B (white count labels)
  - Missed, partly stated: #9E9E9E (black count labels)
  - Missed, not stated: white fill with #9E9E9E hatch "////" and #9E9E9E outline (black labels on a white box)
  White 0.8 pt separators between segments so black and #3B3B3B stay distinct.
- Legend: one row above the plot, in segment order, no frame. No title, no "Figure N", no n-list sentence, no
  statistic other than the per-row fact count and the outline's share column.
- Axis: x ticks 0 %, 25 %, 50 %, 75 %, 100 %, label "Share of OMIM facts"; bottom spine bounded to 0-100; no top,
  right or left spine; no grid (bars cover it).
