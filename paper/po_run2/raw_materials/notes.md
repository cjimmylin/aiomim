# Notes for the writing agents

## Venue and positioning

- Target: ICLR, main conference, written as a controlled empirical study with a benchmark. Double-blind: no author
  names, affiliations, acknowledgements, repository URLs or the name of this project's code package.
- The general contribution is a controlled comparison of strategies for evidence-grounded knowledge-base writing, and
  the finding about access to sources. The paper is not a ranking of curation tools and not a clinical tool.
- Frame the strategies as three paradigms (read and write; extract, then write; memory first), one control, and three
  add-ons each tested against its parent. Never present them as "nine strategies" of equal standing.
- Lead the access claim with the within-paper hidden-full-text experiment. The comparison across papers by access level
  is observational and confounded with entry creation date and journal; say so.
- Name OMIM facts conveyed, scored against fixed fact lists, as the primary endpoint. Everything else is secondary.
- Related work should be organised by the paper's own axes: (1) literature-to-knowledge-base curation in genetics and
  biology; (2) intermediate representation against long-context reading; (3) memory, verification and contamination;
  (4) supervision by prompt optimisation; and a paragraph on evaluation: atomic-claim checking, citation support and
  the validity of model judges.
- The closest prior work is FlyAOC (memorisation, pipeline and agent harnesses scored against FlyBase curators),
  GEN-KnowRD (generated rare-disease profiles compared with curated reports), WikiCrow (gene articles against
  Wikipedia) and Groza et al. 2026 (model memory of rare-disease genes and phenotypes). State the difference from each:
  here the cited papers are fixed, the reference is the curators' own text and structured fields, and the generation
  strategy is the only variable.

## Words to use

- "OMIM facts conveyed" means coverage of facts in OMIM's allelic-variant descriptions as deposited in ClinVar. These
  come from OMIM's gene entries and are variant-centred. Say this wherever the measure is introduced, and in the
  abstract say "curator-written per-paper text", not "the OMIM entry".
- The clinical-synopsis reference is the Human Phenotype Ontology's disease annotations. About three quarters of them
  are the HPO team's own curation from papers and about a quarter are taken from OMIM. Do not call them OMIM's synopsis.
- "Supported by the cited paper" is a judgement by the same model that wrote the draft. Say "judged supported".
- "Unsupported by the cited papers" is not "wrong". Report unsupported and contradicted separately.
- Say "our extract-then-write implementations" when a result may depend on implementation choices, and report the
  matched ablation beside it.
- Say "stopped by the model's safety filter" for replies the model interface cut short. The reasons are not visible.

## Claims the paper must not make

- Do not claim the method matters little in general. At current open access the reading strategies are close; where
  more full text is readable, differences grow. Report both.
- Do not claim the evidence graph conveys fewer facts than direct reading overall. Under the corrected analysis the
  difference is not distinguishable from zero.
- Do not present results on the large-entry tier as findings. It has about ten comparable entries, nearly all of whose
  papers are abstracts, and its fact score covers a minority of each entry's references. It is exploratory.
- Do not claim that verification after recall cannot help in general. The implementation tested may not add content
  from the papers; it restates, corrects or deletes.
- Do not claim that a learned guide does not help in general. The search was two reflection rounds on 27 entries and
  did not improve its own training entries.
- Do not claim that structure "pays when the database is the product". The case database was not validated against
  external per-patient ground truth. Reconciliation changed counts and no score.
- Do not claim OMIM is wrong anywhere. Disagreements between a draft and the reference were adjudicated by the same
  model and are unconfirmed leads; they may be mentioned in one sentence as such, with no entry named.
- Do not claim the audit establishes correctness. It checks fidelity to the cited text. A draft can faithfully copy a
  source's error, and the audit passes claims supported only by second-hand text.
- Do not claim the reading results are free of memorisation. The control shows memory contributes little for the
  newest entries; within abstract-only papers, coverage by reading also declines with creation date.
