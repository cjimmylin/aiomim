"""Waves through the cache: collect, submit, poll, ingest, step, smoke.

    collect   run every unfinished task offline; requests that miss the cache go into
              private/requests/wave_NNN[_pPP].jsonl (OpenAI format) with a private manifest,
              and state/waves/wave_NNN.json gets counts and the estimated cost
    submit    upload each part of the latest wave and create its batch; refuse a part whose
              estimated cost would take the spend past the cap
    poll      check the open batches; download output and error files when they end
    ingest    write every reply into the study's cache under the key the task will look up,
              with meta (model, effort, tokens, cost, safety_stops, provider, batch id);
              update the ledger
    step      poll -> ingest -> collect -> submit: one idempotent advance; state/status.json

State that is committed (state/) carries ids, counts and costs only. Prompts, replies and
anything derived from OMIM's text stay in private/.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..cache import DiskCache
from .backend import Recorder, label_for
from .config import Study, StudyPaths, now, read_json, write_json, write_text
from .errors import StudyError
from .openai_format import parse_line
from .providers import TERMINAL
from .tasks import (
    FINAL,
    Bundle,
    Context,
    Outcome,
    TaskSpec,
    plan_tasks,
    run_all,
    write_result,
)

log = logging.getLogger(__name__)

VERIFIABLE_KINDS = ("A1", "A2F", "A2C", "A3")
# Requests of the writers whose prompt depends on nothing the new model wrote: they must equal the
# original runs' prompts (checked against the bundle's verification keys on wave 1).
VERIFIABLE_WRITER_LABELS = ("synthesize:direct", "extract", "recall:closedbook")


# --------------------------------------------------------------------------- #
# State files
# --------------------------------------------------------------------------- #


def tasks_state(paths: StudyPaths) -> dict[str, Any]:
    st = read_json(paths.state / "tasks.json")
    if st is None:
        raise StudyError("no task list yet: run `plan` first")
    return st


def save_tasks(paths: StudyPaths, st: dict[str, Any]) -> None:
    counts = defaultdict(int)
    for t in st["tasks"].values():
        counts[t["status"]] += 1
    st["counts"] = dict(sorted(counts.items()))
    st["updated_at"] = now()
    write_json(paths.state / "tasks.json", st)


def batches_state(paths: StudyPaths) -> dict[str, Any]:
    return read_json(paths.state / "batches.json", {"batches": []})


def save_batches(paths: StudyPaths, st: dict[str, Any]) -> None:
    write_json(paths.state / "batches.json", st)


def ledger(paths: StudyPaths) -> dict[str, Any]:
    return read_json(paths.state / "ledger.json", {"waves": {}, "totals": {}})


def save_ledger(paths: StudyPaths, led: dict[str, Any]) -> None:
    totals: dict[str, float] = defaultdict(float)
    for w in led["waves"].values():
        for k, v in (w.get("total") or {}).items():
            totals[k] += v
    led["totals"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sorted(totals.items())}
    led["updated_at"] = now()
    write_json(paths.state / "ledger.json", led)


def spent_usd(paths: StudyPaths) -> float:
    return float((ledger(paths).get("totals") or {}).get("cost_usd", 0.0))


def open_batches(paths: StudyPaths) -> list[dict[str, Any]]:
    return [b for b in batches_state(paths)["batches"] if not b.get("ingested")]


# --------------------------------------------------------------------------- #
# plan
# --------------------------------------------------------------------------- #


def plan(paths: StudyPaths, study: Study) -> dict[str, Any]:
    """Build (or extend) state/tasks.json from study.json; finished tasks keep their status."""
    old = read_json(paths.state / "tasks.json", {"tasks": {}}) or {"tasks": {}}
    tasks: dict[str, Any] = {}
    for spec in plan_tasks(study):
        prev = old["tasks"].get(spec.id)
        tasks[spec.id] = prev or {"kind": spec.kind, "mim": spec.mim, "variant": spec.variant, "status": "pending",
                                  "waves": [], "requests": 0}
    dropped = sorted(set(old["tasks"]) - set(tasks))
    st = {"study": "openai_second_model", "model": study.model, "tasks": tasks, "dropped_from_plan": dropped,
          "created_at": old.get("created_at") or now()}
    save_tasks(paths, st)
    return st


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #


def _wave_files(paths: StudyPaths, n: int) -> tuple[Path, Path]:
    return paths.requests / f"wave_{n:03d}.jsonl.partial", paths.requests / f"wave_{n:03d}.manifest.json"


def next_wave(paths: StudyPaths) -> int:
    """The number the next collect writes: the latest wave again if none of it was submitted yet."""
    waves = sorted(int(p.stem.split("_")[1]) for p in paths.waves.glob("wave_*.json"))
    if not waves:
        return 1
    last = waves[-1]
    submitted = any(b["wave"] == last for b in batches_state(paths)["batches"])
    return last if not submitted else last + 1


def _calibration(paths: StudyPaths, study: Study) -> dict[str, dict[str, float]]:
    """Measured characters per input token and output tokens per request, by label (from the ledger)."""
    led = ledger(paths)
    agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for w in led["waves"].values():
        for label, c in (w.get("by_label") or {}).items():
            for k in ("replies", "chars_replied", "input_tokens", "output_tokens"):
                agg[label][k] += c.get(k, 0) or 0
    out = {}
    for label, c in agg.items():
        if c["replies"] >= int(study.setting("estimation", "calibrate_after_replies", default=20)) \
                and c["input_tokens"] > 0:
            out[label] = {"chars_per_token": c["chars_replied"] / c["input_tokens"],
                          "output_tokens": c["output_tokens"] / c["replies"]}
    return out


def estimate(study: Study, entries: list[dict[str, Any]], calib: dict[str, dict[str, float]] | None = None
             ) -> dict[str, float]:
    calib = calib or {}
    inp = out = 0.0
    for e in entries:
        c = calib.get(e["label"]) or {}
        inp += e["chars"] / (c.get("chars_per_token") or study.chars_per_token(e["label"]))
        out += c.get("output_tokens") or study.expected_output_tokens(e["label"])
    return {"requests": len(entries), "est_input_tokens": int(inp), "est_output_tokens": int(out),
            "est_cost_usd": round(study.cost(int(inp), 0, int(out)), 4)}


def _verify_keys(bundle: Bundle) -> tuple[set[str], set[str]] | None:
    path = bundle.root / "verify" / "prompt_keys.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("hit", [])), set(data.get("miss", []))


def _verifiable(entry: dict[str, Any]) -> bool:
    """A request whose prompt the bundle verification fixed: attempt 1, no coverage note, and either a
    judge task (its prompts depend only on the bundle) or a writer's first call."""
    kinds = {t.split(":")[0] for t in entry["tasks"]}
    if entry["attempt"] != 1 or entry.get("retry_note"):
        return False
    if kinds & set(VERIFIABLE_KINDS):
        return True
    return entry["label"] in VERIFIABLE_WRITER_LABELS and bool(kinds & {"B1", "B2"})


