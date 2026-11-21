# Number and claim check: `latex/formatted_v1.tex` (and `formatted_v1.pdf`) against `raw_materials/experimental_log.md`

Scope: abstract, main text, figure and table captions, all 55 tables, all 6 figures (read from the compiled PDF), the
appendix, and the ethics and reproducibility statements. Rules taken from `raw_materials/notes.md`; where notes
sections conflict, the later section was applied. Table and figure numbers below are those of the compiled PDF.

No table cell was found to differ from the log. The findings are about labels, entry sets, aggregation, hedges,
status labels, cross-references and claims that the log does not support. Most serious first.

---

## 1. Abstract: a range of point estimates looks like a confidence interval that excludes zero

- **Location.** Abstract: "no agent, evidence graph or case table conveyed more at the main settings (−0.5 to −1.9 points; their order shifts with entries and settings)".
- **Log.** §2.3: "OMIM per-paper facts conveyed (primary) ↑ | -0.5 (-1.5 to +0.5); 33/45/15 | -0.6 (-1.3 to +0.0); 31/42/20 | … | -1.9 (-3.1 to -0.8); 31/48/14". §2.1: "93 of the run's 100 entries qualify".
- **Problem.** Dropped hedge; rule in notes.md broken. "−0.5 to −1.9" is the range of three point estimates. Next to it, the abstract writes intervals in the same form ("95% CI 38.3 to 49.1", "2.6 points (1.7 to 3.6)"), so readers will take it as an interval that excludes zero, meaning all three designs are significantly worse. That is the claim notes.md forbids: "Do not claim the evidence graph conveys fewer facts than direct reading overall … not distinguishable from zero". It also breaks "No equivalence claims … needs the interval and the entry count next to it". Neither the entry count (93) nor the fact that two of the three intervals include zero is given.
- **Fix.** Write "(point estimates −0.5 to −1.9 points on the 93 entries every strategy completed; the agent's and the evidence graph's 95% intervals include zero; their order shifts with entries and settings)".

## 2. Introduction: the zero-fill figure −3.5 has no interval and no better/worse count

- **Location.** §1, "Reading more completely…": "on all 41 (post hoc) the gain holds only if the unrevised draft is kept … (+2.4 points; −3.5 if such entries count as zero)".
- **Log.** §15.1 All facts, zero rule: "D2 completeness pass | 58.3% | 41 | -3.5 | -11.1 to +2.6 | 28/7/6 | <0.001". Replacement rule: "D2 completeness pass | 64.3% | 41 | +2.4 | +1.5 to +3.4 | 28/4/9 | <0.001".
- **Problem.** Dropped hedge. Without its interval (−11.1 to +2.6, which includes zero) and the 28-better/7-worse count, −3.5 reads as a clear loss. Notes.md, review of v0: "the two arms as evaluated are below direct reading on the mean (−4.8 and −3.5, intervals including zero) although they are better on more entries. Say both". Notes.md, v1 review: "give one estimate with its interval per claim". Section 4.3 states this correctly; the introduction does not.
- **Fix.** Write "(+2.4 points, +1.5 to +3.4; if such entries count as zero, −3.5, −11.1 to +2.6, although 28 entries are better and 7 worse)".

## 3. Post hoc and exploratory headline results are not labelled in the abstract, introduction and conclusion