- Do not claim human validation of any kind. No curator has read any draft, verdict or fact judgement.
- Do not claim generality across models. One model family wrote, audited and judged everything.
- Do not promise experiments that were not run (other models, published systems run as released, curator studies).

## Limitations that must appear

- One model family for writing, auditing and judging; no human validation of the judges.
- The reference is indirect and narrow: variant-centred curator paragraphs, an ontology annotation set from two
  sources, and gene and inheritance tables. Narrative sections of entries are not compared.
- Oracle references: every strategy is given the curators' reference list. Finding the literature is tested only on
  ten entries.
- Open access only, and no supplementary material, where much variant and patient data in genetics papers lives.
- Variant names are not validated against reference sequences; inheritance is compared as coarse classes.
- Strategies were developed on the same entries they are evaluated on; there is no separate development set.
- Stopped replies remove entries, unevenly across strategies.
- Entries with a few references dominate; inputs too large for one prompt were not tested.
- Cost is at list price for one model.

## Ethics and data use

- The benchmark is built from public resources (NCBI, ClinVar, HPO, MedGen, Europe PMC, HGNC). Curator-written text is
  used for scoring and is not redistributed; released score files carry fact identifiers and statuses, not wording.
- Generated entries are drafts for expert review and are not clinical guidance. They must be marked as machine
  generated and not as OMIM content.
- Rights holders' terms of use for curated text apply to anyone rebuilding the reference.

## Added after the first review round (three further analyses; numbers are in the log)

- **Where the conveyed facts came from (log 3.1).** Every fact direct reading conveyed was checked against the text the
  writer had. Use it to answer "is coverage from abstracts reading or recall?": of facts conveyed in full from
  abstract-only or title-only papers, few are stated in no supplied text; most are stated in the paper's own abstract,
  some only in another supplied paper, and some only partly stated. Say "stated in no supplied text" (the fact may have
  been recalled, inferred or misjudged), not "recalled". Facts conveyed in part are more often outside the text; report
  that too. This is a model judgement. It does not make the reading results "free of memorisation".
- **Audit control (log 11).** The planted test's 60 paragraphs were re-audited unaltered with fresh calls. Report the
  result as the rate at which a re-audit flags a paragraph that had passed once. It is not a false-flag rate on
  arbitrary paragraphs, and omissions and misattributed citations remain untested.
- **Repair parity (log 6.2).** The full-text arm of the hidden-full-text experiment was also scored before the repair
  round, so all three arms can be compared without repair. Lead with whichever comparison is like for like and state
  the other.
- **Aggregation.** Say for every level whether it is pooled over facts or a mean over entries. The primary endpoint is
  the mean over entries; paired differences are means over entries; the by-access figures and the missed-fact and
  conveyed-fact attributions are pooled over facts. The hidden-full-text levels exist both ways (log 6.2).
- **2026 entries (log 10).** They were chosen by creation date alone, used in no other run, and no code that shapes
  how drafts are written, audited or repaired changed after their drafts were generated. They may be described as a
  sample not used in developing the strategies. Five strategies were run on them (not recall, then verify), 20 of 30
  entries are compared, and stopped replies are frequent there; say so.
- **Framing of the task and the reference.** Each strategy writes a whole entry, but the primary endpoint scores only
  what the draft says about each cited paper against variant-centred curator paragraphs. Do not let the title, abstract
  or introduction suggest that agreement with whole OMIM entries is measured.

## Added after the second review round (numbers are in the log)

- **Strategies compared on the facts the text states (log 2.10a).** Every fixed fact carries a stored judgement of
  whether the text available for its paper states it. On stated facts the reading strategies convey most of them and
  on facts not stated almost none; that contrast, with the hidden-full-text experiment, is the evidence that access
  bounds agreement. The comparison also answers the objection that the strategies look close only because most facts
  were unavailable: give the differences from direct reading on stated facts. Say that the restriction creates a
  ceiling of its own (most entries tie on abstract-only papers) and that the judgement of what the text states is the
  model's. The case table's deficit is larger on stated facts, most of all on full-text papers.
