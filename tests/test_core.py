"""Offline tests for the model-free logic: grounding, variant merging, the graph, scoring."""

from __future__ import annotations

from pydantic import BaseModel

from aiomim.evaluate import _tally, _variant_keys, eval_faithfulness, eval_genes, eval_inheritance, eval_variants, prf
from aiomim.grounding import SourceIndex
from aiomim.kg import build_graph, nucleotide_key, omim_variant_name, protein_key, variant_keys
from aiomim.llm import schema_for
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
    PhenotypeMention,
    Seed,
    VariantMention,
)
from aiomim.render import entry_markdown

SOURCE = """TITLE: A mitochondrial DNA mutation at nucleotide pair 14459 of the NADH dehydrogenase subunit 6 gene
ABSTRACT:
A five-generation Hispanic family expressing maternally transmitted Leber hereditary optic neuropathy
and/or early-onset dystonia associated with bilateral basal ganglia lesions was studied. A G-to-A transition
at nucleotide pair 14459 changed a moderately conserved alanine to a valine at NADH dehydro-
genase subunit 6 (ND6) residue 72. The mutation was heteroplasmic in 3 of 19 family members.
"""


# --------------------------------------------------------------------------- #
# Quote grounding
# --------------------------------------------------------------------------- #


def test_verbatim_quote_is_grounded_despite_wrapping_and_case():
    index = SourceIndex(SOURCE)
    assert index.score("a five-generation hispanic family expressing maternally transmitted "
                       "Leber hereditary optic neuropathy and/or early-onset dystonia") == 1.0


def test_hyphenated_line_break_is_rejoined():
    index = SourceIndex(SOURCE)
    assert index.score("valine at NADH dehydrogenase subunit 6 (ND6) residue 72") == 1.0


def test_changed_number_is_not_grounded():
    index = SourceIndex(SOURCE)
    altered = "A G-to-A transition at nucleotide pair 14484 changed a moderately conserved alanine to a valine"
    assert index.score(altered) < 1.0
    assert not SourceIndex(SOURCE).contains("The mutation was homoplasmic in all 19 family members examined here")


def test_invented_quote_scores_low():
    index = SourceIndex(SOURCE)
    assert index.score("Muscle biopsy showed ragged red fibres and complex I deficiency in the proband") < 0.5


def test_ellipsis_takes_the_worst_piece():
    index = SourceIndex(SOURCE)
    good = "A five-generation Hispanic family ... was studied"
    bad = "A five-generation Hispanic family ... carried a homozygous nonsense mutation in exon four"
    assert index.score(good) == 1.0
    assert index.score(bad) < 0.6


# --------------------------------------------------------------------------- #
# Variant canonicalisation
# --------------------------------------------------------------------------- #


def test_protein_key_unifies_notations():
    for text in ("p.Gly131Ser", "G131S", "gly131-to-ser", "GLY131SER", "p.(Gly131Ser)"):
        assert protein_key(text) == "p.G131S", text
    assert protein_key("Arg123Ter") == "p.R123*"
    assert protein_key("R123X") == "p.R123*"
    assert protein_key("p.Leu12ProfsTer5").startswith("p.L12")
    assert protein_key("c.3697G>A") == ""


def test_nucleotide_key_unifies_notations():
    assert nucleotide_key("c.3697G>A") == "c.3697G>A"
    assert nucleotide_key("3697G-A") == "c.3697G>A"
    assert nucleotide_key("G14459A", mito=True) == "m.14459G>A"
    assert nucleotide_key("m.14459G>A") == "m.14459G>A"
    assert nucleotide_key("NM_005902.4:c.859C>T") == "c.859C>T"
    assert nucleotide_key("c.367+1G>A") == "c.367+1G>A"
    assert nucleotide_key("Gly131Ser") == ""


def test_mito_detection_does_not_catch_nuclear_mt_genes():
    assert variant_keys(VariantMention(gene="MT-ND6", as_reported="G14459A")) == {"m.14459G>A"}
    assert variant_keys(VariantMention(gene="MTND6", as_reported="14459G-A")) == {"m.14459G>A"}
    assert variant_keys(VariantMention(gene="MTHFR", as_reported="C677T")) == {"c.677C>T"}


def test_omim_variant_names():
    assert omim_variant_name("SMAD3", ["c.859C>T", "p.R287W"]) == "SMAD3, ARG287TRP"
    assert omim_variant_name("MT-ND1", ["m.3697G>A"]) == "MTND1, 3697G-A"


