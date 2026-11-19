# Approaches for generating OMIM-style entries from literature: survey, ranking and token estimates

Prepared 2026-11-19 for the methods-comparison paper. It covers SLIDERS and DataSTORM (Stanford) and fifteen other
published approaches, alongside the six strategies already implemented in this repository.

**How far to trust each part.** Descriptions and reported figures come from the papers and repositories listed under
Sources; the ones marked ✓ I re-read in the primary source, the rest were read there by a research assistant and not
re-checked. The rankings are my judgement, not a measurement: only the six strategies in section 2 have been run on
OMIM entries. The token estimates in section 5 are order-of-magnitude models built from each system's described call
structure, calibrated on our own measured runs; expect them to be off by up to a factor of two either way.

## 1. The task and its size

Measured on the 100-entry evaluation set (515 papers):

| | Tokens |
|---|---|
| A paper readable in full (96 papers) | 8,700 mean, 31,600 max |
| A paper with abstract only (345) | 330 |
| A paper with title only (74) | 23 |
| Source text per entry | 9,500 mean, 5,100 median, 44,500 max |

At OMIM's scale: 6,953 phenotype entries have a gene-map gene. In a random sample of 300 of them the reference list
has a median of 3 papers and a mean of 10.6 (90th percentile 25, maximum 256). 17% of entries have more than 12
references, and those entries hold 72% of all references. So most entries are small enough for any method, and most of
the literature sits in the few entries that are not. Extrapolating, the whole set is about 74,000 references: roughly
140 million tokens at today's mix of full text and abstracts, or 640 million if every paper were readable in full.

Three scenarios are used for the estimates below:

| Scenario | Papers | Source tokens |
|---|---|---|
| **A** — an average entry as run here | 5 | 9,500 |
| **B** — the same entry with every paper in full text | 5 | 45,000 |
| **C** — a large entry | 100, full text | 870,000 |

## 2. What is already implemented and measured

All six take the same papers and produce the same entry format, so they share one audit and one scoring. Tokens are
for generation only, measured on one entry of 5 papers and 24,000 source tokens (MIM 620249). The audit that follows
is the same procedure for every strategy and cost about 78,000 input and 35,000 output tokens on that entry: more
than any strategy's generation except the agent's cumulative input.

| Strategy | What it does | Generation tokens, in / out | Calls |
|---|---|---|---|
| Direct reading | All papers in one prompt | 44,000 / 9,300 | 2 |
| Evidence graph | Quote-backed findings per paper → knowledge graph → entry | 76,000 / 23,000 | 7 |
| Agentic curator | An agent reads and searches a folder of the papers, then writes | 111,000 / 13,800 (11 turns, mostly cached re-reads) | 1 session |
| Memory only (control) | Written from the model's memory, no papers | 7,600 / 2,300 | 1 |
| Recall, then verify | Memory draft audited against the papers; unsupported claims deleted | 84,000 / 24,000 | 10 |
| Case table first | One record per reported patient or family → pooled table → entry | 110,000 / 30,000 | 7 |

All six have since been run on the same 100 entries, together with three add-ons built on them (second-hand evidence, a
reconciled case database and a learned curation guide). The results are in the README and in `results/omim100/strategies.md`.

## 3. SLIDERS and DataSTORM

### SLIDERS ✓
*Joshi, Shethia, Dao, Lam (Stanford OVAL). "Contexts are Never Long Enough: Structured Reasoning for Scalable Question
Answering over Long Document Sets", arXiv 2604.22294, April 2026. Code: github.com/stanford-oval/sliders.*

**How it works.** Given a question, a model first defines typed *evidence variables* (name, type, normalisation rule,
extraction instruction). Documents are cut into chunks of 16,000; for each chunk a cheap model decides whether it holds
evidence (a relevance gate) and, if so, extracts rows. Every value is stored with its source span and a rationale.
A coding agent then *reconciles* the table with SQL: it picks a key, canonicalises values, and resolves duplicates,
complementary records and true conflicts, with a second agent checking each change. The answer is written from the
reconciled table, with citations to spans. The table can be reused for follow-up questions.