def collect(paths: StudyPaths, study: Study, *, jobs: int | None = None, force: bool = False,
            kinds: list[str] | None = None, retry_failed: bool = False) -> dict[str, Any]:
    """Run every unfinished task offline; write the wave's request files. Returns the wave's summary."""
    from .offline import NETWORK_ATTEMPTS, activate, network_blocked

    st = tasks_state(paths)
    if st.get("model") and st["model"] != study.model:
        raise StudyError(f"study.json names {study.model} but this study's tasks were planned for {st['model']}: "
                         "the model is part of every cache key; use a fresh study directory for another model")
    if open_batches(paths) and not force:
        raise StudyError("a batch of the previous wave is still open: poll and ingest it first (or use step)")
    bundle = Bundle(paths.bundle)
    n = next_wave(paths)
    raw, manifest_path = _wave_files(paths, n)
    for old in paths.requests.glob(f"wave_{n:03d}_p*.jsonl"):
        old.unlink()
    recorder = Recorder(study, raw)
    todo = [TaskSpec.parse(tid) for tid, t in st["tasks"].items()
            if (t["status"] not in FINAL or (retry_failed and t["status"] == "failed"))
            and (kinds is None or t["kind"] in kinds)]
    attempts_before = len(NETWORK_ATTEMPTS)
    finished: dict[str, int] = defaultdict(int)
    outcomes: list[Outcome] = []
    try:
        with network_blocked():
            settings = activate(paths, study)
            ctx = Context(paths, study, bundle, settings, recorder)

            def done(o: Outcome) -> None:
                if o.status in FINAL:
                    write_result(paths, o)

            outcomes = run_all(ctx, todo, jobs or int(study.setting("concurrency", "tasks", default=8)),
                               on_done=done)
    finally:
        recorder.close()
    network_attempts = len(NETWORK_ATTEMPTS) - attempts_before

    errors = []
    for o in outcomes:
        t = st["tasks"][o.spec.id]
        t["status"] = o.status
        t["requests"] = t.get("requests", 0) + o.requests
        if o.status == "waiting":
            t["waves"] = sorted(set(t.get("waves", [])) | {n})
            if o.requests == 0:
                errors.append(f"{o.spec.id}: waiting without a recorded request")
        elif o.status in FINAL:
            finished[o.status] += 1
            t["finished_at_wave"] = n
            t["detail"] = {k: v for k, v in ((o.payload or {}).get("detail") or {}).items()
                           if isinstance(v, (int, float, str, bool, type(None)))}
        if o.status == "error":
            t["error"] = o.message[:300]
            errors.append(f"{o.spec.id}: {o.message[:300]}")
        else:
            t.pop("error", None)
        if o.stops_not_sent:
            t["stops_not_sent"] = o.stops_not_sent
    save_tasks(paths, st)

    entries = list(recorder.entries.values())
    for e in entries:
        e["tasks"] = sorted(e["tasks"])
    summary: dict[str, Any] = {"wave": n, "collected_at": now(), "tasks_run": len(todo),
                               "tasks_finished": dict(finished),
                               "tasks_waiting": sum(1 for o in outcomes if o.status == "waiting"),
                               "task_errors": len(errors), "network_attempts": network_attempts,
                               "requests": len(entries)}
    if not entries:
        raw.unlink(missing_ok=True)
        summary["parts"] = []
        _write_wave_errors(paths, n, errors)
        return summary

    # Did the code build the same prompts the bundle was verified with?
    keys = _verify_keys(bundle)
    drift = {"checked": 0, "identical_to_original_runs": 0, "same_as_bundle_verification": 0, "not_matched": 0}
    for e in entries:
        if keys is None or not _verifiable(e):
            continue
        drift["checked"] += 1
        hit, miss = keys
        if e["claude_key"] in hit:
            drift["identical_to_original_runs"] += 1
        if e["claude_key"] in hit or e["claude_key"] in miss:
            drift["same_as_bundle_verification"] += 1
        else:
            drift["not_matched"] += 1
    summary["prompt_check"] = drift if keys is not None else "no verification keys in the bundle"

    parts = _split_parts(paths, study, n, raw, entries)
    calib = _calibration(paths, study)
    by_label: dict[str, list] = defaultdict(list)
    by_kind: dict[str, list] = defaultdict(list)
    for e in entries:
        by_label[e["label"]].append(e)
        by_kind[e["tasks"][0].split(":")[0]].append(e)
    summary.update(
        parts=[{k: v for k, v in p.items() if k != "custom_ids"} for p in parts],
        estimate=estimate(study, entries, calib),
        by_label={k: estimate(study, v, calib) for k, v in sorted(by_label.items())},
        by_task_kind={k: estimate(study, v, calib) for k, v in sorted(by_kind.items())},
        retries={"attempt_2": sum(1 for e in entries if e["attempt"] == 2),
                 "with_coverage_note": sum(1 for e in entries if e["retry_note"])},
        calibrated_labels=sorted(calib),
    )
    write_json(manifest_path, {"wave": n, "model": study.model, "requests": entries})
    write_json(paths.waves / f"wave_{n:03d}.json", summary)
    _write_wave_errors(paths, n, errors)
    return summary