def test_protein_key_keeps_frameshifts_apart_from_missense():
    # The bug: a frameshift was reduced to the missense change at the same residue.
    for text in ("Glu296LysfsTer12", "p.Glu296Lysfs*6", "GLU296LYSFSTER12", "E296KfsX12", "p.(Glu296LysfsTer12)"):
        assert protein_key(text) == "p.E296Kfs", text
    assert protein_key("p.(Pro216Argfs*14)") == "p.P216Rfs"
    assert protein_key("p.Glu296Lysfs*6") != protein_key("p.Glu296Lys") == "p.E296K"
    assert protein_key("R123fs") == protein_key("ARG123FS") == "p.R123fs"
    # nonsense, missense, extension, delins and in-frame deletions keep their kind
    assert protein_key("p.Arg123Ter") == protein_key("p.Arg123*") == protein_key("R123X") == "p.R123*"
    assert protein_key("p.Gly131Ser") == "p.G131S"
    assert protein_key("p.Ter110GlnextTer17") == "p.*110Qext"
    assert protein_key("p.Met1ext-5") == "p.M1ext"
    assert protein_key("p.Cys28delinsTrpVal") == "p.C28delinsWV"
    assert protein_key("p.Cys28delinsTrpVal") != protein_key("p.Cys28del") == "p.C28del"
    assert protein_key("p.Lys2_Met3del") == "p.K2_M3del"
    assert protein_key("p.Phe508del") == "p.F508del"


def test_frameshift_names_and_keys():
    keys = variant_keys(VariantMention(gene="PNPLA8", as_reported="p.Glu296Lysfs*6"))
    assert keys == {"p.E296Kfs", "p.E296fs"} and "p.E296K" not in keys
    assert omim_variant_name("PNPLA8", keys) == "PNPLA8, GLU296LYSFS"
    assert omim_variant_name("TYK2", ["p.P216fs"]) == "TYK2, PRO216FS"
    assert omim_variant_name("X", ["p.R123*"]) == "X, ARG123TER"
    assert omim_variant_name("X", ["p.*110Qext"]) == "X, TER110GLNEXT"
    assert omim_variant_name("X", ["p.C28delinsWV"]) == "X, CYS28DELINSTRPVAL"
    # a missense change at the same residue is a different variant: it must not merge or match
    assert "E296K" not in _variant_keys(["PNPLA8, GLU296LYSFSTER12"], "PNPLA8")
    assert "E296Kfs" in _variant_keys(["PNPLA8, GLU296LYSFSTER12"], "PNPLA8")
    assert not (_variant_keys(["p.Glu296Lys"], "PNPLA8") & _variant_keys(["p.Glu296Lysfs*6"], "PNPLA8"))


# --------------------------------------------------------------------------- #
# Knowledge graph
# --------------------------------------------------------------------------- #


def _papers():
    return [
        Paper(pmid="1", title="First report", authors=["Jun AS", "Brown MD", "Wallace DC"], year=1994,
              abstract="x" * 200),
        Paper(pmid="2", title="Second family", authors=["Shoffner JM", "Brown MD"], year=1995,
              abstract="x" * 200),
        Paper(pmid="3", title="Unrelated LHON review", authors=["Smith A"], year=1996, abstract="x" * 200),
    ]


def _finding(fid, pmid, section, variants=(), phenotypes=(), inheritance="UNKNOWN", genes=("ND6",)):
    return Finding(id=fid, pmid=pmid, section=section, statement=f"statement {fid}", quotes=["q"],
                   quote_grounding=[1.0], genes=list(genes), variants=list(variants), phenotypes=list(phenotypes),
                   inheritance=inheritance)


def _graph():
    seed = Seed(mim="500001", title="LEBER OPTIC ATROPHY AND DYSTONIA")
    dystonia = PhenotypeMention(text="dystonia", hpo_id="HP:0001332", hpo_label="Dystonia")
    extractions = [
        PaperExtraction(pmid="1", relevance="primary", findings=[
            _finding("1:1", "1", "clinical_features", phenotypes=[dystonia]),
            _finding("1:2", "1", "molecular_genetics", inheritance="MT",
                     variants=[VariantMention(gene="ND6", as_reported="G14459A", protein="A72V")]),
        ]),
        PaperExtraction(pmid="2", relevance="supporting", findings=[
            _finding("2:1", "2", "molecular_genetics", inheritance="MT", genes=("MTND6",),
                     variants=[VariantMention(gene="MTND6", genomic="m.14459G>A", protein="p.Ala72Val")]),
            _finding("2:2", "2", "clinical_features",
                     phenotypes=[PhenotypeMention(text="dystonia", hpo_id="HP:0001332", hpo_label="Dystonia", present=False)]),
        ]),
        PaperExtraction(pmid="3", relevance="background", findings=[
            _finding("3:1", "3", "molecular_genetics", inheritance="AD", genes=("OPA1",),
                     variants=[VariantMention(gene="OPA1", cdna="c.100A>G")]),
        ]),
    ]
    alias = {"ND6": "MT-ND6", "MTND6": "MT-ND6"}
    return build_graph(seed, _papers(), extractions, normalize_gene=lambda s: alias.get(s, s))


