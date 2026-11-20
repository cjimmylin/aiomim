# Number and claim check, refined_v5 against the experimental log

Inputs: `paper/po_run1/final_paper.tex` (before), `paper/po_run1/latex/refined_v5.tex` and `refined_v5.pdf` (after),
`raw_materials/experimental_log.md` (sections 4.2, 11, 13, 14.1-14.4), `raw_materials/notes.md`,
`docs/experiments-round2.md`, `lit/citation_map.json`. I made my own diff of the old and new versions (main text and
appendix). The worklog was read only to locate changes, not taken as evidence.

## Counts

| Item | Count |
|---|---|
| Numeric tokens in new or changed text | 2,257: 184 in the main text (abstract, takeaways, Sec. 4.4 and Table 3, padding and large-entry paragraphs, audit paragraph, Discussion, Limitations, Conclusion, Reproducibility), 50 in the new Appendix A rows, about 2,020 in Appendix J (every table cell, plus version strings and default values in the settings tables) |
| Number-bearing statements with a problem | 5 |
| Everything else | matches the log (value, sign, interval, n, b/w/t, what it describes, pooled or mean, before or after repair) |
| Problems: wrong | 1 |
| Problems: unsupported | 0 |
| Problems: inconsistent | 4 |
| Problems: wording | 11 |

Appendix J tables: I compared every cell of Tables 31-47 (all of them, not a sample), plus every caption and column head,
against the log tables they come from. Apart from P1 below, every cell matches.

## Problems

Line numbers refer to `latex/refined_v5.tex`.

