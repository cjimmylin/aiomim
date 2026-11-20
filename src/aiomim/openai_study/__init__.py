"""A second model family for the study: OpenAI models through the OpenAI Batch API.

The project's own code paths (fixed-fact scoring, the availability judgements, the
writers) run unchanged. Only the model backend differs: instead of calling a model,
it records each request that misses the cache and stops the task (`Pending`). The
requests of all tasks go to OpenAI as one batch (a *wave*); the replies are written
into the study's cache under the same keys, and the next wave's run reads them and
proceeds to the next stage. See `studies/openai_second_model/README.md`.

Modules:

    errors          Pending, ForbiddenCall, NetworkBlocked
    config          study.json, paths, prices, effort mapping
    openai_format   request lines for POST /v1/responses; parsing of batch output lines
    backend         the recording backend and the request recorder
    offline         offline environment: settings, HTTP (HGNC) from the bundle, HPO, network guard
    bundle          the private input bundle: build (here), unpack and read (owner's machine)
    tasks           the study's tasks and how each runs the project's code
    waves           collect, submit, poll, ingest, step, smoke
    providers       the OpenAI SDK provider and a fake provider for dry runs
    stats / report  the outputs Claude Code parses
    validate        JSON Schema and OMIM-wording checks of the outputs
"""

STUDY_DIR_DEFAULT = "studies/openai_second_model"