def _write_wave_errors(paths: StudyPaths, n: int, errors: list[str]) -> None:
    if errors:
        write_text(paths.logs / f"wave_{n:03d}.errors.txt", "\n".join(errors) + "\n")


def _split_parts(paths: StudyPaths, study: Study, n: int, raw: Path, entries: list[dict[str, Any]]
                 ) -> list[dict[str, Any]]:
    """Cut the wave into batch files within the Batch API's limits (50,000 requests, 200 MB per file)."""
    max_req = int(study.setting("batch", "max_requests_per_file", default=20000))
    max_bytes = int(study.setting("batch", "max_bytes_per_file", default=150_000_000))
    by_cid = {e["custom_id"]: e for e in entries}
    parts: list[dict[str, Any]] = []
    fh = None
    cur: dict[str, Any] | None = None
    calib = _calibration(paths, study)

    def close() -> None:
        nonlocal fh, cur
        if fh:
            fh.close()
            fh = None
        if cur:
            est = estimate(study, [by_cid[c] for c in cur["custom_ids"]], calib)
            cur.update(est)
            parts.append(cur)
            cur = None

    with open(raw, encoding="utf-8") as src:
        for line in src:
            if not line.strip():
                continue
            cid = json.loads(line)["custom_id"]
            size = len(line.encode("utf-8"))
            if cur is None or cur["requests_in_file"] >= max_req or cur["bytes"] + size > max_bytes:
                close()
                k = len(parts) + 1
                path = paths.requests / f"wave_{n:03d}_p{k:02d}.jsonl"
                fh = open(path, "w", encoding="utf-8")
                cur = {"part": k, "file": str(path.relative_to(paths.root)), "requests_in_file": 0, "bytes": 0,
                       "custom_ids": []}
            fh.write(line)
            cur["requests_in_file"] += 1
            cur["bytes"] += size
            cur["custom_ids"].append(cid)
            by_cid[cid]["part"] = cur["part"]
    close()
    raw.unlink()
    return parts


# --------------------------------------------------------------------------- #
# submit / poll / ingest
# --------------------------------------------------------------------------- #


def submit(paths: StudyPaths, study: Study, provider) -> dict[str, Any]:
    """Create a batch for every part of the latest wave not yet submitted, within the cap."""
    waves = sorted(paths.waves.glob("wave_*.json"))
    if not waves:
        return {"submitted": [], "reason": "nothing collected"}
    wave = read_json(waves[-1])
    n = wave["wave"]
    bst = batches_state(paths)
    done_parts = {b["part"] for b in bst["batches"] if b["wave"] == n}
    cap = study.cap_usd
    spent = spent_usd(paths)
    in_flight = sum(b.get("est_cost_usd", 0.0) for b in bst["batches"] if not b.get("ingested"))
    max_tokens = study.setting("batch", "max_enqueued_est_tokens")
    enq = sum(b.get("est_input_tokens", 0) for b in bst["batches"]
              if b.get("status") not in TERMINAL and not b.get("ingested"))
    out: dict[str, Any] = {"wave": n, "submitted": [], "spent_usd": round(spent, 4), "cap_usd": cap}
    for part in wave.get("parts", []):
        if part["part"] in done_parts:
            continue
        if spent + in_flight + part["est_cost_usd"] > cap:
            out["blocked"] = (f"cost cap: spent ${spent:.2f} + open ${in_flight:.2f} + this batch's estimate "
                              f"${part['est_cost_usd']:.2f} would pass the cap of ${cap:.2f}")
            break
        if max_tokens and out["submitted"] and enq + part["est_input_tokens"] > int(max_tokens):
            out["deferred"] = "enqueued-token limit of study.json: the remaining parts go in a later step"
            break
        file_id = provider.upload(paths.root / part["file"])
        batch = provider.create(file_id, {"wave": f"{n:03d}", "part": f"{part['part']:02d}"})
        rec = {"wave": n, "part": part["part"], "batch_id": batch["id"], "input_file_id": file_id,
               "status": batch.get("status", "validating"), "submitted_at": now(),
               "requests": part["requests_in_file"], "est_cost_usd": part["est_cost_usd"],
               "est_input_tokens": part["est_input_tokens"], "ingested": False, "downloaded": False}
        bst["batches"] = [b for b in bst["batches"] if not (b["wave"] == n and b["part"] == part["part"])]
        bst["batches"].append(rec)
        save_batches(paths, bst)
        _count_sends(paths, n, part["part"])
        in_flight += part["est_cost_usd"]
        enq += part["est_input_tokens"]
        out["submitted"].append(rec["batch_id"])
    return out


