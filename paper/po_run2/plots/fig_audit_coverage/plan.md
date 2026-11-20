# fig_audit_coverage — plan

## Planner

Purpose (outline, Sec. 4.5): which planted errors the claim-level audit flags, and which it cannot see by
design, with the unaltered controls. Cleveland dot plot, one row per class (qualifier class split by
deletion rule), rows grouped under headings by the outcome the design expects.

Visual channels
- y: one row per class / rule, grouped (top to bottom): errors the audit should catch; not visible to the
  audit by design; unaltered controls.
- x: share flagged by the audit, 0-100 %. Measure: item counts as flagged when at least one planted claim
  was judged unsupported or contradicted (log 14.4 'Audit on planted errors', column 'Planted claim
  flagged'; Sec. 11: "flagged all 60, each on a claim containing the altered value"). Where no planted claim
  exists (omitted finding) and for the controls, the paragraph-level count is used (column 'Paragraph
  flagged'; 'Control'). Wherever both are logged they are equal, so the x axis is labelled
  "Flagged by the audit (%)".
- right-hand annotation: k/n exactly as logged (n = truth-known items, or paragraphs for controls).
- marker: filled dark-grey circle = should be flagged; open square = not visible by design (outline);
  open circle = unaltered control.
- No intervals (none logged).

Every data point (k / n, % = k/n):

| Row label | k | n | % | Source |
|---|---|---|---|---|
| Single value altered | 60 | 60 | 100 | Sec. 11 'Planted errors' ("The audit flagged all 60, each on a claim containing the altered value") |
| Citation swapped, other entry | 30 | 30 | 100 | Sec. 14.4 'Audit on planted errors', C1, Planted claim flagged 30/30 (truth known 30) |
| Citation swapped, same entry | 26 | 26 | 100 | ibid., C2, 26/26 (truth known 26 of 30 items) |
| Sentence moved to other paper | 25 | 25 | 100 | ibid., C3 conflation, 25/25 (truth known 25 of 30 items) |
| Negation deleted | 8 | 8 | 100 | Sec. 14.4 'C5 by deletion rule', negation, Planted claim flagged 8/8 |
| Hedge deleted | 2 | 8 | 25 | ibid., hedge 2/8 |
| Count deleted | 1 | 4 | 25 | ibid., count 1/4 |
| Zygosity deleted | 0 | 8 | 0 | ibid., zygosity 0/8 |
| "One family/patient" deleted | 0 | 2 | 0 | ibid., single family or patient 0/2 |
| Irrelevant citation added | 0 | 30 | 0 | Sec. 14.4 'Audit on planted errors', C4 over-citation, Planted claim flagged 0/30 |
| Finding omitted | 0 | 30 | 0 | ibid., C6 omitted finding, Paragraph flagged 0/30 (planted claim n/a) |
| Control: single-value paragraphs | 0 | 60 | 0 | Sec. 11 'Audit control' ("0 of 60 had at least one claim flagged") |
| Control: other classes' paragraphs | 0 | 113 | 0 | Sec. 14.4 'Control' ("113 paragraphs, 0 flagged (0%)") |

Checks: C5 rules sum to 4+8+8+2+8 = 30 items and 1+2+8+0+0 = 11 flagged = C5 row 11/30 of the main table.
For every class with both columns, paragraph flagged = planted claim flagged (C1 30, C2 26, C3 25, C4 0,
C5 11).

Group headings (log wording): C4's and C6's expected outcome is a pass ("the claim takes the best cited
paper's verdict"; "the audit judges only what is written") -> heading "Not visible to the audit by design".
The remaining classes are planted errors the audit is meant to flag -> "Errors the audit should catch".
Controls -> "Unaltered control" (critic round 1 dropped "(re-audited)", which is caption material).

Deviation from outline: the outline lists one control (0/113); the single-value row (Sec. 11) has its own
control (0/60), which the section text also reports, so it is drawn as a second control row. Outcome-based
headings ('Caught' / 'Rarely caught') replaced by expectation-based headings at the orchestrator's request;
the outcome is read from the dots.

Not in the image (caption): 30 items per class, truth-known counts, rule sizes 2-8, swaps are easy cases,
not a sensitivity estimate, controls passed once before, all items in evidence-graph drafts.

## Stylist

- Print width 3.0 in (0.55 x 5.5 in text width), designed at 1:1 so pt sizes are final; saved image 2.98 x 2.52 in
  after tight crop (figsize 3.0 x 2.59; critic round 1 moved the k/n column left so the crop stays under 3.0 in); height ~2.6 in
  (13 rows + 3 headings need ~9.5 pt line pitch at 7 pt text; the outline's 4:3 would force ~8.5 pt pitch).
- Font: Liberation Sans (Arial metrics), sans-serif. Every text element 7 pt; headings 7 pt bold.
- Colours: greys only (no strategy colour; all items are evidence-graph paragraphs, but the figure compares
  error classes, not strategies). Markers #333333 (0.2 grey) filled / open; row guide lines 0.85 grey,
  0.5 pt; no other grid. Bottom spine only, 0.6 pt.
- Row labels left-aligned in a column, indented under left-aligned bold headings; k/n column at right,
  aligned on the slash.
- x ticks 0, 25, 50, 75, 100; xlim -6..106 so markers at 0 and 100 are not clipped.
- No title, no legend (headings + marker shapes suffice), no caption text in the image.
- Save PNG (PO_OUT, dpi 300, bbox tight) and PDF beside it (fonttype 42).
