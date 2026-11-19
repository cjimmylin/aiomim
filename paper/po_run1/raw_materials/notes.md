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
