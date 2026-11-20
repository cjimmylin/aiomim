"""The OpenAI second-model-family kit (aiomim.openai_study): no OpenAI call anywhere.

Request formatting, output parsing (fixtures written from the Batch and Responses API
documentation's examples), the cache round trip through `Pending`, retry-once, stops,
`LLM.map`, the cost cap, statistics, validation and redaction, and an end-to-end dry run
with the fake provider when this checkout has the original runs' data.
"""

from __future__ import annotations

import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from aiomim.config import DEFAULT_EFFORT, STAGES, Settings
from aiomim.llm import EMPTY_REPLY, LLM, SAFETY_STOP, LLMError, LLMRefusal, schema_for
from aiomim.openai_study import backend as bk
from aiomim.openai_study.config import Study, StudyPaths, cost_usd, read_json
from aiomim.openai_study.errors import ForbiddenCall, NetworkBlocked, Pending
from aiomim.openai_study.openai_format import (
    parse_line,
    request_line,
    request_parts,
    strict_problems,
)

REPO = Path(__file__).resolve().parents[1]
STUDY_JSON = REPO / "studies" / "openai_second_model" / "study.json"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _study(**changes) -> Study:
    data = json.loads(STUDY_JSON.read_text())
    data.update(changes)
    return Study(data)


def _settings(tmp_path: Path, model: str = "gpt-test") -> Settings:
    return Settings(home=tmp_path / "home", runs=tmp_path / "runs", claude_bin="claude",
                    models={s: model for s in STAGES}, efforts=dict(DEFAULT_EFFORT), llm_concurrency=4)


def _llm(tmp_path: Path, recorder: bk.Recorder, allowed=("judge:mark", "synthesize:direct", "judge:avail")):
    llm = LLM(_settings(tmp_path))
    llm.backend = bk.StudyBackend(settings=llm.settings, cache=llm.cache, recorder=recorder, task_id="T:1",
                                  allowed=set(allowed))
    return llm


def _ok_line(cid: str, data, usage=None) -> dict:
    return {"id": "batch_req_1", "custom_id": cid,
            "response": {"status_code": 200, "request_id": "req_1",
                         "body": {"id": "resp_1", "object": "response", "status": "completed",
                                  "output": [{"type": "reasoning", "id": "rs_1", "summary": []},
                                             {"type": "message", "role": "assistant", "status": "completed",
                                              "content": [{"type": "output_text", "text": json.dumps(data)}]}],
                                  "usage": usage or {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 200},
                                                     "output_tokens": 300,
                                                     "output_tokens_details": {"reasoning_tokens": 100},
                                                     "total_tokens": 1300}}},
            "error": None}


def _ingest(llm: LLM, recorder: bk.Recorder, line: dict, study: Study | None = None) -> str:
    """What `waves.ingest` does for one line: parse it and store it under the request's key."""
    from aiomim.openai_study.waves import _store_reply

    study = study or _study()
    entry = recorder.entries[line["custom_id"]]
    return _store_reply(llm.cache, study, {"batch_id": "batch_x"}, entry, parse_line(line), 1, 3,
                        Path(llm.cache.root).parent / "logs")


class Marks(BaseModel):
    marks: list[dict]


# --------------------------------------------------------------------------- #
# Request format
# --------------------------------------------------------------------------- #


def test_project_reply_schemas_are_strict_compatible():
    from aiomim.extract import XChoices, XExtraction
    from aiomim.facts import XMarks
    from aiomim.gaps import XGapVerdicts
    from aiomim.synthesize import DEntry, XEntry

    for model in (XMarks, XGapVerdicts, DEntry, XEntry, XExtraction, XChoices):
        assert strict_problems(schema_for(model)) == [], model.__name__


def test_strict_check_flags_open_objects_and_unsupported_keywords():
    open_obj = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    assert strict_problems(open_obj)
    optional = {"type": "object", "properties": {"a": {"type": "string"}}, "required": [],
                "additionalProperties": False}
    assert strict_problems(optional)
    odd = {"type": "object", "properties": {"a": {"type": "string", "minLength": 2}}, "required": ["a"],
           "additionalProperties": False}
    assert any("minLength" in p for p in strict_problems(odd))


