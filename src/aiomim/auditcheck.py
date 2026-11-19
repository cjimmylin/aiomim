"""How much can the audit be trusted? Plant errors and see whether it catches them.

The headline faithfulness score is produced by a model (the auditor) reading the
cited paper. This module measures that auditor directly. It takes paragraphs the
audit passed as fully supported, changes exactly one fact in each by rule (a
count, an age, a zygosity, a residue, a mode of inheritance), and audits the
altered paragraph again against the same paper. An altered paragraph that is
still passed as fully supported is a miss.

The alterations are made by regular expressions, not by a model, so what was
changed is known exactly and nothing else in the paragraph moves.
"""

from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import Any, Callable

from .llm import LLM
from .models import EntryParagraph, GeneratedEntry
from .verify import verify_entry

log = logging.getLogger(__name__)

_AA = ["ala", "arg", "asn", "asp", "cys", "gln", "glu", "gly", "his", "ile", "leu", "lys", "met", "phe", "pro",
       "ser", "thr", "trp", "tyr", "val"]
_AA1 = "ARNDCQEGHILKMFPSTWYV"


def _swap_count(text: str) -> tuple[str, str, str] | None:
    """Change a small count or age: '3 sibs' -> '6 sibs', '14-year-old' -> '21-year-old'."""
    pattern = re.compile(
        r"(?<![\w.>\-+/])(\d{1,2})(?=(?:-year-old| (?:of \d+ )?(?:unrelated |affected |additional )?"
        r"(?:patients|families|sibs|individuals|members|brothers|sisters|children|boys|girls|men|women|probands|"
        r"years|months|weeks|kindreds|pedigrees|cases|relatives|controls)\b))")
    match = pattern.search(text)
    if not match:
        return None
    old = int(match.group(1))
    new = str(old + 3 if old < 10 else old + 7)
    return text[:match.start(1)] + new + text[match.end(1):], match.group(0), new


def _swap_zygosity(text: str) -> tuple[str, str, str] | None:
    for old, new in (("compound heterozygous", "homozygous"), ("homozygous", "heterozygous"),
                     ("heterozygous", "homozygous"), ("hemizygous", "heterozygous"),
                     ("homoplasmic", "heteroplasmic"), ("heteroplasmic", "homoplasmic")):
        match = re.search(rf"\b{old}\b", text)
        if match:
            return text[:match.start()] + new + text[match.end():], old, new
    return None


def _swap_residue(text: str) -> tuple[str, str, str] | None:
    """Change the substituted amino acid: 'arg123-to-trp (R123W)' -> 'arg123-to-ser (R123S)'."""
    match = re.search(r"\b([a-z]{3})(\d+)-to-([a-z]{3})\b", text)
    if match and match.group(3) in _AA:
        new3 = next(a for a in ("ser", "leu", "gly") if a not in (match.group(1), match.group(3)))
        out = text[:match.start(3)] + new3 + text[match.end(3):]
        # Keep the one-letter form consistent, so the paragraph does not contradict itself.
        old1, new1 = _AA1[_AA.index(match.group(3))], _AA1[_AA.index(new3)]
        out = re.sub(rf"\b([A-Z]){match.group(2)}{old1}\b", rf"\g<1>{match.group(2)}{new1}", out)
        return out, match.group(0), f"{match.group(1)}{match.group(2)}-to-{new3}"
    return None


def _swap_inheritance(text: str) -> tuple[str, str, str] | None:
    for old, new in (("autosomal recessive", "autosomal dominant"), ("autosomal dominant", "autosomal recessive"),
                     ("X-linked recessive", "autosomal recessive"), ("de novo", "inherited"),
                     ("maternally", "paternally")):
        match = re.search(rf"\b{old}\b", text)
        if match:
            return text[:match.start()] + new + text[match.end():], old, new
    return None


ALTERATIONS: list[tuple[str, Callable[[str], tuple[str, str, str] | None]]] = [
    ("count or age", _swap_count), ("zygosity", _swap_zygosity),
    ("amino acid change", _swap_residue), ("inheritance or origin", _swap_inheritance),
]


