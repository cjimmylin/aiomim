"""Checks of what may be committed: JSON Schema conformance and no OMIM wording.

`OmimScanner` holds every 60-character window of the OMIM-authored texts the bundle
carries (the gold paragraphs, OMIM-sourced definitions, and the fixed fact lists),
case-folded with whitespace collapsed, as hashes. A file passes when none of its
60-character windows is one of them. Model-written drafts are allowed in git; a draft
that reproduces a window of OMIM's text is written with that span replaced (see
`redact`), and the report says how many were.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

WINDOW = 60
_WS = re.compile(r"\s+")
REDACTED = "[omitted: matches OMIM text]"


def _lower1(text: str) -> str:
    """Lower-case each character without changing the string's length."""
    return "".join(c.lower() if len(c.lower()) == 1 else c for c in text)


def normalize(text: str) -> str:
    return _lower1(_WS.sub(" ", text or "").strip())


class OmimScanner:
    """Every 60-character window of the OMIM-authored texts, as hashes; `items` are (ref, text) pairs.

    `ref` names the text without quoting it (a paragraph key, a fact id, a definition's MIM
    number), so a redacted span can be written down as pointers into the gold text and
    restored exactly wherever that text is at hand (`restore_entry`).
    """

    def __init__(self, items: Iterable[tuple[dict[str, Any], str] | str], window: int = WINDOW):
        self.window = window
        self.grams: set[int] = set()
        self.texts: list[tuple[dict[str, Any], str]] = []
        self._pos: dict[int, tuple[int, int]] | None = None
        for item in items:
            ref, text = (item if isinstance(item, tuple) else ({}, item))
            t = normalize(text)
            if len(t) < window:
                continue
            self.texts.append((ref, t))
            for i in range(len(t) - window + 1):
                self.grams.add(hash(t[i:i + window]))

    @property
    def n_texts(self) -> int:
        return len(self.texts)

    def spans(self, text: str) -> list[tuple[int, int]]:
        """Matching spans in `normalize(text)` (merged)."""
        t = normalize(text)
        w = self.window
        out: list[tuple[int, int]] = []
        for i in range(len(t) - w + 1):
            if hash(t[i:i + w]) in self.grams:
                if out and i <= out[-1][1]:
                    out[-1] = (out[-1][0], i + w)
                else:
                    out.append((i, i + w))
        return out

    def hits(self, text: str) -> int:
        return len(self.spans(text))

    def _positions(self) -> dict[int, tuple[int, int]]:
        if self._pos is None:
            pos: dict[int, tuple[int, int]] = {}
            w = self.window
            for ti, (_, t) in enumerate(self.texts):
                for i in range(len(t) - w + 1):
                    pos.setdefault(hash(t[i:i + w]), (ti, i))
            self._pos = pos
        return self._pos

    def _segments(self, t: str, a: int, b: int) -> list[dict[str, Any]] | None:
        """Pointers (text ref, start, length) whose gold characters spell t[a:b]."""
        pos, w = self._positions(), self.window
        segs: list[dict[str, Any]] = []
        i = a
        while i < b:
            found = None
            for j in range(i, max(a, i - w + 1) - 1, -1):     # a matching window that covers position i
                if j + w > len(t):
                    continue
                hit = pos.get(hash(t[j:j + w]))
                if hit is not None and self.texts[hit[0]][1][hit[1]:hit[1] + w] == t[j:j + w]:
                    found = (j, hit)
                    break
            if found is None:
                return None
            j, (ti, off) = found
            gold = self.texts[ti][1]
            start = off + (i - j)
            n = 0
            while i + n < b and start + n < len(gold) and gold[start + n] == t[i + n]:
                n += 1
            if n == 0:
                return None
            segs.append({"ref": self.texts[ti][0], "start": start, "length": n})
            i += n
        return segs

    def redact(self, text: str, records: list[dict[str, Any]] | None = None) -> tuple[str, int]:
        """The text (whitespace collapsed) with every matching span replaced by a marker.

        With `records`, each span is appended there as pointers into the gold text and the
        positions of its upper-case letters, enough to restore it (`restore_string`); the
        marker names the record's index.
        """
        squashed = _WS.sub(" ", text or "").strip()
        spans = self.spans(squashed)
        if not spans:
            return text, 0
        t = normalize(squashed)
        out, last = [], 0
        for a, b in spans:
            out.append(squashed[last:a])
            marker = REDACTED
            if records is not None:
                segs = self._segments(t, a, b)
                original = squashed[a:b]
                rec = {"k": len(records), "length": b - a, "segments": segs,
                       "upper": [i for i, (c, n) in enumerate(zip(original, t[a:b])) if c != n and c == n.upper()],
                       "other": {str(i): c for i, (c, n) in enumerate(zip(original, t[a:b]))
                                 if c != n and c != n.upper()}}
                records.append(rec)
                marker = f"[omitted: matches OMIM text; redaction {rec['k']}]"
            out.append(marker)
            last = b
        out.append(squashed[last:])
        return "".join(out), len(spans)