def _count_sends(paths: StudyPaths, n: int, part: int) -> None:
    sent = read_json(paths.private_ledger, {}) or {}
    manifest = read_json(paths.requests / f"wave_{n:03d}.manifest.json", {}) or {}
    for e in manifest.get("requests", []):
        if e.get("part") == part:
            sent[e["custom_id"]] = sent.get(e["custom_id"], 0) + 1
    write_json(paths.private_ledger, sent, indent=None)


def poll(paths: StudyPaths, provider) -> dict[str, Any]:
    """Check every open batch; download its files once it has ended."""
    bst = batches_state(paths)
    seen = []
    for b in bst["batches"]:
        if b.get("ingested") or b.get("downloaded"):
            continue
        info = provider.retrieve(b["batch_id"])
        b["status"] = info.get("status")
        b["request_counts"] = info.get("request_counts")
        if info.get("usage"):
            b["usage"] = info["usage"]
        if b["status"] in TERMINAL:
            b["ended_at"] = now()
            for key, suffix in (("output_file_id", "output"), ("error_file_id", "errors")):
                fid = info.get(key)
                if fid:
                    dest = paths.responses / f"{b['batch_id']}.{suffix}.jsonl"
                    provider.download(fid, dest)
                    b[key] = fid
            b["downloaded"] = True
            if b["status"] == "failed":
                errs = ((info.get("errors") or {}).get("data") or [])
                b["failure"] = [{"code": e.get("code"), "message": str(e.get("message"))[:200]} for e in errs[:5]]
        seen.append({"batch_id": b["batch_id"], "status": b["status"], "counts": b.get("request_counts")})
        save_batches(paths, bst)
    return {"polled": seen}


def _manifest_index(paths: StudyPaths, n: int) -> dict[str, dict[str, Any]]:
    data = read_json(paths.requests / f"wave_{n:03d}.manifest.json", {}) or {}
    return {e["custom_id"]: e for e in data.get("requests", [])}


def ingest(paths: StudyPaths, study: Study) -> dict[str, Any]:
    """Write every downloaded reply into the study's cache; update the ledger."""
    cache = DiskCache(paths.home / "cache" / "llm")
    bst = batches_state(paths)
    led = ledger(paths)
    sent = read_json(paths.private_ledger, {}) or {}
    max_transport = int(study.setting("retries", "transport", default=3))
    out: dict[str, Any] = {"ingested": [], "blocked": None}
    for b in bst["batches"]:
        if b.get("ingested") or not b.get("downloaded"):
            continue
        n = b["wave"]
        manifest = _manifest_index(paths, n)
        part_ids = {cid for cid, e in manifest.items() if e.get("part") == b["part"]}
        wl = led["waves"].setdefault(f"{n:03d}", {"batches": [], "by_label": {}, "by_task_kind": {}, "total": {}})
        if b["batch_id"] not in wl["batches"]:
            wl["batches"].append(b["batch_id"])
        seen: set[str] = set()
        counts = defaultdict(int)
        for suffix in ("output", "errors"):
            path = paths.responses / f"{b['batch_id']}.{suffix}.jsonl"
            if not path.exists():
                continue
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                reply = parse_line(raw)
                entry = manifest.get(reply.custom_id)
                if entry is None or reply.custom_id in seen:
                    counts["unknown_or_duplicate"] += 1
                    continue
                seen.add(reply.custom_id)
                outcome = _store_reply(cache, study, b, entry, reply, sent.get(reply.custom_id, 1), max_transport,
                                       paths.logs)
                counts[outcome] += 1
                _ledger_add(wl, study, entry, reply, outcome)
        # Requests the batch never answered (a failed batch, or lines missing) are asked again next wave.
        for cid in part_ids - seen:
            counts["not_answered"] += 1
            if sent.get(cid, 0) >= max_transport and b.get("status") != "failed":
                _store_failure(cache, study, b, manifest[cid], "no reply after repeated sends")
        if b.get("status") == "failed":
            # Validation failed (e.g. an enqueued-token limit): the requests were never run; not a send.
            for cid in part_ids:
                sent[cid] = max(0, sent.get(cid, 1) - 1)
            codes = ", ".join(sorted({str(f.get("code")) for f in b.get("failure") or []})) or "unknown"
            out["blocked"] = (f"batch {b['batch_id']} failed validation ({codes}); its requests will be asked again. "
                              "If the reason is a token or size limit, lower batch.max_requests_per_file or set "
                              "batch.max_enqueued_est_tokens in study.json, then run step again")
        b["ingested"] = True
        b["ingested_at"] = now()
        b["outcomes"] = dict(counts)
        rejected = counts.get("rejected", 0)
        if rejected and rejected > 0.05 * max(1, len(part_ids)):
            out["blocked"] = (f"batch {b['batch_id']}: {rejected} of {len(part_ids)} requests were rejected by the "
                              "API; see private/logs/rejections.jsonl before going on")
        out["ingested"].append({"batch_id": b["batch_id"], **counts})
    save_batches(paths, bst)
    write_json(paths.private_ledger, sent, indent=None)
    save_ledger(paths, led)
    return out


