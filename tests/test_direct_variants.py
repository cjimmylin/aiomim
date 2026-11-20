"""The three variants of direct reading (D1 checklist, D2 completeness pass, D3 three-draft merge).

Offline: a scripted model and stubbed ontology and nomenclature services.
"""

from __future__ import annotations

import dataclasses
import json
import random
import re
import sys
import types
from dataclasses import dataclass

import pytest

from aiomim import synthesize
from aiomim.config import get_settings
from aiomim.llm import LLMRefusal, cache_key, schema_for
from aiomim.models import Paper, Seed
from aiomim.strategies import STRATEGIES, direct, direct_checklist, direct_complete, direct_ensemble
from aiomim.synthesize import DIRECT_SYSTEM, STYLE, DAllelicVariant, DEntry, DParagraph, DSection

SEED = Seed(mim="500001", prefix="#", title="LEBER OPTIC ATROPHY AND DYSTONIA", symbol="LDYT")


class FakeHPO:
    terms = {"HP:0001332": "Dystonia", "HP:0000648": "Optic atrophy"}

    def exact(self, text):
        return next((i for i, label in self.terms.items() if label.lower() == text.lower()), None)

    def search(self, text, k=10):
        return []

    def label(self, hpo_id):
        return self.terms.get(hpo_id, "")

    def is_phenotype(self, hpo_id):
        return hpo_id in self.terms

    def category(self, hpo_id):
        return "Neurologic"


@dataclass
class _Gene:
    symbol: str
    omim_id: str
    location: str


@pytest.fixture(autouse=True)
def stub_services(monkeypatch):
    hpo_module = types.ModuleType("aiomim.sources.hpo")
    hpo_module.get_hpo = lambda: FakeHPO()
    hgnc_module = types.ModuleType("aiomim.sources.hgnc")
    hgnc_module.normalize_symbol = lambda s: s.upper()
    hgnc_module.gene_info = lambda s: _Gene("MT-ND6", "516006", "mitochondria") if s.upper() == "MT-ND6" else None
    monkeypatch.setitem(sys.modules, "aiomim.sources.hpo", hpo_module)
    monkeypatch.setitem(sys.modules, "aiomim.sources.hgnc", hgnc_module)


def make_paper(pmid: str, year: int, author: str, fulltext: str | None = None) -> Paper:
    return Paper(pmid=pmid, title=f"Report {pmid}", authors=[f"{author} AB", "Jones CD", "Lee EF"], year=year,
                 journal="J Test", abstract=f"Abstract of {pmid}: three affected sibs had dystonia and optic atrophy. "
                                            "The 14459G-A transition was homoplasmic in all of them.",
                 fulltext=fulltext)


def papers() -> list[Paper]:
    body = ("FULL TEXT body. The proband was a 12-year-old girl of Turkish origin. Her parents were first cousins. "
            "The variant was absent from 200 control chromosomes. Fibroblasts showed reduced complex I activity. ") * 30
    return [make_paper("111", 1994, "Jun", body), make_paper("222", 1990, "Novotny"),
            make_paper("333", 2001, "Gropman")]


_PMID = re.compile(r'<paper pmid="(\d+)"')


def a_draft(pmids: list[str], extra: str = "", variant: str = "MTND6, ALA72VAL", hgvs=("m.14459G>A",)) -> DEntry:
    P = DParagraph
    return DEntry(
        intro=P(text="A number sign (#) is used with this entry because LDYT is caused by mutation in MT-ND6.",
                pmids=pmids[:1]),
        sections=[DSection(name="clinical_features", paragraphs=[
            P(text=f"Report {p} described affected members.{extra}", pmids=[p]) for p in pmids])],
        relationships=[synthesize.DRelationship(gene_symbol="MT-ND6", inheritance=["MT"], pmids=pmids[:1])],
        allelic_variants=[DAllelicVariant(gene_symbol="MT-ND6", name=variant, hgvs=list(hgvs), phenotype="LDYT",
                                          paragraphs=[P(text=f"Report {pmids[-1]} found the 14459G-A transition.",
                                                        pmids=[pmids[-1]])])],
        clinical_synopsis=[synthesize.DSynopsisItem(feature="dystonia", hpo_label="Dystonia", pmids=pmids[:1])],
    )