def plant_errors(run_dir: Path, n: int = 60, seed: int = 11, strategy: str = "kg") -> list[dict[str, Any]]:
    """Pick fully supported single-paper paragraphs and alter one fact in each."""
    rng = random.Random(seed)
    pool: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob(f"*/entry.{strategy}.json")):
        entry = GeneratedEntry.model_validate_json(path.read_text())
        candidates = [p for p in entry.all_paragraphs()
                      if p.status == "supported" and len(p.pmids) == 1 and len(p.text) > 150]
        rng.shuffle(candidates)
        for para in candidates[:3]:
            pool.append({"mim": path.parent.name, "paragraph_id": para.id, "pmid": para.pmids[0], "text": para.text})
    rng.shuffle(pool)

    probes: list[dict[str, Any]] = []
    per_kind: dict[str, int] = {}
    quota = max(1, n // len(ALTERATIONS))
    # Rotate the starting rule so the four kinds of alteration are evenly represented.
    for i, item in enumerate(pool):
        if len(probes) >= n:
            break
        order = ALTERATIONS[i % len(ALTERATIONS):] + ALTERATIONS[:i % len(ALTERATIONS)]
        for kind, alter in order:
            if per_kind.get(kind, 0) >= quota + 2:
                continue
            changed = alter(item["text"])
            if changed and changed[0] != item["text"]:
                per_kind[kind] = per_kind.get(kind, 0) + 1
                probes.append({**item, "kind": kind, "altered_text": changed[0],
                               "was": changed[1], "now": changed[2]})
                break
    return probes


def run_audit_check(run_dir: Path, n: int = 60, seed: int = 11) -> dict[str, Any]:
    from .sources.fulltext import load_papers

    probes = plant_errors(run_dir, n=n, seed=seed)
    papers = {p.pmid: p for p in load_papers(sorted({probe["pmid"] for probe in probes}), with_fulltext=True)}
    probes = [p for p in probes if p["pmid"] in papers]

    # One synthetic "entry" holding only the altered paragraphs, so the normal audit runs on them unchanged.
    holder = GeneratedEntry(title="audit check")
    holder.sections = []
    paragraphs = []
    for i, probe in enumerate(probes):
        para = EntryParagraph(id=f"probe.{i}", text=probe["altered_text"], pmids=[probe["pmid"]])
        paragraphs.append(para)
    from .models import EntrySection

    holder.sections.append(EntrySection(name="clinical_features", paragraphs=paragraphs))
    for i, para in enumerate(paragraphs):
        para.id = f"probe.{i}"  # keep our ids; do not renumber
    verify_entry(holder, papers, LLM())

    def tally(items: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(items)
        caught = sum(1 for p in items if p["result"] == "flagged")
        doubted = sum(1 for p in items if p["result"] == "partial")
        return {"n": total, "flagged": caught, "downgraded_to_partial": doubted,
                "missed": total - caught - doubted,
                "detection_rate": round((caught + doubted) / total, 3) if total else None,
                "flag_rate": round(caught / total, 3) if total else None}

    for probe, para in zip(probes, paragraphs):
        probe["result"] = para.status if para.status in ("flagged", "partial", "supported") else "unverified"
        probe["content_level"] = papers[probe["pmid"]].content_level
        probe["checks"] = [c.model_dump() for c in para.checks if c.verdict != "supported"]
    judged = [p for p in probes if p["result"] != "unverified"]
    result = {
        "run": run_dir.name, "seed": seed, "overall": tally(judged),
        "by_kind": {kind: tally([p for p in judged if p["kind"] == kind]) for kind, _ in ALTERATIONS},
        "by_content_level": {level: tally([p for p in judged if p["content_level"] == level])
                             for level in sorted({p["content_level"] for p in judged})},
        "probes": probes,
    }
    (run_dir / "audit_check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result
