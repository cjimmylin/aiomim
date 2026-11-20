# Plan: fig_overview (diagram, full text width 5.5 in)

Sources: outline.json plotting_plan entry `fig_overview`; idea.md "Core idea", "Formal setup", "Design rationale";
experimental_log.md Sec. 1.1 (task, data, reference), 1.3 (strategy table, guards), 1.4 (audit, scoring),
Sec. 15 (the four reading-better arms D1-D4); notes.md "Words to use", "Claims the paper must not make", "Figures".
No project, package, author or model names. Nothing is plotted from numbers; the diagram carries no statistics.

## Planner: elements, labels, connections (left to right, plus a bottom band)

### Column A, header "Input (same for all)" (idea.md Formal setup; log 1.1 "Input to every strategy")
- Outer frame titled "Entry e = (h, R)" (idea.md: e = (h, R)).
- Box "Header h": "number, title, alternative titles" (log 1.1, idea.md Task).
- Box "Cited papers R": three page icons, one per access level a(d) in {full text, abstract, title}
  (idea.md Formal setup), drawn with many / few / no body lines and labelled "full text", "abstract", "title";
  a vertical ellipsis between the second and third icon (more papers). Two lines below:
  "access level a(d), set by open access" (idea.md "Access ... depending on open access").
- Padlock icon with grey text "causal gene withheld" (log 1.1 "The causal gene is withheld"); no strike-through.
- No indices (d1 ... dn) because subscripts would fall below 7 pt.
- Arrow A -> B into a bracket that spans every strategy group (the same input reaches every strategy).

### Column B, header "Strategy (the only variable)" (log 1.3 table; idea.md Core idea; notes.md framing)
Paradigm groups (neutral grey boxes), strategy pills with a colour dot and edge in the strategy's colour; add-ons
are dashed grey pills with "+", hung by a tree connector under their parent (log 1.3 "Add-on to ..."):
- "Read and write": "Direct reading (baseline)"; + "Second-hand evidence" (dashed); + "Learned curation guide"
  (dashed); solid sub-box "reading better" (log Sec. 15 arms D1-D4) listing "checklist", "completeness pass",
  "three-draft merge", "checklist + completeness pass", each with its own colour dot; then "Agentic curator".
- "Extract, then write": "Evidence graph"; "Case table first"; + "Reconciled case database" (dashed, under the case
  table).
- "Memory first": "Recall, then verify".
- "Control": "Memory only (no papers)".
- No count of strategies anywhere (notes.md: never "nine strategies").
- Bracket on the right of all groups, one arrow labelled "D" (the draft) to the audit.

### Column C, top: header "One audit, every draft" (log 1.4 Audit; idea.md Faithfulness)
White box, one step per line:
1. "paragraph -> atomic claims c, cited papers R(c)"
2. "-> verdict per cited paper + verbatim quote" (log 1.4: a "supported" verdict whose quote is not found
   verbatim in the paper is downgraded)
3. (indented) "supported / partly / unsupported / contradicted" (log 1.4 verdict set)
4. "-> best verdict over R(c)" (log 1.4 "A claim's verdict is the best over the papers it cites")
5. "-> one repair round for flagged claims" (log 1.4)
Arrow down to the scoring box.

### Column C, bottom: header "One scoring, every draft" (log 1.4; idea.md Coverage; notes.md Words to use)
- Reference sub-box (light fill): bold "Curator paragraph g", then the exact label split over two lines
  "curator-written per-paper text: OMIM / allelic-variant descriptions in ClinVar".
- Arrow down, side label "split once, without sight of any draft" (log 1.1 fixed fact lists).
- Box "fixed fact list Phi(g)" with a tag attached: "stated / partly / not stated in the supplied text"
  (log 2.10a: stored judgement, identical for every strategy).