class ScriptedLLM:
    """Plays the writer, the completeness check, the revision and the merge."""

    def __init__(self, stop_stage: str | None = None, stop_check_pmid: str | None = None, omissions: bool = True):
        self.settings = get_settings()
        self.calls: list[tuple[str, str, str, str]] = []
        self.stop_stage, self.stop_check_pmid, self.with_omissions = stop_stage, stop_check_pmid, omissions

    def call(self, stage, system, prompt, output, **_):
        self.calls.append((stage, output.__name__, system, prompt))
        if stage == self.stop_stage:
            raise LLMRefusal("the model's safety filter stopped this reply")
        return getattr(self, f"_{output.__name__}")(stage, prompt)

    def map(self, stage, system, prompts, output, **_):
        out = []
        for p in prompts:
            try:
                out.append(self.call(stage, system, p, output))
            except Exception as exc:  # noqa: BLE001 - as LLM.map does
                out.append(exc)
        return out

    def _XChoices(self, stage, prompt):
        from aiomim.extract import XChoices
        return XChoices(choices=[])

    def _DEntry(self, stage, prompt):
        if stage == "revise":
            draft = DEntry.model_validate_json(re.search(r"<draft>\n(.*)\n</draft>", prompt, re.S).group(1))
            draft.sections[0].paragraphs[0].text += " The proband was a 12-year-old girl of Turkish origin."
            draft.relationships = []          # not allowed: must be carried over
            return draft
        return a_draft(_PMID.findall(prompt))

    def _XOmissions(self, stage, prompt):
        from aiomim.auditstress import XOmission, XOmissions
        pmid = re.search(r"PMID (\d+)", prompt).group(1)
        if pmid == self.stop_check_pmid:
            raise LLMRefusal("the model's safety filter stopped this reply")
        if pmid != "111" or not self.with_omissions:
            return XOmissions(omissions=[])
        return XOmissions(omissions=[
            XOmission(finding="The proband was a 12-year-old Turkish girl.",
                      quote="The proband was a 12-year-old girl of Turkish origin."),
            XOmission(finding="Something the paper does not say.", quote="This sentence is not in the paper."),
        ])

    def _EEntry(self, stage, prompt):
        E = direct_ensemble
        ids = re.findall(r"^\[(P\d+)\] \(cites .*?\) (.*)$", prompt, re.M)
        intros = [pid for pid, text in ids if text.startswith("A number sign")]
        report = {}
        for pid, text in ids:
            m = re.match(r"Report (\d+) described", text)
            if m:
                report.setdefault(m.group(1), []).append(pid)
        variant_paras = re.findall(r"^    \[(P\d+)\]", prompt, re.M)
        groups = re.findall(r"^\[(G\d+)\]", prompt, re.M)
        P = E.EParagraph
        paragraphs = [P(sources=pids, text=f"Report {pm} described affected members.") for pm, pids in report.items()]
        paragraphs[0].sources = paragraphs[0].sources[:-1]            # one source left out: not restored (cited elsewhere)
        paragraphs.append(P(sources=["P9999"], text="Invented, with no source."))
        paragraphs.append(P(sources=[report["222"][0]], text="x" * 5000))  # much longer than its source
        return E.EEntry(
            intro=P(sources=intros, text="A number sign (#) is used with this entry because LDYT is caused by "
                                         "mutation in MT-ND6."),
            sections=[E.ESection(name="clinical_features", paragraphs=paragraphs)],
            allelic_variants=[E.EVariant(group=groups[0], paragraphs=[P(sources=variant_paras, text="Merged.")])],
        )


# --------------------------------------------------------------------------- #
# Registry and stages
# --------------------------------------------------------------------------- #