**Reported.** Average cost $0.79 per question across eight benchmarks, range $0.37–1.39 (GPT-4.1 for reasoning,
GPT-4.1-mini for extraction). Extracting and reconciling a corpus of 100 documents and 3.9 million tokens took $13.10
and about 16 minutes, against $182 and 2.3 hours for GraphRAG to build its graph.
45% of chunks passed the relevance gate in the sample analysed. A check of 410 extracted facts found 99.03% correct.
Removing reconciliation dropped accuracy from 78.9 to 60.5 on that corpus. End-to-end latency 2–3 minutes.

**Pros for this task**
- Every stored value carries a span and a rationale, which is the provenance OMIM curation needs.
- Reconciliation targets the weakness our own structured strategies showed: the same patients or the same variant
  reported in several papers under different names.
- OMIM's entry format is a fixed schema, so the evidence variables can be written once and reused for every entry.
- The product is a relational table: the database is built as a by-product of writing the entries.
- Cost is reported, moderate, and falls further when the table is reused.

**Cons**
- It is built to answer questions, not to write long narrative entries; the writing step would have to be added.
- The authors note that evidence which "does not factor cleanly into typed fields" falls back on free-text columns.
  Our results point the same way: the extraction-based strategy conveyed fewer of OMIM's facts than direct reading
  on the 23 entries where at least half the papers were readable in full (66.0% against 70.5%).
- "Aggressive canonicalization can collapse genuinely distinct entities": two unrelated patients with the same variant
  are exactly that case.
- 55% accuracy on the hardest benchmark, which the authors call insufficient for full automation.

### DataSTORM ✓
*Liu, Jiang, Farook, Nicollier Sanchez, Castro Pena, Lam (Stanford). "DataSTORM: Deep Research on Large-Scale Databases
using Exploratory Data Analysis and Data Storytelling", arXiv 2604.06474, April 2026.*

**How it works.** It needs a relational database, optionally the web, and a query. Co-STORM first produces a
preliminary report from web sources. Then, for up to five layers, a planner writes exploration questions, a ReAct-style
executor answers each by inspecting the schema and running SQL and Python (up to 15 turns per question), a consistency
module standardises filters across sibling queries, and findings are merged into a capped "insight bank". A thesis is
formed and then sharpened, pivoted or confirmed every few layers. The report is written in five stages: outline,
section drafts, sentence-level fact verification, revision, polish.

**Reported.** On InsightBench, insight-level recall of 61.9 against 47.1 for the previous best with a GPT-4o judge
(69.3 against 49.9 with a Qwen judge). On a 1.6-million-row
conflict database, journalists preferred it to OpenAI's deep research in 57.5% of comparisons. An audit of 50 numeric
claims found 86% faithful and 10% unfaithful. No cost, token or call counts are reported.

**Pros for this task**
- It is the only approach here designed to write from a database rather than from documents, so it fits a second
  phase: once a case or evidence table exists across many entries, it could write the sections that need aggregation
  (genotype–phenotype correlations, population genetics) or cross-entry reviews of a gene family.
- Thesis-driven exploration can surface patterns no single paper states.

**Cons**
- It cannot start from papers: it "expects a cleaned dataset", so another method has to build the database first.
- An OMIM entry is a record of what papers reported, not a thesis; exploratory storytelling is the wrong shape for
  most sections and invites over-interpretation.
- 10% of audited numeric claims were unfaithful.
- By construction it is the most expensive approach per report (section 5), and its cost does not shrink for small
  entries.

## 4. Fifteen other approaches, ranked

Ranked for one purpose: producing faithful OMIM-style entries and the database behind them, at OMIM's scale. The
criteria, in order of weight: provenance and faithfulness; fit to an entry's two halves (narrative and structured
fields); behaviour on large reference lists; token cost; maturity of the code; and what it would add to the paper that
the six implemented strategies do not already show.

