"""The entries of Experiment B and the corpus each system is given.

Entries: the 38 ablation entries every variant completed (`results/ablation40/ablation_tables.json`,
key "common"; the two left out, 613744 and 619681, lost a per-paper call), sorted by MIM
number and shuffled with `random.Random(SEED)`. Written to `evalsets/external38.tsv`. The
first 10 (reduced from the design's 24) are the set for PaperQA2 and STORM; GraphRAG takes
a prefix of those (as many as fit in 1,000 model calls, at least 6).

Corpus of one entry: its header (title, alternative titles; the causal gene is withheld,
as from the project's strategies) and exactly the papers its strategies were given, at the
access level they had, with the same text. The papers are read with
`gaps.load_entry_papers` from the entry folder of run `omim100` (the run the comparison
strategies come from; its paper lists are identical to those of `ablation40`), and each
paper's text is what `synthesize.paper_blocks` shows a writer: the reference line, a blank
line, then `Paper.source_text()` (TITLE / ABSTRACT / FULL TEXT) cut to the same equal
share of 600,000 characters. A title-only paper is its reference line and title.

    PYTHONPATH=src python -m aiomim.external.corpus order            # writes evalsets/external38.tsv
    PYTHONPATH=src python -m aiomim.external.corpus export 108770 DIR  # one entry's corpus
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Paper

SEED = 20261120                       # the date the design was fixed
N_MAIN = 10                           # PaperQA2 and STORM (reduced from the design's 24); GraphRAG takes a prefix
SOURCE_RUN = "omim100"
ABLATION_TABLES = Path("results/ablation40/ablation_tables.json")
ABLATION_TSV = Path("evalsets/ablation40.tsv")
ORDER_TSV = Path("evalsets/external38.tsv")
DIRECT_TOTAL_CHARS = 600_000          # as synthesize.paper_blocks
MIN_PER_PAPER = 20_000


class CorpusError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Entry list
# --------------------------------------------------------------------------- #


def ablation_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    header: list[str] | None = None
    for line in ABLATION_TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cells = line.split("\t")
        if header is None:
            header = cells
            continue
        rows[cells[0]] = dict(zip(header, cells))
    return rows


def completed_entries() -> list[str]:
    common = json.loads(ABLATION_TABLES.read_text(encoding="utf-8"))["common"]
    if len(common) != 38:
        raise CorpusError(f"expected 38 completed ablation entries, found {len(common)}")
    return sorted(common, key=int)


def seeded_order(entries: list[str] | None = None, seed: int = SEED) -> list[str]:
    order = sorted(entries if entries is not None else completed_entries(), key=int)
    random.Random(seed).shuffle(order)
    return order


def write_order(path: Path = ORDER_TSV) -> list[str]:
    order = seeded_order()
    rows = ablation_rows()
    lines = [
        "# Experiment B (docs/experiments-round2.md): published systems as released.",
        "# Entries: the 38 entries of evalsets/ablation40.tsv that every ablation variant completed",
        "# (results/ablation40/ablation_tables.json, key 'common'; 613744 and 619681 left out).",
        f"# Order: sorted by MIM number, then random.Random({SEED}).shuffle. Rank 1-{N_MAIN} is the set for",
        f"# PaperQA2 and STORM (reduced from the design's 24 for budget); GraphRAG runs on a prefix of those ranks",
        "# (as many as fit in 1,000 model calls, at least 6). Ranks after that are listed for completeness.",
        "mim\trank\tset\tn_papers\tn_fulltext\tn_abstract\tn_title\ttitle",
    ]
    for rank, mim in enumerate(order, 1):
        r = rows[mim]
        lines.append("\t".join([mim, str(rank), f"main{N_MAIN}" if rank <= N_MAIN else "rest",
                                r["n_papers"], r["n_fulltext"], r["n_abstract"], r["n_title"], r["title"]]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return order


def entry_order(path: Path = ORDER_TSV) -> list[str]:
    """MIM numbers in their seeded order (from the TSV if written, else recomputed)."""
    if path.exists():
        return [line.split("\t")[0] for line in path.read_text(encoding="utf-8").splitlines()
                if line[:1].isdigit()]
    return seeded_order()


def main_set() -> list[str]:
    return entry_order()[:N_MAIN]


# --------------------------------------------------------------------------- #
# Titles in ordinary capitalisation
# --------------------------------------------------------------------------- #

# Words that keep a capital in running text (eponyms, X-linked). Everything else is lower case,
# except the first letter, roman numerals, tokens mixing letters and digits (2EE, 10B, Q10) and
# tokens that are already in mixed case in the OMIM title (ReNU).
_KEEP = {"charcot-marie-tooth": "Charcot-Marie-Tooth", "noonan": "Noonan", "wolfram": "Wolfram",
         "loeys-dietz": "Loeys-Dietz", "stickler": "Stickler", "x-linked": "X-linked",
         "acetylcholine": "acetylcholine"}
_ROMAN = re.compile(r"^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$")


def _word(token: str) -> str:
    core = token.strip(",;:()")
    lead = token[: len(token) - len(token.lstrip(",;:()"))]
    trail = token[len(lead) + len(core):]
    low = core.lower()
    if low in _KEEP:
        out = _KEEP[low]
    elif core and _ROMAN.match(core) and len(core) > 0 and core not in ("I",):
        out = core
    elif re.search(r"\d", core) and re.search(r"[A-Za-z]", core):
        out = core.upper()
    elif core != core.upper() and core != core.lower():
        out = core               # already mixed case (ReNU)
    else:
        out = low
    return lead + out + trail


def ordinary_title(title: str, *, capitalise: bool = True) -> str:
    """'CHARCOT-MARIE-TOOTH DISEASE, AXONAL, TYPE 2EE' -> 'Charcot-Marie-Tooth disease, axonal, type 2EE'.

    With `capitalise=False` the first letter is left as the rules make it, for use inside a
    sentence ('atrial standstill 1', 'Noonan syndrome-like disorder ...')."""
    words = [_word(t) for t in title.split()]
    text = " ".join(words)
    return text[:1].upper() + text[1:] if text and capitalise else text


# --------------------------------------------------------------------------- #
# One entry's corpus
# --------------------------------------------------------------------------- #


@dataclass
class EntryCorpus:
    mim: str
    title: str                 # as OMIM writes it (upper case)
    title_ordinary: str
    alt_titles: list[str]
    papers: list[Paper]        # oldest first, as paper_blocks orders them
    texts: dict[str, str]      # pmid -> exported text
    per_paper_chars: int
    truncated: list[str]

    @property
    def pmids(self) -> list[str]:
        return [p.pmid for p in self.papers]


def source_dir(mim: str, run: str = SOURCE_RUN) -> Path:
    from ..config import get_settings

    return get_settings().runs / run / mim


def paper_text(paper: Paper, per_paper: int) -> tuple[str, bool]:
    """The paper as `synthesize.paper_blocks` shows it, without the <paper> tag: reference, blank line, text."""
    text = paper.source_text()
    cut = len(text) > per_paper
    if cut:
        text = text[:per_paper]
    return f"{paper.reference}\n\n{text}", cut


def load_entry(mim: str, run: str = SOURCE_RUN) -> EntryCorpus:
    from ..gaps import load_entry_papers

    entry_dir = source_dir(mim, run)
    seed = json.loads((entry_dir / "seed.json").read_text(encoding="utf-8"))
    records = json.loads((entry_dir / "papers.json").read_text(encoding="utf-8"))
    by_pmid = load_entry_papers(entry_dir)
    recorded = {r["pmid"]: r.get("content_level") for r in records}
    missing = [r["pmid"] for r in records if r["pmid"] not in by_pmid]
    if missing:
        raise CorpusError(f"{mim}: papers not loadable: {missing}")
    changed = [f"{pmid} {by_pmid[pmid].content_level} != {lvl}" for pmid, lvl in recorded.items()
               if lvl and by_pmid[pmid].content_level != lvl]
    if changed:
        raise CorpusError(f"{mim}: access level differs from the run's record: {changed}")
    papers = sorted(by_pmid.values(), key=lambda p: (p.year or 9999, p.pmid))
    per_paper = max(MIN_PER_PAPER, DIRECT_TOTAL_CHARS // max(1, len(papers)))
    texts, truncated = {}, []
    for p in papers:
        texts[p.pmid], cut = paper_text(p, per_paper)
        if cut:
            truncated.append(p.pmid)
    return EntryCorpus(mim=mim, title=seed["title"], title_ordinary=ordinary_title(seed["title"]),
                       alt_titles=list(seed.get("alt_titles") or []), papers=papers, texts=texts,
                       per_paper_chars=per_paper, truncated=truncated)


def export_entry(mim: str, out_dir: str | Path, run: str = SOURCE_RUN) -> EntryCorpus:
    """Write `<out_dir>/<pmid>.txt` per paper, `papers.csv` and `entry.json`. Returns the corpus."""
    corpus = load_entry(mim, run)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for pmid, text in corpus.texts.items():
        (out / f"{pmid}.txt").write_text(text, encoding="utf-8")
    with (out / "papers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pmid", "title", "first_author", "year", "journal", "access_level", "characters", "label",
                    "file"])
        for p in corpus.papers:
            w.writerow([p.pmid, p.title, p.authors[0] if p.authors else "", p.year or "", p.journal,
                        p.content_level, len(corpus.texts[p.pmid]), p.label, f"{p.pmid}.txt"])
    (out / "entry.json").write_text(json.dumps({
        "mim": mim, "title": corpus.title, "title_ordinary": corpus.title_ordinary,
        "alt_titles": corpus.alt_titles, "n_papers": len(corpus.papers), "pmids": corpus.pmids,
        "per_paper_chars": corpus.per_paper_chars, "truncated": corpus.truncated, "source_run": run,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return corpus


def corpus_summary(corpus: EntryCorpus) -> dict[str, Any]:
    levels: dict[str, int] = {}
    for p in corpus.papers:
        levels[p.content_level] = levels.get(p.content_level, 0) + 1
    return {"mim": corpus.mim, "n_papers": len(corpus.papers), "levels": levels,
            "characters": sum(len(t) for t in corpus.texts.values()), "truncated": corpus.truncated}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.external.corpus")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("order", help=f"write {ORDER_TSV}")
    ex = sub.add_parser("export", help="export one entry's corpus")
    ex.add_argument("mim")
    ex.add_argument("out_dir")
    sub.add_parser("titles", help="print each entry's title in ordinary capitalisation")
    args = ap.parse_args(argv)
    if args.cmd == "order":
        for rank, mim in enumerate(write_order(), 1):
            print(rank, mim)
    elif args.cmd == "export":
        print(json.dumps(corpus_summary(export_entry(args.mim, args.out_dir)), indent=1))
    else:
        rows = ablation_rows()
        for mim in entry_order():
            print(mim, ordinary_title(rows[mim]["title"]), sep="\t")


if __name__ == "__main__":
    main()
