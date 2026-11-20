"""GraphRAG integration (Experiment B): data-reference mapping and output conversion. No network, no model."""

from __future__ import annotations

from aiomim.external import sys_graphrag as g
from aiomim.external.adapt import validate

TABLES = {
    "documents": [{"id": "d1", "human_readable_id": 0, "title": "11111111.txt"},
                  {"id": "d2", "human_readable_id": 1, "title": "22222222.txt"}],
    "text_units": [{"id": "t1", "human_readable_id": 0, "document_id": "d1"},
                   {"id": "t2", "human_readable_id": 1, "document_id": "d1"},
                   {"id": "t3", "human_readable_id": 2, "document_id": "d2"}],
    "entities": [{"id": "e1", "human_readable_id": 0, "title": "GENE A", "text_unit_ids": ["t1"]},
                 {"id": "e2", "human_readable_id": 1, "title": "FAMILY B", "text_unit_ids": ["t3"]},
                 {"id": "e3", "human_readable_id": 2, "title": "X", "text_unit_ids": ["t2", "t3"]}],
    "relationships": [{"id": "r1", "human_readable_id": 0, "source": "GENE A", "target": "FAMILY B",
                       "text_unit_ids": ["t3"]}],
    "communities": [{"id": "c0", "community": 0, "level": 0, "entity_ids": ["e1", "e2"]},
                    {"id": "c1", "community": 1, "level": 1, "entity_ids": ["e1"]}],
    "community_reports": [{"id": "cr0", "community": 0, "level": 0, "title": "Report 0"}],
}
SHOWN = {"sources": {"0", "1", "2"}, "entities": {"0", "1", "2"}, "relationships": {"0"}, "reports": {"0", "1"}}


def test_parse_refs():
    raw, refs = g.parse_refs("A is B [Data: Sources (0, 2); Entities (1, +more)]. C [Data: Reports (3)].")
    assert raw == ["[Data: Sources (0, 2); Entities (1, +more)]", "[Data: Reports (3)]"]
    assert refs == {"sources": ["0", "2"], "entities": ["1"], "reports": ["3"]}
    _, refs = g.parse_refs("x [Data: Entities (5), Relationships (7, 8)]")
    assert refs == {"entities": ["5"], "relationships": ["7", "8"]}
    assert g.parse_refs("no markers here") == ([], {})


def test_map_sources_entities_reports():
    imap = g.IndexMap(TABLES)
    m = g.map_block("x [Data: Sources (2)]", imap, SHOWN)
    assert m["pmids"] == ["22222222"] and m["basis"] == "sources"
    m = g.map_block("x [Data: Entities (2)]", imap, SHOWN)
    assert m["pmids"] == ["11111111", "22222222"] and m["basis"] == "entities_relationships"
    m = g.map_block("x [Data: Relationships (0)]", imap, SHOWN)
    assert m["pmids"] == ["22222222"] and m["basis"] == "entities_relationships"
    m = g.map_block("x [Data: Reports (1)]", imap, SHOWN)  # community 1 -> e1 -> t1 -> d1
    assert m["pmids"] == ["11111111"] and m["basis"] == "reports_only"
    m = g.map_block("x [Data: Reports (0); Sources (0)]", imap, SHOWN)
    assert set(m["pmids"]) == {"11111111", "22222222"} and m["basis"] == "sources"
    assert g.map_block("plain text", imap, SHOWN)["basis"] == "none"


def test_ids_not_shown_are_not_mapped():
    imap = g.IndexMap(TABLES)
    m = g.map_block("x [Data: Sources (2)]", imap, {"sources": {"0"}})
    assert m["pmids"] == [] and m["basis"] == "none" and m["not_shown"] == {"sources": ["2"]}


def test_context_ids():
    ctx = {"sources": [{"id": "3", "text": "..."}], "entities": [{"id": "1"}, {"id": ""}], "reports": []}
    assert g.context_ids(ctx) == {"sources": {"3"}, "entities": {"1"}, "reports": set()}


def test_split_paragraphs_joins_reference_only_paragraph():
    text = "## Head\n\nA triad:\n1. one\n2. two\n\n[Data: Sources (0); Entities (1)]\n\nNext para [Data: Sources (1)]."
    assert g.split_paragraphs(text) == ["## Head", "A triad:\n1. one\n2. two\n\n[Data: Sources (0); Entities (1)]",
                                        "Next para [Data: Sources (1)]."]
    assert "".join(g.split_paragraphs("x\n\ny")) == "xy"


