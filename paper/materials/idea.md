# Idea summary

## Problem

Curated knowledge bases are written by experts who read papers and record, entry by entry, what each paper showed.
OMIM, the reference catalogue of human genetic disorders, is the example studied here: about 7,000 phenotype entries
with a known molecular basis, each built from the papers a curator chose to cite. Language models can now read those
papers, and many system designs have been proposed for turning a set of documents into structured, cited text:
reading everything in one long context, extracting into a knowledge graph or a table first, letting an agent decide
what to read, drafting from the model's memory and verifying afterwards, and optimising prompts from examples.

These designs have been evaluated on different tasks, with different models, retrieval stacks and scoring, so their
results cannot be compared. Three questions are open for evidence-grounded knowledge-base writing:

1. With the model, the sources, the guards and the scoring held fixed, how much does the generation strategy matter?
2. What limits agreement with what experts wrote: the strategy, or what the strategy was given to read?
3. Which errors does a claim-level audit against the cited source catch, and which can it not see?

## Core idea

A controlled benchmark in which the generation strategy is the only thing that varies.

- **Task.** Given an entry's header (number, title, alternative titles) and exactly the papers the curators cited,
  with the causal gene withheld, write the entry: narrative paragraphs each citing papers, a gene and inheritance
  table, a clinical synopsis as ontology terms, and a list of allelic variants.
- **Reference.** A gold standard assembled from public sources that carry curator-written content: curator prose about
  individual papers, a clinical synopsis as Human Phenotype Ontology terms, the causal gene, the mode of inheritance
  and the allelic variants.
- **Strategies as controlled variables.** One model writes every draft. Strategies fall into three paradigms, a
  control, and add-ons each tested against its parent:
  - *Read and write*: all papers in one prompt (direct reading); the same with read and search tools (agentic curator).
  - *Extract, then write*: quote-backed findings per paper joined into an evidence graph; one record per reported
    patient or family pooled into a case table.
  - *Memory first*: a draft from the model's memory, then checked against the papers and rewritten from what survives.
  - *Control*: the memory draft alone, with no papers.
  - *Add-ons*: second-hand evidence for papers that cannot be read in full (passages from later open-access papers
    that describe them); reconciliation of the case table (merging the same patient, family or variant across papers);
    a curation guide learned from the omissions and extras of a training split.
- **One audit for every draft.** Each paragraph is split into atomic claims attributed to the papers it cites; each
  claim is judged against each cited paper with a supporting quote that must occur in the paper; flagged claims get one
  repair round.
- **One scoring for every draft**, against the gold standard, with the same fixed list of facts for every strategy.
- **Access as an experimental variable.** Papers are readable in full, as an abstract, or as a title only, depending on
  open access. A within-paper experiment hides the full text of papers that have one, so the effect of access is
  measured on the same papers and not only across different ones.

## Formal setup

- An entry is `e = (h, R)` with header `h` and references `R = {d_1, …, d_n}`. Each paper has an access level
  `a(d) ∈ {full text, abstract, title}`.
- A strategy `S` maps `(h, R)` to a draft `D`: paragraphs `p`, each citing a non-empty subset of `R`; a set of genes;
  a set of inheritance modes; a set of ontology terms; a set of variants.
- **Completion.** `S` completes `e` when every model call it needs returns a usable reply. A draft may be missing (the
  writer's reply was stopped) or incomplete (a per-paper call failed). Strategies are compared only on entries that
  every compared strategy completed, and completion is reported as an outcome.
- **Faithfulness.** The audit splits `D` into atomic claims `c`, each attributed to papers `R(c) ⊆ R`. A verdict
  `v(c, d) ∈ {supported, partly supported, unsupported, contradicted}` is given for each `d ∈ R(c)`, and the claim's
  verdict is the best over `R(c)`. Faithfulness is the share of claims supported; the error rate is the share
  unsupported or contradicted, before and after repair.
- **Coverage of curator-written facts (primary endpoint).** For each curator paragraph `g` about cited papers, a list
  of atomic facts `Φ(g)` is produced once, without sight of any draft, and reused for every strategy. Each fact is
  marked present, partly present, absent or contradicted in what `D` says about those papers. Coverage is
  `(present + ½ partial) / |facts judged|`.
- **Structured fields.** Precision, recall and F1 of ontology terms (exact, with ancestors, and by semantic
  similarity); recall and precision of allelic variants; F1 of the causal gene; agreement of the inheritance modes. A
  strategy that predicts nothing where the gold set is non-empty scores zero.
- **Comparison.** Paired differences between strategies over entries, with a bootstrap 95% interval over entries, the
  median difference, an exact sign test, and Holm correction across secondary measures.

## Contributions

1. A benchmark and open harness for evidence-grounded knowledge-base writing against curator-written references,
   built only from public sources, with a claim-level audit, fixed fact lists and per-entry release of every draft,
   verdict and score.
2. A controlled comparison of three paradigms, a control and four add-ons under one model, with completion, variance
   between repeated runs and matched ablations of the extract-then-write strategies reported.
3. Evidence that access to the source, not the strategy, bounds agreement with curators at current open access,
   including a within-paper experiment, and that differences between strategies grow as more full text is readable.
4. A characterisation of what the audit can and cannot see: it removes unsupported claims and catches planted errors,
   but it passes claims supported only by a later paper's description of the cited paper, and it checks fidelity to
   the source, not correctness.
5. A memory-only control by entry creation date as a contamination check, and negative results for
   verify-after-recall, for a learned curation guide and for reconciliation at this entry size.

## Design rationale

- **Why OMIM.** Entries cite their sources explicitly; curator prose about individual papers, a clinical synopsis,
  genes, inheritance and variants are all available from public resources; entries span decades, which gives a
  natural gradient of how well the model already knows them.
- **Why withhold the gene.** Naming the causal gene from the papers is part of the curator's task.
- **Why one model.** Holding the model fixed isolates the strategy. It also limits generality; that is stated.
- **Why a memory-only control.** Curated knowledge bases are public and models have seen them. The control measures
  what memory alone supplies, by when the entry was created.
- **Why mechanical guards.** Ontology identifiers are never written by the model; the model chooses among candidates
  returned by an ontology search. Quotes are matched against the paper text. Citations must point at supplied papers.
  Cross-reference numbers recalled from memory are removed. These apply to every strategy.
- **Why fixed fact lists.** Splitting the reference paragraph afresh for each draft lets the split adapt to the draft
  and gives different denominators to different strategies.
- **Why treat stopped replies as an outcome.** The model's safety filter stops some replies. A strategy that makes one
  call per entry loses the whole entry; a strategy that makes one call per paper loses a paper. Scoring the second and
  excluding the first biases the comparison.
