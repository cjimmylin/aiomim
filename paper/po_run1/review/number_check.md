# Number check: refined_v3.tex against experimental_log.md

Checked: `latex/refined_v3.tex`, `latex/refined_v3.pdf` (36 pages; main text ends on p. 10; pages 4-11 rendered and read),
the five PNGs in `latex/figures/`, `latex/figures/info.json`, and `plots/<id>/plot.py` for the four data figures.
Ground truth: `raw_materials/experimental_log.md` (cited as "log §x"), `idea.md`, `notes.md`.

## Counts

- Statements about the study's own results checked, sentence by sentence (abstract, Introduction, Sections 3-6,
  Ethics and Reproducibility statements, 2 main tables, 5 figure captions, appendix prose): about 140.
- Numbers checked against the log by hand: about 650 in the main text (including all 54 cells of Table 1 and all 36
  cells of Table 2, and every number printed in the four data figures), and about 1,100 appendix table cells. Every
  appendix table was compared with its log table row by row, well beyond the five-cell minimum.
- Mechanical check: all 4,525 numeric tokens in the .tex after line 33 were looked up in the log, idea.md and notes.md.
  Every one occurs there except page-layout widths (0.545, 0.435, 0.49) and the style-file year 2025.
- Problems found: **wrong 2, unsupported 1, inconsistent 2, wording 12** (17 in all). No wrong value, sign, interval
  bound, n or better/worse/tied count was found in any table, figure or caption.

## Problems