- **Location.** Abstract: "Hiding the full text … lowers mean coverage from 79.8% to 36.1% (46 entries; 43.7 points, 95% CI 38.3 to 49.1)". Introduction: "from 79.8% to 36.1% (… all before the audit's repair round; +43.7 points …)". Conclusion: "from 79.8% to 36.1%". Also in the abstract: "on all 41, it requires keeping the unrevised draft …" (the §15.1 sensitivity analysis) and "A claim-level audit catches swapped citations, not added citations or omissions" (from the six-class planted test).
- **Log.** §6.2: "Full text before repair minus abstract only | 46 | +43.7 (+38.3 to +49.1)" comes from the repair-parity rescoring. The originally designed comparison is "Full text minus abstract only | 46 | +43.9 (+38.5 to +49.3)" (full text 79.9%). §15.1: "Added after the paper's first review round (not in the evaluation design…)". §14: "the results show directions and large effects only".
- **Problem.** Rule in notes.md broken: "Separate pre-specified results from exploratory and post-hoc ones, and label the latter". The paper's own status list puts "(e) scoring the hidden-full-text arm before repair" and "(i) the reading-better analysis with stopped entries put back" among the post hoc analyses, and the planted classes among the exploratory ones. Section 4.1 labels the 79.8% figure post hoc, but the abstract, introduction and conclusion lead with it unlabelled, and the pre-specified +43.9 never appears in the main text. Notes.md allows leading with the like-for-like comparison ("Lead with whichever comparison is like for like and state the other"), but it must be labelled.
- **Fix.** Abstract and introduction: add "(like for like, both unrepaired; post hoc rescoring; as designed, +43.9, 38.5 to 49.3)". Conclusion: add "(both unrepaired)". Mark the all-41 clause "(post hoc)" and the audit sentence "(exploratory, 30 items per class)".

## 4. The definition "paired differences are always means over entries" is contradicted by Table 13

- **Location.** §3.3 Definitions: "A level is a mean over entries unless marked pooled …; paired differences are always means over entries." Table 13, bottom panel: "difference from direct reading in points with a 95% interval from resampling entries".
- **Log.** §2.8, second table: "Coverage pooled over the facts of all papers at that level, strategy minus baseline in percentage points, with a 95% interval from resampling entries (all of an entry's facts move together)".
- **Problem.** Pooled/mean mix-up. The differences in Table 13's bottom panel are differences between pooled coverages, not means of per-entry differences. Neither the caption nor the definition says so, and the definition says the opposite.
- **Fix.** Definition: "paired differences are means over entries, except the by-access-level differences of Table 13, which are differences of pooled coverage". Table 13 caption, bottom: "difference in coverage pooled over the facts at that level (strategy minus direct reading)…".

## 5. Paired-difference rows labelled "unsupported, before the repair round" measure unsupported or contradicted

- **Location.** Second row of Table 7 ("… unsupported, before the repair round ↓", memory only "+22.4 (+18.3 to +26.7)"). The same label appears in both panels of Table 11, in the paired rows of Table 26 (middle), Table 27, Table 28 (bottom) and Table 54 (differences).
- **Log.** §2.3a names this measure "Claims unsupported or contradicted, before the repair round (<0.001; +22.4 points)". §2.3 and §2.4 label the row "… same, before the repair round". §2.2 levels: memory only unsupported 22.1%, contradicted 0.6%; direct reading 0.2% and 0.0%.
- **Problem.** Internal inconsistency (wrong label). Table 8 of the paper calls the same measure "claims unsupported or contradicted, before the repair round (<0.001; +22.4)". The arithmetic agrees with Table 8, not Table 7: unsupported only gives 22.1 − 0.2 = 21.9, while unsupported or contradicted gives 22.7 − 0.2 = 22.5 ≈ 22.4. The 100-entry level in Table 11 (memory only 22.8%) also matches the combined measure (22.1 + 0.6 on the 93 entries).
- **Fix.** Relabel these rows "… unsupported or contradicted, before the repair round ↓" in Tables 7, 11, 26, 27, 28 and 54. Keep "unsupported" only where it is the separate level row, as in Tables 1 and 6.

## 6. Abstract and introduction: "38 … with a complete draft from every arm" is the wrong entry set

- **Location.** Abstract: "On 38 test entries with a complete draft from every arm, a completeness pass adds 2.6 points". Introduction: "On 38 entries not used in its design, each with a complete draft from every arm".
- **Log.** §15: "41 entries …; 38 complete for every arm are compared" refers to the first four arms. The extension: "Comparisons use the 35 entries complete for all five arms". The D4 completion row shows 35 complete, 2 incomplete and 4 without a draft.
- **Problem.** Wrong entry set or denominator. The paper presents the checklist with the completeness pass as a fourth arm (§4.3), and it is complete on only 35 entries. The 38 entries are those complete for the baseline and the first three arms. Notes.md says so: "38 entries for the first four arms, 35 for the five-arm comparison". Its later shorthand "(the 38 every arm completed)" is ambiguous.
- **Fix.** Write "On the 38 test entries for which direct reading and the first three reading-better arms all wrote a complete draft…" in the abstract, and the same in the introduction.

