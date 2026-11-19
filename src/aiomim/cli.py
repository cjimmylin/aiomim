"""Command line interface: `aiomim --help`."""

from __future__ import annotations

import json
import logging
import re

import click

from .config import get_settings
from .pipeline import RunConfig, collect_summary, run_many, run_seed


def _strategies(value: str) -> tuple[str, ...]:
    from .strategies import parse_strategies

    try:
        return parse_strategies(value)
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from exc


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
@click.option("--strategy", default="kg", show_default=True,
              help="How entries are generated: kg, direct, agent, closedbook, recall, cohort; a comma-separated "
                   "list; 'both' (kg and direct) or 'all'.")
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
@click.option("--min-paragraphs", default=1, show_default=True,
              help="Minimum OMIM-authored paragraphs (ClinVar) about papers the entry cites.")
@click.option("--include", multiple=True, help="MIM numbers to include regardless of the draw.")
@click.option("--prefilter", is_flag=True,
              help="Check reference and HPO counts before building gold (fast for large-entry draws).")
@click.option("--fill-short", is_flag=True, help="Give quota a stratum cannot fill to the other strata.")
@click.option("--describe-papers", is_flag=True,
              help="Retrieve each entry's papers and add columns for how readable they are.")
@click.option("--out", required=True, type=click.Path(), help="TSV file to write.")
def evalset(n, seed, min_refs, max_refs, min_hpo, min_paragraphs, include, prefilter, fill_short,
            describe_papers, out):
    """Draw a reproducible, stratified evaluation set of phenotype entries.

    The defaults reproduce evalsets/omim100.tsv. The large-entry tier was drawn with
    -n 12 --min-refs 30 --max-refs 100 --min-paragraphs 5 --prefilter --fill-short --describe-papers.
    """
    from pathlib import Path

    from .evalset import describe_papers as describe
    from .evalset import sample

    columns = ["mim", "stratum", "n_refs", "n_hpo", "n_omim_paragraphs", "genes", "inheritance", "title"]
    if describe_papers:
        columns[5:5] = ["n_papers", "n_fulltext", "n_abstract", "n_title", "source_chars"]
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(columns) + "\n")
        for row in sample(n=n, seed=seed, min_refs=min_refs, max_refs=max_refs, min_hpo=min_hpo,
                          min_paragraphs=min_paragraphs, include=tuple(include), prefilter=prefilter,
                          fill_short=fill_short):
            if describe_papers:
                row.update(describe(row["mim"]))
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
@click.option("--baseline", default="direct", show_default=True, help="Strategy the others are compared against.")
@click.option("--entries-file", type=click.Path(exists=True), default=None,
              help="Compare only these entries (MIM numbers in the first column), e.g. a held-out test split.")
@click.option("--tag", default=None,
              help="Write strategies.<tag>.json/.md instead of the main files (default with --entries-file: the "
                   "file's name without extension). Graph-edge and two-way comparison files are not written.")
@click.option("--by-availability", is_flag=True,
              help="Only OMIM facts conveyed, restricted by whether the text available for the paper states the fact "
                   "(stored judgements of `gaps --frozen`; no model call). Writes strategies.by_availability.json/.md.")
def compare(run_name, baseline, entries_file, tag, by_availability):
    """Compare every strategy of a run: scores, paired differences from the baseline, volume and cost."""
    if by_availability:
        from .gaps import by_availability_markdown, compare_by_availability

        run_dir = get_settings().runs / run_name
        result = compare_by_availability(run_dir, baseline=baseline)
        text = by_availability_markdown(result)
        (run_dir / "strategies.by_availability.json").write_text(json.dumps(result, indent=2))
        (run_dir / "strategies.by_availability.md").write_text(text)
        click.echo(text)
        return
    from .compare import (compare_run, compare_strategies, comparison_markdown, edge_markdown, load_evals,
                          strategies_markdown, write_graph_comparison)

    run_dir = get_settings().runs / run_name
    if entries_file or tag:
        from pathlib import Path

        entries = _read_mims(entries_file) if entries_file else None
        tag = tag or Path(entries_file).name.rsplit(".", 1)[0]
        result = compare_strategies(run_dir, baseline=baseline, entries=entries)
        result["entries_file"] = entries_file
        text = strategies_markdown(result) if result else "No scored entries.\n"
        (run_dir / f"strategies.{tag}.json").write_text(json.dumps(result, indent=2))
        (run_dir / f"strategies.{tag}.md").write_text(text)
        click.echo(text)
        return
    present = load_evals(run_dir)
    edges = write_graph_comparison(run_dir)
    result = compare_strategies(run_dir, baseline=baseline)
    result["knowledge_graph_edges"] = edges
    text = strategies_markdown(result) + "\n" + edge_markdown(edges)
    (run_dir / "strategies.json").write_text(json.dumps(result, indent=2))
    (run_dir / "strategies.md").write_text(text)
    if "kg" in present and "direct" in present:
        # The detailed two-way comparison of the evidence graph with the direct baseline.
        pair = compare_run(run_dir)
        pair["knowledge_graph_edges"] = {k: v for k, v in edges.items() if k in ("kg", "direct")}
        (run_dir / "comparison.json").write_text(json.dumps(pair, indent=2))
        (run_dir / "comparison.md").write_text(
            comparison_markdown(pair) + "\n" + edge_markdown(pair["knowledge_graph_edges"]))
    click.echo(text)


