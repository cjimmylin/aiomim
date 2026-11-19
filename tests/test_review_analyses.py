"""Pure parts of three reviewer analyses: conveyed facts by source, the unaltered audit control,
and the repair round's reach in the hidden-full-text experiment. No network, no model."""

from __future__ import annotations

import json

from aiomim.auditcheck import control_tally
from aiomim.gaps import classify_conveyed, headline_conveyed, tally_conveyed
from aiomim.secondhand import cached_revisions, repair_tally


def test_classify_conveyed():
    assert classify_conveyed("yes", None) == "stated"
    assert classify_conveyed("partly", "no") == "partly_stated"
    assert classify_conveyed("partly", "partly") == "partly_stated"
    assert classify_conveyed("partly", "yes") == "stated_elsewhere"
    assert classify_conveyed("no", "yes") == "stated_elsewhere"
    assert classify_conveyed("no", "partly") == "partly_elsewhere"
    assert classify_conveyed("no", "no") == "not_in_supplied_text"
    assert classify_conveyed("no", "no_other_papers") == "not_in_supplied_text"
    assert classify_conveyed("partly", "no_other_papers") == "partly_stated"
    assert classify_conveyed("no", "unjudged") == "unjudged"
    assert classify_conveyed("unjudged", None) == "unjudged"


def _fact(status, own, other=None):
    return {"draft_status": status, "own": own, "other": other,
            "class": classify_conveyed(own, other if own != "yes" else None)}


def test_tally_and_headline_conveyed():
    paragraphs = [
        {"content_level": "abstract", "facts": [_fact("present", "yes"), _fact("present", "no", "no"),
                                                _fact("partial", "partly", "no"), _fact("present", "no", "yes")]},
        {"content_level": "title", "facts": [_fact("present", "no", "no_other_papers")]},
        {"content_level": "fulltext", "facts": [_fact("present", "no", "no")]},
    ]
    t = tally_conveyed(paragraphs)
    assert list(t) == ["fulltext", "abstract", "title", "all"]
    a = t["abstract"]
    assert a["present"]["n"] == 3 and a["partial"]["n"] == 1 and a["conveyed"]["n"] == 4
    assert a["present"]["class"]["not_in_supplied_text"] == 1
    assert a["conveyed"]["other_given_own"]["no"] == {"yes": 1, "partly": 0, "no": 1, "no_other_papers": 0,
                                                      "unjudged": 0}
    assert t["all"]["conveyed"]["n"] == 6
    h = headline_conveyed(t)
    # Abstract and title only: present facts 4, of which 2 in no supplied text; full text left out.
    assert h["present"]["n_judged"] == 4 and h["present"]["not_in_supplied_text"] == 2
    assert h["present"]["share_not_in_supplied_text"] == 0.5
    assert h["conveyed"]["at_most_partly_in_supplied_text"] == 1
    # Counts only: nothing in the tally carries wording.
    assert "fact" not in json.dumps(t).replace("facts", "")


def test_control_tally():
    t = control_tally([["supported", "supported"], ["supported", "unsupported", "partially_supported"],
                       ["contradicted", "not_checkable"], ["partially_supported"]])
    assert t["paragraphs"] == 4 and t["paragraphs_flagged"] == 2
    assert t["claims_audited"] == 7 and t["claims_not_checkable"] == 1
    assert t["claims_flagged"] == 2 and t["claims_unsupported"] == 1 and t["claims_contradicted"] == 1
    assert t["claims_partly_supported"] == 2 and t["paragraphs_with_partly_supported"] == 2
    assert t["paragraph_flag_rate"] == 0.5 and t["claim_flag_rate"] == round(2 / 7, 4)
    assert control_tally([])["paragraph_flag_rate"] is None


