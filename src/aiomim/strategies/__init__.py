"""The ways an entry can be generated.

Every strategy takes the same input (the entry header and the papers) and returns
the same `GeneratedEntry`, so all of them go through the same audit and the same
scoring and can be compared entry by entry.

    direct      the papers go into one prompt; the model writes the entry.
    kg          quote-backed findings are extracted per paper, joined into an
                evidence knowledge graph, and the entry is written from the graph.
    agent       an autonomous curator works in a folder holding the papers, with
                tools to read and search them, and decides for itself what to read
                and re-check before writing.
    closedbook  the model writes the entry from memory alone. A control: it shows
                what the model already knows, and nothing in it is grounded.
    recall      the memory draft is taken claim by claim to the papers; what the
                papers support is kept and corrected, the rest is deleted.
    cohort      one structured record is extracted per reported patient or family,
                the records are pooled into a case table with frequencies, and the
                entry is rendered from the table.

A strategy module exposes `run(seed, papers, llm, out_dir) -> GeneratedEntry`. It
may write its own working files into `out_dir`.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from ..models import GeneratedEntry, Paper, Seed


@dataclass(frozen=True)
class StrategySpec:
    name: str
    label: str
    summary: str
    audit: bool = True    # run the claim-level audit on its entries
    repair: bool = True   # let the audit's findings be repaired


STRATEGIES: dict[str, StrategySpec] = {s.name: s for s in (
    StrategySpec("kg", "Evidence graph",
                 "Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph."),
    StrategySpec("direct", "Direct reading",
                 "All papers in one prompt; the model writes the entry straight from the text."),
    StrategySpec("agent", "Agentic curator",
                 "An autonomous agent reads and searches the papers with tools, then writes the entry."),
    StrategySpec("closedbook", "Memory only (control)",
                 "Written from the model's memory with no papers; nothing is grounded. A control, not a method.",
                 repair=False),
    StrategySpec("recall", "Recall, then verify",
                 "A draft from memory is checked claim by claim against the papers; unsupported claims are deleted."),
    StrategySpec("cohort", "Case table first",
                 "One structured record per reported patient or family, pooled into a case table; the entry is rendered from it."),
)}


def parse_strategies(value: str) -> tuple[str, ...]:
    """'kg', 'both', 'all' or a comma-separated list -> strategy names in registry order."""
    if value == "both":
        wanted = {"kg", "direct"}
    elif value == "all":
        wanted = set(STRATEGIES)
    else:
        wanted = {v.strip() for v in value.split(",") if v.strip()}
    unknown = wanted - set(STRATEGIES)
    if unknown:
        raise ValueError(f"unknown strategy: {', '.join(sorted(unknown))} (known: {', '.join(STRATEGIES)})")
    return tuple(name for name in STRATEGIES if name in wanted)


def run_strategy(name: str, seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    entry = import_module(f"{__name__}.{name}").run(seed, papers, llm, out_dir)
    entry.meta["strategy"] = name
    return entry
