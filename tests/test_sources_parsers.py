"""Offline tests of the source parsers, against trimmed real responses in fixtures/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from aiomim.models import Paper
from aiomim.sources.clinvar import merge_variants, parse_vcv_xml
from aiomim.sources.fulltext import bioc_to_text, jats_to_text
from aiomim.sources.hgnc import mito_symbol
from aiomim.sources.hpo import HPO, normalize
from aiomim.sources.medgen import inheritance_code, parse_conceptmeta
from aiomim.sources.ncbi import parse_omim_summary, parse_pubmed_xml, split_alt_titles, split_omim_title
from aiomim.sources.omim_api import section_key

FIX = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- PubMed


def test_pubmed_xml_to_paper():
    papers = parse_pubmed_xml(read("pubmed_efetch.xml"))
    by = {p.pmid: p for p in papers}
    assert set(by) == {"17562939", "8016139"}
    p = by["17562939"]
    assert p.title == ("A MELAS-associated ND1 mutation causing leber hereditary optic neuropathy "
                       "and spastic dystonia.")
    assert p.authors[0] == "Spruijt L" and len(p.authors) >= 3
    assert p.year == 2007
    assert p.journal == "Arch Neurol"
    assert p.volume == "64" and p.pages == "890-3"
    assert p.doi == "10.1001/archneur.64.6.890"
    assert p.pmcid is None
    assert "Case Reports" in p.pub_types
    assert "DNA, Mitochondrial" in p.mesh_terms
    assert p.abstract.startswith("OBJECTIVE: ")
    assert "\nDESIGN: " in p.abstract
    assert p.label == "Spruijt et al. (2007)"
    q = by["8016139"]
    assert q.pmcid == "PMC44167"
    assert q.journal == "Proc Natl Acad Sci U S A"


def test_paper_label_author_counts():
    assert Paper(pmid="1", authors=["Novotny EJ"], year=1986).label == "Novotny (1986)"
    assert Paper(pmid="1", authors=["Novotny EJ", "Singh G"], year=1986).label == "Novotny and Singh (1986)"
    assert Paper(pmid="1", authors=["Novotny EJ", "Singh G", "Wallace DC"], year=1986).label == \
        "Novotny et al. (1986)"
    assert Paper(pmid="9", authors=[]).label == "PMID 9 (n.d.)"


def test_pubmed_book_and_medline_date():
    xml = """<PubmedArticleSet>
    <PubmedBookArticle><BookDocument><PMID Version="1">20301352</PMID>
      <Book><BookTitle>GeneReviews<sup>®</sup></BookTitle><PubDate><Year>1993</Year></PubDate></Book>
      <ArticleTitle>Leber Hereditary Optic Neuropathy</ArticleTitle>
      <AuthorList Type="authors"><Author><LastName>Yu-Wai-Man</LastName><Initials>P</Initials></Author>
      <Author><CollectiveName>The LHON Consortium</CollectiveName></Author></AuthorList>
      <Abstract><AbstractText Label="CLINICAL CHARACTERISTICS">LHON is <i>common</i>.</AbstractText></Abstract>
    </BookDocument></PubmedBookArticle>
    <PubmedArticle><MedlineCitation><PMID>1</PMID><Article><Journal><JournalIssue>
      <PubDate><MedlineDate>1998 Dec-1999 Jan</MedlineDate></PubDate></JournalIssue>
      <Title>Some Journal</Title></Journal><ArticleTitle>X<sup>2</sup> test.</ArticleTitle></Article>
    </MedlineCitation></PubmedArticle>
    </PubmedArticleSet>"""
    a, b = parse_pubmed_xml(xml)
    assert a.pmid == "20301352" and a.year == 1993 and a.journal == "GeneReviews®"
    assert a.authors == ["Yu-Wai-Man P", "The LHON Consortium"]
    assert a.abstract == "CLINICAL CHARACTERISTICS: LHON is common."
    assert b.year == 1998 and b.journal == "Some Journal" and b.title == "X2 test."


# --------------------------------------------------------------------------- OMIM summary


def test_alt_title_splitting():
    assert split_omim_title("LOEYS-DIETZ SYNDROME 3; LDS3") == ("LOEYS-DIETZ SYNDROME 3", "LDS3")
    assert split_omim_title("LEBER OPTIC ATROPHY AND DYSTONIA") == ("LEBER OPTIC ATROPHY AND DYSTONIA", "")
    assert split_alt_titles("ANEURYSMS-OSTEOARTHRITIS SYNDROME; AOS;;LOEYS-DIETZ SYNDROME, TYPE 1C;;") == [
        "ANEURYSMS-OSTEOARTHRITIS SYNDROME", "LOEYS-DIETZ SYNDROME, TYPE 1C"]
    s = parse_omim_summary({"uid": "613795", "oid": "#613795", "title": "LOEYS-DIETZ SYNDROME 3; LDS3",
                            "alttitles": "AOS SYNDROME;;LDS1C", "locus": ""})
    assert s["prefix"] == "#" and s["symbol"] == "LDS3" and s["title"] == "LOEYS-DIETZ SYNDROME 3"
    assert s["alt_titles"] == ["AOS SYNDROME", "LDS1C"]
    assert parse_omim_summary({"uid": "100100", "oid": "100100", "title": "X"})["prefix"] == ""


# --------------------------------------------------------------------------- Full text


def test_jats_to_text_keeps_tables_drops_references():
    text = jats_to_text(read("jats_PMC6418351.xml"))
    assert text.startswith("## INTRODUCTION")
    assert "## MATERIALS AND METHODS" in text and "### Patients" in text
    # table caption and rows kept
    assert "Table 1. The clinical features and the laboratory findings" in text
    assert "III3 | 20/M | 6 | Spastic dystonia | None | 17 | Bilateral hyperintensities of the putamen" in text
    assert "Figure 1. The pedigree of family" in text
    # back matter dropped
    for gone in ("REFERENCES", "ACKNOWLEDGMENTS", "CONFLICT OF INTEREST", "Contributor Information",
                 "National Natural Science Foundation", "Click here for additional data file",
                 "Appenzeller, P"):
        assert gone not in text, gone
    # author-year citations kept intact, paragraphs separated by blank lines
    assert "(Lim, 2009)" in text
    assert "\n\n" in text


def test_jats_numeric_citations_dropped():
    xml = ("<article><body><sec><title>Results</title><p>Seen in five families "
           "[<xref ref-type='bibr' rid='b1'>1</xref>,<xref ref-type='bibr' rid='b2'>2</xref>].</p>"
           "</sec></body><back><ref-list><ref id='b1'>Ref one</ref></ref-list></back></article>")
    assert jats_to_text(xml) == "## Results\n\nSeen in five families."


def test_bioc_to_text():
    text = bioc_to_text(json.loads(read("bioc_30623604.json")))
    assert text.startswith("## INTRODUCTION")
    assert "Patient | Age/gender | Age at onset" in text
    assert "III5 | 16/M | 4 | Spastic dystonia" in text
    assert "CONFLICT OF INTEREST" not in text and "no conflict of interest" not in text
    assert "Autosomal‐dominant striatal degeneration is caused" not in text  # REF passage
    assert "Bilateral striatal necrosis due to homoplasmic" not in text.split("\n")[0]


# --------------------------------------------------------------------------- ClinVar


def test_clinvar_vcv_to_allelic_variant():
    avs = parse_vcv_xml(read("clinvar_vcv_9733.xml"))
    assert len(avs) == 1
    av = avs[0]
    assert av.omim_id == "516000.0012"
    assert av.name == "MTND1, 3697G-A"
    assert av.gene_symbol == "MTND1"
    assert av.clinvar_variation_id == "9733"
    assert av.clinvar_name == "NC_012920.1(MT-ND1):m.3697G>A"
    assert set(av.phenotypes) == {"MELAS SYNDROME", "LEBER OPTIC ATROPHY AND DYSTONIA"}
    assert "SCV000030611" in av.scv and "SCV000030612" in av.scv
    para = next(p for p in av.paragraphs if "17562939" in p.pmids)
    assert "500001" in para.mims
    assert para.text.startswith("Spruijt et al. (2007) reported a sister and brother")
    # paragraphs de-duplicated by text across the two SCVs
    assert len({p.text for p in av.paragraphs}) == len(av.paragraphs)


def test_merge_variants_dedupes_paragraphs():
    avs = parse_vcv_xml(read("clinvar_vcv_9733.xml"))
    again = merge_variants(avs + avs)
    assert len(again) == 1 and len(again[0].paragraphs) == len(avs[0].paragraphs)


# --------------------------------------------------------------------------- MedGen


def test_medgen_conceptmeta():
    meta = parse_conceptmeta(read("medgen_conceptmeta_613795.xml"), "613795")
    assert meta["omim_symbol"] == "LDS3"
    assert meta["omim_title"] == "LOEYS-DIETZ SYNDROME 3"
    assert "LOEYS-DIETZ SYNDROME WITH OSTEOARTHRITIS" in meta["omim_alt_titles"]
    assert "LOEYS-DIETZ SYNDROME 3" not in meta["omim_alt_titles"]
    assert meta["inheritance"] == ["AD"]
    assert [(g.symbol, g.entrez_id, g.location) for g in meta["genes"]] == [("SMAD3", "4088", "15q22.33")]
    assert "HP:0004942" in meta["clinical_feature_hpo"]
    assert meta["definitions"][0]["source"] == "GeneReviews"


def test_inheritance_code():
    assert inheritance_code("Autosomal dominant inheritance") == "AD"
    assert inheritance_code("Autosomal recessive inheritance") == "AR"
    assert inheritance_code("X-linked recessive inheritance") == "XLR"
    assert inheritance_code("Mitochondrial inheritance") == "MT"
    assert inheritance_code("Somatic mosaicism") == "SOMATIC_MOSAIC"
    assert inheritance_code("Something odd") is None


# --------------------------------------------------------------------------- misc


def test_mito_symbol_and_section_keys():
    assert mito_symbol("MTND1") == "MT-ND1"
    assert mito_symbol("MTTL1") == "MT-TL1"
    assert mito_symbol("MTATP6") == "MT-ATP6"
    assert mito_symbol("smad3") == "SMAD3"
    assert mito_symbol("MTOR") == "MTOR"
    assert section_key("clinicalFeatures") == "clinical_features"
    assert section_key("molecularGenetics") == "molecular_genetics"
    assert section_key("text") == "intro"
    assert section_key("animalModel") == "animal_model"


# --------------------------------------------------------------------------- HPO


@pytest.fixture(scope="module")
def tiny_hpo(tmp_path_factory) -> HPO:
    d = tmp_path_factory.mktemp("hpo")
    shutil.copy(FIX / "tiny.obo", d / "hp.obo")
    shutil.copy(FIX / "tiny.hpoa", d / "phenotype.hpoa")
    return HPO(obo_path=d / "hp.obo", hpoa_path=d / "phenotype.hpoa", download=False)


def test_hpo_structure(tiny_hpo: HPO):
    h = tiny_hpo
    assert h.label("HP:0000648") == "Optic atrophy"
    assert h.definition("HP:0000648") == "Atrophy of the optic nerve."
    assert "Optic nerve atrophy" in h.synonyms("HP:0000648")
    assert h.ancestors("HP:0000648") == frozenset(
        {"HP:0000648", "HP:0000587", "HP:0000478", "HP:0000707", "HP:0000118", "HP:0000001"})
    assert "HP:0000648" not in h.ancestors("HP:0000648", include_self=False)
    assert set(h.parents("HP:0000587")) == {"HP:0000478", "HP:0000707"}
    assert "HP:0000648" in h.children("HP:0000587")
    assert h.descendants("HP:0000478") == frozenset({"HP:0000587", "HP:0000648"})
    assert h.is_phenotype("HP:0000648") and not h.is_phenotype("HP:0001427")
    assert h.is_inheritance("HP:0001427")


def test_hpo_resolve(tiny_hpo: HPO):
    h = tiny_hpo
    assert h.resolve("HP:0007768") == "HP:0000648"  # alt_id
    assert h.resolve("HP:0009999") == "HP:0000648"  # replaced_by
    assert h.resolve("HP:0009998") is None          # obsolete, no replacement
    assert h.resolve("HP:1234567") is None
    assert h.exists("HP:0007768") and not h.exists("HP:1234567")


def test_hpo_exact_and_search(tiny_hpo: HPO):
    h = tiny_hpo
    assert h.exact("Optic atrophy") == "HP:0000648"
    assert h.exact("  optic-ATROPHIES ") == "HP:0000648"
    assert h.exact("optic nerve atrophy") == "HP:0000648"
    assert h.exact("Old optic term") is None
    assert h.exact("obsolete Old optic term") is None
    hits = h.search("Optic atrophy")
    assert hits[0].id == "HP:0000648" and hits[0].score == 1.0
    hits = h.search("atrophy of both optic nerves", k=3)
    assert hits[0].id == "HP:0000648" and 0 < hits[0].score < 1.0
    # fuzzy matches come from the phenotypic-abnormality branch only
    assert all(x.id != "HP:0001427" for x in h.search("inheritance via mitochondria"))
    assert all(h.is_phenotype(x.id) for x in h.search("nervous system atrophy", k=10))
    assert h.search("aortic aneurysms")[0].id == "HP:0004942"


def test_hpo_category(tiny_hpo: HPO):
    h = tiny_hpo
    assert h.category("HP:0000648") == "Head & Neck: Eyes"   # eye beats nervous system
    assert h.category("HP:0001332") == "Neurologic"
    assert h.category("HP:0004942") == "Cardiovascular"
    assert h.category("HP:0001427") == "Miscellaneous"


def test_hpo_annotations_and_ic(tiny_hpo: HPO):
    h = tiny_hpo
    anns = h.annotations("500001")
    assert [a.hpo_id for a in anns] == ["HP:0000648", "HP:0001332", "HP:0001427"]
    assert anns[0].label == "Optic atrophy" and anns[0].frequency == "2/2"
    assert anns[2].aspect == "I"
    assert h.annotated_mims() == {"500001", "613795"}
    # 2 annotated diseases; optic atrophy in 1 of them, phenotype root in both
    assert h.information_content("HP:0000648") == pytest.approx(0.6931, abs=1e-3)
    assert h.information_content("HP:0000118") == 0.0
    # a second load reuses the pickled index
    again = HPO(obo_path=h.obo_path, hpoa_path=h.hpoa_path, download=False)
    assert again.exact("dystonic movements") == "HP:0001332"


def test_normalize():
    assert normalize("Optic-Atrophies") == normalize("optic atrophy")
