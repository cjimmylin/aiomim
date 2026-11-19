"""Offline tests for the paired strategy comparison and the shareable export."""

from __future__ import annotations

import json

from aiomim.compare import _sign_test, access_group, compare_run, comparison_markdown, same_draft, same_fact_marks
from aiomim.export import export_run


def _eval(mim, supported, coverage, f1, access):
    n = 100
    return {
        "mim": mim, "title": f"ENTRY {mim}", "gold_reference_access": access,
        "references": {"cited": {"recall": 1.0}},
        "genes": {"f1": 1.0}, "inheritance": {"match": True},
        "synopsis": {"exact": {"f1": f1, "precision": f1, "recall": f1}, "hierarchical": {"f1": f1},
                     "semantic": {"f1": f1}},
        "variants": {"recall": 1.0},
        "gold_text": {"n_facts": 10, "present": int(coverage * 10), "partial": 0, "absent": 10 - int(coverage * 10),
                      "contradicted": 0, "coverage": coverage, "strict_coverage": coverage, "contradiction_rate": 0.0,
                      "by_content_level": {"abstract": {"n_facts": 10, "present": int(coverage * 10), "partial": 0,
                                                        "contradicted": 0}},
                      "paragraphs": [{"pmids": ["1"], "reference": "OMIM-authored wording", "draft": "draft wording",
                                      "facts": [{"fact": "a fact restating the reference", "status": "present", "note": ""}]}]},
        "faithfulness": {"supported": supported, "partially_supported": 0, "unsupported": n - supported,
                         "contradicted": 0, "supported_rate": supported / n, "error_rate": (n - supported) / n,
                         "before_repair": {"error_rate": (n - supported) / n}},
    }


def _run(tmp_path):
    run = tmp_path / "demo"
    mims = ["100100", "600100", "610100", "616100", "620100", "620200"]
    for i, mim in enumerate(mims):
        d = run / mim
        d.mkdir(parents=True)
        access = {"abstract": 3} if i % 2 else {"fulltext": 2, "abstract": 1}
        (d / "eval.kg.json").write_text(json.dumps(_eval(mim, 98, 0.6, 0.5, access)))
        (d / "eval.direct.json").write_text(json.dumps(_eval(mim, 95, 0.6, 0.4 + 0.02 * i, access)))
        (d / "gold.json").write_text(json.dumps({"secret": "gold text"}))
        (d / "seed.json").write_text(json.dumps({"title": f"ENTRY {mim}"}))
        (d / "entry.kg.md").write_text("# draft\n")
        (d / "entry.kg.json").write_text("{}")
    return run


def test_paired_differences_and_wins(tmp_path):
    result = compare_run(_run(tmp_path))
    assert result["n_entries"] == 6
    rows = {r["metric"]: r for r in result["overall"]}
    supported = rows["claim_supported_rate"]
    assert (supported["kg"], supported["direct"], supported["difference"]) == (0.98, 0.95, 0.03)
    assert (supported["kg_better"], supported["direct_better"], supported["ties"]) == (6, 0, 0)
    assert supported["ci95"] == [0.03, 0.03]
    error = rows["claim_error_rate"]                      # lower is better: the graph wins here too
    assert error["difference"] == -0.03 and error["kg_better"] == 6
    assert rows["gold_fact_coverage"]["ties"] == 6 and rows["gold_fact_coverage"]["sign_test_p"] is None
    f1 = rows["hpo_exact_f1"]                             # 0.5 against 0.40 .. 0.50
    assert f1["kg_better"] == 5 and f1["ties"] == 1 and f1["sign_test_p"] == 0.0625


def test_breakdowns_and_pooled_counts(tmp_path):
    result = compare_run(_run(tmp_path))
    assert {g: b["n"] for g, b in result["by_stratum"].items()} == {
        "classic (1xxxxx-5xxxxx)": 1, "600000-609999": 1, "610000-615999": 1, "616000-619999": 1, "620000 onward": 2}
    assert {g: b["n"] for g, b in result["by_access"].items()} == {
        "no full text (abstracts only)": 3, "half or more full text": 3}
    assert result["pooled"]["kg"]["claims"]["supported_rate"] == 0.98
    assert result["pooled"]["direct"]["claims"]["error_rate"] == 0.05
    assert result["by_gold_text_content_level"]["abstract"]["kg"]["coverage"] == 0.6
    text = comparison_markdown(result)
    assert "| Claims supported by cited paper ↑ | 6 | 98.0% | 95.0% | +3.0 |" in text