## 7. Learned guide: "+1.0" is presented as a gain, but the log reads it as a null result

- **Location.** §4.2, "Two add-ons": "The learned guide … adds 1.0 point (+0.0 to +2.0) on 68 held-out entries".
- **Log.** §8: "OMIM per-paper facts conveyed (primary) ↑ | +1.0 (+0.0 to +2.0); 30/25/13". §12: "The learned guide did not improve its own training entries; its null result on held-out entries says nothing about better-resourced prompt optimisation."
- **Problem.** Dropped hedge. The interval reaches zero, 30 entries are better and 25 worse, and the log calls the held-out result null. "Adds 1.0 point" reads as a gain.
- **Fix.** Write "changes coverage by +1.0 point (+0.0 to +2.0; 30 better, 25 worse, 13 tied), an interval that reaches zero".

## 8. Completeness check: "none in the unaltered texts" leaves out partial matches and the natural omissions

- **Location.** §4.5, "What it misses": "a completeness check by the same model listed 16 of 29 planted deletions in full and none in the unaltered texts."
- **Log.** §14.4 C6: "Unaltered (false-alarm side) | 30 | 5.59 / 3 | 4/29 (14%) | 0/29 (0%) | 2/29 (7%)". Natural omissions: "Listed by the check (judge 'states it'): 24 (40%) … Omissions listed: 284 (10.14 per paper…). Matching any curator fact about the paper: 56 (20%)".
- **Problem.** Dropped hedge; rule in notes.md broken. "None" holds only for whole-sentence judge matches. On the unaltered texts the judge matched 2 of 29 in part and the mechanical match flagged 4 of 29. Notes.md (§14.4 item) requires: "The completeness check recovers part of planted and real omissions and lists many items the curators did not record". The main text omits the real omissions (24 of 60) and the 284 listed omissions, of which 20% match a curator fact.
- **Fix.** Write "listed 16 of 29 planted deletions in full (24 in full or in part) and, in the unaltered texts, none in full (2 in part). It found 24 of 60 real omissions, and only 56 of the 284 omissions it listed on those papers (20%) match a curator fact."

## 9. Main text: the 97.2% and 97.0% judged-supported shares are pooled but not marked pooled

- **Location.** §4.3: "the share of claims judged supported, did not fall on the 20 audited entries (97.2% against 97.0%; no interval…)".
- **Log.** §15, claims judged by the audit: "Shares are over checkable claims"; "Baseline … 2,578 | 2,501 (97.0%)"; "D2 … 3,278 | 3,185 (97.2%)".
- **Problem.** Pooled/mean mix-up. These are pooled over checkable claims. By the paper's own convention ("A level is a mean over entries unless marked pooled"), an unmarked level reads as a mean over entries. The appendix caption of Table 33 says "pooled"; the main text does not.
- **Fix.** Write "(97.2% against 97.0% of checkable claims, pooled; no interval…)".

## 10. Reproducibility statement: the total model usage may not include the later runs

- **Location.** Reproducibility statement: "all experiments, pilots and re-scoring used 45,291 cached model calls, 338 million input and 82 million output tokens, about $3,587 at list price."
- **Log.** §13: "All experiments, pilots and re-scoring: 45,291 cached model calls …". §13 comes before §14 (runs of 20–21 November) and §15. Those runs report their own new calls: 1,338 for the large entries (§14.1), 683 for padding (§14.2), 698 in the GraphRAG ledger (§14.3), 540 for the planted classes (§14.4), plus 1,624 and 572 for reading better (§15), and the PaperQA2 and STORM calls on top.
- **Problem.** Claim beyond the log; possibly stale. The log does not say whether the §13 total includes the runs of §14 and §15. If it does not, "all experiments" understates usage by roughly 5,500 or more new calls and several hundred dollars.
- **Fix.** Confirm with the source. If §13 predates §14 and §15, write "…for the main study; the second-round and reading-better runs made a further N new calls ($X)", or recompute the total.

