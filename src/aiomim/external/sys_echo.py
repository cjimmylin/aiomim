"""A trivial stand-in "system" that proves the harness end to end without any published package.

For each entry: export the corpus, start the adapter, make ONE chat request through it (plain
HTTP, OpenAI wire format) asking for a short cited summary of the supplied papers, map the
"[PMID n]" citations back to the supplied papers, save the intermediate format, then score.

    PYTHONPATH=src python -m aiomim.external.sys_echo 621313 301059
    PYTHONPATH=src python -m aiomim.external.score score --system echo --entries 621313 301059
    PYTHONPATH=src python -m aiomim.external.score summarize --systems echo --out runs/external/echo/summary

A real integration follows the same outline in `sys_<name>.py`, except that the published
package runs in its own virtual environment as a subprocess (see README.md).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request

from .adapt import entry_dir, save_output
from .corpus import export_entry
from .shim import TAG_HEADER, ShimServer

SYSTEM = "echo"
SYSTEM_PROMPT = "You summarise biomedical papers accurately and concisely."
_CITE = re.compile(r"\[(?:PMIDs?:?\s*)?(\d{6,9}(?:\s*[,;]\s*(?:PMID:?\s*)?\d{6,9})*)\]", re.I)


def build_prompt(title: str, texts: dict[str, str]) -> str:
    papers = "\n\n".join(f'<paper pmid="{pmid}">\n{text}\n</paper>' for pmid, text in texts.items())
    return (f"Disorder: {title}\n\nWrite a short summary, in three to six paragraphs separated by blank lines, of "
            "what the papers below report about this disorder. After each sentence, cite the papers that support "
            "it by PubMed id in square brackets, e.g. [PMID 12345678] or [PMID 12345678, 23456789].\n\n" + papers)


def map_citations(text: str, supplied: set[str]) -> tuple[list[str], list[str]]:
    """(mapped supplied PMIDs, raw citation markers) of one paragraph."""
    pmids, raw = [], []
    for m in _CITE.finditer(text):
        raw.append(m.group(0))
        pmids.extend(p for p in re.findall(r"\d{6,9}", m.group(1)) if p in supplied)
    return list(dict.fromkeys(pmids)), raw


def chat(base_url: str, body: dict, tag: str) -> dict:
    req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", TAG_HEADER: tag}, method="POST")
    with urllib.request.urlopen(req, timeout=1800) as resp:
        return json.loads(resp.read())


def run_entry(mim: str) -> dict:
    folder = entry_dir(SYSTEM, mim)
    corpus = export_entry(mim, folder / "corpus")
    tag = f"{SYSTEM}/{mim}"
    started = time.time()
    with ShimServer(tag=tag, ledger=folder / "ledger.jsonl") as base_url:
        reply = chat(base_url, {"model": "claude-opus-5-5", "temperature": 0,
                                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                             {"role": "user", "content": build_prompt(corpus.title_ordinary,
                                                                                      corpus.texts)}]}, tag)
    choice = reply["choices"][0]
    supplied = set(corpus.pmids)
    blocks = []
    for para in re.split(r"\n\s*\n", choice["message"]["content"] or ""):
        if para.strip():
            pmids, raw = map_citations(para, supplied)
            blocks.append({"section": "Summary", "text": para.strip(), "pmids": pmids, "citations": raw})
    stopped = choice["finish_reason"] == "content_filter"
    output = {
        "system": SYSTEM, "mim": mim, "blocks": blocks,
        "stopped": ("safety stop" if stopped else None) if not blocks else None,
        "meta": {"package": "aiomim.external.sys_echo", "version": "1", "tag": tag,
                 "settings_changed": [{"setting": "(none)", "default": "", "value": "",
                                       "reason": "stand-in, not a published system"}],
                 "calls": 1, "stops": int(stopped), "seconds": round(time.time() - started, 1),
                 "ledgers": [str(folder / "ledger.jsonl")]},
    }
    save_output(output)
    return {"mim": mim, "blocks": len(blocks), "cited_blocks": sum(1 for b in blocks if b["pmids"]),
            "stopped": stopped}


if __name__ == "__main__":
    for mim in sys.argv[1:]:
        print(json.dumps(run_entry(mim)))