| Rank | Approach | Role | Main reason for the rank |
|---|---|---|---|
| 1 | **SLIDERS** | Entry + database | Span-level provenance, reconciliation across papers, reusable table, known cost |
| 2 | Evidence Aggregator (EvAgg) | Database (cases, variants) | The only one validated against ClinGen curation of rare-disease papers |
| 3 | Quote-then-cluster writing (Ai2 Scholar QA) | Entry | Matches OMIM's paper-by-paper structure at the lowest cost of any writer |
| 4 | WikiCrow / PaperQA2 | Entry | Already tested on writing gene articles against human-written ones |
| 5 | Span-grounded schema extraction (LangExtract; SPIRES/OntoGPT) | Database | Cheap, linear, character-offset provenance, ontology grounding |
| 6 | Prompt optimisation (DSPy with GEPA) | On top of any pipeline | Could raise the weak scores (HPO precision, fact coverage) without new architecture |
| 7 | DocETL | Entry + database | Validation loops removed hallucination in its own test; built-in entity resolution |
| 8 | STORM / Co-STORM | Entry | Question-driven outlining; a curator can steer Co-STORM |
| 9 | **DataSTORM** | Reports from the database | Valuable after a database exists, not for writing entries from papers |
| 10 | RAPTOR and map-reduce chains | Large entries | Cheapest way to cover hundreds of papers, at the price of provenance |
| 11 | GraphRAG, LightRAG, HippoRAG 2 | Large corpora | A graph method is already in the study; indexing cost is high |
| 12 | Recursive Language Models | Large entries | Strong on long-context benchmarks, unpredictable cost, no provenance |
| 13 | Open deep-research agents | New entries from scratch | Useful baseline for literature discovery, weakest control over sources |
| 14 | PubTator 3 with BioREx | Triage and cross-check | Free and precomputed, but abstracts only and no narrative |
| 15 | AutoSurvey family | Entry | Built for 30,000-token surveys of 1,000 papers; wrong scale |
| 16 | LOTUS, Palimpzest | Corpus-scale plumbing | Useful operators and cost optimisers rather than a method to compare |
| 17 | Evaporate | Regular fields only | Nearly free per document, unsuited to free prose |

### 2. Evidence Aggregator (EvAgg) ✓ (abstract)
*Twede, Conard, … MacArthur, Rehm (Microsoft Research, Broad Institute). bioRxiv 10.1101/2025.03.10.642480, 2025.
Code: github.com/microsoft/healthfutures-evagg.* Given a gene, it finds open-access papers, then runs a chain of
prompts over each paper's full text and tables to list variants and individuals, normalises variants to HGVS and
validates them with Mutalyzer, and extracts phenotype (as HPO), zygosity, variant type and inheritance per observation.
- **Pros:** benchmarked on 45 genes from ClinGen curation: paper recall 0.97, variant recall 0.92–0.95,
  observation-level content about 80%, phenotype recall 0.96; cut analysts' review time by 34%. It produces exactly
  the per-paper, per-patient table that our case-table strategy attempts, with external validation of variants.
- **Cons:** no narrative; open-access full text only (19% of our papers); each prompt re-sends the whole paper, and
  the authors say cost "may be prohibitive" and was not evaluated for genes with large literatures.
- **Use here:** adopt its variant normalisation and per-observation design to strengthen the case table, and its
  benchmark as a second gold standard.

### 3. Quote-then-cluster writing (Ai2 Scholar QA) ✓
*Singh et al. (Allen Institute for AI), arXiv 2504.10861, 2025. Code: github.com/allenai/ai2-scholarqa-lib.* One call
per paper extracts verbatim quotes relevant to the query; the quotes are clustered into an outline of sections; each
section is written from its quotes.
- **Pros:** reported about $0.50 and 2.5 minutes per 2,400-word report; verbatim quotes give provenance; outscored
  STORM, OpenScholar and PaperQA2 on its own benchmark (61.9 against 59.5, 53.5 and 51.4).
