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