def test_answers_to_blocks_and_validate():
    imap = g.IndexMap(TABLES)
    answers = [{"key": "description", "section": "Description",
                "response": "## Overview\n\nThe disorder [Data: Sources (0)].\n\nMore text [Data: Reports (0)].\n",
                "context": {"sources": [{"id": "0"}], "reports": [{"id": "0"}]}},
               {"key": "inheritance", "section": "Inheritance", "response": "", "context": {}}]
    blocks, records = g.answers_to_blocks(answers, imap)
    assert [b["text"] for b in blocks] == ["## Overview", "The disorder [Data: Sources (0)].",
                                           "More text [Data: Reports (0)]."]
    assert [r["basis"] for r in records] == ["none", "sources", "reports_only"]
    assert blocks[1]["pmids"] == ["11111111"] and blocks[1]["citations"] == ["[Data: Sources (0)]"]
    assert set(blocks[2]["pmids"]) == {"11111111", "22222222"}
    shares = g.mapping_shares(records)
    assert shares["chars"] == sum(len(b["text"]) for b in blocks)
    assert shares["chars_reports_only"] == len(blocks[2]["text"])
    out = validate({"system": "graphrag", "mim": "100100", "stopped": None, "blocks": blocks, "meta": {}},
                   supplied={"11111111", "22222222"})
    assert len(out["blocks"]) == 3


def test_configure_changes_only_what_is_allowed():
    generated = {
        "completion_models": {"default_completion_model": {"model_provider": "openai", "model": "gpt-4.1",
                                                           "auth_method": "api_key",
                                                           "api_key": "${GRAPHRAG_API_KEY}",
                                                           "retry": {"type": "exponential_backoff"}}},
        "embedding_models": {"default_embedding_model": {"model_provider": "openai",
                                                         "model": "text-embedding-3-large",
                                                         "api_key": "${GRAPHRAG_API_KEY}",
                                                         "retry": {"type": "exponential_backoff"}}},
        "chunking": {"size": 1200, "overlap": 100},
        "extract_graph": {"completion_model_id": "default_completion_model", "prompt": "prompts/extract_graph.txt",
                          "entity_types": ["organization", "person", "geo", "event"], "max_gleanings": 1},
        "summarize_descriptions": {"completion_model_id": "default_completion_model"},
        "community_reports": {"completion_model_id": "default_completion_model"},
        "local_search": {"completion_model_id": "default_completion_model"},
        "global_search": {"completion_model_id": "default_completion_model"},
    }
    s, changes = g.configure(generated)
    assert s["chunking"] == generated["chunking"]
    assert s["extract_graph"]["entity_types"] == ["organization", "person", "geo", "event"]
    assert s["extract_graph"]["max_gleanings"] == 1 and s["extract_graph"]["prompt"] == "prompts/extract_graph.txt"
    assert s["concurrent_requests"] == 3
    for model in s["completion_models"].values():
        assert model["model"] == "claude-opus-5-5" and model["api_base"] == "${GRAPHRAG_API_BASE}"
        assert model["call_args"]["timeout"] >= 900
    steps = {m["call_args"]["extra_headers"]["X-Aiomim-Tag"] for m in s["completion_models"].values()}
    assert "${AIOMIM_TAG}/extract_graph" in steps
    assert all({"setting", "default", "value", "reason"} <= set(c) for c in changes)
    assert generated["completion_models"]["default_completion_model"]["model"] == "gpt-4.1"  # not mutated


def test_step_of():
    assert g.step_of({"tag": "graphrag/1/extract_graph", "rendering": "transcript", "prompt_chars": 9000,
                      "endpoint": "/v1/chat/completions"}) == "extract_graph_gleaning"
    assert g.step_of({"tag": "graphrag/1/extract_graph", "rendering": "single", "prompt_chars": 9000,
                      "endpoint": "/v1/chat/completions"}) == "extract_graph"
    assert g.step_of({"tag": "graphrag/1/community_reports", "rendering": "single",
                      "prompt_chars": len(g.CONNECTIVITY_TEST) + len("You are a helpful assistant."),
                      "endpoint": "/v1/chat/completions"}) == "connectivity_test"
    assert g.step_of({"tag": "graphrag/1/embeddings", "endpoint": "/v1/embeddings"}) == "embeddings"
