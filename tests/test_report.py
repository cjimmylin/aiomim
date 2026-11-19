"""Offline tests for the curator review page (aiomim.report)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from aiomim.evaluate import eval_faithfulness, eval_genes, eval_inheritance, eval_references, eval_variants, prf
from aiomim.models import (
    AllelicVariantEntry,
    ClaimCheck,
    EntryParagraph,
    EntrySection,
    Finding,
    GenePhenotypeRelationship,
    GeneratedEntry,
    GoldAllelicVariant,
    GoldEntry,
    GoldGene,
    GoldParagraph,
    Paper,
    PaperExtraction,
    Reference,
    Seed,
    SynopsisItem,
)
from aiomim.pipeline import _paper_record
from aiomim.report import build as report_build
from aiomim.report.build import build_report, json_for_script, strategy_info, unpack

BREAKOUT = "</script><script>window.pwned=1</script><!--"

PAPER = Paper(pmid="8016139", title="A mitochondrial DNA mutation at nucleotide pair 14459 of the ND6 gene",
              authors=["Jun AS", "Brown MD", "Wallace DC"], year=1994, journal="Proc Natl Acad Sci U S A",
              abstract="A five-generation Hispanic family with Leber optic neuropathy and dystonia was studied. " * 2)


def _entry(strategy: str) -> GeneratedEntry:
    entry = GeneratedEntry(
        mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", inheritance=["MT"],
        relationships=[GenePhenotypeRelationship(phenotype="Leber optic atrophy and dystonia", gene_symbol="MT-ND6",
                                                 inheritance=["MT"], pmids=["8016139"])],
        intro=EntryParagraph(text="LDYT is caused by mutation in MT-ND6.", pmids=["8016139"]),
        sections=[EntrySection(name="molecular_genetics", heading="Molecular Genetics", paragraphs=[
            EntryParagraph(text=f"Jun et al. (1994) found m.14459G>A. {BREAKOUT}", pmids=["8016139"],
                           finding_ids=["8016139:1"],
                           checks=[ClaimCheck(claim="m.14459G>A", pmid="8016139", verdict="supported",
                                              evidence_quote="nucleotide pair 14459"),
                                   ClaimCheck(claim="in 105 controls", pmid="8016139", verdict="unsupported")]),
        ])],
        clinical_synopsis=[SynopsisItem(category="Eyes", feature="optic atrophy", hpo_id="HP:0000648",
                                        hpo_label="Optic atrophy", pmids=["8016139"], n_papers=1)],
        allelic_variants=[AllelicVariantEntry(number=2, gene_symbol="MT-ND6", name="MTND6, ALA72VAL",
                                              hgvs=["m.14459G>A"], paragraphs=[EntryParagraph(text="Variant text.", pmids=["8016139"])])],
        references=[Reference(pmid="8016139", label=PAPER.label, citation=PAPER.reference, content_level="abstract")],
    )
    entry.assign_paragraph_ids()
    entry.meta = {"strategy": strategy, "generated": "2026-01-01", "dropped_ungrounded": [{"text": "x"}]}
    return entry


GOLD = GoldEntry(mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", cited_pmids=["8016139"],
                 genes=[GoldGene(symbol="MT-ND6")], inheritance=["MT"],
                 allelic_variants=[GoldAllelicVariant(omim_id="516006.0002", gene_symbol="MT-ND6", name="MTND6, ALA72VAL",
                                                      paragraphs=[GoldParagraph(text="Jun et al. (1994) ...", pmids=["8016139"], mims=["500001"])])])


def _eval(entry: GeneratedEntry) -> dict:
    return {
        "mim": "500001", "title": GOLD.title, "strategy": entry.meta["strategy"],
        "gold_reference_access": {"abstract": 1},
        "references": eval_references(entry, GOLD, ["8016139"]), "genes": eval_genes(entry, GOLD),
        "inheritance": eval_inheritance(entry, GOLD),
        "synopsis": {"exact": prf({"HP:0000648"}, {"HP:0000648", "HP:0001332"}),
                     "hierarchical": prf({"a"}, {"a", "b"}), "semantic": {"precision": None, "recall": None, "f1": None},
                     "missed": ["HP:0001332 Dystonia"], "extra": []},
        "variants": eval_variants(entry, GOLD),
        "gold_text": {"n_paragraphs": 0}, "faithfulness": eval_faithfulness(entry),
    }


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, default=str), encoding="utf-8")


def _embedded(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S)
    assert m, "data block missing"
    return json.loads(m.group(1))


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "demo"
    d = run / "500001"
    _write(d / "seed.json", Seed(mim="500001", prefix="#", title=GOLD.title).model_dump())
    _write(d / "gold.json", GOLD.model_dump())
    _write(d / "papers.json", [_paper_record(PAPER)])
    _write(d / "extractions.json", [PaperExtraction(pmid="8016139", findings=[
        Finding(id="8016139:1", pmid="8016139", section="molecular_genetics", statement="m.14459G>A",
                quotes=["nucleotide pair 14459"], quote_grounding=[1.0])]).model_dump()])
    _write(d / "kg.json", {"nodes": [{"id": "entry", "type": "Entry", "label": "x"},
                                     {"id": "gene:MT-ND6", "type": "Gene", "label": "MT-ND6"}],
                           "edges": [{"src": "entry", "rel": "caused_by", "dst": "gene:MT-ND6", "pmids": ["8016139"]}],
                           "stats": {"nodes": {"Gene": 1}, "edges": {"caused_by": 1}}})
    for strategy in ("kg", "direct"):
        entry = _entry(strategy)
        _write(d / f"entry.{strategy}.json", entry.model_dump())
        _write(d / f"eval.{strategy}.json", _eval(entry))
    return run


def _payload(data: dict, i: int = 0) -> dict:
    return data["payloads"][data["entries"][i]["file"]]


def test_report_builds_and_embeds_data(run_dir: Path):
    path = build_report(run_dir, None)
    assert path == run_dir / "report.html" and path.is_file()
    html = path.read_text(encoding="utf-8")
    data = _embedded(html)
    assert data["run"] == "demo" and data["split"] is False
    assert data["strategies"] == ["kg", "direct"]
    index = data["entries"][0]
    assert index["mim"] == "500001" and index["strategies"] == ["kg", "direct"]
    assert index["pids"]["kg"] == ["intro", "molecular_genetics.1", "av0002.1"]
    assert index["rows"]["kg"]["gene_f1"] == 1.0 and index["rows"]["kg"]["claims"] == 2
    item = _payload(data)
    assert set(item["entries"]) == {"kg", "direct"} and set(item["evals"]) == {"kg", "direct"}
    para = item["entries"]["kg"]["sections"][0]["paragraphs"][0]
    assert para["status"] == "flagged" and para["id"] == "molecular_genetics.1"
    assert item["entries"]["kg"]["intro"]["status"] == "unverified"
    assert item["kg"]["entities"][0]["label"] == "MT-ND6"
    assert all("draft" not in p for p in item["evals"]["kg"]["gold_text"].get("paragraphs", []))
    assert item["extractions"][0]["findings"][0]["quotes"] == ["nucleotide pair 14459"]
    assert "abstract" not in item["papers"][0]  # paper text is not embedded
    assert item["entries"]["kg"]["meta"]["dropped_ungrounded_count"] == 1


def test_report_is_self_contained(run_dir: Path):
    html = build_report(run_dir, str(run_dir / "out" / "page.html")).read_text(encoding="utf-8")
    low = html.lower()
    assert "<script src" not in low
    assert '<link rel="stylesheet"' not in low
    assert "@import" not in low
    assert "<title>" in low and "prefers-color-scheme: dark" in low


def test_script_breakout_is_escaped(run_dir: Path):
    html = build_report(run_dir, None).read_text(encoding="utf-8")
    # Exactly the two real script elements close; the data cannot add one.
    assert html.count("</script>") == 2
    assert "window.pwned" in html  # still present, but only as escaped JSON text
    text = _payload(_embedded(html))["entries"]["kg"]["sections"][0]["paragraphs"][0]["text"]
    assert BREAKOUT in text
    assert "<" not in json_for_script({"a": "</script>"})


def test_missing_optional_files_do_not_raise(tmp_path: Path):
    run = tmp_path / "sparse"
    # A new-entry draft: slug directory, no gold, no eval, single strategy.
    new = run / "my-new-disorder"
    entry = _entry("kg")
    entry.mim = None
    _write(new / "seed.json", Seed(title="MY NEW DISORDER").model_dump())
    _write(new / "entry.kg.json", entry.model_dump())
    # An entry folder with nothing but a seed, and one with a broken file.
    _write(run / "500002" / "seed.json", Seed(mim="500002", title="ONLY A SEED").model_dump())
    (run / "500003").mkdir(parents=True)
    (run / "500003" / "papers.json").write_text("{not json", encoding="utf-8")
    (run / "not-an-entry").mkdir()
    data = _embedded(build_report(run, None).read_text(encoding="utf-8"))
    dirs = [e["dir"] for e in data["entries"]]
    assert dirs == ["500002", "500003", "my-new-disorder"]
    assert data["entries"][-1]["strategies"] == ["kg"] and data["entries"][-1]["has_gold"] is False
    new_item = _payload(data, -1)
    assert "gold" not in new_item and new_item["evals"] == {}  # absent parts are left out of the payload
    assert new_item["entries"]["kg"]["audit"]["n_claims"] == 2
    assert data["entries"][-1]["rows"]["kg"]["claim_error_rate"] == 0.5
    assert _payload(data, 1)["papers"] == []
    assert data["comparison"] is None


def test_empty_run_and_missing_dir(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    assert _embedded(build_report(tmp_path / "empty", None).read_text(encoding="utf-8"))["entries"] == []
    with pytest.raises(FileNotFoundError):
        build_report(tmp_path / "nope", None)


def _registered(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    m = re.fullmatch(r"window\.__aiomimRegister\((\"[^\"]*\"),(.*)\);\n", text, re.S)
    assert m, text[:80]
    return json.loads(m.group(1)), json.loads(m.group(2))


def test_split_mode_writes_one_file_per_entry(run_dir: Path, tmp_path: Path):
    # a second entry with a slug name, and a stale data file from an earlier build
    entry = _entry("kg")
    entry.mim = None
    _write(run_dir / "my-new" / "entry.kg.json", entry.model_dump())
    stale = run_dir / "report_data" / "gone.js"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")

    html = build_report(run_dir, None, split=True).read_text(encoding="utf-8")
    data = _embedded(html)
    assert data["split"] is True and "payloads" not in data
    files = sorted(p.name for p in (run_dir / "report_data").glob("*.js"))
    assert files == ["500001.js", "my-new.js"] and not stale.exists()
    name, payload = _registered(run_dir / "report_data" / "500001.js")
    assert name == "500001" + ".js" and set(payload["entries"]) == {"kg", "direct"}
    # data files are script too: nothing in them may close a script element
    raw = (run_dir / "report_data" / "500001.js").read_text(encoding="utf-8")
    assert "</script" not in raw and BREAKOUT in json.dumps(payload)
    assert len(html) < 400_000  # the page itself holds only the index
    low = html.lower()
    assert "<script src" not in low and "'self'" in low  # data files load at run time, same directory only


def test_auto_split_by_size(run_dir: Path, monkeypatch):
    monkeypatch.setattr(report_build, "SPLIT_THRESHOLD", 10)
    data = _embedded(build_report(run_dir, None).read_text(encoding="utf-8"))
    assert data["split"] is True and (run_dir / "report_data" / "500001.js").is_file()
    monkeypatch.setattr(report_build, "SPLIT_THRESHOLD", 10**9)
    assert _embedded(build_report(run_dir, None).read_text(encoding="utf-8"))["split"] is False


def test_comparison_and_graph_data(run_dir: Path):
    comparison = {"run": "demo", "n_entries": 1, "overall": [{"metric": "gene_f1", "label": "Causal gene F1", "higher_is_better": True,
                  "n": 1, "kg": 1.0, "direct": 1.0, "difference": 0.0, "ci95": None, "kg_better": 0, "direct_better": 0,
                  "ties": 1, "sign_test_p": None}], "pooled": {}, "by_stratum": {}, "by_access": {}}
    _write(run_dir / "comparison.json", comparison)
    kg = json.loads((run_dir / "500001" / "kg.json").read_text())
    kg["nodes"].append({"id": "variant:MT-ND6:m.14459G>A", "type": "Variant", "label": "MT-ND6 m.14459G>A", "omim_name": "MTND6, ALA72VAL"})
    kg["edges"] += [{"src": "entry", "rel": "has_variant", "dst": "variant:MT-ND6:m.14459G>A", "pmids": ["8016139"]},
                    {"src": "variant:MT-ND6:m.14459G>A", "rel": "in_gene", "dst": "gene:MT-ND6"}]
    _write(run_dir / "500001" / "kg.json", kg)
    data = _embedded(build_report(run_dir, None).read_text(encoding="utf-8"))
    assert data["comparison"]["overall"][0]["metric"] == "gene_f1"
    variant = next(e for e in _payload(data)["kg"]["entities"] if e["rel"] == "has_variant")
    assert variant["gene_id"] == "gene:MT-ND6" and variant["omim_name"] == "MTND6, ALA72VAL"


# --------------------------------------------------------------------------- #
# Any number of strategies
# --------------------------------------------------------------------------- #

REFERENCE_TEXT = "Synthetic reference paragraph, written for this test and not taken from OMIM."


def _eval_with_gold(entry: GeneratedEntry) -> dict:
    ev = _eval(entry)
    facts = [{"fact": "a", "status": "present", "note": ""}, {"fact": "b", "status": "partial", "note": "x"}]
    ev["gold_text"] = {"n_paragraphs": 1, "n_facts": 2, "present": 1, "partial": 1, "absent": 0, "contradicted": 0,
                       "coverage": 0.75, "paragraphs": [{"pmids": ["8016139"], "content_level": "abstract",
                                                         "reference": REFERENCE_TEXT, "draft": "draft text", "facts": facts,
                                                         "n_facts": 2, "present": 1, "partial": 1, "absent": 0,
                                                         "contradicted": 0, "coverage": 0.75, "strict_coverage": 0.5,
                                                         "contradiction_rate": 0.0}]}
    return ev


@pytest.fixture
def many(tmp_path: Path) -> Path:
    """Two entries: one drafted five ways (one of them a strategy the registry does not know), one drafted twice."""
    run = tmp_path / "many"
    for mim, strategies in (("500001", ("recall", "kg", "zzz_new", "closedbook", "direct")), ("500002", ("direct", "agent"))):
        d = run / mim
        _write(d / "seed.json", Seed(mim=mim, prefix="#", title=GOLD.title).model_dump())
        _write(d / "papers.json", [_paper_record(PAPER)])
        for strategy in strategies:
            entry = _entry(strategy)
            _write(d / f"entry.{strategy}.json", entry.model_dump())
            _write(d / f"eval.{strategy}.json", _eval_with_gold(entry))
    return run


def test_any_number_of_strategies(many: Path):
    data = _embedded(build_report(many, None).read_text(encoding="utf-8"))
    # registry order first, then strategies the registry does not know
    assert data["strategies"] == ["kg", "direct", "agent", "closedbook", "recall", "zzz_new"]
    info = {i["name"]: i for i in data["strategy_info"]}
    assert info["kg"]["label"] == "Evidence graph" and info["kg"]["summary"]
    assert info["closedbook"]["control"] is True and not any(i["control"] for n, i in info.items() if n != "closedbook")
    assert info["zzz_new"]["label"] == "zzz_new" and info["zzz_new"]["summary"] == ""
    assert info["direct"]["n_drafts"] == 2 and info["agent"]["n_drafts"] == 1 and info["agent"]["n_scored"] == 1
    assert data["baseline"] == "direct" and data["compared"] is None
    first, second = data["entries"]
    assert first["strategies"] == ["kg", "direct", "closedbook", "recall", "zzz_new"]
    assert second["strategies"] == ["direct", "agent"]
    assert set(first["rows"]) == set(first["strategies"]) and set(first["pids"]) == set(first["strategies"])
    assert first["rows"]["zzz_new"]["has_draft"] and first["rows"]["zzz_new"]["claims"] == 2
    assert set(_payload(data, 1)["entries"]) == {"direct", "agent"}


def test_strategies_json_drives_labels_and_comparison(many: Path):
    compared = {
        "run": "many", "baseline": "kg", "n_entries": 1,
        "strategies": [{"name": "kg", "label": "Graph (renamed)", "summary": "From the file.", "n_entries": 1},
                       {"name": "direct", "label": "Plain reading", "summary": "", "n_entries": 2, "control": True}],
        "means": [{"metric": "gene_f1", "label": "Causal gene F1", "higher_is_better": True,
                   "values": {"kg": 1.0, "direct": 0.5}, "n": {"kg": 1, "direct": 1}}],
        "volume": [], "versus_baseline": {"direct": []}, "pooled": {}, "by_content_level": {}, "by_stratum": {},
        "by_access": {}, "by_reference_count": {}, "cost": {},
    }
    _write(many / "strategies.json", compared)
    data = _embedded(build_report(many, None).read_text(encoding="utf-8"))
    info = {i["name"]: i for i in data["strategy_info"]}
    assert info["kg"]["label"] == "Graph (renamed)" and info["kg"]["summary"] == "From the file."
    assert info["direct"]["control"] is True               # an explicit flag in the data wins
    assert info["direct"]["summary"]                       # an empty summary falls back to the registry
    assert info["closedbook"]["label"].startswith("Memory only")  # not in the file: from the registry
    assert data["baseline"] == "kg" and data["compared"]["means"][0]["values"]["direct"] == 0.5
    # a file without the comparison tables is ignored
    _write(many / "strategies.json", {"run": "many"})
    assert _embedded(build_report(many, None).read_text(encoding="utf-8"))["compared"] is None


def test_strategy_info_without_registry(monkeypatch):
    monkeypatch.setattr(report_build, "_registry", lambda: {})
    info = strategy_info(["direct", "mystery", "kg"], [{"name": "mystery", "label": "A control arm", "summary": ""}])
    assert [i["name"] for i in info] == ["kg", "direct", "mystery"]      # fallback order, then by name
    assert info[0]["label"] == "kg" and info[2]["control"] is True       # "control" in the label


def test_gold_text_and_references_are_stored_once(many: Path):
    data = _embedded(build_report(many, None).read_text(encoding="utf-8"))
    payload = _payload(data)
    assert payload["gold_refs"] == [REFERENCE_TEXT]        # five evals, one copy of the reference paragraph
    for ev in payload["evals"].values():
        (para,) = ev["gold_text"]["paragraphs"]
        assert para["ref"] == 0 and "reference" not in para and "draft" not in para
        assert "n_facts" not in para and len(para["facts"]) == 2   # the page recounts the tally from the facts
        assert ev["gold_text"]["coverage"] == 0.75                 # entry-level totals stay
    # a reference identical to the paper list keeps only its PMID
    assert payload["entries"]["kg"]["references"] == [{"pmid": "8016139"}]
    assert payload["papers"][0]["reference"] == PAPER.reference


def _cohort(n_records: int = 2, quote: str = "a quote from the paper") -> dict:
    record = lambda i: {  # noqa: E731
        "id": f"R:8016139:{i}", "pmid": "8016139", "label": f"Family {i}", "kind": "family", "n_affected": 3, "n_families": 1,
        "phenotypes": [{"text": "optic atrophy", "hpo_label": "Optic atrophy", "hpo_id": "HP:0000648", "present": True,
                        "n_with": None, "n_assessed": None, "some_only": False, "other_cause": False}] * 4,
        "variants": [{"gene": "MT-ND6", "as_reported": "14459G-A", "zygosity": "unknown", "origin": "inherited", "key": "V1"}],
        "inheritance": "MT", "genotype_mode": "MT", "genotype_reason": "mtDNA variant",
        "quotes": [quote, quote + " again"], "quote_grounding": [1.0, 1.0],
    }
    return {
        "totals": {"individuals": 3 * n_records, "families": n_records, "records": n_records},
        "papers": [{"pmid": "8016139", "label": "Jun et al. (1994)", "relevance": "primary", "records": n_records, "notes": 1}],
        "phenotypes": {f"HP:{i:07d}": {"label": f"Feature {i}", "present": i, "absent": 0, "assessed": i + 1,
                                        "records": ["R:8016139:1"], "pmids": ["8016139"], "lower_bound": False}
                       for i in range(1, 121)},
        "variants": [{"id": "V1", "gene": "MT-ND6", "keys": ["m.14459G>A"], "omim_name": "MTND6, ALA72VAL",
                      "records": ["R:8016139:1"], "pmids": ["8016139"], "individuals": 3}],
        "genes": {"MT-ND6": {"pmids": ["8016139"], "variants": ["V1"], "individuals": 3}},
        "inheritance": {"chosen": ["MT"], "support": {"MT": {"individuals": 3, "records": ["R:8016139:1"], "pmids": ["8016139"],
                                                           "reasons": {"mtDNA variant": 1}}}},
        "possible_duplicates": [["R:8016139:1", "R:8016139:2"]],
        "records": [record(i) for i in range(1, n_records + 1)],
        "notes": [{"id": "N:8016139:1", "pmid": "8016139", "section": "pathogenesis", "statement": "A note.",
                   "quotes": [quote], "quote_grounding": [1.0]}],
        "dropped": {"records": [{"id": "x"}], "notes": []},
        "gene_decisions": {"candidates": ["MT-ND6"], "confirmed": ["MT-ND6"], "not_confirmed": [], "dropped": []},
    }


def test_strategy_working_files_are_embedded(tmp_path: Path):
    run = tmp_path / "work"
    d = run / "500001"
    for strategy in ("cohort", "recall"):
        entry = _entry(strategy)
        entry.meta[strategy] = {"marker": strategy}
        _write(d / f"entry.{strategy}.json", entry.model_dump())
    _write(d / "cohort.json", _cohort())
    memory = _entry("closedbook")      # the from-memory draft with its audit: 1 supported claim, 1 unsupported
    _write(d / "recall.memory_audit.json", memory.model_dump())
    _write(d / "usage.json", {"by_strategy": {"recall": {
        "generate/recall": {"calls": 1, "turns": 2, "full_list_price_usd": 0.11, "full_seconds": 10.0},
        "generate/verify": {"calls": 9, "turns": 18, "full_list_price_usd": 0.7, "full_seconds": 99.0},
        "audit/verify": {"calls": 7, "turns": 14, "full_list_price_usd": 0.3, "full_seconds": 40.0},
        "score/judge": {"calls": 5, "turns": 10, "full_list_price_usd": 0.15, "full_seconds": 20.0},
        "total": {"calls": 22}}}, "total": {"calls": 22}})
    payload = _payload(_embedded(build_report(run, None).read_text(encoding="utf-8")))

    assert payload["entries"]["cohort"]["meta"]["cohort"] == {"marker": "cohort"}   # strategy meta passes through
    cohort = payload["cohort"]
    assert cohort["totals"]["individuals"] == 6 and len(cohort["records"]) == 2 and len(cohort["notes"]) == 1
    assert cohort["records"][0]["quotes"] == ["a quote from the paper", "a quote from the paper again"]
    assert cohort["n_dropped"] == {"records": 1, "notes": 0}
    assert len(cohort["phenotypes"]) == 80 and cohort["trimmed"] == {"phenotypes": {"shown": 80, "of": 120}}
    assert cohort["phenotypes"][0]["label"] == "Feature 120"                         # the most frequent are kept
    assert cohort["inheritance"]["support"]["MT"]["n_records"] == 1

    memory_audit = payload["recall_memory"]
    assert memory_audit["claims"] == 2 and memory_audit["by_verdict"] == {"supported": 1, "unsupported": 1}
    assert memory_audit["n_not_standing"] == 1 and memory_audit["not_standing"][0]["claim"] == "in 105 controls"
    assert memory_audit["not_standing"][0]["where"] == "Molecular Genetics"

    use = payload["usage"]["by_strategy"]["recall"]
    assert use["generate"] == {"calls": 10, "turns": 20, "usd": 0.81, "seconds": 109.0}
    assert use["audit"]["usd"] == 0.3 and use["score"]["calls"] == 5


def test_large_case_table_is_capped():
    big = report_build._slim_cohort(_cohort(n_records=400, quote="q" * 300))
    assert report_build._size(big) <= report_build.COHORT_CAP_BYTES
    trimmed = big["trimmed"]
    assert trimmed["record_features"] == "counts" and trimmed["quotes"] == "first only"
    assert trimmed["records"]["of"] == 400 and trimmed["records"]["shown"] == len(big["records"]) < 400
    assert big["totals"]["records"] == 400 and big["records"][0]["n_phenotypes"] == 4 and big["records"][0]["n_quotes"] == 2
    small = report_build._slim_cohort(_cohort())
    assert "records" not in small["trimmed"] and len(small["records"][0]["phenotypes"]) == 4
    assert report_build._slim_cohort(None) is None and report_build._slim_memory_audit([]) is None


def test_packed_single_file_round_trips(many: Path, monkeypatch):
    plain = _embedded(build_report(many, None).read_text(encoding="utf-8"))
    assert "packed" not in plain                                   # small pages keep readable JSON
    html = build_report(many, None, packed=True).read_text(encoding="utf-8")
    data = _embedded(html)
    assert "payloads" not in data and set(data["packed"]) == set(plain["payloads"])
    for name, text in data["packed"].items():
        assert re.fullmatch(r"[A-Za-z0-9+/=]+", text) and unpack(text) == plain["payloads"][name]
    assert BREAKOUT not in html and "window.pwned" not in html     # packed data cannot carry markup
    assert build_report(many, None, packed=True).read_text(encoding="utf-8") == html   # byte-for-byte repeatable
    # by size: above the threshold a single file is packed; a split page never is
    monkeypatch.setattr(report_build, "PACK_THRESHOLD", 10)
    assert "packed" in _embedded(build_report(many, None).read_text(encoding="utf-8"))
    split = _embedded(build_report(many, None, split=True).read_text(encoding="utf-8"))
    assert split["split"] is True and "packed" not in split and "payloads" not in split
    name, payload = _registered(many / "report_data" / "500001.js")
    assert payload == plain["payloads"][name]