## 11. Discussion: "The regime favours direct reading" is an explanation the log does not give

- **Location.** §5: "The regime favours direct reading (most papers are abstracts; 2,669 of 6,239 compared facts are not stated…; stated full-text facts span 40 entries)".
- **Log.** No statement that the regime favours any design. §2.3 and §2.10a show small differences, and §5 shows that the evidence graph's sign depends on the entries averaged.
- **Problem.** Claim beyond the log; rule in notes.md broken: "Patterns the log shows but does not explain … Mention them only as observed; do not invent explanations". Notes.md (v1 review) also says "Do not present 'the strategies separate where more full text is readable' as a finding". "Favours direct reading" implies that another regime would favour other designs.
- **Fix.** Write "The regime leaves little room for designs to differ (most papers are abstracts; …)", or drop the clause.

## 12. Second-hand evidence: the rise in contradicted facts is left out

- **Location.** §4.1: "as an add-on on 96 entries they add 1.8 points (+1.0 to +2.8) but raise the share of claims unsupported before repair".
- **Log.** §12: "Second-hand evidence increased unsupported claims before repair and contradictions with the reference." §6.3: "OMIM per-paper facts contradicted ↓ | 0.4% | 0.7%"; paired "+0.2 (+0.0 to +0.5); 4/11/81".
- **Problem.** Dropped hedge. The log gives two caveats; the paper gives one.
- **Fix.** Add "and the share of curator facts contradicted (0.4% to 0.7%; +0.2, +0.0 to +0.5)".

## 13. Limitation (iii): "each paradigm has one implementation" is wrong

- **Location.** §5 (iii): "matched settings ran on 38 entries, and each paradigm has one implementation."
- **Log.** §1.3: read and write contains direct reading and the agentic curator; extract, then write contains the evidence graph and case table first.
- **Problem.** Internal inconsistency with §3.2 and Table 4. Two paradigms have two strategies each. What has one implementation is each strategy.
- **Fix.** Write "each strategy has one implementation".

## 14. Limitation (xi) asks for an analysis that Table 53 already reports

- **Location.** §5 (xi): "…a larger stress test would give per-class sensitivity, and an any-cited-paper-fails rule applied to stored verdicts its flag rate."
- **Log.** §14.4, citation precision: "Claims passing with a non-supporting cited paper": kg 76 of 991, direct 142 of 1782, agent 78 of 1772, cohort 118 of 1254 (replayable entries).
- **Problem.** Internal inconsistency. The last column of Table 53 counts exactly the claims an any-cited-paper-fails rule would flag, on the replayable entries. The limitation describes this as missing.
- **Fix.** Write "…and an any-cited-paper-fails rule would flag 4–8% of multi-citation claims on the entries that could be replayed (Table 53); its effect on entries the repair round changed is unmeasured", or drop the clause.

## 15. "Held out" is defined for two sets but used for a third

- **Location.** §3.3 Definitions: "Held out: the entries created in 2026 from all development; the reading-better test split from the design of its prompts and from guide learning…". It is also used in §4.2 ("on 68 held-out entries"), Table 2 ("70 held-out main entries"), Table 4 and Table 28 for the learned guide's test set.
- **Log.** §1.3: guide "learned … from 27 training entries' omissions and extras … tested on 70 held-out entries".
- **Problem.** Rule in notes.md broken: "Say what each held-out set was held out from". The guide's 70 entries are held out from guide learning only, not from the development of the main strategies, and the definition does not cover them.
- **Fix.** Add to the definition: "the guide's 70 test entries, from guide learning only".

## 16. Table 2 says the all-full-text entry is "in no group"; Table 14 shows it as a group