| # | Location | Paper says | Log says | Severity | Correction |
|---|---|---|---|---|---|
| 1 | l. 48, Introduction | "Between strategies, on the 93 entries every strategy completed, only case table first is clearly behind direct reading ($-1.9$ points, $-3.1$ to $-0.8$)" | §2.3: memory only "-34.0 (-39.3 to -28.7)" and recall, then verify "-34.5 (-39.2 to -29.9)" are also clearly behind direct reading | wrong (as written) | "Among the reading strategies, on the 93 entries every strategy completed, only case table first is clearly behind direct reading (...)" |
| 2 | l. 239, Sec. 4.8 | "\textbf{Reconciliation} changed facts by $+0.1$ ($-0.1$ to $+0.4$) and no other score" | §7 table: claims supported "+0.0 (-0.4 to +0.4); 15/13/69"; unsupported before repair "+0.1 (-0.0 to +0.3); 4/12/81"; facts contradicted "+0.1 (-0.0 to +0.2)"; synopsis exact "-0.1 (-0.4 to +0.3); 6/5/86"; variants recovered "+0.1 (+0.0 to +0.3); 1/0/96". Other scores moved by the same tiny amounts. (notes.md says "changed counts and no score", which the log table does not bear out either.) | wrong | "Reconciliation changed no score by more than 0.1 point (facts $+0.1$, $-0.1$ to $+0.4$; App. Table recon)" |
| 3 | l. 171, Sec. 4.2 | "On those 30 entries the evidence graph's difference from direct reading was $+0.7$, $+1.9$ and $+0.5$ points in the three replicates, opposite in sign to its $-0.5$ on the 93 entries, an illustration of that noise." | §4.2: replicate differences "+0.7 / +1.9 / +0.5" are all positive. Replicate 1 has the same means as the main run's drafts on those entries (§4.1/§4.2 replicate 1: direct 45.6, graph 46.3), so the change of sign comes from averaging over 30 entries instead of 93. It is entry-sampling difference, not replicate noise. Replicate noise is the spread +0.5 to +1.9. | unsupported | "...opposite in sign to its $-0.5$ on the 93 entries; that difference comes from which entries are averaged, while the replicates themselves range from $+0.5$ to $+1.9$." Or delete the clause after "93 entries". |
| 4 | l. 50, Introduction (contribution 2) | "reporting completion (stopped replies are an outcome, not an exclusion)" | §2.1: "An entry is compared only when every strategy below completed it in full ... 93 of the run's 100 entries qualify". Stopped replies do exclude entries; completion is also reported, and §2.4 zero-fills as sensitivity. The paper's own l. 99 says the same. | inconsistent | "reporting completion (stopped replies are reported as an outcome, and a sensitivity analysis counts missing drafts as zero)" |
| 5 | l. 111, Sec. 3.3 Statistics | "We report paired differences ... the number of entries better, worse and tied, the median difference and an exact sign test ..., with Holm correction ... across the secondary headline measures" | Medians and sign-test p appear only for the all-100-entry sensitivity analysis (§2.4; App. Table itt), and those p are unadjusted. The main 93-entry comparison (§2.3, Table 1, App. Table paired) has no median or p. The log contains no Holm-adjusted value anywhere. | inconsistent | "...the number of entries better, worse and tied, and, for the sensitivity analysis, the median difference and an exact sign test (unadjusted p)". Either drop "with Holm correction" or report the adjusted values. |
| 6 | l. 48, Introduction | "and part of its gap reflects the extraction effort of our implementation" | §5: "on facts, claims and variants the matched step is the extraction effort; that attribution is an inference" (two changes were made together) | wording | "...and the matched ablation suggests that part of its gap reflects the extraction effort of our implementation (an inference, Section 4.7)" |
| 7 | l. 107, Sec. 3.3 | "The reference covers a minority of the task: 24\% of a direct-reading draft's statements have a counterpart in the paragraph" | §8: measured on the learned-guide held-out entries (68), from the editorial report: "24% (direct) and 25% (guide)" | wording | add "(on the 68 held-out entries of the guide experiment)" |
| 8 | l. 140, Sec. 4.1 | "checked against the writer's text for its paper and, if not stated there, against the entry's other supplied papers" | §3.1: "A fact that text did not state, or stated only partly, was checked once more" | wording | "if not stated there, or only partly stated, against the entry's other supplied papers". App. Table conveyed already says this. |
| 9 | l. 171, Sec. 4.2 | "On 20 entries created in 2026, not used in developing the strategies, the ordering is the same" | §10 and notes.md (2026 entries): five strategies (no recall, then verify), 20 of 30 compared, and "stopped replies are frequent there; say so" | wording (notes compliance, partial) | "On 20 of 30 entries created in 2026 (five strategies; stopped replies frequent), not used in developing the strategies, the ordering is the same". Limitation (vi) gives 20 and five, but the stopped-reply frequency appears only in App. new. |
| 10 | l. 204, Sec. 4.3 | "on what was readable, three strategies convey nearly all of it" | §2.10a: on stated facts 93.6-94.4%; on "stated or partly" facts 76.9-77.5% | wording (overstatement) | "on facts the supplied text states, three strategies convey 93.6--94.4\%" |
| 11 | Fig. 4 (l. 209) and fig_access_strata.png | Shaded "replicate-noise half-widths over 93 ($\pm$1.0) and 30 entries ($\pm$1.8)" drawn behind groups of 46, 25 and 21 entries | §4.2: 1.0 is for a difference over 93 entries and 1.8 over 30. By the same scaling the yardstick is about 1.4 for 46 entries, 1.9 for 25 and 2.1 for 21, so the ±1.0 band understates the noise for every group shown | wording (presentation) | Drop the ±1.0 band, or say in the caption "half-widths for 93 and 30 entries; the groups have 21-46 entries, so their yardstick is wider than the darker band" |
| 12 | l. 231, Sec. 4.6 | "within abstract-only papers direct-reading coverage declines from 49.8\% (600000--609999) to 37.9\% (620000 onward; pooled)" | §2.10 direct, abstract row: classic 33.0%, 49.8%, 42.0%, 40.2%, 37.9%. The oldest band is the lowest, so the decline holds only from 600000 on | wording (selective) | "...declines from 49.8\% (600000--609999) to 37.9\% (620000 onward; pooled), though the classic band is lowest (33.0\%)" |
| 13 | l. 235, Sec. 4.7 | "so we attribute the gain in facts to extraction effort" | §5: graph matched − graph "+0.8 (-0.5 to +2.1)" (no distinguishable gain); table matched − table "+2.1 (+1.1 to +3.2)" | wording | "so we attribute case table first's gain in facts (+2.1) to extraction effort; the evidence graph's +0.8 ($-0.5$ to $+2.1$) is not distinguishable from zero" |
| 14 | l. 237 (section title "two nulls"), l. 50 ("negative results ... a small learned guide"), l. 239 | Guide described as a null/negative result | §8: held-out facts "+1.0 (+0.0 to +2.0); 30/25/13" (interval touches zero; point estimate positive) | wording (borderline understatement) | "a small learned guide whose held-out gain (+1.0, +0.0 to +2.0) is not clearly distinguishable from zero", and in the title "one gain with costs, one borderline and one null" |
| 15 | l. 239, Sec. 4.8 | "Second-hand evidence raises ... but also unsupported claims before repair (0.4\% to 3.9\%)" | §6.3: facts contradicted 0.4% → 0.7%, "+0.2 (+0.0 to +0.5); 4/11/81"; §12: "Second-hand evidence increased unsupported claims before repair and contradictions with the reference" | wording (omission of a listed limit) | add "and contradictions with the reference (0.4\% to 0.7\%; $+0.2$, $+0.0$ to $+0.5$)" |
| 16 | l. 251, Conclusion | "what limits agreement with curator-written text is access to the source" | notes.md: "Do not claim the method matters little in general. At current open access the reading strategies are close". Intro l. 48 and Discussion l. 243 qualify the claim with "in the regime tested" | wording (notes compliance risk) | "...in the regime tested (2--12 references, 19\% full text, one model), what limits agreement ... is access to the source" |
| 17 | l. 947, App. addons | "A planted test on six entries merged 10 of 10 copied reports with their originals and no unrelated records." | §7 continues: "this easy case shows only that a stated re-report is caught" | wording (caveat dropped) | append "; this easy case shows only that a stated re-report is caught" |

