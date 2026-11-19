# Plan: fig_memory_by_era (statistical plot, 16:10 (7.0 x 4.4 in), double-column width ~7 in)

## Planner: channels and data
Two panels stacked vertically (top: facts conveyed; bottom: gene F1) sharing one x axis.
(Revised from side-by-side after critic rounds 1-2: era tick labels overlapped at half width.)
- x: creation-era band of the entry (MIM-number range), five ordered categories, plus a sixth
  position to the right, separated by a vertical dashed rule, for the separate newest-entry set.
- y: percentage (entry means), 0-100.
- hue: strategy (memory only control vs direct reading).
- Top panel y: "OMIM facts conveyed (%)" (primary endpoint).
- Bottom panel y: "Causal gene F1 (%)".
- Era bands are joined by lines; the newest-entry set is an unconnected marker (different sample).

### Data, copied from experimental_log.md Sec. 2.11 (entry means; "Facts conveyed: memory / direct", "Gene F1: memory / direct")
| Era band | Entries | Facts memory | Facts direct | Gene F1 memory | Gene F1 direct |
|---|---|---|---|---|---|
| classic (1xxxxx-5xxxxx) | 18 | 14.5 | 34.9 | 88.9 | 87.0 |
| 600000-609999 | 19 | 24.1 | 53.9 | 94.7 | 100.0 |
| 610000-615999 | 20 | 17.5 | 51.2 | 100.0 | 100.0 |
| 616000-619999 | 19 | 12.6 | 51.4 | 89.5 | 100.0 |
| 620000 onward | 17 | 5.7 | 53.5 | 41.2 | 100.0 |

### Separate sample, experimental_log.md Sec. 10 (20 compared entries created June-November 2026; headline table)
| Set | Entries | Facts memory | Facts direct | Gene F1 memory | Gene F1 direct |
|---|---|---|---|---|---|
| created Jun-Nov 2026 | 20 | 7.0 | 52.2 | 30.0 | 100.0 |

No CIs are given in Sec. 2.11, so no error bars. Nothing else is plotted.

## Stylist
- White background, sans-serif (DejaVu Sans), tick labels 8 pt, axis labels 8.5 pt.
- Colours (Okabe-Ito): direct reading #0072B2 (circle markers, solid line); memory only (control)
  #D55E00 (square markers, solid line). Same colours for the newest set, hollow markers to mark
  the different sample.
- Thin light-grey horizontal grid only; top/right spines removed.
- One shared legend above the panels (single row); direct labels would collide with the separate-set markers.
- Figure 7.0 x 4.4 in. x tick labels (8 pt, bottom panel only): band range on one line (first band
  "classic (1xxxxx-5xxxxx)"), then "n=..."; newest set "created Jun-Nov 2026 (separate set) n=20",
  placed right of a grey dashed rule. x-axis label "Creation era of the entry (MIM-number range)".
- y labels name the measure: "OMIM facts conveyed (%)", "Causal gene F1 (%)"; y ticks 0/25/50/75/100.
- No caption or figure number in the image.
- No project, package or author names anywhere.