- **Location.** Table 2, row "Groups by access (observational)": "the one entry with all references readable in full is in no group".
- **Log.** §2.9: "all full text | 1 | +17.8 †; n=1 | …". Table 14 reproduces this row.
- **Problem.** Internal inconsistency. 46 + 25 + 21 + 1 = 93.
- **Fix.** Write "the one entry with all references readable in full forms its own group (1 entry, no interval; Table 14)".

## 17. Appendix J: the range "Tables 36–40" covers the wrong tables

- **Location.** Appendix J, "How the systems were run": "…and, as a check that does not depend on the mapping, anywhere in the draft (Tables 36–40)."
- **Log.** Not applicable; this concerns cross-references.
- **Problem.** Broken cross-reference. Tables 37–39 are the run table and the two settings tables, which hold no credited-anywhere figures. Table 41 ("Our strategies on the same entries"), which holds the strategies' (a) and (b) figures, is left out.
- **Fix.** Write "(Tables 36, 40 and 41)".

## 18. Appendix B: the description of how synopsis terms are assigned conflicts with "assigned by rule"

- **Location.** Appendix B: "Synopsis terms are assigned by a lexical search over the ontology's labels and synonyms that returns candidates, from which the model chooses."
- **Log.** §1.4 has this sentence, but §1.3 says: evidence graph "Synopsis terms are computed from the graph by rule"; case table "synopsis terms and inheritance are computed by rule". §5: the matched variant lets "the writer choose[s] the synopsis terms … instead of fixed rules".
- **Problem.** Internal inconsistency. §3.2 of the paper ("their synopsis terms … are assigned by rule") and Table 4 say the opposite for the two extract-then-write strategies at the main settings.
- **Fix.** Qualify the sentence: "Ontology identifiers come from candidates returned by a lexical search…; at the main settings the evidence graph and case table first set their synopsis terms by rule, the other strategies' writers choose them".

## 19. "4% … the headroom for reading better" uses the wrong quantity

- **Location.** §4.1, "Missed and conveyed facts": "over all facts, 4% were not fully conveyed although stated, the headroom for reading better."
- **Log.** §3: "Of all OMIM facts: 43% conveyed, 4% omitted though stated…" (291 of 6,498, pooled). §15, "Where direct reading loses facts", item 3: "Conveying all of them would add about 3.5 points, and about 5 with the partly stated ones: the ceiling for any change to how the papers are read."
- **Problem.** Wrong number for "headroom". 149 of the 291 facts were already conveyed in part (half credit), so the headroom is about 3.5 points of coverage, not 4. The 4% is a share of facts.
- **Fix.** Write "over all facts, 4% were not fully conveyed although stated; conveying them would add about 3.5 points (about 5 with partly stated facts), the headroom for reading better".

## 20. Figure 4: the group heading "Errors the audit should catch" covers edits the log judged nearly harmless

- **Location.** Figure 4. The group heading "Errors the audit should catch" includes the hedge, count, zygosity and "one family" deletion rows.
- **Log.** §14.4, pilot review: "hedge (8): 5 change the claim …, 2 are nearly meaning-preserving …, 1 degenerate …. zygosity (8): … about 3 nearly meaning-preserving where de novo or dominant inheritance implies heterozygosity."
- **Problem.** Claim beyond the log. Some of these edits do not change the claim, so the heading overstates what the audit misses.
- **Fix.** Rename the heading "Planted edits", or add to the caption: "about 3 of 8 zygosity and 2 of 8 hedge edits are nearly meaning-preserving, and 1 hedge edit is degenerate (Appendix L)".

## 21. Appendix K.1 deviations: two statements are not in the log

- **Location.** Appendix K.1, Deviations: "Before any run finished this was cut to 8 entries, about 1,200,000 characters and at most 800 new model calls". Design: "The task prompt is unchanged."
- **Log.** §14.2: "Deviation (user's request, smaller budget): 8 entries planned instead of 12 … The pilot (first 2 entries) cost about 125 new calls per entry … so the entries were reduced in order to 6". "Decided before any run finished" appears only for the released systems (§14.3, deviation 1). The log says nothing about the task prompt.
- **Problem.** Claim beyond the log.
- **Fix.** Write "At the project's request the design was cut to 8 entries…", and remove "The task prompt is unchanged" unless another source supports it.

