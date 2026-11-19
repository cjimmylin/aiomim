"""Second-hand evidence: JATS parsing, caps, the source-text block, attribution, and the strategy end to end.

Offline: Europe PMC and PMC are replaced by small synthetic JATS fixtures, the
model by a scripted one, and the ontology and nomenclature services by stubs.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiomim import synthesize, verify
from aiomim.cache import DiskCache
from aiomim.config import get_settings
from aiomim.models import Paper, SecondhandPassage, Seed
from aiomim.pipeline import RunConfig, build_entries
from aiomim.render import entry_markdown
from aiomim.sources import citing
from aiomim.strategies import secondhand as sh

from test_pipeline_offline import FakeHPO, _Gene

FIXTURES = Path(__file__).parent / "fixtures"
TITLE = "A new recessive ataxia caused by GENEX mutation in two families"
ABSTRACT = ("We describe a recessive ataxia in two families. Affected children were unable to walk unaided "
            "and carried a variant in the GENEX gene, which was absent from controls.")
TARGET = Paper(pmid="90000003", title=TITLE, authors=["Gamma A", "Other B"], year=2001, journal="Fict J Genet",
               abstract=ABSTRACT)
OWN_FULL = Paper(pmid="90000009", title="GENEX function in neurons", authors=["Eta E"], year=2010,
                 abstract="An abstract that is long enough to count as one, about GENEX in cultured neurons and more.",
                 fulltext="RESULTS\n" + "GENEX was expressed in Purkinje cells of the mouse cerebellum. " * 60)


def numeric() -> str:
    return (FIXTURES / "citing_numeric.xml").read_text()


def authoryear() -> str:
    return (FIXTURES / "citing_authoryear.xml").read_text()


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def test_numeric_citations_ranges_and_table_rows():
    found, passages = citing.cited_passages(numeric(), citing.Target.of(TARGET))
    assert found
    texts = [p.text for p in passages]
    # The paragraph that cites only reference 1 is not about the target.
    assert not any("rare disorder of the fictional GENEX" in t for t in texts)
    first = next(p for p in passages if "consanguineous" in p.text)
    assert first.section == "Introduction" and first.kind == "paragraph" and first.n_other_refs == 0
    assert "5 affected sibs who had ataxia from age 3 years [*]." in first.text
    # [2]–[5]: only the endpoints carry an xref; the target (3) lies inside the range.
    ranged = next(p for p in passages if "many families" in p.text)
    assert ranged.section == "Discussion > Phenotype"
    assert ranged.n_other_refs == 3 and "[*]" in ranged.text and "(" not in ranged.text.split("families")[1][:6]
    # "2,4" does not cite 3; "2-4" as one xref's text does.
    assert not any("Brain imaging" in t for t in texts)
    assert any("Cataract was noted" in t for t in texts)
    table = [p for p in passages if p.kind == "table"]
    assert len(table) == 1
    assert table[0].section == "Table 1"
    assert "Row: F1 | c.100A>G | 5 | [*]" in table[0].text and "Columns: Family | Variant | Patients | Ref" in table[0].text
    assert "F2" not in table[0].text


def test_author_year_citation_and_fuzzy_title_match():
    found, passages = citing.cited_passages(authoryear(), citing.Target.of(TARGET))
    assert found
    assert len(passages) == 1
    p = passages[0]
    assert p.section == "Discussion"
    assert p.text.startswith("In the original report, Gamma et al. (2001) [*] found that 5 of 5 affected sibs")


def test_no_reference_to_the_target_means_no_passages():
    other = Paper(pmid="12345678", title="An entirely unrelated paper about kidney stones in adults", year=1990)
    assert citing.cited_passages(numeric(), citing.Target.of(other)) == (False, [])
    assert citing.cited_passages("<html>error page</html>", citing.Target.of(TARGET)) == (False, [])


def test_trim_keeps_the_citing_sentence_within_the_cap():
    filler = "This sentence is filler about something else entirely and adds nothing. "
    text = filler * 20 + "The original family had 5 affected sibs [*]. " + filler * 20
    out = citing.trim_around(text, limit=400)
    assert "[*]" in out and "5 affected sibs" in out
    assert len(out) <= 400 + 4 and out.startswith("…") and out.endswith("…")
    assert citing.trim_around("Short [*].", limit=400) == "Short [*]."


# --------------------------------------------------------------------------- #
# Ranking and caps
# --------------------------------------------------------------------------- #


def test_passage_caps_and_ranking():
    target = citing.Target.of(TARGET)
    papers = [citing.CitingPaper(pmid=str(i), pmcid=f"PMC{i}", open_access=True) for i in range(1, 5)]
    found = []
    for c in papers:
        for k in range(4):
            text = f"Passage {k} of {c.pmid}: 5 patients were homozygous for c.100A>G [*]. " + "x" * 900
            found.append((c, citing.RawPassage("Results", "paragraph", text, n_other_refs=k, full_chars=len(text))))
    chosen = citing.select_passages(found, target)
    assert len(chosen) <= citing.MAX_PASSAGES
    per = {}
    for c, _, _ in chosen:
        per[c.pmid] = per.get(c.pmid, 0) + 1
    assert max(per.values()) <= citing.MAX_PER_CITING
    assert sum(len(p.text) for _, p, _ in chosen) <= citing.TOTAL_CHARS
    # Passages that cite fewer other papers come first.
    assert [p.n_other_refs for _, p, _ in chosen[:4]] == [0, 0, 0, 0]


def test_citing_papers_are_ranked_and_filtered():
    target = citing.Target.of(TARGET)
    cands = [
        citing.CitingPaper(pmid="1", pmcid="PMC1", title="Unrelated cardiology trial", open_access=True),
        citing.CitingPaper(pmid="2", pmcid="PMC2", title="GENEX ataxia families revisited", open_access=True),
        citing.CitingPaper(pmid="3", pmcid="", title="GENEX recessive ataxia", open_access=True),          # no PMCID
        citing.CitingPaper(pmid="4", pmcid="PMC4", title="GENEX recessive ataxia", open_access=False),     # closed
        citing.CitingPaper(pmid="5", pmcid="PMC5", title="GENEX recessive ataxia families", open_access=True),  # own paper
        citing.CitingPaper(pmid="6", pmcid="PMC6", title="Ataxia overview", open_access=True,
                           pub_types=["review-article", "journal article"]),
    ]
    ranked = citing.rank_citing(cands, target, exclude={"5"})
    # Open access with a PMCID, not the entry's own; a review gets a head start over title overlap.
    assert [c.pmid for c in ranked] == ["6", "2", "1"]


def test_search_results_parse():
    data = {"resultList": {"result": [
        {"pmid": "42", "pmcid": "PMC42", "title": "<i>GENEX</i> &amp; ataxia", "authorString": "Smith J, Jones K.",
         "pubYear": "2015", "pubType": "review-article; journal article", "isOpenAccess": "Y"},
        {"id": "PPR1", "source": "PPR", "title": "A preprint"},
    ]}}
    (c,) = citing.parse_search(data)
    assert (c.pmid, c.pmcid, c.title, c.authors, c.year, c.open_access, c.kind) == \
        ("42", "PMC42", "GENEX & ataxia", ["Smith J", "Jones K"], 2015, True, "review")
    assert c.label == "Smith and Jones (2015)"


# --------------------------------------------------------------------------- #
# The paper's text
# --------------------------------------------------------------------------- #


PASSAGE = SecondhandPassage(citing_pmid="42", citing_pmcid="PMC42", citing_label="Smith and Jones (2015)",
                            section="Discussion", text="Gamma et al. (2001) [*] found 5 affected sibs homozygous "
                            "for c.100A>G in two consanguineous families.", n_other_refs=1)


def test_source_text_is_unchanged_without_passages():
    p = Paper(pmid="1", title="T", abstract="A" * 150)
    assert p.source_text() == "TITLE: T\n\nABSTRACT:\n" + "A" * 150
    q = p.model_copy(update={"fulltext": "F" * 3000})
    assert q.source_text() == "TITLE: T\n\nABSTRACT:\n" + "A" * 150 + "\n\nFULL TEXT:\n" + "F" * 3000
    assert q.source_text(20) == ("TITLE: T\n\nABSTRACT:\n" + "A" * 150)[:20]
    assert p.secondhand_block() == ""


def test_source_text_appends_a_delimited_block():
    p = TARGET.model_copy(update={"secondhand": [PASSAGE]})
    text = p.source_text()
    assert text.startswith(TARGET.source_text() + "\n\nSECOND-HAND DESCRIPTIONS OF THIS PAPER\n")
    assert "NOT this paper's own text" in text
    assert '[1] Smith and Jones (2015), PMID 42, section "Discussion" (the same paragraph also cites 1 other paper):' in text
    assert text.endswith("END OF SECOND-HAND DESCRIPTIONS")
    assert p.content_level == TARGET.content_level == "abstract"


def test_attribution_of_evidence_quotes():
    p = TARGET.model_copy(update={"secondhand": [PASSAGE]})
    where = sh.Attributor([p, OWN_FULL])
    assert where.locate(p.pmid, "Affected children were unable to walk unaided") == ("own", "")
    assert where.locate(p.pmid, "found 5 affected sibs homozygous for c.100A>G in two consanguineous families") == \
        ("secondhand", "42")
    assert where.locate(p.pmid, "7 affected sibs were compound heterozygous for a deletion") == ("unlocated", "")
    assert where.locate(p.pmid, "") == ("none", "")
    assert where.locate(OWN_FULL.pmid, "expressed in Purkinje cells of the mouse cerebellum") == ("own", "")


# --------------------------------------------------------------------------- #
# Retrieval never raises, and caches
# --------------------------------------------------------------------------- #


@pytest.fixture
def offline_citing(monkeypatch, tmp_path):
    monkeypatch.setattr(citing, "_result_cache", lambda: DiskCache(tmp_path / "citing", suffix=".json"))
    monkeypatch.setattr(citing, "_miss_cache", lambda: DiskCache(tmp_path / "miss", suffix=".json"))
    found = [
        citing.CitingPaper(pmid="42", pmcid="PMC42", title="GENEX ataxia: a review", authors=["Smith J", "Jones K"],
                           year=2015, pub_types=["review-article"], open_access=True),
        citing.CitingPaper(pmid="43", pmcid="PMC43", title="A boy with GENEX ataxia", authors=["Lee M"], year=2018,
                           pub_types=["case reports"], open_access=True),
        citing.CitingPaper(pmid="90000009", pmcid="PMC9", title="GENEX in neurons", open_access=True),  # own paper
        citing.CitingPaper(pmid="44", pmcid="", title="Closed", open_access=False),
    ]
    xml = {"PMC42": numeric(), "PMC43": authoryear()}
    calls = {"search": 0, "fetch": []}

    def fake_search(pmid):
        calls["search"] += 1
        return found if pmid == TARGET.pmid else []

    def fake_fetch(pmcid):
        calls["fetch"].append(pmcid)
        return (xml[pmcid], "test") if pmcid in xml else None

    monkeypatch.setattr(citing, "citing_papers", fake_search)
    monkeypatch.setattr(citing, "fetch_jats", fake_fetch)
    return calls


def test_secondhand_for_finds_ranks_and_caches(offline_citing):
    record = citing.secondhand_for(TARGET, frozenset({TARGET.pmid, OWN_FULL.pmid}))
    assert (record["n_citing"], record["n_open_access"], record["n_eligible"]) == (4, 3, 2)
    assert sorted(offline_citing["fetch"]) == ["PMC42", "PMC43"]       # never the entry's own paper
    assert all(f["reference_found"] for f in record["fetched"])
    assert 1 <= len(record["passages"]) <= citing.MAX_PASSAGES
    assert sum(1 for p in record["passages"] if p["citing_pmid"] == "42") <= citing.MAX_PER_CITING
    assert {p["citing_label"] for p in record["passages"]} <= {"Smith and Jones (2015)", "Lee (2018)"}
    again = citing.secondhand_for(TARGET, frozenset({TARGET.pmid, OWN_FULL.pmid}))
    assert again["cached"] and offline_citing["search"] == 1


def test_failed_or_empty_lookup_gives_no_passages(monkeypatch, offline_citing):
    other = Paper(pmid="555", title="Some paper with no citations at all", year=2020)
    assert citing.secondhand_for(other)["passages"] == []
    monkeypatch.setattr(citing, "citing_papers", lambda pmid: None)
    record = citing.secondhand_for(Paper(pmid="556", title="Lookup fails"))
    assert record["passages"] == [] and record["error"]

    def boom(pmid):
        raise RuntimeError("network down")
    monkeypatch.setattr(citing, "citing_papers", boom)
    record = citing.secondhand_for(Paper(pmid="557", title="Lookup raises"))
    assert record["passages"] == [] and "network down" in record["error"]


# --------------------------------------------------------------------------- #
# The strategy end to end
# --------------------------------------------------------------------------- #


SEED = Seed(mim="999001", prefix="#", title="FOOBAR SYNDROME", symbol="FOOB")


@pytest.fixture
def stub_services(monkeypatch):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: FakeHPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    hgnc_module.normalize_symbol = lambda s: s.upper()
    hgnc_module.gene_info = lambda s: _Gene("GENEX", "600001", "1p1") if s.upper() == "GENEX" else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


class ScriptedLLM:
    def __init__(self):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str]] = []

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, system, prompt))
        return getattr(self, f"_{output.__name__}")(prompt)

    def map(self, stage, system, prompts, output, **_):
        return [self.call(stage, system, p, output) for p in prompts]

    def _DEntry(self, prompt):
        P = synthesize.DParagraph
        return synthesize.DEntry(
            intro=P(text="FOOBAR syndrome is a recessive ataxia caused by mutation in the GENEX gene.",
                    pmids=[TARGET.pmid]),
            sections=[synthesize.DSection(name="clinical_features", paragraphs=[
                P(text="Gamma et al. (2001) described 5 affected sibs from 2 consanguineous families who were "
                       "unable to walk unaided.", pmids=[TARGET.pmid]),
                P(text="Eta (2010) found GENEX expressed in Purkinje cells.", pmids=[OWN_FULL.pmid]),
            ])],
            relationships=[synthesize.DRelationship(gene_symbol="GENEX", inheritance=["AR"], pmids=[TARGET.pmid])],
            allelic_variants=[], clinical_synopsis=[],
        )

    def _XClaimSets(self, prompt):
        A = verify.XAttributedClaim
        table = {
            "intro": [A(text="FOOBAR syndrome is caused by GENEX mutation", pmids=[TARGET.pmid])],
            "clinical_features.1": [A(text="Gamma et al. (2001) described 5 affected sibs", pmids=[TARGET.pmid]),
                                    A(text="The sibs were unable to walk unaided", pmids=[TARGET.pmid])],
            "clinical_features.2": [A(text="GENEX was expressed in Purkinje cells", pmids=[OWN_FULL.pmid])],
        }
        return verify.XClaimSets(paragraphs=[verify.XParagraphClaims(paragraph_id=k, claims=v)
                                             for k, v in table.items() if f'id="{k}"' in prompt])

    def _XAudit(self, prompt):
        V = verify.XVerdict
        out = []
        if "[intro#1]" in prompt:
            out.append(V(claim_id="intro#1", verdict="supported", explanation="",
                         evidence_quote="carried a variant in the GENEX gene"))
        if "[clinical_features.1#1]" in prompt:
            quote = ("found that 5 of 5 affected sibs were homozygous" if "5 of 5 affected sibs" in prompt
                     else "invented quote that is nowhere at all in this text")
            out.append(V(claim_id="clinical_features.1#1", verdict="supported", explanation="", evidence_quote=quote))
        if "[clinical_features.1#2]" in prompt:
            out.append(V(claim_id="clinical_features.1#2", verdict="supported", explanation="",
                         evidence_quote="Affected children were unable to walk unaided"))
        if "[clinical_features.2#1]" in prompt:
            out.append(V(claim_id="clinical_features.2#1", verdict="supported", explanation="",
                         evidence_quote="GENEX was expressed in Purkinje cells"))
        return verify.XAudit(verdicts=out)

    def _XRevisions(self, prompt):
        return verify.XRevisions(paragraphs=[])


def test_strategy_end_to_end(tmp_path, stub_services, offline_citing):
    llm = ScriptedLLM()
    entries, _ = build_entries(SEED, [TARGET, OWN_FULL], RunConfig(strategies=("secondhand",)), llm, tmp_path)
    entry = entries["secondhand"]

    record = json.loads((tmp_path / "secondhand.json").read_text())
    (target,) = record["targets"]                      # the full-text paper is not supplemented
    assert target["pmid"] == TARGET.pmid and target["n_passages"] >= 1 and target["n_open_access"] == 3
    assert record["totals"]["with_passages"] == 1

    # The writer saw the block and the rules; the audit read the same block.
    stage, system, prompt = next(c for c in llm.calls if c[0] == "synthesize")
    assert "SECOND-HAND DESCRIPTIONS OF THIS PAPER" in prompt and "Second-hand descriptions." in system
    assert system.startswith(synthesize.DIRECT_SYSTEM)
    audits = [p for s, _, p in llm.calls if s == "verify" and "Claims attributed to this paper" in p]
    assert any("SECOND-HAND DESCRIPTIONS" in p for p in audits if f"PMID {TARGET.pmid}" in p)

    para = entry.sections[0].paragraphs[0]
    # Support found only in a later paper's description is not support by the cited paper.
    assert [c.verdict for c in para.checks] == ["not_checkable", "supported"]
    second = para.checks[0]
    assert "Lee (2018) (PMID 43)" in second.explanation and "not checked against PMID 90000003" in second.explanation
    assert "Verdict on the later paper's description: supported." in second.explanation
    assert para.secondhand_pmids == ["43"]
    assert entry.sections[0].paragraphs[1].secondhand_pmids == [] and entry.intro.secondhand_pmids == []
    meta = entry.meta["secondhand"]
    assert meta["claims"] == 4 and meta["claims_on_secondhand"] == 1 and meta["claims_on_own_text"] == 3
    assert meta["secondhand_verdicts"] == {"supported": 1}
    assert meta["secondhand_verdicts_by_passage_kind"] == {"paragraph": {"supported": 1}}
    assert meta["secondhand_verdicts_by_cocited"] == {"few": {"supported": 1}}
    assert meta["papers_supplemented"] == 1 and meta["papers_with_passages"] == 1
    assert meta["named_citing_papers"] == []
    # The audit tally and the faithfulness score leave the second-hand claim out.
    from aiomim.evaluate import eval_faithfulness
    assert entry.meta["audit"] == {"supported": 3, "not_checkable": 1}
    faith = eval_faithfulness(entry)
    assert (faith["n_claims"], faith["not_checkable"], faith["supported_rate"]) == (3, 1, 1.0)
    assert "Never name the later papers" in system
    # Citing papers are never references of the entry.
    assert entry.meta["strategy"] == "secondhand"
    assert {r.pmid for r in entry.references} == {TARGET.pmid, OWN_FULL.pmid}

    md = (tmp_path / "entry.secondhand.md").read_text()
    assert "unable to walk unaided. †" in md
    assert "† Rests in part on later papers' descriptions of the cited work, not on its own text: Lee (2018), PMID 43." in md
    # Other strategies' Markdown is unchanged: no dagger, no footnote.
    plain = entry.model_copy(deep=True)
    for p in plain.all_paragraphs():
        p.secondhand_pmids = []
    assert "†" not in entry_markdown(plain)

    # The audit hook rebuilds the same papers from the record.
    again = sh.audit_papers([TARGET, OWN_FULL], tmp_path)
    assert len(again[0].secondhand) == target["n_passages"] and again[1].secondhand == []
    assert again[0].source_text().startswith(TARGET.source_text() + "\n\nSECOND-HAND DESCRIPTIONS")


def test_double_audit_of_claims_about_a_hidden_paper(tmp_path, stub_services, offline_citing):
    """The validation's audit: what the writer saw, then the true full text, per claim."""
    from aiomim.secondhand import _claim_counts, audit_hidden

    llm = ScriptedLLM()
    augmented, _ = sh.supplement([TARGET, OWN_FULL])
    entry = synthesize.synthesize_direct(SEED, augmented, llm, extra_rules=sh.RULES, strategy="secondhand")
    # The "true" full text of the hidden paper says something else about the sibs.
    truth = TARGET.model_copy(update={"fulltext": "RESULTS\n" + "Affected children were unable to walk unaided. " * 60})
    rows = audit_hidden(entry, augmented, {TARGET.pmid: truth, OWN_FULL.pmid: OWN_FULL}, {TARGET.pmid}, llm)
    by_claim = {r["claim_id"]: r for r in rows}
    assert set(by_claim) == {"intro#1", "clinical_features.1#1", "clinical_features.1#2"}   # not the other paper's
    sibs = by_claim["clinical_features.1#1"]
    assert (sibs["evidence_in"], sibs["citing_pmid"]) == ("secondhand", "43")
    assert sibs["seen"]["verdict"] == "supported"
    assert sibs["primary"]["verdict"] == "partially_supported"      # its quote is not in the full text
    assert by_claim["clinical_features.1#2"]["evidence_in"] == "own"
    assert (sibs["passage_kind"], sibs["passage_n_other_refs"], sibs["passage_cocited"]) == ("paragraph", 0, "few")
    counts = _claim_counts(rows)
    assert counts["by_evidence_location"]["secondhand"]["against_full_text"]["partially_supported"] == 1
    assert counts["secondhand_by_passage_kind"]["paragraph"]["n"] == 1
    assert counts["secondhand_by_cocited"]["few"]["against_full_text"]["partially_supported"] == 1
    assert counts["collapsed"]["n_claims"] == 3


