"""Human Phenotype Ontology: term lookup, text matching, OMIM annotations, IC.

On first use `hp.obo` and `phenotype.hpoa` are downloaded into
`settings.ontology_dir` (refreshed after 30 days) and a compact pickled index is
built next to them, so later loads take a fraction of a second.
"""

from __future__ import annotations

import logging
import math
import os
import pickle
import re
import tempfile
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings
from ..models import GoldPhenotypeAnnotation

log = logging.getLogger(__name__)

HP_OBO_URL = "https://purl.obolibrary.org/obo/hp.obo"
HPOA_URL = "https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa"
REFRESH_S = 30 * 86400
INDEX_VERSION = 3

ROOT = "HP:0000001"
PHENOTYPE_ROOT = "HP:0000118"
INHERITANCE_ROOT = "HP:0000005"

# Top-level organ-system branches (children of HP:0000118) -> OMIM clinical
# synopsis headings. HP:0003011 (musculature) is a sub-branch promoted so that
# muscle findings do not all land under "Skeletal".
CATEGORY_MAP: dict[str, str] = {
    "HP:0000478": "Head & Neck: Eyes",
    "HP:0000598": "Head & Neck: Ears",
    "HP:0001608": "Voice",
    "HP:0000769": "Chest: Breasts",
    "HP:0001626": "Cardiovascular",
    "HP:0002086": "Respiratory",
    "HP:0025031": "Abdomen",
    "HP:0000119": "Genitourinary",
    "HP:0001574": "Skin, Nails, & Hair",
    "HP:0003011": "Muscle, Soft Tissues",
    "HP:0040064": "Skeletal: Limbs",
    "HP:0000707": "Neurologic",
    "HP:0033127": "Skeletal",
    "HP:0000152": "Head & Neck",
    "HP:0000818": "Endocrine Features",
    "HP:0001871": "Hematology",
    "HP:0002715": "Immunology",
    "HP:0002664": "Neoplasia",
    "HP:0001939": "Metabolic Features",
    "HP:0001197": "Prenatal Manifestations",
    "HP:0001507": "Growth",
    "HP:0045027": "Chest",
    "HP:0025354": "Laboratory Abnormalities",
    "HP:0025142": "Miscellaneous",
}
# Fixed priority when a term sits under several branches: the dict order above
# (most specific organ first).
CATEGORY_PRIORITY: list[str] = list(CATEGORY_MAP)

_STOP = {"of", "the", "and", "in", "to", "a", "an", "with", "or", "by", "on", "for", "at", "from"}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _fold(tok: str) -> str:
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
        return tok[:-1]
    return tok


def tokens(text: str) -> list[str]:
    return [_fold(t) for t in _NON_ALNUM.sub(" ", (text or "").lower()).split()]


def normalize(text: str) -> str:
    return " ".join(tokens(text))


@dataclass(frozen=True)
class HpoHit:
    id: str
    label: str
    score: float
    matched_text: str


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

_SYN = re.compile(r'^"((?:[^"\\]|\\.)*)"\s+(EXACT|BROAD|NARROW|RELATED)')
_DEF = re.compile(r'^"((?:[^"\\]|\\.)*)"')


def parse_obo(path: Path) -> dict[str, dict]:
    terms: dict[str, dict] = {}
    cur: dict | None = None
    in_term = False
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("["):
                if cur is not None and in_term and cur.get("id"):
                    terms[cur["id"]] = cur
                in_term = line.strip() == "[Term]"
                cur = {"id": "", "name": "", "def": "", "syn": [], "is_a": [], "alt": [],
                       "obsolete": False, "replaced_by": "", "consider": []} if in_term else None
                continue
            if not in_term or cur is None or ":" not in line:
                continue
            key, _, val = line.partition(": ")
            val = val.strip()
            if key == "id":
                cur["id"] = val
            elif key == "name":
                cur["name"] = val
            elif key == "def":
                m = _DEF.match(val)
                cur["def"] = m.group(1).replace('\\"', '"') if m else val
            elif key == "synonym":
                m = _SYN.match(val)
                if m:
                    cur["syn"].append((m.group(1).replace('\\"', '"'), m.group(2)))
            elif key == "is_a":
                cur["is_a"].append(val.split()[0])
            elif key == "alt_id":
                cur["alt"].append(val.split()[0])
            elif key == "is_obsolete":
                cur["obsolete"] = val.lower() == "true"
            elif key == "replaced_by":
                cur["replaced_by"] = val.split()[0]
            elif key == "consider":
                cur["consider"].append(val.split()[0])
    if cur is not None and in_term and cur.get("id"):
        terms[cur["id"]] = cur
    return terms