| # | Severity | Location | Paper says | Log says | Correction (old → new) |
|---|---|---|---|---|---|
| P1 | **wrong** | App. J.4, caption of Table `tab:app_audit_classes` (l. 1602) | For truth-unknown moved sentences, "the control's analogue of the planted claim flagged 4 of 5" | 14.4: "C3 truth unknown …: 5 items, paragraph flagged 5, planted-claim-analogue flagged 4/5". This analogue is in the **altered** paragraph. The control, which is all 113 unaltered paragraphs, had 0 paragraphs and 0 of 733 claims flagged, so a control figure of 4 of 5 is impossible. It also contradicts the paper's own "no unaltered control was flagged (0 of 113)". | "(paragraph flagged 5; the control's analogue of the planted claim flagged 4 of 5)" → "(paragraph flagged 5; claims naming the moved variant flagged in 4 of 5)" |
| P2 | **inconsistent** | Sec. 4.5 padding paragraph (l. 248); App. J.2 Design (l. 1415) | It reports only the largest-size change for direct reading (+3.2, −0.7 to +6.8) and calls the rise "within run-to-run noise (single-entry coverage varies by about 4 points between runs …), not a gain" | 14.2 6-entry table: at P1, direct reading +3.6 (**+1.0 to +5.9**, interval excludes zero), 5/1/0, p = 0.22. At P2, +3.2 (−0.7 to +6.8). The interaction at P1 is −2.8, −3.8 and −4.6, all three intervals excluding zero. The "about 4 points" figure is from 14.2's decision bullet, but log 4.2 (and the paper's own Table `tab:app_stability`) gives a within-entry SD of **2.5** for direct reading; 4.0 is the evidence graph's. Sec. 3.3 and App. E state that "the interval … [is] the test of a difference", and notes.md says replicate noise "is a yardstick, not a test". | Main text: "No strategy lost more than about a point from no padding to the largest input (case table first $-0.9$, $-2.1$ to $+0.1$; direct reading $+3.2$, $-0.7$ to $+6.8$; Appendix Table~\ref{tab:app_pad_cov}); direct reading's rise is within run-to-run noise (single-entry coverage varies by about 4 points between runs; the unpadded drafts are an earlier generation), not a gain." → "No strategy lost more than about a point at either size (case table first $-1.0$, $-2.1$ to $+0.0$, and $-0.9$, $-2.1$ to $+0.1$; Appendix Table~\ref{tab:app_pad_cov}). Direct reading rose by $+3.6$ points ($+1.0$ to $+5.9$) and $+3.2$ ($-0.7$ to $+6.8$), better on 5 of 6 entries at each size (sign test $p=0.22$); the unpadded drafts are an earlier generation with no replicate, so we do not read the rise as a gain, and the wider gaps to direct reading at the first size come from it." App. J.2: "Run-to-run variation of single-entry coverage is about 4 points (within-entry standard deviation in the replicate runs), so changes of a few points over 6 entries are within noise." → "The unpadded drafts are an earlier generation with no replicate, so a change from P0 mixes input size with run-to-run variation (within-entry standard deviation of single-entry coverage in the replicate runs: 2.5 points for direct reading, 4.0 for the evidence graph; Table~\ref{tab:app_stability})." |
| P3 | **inconsistent** | Table 3 caption (l. 207) | The caption says "(means over entries, \%; …)" for the whole table, including the "Supp." column | 14.3 audit table: counts pooled over claims (PaperQA2 780/853 = 91.4%). Appendix Table `tab:app_ext_audit` correctly says "pooled claims". notes.md requires stating pooled or mean for every level. | "Supp.: claims judged supported, audit without repair." → "Supp.: claims judged supported, pooled over claims, audit without repair." |
| P4 | **inconsistent** | Sec. 4.4 (l. 229) | "they wrote more text at several to many times the calls and cost" | 14.3: the strategies' drafts compared are after repair, and their audit and repair add 6.5-7.5 calls and \$0.93-\$1.21 per entry (the Table 3 caption says so). Counting that round, the strategies cost \$1.29-\$2.09 per entry against PaperQA2's \$2.17, which is 1.0-1.7 times, not "several". The multiple holds for generation alone. Repair moves coverage by about 0.2 points, so a comparison of generation cost alone is defensible, but the text must say so. | "at several to many times the calls and cost" → "at several to many times the generation calls and cost" |
| P5 | **inconsistent** | Sec. 4.6 (l. 256) | "(30 items each …) … every variant-naming sentence moved into another paper's paragraph (25 of 25)" | 14.4: 30 moved sentences, of which 25 have known truth. Five have unknown truth, and the planted-claim analogue was flagged in 4 of those 5. The same sentence labels C2's base ("26 of 26 with known truth") but not C3's. | "(25 of 25)" → "(25 of 25 with known truth)" |
| W1 | wording | Abstract (l. 36), Takeaway (3) (l. 114), Conclusion (l. 270), contribution (2) (l. 59) | "released PaperQA2 and GraphRAG pipelines"; Takeaway (3) uses the generic present tense "convey" | notes.md: "Name them as run: PaperQA2's document-query pipeline (without its agent), GraphRAG with local search". Sec. 4.4 does this. | Abstract: "released PaperQA2 and GraphRAG pipelines conveyed" → "PaperQA2's document-query pipeline (without its agent) and GraphRAG's local search conveyed". To stay within 200 words, also change "are within about a point of one another, our case-table-first implementation trails them" → "are within about a point, our case-table-first implementation trails" (198 → 199 words). Takeaway (3): "Released PaperQA2 and GraphRAG pipelines convey fewer facts" → "On these entries and settings, PaperQA2's document-query pipeline and GraphRAG's local search conveyed fewer facts". Conclusion: "released PaperQA2 and GraphRAG pipelines conveyed" → "PaperQA2's document-query pipeline (without its agent) and GraphRAG's local search conveyed". |
| W2 | wording | Takeaway (4) (l. 114) | "Unrelated padding costs no strategy more than about a point" | 14.2: this holds with losses of added papers allowed (6 entries). Under the symmetric rule (2 entries), case table first is −3.0 at both sizes. The paper discloses this in Sec. 4.5. | "Unrelated padding costs no strategy more than about a point;" → "Unrelated padding costs no strategy more than about a point (6 entries, losses of added papers allowed);" |
| W3 | wording | Sec. 4.4 (l. 204) | "through a local adapter:" (the term is never explained) | 14.3: a local server in front of the command-line model | "through a local adapter:" → "through a local adapter (a local server that relays each system's model requests to the command-line model):" |
| W4 | wording | Discussion (l. 262) | "test a released pipeline with its intended model, on which it depends …" | notes.md allows a portability finding but says not to give a cause for the stops. "Intended model" implies STORM failed because it was not run with its intended model, and reads as advice against the study's own fixed-model design. | "and test a released pipeline with its intended model, on which it depends in ways a model-agnostic description hides (STORM could not run here)." → "and check that a released pipeline runs with the model it will be used with, since pipelines depend on the model behind them in ways a model-agnostic description hides (STORM could not run here)." |
| W5 | wording | Discussion (l. 262) | "nor did released pipelines of two of these designs do better" ("these" has no antecedent in the section) | — | "released pipelines of two of these designs" → "released retrieval-augmented and graph-based pipelines" |
| W6 | wording | App. J.1 (l. 1228), J.4 (l. 1599, l. 1631) | Process jargon: "the ledgers tally 698 calls, including … a smoke test"; "in one holder"; "after reading the built edits"; "the selector of planted claims"; "the decomposer attributed" | — | "(the ledgers tally 698 calls, including the global-search queries and a smoke test)" → "(698 calls were made in all, including the global-search queries and a test run)"; "the audit run in chunks rather than in one holder" → "the audit run on chunks of 5 paragraphs rather than on all items together"; "after reading the built edits" → "after reading the edits they produced"; "the selector of planted claims for deleted qualifiers was widened" → "the rule that picks the planted claims for deleted qualifiers was widened"; "the decomposer attributed 176" → "the claim-splitting step attributed 176" |
| W7 | wording | App. J.4 (l. 1599); Tables `tab:app_pad_cov`, `tab:app_pad_cov2` | "\$43.7849"; p-values to 4 decimals ("0.2188", "0.6875") while every other table uses 3 | Values are correct (14.4, 14.2) | "\$43.7849" → "\$43.78"; "0.2188" → "0.219", "0.6875" → "0.688" |
| W8 | wording | Sec. 4.2 (l. 166), Sec. 4.3 (l. 200), App. J | The cuts removed the only references to Appendix Tables `tab:app_stated` and `tab:app_abl_means`. Nine new App. J tables are never referenced by number (`app_ext_strat`, `app_ext_cost`, `app_ext_audit`, `app_pad_size`, `app_pad_completion`, `app_pad_cost`, `app_audit_rules`, `app_audit_complete`, `app_audit_precision`). | — | Sec. 4.2: "the evidence graph's step is not distinguishable from zero (Appendix~\ref{app:ablation})" → "… (Appendix Tables~\ref{tab:app_abl_means}--\ref{tab:app_abl_diff})". Sec. 4.3: "On stated facts (Table~\ref{tab:stated})," → "On stated facts (Table~\ref{tab:stated}; counts in Appendix Table~\ref{tab:app_stated}),". Reference each J table once in its subsection's text. |
| W9 | wording | App. J.2 (l. 1417) | "Direct reading's prompt cut each paper to 75,000--300,000 characters at P0 … and to 33,333--66,666 at P1" | 14.2 caps: these are per-paper cap ranges. Only 1 own paper at P0, and 2 own plus 24 added papers at P1, were actually cut. | "cut each paper to 75,000--300,000 characters at P0 (one own paper cut) and to 33,333--66,666 at P1" → "capped each paper at 75,000--300,000 characters at P0 (one own paper cut) and at 33,333--66,666 at P1" |
| W10 | wording | App. I.3 (moved from the main text) | The draft–reference disagreements now take two sentences | notes.md: "may be mentioned in one sentence as such, with no entry named". No entry is named, and the numbers match log 11. | "…13 could not be decided from the readable text. These are unconfirmed leads: no curator has checked them, many rest on abstracts only, and the judge had already passed the same claims." → "…13 could not be decided from the readable text; these are unconfirmed leads (no curator has checked them, many rest on abstracts only, and the judge had already passed the same claims)." |
| W11 | wording | Sec. 4.6 (l. 256) | "30 items each" and then "16 of 29 planted deletions", with no reason given for 29 | 14.4: 2 safety-filter stops on one item | "for 16 of 29 planted deletions" → "for 16 of 29 planted deletions (one stopped by the safety filter)" |

