"""A small content-addressed disk cache.

Both the HTTP layer and the LLM layer go through this, which is what makes a
pipeline run reproducible and cheap to repeat: a second run of the same entry
re-reads every network response and every model response from disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def stable_hash(*parts: Any) -> str:
    """SHA-256 over a canonical JSON rendering of `parts`."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class DiskCache:
    """Maps a hash key to one file under `root`, fanned out by key prefix."""

    def __init__(self, root: Path, suffix: str = ".json"):
        self.root = Path(root)
        self.suffix = suffix

    def path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}{self.suffix}"

    def get_text(self, key: str, max_age_s: float | None = None) -> str | None:
        p = self.path(key)
        try:
            if max_age_s is not None and time.time() - p.stat().st_mtime > max_age_s:
                return None
            return p.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def put_text(self, key: str, text: str) -> None:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-rename so concurrent workers never observe a partial file.
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, p)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def get_json(self, key: str, max_age_s: float | None = None) -> Any | None:
        text = self.get_text(key, max_age_s)
        return None if text is None else json.loads(text)

    def put_json(self, key: str, value: Any) -> None:
        self.put_text(key, json.dumps(value, ensure_ascii=False))
