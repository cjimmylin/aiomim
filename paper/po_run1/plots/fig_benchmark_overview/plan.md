# Plan: fig_benchmark_overview (diagram, 21:9, double column)

Sources: outline.json plotting_plan entry; idea.md "Core idea", "Formal setup", "Design rationale";
experimental_log.md Sec. 1.1 (counts), 1.3 (strategy table and guards), 1.4 (audit, scoring);
notes.md "Words to use" and "Claims the paper must not make". No project, package, author or model names.

## Planner: elements, labels, connections (left to right)

### Panel A, "Input: entry e = (h, R)" (idea.md Formal setup; log 1.1)
- Box "Header h": "number, title, alternative titles".
- Box "Cited papers R = {d1, ..., dn}" with three page icons, each tagged with its access level a(d):
  "full text", "abstract", "title" (idea.md: a(d) in {full text, abstract, title}).
- Struck-through tag "causal gene: withheld" (log 1.1 "The causal gene is withheld").
- Count line (log 1.1): "100 entries; 515 papers: 96 full text, 345 abstract, 74 title".
- Arrow A -> B labelled "same input to every strategy".

### Panel B, "Generation strategy (the only variable)" (log 1.3 table; notes.md framing)
Three paradigm boxes, one control box; add-ons drawn as small dashed attachments with a "+" to their parent:
- Paradigm "Read and write": "Direct reading" [+ "Second-hand evidence"] [+ "Learned curation guide"];
  "Agentic curator".
- Paradigm "Extract, then write": "Evidence graph"; "Case table first" [+ "Reconciled case database"].
- Paradigm "Memory first": "Recall, then verify".
- "Control": "Memory only (no papers)".
- Legend line: "+ dashed = add-on, tested against its parent".
- Band beneath all strategies, "Guards applied to every strategy": "ontology IDs chosen only from
  ontology-search candidates; gene symbols normalised against HGNC; recalled cross-reference numbers
  removed; every paragraph cites a supplied paper" (log 1.3 last paragraph).
- Arrow B -> C labelled "draft D".
- No count of strategies is written (notes: never "nine strategies").

### Panel C, "Shared audit and scoring" (log 1.4; idea.md Formal setup)
- Box "Claim-level audit (every draft)": three steps chained by arrows:
  "atomic claims" -> "verdict per cited paper + verbatim quote" -> "one repair round".
- Box "Scoring against the reference (every draft)": "OMIM facts conveyed (primary; fixed fact lists)",
  "HPO terms", "allelic variants", "causal gene", "inheritance".
- Box "Reference (public sources)" feeding the scoring box by an arrow:
  "curator-written per-paper text (OMIM allelic-variant descriptions in ClinVar)": 476 paragraphs, 6,652 facts;
  "HPO disease annotations": 2,311; "allelic variants": 427; gene map, inheritance modes (no count).
  All counts from log 1.1. Required wording from notes.md used verbatim.

## Stylist
- White background, no grid, no shadows, no 3-D. Font Liberation Sans (Arial metrics), body 8 pt, headers
  8.5 pt bold; figure 7.2 x 3.1 in (about 21:9) for a full-width figure.
- Colour per paradigm (Okabe-Ito, used as light fills with a darker edge): Read and write #0072B2,
  Extract then write #009E73, Memory first #E69F00, Control grey #999999; add-ons dashed edge in the
  parent's colour. Input panel and audit/scoring panels neutral grey outlines; primary endpoint in bold.
- Arrows thin dark grey. No legend box: add-on convention explained by a direct one-line note.
- No caption or figure number inside the image.

## Revisions after critic rounds
- Round 1: papers label shortened to "Cited papers R = {d_i}" (overflowed its box); struck-through
  "causal gene" replaced by plain "causal gene withheld"; Memory-first/Control split moved so
  "Memory only (no papers)" fits its pill; guards band re-wrapped into four lines in the log's wording
  ("ontology IDs chosen only from candidates returned by an ontology search ...") and enlarged so it no
  longer runs into the reference box; add-on convention note added.
- Round 2: add-on note reduced to one italic line "dashed = add-on to its parent" beside Agentic curator
  (two-line version touched the box edge); last reference line shortened to "causal gene; inheritance modes"
  (touched the right edge).