## 22. Appendix J: "like those of Appendices K and L, were made on 20–21 November 2026"

- **Location.** Appendix J, first sentence.
- **Log.** §11: the single-value planted test is under "Earlier analyses on the main set". §14 covers only the six-class test, padding and large entries on 20–21 November.
- **Problem.** Claim beyond the log. Appendix L also reports the earlier single-value test.
- **Fix.** Write "like the padding and large-entry runs (Appendix K) and the six-class planted test (Appendix L)".

## 23. Limitation (x): "Each entry was run once"

- **Location.** §5 (x): "Each entry was run once, without temperature or seed control".
- **Log.** §4.2: "30 entries, three full replicates of generation, audit and scoring".
- **Problem.** Internal inconsistency with Appendix E and Table 20.
- **Fix.** Write "The main comparison is a single run per entry (30 entries were run three times), without temperature or seed control".

## 24. Table 3: "3 of 361 claims could not be audited"

- **Location.** Table 3, row "Planted single values; unaltered re-audit": "(in the re-audit, 3 of 361 claims could not be audited)". Appendix L words the same result differently: "of 361 claims none was flagged …, 6 came back partly supported and 3 could not be audited".
- **Log.** §11: "0 of 361 claims were flagged (0 unsupported, 0 contradicted) and 6 came back partly supported; 3 could not be audited."
- **Problem.** Internal inconsistency (minor). The log does not say the 3 are among the 361.
- **Fix.** Write "(in the re-audit, 3 further claims could not be audited)", or confirm the denominator.

## 25. Appendix M.1: "3–19 papers per entry" conflicts with another table in the log

- **Location.** Appendix M.1: "OMIM paragraphs exist for a minority of each entry's references (3–19 papers per entry)."
- **Log.** §9: "(3–19 papers per entry)". The §14.1 per-entry table, "refs scored", lists entry 258870 as "2 (5.9%)" and the 12 earlier entries as 2–19.
- **Problem.** Possible wrong number. The two log sections disagree; the paper follows §9.
- **Fix.** Check against the source. If the §14.1 table is right, write "2–19".

## 26. Appendix G and §4.1: the counts of hidden papers reconcile only through an unstated number

- **Location.** Appendix G: "hid all 91 of their full-text papers (81 of the 96 full-text papers have an in-scope paragraph); the other 5 full-text papers, in 5 entries, have no in-scope paragraph".
- **Log.** §1.1: "81 of 96 readable in full". §6.2: "all their full-text papers were hidden (91 papers). The other 5 full-text papers (in 5 entries) have no in-scope curator paragraph".
- **Problem.** Internal clarity. 91 + 5 = 96 and 81 + 15 = 96 both hold only because 10 of the 91 hidden papers have no in-scope paragraph of their own. A reader who adds 81 + 5 gets 86, not 96.
- **Fix.** Add "(10 of the 91 hidden papers have no in-scope paragraph of their own)".

## 27. Draft length is missing beside two coverage gains

- **Location.** §4.1, second-hand evidence: "+1.8 points (+1.0 to +2.8)". §4.2, learned guide: "+1.0 point".
- **Log.** §8: "direct reading 24.0 statements per paper, with the guide 22.2". §6.3 gives no draft length for second-hand evidence.
- **Problem.** Rule in notes.md broken: "Report draft length beside every coverage gain and say the endpoint rewards recall."
- **Fix.** Guide: add "(22.2 statements per paper against 24.0)". Second-hand evidence: add "(draft length not recorded)".

## 28. For information: the ablation's main-settings intervals come from one of two bootstrap runs