_MARKER = re.compile(r"\[omitted: matches OMIM text; redaction (\d+)\]")


def restore_string(text: str, records: list[dict[str, Any]], resolve) -> str:
    """Undo `redact`: `resolve(ref)` returns the gold text a pointer names (it is normalised here)."""
    by_k = {r["k"]: r for r in records}

    def one(m: re.Match) -> str:
        rec = by_k[int(m.group(1))]
        if not rec.get("segments"):
            raise ValueError(f"redaction {rec['k']} has no pointers")
        span = "".join(normalize(resolve(s["ref"]))[s["start"]:s["start"] + s["length"]] for s in rec["segments"])
        chars = list(span)
        for i in rec.get("upper", []):
            chars[i] = chars[i].upper()
        for i, c in (rec.get("other") or {}).items():
            chars[int(i)] = c
        return "".join(chars)

    return _MARKER.sub(one, text)


def restore_entry(entry: dict[str, Any], resolve) -> dict[str, Any]:
    """A redacted draft (outputs/drafts/...json) with its redacted spans put back."""
    records = (entry.get("meta") or {}).get("redactions") or []
    if not records:
        return entry

    def walk(node: Any) -> Any:
        if isinstance(node, str):
            return restore_string(node, records, resolve) if "[omitted: matches OMIM text;" in node else node
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items() if not (node is entry.get("meta") and k == "redactions")}
        return node

    out = walk(entry)
    out.setdefault("meta", {}).pop("redacted_spans_matching_omim", None)
    return out


def gold_texts_from_bundle(bundle_root: Path) -> list[tuple[dict[str, Any], str]]:
    """OMIM-authored texts in the bundle, with refs: gold paragraphs, OMIM-sourced definitions, fixed facts."""
    items: list[tuple[dict[str, Any], str]] = []
    root = Path(bundle_root)
    for gold_path in sorted((root / "entries").glob("*/gold.json")):
        items.extend(_gold_texts(json.loads(gold_path.read_text(encoding="utf-8"))))
    for rec_path in sorted((root / "factstore").glob("*/*.json")):
        if rec_path.parent.name == "avail":
            continue
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        items.extend(({"fact": f["id"]}, f.get("fact", "")) for f in rec.get("facts") or [])
    return items


def gold_texts_from_runs(run_dir: Path) -> list[tuple[dict[str, Any], str]]:
    """The same from a run folder (gold.json and gold_facts.json per entry): for the Claude Code side."""
    items: list[tuple[dict[str, Any], str]] = []
    for gold_path in sorted(Path(run_dir).glob("*/gold.json")):
        items.extend(_gold_texts(json.loads(gold_path.read_text(encoding="utf-8"))))
        gf = gold_path.parent / "gold_facts.json"
        if gf.exists():
            for para in json.loads(gf.read_text(encoding="utf-8")).get("paragraphs") or []:
                items.extend(({"fact": f["id"]}, f.get("fact", "")) for f in para.get("facts") or [])
    return items


def resolver(items: list[tuple[dict[str, Any], str]]):
    """`restore_entry`'s `resolve`: a pointer's gold text from (ref, text) pairs."""
    table = {json.dumps(ref, sort_keys=True): text for ref, text in items}

    def resolve(ref: dict[str, Any]) -> str:
        key = json.dumps(ref, sort_keys=True)
        if key not in table:
            raise KeyError(f"no gold text for {ref}")
        return table[key]

    return resolve


