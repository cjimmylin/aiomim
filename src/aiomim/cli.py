"""Command line interface: `aiomim --help`."""

from __future__ import annotations

import json
import logging
import re

import click

from .config import get_settings
from .pipeline import RunConfig, collect_summary, run_many, run_seed


def _strategies(value: str) -> tuple[str, ...]:
    return ("kg", "direct") if value == "both" else (value,)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Debug logging.")
def main(verbose: bool) -> None:
    """Automated, evidence-grounded curation of OMIM-style entries."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _read_mims(path: str) -> list[str]:
    """MIM numbers from the first column of a TSV/text file (header and comments skipped)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            token = line.split("\t")[0].strip()
            if token.isdigit():
                out.append(token)
    return out


@main.command()
@click.argument("mims", nargs=-1)
@click.option("--from-file", type=click.Path(exists=True), help="Read MIM numbers from a file (first column).")
@click.option("--run", "run_name", default="default", show_default=True, help="Name of the run directory.")
@click.option("--retrieval", type=click.Choice(["oracle", "open"]), default="oracle", show_default=True,
              help="oracle: use OMIM's own reference list. open: find the literature from scratch.")
@click.option("--strategy", type=click.Choice(["kg", "direct", "both"]), default="kg", show_default=True,
              help="kg: write from the evidence graph. direct: baseline, write straight from the papers.")
@click.option("--max-papers", default=25, show_default=True, help="Cap on papers selected by open retrieval.")
@click.option("--no-verify", is_flag=True, help="Skip the claim-level audit.")
@click.option("--no-repair", is_flag=True, help="Audit but do not revise flagged paragraphs.")
@click.option("--no-eval", is_flag=True, help="Skip scoring against the gold standard.")
@click.option("--no-fulltext", is_flag=True, help="Use abstracts only.")
@click.option("--jobs", default=1, show_default=True, help="Entries to process in parallel.")
def run(mims, from_file, run_name, retrieval, strategy, max_papers, no_verify, no_repair, no_eval, no_fulltext, jobs):
    """Replicate existing OMIM entries (by MIM number) and score them."""
    mims = list(mims) + (_read_mims(from_file) if from_file else [])
    if not mims:
        raise click.UsageError("give MIM numbers or --from-file")
    cfg = RunConfig(run=run_name, retrieval=retrieval, strategies=_strategies(strategy), verify=not no_verify,
                    repair=not no_repair, evaluate=not no_eval, fulltext=not no_fulltext, max_papers=max_papers)
    summary = run_many(list(mims), cfg, jobs=jobs)
    _print_summary(summary)


@main.command()
@click.option("--title", required=True, help="Working title of the disorder (or gene).")
@click.option("--gene", "genes", multiple=True, help="Gene symbol(s) involved.")
@click.option("--pmid", "pmids", multiple=True, help="Key papers to start from.")
@click.option("--entry-type", type=click.Choice(["phenotype", "gene"]), default="phenotype", show_default=True)
@click.option("--run", "run_name", default="new", show_default=True)
@click.option("--max-papers", default=25, show_default=True)
def create(title, genes, pmids, entry_type, run_name, max_papers):
    """Draft a NEW entry from a title, gene(s) and optional seed papers."""
    from .models import Seed

    seed = Seed(title=title.upper(), entry_type=entry_type, gene_symbols=list(genes), seed_pmids=list(pmids))
    name = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    cfg = RunConfig(run=run_name, retrieval="open", strategies=("kg",), evaluate=False, max_papers=max_papers)
    entries = run_seed(seed, cfg, name)
    out = get_settings().runs / run_name / name
    click.echo(f"Draft written to {out}/entry.kg.md ({len(entries['kg'].all_paragraphs())} paragraphs)")