- **Cons:** evaluated on computer-science questions with a model judge; incorrect or missing references were a
  common user complaint (126 of 383 negative comments); no structured fields; close to a simplification of our evidence-graph strategy, so less new for the paper.

### 4. WikiCrow / PaperQA2 ✓
*Skarlinski et al. (FutureHouse), arXiv 2409.13740, 2024. Code: github.com/Future-House/paper-qa (Apache-2.0).* An
agent searches a local paper collection, retrieves chunks, has a model re-rank and summarise each chunk in the context
of the question, follows citations, and answers from the best summaries. WikiCrow writes a gene article from four such
queries plus one overview call.
- **Pros:** $4.48 and about 8 minutes per article; 86.1% of cited statements supported, against 71.2% for the matching
  human-written Wikipedia articles (375 statements, 240 articles); works on a supplied folder of PDFs.
- **Cons:** retrieval keeps only the top chunks, so per-patient detail can be missed; 13.5% of cited statements
  were unsupported, far above the rates our audit finds; no structured fields; about ten times our direct strategy's
  cost at this scale.

### 5. Span-grounded schema extraction (LangExtract; SPIRES/OntoGPT)
*LangExtract: Google, github.com/google/langextract (Apache-2.0). SPIRES/OntoGPT: Caufield et al., Bioinformatics 2024.*
A schema (few-shot examples or a LinkML model) drives extraction chunk by chunk. LangExtract aligns every value to
character offsets in the source and can make several passes for recall. SPIRES recurses into nested objects and
grounds terms to ontology identifiers.
- **Pros:** linear cost; LangExtract's offsets are stronger provenance than our quote matching; SPIRES grounded 97–100
  of 100 terms to GO and MONDO with a lookup step, against almost none when the model was asked for identifiers.
- **Cons:** extraction only: no reconciliation across papers and no writing. In the one rare-disease application of
  SPIRES (AutoMAxO), a clinician accepted 6.1% of 15,676 candidates, and only about 24% of phenotype terms grounded
  to HPO. LangExtract has no paper or published accuracy.

### 6. Prompt optimisation (DSPy with GEPA)
*Agrawal, Khattab et al., arXiv 2507.19457. Code: github.com/gepa-ai/gepa, github.com/stanfordnlp/dspy.* A reflection
model rewrites each stage's prompt from execution traces and textual feedback, keeping candidates that improve a
metric.
- **Pros:** our scoring already gives the textual feedback GEPA uses (which OMIM facts were missed, which HPO terms
  were extra); reported gains of 6–7 points over the previous optimiser.
- **Cons:** 1,800–7,000 pipeline runs per task; real risk of fitting to quirks of the gold standard (the HPO
  annotations are themselves noisy); needs a held-out split of the 100 entries.

### 7. DocETL
*Shankar et al. (UC Berkeley), arXiv 2410.12189. Code: github.com/ucbepic/docetl (MIT).* A pipeline of map, reduce,
resolve and filter operators; an optimiser rewrites it (splitting tasks, adding "gleaning" validation rounds) and
scores candidates on a sample.
- **Pros:** in its legal-contract test the optimised pipeline had a hallucination rate of 0.000 against 0.072
  unoptimised, and F1 0.477 against 0.379; `resolve` is a ready-made entity-resolution step.
- **Cons:** the optimised pipeline cost 18 times the plain one ($1.46 against $0.08); the optimiser targets accuracy
  only; span-level provenance is not described.

### 8. STORM / Co-STORM
*Shao et al., NAACL 2024; Jiang et al., EMNLP 2024 (Stanford OVAL). Code: github.com/stanford-oval/storm (MIT).*
Simulated conversations between a question-asking writer and a search-grounded expert, from several perspectives,
produce an outline; sections are then written from the collected references. Co-STORM adds a moderator and lets a
person take part.
- **Pros:** better organised articles than outline-driven retrieval (4.00 against 3.25 from Wikipedia editors); can
  run on supplied documents; Co-STORM's turn-taking suits a curator in the loop.
