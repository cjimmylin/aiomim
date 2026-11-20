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


# --------------------------------------------------------------------------- #
# Opt-in pooling of long embedding inputs (aiomim.external.embed)
# --------------------------------------------------------------------------- #

import re as _re

from aiomim.external import embed as _embed


def _ws_encode(text):
    """Whitespace tokenizer: offsets of each word."""
    return [m.span() for m in _re.finditer(r"\S+", text)]


class _FakeModel:
    """Vector = (number of words, 1.0); records each embed call."""

    def __init__(self):
        self.calls = []

    def embed(self, texts, batch_size=64):
        self.calls.append(list(texts))
        return [[float(len(t.split())), 1.0] for t in texts]


def _fake_embedder(mode):
    e = _embed.LocalEmbedder(cache=__import__("pathlib").Path("/nonexistent"), long_inputs=mode)
    e._model = _FakeModel()
    e._encode_fn, e._max_tokens = _ws_encode, 4
    return e


def test_split_windows_consecutive_and_fitting():
    text = "a b c d e f g h i j"
    assert _embed.split_windows(text, _ws_encode, 4) == ["a b c d", "e f g h", "i j"]
    assert _embed.split_windows("a b c", _ws_encode, 4) == ["a b c"]
    assert _embed.split_windows("a b c d", _ws_encode, 4) == ["a b c d"]


def test_mean_normalised():
    v = _embed.mean_normalised([[1.0, 0.0], [0.0, 1.0]])
    assert abs(v[0] - 2 ** -0.5) < 1e-12 and abs(sum(x * x for x in v) - 1) < 1e-12


def test_default_mode_unchanged_and_rejects_bad_mode():
    e = _fake_embedder("truncate")
    assert e.embed(["a b c d e f"]) == [[6.0, 1.0]]          # passed through whole, no windowing
    assert e.name == _embed.EMBED_MODEL
    import pytest

    with pytest.raises(ValueError):
        _embed.LocalEmbedder(long_inputs="other")


def test_pool_mode_short_inputs_take_the_default_call():
    d, p = _fake_embedder("truncate"), _fake_embedder("pool")
    short = ["a b", "c d e"]
    assert p.embed(short) == d.embed(short)
    assert p._model.calls == [short]                          # one call, same batch, same order


def test_pool_mode_long_input_windows_averaged():
    p = _fake_embedder("pool")
    out = p.embed(["x y", "a b c d e f g h i j"])
    assert out[0] == [2.0, 1.0]                               # short input untouched
    assert p._model.calls[1] == ["a b c d", "e f g h", "i j"]
    mean = [(4 + 4 + 2) / 3, 1.0]
    norm = sum(x * x for x in mean) ** 0.5
    assert out[1] == [x / norm for x in mean]
    assert p.name.startswith(_embed.EMBED_MODEL) and p.name != _embed.EMBED_MODEL
