# fig_access_bound: plan (Planner + Stylist)

Placement: main text, Section 4.1, printed at full text width (ICLR \textwidth = 5.5 in), so the figure is drawn at
5.5 in wide and printed 1:1. Aspect 21:9 -> 5.5 x 2.36 in. Three panels in one row, overall panel widths about
1 : 1.1 : 1.4 (including tick labels). Panel letters (a) (b) (c) only; no titles, no n-lists, no statistics.

All numbers are copied from RUN/raw_materials/experimental_log.md. Section and line cited per data point.

## Panel (a): hidden-full-text experiment, like for like (no arm repaired)

- Type: vertical bars, one per condition, all three are DIRECT READING drafts on the same 46 entries,
  136 curator paragraphs and 2,120 fixed facts.
- x: condition (categorical); y: OMIM facts conveyed, MEAN OVER ENTRIES (n = 46), 0-100, label
  "% of fixed facts conveyed".
- Data points (log Sec. 6.2):
  | Bar label | Value (mean over entries) | Log source |
  |---|---|---|
  | Abstract only | 36.1% | Sec. 6.2, sentence "OMIM facts conveyed on the fixed fact lists" (l. 668); frozen table last column (l. 684) |
  | Abstract + second-hand | 40.9% | Sec. 6.2, same sentence (l. 668); frozen table (l. 685) |
  | Full text (before the repair round) | 79.8% | Sec. 6.2, same sentence (l. 668); "Repair parity" paragraph (l. 701) |
- NOT drawn (the after-repair 79.9% and the pooled levels 31.2 / 36.7 / 77.3 / 77.4%): the full-text bar is the
  draft before repair so that no bar is repaired (the two abstract drafts never went through repair, l. 662).
- Paired differences go in the caption only (means over entries, bootstrap 95% CI, better/worse/tied):
  abstract + second-hand minus abstract only +4.9 (+2.8 to +7.1), 33/9/4 (Sec. 6.2 l. 692);
  full text before repair minus abstract only +43.7 (+38.3 to +49.1), 45/0/1 (Sec. 6.2 "Repair parity", l. 705).
- Value label on each bar ("36.1%", "40.9%", "79.8%").

## Panel (b): what the supplied text states, by access level (pooled over facts)

- Type: horizontal 100%-stacked bars, one row per access level (top to bottom: full text, abstract only,
  title only). x: share of the level's fixed facts (0-100, "% of fixed facts"); colour/fill: availability judgement.