## The questions asked in the brief

**The padding result (P2).** The treatment is not fully fair.
- The main text reports only the largest size (+3.2, interval including zero) and calls the rise noise. It leaves out that at the first size the interval over entries excludes zero (+3.6, +1.0 to +5.9). The sign test does not reach significance (5/1/0, p = 0.22).
- The "about 4 points" used to justify "noise" is the evidence graph's within-entry SD. Direct reading's is 2.5 (log 4.2; paper Table `tab:app_stability`). Direct reading's replicate means moved by at most 1.2 points between runs.
- The defensible reason for not calling the rise a gain is a different one: P0 is an earlier generation with no replicate, so a shift between generation runs cannot be separated from the effect of size. The proposed wording keeps notes.md's "do not call it a gain" and reports both sizes.
- "No strategy lost more than about a point" is correct for the 6-entry table: the worst is case table first, −1.0 at P1 and −0.9 at P2. Under the symmetric rule (2 entries, disclosed), case table first lost 3.0 points.
- notes.md is internally in tension here. Its round-2 instruction says to write "within run-to-run noise", while the earlier instruction says "Do not write 'within' … the half-width as if it were a significance threshold". Log 14.2 also conflicts with log 4.2. Both are flagged under "Outside the brief" below.

**Released systems: stated versus unstated facts.** The paper says both systems "fall short mainly on facts the supplied text states". This is supported:
- PaperQA2 (10 entries): −18.4 points on stated facts (−25.5 to −10.7) against −5.7 on facts the text does not state (−11.5 to −0.4).
- GraphRAG local (4 entries): −23.0 on stated facts against +1.1.
- Weighting by the share of stated facts (about 65%), roughly 12 of PaperQA2's 14.5-point shortfall is on stated facts. "Mainly" is the right strength. The design document's stronger "not on facts they do not" would overstate the PaperQA2 case, because PaperQA2 is also lower on unstated facts (6.2% against 11.8%).

