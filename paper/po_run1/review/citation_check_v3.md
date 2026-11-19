# Citation check: refined_v3.tex against the reference library abstracts

Inputs (read only): `latex/refined_v3.tex`, `lit/citation_map.json`, `latex/references.bib`, `latex/refined_v3.bbl` (built 22:20, after the .bib update at 22:01), `review/citation_check_v0.md`.
Evidence used: the `abstract` field of each key in `citation_map.json`. For `holm1979simple` only the title was used. `abstract_summary` and my own memory were not used as evidence for "supported".

## 1. Counts

| | n |
|---|---|
| Citation commands (`\citep` 71, `\citet` 2, `\citealp` 1) | 74 |
| Citing sentences (all on lines 42–111; the abstract and the appendix contain no `\cite`) | 28 |
| (sentence, key) pairs checked | 118 |
| Distinct keys cited | 99 (all present in the map, the .bib and the .bbl; no unresolved citations) |
| **supported** | 101 |
| **method/tool citation** (correct use) | 13 |
| **beyond the abstract** | 4 pairs (2 problems) |
| **wrong** | 0 |

Method/tool pairs (all correct):
- line 50: `sayers2026database`, `Louden2020MedgenNcbis`, `rosonovski2024europe`, `seal2023genenames`
- line 87: `rosonovski2024europe`
- line 89: `landrum2025clinvar`, `gargano2024human`, `Louden2020MedgenNcbis`
- line 95: `seal2023genenames`
- line 109: `Khler2009ClinicalDiagnostics` ("in the spirit of"; the abstract describes semantic-similarity metrics over the HPO)
- line 111: `Efron1979BootstrapMethods`, `Dixon1946StatisticalSign`, `holm1979simple` (title only)

Named systems are all attached to the right key: FlyAOC → `zhang2026flyaoc`, GEN-KnowRD → `yan2026genknowrd`, PaperQA2 → `skarlinski2024language`, VeriScore → `Song2024VeriscoreEvaluating`. The prose names no year or venue except through `\citet` (`groza2026systematic` prints 2026 and `Khler2009…` prints 2009, both matching the map).

## 2a. Pairs that are not plainly supported

| Line | Sentence (shortened) | Key | Class | What the abstract says | Minimal rewording the abstract supports |
|---|---|---|---|---|---|
| 44 | "several hold the model and settings fixed …; they concern question answering, summarisation **or open retrieval** scored against benchmark answers" | `li2024retrieval`, `Li2025LaraBenchmarking`, `han2025rag` (3 pairs, one problem) | beyond ("open retrieval") | li2024: "We benchmark RAG and LC across various public datasets using three latest LLMs". LaRA: "2326 test cases across four practical QA task categories". han: "established text-based tasks, including question answering and query-based summarization". None of the three is about open retrieval. The phrase dates from v0, where it summarised a wider set of works; after the merge it sits on these three keys only. | "…several hold the model and settings fixed \citep{…}; they concern question answering and query-based summarisation on public benchmarks." |
| 60 | "**Table- and database-centred** pipelines rewrite document-processing operations agentically" | `shankar2025docetl` | beyond (minor: "table-centred") | "a system that optimizes complex document processing pipelines … uses an agent-based approach to automatically optimize them, leveraging novel agent-based rewrites". It mentions no tables or databases. v0 accepted this wording, but v0 had flagged DocETL for "table" in the Introduction. | "Document-processing pipelines are rewritten agentically \citep{shankar2025docetl}, and database-centred systems reconcile extracted databases for systematic reviews \citep{joshi2026sliders} or carry out deep research over large databases \citep{liu2026datastorm}." |

Supported, with notes (not counted as problems):
- line 63, "Surveys catalogue contamination, its detection and its mitigation" (5 keys). This is supported only when read collectively. `Ravaut2024…` covers detection only ("survey all recent work on contamination detection"). `Xu2024…` and `Chen2025…` cover mitigation only. `Deng2024…` and `Cheng2025…` cover both. This is the wording v0 recommended.
- line 42, "built this way, and so, in part, are" ClinVar (`Landrum2017…`, `landrum2025…`) and HPO (`robinson2008human`). As in v0, the abstracts describe interpretations "submitted by clinical testing laboratories, research laboratories, expert panels", and HPO annotations made for OMIM entries rather than from papers. The "in part" hedge carries this.
- line 57, `twede2026evidence` "evaluated for … rare-disease diagnostics". This is supported, but the abstract describes a literature-extraction tool, evaluated for "relevant article selection … extracting specific details" against an expert-curated data set. It would sit more naturally in the extraction group of the same sentence.

