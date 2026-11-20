# Second round of experiments: larger inputs, published systems, audit coverage

Design fixed on 20 November 2026, before any of these runs. Results are appended at the end when the runs finish.
The three experiments answer the three gaps the paper's reviewers named that need new work and no new people:

| Gap | Experiment |
|---|---|
| Entries have 2–12 references and fit one prompt, which favours direct reading | A1 natural large-entry tier; A2 controlled padding of the input |
| The strategies are our own implementations, not published systems | B PaperQA2, STORM and GraphRAG as released, on the same papers |
| The audit was tested only on single-value substitutions | C planted misattributions, conflations and omissions |

## Rules common to all three

- One model for everything, as before (Claude Opus 5.5 through the Claude Code command line, replies cached). No other
  provider or key.
- Primary measure as before: OMIM facts conveyed, scored against fact lists fixed before any draft is seen. A reply
  stopped by the model's safety filter is recorded, never retried with a changed prompt, and completion is reported.
- Entries, sizes, questions and analysis below are fixed here. Anything that had to change is listed under
  "Deviations" in the results.
- No claim-level audit and no repair round in A1, A2 and B unless stated: the repair round moves coverage by 0.2
  points (hidden-full-text experiment), and the audit is the largest cost. Every arm of a comparison is treated alike.
- Curator-written wording and the fact lists stay out of git and `results/`.

## A1. Natural large-entry tier

**Question.** Do the strategies still convey the same share of curator-written facts when an entry has many
references and much of their text is readable?

