# fig_access_strata — plan

## Planner

Type: forest plot (point estimate + bootstrap 95% interval), horizontal.

Source: experimental_log.md Sec. 2.9, table "OMIM facts conveyed" (paired difference from direct reading, percentage
points, strategy minus baseline, bootstrap 95% interval over entries); Sec. 4.2 for the replicate-noise half-width.

Channels
- x: paired difference from direct reading in OMIM facts conveyed (percentage points).
- y: access group (three blocks, top to bottom: no full text, under half full text, half or more full text), and
  within each block one row per strategy (evidence graph, agentic curator, case table first).
- hue: strategy (consistent colour per strategy).

Data points (copied exactly from Sec. 2.9, "OMIM facts conveyed"):

| Access group | Entries | Evidence graph | Agentic curator | Case table first |
|---|---|---|---|---|
| no full text (abstracts only) | 46 | -0.2 (-1.1 to +0.8) | -0.1 (-1.1 to +0.7) | +0.6 (-0.3 to +1.6) |
| under half full text | 25 | -0.7 (-2.6 to +1.3) | -0.4 (-1.6 to +0.8) | -4.0 (-6.3 to -2.0) |
| half or more full text | 21 | -1.8 (-4.4 to +0.7) | -2.0 (-3.4 to -0.7) | -6.1 (-8.3 to -3.6) |

Note: the outline's objective quotes case table first as (-6.2 to -2.0) and (-8.4 to -3.7); the log says
(-6.3 to -2.0) and (-8.3 to -3.6). The log values are used.

Off-scale (text note inside the axes, not on the main axis), Sec. 2.9:
- Memory only (control): -18.1, -41.7, -59.6
- Recall, then verify: -19.1, -42.5, -58.7

Omitted: "all full text" group (1 entry, no interval; marked † in the log).

Reference elements
- Vertical line at 0 (no difference from direct reading).
- Shaded band at ±1.0 point: replicate-noise 95% half-width on a difference between two strategies over 93 entries
  (Sec. 4.2). A lighter band at ±1.8 points, the same quantity over 30 entries (Sec. 4.2), because the groups have
  21–46 entries, so the 93-entry band understates the noise for them. Both values are stated in the log.

## Stylist

- White background, sans-serif (DejaVu Sans), all text ≥ 8 pt at 7 in width; double-column, 16:9 → 7.0 × 3.94 in.
- Colours (Okabe–Ito): evidence graph #0072B2, agentic curator #009E73, case table first #D55E00
  (memory only #CC79A7, recall then verify #E69F00, direct reading #000000 if other figures need them).
- Markers: filled circle, 2.0 pt-wide error bars with small caps; zero line solid black 0.8 pt; noise bands grey
  (alpha 0.18 for ±1.0, 0.08 for ±1.8), labelled directly at the top of the axes.
- Group labels on the y axis with n; thin dotted separators between groups; light vertical grid only.
- Legend above the axes: row 1 the three strategies, row 2 the two noise bands (direct labels would repeat three times).
- Value labels to the right of each interval, with a true minus sign.
- Off-scale values: small grey text box at the left of the plot.
- No title inside the image; no caption text.

## Legibility revision (print size)
- 2.75 x 2.4 in (beside fig_memory_by_era, same height). Legend inside the empty upper left; noise bands labelled directly (±1.0, ±1.8) instead of legend entries; value labels in dark grey; off-scale note for memory only and recall, then verify removed from the image (values kept as a comment in plot.py, caption carries them); group label 'No full text' (was 'No full text (abstracts only)').
- Font Liberation Sans in all five figures; every text element 7 pt at print size (panel headers 7.5 pt); figsize equals printed width; saved at dpi 300 without bbox cropping so the PNG is exactly the printed size. Strategy colours shared by all figures (Okabe-Ito): direct reading #0072B2, agentic curator #56B4E9, evidence graph #009E73, case table first #D55E00, recall then verify #E69F00, memory only #000000. Outcome categories (fig_hidden_fulltext, fig_missed_facts) use greys plus #F0E442 (missed although in text) and #CC79A7 (contradicted), so no strategy colour means anything else. Data values unchanged.