def test_repeated_claims_collapse_and_counts_pool():
    from aiomim.secondhand import _add, _claim_counts, check_markdown, collapse, pool_results

    def row(cid, claim, primary, kind="table", co="many"):
        return {"claim_id": cid, "pmid": "1", "claim": claim, "evidence_in": "secondhand", "citing_pmid": "9",
                "passage_kind": kind, "passage_cocited": co, "passage_n_other_refs": 5,
                "seen": {"verdict": "supported"}, "primary": {"verdict": primary}}
    rows = [row("molecular_genetics.3#2", "The patient had an annular pancreas.", "unsupported"),
            row("av0001.1#3", "The patient had an annular  pancreas", "partially_supported"),
            row("molecular_genetics.3#1", "Mutations were found in 6 infants.", "contradicted", "paragraph", "few")]
    assert len(collapse(rows)) == 2
    counts = _claim_counts(rows)
    assert counts["secondhand_by_passage_kind"]["table"]["against_full_text"]["unsupported"] == 1
    assert counts["collapsed"]["secondhand_by_passage_kind"]["table"]["against_full_text"] == \
        {"supported": 0, "partially_supported": 1, "unsupported": 0, "contradicted": 0, "no_verdict": 0}
    assert _add({"a": {"b": 1}, "n": 2}, {"a": {"b": 2, "c": 1}, "n": 1, "s": "x"}) == {"a": {"b": 3, "c": 1}, "n": 3}
    entry = {"mim": "1", "title": "T", "hidden_papers": ["1"], "gold_paragraphs": 0,
             "retrieval": {"hidden_with_passages": 1}, "claims": counts,
             "coverage": {k: {"paragraphs": 0, "n_facts": 0, "present": 0, "partial": 0, "absent": 0,
                              "contradicted": 0, "coverage": None} for k in ("abstract", "secondhand", "fulltext")},
             "coverage_same_paragraphs": {"paragraphs": 0}}
    summary = pool_results([entry, entry])
    assert summary["claims"]["n_claims"] == 6 and summary["claims"]["collapsed"]["n_claims"] == 4
    md = check_markdown({**summary, "source": "x", "run": "y", "failures": {}})
    assert "exclude supplementary material" in md and "upper bound" in md
    assert "| table | 4 (2) |" in md and "| few | 2 (2) |" in md


