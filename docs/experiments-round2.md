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