@main.command()
@click.argument("mims", nargs=-1, required=True)
@click.option("--refresh", is_flag=True, help="Rebuild instead of using the cached gold record.")
def gold(mims, refresh):
    """Show what gold-standard material is publicly available for each MIM number."""
    from .gold import build_gold

    for mim in mims:
        g = build_gold(mim, refresh=refresh)
        click.echo(json.dumps({
            "mim": g.mim, "prefix": g.prefix, "type": g.entry_type, "title": g.title, "symbol": g.symbol,
            "cited_references": len(g.cited_pmids), "genes": [x.symbol for x in g.genes],
            "inheritance": g.inheritance, "hpo_annotations": len(g.hpo_annotations),
            "omim_allelic_variants": len(g.allelic_variants), "omim_paragraphs": len(g.gold_paragraphs),
            "omim_full_text": bool(g.omim_text),
        }, indent=2))


@main.command()
@click.option("--from", "created_from", required=True, help="Earliest creation date, YYYY/MM/DD.")
@click.option("--to", "created_to", required=True, help="Latest creation date, YYYY/MM/DD.")
@click.option("--entry-type", type=click.Choice(["phenotype", "gene"]), default="phenotype", show_default=True)
@click.option("--limit", default=40, show_default=True)
@click.option("--min-paragraphs", default=1, show_default=True,
              help="Keep entries with at least this many OMIM-authored gold paragraphs.")
def select(created_from, created_to, entry_type, limit, min_paragraphs):
    """List OMIM entries created in a date window, with their gold coverage.

    Entries created after the writing model's training cut-off are the cleanest
    test: the model cannot have seen them.
    """
    from .gold import find_entries, gold_coverage

    rows = []
    for mim in find_entries(created_from, created_to, entry_type=entry_type, limit=limit):
        try:
            row = gold_coverage(mim)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"{mim}\tERROR {exc}", err=True)
            continue
        if row.get("n_gold_paragraphs", 0) >= min_paragraphs:
            rows.append(row)
            click.echo("\t".join(str(row.get(k, "")) for k in
                                 ("mim", "prefix", "n_refs", "n_gold_paragraphs", "n_hpo", "n_genes", "inheritance", "title")))
    click.echo(f"{len(rows)} entries", err=True)


@main.command()
@click.option("-n", "n", default=100, show_default=True, help="Number of entries.")
@click.option("--seed", default=13, show_default=True, help="Random seed; the same seed gives the same set.")
@click.option("--min-refs", default=2, show_default=True)
@click.option("--max-refs", default=12, show_default=True)
@click.option("--min-hpo", default=5, show_default=True, help="Minimum HPO phenotype annotations.")
@click.option("--include", multiple=True, help="MIM numbers to include regardless of the draw.")
@click.option("--out", required=True, type=click.Path(), help="TSV file to write.")
def evalset(n, seed, min_refs, max_refs, min_hpo, include, out):
    """Draw a reproducible, stratified evaluation set of phenotype entries."""
    from pathlib import Path

    from .evalset import sample

    columns = ["mim", "stratum", "n_refs", "n_hpo", "n_omim_paragraphs", "genes", "inheritance", "title"]
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(columns) + "\n")
        for row in sample(n=n, seed=seed, min_refs=min_refs, max_refs=max_refs, min_hpo=min_hpo,
                          include=tuple(include)):
            fh.write("\t".join(str(row[c]) for c in columns) + "\n")
            fh.flush()
            count += 1
            click.echo(f"{count:3d}  {row['mim']}  refs={row['n_refs']:<3} hpo={row['n_hpo']:<3} "
                       f"omim_paragraphs={row['n_omim_paragraphs']:<2} {row['title'][:60]}")
    click.echo(f"{count} entries written to {path}")


@main.command()
@click.argument("run_name")
def summary(run_name):
    """Recompute and print the score table for a finished run."""
    run_dir = get_settings().runs / run_name
    data = collect_summary(run_dir)
    (run_dir / "summary.json").write_text(json.dumps(data, indent=2, default=str))
    _print_summary(data)


