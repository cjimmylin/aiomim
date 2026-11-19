"""Assemble the gold standard for an OMIM entry from public OMIM-derived sources.

Nothing here touches omim.org entry pages. Sources:
  * NCBI E-utilities: OMIM title/symbol/prefix, the entry's cited PMIDs, ClinVar and MedGen links
  * ClinVar: OMIM's own allelic-variant submissions (per-paper paragraphs)
  * HPO phenotype.hpoa: phenotype and inheritance annotations
  * MedGen: definition, OMIM alternative titles, inheritance, associated genes
  * mim2gene_medgen / mim2gene.txt: gene-phenotype links
  * OMIM API (only with OMIM_API_KEY): full text and clinical synopsis
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from collections import deque

from .config import get_settings
from .models import HPO_TO_INHERITANCE, GoldAllelicVariant, GoldEntry, GoldGene, Seed
from .sources import mim2gene, ncbi
from .sources.clinvar import omim_allelic_variants
from .sources.hgnc import gene_info, mito_symbol
from .sources.hpo import get_hpo
from .sources.medgen import medgen_for_mim
from .sources.omim_api import fetch_entry

log = logging.getLogger(__name__)


def _clean(mim: str) -> str:
    return re.sub(r"\D", "", str(mim))


def _gold_path(mim: str):
    return get_settings().home / "gold" / f"{mim}.json"


def inheritance_from_hpo(hpo_ids: list[str]) -> list[str]:
    """Map HPO mode-of-inheritance ids to codes, climbing to the nearest mapped ancestor."""
    hpo = get_hpo()
    codes: list[str] = []
    for hid in hpo_ids:
        start = hpo.resolve(hid) or hid
        queue, seen = deque([start]), {start}
        while queue:
            cur = queue.popleft()
            if cur in HPO_TO_INHERITANCE:
                code = HPO_TO_INHERITANCE[cur]
                if code not in codes:
                    codes.append(code)
                break
            for p in hpo.parents(cur):
                if p not in seen:
                    seen.add(p)
                    queue.append(p)
    return codes


def _entry_type(prefix: str, mim: str) -> str:
    if prefix in ("*", "+"):
        return "gene"
    if prefix in ("#", "%"):
        return "phenotype"
    try:
        typ = mim2gene.mim_entry_type(mim)
    except Exception:  # pragma: no cover - network trouble
        typ = None
    return "gene" if typ in ("gene", "gene/phenotype") else "phenotype"


def _fill_gene(g: GoldGene) -> GoldGene:
    info = gene_info(g.symbol) if g.symbol else None
    if info is None:
        return g
    return g.model_copy(update={
        "symbol": info.symbol,
        "entrez_id": g.entrez_id or info.entrez_id,
        "mim": g.mim or info.omim_id,
        "location": g.location or info.location,
    })


def _merge_genes(groups: list[list[GoldGene]]) -> list[GoldGene]:
    out: dict[str, GoldGene] = {}
    for group in groups:
        for g in group:
            g = _fill_gene(g)
            if not g.symbol:
                continue
            cur = out.get(g.symbol)
            if cur is None:
                out[g.symbol] = g
            else:
                upd = {f: getattr(g, f) for f in ("entrez_id", "mim", "location")
                       if not getattr(cur, f) and getattr(g, f)}
                if g.source and g.source not in cur.source:
                    upd["source"] = f"{cur.source}; {g.source}" if cur.source else g.source
                out[g.symbol] = cur.model_copy(update=upd)
    return list(out.values())


def build_gold(mim: str, refresh: bool = False) -> GoldEntry:
    mim = _clean(mim)
    path = _gold_path(mim)
    if path.exists() and not refresh:
        try:
            return GoldEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("unreadable cached gold for %s; rebuilding", mim)

    today = _dt.date.today().isoformat()
    prov: dict[str, str] = {"retrieved": today}
    summary = ncbi.omim_summary(mim)
    prov["header"] = "NCBI E-utilities esummary db=omim"
    prefix = summary["prefix"]
    entry_type = _entry_type(prefix, mim)

    gold = GoldEntry(mim=mim, prefix=prefix, entry_type=entry_type, title=summary["title"],
                     alt_titles=summary["alt_titles"], symbol=summary["symbol"])

    gold.cited_pmids = ncbi.omim_cited_pmids(mim)
    prov["cited_pmids"] = "NCBI elink omim_pubmed_cited"

    # MedGen: definition, alternative titles, inheritance, genes.
    medgen = None
    try:
        medgen = medgen_for_mim(mim) if entry_type == "phenotype" else None
    except Exception as exc:
        prov["medgen"] = f"error: {exc}"
        log.warning("MedGen failed for %s: %s", mim, exc)
    if medgen:
        prov["medgen"] = f"MedGen uid {medgen['uid']} ({medgen['cui']})"
        gold.medgen_cui = medgen["cui"]
        gold.definition = medgen["definition"]
        gold.definition_source = medgen["definition_source"]
        if medgen["definition"]:
            prov["definition"] = f"MedGen ({medgen['definition_source'] or 'unspecified source'})"
        if not gold.alt_titles and medgen["omim_alt_titles"]:
            gold.alt_titles = list(medgen["omim_alt_titles"])
            prov["alt_titles"] = "MedGen OMIM ETAL names"
        elif gold.alt_titles:
            prov["alt_titles"] = "NCBI E-utilities esummary db=omim"
        if not gold.symbol and medgen["omim_symbol"]:
            gold.symbol = medgen["omim_symbol"]
            prov["symbol"] = "MedGen OMIM ACR name"

    # HPO annotations and inheritance.
    try:
        hpo = get_hpo()
        gold.hpo_annotations = hpo.annotations(mim)
        prov["hpo_annotations"] = "HPO phenotype.hpoa"
    except Exception as exc:
        prov["hpo_annotations"] = f"error: {exc}"
        log.warning("HPO failed for %s: %s", mim, exc)
    inh: list[str] = []
    if gold.hpo_annotations:
        inh = inheritance_from_hpo([a.hpo_id for a in gold.hpo_annotations if a.aspect == "I"])
        if inh:
            prov["inheritance"] = "HPO phenotype.hpoa aspect I"
    if medgen and medgen["inheritance"]:
        new = [c for c in medgen["inheritance"] if c not in inh]
        inh += new
        if new:
            prov["inheritance"] = (prov.get("inheritance", "") + "; MedGen modes of inheritance").lstrip("; ")
    gold.inheritance = sorted(set(inh))

    # ClinVar: OMIM allelic variants and their per-paper paragraphs.
    avs: list[GoldAllelicVariant] = []
    try:
        vids = ncbi.omim_linked_ids(mim, "clinvar")
        avs = omim_allelic_variants(vids) if vids else []
        if entry_type == "phenotype":
            avs = [av for av in avs if any(mim in p.mims for p in av.paragraphs)]
        else:
            avs = [av for av in avs if av.omim_id.split(".")[0] == mim] or avs
        prov["allelic_variants"] = f"ClinVar OMIM submissions ({len(vids)} linked variations)"
    except Exception as exc:
        prov["allelic_variants"] = f"error: {exc}"
        log.warning("ClinVar failed for %s: %s", mim, exc)
    gold.allelic_variants = avs

    # Genes.
    try:
        if entry_type == "phenotype":
            from_m2g = mim2gene.genes_for_phenotype(mim)
            from_medgen = list(medgen["genes"]) if medgen else []
            from_clinvar = []
            for av in avs:
                sym = mito_symbol(av.gene_symbol)
                if sym:
                    from_clinvar.append(GoldGene(symbol=sym, mim=av.omim_id.split(".")[0],
                                                 source="ClinVar OMIM allelic variants"))
            gold.genes = _merge_genes([from_m2g, from_medgen, from_clinvar])
            prov["genes"] = "mim2gene_medgen GeneMap; MedGen associated genes; ClinVar OMIM variants; HGNC"
        else:
            g = mim2gene.gene_for_gene_mim(mim)
            if g is None and gold.symbol:
                g = GoldGene(symbol=gold.symbol, mim=mim, source="esummary")
            gold.genes = _merge_genes([[g]]) if g else []
            prov["genes"] = "mim2gene.txt; HGNC"
    except Exception as exc:
        prov["genes"] = f"error: {exc}"
        log.warning("gene lookup failed for %s: %s", mim, exc)

    # OMIM API text (only with a key).
    api = fetch_entry(mim)
    if api:
        gold.omim_text = api["text"] or None
        gold.omim_clinical_synopsis = api["clinical_synopsis"] or None
        prov["omim_text"] = "OMIM API"
        if api.get("created"):
            prov["omim_created"] = str(api["created"])
        if api.get("edited"):
            prov["omim_edited"] = str(api["edited"])

    gold.provenance = prov
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(gold.model_dump_json(indent=1), encoding="utf-8")
    return gold


def seed_from_gold(gold: GoldEntry) -> Seed:
    if gold.entry_type == "gene":
        gene_symbols = [gold.genes[0].symbol] if gold.genes else ([gold.symbol] if gold.symbol else [])
    else:
        gene_symbols = [g.symbol for g in gold.genes]
    years = [p.year for p in ncbi.pubmed_fetch(gold.cited_pmids) if p.year]
    return Seed(
        mim=gold.mim, entry_type="gene" if gold.entry_type == "gene" else "phenotype",
        prefix=gold.prefix, title=gold.title, alt_titles=list(gold.alt_titles), symbol=gold.symbol,
        gene_symbols=gene_symbols, max_year=max(years) if years else None,
    )


def gold_coverage(mim: str) -> dict:
    g = build_gold(mim)
    paras = g.gold_paragraphs
    pmids = {p for para in paras for p in para.pmids}
    return {
        "mim": g.mim, "title": g.title, "prefix": g.prefix, "entry_type": g.entry_type,
        "n_refs": len(g.cited_pmids), "n_hpo": len(g.hpo_annotations),
        "n_gold_paragraphs": len(paras), "n_gold_paragraph_pmids": len(pmids),
        "n_genes": len(g.genes), "inheritance": list(g.inheritance),
    }


def _pdat(d: str) -> str:
    return d.strip().replace("-", "/")


def find_entries(created_from: str, created_to: str, entry_type: str = "phenotype",
                 limit: int = 200) -> list[str]:
    """MIM numbers first published between the two dates (YYYY/MM/DD or YYYY-MM-DD)."""
    term = f"{_pdat(created_from)}:{_pdat(created_to)}[PDAT]"
    mims = ncbi.omim_search(term, retmax=max(limit * 5, 500))
    unknown = []
    types: dict[str, str] = {}
    for m in mims:
        try:
            t = mim2gene.mim_entry_type(m)
        except Exception:
            t = None
        if t:
            types[m] = "gene" if t in ("gene", "gene/phenotype") else (
                "removed" if t.startswith("moved") else "phenotype")
        else:
            unknown.append(m)
    if unknown:
        for m, s in ncbi.omim_summaries(unknown).items():
            p = s["prefix"]
            types[m] = "gene" if p in ("*", "+") else ("removed" if p == "^" else "phenotype")
    out = [m for m in mims if types.get(m) == entry_type]
    return out[:limit]