def test_same_variant_named_differently_becomes_one_node():
    kg = _graph()
    mito = [n for n in kg.variant_nodes() if n["gene"] == "MT-ND6"]
    assert len(mito) == 1
    assert set(mito[0]["keys"]) == {"m.14459G>A", "p.A72V"}
    assert {f.pmid for f in kg.findings_for(mito[0]["id"])} == {"1", "2"}
    assert mito[0]["omim_name"] == "MTND6, ALA72VAL"


def test_background_papers_do_not_define_the_entry():
    kg = _graph()
    assert list(kg.gene_support()) == ["MT-ND6"]
    assert kg.inheritance_support() == {"MT": ["1", "2"]}
    caused_by = [e["dst"] for e in kg.out("entry", "caused_by")]
    assert caused_by == ["gene:MT-ND6"]


def test_phenotype_profile_tracks_presence_and_absence():
    profile = _graph().phenotype_profile()
    assert profile["HP:0001332"]["present"] == ["1"]
    assert profile["HP:0001332"]["absent"] == ["2"]


def test_findings_are_ordered_oldest_first():
    kg = _graph()
    assert [f.id for f in kg.findings_in("molecular_genetics")] == ["1:2", "2:1", "3:1"]


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #


def test_prf_handles_empty_sets():
    assert prf({"a", "b"}, {"b", "c"}) == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "tp": 1,
                                             "n_predicted": 2, "n_gold": 2}
    assert prf(set(), {"a"})["precision"] is None
    assert prf({"a"}, set())["recall"] is None


def _entry():
    entry = GeneratedEntry(
        mim="500001", title="LEBER OPTIC ATROPHY AND DYSTONIA", symbol="LDYT", prefix="#",
        relationships=[GenePhenotypeRelationship(gene_symbol="MT-ND6", inheritance=["MT"], pmids=["1"])],
        inheritance=["MT"],
        intro=EntryParagraph(text="A number sign (#) is used with this entry.", pmids=["1"]),
        sections=[EntrySection(name="clinical_features", heading="Clinical Features", paragraphs=[
            EntryParagraph(text="Jun et al. (1994) described a family.", pmids=["1"], checks=[
                ClaimCheck(claim="a", verdict="supported"), ClaimCheck(claim="b", verdict="contradicted")]),
        ])],
        allelic_variants=[AllelicVariantEntry(number=1, gene_symbol="MT-ND6", name="MTND6, ALA72VAL",
                                              hgvs=["m.14459G>A", "p.A72V"],
                                              paragraphs=[EntryParagraph(text="In a family ...", pmids=["1"])])],
    )
    entry.assign_paragraph_ids()
    return entry


def _gold():
    return GoldEntry(
        mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", cited_pmids=["1", "2"],
        genes=[GoldGene(symbol="MT-ND6")], inheritance=["MT"],
        allelic_variants=[
            GoldAllelicVariant(omim_id="516006.0002", gene_symbol="MTND6", name="MTND6, 14459G-A",
                               clinvar_name="NC_012920.1(MT-ND6):m.14459G>A",
                               paragraphs=[GoldParagraph(text="Jun et al. ...", pmids=["1"], mims=["500001"])]),
            GoldAllelicVariant(omim_id="516000.0012", gene_symbol="MTND1", name="MTND1, 3697G-A",
                               clinvar_name="NC_012920.1(MT-ND1):m.3697G>A",
                               paragraphs=[GoldParagraph(text="Spruijt et al. ...", pmids=["9"], mims=["500001"])]),
            GoldAllelicVariant(omim_id="516006.0001", gene_symbol="MTND6", name="MTND6, 14484T-C",
                               paragraphs=[GoldParagraph(text="other disorder", pmids=["8"], mims=["535000"])]),
        ],
    )


def test_gene_and_inheritance_scores():
    assert eval_genes(_entry(), _gold())["f1"] == 1.0
    assert eval_inheritance(_entry(), _gold())["match"] is True


