# Improving on direct reading: ten approaches, three tested

Started 20 November 2026. The published evidence for each approach is in
[`direct-improvements-evidence.md`](direct-improvements-evidence.md); this file holds the analysis of where direct
reading loses facts, the ranking, the evaluation design (fixed before any run) and, at the end, the results.

## Where direct reading loses facts

All figures are for direct reading on the main set, scored against the fixed fact lists, from files already in
`results/` and `runs/` (no new model calls).

1. **What was not in the text it was given.** Of 6,498 curator facts (97 entries), 40% are not stated in the text the
   model had (gap analysis, log section 3). On facts the supplied text states, direct reading conveys 94.4% (mean over
   entries; 97.1% for abstract-only papers, 88.5% for full-text papers), and on facts it does not state, 6.9%
   (log 2.10a). Hiding the full text of the same papers costs 43.7 points (log 6.2).
2. **Free to read but not openly licensed.** Europe PMC lists a free-to-read copy (in PMC outside the open-access
   subset, at the publisher, or through Unpaywall) for 130 of the 342 abstract-only papers and 30 of the 74 title-only
   papers. The curator paragraphs about those papers hold 2,223 of the 6,498 facts (34%), of which direct reading now
   conveys 36.8%. Were they read at the coverage the hidden-full-text experiment shows for full text, coverage would
   rise by about 15 points (pooled; a rough projection). The pipeline cannot fetch them: PMC and Europe PMC permit bulk
   retrieval only of the open-access subset, the publisher sites refuse this environment, and the services that
   locate legal copies (Unpaywall, OpenAlex) now require an e-mail address or a key.
3. **What was in the text and was missed.** 291 facts are stated in full in the supplied text and were missed or
   conveyed in part (245 of them in full-text papers, where 49% of missed facts were in the text), and 210 more are
   partly stated and were missed entirely. Conveying all of them would add about 3.5 points, and about 5 with the
   partly stated ones: the ceiling for any change to how the papers are read. The kinds of fact most often missed
   although stated are functional studies and model organisms, population controls, counts of patients and families,
   zygosity, ancestry and consanguinity, and age, sex and onset (keyword classes; a fact can fall in several).
4. **Run-to-run variation.** On the 30 replicate entries, single direct-reading runs convey 44.7–45.9%; the union of
   the facts conveyed by any of three runs is 48.7% (two runs: 47.5%). This is an upper bound for a sampling ensemble
   with a perfect merge, and it includes judge variation.

So the largest lever is access, which cannot be pulled here; among changes to how the supplied text is read, the
ceiling is about 3.5–5 points overall and larger on entries with full text.

## Ten approaches

| # | Approach | What it targets | Added calls per entry |
|---|---|---|---|
| 1 | Expanded legal access (OA copies elsewhere, institutional access, user-supplied text) | facts not in the supplied text (item 2) | none to write; retrieval only |
| 2 | Supplementary material (variant and patient tables) | variant facts held only in supplements | 0 to write; parsing |
| 3 | Completeness pass: per-paper omission check, then revision | stated facts missed (item 3) | about one per paper plus one |
| 4 | Long-context layout: papers first, instructions last, quotes extracted before writing | attention over long input | 0 |
| 5 | Curator checklist: the fields a curator records about each paper | the missed kinds in item 3 | 0 |
| 6 | Per-paper writing, then assembly (map, then reduce) | attention per paper | about one per paper plus one |
| 7 | Sampling ensemble with a merge | run-to-run variation (item 4) | two to four |
| 8 | More reasoning effort for the writer | depth of reading | 0 (longer calls) |
| 9 | Few-shot examples of curated paragraphs | granularity of what is recorded | 0 |
| 10 | Second-hand descriptions from citing papers | unreadable papers | retrieval; tested before (+0.8, not distinguishable from zero) |

Ranking and choice: below, after the evidence review.

## Ranking and choice

From the evidence review (expected effects are estimates, not measurements):

| Rank | Approach | Expected effect on facts conveyed | Decision |
|---|---|---|---|
| 1 | Expanded legal access | large (up to about +12–15 points) | not testable here: the copies cannot be fetched under the terms the project keeps to (see above); needs a licence review and either institutional access or a key for a service that locates legal copies; the pipeline already reads text a user supplies for papers they have the right to read |
| 2 | Curator checklist in the prompt | small (+0.5–2), at no added call | **tested (D1)** |
| 3 | Completeness pass, then revision | small (+1–2), one call per paper plus one | **tested (D2)** |
| 4 | Second-hand descriptions | small; already measured (+1.8 on 96 entries, with more unsupported claims) | not repeated |
| 5 | Sampling ensemble with a merge | small to moderate (+1.5–2.5; oracle ceiling +3.3) | **tested (D3)** |
| 6 | Per-paper writing, then assembly | none to small; measured as the matched evidence graph (+1.8) | not repeated |
| 7–10 | Layout and quotes first; more effort; few-shot examples; question-driven filling | none to small | not tested |

