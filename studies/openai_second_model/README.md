# A second model family: OpenAI models through the Batch API

Every model call in the study so far went to one Claude model: it wrote the drafts, audited them and judged them
against OMIM's fixed fact lists. This kit repeats the judging, and part of the writing, with an OpenAI model, through
the [OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch), on the owner's machine. The project's
own code runs unchanged: the same prompts, the same reply schemas, the same guards and the same scoring. Only the
model differs. The design is in [PROTOCOL.md](PROTOCOL.md); the files it produces are specified in
[OUTPUT_SPEC.md](OUTPUT_SPEC.md).

## How it works

The project calls a model through `aiomim.llm.LLM`, which reads a disk cache first and calls its backend only on a
miss. Here the backend does not call a model: it records the request and stops the task (`Pending`). One pass over
all unfinished tasks (`collect`) gathers every missing request into a *wave*, which goes to OpenAI as one batch.
When the batch has run, `ingest` writes each reply into the study's cache under the exact key the task looks up,
and the next pass replays everything cached and gets one stage further. A task's result is written only when its
code path finishes. A reply that does not parse or validate is asked once more (under a separate key); a reply the
model's safety filter stopped (a refusal or a content-filter finish) is recorded as a stop and never asked again.

The tasks read nothing from the network: papers, gold standard, fixed fact lists, drafts, the ontology and the
HGNC gene-symbol data all come from a private bundle, and `collect` runs with every socket connection in the process
disabled. Each wave records how many network attempts it saw (zero is the only acceptable number).

## Two phases

**1. The OpenAI side, on the owner's machine, driven by Codex.**

```bash
# once: a checkout of this repository at the commit the bundle was built for (check verifies it)
python3 -m venv .venv && . .venv/bin/activate
pip install -e . && pip install -r studies/openai_second_model/requirements.txt
export PYTHONPATH=src OPENAI_API_KEY=...            # the key is read by the SDK and never printed

S=studies/openai_second_model
# place the bundle (delivered out of band) and its checksum:
#   $S/private/openai_study_bundle.tar.gz  and  $S/private/openai_study_bundle.tar.gz.sha256
python -m aiomim.openai_study check --study $S      # unpacks the bundle, checks everything; must say "ok": true
python -m aiomim.openai_study plan  --study $S      # 1,064 tasks -> state/tasks.json
python -m aiomim.openai_study smoke --study $S      # submits <= 8 requests (one per kind of call)
python -m aiomim.openai_study smoke --study $S      # again later: polls; "passed": true when the format works
python -m aiomim.openai_study step  --study $S      # repeat until the phase is "done" (see below)
python -m aiomim.openai_study report   --study $S   # writes outputs/
python -m aiomim.openai_study validate --study $S   # schemas and OMIM wording; must exit 0
git add studies/openai_second_model/state studies/openai_second_model/outputs   # never private/
```

`step` is the only command a driver repeats. It polls the open batches, ingests what has come back, collects the
next wave and submits it, prints one line and writes `state/status.json` with `phase`:

| Phase | Meaning | What to do |
|---|---|---|
| `waiting_for_batch` | a batch is running at OpenAI | wait (15–30 minutes is reasonable) and run `step` again |
| `ready` | requests are collected and can be submitted | run `step` again now |
| `done` | every task has finished | run `report`, then `validate`, then commit `state/` and `outputs/` |
| `blocked` | something needs a person (the reason says what) | stop; read `reason`, `state/tasks.json` and `private/logs/` |

Every command is safe to re-run and the work survives a restart: run `step` again. `private/` holds the replies
already paid for (`private/work/home/cache/llm`): never delete it while the study runs. Do not change `study.json`'s
model during a run (the model is part of every cache key), and do not edit any file under `src/`.

**2. The Claude Code side, afterwards, in this repository.** The committed `outputs/` are parsed directly: every
OpenAI mark and verdict sits next to Claude's for the same fact id. Drafts are committed with any span that matches
60 characters of OMIM's own text replaced by a marker (house-style variant sentences do); the gold text is local
here, so the full drafts come back with

```bash
python -m aiomim.openai_study restore-drafts --study $S --gold-runs runs/omim100 --out runs/openai_drafts --layout run
AIOMIM_RUNS=runs/openai_drafts aiomim rescore B1      # the Claude judge on the OpenAI writer's drafts
```

## Requirements

- Python 3.10 or newer (3.13 tested); the project's dependencies (`pip install -e .`); `openai` (submit, poll, step,
  smoke) and `jsonschema` (validate), from `requirements.txt`.
- `OPENAI_API_KEY` for an account with access to `gpt-6.2-astra` or `gpt-6.2-sol` and the Batch API. Network access
  to `api.openai.com` only.
- About 1 GB of disk: the bundle (14 MB packed, 120 MB unpacked), the study's cache and the request and response
  files.

## Costs