def parse_hpoa(path: Path) -> dict[str, list[tuple]]:
    """OMIM rows of phenotype.hpoa: mim -> [(hpo_id, aspect, qualifier, frequency, onset, evidence, reference)]."""
    out: dict[str, list[tuple]] = defaultdict(list)
    cols: list[str] | None = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                if line.startswith("#DatabaseID") or line.startswith("#database_id"):
                    cols = line[1:].rstrip("\n").split("\t")
                continue
            parts = line.rstrip("\n").split("\t")
            if cols is None:
                if parts[0].lower() in ("database_id", "databaseid"):
                    cols = parts
                    continue
                cols = ["database_id", "disease_name", "qualifier", "hpo_id", "reference", "evidence",
                        "onset", "frequency", "sex", "modifier", "aspect", "biocuration"]
            row = dict(zip([c.lower() for c in cols], parts))
            db = row.get("database_id") or row.get("databaseid") or ""
            if not db.startswith("OMIM:"):
                continue
            out[db[5:]].append((
                row.get("hpo_id", ""), row.get("aspect", ""), row.get("qualifier", ""),
                row.get("frequency", ""), row.get("onset", ""), row.get("evidence", ""),
                row.get("reference", ""),
            ))
    return dict(out)


# --------------------------------------------------------------------------- #
# Index
# --------------------------------------------------------------------------- #


def build_index(obo: Path, hpoa: Path | None) -> dict:
    terms = parse_obo(obo)
    ids = sorted(terms)
    idx = {t: i for i, t in enumerate(ids)}
    parents = [tuple(idx[p] for p in terms[t]["is_a"] if p in idx) for t in ids]
    alt = {}
    for t in ids:
        for a in terms[t]["alt"]:
            alt[a] = t
    obsolete = [terms[t]["obsolete"] for t in ids]

    # Ancestor sets (as index sets) for IC and branch tests.
    anc_cache: dict[int, frozenset] = {}

    def anc(i: int) -> frozenset:
        got = anc_cache.get(i)
        if got is not None:
            return got
        stack, seen = [i], {i}
        while stack:
            for p in parents[stack.pop()]:
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        got = frozenset(seen)
        anc_cache[i] = got
        return got

    pheno_root = idx.get(PHENOTYPE_ROOT)

    exact: dict[str, str] = {}
    for t in ids:  # labels win over synonyms
        if not terms[t]["obsolete"] and terms[t]["name"]:
            exact.setdefault(normalize(terms[t]["name"]), t)
    for t in ids:
        if terms[t]["obsolete"]:
            continue
        for text, scope in terms[t]["syn"]:
            if scope == "EXACT":
                exact.setdefault(normalize(text), t)

    # Search names: phenotypic-abnormality branch only.
    names: list[tuple[int, str, frozenset]] = []
    for t in ids:
        i = idx[t]
        if terms[t]["obsolete"] or pheno_root is None or pheno_root not in anc(i) or i == pheno_root:
            continue
        seen_norm = set()
        for text in [terms[t]["name"]] + [s for s, _ in terms[t]["syn"]]:
            toks = frozenset(x for x in tokens(text) if x not in _STOP)
            key = " ".join(sorted(toks))
            if not toks or key in seen_norm:
                continue
            seen_norm.add(key)
            names.append((i, text, toks))
    df: dict[str, int] = defaultdict(int)
    for _, _, toks in names:
        for tok in toks:
            df[tok] += 1
    n_names = max(1, len(names))
    idf = {tok: math.log((n_names + 1) / (c + 0.5)) for tok, c in df.items()}
    postings: dict[str, list[int]] = defaultdict(list)
    name_weight: list[float] = []
    for j, (_, _, toks) in enumerate(names):
        for tok in toks:
            postings[tok].append(j)
        name_weight.append(sum(idf[t] for t in toks))

    annotations = parse_hpoa(hpoa) if hpoa and Path(hpoa).exists() else {}

    def resolve(t: str) -> str | None:
        for _ in range(5):
            if t in alt:
                t = alt[t]
            if t not in idx:
                return None
            if not terms[t]["obsolete"]:
                return t
            if not terms[t]["replaced_by"]:
                return None
            t = terms[t]["replaced_by"]
        return None

    counts: dict[int, int] = defaultdict(int)
    n_dis = 0
    for mim, rows in annotations.items():
        dis_terms = set()
        for hpo_id, aspect, qualifier, *_ in rows:
            if aspect != "P" or qualifier == "NOT":
                continue
            r = resolve(hpo_id)
            if r:
                dis_terms.add(idx[r])
        if not dis_terms:
            continue
        n_dis += 1
        closure = set()
        for i in dis_terms:
            closure |= anc(i)
        for i in closure:
            counts[i] += 1

    return {
        "version": INDEX_VERSION,
        "ids": ids,
        "labels": [terms[t]["name"] for t in ids],
        "defs": [terms[t]["def"] for t in ids],
        "syns": [[s for s, _ in terms[t]["syn"]] for t in ids],
        "parents": parents,
        "obsolete": obsolete,
        "replaced_by": {t: terms[t]["replaced_by"] for t in ids if terms[t]["replaced_by"]},
        "alt": alt,
        "exact": exact,
        "names": [(i, text) for i, text, _ in names],
        "name_tokens": [tuple(toks) for _, _, toks in names],
        "name_weight": name_weight,
        "postings": dict(postings),
        "idf": idf,
        "max_idf": math.log((n_names + 1) / 0.5),
        "ic_counts": dict(counts),
        "n_diseases": n_dis,
        "annotations": annotations,
    }