The three tested approaches act on different causes of a miss: D1 on what the writer thinks a curator records, D2 on
attention to each paper, D3 on which facts a single run happens to pick.

## Evaluation design (fixed before any run)

- **Entries.** The 41 entries of the held-out test split (`evalsets/omim100.test.tsv`) that have at least one paper
  readable in full and a direct-reading draft: reading changes can only matter where text is readable, and on
  abstract-only papers direct reading already conveys 97% of the facts the text states. Prompts are written and
  piloted on at most three training-split entries with full text and frozen before the test entries are run.
- **Arms.** Baseline: direct reading as in the main run, its drafts taken before the repair round (rebuilt from cached
  replies). D1: direct reading with the curator checklist (same single call; the house style's "salient findings"
  becomes an explicit list of what a curator records about each paper). D2: the direct-reading draft, then for each
  paper a completeness check listing what the paper states that the draft's text about it omits (the check measured
  in the audit stress test), then one revision call that adds what is listed, keeping citations to the paper. D3:
  three independent direct-reading drafts (the baseline's and two more with fresh samples) and one merge call that
  keeps every distinct statement from any draft, adds nothing, and cites the union of the drafts' papers.
- **Same for every arm.** The same model, efforts (writer and revision high, check medium, merge high), mechanical
  guards, fixed fact lists and judge. No repair round. Claim-level audit without repair on every draft.
- **Completion.** Entries are compared only where every arm completed. A stopped reply is recorded and never retried;
  an ensemble with a stopped member counts as stopped, and a completeness pass with a stopped check counts as
  incomplete.
- **Primary measure.** Facts conveyed, mean over entries; paired difference of each arm from the baseline with a
  bootstrap 95% interval over entries, better/worse/tied and an exact sign test, Holm-adjusted across the three arms.
- **Secondary.** Facts conveyed on facts the supplied text states (all, full-text papers, abstract-only papers);
  claims judged supported, unsupported and contradicted; characters and claims per entry; variants recovered and
  variant precision; calls and list price per entry.
- **Budget.** At most 2,200 new model calls, pilot included.

## Pilot and changes made before the test run

Piloted on three training entries (300148, 600740, 603552; 162 calls). No prompt changed after the first pilot calls;
the piloted prompts are frozen for the test run. Three decisions were taken after the pilot and before any test entry
was run:

- **Audit on a subsample.** The pilot projected about 2,040 calls and $300 for the full design, against a 2,200-call
  cap and an earlier estimate of about $170, most of it in the claim-level audit. The primary endpoint and the
  stated-facts split stay on all 41 entries; the claim-level audit (all arms, without repair) is run on 20 of the 41,
  drawn with `random.Random(20261120)` from the sorted entry numbers.
- **Audit stops.** A stopped audit call leaves that paper's claims not checkable. It does not affect completion (the
  draft exists); claim shares are computed over checkable claims, and the not-checkable count is reported per arm.
- **Cap.** 2,200 new calls including the pilot; the runner halts at the cap.

## Results (41 held-out entries with full text; `results/direct_improve/direct_improve.md`)

