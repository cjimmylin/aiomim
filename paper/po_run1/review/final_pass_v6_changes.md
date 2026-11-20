# Final correction pass: refined_v5.tex -> refined_v6.tex

Inputs: `latex/refined_v5.tex`, `review/number_check_v5.md` (P1-P5, W1-W11), `review/review_v5.json` (area chair's weaknesses, items B1-B6 of the brief), `raw_materials/experimental_log.md` (regenerated 20 Nov), `raw_materials/notes.md`. Output: `latex/refined_v6.tex` (45 pages; main text ends with the Conclusion at the bottom of page 10).

Each entry gives the location (v5 line / v6 line and section), the source item, the old text and the new text. Applying every entry below to v5, plus the table cells in the last entry, reproduces v6 exactly. 'Length' marks a cut made to keep the main text within 10 pages; no caveat or required limitation was removed by a length cut.

## Number-check items

| Item | Status | Where |
|---|---|---|
| P1 | applied as given | App. J.4, Table `tab:app_audit_classes` caption |
| P2 | applied; 'sign test $p=0.22$' written as $p=0.219$ (log 14.2 gives 0.2188; three decimals as in W7); the closing clause replaced by the B3 sentence (P1 interactions with intervals and their cause); App. J.2 correction applied as given and agrees with the regenerated log 14.2 (2.5 and 4.0 points) | Sec. 4.5 Padding; App. J.2 Design |
| P3 | applied as given | Table 3 caption |
| P4 | applied as given | Sec. 4.4, second paragraph |
| P5 | applied as given | Sec. 4.6 |
| W1 | applied; 'GraphRAG with local search' (B1, notes.md) used instead of 'GraphRAG's local search'; abstract wording superseded by B1 | Abstract; contribution (2); Takeaway (3); Conclusion |
| W2 | applied as given | Takeaway (4) |
| W3 | applied as given | Sec. 4.4, first paragraph |
| W4 | applied as given | Sec. 5, measurement lessons |
| W5 | applied as given | Sec. 5, first sentence |
| W6 | all five replacements applied as given | App. J.1 Deviations (1); App. J.4 Deviations and cost (3); App. J.4 claim-level paragraph |
| W7 | applied as given ($43.78; 6 cells 0.2188 -> 0.219; 9 cells 0.6875 -> 0.688) | App. J.4; Table `tab:app_pad_cov` |
| W8 | applied: Sec. 4.2 and Sec. 4.3 references as given; each of the nine App. J tables now referenced in its subsection's text (also `tab:app_ext_own` and `tab:app_stability`) | Sec. 4.2; Sec. 4.3; App. J.1, J.2, J.4 |
| W9 | applied as given | App. J.2 |
| W10 | applied as given | App. I.3 |
| W11 | applied as given | Sec. 4.6 |

## Changes in document order

### 1. Abstract (v5 l. 36 / v6 l. 36)

- Source: B1; number check W1
- Note: Released systems named as run, entries in parentheses; case-table-first result stated as a mean difference with its interval and sign test; reading strategies stated as differing by under a point with intervals that include or touch zero. B1 supersedes W1's abstract wording; 'GraphRAG with local search' (B1, notes.md) used in place of W1's 'GraphRAG's local search'. 198 words (whitespace split; 204 if hyphenated compounds are split).

Old:

```latex
Many system designs turn papers into cited, structured text, but comparisons holding papers, model and scoring fixed concern question answering and summarisation, not writing what experts wrote about each paper. We build such a comparison from 100 OMIM phenotype entries, each drafted from exactly the papers its curators cited by one model under one claim-level audit and scoring; the primary endpoint, OMIM facts conveyed, is coverage of fixed fact lists split from curator-written per-paper text. Hiding the full text of the same papers lowers coverage from 79.8\% to 36.1\% (means over entries). On facts the supplied text states, the reading strategies convey more than nine in ten; on facts it does not state, under 7\%. Three reading strategies are within about a point of one another, our case-table-first implementation trails them, and drafting from memory conveys far less. On the same papers and model, released PaperQA2 and GraphRAG pipelines conveyed fewer facts than direct reading at higher cost (10 and 4 entries), and STORM could not run with this model. Handling stopped replies asymmetrically produced a spurious difference larger than those between reading strategies. One model family wrote, audited and judged everything, and no human validated any judgement.
```

New:

```latex
Controlled comparisons of designs turning papers into cited text concern question answering and summarisation, not writing what experts wrote about each paper. We build one from 100 OMIM phenotype entries, each drafted from exactly its cited papers by one model under one claim-level audit and scoring; the primary endpoint, OMIM facts conveyed, is coverage of fixed fact lists split from curator-written per-paper text. Hiding the full text of the same papers lowers mean coverage from 79.8\% to 36.1\%. Reading strategies convey over nine in ten facts the supplied text states and under 7\% of those it does not. Three reading strategies differ by under a point, with intervals that include or touch zero; our case-table-first implementation trails direct reading by a mean 1.9 points (interval excluding zero; sign test $p=0.071$); drafting from memory conveys far less. On the same papers and model, PaperQA2's document-query pipeline and GraphRAG with local search conveyed fewer facts than direct reading at higher cost (10 and 4 entries); STORM could not run with this model. Handling stopped replies asymmetrically produced a spurious difference larger than those between reading strategies. One model family wrote, audited and judged everything, and no human validated any judgement.
```

### 2. Introduction, para 1 (v5 l. 43 / v6 l. 43)

- Source: Length

Old:

```latex
and many system designs have been proposed for turning a set of documents into structured, cited text:
```

New:

```latex
and many designs have been proposed for turning documents into structured, cited text:
```

### 3. Introduction, para 1 (v5 l. 43 / v6 l. 43)

- Source: Length

Old:

```latex
drafting first and verifying afterwards \citep
```

New:

```latex
drafting, then verifying \citep
```

### 4. Figure 1 caption (v5 l. 53 / v6 l. 53)

- Source: Length

Old:

```latex
each readable as full text, abstract or title depending on open access; the causal gene is withheld. One model writes every draft; only the strategy varies (add-ons dashed, under their parent), and one audit, scoring and set of guards apply to all.
```

New:

```latex
each readable as full text, abstract or title; the causal gene is withheld. One model writes every draft; only the strategy varies (add-ons dashed, under their parent), under one audit, scoring and set of guards.
```

### 5. Introduction, para 4 (v5 l. 57 / v6 l. 57)

- Source: B1 (consistency with the abstract)

Old:

```latex
convey 93.6--94.4\%, within a point of one another;
```

New:

```latex
convey 93.6--94.4\%, differing by under a point;
```

### 6. Introduction, contributions (v5 l. 59 / v6 l. 59)

- Source: Number check W1; length

Old:

```latex
run-to-run variation, a matched ablation and released PaperQA2 and GraphRAG pipelines;
```

New:

```latex
run-to-run variation, a matched ablation, and PaperQA2's document-query pipeline and GraphRAG with local search;
```

### 7. Introduction, contributions (v5 l. 59 / v6 l. 59)

- Source: Length

Old:

```latex
(4) a characterisation of what the audit can and cannot see, including six classes of planted error;
```

New:

```latex
(4) what the audit can and cannot see, with six classes of planted error;
```

### 8. Related Work, para 1 (v5 l. 66 / v6 l. 66)

- Source: Length

Old:

```latex
In clinical genetics, language models have been applied to extracting variant, gene--disease and gene--phenotype evidence from papers
```

New:

```latex
In clinical genetics, language models extract variant, gene--disease and gene--phenotype evidence from papers
```

### 9. Related Work, para 1 (v5 l. 66 / v6 l. 66)

- Source: Length

Old:

```latex
scores model explanations against human explanations, but compares models rather than generation strategies
```

New:

```latex
scores model explanations against human ones but compares models, not generation strategies
```

### 10. Related Work, para 2 (v5 l. 69 / v6 l. 69)

- Source: Length

Old:

```latex
Here, by contrast, the papers are fixed to the curators' reference list, the reference is the curators' own text, all paradigms share one audit and one scoring, and access is measured and manipulated.
```

New:

```latex
Here the papers are fixed to the curators' reference list, the reference is their own text, all paradigms share one audit and scoring, and access is measured and manipulated.
```

### 11. Related Work, para 5 (v5 l. 78 / v6 l. 78)

- Source: Length

Old:

```latex
Factuality metrics decompose long-form text
```

New:

```latex
Factuality metrics split long-form text
```

### 12. Related Work, para 5 (v5 l. 78 / v6 l. 78)

- Source: Length

Old:

```latex
Citation quality has been measured for models that generate text with citations \citep{gao2023enabling}
```

New:

```latex
Citation quality has been measured for text generated with citations \citep{gao2023enabling}
```

### 13. Related Work, para 5 (v5 l. 78 / v6 l. 78)

- Source: Length

Old:

```latex
that drafts from abstracts convey less is therefore expected, and we measure how much.
```

New:

```latex
so drafts from abstracts should convey less; we measure how much.
```

### 14. Sec. 3.1, Entries and papers (v5 l. 88 / v6 l. 88)

- Source: Length

Old:

```latex
20 from each of five bands of entry number that track when the entry was created (Figure~\ref{fig:memory}).
```

New:

```latex
20 from each of five bands of entry number that track creation date (Figure~\ref{fig:memory}).
```

### 15. Sec. 3.1, Entries and papers (v5 l. 88 / v6 l. 88)

- Source: Length

Old:

```latex
345 as an abstract only and 74 as a title only; supplementary material was not retrieved.
```

New:

```latex
345 as abstract only and 74 as title only; supplements were not retrieved.
```

### 16. Sec. 3.2, Strategies (v5 l. 94 / v6 l. 94)

- Source: Length

Old:

```latex
(a term also used by \citealp{balhoff2026frontier}, for agents working in a workspace that supplies the source publication)
```

New:

```latex
(a term also used by \citealp{balhoff2026frontier})
```

### 17. Sec. 3.3, Completion (v5 l. 100 / v6 l. 100)

- Source: Length

Old:

```latex
A one-call strategy whose reply is stopped loses the entry, a per-paper strategy only a paper; scoring the second and excluding the first would bias the comparison, so completion is reported as an outcome, strategies are compared only on entries every one of them completed, and
```

New:

```latex
A stopped reply costs a one-call strategy the entry, a per-paper strategy only a paper; scoring the second and excluding the first would bias comparisons, so completion is reported as an outcome, comparisons use only entries every strategy completed, and
```

### 18. Sec. 3.3, Audit (v5 l. 102 / v6 l. 102)

- Source: Length

Old:

```latex
Each paper receives its claims and returns a verdict
```

New:

```latex
Each cited paper returns a verdict
```

### 19. Sec. 3.3, Audit (v5 l. 102 / v6 l. 102)

- Source: Length

Old:

```latex
whose quote is not found verbatim in the paper is downgraded.
```

New:

```latex
whose quote is not verbatim in the paper is downgraded.
```

### 20. Sec. 4, Takeaway (2) (v5 l. 114 / v6 l. 114)

- Source: B1 (consistency with the abstract)

Old:

```latex
(2) Three reading strategies are close;
```

New:

```latex
(2) Three reading strategies differ by under a point;
```

### 21. Sec. 4, Takeaway (3) (v5 l. 114 / v6 l. 114)

- Source: Number check W1
- Note: 'GraphRAG with local search' (B1, notes.md) used in place of W1's 'GraphRAG's local search'.

Old:

```latex
(3) Released PaperQA2 and GraphRAG pipelines convey fewer facts than direct reading at higher cost;
```

New:

```latex
(3) On these entries and settings, PaperQA2's document-query pipeline and GraphRAG with local search conveyed fewer facts than direct reading at higher cost;
```

### 22. Sec. 4, Takeaway (4) (v5 l. 114 / v6 l. 114)

- Source: Number check W2; B3

Old:

```latex
(4) Unrelated padding costs no strategy more than about a point;
```

New:

```latex
(4) Unrelated padding costs no strategy more than about a point (6 entries, losses of added papers allowed); direct reading rose at both sizes against an earlier-generation baseline (not read as a gain), so the others lost ground to it at the first size;
```

### 23. Table 1 caption (v5 l. 140 / v6 l. 140)

- Source: Length (the subscripts in the table give the same n)

Old:

```latex
 Subscripts: $n$ where below 93 (variant precision: only 23 and 30 for the memory-based strategies).}
```

New:

```latex
 Subscripts: $n$ where below 93.}
```

### 24. Sec. 4.2, first paragraph heading (v5 l. 164 / v6 l. 164)

- Source: B1 (consistency with the abstract)

Old:

```latex
\textbf{Three reading strategies are close; case table first trails them.}
```

New:

```latex
\textbf{Three reading strategies differ by under a point; case table first trails them.}
```

### 25. Sec. 4.2, first paragraph (v5 l. 164 / v6 l. 164)

- Source: B5 (log 2.2, '... fully (no partial credit)')

Old:

```latex
agentic curator 0.242).
```

New:

```latex
agentic curator 0.242). Without partial credit the levels are 42.4\% (direct reading), 42.0\% (evidence graph), 41.9\% (agentic curator) and 40.8\% (case table first), in the same order (levels only; Appendix Table~\ref{tab:app_full}).
```

### 26. Sec. 4.2, replicate-noise paragraph (moved to the end of the first paragraph of Sec. 4.2) (v5 l. 168 / v6 l. 164)

- Source: Length
- Note: The paragraph was joined to the end of the preceding paragraph; 'three replicates on 30 entries' remains in Sec. 3.3 (Statistics).

Old:

```latex
As a yardstick, not a test, three replicates of generation, audit and scoring on 30 entries give a replicate-noise 95\% half-width of 1.0 point on a difference over 93 entries (Appendix~\ref{app:stability}).
```

New:

```latex
so its low coverage is partly by construction. As a yardstick, not a test, the replicate-noise 95\% half-width is 1.0 point on a difference over 93 entries (Appendix~\ref{app:stability}).
```

### 27. Sec. 4.2, Matched ablation (v5 l. 166 / v6 l. 166)

- Source: B2 (log 5, 'Each strategy against direct reading'; 'Each step'); number check W8

Old:

```latex
a step of $+2.1$ ($+1.1$ to $+3.2$); the evidence graph's step is not distinguishable from zero (Appendix~\ref{app:ablation}).
```

New:

```latex
a step of $+2.1$ ($+1.1$ to $+3.2$), and the evidence graph from $+1.0$ to $+1.8$ ($+0.4$ to $+3.3$), a step of $+0.8$ ($-0.5$ to $+2.1$) (Appendix Tables~\ref{tab:app_abl_means}--\ref{tab:app_abl_diff}).
```

### 28. Sec. 4.2, Contamination check (v5 l. 172 / v6 l. 170)

- Source: Length

Old:

```latex
The memory-only control conveys 5.7\% of facts for the newest band and 7.0\% on the 2026 entries (Figure~\ref{fig:memory}), so memory alone contributes little there.
```

New:

```latex
The memory-only control conveys only 5.7\% of facts for the newest band and 7.0\% on the 2026 entries (Figure~\ref{fig:memory}).
```

### 29. Sec. 4.2, Add-ons (v5 l. 174 / v6 l. 172)

- Source: GROUNDING section 1 (interval kept with the number; log 6.3: +1.8, +1.0 to +2.8); length

Old:

```latex
Second-hand evidence raises OMIM facts conveyed by $+1.8$ points on 96 entries,
```

New:

```latex
Second-hand evidence raises coverage by $+1.8$ points ($+1.0$ to $+2.8$) on 96 entries,
```

### 30. Sec. 4.2, Add-ons (v5 l. 174 / v6 l. 172)

- Source: Length

Old:

```latex
The learned curation guide did not improve its own training entries, and its held-out gain, $+1.0$ points ($+0.0$ to $+2.0$), is not distinguishable from zero
```

New:

```latex
The learned guide did not improve its own training entries, and its held-out gain, $+1.0$ points ($+0.0$ to $+2.0$), is indistinguishable from zero
```

### 31. Sec. 4.2, Add-ons (v5 l. 174 / v6 l. 172)

- Source: Length

Old:

```latex
Reconciliation changed no score by more than 0.1 point,
```

New:

```latex
Reconciliation moved no score by over 0.1 point,
```

### 32. Sec. 4.3 (v5 l. 200 / v6 l. 198)

- Source: Number check W8

Old:

```latex
On stated facts (Table~\ref{tab:stated}), direct reading
```

New:

```latex
On stated facts (Table~\ref{tab:stated}; counts in Appendix Table~\ref{tab:app_stated}), direct reading
```

### 33. Sec. 4.3 (v5 l. 200 / v6 l. 198)

- Source: Length
- Note: Both caveats (same model family judges 'stated' and 'conveyed'; ceiling on abstract-only papers) are kept in full.

Old:

```latex
agreement. Two caveats apply. The same model family
```

New:

```latex
agreement. The same model family
```

### 34. Sec. 4.3 (v5 l. 200 / v6 l. 198)

- Source: Length

Old:

```latex
its deficit is larger on stated facts, most of all in full-text papers.
```

New:

```latex
its deficit is larger on stated facts, most in full-text papers.
```

### 35. Sec. 4.4, first paragraph (v5 l. 204 / v6 l. 202)

- Source: Number check W3

Old:

```latex
through a local adapter: PaperQA2's
```

New:

```latex
through a local adapter (a local server that relays each system's model requests to the command-line model): PaperQA2's
```

### 36. Table 3 caption (v5 l. 207 / v6 l. 205)

- Source: Number check P3

Old:

```latex
Supp.: claims judged supported, audit without repair.}
```

New:

```latex
Supp.: claims judged supported, pooled over claims, audit without repair.}
```

### 37. Sec. 4.4, second paragraph (v5 l. 229 / v6 l. 227)

- Source: GROUNDING section 1 (interval kept with the number; log 14.3: GraphRAG global -13.6, -27.1 to -5.4)

Old:

```latex
global search, secondary, $-13.6$)
```

New:

```latex
global search, secondary, $-13.6$, $-27.1$ to $-5.4$)
```

### 38. Sec. 4.4, second paragraph (v5 l. 229 / v6 l. 227)

- Source: Number check P4

Old:

```latex
at several to many times the calls and cost
```

New:

```latex
at several to many times the generation calls and cost
```

### 39. Sec. 4.5, Entries with more full text (v5 l. 246 / v6 l. 244)

- Source: Length (the matched-ablation figures now stand in Sec. 4.2)

Old:

```latex
but $+1.7$ on facts stated in full-text papers (Table~\ref{tab:stated}) and $+1.0$ on the matched-ablation entries, whose drafts are the main run's, so the estimates differ only in the entries averaged ($-1.2$ on its entries with half or more full text, $+3.1$ on the others; Appendix~\ref{app:ablation}).
```

New:

```latex
but $+1.7$ on facts stated in full-text papers (Table~\ref{tab:stated}); on the ablation entries, whose drafts are the main run's, it is at $-1.2$ where half or more is full text and $+3.1$ elsewhere (Appendix~\ref{app:ablation}).
```

### 40. Sec. 4.5, Padding (v5 l. 248 / v6 l. 246)

- Source: Length

Old:

```latex
with papers, fact lists and task otherwise unchanged and no audit or repair
```

New:

```latex
with fact lists and task unchanged and no audit or repair
```

### 41. Sec. 4.5, Padding (v5 l. 248 / v6 l. 246)

- Source: Number check P2 (supersedes 'about 4 points'); B3 (log 14.2, 6-entry table: change from P0, strategy-by-size interaction)
- Note: P2's text applied; its 'sign test $p=0.22$' written as $p=0.219$ (log 14.2: 0.2188, three decimals as in W7). P2's closing clause 'and the wider gaps to direct reading at the first size come from it' replaced by the B3 sentence giving the P1 interactions with their intervals (log 14.2) and their cause. The 'about 4 points' figure is not used; the regenerated log 14.2 gives 2.5 (direct reading) and 4.0 (evidence graph), now in App. J.2.

Old:

```latex
No strategy lost more than about a point from no padding to the largest input (case table first $-0.9$, $-2.1$ to $+0.1$; direct reading $+3.2$, $-0.7$ to $+6.8$; Appendix Table~\ref{tab:app_pad_cov}); direct reading's rise is within run-to-run noise (single-entry coverage varies by about 4 points between runs; the unpadded drafts are an earlier generation), not a gain.
```

New:

```latex
No strategy lost more than about a point at either size (case table first $-1.0$, $-2.1$ to $+0.0$, and $-0.9$, $-2.1$ to $+0.1$; Appendix Table~\ref{tab:app_pad_cov}). Direct reading rose by $+3.6$ points ($+1.0$ to $+5.9$) and $+3.2$ ($-0.7$ to $+6.8$), better on 5 of 6 entries at each size (sign test $p=0.219$); the unpadded drafts are an earlier generation with no replicate, so we do not read the rise as a gain. The others therefore lost ground to it at the first size, through its rise rather than their own fall (at most 1.0 point): their differences from it changed from no padding by $-2.8$ ($-4.3$ to $-1.1$; agentic curator), $-3.8$ ($-7.5$ to $-0.3$; evidence graph) and $-4.6$ points ($-7.2$ to $-1.5$; case table first); at the largest size these intervals include zero.
```

### 42. Sec. 4.5, Padding (v5 l. 248 / v6 l. 246)

- Source: Length

Old:

```latex
(changes from $-3.0$ to $+4.7$ points; the same order of strategies at every size)
```

New:

```latex
(changes from $-3.0$ to $+4.7$ points; the same order at every size)
```

### 43. Sec. 4.5, Large real entries (v5 l. 250 / v6 l. 248)

- Source: Length (the same point follows in the next sentence: one-call strategies lose whole entries, per-paper strategies lose papers)

Old:

```latex
on every entry, either its writer (no draft) or per-paper extractions (papers lost), so no new entry
```

New:

```latex
on every entry, so no new entry
```

### 44. Sec. 4.6, What it removes (v5 l. 254 / v6 l. 252)

- Source: Length ('paragraphs the audit had passed' kept in the required sentence)

Old:

```latex
in 60 paragraphs the audit had passed was flagged in all 60, on a claim
```

New:

```latex
was flagged in all 60 altered paragraphs, on a claim
```

### 45. Sec. 4.6, Six further classes (v5 l. 256 / v6 l. 254)

- Source: Number check P5

Old:

```latex
moved into another paper's paragraph (25 of 25), easy cases
```

New:

```latex
moved into another paper's paragraph (25 of 25 with known truth), easy cases
```

### 46. Sec. 4.6, Six further classes (v5 l. 256 / v6 l. 254)

- Source: B4 (App. J.4 Construction; log 14.4 Pilot review); counts kept

Old:

```latex
It caught a deleted negation, which reverses the claim, 8 of 8 times, but rarely a claim made broader by a deleted hedge (2 of 8) or count, zygosity or ``one family'' (1 of 14), with 2 to 8 items per rule.
```

New:

```latex
It caught every deleted negation (8 of 8), which reverses the claim and so plants a contradiction, not a broadening, but rarely a deleted hedge (2 of 8) or count, zygosity or ``one family'' (1 of 14); each rule has 2 to 8 items, and not every such edit broadens the claim (on reading, 2 hedge and about 3 zygosity edits are nearly meaning-preserving and 1 hedge edit is degenerate).
```

### 47. Sec. 4.6, Six further classes (v5 l. 256 / v6 l. 254)

- Source: Number check W11

Old:

```latex
for 16 of 29 planted deletions and in full or in part
```

New:

```latex
for 16 of 29 planted deletions (one stopped by the safety filter) and in full or in part
```

### 48. Sec. 5, Discussion (v5 l. 262 / v6 l. 260)

- Source: Number check W5

Old:

```latex
nor did released pipelines of two of these designs do better
```

New:

```latex
nor did released retrieval-augmented and graph-based pipelines do better
```

### 49. Sec. 5, Discussion (measurement lessons) (v5 l. 262 / v6 l. 260)

- Source: Number check W4

Old:

```latex
and test a released pipeline with its intended model, on which it depends in ways a model-agnostic description hides (STORM could not run here).
```

New:

```latex
and check that a released pipeline runs with the model it will be used with, since pipelines depend on the model behind them in ways a model-agnostic description hides (STORM could not run here).
```

### 50. Sec. 6, Conclusion (v5 l. 270 / v6 l. 268)

- Source: Number check W1
- Note: 'GraphRAG with local search' (B1, notes.md) used in place of W1's 'GraphRAG's local search'.

Old:

```latex
released PaperQA2 and GraphRAG pipelines conveyed fewer facts at higher cost
```

New:

```latex
PaperQA2's document-query pipeline (without its agent) and GraphRAG with local search conveyed fewer facts at higher cost
```

### 51. App. I.3, Disagreements (v5 l. 1212 / v6 l. 1210)

- Source: Number check W10

Old:

```latex
13 could not be decided from the readable text. These are unconfirmed leads: no curator has checked them, many rest on abstracts only, and the judge had already passed the same claims.
```

New:

```latex
13 could not be decided from the readable text; these are unconfirmed leads (no curator has checked them, many rest on abstracts only, and the judge had already passed the same claims).
```

### 52. App. J.1, How the systems were run (v5 l. 1226 / v6 l. 1224)

- Source: Number check W8

Old:

```latex
anywhere in the draft. The two are separate judge passes
```

New:

```latex
anywhere in the draft (Tables~\ref{tab:app_ext_own} and~\ref{tab:app_ext_strat}). The two are separate judge passes
```

### 53. App. J.1, How the systems were run (v5 l. 1226 / v6 l. 1224)

- Source: Number check W8

Old:

```latex
the strategies' figures there are their stored audits before repair.
```

New:

```latex
the strategies' figures there are their stored audits before repair (Table~\ref{tab:app_ext_audit}).
```

### 54. App. J.1, Deviations (1) (v5 l. 1228 / v6 l. 1226)

- Source: Number check W6

Old:

```latex
(the ledgers tally 698 calls, including the global-search queries and a smoke test)
```

New:

```latex
(698 calls were made in all, including the global-search queries and a test run)
```

### 55. App. J.1, Deviations (7) (v5 l. 1228 / v6 l. 1226)

- Source: Number check W8

Old:

```latex
which is also given for the systems. The systems ran
```

New:

```latex
which is also given for the systems (Table~\ref{tab:app_ext_cost}). The systems ran
```

### 56. App. J.2, Design (v5 l. 1415 / v6 l. 1413)

- Source: Number check W8

Old:

```latex
nearest its target. The supplied order
```

New:

```latex
nearest its target (sizes in Table~\ref{tab:app_pad_size}). The supplied order
```

### 57. App. J.2, Design (v5 l. 1415 / v6 l. 1413)

- Source: Number check P2 (App. J.2 correction; agrees with the regenerated log 14.2); W8

Old:

```latex
(Table~\ref{tab:app_pad_cov2}). Run-to-run variation of single-entry coverage is about 4 points (within-entry standard deviation in the replicate runs), so changes of a few points over 6 entries are within noise.
```

New:

```latex
(Table~\ref{tab:app_pad_cov2}; completion in Table~\ref{tab:app_pad_completion}). The unpadded drafts are an earlier generation with no replicate, so a change from P0 mixes input size with run-to-run variation (within-entry standard deviation of single-entry coverage in the replicate runs: 2.5 points for direct reading, 4.0 for the evidence graph; Table~\ref{tab:app_stability}).
```

### 58. App. J.2, What the strategies did with the added papers (v5 l. 1417 / v6 l. 1415)

- Source: Number check W9

Old:

```latex
cut each paper to 75,000--300,000 characters at P0 (one own paper cut) and to 33,333--66,666 at P1
```

New:

```latex
capped each paper at 75,000--300,000 characters at P0 (one own paper cut) and at 33,333--66,666 at P1
```

### 59. App. J.2, Deviations (v5 l. 1419 / v6 l. 1417)

- Source: Number check W8

Old:

```latex
The run made 683 new model calls.
```

New:

```latex
The run made 683 new model calls (Table~\ref{tab:app_pad_cost}).
```

### 60. App. J.4, Construction (v5 l. 1593 / v6 l. 1591)

- Source: Number check W8

Old:

```latex
single family or patient, zygosity).
```

New:

```latex
single family or patient, zygosity; Table~\ref{tab:app_audit_rules}).
```

### 61. App. J.4, Completeness check (v5 l. 1595 / v6 l. 1593)

- Source: Number check W8

Old:

```latex
and by judgement when the model judge says it does.
```

New:

```latex
and by judgement when the model judge says it does (Table~\ref{tab:app_audit_complete}).
```

### 62. App. J.4, Citation precision (v5 l. 1597 / v6 l. 1595)

- Source: Number check W8

Old:

```latex
equals the stored one.
```

New:

```latex
equals the stored one (Table~\ref{tab:app_audit_precision}).
```

### 63. App. J.4, Deviations and cost (v5 l. 1599 / v6 l. 1597)

- Source: Number check W6

Old:

```latex
the audit run in chunks rather than in one holder;
```

New:

```latex
the audit run on chunks of 5 paragraphs rather than on all items together;
```

### 64. App. J.4, Deviations and cost (v5 l. 1599 / v6 l. 1597)

- Source: Number check W6

Old:

```latex
after reading the built edits
```

New:

```latex
after reading the edits they produced
```

### 65. App. J.4, Deviations and cost (v5 l. 1599 / v6 l. 1597)

- Source: Number check W6

Old:

```latex
the selector of planted claims for deleted qualifiers was widened
```

New:

```latex
the rule that picks the planted claims for deleted qualifiers was widened
```

### 66. App. J.4, Deviations and cost (v5 l. 1599 / v6 l. 1597)

- Source: Number check W7

Old:

```latex
list price of \$43.7849;
```

New:

```latex
list price of \$43.78;
```

### 67. App. J.4, Table (audit classes) caption (v5 l. 1602 / v6 l. 1600)

- Source: Number check P1 (log 14.4: C3 truth unknown, planted-claim analogue flagged 4/5 in the altered paragraph)

Old:

```latex
(paragraph flagged 5; the control's analogue of the planted claim flagged 4 of 5)
```

New:

```latex
(paragraph flagged 5; claims naming the moved variant flagged in 4 of 5)
```

### 68. App. J.4, claim-level paragraph (v5 l. 1631 / v6 l. 1629)

- Source: Number check W6

Old:

```latex
the decomposer attributed 176
```

New:

```latex
the claim-splitting step attributed 176
```

### 69. App. J.2, Table `tab:app_pad_cov` cells

- Source: Number check W7

Old: `$p$ 0.2188` (6 cells), `$p$ 0.6875` (9 cells)

New: `$p$ 0.219`, `$p$ 0.688`