- Population: the 6,239 fixed facts of the 93 compared entries, POOLED OVER FACTS.
- Data points (log Sec. 2.10a, table "The facts, by availability", l. 335-340):
  | Row | Facts | Stated | Partly stated | Not stated |
  |---|---|---|---|---|
  | Full text | 1,639 | 1,246 | 253 | 140 |
  | Abstract only | 4,221 | 1,099 | 883 | 2,239 |
  | Title only | 379 | 27 | 62 | 290 |
  (Unjudged = 0 in every row; rows sum to 6,239, matching the table's "All papers" row.)
- Derived shares (computed from the counts, rounded to integers; the script asserts the counts sum):
  full text 76 / 15 / 9; abstract only 26 / 21 / 53; title only 7 / 16 / 77.
- The fact count goes in the row tick label ("Full text\n1,639 facts"). Percentage labels only inside segments
  wide enough to hold them (decided by measuring the rendered text against the segment width).

## Panel (c): strategies on stated versus not-stated facts (means over entries)

- Type: dumbbell, one row per strategy (top to bottom: direct reading, agentic curator, evidence graph,
  case table first, recall then verify, memory only (control)). x: OMIM facts conveyed, MEAN OVER ENTRIES, 0-100,
  "% of fixed facts conveyed". Filled marker = facts the supplied text states (89 entries); hollow marker = facts it
  does not state (90 entries); thin line between them in the strategy colour.
- Data points (log Sec. 2.10a, table "Summary: mean over entries", l. 344-352, columns "Stated" and "Not stated"):
  | Strategy | Stated | Not stated |
  |---|---|---|
  | Direct reading | 94.4 | 6.9 |
  | Agentic curator | 93.6 | 6.3 |
  | Evidence graph | 94.2 | 5.5 |
  | Case table first | 91.0 | 5.9 |
  | Recall, then verify | 28.8 | 2.1 |
  | Memory only (control) | 23.3 | 8.2 |
  | Entries (n) | 89 | 90 |
  (Cross-checked against the per-restriction tables "Facts stated in the available text, all papers", l. 377-382,
  and "Facts not stated ...", l. 399-404: identical means.)
- Two-entry marker legend inside the panel (filled = stated, hollow = not stated), in neutral grey.
- Caveat for the caption: "stated" is a model judgement with verified quotes, not checked by a curator (l. 316).

## Stylist

- Size 5.5 x 2.36 in, constrained layout; final PNG checked to stay at about 5.5 in so print scale is 1:1.
- Font: Liberation Sans (Arial metrics), every text element 7 pt; panel letters 8 pt bold. Nothing below 7 pt.
- Strategy colours (binding palette from the orchestrator, identical across figures): direct reading #0072B2,
  agentic curator #56B4E9, evidence graph #009E73, case table first #D55E00, recall then verify #E69F00,
  memory only #000000. NOTE: this palette supersedes the outline's ("direct reading #000000 ..."), so panel (a) is
  drawn in direct reading's blue, not black.
- Panel (a): all three bars direct reading blue #0072B2: abstract only = white fill, blue edge; abstract +
  second-hand = white fill with blue "////" hatch; full text = solid blue. Light horizontal grid (#E6E6E6, 0.4 pt)
  behind bars; top/right spines off.
- Panel (b): availability greys (greys are reserved for access/availability/outcome, never a strategy): stated
  #3B3B3B (white label text), partly stated #9E9E9E (black text), not stated white with grey "\\\\" hatch (#8C8C8C;
  black text on a small white box). Different hatch direction from (a) so the two hatches are not read as linked.
  Legend (3 entries) above the bars; no grid; top/right/left spines off.
- Panel (c): markers 5 pt circles; hollow = white face, strategy-colour edge 1.0 pt; joining line 0.9 pt in strategy
  colour. Light vertical grid at 0/25/50/75/100. Left spine off (markers at x near 0 must not touch it). Legend
  markers in grey #3B3B3B (filled) / hollow grey, lower-right empty region, no frame.
- No caption text, titles, n-lists or statistics in the image (the fact counts in (b) row labels are requested by
  the outline). Save PNG (dpi 300) and PDF beside it.

## Final layout (after the critic rounds)

- Canvas 5.5 x 2.36 in, saved with a tight bbox: PNG 1644 x 708 px at 300 dpi = 5.48 x 2.36 in; PDF 5.48 x 2.36 in.
  Prints 1:1 at \textwidth. Text: 7 pt everywhere, panel letters 8 pt bold (nothing below 7 pt).
- Panel widths incl. labels 1.60 / 1.60 / 2.02 in (about 1 : 1 : 1.26, not the outline's 1 : 1.1 : 1.4): (a) needs
  about 1.26 in of plot width so its three horizontal tick labels do not touch at 7 pt; (c) needs 0.8 in of row labels.
- (a) tick labels "Abstract / only", "Abstract + / second- / hand", "Full text" (line breaks only). Value labels
  with one decimal and %.
- (b) segment labels are integers without "%" (the axis label carries the unit) and are drawn only where the text
  plus 0.015 in each side fits inside the segment: drawn 76, 15, 26, 21, 53, 16, 77; not drawn 9 (full text, not
  stated, 140 facts) and 7 (title only, stated, 27 facts) -> those counts go in the caption. Legend (2 columns,
  reading order Stated, Partly stated, Not stated) left-aligned with the row labels at the top of the panel.
- (c) row label "Memory only / (control)" on two lines to keep the label column narrow; tick pad 6 pt so labels stay
  clear of hollow markers near x = 0; marker legend (dark grey filled = stated, hollow = not stated) lower right.