- **Cons:** about 15% of sentences unsupported; the commonest error is "improper inferential linking", which is the
  failure OMIM can least afford; open-web by default; no cost reported.

### 10. RAPTOR and map-reduce chains
*RAPTOR: Sarthi et al. (Stanford), ICLR 2024. Chain of Agents: Zhang et al. (Google), NeurIPS 2024. LLM×MapReduce:
Zhou et al., arXiv 2410.09342.* RAPTOR builds a tree of summaries over clustered chunks. The chains pass a running
summary from chunk to chunk, or map then reduce.
- **Pros:** RAPTOR's indexing is the cheapest of any structured method measured (1.7 million input tokens where
  GraphRAG used 115.5 million ✓); all scale linearly to hundreds of papers.
- **Cons:** summaries drop provenance and detail (4% of sampled RAPTOR nodes contained hallucinations); Chain of
  Agents averaged 47.6 in the SLIDERS comparison against 77.6 for SLIDERS.

### 11. GraphRAG, LightRAG, HippoRAG 2
*Edge et al. (Microsoft), arXiv 2404.16130; Guo et al., arXiv 2410.05779; Jiménez Gutiérrez et al., arXiv 2502.14802.*
- **Pros:** community summaries answer corpus-wide questions; HippoRAG 2 gets most of the benefit at a twelfth of the
  indexing cost.
- **Cons:** indexing one 11,656-passage corpus took 115.5 million input tokens for GraphRAG, 68.5 million for
  LightRAG and 9.2 million for HippoRAG 2 ✓; GraphRAG matches entities by exact string and did not measure
  hallucination. Our graph strategy already covers this family for the paper.

### 12. Recursive Language Models
*Zhang, Kraska, Khattab (MIT), arXiv 2512.24601.* The text is held as a variable in a Python session; the model writes
code to inspect and split it and calls itself on slices.
- **Pros:** best baseline on long-context benchmarks in the SLIDERS paper; handles inputs far beyond the context
  window.
- **Cons:** the model decides how many sub-calls to make, so cost varies widely ($0.99 ± 1.22 per query on one
  benchmark); no provenance.

### 13. Open deep-research agents
*GPT Researcher (Apache-2.0); LangChain Open Deep Research (MIT, archived August 2026) ✓.*
- **Pros:** closest ready-made tool for drafting an entry for a disorder with no reference list yet.
- **Cons:** 0.6–2 million tokens per report in LangChain's own benchmark runs ✓; web sources of mixed quality;
  citation control weaker than any strategy here.

### 14. PubTator 3 with BioREx
*Wei et al. (NCBI), Nucleic Acids Research 2024.* Precomputed entity and relation annotations over about 36 million
abstracts and 6 million full texts.
- **Pros:** no model tokens at all; gene–disease and variant–disease relations (F1 79.6% on BioRED) for triage and
  as an independent check on extracted genes and variants.
- **Cons:** relations from abstracts only; no inheritance, phenotype terms or narrative.

### 15–17. AutoSurvey, LOTUS and Palimpzest, Evaporate
- **AutoSurvey** (Wang et al., NeurIPS 2024 ✓): outline from chunked abstracts, sections written in parallel.
  3.0 million input and 113,000 output tokens for a 32,000-token survey; citation precision 78%, on a par with human
  surveys. Built for a different scale.
- **LOTUS** (Patel et al., Stanford, VLDB 2025) and **Palimpzest** (Liu et al., MIT): semantic operators with model
  cascades and cost-aware plan optimisers. Worth using to run any chosen method over 74,000 papers cheaply; not
  methods in themselves.
- **Evaporate** (Arora et al., Stanford, VLDB 2023 ✓): the model writes extraction code once and the code runs on
  every document, for a reported 110-fold cut in tokens. Over 40% of generated functions scored below 25 F1; it suits
  semi-structured documents, not case reports.