def test_naming_a_citing_paper_in_the_text_is_recorded():
    from aiomim.models import GeneratedEntry

    entry = GeneratedEntry(title="X", meta={"unknown_citations": ["Lee (2018)", "Nobody et al. (1990)"]})
    papers = [TARGET.model_copy(update={"secondhand": [PASSAGE.model_copy(update={"citing_label": "Lee (2018)"})]})]
    assert sh.named_citing_papers(entry, papers) == ["Lee (2018)"]


def test_entries_without_a_full_text_draft_are_not_pooled_as_zero(tmp_path, monkeypatch):
    from aiomim import secondhand

    def entry(mim, full_present):
        cov = lambda present: {"paragraphs": 1, "n_facts": 10, "present": present, "partial": 0,  # noqa: E731
                               "absent": 10 - present, "contradicted": 0, "coverage": present / 10}
        return {"mim": mim, "title": "T", "hidden_papers": ["1"], "gold_paragraphs": 1,
                "retrieval": {"hidden_with_passages": 1}, "claims": {"n_claims": 0, "by_evidence_location": {}},
                "coverage": {"abstract": cov(4), "secondhand": cov(5), "fulltext": cov(full_present)},
                "coverage_same_paragraphs": {"paragraphs": 1}}

    runs = tmp_path / "runs"
    for mim, stopped in (("100001", False), ("100002", True)):
        (runs / "src" / mim).mkdir(parents=True)
        (runs / "src" / mim / "eval.direct.json").write_text(json.dumps({"stopped": "safety"} if stopped else {}))
        (runs / "chk" / mim / "secondhand_check").mkdir(parents=True)
        (runs / "chk" / mim / "secondhand_check" / "result.json").write_text(json.dumps(entry(mim, 0 if stopped else 8)))
    (runs / "chk" / "secondhand_check.json").write_text(json.dumps({"source": "src", "usage": {"calls": 3}}))
    monkeypatch.setattr(secondhand, "get_settings", lambda: SimpleNamespace(runs=runs))

    summary = secondhand.reaggregate("chk")
    assert summary["left_out_no_fulltext_draft"] == ["100002"] and summary["n_entries_coverage"] == 1
    assert summary["coverage"]["fulltext"]["coverage"] == 0.8          # not (8 + 0) / 20
    assert summary["coverage"]["abstract"]["n_facts"] == 10             # the same entries for every condition
    assert summary["coverage_all_entries"]["abstract"]["n_facts"] == 20 and summary["usage"] == {"calls": 3}
    md = (runs / "chk" / "secondhand_check.md").read_text()
    assert "left out: 1 entries whose full-text direct draft was not written" in md and "| no draft |" in md
