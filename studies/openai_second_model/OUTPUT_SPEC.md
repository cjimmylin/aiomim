# Output specification (version 1.0)

What the driver commits and Claude Code parses. Everything under `outputs/` is written by `report` and checked by
`validate` (the JSON Schemas in `schemas/`, and no 60-character window of OMIM's own text); everything under
`state/` is written by the other commands. Neither holds paper text, prompts, replies, judge notes or OMIM wording:
only ids, statuses, counts, costs and the OpenAI-written drafts.

**Ids.** `mim` is the six-digit entry number. A fixed fact's `id` is `<paragraph key, 12 hex digits>.<n>` (`n` its
position in the frozen list), exactly as in the project's `eval.<strategy>.json` → `gold_text_frozen` and
`gold_facts.json`; `paragraph` is its first part. `content_level` is how the paragraph's paper(s) could be read in the
original run (`fulltext`, `abstract`, `title`, `not_retrieved`; the lowest over the paragraph's papers; for the
abstract-only arms a hidden paper counts as `abstract`).

**Statuses.** A mark is `present`, `partial`, `absent`, `contradicted`, `unjudged` (no verdict was obtained), or
`null` (no mark: the task did not finish, or the draft does not exist). An availability verdict is `yes`, `partly`,
`no`, `unjudged` or `null`. A task's status is `complete`, `incomplete`, `stopped`, `failed`, or (not finished)
`pending` / `waiting` / `error`:

| Status | Meaning |
|---|---|
| `complete` | the code path finished and every fact got a verdict (a writer: a draft, no per-paper failure) |
| `incomplete` | finished, but some facts are `unjudged`, or (evidence graph) a per-paper extraction failed |
| `stopped` | a reply was stopped by the model's safety filter (a writer: no draft; a judge: those facts unjudged) |
| `failed` | two bad replies to the same call, or the project's code gave up (a writer: no draft) |

## outputs/marks/<task>/<mim>.<strategy>.json

One file per draft judged (schema `marks.schema.json`). `task` is `A1`, `A3`, `B1` or `B2`; `strategy` is the
strategy (`direct`, `agent`, `kg`, `cohort`, `recall`, `closedbook`) or the arm (`fulltext_before_repair`,
`abstract`, `secondhand` for A3; `fulltext`, `abstract` for B2).

```json
{"spec_version": "1.0", "task": "A1", "mim": "603552", "strategy": "direct", "status": "complete",
 "openai_model": "gpt-6.2-astra",
 "draft": "claude_main_run",
 "claude_marks_of": "same_draft",
 "claude_source": "omim100/603552/eval.direct.json#gold_text_frozen",
 "counts": {"openai": {"present": 35, "partial": 10, "absent": 23, "contradicted": 0, "n_judged": 68, "unjudged": 0,
                       "coverage": 0.5882},
            "claude": {"...": "same fields"}},
 "facts": [{"id": "427741b5c426.1", "paragraph": "427741b5c426", "content_level": "fulltext",
            "openai": "present", "claude": "present", "claude_j1": "present", "claude_j2": "present"}]}
```

| Field | Meaning |
|---|---|
| `draft` | whose draft was marked: `claude_main_run` (A1), `claude_hidden_fulltext` (A3), `openai` (B1, B2) |
| `claude_marks_of` | what `claude` marks: `same_draft` (A1, A3: Claude's marks of this very draft), `claude_draft_same_strategy` (B1: Claude's marks of Claude's own draft of the strategy, main run, after its repair round; memory only is never repaired), `claude_draft_same_arm` (B2: Claude's full-text draft before repair, or its abstract-only draft) |
| `facts[].openai` | the OpenAI judge's mark |
| `facts[].claude` | Claude's mark (see `claude_marks_of`) |
| `facts[].claude_j1`, `claude_j2` | A1 only, where they exist (direct and kg on the 30 replicate entries): Claude's judge replicates of the same draft |
| `counts.*.coverage` | (present + half of partial) / n_judged, unrounded |
| `writer_status` | B1, B2: the status of the writing alone |

Facts are listed in the order of the frozen lists, paragraph by paragraph; every in-scope fact of the entry
(A3, B2: of the paragraphs about the hidden papers) appears once.

## outputs/availability/<mim>.json

One file per A2 entry (schema `availability.schema.json`): every fixed fact of the entry with both judges'
availability verdicts for the text supplied for its paper(s), cut as direct reading's writer saw it.

| Field | Meaning |
|---|---|
| `status.frozen`, `status.conveyed` | the two A2 tasks' statuses |
| `facts[].openai`, `facts[].claude` | is the fact stated in its own paper's text (`gaps --frozen`) |
| `facts[].claude_direct_mark` | Claude's mark of the fact in direct reading's draft (what selects the conveyed facts) |
| `facts[].rechecked` | present when direct reading conveyed the fact (Claude's marks); true when Claude's own-text verdict was `no` or `partly`, so the other papers were checked |
| `facts[].claude_other`, `openai_other` | is it stated in the entry's other supplied papers (`gaps --conveyed`; the same prompts for both judges) |
| `facts[].claude_class` | Claude's stored class (`stated`, `partly_stated`, `stated_elsewhere`, `partly_elsewhere`, `not_in_supplied_text`, `unjudged`) |
| `facts[].class_with_openai_other` | the class with Claude's own-text verdict and OpenAI's other-papers verdict |

## outputs/drafts/<task>/<mim>/entry.<strategy>.json and .md

B1 and B2 drafts in the project's `GeneratedEntry` format (`aiomim.models`; schema `draft.schema.json`) and its
Markdown rendering (`render.entry_markdown`, no audit badges). The drafts were not audited: every paragraph's
`checks` is empty. `meta.stopped` is set when no draft was written (the entry then has no paragraphs).

A span of a draft that matches 60 characters of OMIM's own text (the house style's variant sentences can) is
replaced by `[omitted: matches OMIM text; redaction <k>]`, and `meta.redactions[k]` records how to put it back without
quoting it: `segments` (pointers: `ref` = `{"paragraph": <paragraph key>}`, `{"fact": <fact id>}` or
`{"definition": <mim>}`; `start` and `length` in that text after whitespace is collapsed and letters lower-cased),
`upper` (positions to capitalise) and `other` (any other character that differs). `meta.redacted_spans_matching_omim`
counts them. `python -m aiomim.openai_study restore-drafts --gold-runs runs/omim100 --out <dir>` restores every
draft exactly from the local gold text (`--layout run` adds what `aiomim rescore` needs). The Markdown is rendered
from the redacted entry; restore it by rendering the restored JSON.

