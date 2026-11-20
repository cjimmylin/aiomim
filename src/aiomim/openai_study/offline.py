"""The study's offline environment: settings, data from the bundle, and no network.

Everything a task reads comes from the private bundle:

* model settings through the environment (`AIOMIM_MODEL` = the OpenAI model, so the
  cache keys differ from Claude's; `AIOMIM_HOME` = the study's own data home; no
  per-stage overrides and no replicate salt, so every stage keeps the project's effort);
* HTTP: the only source the code paths touch is HGNC (gene symbol normalisation and
  the nomenclature lines of the evidence-graph prompt). `OfflineHttp` answers from
  the HGNC responses the original runs cached (exact replay) and, for a symbol they
  never looked up, from HGNC's complete set in the bundle with the semantics of
  `rest.genenames.org/fetch/<field>/<value>` (case-insensitive exact match; checked
  against 1,247 cached responses, all equal). Anything else raises `NetworkBlocked`;
* the Human Phenotype Ontology from the bundle's files (no download, no refresh);
* the Claude backend is disabled outright.

`network_blocked()` additionally makes every socket connection in the process raise
`NetworkBlocked`, which is how `collect` proves that it needs no network.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import socket
import threading
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .config import Study, StudyPaths
from .errors import ForbiddenCall, NetworkBlocked

HGNC_BASE = "https://rest.genenames.org/fetch"
HGNC_FIELDS = ("symbol", "hgnc_id", "entrez_id", "omim_id", "location", "name", "alias_symbol", "prev_symbol",
               "status")

# --------------------------------------------------------------------------- #
# Network guard
# --------------------------------------------------------------------------- #

_guard_lock = threading.Lock()
_guard_depth = 0
_saved: dict[str, Any] = {}
NETWORK_ATTEMPTS: list[str] = []


def _blocked(*args, **kwargs):
    where = ""
    for a in args:
        if isinstance(a, tuple) and a:
            where = str(a[0])
            break
    NETWORK_ATTEMPTS.append(where or "socket")
    raise NetworkBlocked(f"network access attempted while the study runs offline ({where or 'socket'})")


@contextlib.contextmanager
def network_blocked():
    """Make every socket connection in this process raise `NetworkBlocked` (re-entrant)."""
    global _guard_depth
    with _guard_lock:
        if _guard_depth == 0:
            _saved["connect"] = socket.socket.connect
            _saved["connect_ex"] = socket.socket.connect_ex
            _saved["create_connection"] = socket.create_connection
            _saved["getaddrinfo"] = socket.getaddrinfo
            socket.socket.connect = _blocked
            socket.socket.connect_ex = _blocked
            socket.create_connection = _blocked
            socket.getaddrinfo = _blocked
        _guard_depth += 1
    try:
        yield NETWORK_ATTEMPTS
    finally:
        with _guard_lock:
            _guard_depth -= 1
            if _guard_depth == 0:
                socket.socket.connect = _saved["connect"]
                socket.socket.connect_ex = _saved["connect_ex"]
                socket.create_connection = _saved["create_connection"]
                socket.getaddrinfo = _saved["getaddrinfo"]


# --------------------------------------------------------------------------- #
# HGNC without the network
# --------------------------------------------------------------------------- #


class HgncTable:
    """HGNC's complete set, indexed like the REST fetch endpoint."""

    def __init__(self, docs: list[dict[str, Any]]):
        self.docs = docs
        self.index: dict[str, dict[str, list[int]]] = {f: defaultdict(list) for f in ("symbol", "prev_symbol",
                                                                                         "alias_symbol", "hgnc_id")}
        for i, d in enumerate(docs):
            self._add("symbol", d.get("symbol"), i)
            self._add("hgnc_id", d.get("hgnc_id"), i)
            for f in ("prev_symbol", "alias_symbol"):
                for v in d.get(f) or []:
                    self._add(f, v, i)

    def _add(self, field: str, value: Any, i: int) -> None:
        if value:
            bucket = self.index[field][str(value).upper()]
            if i not in bucket:
                bucket.append(i)

    @classmethod
    def load(cls, path: Path) -> HgncTable:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["docs"] if isinstance(data, dict) else data)

    def fetch(self, field: str, value: str) -> list[dict[str, Any]]:
        idx = self.index.get(field)
        if idx is None:
            return []
        return [self.docs[i] for i in idx.get(value.upper(), [])]

    def response_text(self, url: str) -> str:
        path = urlsplit(url).path.rstrip("/").split("/")
        field, value = (path[-2], unquote(path[-1])) if len(path) >= 2 else ("", "")
        docs = self.fetch(field, value)
        return json.dumps({"responseHeader": {"status": 0, "QTime": 0, "emulated_from": "hgnc_complete_set"},
                           "response": {"numFound": len(docs), "start": 0, "numFoundExact": True, "docs": docs}})