- **Location.** §4.2 ("1.0 point above direct reading (−0.9 to +2.8)"), Table 21 and Table 23 ("+1.0 (−0.9 to +2.8)", "−2.3 (−4.5 to +0.1)").
- **Log.** §5 gives these figures from the ablation's comparison report. It also gives the same estimates computed from the main run's per-entry files on identical drafts and fact marks: "+1.0 (38 entries, -0.8 to +2.9…)" and "-2.3 (38 entries, -4.5 to +0.0…)". notes.md quotes the second set.
- **Problem.** Not an error; the paper is consistent internally. The case table's upper bound sits at the edge of zero in one run (+0.0) and just above it in the other (+0.1).
- **Fix.** Optionally add to Table 21's caption, as Appendix C does for Tables 7 and 19: "intervals from the ablation's bootstrap; a separate bootstrap on the same drafts gives −0.8 to +2.9 and −4.5 to +0.0".

---

## Not checkable against the log (literature claims; not verified, no web access used)

- Introduction: OMIM "held over 25,000 entries by 2021"; "A review of 19 evaluations found a median of 14% incorrect extractions"; "about 36 million abstracts but 6 million open-access full texts".
- Related work: FlyAOC's "16,898-paper corpus"; "a model reviewing extracted data caught 2 of 39 deliberate errors"; "about a quarter of quotations in medical articles are erroneous".
- Related work describes GEN-KnowRD as "evaluated by disease ranking", whereas notes.md describes it as "generated rare-disease profiles compared with curated reports". Both may be true; check against the cited paper.

## Count of what was checked

- **Numbers.** The abstract, main text, figure captions and the ethics and reproducibility statements hold about 470 numeric tokens; the appendix holds about 7,000, including table cells and entry numbers.
- **Automated pass.** Every numeric token in the paper occurs in the log except the literature numbers above and the rounded "about 500,000 characters" (log: P1 median 498,324).
- **Manual pass.** All 55 tables were checked cell by cell against the corresponding log tables, and no cell differs. All six figures were read from the PDF and agree with the log within plotting resolution: Fig. 2a/b/c, 3a/b, 4, 5 and 6, including the bar labels 76/15, 26/21/53, 16/77, 1,329/245/134/122, 1,420/46/632/2,159 and 38/53/288.
- **Arithmetic recomputed and correct.**
  - Differences: 79.8 − 36.1 = 43.7; 1.0 + 0.8 = 1.8; −2.3 + 2.1 = −0.2; padding interactions 0.8 − 3.6 = −2.8 and −1.0 − 3.6 = −4.6 (the graph's −3.8 against a recomputed −3.7 is rounding).
  - Sums: 81 + 221 + 25 = 327; 1,835 + 476 = 2,311; 46 + 25 + 21 + 1 = 93; 11 + 7 + 19 + 1 = 38; 22 + 1 + 1 + 13 = 37; 40 + 17 = 57; 1,837 + 283 = 2,120; pooled fact and claim rows sum to 6,239 and to the claim totals; inheritance rows sum to 93; variant rows sum to the totals; cost components add within rounding.
  - Shares: 76% and 26% stated, 49%, 4%, 1.7%, 10.0%, 75%, 66%, 34%.
  - Replicate half-widths: 1.96 × 5.0 / √93 ≈ 1.0 and 1.96 × 5.0 / √30 ≈ 1.8.
  - Ranges: 91.0–94.4%, 5.5–6.9%, 94.7–96.5%, 88.9–100%, 51.2–53.9%, 4–7%, $1.15–$1.18, $1.72–$1.78, 76–148, 2.8–4.6.
- **Cross-references.** All `\ref` targets resolve in the PDF (no "??"). Apart from finding 17, each points to the intended table, figure or appendix.
- **Findings by kind (28 in all):**
  - internal inconsistency: 8 (findings 5, 13, 14, 16, 18, 23, 24, 26; finding 5 is a wrong label repeated in six tables)
  - dropped hedge: 5 (1, 2, 7, 8, 12)
  - claim beyond the log: 5 (10, 11, 20, 21, 22)
  - rule in notes.md broken: 3 (3, 15, 27)
  - pooled/mean mix-up: 2 (4, 9)
  - wrong number: 2 (19; 25 is a discrepancy inside the log that the paper copies)
  - wrong entry set or denominator: 1 (6)
  - broken cross-reference: 1 (17)
  - for information only: 1 (28)

  Findings 1, 8 and 11 also break notes.md rules; each is counted once above.
