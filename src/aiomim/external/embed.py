"""The one local embedding model every system uses: BAAI/bge-small-en-v1.5 through fastembed (ONNX).

fastembed serves this model from its ONNX export `Qdrant/bge-small-en-v1.5-onnx-Q`
(`model_optimized.onnx`, 384 dimensions, inputs truncated at 512 tokens, vectors normalised).

The model files are downloaded once from the Hugging Face hub into `<home>/models/fastembed`
(AIOMIM_HOME, default data/) and read from there afterwards. Embedding inputs never leave
the machine.

Long inputs. By default (`long_inputs="truncate"`) the model's tokenizer cuts every input at 512 tokens, as
fastembed does. The opt-in mode `long_inputs="pool"` embeds an input longer than that limit as consecutive,
non-overlapping windows that each fit (split with the model's own tokenizer, at token boundaries), averages the
window vectors (unweighted mean) and re-normalises the mean to unit length. Inputs within the limit are embedded
exactly as in the default mode. The default mode is unchanged.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
LONG_INPUT_MODES = ("truncate", "pool")
POOLED_NAME_SUFFIX = " (long inputs: pooled 510-token windows)"


def split_windows(text: str, encode: Callable[[str], list[tuple[int, int]]], max_tokens: int) -> list[str]:
    """Consecutive windows of `text` of at most `max_tokens` tokens each (no overlap), cut at token boundaries.

    `encode(text)` returns the character offsets (start, end) of each token, without special tokens.
    A window is the text from its first token's start to its last token's end; a window that re-tokenises
    to more than `max_tokens` tokens is shortened until it fits. Returns [text] if it already fits."""
    offsets = encode(text)
    if len(offsets) <= max_tokens:
        return [text]
    windows, i = [], 0
    while i < len(offsets):
        n = min(max_tokens, len(offsets) - i)
        while True:
            piece = text[offsets[i][0]:offsets[i + n - 1][1]]
            over = len(encode(piece)) - max_tokens
            if over <= 0 or n == 1:
                break
            n = max(1, n - over)
        windows.append(piece)
        i += n
    return windows


def mean_normalised(vectors: list[list[float]]) -> list[float]:
    """Unweighted mean of the vectors, scaled to unit length."""
    dim = len(vectors[0])
    mean = [sum(v[k] for v in vectors) / len(vectors) for k in range(dim)]
    norm = sum(x * x for x in mean) ** 0.5
    return [x / norm for x in mean] if norm else mean


def cache_dir() -> Path:
    from ..config import get_settings

    return get_settings().home / "models" / "fastembed"


class LocalEmbedder:
    """Thread-safe wrapper; the model loads on first use."""

    name = EMBED_MODEL
    dim = EMBED_DIM

    def __init__(self, model: str = EMBED_MODEL, cache: Path | None = None, long_inputs: str = "truncate"):
        if long_inputs not in LONG_INPUT_MODES:
            raise ValueError(f"long_inputs must be one of {LONG_INPUT_MODES}")
        self.long_inputs = long_inputs
        self.name = model + (POOLED_NAME_SUFFIX if long_inputs == "pool" else "")
        self._model_name = model
        self._cache = cache or cache_dir()
        self._model = None
        self._lock = threading.Lock()
        self._encode_fn: Callable[[str], list[tuple[int, int]]] | None = None
        self._max_tokens: int | None = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._cache.mkdir(parents=True, exist_ok=True)
            try:   # once downloaded, never touch the hub again
                self._model = TextEmbedding(self._model_name, cache_dir=str(self._cache), local_files_only=True)
            except Exception:  # noqa: BLE001 - first use: download from the Hugging Face hub
                self._model = TextEmbedding(self._model_name, cache_dir=str(self._cache))
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.long_inputs == "pool":
            return self._embed_pooled(texts)
        with self._lock:
            model = self._load()
            return [[float(x) for x in vec] for vec in model.embed(texts, batch_size=64)]

    # ------------------------------------------------------------------ opt-in pooling of long inputs

    def _tokenizer_setup(self) -> tuple[Callable[[str], list[tuple[int, int]]], int]:
        """(encode -> token offsets without special tokens and without truncation, tokens per window).
        Uses a copy of the model's own tokenizer; the window size is its truncation length minus the
        special tokens it adds ([CLS], [SEP])."""
        if self._encode_fn is None:
            from tokenizers import Tokenizer

            original = self._load().model.tokenizer
            max_len = int((original.truncation or {}).get("max_length") or 512)
            tok = Tokenizer.from_str(original.to_str())
            tok.no_truncation()
            tok.no_padding()
            specials = tok.post_processor.num_special_tokens_to_add(False) if tok.post_processor else 0
            self._encode_fn = lambda t: list(tok.encode(t, add_special_tokens=False).offsets)
            self._max_tokens = max_len - specials
        return self._encode_fn, self._max_tokens

    def _embed_raw(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            model = self._load()
            return [[float(x) for x in vec] for vec in model.embed(texts, batch_size=64)]

    def _embed_pooled(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            encode, max_tokens = self._tokenizer_setup()
        windows = [split_windows(t, encode, max_tokens) for t in texts]
        if all(len(w) == 1 for w in windows):           # nothing long: exactly the default call
            return self._embed_raw(texts)
        short = [i for i, w in enumerate(windows) if len(w) == 1]
        out: list[list[float] | None] = [None] * len(texts)
        if short:
            for i, vec in zip(short, self._embed_raw([texts[i] for i in short]), strict=True):
                out[i] = vec
        for i, w in enumerate(windows):
            if len(w) > 1:
                out[i] = mean_normalised(self._embed_raw(w))
        return out  # type: ignore[return-value]

    def version(self) -> str:
        try:
            from importlib.metadata import version

            return f"fastembed {version('fastembed')}"
        except Exception:  # noqa: BLE001
            return "fastembed"