**Audit-class counts and the base each is over.** All main-text counts match log 14.4, and every one is over items with known truth:
- Swap to another entry: 30/30.
- Swap within the entry: 26/26 (labelled as known truth).
- Moved sentence: 25/25 (base not labelled; P5).
- Negation: 8/8. Hedge: 2/8. Count, zygosity or one family: 1/14.
- Added citation: 0/30. Omission: 0/30.
- Controls: 0 of 113 unaltered paragraphs.
- Citation precision 4-7% for the four reading strategies. Recall, then verify (3%) is correctly left out, because Sec. 3.2 defines the reading strategies as four. The memory-only control is 27%.
- Completeness check: 16 and 24 of 29, against 0 and 2 of 29 unaltered; 24 of 60 natural omissions; about 10.1 listed per paper, 20% matching a curator fact.

The only wrong count statement is the appendix caption in P1.

**Other qualitative statements, at the strength stated.**
- "not a ranking … says nothing about their published results": pass.
- "caught" (swaps, moved sentences, negation): pass. The paper also says these are easy cases.
- "rarely" (2 of 8; 1 of 14): pass.
- "4 entries admit no test (smallest p 0.125)": pass.
- "fewer of their claims were judged supported" (91.4% and 89.8% against 96.5-98.6%, all without repair): pass.
- "one-call strategies lose whole entries, per-paper strategies lose papers": pass. Case table first also lost one whole entry when its writer was stopped, which the appendix shows.

