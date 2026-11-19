"""Stage 4: the evidence knowledge graph.

Findings from all papers are joined into one graph in which every edge carries
its provenance (the finding, and through it the paper and the quotes):

    Paper ─reports▶ Finding ─in_section▶ Section
                       ├─mentions_gene▶ Gene ◀─in_gene─ Variant
                       ├─reports_variant▶ Variant
                       ├─has_phenotype▶ Phenotype (HPO) ─is_a▶ Phenotype
                       └─asserts_inheritance▶ Inheritance

and, derived from those, the entry-level relations the writer and the structured
parts of the entry are built from:

    Entry ─caused_by▶ Gene        Entry ─has_phenotype▶ Phenotype
    Entry ─inheritance▶ Mode      Entry ─has_variant▶ Variant

The graph does three jobs that a bag of text chunks cannot:

* entity resolution across papers: gene aliases collapse to the approved symbol,
  the same variant named three ways becomes one node, phenotype phrases become
  HPO terms;
* aggregation with provenance: how many independent papers support each gene,
  mode of inheritance and clinical feature, and which ones;
* retrieval for writing: the writer is handed the findings for a section together
  with their neighbourhood (which variant, which gene, which other papers report
  the same variant), instead of the nearest text chunks.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Callable, Iterable

from .models import (
    INHERITANCE_HPO,
    SECTION_ORDER,
    Finding,
    Paper,
    PaperExtraction,
    Seed,
    VariantMention,
)

# Only papers that are actually about the entry's subject may shape the derived,
# entry-level relations. Background papers still contribute findings for context.
CORE_RELEVANCE = ("primary", "supporting")

# --------------------------------------------------------------------------- #
# Variant canonicalisation
# --------------------------------------------------------------------------- #

_AA3 = {
    "ala": "A", "arg": "R", "asn": "N", "asp": "D", "cys": "C", "gln": "Q", "glu": "E",
    "gly": "G", "his": "H", "ile": "I", "leu": "L", "lys": "K", "met": "M", "phe": "F",
    "pro": "P", "ser": "S", "thr": "T", "trp": "W", "tyr": "Y", "val": "V", "sec": "U",
    "ter": "*", "stop": "*",
}
_AA1_TO_3 = {v: k.upper() for k, v in _AA3.items() if k not in ("stop",)}
_AA3_RE = re.compile("|".join(_AA3), re.I)
_PROT = re.compile(r"^([A-Z*])(\d+)(fs|del|dup|ins|ext|[A-Z*=])?", re.I)
_NUC_HGVS = re.compile(r"^([-*]?\d+(?:[+-]\d+)?)([ACGT])\s*(?:>|-|→|->)\s*([ACGT])$", re.I)
_NUC_LEGACY = re.compile(r"^([ACGT])(\d+)([ACGT])$", re.I)


def protein_key(text: str) -> str:
    """'p.Gly131Ser', 'G131S', 'gly131-to-ser', 'GLY131SER' -> 'p.G131S'."""
    s = re.sub(r"^\s*p\.", "", (text or "").strip(), flags=re.I)
    s = re.sub(r"[()\s\[\]]", "", s)
    s = re.sub(r"-?to-?", "", s, flags=re.I) if re.search(r"\d-?to-?[a-z]", s, re.I) else s
    s = _AA3_RE.sub(lambda m: _AA3[m.group(0).lower()], s)
    s = re.sub(r"X$", "*", s)
    m = _PROT.match(s)
    if not m:
        return ""
    ref, pos, alt = m.group(1).upper(), m.group(2), (m.group(3) or "")
    alt = alt.lower() if len(alt) > 1 else alt.upper()
    return f"p.{ref}{pos}{alt}"


def nucleotide_key(text: str, mito: bool = False) -> str:
    """'c.3697G>A', '3697G-A', 'G3697A' -> 'c.3697G>A' (or 'm.…' for mtDNA)."""
    s = re.sub(r"\s", "", text or "")
    prefix = "m" if mito else "c"
    m = re.match(r"^(?:NM_[\d.]+:|NC_[\d.]+:)?([cgmn])\.(.*)$", s, re.I)
    if m:
        prefix, s = m.group(1).lower(), m.group(2)
    if mito and prefix == "c":
        prefix = "m"  # papers and models alike write "c." for mtDNA positions; there is no CDS numbering
    if not s:
        return ""
    m = _NUC_HGVS.match(s)
    if m:
        return f"{prefix}.{m.group(1)}{m.group(2).upper()}>{m.group(3).upper()}"
    m = _NUC_LEGACY.match(s)
    if m:
        return f"{prefix}.{m.group(2)}{m.group(1).upper()}>{m.group(3).upper()}"
    if re.search(r"\d", s) and re.search(r"del|dup|ins|inv|_", s, re.I):
        return f"{prefix}.{s.lower()}"
    return ""


_MITO_GENE = re.compile(r"^MT-|^MT(ND[1-6]L?|CO[1-3]|ATP[68]|CYB|RNR[12]|T[A-Z][12]?)$", re.I)


def is_mito_gene(symbol: str) -> bool:
    """True for mtDNA genes in current ('MT-ND1') or legacy ('MTND1') nomenclature."""
    return bool(_MITO_GENE.search(symbol or ""))


def variant_keys(v: VariantMention) -> set[str]:
    """Every canonical name we can derive for a variant mention."""
    mito = is_mito_gene(v.gene)
    keys = {protein_key(v.protein), nucleotide_key(v.cdna, mito), nucleotide_key(v.genomic, mito)}
    # The free-text name is tried as both kinds; at most one will parse.
    for token in re.split(r"[\s,;()/]+", v.as_reported or ""):
        if len(token) >= 4:
            keys.add(nucleotide_key(token, mito) or protein_key(token) if re.search(r"\d", token) else "")
    keys.discard("")
    return keys


def omim_variant_name(gene: str, keys: Iterable[str]) -> str:
    """OMIM's allelic-variant naming: 'SMAD3, ARG287TRP' or 'MTND1, 3697G-A'."""
    keys = sorted(keys)
    gene_label = gene.replace("-", "") if is_mito_gene(gene) else gene
    for key in keys:
        m = re.match(r"^p\.([A-Z*])(\d+)([A-Z*])$", key)
        if m:
            return f"{gene_label}, {_AA1_TO_3.get(m.group(1), m.group(1))}{m.group(2)}{_AA1_TO_3.get(m.group(3), m.group(3))}"
    for key in keys:
        m = re.match(r"^[cgmn]\.(.+?)([ACGT])>([ACGT])$", key)
        if m:
            return f"{gene_label}, {m.group(1)}{m.group(2)}-{m.group(3)}"
    return f"{gene_label}, {keys[0].split('.', 1)[-1].upper()}" if keys else gene_label


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}

    def find(self, x: Any) -> Any:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: Any, b: Any) -> None:
        self.parent[self.find(a)] = self.find(b)