- **The ablation set and the main comparison (log 5, note).** The ablation reuses the main run's drafts for the
  unmodified strategies; where its estimate differs from the main comparison's access groups, the reason is which
  entries are averaged. For the evidence graph the sign of the difference from direct reading is not consistent
  across groups of entries. Do not present "the strategies separate where more full text is readable" as a finding
  for the reading strategies in general: what is consistent is that the case table falls behind where full text is
  readable; the across-entry comparison is observational.
- **Replicate noise is a yardstick, not a test.** The bootstrap interval over entries is the test of a difference.
  The replicate-noise half-width says how much a difference of that kind moves when generation, audit and scoring are
  repeated. Do not write "within" or "exceeds" the half-width as if it were a significance threshold.
- **The planted-error test is not a sensitivity estimate.** It shows that blunt single-value substitutions in
  paragraphs the audit had passed are caught; say so in those words.
- **Venue fit.** The paper is an evaluation and benchmark contribution: a controlled comparison of system designs for
  evidence-grounded generation, with measurement lessons that apply to evaluating such systems generally.

## Added after the second round of experiments (log section 14; design and deviations in the round's own document)

Three limitations become findings, each at small scale. Report them as such: 4 to 10 entries per experiment and 30
planted items per class show directions and large effects only. Say so once where the section starts.

- **Input size (log 14.2, controlled padding).** Within the same entries, papers and fixed fact lists, the input was
  grown with unrelated full-text papers to about 500,000 and about 1,200,000 characters (three prompts and a merge for
  direct reading). No strategy lost more than about a point; direct reading across several prompts lost nothing. Say
  that the added papers were off-topic and were ignored (no draft cited one; the agent opened few or none), so this
  tests input size, not crowding by relevant papers. Report direct reading's rise at both sizes with its intervals (it
  excludes zero at the first size); do not call it a gain, because the unpadded drafts are an earlier generation with
  no replicate, so the change mixes input size with run-to-run variation. The per-paper strategies lost added papers to stopped extraction calls; the reported table allows those
  losses, and under the symmetric completion rule only 2 entries remain. Do not claim that larger inputs do not matter
  in general.
- **Large real entries (log 14.1).** On four new entries with 76–148 references and much readable text, the model's
  safety filter stopped at least one strategy on every entry, so no new entry enters the comparison. This is a finding
  about completion: one-call strategies lose whole entries, per-paper strategies lose papers. The comparison on large
  sets of relevant papers remains untested; keep that as a limitation. The scored curator paragraphs cover only 5–10%
  of these entries' references.
- **Released systems (log 14.3).** Name them as run: "PaperQA2's document-query pipeline (without its agent)",
  "GraphRAG with local search" (global search secondary), "STORM". Give versions in the appendix. State in the main
  text: same papers and same model, reached through a local adapter; each system at one setting with its own code,
  prompts and defaults, changed only where integration required (table of changed settings in the appendix); our six
  section questions for the two question-answering systems; one small local embedding model; the model interface
  ignores temperature and length limits; PaperQA2's agent needs function calling, which the adapter does not provide;
  GraphRAG covers the first four entries of a seeded order that fitted the call budget; the strategies' drafts had
  been through the repair round and the systems' had not. Allowed claim: on these entries and settings, the released
  pipelines conveyed fewer curator-written facts than direct reading, the shortfall is on facts the supplied text
  states, they wrote more text at several to many times the cost, and fewer of their claims were judged supported;
  so the study's own implementations are not outperformed by released pipelines of these designs on this task at the
  settings tested. Do not claim a ranking of these systems in general, that they are poor systems, or anything about
  their published results. Only PaperQA2's comparison passes a test; GraphRAG's four entries cannot.