def test_registered_with_their_stages():
    for name in ("direct_checklist", "direct_complete", "direct_ensemble"):
        assert name in STRATEGIES
    s = get_settings()
    assert (s.effort_for("complete"), s.effort_for("revise"), s.effort_for("merge_drafts")) == ("medium", "high", "high")


def test_direct_draft_is_the_baseline_call():
    """`direct.draft` makes exactly synthesize_direct's writer call, so the baseline's cached reply hits."""
    ps = papers()
    a, b = ScriptedLLM(), ScriptedLLM()
    synthesize.synthesize_direct(SEED, ps, a)
    direct.draft(SEED, ps, b)
    assert [c for c in a.calls if c[1] == "DEntry"] == [c for c in b.calls if c[1] == "DEntry"]


# --------------------------------------------------------------------------- #
# D1
# --------------------------------------------------------------------------- #


def test_checklist_changes_only_the_two_passages():
    assert direct_checklist.WHO_THEN_SALIENT in STYLE and direct_checklist.NO_PAD in STYLE
    sys_ = direct_checklist.CHECKLIST_SYSTEM
    assert "salient findings" not in sys_ and "Do not pad" not in sys_
    assert "consanguineous" in sys_ and "animal models" in sys_ and "population databases" in sys_
    restored = sys_.replace(direct_checklist.CHECKLIST, direct_checklist.WHO_THEN_SALIENT) \
                   .replace(direct_checklist.NO_PAD_NARROWED, direct_checklist.NO_PAD)
    assert restored == DIRECT_SYSTEM


def test_checklist_run_uses_the_direct_prompt(tmp_path):
    ps = papers()
    llm, base = ScriptedLLM(), ScriptedLLM()
    entry = direct_checklist.run(SEED, ps, llm, tmp_path)
    direct.draft(SEED, ps, base)
    (stage, _, system, prompt), = [c for c in llm.calls if c[1] == "DEntry"]
    (_, _, _, base_prompt), = [c for c in base.calls if c[1] == "DEntry"]
    assert (stage, system, prompt) == ("synthesize", direct_checklist.CHECKLIST_SYSTEM, base_prompt)
    assert entry.meta["strategy"] == "direct_checklist" and entry.sections


# --------------------------------------------------------------------------- #
# D2
# --------------------------------------------------------------------------- #


def test_complete_checks_every_paper_keeps_verified_omissions_and_revises(tmp_path):
    llm = ScriptedLLM()
    entry = direct_complete.run(SEED, papers(), llm, tmp_path)
    checks = [c for c in llm.calls if c[0] == "complete"]
    assert len(checks) == 3 and all(c[2] == direct_complete.COMPLETE_SYSTEM for c in checks)
    rec = entry.meta["direct_complete"]
    assert (rec["omissions_listed"], rec["omissions_kept"], rec["papers_failed"]) == (2, 1, [])
    (revise,) = [c for c in llm.calls if c[0] == "revise"]
    assert revise[2] == direct_complete.REVISE_SYSTEM
    # Only the paper with a kept omission is shown, and only the verified omission.
    assert _PMID.findall(revise[3]) == ["111"]
    assert "not in the paper" not in revise[3] and "Turkish" in revise[3]
    # What the revision may not change is carried over; the change is recorded.
    assert entry.relationships and rec["revision"]["relationships_changed"] is True
    assert rec["revision"]["sentences_added"] == 1
    assert any("Turkish origin" in p.text for p in entry.all_paragraphs())


def test_complete_without_kept_omissions_is_the_baseline(tmp_path):
    llm = ScriptedLLM(omissions=False)
    entry = direct_complete.run(SEED, papers(), llm, tmp_path)
    assert not any(c[0] == "revise" for c in llm.calls)
    base = synthesize.synthesize_direct(SEED, papers(), ScriptedLLM())
    assert [p.text for p in entry.all_paragraphs()] == [p.text for p in base.all_paragraphs()]