@main.command()
@click.argument("run_name")
def compare(run_name):
    """Paired comparison of the evidence-graph strategy against the direct baseline."""
    from .compare import compare_run, comparison_markdown, edge_markdown, write_graph_comparison

    run_dir = get_settings().runs / run_name
    result = compare_run(run_dir)
    result["knowledge_graph_edges"] = write_graph_comparison(run_dir)
    (run_dir / "comparison.json").write_text(json.dumps(result, indent=2))
    text = comparison_markdown(result) + "\n" + edge_markdown(result["knowledge_graph_edges"])
    (run_dir / "comparison.md").write_text(text)
    click.echo(text)


@main.command()
@click.argument("run_name")
@click.option("--out", required=True, type=click.Path(), help="Directory to write the shareable copy to.")
def export(run_name, out):
    """Copy a run's results to a directory fit for sharing or committing.

    Generated entries, evidence, graphs and scores are copied. Gold-standard text
    (OMIM-authored paragraphs fetched from ClinVar) is left out: the scores stay,
    the reference wording does not.
    """
    from .export import export_run

    n = export_run(get_settings().runs / run_name, out)
    click.echo(f"{n} entries exported to {out}")


@main.command()
@click.argument("run_name")
@click.option("--out", default=None, help="Output HTML path (default: runs/<run>/report.html).")
@click.option("--split/--single", default=None,
              help="Put each entry's data in report_data/<entry>.js, or everything in one file "
                   "(default: split when the data exceeds about 5 MB).")
def report(run_name, out, split):
    """Build the curator review page for a run."""
    from .report.build import build_report

    path = build_report(get_settings().runs / run_name, out, split)
    click.echo(f"Report written to {path}")


@main.command()
@click.argument("mims", nargs=-1, required=True)
@click.option("--run", "run_name", default="updates", show_default=True)
@click.option("--since", type=int, default=None,
              help="Only consider papers from this year on (default: the year of the entry's newest reference).")
@click.option("--as-of", type=int, default=None,
              help="Back-test: roll the entry back to references published before this year and check "
                   "whether the references OMIM added afterwards are rediscovered.")
@click.option("--max-papers", default=15, show_default=True)
def update(mims, run_name, since, as_of, max_papers):
    """Propose updates to existing entries from literature OMIM does not cite yet."""
    from .update import propose_updates

    for mim in mims:
        result = propose_updates(mim, run_name, since=since, max_papers=max_papers, as_of=as_of)
        line = (f"{mim}: {len(result['proposals'])} proposal(s) from {result['n_screened']} screened papers "
                f"-> {result['path']}")
        if result.get("backtest"):
            b = result["backtest"]
            line += f" | back-test: recovered {len(b['found'])}/{len(b['held_out'])} later OMIM references"
        click.echo(line)


@main.command()
@click.argument("mims", nargs=-1)
@click.option("--from-file", type=click.Path(exists=True), help="Read MIM numbers from a file (first column).")
@click.option("--run", "run_name", default="backtest", show_default=True)
@click.option("--max-papers", default=10, show_default=True)
def backtest(mims, from_file, run_name, max_papers):
    """Back-test update discovery: can the references OMIM added later be rediscovered?

    Each entry is rolled back to its earlier references (the cut-off year is chosen
    so that about the latest third is held out), the later literature is searched,
    and the proposals are checked against the references that were really added.
    """
    from .update import backtest as run_backtest

    mims = list(mims) + (_read_mims(from_file) if from_file else [])
    result = run_backtest(mims, run_name, max_papers=max_papers)
    for row in result["entries"]:
        click.echo(f"{row['mim']}  as of {row['as_of']}: found {row['found']}/{row['held_out']} later references; "
                   f"{row['n_proposals']} proposals from {row['n_screened']} screened  {row['title'][:44]}")
    click.echo(f"\n{result['n_entries']} entries: {result['found']} of {result['held_out']} later OMIM references "
               f"rediscovered (recall {result['recall']}); {result['proposals_not_in_omim']} further proposals "
               f"are papers OMIM does not cite.")


