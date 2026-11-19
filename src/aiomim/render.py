"""Render a generated entry as Markdown laid out like an OMIM page."""

from __future__ import annotations

from collections import defaultdict

from .models import INHERITANCE_HPO, GeneratedEntry

_BADGE = {"supported": "", "partial": " ⚠︎", "flagged": " ✗", "unverified": ""}


def entry_markdown(entry: GeneratedEntry, show_flags: bool = True) -> str:
    out: list[str] = []
    number = f"{entry.prefix} {entry.mim}" if entry.mim else "(new entry)"
    out.append(f"# {number.strip()}")
    title = entry.title + (f"; {entry.symbol}" if entry.symbol else "")
    out.append(f"## {title}")
    if entry.alt_titles:
        out.append("*Alternative titles; symbols*\n\n" + "  \n".join(entry.alt_titles))

    if entry.relationships:
        out.append("### Phenotype-Gene Relationships")
        out.append("| Location | Phenotype | Phenotype MIM number | Inheritance | Phenotype mapping key | Gene/Locus | Gene/Locus MIM number |")
        out.append("|---|---|---|---|---|---|---|")
        for r in entry.relationships:
            out.append(f"| {r.location} | {r.phenotype.title()} | {r.phenotype_mim} | {', '.join(r.inheritance)} | "
                       f"{r.mapping_key} | {r.gene_symbol} | {r.gene_mim} |")

    def para(p) -> str:
        return p.text + (_BADGE.get(p.status, "") if show_flags else "")

    out.append("### TEXT")
    if entry.intro:
        out.append(para(entry.intro))
    for section in entry.sections:
        out.append(f"### {section.heading}")
        out.extend(para(p) for p in section.paragraphs)

    if entry.clinical_synopsis or entry.inheritance:
        out.append("### Clinical Synopsis")
        if entry.inheritance:
            modes = ", ".join(INHERITANCE_HPO[c][1] for c in entry.inheritance if c in INHERITANCE_HPO)
            out.append(f"**INHERITANCE**  \n- {modes}")
        groups: dict[str, list[str]] = defaultdict(list)
        for item in entry.clinical_synopsis:
            groups[item.category].append(f"- {item.hpo_label} [{item.hpo_id}] ({item.n_papers} paper{'s' if item.n_papers != 1 else ''})")
        for category in sorted(groups):
            out.append(f"**{category.upper()}**  \n" + "\n".join(groups[category]))

    if entry.allelic_variants:
        out.append("### ALLELIC VARIANTS")
        for av in entry.allelic_variants:
            names = f" [{'; '.join(av.hgvs)}]" if av.hgvs else ""
            out.append(f"**.{av.number:04d} {av.phenotype.upper()}**  \n{av.name}{names}")
            out.extend(para(p) for p in av.paragraphs)

    if entry.references:
        out.append("### REFERENCES")
        out.extend(f"{n}. {ref.citation}" for n, ref in enumerate(entry.references, 1))

    if show_flags:
        out.append("---\n*Generated automatically from the cited literature. ⚠︎ marks a paragraph with a claim the "
                   "audit found only partly supported by its source; ✗ marks one with an unsupported or contradicted "
                   "claim. Not reviewed by a curator.*")
    return "\n\n".join(out) + "\n"
