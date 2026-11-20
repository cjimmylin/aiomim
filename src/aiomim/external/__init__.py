"""Experiment B (docs/experiments-round2.md): published systems run as released.

Shared harness for the three integrations (PaperQA2, STORM, GraphRAG):

    shim      a local OpenAI-compatible server in front of the project's one model
              (Claude Code command line, project disk cache, ledger) and one local
              embedding model
    corpus    the 38 entries in their seeded order, and each entry's supplied papers
              exported as text files
    tasks     the task wording: STORM's topic, the six section questions
    adapt     the intermediate format an integration writes, validated, saved, and
              converted into the project's entry format with text unedited
    score     facts conveyed (cited and whole-draft), split by availability, the
              optional audit, uncited share, usage; the summary across systems
    sys_echo  a trivial stand-in system proving the path end to end

See README.md in this folder.
"""

from __future__ import annotations

from pathlib import Path

#: Where integrations write: runs/external/<system>/<mim>/ (git-ignored, like all of runs/).
def runs_root() -> Path:
    from ..config import get_settings

    return get_settings().runs / "external"
