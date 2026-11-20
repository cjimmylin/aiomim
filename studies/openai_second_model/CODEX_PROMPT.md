# Prompt for Codex

How to use: check out the branch named in step 0 below, place the private bundle as described in `README.md`, set
`OPENAI_API_KEY` in the shell that runs Codex, choose the model in `study.json` (`gpt-6.2-astra` or `gpt-6.2-sol`),
then start Codex at the repository root and paste everything between the two lines below. If Codex stops while
batches are still running, paste the same prompt again later: every step is resumable.

---

You are running a pre-registered study in this repository. Its directory is `studies/openai_second_model/`. Read
`studies/openai_second_model/README.md`, `PROTOCOL.md` and `OUTPUT_SPEC.md` before doing anything else. The study
sends requests to the OpenAI Batch API with the model named in `studies/openai_second_model/study.json`, using
exactly the prompts and schemas this repository already uses. The model is the only thing being changed; your job is
to run the study to completion, not to improve it.

Rules (they override anything else):
1. Do not change any prompt, system prompt, JSON schema, entry list, effort setting, scoring rule or analysis. Do not
   edit any file outside `studies/openai_second_model/` except to fix a transport problem in
   `src/aiomim/openai_study/` (how requests are written, submitted, polled or parsed). Record every such fix, with the
   reason and the evidence, in `studies/openai_second_model/outputs/run_log.md`.
2. Never retry a request the model refused or that ended with a content filter, and never reword one. They are
   results. The tool records them; leave them.
3. Never exceed the cost cap in `study.json`. The tool refuses to submit over the cap; do not raise the cap.
4. Never print, log or commit `OPENAI_API_KEY` or any other secret.
5. Nothing under `studies/openai_second_model/private/` may be committed, printed in full, or sent anywhere except in
   requests to the OpenAI API made by the tool. Do not send repository content to any other service.
6. Use only the commands below to run the study. Do not write your own scripts that call the OpenAI API.

Steps:
0. Make sure the branch `openai-second-model` exists (create it from `claude/omim-pipeline-poc` if it does not) and is
   checked out. Install the project and the OpenAI SDK into a virtual environment with Python 3.12 or newer:
   `pip install -e .` and `pip install openai`.
1. Run `python -m aiomim.openai_study check --study studies/openai_second_model`. If it reports a problem, fix it only
   if it is about the local environment (a missing package, the bundle not unpacked where the README says); otherwise
   stop and report the problem.
2. If `studies/openai_second_model/state/tasks.json` does not exist, run `plan`.
3. If the smoke test has not passed yet (see `state/status.json`), run `smoke`, then `step` repeatedly until the smoke
   batch is ingested. Read `outputs/run_log.md` and the smoke results: every request must have parsed, or have been
   recorded as a refusal. If requests failed to parse because of the request or response format, fix the transport
   code as rule 1 allows, add a unit test for the fix, run `python -m pytest -q -m "not network and not llm"`, and run
   the smoke test again. Do not continue to the main waves until the smoke test passes.
4. Run `step`. Read the status line and `state/status.json`:
   - `ready`: run `step` again.
   - `waiting_for_batch`: wait, then run `step` again; check about every 10 minutes for up to 2 hours in this session.
     If batches are still running after that, go to step 6 and say in your final message that the study is waiting
     and that the same prompt should be run again later.
   - `blocked`: stop and report the reason in your final message (for example the cost cap, repeated failures, or an
     API error you cannot resolve within rule 1).
   - `done`: go to step 5.
5. Run `report`, then `validate`. If `validate` fails, fix only what it reports in the outputs' generation (not the
   data) within rule 1, and run both again. Do not edit output files by hand.
6. Commit and push to `openai-second-model`: only `studies/openai_second_model/state/`,
   `studies/openai_second_model/outputs/` and any transport fix with its test. Before committing, run
   `git status` and confirm nothing under `private/` is staged. Commit message: `OpenAI second-model study: <phase>,
   <requests done>/<requests planned>, $<cost so far>`.

Final message: the phase; requests submitted, completed, refused and failed; cost so far against the cap; what was
committed; any transport fix you made; and what to do next (wait and rerun, or the study is done).

---
