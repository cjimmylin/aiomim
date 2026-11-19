"""Polite, cached HTTP access for every external source.

* Responses are cached on disk (`settings.http_cache`) keyed by URL + sorted
  params, so a repeated run touches the network only for what is new.
* Each host has its own thread-safe rate limiter (NCBI: 3 req/s, or 10 with an
  API key).
* 429 / 5xx / connection errors are retried with exponential backoff; 404 raises
  `NotFound` immediately.
* Only a generic User-Agent is sent. E-utilities requests carry `tool=aiomim`,
  and `email` / `api_key` only when the user configured them.
"""

from __future__ import annotations

import json
import logging
import os
import random
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from .cache import DiskCache, stable_hash
from .config import get_settings

log = logging.getLogger(__name__)

USER_AGENT = "aiomim/0.1"
EUTILS_HOST = "eutils.ncbi.nlm.nih.gov"

RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, url: str = ""):
        super().__init__(f"{message} (status={status}, url={url})")
        self.status = status
        self.url = url


class NotFound(HttpError):
    pass


class RateLimiter:
    """Minimum spacing between request starts, shared by all threads."""

    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self.interval
        delay = start - now
        if delay > 0:
            time.sleep(delay)


def _host_rate(host: str, ncbi_key: bool) -> float:
    if host == EUTILS_HOST:
        return 9.0 if ncbi_key else 2.8
    if host.endswith("ncbi.nlm.nih.gov"):  # BioC, FTP mirror over HTTPS
        return 2.0
    if host.endswith("ebi.ac.uk"):
        return 8.0
    if host.endswith("genenames.org"):
        return 8.0
    return 5.0


class Http:
    def __init__(self, cache_dir: Path | None = None, timeout: float = 60.0, max_tries: int = 5):
        settings = get_settings()
        self.settings = settings
        self.cache = DiskCache(cache_dir or settings.http_cache, suffix=".txt")
        self.timeout = timeout
        self.max_tries = max_tries
        self._limiters: dict[str, RateLimiter] = {}
        self._lim_lock = threading.Lock()
        self._local = threading.local()

    # ------------------------------------------------------------------ utils
    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers["User-Agent"] = USER_AGENT
            self._local.session = s
        return s

    def _limiter(self, host: str) -> RateLimiter:
        with self._lim_lock:
            lim = self._limiters.get(host)
            if lim is None:
                lim = RateLimiter(_host_rate(host, bool(self.settings.ncbi_api_key)))
                self._limiters[host] = lim
            return lim

    def _augment(self, url: str, params: dict | None) -> dict:
        """Add identification params that must not affect the cache key."""
        params = dict(params or {})
        if urlsplit(url).hostname == EUTILS_HOST:
            params.setdefault("tool", "aiomim")
            if self.settings.ncbi_email:
                params.setdefault("email", self.settings.ncbi_email)
            if self.settings.ncbi_api_key:
                params.setdefault("api_key", self.settings.ncbi_api_key)
        return params

    @staticmethod
    def cache_key(url: str, params: dict | None = None) -> str:
        items = sorted((str(k), str(v)) for k, v in (params or {}).items())
        return stable_hash(url, items)

    def _request(self, url: str, params: dict | None, headers: dict | None,
                 stream: bool = False, max_tries: int | None = None) -> requests.Response:
        host = urlsplit(url).hostname or ""
        tries = max_tries or self.max_tries
        params = self._augment(url, params)
        last_exc: Exception | None = None
        last_status: int | None = None
        for attempt in range(tries):
            self._limiter(host).wait()
            try:
                resp = self._session().get(url, params=params, headers=headers or {},
                                           timeout=self.timeout, stream=stream,
                                           allow_redirects=True)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc, last_status = exc, None
                log.debug("http %s: %s (attempt %d)", url, exc, attempt + 1)
            else:
                if resp.status_code == 404:
                    resp.close()
                    raise NotFound("not found", status=404, url=url)
                if resp.status_code < 400:
                    return resp
                last_status = resp.status_code
                retry_after = resp.headers.get("Retry-After")
                resp.close()
                if resp.status_code not in RETRY_STATUSES:
                    raise HttpError("request failed", status=resp.status_code, url=url)
                if retry_after and retry_after.isdigit() and attempt + 1 < tries:
                    time.sleep(min(float(retry_after), 30.0))
                    continue
            if attempt + 1 < tries:
                time.sleep(min(2 ** attempt, 20) * (0.75 + random.random() / 2))
        raise HttpError(f"giving up after {tries} tries: {last_exc or ''}".strip(),
                        status=last_status, url=url)

    # ------------------------------------------------------------------ API
    def get_text(self, url: str, params: dict | None = None, *, headers: dict | None = None,
                 cache: bool = True, max_age_s: float | None = None,
                 max_tries: int | None = None) -> str:
        key = self.cache_key(url, params)
        if cache:
            hit = self.cache.get_text(key, max_age_s)
            if hit is not None:
                return hit
        resp = self._request(url, params, headers, max_tries=max_tries)
        if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
            # Most of our sources serve UTF-8 without saying so.
            resp.encoding = "utf-8"
        text = resp.text
        if cache:
            self.cache.put_text(key, text)
        return text

    def get_json(self, url: str, params: dict | None = None, *, headers: dict | None = None,
                 cache: bool = True, max_age_s: float | None = None,
                 max_tries: int | None = None) -> Any:
        hdrs = {"Accept": "application/json", **(headers or {})}
        key = self.cache_key(url, params)
        text = self.get_text(url, params, headers=hdrs, cache=cache, max_age_s=max_age_s,
                             max_tries=max_tries)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Never keep an unparsable body in the cache.
            try:
                self.cache.path(key).unlink()
            except FileNotFoundError:
                pass
            raise HttpError(f"invalid JSON: {exc}", status=None, url=url) from exc

    def download(self, url: str, dest: Path, max_age_s: float | None = None) -> Path:
        dest = Path(dest)
        if dest.exists() and (max_age_s is None or time.time() - dest.stat().st_mtime <= max_age_s):
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            resp = self._request(url, None, None, stream=True)
        except HttpError:
            if dest.exists():
                log.warning("could not refresh %s; keeping stale copy", url)
                return dest
            raise
        fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=dest.name, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as fh, resp:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
            os.chmod(tmp, 0o644)
            os.replace(tmp, dest)
        except BaseException as exc:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            if isinstance(exc, Exception) and dest.exists():
                log.warning("download of %s failed; keeping stale copy", url)
                return dest
            raise
        return dest


_HTTP: Http | None = None
_HTTP_LOCK = threading.Lock()


def get_http() -> Http:
    global _HTTP
    with _HTTP_LOCK:
        if _HTTP is None:
            _HTTP = Http()
        return _HTTP
