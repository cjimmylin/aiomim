"""Agreement and paired statistics for the report.

Paired differences reuse `compare._pair_stats` (mean difference, bootstrap 95% interval
over entries with 10,000 resamples, median, better / worse / tied, exact sign test), so
every interval is computed the way the paper's are. Agreement between two judges is
raw agreement and Cohen's kappa, from per-entry confusion matrices, with a percentile
bootstrap interval over entries (all of an entry's facts move together).
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

MARKS = ("present", "partial", "absent", "contradicted")
AVAIL = ("yes", "partly", "no")
KAPPA_RESAMPLES = 2000
KAPPA_SEED = 7


def coverage(statuses: Iterable[str]) -> float | None:
    """(present + half of partial) / judged; unjudged and missing marks are left out, as in the project."""
    judged = [s for s in statuses if s in MARKS]
    if not judged:
        return None
    return (sum(s == "present" for s in judged) + 0.5 * sum(s == "partial" for s in judged)) / len(judged)


def tally(statuses: Iterable[str]) -> dict[str, Any]:
    statuses = list(statuses)
    out = {k: sum(s == k for s in statuses) for k in MARKS}
    out["n_judged"] = sum(out.values())
    out["unjudged"] = len(statuses) - out["n_judged"]
    c = coverage(statuses)
    out["coverage"] = round(c, 4) if c is not None else None
    return out


def _matrix(pairs: Iterable[tuple[str, str]], cats: tuple[str, ...]) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(cats)}
    m = [[0] * len(cats) for _ in cats]
    for a, b in pairs:
        if a in idx and b in idx:
            m[idx[a]][idx[b]] += 1
    return m


def _kappa(m: list[list[int]]) -> tuple[float | None, float | None, int]:
    n = sum(map(sum, m))
    if n == 0:
        return None, None, 0
    po = sum(m[i][i] for i in range(len(m))) / n
    rows = [sum(r) / n for r in m]
    cols = [sum(m[i][j] for i in range(len(m))) / n for j in range(len(m))]
    pe = sum(r * c for r, c in zip(rows, cols))
    kappa = None if pe >= 1 else (po - pe) / (1 - pe)
    return po, kappa, n


def _add(a: list[list[int]], b: list[list[int]]) -> list[list[int]]:
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def agreement(by_entry: dict[str, list[tuple[str, str]]], cats: tuple[str, ...], *,
              binary: str | None = None, resamples: int = KAPPA_RESAMPLES, seed: int = KAPPA_SEED) -> dict[str, Any]:
    """Raw agreement and Cohen's kappa of paired labels, pooled over entries, with bootstrap intervals.

    `binary` collapses the labels to `binary` against everything else first (e.g. present vs not).
    Pairs where either label is outside `cats` (unjudged, missing) are left out.
    """
    if binary is not None:
        two = (binary, "other")
        by_entry = {e: [(binary if a == binary else "other", binary if b == binary else "other")
                        for a, b in pairs if a in cats and b in cats] for e, pairs in by_entry.items()}
        cats = two
    mats = {e: _matrix(pairs, cats) for e, pairs in by_entry.items()}
    mats = {e: m for e, m in mats.items() if sum(map(sum, m))}
    if not mats:
        return {"n_facts": 0, "n_entries": 0}
    total = [[0] * len(cats) for _ in cats]
    for m in mats.values():
        total = _add(total, m)
    po, kappa, n = _kappa(total)
    rng = random.Random(seed)
    keys = sorted(mats)
    pos, kappas = [], []
    for _ in range(resamples if len(keys) >= 5 else 0):
        t = [[0] * len(cats) for _ in cats]
        for k in rng.choices(keys, k=len(keys)):
            t = _add(t, mats[k])
        p, kp, _ = _kappa(t)
        pos.append(p)
        if kp is not None:
            kappas.append(kp)

    def ci(xs: list[float]) -> list[float] | None:
        if len(xs) < 20:
            return None
        xs = sorted(xs)
        return [round(xs[int(0.025 * len(xs))], 4), round(xs[int(0.975 * len(xs)) - 1], 4)]

    return {"n_facts": n, "n_entries": len(mats), "categories": list(cats),
            "raw_agreement": round(po, 4) if po is not None else None, "raw_agreement_ci95": ci(pos),
            "kappa": round(kappa, 4) if kappa is not None else None, "kappa_ci95": ci(kappas),
            "confusion": {"rows": "first judge", "columns": "second judge", "matrix": total},
            "bootstrap": {"resamples": resamples, "seed": seed, "unit": "entry"}}


def paired(values: list[tuple[float, float]], seed: int = 7) -> dict[str, Any] | None:
    """`compare._pair_stats` on (strategy, baseline) pairs of per-entry values, higher is better."""
    from ..compare import _pair_stats

    if not values:
        return None
    return _pair_stats(values, True, random.Random(seed))


def mean(values: Iterable[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return round(sum(kept) / len(kept), 4) if kept else None


def group(rows: Iterable[tuple[str, Any]]) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = defaultdict(list)
    for k, v in rows:
        out[k].append(v)
    return dict(out)
