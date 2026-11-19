# Review of the paper draft, PaperOrchestra-style

19 November 2026. Subject: [`paper-draft.md`](paper-draft.md) as of commit `53abc25`.

[PaperOrchestra](https://arxiv.org/abs/2604.05018) (Google Cloud AI Research, 2026) improves a manuscript through a
Content Refinement step driven by simulated peer review, next to agents that own the literature review, the figures and
the numbers. This review applies those roles to the draft: three independent peer reviewers with different readerships,
a literature auditor, a numbers auditor and a figure critic, each working without sight of the others or of the authors'
view, followed by this meta-review. The reviewers could read the result files and the code, and most of their
criticisms cite a file. Their full reports are summarised here, not reproduced.

**Verdict.** Major revision. All three reviewers scored the paper 5 out of 10. They agree that the design, the
transparency and the access finding are valuable, and that several headline conclusions go beyond what was tested. Two
of the criticisms are errors in the analysis and change reported results; both have been reproduced (section 2).

## 1. Scores

| Reviewer | Originality | Quality | Clarity | Significance | Soundness | Presentation | Contribution | Overall | Decision |
|---|---|---|---|---|---|---|---|---|---|
| Methods and statistics (ML venue) | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 5 | Borderline |
| Clinical genetics (genetics journal) | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 5 | Major revision |
| Biomedical informatics | 2 | 2 | 3 | 3 | 2 | 3 | 2 | 5 | Major revision |

Sub-scores are out of 4, overall out of 10; every reviewer gave confidence 4 of 5.

Literature review, scored 0–100 on PaperOrchestra's six axes: coverage 20, relevance 70, critical synthesis 25,
positioning and novelty 40, organisation 45, citation rigor 35.

## 2. Errors found, and reproduced

These are not matters of framing. Each was checked against the files after the reviewers reported it.

1. **Stopped replies are handled unevenly, and that produces a headline result.** When a one-call strategy's writer is
   stopped the entry is excluded. When one per-paper extraction call is stopped in the evidence graph or the case table,
   the paper is dropped and the entry is still scored. Three evidence-graph entries and three case-table entries were
   scored that way. Comparing only the 93 entries that every reading strategy completed in full:

   | Against direct reading, OMIM facts conveyed | As reported (97 entries) | Symmetric rule (93 entries) |
   |---|---|---|
   | Agentic curator | −0.6 (−1.5 to +0.2) | −0.7 (−1.6 to +0.1) |
   | Evidence graph | −2.1 (−4.1 to −0.4) | −0.8 (−1.7 to +0.1) |
   | Case table first | −3.8 (−6.1 to −2.0) | −2.8 (−4.0 to −1.6) |

   The evidence graph is not distinguishable from direct reading. Counting a missing draft as zero over all 100 entries
   gives direct reading 51.3%, the agent 51.7%, the graph 51.0% and the case table 49.0%.
2. **Averages drop entries with no prediction.** F1 is undefined when a strategy predicts nothing, and such entries
   leave the mean. Memory-only named no gene on 13 of 97 entries; its 97.6% gene F1 is an average over 84. Counted as
   zero it is 84.5%. "The model nearly always knew the gene" is wrong.
3. **A naming bug writes frameshifts as missense changes.** The function that normalises protein changes reduces
   `Glu296LysfsTer` to `p.E296K`. The evidence-graph and case-table drafts print that key, and scoring matches variants
   on it. Direct reading and the agent are unaffected.
4. **The synopsis gold standard is misdescribed.** The draft says the HPO annotations are "derived from OMIM". About
   three quarters of them (1,948 of 2,566 in the local gold files) are the HPO team's own curation from papers, with a
   PubMed reference; only a quarter are OMIM-sourced.
5. **Statements that contradict the data or the code.**
   - "Recall-then-verify was as faithful as the reading strategies": it is 1.8 points lower (−3.3 to −0.4).
   - "Verification can only delete": the rewriter also restates partly supported claims and corrects contradicted ones.
   - "2,794 memory claims": that is over 100 entries; on the 97 compared it is 2,753.
   - "Thirty-three calls were stopped … 22, 9 and one": these sum to 32, and the 22 probably counts each case
     extraction twice.
   - "2,542 HPO annotations": that counts all aspects; 2,311 are phenotype annotations.
   - "21 (75%) passed screening": all 28 passed screening; 21 became proposals.
   - "A second set of twelve entries … drawn the same way": one creation-era band has no entry in it.
   - The gap table omits the 36 contradicted facts, so its rows do not sum.
   - Figure 1 and its caption say every strategy receives the papers and one repair round; the control does neither.
   - The evidence graph's inheritance is written by the model, not computed, contrary to the strengths table and README.

Apart from these, the numbers audit found that every cell of Tables 1–8 matches its source file.

## 3. Major issues

Ordered by how much each would change the paper. (a) rewording, (b) new analysis of existing data, (c) new experiment.

| # | Issue | Raised by | Fix |
|---|---|---|---|
| 1 | **The headline holds only at today's access.** 81% of papers were abstracts or titles, where every method has almost nothing to read. On full texts the case table trails direct reading by 11 points. The 35-point access contrast is between different papers and is confounded with era; the hidden-full-text experiment is the causal evidence and should lead. | All three | (a)+(b): stratified paired tables in the main text; conclusion conditioned on access |
| 2 | **The structured strategies were handicapped by choices that are not about structure.** Per-paper extraction ran at medium effort and the writers at high; the graph and table writers never see paper text; synopsis terms (and the case table's inheritance) come from fixed rules, which is what causes the over-listing and the inheritance failures. | Informatics | (c): matched ablation on 30–50 entries; otherwise (a): "our extract-then-write implementations" |
| 3 | **Every score is the model judging itself.** Fact splitting is redone for each draft; the planted-error test measures only sensitivity on easy edits; the adjudication uses the model that had already passed the same claims. | All three | (c): human-annotated sample; frozen fact list and re-score; a second judge model |
| 4 | **The gold standard is narrower than described.** "OMIM facts conveyed" is coverage of allelic-variant text from OMIM's gene entries. It is not the phenotype entry's narrative. Scope admits variants in other genes (an SPPL2A variant counts against every strategy in one entry). | Genetics, Methods | (a) rename and state scope; (b) restrict variant gold to the entry's genes |
| 5 | **Clinically important errors are invisible to the scores.** Variants are scored on recall only: the graph and case table list 110 and 137 variants not in OMIM against 40 for direct reading. HGVS names are never validated. A draft can be faithful to a paper that is itself wrong. Two disorders were merged in one entry. | Genetics | (b) variant precision, inheritance errors by type; (c) HGVS validation, error taxonomy with severity |
| 6 | **No curator has looked at any draft.** For a genetics readership this is the missing experiment: edit effort, error types and whether an entry could be published. | Genetics, Informatics | (c) blinded review of about 30 entries × 3 strategies by two curators |
| 7 | **Claims that OMIM is wrong are not yet defensible.** The corrections list has duplicates, one false lead, a renumbering difference and many abstract-only comparisons; the draft reports an earlier run of one strategy and omits the current run. | Genetics, Methods | (a) "leads"; (b) de-duplicate, report all; (c) curator confirmation before publication |
| 8 | **"Nine strategies" overstates the design.** There are three paradigms (read and write, extract then write, memory first), a control, and four add-ons each tested once against its parent. | Informatics | (a) restructure |
| 9 | **Three results are true by construction or underpowered.** Recall-then-verify may not add from the papers. The guide's search did not improve even its training entries, so its null says nothing about guidance. The large tier is 11 entries scored on about a fifth of their papers. | Informatics, Methods | (a) reword and move to exploratory; (c) only if they are to carry claims |
| 10 | **Novelty and related work.** One paragraph, ten links, no reference list. Four pieces of close work are missing: FlyAOC, GEN-KnowRD, Groza et al. 2026 and WikiCrow's evaluation. So are long-context-versus-retrieval, atomic-claim evaluation, LLM-judge validity, contamination, and the reference papers for OMIM, ClinVar, HPO, MedGen, Europe PMC and HGNC. | Literature auditor, Informatics | (a) a related-work section on the paper's own axes; narrowed novelty claim; numbered references |
| 11 | **Memory results are overstated.** Of its flagged claims 595 were unsupported by the cited papers and 22 contradicted. Unsupported is not wrong. Within abstract-only papers, direct reading's coverage also falls with era, so "does not depend on memorised text" is too strong. | Genetics, Methods | (a) report the two separately; (b) era × access table |
| 12 | **Statistics.** About 75 unadjusted comparisons; no primary endpoint; sign tests computed but not reported; percentile bootstrap on 11 entries; one run per entry. | Methods | (a)+(b): primary endpoint, medians and sign tests, correction; (c) replicate runs on a subset |
| 13 | **Reproducibility and licensing.** Tool version, per-stage effort, prompts, the commit behind each result folder, the reply cache, and the licences of redistributed abstracts and quotes are missing. A data-use statement for OMIM-derived text is a precondition. Generated entries imitate OMIM's form. | Informatics, Genetics | (a) throughout; mark generated entries as not OMIM |

## 4. Figures

- **No figure shows the central claim at one scale.** Build one: access levels as rows, strategies as dots, the
  hidden-full-text experiment beneath as the within-paper evidence.
- **One colour, one meaning.** The blue of direct reading is also "abstract only", "conveyed in full" and every bar of
  the second-hand figure. Keep the strategy colours for strategies in every figure.
- **The cost figure misleads.** It plots generation cost alone. By total cost, structure costs 1.3 times as much, not
  twice, and recall-then-verify is the cheapest method after the control.
- **Half the conclusion has no figure:** the large entries, the reconciled database, the learned guide, the verdicts by
  strategy, and the spread of entries behind each mean.
- Smaller defects: the design figure is wrong about the control; intervals are missing where bands hold 18–20 entries;
  some tick labels are below print size.

## 5. What the reviewers thought was good

- The controlled, paired design: same model, papers, guards, audit and scoring.
- The hidden-full-text experiment, called the best piece of causal evidence in the paper.
- The memory-only control by creation era.
- Mechanical guards that do not depend on a model: quote matching, ontology-constrained HPO terms, citation checks.
- Honest handling of null results, stopped replies and limitations.
- Cost split into generation, audit and scoring.
- The release of every draft, audit and score, which is what made this review possible.
- Several direct-reading drafts that a curator judged close to publishable.

## 6. Plan for improvement

**Tier 1: corrections that cost nothing.** New analysis of existing files and rewording.

1. Compare strategies only on entries each completed in full; report completion per strategy and a missing-as-zero
   sensitivity table.
2. Count an empty prediction as zero, and print the number of entries behind every mean.
3. Paired differences by access level in the main text; lead the access claim with the hidden-full-text experiment.
4. Add variant precision, inheritance errors by type, medians and sign tests; name OMIM facts conveyed as the primary
   endpoint.
5. Correct the gold-standard description and the statements listed in section 2.
6. Restructure as three paradigms, a control and four add-ons; move updates, open retrieval and adjudication to a
   supplement; narrow every claim that rests on an implementation choice.
7. Write a related-work section with a numbered reference list (47 verified candidates are in the audit).
8. Rebuild the figures around one headline figure and a consistent colour system.

**Tier 2: re-runs with the model, modest cost.**

9. Fix the frameshift naming and regenerate the evidence-graph and case-table drafts it touched.
10. Freeze one fact list per OMIM paragraph and re-score every strategy against it.
11. Matched ablation of the structured strategies: extraction at the writer's effort, the writer sees the text and
    chooses synopsis terms and inheritance.
12. Replicate runs of direct reading and the evidence graph on about 30 entries, for run-to-run and judge variance.
13. A test set of entries created after the model's training cut-off, if enough exist.

**Tier 3: needs people or other systems.**

14. Curator annotation of a stratified sample: fact coverage, audit verdicts including false flags, and blinded
    review of whole drafts for edit effort and error severity.
15. A second model family as writer and as judge.
16. One or two published systems run as they are (PaperQA2, SLIDERS), or an explicit statement that they were not.
17. A data-use statement agreed with OMIM, and curator confirmation of the candidate corrections.

**For ICLR specifically.** The reviewers' consensus score is below that venue's bar. The paper's general contribution
is not a ranking of curation methods; it is a controlled benchmark for evidence-grounded knowledge-base writing and
the finding that, when sources fit in context, access to the source dominates the choice of method. To be competitive
it needs tiers 1 and 2, more than one model, and human validation of the judges. Without those, a workshop or a
biomedical-informatics venue is the realistic target.

## Sources

[PaperOrchestra](https://arxiv.org/abs/2604.05018) · the literature audit's verified candidates, including
[FlyAOC](https://arxiv.org/abs/2602.09163), [GEN-KnowRD](https://pmc.ncbi.nlm.nih.gov/articles/PMC13060512/),
[Groza et al. 2026](https://pubmed.ncbi.nlm.nih.gov/41383021/),
[CGBench](https://arxiv.org/abs/2510.11985) and [long context versus retrieval](https://arxiv.org/abs/2407.16833).
