"""MedGen concept for an OMIM phenotype: definition, names, inheritance, genes, features."""

from __future__ import annotations

import logging
import re

from lxml import etree

from ..models import INHERITANCE_HPO, GoldGene, squash
from .ncbi import _eutils, omim_linked_ids

log = logging.getLogger(__name__)

_PARSER = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False, no_network=True)

_MODE_BY_NAME = {label.lower(): code for code, (_, label) in INHERITANCE_HPO.items()}
_MODE_ALIASES = {
    "x-linked recessive": "XLR", "x-linked dominant": "XLD", "sporadic": None,
    "somatic": "SOMATIC", "mitochondrial": "MT", "maternal": "MT",
}


def inheritance_code(mode_name: str) -> str | None:
    """'Autosomal dominant inheritance' -> 'AD' (None if unmapped)."""
    n = squash(mode_name).lower()
    n = re.sub(r"\s+inheritance$", "", n)
    if n in _MODE_BY_NAME:
        return _MODE_BY_NAME[n]
    if n in _MODE_ALIASES:
        return _MODE_ALIASES[n]
    for label, code in _MODE_BY_NAME.items():
        if n.startswith(label):
            return code
    return None


def parse_conceptmeta(meta: str, mim: str | None = None) -> dict:
    """Parse MedGen's `conceptmeta` XML fragment (it has no single root)."""
    root = etree.fromstring(f"<root>{meta or ''}</root>".encode("utf-8"), _PARSER)
    out = {"names": [], "definitions": [], "inheritance": [], "inheritance_names": [], "genes": [],
           "clinical_feature_hpo": [], "omim_symbol": "", "omim_alt_titles": [], "omim_title": ""}
    if root is None:
        return out
    for n in root.findall("Names/Name"):
        rec = {"sab": n.get("SAB", ""), "tty": n.get("TTY", ""), "sdui": n.get("SDUI", ""),
               "text": squash(n.text or "")}
        out["names"].append(rec)
        if rec["sab"] != "OMIM" or (mim and rec["sdui"] != mim):
            continue
        if rec["tty"] == "ACR" and not out["omim_symbol"]:
            out["omim_symbol"] = rec["text"]
        elif rec["tty"] == "PT" and not out["omim_title"]:
            out["omim_title"] = rec["text"]
        elif rec["tty"] == "ETAL" and rec["text"] not in out["omim_alt_titles"]:
            out["omim_alt_titles"].append(rec["text"])
    for d in root.findall("Definitions/Definition"):
        txt = squash("".join(d.itertext()))
        if txt:
            out["definitions"].append({"source": d.get("source", ""), "text": txt})
    for m in root.findall("ModesOfInheritance/ModeOfInheritance"):
        name = squash(m.findtext("Name") or "")
        if not name:
            continue
        out["inheritance_names"].append(name)
        code = inheritance_code(name)
        if code and code not in out["inheritance"]:
            out["inheritance"].append(code)
    for g in root.findall("AssociatedGenes/Gene"):
        sym = squash(g.text or "")
        if sym:
            out["genes"].append(GoldGene(symbol=sym, entrez_id=g.get("gene_id", ""),
                                         location=g.get("cytogen_loc", ""), source="MedGen"))
    for cf in root.findall("ClinicalFeatures/ClinicalFeature"):
        hp = cf.get("SDUI", "")
        if hp.startswith("HP:") and hp not in out["clinical_feature_hpo"]:
            out["clinical_feature_hpo"].append(hp)
    return out


def _score(meta: dict, mim: str) -> int:
    names = meta["names"]
    if any(n["sab"] == "OMIM" and n["tty"] == "PT" and n["sdui"] == mim for n in names):
        return 3
    if any(n["sab"] == "OMIM" and n["sdui"] == mim and n["tty"] in ("ACR", "ETAL") for n in names):
        return 2
    if any(n["sab"] == "OMIM" and n["sdui"] == mim for n in names):
        return 1
    return 0


def medgen_for_mim(mim: str) -> dict | None:
    mim = re.sub(r"\D", "", str(mim))
    uids = omim_linked_ids(mim, "medgen")
    if not uids:
        data = _eutils("esearch", {"db": "medgen", "term": f"{mim}[mim]", "retmax": 20},
                       max_age_s=30 * 86400)
        uids = (data.get("esearchresult") or {}).get("idlist") or []
    if not uids:
        return None
    data = _eutils("esummary", {"db": "medgen", "id": ",".join(uids)}, max_age_s=30 * 86400)
    res = data.get("result") or {}
    best = None
    for rank, uid in enumerate(res.get("uids", [])):
        doc = res.get(uid) or {}
        meta = parse_conceptmeta(doc.get("conceptmeta", ""), mim)
        key = (_score(meta, mim), -rank)
        if best is None or key > best[0]:
            best = (key, uid, doc, meta)
    if best is None:
        return None
    _, uid, doc, meta = best
    definition = squash(((doc.get("definition") or {}).get("value")) or "")
    source = ""
    for d in meta["definitions"]:
        if definition and (d["text"] == definition or d["text"][:80] == definition[:80]):
            source = d["source"]
            break
    if not definition and meta["definitions"]:
        definition, source = meta["definitions"][0]["text"], meta["definitions"][0]["source"]
    elif definition and not source and meta["definitions"]:
        source = meta["definitions"][0]["source"]
    return {
        "uid": str(uid),
        "cui": doc.get("conceptid", ""),
        "title": doc.get("title", ""),
        "definition": definition,
        "definition_source": source,
        "omim_symbol": meta["omim_symbol"],
        "omim_alt_titles": meta["omim_alt_titles"],
        "inheritance": meta["inheritance"],
        "genes": meta["genes"],
        "clinical_feature_hpo": meta["clinical_feature_hpo"],
    }
