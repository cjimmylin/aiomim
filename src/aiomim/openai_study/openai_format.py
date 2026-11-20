"""The OpenAI side of the wire: request lines for the Batch API and parsing of its output.

Request (one JSONL line per request, `POST /v1/responses`):

    {"custom_id": ..., "method": "POST", "url": "/v1/responses",
     "body": {"model": ..., "input": [{"role": "system", "content": <system prompt>},
                                      {"role": "user", "content": <prompt>}],
              "reasoning": {"effort": ...},
              "text": {"format": {"type": "json_schema", "name": ..., "schema": <the project's schema>,
                                  "strict": true}},
              "store": false}}

The schema is the one the project passes to the model (`llm.schema_for`), unchanged.
It is sent with `strict: true` when it already satisfies Structured Outputs' strict
subset (every object closed and every property required, only supported keywords),
which is true of every reply schema this study uses; otherwise it is sent non-strict
and the reply is validated by the project's own pydantic model when the project code
reads it back from the cache (it always is, either way).

Output (batch output and error files, one JSON object per line):

    {"id": ..., "custom_id": ..., "response": {"status_code": 200, "request_id": ...,
     "body": {"status": "completed" | "incomplete" | ..., "incomplete_details": {"reason": ...},
              "output": [{"type": "reasoning", ...},
                         {"type": "message", "content": [{"type": "output_text", "text": ...}
                                                         | {"type": "refusal", "refusal": ...}]}],
              "usage": {"input_tokens", "input_tokens_details": {"cached_tokens"},
                        "output_tokens", "output_tokens_details": {"reasoning_tokens"}}}},
     "error": null | {"code": ..., "message": ...}}

The parser is tolerant where the documentation leaves room: an error may come as
the line's `error`, as a non-200 `status_code` with `body.error`, or as a body with
status `failed`; a refusal is any content part of type `refusal`; a content-filter
stop is status `incomplete` with reason `content_filter` (or a content part or item
that says so); a top-level `output_text` string is accepted when no message parts
carry text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# Keywords Structured Outputs accepts in strict mode (the guide's "Supported schemas").
_STRICT_KEYS = {
    "type", "properties", "required", "additionalProperties", "items", "enum", "anyOf", "description",
    "$defs", "$ref", "const", "pattern", "format", "multipleOf", "maximum", "exclusiveMaximum", "minimum",
    "exclusiveMinimum", "minItems", "maxItems", "title",
}
_NAME_OK = re.compile(r"[^A-Za-z0-9_-]+")

TRANSIENT_CODES = {
    "batch_expired", "server_error", "rate_limit_exceeded", "timeout", "internal_error", "service_unavailable",
    "overloaded", "batch_cancelled", "request_timeout",
}
CONTENT_FILTER_REASONS = {"content_filter", "content_filtered", "safety"}


def strict_problems(schema: Any, path: str = "$") -> list[str]:
    """Why `schema` cannot be sent with `strict: true` (empty when it can)."""
    problems: list[str] = []
    if path == "$" and (not isinstance(schema, dict) or schema.get("type") != "object" or "anyOf" in schema):
        problems.append("$: the root must be an object schema without anyOf")
    if isinstance(schema, list):
        for i, item in enumerate(schema):
            problems += strict_problems(item, f"{path}[{i}]")
        return problems
    if not isinstance(schema, dict):
        return problems
    for key in schema:
        if key not in _STRICT_KEYS:
            problems.append(f"{path}: keyword {key!r} is not supported in strict mode")
    if schema.get("type") == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is not False:
            problems.append(f"{path}: additionalProperties must be false")
        if sorted(schema.get("required") or []) != sorted(props):
            problems.append(f"{path}: every property must be required")
        for name, sub in props.items():
            problems += strict_problems(sub, f"{path}.{name}")
    for key in ("items",):
        if key in schema:
            problems += strict_problems(schema[key], f"{path}.{key}")
    for key in ("anyOf",):
        for i, sub in enumerate(schema.get(key) or []):
            problems += strict_problems(sub, f"{path}.{key}[{i}]")
    for name, sub in (schema.get("$defs") or {}).items():
        problems += strict_problems(sub, f"{path}.$defs.{name}")
    return problems


def schema_name(label: str) -> str:
    """A `text.format.name`: letters, digits, '_' and '-', at most 64 characters."""
    return (_NAME_OK.sub("_", label).strip("_") or "reply")[:64]


def request_line(custom_id: str, *, model: str, effort: str, system: str, prompt: str, schema: dict[str, Any],
                 name: str, strict: bool, store: bool = False, max_output_tokens: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "input": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "reasoning": {"effort": effort},
        "text": {"format": {"type": "json_schema", "name": schema_name(name), "schema": schema, "strict": strict}},
        "store": store,
    }
    if max_output_tokens:
        body["max_output_tokens"] = int(max_output_tokens)
    return {"custom_id": custom_id, "method": "POST", "url": "/v1/responses", "body": body}


def request_parts(line: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """(system, prompt, schema) back out of a request line."""
    body = line["body"]
    system = prompt = ""
    for msg in body.get("input") or []:
        content = msg.get("content")
        if isinstance(content, list):   # content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        if msg.get("role") in ("system", "developer"):
            system = content or ""
        elif msg.get("role") == "user":
            prompt = content or ""
    return system, prompt, body["text"]["format"]["schema"]


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


@dataclass
class Reply:
    """One parsed output or error line.

    kind:
        ok              JSON text parsed (`data`); whether it fits the schema is decided
                        by the project's pydantic model when the task reads it back
        invalid         completed, but the text is missing or not JSON
        incomplete      cut short for a reason other than a content filter (max_output_tokens)
        refusal         the model refused (a `refusal` content part): a safety stop
        content_filter  generation halted by the content filter: a safety stop
        error           no model reply (request rejected, server error, expired)
    """

    custom_id: str
    kind: str
    data: Any = None
    text: str = ""
    refusal: str = ""
    status: str = ""
    reason: str = ""
    status_code: int | None = None
    error_code: str = ""
    error_message: str = ""
    transient: bool = False
    response_id: str = ""
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def stopped(self) -> bool:
        return self.kind in ("refusal", "content_filter")


def _usage(body: dict[str, Any]) -> dict[str, int]:
    u = body.get("usage") or {}
    details_in = u.get("input_tokens_details") or u.get("prompt_tokens_details") or {}
    details_out = u.get("output_tokens_details") or u.get("completion_tokens_details") or {}
    return {
        "input_tokens": int(u.get("input_tokens", u.get("prompt_tokens", 0)) or 0),
        "cached_tokens": int(details_in.get("cached_tokens", 0) or 0),
        "output_tokens": int(u.get("output_tokens", u.get("completion_tokens", 0)) or 0),
        "reasoning_tokens": int(details_out.get("reasoning_tokens", 0) or 0),
    }


def _is_transient(status_code: int | None, code: str) -> bool:
    if code and code.lower() in TRANSIENT_CODES:
        return True
    return status_code is not None and (status_code >= 500 or status_code in (408, 409, 429))


def parse_line(line: dict[str, Any] | str) -> Reply:
    """Parse one line of a batch output or error file. Never raises on content it does not expect."""
    if isinstance(line, str):
        line = json.loads(line)
    cid = str(line.get("custom_id") or "")
    response = line.get("response") or {}
    err = line.get("error")
    status_code = response.get("status_code") if isinstance(response, dict) else None
    body = response.get("body") if isinstance(response, dict) else None
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {"raw": body}
    body = body if isinstance(body, dict) else {}

    if err and not body:
        code = str((err or {}).get("code") or "")
        return Reply(cid, "error", status_code=status_code, error_code=code,
                     error_message=str((err or {}).get("message") or "")[:500], transient=_is_transient(status_code, code))
    if status_code is not None and status_code != 200:
        e = body.get("error") or err or {}
        code = str(e.get("code") or e.get("type") or "")
        return Reply(cid, "error", status_code=status_code, error_code=code,
                     error_message=str(e.get("message") or "")[:500], transient=_is_transient(status_code, code),
                     usage=_usage(body))

    status = str(body.get("status") or "")
    usage = _usage(body)
    rid = str(body.get("id") or "")
    if status in ("failed", "cancelled"):
        e = body.get("error") or {}
        code = str(e.get("code") or status)
        return Reply(cid, "error", status=status, status_code=status_code, error_code=code,
                     error_message=str(e.get("message") or "")[:500],
                     transient=_is_transient(status_code, code) or status == "cancelled", usage=usage, response_id=rid)

    texts: list[str] = []
    refusals: list[str] = []
    filtered = False
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                kind = part.get("type")
                if kind == "output_text":
                    texts.append(str(part.get("text") or ""))
                elif kind == "refusal":
                    refusals.append(str(part.get("refusal") or part.get("text") or "refused"))
                elif kind in ("content_filter", "content_filtered"):
                    filtered = True
    if not texts and isinstance(body.get("output_text"), str):
        texts.append(body["output_text"])
    reason = str((body.get("incomplete_details") or {}).get("reason") or "")
    if refusals:
        return Reply(cid, "refusal", refusal=" ".join(refusals)[:300], status=status, reason=reason,
                     status_code=status_code, usage=usage, response_id=rid)
    if filtered or (status == "incomplete" and reason in CONTENT_FILTER_REASONS):
        return Reply(cid, "content_filter", status=status, reason=reason or "content_filter",
                     status_code=status_code, usage=usage, response_id=rid)
    text = "".join(texts)
    if status == "incomplete":
        return Reply(cid, "incomplete", text=text, status=status, reason=reason or "unknown",
                     status_code=status_code, usage=usage, response_id=rid)
    if not text.strip():
        return Reply(cid, "invalid", status=status, reason="no output text", status_code=status_code,
                     usage=usage, response_id=rid)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return Reply(cid, "invalid", text=text, status=status, reason=f"not JSON: {exc.msg}",
                     status_code=status_code, usage=usage, response_id=rid)
    return Reply(cid, "ok", data=data, text=text, status=status, status_code=status_code, usage=usage,
                 response_id=rid)
