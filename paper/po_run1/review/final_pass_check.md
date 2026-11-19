# Final-pass check: refined_v3.tex -> refined_v4.tex

Independent check. I made my own diff (`git diff --no-index --word-diff=plain`) and read every changed passage against
`raw_materials/experimental_log.md` (cited as "log §x"), `notes.md`, `lit/citation_map.json`, `review/number_check.md`
and `review/citation_check_v3.md`. The paper was not edited.

## Verdict

- No wrong number. 153 new or changed number instances checked: 153 pass, 0 fail. I also recomputed the primary-endpoint
  sign-test p values from the better/worse counts (exact two-sided binomial test, ties dropped): 33/45 gives 0.213,
  31/42 gives 0.242 and 31/48 gives 0.071, all matching log §2.3a. The Holm-adjusted values 0.011 and 0.002 agree with
  the raw p values (2/15: 0.0023; 1/15: 0.0005) times their Holm multipliers.
- All 17 number-check items are dealt with: 12 applied as proposed and 5 applied differently, each in an acceptable way.
  Both citation-check text problems and both "unlike prior work" fixes are applied, as are the bib fixes. Template
  items (the ICLR 2025 style and the hidden author block) are not applied, and neither is a factual issue.
- Two wording fails (F1, F2). Neither changes a number. With these two edits, v4 is ready from a factual standpoint.

## Fails

| # | Location | Problem | Correction (old -> new) |
|---|---|---|---|
| F1 | Sec. 4.2, "Three reading strategies are close" paragraph | "after Holm adjustment no secondary headline measure differs from direct reading for any of these three" reads as "no difference on any secondary measure". Sec. 3.3 calls both the bootstrap interval and the sign test "the tests of a difference", yet log §2.3 has bootstrap intervals that exclude zero for case table first on claims supported (-1.4, -2.7 to -0.4), synopsis exact F1 (-2.0, -3.9 to -0.1) and hierarchical F1 (-2.5, -4.1 to -0.9), and for the evidence graph on hierarchical F1 (-1.4, -2.8 to -0.1). This is an overstatement of a null. | "after Holm adjustment no secondary headline measure differs from direct reading for any of these three," -> "after Holm adjustment no secondary headline measure has a sign-test $p$ below 0.05 for any of these three, although some bootstrap intervals exclude zero (Appendix Table~\ref{tab:app_paired})," |
| F2 | Sec. 4.1, "Where the conveyed facts came from" | v4 drops the 15.6% "partly stated there", so the shares given (74.7 + 7.2 + 1.7) leave 16% unexplained. notes.md ("Added after the first review round") requires "most are stated in the paper's own abstract, some only in another supplied paper, and some only partly stated". Log §3.1: 222 (15.6%). | "74.7\% are stated in the paper's own abstract and 7.2\% only in another supplied paper." -> "74.7\% are stated in the paper's own abstract, 15.6\% are partly stated there and 7.2\% are stated only in another supplied paper." |

## 1. New or changed numbers (all pass)

| Location | Numbers (log section) | n |
|---|---|---|
| Introduction | 79.8 / 36.1, 46 entries (§6.2); 93.6-94.4, 5.5-6.9 (§2.10a); -1.9 (§2.3); p = 0.071 (§2.3a); 2-12 | 8 |
| Sec. 3.3 | 68 held-out entries and 24% (§8); "eight" secondary headline measures (§2.3a, 8 rows) | 3 |
| Takeaways | "more than nine in ten" of stated facts (reading strategies 91.0-94.4%, §2.10a) | 1 |
| Sec. 4.1 | 49, 91, 46; 79.8 / 36.1; "every entry but one, which tied" (45/0/1, §6.2 before repair); 40.9; +43.9; 49%, 2%, none; 43%, 40%, 4% (§3); 1,420, 74.7%, 7.2%, 24 (1.7%), 10.0% (§3.1) | 20 |
| Completion | 100, 93 (§2.1) | 2 |
| Sec. 4.2 | 0.7 (49.1 / 48.6 / 48.4); -1.9; p 0.071 / 0.213 / 0.242 / < 0.001; "four or five" Holm-significant (4 and 5, §2.3a); -2.3 -> -0.2 (§5); 1.0 over 93, three replicates, 30 entries (§4.2); 20 of 30, five strategies, stopped replies frequent (§10) | 15 |
| Secondary measures | $1.15-$1.18, $1.72-$1.78 (§2.12) | 2 |
| Sec. 4.3 | 6,239, 2,372, 2,669; 93.6-94.4; 5.5-6.9; 8.2; 95.5-97.1; -8.4 (§2.10a) | 8 |
| Fig. 4 caption | ±1.0 (93), ±1.8 (30), "21-46 entries", -18.1 to -59.6 (§2.9, §4.2) | 4 |
| Sec. 4.4 | 46 / 25 / 21; -4.0, -6.1, +0.6; -1.8, +1.7, +1.0; -1.2, +3.1; -2.0, -0.2 (§2.9, §2.10a, §5 note) | 13 |
| Sec. 4.5 | 94.2-96.5 "after repair" (§2.2 final claims supported); 0 of 361 (§11); 112, 11, 3 (§6.2) | 5 |
| Sec. 4.6 | 5.7, 12.6-24.1 (§2.11); 7.0 (§10); 49.8, 37.9, 33.0, "second-oldest band" (§2.10) | 6 |
| Sec. 4.7 | 40 / 38; -2.3 -> -0.2; step +2.1 (+1.1 to +3.2); +1.0 -> +1.8; step +0.8 (-0.5 to +2.1); "plus text raises claims, not facts" (+1.5 / +1.2 claims vs +0.0 / +0.8 facts) (§5) | 8 |
| Sec. 4.8 | +1.8 on 96; 0.4% -> 3.9%; 0.4% -> 0.7% contradicted (§6.3); +1.0 (+0.0 to +2.0) (§8); "no score by more than 0.1 point" (max abs. 0.1, §7) | 6 |
| Discussion, Limitations, Conclusion | 2-12, 19%, 0.05; 20, five; 79.8 / 36.1; 93.6-94.4 | 8 |
| App. Table app_sign | 5 primary p, 15 better/worse/tied counts, 5 x "8", 9 adjusted p, 9 mean differences: every cell equals log §2.3a | 43 |
| App. stability | replicates "+0.5 to +1.9"; replicate 1 = main run (§4.2) | 1 |
| **Total** | | **153** |