def compact_hgnc(complete_set: dict[str, Any]) -> list[dict[str, Any]]:
    """The fields of HGNC's complete set that the project reads (`sources.hgnc._to_info`)."""
    docs = complete_set["response"]["docs"] if "response" in complete_set else complete_set
    return [{k: d[k] for k in HGNC_FIELDS if k in d} for d in docs]


def make_offline_http(cache_dir: Path, hgnc: HgncTable | None):
    """An `aiomim.http.Http` that never touches the network."""
    from ..http import Http

    class OfflineHttp(Http):
        def __init__(self):
            super().__init__(cache_dir=cache_dir)
            self.hgnc = hgnc
            self.replayed = 0
            self.emulated: list[str] = []
            self._count_lock = threading.Lock()

        def get_text(self, url: str, params: dict | None = None, *, headers: dict | None = None,
                     cache: bool = True, max_age_s: float | None = None, max_tries: int | None = None) -> str:
            hit = self.cache.get_text(self.cache_key(url, params))   # no max-age: the bundle is a snapshot
            if hit is not None:
                with self._count_lock:
                    self.replayed += 1
                return hit
            if self.hgnc is not None and url.startswith(HGNC_BASE + "/") and not params:
                with self._count_lock:
                    self.emulated.append(urlsplit(url).path)
                return self.hgnc.response_text(url)
            NETWORK_ATTEMPTS.append(urlsplit(url).hostname or url)
            raise NetworkBlocked(f"offline: no bundled response for {urlsplit(url).hostname}")

        def _request(self, url, params, headers, stream=False, max_tries=None):
            NETWORK_ATTEMPTS.append(urlsplit(url).hostname or url)
            raise NetworkBlocked(f"offline: {urlsplit(url).hostname}")

        def download(self, url: str, dest: Path, max_age_s: float | None = None) -> Path:
            if Path(dest).exists():
                return Path(dest)
            NETWORK_ATTEMPTS.append(urlsplit(url).hostname or url)
            raise NetworkBlocked(f"offline: download of {url}")

    return OfflineHttp()


# --------------------------------------------------------------------------- #
# The study's data home
# --------------------------------------------------------------------------- #

HOME_MARKER = ".prepared.json"