## outputs/summary.json and summary.md

`summary.md` is a readable rendering of `summary.json` (schema `summary.schema.json`). Fractions are 0–1; paired
rows are `compare._pair_stats` objects: `n`, `difference`, `ci95` [low, high], `median_difference`, `better`,
`worse`, `ties`, `sign_test_p`, `ci_unreliable` (fewer than 20 entries).

| Key | Content |
|---|---|
| `openai_model`, `bundle_id`, `phase`, `generated_at` | provenance |
| `files` | number of files written per kind |
| `completion.<task>.<strategy or arm>` | counts of `complete`, `incomplete`, `stopped`, `failed`, `unfinished` |
| `agreement.A1.all_strategies`, `.by_strategy.<s>` | `four_marks` and `present_vs_not`: `n_facts`, `n_entries`, `raw_agreement`, `raw_agreement_ci95`, `kappa`, `kappa_ci95`, `confusion` (rows OpenAI, columns Claude, order of `categories`) |
| `agreement.A3.<arm>` | the same per hidden-full-text arm |
| `agreement.A2.own_text`, `.other_papers` | `three_verdicts` and `stated_vs_not` |
| `agreement.claude_self_baseline` | `claude_main_vs_j1`, `claude_main_vs_j2` (Claude against itself) and `openai_vs_claude_main` on exactly those drafts |
| `A1` | `entries` compared, `coverage.<judge>.<s>.mean_over_entries`, `versus_direct.<judge>.<s>` (paired) |
| `B1` | `entries`, `coverage` and `versus_direct` for `openai_writer_openai_judge`, `claude_writer_claude_judge`, `claude_writer_openai_judge`; `writer_effect.<s>` (OpenAI draft minus Claude draft, OpenAI judge) |
| `stated_facts.<judge>.<restriction>.<level>` | restrictions `all`, `stated`, `stated_or_partly`, `not_stated`; levels `all`, `fulltext`, `abstract`; `by_strategy.<s>` (`mean_over_entries`, `n_entries`, `n_facts`) and `versus_direct.<s>` |
| `conveyed_facts` | facts conveyed in full from abstract- or title-only papers: class counts and `share_not_in_supplied_text`, `claude` (stored) and `claude_own_openai_other` |
| `hidden_fulltext.A3.<judge>` | `mean_over_entries` per arm, `fulltext_before_repair_minus_abstract`, `secondhand_minus_abstract` (paired), `entries` |
| `hidden_fulltext.B2` | `openai_writer_openai_judge` and `claude_writer_claude_judge_same_entries`: `fulltext_minus_abstract` |
| `usage.by_wave.<wave>`, `.by_task_kind.<task>`, `.totals` | requests, replies, ok, invalid, incomplete, stops, transient, rejected, input / cached / output / reasoning tokens, cost_usd |
| `redactions` | drafts with redacted spans, number of spans |

## outputs/run_log.md

One table row per `step` (and per smoke submission and check): time (UTC), wave, batch ids, phase, reason, spend
so far. The driver adds a line for every deviation and transport fix.

## state/ (written by the kit; committed)

| File | Content |
|---|---|
| `tasks.json` | every task: `kind`, `mim`, `variant`, `status`, waves it waited in, requests it recorded, `detail` (counts), kit `error` if any |
| `waves/wave_NNN.json` | per wave: tasks run and finished, requests by stage label and task kind with estimated tokens and cost, batch-file parts, `network_attempts` (must be 0), `prompt_check` (requests identical to the original runs' prompts) |
| `batches.json` | per batch: wave, part, batch id, input file id, status, request counts, estimated cost, output and error file ids, outcomes at ingest |
| `ledger.json` | real usage per wave, stage label and task kind: requests, replies, ok, invalid, incomplete, stops, transient, rejected, tokens and cost |
| `smoke.json` | the smoke batch: ids, per request label, reply kind, schema validity and usage; `passed` |
| `status.json` | the last `step`: `phase`, `reason`, `wave`, task counts, `tasks_finished` / `tasks_planned`, `requests` (`submitted`, `replies`, `completed`, `refused`, `failed`), smoke state, `spent_usd`, `cap_usd`, open batches |
| `check.json` | the last `check` (no secrets: whether `OPENAI_API_KEY` is present, never its value) |

Stage labels: `judge:mark`, `judge:avail`, `judge:avail_other`, `synthesize:direct`, `synthesize:kg`,
`recall:closedbook`, `extract`, `normalize`.