Run on 20 November 2026: 1,624 new model calls including the pilot ($218 at list price), 7 replies stopped by the
safety filter (none retried). 38 entries are complete for every arm and compared; the completeness pass lost 3 entries
(118210, 617232, 621030) to stopped replies in its check or revision step. The baseline, direct reading before repair,
conveys 60.3% of facts on these entries (higher than the main set's 49.1% because every entry has full text).

| Arm | Facts conveyed | Difference (95% interval); better/worse/tied | Facts the text states, full-text papers | Facts the text does not state | Claims judged supported (20 entries) | Unsupported + contradicted | Variant precision | List price per entry |
|---|---|---|---|---|---|---|---|---|
| Direct reading (baseline) | 60.3% | – | 88.5% | 10.5% | 97.0% | 6 + 0 | 87.1% | $1.09 |
| D1 curator checklist | 61.9% | +1.6 (+0.5 to +2.7); 23/11/4; sign p = 0.058 | 90.5% (+2.0) | 10.2% (−0.3) | 97.3% | 8 + 2 | 87.5% | $1.15 |
| D2 completeness pass | 62.9% | +2.6 (+1.7 to +3.6); 28/4/6; p < 0.001 | 93.0% (+4.5) | 10.3% (−0.1) | 97.2% | 4 + 0 | 87.1% | $2.10 |
| D3 three drafts merged | 63.4% | +3.1 (+2.1 to +4.2); 31/3/4; p < 0.001 | 92.1% (+3.7) | 12.0% (+1.5) | 95.8% | 14 + 4 | 83.4% | $2.32 |

Means over entries; differences are paired over the 38 compared entries with bootstrap intervals; sign-test p-values
are Holm-adjusted across the three arms (D1 0.058, D2 and D3 below 0.001). Claim shares are over checkable claims on
the 20 audited entries. List price per entry is the whole method from scratch, generation, audit and scoring.

- **The completeness pass is the clearest gain.** It conveys 2.6 more points of curator facts, 4.5 more on facts
  that full-text papers state, with no change in claims judged supported and no change on facts the text does not
  state: what it adds comes from the papers. It about doubles the cost, and its extra calls cost 3 of 41 entries to
  stopped replies.
- **The merged ensemble gains as much, but not all of it from the papers.** About half of its extra comes on facts
  the supplied text does not state (+1.5, +0.4 to +2.7), and it has more unsupported and contradicted claims and lower
  variant precision. Merging three samples brings in content the audit and the papers do not support as well.
- **The checklist costs nothing and probably helps a little:** +1.6 points with an interval that excludes zero, but
  the sign test does not reach 0.05 after adjustment.
- **The gains are on full text.** On abstract-only papers direct reading already conveys 96.9% of the facts the
  abstract states, and no arm moves that by more than a point.
- These sizes are of the order the headroom analysis predicted for changes to reading (3.5–5 points on the main set,
  more on entries with full text); none comes near what access to full text would add.
- Not tested: the checklist and the completeness pass together, and either on entries without full text beyond the
  abstract-only papers inside these entries. Every judgement here is the same model's, as in the rest of the study.

## Extension: checklist and completeness pass together (D4), designed before any run

Asked for after the results above. D4 starts from D1's checklist draft and applies D2's completeness pass unchanged
(the same check prompt; the revision prompt with the checklist house style the draft was written in). Same 41
entries, same scoring and stated / not-stated split, audit without repair on the same 20 sampled entries, the same
completion rules. Comparisons use the entries complete for all five arms. Primary for the extension: D4 minus the
baseline; secondary: D4 minus D2 and D4 minus D1. The four arms already run are not re-run. Cap: 700 new calls for
D4, pilot (the three training entries) included. Piloted first; the test entries are run from the owner's session.

### Result of the extension (`results/direct_improve/direct_improve.md`, section "Extension: D4")

572 new calls including the pilot ($75 at list price), 9 replies stopped by the safety filter (none retried). D4 was
complete on 35 of 41 entries (2 incomplete, 4 without a draft, every loss a stopped reply), so the five arms are
compared on 35 entries; the four earlier arms' 38-entry results above are unchanged.

| On the 35 entries | Baseline | D1 checklist | D2 completeness pass | D3 merge | D4 both |
|---|---|---|---|---|---|
| Facts conveyed | 60.1% | 61.8% | 62.6% | 63.2% | 63.4% |
| Facts the text states | 91.1% | 92.6% | 94.4% | 94.1% | 95.6% |
| … on full-text papers | 88.4% | 90.6% | 92.8% | 92.2% | 94.7% |
| Facts the text does not state | 9.8% | 9.6% | 9.7% | 11.2% | 10.1% |
| Claims judged supported (20 audited entries) | 97.0% | 97.3% | 97.2% | 95.8% | 97.2% |
| List price per entry | $1.09 | $1.15 | $2.10 | $2.32 | $2.11 |

- **D4 against the baseline (primary):** +3.3 points (+2.0 to +4.7; better on 27, worse on 6, tied on 2); +4.6 on
  facts the text states and +6.3 (+4.0 to +8.7) on those of full-text papers; +0.2 (−1.2 to +1.8) on facts the text
  does not state, so the gain comes from the papers. Claims judged supported are unchanged (97.2%; 9 unsupported and 1
  contradicted against 6 and 0).
- **D4 against each part:** +1.6 (+0.7 to +2.5) over the checklist alone, but only +0.8 (−0.4 to +1.8) over the
  completeness pass alone, not distinguishable from zero (on full-text papers' stated facts +1.8, +0.1 to +3.7, sign
  test p = 0.23). The two overlap: the completeness pass already recovers most of what the checklist adds, and on a
  checklist draft it finds fewer omissions to fill (600 against 735 on the same 37 entries).
- **Cost and completion:** the same price as the completeness pass alone ($2.11 per entry), but more entries lost to
  stopped replies (6 of 41 against 3 for the completeness pass and none for direct reading).
- **Reading:** the combination has the best point estimate and is a reasonable default where full text is available;
  most of its gain is the completeness pass's. Every judgement is the same model's.