def test_complete_stopped_check_is_incomplete_and_stopped_revision_has_no_draft(tmp_path):
    from aiomim.compare import _papers_failed
    entry = direct_complete.run(SEED, papers(), ScriptedLLM(stop_check_pmid="222"), tmp_path)
    assert entry.meta["direct_complete"]["papers_failed"] == ["222"]
    assert _papers_failed(entry.meta) == ["222"]
    with pytest.raises(LLMRefusal):
        direct_complete.run(SEED, papers(), ScriptedLLM(stop_stage="revise"), tmp_path)


# --------------------------------------------------------------------------- #
# D3
# --------------------------------------------------------------------------- #


def test_salt_is_on_the_salted_wrapper_only():
    from aiomim.llm import LLM
    llm = LLM(dataclasses.replace(get_settings(), replicate=""))
    s2 = direct_ensemble.salted(llm, 2)
    assert s2.settings.replicate == "direct_ensemble-2" and llm.settings.replicate == ""
    assert s2.cache is llm.cache and s2.usage is llm.usage and s2.backend is llm.backend
    schema = schema_for(DEntry)
    plain = cache_key("m", "high", "sys", "prompt", schema)
    assert cache_key("m", "high", "sys", "prompt", schema, replicate="") == plain
    assert cache_key("m", "high", "sys", "prompt", schema, replicate=s2.settings.replicate) != plain
    nested = direct_ensemble.salted(LLM(dataclasses.replace(get_settings(), replicate="r2")), 3)
    assert nested.settings.replicate == "r2/ensemble-3"


def test_variant_groups_match_across_drafts():
    a = a_draft(["111"], variant="MTND6, ALA72VAL", hgvs=("m.14459G>A",))
    b = a_draft(["111"], variant="MT-ND6, 14459G-A", hgvs=("14459G>A", "p.Ala72Val"))
    c = a_draft(["111"], variant="MTND6, GLY10SER", hgvs=("p.Gly10Ser",))
    groups = direct_ensemble.variant_groups([a, b, c])
    assert sorted(map(sorted, groups)) == [[(0, 0), (1, 0)], [(2, 0)]]


def test_ensemble_merges_with_mechanical_citations(tmp_path):
    llm = ScriptedLLM()
    entry = direct_ensemble.run(SEED, papers(), llm, tmp_path)
    writers = [c for c in llm.calls if c[1] == "DEntry"]
    assert len(writers) == 3 and len({c[3] for c in writers}) == 1   # the same prompt three times
    (merge,) = [c for c in llm.calls if c[0] == "merge_drafts"]
    assert "<paper" not in merge[3]                                   # the merge never sees the papers
    rec = entry.meta["direct_ensemble"]
    m = rec["merge"]
    assert m["unknown_ids"] == 1 and m["unsourced_dropped"] == 1 and m["rejected_longer"] == 1
    assert m["restored"] == 0 and m["unused"] == 1                    # left out, but its paper is cited elsewhere
    assert not any("x" * 100 in p.text for p in entry.all_paragraphs())
    assert len(entry.allelic_variants) == 1 and entry.allelic_variants[0].paragraphs[0].pmids == ["333"]
    assert {p.pmids[0] for p in entry.sections[0].paragraphs} >= {"111", "222", "333"}


def test_ensemble_restores_a_paragraph_whose_paper_would_be_lost():
    drafts = [a_draft(["111", "222"]), a_draft(["111", "222"]), a_draft(["111", "333"])]
    groups = direct_ensemble.variant_groups(drafts)
    _, paragraphs = direct_ensemble.merge_prompt(SEED, papers(), drafts, groups)
    E = direct_ensemble
    plan = E.EEntry(intro=E.EParagraph(sources=["P1"], text="Intro."), sections=[], allelic_variants=[])
    merged, stats = E.assemble(plan, paragraphs, drafts, groups)
    assert direct.cited_in(merged) >= {"111", "222", "333"}
    assert stats["restored"] and stats["groups_restored"] == len(groups) and not stats["pmids_lost"]