## Citations for the three named systems

| System | Key | Supported by its abstract? |
|---|---|---|
| PaperQA2 | `skarlinski2024language` | Yes. The abstract introduces PaperQA2, an agent that writes cited Wikipedia-style summaries. Describing the run as "without its agent" is consistent with this. |
| GraphRAG | `edge2024local` | Yes. The abstract introduces GraphRAG. "Local search" is a setting of the released package, and the paper does not attribute it to the abstract. |
| STORM | `shao2024assisting` | Yes. The abstract describes Wikipedia-like articles grounded on Internet sources. |

The Related Work sentences about the three works are unchanged from the earlier version and supported. Nothing new is
said about these works beyond the names, the versions run and the settings. No citation key was added. 29 keys were
dropped together with whole clauses of Related Work and the introduction; none of the remaining sentences changed what
they say about a cited work.

## Cut text, dangling references, jargon, anonymity

- No undefined `\ref` and no "??" in the PDF text.
- Tables that lost their only reference: `tab:app_stated` and `tab:app_abl_means` (W8). No figure lost its reference.
- Labels placed inside bold paragraphs (`sec:ablation`, `sec:memory`, `sec:addons`, `sec:size`) resolve to their subsection, which is correct for the Appendix A "Where" column.
- The era-band definitions were cut from Sec. 3.1 ("classic band" is used in Sec. 4.2). Figure 5's axis shows them (classic, 600-609, …), so I did not count this as a problem.
- No code names in the text (`direct`, `kg`, `cohort`, `paperqa_pooled`, file names, `.py`, `.tsv`, "salt", "worker", "shim" all absent). "Adapter" is unexplained in the main text (W3). Process jargon remains in App. J (W6).
- Anonymity: the PDF shows "Anonymous authors / Paper under double-blind review". There are no URLs, the code package name does not appear, and the project's tracking header is described only as "a bookkeeping header". Package names and versions appear, which is allowed. The `\author{}` block in the source holds the template placeholder, which the anonymous style hides; it is unchanged from before.

## Abstract

- 198 words, split on whitespace (204 if hyphenated compounds are split). This meets the limit of 200.
- Every statement in it is supported:
  - 79.8% → 36.1% is a mean over entries, from the hidden-full-text experiment.
  - "More than nine in ten" stated facts: 91.0-94.4% for the four reading strategies. "Under 7%" of unstated facts: 5.5-6.9%.
  - Three strategies within 0.7 points; case table first trails; memory far behind.
  - PaperQA2 and GraphRAG lower on 10 and 4 entries at higher cost. Cost is higher even when audit and repair are counted ($2.17 against $1.29 for direct reading).
  - STORM 0 of 10.
  - The asymmetric completion rule gave 2.1 points, which is larger than every difference between reading strategies.
  - One model family wrote, audited and judged everything.
- The only issue is naming (W1).

## notes.md checklist

### "Added after the second round of experiments"

