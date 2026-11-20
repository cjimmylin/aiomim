"""Offline tests of the Experiment B harness (aiomim.external): no model calls, no network."""

from __future__ import annotations

import base64
import json
import struct
import urllib.error
import urllib.request

import pytest

from aiomim.cache import DiskCache
from aiomim.external import adapt, corpus, score, shim, tasks
from aiomim.external.model import DEFAULT_SYSTEM, ProjectModel
from aiomim.llm import LLMRefusal


class FakeBackend:
    """Scripted stand-in for the Claude Code backend; records every call."""

    def __init__(self, replies=None, structured=None):
        self.replies = list(replies or [])
        self.structured = structured
        self.calls: list[dict] = []

    def _meta(self):
        return {"model": "m", "effort": "medium", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.01,
                "seconds": 0.1, "turns": 1, "safety_stops": 0}

    def complete_text(self, *, system, prompt, model, effort, timeout_s=None):
        self.calls.append({"system": system, "prompt": prompt, "schema": None})
        reply = self.replies.pop(0) if self.replies else f"reply {len(self.calls)}"
        if reply == "STOP":
            return "", {**self._meta(), "safety_stops": 1}
        if reply == "REFUSAL":
            raise LLMRefusal("refused")
        return reply, self._meta()

    def complete(self, *, system, prompt, schema, model, effort, tools=(), workdir=None, timeout_s=None):
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        return self.structured or {"answer": "x"}, self._meta()


class FakeEmbedder:
    name = "fake-embed"

    def embed(self, texts):
        return [[float(len(t)), 0.5, -1.0] for t in texts]


@pytest.fixture
def server(tmp_path):
    backend = FakeBackend()
    model = ProjectModel(backend=backend, cache=DiskCache(tmp_path / "cache"), max_concurrency=2)
    s = shim.Shim(tag="test/1", ledger=tmp_path / "ledger.jsonl", model=model, embedder=FakeEmbedder())
    srv = shim.ShimServer(shim=s)
    url = srv.start()
    yield url, backend, tmp_path / "ledger.jsonl", s
    srv.stop()


