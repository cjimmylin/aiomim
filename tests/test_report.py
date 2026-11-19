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
from aiomim.report.build import build_report, json_for_script

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
    assert new_item["gold"] is None and new_item["evals"] == {}
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
