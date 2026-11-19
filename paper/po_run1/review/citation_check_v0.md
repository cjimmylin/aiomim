# Citation check: draft_v0.tex against the reference library abstracts

Inputs (read only): `latex/draft_v0.tex`, `lit/citation_map.json`, `latex/references.bib`.
Evidence used: the `abstract` field of each key in `citation_map.json` (titles only for `holm1979simple`). `abstract_summary` and my own memory were not used as evidence for "supported".

## 1. Counts

| | n |
|---|---|
| Citation commands (`\citep` 68, `\citet` 2, `\citealp` 2) | 72 |
| Citing sentences checked (period-delimited; all fall on lines 41–112. Lines 289–1046 of the appendix contain no `\cite`) | 28 |
| (sentence, key) pairs checked | 124 |
| Distinct keys cited | 103 (all present in the map and the .bib) |
| **supported** | 102 |
| **method/tool citation** (correct use) | 12 |
| **beyond the abstract** | 8 |
| **wrong** | 2 |

Method/tool pairs (all correct): line 49 `sayers2026database`, `Louden2020MedgenNcbis`, `rosonovski2024europe`, `seal2023genenames`; line 88 `rosonovski2024europe`; line 90 `landrum2025clinvar`, `gargano2024human`, `Louden2020MedgenNcbis`; line 96 `seal2023genenames`; line 112 `Efron1979BootstrapMethods`, `Dixon1946StatisticalSign`, `holm1979simple` (title only, no abstract; the title matches its use as the Holm correction).

There is also one uncited summary claim ("unlike X, we ...") that the cited abstracts partly contradict. It is not a single pair, so it is listed separately in 2b.

## 2a. Pairs that are not plainly supported

| Line | Sentence (shortened) | Key | Class | What the abstract says | Minimal rewording the abstract supports |
|---|---|---|---|---|---|
| 41 | "reviews of generative models for evidence synthesis and literature review document the spread of such tools" | `cao2025automation` | **wrong** | Not a review. "To validate a large language model (LLM)-based workflow (otto-SR) to automate … article screening, data extraction, and risk of bias assessment" | "…reviews document the spread of such tools \citep{Clark2025GenerativeArtificial,scherbakov2025emergence}, and LLM workflows now automate screening and data extraction for systematic reviews \citep{cao2025automation,wang2025accelerating}." |
| 41 | same | `wang2025accelerating` | **wrong** | Not a review. "we propose a generative artificial intelligence (AI) pipeline named TrialMind to streamline study search, study screening, and data extraction tasks in SR" | Same fix as the row above. |
| 41 | "Automated text mining already annotates genes, variants and diseases across PubMed abstracts and open-access full text" | `allot2023tracking` | beyond | LitVar 2.0 covers variants only: "accurately search for genetic variants in the unstructured literature … unified search of full text and supplementary data". Genes, diseases and PubMed abstracts are not mentioned. | "…across PubMed abstracts and open-access full text \citep{Wei2019PubtatorCentral,wei2024pubtator}, and variants can be searched across full text and supplementary data \citep{allot2023tracking}" |
| 41 | "extraction into a graph or a table before writing" | `shankar2025docetl` | beyond | DocETL "optimizes complex document processing pipelines … agent-based rewrites". The abstract does not mention tables or a writing step. | "extraction into a graph or a table, or optimised document-processing pipelines, before writing \citep{edge2024local,joshi2026sliders,shankar2025docetl}". Alternatively drop DocETL here; line 61 already cites it correctly. |
| 58 | "GEN-KnowRD generates schema-guided rare-disease profiles, assesses their quality against curated knowledge and builds a knowledge base from them" | `yan2026genknowrd` | beyond ("against curated knowledge") | "generate schema-guided rare disease profiles, systematically assesses their quality, and constructs a computable knowledge base (PheMAP-RD)". Curated knowledge appears only as a comparison variant: "a variant of GEN-KnowRD instantiated with expert-curated knowledge". Note: the map's abstract is cut off at about 1,500 characters. | "GEN-KnowRD generates schema-guided rare-disease profiles, assesses their quality and builds a knowledge base from them, evaluated by disease ranking on patient benchmarks" |
| 58 | "WikiCrow writes gene articles compared against Wikipedia" | `skarlinski2024language` | beyond (the system name and the "gene" scope) | "WikiCrow" does not appear in the title or abstract, and neither do "gene articles". The abstract says: "PaperQA2 writes cited, Wikipedia-style summaries of scientific topics that are significantly more accurate than existing, human-written Wikipedia articles". | "PaperQA2 writes cited Wikipedia-style summaries of scientific topics, compared against existing Wikipedia articles \citep{skarlinski2024language}". Line 43 uses the same key; its wording there is fine. |
| 61 | "Agentic and retrieval-augmented systems write cited answers or articles from the scientific literature" | `shao2024assisting` | beyond (scope) | STORM writes "Wikipedia-like articles from scratch" using a "topic expert grounded on trusted Internet sources", evaluated on FreshWiki. The abstract does not mention scientific literature. | Split it out: "…from the scientific literature \citep{Lla2023…,Asai2024…,singh2025ai2,skarlinski2024language} or Wikipedia-like articles from Internet sources \citep{shao2024assisting}" |
| 64 | "Surveys catalogue contamination and its detection" | `Xu2024BenchmarkData` | beyond (detection) | "reviews the complex challenge of BDC … and explores alternative assessment methods to mitigate the risks". Detection is not mentioned. | "Surveys catalogue contamination, its detection and its mitigation" (this wording also covers the next row) |
| 64 | same | `Chen2025RecentAdvances` | beyond (detection) | "in-depth analysis of existing static to dynamic benchmarking methods aimed at reducing data contamination risks". Detection is not mentioned. | Same as the row above. |
| 70 | "Text mining yields more from full text than from abstracts, whose structure and content differ" | `Cohen2010StructuralContent` | beyond, and partly contrary, for "yields more" | Supports "structure and content differ". On yield it points the other way: "a wide variety of gene mention systems performed much worse on article bodies than they did on abstracts". | "Text mining yields more from full text than from abstracts \citep{Westergaard2018ComprehensiveQuantitative}, whose structure and content differ \citep{Cohen2010StructuralContent}" |