Batch prices (per 1M tokens, 50% of the standard rate, as of 20 November 2026): `gpt-6.2-astra` input $4.00, cached
input $0.20, output $20.00; `gpt-6.2-sol` input $1.00, cached $0.05, output $5.00. `study.json` sets the model and a
hard cap (default $400 for Astra, $120 for Sol); `submit` refuses a batch whose estimated cost would take the spend
past the cap. Before any batch has returned, input tokens are estimated as request characters / 3.0 (deliberately
high; OpenAI tokenisers give about 4 characters per token on English text) and output tokens from a per-stage table
in `study.json` that leaves room for reasoning; after a stage has 20 replies its measured ratios are used instead.
The ledger (`state/ledger.json`) holds the real tokens and cost of every reply.

Estimated cost of the whole study, from a full dry run of every task (request sizes exact; output tokens as Claude's
replies to the same calls, once and twice over for reasoning; marks of the new drafts added):

| Task | Requests (wave 1) | Astra | Sol |
|---|---|---|---|
| A1 marks, six strategies, 93 entries | 2,545 | $48–86 | $12–21 |
| A2 availability, own text | 449 | $16–28 | $4–7 |
| A2 conveyed facts, other papers | 372 | $17–25 | $4–6 |
| A3 marks, hidden-full-text arms | 307 | $6–11 | $2–3 |
| B1 writers (direct, graph, memory) and their marks | 205 + about 450 later | $26–47 | $6–12 |
| B2 writers (full text, abstract) and their marks | 80 + about 340 later | $19–34 | $5–9 |
| Total (plus 5–10% for re-asks) | | about $140–250 | about $35–60 |

The kit's own (conservative) estimate for wave 1 is about $307 with Astra and $77 with Sol, inside the caps.

## Time

A batch finishes within its 24-hour window, usually much sooner. The study needs about 4 to 7 waves: the judge tasks
finish in the first one or two (a reply that misses a fact number, or does not parse, is asked again in the next),
the writers need more because their stages build on each other (evidence graph: extraction, term choice, writing,
marks). Wave 1 has about 4,000 requests (45 MB); later waves are small.

## Files

| Path | In git | What |
|---|---|---|
| `study.json` | yes | model, effort mapping, prices, cap, entry lists per task |
| `PROTOCOL.md`, `OUTPUT_SPEC.md`, `schemas/` | yes | the design and the output format |
| `state/` | yes (written by the kit) | tasks, waves, batches, ledger, status: ids, counts and costs only |
| `outputs/` | yes (written by `report`) | marks, availability, drafts, summary, run log |
| `private/` | **never** | bundle, request and response files, the study's cache, results, logs |

## The kit

The code is `src/aiomim/openai_study/` (`python -m aiomim.openai_study --help`); the tests are
`tests/test_openai_study.py` (no OpenAI call; an end-to-end dry run with a fake provider that replays this project's
own cached Claude replies runs where the original runs' data is present). The bundle is built here with
`python -m aiomim.openai_study bundle` from `runs/` and `data/`; its manifest records the code fingerprint (hashes of
every prompt, schema and effort the study uses), and its verification replays every task over the bundle against
the original runs' cache: all 37,434 fixed-fact marks, 6,239 availability verdicts, 3,440 conveyed-fact re-checks
and 6,360 hidden-full-text marks came back identical, so the bundle reproduces the original prompts byte for byte.

## OpenAI documentation relied on

Read on 20 November 2026:

- Batch API guide: <https://developers.openai.com/api/docs/guides/batch> (input line format, `/v1/responses`,
  `completion_window` "24h", 50,000 requests and 200 MB per file, output and error files, `batch_expired`, output
  order not guaranteed, 50% price)
- Batch object reference: <https://developers.openai.com/api/reference/resources/batches> (statuses, file ids,
  `request_counts`, `errors`, `usage`)
- Responses API reference: <https://developers.openai.com/api/reference/resources/responses/methods/create>
  (`input` messages, `reasoning.effort`, `text.format` json_schema with `name`/`schema`/`strict`, response `status`,
  `usage` fields)
- Structured Outputs guide: <https://developers.openai.com/api/docs/guides/structured-outputs> (strict-mode schema
  subset, `refusal` content parts, `incomplete` with `max_output_tokens` or `content_filter`)
- Reasoning guide: <https://developers.openai.com/api/docs/guides/reasoning> (effort values; the 6.2 models reject
  `none`; reasoning tokens billed as output)
- Model pages: <https://developers.openai.com/api/docs/models/gpt-6.2-astra>,
  <https://developers.openai.com/api/docs/models/gpt-6.2-sol> (context, Batch and Structured Outputs support, prices)

Where these pages leave room the parser is tolerant: an error may arrive as the line's `error`, as a non-200
`status_code` with `body.error`, or as a body with status `failed`; a refusal is any content part of type `refusal`;
a content-filter stop is status `incomplete` with reason `content_filter` (or a content part that says so); a
top-level `output_text` is accepted when no message part carries text; usage fields default to zero when absent.