def test_ensemble_with_a_stopped_draft_has_no_draft(tmp_path):
    class StopSalted(ScriptedLLM):
        def call(self, stage, system, prompt, output, **kw):
            if output is DEntry and self.settings.replicate:
                raise LLMRefusal("the model's safety filter stopped this reply")
            return super().call(stage, system, prompt, output, **kw)

    with pytest.raises(LLMRefusal):
        direct_ensemble.run(SEED, papers(), StopSalted(), tmp_path)


# --------------------------------------------------------------------------- #
# Runner: the audit subsample
# --------------------------------------------------------------------------- #


def test_audit_sample_is_the_designed_draw_and_is_never_redrawn(tmp_path, monkeypatch):
    import json

    from aiomim import directplus

    mims = [str(600000 + 7 * i) for i in range(41)]
    for m in mims:
        (tmp_path / m).mkdir()
        (tmp_path / m / "source.json").write_text(json.dumps({"source_run": "x", "mim": m}))
    monkeypatch.setattr(directplus, "run_dir_of", lambda name: tmp_path)
    chosen = directplus.draw_audit_sample("t", 20, 20261120)
    assert chosen == sorted(random.Random(20261120).sample(sorted(mims), 20))
    assert directplus.audit_sample(tmp_path) == set(chosen)
    assert directplus.draw_audit_sample("t", 20, 20261120) == chosen          # same draw: kept
    with pytest.raises(RuntimeError):
        directplus.draw_audit_sample("t", 20, 1)                               # another draw: refused


# --------------------------------------------------------------------------- #
# D4: the checklist draft, then the completeness pass
# --------------------------------------------------------------------------- #

FROZEN = {  # sha256 of the prompts frozen after the pilot; D2's cached replies depend on them
    "REVISE_SYSTEM": "d0c7c1e8d88e5f34629fa910fe904380c7d6e9d27b272a3c2cbfe95268b059cb",
    "CHECKLIST_SYSTEM": "230ad062e758ce3cf07ae127573f0167b84caa1c08ee6204e48031e68a23b5d0",
    "MERGE_DRAFTS_SYSTEM": "500db52ac702f5cb8fa116e03aba16bb30c1bcd59b94f6919bf537d137cef68f",
}


def test_frozen_prompts_are_unchanged():
    import hashlib
    got = {"REVISE_SYSTEM": direct_complete.REVISE_SYSTEM, "CHECKLIST_SYSTEM": direct_checklist.CHECKLIST_SYSTEM,
           "MERGE_DRAFTS_SYSTEM": direct_ensemble.MERGE_DRAFTS_SYSTEM}
    assert {k: hashlib.sha256(v.encode()).hexdigest() for k, v in got.items()} == FROZEN


def test_d4_revision_prompt_differs_from_d2s_only_in_the_house_style():
    from aiomim.strategies import direct_checklist_complete as d4
    style = direct_checklist.checklist_style()
    assert d4.REVISE_CHECKLIST_SYSTEM.endswith(style)
    assert d4.REVISE_CHECKLIST_SYSTEM.replace(style, STYLE) == direct_complete.REVISE_SYSTEM
    for word in ("reasoning", "think", "thought", "rationale", "explain"):
        assert word not in d4.REVISE_CHECKLIST_SYSTEM.lower()


def test_d4_starts_from_the_checklist_draft_and_runs_d2s_procedure(tmp_path):
    from aiomim.strategies import direct_checklist_complete as d4
    llm = ScriptedLLM()
    entry = d4.run(SEED, papers(), llm, tmp_path)
    (writer,) = [c for c in llm.calls if c[1] == "DEntry" and c[0] == "synthesize"]
    d1 = ScriptedLLM()
    direct_checklist.run(SEED, papers(), d1, tmp_path)
    (d1_writer,) = [c for c in d1.calls if c[1] == "DEntry"]
    assert writer == d1_writer                      # the very call D1 made, so its cached reply is read
    checks = [c for c in llm.calls if c[0] == "complete"]
    assert len(checks) == 3 and all(c[2] == direct_complete.COMPLETE_SYSTEM for c in checks)
    (revise,) = [c for c in llm.calls if c[0] == "revise"]
    assert revise[2] == d4.REVISE_CHECKLIST_SYSTEM
    rec = entry.meta["direct_checklist_complete"]
    assert entry.meta["strategy"] == "direct_checklist_complete" and "direct_complete" not in entry.meta
    assert (rec["omissions_listed"], rec["omissions_kept"]) == (2, 1)
    assert (tmp_path / "direct_checklist_complete.json").exists()
    assert not (tmp_path / "direct_complete.json").exists()   # D2's working file is never overwritten


