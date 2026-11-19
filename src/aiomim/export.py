"""Write a shareable copy of a run: everything the pipeline produced, without gold text."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

# Per-entry files copied as they are. gold.json is deliberately absent.
COPY = ("seed.json", "retrieval.json", "papers.json", "extractions.json", "kg.json", "kg_triples.tsv",
        "cohort.json", "recall.memory_audit.json", "usage.json", "updates.json", "updates.md")
ENTRY_GLOBS = ("entry.*.json", "entry.*.md")
RUN_FILES = ("summary.json", "strategies.json", "strategies.md", "comparison.json", "comparison.md",
             "backtest.json", "audit_check.json", "adjudication.json", "candidate_corrections.md")
RUN_GLOBS = ("knowledge_graph.*.tsv",)


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
    for pattern in RUN_GLOBS:
        for path in run_dir.glob(pattern):
            shutil.copyfile(path, out / path.name)

    rows = []
    for entry_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        if not list(entry_dir.glob("entry.*.json")) and not (entry_dir / "updates.json").exists():
            continue
        target = out / entry_dir.name
        target.mkdir(exist_ok=True)
        files = [entry_dir / name for name in COPY] + [f for g in ENTRY_GLOBS for f in sorted(entry_dir.glob(g))]
        for path in files:
            if not path.exists():
                continue
            if path.suffix == ".json":
                # Compact JSON: these are data files, and a hundred entries add up.
                (target / path.name).write_text(_compact(json.loads(path.read_text())))
            else:
                shutil.copyfile(path, target / path.name)
        for eval_path in entry_dir.glob("eval.*.json"):
            (target / eval_path.name).write_text(_compact(_redact(json.loads(eval_path.read_text()))))
        seed = json.loads((entry_dir / "seed.json").read_text()) if (entry_dir / "seed.json").exists() else {}
        rows.append((entry_dir.name, seed.get("title", "")))

    from .strategies import STRATEGIES

    present = [s for s in STRATEGIES if any((out / name / f"entry.{s}.md").exists() for name, _ in rows)]
    lines = ["# Generated entries", "",
             "Machine-drafted and unreviewed. Each folder holds one draft per generation strategy (`entry.<strategy>.md` "
             "and `.json`, the latter with the audit's verdict on every claim), the evidence behind them "
             "(`extractions.json`, `kg.json`, `cohort.json` where the strategy produces them) and the scores against "
             "OMIM (`eval.<strategy>.json`).", "",
             "Strategies: " + "; ".join(f"`{s}` = {STRATEGIES[s].label}" for s in present) + ".", "",
             "| Entry | Title | Drafts |", "|---|---|---|"]
    for name, title in rows:
        links = " · ".join(f"[{s}]({name}/entry.{s}.md)" for s in present if (out / name / f"entry.{s}.md").exists())
        lines.append(f"| {name} | {title.title()} | {links} |")
    (out / "README.md").write_text("\n".join(lines) + "\n")
    return len(rows)
