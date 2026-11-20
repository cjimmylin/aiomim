"""Runs INSIDE GraphRAG's own virtual environment (`.venvs/graphrag/bin/python`), never in the project's.

It only calls the released package's own code paths and writes JSON for the driver
(`sys_graphrag.py`, project environment) to read; it imports nothing from `aiomim`.

    python graphrag_runner.py query  <project_root> <local|global> <questions.json> <answers.json>
    python graphrag_runner.py export <project_root> <tables.json>

`query` runs each question exactly as `graphrag query --method <m> --query <q> --root <root>` does with
the command line's defaults (community level 2, response type "Multiple Paragraphs", no dynamic community
selection, no streaming): it calls the same CLI functions (`graphrag.cli.query.run_local_search` /
`run_global_search`), which load `settings.yaml`, read the index and call the public query API, and
return the response together with the context tables the answer's data references point into.
Answers are written after every question, and a question already answered is not asked again, so a
stopped run resumes.

`export` reads the index tables (parquet) and writes the columns the driver needs to map data
references back to documents (the project environment has no parquet reader).
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# The command line's defaults for `graphrag query` (graphrag/cli/main.py, `_query_cli`).
CLI_DEFAULTS = {"community_level": 2, "response_type": "Multiple Paragraphs", "streaming": False,
                "dynamic_community_selection": False}


def _jsonable(value: Any) -> Any:
    import numpy as np
    import pandas as pd

    if isinstance(value, pd.DataFrame):
        return [{str(k): _jsonable(v) for k, v in row.items()} for row in value.to_dict(orient="records")]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and value != value:  # NaN
            return None
        return value
    return str(value)


def query(root: Path, method: str, questions_path: Path, out_path: Path) -> int:
    from graphrag.cli.query import run_global_search, run_local_search

    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    done: dict[str, Any] = {}
    if out_path.exists():
        done = {a["key"]: a for a in json.loads(out_path.read_text(encoding="utf-8")) if a.get("error") is None}
    answers = []
    failed = 0
    for q in questions:
        if q["key"] in done:
            answers.append(done[q["key"]])
            continue
        started = time.time()
        rec: dict[str, Any] = {"key": q["key"], "section": q["section"], "question": q["question"],
                               "method": method, "cli_defaults": CLI_DEFAULTS}
        try:
            if method == "local":
                response, context = run_local_search(
                    data_dir=None, root_dir=root, community_level=CLI_DEFAULTS["community_level"],
                    response_type=CLI_DEFAULTS["response_type"], streaming=CLI_DEFAULTS["streaming"],
                    query=q["question"], verbose=False)
            elif method == "global":
                response, context = run_global_search(
                    data_dir=None, root_dir=root, community_level=CLI_DEFAULTS["community_level"],
                    dynamic_community_selection=CLI_DEFAULTS["dynamic_community_selection"],
                    response_type=CLI_DEFAULTS["response_type"], streaming=CLI_DEFAULTS["streaming"],
                    query=q["question"], verbose=False)
            else:
                raise ValueError(f"unknown method {method!r}")
            rec.update(response=response if isinstance(response, str) else json.dumps(_jsonable(response)),
                       context=_jsonable(context), error=None)
        except Exception as exc:  # noqa: BLE001 - recorded; the driver decides what a failure means
            failed += 1
            rec.update(response=None, context=None, error=f"{type(exc).__name__}: {exc}",
                       traceback=traceback.format_exc()[-4000:])
        rec["seconds"] = round(time.time() - started, 1)
        answers.append(rec)
        out_path.write_text(json.dumps(answers, ensure_ascii=False, indent=1), encoding="utf-8")
    out_path.write_text(json.dumps(answers, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if failed else 0


TABLES = {
    "documents": ["id", "human_readable_id", "title"],
    "text_units": ["id", "human_readable_id", "document_id", "n_tokens"],
    "entities": ["id", "human_readable_id", "title", "type", "text_unit_ids", "frequency", "degree"],
    "relationships": ["id", "human_readable_id", "source", "target", "text_unit_ids", "weight"],
    "communities": ["id", "human_readable_id", "community", "level", "parent", "entity_ids", "relationship_ids",
                    "text_unit_ids", "size"],
    "community_reports": ["id", "human_readable_id", "community", "level", "title", "rank"],
}


def export(root: Path, out_path: Path) -> int:
    import pandas as pd

    out_dir = root / "output"
    tables: dict[str, Any] = {}
    for name, cols in TABLES.items():
        path = out_dir / f"{name}.parquet"
        if not path.exists():
            tables[name] = None
            continue
        df = pd.read_parquet(path)
        tables[name] = _jsonable(df[[c for c in cols if c in df.columns]])
        tables[f"{name}__columns"] = list(df.columns)
    stats = out_dir / "stats.json"
    tables["stats"] = json.loads(stats.read_text(encoding="utf-8")) if stats.exists() else None
    out_path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 5 and argv[0] == "query":
        return query(Path(argv[1]).resolve(), argv[2], Path(argv[3]), Path(argv[4]))
    if len(argv) >= 3 and argv[0] == "export":
        return export(Path(argv[1]).resolve(), Path(argv[2]))
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
