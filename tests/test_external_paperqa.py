"""Offline tests of the PaperQA2 integration's citation mapping and output conversion (no network, no model)."""

from __future__ import annotations

from aiomim.external import adapt
from aiomim.external.paperqa_runner import docname_for
from aiomim.external.sys_paperqa import answer_blocks, convert, map_paragraph

NAMES = {"Rutten2024-38430071": "38430071", "Rendu2019-31705625": "31705625"}


def test_docname_for():
    assert docname_for("Rutten JW", "2024", "38430071") == "Rutten2024-38430071"
    assert docname_for("Van Noolen L", "2019", "1234567") == "VanNoolen2019-1234567"
    assert docname_for("de Bot ST", "2020", "22222222") == "DeBot2020-22222222"
    assert docname_for("", "", "33333333") == "Paper-33333333"


def test_map_paragraph_single_and_multiple():
    text = ("Patients present in mid-adulthood (Rutten2024-38430071 chunk 1). Lesions were cavitating "
            "(Rendu2019-31705625 chunk 2, Rutten2024-38430071 chunk 1).")
    pmids, raw = map_paragraph(text, NAMES)
    assert pmids == ["38430071", "31705625"]
    assert raw == ["(Rutten2024-38430071 chunk 1)", "(Rendu2019-31705625 chunk 2, Rutten2024-38430071 chunk 1)"]


def test_map_paragraph_ignores_other_parentheticals_and_prefix_clashes():
    names = {"Smith2020-1111111": "1111111", "Smith2020-11111112": "11111112"}
    text = "Onset is early (age 3 years) (Smith2020-11111112 chunk 4); see also (Smith2020-1111111x)."
    pmids, raw = map_paragraph(text, names)
    assert pmids == ["11111112"]
    assert raw == ["(Smith2020-11111112 chunk 4)"]


def test_answer_blocks_split_and_unedited():
    answer = "First paragraph (Rendu2019-31705625 chunk 1).\n\n  \nI cannot answer this part.\n"
    blocks = answer_blocks("Inheritance", answer, NAMES)
    assert [b["text"] for b in blocks] == ["First paragraph (Rendu2019-31705625 chunk 1).", "I cannot answer this part."]
    assert blocks[0]["pmids"] == ["31705625"] and blocks[1]["pmids"] == [] and blocks[1]["citations"] == []
    assert all(b["section"] == "Inheritance" for b in blocks)


def test_convert_maps_only_supplied_and_validates():
    result = {
        "papers": [{"pmid": "38430071", "docname": "Rutten2024-38430071"},
                   {"pmid": "31705625", "docname": "Rendu2019-31705625"},
                   {"pmid": "99999999", "docname": "Ghost2000-99999999"}],
        "answers": [
            {"key": "description", "section": "Description",
             "answer": "A disorder (Rutten2024-38430071 chunk 1, Ghost2000-99999999 chunk 1).", "contexts": [{}]},
            {"key": "inheritance", "section": "Inheritance", "answer": "", "contexts": []},
        ],
    }
    blocks, notes = convert("621313", result, {"38430071", "31705625"})
    assert len(blocks) == 1 and blocks[0]["pmids"] == ["38430071"]
    assert notes["questions"][1]["blocks"] == 0
    out = adapt.validate({"system": "paperqa", "mim": "621313", "blocks": blocks, "stopped": None,
                          "meta": {"settings_changed": []}}, supplied={"38430071", "31705625"})
    assert out["blocks"][0]["citations"] == ["(Rutten2024-38430071 chunk 1, Ghost2000-99999999 chunk 1)"]


def test_bare_context_keys_map_through_contexts():
    text = "The sources disagree: c.457G>A according to pqac-7c33d06c, c.670dupA according to pqac-8a0c347c."
    pmids, raw = map_paragraph(text, NAMES, {"pqac-7c33d06c": "31705625", "pqac-8a0c347c": "31705625"})
    assert pmids == ["31705625"] and raw == ["pqac-7c33d06c", "pqac-8a0c347c"]
    # an unknown (hallucinated) key maps to nothing
    assert map_paragraph("x pqac-deadbeef y", NAMES, {}) == ([], [])


def test_convert_uses_session_contexts_for_bare_keys():
    result = {"papers": [{"pmid": "31705625", "docname": "Rendu2019-31705625"}],
              "answers": [{"key": "inheritance", "section": "Inheritance", "answer": "Mother carries it pqac-7c33d06c.",
                           "contexts": [{"id": "pqac-7c33d06c", "docname": "Rendu2019-31705625"}]}]}
    blocks, notes = convert("621313", result, {"31705625"})
    assert blocks[0]["pmids"] == ["31705625"] and notes["questions"][0]["bare_keys"] == 1