@main.command()
@click.argument("run_name")
@click.option("--strategy", default="direct", show_default=True)
@click.option("--entries-file", type=click.Path(exists=True), default=None, help="Only these entries (first column).")
@click.option("--jobs", default=1, show_default=True, help="Entries to process in parallel.")
@click.option("--frozen", is_flag=True,
              help="Use the frozen fact lists (after `rescore`): availability is judged once per paragraph and "
                   "shared by every strategy; writes gaps.<strategy>.frozen.*.")
@click.option("--conveyed", is_flag=True,
              help="The converse, on the frozen fact lists: are the facts the draft conveyed stated in the text it "
                   "had (then in the entry's other papers)? Writes gaps.<strategy>.conveyed.*.")
def gaps(run_name, strategy, entries_file, jobs, frozen, conveyed):
    """Split the OMIM facts a draft missed into ones the available text had (omission) and ones it lacked (access)."""
    from .gaps import conveyed_markdown, conveyed_run, gaps_markdown, gaps_run

    run_dir = get_settings().runs / run_name
    if conveyed:
        result = conveyed_run(run_dir, strategy, entries=_read_mims(entries_file) if entries_file else None,
                              jobs=jobs)
        click.echo(conveyed_markdown(result, run_name, strategy))
        return
    result = gaps_run(run_dir, strategy, entries=_read_mims(entries_file) if entries_file else None, jobs=jobs,
                      frozen=frozen)
    click.echo(gaps_markdown(result, run_name, strategy))


@main.command()
@click.argument("run_name")
@click.option("--strategies", "strategies", default=None,
              help="Comma-separated strategies (default: every strategy scored in the run).")
@click.option("--whole-draft", is_flag=True,
              help="Also mark the frozen facts against the whole draft (gold_text_frozen_whole).")
@click.option("--entries-file", type=click.Path(exists=True), default=None, help="Only these entries (first column).")
@click.option("--jobs", default=1, show_default=True, help="Entries to process in parallel.")
def rescore(run_name, strategies, whole_draft, entries_file, jobs):
    """Score a run's existing drafts against frozen per-paragraph fact lists, without regenerating anything.

    Writes gold_text_frozen into eval.<strategy>.json (gold_text is left as it is).
    Under AIOMIM_REPLICATE=<salt> the marks go to judge_<salt>.<strategy>.json
    instead, and the fact lists are read from the store, not split again.
    """
    from .facts import rescore_run

    run_dir = get_settings().runs / run_name
    names = [s.strip() for s in strategies.split(",") if s.strip()] if strategies else None
    result = rescore_run(run_dir, names, whole=whole_draft, jobs=jobs,
                         entries=_read_mims(entries_file) if entries_file else None)
    for strategy, m in result["means"].items():
        click.echo(f"{strategy:12s} {m['n_entries']} entries  coverage: old {_fmt(m.get('gold_text_coverage_mean'))} "
                   f"on {m.get('gold_text_n_facts')} facts, frozen {_fmt(m.get('gold_text_frozen_coverage_mean'))} "
                   f"on {m.get('gold_text_frozen_n_facts')} facts"
                   + (f", whole draft {_fmt(m.get('gold_text_frozen_whole_coverage_mean'))}"
                      if "gold_text_frozen_whole_coverage_mean" in m else "")
                   + f"; unjudged {m['unjudged']}")
    u = result["usage"]
    click.echo(f"Model calls: {int(u.get('calls', 0))} ({int(u.get('cached', 0))} from cache), "
               f"{int(u.get('input_tokens', 0)):,} input / {int(u.get('output_tokens', 0)):,} output tokens spent now; "
               f"{int(u.get('full_input_tokens', 0)):,} / {int(u.get('full_output_tokens', 0)):,} if made fresh.")
    if result["failures"]:
        click.echo(f"Failed entries: {result['failures']}")


