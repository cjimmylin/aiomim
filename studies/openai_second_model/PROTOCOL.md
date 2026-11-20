# Protocol: a second model family

Fixed before any OpenAI request is sent. Deviations are recorded in `outputs/run_log.md` and reported with the
results.

## Why

Every model call of the study went to one Claude model (`claude-opus-5-5`): it wrote the drafts, audited their
claims, split OMIM's paragraphs into the fixed fact lists, marked those facts against the drafts, and judged whether
the supplied text states each fact. The main objection of the reviewers is exactly that: one model family wrote,
audited and judged everything, so the scores could reflect that family's preferences rather than the strategies.
This study replaces the model, and nothing else, in two roles: the judge (part A) and the writer (part B).

## Questions

- **QA1 (judge, main comparison).** Does a second judge mark the same facts present, partly present, absent or
  contradicted in the same drafts, and does it reproduce the strategy means and the paired differences from direct
  reading on the 93 compared entries?
- **QA2 (judge, availability).** Does a second judge agree on whether the text supplied for a paper states each
  fixed fact, and does the stated-facts comparison (strategies within 1–3 points on facts the text states) hold under
  its availability verdicts and its marks? Does the share of facts conveyed from abstract- or title-only papers
  that no supplied text states (1.6% on these 93 entries) hold under its re-check?
- **QA3 (judge, hidden full text).** Under a second judge, is the hidden-full-text effect (full text before repair
  minus abstract only: +43.7 points, 45 of 46 entries higher; second-hand passages: +4.9) reproduced?
- **QB1 (writer).** With a second model writing, do direct reading, the evidence graph and memory only order as
  they did (graph about level with direct reading; memory far below), and how far are its drafts from Claude's?
- **QB2 (writer, access).** With a second model writing, does hiding the full text cost as much coverage?

## The model

`gpt-6.2-astra` (flagship) or `gpt-6.2-sol` (cheaper), chosen in `study.json` before the first request; the same
model for every role and every task in a run. Requests go through the OpenAI Batch API (`POST /v1/responses`, 24-hour
window, 50% of the standard price).

**Effort.** Each stage keeps the effort the project gives it (`aiomim.config.DEFAULT_EFFORT`), sent as the same word
in `reasoning.effort`:

| Stage (project) | Calls in this study | Project effort | `reasoning.effort` |
|---|---|---|---|
| `judge` | fixed-fact marks, availability verdicts | medium | medium |
| `synthesize` | direct reading's writer, the evidence graph's writer | high | high |
| `recall` | the memory-only writer | high | high |
| `extract` | per-paper findings for the evidence graph | medium | medium |
| `normalize` | choosing an HPO term among ontology search hits | low | low |

`xhigh` and `max` map to the same words but no stage of this study uses them. The 6.2 models reject `none`.