## 2. Number-check items (17)

| # | Status |
|---|---|
| 1 | Applied, reworded: "Among the reading strategies, only our case-table-first implementation trails ...", plus a new sentence placing both memory-based strategies far behind. Correct. |
| 2 | Applied: "no score by more than 0.1 point". |
| 3 | Applied differently: the sentence is cut from the main text, and the correct explanation is in App. stability. Acceptable (the number check allowed deletion). |
| 4 | Applied (contribution 2 and Sec. 3.3 Completion). |
| 5 | Applied differently: the paragraph now describes the sign test with Holm adjustment, which log §2.3a now supports, and App. Table app_sign reports it. Acceptable. Small residual: Sec. 3.3 no longer mentions the medians and unadjusted p of App. Table itt, and that caption does not say "unadjusted" (see the suggestions below). |
| 6 | Applied ("a matched ablation suggests, as an inference"). |
| 7 | Applied. |
| 8 | Applied ("if not stated there or only partly stated"). |
| 9 | Applied in Sec. 4.2 and Limitation (vi). |
| 10 | Applied by deleting the overstatement. |
| 11 | Applied differently: the caption says "the groups have 21-46 entries, so the ±1.8 band is the nearer guide". Acceptable: scaling gives about 1.4, 2.0 and 2.1 for 46, 25 and 21 entries, so the yardstick for the two smaller groups is still a little wider than 1.8 (optional wording below). |
| 12 | Applied (classic band 33.0%). |
| 13 | Applied, including the graph's +0.8 (-0.5 to +2.1). |
| 14 | Applied differently: "not distinguishable from zero" and the title "two results indistinguishable from zero". Acceptable, since the interval reaches +0.0. |
| 15 | Applied without the interval (+0.2, +0.0 to +0.5). Acceptable. |
| 16 | Applied differently ("For this model and in the regime tested"; the regime is spelled out in the Discussion). Acceptable. |
| 17 | Applied. |

## Citation-check items

| Item | Status |
|---|---|
| 2a "open retrieval" (Intro) | Applied verbatim. |
| 2a DocETL "table-centred" | Applied verbatim. |
| 2b-1 CGBench | Applied. Related Work: "built from ClinGen's expert-curated literature interpretations, scores model explanations against human explanations, but compares models rather than generation strategies". Each clause is in the abstract ("built from ClinGen, a resource of expert-curated literature interpretations"; "we measure LM explanations against human explanations"; "We test 8 different LMs"). "compares models rather than strategies" was also added to the Introduction's list. Supported. |
| 2b-2 Abstract first sentence | Applied verbatim; see Section 6. |
| v0 §3.1 "agentic curator" credit | Applied: "(a term \citet{balhoff2026frontier} also use for agents working in a workspace that supplies the source publication)". The abstract says: "each operating as an 'agentic curator' within a self-contained workspace that supplies the source publication PDF". Supported. Style only: it prints as nested parentheses, "(a term Balhoff & Lapp (2026) also use ...)". |
| §4 bib: Furlan "wan", openRxiv entries, missing arXiv ids, Cohen 2010 article number | Applied in references.bib (Wan, A.; @misc bioRxiv/medRxiv; eprints present; pages 492). |
| §3.9 iclr2025 style; template author block (l. 18-22) | Not applied. Not a factual issue, but the author block will show if the source is uploaded. |