- **STORM.** It could not be run with this model: the model's safety filter stopped every chain-of-thought prompt of
  its research stage (its plain prompts were answered), so it produced no article. Nothing was reworded or retried.
  Do not say why the filter stopped them; the cause is not visible. It may be reported as a portability finding:
  released pipelines depend on the model behind them in ways a model-agnostic description hides.
- **Audit coverage (log 14.4).** Six classes of planted error, 30 items each, with unaltered controls. Report what is
  caught (citation swapped to a paper of another entry or of the same entry; a sentence moved between papers'
  paragraphs; a deleted negation) and what is not (an added irrelevant citation, which the audit cannot see because a
  claim takes the best verdict over its cited papers; a deleted count, zygosity or "one family", rarely; omissions, by
  construction). Say that the citation swaps are easy cases (the swapped paper is usually about something else) and
  that each qualifier rule has 2 to 8 items. Natural over-citation: give the share of (claim, cited paper) pairs in
  multi-citation paragraphs where the cited paper does not support the claim, with the caveat that entries the
  repair round changed are excluded. The completeness check recovers part of planted and real omissions and lists
  many items the curators did not record; it and its judge are the same model. The audit still checks fidelity to the
  cited text, not correctness.
- **Limitations after this round.** Keep (i) one model family / no human validation unchanged and first. Rewrite the
  input-size item: size alone was tested by padding with unrelated text; large sets of relevant papers could not be
  compared because of stopped replies. Rewrite the audit item: over-citation, broadened claims and omissions are not
  caught; the stress test is small. Add: released systems were run at one setting each, PaperQA2 without its agent,
  STORM not at all.

## Added for the next version (improving on direct reading, log section 15)

- **What may be claimed.** On held-out entries that have at least one paper readable in full (41 entries; 38 or 35
  compared, by the symmetric completion rule): the completeness pass and the checklist with the completeness pass
  convey more curator facts than direct reading, the gain comes from facts the supplied text states (most on full-text
  papers), facts the text does not state do not change, and claims judged supported do not fall. Give the intervals,
  better/worse/tied and sign tests from the log, and say which comparison set each figure comes from (38 entries for the
  first four arms, 35 for the five-arm comparison).
- **The merge of three drafts.** Its gain is partly on facts the supplied text does not state, and it has more
  unsupported and contradicted claims and lower variant precision. Do not present it as an improvement in fidelity;
  say that sampling and merging brings in content the papers do not support.
- **The checklist.** A small gain whose interval excludes zero but whose sign test does not reach 0.05 after Holm
  adjustment. Combined with the completeness pass it adds little over the completeness pass alone (interval includes
  zero). Say the two overlap.
- **Scope.** The arms were designed after the main study, on the same model; prompts were written on three training
  entries and frozen before the held-out entries were run; the combined arm was designed after the other four had run.
  No arm was tested on entries without full text; on abstract-only papers no arm moved coverage by more than about a
  point. The gains are of the size the headroom analysis allowed for reading better (a few points), far below what
  access to full text adds. Extra calls cost entries to stopped replies (3 and 6 of 41 for the two completeness arms,
  none for direct reading); report completion.
- **Free-to-read papers.** The approach with the largest expected effect, reading the papers that are free to read but
  not openly licensed (about a third of curator facts concern them), was not tested: the project uses only openly
  licensed text. It may be stated as the largest remaining lever, with the log's figures, not as a result.
- **Adoption.** The pipeline now uses the checklist with the completeness pass by default where a paper is readable in
  full. That is a project decision; the paper may mention it in the reproducibility statement but must not present it
  as a finding.
- **Still not done.** No second model family has been run (an OpenAI study is designed but has not been run: do not
  mention it as planned work or report anything from it), and no human has validated any judgement. These stay first
  among the limitations.