def post(url, path, body, headers=None, raw=False):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
            return resp.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def ledger(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


# --------------------------------------------------------------------------- adapter


def test_render_messages():
    assert shim.render_messages([{"role": "user", "content": "hi"}]) == (DEFAULT_SYSTEM, "hi", "single")
    system, prompt, how = shim.render_messages([
        {"role": "system", "content": "S1"}, {"role": "user", "content": [{"type": "text", "text": "q1"}]},
        {"role": "assistant", "content": "a1"}, {"role": "system", "content": "S2"},
        {"role": "user", "content": "q2"}])
    assert system == "S1\n\nS2" and how == "transcript"
    assert "[User]\nq1\n\n[Assistant]\na1\n\n[User]\nq2" in prompt and prompt.startswith(shim.TRANSCRIPT_INTRO)
    _, prompt, _ = shim.render_messages([{"role": "user", "content": "q"}, {"role": "assistant", "content": "par"}])
    assert prompt.startswith(shim.TRANSCRIPT_CONTINUE)
    with pytest.raises(shim.BadRequest):
        shim.render_messages([{"role": "tool", "content": "x"}])
    with pytest.raises(shim.BadRequest):
        shim.render_messages([{"role": "user", "content": [{"type": "image_url", "image_url": {}}]}])


def test_apply_stop():
    assert shim.apply_stop("abc END def STOP", ["STOP", "END"]) == ("abc ", True)
    assert shim.apply_stop("abc", "x") == ("abc", False)


def test_plain_system_and_ignored_params(server):
    url, backend, led, _ = server
    st, r = post(url, "/chat/completions", {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 9, "seed": 1,
                                            "messages": [{"role": "system", "content": "be brief"},
                                                         {"role": "user", "content": "hello"}]})
    assert st == 200 and r["choices"][0]["message"]["content"] == "reply 1"
    assert r["choices"][0]["finish_reason"] == "stop" and r["usage"]["prompt_tokens"] == 10
    assert backend.calls[0]["system"] == "be brief" and backend.calls[0]["prompt"] == "hello"
    row = ledger(led)[0]
    assert row["tag"] == "test/1" and row["fresh"] and row["ignored_params"] == ["max_tokens", "seed", "temperature"]
    assert row["requested_model"] == "gpt-4o" and row["cost_usd"] == 0.01 and row["safety_stop"] is False


def test_cached_repeat_makes_no_call(server):
    url, backend, led, _ = server
    body = {"model": "x", "messages": [{"role": "user", "content": "same"}]}
    first = post(url, "/chat/completions", body)[1]
    second = post(url, "/chat/completions", {**body, "temperature": 1.0}, headers={"X-Aiomim-Tag": "sys/2"})[1]
    assert len(backend.calls) == 1
    assert first["choices"][0]["message"] == second["choices"][0]["message"]
    rows = ledger(led)
    assert [r["cached"] for r in rows] == [False, True] and rows[1]["tag"] == "sys/2"


def test_multiturn_stop_and_user_tag(server):
    url, backend, led, _ = server
    backend.replies = ["one\nObservation: two"]
    st, r = post(url, "/chat/completions", {"model": "x", "user": "storm/5", "stop": ["Observation:"], "messages": [
        {"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]})
    assert r["choices"][0]["message"]["content"] == "one\n"
    assert "[Assistant]\nb" in backend.calls[0]["prompt"]
    assert ledger(led)[0]["tag"] == "storm/5" and ledger(led)[0]["stop_applied"]


def test_json_mode_reasks_once(server):
    url, backend, led, _ = server
    backend.replies = ["not json", '{"a": 1}']
    st, r = post(url, "/chat/completions", {"model": "x", "response_format": {"type": "json_object"},
                                            "messages": [{"role": "user", "content": "give json"}]})
    assert json.loads(r["choices"][0]["message"]["content"]) == {"a": 1}
    assert len(backend.calls) == 2 and shim.JSON_INSTRUCTION in backend.calls[0]["system"]
    row = ledger(led)[0]
    assert row["model_calls"] == 2 and row["json_valid"] and row["input_tokens"] == 20


def test_json_schema_uses_structured_output(server):
    url, backend, _, _ = server
    backend.structured = {"name": "n"}
    schema = {"type": "object", "properties": {"name": {"$ref": "#/$defs/S"}}, "$defs": {"S": {"type": "string"}}}
    st, r = post(url, "/chat/completions", {"model": "x", "messages": [{"role": "user", "content": "q"}],
                                            "response_format": {"type": "json_schema",
                                                                "json_schema": {"name": "x", "schema": schema}}})
    assert json.loads(r["choices"][0]["message"]["content"]) == {"name": "n"}
    assert backend.calls[0]["schema"]["properties"]["name"] == {"type": "string"}
    # a non-object top level is instructed instead
    st, r = post(url, "/chat/completions", {"model": "x", "messages": [{"role": "user", "content": "q2"}],
                                            "response_format": {"type": "json_schema", "json_schema": {
                                                "name": "y", "schema": {"type": "array"}}}})
    assert backend.calls[-1]["schema"] is None and "JSON Schema" in backend.calls[-1]["system"]


def test_streaming(server):
    url, backend, _, _ = server
    st, text = post(url, "/chat/completions", {"model": "x", "stream": True, "stream_options": {"include_usage": True},
                                               "messages": [{"role": "user", "content": "s"}]}, raw=True)
    events = [line[6:] for line in text.split("\n") if line.startswith("data: ")]
    assert events[-1] == "[DONE]"
    chunks = [json.loads(e) for e in events[:-1]]
    assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"]) == "reply 1"
    assert chunks[2]["choices"][0]["finish_reason"] == "stop" and chunks[3]["usage"]["completion_tokens"] == 5


def test_tools_and_n_refused(server):
    url, backend, led, _ = server
    st, r = post(url, "/chat/completions", {"model": "x", "messages": [{"role": "user", "content": "q"}],
                                            "tools": [{"type": "function", "function": {"name": "f"}}]})
    assert st == 400 and "tool" in r["error"]["message"]
    st, _ = post(url, "/chat/completions", {"model": "x", "n": 2, "messages": [{"role": "user", "content": "q"}]})
    assert st == 400 and not backend.calls
    assert [r["status"] for r in ledger(led)] == [400, 400]


@pytest.mark.parametrize("kind", ["STOP", "REFUSAL"])
def test_safety_stop_is_content_filter_and_cached(server, kind):
    url, backend, led, s = server
    backend.replies = [kind]
    body = {"model": "x", "messages": [{"role": "user", "content": "q"}]}
    for _ in range(2):
        st, r = post(url, "/chat/completions", body)
        assert st == 200 and r["choices"][0]["finish_reason"] == "content_filter"
        assert r["choices"][0]["message"]["content"] == ""
    assert len(backend.calls) == 1
    assert [row["safety_stop"] for row in ledger(led)] == [True, True] and s.stats["stops"] == 2


def test_embeddings_and_models(server):
    url, _, led, _ = server
    st, r = post(url, "/embeddings", {"model": "text-embedding-3-small", "input": ["ab", "abcd"]})
    assert st == 200 and [d["embedding"][0] for d in r["data"]] == [2.0, 4.0]
    st, r = post(url, "/embeddings", {"model": "e", "input": "abc", "encoding_format": "base64"})
    assert struct.unpack("<3f", base64.b64decode(r["data"][0]["embedding"]))[0] == 3.0
    st, r = post(url, "/embeddings", {"model": "e", "input": [[1, 2, 3]]})
    assert st == 400
    with urllib.request.urlopen(url + "/models") as resp:
        assert json.loads(resp.read())["data"][1]["id"] == "fake-embed"
    assert ledger(led)[0]["n_inputs"] == 2


def test_openai_client_if_installed(server):
    openai = pytest.importorskip("openai")
    url, _, _, _ = server
    client = openai.OpenAI(base_url=url, api_key="dummy")
    r = client.chat.completions.create(model="claude", messages=[{"role": "user", "content": "q"}])
    assert r.choices[0].message.content == "reply 1"
    e = client.embeddings.create(model="e", input=["abc"])
    assert e.data[0].embedding[0] == 3.0
    with pytest.raises(openai.BadRequestError):
        client.chat.completions.create(model="c", messages=[{"role": "user", "content": "q"}],
                                       tools=[{"type": "function", "function": {"name": "f", "parameters": {}}}])


# --------------------------------------------------------------------------- corpus and tasks


def test_ordinary_title():
    assert corpus.ordinary_title("CHARCOT-MARIE-TOOTH DISEASE, AXONAL, TYPE 2EE") == \
        "Charcot-Marie-Tooth disease, axonal, type 2EE"
    assert corpus.ordinary_title("STICKLER SYNDROME, TYPE VI") == "Stickler syndrome, type VI"
    assert corpus.ordinary_title("ReNU SYNDROME") == "ReNU syndrome"
    assert corpus.ordinary_title("SPERMATOGENIC FAILURE, X-LINKED, 3") == "Spermatogenic failure, X-linked, 3"
    assert corpus.ordinary_title("COENZYME Q10 DEFICIENCY, PRIMARY, 2") == "Coenzyme Q10 deficiency, primary, 2"


def test_seeded_order():
    entries = [str(600000 + i) for i in range(38)]
    assert corpus.seeded_order(entries) == corpus.seeded_order(list(reversed(entries)))
    assert sorted(corpus.seeded_order(entries)) == entries
    assert corpus.N_MAIN == 10


def test_order_file_matches_rule():
    if not corpus.ORDER_TSV.exists() or not corpus.ABLATION_TABLES.exists():
        pytest.skip("order file or ablation tables not present")
    assert corpus.entry_order() == corpus.seeded_order()
    assert len(corpus.entry_order()) == 38


def test_task_wording():
    qs = tasks.section_questions("ATRIAL STANDSTILL 1")
    assert [q["key"] for q in qs] == ["description", "clinical_features", "inheritance", "molecular_genetics",
                                      "genotype_phenotype", "pathogenesis"]
    assert all("atrial standstill 1" in q["question"] and "Cite" in q["question"] for q in qs)
    text = " ".join(q["question"] for q in qs).lower()
    assert "omim" not in text and "score" not in text and "fact" not in text
    assert tasks.storm_topic("ATRIAL STANDSTILL 1") == "Atrial standstill 1"
    assert "of Noonan syndrome-like" in tasks.section_questions("NOONAN SYNDROME-LIKE DISORDER")[1]["question"]


# --------------------------------------------------------------------------- intermediate format and scoring


def _output(**kw):
    return {"system": "demo", "mim": "123456", "blocks": [
        {"section": "Clinical features", "text": "A [1].", "pmids": ["1", "1"]},
        {"section": "Clinical features", "text": "Uncited text here.", "pmids": []},
        {"section": "Inheritance", "text": "B.", "pmids": ["2"]}], "meta": {"settings_changed": []}, **kw}


def test_validate_format():
    out = adapt.validate(_output(), supplied={"1", "2"})
    assert out["blocks"][0]["pmids"] == ["1"] and out["format"] == adapt.FORMAT
    with pytest.raises(adapt.FormatError):
        adapt.validate(_output(), supplied={"1"})
    with pytest.raises(adapt.FormatError):
        adapt.validate({**_output(), "blocks": []}, supplied={"1", "2"})
    assert adapt.validate({**_output(), "blocks": [], "stopped": "safety stop"}, supplied=set())["stopped"]
    share = adapt.uncited_share(out)
    assert share["uncited_blocks"] == 1 and share["uncited_chars"] == len("Uncited text here.")


def test_to_entry_keeps_text(monkeypatch, tmp_path):
    src = tmp_path / "123456"
    src.mkdir()
    (src / "seed.json").write_text(json.dumps({"title": "T", "prefix": "#", "alt_titles": []}))
    (src / "papers.json").write_text(json.dumps([{"pmid": "1", "label": "X (2000)", "reference": "R1",
                                                  "content_level": "abstract"},
                                                 {"pmid": "2", "label": "Y (2001)", "reference": "R2",
                                                  "content_level": "title"}]))
    monkeypatch.setattr(corpus, "source_dir", lambda mim, run="omim100": tmp_path / mim)
    entry = adapt.to_entry(adapt.validate(_output(), supplied={"1", "2"}))
    assert [s.heading for s in entry.sections] == ["Clinical features", "Inheritance"]
    assert [p.text for p in entry.sections[0].paragraphs] == ["A [1].", "Uncited text here."]
    assert entry.sections[0].paragraphs[1].pmids == [] and [r.pmid for r in entry.references] == ["1", "2"]


def test_ledger_usage(tmp_path):
    path = tmp_path / "l.jsonl"
    rows = [{"endpoint": "/v1/chat/completions", "tag": "s/1", "status": 200, "cached": False, "model_calls": 2,
             "input_tokens": 10, "output_tokens": 3, "cost_usd": 0.5, "call_seconds": 4, "safety_stop": False,
             "ignored_params": ["temperature"]},
            {"endpoint": "/v1/chat/completions", "tag": "s/1/q2", "status": 200, "cached": True,
             "input_tokens": 10, "output_tokens": 3, "cost_usd": 0.5, "call_seconds": 4, "safety_stop": True},
            {"endpoint": "/v1/chat/completions", "tag": "s/10", "status": 200, "cached": False},
            {"endpoint": "/v1/embeddings", "tag": "s/1", "status": 200},
            {"endpoint": "/v1/chat/completions", "tag": "s/1", "status": 400}]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    u = score.ledger_usage("s", "1", [path])
    assert (u["requests"], u["model_calls"], u["cached"], u["stops"], u["refused"], u["embedding_requests"]) == \
        (4, 2, 1, 1, 1, 1)
    assert u["fresh_cost_usd"] == 0.5 and u["full_cost_usd"] == 1.0 and u["ignored_params"] == ["temperature"]


def test_by_availability():
    frozen = {"paragraphs": [{"content_level": "abstract", "facts": [
        {"id": "a.1", "status": "present"}, {"id": "a.2", "status": "absent"}, {"id": "a.3", "status": "partial"},
        {"id": "a.4", "status": "unjudged"}]}]}
    out = score.by_availability(frozen, {"a.1": "yes", "a.2": "no", "a.3": "yes"})
    assert out["stated"]["n_facts"] == 2 and out["stated"]["coverage"] == 0.75
    assert out["not_stated"]["coverage"] == 0.0 and out["all"]["n_facts"] == 3


def test_ledger_usage_distinct_counts_each_request_once(tmp_path):
    path = tmp_path / "l.jsonl"
    fresh = {"endpoint": "/v1/chat/completions", "tag": "s/1", "status": 200, "cached": False, "model_calls": 1,
             "input_tokens": 100, "output_tokens": 10, "cost_usd": 1.0, "call_seconds": 5, "key": "k1"}
    resave = {**fresh, "cached": True}                       # the same request re-asked from the cache
    earlier = {**fresh, "cached": True, "key": "k2"}           # first made by another run, cached here
    step = {**fresh, "key": "k3", "tag": "s/1/search"}
    path.write_text("\n".join(json.dumps(r) for r in (fresh, resave, resave, earlier, step)))
    u = score.ledger_usage("s", "1", [path])
    assert (u["chat_requests"], u["model_calls"], u["distinct_requests"]) == (5, 2, 3)
    assert u["full_cost_usd"] == 5.0 and u["distinct_cost_usd"] == 3.0 and u["distinct_input_tokens"] == 300
    v = score.ledger_usage("s", "1", [path], skip_steps=("search",))
    assert v["distinct_requests"] == 2 and v["model_calls"] == 1


def test_wall_seconds_rules(monkeypatch, tmp_path):
    monkeypatch.setattr(score, "runs_root", lambda: tmp_path)
    (tmp_path / "sys").mkdir()
    (tmp_path / "sys" / "pilot.log").write_text(json.dumps({"mim": "1", "calls": 30, "seconds": 177.2}) + "\n")
    resaved = {"meta": {"chat_requests_this_run": 30, "cached_requests_this_run": 30, "seconds": 6.9}}
    assert score.wall_seconds("sys", "1", resaved)["seconds"] == 177.2
    assert score.wall_seconds("sys", "2", resaved)["seconds"] is None
    partly = {"meta": {"chat_requests_this_run": 66, "cached_requests_this_run": 52, "seconds": 150.0}}
    w = score.wall_seconds("sys", "2", partly)
    assert w["seconds"] == 150.0 and "understates" in w["source"]
    graph = {"meta": {"seconds": 188.8, "query_run": None,
                      "index_status": {"attempts": [{"seconds": 247.5}]}}}
    assert score.wall_seconds("g", "1", graph)["seconds"] == 436.3
    graph["meta"]["query_run"] = {"seconds": 325.3}
    assert score.wall_seconds("g", "1", graph)["seconds"] == 572.8


def test_pair_gives_interval_at_small_n():
    import random

    out = score._pair([(0.5, 0.6), (0.4, 0.6), (0.7, 0.6), (0.3, 0.6)], random.Random(7))
    assert out["n"] == 4 and out["ci95"] is not None and out["ci95"][0] <= out["difference"] <= out["ci95"][1]
    assert (out["better"], out["worse"]) == (1, 3) and out["ci_unreliable"]
