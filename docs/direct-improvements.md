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
