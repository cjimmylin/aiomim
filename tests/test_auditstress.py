"""Pure functions of Experiment C (auditstress): item construction, rules, matching, tallies."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

import pytest

from aiomim import auditstress as A
from aiomim.models import EntryParagraph, EntrySection, GeneratedEntry, Paper
from aiomim.verify import VERIFY_SYSTEM, verify_entry


def test_sentence_spans_keep_et_al_and_variant_prefixes():
    text = ("Murphy et al. (2004) studied a brother and sister. They carried the c.4C>T change in exon 1. "
            "The parents (e.g. Dr. Smith's cohort) were carriers.")
    sents = A.sentences(text)
    assert len(sents) == 3
    assert sents[0].startswith("Murphy et al. (2004)")
    assert sents[1] == "They carried the c.4C>T change in exon 1."


def test_label_forms_relabel_and_add_citation():
    assert A.label_forms("Seliem et al. (2000)") == ("Seliem et al. (2000)", "Seliem et al., 2000")
    assert A.label_forms("PMID 123 (2000)") is None
    text = "Seliem et al. (2000) found X. This was confirmed (Seliem et al., 2000)."
    out, n = A.relabel(text, "Seliem et al. (2000)", "Jones and Li (2011)")
    assert n == 2 and "Jones and Li (2011) found" in out and "(Jones and Li, 2011)" in out
    out, how = A.add_citation(text, "Seliem et al. (2000)", "Jones and Li (2011)")
    assert how == "narrative" and out.startswith("Seliem et al. (2000) and Jones and Li (2011) found")
    out, how = A.add_citation("X was seen (Seliem et al., 2000).", "Seliem et al. (2000)", "Jones and Li (2011)")
    assert how == "parenthetical" and "(Seliem et al., 2000; Jones and Li, 2011)" in out


@pytest.mark.parametrize("claim,paper,expected", [
    ("the ala2-to-val (A2V) substitution", "We found p.Ala2Val in TNNI3.", True),
    ("the A2V substitution", "a 4C>T transition (Ala2Val)", True),
    ("a c.367C>T transition", "the 367C-T change", True),
    ("a c.367C>T transition", "the C367T change", True),
    ("an arg123-to-trp substitution", "p.R123Q was found", True),        # same residue position: generous
    ("an arg123-to-trp substitution", "p.G55S was found", False),
    ("a glu296lysfs frameshift", "c.886delG (p.Glu296LysfsTer12)", True),
])
def test_variant_occurrence_is_generous_across_notations(claim, paper, expected):
    keys = A.text_variant_keys(paper)
    mentions = A.variant_mentions(claim)
    assert mentions
    got = any(A.occurs(m, k, keys, A._normalise_hgvs(paper).lower()) for m, k in mentions.items())
    assert got is expected


def test_variant_mentions_ignore_plain_words():
    assert A.variant_mentions("Patients aged 12 years had seizures in 2004.") == {}


@pytest.mark.parametrize("rule,text,deleted,after", [
    ("count", "The variant was found in 2 of 5 patients with ataxia.", "in 2 of 5 patients",
     "The variant was found with ataxia."),
    ("zygosity", "They carried a homozygous missense mutation.", "homozygous", "They carried a missense mutation."),
    ("zygosity", "They carried an heterozygous change.", "heterozygous", "They carried a change."),
    ("single family or patient", "The mutation was identified in one Turkish family.", "in one Turkish family",
     "The mutation was identified."),
    ("negation", "The variant was not found in 200 controls.", "not", "The variant was found in 200 controls."),
    ("hedge", "The variant possibly affects splicing.", "possibly", "The variant affects splicing."),
])
def test_c5_rules(rule, text, deleted, after):
    done = A.apply_rule(text, rule)
    assert done["deleted"] == deleted
    assert done["altered_text"] == after
    assert done["after_sentence"] == after and done["before_sentence"] == text


def test_c5_rule_without_match():
    assert A.apply_rule("Nothing restrictive here at all.", "count") is None


def test_distinctive_and_mechanical_match():
    s = "Two sibs born in 2004 carried the R123W variant (OMIM 123456) at age 12 years."
    d = A.distinctive(s)
    assert d["keys"] == ["c.123G>W"] or "p.R123W" in d["keys"]
    assert "2004" not in d["numbers"] and "123456" not in d["numbers"] and "12" in d["numbers"]
    assert A.mechanical_match(s, ["The paper reports p.Arg123Trp in two sibs."]) is True
    assert A.mechanical_match(s, ["The paper reports p.Gly5Ser."]) is False
    assert A.mechanical_match("Onset was at 3 to 14 years.", ["Age at onset ranged from 3 to 14 years."]) is True
    assert A.mechanical_match("Onset was at 3 to 14 years.", ["Age at onset was 3 years."]) is False
    assert A.mechanical_match("They had seizures.", ["anything"]) is None


def test_control_list_is_item_major_and_deduplicated():
    mk = lambda i, pid: {"mim": "1", "paragraph_id": pid, "pmid": "9", "text": "t" + pid}  # noqa: E731
    items = {"C1": [mk(0, "a"), mk(1, "b")], "C2": [mk(0, "a"), mk(1, "c")],
             "C3": [{**mk(0, "d"), "source_paragraph_id": "e", "source_pmid": "8", "source_text": "te"}]}
    ctl = A.control_list(items)
    assert [c["paragraph_id"] for c in ctl] == ["a", "d", "e", "b", "c"]
    assert [c["first_needed_by"] for c in ctl] == [0, 0, 0, 1, 1]


def test_chunks_round_up_to_whole_chunks():
    assert A._chunks(12, 5) == [(0, 5)]
    assert A._chunks(12, 6) == [(0, 5), (5, 10)]
    assert A._chunks(12, None) == [(0, 5), (5, 10), (10, 12)]


def test_select_natural_caps_facts_fulltext_first():
    targets = [{"mim": "1", "pmid": "a", "content_level": "abstract", "target_fact_ids": ["a1", "a2", "a3"]},
               {"mim": "1", "pmid": "b", "content_level": "fulltext", "target_fact_ids": ["b1", "b2"]}]
    got = A.select_natural(targets, 3, seed=1)
    ids = [f for t in got for f in t["target_fact_ids"]]
    assert len(ids) == 3 and {"b1", "b2"} <= set(ids)
    assert A.select_natural(targets, 3, seed=1) == got


# --------------------------------------------------------------------------- #
# The audit with per-paper verdicts agrees with verify_entry
# --------------------------------------------------------------------------- #


def _paper(pmid, abstract):
    return Paper(pmid=pmid, title=f"Paper {pmid}", abstract=abstract, authors=["Smith J", "Doe A", "Roe B"],
                 year=2000 + int(pmid))


class FakeLLM:
    """Decomposes by sentence and attributes to every cited paper; a paper supports a claim it contains."""

    def __init__(self):
        self.settings = SimpleNamespace(replicate="")
        self.safety_stops = 0

    def map(self, stage, system, prompts, output):
        out = []
        for prompt in prompts:
            if system == VERIFY_SYSTEM:
                source = re.search(r"<paper>\n(.*?)\n</paper>", prompt, re.S).group(1)
                verdicts = []
                for cid, claim in re.findall(r"^\[([^\]]+)\] (.*)$", prompt, re.M):
                    hit = claim.rstrip(".") in source
                    verdicts.append({"claim_id": cid, "verdict": "supported" if hit else "unsupported",
                                     "evidence_quote": claim.rstrip(".") if hit else "", "explanation": ""})
                out.append(output.model_validate({"verdicts": verdicts}))
            else:
                paras = []
                for pid, text, cited in re.findall(r'<paragraph id="([^"]+)">\n(.*?)\n</paragraph>\nPapers cited: (.*)',
                                                   prompt):
                    pmids = [c.split(" = ")[0] for c in cited.split("; ")]
                    paras.append({"paragraph_id": pid, "claims": [{"text": s, "pmids": pmids}
                                                                   for s in A.sentences(text)]})
                out.append(output.model_validate({"paragraphs": paras}))
        return out

    def call(self, *a, **k):
        raise AssertionError("no retry expected")


def test_audit_paragraphs_matches_verify_entry_and_keeps_per_paper_verdicts():
    papers = {"1": _paper("1", "The patients had ataxia and seizures in childhood."),
              "2": _paper("2", "An unrelated study of mice found nothing of the kind.")}
    texts = [("p.0", "The patients had ataxia. The patients had blue eyes.", ["1"]),
             ("p.1", "The patients had ataxia. Mice found nothing.", ["1", "2"])]
    paras = [EntryParagraph(id=i, text=t, pmids=p) for i, t, p in texts]
    got = A.audit_paragraphs(paras, papers, FakeLLM())

    holder = GeneratedEntry(title="x")
    ref = [EntryParagraph(id=i, text=t, pmids=p) for i, t, p in texts]
    holder.sections = [EntrySection(name="clinical_features", paragraphs=ref)]
    verify_entry(holder, papers, FakeLLM())
    for para in ref:
        assert [c.verdict for c in para.checks] == got[para.id]["verdicts"]
        assert para.status == got[para.id]["status"]
    first = got["p.1"]["claims"][0]
    assert first["per_paper"]["1"]["verdict"] == "supported" and first["per_paper"]["2"]["verdict"] == "unsupported"
    assert got["p.0"]["status"] == "flagged"


def test_precision_tally_counts_pairs_in_multi_citation_paragraphs():
    para = EntryParagraph(id="x", text="t", pmids=["1", "2"])
    single = EntryParagraph(id="y", text="t", pmids=["1"])
    r = {"claims": [
        {"pmids": ["1", "2"], "verdict": "supported",
         "per_paper": {"1": {"verdict": "supported"}, "2": {"verdict": "unsupported"}}},
        {"pmids": ["2"], "verdict": "partially_supported", "per_paper": {"2": {"verdict": "partially_supported"}}}]}
    t = A.precision_tally([(para, r), (single, r)])
    assert t["paragraphs"] == 1 and t["pairs"] == 3
    assert t["share_not_supported"] == round(1 / 3, 4)
    assert t["claims_passing_with_a_non_supporting_cited_paper"] == 1
    assert t["claims_attributed_to_every_cited_paper"] == 1


# --------------------------------------------------------------------------- #
# Planted claims and tallies
# --------------------------------------------------------------------------- #


def _claims(*pairs):
    return [{"text": t, "verdict": v, "pmids": ["1"], "per_paper": {}} for t, v in pairs]


def test_planted_claims_by_class():
    claims = _claims(("Two sibs had ataxia.", "supported"), ("They carried the R123W variant.", "unsupported"),
                     ("Onset was in infancy.", "supported"))
    assert A.planted_claims("C1", {}, claims) == [0, 1, 2]
    assert A.planted_claims("C3", {"moved_keys": ["p.R123W"]}, claims) == [1]
    item = {"variants": [{"mention": "arg123-to-trp", "occurs": False}, {"mention": "G5S", "occurs": True}]}
    assert A.planted_claims("C2", item, claims) == [1]
    c5 = {"after_sentence": "Onset was in infancy.", "before_sentence": "Onset was possibly in infancy."}
    assert A.planted_claims("C5", c5, claims) == [2]
    assert A.planted_claims("C6", {}, claims) is None


def test_tally_class_counts_known_unknown_and_controls():
    items = [{"id": "C2.0", "mim": "1", "paragraph_id": "a", "truth_known": True,
              "variants": [{"mention": "R123W", "occurs": False}]},
             {"id": "C2.1", "mim": "1", "paragraph_id": "b", "truth_known": False,
              "variants": [{"mention": "R123W", "occurs": True}]}]
    res = {"C2.0": {"status": "flagged", "claims": _claims(("R123W was found.", "contradicted"))},
           "C2.1": {"status": "supported", "claims": _claims(("R123W was found.", "supported"))}}
    ctl = {"ctl.0": {"status": "supported", "claims": _claims(("R123W was found.", "supported"))}}
    t = A.tally_class("C2", items, res, ctl, {("1", "a"): "ctl.0"})
    assert t["known"]["items"] == 1 and t["known"]["planted_claim_flagged"] == 1
    assert t["known"]["planted_claim_worst_verdict"] == {"contradicted": 1}
    assert t["known"]["control_paragraphs_flagged"] == 0 and t["known"]["control_planted_items"] == 1
    assert t["unknown"]["items"] == 1 and t["unknown"]["paragraphs_flagged"] == 0


def test_tally_c4_added_paper_verdicts():
    items = [{"id": "C4.0", "mim": "1", "paragraph_id": "a", "added_pmid": "9", "truth_known": True}]
    claims = [{"text": "x", "pmids": ["1", "9"], "verdict": "supported",
               "per_paper": {"1": {"verdict": "supported"}, "9": {"verdict": "unsupported"}}},
              {"text": "y", "pmids": ["1"], "verdict": "supported", "per_paper": {"1": {"verdict": "supported"}}}]
    t = A.tally_class("C4", items, {"C4.0": {"status": "supported", "claims": claims}}, {}, {})
    k = t["known"]
    assert k["added_paper_verdicts"] == {"unsupported": 1, "not_attributed": 1}
    assert k["added_paper_share_flagged"] == 1.0 and k["paragraphs_flagged"] == 0


def test_tally_c6_and_natural():
    items = [{"id": "C6.0", "deleted_sentence": "Onset was at 7 years."},
             {"id": "C6.1", "deleted_sentence": "Onset was at 9 years."}]
    om = {"finding": "onset at 7 years", "quote": "q", "quote_verified": True}
    done = {"0-2": {"results": {
        "C6.0": {"altered": {"error": None, "omissions": [om, om], "judge": [{"n": 1, "match": "full"}],
                             "mechanical": True, "mechanical_verified": True},
                 "control": {"error": None, "omissions": [], "mechanical": None, "mechanical_verified": None}},
        "C6.1": {"altered": {"error": None, "omissions": [om], "judge": [{"n": 1, "match": "partial"}],
                             "mechanical": False, "mechanical_verified": False},
                 "control": {"error": None, "omissions": [om], "judge": [], "mechanical": False,
                             "mechanical_verified": False}}}}}
    t = A.tally_c6(items, done)
    assert t["altered"]["deleted_sentence_listed_judge_full"] == 1
    assert t["altered"]["deleted_sentence_listed_judge_full_or_partial"] == 2
    assert t["altered"]["deleted_sentence_listed_mechanical"] == 1 and t["altered"]["mechanical_items"] == 2
    assert t["control"]["omissions_listed_mean"] == 0.5 and t["control"]["rate_judge_any"] == 0.0
    nat = {"chunks": {"0-1": {"results": {"1:a": {
        "error": None, "omissions": [om, {**om, "quote_verified": False}, om],
        "target_fact_ids": ["f1", "f2"], "fact_ids": ["f1", "f2", "f3"],
        "fact_marks": {"f1": {"stating": [2], "stating_part": []}, "f2": {"stating": [], "stating_part": [1]},
                       "f3": {"stating": [3], "stating_part": []}}, "n_draft_chars": 10}}}}}
    n = A.tally_natural(nat)
    assert n["target_facts"] == 2 and n["target_facts_listed"] == 1 and n["target_facts_listed_or_partly"] == 2
    assert n["target_facts_listed_with_verified_quote"] == 0
    assert n["omissions_matching_a_curator_fact"] == 2 and n["share_matching_incl_partly"] == 1.0


def test_budget_backend_stops_at_cap(tmp_path):
    from aiomim.llm import LLMLimitReached

    class Inner:
        def complete(self, **kw):
            return {}, {"cost_usd": 0.5, "input_tokens": 3, "output_tokens": 1}

    b = A.BudgetBackend(Inner(), tmp_path / "ledger.json", cap=2)
    b.complete(effort="medium")
    b.complete(effort="medium")
    with pytest.raises(LLMLimitReached):
        b.complete(effort="medium")
    led = json.loads((tmp_path / "ledger.json").read_text())
    assert led["calls"] == 2 and led["cost_usd"] == 1.0


def test_numbers_in_reads_words_and_thousands():
    assert A.numbers_in("two-point lod 2.11 in a 4-cM region; 1,012 patients, 3 sibs") == {"2", "2.11", "4", "1012", "3"}
    s = "A scan gave a maximum 2-point lod score of 2.11 for markers in a 4-cM region."
    assert A.mechanical_match(s, ["a maximum two-point lod score of 2.11 ... a 4-cM region"]) is True
    assert A.mechanical_match("The deletion removes 3 amino acids (Pro102_Val104del).",
                              ["The deletion removes 3 amino acids, p.P102-V104del."]) is True