### Values the log gives twice (separate bootstrap runs); no error in the paper

The paper keeps each value to the table it comes from and says so in captions/prose. Listed for completeness:

- Facts conveyed, all 93 entries: case table first −1.9 (−3.1 to **−0.8**) (log §2.3) vs (−3.1 to **−0.7**) (§2.10a);
  memory only (**−39.3** to −28.7) vs (**−39.2** to −28.7); recall, then verify (−39.2 to −29.9) vs (−39.3 to −30.0).
  The paper uses §2.3 in Table 1, l. 48 and l. 171, and §2.10a in App. Table stated, whose caption notes "can differ by 0.1". Consistent.
- Top access group: evidence graph −1.8 (−4.4 to **+0.7**) (§2.9) vs (−4.4 to **+0.6**) (§5 note); case table first
  −6.1 (−8.3 to **−3.6**) vs (−8.3 to **−3.7**). §2.9 is used in l. 221, Fig. 4, plot.py and App. Table strata. §5 is
  used in the App. ablation prose, which carries a "separate bootstrap" disclaimer. Consistent.
- 38 ablation entries: evidence graph +1.0 (**−0.9** to **+2.8**) (§5 table) vs (−0.8 to +2.9) (§5 note); case table
  −2.3 (−4.5 to **+0.1**) vs (−4.5 to **+0.0**). The table values are used in l. 221 and l. 235 and App. Table abl_diff, and the note values in the App. ablation prose (disclaimed). Consistent.
- Log internal: §1.1 says the ablation subset was "filled to 40 at random", while §5 says it was filled "to bring each creation-era band to 8 entries". The paper follows §5.

## notes.md compliance

### Claims the paper must not make

| Item | Result | Location |
|---|---|---|
| Method matters little in general | pass, with a risk | Abstract and l. 48 qualify the claim with "in the regime tested". The Conclusion (l. 251) states the access claim without a regime qualifier (problem 16). Case table first falling behind with full text is reported (l. 221, 243). |
| Evidence graph conveys fewer facts overall | pass | l. 171, 173; App. corrected analyses |
| Large-entry tier as findings | pass | App. large: "we draw no findings from it". Main text cites it only in Limitation (viii). |
| Verification after recall cannot help in general | pass | l. 50 "at this scale"; l. 93 and l. 175 "may not add content from the papers" |
| Learned guide does not help in general | pass | l. 50 "a small learned guide", l. 93 "two reflection rounds from 27 training entries". Borderline understatement: problem 14. |
| Structure "pays when the database is the product" | pass | not claimed; l. 239 "not validated against per-patient ground truth" |
| OMIM is wrong | pass | l. 227: one sentence, "unconfirmed leads", no entry named. The Ethics statement repeats "unconfirmed". |
| Audit establishes correctness | pass | l. 107, 227 |
| Reading results free of memorisation | pass | l. 231; Fig. 5 caption; Limitation (iv) |
| Human validation | pass | Abstract, l. 50, 117, 245, 251 |
| Generality across models | pass | l. 245 (i) |
| Promises of unrun experiments | pass | none |