@main.command()
@click.argument("run_name")
@click.option("--strategies", "strategies", default="direct", show_default=True, help="Comma-separated strategies.")
@click.option("--entries-file", type=click.Path(exists=True), default=None, help="Only these entries (first column).")
@click.option("--jobs", default=1, show_default=True, help="Entries to process in parallel.")
def editorial(run_name, strategies, entries_file, jobs):
    """Editorial precision: the share of what a draft says about each paper that OMIM's paragraph also says."""
    from .editorial import editorial_markdown, editorial_run

    run_dir = get_settings().runs / run_name
    result = editorial_run(run_dir, _strategies(strategies), entries=_read_mims(entries_file) if entries_file else None,
                           jobs=jobs)
    click.echo(editorial_markdown(result))


@main.command(name="guide-split")
@click.option("--source", default="evalsets/omim100.tsv", show_default=True, type=click.Path(exists=True))
@click.option("--train", "train_out", default="evalsets/omim100.train.tsv", show_default=True)
@click.option("--test", "test_out", default="evalsets/omim100.test.tsv", show_default=True)
@click.option("-n", "n_train", default=30, show_default=True, help="Training entries.")
@click.option("--seed", default=None, type=int, help="Random seed (default: the fixed seed in aiomim.guide).")
def guide_split(source, train_out, test_out, n_train, seed):
    """Split an evaluation set into train and test, stratified by MIM-range stratum (fixed seed)."""
    from pathlib import Path

    from .guide import SPLIT_SEED, write_split

    n, m = write_split(Path(source), Path(train_out), Path(test_out), n_train=n_train,
                       seed=SPLIT_SEED if seed is None else seed)
    click.echo(f"{n} training entries -> {train_out}; {m} test entries -> {test_out}")


@main.command(name="guide-learn")
@click.argument("run_name")
@click.option("--train-file", required=True, type=click.Path(exists=True), help="Training entries (first column).")
@click.option("--out", default="guides/omim100.guide.md", show_default=True, type=click.Path())
@click.option("--rounds", default=2, show_default=True)
@click.option("--work", default=None, help="Run folder for the training rounds (default: <run>_guide_train).")
@click.option("--strategy", default="direct", show_default=True, help="Baseline strategy the feedback comes from.")
@click.option("--jobs", default=3, show_default=True, help="Entries to process in parallel.")
def guide_learn(run_name, train_file, out, rounds, work, strategy, jobs):
    """Learn a curation guide from the training entries' misses and extras, in a few reflect-and-score rounds."""
    from pathlib import Path

    from .guide import learn_guide

    record = learn_guide(run_name, Path(train_file), Path(out), rounds=rounds, work=work, strategy=strategy, jobs=jobs)
    b = record["baseline"]
    click.echo(f"baseline: coverage {b['gold_fact_coverage']}, synopsis F1 {b['synopsis_exact_f1']}, "
               f"statements/paper {b['statements_per_paper']}")
    for r in [*record["history"], {"round": "final", **record["confirmation"]}]:
        s, g = r["scores"], r["gains"]
        click.echo(f"{r['round']}: coverage {s['gold_fact_coverage']} ({g['coverage_gain']:+}), synopsis F1 "
                   f"{s['synopsis_exact_f1']} ({g['synopsis_f1_gain']:+}), statements/paper {s['statements_per_paper']} "
                   f"(x{g['statements_growth']}), on {s['n_entries']} entries")
    for part, sel in record["selection"].items():
        click.echo(f"{part} part: {sel['why']}; {'included' if sel['included'] else 'left out'}")
    click.echo(f"guide -> {out}")


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
@click.option("--fragment", is_flag=True,
              help="Also write report.fragment.html: the page without its <html>/<head>/<body> shell, for hosts "
                   "that supply their own.")
def report(run_name, out, split, fragment):
    """Build the curator review page for a run."""
    from .report.build import build_report

    path = build_report(get_settings().runs / run_name, out, split, fragment)
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
@click.argument("run_names", nargs=-1, required=True)
def replicates(run_names):
    """Run-to-run variation across replicate runs (AIOMIM_REPLICATE) of the same entries and strategies.

    Writes replicates.json and replicates.md into the first run's folder.
    """
    from .replicates import replicates_markdown, write_replicates

    if len(run_names) < 2:
        raise click.UsageError("give at least two replicate runs")
    result = write_replicates([get_settings().runs / name for name in run_names])
    click.echo(replicates_markdown(result))


@main.command()
@click.argument("run_name")
def adjudicate(run_name):
    """Where a draft and OMIM disagree, check the paper to see which one it supports."""
    from .adjudicate import adjudicate_run, corrections_markdown

    run_dir = get_settings().runs / run_name
    result = adjudicate_run(run_dir)
    (run_dir / "candidate_corrections.md").write_text(corrections_markdown(result))
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


