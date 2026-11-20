# Prompt for Codex

How to use:

1. Check out the branch `claude/omim-pipeline-poc` (it contains this kit) and create `openai-second-model` from it,
   or let Codex do that in step 0.
2. Put the private bundle and its checksum file in `studies/openai_second_model/private/` (see `README.md`). The
   bundle is delivered separately and is never committed.
3. Choose the model in `studies/openai_second_model/study.json` (`"model": "gpt-6.2-astra"` or `"gpt-6.2-sol"`) and
   do not change it once the study has started.
4. Export `OPENAI_API_KEY` in the shell that runs Codex. The Batch API needs an API key with billing; a ChatGPT
   sign-in is not enough.
5. Start Codex (CLI or IDE extension, on your own machine, not a cloud task) at the repository root and paste
   everything between the two lines below. Batches can take up to 24 hours. If Codex stops while they run, paste the
   same prompt again later: every step resumes where it stopped.

---

You are running a pre-registered study in this repository. Its directory is `studies/openai_second_model/`. Before
doing anything else, read `studies/openai_second_model/README.md`, `PROTOCOL.md` and `OUTPUT_SPEC.md`. The study
sends requests to the OpenAI Batch API with the model named in `studies/openai_second_model/study.json`, using
exactly the prompts, schemas and code this repository already uses. The model is the only thing being changed. Your
job is to run the study to completion with the kit's commands, not to improve or extend it.

Rules (they override anything else):
1. Do not change any prompt, system prompt, JSON schema, entry list, effort setting, scoring rule or analysis, and do
   not change `model` in `study.json`. The only edits allowed are: (a) a fix to a transport problem in
   `src/aiomim/openai_study/` (how requests are written, submitted, polled, downloaded or parsed), with a unit test;
   (b) in `study.json`, `batch.max_requests_per_file` or `batch.max_enqueued_est_tokens` if OpenAI rejects a batch
   for its size or token limit, and raising (never lowering) values under `estimation.expected_output_tokens`.
   Record every such edit, with the reason and the evidence, in `studies/openai_second_model/outputs/run_log.md`.
2. Never retry a request the model refused or that ended with a content filter, and never reword one. They are
   results; the kit records them.
3. Never exceed or raise the cost cap in `study.json`. The kit refuses to submit over the cap.
4. Never print, log or commit `OPENAI_API_KEY` or any other secret.
5. Nothing under `studies/openai_second_model/private/` may be committed, printed in full, moved or deleted, and its
   contents may go nowhere except in the requests the kit sends to the OpenAI API. Do not run `git clean -x` or
   anything else that could remove it: it holds replies already paid for. Do not send repository content to any other
   service.
6. Run the study only with the kit's commands (`python -m aiomim.openai_study <command> --study
   studies/openai_second_model`). Do not write your own code that calls the OpenAI API.

Steps (`S=studies/openai_second_model`; run every command from the repository root):
0. Make sure the branch `openai-second-model` is checked out (create it from `claude/omim-pipeline-poc` if it does not
   exist). Use a virtual environment with Python 3.10 or newer, then `pip install -e .` and
   `pip install -r $S/requirements.txt`, and `export PYTHONPATH=src`.
1. Run `check`. It unpacks the bundle and verifies it, the code and the settings, and must report `"ok": true`. If it
   reports a problem with the local environment (a missing package, the bundle not where the README says, a wrong
   checkout), fix that and run it again. If it reports anything else, stop and report it.
2. If `$S/state/tasks.json` does not exist, run `plan`.
3. If `$S/state/smoke.json` does not exist, run `smoke` once (it submits at most 8 requests). Then run `step`, waiting
   between runs as in step 4, until `$S/state/smoke.json` shows `"passed": true` (a refusal in the smoke batch still
   counts as passed). If the smoke batch failed because of the request or response format, fix the transport code as
   rule 1(a) allows, run `python -m pytest -q -m "not network and not llm"`, and run `smoke` again. After the smoke
   batch, compare each request's output tokens in `state/smoke.json` with `estimation.expected_output_tokens` in
   `study.json` and raise any default the real figure exceeds (rule 1(b)). Do not continue until the smoke test has
   passed.
4. Run `step` and read its status line and `$S/state/status.json`. `step` exits with code 2 when the phase is
   `blocked`; that is a status, not a crash.
   - `ready`: run `step` again at once.
   - `waiting_for_batch`: wait about 15 minutes, then run `step` again, for up to 2 hours in this session. If batches
     are still running after that, go to step 6 and say in your final message that the study is waiting and that this
     prompt should be pasted again later.
   - `blocked`: read `reason` in `status.json`. If it is a batch size or token limit, apply rule 1(b) and continue. If
     it is a transport error, apply rule 1(a) and continue. Otherwise (the cost cap, a changed prompt or model,
     repeated failures, anything else), go to step 6 and report the reason.
   - `done`: go to step 5.
5. Run `report`, then `validate`. If `validate` fails, fix only the code that generates the outputs, within rule 1(a),
   and run both again. Never edit an output file by hand.
6. Commit and push to `openai-second-model`: only `$S/state/`, `$S/outputs/`, and any transport fix with its test.
   Run `git status` first and make sure nothing under `$S/private/` is staged. Commit message:
   `OpenAI second-model study: <phase>, tasks <tasks_finished>/<tasks_planned>, requests <completed> completed,
   <refused> refused, <failed> failed, $<cost so far>` (figures from `status.json`).

Final message: the phase; tasks finished and planned; requests submitted, completed, refused and failed; cost so
far against the cap; what was committed; every edit made under rule 1; and what happens next (paste the prompt again
later, or the study is done).

---