## 3. New claim sentences

All are supported at the strength stated except F1 and F2.

- **Takeaways (1)-(4):** supported. (1): hidden-full-text drop, and 91.0-94.4% on stated facts (§6.2, §2.10a). (2): the
  three are within 0.7; case table first is at -1.9 overall, and at -4.0 / -6.1 and -8.4 where full text is readable.
  The body hedges it with the sign test. (3): 15.1 / 14.6 against 47-49; 5.7% for the newest band and 7.0% for 2026.
  (4): matches notes.md.
- **Case table first, mean difference against sign test (Intro, Sec. 4.2, Discussion):** the interval -3.1 to -0.8
  excludes zero, and p = 0.071 (31/48/14). Both are correct, and both are stated wherever "trails" appears in the body.
  The abstract and Takeaway (2) say "trails" without the hedge. That is acceptable, because the mean is lower and the
  interval excludes zero.
- **Ablation -2.3 to -0.2:** log §5 gives -2.3 (-4.5 to +0.1) and -0.2 (-2.4 to +2.1) on 38 entries. The text calls the
  attribution an inference. Supported.
- **Other new interpretive sentences:**
  - Sec. 4.3: "this analysis supports the hidden-full-text experiment and does not stand alone". Appropriate hedge.
  - Sec. 4.6: "consistent with memory helping on older entries and not separated from reading; the classic band is
    lowest". Hedged. Direct-reading coverage peaks in the same band as the memory-only control (22.9% on abstract-only
    papers).
  - Intro: "a regime in which direct reading is expected to do well". Not from the log. It reads as a hedged
    expectation rather than a result, so acceptable.

## 4. notes.md requirements no longer stated

- "Limitations that must appear": all nine are still in Limitations (i)-(x). The Introduction dropped its
  open-access/no-supplements sentence, but Limitation (iv) keeps it.
- "Added after" sections:
  - Met: audit control (re-audit flag rate, omissions untested); repair parity (the main text leads with the
    like-for-like 79.8 vs 36.1 and states the after-repair +43.9; the like-for-like interval +43.7 (+38.3 to +49.1)
    is now only in Fig. 2 and App. Table hidden, which is acceptable); aggregation; 2026 entries (now complete in the
    main text); framing; stated-facts comparison with ceiling and model judgement; ablation-set explanation; replicate
    noise as a yardstick; planted-error wording.
  - Not met: the conveyed-facts "some only partly stated" item. See F2.

## 5. Deletions: references and undefined terms

- No `\ref` points to a missing label, and refined_v4.pdf has no "??".
- No figure or table lost its last in-text reference. Labels referenced in v3 but not in v4: none.
- Sixteen labels are referenced in v4 that were not in v3 (for example tab:app_missed, tab:app_guide, tab:app_recon,
  tab:app_secondhand(_claims)).
- Labels that remain unreferenced in both versions (pre-existing): tab:app_access, app_era, app_era_access, app_large,
  app_new, app_paired, app_pooled, app_stability. The F1 correction would add a reference to tab:app_paired.
- No undefined terms. "Reading strategies", "pooled", "judged supported" and "replicate noise" are all still defined
  before use.
- Completion sentence: "93 were completed by all six strategies; the others lost drafts or per-paper calls" still reads
  correctly about the 7 excluded entries.

## 6. Abstract

- Word count: 197 by whitespace (202 if every hyphenated compound is split). This is within the limit of 200, but close.
- Every statement is supported:
  - Opening sentence: the related-work abstracts (LaRA and Han et al.: QA and query-based summarisation) bear it out.
    CGBench compares models, and FlyAOC searches a corpus, so neither holds the papers and the model fixed.
  - 79.8% and 36.1%, means over entries, no arm repaired (§6.2).
  - "More than nine in ten" (91.0-94.4%) and "under 7%" (5.5-6.9%) (§2.10a).
  - "Within about a point" (0.7), case table first trails (-1.9, interval excludes zero), memory far less (§2.2-2.3).
  - The spurious 2.1 against at most 1.9 between reading strategies (§12, §2.2).
  - One model family, no human validation.
- Not a v4 regression: the abstract does not say that differences grow where more full text is readable (notes.md,
  "Report both"). The body and Conclusion say it.

## Optional suggestions (not fails)

- App. Table itt caption: "exact sign-test $p$" -> "exact sign-test $p$ (unadjusted)".
- Fig. 4 caption: "so the $\pm$1.8 band is the nearer guide" -> "so their yardstick is nearer the $\pm$1.8 band, and somewhat wider for the two smaller groups".
- Blank the template author block (l. 18-22).