@main.command(name="audit-control")
@click.argument("run_name")
def audit_control(run_name):
    """Re-audit the planted test's paragraphs unaltered: how often a re-audit flags a paragraph that passed once.

    Run under AIOMIM_REPLICATE=<salt> so every call is made afresh. Writes audit_control.json.
    """
    from .auditcheck import run_audit_control

    if not get_settings().replicate:
        raise click.UsageError("set AIOMIM_REPLICATE=<salt>: the control must not replay cached verdicts")
    result = run_audit_control(get_settings().runs / run_name)
    o = result["overall"]
    click.echo(f"{o['paragraphs']} unaltered paragraphs: {o['paragraphs_flagged']} with a claim flagged; "
               f"{o['claims_flagged']} of {o['claims_audited']} claims flagged ({o['claims_unsupported']} unsupported, "
               f"{o['claims_contradicted']} contradicted), {o['claims_partly_supported']} partly supported, "
               f"{o['claims_not_checkable']} not checkable. Safety stops: {result['safety_stops']}. "
               f"Calls: {result['usage']['fresh']} fresh, {result['usage']['cached']} cached.")


@main.command(name="secondhand-check")
@click.argument("mims", nargs=-1)
@click.option("--from-file", type=click.Path(exists=True), help="Read MIM numbers from a file (first column).")
@click.option("--source", default="omim100", show_default=True,
              help="Run whose entries, gold and full-text drafts are read (never written).")
@click.option("--run", "run_name", default="secondhand_check", show_default=True,
              help="Run directory the check writes to.")
@click.option("--limit", type=int, default=None, help="Check at most this many entries.")
@click.option("--jobs", default=1, show_default=True, help="Entries to process in parallel.")
def secondhand_check(mims, from_file, source, run_name, limit, jobs):
    """Hide the full text of papers read in full and measure what second-hand evidence recovers, and how accurately."""
    from .secondhand import check_run

    mims = list(mims) + (_read_mims(from_file) if from_file else [])
    result = check_run(source, run_name, mims or None, limit=limit, jobs=jobs)
    click.echo((get_settings().runs / run_name / "secondhand_check.md").read_text())
    if result.get("failures"):
        click.echo(f"Failed entries: {result['failures']}")


@main.command(name="secondhand-fetch")
@click.argument("mims", nargs=-1)
@click.option("--from-file", type=click.Path(exists=True), help="Read MIM numbers from a file (first column).")
@click.option("--include-fulltext", is_flag=True,
              help="Also fetch for papers readable in full (what secondhand-check hides).")
@click.option("--jobs", default=4, show_default=True, help="Target papers looked up in parallel.")
def secondhand_fetch(mims, from_file, include_fulltext, jobs):
    """Fill the second-hand evidence cache (citing papers and passages) without generating anything."""
    from .secondhand import fetch_entries

    mims = list(mims) + (_read_mims(from_file) if from_file else [])
    if not mims:
        raise click.UsageError("give MIM numbers or --from-file")
    result = fetch_entries(mims, include_fulltext=include_fulltext, jobs=jobs, echo=click.echo)
    t = result["total"]
    click.echo(f"\n{result['entries']} entries, {t['targets']} target papers in {result['seconds']} s: "
               f"{t['with_citing']} with citing papers, {t['with_open_access_citing']} with open-access citing papers, "
               f"{t['with_passages']} with at least one passage; {t['passages']} passages, {t['chars']:,} characters; "
               f"{t['lookup_failed']} lookups failed (not cached; rerun to retry).")
    for level, y in result["by_content_level"].items():
        click.echo(f"  {level:9s} {y['targets']} targets, {y['with_citing']} with citing, "
                   f"{y['with_open_access_citing']} open-access citing, {y['with_passages']} with passages, "
                   f"{y['passages']} passages, {y['chars']:,} chars")
    if result["failures"]:
        click.echo(f"Entries that could not be loaded: {result['failures']}")


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


@main.command()
@click.argument("run_name")
@click.option("--strategy", default="reconciled", show_default=True, type=click.Choice(["reconciled", "cohort"]),
              help="Whose case table to export; frequency agreement is reported for both when present.")
def casebase(run_name, strategy):
    """Score a run's case tables against OMIM's HPO frequencies and export the pooled case database."""
    from .casebase import build_casebase, summary_markdown

    summary = build_casebase(get_settings().runs / run_name, strategy)
    click.echo(summary_markdown(summary))


@main.command("reconcile-check")
@click.argument("run_name")
@click.option("--n", "n", default=20, show_default=True, help="Entries to plant a re-report in.")
@click.option("--seed", default=1, show_default=True)
def reconcile_check_cmd(run_name, n, seed):
    """Plant a re-reported paper in entries of a reconciled run and see whether reconciliation merges it."""
    from .casebase import reconcile_check

    report = reconcile_check(get_settings().runs / run_name, n=n, seed=seed)
    click.echo(json.dumps(report["total"], indent=2))
    click.echo(report["caveat"])


if __name__ == "__main__":
    main()