def test_request_line_carries_the_project_schema_unchanged():
    from aiomim.facts import MARK_SYSTEM, XMarks

    schema = schema_for(XMarks)
    line = request_line("r1-abc", model="gpt-6.2-sol", effort="medium", system=MARK_SYSTEM, prompt="P",
                        schema=schema, name="judge:mark", strict=True)
    assert line["method"] == "POST" and line["url"] == "/v1/responses"
    body = line["body"]
    assert body["model"] == "gpt-6.2-sol" and body["reasoning"] == {"effort": "medium"}
    assert body["input"] == [{"role": "system", "content": MARK_SYSTEM}, {"role": "user", "content": "P"}]
    fmt = body["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["schema"] is schema
    assert fmt["name"] == "judge_mark" and body["store"] is False
    assert request_parts(line) == (MARK_SYSTEM, "P", schema)


def test_effort_mapping_and_study_checks():
    s = _study()
    assert [s.openai_effort(e) for e in ("low", "medium", "high")] == ["low", "medium", "high"]
    from aiomim.openai_study.errors import StudyError

    with pytest.raises(StudyError):
        _study(model="gpt-4o")
    with pytest.raises(StudyError):
        _study(effort_map={"low": "none", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "max"})
    assert _study(model="gpt-6.2-sol").cap_usd == 120


def test_cost_from_price_table():
    price = {"input": 4.0, "cached_input": 0.2, "output": 20.0}
    assert cost_usd(price, 1_000_000, 0, 0) == pytest.approx(4.0)
    assert cost_usd(price, 1_000_000, 500_000, 100_000) == pytest.approx(2.0 + 0.1 + 2.0)


# --------------------------------------------------------------------------- #
# Output parsing (the documentation's line formats)
# --------------------------------------------------------------------------- #


def test_parse_success_line():
    r = parse_line(_ok_line("task-001", {"marks": []}))
    assert r.kind == "ok" and r.data == {"marks": []} and not r.stopped
    assert r.usage == {"input_tokens": 1000, "cached_tokens": 200, "output_tokens": 300, "reasoning_tokens": 100}


def test_parse_refusal_line():
    line = _ok_line("c", {})
    line["response"]["body"]["output"][1]["content"] = [{"type": "refusal", "refusal": "I can't help with that."}]
    r = parse_line(line)
    assert r.kind == "refusal" and r.stopped and r.data is None


def test_parse_incomplete_and_content_filter_lines():
    line = _ok_line("c", {"a": 1})
    body = line["response"]["body"]
    body["status"] = "incomplete"
    body["incomplete_details"] = {"reason": "max_output_tokens"}
    body["output"][1]["content"] = [{"type": "output_text", "text": '{"marks": ['}]
    r = parse_line(line)
    assert r.kind == "incomplete" and not r.stopped and r.reason == "max_output_tokens"
    body["incomplete_details"] = {"reason": "content_filter"}
    r = parse_line(line)
    assert r.kind == "content_filter" and r.stopped


def test_parse_invalid_json_and_missing_text():
    line = _ok_line("c", {})
    line["response"]["body"]["output"][1]["content"] = [{"type": "output_text", "text": "not json"}]
    assert parse_line(line).kind == "invalid"
    line["response"]["body"]["output"] = [{"type": "reasoning", "summary": []}]
    assert parse_line(line).kind == "invalid"


def test_parse_error_file_lines():
    expired = {"id": "batch_req_2", "custom_id": "task-002", "response": None,
               "error": {"code": "batch_expired",
                         "message": "This request could not be executed before the completion window expired."}}
    r = parse_line(json.dumps(expired))
    assert r.kind == "error" and r.transient and r.error_code == "batch_expired"
    rejected = {"id": "batch_req_3", "custom_id": "task-003",
                "response": {"status_code": 400, "request_id": "req_3",
                             "body": {"error": {"message": "Invalid schema", "type": "invalid_request_error",
                                                "code": "invalid_json_schema"}}}, "error": None}
    r = parse_line(rejected)
    assert r.kind == "error" and not r.transient and r.status_code == 400
    server = {"custom_id": "t4", "response": {"status_code": 500, "body": {"error": {"message": "x"}}}}
    assert parse_line(server).transient


# --------------------------------------------------------------------------- #
# The cache round trip
# --------------------------------------------------------------------------- #


def test_pending_is_not_an_exception():
    assert not issubclass(Pending, Exception)
    assert not issubclass(ForbiddenCall, Exception) and not issubclass(NetworkBlocked, Exception)


def test_miss_records_request_and_ingested_reply_lets_the_next_wave_proceed(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks

    rec = bk.Recorder(_study(), tmp_path / "w.jsonl")
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "prompt one", XMarks)
    rec.close()
    (cid, entry), = rec.entries.items()
    assert entry["attempt"] == 1 and entry["label"] == "judge:mark" and entry["effort"] == "medium"
    line = json.loads((tmp_path / "w.jsonl").read_text().splitlines()[0])
    assert line["custom_id"] == cid and line["body"]["reasoning"]["effort"] == "medium"
    assert _ingest(llm, rec, _ok_line(cid, {"marks": [{"n": 1, "status": "present", "note": ""}]})) == "ok"
    # The next wave: a fresh wrapper over the same cache reads the reply.
    rec2 = bk.Recorder(_study(), None)
    reply = _llm(tmp_path, rec2).call("judge", MARK_SYSTEM, "prompt one", XMarks)
    assert reply.marks[0].status == "present" and not rec2.entries
    hit = llm.cache.get_json(entry["storage_key"])
    assert hit["meta"]["provider"] == "openai" and hit["meta"]["safety_stops"] == 0
    assert hit["meta"]["cost_usd"] == pytest.approx((800 * 4 + 200 * 0.2 + 300 * 20) / 1e6)


def test_map_records_every_request_of_the_wave(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.map("judge", MARK_SYSTEM, [f"prompt {i}" for i in range(9)], XMarks)
    assert len(rec.entries) == 9


def test_pending_passes_through_broad_exception_handlers(tmp_path):
    """`evaluate.eval_variants` catches Exception around its judge call; Pending must still stop the task."""
    from aiomim.evaluate import MATCH_SYSTEM, XPairs

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec, allowed=("judge:variant_match",))

    def project_style():
        try:
            return llm.call("judge", MATCH_SYSTEM, "List A\nA1. x\n\nList B\nB1. y", XPairs)
        except Exception:  # noqa: BLE001 - what the project's code does
            return None

    with pytest.raises(Pending):
        project_style()


def test_retry_once_then_the_project_gives_up(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid1 = next(iter(rec.entries))
    bad = _ok_line(cid1, {})
    bad["response"]["body"]["output"][1]["content"] = [{"type": "output_text", "text": "{oops"}]
    assert _ingest(llm, rec, bad) == "invalid"
    with pytest.raises(Pending):                 # the re-ask, under a distinct key
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid2 = [c for c in rec.entries if c != cid1][0]
    e1, e2 = rec.entries[cid1], rec.entries[cid2]
    assert e2["attempt"] == 2 and e2["storage_key"] == bk.retry_key(e1["cache_key"]) != e1["storage_key"]
    assert _ingest(llm, rec, {**bad, "custom_id": cid2}) == "invalid"
    with pytest.raises(LLMError):                # two bad replies: the project's own outcome
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    assert len(rec.entries) == 2


def test_retry_that_succeeds_is_used(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid1 = next(iter(rec.entries))
    _ingest(llm, rec, _ok_line(cid1, {"wrong": True}))      # parses, but fails the project's validation
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid2 = [c for c in rec.entries if c != cid1][0]
    _ingest(llm, rec, _ok_line(cid2, {"marks": []}))
    assert llm.call("judge", MARK_SYSTEM, "p", XMarks).marks == []


def test_empty_writer_reply_twice_is_the_projects_empty_reply_outcome(tmp_path):
    from aiomim.synthesize import DIRECT_SYSTEM, DEntry, has_content

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    empty = {"intro": {"text": "", "pmids": []}, "sections": [], "relationships": [], "allelic_variants": [],
             "clinical_synopsis": []}
    for _ in range(2):
        with pytest.raises(Pending):
            llm.call("synthesize", DIRECT_SYSTEM, "papers", DEntry, accept=has_content)
        cid = list(rec.entries)[-1]
        _ingest(llm, rec, _ok_line(cid, empty))
    with pytest.raises(LLMRefusal, match=EMPTY_REPLY):
        llm.call("synthesize", DIRECT_SYSTEM, "papers", DEntry, accept=has_content)


def test_a_stop_is_recorded_and_never_asked_again(tmp_path):
    from aiomim.facts import MARK_SYSTEM, RETRY_NOTE, XMarks, map_covering

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid = next(iter(rec.entries))
    refusal = _ok_line(cid, {})
    refusal["response"]["body"]["output"][1]["content"] = [{"type": "refusal", "refusal": "no"}]
    assert _ingest(llm, rec, refusal) == "stop"
    with pytest.raises(LLMRefusal, match=SAFETY_STOP):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    # The judge procedure re-asks a failed reply with a note appended: after a stop that is not sent.
    out = map_covering(llm, MARK_SYSTEM, ["p"], XMarks, [3], lambda r: r.marks)
    assert out[0][0] == {} and out[0][1] == 2
    assert len(rec.entries) == 1
    assert llm.backend.stops_not_sent == 1
    assert bk.split_retry_note("p" + RETRY_NOTE.format(n=3)) == "p"


def test_forbidden_calls_are_never_recorded(tmp_path):
    from aiomim.facts import SPLIT_SYSTEM, XSplit
    from aiomim.llm import ClaudeCode  # noqa: F401

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(ForbiddenCall):
        llm.call("judge", SPLIT_SYSTEM, "<reference>x</reference>", XSplit)
    with pytest.raises(ForbiddenCall):
        llm.backend.complete(system="x", prompt="y", schema={}, model="m", effort="low", tools=("Read",))
    assert not rec.entries


def test_requests_shared_by_tasks_are_sent_once(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks

    rec = bk.Recorder(_study(), None)
    for task in ("A:1", "B:2"):
        llm = _llm(tmp_path, rec)
        llm.backend.task_id = task
        with pytest.raises(Pending):
            llm.call("judge", MARK_SYSTEM, "same prompt", XMarks)
    (entry,) = rec.entries.values()
    assert entry["tasks"] == ["A:1", "B:2"]


# --------------------------------------------------------------------------- #
# Offline environment
# --------------------------------------------------------------------------- #


def test_network_guard_blocks_sockets():
    from aiomim.openai_study.offline import network_blocked

    with network_blocked(), pytest.raises(NetworkBlocked):
        socket.create_connection(("example.org", 443), timeout=1)
    assert socket.create_connection is not None


def test_hgnc_emulation_matches_the_fetch_endpoint():
    from aiomim.openai_study.offline import HgncTable

    table = HgncTable([{"symbol": "MAPT", "hgnc_id": "HGNC:6893", "alias_symbol": ["tau", "TAU", "MSTD"],
                        "status": "Approved"},
                       {"symbol": "GJA1", "hgnc_id": "HGNC:4274", "alias_symbol": ["CX43"], "prev_symbol": ["ODDD"],
                        "status": "Approved"}])
    assert [d["symbol"] for d in table.fetch("alias_symbol", "Tau")] == ["MAPT"]
    assert [d["symbol"] for d in table.fetch("symbol", "gja1")] == ["GJA1"]
    assert table.fetch("prev_symbol", "GJA1") == []
    body = json.loads(table.response_text("https://rest.genenames.org/fetch/prev_symbol/ODDD"))
    assert body["response"]["numFound"] == 1 and body["response"]["docs"][0]["symbol"] == "GJA1"


def test_offline_http_replays_cache_emulates_hgnc_and_blocks_the_rest(tmp_path):
    from aiomim.http import Http
    from aiomim.openai_study.offline import HgncTable, make_offline_http

    http = make_offline_http(tmp_path / "http", HgncTable([{"symbol": "GJA1", "status": "Approved"}]))
    url = "https://rest.genenames.org/fetch/symbol/TBX22"
    http.cache.put_text(Http.cache_key(url), '{"cached": true}')
    assert http.get_json(url) == {"cached": True}
    assert http.get_json("https://rest.genenames.org/fetch/symbol/GJA1")["response"]["numFound"] == 1
    with pytest.raises(NetworkBlocked):
        http.get_text("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", {"id": "1"})


# --------------------------------------------------------------------------- #
# Waves: cost cap, ingest of error lines
# --------------------------------------------------------------------------- #


class _NoProvider:
    def upload(self, path):  # pragma: no cover - must not be reached
        raise AssertionError("upload called although the cap forbids it")

    create = upload


def test_submit_refuses_a_batch_past_the_cap(tmp_path):
    from aiomim.openai_study.config import write_json
    from aiomim.openai_study.waves import submit

    paths = StudyPaths(tmp_path)
    data = json.loads(STUDY_JSON.read_text())
    data["cost_cap_usd"]["gpt-6.2-astra"] = 1
    write_json(paths.study_json, data)
    (paths.requests).mkdir(parents=True)
    (paths.requests / "wave_001_p01.jsonl").write_text("{}\n")
    write_json(paths.waves / "wave_001.json", {"wave": 1, "parts": [
        {"part": 1, "file": "private/requests/wave_001_p01.jsonl", "requests_in_file": 1, "bytes": 3,
         "requests": 1, "est_input_tokens": 1_000_000, "est_output_tokens": 0, "est_cost_usd": 4.0}]})
    out = submit(paths, Study.load(paths), _NoProvider())
    assert out["submitted"] == [] and "cost cap" in out["blocked"]


def test_transient_errors_are_asked_again_then_recorded_as_failed(tmp_path):
    from aiomim.facts import MARK_SYSTEM, XMarks
    from aiomim.openai_study.waves import _store_reply

    rec = bk.Recorder(_study(), None)
    llm = _llm(tmp_path, rec)
    with pytest.raises(Pending):
        llm.call("judge", MARK_SYSTEM, "p", XMarks)
    cid = next(iter(rec.entries))
    expired = parse_line({"custom_id": cid, "response": None, "error": {"code": "batch_expired", "message": "x"}})
    logs = tmp_path / "logs"
    assert _store_reply(llm.cache, _study(), {"batch_id": "b"}, rec.entries[cid], expired, 1, 3, logs) == "transient"
    assert llm.cache.get_json(rec.entries[cid]["storage_key"]) is None
    assert _store_reply(llm.cache, _study(), {"batch_id": "b"}, rec.entries[cid], expired, 3, 3,
                        logs) == "transient_exhausted"
    assert llm.cache.get_json(rec.entries[cid]["storage_key"])["data"] is None


# --------------------------------------------------------------------------- #
# Statistics, validation, redaction
# --------------------------------------------------------------------------- #


def test_kappa_and_agreement():
    from aiomim.openai_study.stats import MARKS, agreement, coverage

    by_entry = {f"e{i}": [("present", "present"), ("absent", "absent"), ("partial", "absent")] for i in range(10)}
    a = agreement(by_entry, MARKS, resamples=200)
    assert a["n_facts"] == 30 and a["raw_agreement"] == pytest.approx(2 / 3, abs=1e-4)
    assert 0 < a["kappa"] < 1 and a["kappa_ci95"] is not None
    perfect = agreement({"e": [("present", "present"), ("absent", "absent")]}, MARKS, binary="present")
    assert perfect["kappa"] == 1.0
    assert coverage(["present", "partial", "absent", "unjudged"]) == pytest.approx(0.5)


def test_paired_reuses_compare_statistics():
    from aiomim.openai_study.stats import paired

    out = paired([(0.6, 0.5)] * 6 + [(0.4, 0.5)] * 2)
    assert out["n"] == 8 and out["better"] == 6 and out["worse"] == 2
    assert out["difference"] == pytest.approx(0.05)


GOLD = ("Smith et al. (2010) identified a homozygous c.123C-T transition in the ABC1 gene, resulting in an "
        "arg41-to-trp substitution, in two sibs from a consanguineous family.")


def test_scanner_redacts_and_restores_exactly():
    from aiomim.openai_study.validate import OmimScanner, resolver, restore_entry

    items = [({"paragraph": "k1"}, GOLD)]
    sc = OmimScanner(items)
    draft = ("In Clinical Features, SMITH et al. (2010) identified a homozygous c.123C-T transition in the ABC1 gene, "
             "resulting in an Arg41-to-trp substitution. Nothing else matches.")
    records: list = []
    red, n = sc.redact(draft, records)
    assert n == 1 and "redaction 0" in red and sc.hits(red) == 0
    entry = {"intro": {"text": red}, "meta": {"redactions": records}}
    assert restore_entry(entry, resolver(items))["intro"]["text"] == draft
    assert sc.hits("Short text") == 0


def test_validate_flags_schema_problems_and_omim_wording(tmp_path):
    from aiomim.openai_study.validate import OmimScanner, validate_dir

    out = tmp_path / "outputs"
    schemas = REPO / "studies" / "openai_second_model" / "schemas"
    good = {"spec_version": "1.0", "task": "A1", "mim": "123456", "strategy": "direct", "status": "complete",
            "openai_model": "gpt-6.2-astra", "draft": "claude_main_run", "claude_marks_of": "same_draft",
            "claude_source": "x", "counts": {"openai": None, "claude": None},
            "facts": [{"id": "0123456789ab.1", "paragraph": "0123456789ab", "content_level": "abstract",
                       "openai": "present", "claude": "absent"}]}
    (out / "marks" / "A1").mkdir(parents=True)
    (out / "marks" / "A1" / "123456.direct.json").write_text(json.dumps(good))
    sc = OmimScanner([GOLD])
    assert validate_dir(out, schemas, sc)["ok"]
    bad = dict(good, facts=[{**good["facts"][0], "openai": "maybe"}])
    (out / "marks" / "A1" / "123456.kg.json").write_text(json.dumps(bad))
    leak = dict(good, claude_source=GOLD[:100])
    (out / "marks" / "A1" / "123456.agent.json").write_text(json.dumps(leak))
    (out / "stray.txt").write_text("x")
    res = validate_dir(out, schemas, sc)
    assert not res["ok"]
    joined = "\n".join(res["problems"])
    assert "123456.kg.json" in joined and "OMIM" in joined and "stray.txt" in joined


def test_task_plan_from_study_json():
    from aiomim.openai_study.tasks import plan_tasks

    specs = plan_tasks(_study())
    kinds = {}
    for s in specs:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    assert kinds == {"A1": 93 * 6, "A2F": 93, "A2C": 93, "A3": 46 * 3, "B1": 30 * 3, "B2": 46 * 2}
    assert specs[0].allowed() == {"judge:mark"}


# --------------------------------------------------------------------------- #
# End to end with the fake provider (needs this checkout's runs/ and data/)
# --------------------------------------------------------------------------- #

HAVE_RUNS = (REPO / "runs" / "omim100" / "603552" / "entry.direct.json").exists() and \
    (REPO / "data" / "cache" / "llm").exists() and (REPO / "data" / "ontologies" / "hp.obo").exists()


@pytest.mark.skipif(not HAVE_RUNS, reason="needs the original runs' data (runs/, data/)")
def test_dry_run_end_to_end(tmp_path, monkeypatch):
    """Two entries per task: build a bundle, run smoke and step until done with replayed Claude replies
    (and injected invalid replies, refusals and expired requests), then report and validate."""
    import shutil

    from aiomim.openai_study import bundle as bundle_mod
    from aiomim.openai_study.offline import compact_hgnc, deactivate
    from aiomim.openai_study.providers import FakeProvider
    from aiomim.openai_study.report import report
    from aiomim.openai_study.validate import (
        OmimScanner,
        gold_texts_from_bundle,
        validate_dir,
    )
    from aiomim.openai_study.waves import plan, smoke, step

    monkeypatch.chdir(REPO)
    monkeypatch.setenv("AIOMIM_HOME", str(REPO / "data"))
    monkeypatch.setenv("AIOMIM_RUNS", str(REPO / "runs"))
    from aiomim.config import get_settings

    get_settings.cache_clear()
    data = json.loads(STUDY_JSON.read_text())
    for k, mims in (("A1", ["603552", "620481"]), ("A2", ["603552", "620481"]), ("A3", ["603552", "118210"]),
                    ("B1", ["603552", "620481"]), ("B2", ["603552", "118210"])):
        data["tasks"][k]["entries"] = mims
    study_dir = tmp_path / "study"
    paths = StudyPaths(study_dir)
    paths.root.mkdir()
    paths.study_json.write_text(json.dumps(data))
    shutil.copytree(REPO / "studies" / "openai_second_model" / "schemas", paths.schemas)
    study = Study.load(paths)
    # A small HGNC table stands in for the complete set (every lookup of these entries is in the cache).
    hgnc = tmp_path / "hgnc.json"
    hgnc.write_text(json.dumps({"response": {"docs": compact_hgnc({"response": {"docs": [
        {"symbol": "STX11", "hgnc_id": "HGNC:11429", "status": "Approved"}]}})}}))
    try:
        built = bundle_mod.build(REPO, study, paths.bundle_tar, hgnc_complete=hgnc, work=tmp_path / "work",
                                 verify=True, jobs=4)
        ver = built["manifest"]["verification"]
        assert ver["network_attempts"] == 0
        for kind, cell in ver["replayed_equals_stored"].items():
            assert cell["equal"] == cell["facts"], kind
        bundle_mod.unpack(paths)
        assert bundle_mod.check_files(paths.bundle) == []

        fake = FakeProvider(paths.private / "fake", paths.requests, REPO / "data" / "cache" / "llm",
                            faults={"invalid": 0.05, "refusal": 0.03, "expired": 0.05})
        plan(paths, study)
        smoke(paths, study, fake)               # sends the smoke batch; `step` polls and checks it (as Codex runs it)
        phases = []
        for _ in range(14):
            status = step(paths, study, fake, jobs=4)
            phases.append(status["phase"])
            if status["phase"] in ("done", "blocked"):
                break
        assert phases[-1] == "done", phases
        assert read_json(paths.state / "smoke.json")["passed"]
        status = read_json(paths.state / "status.json")
        assert status["tasks_finished"] == status["tasks_planned"] == 32
        assert status["requests"]["submitted"] >= status["requests"]["replies"] > 0
        wave1 = read_json(paths.waves / "wave_001.json")
        assert wave1["network_attempts"] == 0 and wave1["prompt_check"]["not_matched"] == 0
        summary = report(paths, study)
        assert summary["completion"]["A1"]["direct"]["unfinished"] == 0
        res = validate_dir(paths.outputs, paths.schemas, OmimScanner(gold_texts_from_bundle(paths.bundle)),
                           also=[paths.state])
        assert res["ok"], res["problems"][:5]
    finally:
        deactivate()
        get_settings.cache_clear()


def test_deactivate_restores_the_environment(tmp_path):
    from aiomim import llm as aiomim_llm
    from aiomim.openai_study.offline import _ORIGINAL, deactivate

    deactivate()
    assert not _ORIGINAL
    assert aiomim_llm.ClaudeCode.complete.__name__ == "complete"


def test_settings_replace_keeps_project_efforts(tmp_path):
    s = replace(_settings(tmp_path), replicate="")
    assert s.effort_for("judge") == "medium" and s.effort_for("synthesize") == "high"
    assert s.effort_for("normalize") == "low" and s.effort_for("recall") == "high"