def test_variant_matching_across_notations_and_scope():
    result = eval_variants(_entry(), _gold())
    # Of three gold variants, one belongs to another phenotype and one rests on a
    # paper this entry does not cite; only the remaining one is in scope.
    assert result["n_gold"] == 1 and result["n_gold_out_of_scope"] == 2
    assert result["n_matched"] == 1 and result["recall"] == 1.0 and result["missed"] == []

    gold = _gold()
    gold.cited_pmids.append("9")            # now the MTND1 paper is one the entry cites
    result = eval_variants(_entry(), gold)
    assert result["n_gold"] == 2 and result["recall"] == 0.5
    assert result["missed"] == ["516000.0012 MTND1, 3697G-A"]


def test_variant_keys_from_clinvar_and_omim_names():
    assert "859C>T" in _variant_keys(["NM_005902.4(SMAD3):c.859C>T (p.Arg287Trp)"], "SMAD3")
    assert "R287W" in _variant_keys(["NM_005902.4(SMAD3):c.859C>T (p.Arg287Trp)"], "SMAD3")
    assert "R287W" in _variant_keys(["SMAD3, ARG287TRP"], "SMAD3")


def test_gold_paragraphs_filtered_to_this_phenotype_and_its_references():
    assert [p.pmids for p in _gold().gold_paragraphs] == [["1"], ["9"]]
    assert [p.pmids for p in _gold().scoped_paragraphs] == [["1"]]


def test_faithfulness_and_paragraph_status():
    entry = _entry()
    result = eval_faithfulness(entry)
    assert result["n_claims"] == 2 and result["supported_rate"] == 0.5 and result["error_rate"] == 0.5
    assert entry.sections[0].paragraphs[0].status == "flagged"
    assert entry.intro.status == "unverified"


def test_tally():
    facts = [{"status": "present"}, {"status": "partial"}, {"status": "absent"}, {"status": "contradicted"}]
    assert _tally(facts)["coverage"] == 0.375
    assert _tally([])["coverage"] is None


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #


def test_citation_labels():
    one, two, three = (Paper(pmid="1", authors=a, year=2001) for a in (["Smith J"], ["Smith J", "Jones K"],
                                                                         ["Smith J", "Jones K", "Lee M"]))
    assert (one.label, two.label, three.label) == ("Smith (2001)", "Smith and Jones (2001)", "Smith et al. (2001)")
    assert Paper(pmid="1", authors=["van der Knaap MS", "X Y", "Z W"], year=1999).label == "van der Knaap et al. (1999)"


def test_schema_is_closed_and_inlined():
    class Inner(BaseModel):
        gene: str
        note: str = ""

    class Outer(BaseModel):
        items: list[Inner]
        count: int | None = None

    schema = schema_for(Outer)
    assert "$defs" not in schema and "$ref" not in str(schema)
    assert schema["additionalProperties"] is False and schema["required"] == ["items", "count"]
    assert schema["properties"]["items"]["items"]["required"] == ["gene", "note"]


def test_markdown_render_has_omim_layout():
    text = entry_markdown(_entry())
    assert text.startswith("# # 500001")
    for needle in ("LEBER OPTIC ATROPHY AND DYSTONIA; LDYT", "Phenotype-Gene Relationships", "### Clinical Features",
                   "### ALLELIC VARIANTS", ".0001", "MTND6, ALA72VAL", "✗"):
        assert needle in text, needle


def test_recalled_omim_cross_references_are_stripped():
    from aiomim.synthesize import _strip_mim_numbers

    removed: list[str] = []
    text = ("Jun et al. (1994) found an ala72-to-val substitution (A72V; 516006.0002) in the MTND6 gene (516006) "
            "in a family with LHON (535000); it was absent from 125000 controls (see 540000).")
    cleaned = _strip_mim_numbers(text, {"516006", "500001"}, removed)
    assert cleaned == ("Jun et al. (1994) found an ala72-to-val substitution (A72V) in the MTND6 gene (516006) "
                       "in a family with LHON; it was absent from 125000 controls.")
    assert removed == ["516006.0002", "535000", "540000"]


