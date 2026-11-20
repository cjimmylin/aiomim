"""Offline tests for experiment A2 (controlled padding of the input): the pure helpers only."""

from __future__ import annotations

import random

from aiomim.padding import (
    added_citations,
    classify,
    complete_sets,
    coverage,
    eligible_pool,
    entry_rng,
    fill_to_target,
    paired,
    plan_padding,
    select_entries,
    supplied_order,
)


def test_select_entries_rule_and_order():
    rows = [
        {"mim": "620000", "n_papers": "4", "n_fulltext": "2"},
        {"mim": "100000", "n_papers": "3", "n_fulltext": "1"},   # under half
        {"mim": "610000", "n_papers": "2", "n_fulltext": "1"},
        {"mim": "605000", "n_papers": "2", "n_fulltext": "2"},   # not complete
        {"mim": "600001", "n_papers": "5", "n_fulltext": "3"},
    ]
    assert select_entries(rows, {"620000", "100000", "610000", "600001"}, 12) == ["600001", "610000", "620000"]
    assert select_entries(rows, {"620000", "100000", "610000", "600001"}, 2) == ["600001", "610000"]


def test_eligible_pool_excludes_own_shared_gene_named_and_long():
    pool = {
        "1": {"chars": 1000, "entry_genes": [["ABC"]], "mentions": set()},      # own
        "2": {"chars": 1000, "entry_genes": [["XYZ"], ["abc"]], "mentions": set()},  # a citing entry shares the gene
        "3": {"chars": 1000, "entry_genes": [["XYZ"]], "mentions": {"ABC"}},    # names the gene
        "4": {"chars": 999_999, "entry_genes": [["XYZ"]], "mentions": set()},   # too long
        "5": {"chars": 1000, "entry_genes": [[]], "mentions": set()},           # unknown provenance
        "6": {"chars": 1000, "entry_genes": [["XYZ"]], "mentions": set()},
    }
    keep, why = eligible_pool(pool, ["1"], ["ABC"], max_chars=180_000)
    assert keep == ["6"]
    assert why == {"own": 1, "shares_gene": 1, "names_gene": 1, "unknown_gene": 1, "too_long": 1}


def test_fill_to_target_nearest_prefix():
    assert fill_to_target(0, [100, 100, 100], 250) == 2       # 200 is as near as 300; stop before overshooting more
    assert fill_to_target(0, [100, 100, 100], 260) == 3       # 300 is nearer than 200
    assert fill_to_target(500, [100], 400) == 0              # already above the target
    assert fill_to_target(0, [10, 10], 1000) == 2             # pool runs out


def test_plan_padding_nested_and_seeded():
    sizes = {str(i): 50_000 + 1000 * i for i in range(60)}
    a = plan_padding(20_000, list(sizes), sizes, entry_rng("606763"))
    b = plan_padding(20_000, list(sizes), sizes, entry_rng("606763"))
    assert a == b
    assert a["P2"][:len(a["P1"])] == a["P1"] and len(a["P1"]) < len(a["P2"])
    tot = lambda lv: 20_000 + sum(sizes[p] for p in a[lv])  # noqa: E731
    assert abs(tot("P1") - 500_000) < 60_000 and abs(tot("P2") - 1_200_000) < 60_000
    assert plan_padding(20_000, list(sizes), sizes, entry_rng("611521"))["order"] != a["order"]


def test_supplied_order_shared_permutation():
    own, p2 = ["o1", "o2"], ["a1", "a2", "a3", "a4"]
    full = supplied_order(own, p2, p2, random.Random("s"))
    part = supplied_order(own, p2, ["a1", "a3"], random.Random("s"))
    assert sorted(full) == sorted(own + p2)
    assert part == [p for p in full if p in {"o1", "o2", "a1", "a3"}]


def test_coverage_counts_half_partial_over_judged():
    assert coverage({"n_judged": 10, "present": 5, "partial": 2}) == 0.6
    assert coverage({"n_judged": 0}) is None
    assert coverage(None) is None


def test_added_citations():
    entry = {
        "intro": {"text": "Intro.", "pmids": ["1"]},
        "sections": [{"name": "clinical_features", "paragraphs": [
            {"text": "Own.", "pmids": ["1"]}, {"text": "Off topic.", "pmids": ["9"]}, {"text": " ", "pmids": ["9"]}]}],
        "allelic_variants": [{"paragraphs": [{"text": "Variant.", "pmids": ["1", "8"]}]}],
        "relationships": [{"pmids": ["8"]}], "clinical_synopsis": [{"pmids": ["1"]}],
    }
    out = added_citations(entry, {"8", "9"})
    assert out["n_paragraphs"] == 4 and out["n_citing_added"] == 2 and out["share_citing_added"] == 0.5
    assert out["added_cited"] == ["8", "9"] and out["added_in_relationships"] == ["8"]
    assert out["added_in_synopsis"] == []


def test_classify_and_complete_sets():
    assert classify(None, None) == "no_draft"
    assert classify({"stopped": "x"}, {}) == "no_draft"
    assert classify({}, {"extraction": {"papers_failed": ["5"]}}) == "incomplete"
    assert classify({}, {"extraction": {"papers_failed": []}}) == "complete"
    status = {"P0": {"direct": {"a": "complete", "b": "complete"}, "kg": {"a": "complete", "b": "complete"}},
              "P1": {"direct": {"a": "complete", "b": "complete"}, "kg": {"a": "incomplete", "b": "complete"}}}
    sets = complete_sets(status, ["a", "b"], ("direct", "kg"))
    assert sets == {"P0": ["a", "b"], "P1": ["b"], "all": ["b"]}


def test_paired_stats():
    row = paired([(0.6, 0.5), (0.5, 0.5), (0.4, 0.5), (0.7, 0.5), (0.8, 0.5)])
    assert row["n"] == 5 and row["better"] == 3 and row["worse"] == 1 and row["ties"] == 1
    assert row["ci95"] is not None
    assert paired([]) is None
