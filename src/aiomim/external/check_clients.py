"""Live check of the adapter with the real OpenAI and LiteLLM clients (makes real model calls).

Run the adapter in the project environment, this script in an environment that has `openai`
and `litellm` (it imports nothing from aiomim):

    PYTHONPATH=src python -m aiomim.external.shim --port 8765 --ledger runs/external/_check/ledger.jsonl --tag check
    .venvs/clients/bin/python src/aiomim/external/check_clients.py http://127.0.0.1:8765/v1

Prints one line per check and exits non-zero if any fails.
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/v1"
MODEL = "claude-opus-5-5"
results: list[tuple[str, bool, str]] = []


def check(name, fn):
    t = time.time()
    try:
        detail = fn()
        results.append((name, True, f"{detail} ({time.time() - t:.1f}s)"))
    except Exception as exc:  # noqa: BLE001
        results.append((name, False, f"{type(exc).__name__}: {exc}"[:300]))
    print(("PASS" if results[-1][1] else "FAIL"), name, "-", results[-1][2], flush=True)


def main() -> None:
    import openai

    c = openai.OpenAI(base_url=BASE, api_key="dummy", max_retries=0, timeout=900)

    def plain():
        r = c.chat.completions.create(model=MODEL, messages=[{"role": "user", "content":
                                      "What is the capital of France? Answer with one word."}])
        assert "paris" in r.choices[0].message.content.lower(), r.choices[0].message.content
        return repr(r.choices[0].message.content)

    def system_user():
        r = c.chat.completions.create(model=MODEL, temperature=0.3, max_tokens=50, messages=[
            {"role": "system", "content": "You answer only in upper-case letters."},
            {"role": "user", "content": "Name the largest planet of the solar system, one word."}])
        text = r.choices[0].message.content.strip()
        assert "JUPITER" in text, text
        return repr(text)

    def multi_turn():
        r = c.chat.completions.create(model=MODEL, messages=[
            {"role": "user", "content": "Remember the number 41. Reply OK."},
            {"role": "assistant", "content": "OK."},
            {"role": "user", "content": "What is that number plus one? Reply with the number only."}])
        text = r.choices[0].message.content.strip()
        assert "42" in text and "[Assistant]" not in text, text
        return repr(text)

    def stop_seq():
        r = c.chat.completions.create(model=MODEL, stop=["THREE"], messages=[{"role": "user", "content":
                                      "Write exactly these words separated by spaces: ONE TWO THREE FOUR"}])
        text = r.choices[0].message.content
        assert "TWO" in text and "THREE" not in text and "FOUR" not in text, text
        return repr(text)

    def json_mode():
        r = c.chat.completions.create(model=MODEL, response_format={"type": "json_object"}, messages=[
            {"role": "user", "content": "Give a JSON object with keys 'gene' (string 'CFTR') and 'chromosome' (7)."}])
        data = json.loads(r.choices[0].message.content)
        assert data.get("chromosome") == 7, data
        return data

    def json_schema():
        schema = {"type": "object", "properties": {"answer": {"type": "integer"}}, "required": ["answer"],
                  "additionalProperties": False}
        r = c.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "What is 6 times 7?"}],
                                      response_format={"type": "json_schema",
                                                       "json_schema": {"name": "a", "schema": schema}})
        data = json.loads(r.choices[0].message.content)
        assert data == {"answer": 42}, data
        return data

    def streaming():
        parts, finish = [], None
        for ch in c.chat.completions.create(model=MODEL, stream=True, messages=[{"role": "user", "content":
                                            "Say the word 'streamed' and nothing else."}]):
            if ch.choices:
                parts.append(ch.choices[0].delta.content or "")
                finish = ch.choices[0].finish_reason or finish
        text = "".join(parts)
        assert "streamed" in text.lower() and finish == "stop", (text, finish)
        return repr(text)

    def embeddings():
        r = c.embeddings.create(model="text-embedding-3-small", input=["cystic fibrosis", "CFTR", "a third text"])
        dims = {len(d.embedding) for d in r.data}
        assert len(r.data) == 3 and dims == {384}, dims
        return f"3 vectors, dim {dims}"

    def cached_repeat():
        t = time.time()
        a = c.chat.completions.create(model=MODEL, messages=[{"role": "user", "content":
                                      "What is the capital of France? Answer with one word."}])
        assert time.time() - t < 2.0, "repeat took too long to be a cache hit"
        return repr(a.choices[0].message.content)

    def tools_refused():
        try:
            c.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "weather?"}], tools=[
                {"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object",
                                                                                        "properties": {}}}}])
        except openai.BadRequestError as exc:
            return f"HTTP 400: {str(exc)[:80]}"
        raise AssertionError("tool request was not refused")

    for name, fn in [("openai plain", plain), ("openai system+user", system_user), ("openai multi-turn", multi_turn),
                     ("openai stop sequence", stop_seq), ("openai JSON mode", json_mode),
                     ("openai json_schema", json_schema), ("openai streaming", streaming),
                     ("openai embeddings batch", embeddings), ("openai cached repeat", cached_repeat),
                     ("openai tool call refused", tools_refused)]:
        check(name, fn)

    import litellm

    def ll_plain():
        r = litellm.completion(model=f"openai/{MODEL}", api_base=BASE, api_key="dummy", messages=[
            {"role": "system", "content": "Reply tersely."},
            {"role": "user", "content": "Which organ produces insulin? One word."}])
        text = r.choices[0].message.content
        assert "pancreas" in text.lower(), text
        return repr(text)

    def ll_cached():   # the openai plain question again, through LiteLLM: a cache hit
        r = litellm.completion(model=f"openai/{MODEL}", api_base=BASE, api_key="dummy", temperature=0,
                               messages=[{"role": "user", "content":
                                          "What is the capital of France? Answer with one word."}])
        return repr(r.choices[0].message.content)

    def ll_stream():
        text = "".join((ch.choices[0].delta.content or "") for ch in litellm.completion(
            model=f"openai/{MODEL}", api_base=BASE, api_key="dummy", stream=True,
            messages=[{"role": "user", "content": "Say the word 'streamed' and nothing else."}]) if ch.choices)
        assert "streamed" in text.lower(), text
        return repr(text)

    def ll_json():
        r = litellm.completion(model=f"openai/{MODEL}", api_base=BASE, api_key="dummy",
                               response_format={"type": "json_object"}, messages=[{"role": "user", "content":
                               "Give a JSON object with keys 'gene' (string 'CFTR') and 'chromosome' (7)."}])
        return json.loads(r.choices[0].message.content)

    def ll_embed():
        r = litellm.embedding(model=f"openai/{MODEL}-embed", api_base=BASE, api_key="dummy", input=["a", "b"])
        assert len(r.data) == 2 and len(r.data[0]["embedding"]) == 384
        return "2 vectors, dim 384"

    def ll_tools():
        try:
            litellm.completion(model=f"openai/{MODEL}", api_base=BASE, api_key="dummy", num_retries=0,
                               messages=[{"role": "user", "content": "weather?"}],
                               tools=[{"type": "function", "function": {"name": "w", "parameters": {
                                   "type": "object", "properties": {}}}}])
        except litellm.BadRequestError as exc:
            return f"BadRequestError: {str(exc)[:80]}"
        raise AssertionError("tool request was not refused")

    for name, fn in [("litellm system+user", ll_plain), ("litellm cached repeat", ll_cached),
                     ("litellm streaming", ll_stream), ("litellm JSON mode", ll_json),
                     ("litellm embeddings", ll_embed), ("litellm tool call refused", ll_tools)]:
        check(name, fn)
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