def test_planted_error_rules_change_exactly_one_fact():
    from aiomim.auditcheck import _swap_count, _swap_inheritance, _swap_residue, _swap_zygosity

    text = ("In 3 sibs from a consanguineous family, Smith et al. (2001) identified a homozygous c.367C-T "
            "transition in the GENE gene, resulting in an arg123-to-trp (R123W) substitution. The 14-year-old "
            "proband had onset in 2001; inheritance was autosomal recessive.")
    assert _swap_count(text)[0].startswith("In 6 sibs from a consanguineous family, Smith et al. (2001)")
    assert "c.367C-T" in _swap_count(text)[0] and "(2001)" in _swap_count(text)[0]      # variants and years untouched
    assert "a heterozygous c.367C-T" in _swap_zygosity(text)[0]
    altered, was, now = _swap_residue(text)
    assert "arg123-to-ser (R123S)" in altered and (was, now) == ("arg123-to-trp", "arg123-to-ser")
    assert "autosomal dominant" in _swap_inheritance(text)[0]
    assert _swap_count("The c.2981-2A-G mutation was found in 1996.") is None
    assert _swap_residue("No protein change was reported.") is None


def test_citation_labels_for_collective_names_and_suffixes():
    assert Paper(pmid="1", authors=["Epi4K Consortium", "Allen AS", "Berkovic SF"], year=2013).label == \
        "Epi4K Consortium et al. (2013)"
    assert Paper(pmid="1", authors=["Smith JR Jr", "Jones K"], year=1999).label == "Smith and Jones (1999)"
    assert Paper(pmid="1", authors=["De Vries DD", "Went LN", "Bruyn GW"], year=1996).label == "De Vries et al. (1996)"


def test_citation_matching_ignores_accents_and_flags_true_unknowns():
    from aiomim.synthesize import _attach_text_citations, _labels

    papers = [Paper(pmid="1", authors=["Müller T", "A B", "C D"], year=2014),
              Paper(pmid="2", authors=["Héon E", "A B", "C D"], year=1999),
              Paper(pmid="3", authors=["van der Knaap MS", "A B", "C D"], year=2005)]
    para = EntryParagraph(text="Muller et al. (2014) and Heon et al. (1999) agreed with van der Knaap et al. (2005), "
                               "unlike Novotny et al. (1986).", pmids=[])
    unknown: list[str] = []
    _attach_text_citations(para, _labels(papers), unknown)
    assert sorted(para.pmids) == ["1", "2", "3"]
    assert unknown == ["Novotny et al. (1986)"]


def test_parenthetical_citations_are_matched_and_unknown_ones_flagged():
    from aiomim.synthesize import _attach_text_citations, _labels

    papers = [Paper(pmid="1", authors=["Boyden SE", "A B", "C D"], year=2012),
              Paper(pmid="2", authors=["Jun AS", "Brown MD"], year=1994)]
    para = EntryParagraph(text="Weakness is mainly axial (Boyden et al., 2012; Jun and Brown, 1994), and minicores "
                               "are seen on biopsy (Takayama et al., 2016).", pmids=[])
    unknown: list[str] = []
    _attach_text_citations(para, _labels(papers), unknown)
    assert sorted(para.pmids) == ["1", "2"]
    assert unknown == ["Takayama et al. (2016)"]


def test_audit_only_papers_are_checked_but_not_cited():
    entry = GeneratedEntry(title="X", sections=[EntrySection(name="description", paragraphs=[
        EntryParagraph(text="From memory.", audit_pmids=["1", "2"]),
        EntryParagraph(text="Jun et al. (1994) said so.", pmids=["2"], audit_pmids=["2"])])])
    assert entry.cited_pmids() == ["2"]
    assert entry.sections[0].paragraphs[0].checked_pmids == ["1", "2"]
    assert entry.sections[0].paragraphs[1].checked_pmids == ["2"]


def test_transcript_ids_and_non_nucleotide_names_never_become_variant_keys():
    assert nucleotide_key("NM_007077.3") == "" and nucleotide_key("NM_007077.3:") == ""
    assert nucleotide_key("NM_007077.3:c.124C>T") == "c.124C>T"
    assert nucleotide_key("p.Glu163_Ser165del") == "" and nucleotide_key("r.421_542del") == ""
    assert nucleotide_key("IVS3+2delT") == "" and nucleotide_key("insT1354") == ""
    assert nucleotide_key("chrX_24091319C/T") == ""
    assert nucleotide_key("c.695_697delACA") == "c.695_697delaca"
    assert nucleotide_key("c.542+1_542+4delGTAA") == "c.542+1_542+4delgtaa"
    assert nucleotide_key("c.131_132del") == "c.131_132del"
    # Two different variants quoted with the same transcript must stay two variants.
    a = variant_keys(VariantMention(gene="AP4S1", as_reported="c.124C>T (NM_007077.3)"))
    b = variant_keys(VariantMention(gene="AP4S1", as_reported="c.289C>T (NM_007077.3)"))
    assert a == {"c.124C>T"} and b == {"c.289C>T"} and not a & b