def _gold_texts(gold: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    from ..facts import paragraph_key

    out = []
    mim = gold.get("mim", "")
    for av in gold.get("allelic_variants") or []:
        for p in av.get("paragraphs") or []:
            out.append(({"paragraph": paragraph_key(p.get("text", ""))}, p.get("text", "")))
    if "omim" in str(gold.get("definition_source") or "").lower():
        out.append(({"definition": mim}, gold.get("definition") or ""))
    for name, text in (gold.get("omim_text") or {}).items():
        out.append(({"omim_text": mim, "section": name}, text or ""))
    for name, text in (gold.get("omim_clinical_synopsis") or {}).items():
        out.append(({"omim_synopsis": mim, "section": name}, text or ""))
    return out


def _strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

SCHEMA_FOR = (
    (re.compile(r"^marks/[^/]+/[^/]+\.json$"), "marks.schema.json"),
    (re.compile(r"^availability/[^/]+\.json$"), "availability.schema.json"),
    (re.compile(r"^drafts/[^/]+/[^/]+/entry\.[^/]+\.json$"), "draft.schema.json"),
    (re.compile(r"^summary\.json$"), "summary.schema.json"),
)
TEXT_FILES = (re.compile(r"^summary\.md$"), re.compile(r"^run_log\.md$"),
              re.compile(r"^drafts/[^/]+/[^/]+/entry\.[^/]+\.md$"), re.compile(r"^\.gitkeep$"),
              re.compile(r"^README\.md$"))


def schema_for(rel: str) -> str | None:
    for pattern, name in SCHEMA_FOR:
        if pattern.match(rel):
            return name
    return None


_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def mini_validate(schema: dict[str, Any], value: Any, path: str = "") -> list[tuple[str, str]]:
    """The JSON Schema keywords the kit's schemas use, for when `jsonschema` is not installed."""
    errs: list[tuple[str, str]] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            return [(path, f"{value!r:.60} is not of type {types}")]
    if "const" in schema and value != schema["const"]:
        errs.append((path, f"{value!r:.60} is not {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        errs.append((path, f"{value!r:.60} is not one of {schema['enum']}"))
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append((path, f"{value!r:.60} does not match {schema['pattern']!r}"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append((path, "string too long"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append((path, f"{value} is less than {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            errs.append((path, f"{value} is greater than {schema['maximum']}"))
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append((path, f"{k!r} is a required property"))
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs += mini_validate(props[k], v, f"{path}/{k}")
            elif schema.get("additionalProperties") is False:
                errs.append((path, f"additional property {k!r}"))
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += mini_validate(schema["additionalProperties"], v, f"{path}/{k}")
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append((path, "too many items"))
        if isinstance(schema.get("items"), dict):
            for i, v in enumerate(value):
                errs += mini_validate(schema["items"], v, f"{path}/{i}")
    if "anyOf" in schema and not any(not mini_validate(sub, value, path) for sub in schema["anyOf"]):
        errs.append((path, "matches none of anyOf"))
    if "not" in schema and not mini_validate(schema["not"], value, path):
        errs.append((path, "matches a forbidden schema"))
    return errs


def validate_dir(outputs: Path, schemas: Path, scanner: OmimScanner | None, *, also: Iterable[Path] = ()
                 ) -> dict[str, Any]:
    """Validate every file under `outputs` (and scan the files in `also`). Returns the problems found.

    Uses `jsonschema` (Draft 2020-12) when it is installed, else `mini_validate`."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - environment
        jsonschema = None

    loaded: dict[str, Any] = {}
    problems: list[str] = []
    n_files = n_json = 0
    for path in sorted(p for p in Path(outputs).rglob("*") if p.is_file()):
        rel = path.relative_to(outputs).as_posix()
        n_files += 1
        name = schema_for(rel)
        text = path.read_text(encoding="utf-8")
        if name is not None:
            n_json += 1
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                problems.append(f"{rel}: not JSON ({exc.msg})")
                continue
            if name not in loaded:
                loaded[name] = json.loads((Path(schemas) / name).read_text(encoding="utf-8"))
            if jsonschema is not None:
                validator = jsonschema.Draft202012Validator(loaded[name])
                errs = [("/".join(str(x) for x in e.path), e.message)
                        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))]
            else:
                errs = mini_validate(loaded[name], data)
            for where, msg in errs[:5]:
                problems.append(f"{rel}: schema {name}: {where or '(root)'}: {msg[:200]}")
            strings = list(_strings(data))
        elif any(p.match(rel) for p in TEXT_FILES):
            strings = [text]
        else:
            problems.append(f"{rel}: not a file the output spec defines")
            strings = [text]
        if scanner is not None:
            n_hits = sum(scanner.hits(s) for s in strings if len(s) >= scanner.window)
            if n_hits:
                problems.append(f"{rel}: {n_hits} span(s) match OMIM-authored text")
    for path in also:
        for p in sorted(Path(path).rglob("*.json")) if Path(path).is_dir() else [Path(path)]:
            if scanner is not None and p.exists():
                n_hits = scanner.hits(p.read_text(encoding="utf-8"))
                if n_hits:
                    problems.append(f"{p}: {n_hits} span(s) match OMIM-authored text")
    return {"files": n_files, "json_files": n_json, "problems": problems, "ok": not problems,
            "validator": "jsonschema" if jsonschema is not None else "built-in (jsonschema not installed)",
            "scanner": {"texts": scanner.n_texts, "windows": len(scanner.grams)} if scanner else None}