### Limitations that must appear (all in Sec. 5, l. 245)

| Item | Result | Location |
|---|---|---|
| One model family; no human validation | pass | (i) |
| Reference indirect and narrow; narrative sections not compared | pass | (ii) |
| Oracle references; retrieval only on ten entries | pass | (iii) |
| Open access only, no supplementary material | pass | (iv). The notes' "where much variant and patient data lives" is not said. |
| Variant names not validated; inheritance coarse | pass | (v) |
| Developed on the same entries; no separate development set | pass | (vi), implicit |
| Stopped replies remove entries unevenly | pass | (vii) |
| Few-reference entries dominate; too-large inputs not tested | pass | (viii) |
| Cost at list price for one model | pass | (x) |

### Required wording and later notes

| Item | Result | Location |
|---|---|---|
| "curator-written per-paper text" in the abstract; measure introduced as OMIM allelic-variant descriptions in ClinVar, from gene entries, variant-centred | pass | l. 35, 46, 89 |
| HPO annotations not called OMIM's synopsis; two sources given | pass | l. 89 |
| "judged supported" | pass | l. 107, Table 1 caption, l. 225, appendix tables |
| Unsupported vs contradicted reported separately; unsupported ≠ wrong | pass | l. 107, 225 |
| "our extract-then-write implementations" + matched ablation beside it | pass | l. 48, Sec. 4.7 title |
| "stopped by the model's safety filter" | pass | l. 95 |
| Conveyed facts: "stated in no supplied text", not "recalled"; partial facts more often outside the text | pass | l. 140 (but see problem 8) |
| Audit control as the re-audit flag rate on passed paragraphs; omissions and misattributions untested | pass | l. 225 |
| Repair parity: lead with like-for-like | pass | l. 123 (before repair first, after repair stated) |
| Aggregation stated for every level | pass | l. 107 sets the convention (mean unless "pooled"); pooled levels are marked |
| 2026 entries: sample not used in development; five strategies; 20 of 30; stopped frequent | partial | App. new has all of it. The main text l. 171 and (vi) give "20" and "five", but not the stopped-reply frequency (problem 9). |
| Task/reference framing (no suggestion of whole-entry agreement) | pass | title, l. 35, l. 46 |
| Stated-facts comparison, ceiling, model judgement, case-table deficit | pass | Sec. 4.3 |
| Ablation-set explanation; graph sign not consistent; no general "separate" claim | pass | l. 221 |
| Replicate noise a yardstick, not a test | pass in wording | l. 111, 171, Fig. 4. But problem 3 attributes an entry-set difference to that noise, and problem 11 is about the band shown. |
| Planted-error test wording | pass | l. 225 (exact wording) |
| Venue fit | pass | l. 44 |

## Anonymity and process language

- PDF title block prints "Anonymous authors / Paper under double-blind review". The .tex still contains the template
  author block (l. 18-22: "Ambitious AI Researcher ... researcher@institute.ai"). It does not print, but it would be
  visible if the source were uploaded. Not counted as a problem, but it is worth blanking.
- No repository, URL (other than the template comment l. 4, which does not print), package name or acknowledgement.
- None of "frozen", "salt", "rescore", "worker", "gaps", run names (`omim100`, `ablation40`), file names or command names
  appear. The paper says "fixed" throughout. "Claude Code command-line interface" (l. 305) and "Claude Opus 5.5" name the
  vendor tool and model, not the authors.

## Could not check

- Holm-corrected results: the paper says Holm correction is applied (l. 111), but the log contains no adjusted value (see problem 5).
- Why 91 papers were hidden in 49 entries when 96 papers are readable in full overall: the log gives 91 without explanation. The paper's "the 91 papers readable in full" (l. 123) is taken from the log.
- Figures: values were checked against plot.py and by eye on the rendered images. Bar lengths were not measured in pixels. The Fig. 3 percentage labels were recomputed from the log counts (72/13, 33/15/50, 10/14/76) and agree.
- Statements the log itself takes from other reports (the editorial agreement figures in §8, the variant precision in the ablation, the whole-draft crediting in §4.3) match the log, but their sources were not available.
- Outside this brief: the PDF header reads "Under review as a conference paper at ICLR 2025" (style-file year).
