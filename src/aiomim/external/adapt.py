"""The intermediate format every integration writes, and its conversion into the project's entry format.

One file per system and entry, `runs/external/<system>/<mim>/output.json`:

    {
      "format": "aiomim-external/1",
      "system": "paperqa2",                 # lower-case [a-z0-9_]+
      "mim": "621313",
      "stopped": null,                      # or a reason when the system produced no answer
                                            # (e.g. "safety stop on every question")
      "blocks": [                           # in output order, text exactly as the system wrote it
        {"section": "Clinical features",    # the section or question it came from
         "text": "Patients present with ...",
         "pmids": ["31705625"],             # supplied papers its citations map to (may be [])
         "citations": ["(Rendu2019 pages 2-3)"]}   # optional: the raw citation markers, for the record
      ],
      "meta": {
        "package": "paper-qa", "version": "5.0.0",
        "settings_changed": [               # every setting changed from the package's defaults
          {"setting": "llm", "default": "gpt-4o-2024-11-20", "value": "openai/claude-opus-5-5",
           "reason": "the local adapter in front of the project's model"}],
        "calls": 31, "stops": 0, "seconds": 412.5,     # as the integration counted them
        "tag": "paperqa2/621313",           # the ledger tag its requests carried
        "ledgers": ["runs/external/paperqa2/621313/ledger.jsonl"]
      }
    }

The integration does the system-specific citation mapping (its own citation keys to
PubMed ids); `save_output` validates that every mapped id is one of the entry's supplied
papers. `to_entry` makes a `GeneratedEntry` with the text unedited: consecutive blocks of
the same section form one section; a block with mapped citations becomes a paragraph
citing those papers; a block without becomes an uncited paragraph (kept for whole-draft
scoring and counted).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models import EntryParagraph, EntrySection, GeneratedEntry, Reference
from . import runs_root

FORMAT = "aiomim-external/1"
_SYSTEM = re.compile(r"^[a-z0-9_]+$")


class FormatError(ValueError):
    pass


def entry_dir(system: str, mim: str) -> Path:
    return runs_root() / system / mim


def supplied_papers(mim: str) -> list[dict[str, Any]]:
    """The entry's supplied papers as the run recorded them (pmid, label, reference, content_level, ...)."""
    from .corpus import source_dir

    return json.loads((source_dir(mim) / "papers.json").read_text(encoding="utf-8"))


def validate(output: dict[str, Any], supplied: set[str] | None = None) -> dict[str, Any]:
    """Check an output against the format; returns it normalised (pmids de-duplicated, order kept)."""
    if not isinstance(output, dict):
        raise FormatError("output must be an object")
    if output.get("format", FORMAT) != FORMAT:
        raise FormatError(f"format must be {FORMAT!r}")
    system, mim = output.get("system"), str(output.get("mim", ""))
    if not isinstance(system, str) or not _SYSTEM.match(system):
        raise FormatError("system must match [a-z0-9_]+")
    if not mim.isdigit():
        raise FormatError("mim must be the entry number")
    supplied = supplied if supplied is not None else {p["pmid"] for p in supplied_papers(mim)}
    blocks = output.get("blocks")
    if not isinstance(blocks, list):
        raise FormatError("blocks must be a list")
    stopped = output.get("stopped")
    if stopped is not None and not isinstance(stopped, str):
        raise FormatError("stopped must be null or a reason")
    if not blocks and not stopped:
        raise FormatError("no blocks: give `stopped` with the reason when the system produced nothing")
    norm = []
    for i, b in enumerate(blocks):
        if not isinstance(b, dict):
            raise FormatError(f"block {i} must be an object")
        text, section = b.get("text"), b.get("section")
        if not isinstance(text, str) or not text.strip():
            raise FormatError(f"block {i}: text must be a non-empty string")
        if not isinstance(section, str) or not section.strip():
            raise FormatError(f"block {i}: section must be a non-empty string")
        pmids = b.get("pmids", [])
        if not isinstance(pmids, list) or not all(isinstance(p, str) for p in pmids):
            raise FormatError(f"block {i}: pmids must be a list of strings")
        foreign = [p for p in pmids if p not in supplied]
        if foreign:
            raise FormatError(f"block {i}: pmids not among the entry's supplied papers: {foreign}")
        cites = b.get("citations", [])
        if not isinstance(cites, list):
            raise FormatError(f"block {i}: citations must be a list")
        norm.append({"section": section, "text": text, "pmids": list(dict.fromkeys(pmids)),
                     "citations": [str(c) for c in cites]})
    meta = output.get("meta") or {}
    if not isinstance(meta, dict):
        raise FormatError("meta must be an object")
    changed = meta.get("settings_changed", [])
    if not isinstance(changed, list) or not all(isinstance(c, dict) and "setting" in c for c in changed):
        raise FormatError("meta.settings_changed must be a list of {setting, default, value, reason}")
    return {"format": FORMAT, "system": system, "mim": mim, "stopped": stopped, "blocks": norm, "meta": meta}


def save_output(output: dict[str, Any]) -> Path:
    """Validate and write `runs/external/<system>/<mim>/output.json`, plus the converted entry
    (`entry.<system>.json` and `.md`). Returns the folder."""
    from ..pipeline import _write
    from ..render import entry_markdown

    out = validate(output)
    folder = entry_dir(out["system"], out["mim"])
    _write(folder / "output.json", out)
    if out["blocks"]:
        entry = to_entry(out)
        _write(folder / f"entry.{out['system']}.json", entry.model_dump(mode="json"))
        _write(folder / f"entry.{out['system']}.md", entry_markdown(entry, show_flags=False))
    return folder


def load_output(system: str, mim: str) -> dict[str, Any] | None:
    path = entry_dir(system, mim) / "output.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "section"


def uncited_share(output: dict[str, Any]) -> dict[str, Any]:
    blocks = output.get("blocks") or []
    total = sum(len(b["text"]) for b in blocks)
    uncited = sum(len(b["text"]) for b in blocks if not b["pmids"])
    return {"blocks": len(blocks), "uncited_blocks": sum(1 for b in blocks if not b["pmids"]),
            "chars": total, "uncited_chars": uncited, "uncited_share": round(uncited / total, 4) if total else None}


def to_entry(output: dict[str, Any]) -> GeneratedEntry:
    """The project's entry format, text unedited. Paragraph ids are b1, b2, ... in block order."""
    from .corpus import source_dir

    seed = json.loads((source_dir(output["mim"]) / "seed.json").read_text(encoding="utf-8"))
    papers = {p["pmid"]: p for p in supplied_papers(output["mim"])}
    sections: list[EntrySection] = []
    for n, b in enumerate(output["blocks"], 1):
        if not sections or sections[-1].heading != b["section"]:
            sections.append(EntrySection(name=_slug(b["section"]), heading=b["section"]))
        sections[-1].paragraphs.append(EntryParagraph(id=f"b{n}", text=b["text"], pmids=list(b["pmids"])))
    cited = list(dict.fromkeys(p for b in output["blocks"] for p in b["pmids"]))
    refs = [Reference(pmid=p, label=papers[p].get("label", ""), citation=papers[p].get("reference", ""),
                      content_level=papers[p].get("content_level", "abstract")) for p in cited if p in papers]
    return GeneratedEntry(
        mim=output["mim"], prefix=seed.get("prefix", ""), title=seed.get("title", ""),
        alt_titles=list(seed.get("alt_titles") or []), sections=sections, references=refs,
        meta={"strategy": output["system"], "external": output.get("meta") or {}, "uncited": uncited_share(output)},
    )
