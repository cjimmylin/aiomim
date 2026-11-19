"""The official OMIM API (api.omim.org). Used only when `OMIM_API_KEY` is set.

Without a key every function returns None. omim.org entry pages are never
scraped.
"""

from __future__ import annotations

import logging
import re

from ..config import get_settings
from ..http import HttpError, get_http
from ..models import SECTION_HEADINGS

log = logging.getLogger(__name__)

API = "https://api.omim.org/api/entry"

# OMIM textSectionName values that do not convert mechanically to our keys.
_SECTION_ALIASES = {
    "text": "intro",
    "": "intro",
    "cloning": "cloning_expression",
    "cloningAndExpression": "cloning_expression",
    "geneStructure": "gene_structure",
    "genotypePhenotypeCorrelations": "genotype_phenotype_correlations",
    "genotypePhenotype": "genotype_phenotype_correlations",
    "biochemicalFeatures": "biochemical_features",
    "clinicalManagement": "clinical_management",
    "populationGenetics": "population_genetics",
    "animalModel": "animal_model",
    "otherFeatures": "other_features",
}


def section_key(name: str) -> str:
    if name in _SECTION_ALIASES:
        return _SECTION_ALIASES[name]
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    if snake in SECTION_HEADINGS:
        return snake
    title = name.strip().lower()
    for key, heading in SECTION_HEADINGS.items():
        if heading.lower() == title:
            return key
    return snake


def parse_entry(entry: dict) -> dict:
    text: dict[str, str] = {}
    for item in entry.get("textSectionList", []) or []:
        sec = item.get("textSection", item) or {}
        key = section_key(sec.get("textSectionName", "") or "")
        content = (sec.get("textSectionContent") or "").strip()
        if content:
            text[key] = (text[key] + "\n\n" + content) if key in text else content
    synopsis: dict[str, str] = {}
    cs = entry.get("clinicalSynopsis") or {}
    for k, v in cs.items():
        if isinstance(v, str) and not k.endswith("Exists") and k not in ("mimNumber", "prefix",
                                                                       "preferredTitle", "oldFormat"):
            synopsis[k] = v
    dates = {"created": entry.get("dateCreated") or entry.get("epochCreated"),
             "edited": entry.get("dateUpdated") or entry.get("epochUpdated")}
    return {"text": text, "clinical_synopsis": synopsis, **dates}


def fetch_entry(mim: str) -> dict | None:
    key = get_settings().omim_api_key
    if not key:
        return None
    try:
        data = get_http().get_json(API, {
            "mimNumber": str(mim),
            "include": "text,clinicalSynopsis,allelicVariantList,referenceList,geneMap,dates",
            "format": "json",
        }, headers={"ApiKey": key}, max_age_s=30 * 86400)
    except HttpError as exc:
        log.warning("OMIM API failed for %s: %s", mim, exc)
        return None
    try:
        entries = data["omim"]["entryList"]
        entry = entries[0]["entry"]
    except (KeyError, IndexError, TypeError):
        return None
    return parse_entry(entry)