## 2b. "Unlike X, we …" and "no prior work" statements

- **Line 61, last sentence** (no direct citation; it refers to the works cited in that paragraph): "These comparisons are on question answering, summarisation or open retrieval, where the model, the retrieval and the scoring change together." The task part is consistent with the abstracts. The "change together" part is **contradicted by several cited abstracts**:
  - `han2025rag`: "a unified evaluation protocol that standardizes data preprocessing, retrieval configurations, and generation settings, enabling fair and reproducible comparisons".
  - `Li2025LaraBenchmarking`: "a novel benchmark specifically designed to rigorously compare RAG and LC LLMs".
  - `li2024retrieval`: "We benchmark RAG and LC across various public datasets using three latest LLMs".
  - `Li2024LongContext`: "a more comprehensive evaluation by filtering out questions…".

  These are controlled comparisons of strategy with the model held fixed. A reviewer will catch this, and it bears on the paper's novelty claim, which recurs at line 34 ("evaluated with different models, sources and scoring, so their results cannot be compared") and line 43. Suggested wording: "These comparisons hold the model fixed but are on question answering, summarisation or open retrieval against benchmark answers; we hold the papers fixed, score against curator-written per-paper text, and report a matched ablation…".
- **Line 43 and line 58**, the "four closest studies": the abstracts of `zhang2026flyaoc`, `yan2026genknowrd`, `skarlinski2024language` and `groza2026systematic` are **consistent** with the stated differences.
  - FlyAOC searches a 16,898-paper corpus and scores against expert-curated FlyBase annotations, so the papers are not fixed and the reference is not per-paper text. It does, however, compare harnesses including memorisation, which is close to this paper's strategy comparison and memory-only control. The draft says so.
  - GEN-KnowRD has no paper-fixed input in its abstract.
  - PaperQA2 searches the literature and is compared with Wikipedia.
  - Groza et al. measure memory only.
- **Line 70**, "our access experiments measure this effect for knowledge-base writing": consistent. Neither Cohen 2010 nor Westergaard 2018 concerns generation.

## 3. Other things a reviewer would catch