- "-> each fact in the draft text citing the paper:" / "present / partly / absent / contradicted" (log 1.4).
- Bold "-> OMIM facts conveyed (primary)" / "(present + 0.5 x partly) / facts judged" (log 1.4: present + half of
  partial over facts judged; written "0.5 x" because a 1/2 glyph would print below 7 pt).
- Thin rule, then "secondary: HPO disease annotations, allelic variants, causal gene, inheritance"
  (log 1.4; notes.md: "HPO disease annotations", never "OMIM synopsis").

### Bottom band, full width: "Guards for every strategy" (log 1.3, last paragraph)
Four cells, two lines each: "ontology IDs only from ontology-search candidates" | "gene symbols normalised (HGNC)" |
"recalled cross-reference numbers removed" | "every paragraph cites a supplied paper".

### Left out of the image on purpose (caption carries them)
Counts (100 entries; 515 papers: 96 full text, 345 abstract, 74 title; 476 curator paragraphs; 6,652 fixed facts),
the add-on convention, "one model writes every draft", and every result.

## Stylist
- Size: 5.5 in wide (full text width) by the height the content needs at >= 7 pt (about 3.2-3.3 in; the outline's
  21:9 = 2.36 in cannot hold the required elements at 7 pt). Saved at dpi 300, bbox tight with 0.02 in pad; PNG and
  PDF.
- Font Liberation Sans (Arial metrics) as in the sibling figures; body 7 pt, column headers 7.5 pt bold; mathtext in
  Liberation Sans; no subscripts or fractions (they would print below 7 pt).
- White background, no grid, no shadows, no 3-D. Paradigm groups light neutral grey (#F1F1F1 fill, #B5B5B5 edge);
  reference boxes #F4F4F4; arrows and frames dark grey #222222.
- Strategy colours (orchestrator's binding palette, one per strategy across all figures): direct reading #0072B2,
  agentic curator #56B4E9, evidence graph #009E73, case table first #D55E00, recall then verify #E69F00,
  memory only #000000.
- Reading-better arms: the same colours as the sibling forest plot fig_design_vs_reading (blue family or grey, never
  another strategy's colour): checklist #8C8C8C, completeness pass #3D6F98, three-draft merge #555555,
  checklist + completeness pass #003A5E.
- Add-ons: dashed grey edge, no colour (no palette colour exists for them).
- Access-level icons black outline with grey body lines. Padlock and "withheld" text mid grey.
- No legend, no title, no caption or figure number inside the image.

## Revisions after critic rounds
- Round 1: page icons were blank (their body lines sat under the white page fill) -> lines drawn above the fill;
  Liberation Sans' arrow glyph prints tiny and on the baseline -> every in-text arrow drawn in DejaVu Sans with
  continuation lines indented to the text after the arrow; the "D" label was cramped against the fan-in bracket ->
  gap between strategy and audit columns widened from 0.14 to 0.20 in; "set by open access" sat 0.018 in from its box
  edge -> column A inner boxes widened; column A content ended 0.3 in above the others -> icon pitch and gaps
  increased, padlock centred in the remaining space; scoring frame bottom aligned with the strategy column.
- Round 2: content: "One audit, every draft" overclaimed (the memory-only control is audited without repair, log
  1.3; the reading-better arms were audited without repair on 20 of 41 entries, log Sec. 15) -> headers are the
  outline's "One audit" and "One scoring"; the exceptions go to the caption. Presentation: bbox tight with 0.02 in
  pad made the PNG 5.54 in wide, so 7 pt text would print at about 6.95 pt at text width -> saved with pad 0; the file
  is exactly 5.5 x 3.10 in (PNG 1650 x 930 px at 300 dpi; PDF 5.5 x 3.10 in, fonts embedded).
- Round 3: no changes needed.

## Final
5.5 x 3.10 in (about 16:9), smallest text 7.0 pt (body), headers 7.5 pt bold; 71 text elements, none overlapping,
none crossing a box edge (checked programmatically from the rendered text extents).