@main.command()
@click.argument("run_name")
def adjudicate(run_name):
    """Where a draft and OMIM disagree, check the paper to see which one it supports."""
    from .adjudicate import adjudicate_run

    result = adjudicate_run(get_settings().runs / run_name)
    for strategy, row in result["by_strategy"].items():
        click.echo(f"{strategy}: {row['n']} disagreements with OMIM - paper supports the draft in {row['draft']}, "
                   f"OMIM in {row['reference']}, both in {row['both']}, neither in {row['neither']}; "
                   f"undecidable from the available text in {row['cannot_tell']}.")


@main.command(name="audit-check")
@click.argument("run_name")
@click.option("-n", "n", default=60, show_default=True, help="Number of paragraphs to alter.")
@click.option("--seed", default=11, show_default=True)
def audit_check(run_name, n, seed):
    """Measure the audit: plant one known error per paragraph and count how many it catches."""
    from .auditcheck import run_audit_check

    result = run_audit_check(get_settings().runs / run_name, n=n, seed=seed)
    o = result["overall"]
    click.echo(f"{o['n']} altered paragraphs: {o['flagged']} flagged, {o['downgraded_to_partial']} downgraded to "
               f"partly supported, {o['missed']} still passed as supported (detection {o['detection_rate']}).")
    for kind, row in result["by_kind"].items():
        click.echo(f"  {kind:24s} n={row['n']:<3} detected={row['detection_rate']}  missed={row['missed']}")
    for level, row in result["by_content_level"].items():
        click.echo(f"  paper read as {level:9s} n={row['n']:<3} detected={row['detection_rate']}  missed={row['missed']}")


def _fmt(value) -> str:
    if value is None:
        return "  -  "
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _print_summary(summary: dict) -> None:
    columns = [("mim", 7), ("refs_gold", 5), ("ref_recall", 6), ("gene_f1", 6), ("inheritance_match", 5),
               ("hpo_exact_f1", 6), ("hpo_hier_f1", 6), ("variant_recall", 6), ("gold_fact_coverage", 6),
               ("claims", 6), ("claim_supported_rate", 6), ("claim_error_rate", 6)]
    heads = ["MIM", "refs", "refRec", "geneF1", "inh", "hpoF1", "hpoHF1", "varRec", "factCov", "claims", "supp", "err"]
    for strategy, rows in summary.get("entries", {}).items():
        click.echo(f"\n== strategy: {strategy} ==")
        click.echo("  ".join(h.ljust(w) for h, (_, w) in zip(heads, columns)) + "  title")
        for row in rows:
            click.echo("  ".join(_fmt(row.get(k)).ljust(w) for k, w in columns) + f"  {row['title'][:48]}")
        s = summary["strategies"][strategy]
        click.echo(f"-- mean over {s['n_entries']} entries: gene F1 {_fmt(s['gene_f1'])}, inheritance match "
                   f"{_fmt(s['inheritance_match'])}, HPO exact F1 {_fmt(s['synopsis_exact_f1'])}, HPO hierarchical F1 "
                   f"{_fmt(s['synopsis_hierarchical_f1'])}, variant recall {_fmt(s['variant_recall'])}, gold fact "
                   f"coverage {_fmt(s['gold_fact_coverage'])}, claims supported {_fmt(s['claim_supported_rate'])}, "
                   f"claim error rate {_fmt(s['claim_error_rate'])}")
    if summary.get("failures"):
        click.echo(f"\nFailed entries: {summary['failures']}")
    if summary.get("usage_total"):
        u = summary["usage_total"]
        click.echo(f"\nModel usage: {int(u.get('calls', 0))} calls ({int(u.get('cached', 0))} from cache), "
                   f"{int(u.get('input_tokens', 0)):,} input / {int(u.get('output_tokens', 0)):,} output tokens.")


if __name__ == "__main__":
    main()