1. **Strategy name clash.** `balhoff2026frontier` (line 58) describes its agents as an "agentic curator" working in a workspace that supplies the source PDFs. The draft names its own strategy "agentic curator" and cites Balhoff only as "agents for ontology curation of natural phenotypes". Credit the term or rename the strategy.
2. **Year mismatch.** `Li2024LongContext` has map/bib year 2024, but its arXiv id is 2501.01880 (January 2025).
3. **Malformed .bib entries.** `Li2025GenewhispererEnhancing` and `Murphy2024HarnessingGenerative` are `@inproceedings` with `booktitle={openRxiv}`. They are preprints (DOIs 10.1101/… on bioRxiv and medRxiv) and should be `@misc` with `howpublished`. `yan2026genknowrd` has DOI prefix `10.64898/…`, which is unlike every other preprint DOI in the file (10.1101/…); check it resolves.
4. **Keys with stripped diacritics or hyphens.** `Gutirrez2024…` (Gutiérrez), `Khler2009…` (Köhler), `Lla2023…` (Lála), `Opsahlong2024…` (Opsahl-Ong), and `Stewartevans2025…` (uncited). Rendered output is unaffected because the author fields are correct, but the .bib mixes two key conventions (auto-generated CamelCase and hand-written lowercase).
5. **Preprints cited where peer-reviewed versions exist.** This is from my memory, not the map; the map lists only the arXiv venue for each of these, so the brief's "map shows a published version" condition is met by none of them. Verify before changing:
   - Lewis 2020 (NeurIPS 2020)
   - Self-RAG (ICLR 2024)
   - RARR (ACL 2023)
   - DSPy (ICLR 2024)
   - SelfCheckGPT (EMNLP 2023)
   - Min-K% Prob / Shi 2023 (ICLR 2024)
   - Roberts 2023 (ICLR 2024)
   - LiveCodeBench (ICLR 2025)
   - LiveBench (ICLR 2025)
   - APE / Zhou 2022 (ICLR 2023)
   - Pryzant 2023 (EMNLP 2023)
   - OPRO (ICLR 2024)
   - EvoPrompt (ICLR 2024)
   - Promptbreeder (ICML 2024)
   - MIPRO / Opsahl-Ong (EMNLP 2024)
   - TextGrad (Nature 2025)
   - Liu 2023 (Findings of EMNLP 2023)
   - VeriScore (Findings of EMNLP 2024)
   - HippoRAG (NeurIPS 2024)
   - GeneGPT (Bioinformatics 2024)
   - EvalGen / `shankar2024who` (UIST 2024)

   The inconsistency is visible in the reference list itself: GEPA is cited at ICLR 2026, but DSPy and MIPRO are cited as arXiv.
6. **Narrative tension at line 58.** "Concept recognition … has moved from dedicated taggers \citep{luo2021phenotagger,groza2024fasthpocr} to language models". FastHPOCR's abstract argues *against* LLMs for this task and goes "back to the basics" in 2024, after LLM solutions existed. The pair is supported (it is a dedicated tagger), but "moved from … to" misstates the trajectory. One fix: "Concept recognition … uses dedicated taggers \citep{…} and, increasingly, language models \citep{…}".
7. **Weak "built this way" at line 41.** The ClinVar abstracts (`Landrum2017ClinvarImproving`, `landrum2025clinvar`) describe an archive of interpretations submitted by laboratories and expert panels. They do not say ClinVar is built by experts reading papers; the "in part" hedge covers this. Similarly, `robinson2008human` says the HPO annotations were made for OMIM entries rather than from papers, though `gargano2024human` supports new curation. These are counted as supported.
8. **Clark 2025 does not document "spread".** `Clark2025GenerativeArtificial` is a performance review of 19 studies, concluding that "the current evidence does not support GenAI use in evidence synthesis without human involvement". It is supported as a review on the topic, but it does not document "spread". `scherbakov2025emergence` does (172 studies).
9. **Style file year.** The paper uses the `iclr2025_conference` style ("Under review … ICLR 2025") while citing ICLR 2026, NeurIPS 2026 and COLM 2026 works. This is outside the citation check, but obvious to a reviewer.
10. **Unused entries.** 23 entries in the .bib and the map are never cited (e.g. `liu2024lost`, `vasilevsky2026mondo`, `Madaan2023SelfrefineIterative`, `Shinn2023ReflexionLanguage`). They are harmless with natbib, but some are relevant, e.g. Self-Refine and Reflexion for the learned curation guide, and "lost in the middle" for long-context reading.
11. No duplicate works were found: titles and DOIs are unique. The stacked OMIM (3), ClinVar (2) and PubTator (2) citations are distinct papers.

## What could not be checked

- **`holm1979simple`** has no abstract; only the title was checked. Its use as a method citation is consistent with the title.
- **16 abstracts in the map are cut off at about 1,500 characters**, ending "... [Truncated]". Cited ones: `Asai2023SelfragLearning`, `Clark2025GenerativeArtificial`, `Golchin2025DataContamination`, `Khattab2023DspyCompiling`, `Lewis2020RetrievalaugmentedGeneration`, `Manakul2023SelfcheckgptZeroresource`, `Murphy2024HarnessingGenerative`, `Shi2023DetectingPretraining`, `White2024LivebenchChallenging`, `Yuksekgonul2024TextgradAutomatic`, `yan2026genknowrd`. Every claim on these keys except GEN-KnowRD's "against curated knowledge" was carried by the visible part. For GEN-KnowRD, the missing tail might state it.
- **Provenance.** The brief says 68 abstracts were fetched today. The map has 70 keys with `abstract_source` and 56 without, including `holm1979simple`. The 55 other abstracts without a source URL have no recorded provenance. I treated them as evidence because they read as genuine abstracts and match their titles, but they were not re-verified against a source.
