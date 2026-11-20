"""The one local embedding model every system uses: BAAI/bge-small-en-v1.5 through fastembed (ONNX).

fastembed serves this model from its ONNX export `Qdrant/bge-small-en-v1.5-onnx-Q`
(`model_optimized.onnx`, 384 dimensions, inputs truncated at 512 tokens, vectors normalised).

The model files are downloaded once from the Hugging Face hub into `<home>/models/fastembed`
(AIOMIM_HOME, default data/) and read from there afterwards. Embedding inputs never leave
the machine.
"""

from __future__ import annotations

import threading
from pathlib import Path

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


def cache_dir() -> Path:
    from ..config import get_settings

    return get_settings().home / "models" / "fastembed"


class LocalEmbedder:
    """Thread-safe wrapper; the model loads on first use."""

    name = EMBED_MODEL
    dim = EMBED_DIM

    def __init__(self, model: str = EMBED_MODEL, cache: Path | None = None):
        self.name = model
        self._cache = cache or cache_dir()
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._cache.mkdir(parents=True, exist_ok=True)
            try:   # once downloaded, never touch the hub again
                self._model = TextEmbedding(self.name, cache_dir=str(self._cache), local_files_only=True)
            except Exception:  # noqa: BLE001 - first use: download from the Hugging Face hub
                self._model = TextEmbedding(self.name, cache_dir=str(self._cache))
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            model = self._load()
            return [[float(x) for x in vec] for vec in model.embed(texts, batch_size=64)]

    def version(self) -> str:
        try:
            from importlib.metadata import version

            return f"fastembed {version('fastembed')}"
        except Exception:  # noqa: BLE001
            return "fastembed"
