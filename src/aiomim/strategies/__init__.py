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
    secondhand  direct reading, but a paper that could not be read in full is
                supplemented with what later open-access papers say it reported.
    reconciled  the case table, after a reconciliation step that merges the same
                patient, family or variant reported in several papers and settles
                conflicts; the entry is rendered from the reconciled database.
    guided      direct reading with a curation guide learned from the misses and
                extras of other entries (a training split) appended to the prompt.
    direct_checklist  direct reading with the house style's per-paper guidance made
                into an explicit list of what a curator records about each paper.
    direct_complete   direct reading's draft, a completeness check per paper, then
                one revision adding the omissions the check listed (quotes verified).
    direct_ensemble   direct reading's draft and two fresh samples, merged into one
                draft keeping every distinct statement (citations unioned mechanically).

A strategy module exposes `run(seed, papers, llm, out_dir) -> GeneratedEntry`. It
may write its own working files into `out_dir`. Two optional hooks:

    audit_papers(papers, out_dir) -> list[Paper]
        the papers the audit should read, when the strategy wrote from more text
        than the papers as retrieved (second-hand evidence).
    after_audit(entry, papers, out_dir) -> None
        called once the audit and any repair are done, with the papers the audit
        read; may annotate the entry and its `meta`.
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
    control: bool = False  # a reference point, not a way of writing entries


STRATEGIES: dict[str, StrategySpec] = {s.name: s for s in (
    StrategySpec("kg", "Evidence graph",
                 "Quote-backed findings per paper, joined into a knowledge graph; the entry is written from the graph."),
    StrategySpec("direct", "Direct reading",
                 "All papers in one prompt; the model writes the entry straight from the text."),
    StrategySpec("agent", "Agentic curator",
                 "An autonomous agent reads and searches the papers with tools, then writes the entry."),
    StrategySpec("closedbook", "Memory only (control)",
                 "Written from the model's memory with no papers; nothing is grounded. A control, not a method.",
                 repair=False, control=True),
    StrategySpec("recall", "Recall, then verify",
                 "A draft from memory is checked claim by claim against the papers; unsupported claims are deleted."),
    StrategySpec("cohort", "Case table first",
                 "One structured record per reported patient or family, pooled into a case table; the entry is rendered from it."),
    StrategySpec("secondhand", "Second-hand evidence",
                 "Direct reading; a paper not readable in full is supplemented with what later open-access papers say it reported."),
    StrategySpec("reconciled", "Reconciled case database",
                 "The case table after merging the same patient, family or variant across papers and settling conflicts."),
    StrategySpec("guided", "Learned curation guide",
                 "Direct reading with a guide to what OMIM includes, learned from the misses and extras of other entries."),
    # Ablations of the two extract-then-write strategies (review, issue 2): what they
    # lose to lower extraction effort and fixed rules, and what to never seeing the text.
    StrategySpec("kg_matched", "Evidence graph, matched",
                 "Evidence graph with extraction at the writer's effort and synopsis terms chosen by the writer, not by rule."),
    StrategySpec("kg_hybrid", "Evidence graph plus text",
                 "As the matched evidence graph, and the writer also reads the papers' text."),
    StrategySpec("cohort_matched", "Case table, matched",
                 "Case table with extraction at the writer's effort and synopsis terms and inheritance chosen by the writer."),
    StrategySpec("cohort_hybrid", "Case table plus text",
                 "As the matched case table, and the writer also reads the papers' text."),
    # Improvements on direct reading (docs/direct-improvements.md); evaluated without repair.
    StrategySpec("direct_checklist", "Direct reading, curator checklist",
                 "Direct reading; the house style's per-paper guidance is an explicit list of what a curator records."),
    StrategySpec("direct_complete", "Direct reading, completeness pass",
                 "Direct reading's draft; a per-paper omission check, then one revision adding the listed omissions."),
    StrategySpec("direct_ensemble", "Direct reading, three-draft merge",
                 "Direct reading's draft and two fresh samples, merged keeping every distinct statement."),
)}

# What 'all' means on the command line: the strategies of the first comparison.
# The later ones are run by name.
CORE = ("kg", "direct", "agent", "closedbook", "recall", "cohort")


def parse_strategies(value: str) -> tuple[str, ...]:
    """'kg', 'both', 'all' or a comma-separated list -> strategy names in registry order."""
    if value == "both":
        wanted = {"kg", "direct"}
    elif value == "all":
        wanted = set(CORE)
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


def audit_papers(name: str, papers: list[Paper], out_dir: Path) -> list[Paper]:
    """The papers the audit should read for this strategy's entry."""
    hook = getattr(import_module(f"{__name__}.{name}"), "audit_papers", None)
    return hook(papers, out_dir) if hook else papers


def after_audit(name: str, entry: GeneratedEntry, papers: list[Paper], out_dir: Path) -> None:
    hook = getattr(import_module(f"{__name__}.{name}"), "after_audit", None)
    if hook:
        hook(entry, papers, out_dir)