def _meta(study: Study, b: dict[str, Any], entry: dict[str, Any], reply) -> dict[str, Any]:
    u = reply.usage
    return {"model": study.model, "effort": entry["effort"], "openai_effort": entry.get("openai_effort"),
            "input_tokens": u.get("input_tokens", 0), "cached_tokens": u.get("cached_tokens", 0),
            "output_tokens": u.get("output_tokens", 0), "reasoning_tokens": u.get("reasoning_tokens", 0),
            "cost_usd": round(study.cost(u.get("input_tokens", 0), u.get("cached_tokens", 0),
                                         u.get("output_tokens", 0)), 6),
            "seconds": 0, "turns": 1, "safety_stops": 1 if reply.stopped else 0, "provider": "openai",
            "batch_id": b["batch_id"], "custom_id": entry["custom_id"], "response_id": reply.response_id,
            "attempt": entry["attempt"], "reply_kind": reply.kind, "label": entry["label"]}


def _store_reply(cache: DiskCache, study: Study, b: dict[str, Any], entry: dict[str, Any], reply, sends: int,
                 max_transport: int, logs: Path) -> str:
    key = entry["storage_key"]
    if reply.kind == "error":
        if reply.transient and sends < max_transport:
            return "transient"          # not cached: the next collect asks again under the same custom_id
        log_rejection = {"custom_id": entry["custom_id"], "status_code": reply.status_code,
                         "code": reply.error_code, "message": reply.error_message[:300], "at": now()}
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / "rejections.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_rejection) + "\n")
        _store_failure(cache, study, b, entry, f"{reply.error_code or reply.status_code}", reply)
        return "transient_exhausted" if reply.transient else "rejected"
    meta = _meta(study, b, entry, reply)
    if reply.stopped:
        meta["stop"] = reply.kind
        cache.put_json(key, {"data": {}, "meta": meta})
        return "stop"
    if reply.kind == "ok":
        cache.put_json(key, {"data": reply.data, "meta": meta})
        return "ok"
    # invalid or incomplete: cached as an unusable reply; the project's code rejects it and the backend
    # asks once more under the retry key (or, for the retry itself, the project gives up).
    meta["unusable"] = reply.reason or reply.kind
    cache.put_json(key, {"data": None, "meta": meta})
    return reply.kind


def _store_failure(cache: DiskCache, study: Study, b: dict[str, Any], entry: dict[str, Any], why: str,
                   reply=None) -> None:
    meta = {"model": study.model, "effort": entry["effort"], "input_tokens": 0, "output_tokens": 0,
            "cost_usd": 0.0, "safety_stops": 0, "provider": "openai", "batch_id": b["batch_id"],
            "custom_id": entry["custom_id"], "attempt": entry["attempt"], "unusable": f"no reply: {why}",
            "label": entry["label"]}
    cache.put_json(entry["storage_key"], {"data": None, "meta": meta})


