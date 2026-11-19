"""OMIM's public mim2gene.txt and NCBI's mim2gene_medgen: entry types and gene links."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..config import get_settings
from ..http import get_http
from ..models import GoldGene

MIM2GENE_URL = "https://www.omim.org/static/omim/data/mim2gene.txt"
MIM2GENE_MEDGEN_URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen"
REFRESH_S = 30 * 86400


@dataclass
class _Tables:
    entry_type: dict[str, str] = field(default_factory=dict)
    gene_by_mim: dict[str, tuple[str, str, str]] = field(default_factory=dict)  # mim -> (entrez, symbol, ensembl)
    gene_mim_by_entrez: dict[str, str] = field(default_factory=dict)
    symbol_by_entrez: dict[str, str] = field(default_factory=dict)
    pheno_genes: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))
    gene_phenos: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    medgen_cui: dict[str, str] = field(default_factory=dict)


def parse_mim2gene(path: Path, t: _Tables) -> None:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = (line.rstrip("\n").split("\t") + [""] * 5)[:5]
            mim, typ, entrez, symbol, ensembl = (p.strip() for p in parts)
            t.entry_type[mim] = typ
            if entrez:
                t.gene_by_mim[mim] = (entrez, symbol, ensembl)
                if typ in ("gene", "gene/phenotype"):
                    t.gene_mim_by_entrez.setdefault(entrez, mim)
                if symbol:
                    t.symbol_by_entrez.setdefault(entrez, symbol)


def parse_mim2gene_medgen(path: Path, t: _Tables) -> None:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = (line.rstrip("\n").split("\t") + [""] * 6)[:6]
            mim, gene_id, typ, source, cui, _ = (p.strip() for p in parts)
            if cui and cui != "-":
                t.medgen_cui.setdefault(mim, cui)
            if typ != "phenotype" or gene_id in ("", "-") or "GeneMap" not in source:
                continue
            if all(g != gene_id for g, _ in t.pheno_genes[mim]):
                t.pheno_genes[mim].append((gene_id, source))
            if mim not in t.gene_phenos[gene_id]:
                t.gene_phenos[gene_id].append(mim)


_TABLES: _Tables | None = None
_LOCK = threading.Lock()


def _tables() -> _Tables:
    global _TABLES
    with _LOCK:
        if _TABLES is None:
            d = get_settings().home / "downloads"
            http = get_http()
            p1 = http.download(MIM2GENE_URL, d / "mim2gene.txt", max_age_s=REFRESH_S)
            p2 = http.download(MIM2GENE_MEDGEN_URL, d / "mim2gene_medgen", max_age_s=REFRESH_S)
            t = _Tables()
            parse_mim2gene(p1, t)
            parse_mim2gene_medgen(p2, t)
            _TABLES = t
        return _TABLES


def mim_entry_type(mim: str) -> str | None:
    return _tables().entry_type.get(str(mim))


def gene_for_gene_mim(mim: str) -> GoldGene | None:
    got = _tables().gene_by_mim.get(str(mim))
    if not got:
        return None
    entrez, symbol, _ = got
    return GoldGene(symbol=symbol, entrez_id=entrez, mim=str(mim), source="mim2gene")


def genes_for_phenotype(mim: str) -> list[GoldGene]:
    t = _tables()
    out = []
    for entrez, source in t.pheno_genes.get(str(mim), []):
        out.append(GoldGene(
            symbol=t.symbol_by_entrez.get(entrez, ""), entrez_id=entrez,
            mim=t.gene_mim_by_entrez.get(entrez, ""), source=f"mim2gene_medgen ({source})",
        ))
    return out


def phenotypes_for_gene(entrez_id: str) -> list[str]:
    return list(_tables().gene_phenos.get(str(entrez_id), []))


def medgen_cui_for_mim(mim: str) -> str | None:
    return _tables().medgen_cui.get(str(mim))