**Entries.** The existing 12 entries with 30–75 references (nearly all abstracts), plus 16 new entries chosen by rule:
eligible phenotype entries (the main set's eligibility rules) with 30–150 references that are in no existing
evaluation set; from a seeded random sample of up to 400 such entries, the 16 with the most references readable in
full (ties by entry number), requiring at least 5. The rule aims at entries whose supplied text is large, not only
whose reference list is long.

**Strategies.** Direct reading (batched above the one-prompt limit), agentic curator, evidence graph, case table
first. Generation and scoring only.

**Analysis.** Completion per strategy. Paired differences from direct reading on entries every strategy completed
(mean over entries, bootstrap interval, better/worse/tied, sign test), for all compared entries and split at the
median of supplied characters. The same on facts the supplied text states. Cost and calls per entry.

## A2. Controlled padding of the input (within-entry manipulation of size)

**Question.** Holding the entry, its papers and its fact lists fixed, how does each strategy's coverage change as the
input grows past what one prompt holds?

**Entries.** 12 entries from the ablation set with at least half their papers readable in full and complete for all
strategies, taken in entry-number order.

**Manipulation.** Unrelated full-text papers cited by other entries are added to the supplied papers, shuffled among
them (seeded): P0 none (the existing drafts); P1 padded to about 500,000 characters (near the one-prompt limit);
P2 padded to about 1,800,000 characters (three or more prompts for direct reading). P1's added papers are a subset of
P2's. The added papers are off-topic by construction: the manipulation is input size, and any loss is attributable
to size alone. The task prompt is unchanged.

**Strategies.** Direct reading, agentic curator, evidence graph, case table first. Generation and scoring only; P0 is
re-scored without repair so that all levels are alike.

**Analysis.** Coverage of the entry's own fixed facts at P0, P1, P2 per strategy; paired change from P0 with
bootstrap interval; strategy-by-size interaction (difference from direct reading at each level). Share of each draft's
paragraphs that cite an added paper. Completion, calls, cost and time per level.

## B. Published systems as released

**Question.** Do released systems, run with their own code, prompts and defaults on the same papers and the same
model, convey more or fewer curator-written facts than our implementations?

**Systems.** PaperQA2 (`paper-qa`), STORM (`knowledge-storm`), GraphRAG (`graphrag`), latest released versions,
installed from the package index. Changed from defaults only: the model endpoint (a local adapter in front of the same
model), the embedding model (a small local one, the same for all three), the corpus (exactly the entry's supplied
papers, at the access level they have), and settings that would call outside search or metadata services. Every
changed setting is listed.

**Task given to each system.** STORM: the entry title as topic. PaperQA2 and GraphRAG (question-answering systems): the
same six section questions per entry, fixed here: description; clinical features; inheritance; molecular genetics
and the variants each paper reported; genotype–phenotype relationships; pathogenesis and functional evidence. Answers
are concatenated. No system is told how it will be scored.

**Entries.** The 38 ablation entries in a seeded order; the first 24 for PaperQA2 and STORM; GraphRAG on as many of
the first 24 as fit in 3,000 model calls (at least 12).

**Scoring.** Citations are mapped back to the supplied papers without editing text. Facts conveyed, credited to
paragraphs citing the paper (as in the paper) and credited anywhere in the draft (fair to systems whose citations do
not map to papers); the same split by whether the supplied text states the fact (a system that conveys facts the text
does not state is drawing on memory). Claim-level audit without repair on paragraphs with mapped citations. Share of
text with no mappable citation. Calls, tokens, time. Compared with direct reading, agentic curator, evidence graph and
case table first on the same entries.

## C. Audit coverage: planted errors beyond single values

**Question.** Which kinds of error does the claim-level audit catch, and which can it not see?

Each class is planted in paragraphs the audit had passed, with the unaltered paragraph re-audited as control. About 60
items per class.

| Class | What is planted | Truth by construction |
|---|---|---|
| C1 citation swap, other entry | the paragraph's citation is replaced by a paper of another entry | the cited paper is about another disease |
| C2 citation swap, same entry | replaced by another paper of the same entry | only for claims naming a variant that does not occur in the new paper's text |
| C3 conflation | one variant-naming sentence from the paragraph about paper A is moved into the paragraph about paper B | the moved sentence, where the variant does not occur in B's text |
| C4 over-citation | a second, non-supporting paper is added to the citation | the claim-level verdict takes the best cited paper, so this should pass; per-paper verdicts are examined |
| C5 dropped qualifier | a restricting phrase is deleted by rule (a count "in 2 of 5", zygosity, "one family", a negation) | the claim becomes broader than the source |
| C6 omitted finding | a supported sentence is deleted | the audit judges only what is written; tested against a separate completeness check |

**C6 completeness check.** A new check lists findings a cited paper states that the draft's text about it omits.
Measured on planted deletions (is the deleted sentence listed?) and on natural omissions (of curator-written facts the
draft omitted although the text states them, how many are listed?), with the number of omissions listed per unaltered
paragraph as the false-alarm side.

**Analysis.** Per class: items, flagged at paragraph level, flagged on the planted claim, verdicts on the planted
claim; the same for controls. From existing audit files, with no new calls: citation precision, the share of
(claim, cited paper) pairs in multi-citation paragraphs where the paper is judged not to support the claim.

## Budget

About 15,000 new model calls in all (A1 4,500; A2 2,000; B 7,000; C 1,200), each experiment stopping at its cap.

## Reduced sizes (same day, before any run finished)

The round was cut to about a third at the project owner's request. The questions, measures and analysis are as
written above; only the sizes change. With these sizes every result is exploratory.

| Experiment | As designed | As run |
|---|---|---|
| A1 natural large-entry tier | 16 new entries; 4,500 calls | 8 new entries (20 with the existing 12); 1,500 calls; the split on facts the text states only if it fits |
| A2 controlled padding | 12 entries; P2 about 1,800,000 characters; 2,500 calls | 8 entries; P2 about 1,200,000 characters (still more than one prompt); 800 calls |
| B published systems | 24 entries for PaperQA2 and STORM; GraphRAG within 3,000 calls | 10 entries for PaperQA2 and STORM; GraphRAG on at least 6 of them within 1,000 calls; about 2,500 calls in all |
| C audit coverage | about 60 items per class; 1,200 calls | about 30 items per class; 600 calls |

About 5,400 new model calls in all.

# Results

Run on 20–21 November 2026 at the reduced sizes. Every number below is in the result files named with it. One model
family wrote, audited and judged everything, as in the rest of the study, and no person checked any judgement. With 4
to 10 entries per experiment these results show directions and large effects only.

## A1. Natural large-entry tier — `results/largeft/large_tier.md`

Eight entries were selected by the rule (from a seeded sample of 200 eligible entries with 30–150 references, the 8
with the most references readable in full: 9 to 33 of 63 to 148 references, 290,000 to 998,000 characters of supplied
text). Four were run, in rule order, before the cap (1,338 calls): 155600, 168600, 152700 and 114500, each with
375,000 to 998,000 characters, and direct reading needing two prompts and a merge on three of them.

**No new entry was completed by all four strategies, so the planned comparison has no new entry in it.** The model's
safety filter stopped at least one strategy on every one of the four:

| Strategy | Complete | Incomplete (a per-paper call stopped) | No draft (the writer stopped) |
|---|---|---|---|
| Direct reading | 1 | 0 | 3 |
| Agentic curator | 2 | 0 | 2 |
| Evidence graph | 0 | 4 | 0 |
| Case table first | 0 | 3 | 1 |

- Per-paper extraction was stopped for 37 papers (evidence graph) and 25 papers (case table first) across the four
  entries. Nothing was retried.
- The tier's comparison therefore rests on the earlier 12 entries alone, which are nearly all abstracts: on the 10 of
  them every strategy completed, the agentic curator is −0.6 points from direct reading (−2.1 to +0.7), the evidence
  graph +0.7 (−2.7 to +3.4) and case table first +0.4 (−1.4 to +2.3), the figures the study already had.
- On the one new entry where every strategy wrote something (152700): direct reading 52.3%, agentic curator 51.5%,
  case table first 49.6% with two papers lost, evidence graph 39.8% with three papers lost. One entry; not a result.
- Even where drafts exist the measure is weak here: the curator paragraphs that are scored concern 5–10% of each new
  entry's references.
- What A1 shows is about completion, not coverage: on large entries with much readable text the safety filter, not
  the strategy, decided which drafts exist. A strategy that makes one call per entry loses the whole entry; a
  strategy that makes one call per paper almost always loses some papers.

## A2. Controlled padding — `results/padding/padding.md`

Six entries were run (the pilot showed eight would not fit the reduced cap; 685 calls). Median input 39,450
characters as cited, about 500,000 at P1 and about 1,190,000 at P2 (27–37 papers; direct reading used three prompts
and a merge at P2).

| Strategy | P0 | P1 | P2 | P2 − P0 (95% interval) |
|---|---|---|---|---|
| Direct reading | 71.3% | 74.9% | 74.5% | +3.2 (−0.7 to +6.8) |
| Agentic curator | 69.8% | 70.6% | 70.3% | +0.5 (−3.4 to +4.4) |
| Evidence graph | 73.5% | 73.3% | 74.1% | +0.7 (−1.0 to +2.5) |
| Case table first | 70.0% | 69.0% | 69.1% | −0.9 (−2.1 to +0.1) |

- No strategy lost more than about a point of its entry's own facts when the input grew thirtyfold with unrelated
  papers. Direct reading's rise is within run-to-run noise (P0 is an earlier generation; there is no P0 replicate).
- No padded draft cited an added paper. The agent opened 5 of 63 added papers at P1 and none of 174 at P2; the
  extract-then-write strategies marked them not relevant. Off-topic padding is easy to ignore, so this tests size, not
  crowding by relevant papers.
- Completion fell for the per-paper pipelines as papers were added: at P2 the evidence graph and the case table were
  each complete on 3 of 6 entries, every loss a safety-filter stop on an extraction call for an added paper. Direct
  reading and the agent completed all 6 at every level. Under the symmetric rule only 2 entries are complete for every
  strategy at every level; on those the ranking is the same at every level. The table above allows losses on added
  papers.

## B. Published systems — `results/external/external.md`

| System | Version | How it was run | Entries completed |
|---|---|---|---|
| PaperQA2 | paper-qa 2026.8.12 | document-query pipeline (`Docs.aquery`), six questions; without its agent, which needs function calling the local adapter does not provide | 10 of 10 |
| GraphRAG | graphrag 3.3.0 | `graphrag init` defaults, standard indexing, local search (and global search), six questions | 4 of 4 attempted; the fifth entry did not fit the 1,000-call cap |
| STORM | knowledge-storm 1.1.1 | its own runner, all four stages, a local vector store over the entry's papers | 0 of 10 |

**STORM produced no article.** The model's safety filter stopped every chain-of-thought prompt of its research stage
(30 of 30 requests; its 20 plain prompts were answered). With no research it wrote an outline from memory and then
failed. Nothing was retried or reworded.

On the 4 entries every system completed (facts conveyed, mean over entries):

| | PaperQA2 | GraphRAG local | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|
| Credited to paragraphs citing the paper | 49.6% | 46.2% | 46.0% | 59.6% | 59.6% | 59.6% | 56.5% |
| Credited anywhere in the draft | 51.6% | 47.3% | 47.7% | 61.5% | 60.9% | 60.8% | 56.5% |
| On facts the supplied text states | 73.9% | 65.8% | 68.2% | 88.8% | 88.4% | 92.0% | 86.8% |
| On facts it does not state | 2.1% | 4.1% | 20.5% | 3.0% | 2.9% | 1.1% | 2.0% |
| Characters written | 15,445 | 37,932 | 63,752 | 11,127 | 11,651 | 14,232 | 14,256 |
| Model calls | 57 | 135 | 165 | 2 | 2 | 7 | 7 |
| List price | $2.17 | $9.29 | $12.14 | $0.36 | $0.39 | $0.80 | $0.88 |

- PaperQA2 on its 10 entries: 47.4% against 61.9% for direct reading, −14.5 points (−21.8 to −7.0), worse on 9 of 10
  entries (sign test p = 0.02). On facts the text states: 70.4% against 88.8%. The first run, with the shared
  embedding model cutting each passage at 512 tokens, gave 49.1%; removing the cut changed retrieval and not the
  result.
- GraphRAG on its 4 entries: local search −13.4 points from direct reading (−25.3 to −1.5), global search −13.6. Four
  entries cannot support a test (the sign test cannot go below p = 0.125).
- The shortfall of both systems is on facts the papers state, not on facts they do not: they convey less of what is
  there, while writing more text and making 25 to 80 times as many calls. The one exception, global search conveying
  20.5% of facts the text does not state, comes mostly from one entry and points to memory entering the community
  reports.
- Claims judged supported, audit without repair on the 4 common entries: PaperQA2 91.4% (0.8% unsupported or
  contradicted), GraphRAG local 89.8% (2.5%), against 96.5–98.6% for the four strategies as stored before repair.
- What this does not show: a ranking of these systems in general. PaperQA2 ran without its agent; each system ran at
  one setting, with one small local embedding model and a model interface that ignores temperature and length
  limits; the questions were ours; the strategies' drafts had been through the repair round and the systems' had not;
  and GraphRAG's entries are the first four of the order, not a sample.

## C. Audit coverage — `results/omim100/audit_stress.md`

Thirty items per class (540 calls). Counts are over items where the truth is known by construction.

| Class | Items | Planted claim flagged | Unaltered paragraph flagged |
|---|---|---|---|
| C1 citation swap, other entry | 30 | 30 (100%) | 0 |
| C2 citation swap, same entry | 26 | 26 (100%) | 0 |
| C3 conflation | 25 | 25 (100%) | 0 |
| C4 over-citation | 30 | 0 | 0 |
| C5 dropped qualifier | 30 | 11 (37%) | 0 |
| C6 omitted finding | 30 | 0 | 0 |

- The audit catches a wrong citation and a sentence moved between papers' paragraphs, and it never flagged an
  unaltered paragraph (0 of 113 paragraphs, 0 of 733 claims).
- It does not see over-citation: the claim's verdict is the best over its cited papers, so an added paper judged
  unsupporting on 176 of 176 claims never shows. In the existing drafts, 4–7% of (claim, cited paper) pairs in
  multi-citation paragraphs are of this kind for the paper-reading strategies and 27% for the memory-only control.
- It rarely sees a claim made broader: a deleted negation was flagged 8 of 8 times, a deleted hedge 2 of 8, and a
  deleted count, zygosity or "one family" 1 of 14.
- It does not see omissions. The separate completeness check listed the deleted finding in 16 of 29 cases in full and
  24 of 29 in full or in part, against 2 of 29 on unaltered text. On real omissions it listed 24 of 60 curator facts
  that the text states and the draft lacks, while listing about ten omissions per paper, a fifth of which match any
  curator fact.
- Limits: the citation swaps are easy cases (the swapped paper is usually about something else); the qualifier rules
  have 2 to 8 items each; the completeness check and its judge are the same model.

# What the round shows

1. **Larger inputs.** Padding an entry's own papers with up to thirty times as much unrelated text did not lower any
   strategy's coverage of the entry's facts, and direct reading across three prompts lost nothing (6 entries). That
   answers the objection in its narrow form: input size as such did not penalise direct reading. It does not answer
   it for large sets of relevant papers: the natural large-entry tier produced no entry that every strategy
   completed. In both experiments, strategies that make one call per paper lost papers to the safety filter as the
   number of papers grew.
2. **Published systems.** On the same papers and model, PaperQA2's document-query pipeline conveyed 14.5 points fewer
   curator-written facts than direct reading on 10 entries (worse on 9), and GraphRAG about 13 points fewer on 4, at
   5 to 33 times the cost and with fewer claims judged supported. STORM could not be run with this model. The systems
   were run at one setting each and PaperQA2 without its agent, so this is not a ranking of the systems; it does
   show that our implementations were not weak stand-ins for these designs on this task.
3. **Audit coverage.** The claim-level audit catches wrong citations and conflation across papers and does not flag
   unaltered text. It cannot see an added irrelevant citation, rarely sees a claim made broader by a dropped
   qualifier, and cannot see omissions; a separate completeness check recovers about half of planted omissions and
   two fifths of real ones, with many listed items the curators did not record.

## Usage

4,591 new model calls in all (A1 1,338; A2 685; C 540; B the rest, including scoring), against the reduced plan of
about 5,400; about $400 at list price (the project's total went from 38,505 calls and $2,896 to 43,096 calls and
$3,294).

## Deviations from the design

- Sizes were reduced to about a third before any run finished (table above), and two experiments ended below their
  reduced size because entries cost more calls than projected: A1 ran 4 new entries (planned 8, floor 6) and A2 ran 6
  (planned 8). GraphRAG ran on 4 entries (floor 6). In each case the call cap was kept.
- A1: the candidate sample was 200 (design 400); the comparison on facts the supplied text states was not made.
- A2: the strict completion rule leaves 2 entries; the table reported allows per-paper losses on added papers.
- B: PaperQA2 ran without its agent; its first run had the embedding cut and was repeated without it; STORM produced
  nothing; GraphRAG global search was added; the audit covers the 4 common entries; the strategies' drafts are after
  their repair round and the systems' drafts had none.
- C: 30 items per class; the natural-omission part used 60 of 130 eligible facts; one unaltered audit served as the
  control for all classes.
- The machine restarted twice during the runs; interrupted jobs were resumed from their files and caches.