## 2b. "Unlike prior work" and "no prior work" statements

1. **Line 57 (end), line 60 (end) and line 44: CGBench is closer than the draft says.** The draft cites `queen2025cgbench` only as "benchmarked on clinical-genetics reasoning". Its abstract says: "CGBench is built from ClinGen, a resource of expert-curated literature interpretations … we measure LM explanations against human explanations with an LM judge approach". That is scoring against what curators wrote about individual publications. It sits awkwardly with line 44 ("The closest work … scores against something other than what curators wrote about each paper") and with the line 57 contrast ("the reference is the curators' own per-paper text"). The "has not been used to compare strategies" claim still holds, because CGBench compares models: "We test 8 different LMs". Suggested addition to line 57: "CGBench scores model explanations against ClinGen curators' interpretations of individual publications, but compares models rather than generation strategies \citep{queen2025cgbench}."
2. **Abstract, first sentence (no citation): "they are rarely compared with the papers, the model and the scoring held fixed".** Line 44 now concedes that several comparisons hold the model and settings fixed. Their abstracts also fix the documents and scoring: LaRA "2326 test cases … naturally occurring long texts"; han "a unified evaluation protocol that standardizes data preprocessing, retrieval configurations, and generation settings". So the abstract still carries a weaker form of the v0 "change together" problem. Suggested: "…but comparisons that hold the papers, the model and the scoring fixed concern question answering and summarisation, not writing what experts wrote about each paper."
3. **Lines 44 and 57, the four closest studies** (`zhang2026flyaoc`, `yan2026genknowrd`, `skarlinski2024language`, `groza2026systematic`). The stated differences are consistent with the abstracts. FlyAOC: "access to a 16,898-paper corpus", "7,397 expert-curated annotations". GEN-KnowRD: profiles generated by the model, judged by disease ranking. PaperQA2: compared with Wikipedia. Groza: "LLM recall of curated RD knowledge". The line 57 wording, "memorisation, pipeline and agent harnesses that search a paper corpus", groups the memorisation harness with corpus search. This is harmless but slightly loose.
4. **Line 60, "Here, by contrast, … all paradigms share one audit and one scoring".** This is consistent: it contrasts with the literature-writing systems in the preceding sentence. `han2025rag` also uses a unified protocol, but line 44 already acknowledges that.
5. **Line 69, "that drafts from abstracts convey less … is therefore expected".** Consistent; neither Westergaard nor Cohen concerns generation.

## 3. Status of the v0 corrections

