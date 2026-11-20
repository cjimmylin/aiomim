# Experiment B harness: published systems as released

Shared code for running PaperQA2 (`paper-qa`), STORM (`knowledge-storm`) and GraphRAG (`graphrag`) on the
papers OMIM's curators cited, with the project's one model, and scoring what they write exactly as the
project's own strategies are scored. The design is `docs/experiments-round2.md`, section B.

**Reduced size (budget).** PaperQA2 and STORM run on the **first 10 entries** of the seeded order (not 24);
GraphRAG on as many of those 10 as fit in **1,000 model calls** (at least 6), taken in order.
`evalsets/external38.tsv` lists all 38 entries in the seeded order; the code's default subset is 10
(`corpus.N_MAIN`, `corpus.main_set()`).

| Module | What it gives you |
|---|---|
| `shim` | local OpenAI-compatible server in front of the project's model and the local embedding model |
| `corpus` | the entry order; each entry's supplied papers exported as text files |
| `tasks` | STORM's topic; the six section questions for PaperQA2 and GraphRAG |
| `adapt` | the intermediate format: validate, save, convert to the project's entry format |
| `score` | scoring (a)–(f), comparison strategies, the summary across systems |
| `sys_echo` | a trivial stand-in system: a worked example of the whole path |

## Rules for an integration

- Your code lives in **one file, `src/aiomim/external/sys_<name>.py`** (`paperqa2`, `storm`, `graphrag`). Do not
  edit the shared modules; ask for a change instead.
- The published package lives in **its own virtual environment `.venvs/<name>/`** (git-ignored), created with
  `uv venv .venvs/<name> -p 3.13` (or the Python the package needs) and `VIRTUAL_ENV=.venvs/<name> uv pip install <package>==<latest>`.
  `sys_<name>.py` runs in the project environment, starts the adapter, and runs the package **as a subprocess**
  with `.venvs/<name>/bin/python` (a small driver script of yours, kept in your file or written to the run folder).
- Change from the package's defaults **only** what the design allows: the model endpoint (this adapter), the
  embedding model (this adapter's), the corpus (exactly the exported papers), and settings that would call outside
  search or metadata services (turn them off). **Record every changed setting** in `meta.settings_changed`
  (setting, default, value, reason); the summary prints them as a table.
- The only model is the project's, through this adapter. Never give a subprocess another provider's endpoint or key:
  build its environment from scratch and do not pass on `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_*` or
  similar from the parent environment (an OpenRouter credential exists in this environment; it must not be used).
  Use a dummy key, e.g. `OPENAI_API_KEY=sk-local-dummy`.
- A reply stopped by the model's safety filter is recorded, never retried with a changed prompt, never worked around.
- Curator-written wording (gold paragraphs, fact lists) never goes under `results/` or into any git-tracked file.
  You never need it: scoring reads it itself.
- Write only under `runs/external/<name>/`. Do not `git add`/`commit`.

## The adapter

From Python (what `sys_<name>.py` should do — one adapter per entry, so the ledger and the tag are per entry):

```python
from aiomim.external.adapt import entry_dir
from aiomim.external.shim import ShimServer
folder = entry_dir("paperqa2", mim)                  # runs/external/paperqa2/<mim>/
with ShimServer(tag=f"paperqa2/{mim}", ledger=folder / "ledger.jsonl", max_concurrency=6) as base_url:
    ...  # base_url == "http://127.0.0.1:<free port>/v1"; run the subprocess here
```

From the shell: `PYTHONPATH=src python -m aiomim.external.shim --port 8765 --ledger runs/external/x/ledger.jsonl --tag x/621313 [--effort medium] [--max-concurrency 6]`.

It binds to 127.0.0.1 only and serves:

- `POST /v1/chat/completions` — one call of the project's model (`claude-opus-5-5` through the Claude Code
  command line, effort **medium** for every system) per request. Non-streaming, or `stream: true` answered as a
  minimal event stream carrying the whole reply (and a usage chunk if `stream_options.include_usage`).
