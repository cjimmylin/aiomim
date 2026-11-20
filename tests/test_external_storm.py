"""Offline tests of the STORM integration's citation mapping and output conversion (no network, no model)."""

from __future__ import annotations

from aiomim.external import adapt
from aiomim.external.storm_runner import PUBMED_URL, build_corpus_csv
from aiomim.external.sys_storm import (article_blocks, index_to_pmid, ledger_summary, map_citations,
                                       parse_article, unmapped_markers)

SUPPLIED = {"38430071", "31705625"}
REFERENCE = {"url_to_unified_index": {PUBMED_URL.format(pmid="38430071"): 1,
                                      PUBMED_URL.format(pmid="31705625"): 2,
                                      "https://pubmed.ncbi.nlm.nih.gov/99999999/": 3,
                                      "https://example.org/38430071": 4},
             "url_to_info": {}}

ARTICLE = """# summary

Brain small vessel disease 4 is a disorder of adults.[1][2] It is rare.

# Clinical features

## Neurological signs

Patients present with stroke in mid-adulthood.[2]
Imaging shows white matter lesions.[1][3][4]

# Inheritance

Inheritance is autosomal dominant."""


def test_index_to_pmid_only_supplied_pubmed_urls():
    assert index_to_pmid(REFERENCE, SUPPLIED) == {1: "38430071", 2: "31705625"}


def test_map_citations_keeps_raw_markers_and_order():
    pmids, raw = map_citations("A.[2] B.[1][2] C.[3]", index_to_pmid(REFERENCE, SUPPLIED))
    assert pmids == ["31705625", "38430071"]
    assert raw == ["[2]", "[1]", "[2]", "[3]"]


def test_parse_article_sections_and_paragraphs_unedited():
    blocks = parse_article(ARTICLE)
    assert [b["section"] for b in blocks] == ["summary", "Neurological signs", "Neurological signs", "Inheritance"]
    assert blocks[0]["text"] == "Brain small vessel disease 4 is a disorder of adults.[1][2] It is rare."
    assert blocks[2]["text"] == "Imaging shows white matter lesions.[1][3][4]"
    assert all(not b["text"].startswith("#") for b in blocks)


def test_article_blocks_and_unmapped():
    blocks = article_blocks(ARTICLE, REFERENCE, SUPPLIED)
    assert blocks[0]["pmids"] == ["38430071", "31705625"] and blocks[0]["citations"] == ["[1]", "[2]"]
    assert blocks[2]["pmids"] == ["38430071"] and blocks[2]["citations"] == ["[1]", "[3]", "[4]"]
    assert blocks[3]["pmids"] == [] and blocks[3]["citations"] == []
    assert unmapped_markers(blocks, REFERENCE, SUPPLIED) == ["[3]", "[4]"]
    # the blocks are valid intermediate format and convert with text unedited
    out = adapt.validate({"system": "storm", "mim": "621313", "stopped": None, "blocks": blocks,
                          "meta": {"settings_changed": []}}, supplied=SUPPLIED)
    entry = adapt.to_entry(out)
    texts = [p.text for s in entry.sections for p in s.paragraphs]
    assert texts == [b["text"] for b in blocks]


def test_ledger_summary_by_stage():
    rows = [
        {"endpoint": "/v1/chat/completions", "tag": "storm/1/research", "status": 200, "cached": False,
         "model_calls": 1, "input_tokens": 100, "output_tokens": 10, "cost_usd": 0.01, "call_seconds": 2.0},
        {"endpoint": "/v1/chat/completions", "tag": "storm/1/research", "status": 200, "cached": True,
         "model_calls": 0, "input_tokens": 100, "output_tokens": 10, "cost_usd": 0.01},
        {"endpoint": "/v1/chat/completions", "tag": "storm/1/article", "status": 200, "cached": False,
         "model_calls": 1, "safety_stop": True, "input_tokens": 50, "output_tokens": 0, "cost_usd": 0.005},
        {"endpoint": "/v1/chat/completions", "tag": "storm/1/polish", "status": 400},
        {"endpoint": "/v1/chat/completions", "tag": "storm/10/research", "status": 200, "cached": False},
    ]
    s = ledger_summary(rows, "storm/1")
    assert s["total"]["fresh_calls"] == 2 and s["total"]["cached"] == 1 and s["total"]["refused"] == 1
    assert s["total"]["stops"] == 1 and s["total"]["input_tokens"] == 150
    assert s["stages"]["research"]["fresh_calls"] == 1 and s["stages"]["article"]["stops"] == 1


def test_build_corpus_csv(tmp_path):
    import csv

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "38430071.txt").write_text("Rutten JW et al. 2024. Ref line.\n\nTITLE: T\nABSTRACT: A, b.\n",
                                         encoding="utf-8")
    with (corpus / "papers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pmid", "title", "first_author", "year", "journal", "access_level", "characters", "label",
                    "file"])
        w.writerow(["38430071", "A title, with comma", "Rutten JW", "2024", "J", "abstract", "40", "R",
                    "38430071.txt"])
    out = tmp_path / "c.csv"
    assert build_corpus_csv(corpus, out) == ["38430071"]
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/38430071/"
    assert rows[0]["content"].startswith("Rutten JW et al. 2024. Ref line.\n\nTITLE: T")
    assert rows[0]["description"] == "Rutten JW et al. 2024. Ref line."
    assert rows[0]["title"] == "A title, with comma"