| v0 item | Status in v3 |
|---|---|
| `cao2025automation`, `wang2025accelerating` cited as reviews (wrong) | **Resolved by removal.** The sentence and both keys, along with `Clark2025…` and `scherbakov2025…`, are no longer cited. |
| `allot2023tracking` (genes/diseases/abstracts) | **Applied** (line 42, v0 wording). |
| `shankar2025docetl` in the Introduction | **Applied** (dropped from line 42). The line 60 use is now flagged above. |
| `yan2026genknowrd` "against curated knowledge" | **Applied** (line 57, v0 wording). |
| WikiCrow → PaperQA2 (`skarlinski2024language`) | **Applied** (line 57). |
| `shao2024assisting` split out to "Wikipedia-like articles from Internet sources" | **Applied** (line 60). |
| `Xu2024…`, `Chen2025…` "detection" → "detection and mitigation" | **Applied** (line 63). |
| `Cohen2010…` / `Westergaard2018…` split | **Applied** (line 69). |
| 2b "model, retrieval and scoring change together" | **Applied in the Introduction** (line 44 "several hold the model and settings fixed"; the old line-34 "cannot be compared" claim is gone). The abstract still has a residual form (2b item 2). |
| §3.1 "agentic curator" name clash with `balhoff2026frontier` | **Not applied.** The strategy is still called "agentic curator" (lines 48, 93, tables), and Balhoff is still cited only as "agents for ontology curation of natural phenotypes". Its abstract says each model operates "as an 'agentic curator' within a self-contained workspace that supplies the source publication PDF". |
| §3.2 `Li2024LongContext` year | **Applied** (map, .bib and .bbl give 2025, arXiv 2501.01880). The key still says 2024, which is harmless. |
| §3.3 GeneWhisperer, Murphy as `@inproceedings{booktitle=openRxiv}` | **Not applied.** They still print as "In *openRxiv*, 2025/2024". |
| §3.3 `yan2026genknowrd` DOI prefix 10.64898 | **Resolved.** doi.org redirects it to medrxiv.org (checked today). |
| §3.4 keys with stripped diacritics | Unchanged; rendered output unaffected. |
| §3.5 preprints with published versions | **Partly applied.** 13 cited keys now carry published venues (e.g. RARR ACL 2023, Promptbreeder ICML 2024, Min-K% ICLR 2024, LiveCodeBench ICLR 2025, HippoRAG NeurIPS 2024, GeneGPT Bioinformatics 2024, Ravaut TMLR 2025). Still arXiv in the map, .bib and .bbl, marked `published: False` in `lit/venue_updates.json`: Self-RAG, DSPy, Roberts 2023, LiveBench, APE, OPRO, EvoPrompt, TextGrad, EvalGen (`shankar2024who`). v0 believed (from memory, unverified) that all of these have published versions. The inconsistency GEPA = ICLR 2026 vs DSPy = arXiv remains. |
| §3.6 FastHPOCR "moved from … to" | **Applied** ("uses dedicated taggers … and, increasingly, language models"). |
| §3.7 ClinVar/HPO "built this way" | Wording unchanged, and acceptable under "in part". |
| §3.8 Clark 2025 "spread" | Resolved by removal. |
| §3.9 `iclr2025_conference` style | **Not applied** (line 2, line 262). |
| §3.10 unused entries | Now 27 uncited (includes `liu2024lost`, `Madaan2023…`, `Shinn2023…`, and the four keys dropped above). Harmless with natbib. |

## 4. Reference list (refined_v3.bbl, 99 entries)

- No key cited in the text is missing from the .bib. There are no `?` citations in the PDF.
- Map, .bib and .bbl years agree for all 99 cited keys. The years changed today are carried through, with natexlab letters (e.g. Li et al. 2025a–d, Gao et al. 2023a/b, Groza et al. 2024a/b).
- No duplicate works: titles are unique, and PaperQA vs PaperQA2 and the OMIM/ClinVar/PubTator stacks are distinct papers.
- **Malformed author:** `furlan2025eagleai` prints "A.~wan". The .bib has `wan, A.`, a lower-case surname, probably "Wan, A."; check the source.
- **Preprint mis-typed as proceedings:** `Li2025GenewhispererEnhancing` and `Murphy2024HarnessingGenerative` print "In *openRxiv*". Make them `@misc` with `howpublished = {bioRxiv}` and `{medRxiv}` (DOIs 10.1101/2025.03.30.646211 and 10.1101/2024.06.10.24308475).
- **Missing identifier:** these preprints print only "arXiv, 2024/2025/2026" with no arXiv number: `balhoff2026frontier`, `caufield2024curategpt`, `edge2024local`, `han2025rag`, `joshi2026sliders`, `shankar2024who`, `skarlinski2024language`, `xiang2025use`. Other arXiv entries give "arXiv preprint arXiv:NNNN.NNNNN".
- **Missing article number:** `Cohen2010StructuralContent` prints "BMC Bioinformatics, 11, 2010" with no article number (492). Minor.
- No entry lacks a year or a venue.

## What could not be checked

- **`holm1979simple`** has no abstract; only the title was checked, and it fits its method use.
- **10 cited abstracts are cut off** ("… [Truncated]"): `Asai2023…`, `Golchin2025…`, `Khattab2023…`, `Lewis2020…`, `Manakul2023…`, `Murphy2024…`, `Shi2023…`, `White2024…`, `Yuksekgonul2024…`, `yan2026genknowrd`. Every claim on these keys was carried by the visible part.
- **Provenance of abstracts.** As in v0, many abstracts have no recorded source URL; I treated them as genuine, and they were not re-verified against a source.
- **Published venues** for the remaining arXiv entries were not verified; I did no external lookup except the single DOI resolution check.