- `POST /v1/embeddings` — `BAAI/bge-small-en-v1.5` through fastembed (ONNX export
  `Qdrant/bge-small-en-v1.5-onnx-Q`; 384 dimensions; inputs truncated at 512 tokens), the same for all
  systems, local. `encoding_format` float or base64. Inputs must be strings: token-id arrays get HTTP 400
  (LangChain-style clients: set `check_embedding_ctx_length=False`). The `model` name you send is ignored.
- `GET /v1/models`. (Paths without `/v1` work too.)

Point clients at it:

- OpenAI SDK: `OpenAI(base_url=base_url, api_key="sk-local-dummy")`, or env `OPENAI_BASE_URL=<base_url>`,
  `OPENAI_API_BASE=<base_url>` (older code), `OPENAI_API_KEY=sk-local-dummy`.
- LiteLLM: `model="openai/claude-opus-5-5"`, `api_base=<base_url>`, `api_key="sk-local-dummy"`; embeddings
  `model="openai/bge-small-en-v1.5"` with the same `api_base`. The model name after `openai/` is only echoed in the
  ledger (`requested_model`); every request goes to the project's model. Use `claude-opus-5-5` so the ledger is
  readable.
- Tagging: each ledger line carries the adapter's tag, unless the request has an `X-Aiomim-Tag` header or a string
  `user` field, which then wins. Use `<system>/<mim>` or a sub-tag `<system>/<mim>/<anything>` (scoring sums both).

Environment for the subprocess (offline and quiet):

```
OPENAI_API_KEY=sk-local-dummy  OPENAI_BASE_URL=<base_url>  OPENAI_API_BASE=<base_url>
NO_PROXY=127.0.0.1,localhost   no_proxy=127.0.0.1,localhost     # the box has an HTTPS proxy configured
LITELLM_LOCAL_MODEL_COST_MAP=True  LITELLM_TELEMETRY=False       # no cost-map download, no telemetry
ANONYMIZED_TELEMETRY=False  DO_NOT_TRACK=1  OTEL_SDK_DISABLED=true  # chromadb / generic telemetry off
HF_HUB_OFFLINE=1  TRANSFORMERS_OFFLINE=1                         # nothing should load models from the hub
TIKTOKEN_CACHE_DIR=<abs path>/data/cache/tiktoken                # if the package counts tokens with tiktoken
```

tiktoken downloads its encoding files on first use (from `openaipublic.blob.core.windows.net`); if that host is
blocked, fill `TIKTOKEN_CACHE_DIR` once from an environment where it works. LiteLLM ships its own copies. (Not tested
for any of the three packages yet.)

### What every integrator must know about the adapter