def test_sign_test_and_access_groups():
    assert _sign_test(0, 0) is None
    assert _sign_test(5, 5) == 1.0
    assert round(_sign_test(10, 0), 5) == 0.00195
    assert access_group({"gold_reference_access": {"fulltext": 4}}) == "all full text"
    assert access_group({"gold_reference_access": {"fulltext": 1, "abstract": 3}}) == "under half full text"
    assert access_group({}) == "unknown"


def test_export_leaves_gold_text_out(tmp_path):
    run = _run(tmp_path)
    out = tmp_path / "shared"
    assert export_run(run, out) == 6
    assert not list(out.rglob("gold.json"))
    exported = json.loads((out / "100100" / "eval.kg.json").read_text())
    paragraph = exported["gold_text"]["paragraphs"][0]
    assert "reference" not in paragraph and paragraph["facts"] == [{"status": "present"}]
    assert exported["gold_text"]["coverage"] == 0.6           # scores survive
    assert "OMIM-authored wording" not in (out / "100100" / "eval.kg.json").read_text()
    assert "[kg](100100/entry.kg.md)" in (out / "README.md").read_text()


def test_backtest_cutoff_holds_out_about_the_latest_third():
    from aiomim.update import suggest_as_of

    assert suggest_as_of([2007, 2012, 2016, 2018, 2022]) == 2018     # 2 of 5 held out, 3 kept
    assert suggest_as_of([1986, 1986, 1994, 1996, 2006, 2007, 2009]) == 2007     # 2 of 7 held out
    assert suggest_as_of([2020, 2020, 2021]) == 2021
    assert suggest_as_of([2020, 2020, 2020]) is None                  # nothing later to find
    assert suggest_as_of([2019, 2021]) is None                        # too few references


