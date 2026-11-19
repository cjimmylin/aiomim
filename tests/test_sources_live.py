"""Live checks against NCBI, Europe PMC, HPO and HGNC. Deselect with -m 'not network'."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.network


def test_build_gold_500001():
    from aiomim.gold import build_gold

    g = build_gold("500001")
    assert g.prefix == "#" and g.entry_type == "phenotype"
    assert g.title == "LEBER OPTIC ATROPHY AND DYSTONIA"
    assert len(g.cited_pmids) == 8
    assert len(g.hpo_annotations) >= 15
    assert "MT" in g.inheritance
    assert len(g.gold_paragraphs) >= 1
    assert any("17562939" in p.pmids for p in g.gold_paragraphs)
    assert all(a.label for a in g.hpo_annotations)


def test_load_papers_content_levels():
    from aiomim.sources.fulltext import load_papers

    # 35217561 is in the PMC open-access subset; 17562939 has only an abstract.
    papers = load_papers(["35217561", "17562939"])
    assert [p.pmid for p in papers] == ["35217561", "17562939"]
    oa, closed = papers
    assert oa.content_level == "fulltext" and oa.fulltext_source in ("europepmc", "ncbi_bioc")
    assert "m.3685T" in oa.fulltext
    assert closed.content_level == "abstract" and closed.fulltext is None


def test_hpo_exact_live():
    from aiomim.sources.hpo import get_hpo

    assert get_hpo().exact("Optic atrophy") == "HP:0000648"


def test_hgnc_mito_symbol_live():
    from aiomim.sources.hgnc import normalize_symbol

    assert normalize_symbol("MTND1") == "MT-ND1"
