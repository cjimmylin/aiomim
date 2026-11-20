# fig_design_vs_reading: plan (planner + stylist)

Main text, full text width (ICLR \textwidth = 5.5 in; include at width=\linewidth, scale 1.0).
Forest plot: point estimate with 95% percentile bootstrap interval over entries (10,000 resamples, seed 7)
as a horizontal whisker. Paired difference in OMIM facts conveyed (mean over entries, percentage points).

## Structure (two separate comparisons, never one shared row list)

Two blocks stacked vertically with a clear gap and a thin rule between them; each block has its own header,
its own x axis with tick labels, and its own x-axis label that names its baseline.

- Block a: header "a  Other designs, 93 entries"; x label "Difference from direct reading after repair
  (percentage points)". Baseline: direct reading after the audit's repair round (every strategy in the main
  comparison went through one repair round, log Sec. 1.4). Entry set: the 93 entries complete for every strategy
  (log Sec. 2.10a). Marker: circle.
- Block b: header "b  Ways of reading better, held-out entries with full text"; x label "Difference from direct
  reading before repair (percentage points)". Baseline: direct reading's draft before repair; no arm repaired
  (log Sec. 15 preamble). Entry set: 38 entries complete for D1-D3 (Sec. 15 "Improving on direct reading:
  evaluation"), 35 complete for all five arms for D4 (Sec. 15 "Extension: D4"). The entry count is in each row
  label; a dotted rule separates the D4 row (different entry set) from the three rows above it. Marker: diamond.

Facets (columns, same in both blocks, headers drawn once above block a):
"All facts" | "Stated, full-text papers" | "Stated, abstract-only papers" | "Not stated".
Row labels drawn once per block at the left. One shared x range in every panel: -15.5 to +10.5, ticks -10, -5,
0, +5 (gridlines also at -15 and +10 unlabelled), vertical line at 0 in each panel.
No equivalence band, no replicate-noise band. No numeric labels (they do not fit without overlap at this
scale; values are in the caption/text and listed below).

## Every data point (mean [95% interval lo, hi]); copied exactly from experimental_log.md

### Block a: log Sec. 2.10a, table "Difference from Direct reading" (summary, lines 354-360), cross-checked
against the per-restriction tables "All facts (unrestricted), all papers", "Facts stated in the available text,
papers readable in full", "... papers readable as abstract only", "Facts not stated in the available text, all papers"

| Row | All facts | Stated, full-text papers | Stated, abstract-only papers | Not stated |
|---|---|---|---|---|
| Agentic curator | -0.6 [-1.3, +0.0] | -0.2 [-1.8, +1.2] | -0.8 [-2.6, +0.5] | -0.5 [-1.8, +1.0] |
| Evidence graph | -0.5 [-1.5, +0.5] | +1.7 [-0.7, +4.0] | -0.5 [-2.5, +1.2] | -1.4 [-3.4, +0.7] |
| Case table first | -1.9 [-3.1, -0.7] | -8.4 [-14.3, -3.8] | -1.6 [-3.6, +0.2] | -1.0 [-3.1, +1.2] |
| Entries with such facts (n) | 93 | 40 | 79 | 90 |

### Block b: log Sec. 15
D1-D3 from "Improving on direct reading: evaluation" tables "All facts", "... on papers readable in full",
"... on papers readable as abstract only", "Facts the supplied text does not state".
D4 from the Extension tables "D4: All facts", "D4: ... on papers readable in full", "D4: ... on papers readable
as abstract only", "D4: Facts the supplied text does not state", row "D4 - baseline (primary)".

| Row | All facts | Stated, full-text papers | Stated, abstract-only papers | Not stated |
|---|---|---|---|---|
| Checklist (38) [D1] | +1.6 [+0.5, +2.7] | +2.0 [+0.4, +3.7] | +0.2 [-1.0, +1.3] | -0.3 [-1.9, +1.3] |
| Completeness pass (38) [D2] | +2.6 [+1.7, +3.6] | +4.5 [+2.9, +6.3] | +1.0 [-0.3, +2.9] | -0.1 [-1.3, +0.7] |
| Three-draft merge (38) [D3] | +3.1 [+2.1, +4.2] | +3.7 [+2.1, +5.5] | +1.0 [+0.1, +2.1] | +1.5 [+0.4, +2.7] |
| Entries with such facts, D1-D3 (n) | 38 | 34 | 31 | 36 |
| Checklist + completeness pass (35) [D4] | +3.3 [+2.0, +4.7] | +6.3 [+4.0, +8.7] | +1.5 [-0.6, +3.9] | +0.2 [-1.2, +1.8] |
| Entries with such facts, D4 (n) | 35 | 32 | 28 | 33 |

Not drawn: memory only (control) and recall, then verify, off scale in block a (Sec. 2.10a: -34.0 to -77.6 on
these four restrictions); the caption says so. The "Stated" (all papers) and "Stated or partly" restrictions are
not drawn (not among the four facets). Per-panel n are in the caption, not in the image.

## Style (stylist)

- White background; sans-serif (Liberation Sans / Arial); every text element >= 7 pt at 5.5 in width
  (ticks and row labels 7 pt, column and block headers 7.5 pt, block letters bold).
- Colour per strategy, as given by the orchestrator's shared palette (identical in every figure):
  agentic curator #56B4E9, evidence graph #009E73, case table first #D55E00 (direct reading #0072B2 is the
  baseline, drawn as the zero line in black as in the house style).
- Reading-better arms, variants of direct reading (blue-family or grey, never another strategy's colour):
  arms that include the completeness pass in dark blues, arms without it in greys (rule by construction,
  not by result): checklist #8C8C8C, completeness pass #3D6F98, three-draft merge #555555,
  checklist + completeness pass #003A5E. None equals #0072B2, #56B4E9 or #000000.
- Markers: circles (block a), diamonds (block b); whiskers 1.1 pt with small caps.
- Thin light x grid (0.9 grey, 0.4 pt), no top/right spines, no legend (rows are directly labelled), no title,
  no caption text, no "Figure N".
