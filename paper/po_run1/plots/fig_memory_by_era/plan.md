# Plan: fig_memory_by_era (statistical plot, 16:9, double-column width ~7 in)

## Planner: channels and data
Two panels side by side, shared x layout.
- x: creation-era band of the entry (MIM-number range), five ordered categories, plus a sixth
  position to the right, separated by a vertical dashed rule, for the separate newest-entry set.
- y: percentage (entry means), 0-100.
- hue: strategy (memory only control vs direct reading).
- Left panel y: "OMIM facts conveyed (%)" (primary endpoint).
- Right panel y: "Causal gene F1 (%)".
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
- White background, sans-serif (DejaVu Sans), tick labels 8 pt, axis labels 9 pt.
- Colours (Okabe-Ito): direct reading #0072B2 (circle markers, solid line); memory only (control)
  #D55E00 (square markers, solid line). Same colours for the newest set, hollow markers to mark
  the different sample.
- Thin light-grey horizontal grid only; top/right spines removed.
- Direct labels at the right end of the left panel's lines instead of a legend box would collide
  with the separate-set markers; use one shared legend above the panels (single row).
- x tick labels: two lines, band range and "n=..."; newest set labelled "Jun-Nov 2026\n(separate set,\nn=20)".
- Each panel titled with its measure; no caption or figure number in the image.
- No project, package or author names anywhere.
