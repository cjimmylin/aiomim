"""Agentic curator: an autonomous agent works in a folder of papers and writes the entry.

The papers are laid out as plain-text files with an index, and one Claude Code
agent session (read-only file tools, confined to that folder, no shell, no
network) decides for itself what to read, what to search for and what to
re-check before it writes. Its draft has the shape of the direct strategy's,
plus verbatim quotes per paragraph, and goes through `draft_to_entry` with the
quote check on, so every guard the other strategies get applies here too.

Working files, in `out_dir / "agent_workspace"` (rebuilt on every run, holding
the supplied papers and nothing else):

    PAPERS.md           index: PMID, citation label, year, journal, title,
                        what text is available, size, file
    papers/<pmid>.txt   `paper.source_text()` in full, hard-wrapped
"""

from __future__ import annotations

import logging
import shutil
import textwrap
from pathlib import Path

from pydantic import BaseModel, Field

from ..cache import stable_hash
from ..models import GeneratedEntry, InheritanceCode, Paper, SectionName, Seed
from ..synthesize import INTRO_RULE, STYLE, DSynopsisItem, _gene_reference, _header, draft_to_entry

log = logging.getLogger(__name__)

WRAP = 150            # the Read tool truncates very long lines; full texts have paragraph-long ones
HARD_LIMIT = 1500     # a single "word" longer than this (a sequence, a table row) is cut regardless

AVAILABLE = {"fulltext": "full text", "abstract": "abstract only", "title": "title only"}


# --------------------------------------------------------------------------- #
# Reply schema: DEntry plus quotes per paragraph and a record of the reading
# --------------------------------------------------------------------------- #

_QUOTES = ("One or two spans copied verbatim from a paper this paragraph cites, carrying its key facts "
           "(variant, numbers, zygosity, finding). Checked mechanically against the paper.")


class AParagraph(BaseModel):
    text: str
    pmids: list[str]
    quotes: list[str] = Field(description=_QUOTES)


class ASection(BaseModel):
    name: SectionName
    paragraphs: list[AParagraph]


class ARelationship(BaseModel):
    gene_symbol: str
    inheritance: list[InheritanceCode]
    pmids: list[str]


class AAllelicVariant(BaseModel):
    gene_symbol: str
    name: str
    hgvs: list[str]
    phenotype: str
    paragraphs: list[AParagraph]


class AEntry(BaseModel):
    intro: AParagraph
    sections: list[ASection]
    relationships: list[ARelationship]
    allelic_variants: list[AAllelicVariant]
    clinical_synopsis: list[DSynopsisItem]
    papers_read: list[str] = Field(description="PMIDs of the papers you actually opened")
    process_note: str = Field(description="Briefly: what you read in full, what you searched for, "
                                          "and anything you looked for but could not find")


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

AGENT_SYSTEM = f"""\
You are a senior curator writing an entry for OMIM (Online Mendelian Inheritance in Man). You are at \
your desk with a folder holding the papers the entry is to be based on, and you have tools to list, \
read and search the files in it. Nobody will hand you excerpts: what you know about these papers is \
what you read in them, so read them.

The folder holds `PAPERS.md`, an index of the papers (PMID, the citation label to use for each, year, \
journal, title, whether the full text or only the abstract is available, and its size), and one \
plain-text file per paper under `papers/`. Start with the index. When there are only a few papers, \
read every one of them. A long full text can be read in parts with the Read tool's offset and limit, \
and Grep is the quickest way to find things in it: variant names, patient and family counts, ages, \
ancestry, methods, segregation. A paper you have not opened cannot be cited, and one you skimmed \
can be misreported, so give each paper the reading its content deserves.

The papers in this folder are the only admissible evidence. After you write, every sentence will be \
audited claim by claim against the paper it cites. So write only what the papers say: no facts, \
numbers, variants, citations or interpretations from your own memory of the disorder, the gene, or \
the existing OMIM entry, however confident you are. If the papers leave a gap, leave the gap. Where \
only an abstract is available, use only what the abstract says, and do not fill in what the full \
paper probably contained. Never merge two papers' results into a claim neither made, and never \
attribute a finding to a paper other than the one it came from. Papers that turn out not to concern \
this entry's subject can be left uncited.

Details are where drafts go wrong, so before you finalise, re-check every specific detail you are \
about to write against the paper, with Grep or by re-reading the passage: nucleotide and protein \
changes, zygosity, numbers of patients and families, ages, ancestry and consanguinity. Correct or \
remove anything you cannot find.

For each paragraph, list in `pmids` the PMIDs of the papers it draws on, and in `quotes` one or two \
spans copied verbatim from those papers that carry the paragraph's key facts. The quotes are checked \
mechanically against the cited papers, and a paragraph none of whose quotes is found is discarded. \
So copy the words exactly as they appear in the file: a contiguous span of a sentence or two, not a \
paraphrase, without the line numbers the Read tool shows at the start of each line and without \
stitching together pieces from different places. A span may run across a line break in the file; \
just copy the words in order. The intro needs quotes too: take them from the passage that \
establishes the gene and zygosity.

{STYLE}

{INTRO_RULE}

`relationships`: one item per gene that the papers show to cause this phenotype, with the mode(s) of \
inheritance they establish and the supporting PMIDs. Leave empty if none, or for a gene entry.

`allelic_variants`: one item per variant reported as disease-causing in patients, in chronological \
order of first report, with `hgvs` listing its nucleotide and protein names as the papers give them.

`clinical_synopsis`: the disorder's clinical features as short phrases, one item each, with the \
best-matching Human Phenotype Ontology term name and the PMIDs reporting it.

Finally, list in `papers_read` the PMIDs of the papers you actually opened, and in `process_note` say \
in a few sentences what you read in full, what you searched for, and anything you looked for but \
could not find.\
"""