# --------------------------------------------------------------------------- #
# The graph
# --------------------------------------------------------------------------- #


class KnowledgeGraph:
    def __init__(self, seed: Seed):
        self.seed = seed
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.findings: dict[str, Finding] = {}
        self.papers: dict[str, Paper] = {}
        self.relevance: dict[str, str] = {}
        self._out: dict[str, list[int]] = defaultdict(list)
        self._in: dict[str, list[int]] = defaultdict(list)

    # -- construction ------------------------------------------------------- #

    def add_node(self, node_id: str, type_: str, label: str, **props: Any) -> str:
        node = self.nodes.setdefault(node_id, {"id": node_id, "type": type_, "label": label})
        node.update({k: v for k, v in props.items() if v not in (None, "", [])})
        return node_id

    def add_edge(self, src: str, rel: str, dst: str, **props: Any) -> None:
        edge = {"src": src, "rel": rel, "dst": dst, **{k: v for k, v in props.items() if v not in (None, "")}}
        self._out[src].append(len(self.edges))
        self._in[dst].append(len(self.edges))
        self.edges.append(edge)

    def out(self, node_id: str, rel: str | None = None) -> list[dict[str, Any]]:
        return [e for i in self._out.get(node_id, ()) if (e := self.edges[i]) and (rel is None or e["rel"] == rel)]

    def into(self, node_id: str, rel: str | None = None) -> list[dict[str, Any]]:
        return [e for i in self._in.get(node_id, ()) if (e := self.edges[i]) and (rel is None or e["rel"] == rel)]

    # -- queries ------------------------------------------------------------ #

    def is_core(self, pmid: str) -> bool:
        return self.relevance.get(pmid) in CORE_RELEVANCE

    def _order(self, finding: Finding) -> tuple[int, str, int]:
        paper = self.papers.get(finding.pmid)
        return (paper.year or 9999 if paper else 9999, finding.pmid, int(finding.id.rsplit(":", 1)[-1]))

    def findings_in(self, section: str) -> list[Finding]:
        """Findings filed under one section, oldest paper first."""
        return sorted((f for f in self.findings.values() if f.section == section), key=self._order)

    def variant_nodes(self) -> list[dict[str, Any]]:
        return sorted((n for n in self.nodes.values() if n["type"] == "Variant"), key=lambda n: n["id"])

    def findings_for(self, node_id: str) -> list[Finding]:
        """Findings directly attached to an entity node (gene, variant, phenotype, mode)."""
        ids = {e["src"] for e in self.into(node_id) if e["src"].startswith("finding:")}
        return sorted((self.findings[i[len("finding:"):]] for i in ids), key=self._order)

    def gene_support(self) -> dict[str, dict[str, Any]]:
        """For each gene: which core papers report patient variants in it."""
        support: dict[str, dict[str, Any]] = {}
        for node in self.variant_nodes():
            gene = node.get("gene", "")
            if not gene:
                continue
            pmids = {f.pmid for f in self.findings_for(node["id"])
                     if self.is_core(f.pmid) and f.section in ("molecular_genetics", "genotype_phenotype_correlations", "clinical_features")}
            if pmids:
                entry = support.setdefault(gene, {"pmids": set(), "variants": []})
                entry["pmids"] |= pmids
                entry["variants"].append(node["id"])
        return {g: {"pmids": sorted(s["pmids"]), "variants": s["variants"]} for g, s in support.items()}

    def inheritance_support(self) -> dict[str, list[str]]:
        support: dict[str, set[str]] = defaultdict(set)
        for f in self.findings.values():
            if f.inheritance in INHERITANCE_HPO and self.is_core(f.pmid):
                support[f.inheritance].add(f.pmid)
        return {code: sorted(pmids) for code, pmids in sorted(support.items(), key=lambda kv: -len(kv[1]))}

    def phenotype_profile(self) -> dict[str, dict[str, Any]]:
        """HPO term -> the core papers reporting it present or absent."""
        profile: dict[str, dict[str, Any]] = {}
        for f in self.findings.values():
            if not self.is_core(f.pmid):
                continue
            for m in f.phenotypes:
                if not m.hpo_id:
                    continue
                row = profile.setdefault(m.hpo_id, {
                    "label": m.hpo_label, "present": set(), "absent": set(), "texts": Counter(), "frequencies": [],
                })
                (row["present"] if m.present else row["absent"]).add(f.pmid)
                row["texts"][m.text] += 1
                if m.frequency:
                    row["frequencies"].append(f"{m.frequency} ({f.pmid})")
        return {
            hpo_id: {
                "label": row["label"], "present": sorted(row["present"]), "absent": sorted(row["absent"]),
                "text": row["texts"].most_common(1)[0][0], "frequencies": row["frequencies"],
            }
            for hpo_id, row in profile.items()
        }

    def stats(self) -> dict[str, Any]:
        return {
            "nodes": dict(Counter(n["type"] for n in self.nodes.values())),
            "edges": dict(Counter(e["rel"] for e in self.edges)),
        }

    # -- export ------------------------------------------------------------- #

    def to_json(self) -> dict[str, Any]:
        return {"seed": self.seed.model_dump(), "nodes": list(self.nodes.values()), "edges": self.edges,
                "stats": self.stats()}

    def triples(self) -> list[tuple[str, str, str, str]]:
        """(subject, predicate, object, provenance) with readable labels."""
        rows = []
        for e in self.edges:
            src, dst = self.nodes[e["src"]], self.nodes[e["dst"]]
            if src["type"] == "Finding":
                continue  # reified below through the entry-level and entity-level edges
            rows.append((src["label"], e["rel"], dst["label"], ",".join(e.get("pmids", [])) or e.get("pmid", "")))
        return rows