- **Figures.** Every figure must be legible at the width it is printed (no text below 7 pt), use one colour per
  strategy consistently across figures, and carry no text that belongs in the caption.

## Added after the first review of the next version (draft v0 of run 2; numbers are in the log)

- **Stopped entries in the reading-better arms (log 15.1, added after this review, not pre-specified).** On all 41
  entries, with the entries the completeness-pass arms lost to a stopped revision put back: if the draft the revision
  would have revised is scored in their place (what the adopted default does), the checklist with the completeness
  pass conveys 3.1 points more than direct reading (+1.8 to +4.3; 32/7/2) and the completeness pass alone 2.4 (+1.5 to
  +3.4); if a lost entry counts as zero, the two arms as evaluated are below direct reading on the mean (−4.8 and
  −3.5, intervals including zero) although they are better on more entries. Say both, and say that the gain depends
  on keeping the draft when the revision is stopped. Label the analysis as added after review.
- **Scope the strategy claim.** "No other design conveyed more than direct reading" holds at the main comparison's
  settings only. State in the main text, where the settings are introduced (not only in an appendix), that per-paper
  extraction ran at medium effort and synopsis terms were assigned by rule in the main comparison. The supported claim:
  the designs differ by a few points either way, which design is ahead depends on the entries compared and, for the
  case table, on settings, and every such difference is small against the effect of access to full text. (Corrected
  after the review of v1; see the next item.)
- **What the ablation shows (log 5; corrected after the review of v1).** The ablation reuses the main run's drafts on
  38 entries chosen with more full text. On those entries, at the main settings, the evidence graph was already +1.0
  against direct reading (−0.8 to +2.9) and the case table −2.3; in the main run on all 93 entries they were −0.5 and
  −1.9. Matching the settings moved the case table by +2.1 (+1.1 to +3.2; 25/8) but the evidence graph by only +0.8
  (−0.5 to +2.1; 18/12). So the matched evidence graph's +1.8 (+0.4 to +3.3) against direct reading is mostly an
  entry-set difference, not a settings effect: do not headline it, and do not put it in the abstract or the
  introduction as a settings result. The clear settings effect is the case table's. Within the main run the evidence
  graph's sign also depends on the entries (log 5: −1.2 on the ablation's entries with half or more full text, +3.1 on
  the others).
- **The case table's deficit.** Its interval excludes zero but its sign test does not reach 0.05, the five
  comparisons with direct reading are not adjusted, and counting missing drafts as zero gives an interval including
  zero (log 2.3a, 2.4). Call it suggestive. The restriction to facts stated in full-text papers (log 2.10a) was added
  after the first results, not specified in advance: say so wherever it is used, and do not call it "the stronger
  evidence".
- **The access claim.** Let the hidden-full-text experiment carry it (the within-paper comparison). The stated /
  not-stated split is consistent with it but partly by construction: "stated" needs a quote the model found, so facts
  that need inference are more likely classed as not stated. Say this in one sentence where the split is shown.
- **Released systems.** Remove them from the introduction's list of findings and contributions. Keep one short
  paragraph in the results (what was run, on how many entries, the caveats in the earlier note) and the detail in the
  appendix.
- **Recall, then verify.** Its writer adds nothing from the papers, so its low coverage is by construction. Present it
  as the memory-first paradigm's verified variant and say what it shows (how much of memory survives verification),
  not as a competitor on coverage.
- **Reuse of the benchmark.** The fixed fact lists contain curator wording and are not redistributed. A new strategy
  can be scored against the same denominators only by someone who rebuilds the reference under the rights holder's
  terms and re-splits it. How much a fresh split by the same procedure moves levels was not measured; a different
  procedure (splitting afresh for each draft, log 4.4) ran 2–5 points higher with the same ordering. Differences
  measured within one split are the comparable quantity. Say this plainly in the benchmark description and the limitations.