- **Message mapping.** All `system`/`developer` messages are joined (blank line between) into the system prompt;
  with none, the system prompt is "You are a helpful assistant.". A single user message is the prompt verbatim.
  Anything longer (several user messages, assistant turns) is rendered as one prompt: an instruction ("Below is a
  conversation … Write the assistant's next reply …"), then a `<transcript>` block with each turn under a
  `[User]` or `[Assistant]` label (with `(name)` if the message has one). If the history ends with an assistant
  message, the model is asked to continue it. The CLI model has no native multi-turn here; it sees one prompt.
- **Ignored parameters.** `temperature`, `top_p`, `max_tokens`, `max_completion_tokens`, `seed`, penalties,
  `logit_bias`, `logprobs` and similar cannot reach the command-line model; they are accepted, ignored, and listed in
  each ledger line's `ignored_params`. Replies are not shortened by `max_tokens`; no logprobs are returned.
- **Refused (HTTP 400):** `tools`, `functions`, `tool_choice` other than "none", tool/function messages,
  `n` other than 1, non-text content (images), `/v1/completions` and `/v1/responses`. If the package needs tool
  calling for something, switch that feature off (and record it), do not work around the refusal.
- **`stop`** truncates the reply at the earliest stop string (`finish_reason` stays "stop").
- **JSON.** `response_format: json_object`: the system prompt asks for one JSON object; a reply that does not parse
  is asked once more; if it still does not parse it is returned as is (ledger `json_valid: false`). `json_schema`:
  the CLI's structured output when the schema's top level is an object (local `$ref`s are inlined), otherwise
  instructed like json_object with the schema shown.
- **Safety stop.** Returned as a normal completion with empty content and `finish_reason: "content_filter"`,
  counted in the ledger (`safety_stop: true`), cached as a stop, never retried. Your integration must count stops
  (`meta.stops`) and, if the system produces nothing for an entry, save `stopped` with the reason.
- **Errors.** Transient model failures are retried inside the adapter with back-off (up to 5 tries, up to minutes).
  An exhausted usage limit is HTTP 503, any other model failure HTTP 502. Set the client timeout generously
  (≥ 900 s) and its own retries low; a 503 means stop the run.
- **Cache and determinism.** Replies are cached in the project's disk cache (`data/cache/llm`) under model,
  effort, system prompt, rendered prompt, schema and JSON mode. A re-run on the same entry makes no new calls and
  gets identical replies — also when a system re-asks the same prompt hoping for variation. Identical concurrent
  requests make one call.
- **Speed.** One call costs at least ~2–3 s (command-line start-up) and ~1,400 input tokens of fixed overhead; a
  6,600-token prompt took 13 s, a 24,000-token prompt 18 s (echo stand-in). Concurrent model calls are capped by
  `max_concurrency` (default 6); cache hits do not wait.
- **Ledger line** (JSON, one per request): `time, endpoint, tag, requested_model, model, effort, stream,
  ignored_params, rendering (single|transcript), n_messages, response_format, prompt_chars, status, cached, fresh,
  model_calls, json_handling, json_valid, input_tokens, output_tokens, cost_usd (list price, as the project's usage
  ledger reports it; a cached line repeats the stored figures, `fresh` says whether this request paid them),
  call_seconds, seconds (wall), safety_stop, finish_reason, stop_applied, key, error, notes`.

## Entries and corpus

```python
from aiomim.external.corpus import main_set, export_entry
for mim in main_set():                       # the first 10 of evalsets/external38.tsv
    c = export_entry(mim, entry_dir("paperqa2", mim) / "corpus")
    c.title_ordinary, c.alt_titles, c.pmids  # header (the causal gene is withheld)
```

`export_entry` writes `<pmid>.txt` per paper (the paper exactly as direct reading shows it to its writer: the
reference line, a blank line, `TITLE:` / `ABSTRACT:` / `FULL TEXT:` cut to an equal share of 600,000 characters;
a title-only paper is its reference line and title), `papers.csv` (pmid, title, first_author, year, journal,
access_level, characters, label, file) and `entry.json` (mim, title, title_ordinary, alt_titles, pmids, …). Give
the system the `.txt` files only (not the CSV or JSON, unless it needs metadata you then record as a changed
setting). Shell: `PYTHONPATH=src python -m aiomim.external.corpus export 621313 /some/dir`.

## Task wording (`tasks`)

`storm_topic(title)` gives STORM's topic; `section_questions(title)` the six questions (keys `description`,
`clinical_features`, `inheritance`, `molecular_genetics`, `genotype_phenotype`, `pathogenesis`) in their fixed
order, each with a section heading. Ask them as worded; use the heading as each answer's `section`; keep the order.

## The intermediate format

One file per system and entry, written with `adapt.save_output(output)`, which validates it and writes
`runs/external/<system>/<mim>/output.json` plus the converted draft `entry.<system>.json` / `.md`:

```json
{
  "system": "paperqa2",
  "mim": "621313",
  "stopped": null,
  "blocks": [
    {"section": "Clinical features",
     "text": "Patients present with movement disorders in mid-adulthood (Rutten2024 pages 2-3).",
     "pmids": ["38430071"],
     "citations": ["(Rutten2024 pages 2-3)"]},
    {"section": "Inheritance", "text": "Inheritance is autosomal recessive.", "pmids": [], "citations": []}
  ],
  "meta": {
    "package": "paper-qa", "version": "x.y.z",
    "settings_changed": [{"setting": "llm", "default": "<package default>", "value": "openai/claude-opus-5-5",
                          "reason": "the local adapter in front of the project's model"}],
    "calls": 31, "stops": 0, "seconds": 412.5,
    "tag": "paperqa2/621313", "ledgers": ["runs/external/paperqa2/621313/ledger.jsonl"]
  }
}
```

- `blocks`: the system's output in order, **text unedited** (citation markers may stay in the text). A block is a
  paragraph or answer; split long answers at blank lines if you like, never rewrite.
- `pmids`: the supplied papers the block's citations map to — your system-specific mapping (e.g. PaperQA2's doc
  keys, STORM's `[n]` URL list, GraphRAG's source ids → the `<pmid>.txt` file → PubMed id). Only supplied PMIDs
  are accepted. A block whose citations do not map gets `[]`: it is kept as an uncited paragraph, counts for
  whole-draft scoring and for the uncited share.
- `stopped`: null, or the reason when the system produced no blocks at all (then `blocks` may be empty).
- Conversion: consecutive blocks with the same `section` form one section; each block is one paragraph citing its
  `pmids`.

## Scoring and summary

```
PYTHONPATH=src python -m aiomim.external.score score --system paperqa2 [--entries 621313 ...] [--audit] [--jobs 2]
PYTHONPATH=src python -m aiomim.external.score summarize            # results/external/external.json and .md
```

`score` writes `runs/external/<system>/<mim>/eval.<system>.json`: (a) facts conveyed credited to paragraphs citing
the paper; (b) credited anywhere in the draft; (c) both split by whether the supplied text states the fact (stored
availability judgements); (d) with `--audit`, the claim-level audit without repair on paragraphs with mapped
citations (off by default; costs calls); (e) uncited share of characters; (f) usage from the ledger lines tagged
`<system>/<mim>[/…]` in any `*.jsonl` under `runs/external/<system>/`. Scoring costs about 2 judge calls per OMIM
paragraph of the entry (4–7 paragraphs per entry). By default it also computes the missing whole-draft scores of
the comparison strategies (direct, agent, kg, cohort from run `omim100`) on the same entries — about 1 call per
paragraph per strategy, once (`--no-baselines` to skip; `score baselines --entries … --strategies direct` to do it
separately). Run omim100 is never modified; those scores go to `runs/external/_baselines/`.

`summarize` covers every system folder under `runs/external/` (except `echo` and `_*`): completion, means of
(a)–(c) for the system and the four comparison strategies on the entries the system completed, paired
differences from direct reading (bootstrap interval, better/worse/tied, sign test), uncited share, audit, usage,
and the table of changed settings. Run `score` again after re-running a system so usage is current.

## Worked example

`sys_echo.py` is a complete (trivial) integration: export, adapter, one request per entry, citation mapping,
`save_output`. Proven on 621313 and 615582:

```
PYTHONPATH=src python -m aiomim.external.sys_echo 621313 615582
PYTHONPATH=src python -m aiomim.external.score score --system echo --entries 621313 615582 --no-baselines
PYTHONPATH=src python -m aiomim.external.score baselines --entries 621313 615582 --strategies direct
PYTHONPATH=src python -m aiomim.external.score summarize --systems echo --out runs/external/echo/summary
```

`check_clients.py` checks the adapter with the real `openai` and `litellm` clients (run it from a venv that has
them; it makes about 8 model calls the first time, none after).
