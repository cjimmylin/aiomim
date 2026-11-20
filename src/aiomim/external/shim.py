"""A local OpenAI-compatible server in front of the project's one model and one local embedding model.

Endpoints (also served without the /v1 prefix):

    POST /v1/chat/completions   one call of the project's model per request (cached)
    POST /v1/embeddings         BAAI/bge-small-en-v1.5 through fastembed, locally
    GET  /v1/models             the model names served

Mapping of a chat request to one model call
-------------------------------------------
* Every system (and "developer") message, wherever it stands, is joined into the system
  prompt, in order, separated by blank lines. With none, the system prompt is
  `model.DEFAULT_SYSTEM`.
* A single user message is the prompt, verbatim.
* Anything else (several user messages, assistant turns) is rendered as a labelled
  transcript (see `render_transcript`) that the model is asked to continue with the
  assistant's next reply.
* `stop` truncates the reply at the earliest stop sequence. `n` must be 1.
* `response_format` json_object: the system prompt asks for one JSON object; a reply
  that does not parse is asked once more (as the project's layer does). json_schema:
  the CLI's structured output with that schema when its top level is an object,
  otherwise (or if the CLI rejects the schema) instructed like json_object with the
  schema shown.
* temperature, top_p, max_tokens, max_completion_tokens, seed, presence/frequency
  penalties, logit_bias, logprobs, top_logprobs, user-irrelevant extras cannot be passed
  to the command-line model: they are accepted, ignored and listed in the ledger line.
* tools / functions / tool_choice / tool or function messages: HTTP 400. Tool calling
  is not supported, so that no integration silently depends on it.
* A reply stopped by the safety filter is a normal completion with empty content and
  finish_reason "content_filter"; it is cached as a stop and never retried.

Every request writes one JSON line to the ledger (see `Shim._ledger`). The tag of a
line is the request's `X-Aiomim-Tag` header, else its `user` field, else the server's tag.

Run it:  PYTHONPATH=src python -m aiomim.external.shim --port 8765 --ledger L.jsonl --tag paperqa2/108770
or from Python:  with ShimServer(tag=..., ledger=...) as base_url: ...   (base_url ends in /v1)
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import signal
import struct
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..llm import LLMError, LLMLimitReached
from .model import DEFAULT_EFFORT, DEFAULT_SYSTEM, ProjectModel

log = logging.getLogger(__name__)

TAG_HEADER = "X-Aiomim-Tag"
IGNORED_PARAMS = ("temperature", "top_p", "max_tokens", "max_completion_tokens", "seed", "presence_penalty",
                  "frequency_penalty", "logit_bias", "logprobs", "top_logprobs", "top_k", "repetition_penalty",
                  "min_p", "reasoning_effort", "stream_options", "parallel_tool_calls", "service_tier", "store",
                  "metadata", "prediction", "modalities", "audio", "web_search_options", "thinking")
JSON_INSTRUCTION = ("Reply with one valid JSON object and nothing else: no text before or after it, "
                    "no code fence.")
TRANSCRIPT_INTRO = ("Below is a conversation between a user and an assistant, as a transcript. "
                    "Write the assistant's next reply. Reply with that message only: do not repeat the "
                    "transcript and do not add a speaker label.")
TRANSCRIPT_CONTINUE = ("Below is a conversation between a user and an assistant, as a transcript. The "
                       "assistant's last message is unfinished. Continue it from exactly where it stops: reply "
                       "with the continuation only, without repeating what is already written and without a "
                       "speaker label.")


class BadRequest(ValueError):
    """A request the adapter refuses (HTTP 400)."""


# --------------------------------------------------------------------------- #
# Messages -> one model call
# --------------------------------------------------------------------------- #


def _text_of(content: Any, role: str) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict) and part.get("type") in ("text", "input_text"):
                out.append(str(part.get("text", "")))
            else:
                kind = part.get("type") if isinstance(part, dict) else type(part).__name__
                raise BadRequest(f"unsupported content part of type {kind!r} in a {role} message: text only")
        return "\n".join(out)
    raise BadRequest(f"unsupported content in a {role} message")


def _label(msg: dict[str, Any]) -> str:
    role = "User" if msg["role"] == "user" else "Assistant"
    return f"[{role} ({msg['name']})]" if msg.get("name") else f"[{role}]"


def render_transcript(turns: list[dict[str, Any]]) -> str:
    """A multi-turn history as one prompt: an instruction, then each turn under a [User] or
    [Assistant] label, in order, separated by blank lines, between transcript markers."""
    continue_last = turns[-1]["role"] == "assistant"
    body = "\n\n".join(f"{_label(m)}\n{m['text']}" for m in turns)
    return (f"{TRANSCRIPT_CONTINUE if continue_last else TRANSCRIPT_INTRO}\n\n"
            f"<transcript>\n{body}\n</transcript>")


def render_messages(messages: Any) -> tuple[str, str, str]:
    """(system prompt, prompt, rendering) for a chat message list; rendering is 'single' or 'transcript'."""
    if not isinstance(messages, list) or not messages:
        raise BadRequest("messages must be a non-empty list")
    system_parts: list[str] = []
    turns: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg:
            raise BadRequest("each message must be an object with a role")
        role = msg["role"]
        if role in ("tool", "function") or msg.get("tool_calls") or msg.get("function_call"):
            raise BadRequest("tool and function calling are not supported by this adapter")
        if role not in ("system", "developer", "user", "assistant"):
            raise BadRequest(f"unsupported message role {role!r}")
        text = _text_of(msg.get("content"), role)
        if role in ("system", "developer"):
            if text.strip():
                system_parts.append(text)
        else:
            turns.append({"role": role, "text": text, "name": msg.get("name")})
    if not turns:
        raise BadRequest("the request has no user message")
    system = "\n\n".join(system_parts) if system_parts else DEFAULT_SYSTEM
    if len(turns) == 1 and turns[0]["role"] == "user":
        return system, turns[0]["text"], "single"
    return system, render_transcript(turns), "transcript"


def apply_stop(text: str, stop: Any) -> tuple[str, bool]:
    """Cut `text` at the earliest stop sequence; whether one was found."""
    if not stop:
        return text, False
    seqs = [stop] if isinstance(stop, str) else [s for s in stop if isinstance(s, str) and s]
    cut = min((i for i in (text.find(s) for s in seqs) if i >= 0), default=-1)
    return (text[:cut], True) if cut >= 0 else (text, False)


def _inline_refs(schema: Any) -> Any:
    """Inline local $refs ($defs / definitions). Raises BadRequest on recursion."""
    if not isinstance(schema, dict):
        return schema
    defs = {**(schema.get("definitions") or {}), **(schema.get("$defs") or {})}

    def walk(node: Any, seen: tuple[str, ...]) -> Any:
        if isinstance(node, list):
            return [walk(x, seen) for x in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            name = str(node["$ref"]).rsplit("/", 1)[-1]
            if name in seen or name not in defs:
                raise BadRequest("schema with recursive or unresolvable $ref")
            return walk(defs[name], seen + (name,))
        return {k: walk(v, seen) for k, v in node.items() if k not in ("$defs", "definitions")}

    return walk(schema, ())


def response_mode(fmt: Any) -> tuple[str, dict[str, Any] | None]:
    """('text' | 'json_object' | 'json_schema', schema)."""
    if not fmt:
        return "text", None
    if not isinstance(fmt, dict):
        raise BadRequest("response_format must be an object")
    kind = fmt.get("type", "text")
    if kind == "text":
        return "text", None
    if kind == "json_object":
        return "json_object", None
    if kind == "json_schema":
        spec = fmt.get("json_schema") or {}
        schema = spec.get("schema") if isinstance(spec, dict) else None
        if not isinstance(schema, dict):
            raise BadRequest("response_format json_schema without a schema")
        return "json_schema", schema
    raise BadRequest(f"unsupported response_format type {kind!r}")


# --------------------------------------------------------------------------- #
# The server
# --------------------------------------------------------------------------- #


class Shim:
    """The request logic, independent of HTTP (tests call it directly too)."""

    def __init__(self, *, tag: str = "", ledger: str | Path | None = None, effort: str = DEFAULT_EFFORT,
                 max_concurrency: int = 6, model: ProjectModel | None = None, embedder=None):
        self.tag = tag
        self.ledger_path = Path(ledger) if ledger else None
        self.model = model or ProjectModel(effort=effort, max_concurrency=max_concurrency)
        self._embedder = embedder
        self._ledger_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self.stats = {"chat_requests": 0, "fresh": 0, "cached": 0, "model_calls": 0, "stops": 0, "errors": 0,
                      "refused": 0, "embedding_requests": 0, "embedded_texts": 0,
                      "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    @property
    def embedder(self):
        if self._embedder is None:
            from .embed import LocalEmbedder

            self._embedder = LocalEmbedder()
        return self._embedder

    # ------------------------------------------------------------------ ledger

    def _ledger(self, row: dict[str, Any]) -> None:
        if self.ledger_path is None:
            return
        line = json.dumps(row, ensure_ascii=False, default=str)
        with self._ledger_lock:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def _count(self, **kv: float) -> None:
        with self._stats_lock:
            for k, v in kv.items():
                self.stats[k] += v

    def tag_for(self, body: dict[str, Any], headers: dict[str, str]) -> str:
        return headers.get(TAG_HEADER.lower()) or (body.get("user") if isinstance(body.get("user"), str) else "") \
            or self.tag

    # ------------------------------------------------------------------ chat

    def chat(self, body: dict[str, Any], headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        """(HTTP status, response body). The response is always a full completion; streaming wraps it."""
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        started = time.time()
        tag = self.tag_for(body, headers)
        ignored = sorted(k for k in IGNORED_PARAMS if k in body)
        row: dict[str, Any] = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "endpoint": "/v1/chat/completions",
                               "tag": tag, "requested_model": body.get("model"), "model": self.model.model,
                               "effort": self.model.effort, "stream": bool(body.get("stream")),
                               "ignored_params": ignored}
        self._count(chat_requests=1)
        try:
            self._refuse_unsupported(body)
            system, prompt, rendering = render_messages(body.get("messages"))
            mode, schema = response_mode(body.get("response_format"))
        except BadRequest as exc:
            self._count(refused=1)
            row.update(status=400, error=str(exc), seconds=round(time.time() - started, 3))
            self._ledger(row)
            return 400, _error(str(exc), "invalid_request_error")
        row.update(rendering=rendering, n_messages=len(body["messages"]), response_format=mode,
                   prompt_chars=len(system) + len(prompt))
        try:
            done, how = self._complete(system, prompt, mode, schema)
        except LLMLimitReached as exc:
            self._count(errors=1)
            row.update(status=503, error=f"usage limit: {exc}", seconds=round(time.time() - started, 3))
            self._ledger(row)
            return 503, _error(f"the model's usage limit is reached: {exc}", "usage_limit")
        except (LLMError, OSError) as exc:
            self._count(errors=1)
            row.update(status=502, error=f"{type(exc).__name__}: {exc}"[:500], seconds=round(time.time() - started, 3))
            self._ledger(row)
            return 502, _error(f"model call failed: {exc}", "model_error")

        text, cut = apply_stop(done.text, body.get("stop"))
        finish = "content_filter" if done.stopped else "stop"
        meta = done.meta
        calls = 0 if done.cached else done.attempts
        self._count(**({"cached": 1} if done.cached else {"fresh": 1, "model_calls": calls}),
                    stops=int(done.stopped),
                    **({} if done.cached else {"input_tokens": int(meta.get("input_tokens") or 0),
                                               "output_tokens": int(meta.get("output_tokens") or 0),
                                               "cost_usd": float(meta.get("cost_usd") or 0.0)}))
        row.update(status=200, cached=done.cached, fresh=not done.cached, model_calls=calls,
                   json_handling=how, json_valid=done.json_valid,
                   # As the project's usage ledger reports a call: what it cost when made (a cached
                   # reply repeats the stored figures; `fresh` says whether this request paid them).
                   input_tokens=int(meta.get("input_tokens") or 0), output_tokens=int(meta.get("output_tokens") or 0),
                   cost_usd=round(float(meta.get("cost_usd") or 0.0), 6), call_seconds=meta.get("seconds"),
                   seconds=round(time.time() - started, 3), safety_stop=done.stopped,
                   finish_reason=finish, stop_applied=cut, key=done.key[:16], error=None)
        if done.notes:
            row["notes"] = done.notes
        self._ledger(row)
        resp = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}", "object": "chat.completion", "created": int(time.time()),
            "model": self.model.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish,
                         "logprobs": None}],
            "usage": {"prompt_tokens": row["input_tokens"], "completion_tokens": row["output_tokens"],
                      "total_tokens": row["input_tokens"] + row["output_tokens"]},
            "system_fingerprint": f"aiomim-shim:{self.model.effort}",
        }
        return 200, resp

    @staticmethod
    def _refuse_unsupported(body: dict[str, Any]) -> None:
        if body.get("tools") or body.get("functions"):
            raise BadRequest("tool and function calling are not supported by this adapter "
                             "(the request carries tools/functions)")
        choice = body.get("tool_choice")
        if choice not in (None, "none"):
            raise BadRequest("tool_choice is not supported by this adapter")
        if body.get("function_call") not in (None, "none"):
            raise BadRequest("function_call is not supported by this adapter")
        n = body.get("n")
        if n not in (None, 1):
            raise BadRequest("only n=1 is supported")

    def _complete(self, system: str, prompt: str, mode: str, schema: dict[str, Any] | None):
        if mode == "text":
            return self.model.complete(system, prompt), "none"
        if mode == "json_schema":
            usable = None
            try:
                inlined = _inline_refs(schema)
                if inlined.get("type") == "object":
                    usable = inlined
            except BadRequest:
                usable = None
            if usable is not None:
                try:
                    return self.model.complete(system, prompt, schema=usable), "structured_output"
                except LLMLimitReached:
                    raise
                except LLMError as exc:
                    log.warning("shim: structured output with this schema failed (%s); instructing instead", exc)
            instructed = (f"{system}\n\n{JSON_INSTRUCTION} The object must conform to this JSON Schema:\n"
                          f"{json.dumps(schema, ensure_ascii=False)}")
            return self.model.complete(instructed, prompt, json_mode=True), "instructed_schema"
        return self.model.complete(f"{system}\n\n{JSON_INSTRUCTION}", prompt, json_mode=True), "instructed"

    # ------------------------------------------------------------------ embeddings

    def embeddings(self, body: dict[str, Any], headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        started = time.time()
        tag = self.tag_for(body, headers)
        raw = body.get("input")
        row: dict[str, Any] = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "endpoint": "/v1/embeddings", "tag": tag,
                               "requested_model": body.get("model"), "model": getattr(self.embedder, "name", "?"),
                               "ignored_params": sorted(k for k in ("dimensions",) if k in body)}
        texts = [raw] if isinstance(raw, str) else raw
        if not isinstance(texts, list) or not texts or not all(isinstance(t, str) for t in texts):
            msg = ("input must be a string or a non-empty list of strings (token-id arrays are not supported: "
                   "turn off client-side tokenisation, e.g. check_embedding_ctx_length=False)")
            row.update(status=400, error=msg)
            self._ledger(row)
            return 400, _error(msg, "invalid_request_error")
        vectors = self.embedder.embed(texts)
        self._count(embedding_requests=1, embedded_texts=len(texts))
        fmt = body.get("encoding_format") or "float"
        data = []
        for i, vec in enumerate(vectors):
            emb: Any = vec
            if fmt == "base64":
                emb = base64.b64encode(struct.pack(f"<{len(vec)}f", *vec)).decode("ascii")
            data.append({"object": "embedding", "index": i, "embedding": emb})
        approx_tokens = sum(max(1, len(t) // 4) for t in texts)
        row.update(status=200, n_inputs=len(texts), input_chars=sum(len(t) for t in texts), encoding_format=fmt,
                   seconds=round(time.time() - started, 3), model_calls=0, error=None)
        self._ledger(row)
        return 200, {"object": "list", "data": data, "model": getattr(self.embedder, "name", "?"),
                     "usage": {"prompt_tokens": approx_tokens, "total_tokens": approx_tokens}}

    def models(self) -> dict[str, Any]:
        from .embed import EMBED_MODEL

        now = int(time.time())
        return {"object": "list", "data": [
            {"id": self.model.model, "object": "model", "created": now, "owned_by": "aiomim-shim"},
            {"id": getattr(self._embedder, "name", EMBED_MODEL), "object": "model", "created": now,
             "owned_by": "aiomim-shim"}]}


def _error(message: str, kind: str) -> dict[str, Any]:
    return {"error": {"message": message, "type": kind, "param": None, "code": kind}}


def _sse_chunks(resp: dict[str, Any], include_usage: bool) -> list[str]:
    """The whole reply as a minimal valid chat.completion.chunk event stream."""
    choice = resp["choices"][0]
    base = {"id": resp["id"], "object": "chat.completion.chunk", "created": resp["created"], "model": resp["model"]}
    events = [
        {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]},
        {**base, "choices": [{"index": 0, "delta": {"content": choice["message"]["content"]},
                              "finish_reason": None}]},
        {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": choice["finish_reason"]}]},
    ]
    if include_usage:
        events.append({**base, "choices": [], "usage": resp["usage"]})
    return [f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events] + ["data: [DONE]\n\n"]


def _handler(shim: Shim):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "aiomim-shim/1"

        def log_message(self, fmt, *args):  # quiet: the ledger is the record
            log.debug("shim %s", fmt % args)

        def _send(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _path(self) -> str:
            path = self.path.split("?", 1)[0].rstrip("/")
            return path[3:] if path.startswith("/v1") else path

        def do_GET(self):  # noqa: N802
            path = self._path()
            if path == "/models":
                self._send(200, shim.models())
            elif path in ("/health", ""):
                self._send(200, {"status": "ok", "stats": shim.stats})
            else:
                self._send(404, _error(f"no such endpoint: GET {self.path}", "not_found"))

        def do_POST(self):  # noqa: N802
            path = self._path()
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("body is not a JSON object")
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, _error(f"invalid JSON body: {exc}", "invalid_request_error"))
                return
            headers = dict(self.headers.items())
            try:
                if path == "/chat/completions":
                    status, resp = shim.chat(body, headers)
                    if status == 200 and body.get("stream"):
                        include = bool((body.get("stream_options") or {}).get("include_usage"))
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        for chunk in _sse_chunks(resp, include):
                            self.wfile.write(chunk.encode("utf-8"))
                        self.wfile.flush()
                        self.close_connection = True
                        return
                    self._send(status, resp)
                elif path == "/embeddings":
                    self._send(*shim.embeddings(body, headers))
                elif path in ("/completions", "/responses"):
                    self._send(400, _error(f"{path} is not supported: use /v1/chat/completions",
                                           "invalid_request_error"))
                else:
                    self._send(404, _error(f"no such endpoint: POST {self.path}", "not_found"))
            except Exception as exc:  # noqa: BLE001 - one bad request must not stop the server
                log.exception("shim: unhandled error")
                self._send(500, _error(f"{type(exc).__name__}: {exc}", "server_error"))

    return Handler


class ShimServer:
    """The adapter on 127.0.0.1, in a background thread. As a context manager it returns the base URL
    (`http://127.0.0.1:<port>/v1`); `port=0` picks a free port."""

    def __init__(self, *, port: int = 0, tag: str = "", ledger: str | Path | None = None,
                 effort: str = DEFAULT_EFFORT, max_concurrency: int = 6, shim: Shim | None = None):
        self.shim = shim or Shim(tag=tag, ledger=ledger, effort=effort, max_concurrency=max_concurrency)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), _handler(self.shim))
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}/v1"
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="aiomim-shim", daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m aiomim.external.shim", description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8765, help="0 picks a free port")
    ap.add_argument("--ledger", help="JSON-lines file, one line per request (appended)")
    ap.add_argument("--tag", default="", help="default tag of the ledger lines, e.g. paperqa2/108770")
    ap.add_argument("--effort", default=DEFAULT_EFFORT)
    ap.add_argument("--max-concurrency", type=int, default=6, help="simultaneous model calls")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ShimServer(port=args.port, tag=args.tag, ledger=args.ledger, effort=args.effort,
                        max_concurrency=args.max_concurrency)
    print(f"aiomim shim serving {server.shim.model.model} (effort {server.shim.model.effort}) at {server.base_url}",
          flush=True)

    def _term(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _term)
    try:
        server.httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.httpd.server_close()
        print(json.dumps(server.shim.stats), file=sys.stderr)


if __name__ == "__main__":
    main()
