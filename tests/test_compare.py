"""Offline tests for the paired strategy comparison and the shareable export."""

from __future__ import annotations

import json

from aiomim.compare import _sign_test, access_group, compare_run, comparison_markdown
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
    assert "[entry.kg.md](100100/entry.kg.md)" in (out / "README.md").read_text()


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