**Request.** System prompt and prompt as the `system` and `user` messages; the reply schema the project passes
(`aiomim.llm.schema_for`) unchanged as `text.format` (`json_schema`, `strict: true`, which every schema of the study
satisfies as it is); `store: false`; no output-token limit (the model's own, 128,000).

## What is run

| Task | What | Entries | Units | Code path (unchanged) |
|---|---|---|---|---|
| A1 | fixed-fact marks of the existing drafts of the six strategies (direct, agent, kg, cohort, recall, closedbook) | the 93 compared entries | 558 drafts, 6,239 facts each strategy | `facts.eval_gold_text_frozen`, as `aiomim rescore` |
| A2 frozen | whether the text supplied for the paragraph's paper(s) states each fixed fact | 93 | 450 paragraphs, 6,239 facts | `gaps.gap_entry_frozen`, as `aiomim gaps --frozen` |
| A2 conveyed | for facts direct reading conveyed but the own text states at most partly: whether the other supplied papers state them | 93 | 1,178 facts | `gaps.conveyed_entry`, as `aiomim gaps --conveyed` |
| A3 | fixed-fact marks of the hidden-full-text arms: full text (direct reading's draft before the repair round), abstract only, abstract plus second-hand passages | the 46 entries of the experiment | 138 drafts, 2,120 facts each arm | as `secondhand.rescore_frozen_entry` and `score_before_repair_entry` |
| B1 | new drafts: direct reading, evidence graph, memory only; then their fixed-fact marks | the 30 replicate entries (`evalsets/replicate30.tsv`) | 90 drafts | `pipeline.build_entries` (no audit), then `run_entry`'s scoring |
| B2 | new drafts by direct reading from the full text and with the full text hidden (abstract only), as `secondhand.check_entry` hides it; their marks on the gold paragraphs about the hidden papers | the 46 entries | 92 drafts | `synthesize_direct` / `build_entries`, then as A3 |

Entry lists are in `study.json`. The 93 entries are those every strategy completed in the main comparison
(`results/omim100/strategies.json`; left out: 118210, 300148, 609296, 617232, 620609, 621030, 621068). The 46 are the
hidden-full-text entries with a full-text draft (`runs/secondhand_check_omim100`, `coverage_frozen.per_entry`).

**Inputs.** Everything comes from the private bundle, built from the original runs: the seed (title, symbol,
alternative titles; the causal gene withheld), the papers exactly as the strategies received them (title, abstract,
full text where readable; serialized so that the project's rendering rebuilds every original prompt byte for byte),
the gold standard, the fixed fact lists, the drafts being judged, Claude's marks and verdicts for comparison, the
HPO files, and HGNC's gene-symbol data. No task reads NCBI, Europe PMC or any other source.

**Verification of the inputs.** Every task was replayed over the bundle with the original model's name against the
original runs' cache: every A-task prompt was found there, and the replayed marks and verdicts equal the stored ones
fact by fact (37,434 marks, 6,239 availability verdicts, 3,440 conveyed re-checks, 6,360 hidden-full-text marks); the
writers' first calls were found as well. On the owner's machine, every first-wave request of the judge tasks and
every first call of a writer is checked against the keys of that replay; a request that differs blocks the run.

## Rules

1. **The model is the only variable.** No prompt, system prompt, schema, entry list, effort, guard or scoring rule is
   changed. The fixed fact lists are not split again.
2. **A stop is a result.** A reply stopped by the model's safety filter (a refusal, or an incomplete reply with a
   content-filter reason) is recorded as a stop and never asked again, reworded or not. The project's judge procedure
   re-asks a reply that left fact numbers out with a note appended to the prompt; after a stop that note is not sent:
   the stop is recorded for the re-ask too, and the paragraph's facts stay unjudged.
3. **A malformed reply is asked once more.** A reply that does not parse, does not validate against the project's
   reply model, is cut short (`max_output_tokens`), or is an empty writer reply is asked again once, as a separate
   request; if the second reply fails too, the project's own outcome follows (no verdict for those facts; for a
   writer, no draft: "the model returned an empty reply twice"). A request the Batch API did not run (expired, server
   error) is sent again up to three times; it is not a reply.
4. **No audit, no repair.** The OpenAI drafts are not put through the claim-level audit or the repair round.
5. **Cost cap.** `study.json` sets a hard cap (default $400 with Astra, $120 with Sol). No batch is submitted whose
   estimated cost would take the spend past it; the cap is not raised during a run.
6. **No data leaves except to OpenAI.** Requests carry public paper text, the entry headers, the fixed fact lists and
   OMIM's paragraphs (the mark and availability prompts show them, as they did to Claude). Nothing derived from
   OMIM's wording is committed: `outputs/` and `state/` carry ids, statuses and counts, and OpenAI-written drafts with
   any 60-character span matching OMIM's text replaced by a pointer into that text.

## Measures

- **OMIM facts conveyed** (primary): per draft, (present + half of partial) / facts judged, over the fixed lists of
  the entry's in-scope paragraphs (the cited text of the draft); mean over entries. As in the paper, per-entry
  coverage is rounded to 0.001 for A1 and B1.
- **Agreement between judges**, per fact, on the same draft and the same fixed list: raw agreement and Cohen's kappa,
  on the four marks and on present versus not; for availability, on the three verdicts and on stated versus not. 95%
  percentile bootstrap intervals over entries (2,000 resamples; all facts of an entry move together). Facts either
  judge left unjudged are left out. **Reference:** Claude against itself on the same drafts (the judge replicates
  j1 and j2 of the paper: direct reading and evidence graph on 30 entries; 95.7% raw agreement).
- **Paired differences** between strategies (or arms) under each judge: mean of per-entry differences with a 95%
  bootstrap interval over entries (10,000 resamples), better / worse / tied, exact two-sided sign test; computed with
  `compare._pair_stats` (seed 7 as `compare`; seed 20261119 for the hidden-full-text arms, as `secondhand`).
- **Stated-facts comparison**: every strategy's coverage restricted to facts the supplied text states, states at
  least partly, or does not state (`gaps.compare_by_availability`), under the OpenAI judge's availability verdicts
  and marks, and under Claude's.
- **Completion**: per task, complete / incomplete (finished with unjudged facts, or a per-paper extraction failed) /
  stopped (a safety stop) / failed (two bad replies, or the project's code gave up).
- **Use**: requests, tokens (input, cached, output, reasoning), stops and cost per wave and per task.

## Analysis

The comparison set of each question is fixed by completion, as in the paper: an entry is compared only when every
strategy (or arm) in the comparison has a complete result under the judge in question.

- **QA1.** Report per-fact agreement (overall and per strategy) next to Claude's self-agreement, the six means under
  both judges on the same entries, and the five paired differences from direct reading under both judges. A
  difference is called *reproduced* when the OpenAI judge's interval and Claude's overlap and their signs agree or
  either interval includes zero; *not reproduced* otherwise. The memory-only and recall controls are expected far
  below the reading strategies under any judge; if they are not, the judge is not measuring what the lists say.
- **QA2.** Agreement on availability (own text; other papers), the stated-facts table under both judges, and the
  conveyed-from-nowhere share with OpenAI's re-check.
- **QA3.** The two hidden-full-text differences under both judges on the same entries and paragraphs.
- **QB1.** Under the OpenAI judge: graph minus direct and memory minus direct for OpenAI's drafts, beside the same
  differences for Claude's drafts (Claude judge, from the paper's runs); and OpenAI's drafts minus Claude's drafts for
  each strategy. Under the Claude judge the OpenAI drafts are marked afterwards, on the Claude Code side (`rescore`),
  which completes the writer-by-judge table (2 × 2 for each strategy).
- **QB2.** Full text minus abstract for OpenAI's drafts under the OpenAI judge, beside Claude's on the same entries.

All statistics are descriptive at the paper's level (no new multiplicity correction); the 93-entry replicate noise
of about ±1.0 point on a difference between two strategies is the yardstick for "close".

## What is not tested, and why

- **The agentic curator, case table first and recall-then-verify are not run as writers.** The agent is a
  tool-using session (read and search tools over a folder of papers, through the Claude Code harness); a batch
  request is one structured completion, so an OpenAI agent would need another harness, which changes the method, not
  just the model. Recall-then-verify contains the claim-level audit as one of its own steps, and this study runs no
  audit. The case table is a multi-stage pipeline (per-paper case records, then a rendering) whose result was close
  to the evidence graph's in the main comparison; the evidence graph stands for extract-then-write here, within the
  budget. All three are judged in A1.
- **No claim-level audit and no repair round for any OpenAI draft.** The audit is itself a model judgement; running
  Claude's audit on OpenAI drafts would reintroduce the family this study removes, and a second-family audit is a
  study of its own. The repair round moved direct reading's coverage by +0.2 points (46 entries); B2 is compared with
  Claude's full-text draft *before* repair, and B1 notes that Claude's direct and graph drafts were repaired (memory
  only never was).
- **The fixed fact lists stay Claude's.** They were split once, without sight of any draft, and are what every
  score refers to; splitting them again would change the measuring stick, not the judge. That the lists are
  Claude's is a remaining single-family element of the design.
- **The gold standard, the selection of entries, the papers and the scoring rules are unchanged.** Clinical
  synopsis, variants, gene and inheritance scores of the new drafts need no model and are computed afterwards on the
  Claude Code side from the committed drafts.
- **One run per arm.** No OpenAI replicate is run; the Claude replicates give the run-to-run yardstick.

## Data use

The requests send to OpenAI: public paper text (titles, abstracts, open-access full text), entry headers, and
OMIM-derived material (OMIM's per-paper paragraphs, as deposited in ClinVar, and the fact lists split from them),
which the judge prompts contain. **Before the first request, the owner should confirm that OMIM's terms of use allow
sending this material to a third-party model provider for research, and review OpenAI's API data-use terms**
(retention of batch input and output files, which stay in the account's file storage until deleted; abuse-monitoring
retention; that API data is not used for training by default). Requests are sent with `store: false`. The kit does
not delete uploaded files; they can be deleted in the OpenAI dashboard or with the SDK once the study is done.

## Deviations

Any change to this protocol once requests have been sent, any transport fix to the kit, and any rerun of a failed
task (`collect --retry-failed`) is recorded in `outputs/run_log.md` with the reason.
