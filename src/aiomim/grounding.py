"""Deterministic check that a quoted span really occurs in a source text.

This is the pipeline's first line of defence against hallucination: every
extracted finding must carry at least one verbatim quote, and a finding whose
quotes cannot be located in the paper is discarded before it can reach the
knowledge graph. No model is involved in this check.

Matching is done on normalised tokens so that differences in whitespace, line
wrapping, hyphenation, Unicode punctuation and case do not count as mismatches,
while a changed number, gene symbol or residue does.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

GROUNDED = 0.85

_TOKEN = re.compile(r"[a-z0-9]+")
_ELLIPSIS = re.compile(r"\s*(?:\[\s*\.\.\.\s*\]|\.\.\.+|…)\s*")
_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "µ": "mu", "σ": "sigma", "τ": "tau", "ω": "omega",
}


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text or "")
    for greek, name in _GREEK.items():
        if greek in text:
            text = text.replace(greek, name)
    # Rejoin words split by end-of-line hyphenation: "mito-\nchondrial" -> "mitochondrial".
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return _TOKEN.findall(text.lower())


class SourceIndex:
    """Token index over one source document, built once and queried per quote."""

    def __init__(self, text: str):
        self.tokens = tokens(text)
        self._joined = " " + " ".join(self.tokens) + " "
        self._positions: dict[str, list[int]] = defaultdict(list)
        for i, tok in enumerate(self.tokens):
            self._positions[tok].append(i)

    def score(self, quote: str) -> float:
        """How much of `quote` appears, in order, in the source: 1.0 is verbatim.

        A quote that elides text with an ellipsis is scored piece by piece and
        takes the score of its worst piece, so one invented fragment cannot hide
        behind a genuine one.
        """
        pieces = [p for p in _ELLIPSIS.split(quote or "") if p.strip()]
        scores = [self._score_piece(tokens(p)) for p in pieces]
        scores = [s for s in scores if s is not None]
        return min(scores) if scores else 0.0

    def contains(self, quote: str) -> bool:
        return self.score(quote) >= GROUNDED

    def _score_piece(self, q: list[str]) -> float | None:
        if not q:
            return None
        if " " + " ".join(q) + " " in self._joined:
            return 1.0
        if len(q) < 4:
            return 0.0  # too short to match fuzzily without false positives

        # Anchor on the quote's rarest tokens to propose where it might start.
        anchors = sorted(
            (i for i, tok in enumerate(q) if tok in self._positions),
            key=lambda i: len(self._positions[q[i]]),
        )[:6]
        starts: set[int] = set()
        for qi in anchors:
            for di in self._positions[q[qi]][:200]:
                starts.add(max(0, di - qi))
        best = 0.0
        slack = max(3, len(q) // 5)
        for start in starts:
            window = self.tokens[max(0, start - slack): start + len(q) + slack]
            matcher = SequenceMatcher(None, q, window, autojunk=False)
            matched = sum(block.size for block in matcher.get_matching_blocks())
            best = max(best, matched / len(q))
            if best >= 0.999:
                break
        return best
