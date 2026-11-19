"""ClinVar VCV records: OMIM's own allelic-variant submissions and their paragraphs."""

from __future__ import annotations

import logging
import re

from lxml import etree

from ..cache import DiskCache
from ..config import get_settings
from ..http import get_http
from ..models import GoldAllelicVariant, GoldParagraph, squash

log = logging.getLogger(__name__)

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH = 50
CACHE_S = 30 * 86400

_PARSER = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False, no_network=True)


def _text(el) -> str:
    return squash("".join(el.itertext())) if el is not None else ""


def _protein_change(va) -> str:
    """Single-letter protein change of the variation, if ClinVar gives one."""
    for el in va.iter("ProteinChange"):
        if el.text and el.text.strip():
            return el.text.strip()
    for el in va.iter("ProteinExpression"):
        if el.get("singleLetterProteinChange"):
            return el.get("singleLetterProteinChange")
    for el in va.iter("ProteinExpression"):
        if el.get("change"):
            return el.get("change")
    return ""


def parse_variation_archive(va) -> list[GoldAllelicVariant]:
    """One GoldAllelicVariant per OMIM SCV in a <VariationArchive> (merged later)."""
    vid = va.get("VariationID", "")
    vname = va.get("VariationName", "")
    protein = _protein_change(va)
    out: list[GoldAllelicVariant] = []
    for ca in va.iter("ClinicalAssertion"):
        acc = ca.find("ClinVarAccession")
        if acc is None or acc.get("SubmitterName") != "OMIM":
            continue
        allele = ca.find(".//SimpleAllele")
        if allele is None:
            allele = ca
        av_id = ""
        for x in allele.iter("XRef"):
            if x.get("DB") == "OMIM" and x.get("Type") == "Allelic variant":
                av_id = x.get("ID", "")
                break
        sub = ca.find("ClinVarSubmissionID")
        local_key = sub.get("localKey", "") if sub is not None else ""
        if not av_id:
            m = re.match(r"(\d{6}\.\d{4})", local_key)
            av_id = m.group(1) if m else ""
        if not av_id:
            continue
        name = squash(allele.findtext("Name") or "")
        if not name and sub is not None:
            name = (sub.get("title") or "").split("_")[0]
        gene = ""
        g = allele.find("GeneList/Gene")
        if g is not None:
            gene = g.get("Symbol", "")
        if not gene and name:
            gene = name.split(",")[0].strip()
        phenotypes: list[str] = []
        for trait in ca.findall("TraitSet/Trait"):
            pn = trait.find("Name/ElementValue")
            if pn is not None and _text(pn) and _text(pn) not in phenotypes:
                phenotypes.append(_text(pn))
        if not phenotypes and "_" in local_key:
            phenotypes.append(local_key.split("_", 1)[1])
        paragraphs: list[GoldParagraph] = []
        for od in ca.iter("ObservedData"):
            desc = None
            for at in od.findall("Attribute"):
                if at.get("Type") == "Description":
                    desc = _text(at)
            if not desc:
                continue
            pmids = []
            for cit in od.findall("Citation"):
                for cid in cit.findall("ID"):
                    if cid.get("Source") == "PubMed" and (cid.text or "").strip():
                        p = cid.text.strip()
                        if p not in pmids:
                            pmids.append(p)
            mims = []
            for x in od.findall("XRef"):
                if x.get("DB") == "OMIM" and x.get("Type", "MIM") == "MIM" and x.get("ID"):
                    if x.get("ID") not in mims:
                        mims.append(x.get("ID"))
            paragraphs.append(GoldParagraph(text=desc, pmids=pmids, mims=mims))
        out.append(GoldAllelicVariant(
            omim_id=av_id, gene_symbol=gene, name=name, clinvar_variation_id=vid,
            clinvar_name=vname, scv=acc.get("Accession", ""), protein_change=protein,
            phenotypes=phenotypes, paragraphs=paragraphs,
        ))
    return out


def merge_variants(items: list[GoldAllelicVariant]) -> list[GoldAllelicVariant]:
    merged: dict[str, GoldAllelicVariant] = {}
    for av in items:
        cur = merged.get(av.omim_id)
        if cur is None:
            merged[av.omim_id] = av.model_copy(deep=True)
            continue
        for ph in av.phenotypes:
            if ph not in cur.phenotypes:
                cur.phenotypes.append(ph)
        by_text = {p.text: p for p in cur.paragraphs}
        for para in av.paragraphs:
            have = by_text.get(para.text)
            if have is None:
                cur.paragraphs.append(para.model_copy(deep=True))
                by_text[para.text] = cur.paragraphs[-1]
            else:
                have.pmids.extend(p for p in para.pmids if p not in have.pmids)
                have.mims.extend(m for m in para.mims if m not in have.mims)
        if av.scv and av.scv not in cur.scv.split(","):
            cur.scv = f"{cur.scv},{av.scv}" if cur.scv else av.scv
        for f in ("gene_symbol", "name", "clinvar_name", "protein_change", "clinvar_variation_id"):
            if not getattr(cur, f) and getattr(av, f):
                setattr(cur, f, getattr(av, f))
    return list(merged.values())


def parse_vcv_xml(xml: str | bytes) -> list[GoldAllelicVariant]:
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    root = etree.fromstring(data, _PARSER)
    if root is None:
        return []
    items: list[GoldAllelicVariant] = []
    for va in root.iter("VariationArchive"):
        items.extend(parse_variation_archive(va))
    return merge_variants(items)


def _cache() -> DiskCache:
    return DiskCache(get_settings().http_cache / "clinvar_vcv", suffix=".xml")


def fetch_vcv(variation_ids: list[str]) -> dict[str, str]:
    """Raw <VariationArchive> XML per variation id (cached per id)."""
    ids = [str(v).strip() for v in variation_ids if str(v).strip().isdigit()]
    cache = _cache()
    out: dict[str, str] = {}
    missing = []
    for vid in dict.fromkeys(ids):
        hit = cache.get_text(vid, CACHE_S)
        if hit is not None:
            out[vid] = hit
        else:
            missing.append(vid)
    for i in range(0, len(missing), BATCH):
        chunk = missing[i:i + BATCH]
        xml = get_http().get_text(EFETCH, {"db": "clinvar", "rettype": "vcv", "is_variationid": "true",
                                          "id": ",".join(chunk)}, cache=False)
        root = etree.fromstring(xml.encode("utf-8"), _PARSER)
        if root is None:
            continue
        for va in root.iter("VariationArchive"):
            vid = va.get("VariationID", "")
            if vid in chunk:
                text = etree.tostring(va, encoding="unicode")
                cache.put_text(vid, text)
                out[vid] = text
    return out


def omim_allelic_variants(variation_ids: list[str]) -> list[GoldAllelicVariant]:
    raw = fetch_vcv(variation_ids)
    items: list[GoldAllelicVariant] = []
    for vid in dict.fromkeys(str(v) for v in variation_ids):
        if vid not in raw:
            continue
        try:
            va = etree.fromstring(raw[vid].encode("utf-8"), _PARSER)
        except etree.XMLSyntaxError:
            continue
        if va is not None:
            items.extend(parse_variation_archive(va))
    return merge_variants(items)