# --------------------------------------------------------------------------- #
# Workspace
# --------------------------------------------------------------------------- #


def wrap_text(text: str, width: int = WRAP) -> str:
    """Hard-wrap each line of `text` to about `width` characters, blank lines between paragraphs.

    Words are never split (not even at hyphens), so a quote copied from the
    wrapped file is the same sequence of words as in the original text.
    """
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        wrapped = textwrap.wrap(line, width=width, break_long_words=False, break_on_hyphens=False) or [line]
        lines: list[str] = []
        for w in wrapped:
            lines.extend(w[i:i + HARD_LIMIT] for i in range(0, len(w), HARD_LIMIT))
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def _cell(value: str) -> str:
    return " ".join(str(value).split()).replace("|", "/")


def _size(text: str) -> str:
    words = len(text.split())
    return f"{words:,} words, {text.count(chr(10)) + 1:,} lines"


def build_workspace(papers: list[Paper], root: Path) -> tuple[Path, str]:
    """Write the papers and their index into `root` (emptied first); return it and a hash of its contents."""
    if root.exists():
        shutil.rmtree(root)
    (root / "papers").mkdir(parents=True)
    files: dict[str, str] = {}
    rows = []
    for p in sorted(papers, key=lambda p: (p.year or 9999, p.pmid)):
        rel = f"papers/{p.pmid}.txt"
        body = wrap_text(p.source_text())
        files[rel] = body
        rows.append(f"| {p.pmid} | {_cell(p.label)} | {p.year or 'n.d.'} | {_cell(p.journal) or '-'} | "
                    f"{_cell(p.title) or '-'} | {AVAILABLE.get(p.content_level, p.content_level)} | "
                    f"{_size(body)} | {rel} |")
    files["PAPERS.md"] = (
        f"# Papers for this entry ({len(papers)})\n\n"
        "Cite each paper by its label. Files are plain text, wrapped at about 150 characters per line, "
        "with a blank line between paragraphs.\n\n"
        "| PMID | Label | Year | Journal | Title | Available | Size | File |\n"
        "|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )
    for rel, body in files.items():
        (root / rel).write_text(body, encoding="utf-8")
    return root, stable_hash(sorted(files.items()))


# --------------------------------------------------------------------------- #
# The strategy
# --------------------------------------------------------------------------- #


def run(seed: Seed, papers: list[Paper], llm, out_dir: Path) -> GeneratedEntry:
    workspace, key = build_workspace(papers, Path(out_dir) / "agent_workspace")
    gene_ref, gene_facts = _gene_reference(seed.gene_symbols)
    prompt = (
        f"{_header(seed)}\n\n"
        f"Reference data from HGNC (nomenclature only, not literature evidence):\n{gene_ref or 'none supplied'}\n\n"
        f"The {len(papers)} papers for this entry are in your working directory: the index is PAPERS.md "
        "and the texts are under papers/. "
        + ("" if seed.gene_symbols or seed.entry_type == "gene" else
           "No causal gene is given here; establish it, if the papers do, from the papers themselves. ")
        + "Read them, check your details, and write the entry."
    )
    raw = llm.call("agent", AGENT_SYSTEM, prompt, AEntry, tools=("Read", "Grep", "Glob"),
                   workdir=str(workspace), workspace_key=key)

    supplied = [p.pmid for p in sorted(papers, key=lambda p: (p.year or 9999, p.pmid))]
    read = [p for p in dict.fromkeys(str(i).strip() for i in raw.papers_read) if p in supplied]
    paragraphs = [raw.intro, *(x for s in raw.sections for x in s.paragraphs),
                  *(x for v in raw.allelic_variants for x in v.paragraphs)]
    agent_meta = {
        "papers_supplied": len(supplied),
        "papers_read": read,
        "papers_not_read": [p for p in supplied if p not in read],
        "papers_read_unknown": [p for p in raw.papers_read if str(p).strip() not in supplied],
        "paragraphs_without_quotes": sum(1 for x in paragraphs if x.text.strip() and not any(q.strip() for q in x.quotes)),
        "process_note": raw.process_note.strip(),
    }
    return draft_to_entry(seed, papers, raw, llm, strategy="agent", gene_facts=gene_facts,
                          check_quotes=True, meta={"agent": agent_meta})