class HPO:
    def __init__(self, obo_path: Path | None = None, hpoa_path: Path | None = None,
                 index_path: Path | None = None, download: bool | None = None):
        settings = get_settings()
        d = settings.ontology_dir
        self.obo_path = Path(obo_path) if obo_path else d / "hp.obo"
        self.hpoa_path = Path(hpoa_path) if hpoa_path else (d / "phenotype.hpoa" if not obo_path else None)
        self.index_path = Path(index_path) if index_path else self.obo_path.with_suffix(".index.pkl")
        if download is None:
            download = obo_path is None
        if download:
            from ..http import get_http
            http = get_http()
            old = self.obo_path.stat().st_mtime if self.obo_path.exists() else None
            http.download(HP_OBO_URL, self.obo_path, max_age_s=REFRESH_S)
            if self.hpoa_path is not None:
                http.download(HPOA_URL, self.hpoa_path, max_age_s=REFRESH_S)
            if old is not None and self.obo_path.stat().st_mtime != old:
                log.info("HPO refreshed; rebuilding index")
        self._load()
        self._anc_cache: dict[str, frozenset[str]] = {}
        self._desc_cache: dict[str, frozenset[str]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- loading
    def _index_fresh(self) -> bool:
        if not self.index_path.exists():
            return False
        mt = self.index_path.stat().st_mtime
        srcs = [self.obo_path] + ([self.hpoa_path] if self.hpoa_path else [])
        return all(not s.exists() or s.stat().st_mtime <= mt for s in srcs)

    def _load(self) -> None:
        data = None
        if self._index_fresh():
            try:
                with open(self.index_path, "rb") as fh:
                    data = pickle.load(fh)
                if data.get("version") != INDEX_VERSION:
                    data = None
            except Exception:
                data = None
        if data is None:
            data = build_index(self.obo_path, self.hpoa_path)
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.index_path.parent, suffix=".tmp")
            with os.fdopen(fd, "wb") as fh:
                pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, self.index_path)
        self._d = data
        self._ids: list[str] = data["ids"]
        self._idx = {t: i for i, t in enumerate(self._ids)}
        children: list[list[int]] = [[] for _ in self._ids]
        for i, ps in enumerate(data["parents"]):
            for p in ps:
                children[p].append(i)
        self._children = children

    # ------------------------------------------------------------- basics
    def _i(self, id_: str) -> int | None:
        return self._idx.get(id_)

    def exists(self, id_: str) -> bool:
        return id_ in self._idx or id_ in self._d["alt"]

    def resolve(self, id_: str) -> str | None:
        t = (id_ or "").strip()
        for _ in range(6):
            t = self._d["alt"].get(t, t)
            i = self._i(t)
            if i is None:
                return None
            if not self._d["obsolete"][i]:
                return t
            nxt = self._d["replaced_by"].get(t)
            if not nxt:
                return None
            t = nxt
        return None

    def _rid(self, id_: str) -> int | None:
        r = self.resolve(id_)
        if r is None:
            i = self._i(self._d["alt"].get(id_, id_))
            return i
        return self._i(r)

    def label(self, id_: str) -> str:
        i = self._rid(id_)
        return self._d["labels"][i] if i is not None else ""

    def definition(self, id_: str) -> str:
        i = self._rid(id_)
        return self._d["defs"][i] if i is not None else ""

    def synonyms(self, id_: str) -> list[str]:
        i = self._rid(id_)
        return list(self._d["syns"][i]) if i is not None else []

    def parents(self, id_: str) -> list[str]:
        i = self._rid(id_)
        return [self._ids[p] for p in self._d["parents"][i]] if i is not None else []

    def children(self, id_: str) -> list[str]:
        i = self._rid(id_)
        return [self._ids[c] for c in self._children[i]] if i is not None else []

    def ancestors(self, id_: str, include_self: bool = True) -> frozenset[str]:
        i = self._rid(id_)
        if i is None:
            return frozenset()
        key = self._ids[i]
        got = self._anc_cache.get(key)
        if got is None:
            stack, seen = [i], {i}
            parents = self._d["parents"]
            while stack:
                for p in parents[stack.pop()]:
                    if p not in seen:
                        seen.add(p)
                        stack.append(p)
            got = frozenset(self._ids[s] for s in seen)
            self._anc_cache[key] = got
        return got if include_self else got - {key}

    def descendants(self, id_: str, include_self: bool = False) -> frozenset[str]:
        i = self._rid(id_)
        if i is None:
            return frozenset()
        key = self._ids[i]
        got = self._desc_cache.get(key)
        if got is None:
            stack, seen = [i], {i}
            while stack:
                for c in self._children[stack.pop()]:
                    if c not in seen:
                        seen.add(c)
                        stack.append(c)
            got = frozenset(self._ids[s] for s in seen)
            self._desc_cache[key] = got
        return got if include_self else got - {key}

    def is_phenotype(self, id_: str) -> bool:
        return PHENOTYPE_ROOT in self.ancestors(id_, include_self=False)

    def is_inheritance(self, id_: str) -> bool:
        return INHERITANCE_ROOT in self.ancestors(id_, include_self=False)

    # ------------------------------------------------------------- text
    def exact(self, text: str) -> str | None:
        return self._d["exact"].get(normalize(text))

    def search(self, text: str, k: int = 10) -> list[HpoHit]:
        hits: list[HpoHit] = []
        seen: set[str] = set()
        ex = self.exact(text)
        if ex:
            hits.append(HpoHit(ex, self.label(ex), 1.0, text))
            seen.add(ex)
        q = {t for t in tokens(text) if t not in _STOP}
        if not q:
            return hits[:k]
        idf, postings = self._d["idf"], self._d["postings"]
        max_idf = self._d["max_idf"]
        q_weight = sum(idf.get(t, max_idf) for t in q)
        acc: dict[int, float] = defaultdict(float)
        for t in q:
            w = idf.get(t)
            if w is None:
                continue
            for j in postings.get(t, ()):
                acc[j] += w
        if not acc:
            return hits[:k]
        weights = self._d["name_weight"]
        names = self._d["names"]
        best: dict[int, tuple[float, str]] = {}
        for j, ov in acc.items():
            score = 2.0 * ov / (q_weight + weights[j])
            term_i, name_text = names[j]
            cur = best.get(term_i)
            if cur is None or score > cur[0]:
                best[term_i] = (score, name_text)
        ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], self._ids[kv[0]]))
        for term_i, (score, name_text) in ranked:
            tid = self._ids[term_i]
            if tid in seen:
                continue
            hits.append(HpoHit(tid, self._d["labels"][term_i], round(min(score, 0.99), 4), name_text))
            seen.add(tid)
            if len(hits) >= k:
                break
        return hits[:k]

    # ------------------------------------------------------------- categories
    def category(self, id_: str) -> str:
        anc = self.ancestors(id_)
        for top in CATEGORY_PRIORITY:
            if top in anc:
                return CATEGORY_MAP[top]
        return "Miscellaneous"

    # ------------------------------------------------------------- annotations
    def annotated_mims(self) -> set[str]:
        return set(self._d["annotations"])

    def annotations(self, mim: str) -> list[GoldPhenotypeAnnotation]:
        out = []
        for hpo_id, aspect, qualifier, freq, onset, evidence, ref in self._d["annotations"].get(str(mim), []):
            rid = self.resolve(hpo_id) or hpo_id
            out.append(GoldPhenotypeAnnotation(
                hpo_id=rid, label=self.label(rid), aspect=aspect or "P", qualifier=qualifier,
                frequency=freq, onset=onset, evidence=evidence, reference=ref,
            ))
        return out

    def information_content(self, id_: str) -> float:
        n = self._d["n_diseases"]
        if n <= 0:
            return 0.0
        i = self._rid(id_)
        c = self._d["ic_counts"].get(i, 0) if i is not None else 0
        return max(0.0, -math.log(max(c, 1) / n))


_HPO: HPO | None = None
_HPO_LOCK = threading.Lock()


def get_hpo() -> HPO:
    global _HPO
    with _HPO_LOCK:
        if _HPO is None:
            _HPO = HPO()
        return _HPO