_LEDGER_KEYS = ("requests", "replies", "ok", "invalid", "incomplete", "stops", "transient", "rejected",
                "input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "cost_usd", "chars_replied")


def _ledger_add(wl: dict[str, Any], study: Study, entry: dict[str, Any], reply, outcome: str) -> None:
    u = reply.usage
    cost = study.cost(u.get("input_tokens", 0), u.get("cached_tokens", 0), u.get("output_tokens", 0))
    kind = entry["tasks"][0].split(":")[0] if entry.get("tasks") else "other"
    for cell in (wl["by_label"].setdefault(entry["label"], {}), wl["by_task_kind"].setdefault(kind, {}),
                 wl["total"]):
        for k in _LEDGER_KEYS:
            cell.setdefault(k, 0)
        cell["requests"] += 1
        if reply.kind != "error":
            cell["replies"] += 1
            cell["chars_replied"] += entry["chars"]
        if outcome == "ok":
            cell["ok"] += 1
        elif outcome == "stop":
            cell["stops"] += 1
        elif outcome in ("invalid", "incomplete"):
            cell[outcome] += 1
        elif outcome == "transient":
            cell["transient"] += 1
        elif outcome in ("rejected", "transient_exhausted"):
            cell["rejected"] += 1
        cell["input_tokens"] += u.get("input_tokens", 0)
        cell["cached_tokens"] += u.get("cached_tokens", 0)
        cell["output_tokens"] += u.get("output_tokens", 0)
        cell["reasoning_tokens"] += u.get("reasoning_tokens", 0)
        cell["cost_usd"] = round(cell["cost_usd"] + cost, 6)


# --------------------------------------------------------------------------- #
# step
# --------------------------------------------------------------------------- #


def step(paths: StudyPaths, study: Study, provider, *, jobs: int | None = None) -> dict[str, Any]:
    """One idempotent advance: poll -> ingest -> collect -> submit. Writes state/status.json."""
    try:
        return _step(paths, study, provider, jobs=jobs)
    except StudyError as exc:
        return _finish(paths, study, {"model": study.model, "cap_usd": study.cap_usd}, "blocked", str(exc))


def _step(paths: StudyPaths, study: Study, provider, *, jobs: int | None = None) -> dict[str, Any]:
    if not (paths.state / "tasks.json").exists():
        plan(paths, study)
    status: dict[str, Any] = {"model": study.model, "cap_usd": study.cap_usd}
    if study.setting("require_smoke", default=True) and not smoke_passed(paths):
        sm = read_json(paths.state / "smoke.json", {}) or {}
        if not sm.get("batch_id"):
            return _finish(paths, study, status, "blocked", "the smoke batch has not been sent: run `smoke` first")
        sm = smoke(paths, study, provider, jobs=jobs)          # polls it and, once it has ended, checks it
        if not sm.get("ended"):
            return _finish(paths, study, status, "waiting_for_batch", "the smoke batch is still running",
                           batches=[{"batch_id": sm["batch_id"], "status": sm.get("status")}])
        if not sm.get("passed"):
            return _finish(paths, study, status, "blocked",
                           "the smoke batch failed: " + "; ".join(sm.get("problems") or ["see state/smoke.json"]))
    polled = poll(paths, provider)
    ing = ingest(paths, study)
    status["polled"] = polled["polled"]
    if ing.get("blocked"):
        return _finish(paths, study, status, "blocked", ing["blocked"])
    still_open = [b for b in batches_state(paths)["batches"] if not b.get("ingested")]
    if still_open:
        return _finish(paths, study, status, "waiting_for_batch",
                       f"{len(still_open)} batch(es) still running", batches=still_open)
    # Parts of the current wave that were collected but not yet submitted (cap or token limit earlier)
    pending_parts = _unsubmitted_parts(paths)
    if pending_parts:
        sub = submit(paths, study, provider)
        status["submit"] = sub
        if sub.get("blocked") and not sub["submitted"]:
            return _finish(paths, study, status, "blocked", sub["blocked"])
        return _finish(paths, study, status, "waiting_for_batch", "submitted the remaining parts of the wave",
                       batches=[b for b in batches_state(paths)["batches"] if not b.get("ingested")])
    col = collect(paths, study, jobs=jobs)
    status["collect"] = {k: col.get(k) for k in ("wave", "requests", "tasks_waiting", "tasks_finished",
                                                 "task_errors", "network_attempts", "estimate", "prompt_check")}
    if col.get("network_attempts"):
        return _finish(paths, study, status, "blocked", "collect attempted network access (see private/logs)")
    pc = col.get("prompt_check")
    if isinstance(pc, dict) and pc.get("not_matched"):
        return _finish(paths, study, status, "blocked",
                       f"{pc['not_matched']} request(s) differ from the prompts the bundle was verified with: "
                       "the checkout's code is not the code the bundle was built for")
    if col.get("task_errors"):
        return _finish(paths, study, status, "blocked",
                       f"{col['task_errors']} task(s) hit a kit or environment error (state/tasks.json, "
                       f"private/logs/wave_{col['wave']:03d}.errors.txt)")
    if col["requests"]:
        sub = submit(paths, study, provider)
        status["submit"] = sub
        if sub.get("blocked") and not sub["submitted"]:
            return _finish(paths, study, status, "blocked", sub["blocked"])
        return _finish(paths, study, status, "waiting_for_batch", f"wave {col['wave']} submitted",
                       batches=[b for b in batches_state(paths)["batches"] if not b.get("ingested")])
    st = tasks_state(paths)
    if all(t["status"] in FINAL for t in st["tasks"].values()):
        return _finish(paths, study, status, "done", "every task has finished; run `report` and `validate`")
    return _finish(paths, study, status, "blocked", "tasks are unfinished but nothing is left to ask")


def _unsubmitted_parts(paths: StudyPaths) -> list[int]:
    waves = sorted(paths.waves.glob("wave_*.json"))
    if not waves:
        return []
    wave = read_json(waves[-1])
    subs = {b["part"] for b in batches_state(paths)["batches"] if b["wave"] == wave["wave"]}
    if not subs:
        return []      # a wave never submitted is re-collected (prompts may depend on what came back since)
    return [p["part"] for p in wave.get("parts", []) if p["part"] not in subs]


def _finish(paths: StudyPaths, study: Study, status: dict[str, Any], phase: str, why: str,
            batches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    st = read_json(paths.state / "tasks.json", {"tasks": {}}) or {"tasks": {}}
    counts = defaultdict(int)
    for t in st["tasks"].values():
        counts[t["status"]] += 1
    waves = sorted(int(p.stem.split("_")[1]) for p in paths.waves.glob("wave_*.json"))
    led = (ledger(paths).get("totals") or {})
    sm = read_json(paths.state / "smoke.json", {}) or {}
    submitted = sum(b.get("requests", 0) for b in batches_state(paths)["batches"]) + int(sm.get("requests", 0) or 0)
    status.update(phase=phase, reason=why, wave=waves[-1] if waves else 0, tasks=dict(sorted(counts.items())),
                  tasks_planned=sum(counts.values()), tasks_finished=sum(v for k, v in counts.items() if k in FINAL),
                  requests={"submitted": submitted, "replies": int(led.get("replies", 0)),
                            "completed": int(led.get("ok", 0)), "refused": int(led.get("stops", 0)),
                            "failed": int(led.get("invalid", 0) + led.get("incomplete", 0) + led.get("rejected", 0)),
                            "asked_again_after_transport_errors": int(led.get("transient", 0))},
                  smoke={"sent": bool(sm.get("batch_id")), "ended": bool(sm.get("ended")),
                         "passed": bool(sm.get("passed")), "problems": sm.get("problems") or []},
                  spent_usd=round(spent_usd(paths), 4), updated_at=now(),
                  open_batches=[{"batch_id": b["batch_id"], "status": b.get("status"),
                                 "counts": b.get("request_counts")} for b in (batches or [])])
    write_json(paths.state / "status.json", status)
    _append_run_log(paths, status)
    return status


def _append_run_log(paths: StudyPaths, status: dict[str, Any]) -> None:
    path = paths.outputs / "run_log.md"
    if not path.exists():
        write_text(path, "# Run log\n\nOne line per `step`: time (UTC), wave, batches, phase, spend so far.\n\n"
                         "| Time | Wave | Batches | Phase | Reason | Spent (USD) |\n|---|---|---|---|---|---|\n")
    ids = ", ".join(b["batch_id"] for b in status.get("open_batches") or []) or "-"
    reason = str(status.get("reason", "")).replace("|", "/")[:160]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"| {status['updated_at']} | {status.get('wave', 0)} | {ids} | {status['phase']} | {reason} | "
                 f"{status['spent_usd']:.2f} |\n")


def status_line(status: dict[str, Any]) -> str:
    t = status.get("tasks", {})
    done = sum(v for k, v in t.items() if k in FINAL)
    total = sum(t.values())
    return (f"{status['phase']}: {status.get('reason', '')} | wave {status.get('wave', 0)} | tasks {done}/{total} "
            f"finished | spent ${status.get('spent_usd', 0):.2f} of ${status.get('cap_usd', 0):.2f}")


# --------------------------------------------------------------------------- #
# smoke
# --------------------------------------------------------------------------- #

SMOKE_LABELS = ("judge:mark", "judge:avail", "judge:avail_other", "synthesize:direct", "extract",
                "recall:closedbook")


def smoke_passed(paths: StudyPaths) -> bool:
    return bool((read_json(paths.state / "smoke.json", {}) or {}).get("passed"))


def _smoke_synthetic(study: Study) -> list[tuple[str, str, str, dict[str, Any], str]]:
    """Requests for reply schemas the first wave cannot contain (they need earlier replies):
    the real system prompt and schema with a tiny made-up prompt. Their replies are not cached."""
    from ..config import DEFAULT_EFFORT
    from ..extract import NORMALIZE_SYSTEM, XChoices
    from ..llm import schema_for
    from ..synthesize import KG_SYSTEM, XEntry

    norm_prompt = ("1. short stature\n   HP:0004322  Short stature\n   HP:0003510  Severe short stature\n\n"
                   "2. seizures\n   HP:0001250  Seizure\n   HP:0002197  Generalized-onset seizure")
    kg_prompt = ("Entry to write: phenotype (disorder) entry\nTitle: SMOKE TEST DISORDER\nMIM number: 000000\n"
                 "Sections available: description\n\nReference data from HGNC (nomenclature only, not literature "
                 "evidence):\nnone\n\n<evidence>\nPAPERS\n\nGENES WITH PATIENT VARIANTS (papers reporting them)\n"
                 "- none\n\nMODES OF INHERITANCE ASSERTED (papers)\n- none stated\n\nVARIANT TABLE (one row per "
                 "distinct variant after merging names across papers)\n\nFINDINGS BY SECTION\n</evidence>")
    return [("normalize", NORMALIZE_SYSTEM, norm_prompt, schema_for(XChoices), DEFAULT_EFFORT["normalize"]),
            ("synthesize:kg", KG_SYSTEM, kg_prompt, schema_for(XEntry), DEFAULT_EFFORT["synthesize"])]


def smoke(paths: StudyPaths, study: Study, provider, *, jobs: int | None = None) -> dict[str, Any]:
    """A batch of at most 8 requests, one per kind of call the study makes, to check format and parsing.

    First call: builds and submits it. Later calls: poll; once it has ended, parse every
    line, validate each reply with the project's own reply model, cache the real study
    requests' replies (they are genuine first-wave requests) and write state/smoke.json.
    """
    from .offline import activate, network_blocked
    from .openai_format import request_line

    st = read_json(paths.state / "smoke.json", {}) or {}
    smoke_dir = paths.smoke
    if not st.get("batch_id"):
        if not (paths.state / "tasks.json").exists():
            plan(paths, study)
        tasks = tasks_state(paths)["tasks"]
        bundle = Bundle(paths.bundle)
        raw = smoke_dir / "candidates.jsonl"
        recorder = Recorder(study, raw)
        firsts: list[TaskSpec] = []
        seen_kinds: set[tuple[str, str]] = set()
        for tid in tasks:
            spec = TaskSpec.parse(tid)
            k = (spec.kind, spec.variant if spec.kind == "B1" else "")
            if k not in seen_kinds:
                seen_kinds.add(k)
                firsts.append(spec)
        with network_blocked():
            settings = activate(paths, study)
            ctx = Context(paths, study, bundle, settings, recorder)
            ctx.work = paths.smoke / "work"
            run_all(ctx, firsts, jobs or 4)
        recorder.close()
        chosen: dict[str, dict[str, Any]] = {}
        for e in sorted(recorder.entries.values(), key=lambda e: e["chars"]):
            if e["label"] in SMOKE_LABELS and e["label"] not in chosen and e["attempt"] == 1:
                chosen[e["label"]] = e
        lines = {}
        for raw_line in raw.read_text(encoding="utf-8").splitlines():
            obj = json.loads(raw_line)
            if obj["custom_id"] in {e["custom_id"] for e in chosen.values()}:
                lines[obj["custom_id"]] = obj
        synthetic = []
        for label, system, prompt, schema, effort in _smoke_synthetic(study):
            cid = f"smoke-{label.replace(':', '-')}"
            lines[cid] = request_line(cid, model=study.model, effort=study.openai_effort(effort), system=system,
                                      prompt=prompt, schema=schema, name=label.replace(":", "_"), strict=True,
                                      store=bool(study.setting("request", "store", default=False)))
            synthetic.append({"custom_id": cid, "label": label, "effort": effort, "synthetic": True})
        path = smoke_dir / "smoke.jsonl"
        write_text(path, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines.values()))
        manifest = [dict(e, synthetic=False) for e in chosen.values()] + synthetic
        write_json(smoke_dir / "smoke.manifest.json", {"requests": manifest})
        n_chars = sum(e.get("chars", 0) for e in chosen.values())
        est = study.cost(int(n_chars / study.chars_per_token()), 0,
                         sum(study.expected_output_tokens(e["label"]) for e in manifest))
        if spent_usd(paths) + est > study.cap_usd:
            raise StudyError("the smoke batch alone would pass the cost cap")
        file_id = provider.upload(path)
        batch = provider.create(file_id, {"wave": "smoke"})
        st = {"batch_id": batch["id"], "input_file_id": file_id, "submitted_at": now(), "requests": len(lines),
              "labels": sorted({e["label"] for e in manifest}), "est_cost_usd": round(est, 4), "passed": False}
        write_json(paths.state / "smoke.json", st)
        _log_line(paths, "smoke", st["batch_id"], "smoke submitted", f"{st['requests']} requests")
        return st

    if not st.get("ended"):
        info = provider.retrieve(st["batch_id"])
        st["status"] = info.get("status")
        if st["status"] not in TERMINAL:
            write_json(paths.state / "smoke.json", st)
            return st
        for key, suffix in (("output_file_id", "output"), ("error_file_id", "errors")):
            if info.get(key):
                provider.download(info[key], smoke_dir / f"smoke.{suffix}.jsonl")
        st["ended"] = now()
    manifest = {e["custom_id"]: e for e in read_json(smoke_dir / "smoke.manifest.json")["requests"]}
    results = []
    cache = DiskCache(paths.home / "cache" / "llm")
    led = ledger(paths)
    wl = led["waves"].setdefault("smoke", {"batches": [st["batch_id"]], "by_label": {}, "by_task_kind": {},
                                           "total": {}})
    models = _reply_models()
    for suffix in ("output", "errors"):
        path = smoke_dir / f"smoke.{suffix}.jsonl"
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            reply = parse_line(raw_line)
            e = manifest.get(reply.custom_id)
            if e is None:
                continue
            valid = None
            if reply.kind == "ok":
                try:
                    models[e["label"]].model_validate(reply.data)
                    valid = True
                except Exception:  # noqa: BLE001 - reported
                    valid = False
            results.append({"custom_id": reply.custom_id, "label": e["label"], "kind": reply.kind,
                            "schema_valid": valid, "status": reply.status, "reason": reply.reason,
                            "error_code": reply.error_code, "usage": reply.usage,
                            "synthetic": bool(e.get("synthetic"))})
            if not e.get("synthetic") and not st.get("ingested"):
                b = {"batch_id": st["batch_id"]}
                outcome = _store_reply(cache, study, b, e, reply, 1,
                                       int(study.setting("retries", "transport", default=3)), paths.logs)
                _ledger_add(wl, study, e, reply, outcome)
            elif e.get("synthetic") and not st.get("ingested"):
                _ledger_add(wl, study, {**e, "chars": 0, "tasks": ["smoke"]}, reply, reply.kind)
    st["ingested"] = True
    save_ledger(paths, led)
    st["results"] = sorted(results, key=lambda r: r["label"])
    answered = {r["label"] for r in results}
    # Passed: every request came back in a form the parser understands (a reply that validates against
    # the project's reply model, or a safety stop), and none was rejected, cut short or malformed.
    bad = [r for r in results if not ((r["kind"] == "ok" and r["schema_valid"]) or r["kind"] in
                                      ("refusal", "content_filter"))]
    st["passed"] = answered >= set(st["labels"]) and not bad
    st["problems"] = [f"{r['label']}: {r['kind']} {r.get('error_code') or r.get('reason') or ''}".strip()
                      for r in bad] + [f"{lab}: no reply" for lab in sorted(set(st["labels"]) - answered)]
    st["warnings"] = [f"{r['label']}: the reply was a safety stop, so this reply schema was not exercised"
                      for r in results if r["kind"] in ("refusal", "content_filter")]
    write_json(paths.state / "smoke.json", st)
    if not st.get("logged"):
        _log_line(paths, "smoke", st["batch_id"], "smoke passed" if st["passed"] else "smoke failed",
                  "; ".join(st["problems"] + st["warnings"])[:160] or "every reply parsed")
        st["logged"] = True
        write_json(paths.state / "smoke.json", st)
    return st


def _log_line(paths: StudyPaths, wave: str, batch: str, phase: str, reason: str) -> None:
    _append_run_log(paths, {"updated_at": now(), "wave": wave, "open_batches": [{"batch_id": batch}],
                            "phase": phase, "reason": reason, "spent_usd": spent_usd(paths)})


def _reply_models() -> dict[str, Any]:
    from ..extract import XChoices, XExtraction
    from ..facts import XMarks
    from ..gaps import XGapVerdicts
    from ..synthesize import DEntry, XEntry

    return {"judge:mark": XMarks, "judge:avail": XGapVerdicts, "judge:avail_other": XGapVerdicts,
            "synthesize:direct": DEntry, "recall:closedbook": DEntry, "extract": XExtraction,
            "normalize": XChoices, "synthesize:kg": XEntry}


def reset_smoke(paths: StudyPaths) -> None:
    (paths.state / "smoke.json").unlink(missing_ok=True)
    if paths.smoke.exists():
        shutil.rmtree(paths.smoke)


__all__ = ["collect", "ingest", "label_for", "plan", "poll", "smoke", "status_line", "step", "submit"]