def prepare_home(paths: StudyPaths, bundle_dir: Path | None = None) -> Path:
    """Lay out the study's data home from the bundle (once): fact lists, ontology, HGNC responses.

    The fact store here holds the fixed lists only; availability judgements written
    into it are the OpenAI judge's. Claude's stay in the bundle.
    """
    bundle_dir = Path(bundle_dir or paths.bundle)
    home = paths.home
    marker = home / HOME_MARKER
    manifest = json.loads((bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    if marker.exists() and json.loads(marker.read_text()).get("bundle_id") == manifest.get("bundle_id"):
        return home
    (home / "cache" / "llm").mkdir(parents=True, exist_ok=True)
    store = home / "gold_facts"
    for src in (bundle_dir / "factstore").glob("*/*.json"):
        if src.parent.name == "avail":
            continue
        dst = store / src.parent.name / src.name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    onto = home / "ontologies"
    onto.mkdir(parents=True, exist_ok=True)
    for name in ("hp.obo", "phenotype.hpoa"):
        if not (onto / name).exists():
            shutil.copyfile(bundle_dir / "ontologies" / name, onto / name)
    http = home / "cache" / "http"
    for src in (bundle_dir / "http").glob("*/*.txt"):
        dst = http / src.parent.name / src.name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    marker.write_text(json.dumps({"bundle_id": manifest.get("bundle_id")}))
    return home


_ENV_KEYS = ("AIOMIM_HOME", "AIOMIM_RUNS", "AIOMIM_MODEL", "AIOMIM_REPLICATE", "AIOMIM_LLM_CONCURRENCY")


def activate(paths: StudyPaths, study: Study | None, *, model: str | None = None, bundle_dir: Path | None = None,
             concurrency: int | None = None, home: Path | None = None):
    """Point the project at the study's offline data and model; returns the project's `Settings`."""
    from .. import config as aiomim_config
    from .. import http as aiomim_http
    from .. import llm as aiomim_llm
    from ..sources import hpo as hpo_mod

    bundle_dir = Path(bundle_dir or paths.bundle)
    home = Path(home) if home else prepare_home(paths, bundle_dir)
    if not _ORIGINAL:
        _ORIGINAL["env"] = {k: v for k, v in os.environ.items() if k.startswith("AIOMIM_")}
        _ORIGINAL["http"] = aiomim_http._HTTP
        _ORIGINAL["hpo"] = hpo_mod._HPO
        _ORIGINAL["claude_complete"] = aiomim_llm.ClaudeCode.complete
    os.environ["AIOMIM_HOME"] = str(home)
    os.environ["AIOMIM_RUNS"] = str(paths.work / "runs")
    os.environ["AIOMIM_MODEL"] = model or (study.model if study else "")
    os.environ.pop("AIOMIM_REPLICATE", None)
    for stage in aiomim_config.STAGES:
        os.environ.pop(f"AIOMIM_MODEL_{stage.upper()}", None)
        os.environ.pop(f"AIOMIM_EFFORT_{stage.upper()}", None)
    n = concurrency or (study.setting("concurrency", "llm", default=8) if study else 8)
    os.environ["AIOMIM_LLM_CONCURRENCY"] = str(n)
    aiomim_config.get_settings.cache_clear()
    settings = aiomim_config.get_settings()

    hgnc_path = bundle_dir / "hgnc" / "hgnc_table.json"
    table = HgncTable.load(hgnc_path) if hgnc_path.exists() else None
    with aiomim_http._HTTP_LOCK:
        aiomim_http._HTTP = make_offline_http(settings.http_cache, table)

    onto = settings.ontology_dir
    with hpo_mod._HPO_LOCK:
        if hpo_mod._HPO is None or Path(getattr(hpo_mod._HPO, "obo_path", "")) != onto / "hp.obo":
            hpo_mod._HPO = hpo_mod.HPO(obo_path=onto / "hp.obo", hpoa_path=onto / "phenotype.hpoa",
                                       index_path=onto / "hp.index.pkl", download=False)

    def _no_claude(self, **kwargs):
        raise ForbiddenCall("the Claude backend is disabled in the OpenAI study")

    aiomim_llm.ClaudeCode.complete = _no_claude
    return settings


_ORIGINAL: dict[str, Any] = {}


def deactivate() -> None:
    """Undo `activate` (tests; a process that goes on to do something else)."""
    from .. import config as aiomim_config
    from .. import http as aiomim_http
    from .. import llm as aiomim_llm
    from ..sources import hpo as hpo_mod

    if not _ORIGINAL:
        return
    for k in [k for k in os.environ if k.startswith("AIOMIM_")]:
        del os.environ[k]
    os.environ.update(_ORIGINAL["env"])
    aiomim_http._HTTP = _ORIGINAL["http"]
    hpo_mod._HPO = _ORIGINAL["hpo"]
    aiomim_llm.ClaudeCode.complete = _ORIGINAL["claude_complete"]
    aiomim_config.get_settings.cache_clear()
    _ORIGINAL.clear()


def settings_with(settings, **changes):
    return replace(settings, **changes)