| Item | Result |
|---|---|
| Small scale stated once where the section starts (4-10 entries, 30 items per class, directions and large effects only) | PASS (Takeaways, l. 114; also App. J intro) |
| Input size: about 500,000 and 1,200,000 characters; three prompts and a merge; no strategy lost more than about a point; direct reading lost nothing | PASS |
| Input size: added papers off-topic and ignored (no draft cited one; the agent opened few or none); tests size, not crowding | PASS |
| Input size: direct reading's rise "within noise", not called a gain | PASS as instructed, but see P2 (the stated reason conflicts with the log's replicate data, and the P1 interval goes unreported) |
| Input size: per-paper losses allowed; symmetric rule leaves 2 entries; no general claim that size does not matter | PASS |
| Large entries: 4 entries with 76-148 references; at least one strategy stopped on every entry; no new entry compared; a finding about completion; large relevant sets untested and kept as a limitation; 5-10% of references scored | PASS |
| Released systems: named as run | PASS in Sec. 4.4; abbreviated in abstract, takeaways and conclusion (W1) |
| Released systems: versions in appendix; same papers and model through a local adapter; one setting with own code, prompts and defaults; table of changed settings | PASS |
| Released systems: six questions; one small local embedding model; interface ignores temperature and length limits; PaperQA2's agent needs function calling | PASS |
| Released systems: GraphRAG on the first four of a seeded order within the budget; strategies repaired, systems not | PASS |
| Released systems: allowed claim only; no ranking, no "poor systems", nothing about published results; only PaperQA2 passes a test | PASS |
| Released systems: "several to many times the cost" | Needs a scope word (P4) |
| STORM: could not run; every chain-of-thought prompt stopped, plain prompts answered; nothing reworded or retried; no cause given; portability finding | PASS (phrasing W4) |
| Audit coverage: six classes, 30 items, controls; caught and not-caught lists as specified | PASS |
| Audit coverage: easy cases; 2-8 items per rule; natural over-citation with the repair-round exclusion caveat; completeness check is the same model and lists many items not recorded; fidelity, not correctness | PASS |
| Limitations: (i) unchanged and first | PASS (text identical to before) |
| Limitations: input-size item rewritten; audit item rewritten; released-systems item added | PASS ((viii), (ix), (x)) |

### "Claims the paper must not make"

All twelve PASS. None is made:
- method matters little in general;
- evidence graph lower overall;
- large-entry tier as a finding (only completion is presented as a finding, and 152700's coverage is "one entry, not a result");
- verification after recall cannot help;
- a learned guide cannot help (framed "at this scale");
- structure pays;
- OMIM is wrong;
- the audit establishes correctness;
- the results are free of memorisation;
- human validation;
- generality across models;
- promises of experiments not run.

### "Limitations that must appear"

All nine PASS:
- one model family and no human validation (i);
- indirect, narrow reference (ii);
- oracle reference lists, with retrieval tested on ten entries (iii);
- open access only, no supplements (iv);
- variants not validated and inheritance compared as coarse classes (v);
- no separate development set (vi);
- stopped replies uneven (vii);
- few-reference entries dominate, with large inputs reframed (viii);
- list-price cost (xi).

Nothing required was lost in the cuts.

### Earlier rounds, re-checked on the new text

- "Replicate noise is a yardstick, not a test": violated in spirit by the padding paragraph (P2).
- "Planted-error test is not a sensitivity estimate": PASS.
- "Unsupported is not wrong": PASS.
- Aggregation stated for every level: Table 3's "Supp." column is mislabelled (P3). Everything else PASS.

## Outside the brief (flagged, not fixed)

- Log 14.2's decision bullet ("Run-to-run variation of single-entry coverage is about 4 points … so changes of a few points over 6 entries are within noise") conflicts with log 4.2 (direct reading 2.5, evidence graph 4.0). notes.md's round-2 instruction repeats the conclusion.
- The design document's results give A2 685 new calls; log 14.2 says 683. The paper uses 683.
- The design document's round summary uses ratios ("25 to 80 times as many calls", "5 to 33 times the cost") and a round total of 4,591 calls that are not in the log. The paper correctly does not use them.

## Could not check

- That the package versions were the latest released at run time ("installed … at its latest released version", App. J.1). The log gives the versions but not that they were the latest.
- Direct reading's P2 "three prompts and a merge". Log 14.2 records only `"prompts": {"3": 6}`, while 14.1's "prompts" column counts batches plus the merge. Entry 611521 (1,237,103 characters, no cuts) needs at least three 600,000-character batches, so three batches plus a merge is the consistent reading. I inferred this; I did not verify it directly.
- The underlying result files (`results/*/…md`). I checked against their reproduction in the log only.
- Numbers in unchanged sections. I confirmed only that moved text kept its earlier values. I did not re-verify the earlier sections against the log.
- Page layout and the 10-page main-text limit beyond the PDF text extraction (45 pages, no "??").