def test_edge_level_graph_comparison(tmp_path):
    from aiomim.compare import edge_scores, graph_edges, write_graph_comparison

    folder = tmp_path / "run" / "500001"
    folder.mkdir(parents=True)
    (folder / "gold.json").write_text(json.dumps({
        "mim": "500001", "title": "LEBER OPTIC ATROPHY AND DYSTONIA",
        "genes": [{"symbol": "MT-ND6"}, {"symbol": "MT-ND1"}], "inheritance": ["MT"],
    }))
    (folder / "entry.kg.json").write_text(json.dumps({
        "relationships": [{"gene_symbol": "MT-ND6", "pmids": ["1"]}, {"gene_symbol": "OPA1", "pmids": ["2"]}],
        "inheritance": ["MT", "AD"],
        "clinical_synopsis": [
            {"hpo_id": "HP:0001332", "hpo_label": "Dystonia", "pmids": ["1"]},
            {"hpo_id": "HP:0007325", "hpo_label": "Generalized dystonia", "pmids": ["1"]}],
        "allelic_variants": [
            {"name": "MTND6, ALA72VAL", "hgvs": ["m.14459G>A"], "paragraphs": [{"pmids": ["1"]}]},
            {"name": "MTND6, NEW", "hgvs": [], "paragraphs": [{"pmids": ["2"]}]}],
    }))
    (folder / "eval.kg.json").write_text(json.dumps({
        "synopsis": {"missed": ["HP:0000648 Optic atrophy"], "extra": ["HP:0007325 Generalized dystonia"]},
        "variants": {"matched": [{"gold": "516006.0002 MTND6, LDYT14459A", "generated": "MTND6, ALA72VAL"}],
                     "missed": ["516000.0012 MTND1, 3697G-A"], "in_omim_via_other_paper": []},
    }))
    rows = graph_edges(tmp_path / "run", "kg")
    by = {(r["relation"], r["object_id"]): r["source"] for r in rows}
    assert by[("caused_by", "MT-ND6")] == "both" and by[("caused_by", "OPA1")] == "generated_only"
    assert by[("caused_by", "MT-ND1")] == "omim_only"
    assert by[("inheritance", "MT")] == "both" and by[("inheritance", "AD")] == "generated_only"
    assert by[("has_phenotype", "HP:0001332")] == "both" and by[("has_phenotype", "HP:0000648")] == "omim_only"
    assert by[("has_variant", "m.14459G>A")] == "both" and by[("has_variant", "516000.0012")] == "omim_only"

    scores = edge_scores(rows)
    assert scores["caused_by"] == {"in_both": 1, "generated": 2, "omim": 2, "precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert scores["has_phenotype"]["precision"] == 0.5 and scores["has_phenotype"]["recall"] == 0.5
    assert write_graph_comparison(tmp_path / "run")["kg"]["inheritance"]["recall"] == 1.0
    assert (tmp_path / "run" / "knowledge_graph.kg.tsv").read_text().count("\n") == len(rows) + 1


def test_all_strategies_side_by_side(tmp_path):
    from aiomim.compare import compare_strategies, strategies_markdown

    run = _run(tmp_path)
    for i, folder in enumerate(sorted(p for p in run.iterdir() if p.is_dir())):
        (folder / "eval.agent.json").write_text(json.dumps(_eval(folder.name, 99, 0.7, 0.45, {"abstract": 3})))
        usage = {"by_strategy": {
            "agent": {"generate/agent": {"calls": 1, "turns": 12, "full_input_tokens": 100000, "full_output_tokens": 5000,
                                         "full_list_price_usd": 1.5, "full_seconds": 200},
                      "audit/verify": {"calls": 6, "turns": 6, "full_input_tokens": 60000, "full_output_tokens": 9000,
                                       "full_list_price_usd": 0.9, "full_seconds": 90},
                      "total": {}},
            "direct": {"generate/synthesize": {"calls": 1, "turns": 1, "full_input_tokens": 40000,
                                               "full_output_tokens": 8000, "full_list_price_usd": 0.5, "full_seconds": 60},
                       "total": {}}}}
        (folder / "usage.json").write_text(json.dumps(usage))
    # one entry the agent did not finish: it must drop out of every column, not just the agent's
    (run / "620200" / "eval.agent.json").unlink()

    result = compare_strategies(run, baseline="direct")
    assert [s["name"] for s in result["strategies"]] == ["kg", "direct", "agent"]      # registry order
    assert result["n_entries"] == 5
    supported = next(r for r in result["means"] if r["metric"] == "claim_supported_rate")
    assert supported["values"] == {"kg": 0.98, "direct": 0.95, "agent": 0.99}
    versus = {r["metric"]: r for r in result["versus_baseline"]["agent"]}
    assert versus["claim_supported_rate"]["difference"] == 0.04 and versus["claim_supported_rate"]["better"] == 5
    assert versus["gold_fact_coverage"]["difference"] == 0.1
    assert "direct" not in result["versus_baseline"]
    cost = result["cost"]["agent"]
    assert cost["entries"] == 5 and cost["generate"]["per_entry"] == {
        "calls": 1.0, "list_price_usd": 1.5, "input_tokens": 100000, "output_tokens": 5000, "seconds": 200.0}
    assert cost["audit"]["per_entry"]["list_price_usd"] == 0.9 and cost["total"]["per_entry"]["list_price_usd"] == 2.4
    assert result["by_content_level"]["abstract"]["agent"]["coverage"] == 0.7
    text = strategies_markdown(result)
    assert "| Metric | Evidence graph | Direct reading | Agentic curator |" in text
    assert "| Generation: list price | $0.50 | $1.50 |" in text


# --------------------------------------------------------------------------- #
# Completion, empty predictions, new measures and statistics (review, section 2)
# --------------------------------------------------------------------------- #


def _full_eval(mim, coverage, *, genes_predicted=("GENE1",), inh_predicted=("AD",), inh_gold=("AD",),
               n_generated=2, n_matched=1, not_in_omim=("X, NEW1",), before=(10, 1, 1)):
    ev = _eval(mim, 95, coverage, 0.5, {"fulltext": 1, "abstract": 1})
    ev["genes"] = {"f1": 1.0 if genes_predicted else None, "recall": 1.0 if genes_predicted else 0.0,
                   "precision": 1.0 if genes_predicted else None,
                   "n_predicted": len(genes_predicted), "n_gold": 1, "predicted": list(genes_predicted), "gold": ["GENE1"]}
    ev["synopsis"]["exact"].update(n_predicted=3, n_gold=4)
    ev["variants"] = {"recall": n_matched / 2, "n_gold": 2, "n_generated": n_generated, "n_matched": n_matched,
                      "not_in_omim": list(not_in_omim), "in_omim_via_other_paper": []}
    ev["inheritance"] = {"predicted": list(inh_predicted), "gold": list(inh_gold),
                         "match": sorted(inh_predicted) == sorted(inh_gold)}
    n, unsupported, contradicted = before
    ev["faithfulness"]["before_repair"] = {"n_claims": n, "unsupported": unsupported, "contradicted": contradicted,
                                           "error_rate": (unsupported + contradicted) / n}
    return ev


def _completion_run(tmp_path):
    run = tmp_path / "run"
    mims = [f"6100{i:02d}" for i in range(8)]
    for i, mim in enumerate(mims):
        d = run / mim
        d.mkdir(parents=True)
        (d / "eval.direct.json").write_text(json.dumps(_full_eval(mim, 0.6)))
        (d / "eval.kg.json").write_text(json.dumps(_full_eval(mim, 0.5 + 0.01 * i)))
        (d / "eval.cohort.json").write_text(json.dumps(_full_eval(mim, 0.5)))
        (d / "eval.reconciled.json").write_text(json.dumps(_full_eval(mim, 0.5)))
        (d / "entry.kg.json").write_text(json.dumps({"meta": {"extraction": {"papers_failed": []}}}))
        (d / "entry.cohort.json").write_text(json.dumps({"meta": {"cohort": {"papers_failed": []}}}))
        (d / "entry.reconciled.json").write_text(json.dumps({"meta": {"reconciled": {}}}))   # nothing recorded
    # 610000: one paper's extraction failed in the graph; the entry is still scored, very low
    (run / "610000" / "entry.kg.json").write_text(json.dumps({"meta": {"extraction": {"papers_failed": ["111"]}}}))
    (run / "610000" / "eval.kg.json").write_text(json.dumps(_full_eval("610000", 0.0)))
    # 610001: the case extraction failed; reconciled has no record and inherits the case table's
    (run / "610001" / "entry.cohort.json").write_text(json.dumps({"meta": {"cohort": {"papers_failed": ["222"]}}}))
    # 610002: direct reading was stopped
    (run / "610002" / "eval.direct.json").write_text(json.dumps({"mim": "610002", "stopped": "safety filter"}))
    return run


def test_completion_is_the_same_rule_for_every_strategy(tmp_path):
    from aiomim.compare import compare_strategies, completion_status, strategies_markdown

    run = _completion_run(tmp_path)
    status = completion_status(run)
    assert status["kg"]["610000"] == {"status": "incomplete", "papers_failed": ["111"], "source": "entry.kg.json"}
    assert status["cohort"]["610001"]["status"] == "incomplete"
    assert status["reconciled"]["610001"]["status"] == "incomplete"
    assert "cohort" in status["reconciled"]["610001"]["source"]
    assert status["direct"]["610002"]["status"] == "no_draft"

    result = compare_strategies(run, baseline="direct")
    assert result["n_entries"] == 5 and result["left_out"] == ["610000", "610001", "610002"]
    assert result["completion"]["kg"]["incomplete"] == {"610000": ["111"]}
    assert result["completion"]["direct"]["no_draft"] == ["610002"]
    assert result["stopped"] == {"direct": ["610002"]}               # the existing field is kept
    coverage = next(r for r in result["versus_baseline"]["kg"] if r["metric"] == "gold_fact_coverage")
    assert coverage["n"] == 5 and coverage["difference"] == round(sum(0.5 + 0.01 * i - 0.6 for i in range(3, 8)) / 5, 4)

    # intention to treat: all 8 entries, the incomplete one kept, the missing draft counted as 0
    itt = result["intention_to_treat"]
    assert itt["n_entries"] == 8 and itt["missing_drafts_counted_as_zero"]["direct"] == 1
    means = next(r for r in itt["means"] if r["metric"] == "gold_fact_coverage")
    assert means["n"] == {"direct": 8, "kg": 8, "cohort": 8, "reconciled": 8}
    assert means["values"]["direct"] == round(0.6 * 7 / 8, 4)
    assert means["values"]["kg"] == round((0.0 + sum(0.5 + 0.01 * i for i in range(1, 8))) / 8, 4)
    text = strategies_markdown(result)
    assert "## Completion" in text and "| Evidence graph | 7 | 1: 610000 (1 paper) | 0 |" in text
    assert "intention to treat" in text


def test_empty_prediction_counts_as_zero(tmp_path):
    from aiomim.compare import compare_strategies, prepare_eval, strategies_markdown

    ev = prepare_eval(_full_eval("610000", 0.5, genes_predicted=()))
    assert ev["genes"]["f1"] == 0.0 and ev["genes"]["recall"] == 0.0 and ev["genes"]["precision"] is None
    assert ev["derived"]["empty_prediction"] == ["genes"]
    syn = _full_eval("610000", 0.5)
    syn["synopsis"] = {"exact": {"f1": None, "precision": None, "recall": 0.0, "n_predicted": 0, "n_gold": 4},
                       "hierarchical": {"f1": None, "recall": 0.0, "n_predicted": 0, "n_gold": 9},
                       "semantic": {"f1": None, "precision": None, "recall": None}}
    syn = prepare_eval(syn)
    assert [syn["synopsis"][k]["f1"] for k in ("exact", "hierarchical", "semantic")] == [0.0, 0.0, 0.0]
    assert syn["synopsis"]["semantic"]["recall"] == 0.0 and syn["synopsis"]["exact"]["precision"] is None
    # an empty gold set leaves the entry undefined, as before
    no_gold = _full_eval("610000", 0.5, genes_predicted=())
    no_gold["genes"]["n_gold"] = 0
    no_gold["genes"]["recall"] = None
    assert prepare_eval(no_gold)["genes"]["f1"] is None

    run = tmp_path / "run"
    for i in range(6):
        d = run / f"61000{i}"
        d.mkdir(parents=True)
        (d / "eval.direct.json").write_text(json.dumps(_full_eval(d.name, 0.6)))
        (d / "eval.closedbook.json").write_text(json.dumps(_full_eval(d.name, 0.2, genes_predicted=() if i < 2 else ("GENE1",))))
    result = compare_strategies(run, baseline="direct")
    gene = next(r for r in result["means"] if r["metric"] == "gene_f1")
    assert gene["values"]["closedbook"] == round(4 / 6, 4) and gene["n"]["closedbook"] == 6
    assert result["pooled"]["closedbook"]["empty_predictions"]["genes"] == 2
    # nothing on disk changed
    assert json.loads((run / "610000" / "eval.closedbook.json").read_text())["genes"]["f1"] is None
    text = strategies_markdown(result)
    assert "Empty predictions count as zero" in text and "Memory only (control): genes 2" in text


def test_variant_precision_inheritance_errors_and_claims_before_repair(tmp_path):
    from aiomim.compare import compare_strategies, prepare_eval, strategies_markdown

    ev = prepare_eval(_full_eval("610000", 0.5, n_generated=4, n_matched=1, not_in_omim=("A", "B", "C"),
                                 before=(20, 3, 1)))
    d = ev["derived"]
    assert d["variant_precision"] == 0.25 and d["variants_not_in_omim"] == 3
    assert d["claim_unsupported_rate_before_repair"] == 0.15 and d["claim_contradicted_rate_before_repair"] == 0.05
    kinds = {
        ((), ("AD",)): "none_stated", (("AD",), ("AD", "AR")): "mode_missing",
        (("AD", "AR"), ("AD",)): "extra_mode", (("AR",), ("AD",)): "different_mode", (("AD",), ("AD",)): None,
    }
    for (pred, gold), kind in kinds.items():
        got = prepare_eval(_full_eval("610000", 0.5, inh_predicted=pred, inh_gold=gold))["derived"]
        assert got["inheritance_error"] == kind
        assert sum(got[f"inheritance_error_{k}"] for k in ("none_stated", "mode_missing", "extra_mode", "different_mode")) == (kind is not None)
    assert prepare_eval(_full_eval("610000", 0.5, inh_gold=()))["derived"]["inheritance_error_none_stated"] is None

    run = tmp_path / "run"
    for i in range(6):
        folder = run / f"61000{i}"
        folder.mkdir(parents=True)
        (folder / "eval.direct.json").write_text(json.dumps(_full_eval(folder.name, 0.6)))
        (folder / "eval.kg.json").write_text(json.dumps(_full_eval(folder.name, 0.6, n_generated=4, n_matched=1,
                                                                   not_in_omim=("A", "B", "C"), inh_predicted=())))
    result = compare_strategies(run, baseline="direct")
    pooled = result["pooled"]["kg"]
    assert pooled["variants"]["not_in_omim"] == 18 and pooled["variants"]["precision"] == 0.25
    assert pooled["inheritance"]["none_stated"] == 6
    precision = next(r for r in result["means"] if r["metric"] == "variant_precision")
    assert precision["values"] == {"kg": 0.25, "direct": 0.5}
    text = strategies_markdown(result)
    assert "## Allelic variants: precision and variants not in OMIM" in text
    assert "| … none stated | 6 | 0 |" in text
    assert "… unsupported, before the repair round" in text and "… contradicted, before the repair round" in text


def test_paired_statistics_holm_and_small_samples(tmp_path):
    from aiomim.compare import _holm, compare_strategies, strategies_markdown

    assert _holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": 0.03, "c": 0.06, "b": 0.06}
    result = compare_strategies(_completion_run(tmp_path), baseline="direct")
    rows = {r["metric"]: r for r in result["versus_baseline"]["kg"]}
    primary = rows["gold_fact_coverage"]
    assert primary["primary"] and "sign_test_p_holm" not in primary
    assert primary["median_difference"] == round(0.55 - 0.6, 4) and primary["ci_unreliable"]
    assert (primary["better"], primary["worse"], primary["ties"]) == (0, 5, 0) and primary["sign_test_p"] == 0.0625
    assert all("sign_test_p_holm" not in r for r in rows.values() if not r["headline"])
    text = strategies_markdown(result)
    assert "Fewer than 20 entries: the bootstrap interval is unreliable" in text
    assert "**(primary)**" in text and "Holm p" in text
    assert result["by_access_paired"]["half or more full text"]["n"] == 5


def test_same_draft_and_same_fact_marks():
    a = {"mim": "1", "sections": [{"heading": "x", "paragraphs": [{"text": "t"}]}], "meta": {"run": "a"}}
    b = {"mim": "1", "sections": [{"heading": "x", "paragraphs": [{"text": "t"}]}], "meta": {"run": "b"}}
    assert same_draft(a, b)
    assert not same_draft(a, {**b, "sections": []})
    e1 = {"gold_text_frozen": {"paragraphs": [{"facts": [{"id": "k.1", "status": "present", "note": "x"},
                                                         {"id": "k.2", "status": "absent"}]}]}}
    e2 = {"gold_text_frozen": {"paragraphs": [{"facts": [{"id": "k.1", "status": "present"},
                                                         {"id": "k.2", "status": "absent"}]}]}}
    assert same_fact_marks(e1, e2)
    e3 = {"gold_text_frozen": {"paragraphs": [{"facts": [{"id": "k.1", "status": "partial"},
                                                         {"id": "k.2", "status": "absent"}]}]}}
    assert not same_fact_marks(e1, e3)
    assert not same_fact_marks({}, {})          # nothing scored is not "the same scores"