# --------------------------------------------------------------------------- #
# Building it
# --------------------------------------------------------------------------- #


def build_graph(
    seed: Seed,
    papers: list[Paper],
    extractions: list[PaperExtraction],
    normalize_gene: Callable[[str], str] | None = None,
) -> KnowledgeGraph:
    if normalize_gene is None:
        from .sources.hgnc import normalize_symbol as normalize_gene  # network-backed, cached

    kg = KnowledgeGraph(seed)
    kg.papers = {p.pmid: p for p in papers}
    entry = kg.add_node("entry", "Entry", seed.title, mim=seed.mim, entry_type=seed.entry_type)
    for section in SECTION_ORDER:
        kg.add_node(f"section:{section}", "Section", section)

    symbol_cache: dict[str, str] = {}

    def gene(symbol: str) -> str:
        key = symbol.strip()
        if key not in symbol_cache:
            symbol_cache[key] = normalize_gene(key) or key.upper()
        return symbol_cache[key]

    # Pass 1: papers and findings; normalise gene symbols in place.
    for ex in extractions:
        paper = kg.papers.get(ex.pmid)
        if paper is None:
            continue
        kg.relevance[ex.pmid] = ex.relevance
        kg.add_node(f"paper:{ex.pmid}", "Paper", paper.label, pmid=ex.pmid, year=paper.year,
                    content_level=ex.content_level, relevance=ex.relevance, title=paper.title)
        for f in ex.findings:
            f.genes = list(dict.fromkeys(gene(g) for g in f.genes))
            for v in f.variants:
                v.gene = gene(v.gene) if v.gene else (f.genes[0] if len(f.genes) == 1 else "")
            kg.findings[f.id] = f

    # Pass 2: merge variant mentions that name the same change in the same gene.
    uf = _UnionFind()
    mention_keys: dict[tuple[str, int], set[tuple[str, str]]] = {}
    for f in kg.findings.values():
        for i, v in enumerate(f.variants):
            keys = {(v.gene, k) for k in variant_keys(v)} or {(v.gene, "raw:" + v.as_reported.strip().lower())}
            mention_keys[(f.id, i)] = keys
            first = next(iter(keys))
            for key in keys:
                uf.union(first, key)
    clusters: dict[Any, set[tuple[str, str]]] = defaultdict(set)
    for keys in mention_keys.values():
        for key in keys:
            clusters[uf.find(key)].add(key)

    def variant_node(f: Finding, i: int) -> str:
        root = uf.find(next(iter(mention_keys[(f.id, i)])))
        keys = sorted(k for _, k in clusters[root])
        gene_symbol = root[0]
        preferred = next((k for k in keys if k[:2] in ("c.", "m.", "g.")), keys[0])
        node_id = f"variant:{gene_symbol}:{preferred}"
        named = [k for k in keys if not k.startswith("raw:")]
        kg.add_node(node_id, "Variant", f"{gene_symbol} {' / '.join(named) or f.variants[i].as_reported}",
                    gene=gene_symbol, keys=keys, omim_name=omim_variant_name(gene_symbol, named))
        return node_id

    # Pass 3: edges from findings.
    for f in sorted(kg.findings.values(), key=kg._order):
        fid = kg.add_node(f"finding:{f.id}", "Finding", f.statement, pmid=f.pmid, section=f.section)
        kg.add_edge(f"paper:{f.pmid}", "reports", fid)
        kg.add_edge(fid, "in_section", f"section:{f.section}")
        for g in f.genes:
            kg.add_edge(fid, "mentions_gene", kg.add_node(f"gene:{g}", "Gene", g), pmid=f.pmid)
        for i, v in enumerate(f.variants):
            vid = variant_node(f, i)
            v.key = vid
            kg.add_edge(fid, "reports_variant", vid, pmid=f.pmid, zygosity=v.zygosity, origin=v.origin,
                        as_reported=v.as_reported)
            if v.gene:
                gid = kg.add_node(f"gene:{v.gene}", "Gene", v.gene)
                if not any(e["dst"] == gid for e in kg.out(vid, "in_gene")):
                    kg.add_edge(vid, "in_gene", gid)
        for m in f.phenotypes:
            if m.hpo_id:
                pid = kg.add_node(f"hpo:{m.hpo_id}", "Phenotype", m.hpo_label, hpo_id=m.hpo_id)
            else:
                pid = kg.add_node(f"phenotext:{m.text.lower()}", "PhenotypeText", m.text)
            kg.add_edge(fid, "has_phenotype", pid, pmid=f.pmid, present=m.present, frequency=m.frequency,
                        text=m.text)
        if f.inheritance in INHERITANCE_HPO:
            hpo_id, label = INHERITANCE_HPO[f.inheritance]
            kg.add_edge(fid, "asserts_inheritance",
                        kg.add_node(f"inh:{f.inheritance}", "Inheritance", label, hpo_id=hpo_id), pmid=f.pmid)

    # Pass 4: entry-level relations, each listing the papers that support it.
    for symbol, support in kg.gene_support().items():
        kg.add_edge(entry, "caused_by", f"gene:{symbol}", pmids=support["pmids"], n_variants=len(support["variants"]))
        for vid in support["variants"]:
            kg.add_edge(entry, "has_variant", vid, pmids=sorted({f.pmid for f in kg.findings_for(vid)}))
    for code, pmids in kg.inheritance_support().items():
        kg.add_edge(entry, "inheritance", f"inh:{code}", pmids=pmids)
    for hpo_id, row in kg.phenotype_profile().items():
        if row["present"]:
            kg.add_edge(entry, "has_phenotype", f"hpo:{hpo_id}", pmids=row["present"],
                        absent_in=row["absent"])
    _link_phenotype_hierarchy(kg)
    return kg


def _link_phenotype_hierarchy(kg: KnowledgeGraph) -> None:
    """Connect each HPO node to its nearest ancestor that is also in the graph."""
    try:
        from .sources.hpo import get_hpo
        hpo = get_hpo()
    except Exception:  # noqa: BLE001 - the hierarchy is an enrichment; the graph is valid without it
        return
    present = {n["hpo_id"] for n in kg.nodes.values() if n["type"] == "Phenotype"}
    for term in present:
        frontier, seen = list(hpo.parents(term)), set()
        while frontier:
            parent = frontier.pop(0)
            if parent in seen:
                continue
            seen.add(parent)
            if parent in present:
                kg.add_edge(f"hpo:{term}", "is_a", f"hpo:{parent}")
            else:
                frontier.extend(hpo.parents(parent))