def test_d4_completion_rules(tmp_path):
    from aiomim import directplus
    from aiomim.compare import _papers_failed
    from aiomim.strategies import direct_checklist_complete as d4
    entry = d4.run(SEED, papers(), ScriptedLLM(stop_check_pmid="333"), tmp_path)
    assert entry.meta["direct_checklist_complete"]["papers_failed"] == ["333"]
    assert _papers_failed(entry.meta) == ["333"]
    assert directplus.INCOMPLETE_KEY["direct_checklist_complete"] == "direct_checklist_complete"
    with pytest.raises(LLMRefusal):
        d4.run(SEED, papers(), ScriptedLLM(stop_stage="revise"), tmp_path)


def test_d4_cache_miss_raises_and_never_writes_a_draft(tmp_path):
    from aiomim.llm import LLM
    from aiomim.strategies import direct_checklist_complete as d4

    class NoCalls:
        def complete(self, **kw):
            raise AssertionError("a model call was made")

    llm = LLM(dataclasses.replace(get_settings(), home=tmp_path))   # an empty cache
    llm.backend = NoCalls()
    with pytest.raises(RuntimeError, match="direct_checklist"):
        d4.run(SEED, papers(), llm, tmp_path)


def test_ledger_caps_are_separate_for_the_extension(tmp_path):
    from aiomim import directplus
    from aiomim.llm import LLMLimitReached

    class Inner:
        def complete(self, **kw):
            return {}, {"cost_usd": 0.5, "input_tokens": 10, "output_tokens": 2}

    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"calls": 3, "cost_usd": 1.0, "input_tokens": 0, "output_tokens": 0,
                                  "safety_stops": 0, "refusals": 0, "errors": 0, "by_stage": {"high": 3}}))
    first = directplus.LedgerBackend(Inner(), ledger, None, 4)
    ext = directplus.LedgerBackend(Inner(), ledger, "direct_checklist_complete", 2)
    first.complete(effort="high")                        # the first four arms reach their cap of 4
    with pytest.raises(LLMLimitReached):
        first.complete(effort="high")
    ext.complete(effort="medium")                        # the extension has its own cap
    ext.complete(effort="medium")
    with pytest.raises(LLMLimitReached):
        ext.complete(effort="medium")
    data = json.loads(ledger.read_text())
    assert data["calls"] == 6 and data["extensions"]["direct_checklist_complete"]["calls"] == 2
    view = directplus.first_four_ledger(data)
    assert (view["calls"], view["cost_usd"], view["by_stage"]) == (4, 1.5, {"high": 4})
    assert "extensions" not in view


def test_completion_reads_d4s_failed_checks(tmp_path):
    from aiomim import directplus
    d = tmp_path / "600001"
    d.mkdir()
    for arm in directplus.ALL_ARMS:
        (d / f"eval.{arm}.json").write_text(json.dumps({}))
        meta = {"direct_checklist_complete": {"papers_failed": ["1"]}} if arm == "direct_checklist_complete" else {}
        (d / f"entry.{arm}.json").write_text(json.dumps({"meta": meta}))
    status = directplus.completion(tmp_path, ["600001"], directplus.ALL_ARMS)
    assert status["direct_checklist_complete"]["600001"] == "incomplete"
    assert all(status[a]["600001"] == "complete" for a in directplus.ARMS)
    assert set(directplus.completion(tmp_path, ["600001"])) == set(directplus.ARMS)   # the first four's view