- **Title.** At most two lines. It must not claim more than is measured: the endpoint is facts from variant-centred
  curator paragraphs about the cited papers, not whole knowledge-base entries.
- **Presentation (all three reviewers).** Put the definitions a reader needs (fact, conveyed and partly conveyed,
  stated in the supplied text, pooled over facts versus mean over entries, completion and the symmetric rule, repaired
  versus unrepaired drafts) in one place in the method section. Separate pre-specified results from exploratory and
  post-hoc ones, and label the latter. Runs on 10 or fewer entries go to the appendix with one sentence each in the
  main text. In prose, give one estimate with its interval per claim and leave the rest to tables. Fewer, plainer
  sentences; no claim should need more than one hedge.
- **Patterns the log shows but does not explain** (e.g. direct reading's lower coverage in the oldest creation band).
  Mention them only as observed; do not invent explanations.
- **Not done, and not to be promised:** no human validation of any judgement, no judge or writer from a second model
  family, no comparable large-entry results. These remain the first limitations. Say what each would establish.

## Added after the review of v1 of run 2 (numbers are in the log)

- **Length.** The primary endpoint counts facts conveyed and has no length or precision counterpart. The
  reading-better drafts are longer (log 15, size table); the extract-then-write drafts carry more audited claims (log
  2). Report draft length beside every coverage gain and say the endpoint rewards recall. The share of claims judged
  supported is the only precision-side check, and for the reading-better arms it rests on 20 audited entries with no
  interval: say "did not fall on the 20 audited entries", not "without lowering".
- **No equivalence claims.** "Not distinguishable" is not "equivalent". Do not write anything in the abstract or
  introduction that reads as equivalence (e.g. "not distinguishable from reading all papers in one prompt" needs the
  interval and the entry count next to it, or should be dropped from the abstract).
- **Forking paths.** List, in one place in the method section, every analysis choice made after results were seen:
  fixed fact lists replacing per-draft splitting; the symmetric completion rule (adopted after a first analysis had
  put the evidence graph 2.1 points behind; log 12); the matched ablation; the stated /
  not-stated restrictions; the widened claim-selection rule for deleted qualifiers; the D4 arm (designed after the
  other reading-better arms' held-out results were seen, then evaluated on the same held-out entries); the
  stopped-entry sensitivity (log 15.1). Say which results are pre-specified (the main comparison's primary endpoint
  on the symmetric set; the hidden-full-text experiment; D1–D3 against the baseline).
- **"Held-out".** Say what each held-out set was held out from: the 2026 entries from all development; the
  reading-better test split from the design of the reading-better prompts and from guide learning, but not from the
  development of the main strategies.
- **Scope of the reference (log 1.1, added after this review).** 327 of the 515 cited papers have an in-scope curator
  paragraph (81 of 96 read in full, 221 of 345 abstract only, 25 of 74 title only); what a draft says about the other
  papers is not scored. Say this where the reference is introduced.
- **Hidden papers (log 6.2, added after this review).** The experiment used the 49 entries with a full-text paper
  that an in-scope curator paragraph is about and hid all 91 of their full-text papers; the other 5 full-text papers
  have no in-scope paragraph, so hiding them could not change the score.
- **Internal consistency.** The planted-error test has the classes and item counts of the log (14.4): do not call
  negation a class of its own if it is one of the qualifier-deletion rules. Every "–" in a table needs a footnote
  saying why (not computed, not applicable, or not in the log).
- **Released systems.** They carry no claim in the main text; one sentence there pointing to the appendix is enough.
- **Title.** Say what the task is in words an ML reader understands (writing knowledge-base entries from cited
  papers, scored on curators' per-paper facts), in at most two lines.
- **Terms.** Replace project jargon in the main text with plain words or define each once: "like for like" (same
  entries and same repair state), "stopped reply" (the model's safety filter ended the reply), "unrepaired" (before
  the repair round), "completes" (writes a draft with every paper processed).
