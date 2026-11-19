"""Write a shareable copy of a run: everything the pipeline produced, without gold text."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

# Per-entry files copied as they are. gold.json is deliberately absent.
COPY = ("seed.json", "retrieval.json", "papers.json", "extractions.json", "kg.json", "kg_triples.tsv",
        "entry.kg.json", "entry.kg.md", "entry.direct.json", "entry.direct.md", "usage.json",
        "updates.json", "updates.md")
RUN_FILES = ("summary.json", "comparison.json", "comparison.md", "knowledge_graph.kg.tsv", "knowledge_graph.direct.tsv",
             "backtest.json", "audit_check.json", "adjudication.json", "candidate_corrections.md")


def _redact(evaluation: dict) -> dict:
    """Drop OMIM-authored wording from an evaluation; keep every score and fact verdict count."""
    for para in (evaluation.get("gold_text") or {}).get("paragraphs", []):
        para.pop("reference", None)
        para.pop("draft", None)  # the draft's own text is in entry.<strategy>.json
        # The judged facts restate the reference sentence by sentence; keep only their verdicts.
        para["facts"] = [{"status": f.get("status")} for f in para.get("facts", [])]
    return evaluation


def _compact(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def export_run(run_dir: Path, out: str | Path) -> int:
    run_dir, out = Path(run_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name in RUN_FILES:
        if (run_dir / name).exists():
            shutil.copyfile(run_dir / name, out / name)

    rows = []
    for entry_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        if not any((entry_dir / f"entry.{s}.json").exists() for s in ("kg", "direct")) \
                and not (entry_dir / "updates.json").exists():
            continue
        target = out / entry_dir.name
        target.mkdir(exist_ok=True)
        for name in COPY:
            if not (entry_dir / name).exists():
                continue
            if name.endswith(".json"):
                # Compact JSON: these are data files, and a hundred entries add up.
                (target / name).write_text(_compact(json.loads((entry_dir / name).read_text())))
            else:
                shutil.copyfile(entry_dir / name, target / name)
        for eval_path in entry_dir.glob("eval.*.json"):
            (target / eval_path.name).write_text(_compact(_redact(json.loads(eval_path.read_text()))))
        seed = json.loads((entry_dir / "seed.json").read_text()) if (entry_dir / "seed.json").exists() else {}
        rows.append((entry_dir.name, seed.get("title", "")))

    lines = ["# Generated entries", "",
             "Machine-drafted and unreviewed. Each folder holds the draft from the evidence graph (`entry.kg.md`), "
             "the direct baseline (`entry.direct.md`), the evidence behind them (`extractions.json`, `kg.json`) and "
             "the scores (`eval.*.json`).", "",
             "| Entry | Title | Evidence-graph draft | Direct draft |", "|---|---|---|---|"]
    for name, title in rows:
        kg = f"[entry.kg.md]({name}/entry.kg.md)" if (out / name / "entry.kg.md").exists() else ""
        direct = f"[entry.direct.md]({name}/entry.direct.md)" if (out / name / "entry.direct.md").exists() else ""
        lines.append(f"| {name} | {title.title()} | {kg} | {direct} |")
    (out / "README.md").write_text("\n".join(lines) + "\n")
    return len(rows)
