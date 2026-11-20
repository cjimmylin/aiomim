# Plan: fig_memory_by_era (statistical plot, Appendix D, aspect 3:2)

## Planner: channels and data
Two line-and-marker panels stacked vertically, sharing one x axis.
- x: creation era of the entry, five ordered MIM-number bands at positions 0-4, joined by lines;
  then, after a visible gap and a grey dashed rule, a sixth unconnected position (x = 5.7) for the
  separate set of entries created in 2026 (a different sample, so not joined to the bands).
- y: percentage, mean over entries, 0-100.
- hue: strategy. Two strategies only: direct reading and the memory-only control.
- Marker fill: filled = era bands of the main set (log Sec. 2.11); hollow = 2026 set (log Sec. 10).
- Top panel: OMIM facts conveyed (%) (primary endpoint). Bottom panel: causal gene F1 (%).
- Tick labels carry the band range and the number of compared entries (n), as the outline asks.

### Data, experimental_log.md Sec. 2.11 "Memory-only control and direct reading by creation era (entry means)"
Columns used: "Entries", "Facts conveyed: memory / direct", "Gene F1: memory / direct".

| Era band (tick) | n (Entries) | Facts memory | Facts direct | Gene F1 memory | Gene F1 direct |
|---|---|---|---|---|---|
| classic (1xxxxx-5xxxxx) | 18 | 14.5 | 34.9 | 88.9 | 87.0 |
| 600000-609999 | 19 | 24.1 | 53.9 | 94.7 | 100.0 |
| 610000-615999 | 20 | 17.5 | 51.2 | 100.0 | 100.0 |
| 616000-619999 | 19 | 12.6 | 51.4 | 89.5 | 100.0 |
| 620000 onward | 17 | 5.7 | 53.5 | 41.2 | 100.0 |

### Data, experimental_log.md Sec. 10 "Entries created after the model's likely training data (June to November 2026)"
"20 of the run's 30 entries qualify"; headline metric table, columns "Direct reading" and "Memory only (control)",
rows "OMIM per-paper facts conveyed (primary endpoint)" and "Causal gene F1".

| Set (tick) | n | Facts memory | Facts direct | Gene F1 memory | Gene F1 direct |
|---|---|---|---|---|---|
| created 2026 | 20 | 7.0 | 52.2 | 30.0 | 100.0 |

24 plotted values in total. Sec. 2.11 gives no intervals, so no error bars. Sec. 10's paired
intervals are differences, not level CIs, so they are not drawn. Nothing else is plotted (no
claims-supported, inheritance or synopsis columns).

## Stylist
- Printed width: full text width, 5.5 in (ICLR \textwidth); figsize 5.5 x 3.67 in (3:2). Include
  with `width=\textwidth` so the print size equals the design size. At this width each band range
  fits on one tick line at 8 pt.
- Font: Liberation Sans (sans-serif), 8 pt for every text element (tick labels, panel headers,
  axis label, direct labels). Smallest text 8 pt (rule: none below 7 pt).
- Colours (brief from the orchestrator, one per strategy across figures): direct reading #0072B2,
  memory only #000000. Direct reading: circles, solid line; memory only: squares, solid line.
  2026 set: same colours, hollow (white-filled) markers.
- Coinciding points (bottom panel 610000-615999: both 100.0; classic 88.9 vs 87.0) are kept
  distinguishable by a small horizontal dodge (direct -0.07, memory +0.07 on the category axis);
  the dodge is not a data value.
- Direct labels in the top panel ("Direct reading", "Memory only") in each strategy's colour,
  no legend box.
- Panel headers at left ("OMIM facts conveyed (%)", "Causal gene F1 (%)") stand in for y labels.
- y ticks 0/25/50/75/100; thin light-grey horizontal grid; top/right spines removed; white
  background; no 3-D, no title, no "Figure N", no caption sentences or statistics in the image.
- Tick labels, two lines each: line 1 the band range, line 2 the n
  ("1xxxxx–5xxxxx" / "classic, n = 18"; "600000–609999" / "n = 19"; ...; "620000 onward" / "n = 17";
  "created 2026" / "n = 20"). x-axis label: "Creation era of the entry (MIM-number range)".
- Saved as PNG (dpi 300) and as a PDF beside it.