def _entry(mim, flagged_claims, flagged, located_hidden, revised=None, located=None):
    revised = flagged if revised is None else revised
    return {"mim": mim, "claims_before_repair": 100, "claims_flagged_before_repair": flagged_claims,
            "claims_unsupported_before_repair": flagged_claims, "claims_contradicted_before_repair": 0,
            "claims_not_checkable_before_repair": 0, "paragraphs_flagged": flagged, "paragraphs_revised": revised,
            "paragraphs_deleted": flagged - revised, "claims_after_repair": 100,
            "claims_after_repair_in_hidden_paragraphs": 60,
            "revised_located": revised if located is None else located, "revised_located_citing_hidden": located_hidden}


def test_repair_tally():
    t = repair_tally([_entry("1", 3, 2, 2), _entry("2", 1, 1, 0), _entry("3", 0, 0, 0),
                      _entry("4", 2, 2, 1, located=1)])
    assert t["entries"] == 4 and t["entries_repaired"] == 3
    assert t["claims_before_repair"] == 400 and t["claims_flagged_before_repair"] == 6
    # Only entry 1 has every flagged paragraph located and citing a hidden paper.
    assert t["claims_flagged_in_hidden_paragraphs"] == 3
    assert t["entries_not_fully_located"] == ["4"]


def test_cached_revisions_recognises_repair_replies_by_shape(tmp_path):
    (tmp_path / "ab").mkdir()
    (tmp_path / "ab" / "ab1.json").write_text(json.dumps(
        {"data": {"paragraphs": [{"paragraph_id": "x.1", "text": "Revised."}]}, "meta": {}}))
    (tmp_path / "ab" / "ab2.json").write_text(json.dumps({"data": {"paragraphs": [{"paragraph_id": "x", "claims": []}]}}))
    (tmp_path / "ab" / "ab3.json").write_text("not json")
    assert cached_revisions(tmp_path) == [[{"paragraph_id": "x.1", "text": "Revised."}]]


def _row(present, partial, absent, ids=None):
    n = present + partial + absent
    facts = [{"id": f"k.{i}", "status": s} for i, s in
             enumerate(["present"] * present + ["partial"] * partial + ["absent"] * absent, 1)]
    return {"facts": facts, "n_facts": n, "n_judged": n, "unjudged": 0, "present": present, "partial": partial,
            "absent": absent, "contradicted": 0}


def test_pool_before_repair_pairs_unrounded_and_checks_unchanged_marks(tmp_path):
    from aiomim.secondhand import BEFORE_REPAIR_FILE, FROZEN_FILE, pool_before_repair

    def write(mim, abstract, after, before, changed):
        out = tmp_path / mim / "secondhand_check"
        out.mkdir(parents=True)
        (out / FROZEN_FILE).write_text(json.dumps({"paragraphs": [
            {"abstract": a, "secondhand": a, "fulltext": f} for a, f in zip(abstract, after)]}))
        (out / BEFORE_REPAIR_FILE).write_text(json.dumps({"paragraphs": [
            {"changed": c, "before_repair": b} for b, c in zip(before, changed)]}))

    # Entry 1: repair changed nothing; entry 2: one paragraph changed and lost a fact.
    write("1", [_row(1, 0, 2)], [_row(2, 0, 1)], [_row(2, 0, 1)], [False])
    write("2", [_row(0, 0, 3), _row(1, 0, 2)], [_row(3, 0, 0), _row(1, 1, 1)], [_row(3, 0, 0), _row(1, 0, 2)],
          [False, True])
    frozen = {"per_entry": [{"mim": "1", "paragraphs": 1, "abstract": 0.3333, "fulltext": 0.6667},
                            {"mim": "2", "paragraphs": 2, "abstract": 0.1667, "fulltext": 0.75}]}
    b = pool_before_repair(tmp_path, frozen)
    assert b["n_entries"] == 2 and b["n_paragraphs"] == 3 and b["paragraphs_with_changed_draft_text"] == 1
    assert b["unchanged_paragraphs_with_different_marks"] == 0
    assert b["pooled"]["present"] == 6 and b["pooled"]["n_judged"] == 9
    rep = b["paired"]["after_minus_before_repair"]
    # Rounded per-entry values must not turn an unchanged entry into a "better" one.
    assert (rep["better"], rep["worse"], rep["ties"]) == (1, 0, 1)