**Not ranked: verification loops.** Chain-of-Verification, RARR and FActScore-style refinement, and GeneAgent's
checking of claims against databases, are what our audit-and-repair stage and the recall strategy already do.
RAG-HPO (Garcia et al., Genome Medicine 2025: F1 0.80 for HPO terms from 112 case reports, against 0.48 or lower for
dictionary tools) is a component worth testing in place of our HPO step, at about one model call per phrase.

**What the survey did not find.** No published system generates OMIM-, Orphanet- or MONDO-style disease entries from
literature and scores them against curators. The nearest are EvAgg (gene-centred extraction), AutoMAxO (treatment
annotations with heavy review) and work that extracts HPO terms *from* OMIM text.

## 5. Token estimates

Generation only, per entry, input / output tokens. The audit and scoring used in this project would add roughly the
same amount to every row (about 50,000–120,000 input and 20,000–55,000 output tokens per entry in scenarios A–B).

| Approach | A: 5 papers, 9,500 tokens | B: 5 full texts, 45,000 | C: 100 full texts, 870,000 | Basis |
|---|---|---|---|---|
| Direct reading | 22K / 7K | 76K / 10K | 1.3M / 12K | Fitted to our measured runs; C would not fit a 1M-token context |
| Evidence graph | 57K / 15K | 106K / 33K | 2.1M / 450K | Fitted to our measured runs; C extrapolated |
| Agentic curator | 58K / 10K | 180K / 14K | 1–3M / 20K | Fitted to our measured runs for A–B; C untested. Mostly cached re-reads |
| Memory only (control) | 8K / 2K | 8K / 2K | 8K / 2K | Measured |
| Recall, then verify | 62K / 22K | 116K / 22K | 1.4M / 60K | Fitted to our measured runs; C extrapolated |
| Case table first | 68K / 20K | 166K / 43K | 3.2M / 580K | Fitted to our measured runs; C extrapolated |
| **SLIDERS** | 100K / 14K | 200K / 21K | 3–5.5M / 0.2–0.5M | Gate and extraction each read every chunk; reconciliation sized from the paper's $13.10 for 100 documents (see below). A further entry or question from the same table: 10K–60K |
| **DataSTORM** | 2.4M / 100K | 2.4M / 100K | 2.4M / 100K | 22 questions × ~8 agent turns, reruns, warm start, five-stage report. Does not depend on source size; excludes building the database |
| EvAgg | 0.3M / 15K | 1.4M / 60K | 29M / 1.2M | Whole paper re-sent for each of ~30 prompts per full-text paper |
| Quote-then-cluster (Scholar QA) | 32K / 9K | 78K / 15K | 1.3M / 140K | One read per paper plus quotes twice |
| WikiCrow / PaperQA2 | 130K / 12K | 360K / 20K | 360–400K / 20K | 4 queries × up to 30 chunk summaries; capped by retrieval |
| LangExtract or SPIRES, plus a writing call | 45K / 12K | 190K / 26K | 3.5M / 360K | Two passes; few-shot examples resent per chunk |
| DSPy with GEPA | 0 per entry | 0 per entry | 0 per entry | One-off: 0.2–1 billion tokens to optimise a whole pipeline, 15–55 million for one stage |
| DocETL | 35K–0.4M | 110K–1.6M | 1.8M–26M | Plain pipeline to optimised (18× in the paper's test) |
| STORM | 350K / 35K | 350K / 35K | 350K / 35K | ~90 conversation calls plus outline and sections; Co-STORM 400–600K |
| RAPTOR, then a writing call | 21K / 9K | 64K / 15K | 1.05M / 140K | Each level summarised once |
| Chain of Agents, LLM×MapReduce | 16K / 9K | 57K / 15K | 1.0M / 140K | One pass plus carried summary |
| GraphRAG | 76K / 25K | 360K / 110K | 7M / 2.2M | ~8× source at 600–1,200-token chunks; far more with small passages. LightRAG ~0.6×, HippoRAG 2 ~0.08× of this |
| Recursive Language Models | 0.2–0.7M | 0.2–0.7M | 0.2–0.7M+ | From reported $0.33–0.99 per query; high variance |
| Open deep-research agents | 0.6–2M | 0.6–2M | 0.6–2M | Reported benchmark totals ÷ 100 tasks |
| AutoSurvey style | 92K / 16K | 92K / 16K | 1.0M / 30K | Scaled from its reported 3.0M / 113K |
| PubTator 3 | 0 | 0 | 0 | Precomputed |
| Evaporate | ~0 | ~0 | ~0 | One-off code generation, about 190 tokens per document |

**Reading the table.** The first six rows are fitted to token counts from our own runs (entries of 1,300 to 24,000
source tokens), so scenario C is an extrapolation for them too. Source sizes throughout are characters ÷ 4; the
model's own count of the same text ran about 1.5 times higher in our runs, and every row allows for that. It is why
reading 870,000 "tokens" directly shows as 1.3 million and would have to be split.

**How the SLIDERS row was sized.** The paper reports no token counts, but its $13.10 for 3.9 million tokens can be
split. Reading every chunk once for the gate and 45% of them again for extraction is about 6.5 million small-model
input tokens, roughly $3 at GPT-4.1-mini prices. The remaining $10 or so is the large model reconciling the table:
on the order of 3–4 million tokens, about as many as the corpus itself. So reconciliation is not a small term, and it
is the part most likely to grow with OMIM's larger entries. For OMIM the gate would save little, since a curator has
already chosen every paper as relevant.

**From tokens to price.** In our runs the list price reported by the command-line tool works out at roughly $5 per
million input tokens and $25 per million output for the model used. At that rate scenario B costs about $0.63 for
direct reading, $1.50 for SLIDERS and $14.50 for DataSTORM. SLIDERS' own split, a small model for extraction and a
large one for reconciliation and writing, would bring it close to the direct strategy's cost.

**All 6,953 entries**, at today's access to papers (about 140 million source tokens), generation input only:

| Approach | Input tokens | Note |
|---|---|---|
| Direct reading | ~0.25 billion | Fails on the ~5% of entries with more than 50 references |
| Quote-then-cluster | ~0.4 billion | |
| Evidence graph; agentic curator | ~0.6 billion each | The agent's are mostly cached |
| SLIDERS | ~1.1–2.5 billion | About half is per-chunk and per-entry overhead on abstracts; leaves a reusable table |
| WikiCrow / PaperQA2; STORM | ~2.5 billion each | Fixed cost per entry however small |
| Open deep research | 4–14 billion | |
| DataSTORM | ~17 billion | Plus the cost of building the database |

Two things follow. For the 83% of entries with 12 or fewer references, source text is so small that fixed per-entry
overhead decides the cost, and methods with a large constant (STORM, PaperQA2, deep research, DataSTORM) cost ten to a
hundred times more than reading the papers once. For the 17% of entries that hold most of the literature, direct
reading stops fitting, and the choice is between extraction into a table (SLIDERS, case table, evidence graph),
selective reading (the agent, PaperQA2) and summarisation (RAPTOR, chains).

## 6. Suggested next steps for the paper

*Status, November 2026.* Items 1, 2 and 4 were carried out in adapted form: a reconciled case database (the idea taken
from SLIDERS), a tier of entries with 30–75 references, and a curation guide learned by reflection on a training split
(the idea taken from GEPA). Items 3 and 5 were not done. The list below is kept as written.

1. **Add SLIDERS** as the seventh strategy, with OMIM's sections and fields as fixed evidence variables. It tests the
   one idea the current six lack: reconciliation of a relational evidence table.
2. **Add a large-entry tier** to the evaluation set (entries with 30–250 references). Every difference between methods
   in section 5 grows there, and the current set stops at 12.
3. **Borrow from EvAgg** for the case table (HGVS validation, per-observation fields) and try its ClinGen-derived
   benchmark as a second gold standard.
4. **Run GEPA** on the best two pipelines once the six-way comparison is in, with a train/test split.
5. Use **DataSTORM** only in a second phase, on the pooled table, for cross-entry reports.

## Sources

Re-read in the primary source: [SLIDERS](https://arxiv.org/abs/2604.22294) ·
[DataSTORM](https://arxiv.org/abs/2604.06474) · [PaperQA2 / WikiCrow](https://arxiv.org/abs/2409.13740) ·
[AutoSurvey](https://arxiv.org/abs/2406.10252) · [HippoRAG 2, indexing-cost table](https://arxiv.org/abs/2502.14802) ·
[Ai2 Scholar QA](https://arxiv.org/abs/2504.10861) ·
[Evaporate](https://arxiv.org/abs/2304.09433) ·
[Open Deep Research](https://github.com/langchain-ai/open_deep_research) ·
[Evidence Aggregator](https://www.biorxiv.org/content/10.1101/2025.03.10.642480v1) (abstract-level figures only).

Read by a research assistant, not re-checked: [STORM](https://arxiv.org/abs/2402.14207) ·
[Co-STORM](https://arxiv.org/abs/2408.15232) · [OpenScholar](https://arxiv.org/abs/2411.14199) ·
[GEPA](https://arxiv.org/abs/2507.19457) ·
[Chain-of-Verification](https://arxiv.org/abs/2309.11495) · [RARR](https://arxiv.org/abs/2210.08726) ·
[RAPTOR](https://arxiv.org/abs/2401.18059) · [GraphRAG](https://arxiv.org/abs/2404.16130) ·
[LightRAG](https://arxiv.org/abs/2410.05779) · [DocETL](https://arxiv.org/abs/2410.12189) ·
[LOTUS](https://arxiv.org/abs/2407.11418) · [Palimpzest](https://arxiv.org/abs/2405.14696) ·
[Chain of Agents](https://arxiv.org/abs/2406.02818) · [LLM×MapReduce](https://arxiv.org/abs/2410.09342) ·
[Recursive Language Models](https://arxiv.org/abs/2512.24601) · [LangExtract](https://github.com/google/langextract) ·
[SPIRES / OntoGPT](https://academic.oup.com/bioinformatics/article/40/3/btae104/7612230) ·
[DRAGON-AI](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/) · [CurateGPT](https://arxiv.org/abs/2411.00046) ·
[PubTator 3](https://pmc.ncbi.nlm.nih.gov/articles/PMC11223843) ·
[RAG-HPO](https://pmc.ncbi.nlm.nih.gov/articles/PMC11643181) ·
[AutoPM3](https://pmc.ncbi.nlm.nih.gov/articles/PMC12263107) ·
[GeneAgent](https://pmc.ncbi.nlm.nih.gov/articles/PMC12328209/) ·
[AutoMAxO](https://pmc.ncbi.nlm.nih.gov/articles/PMC12228962/) ·
[TrialMind](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331930/) ·
[GPT Researcher](https://github.com/assafelovic/gpt-researcher).

## Not verified

- No token or call counts are published for DataSTORM, STORM, Co-STORM, EvAgg, SPIRES, LangExtract or Chain of Agents;
  their rows in section 5 are modelled from the described procedure.
- EvAgg's precision figures and per-field accuracies come from the research assistant's reading of the full paper;
  I confirmed only the abstract (97% paper recall, 92% variant recall, about 80% content accuracy, 34% less review time).
- SLIDERS' chunk size is given as 16000 in a sample configuration without units; tokens are assumed.
- The split of SLIDERS' $13.10 between extraction and reconciliation uses GPT-4.1 and GPT-4.1-mini list prices from
  memory ($2 / $8 and $0.40 / $1.60 per million tokens); the paper gives only the total.
- The corpus size behind the GraphRAG indexing figure is given in passages, not tokens, so the "8× source" multiplier
  is an assumption about chunk size.
- Venues for DocETL, HippoRAG 2, OpenScholar and Ai2 Scholar QA were taken from secondary listings.
- Automated systematic-review extraction (otto-SR) could not be opened and is left out.
