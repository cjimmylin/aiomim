# Final correction pass: refined_v3.tex -> refined_v4.tex

Changes are listed as changed source paragraphs (a paragraph is one source line), in document order, from a line diff of v3 against v4. Each entry gives the location (v3 line / v4 line and section), the edit labels it combines, the sources (number-check item numbers, citation-check item, B, D1-D8, E), the old text and the new text. Where one paragraph received several corrections, they are listed together and the new text is the final v4 text. 'E (length)' marks thinning done to keep the main text within 10 pages.

## 1. Abstract (v3 l. 35 / v4 l. 35)

- Edits: Abstract, sentence 1; Abstract, sentence 6; Abstract
- Sources: Citation check 2b item 2; D1; E (abstract length)

Old:

```latex
Many system designs turn a set of papers into cited, structured text, but they are rarely compared with the papers, the model and the scoring held fixed. We build such a comparison from 100 OMIM phenotype entries: each is drafted from exactly the papers its curators cited, by one model under one claim-level audit and one scoring, so the generation strategy is the only variable; the primary endpoint, OMIM facts conveyed, is coverage of fixed fact lists split from curator-written per-paper text. Hiding the full text of the same papers lowers coverage from 79.8\% to 36.1\% (means over entries, no arm repaired). On facts the supplied text states, the strategies that read the papers convey more than nine in ten; on facts it does not state, under 7\%. Three reading strategies are within about a point of one another, a case-table-first pipeline falls behind them, and drafting from memory conveys far less. Measurement choices matter at this resolution: a completion rule that treated stopped replies asymmetrically produced a spurious difference larger than those between the reading strategies. One model family wrote, audited and judged everything, and no human validated any judgement.
```

New:

```latex
Many system designs turn a set of papers into cited, structured text, but comparisons that hold the papers, the model and the scoring fixed concern question answering and summarisation, not writing what experts wrote about each paper. We build such a comparison from 100 OMIM phenotype entries: each is drafted from exactly the papers its curators cited, by one model under one claim-level audit and one scoring, so the generation strategy is the only variable; the primary endpoint, OMIM facts conveyed, is coverage of fixed fact lists split from curator-written per-paper text. Hiding the full text of the same papers lowers coverage from 79.8\% to 36.1\% (means over entries, no arm repaired). On facts the supplied text states, the strategies that read the papers convey more than nine in ten; on facts it does not state, under 7\%. Three reading strategies are within about a point of one another, our case-table-first implementation trails them, and drafting from memory conveys far less. Measurement choices matter: a completion rule that treated stopped replies asymmetrically produced a spurious difference larger than those between the reading strategies. One model family wrote, audited and judged everything, and no human validated any judgement.
```

## 2. section{Introduction} (v3 l. 44 / v4 l. 44)

- Edits: Introduction, para 2; Introduction, para 2, last sentence
- Sources: Citation check 2a (open retrieval); Citation check 2b item 1 (consequence of the CGBench sentence); D2

Old:

```latex
Comparisons between such designs exist, and several hold the model and settings fixed \citep{li2024retrieval,Li2025LaraBenchmarking,han2025rag}; they concern question answering, summarisation or open retrieval scored against benchmark answers. The closest work in genetics and biology searches a corpus for its sources, measures memory alone, or scores against something other than what curators wrote about each paper (Section~\ref{sec:related_work}). The curator's task itself, writing an entry from exactly the papers the curators cited and scoring what it says about each paper against what the curators wrote about that paper, has not been used to compare strategies. Three questions are open. With the model, the sources, the guards and the scoring held fixed, how much does the generation strategy matter? What limits agreement with what experts wrote: the strategy, or what the strategy was given to read? And which errors does a claim-level audit against the cited source catch, and which can it not see? This paper is an evaluation and benchmark contribution: it proposes no new method, but compares system designs for evidence-grounded generation under one control, and its measurement lessons apply to evaluating such systems generally.
```

New:

```latex
Comparisons between such designs exist, and several hold the model and settings fixed \citep{li2024retrieval,Li2025LaraBenchmarking,han2025rag}; they concern question answering and query-based summarisation on public benchmarks. The closest work in genetics and biology searches a corpus for its sources, measures memory alone, compares models rather than strategies, or scores against something other than what curators wrote about each paper (Section~\ref{sec:related_work}). The curator's task itself, writing an entry from exactly the papers the curators cited and scoring what it says about each paper against what the curators wrote about that paper, has not been used to compare strategies. Three questions are open. With the model, the sources, the guards and the scoring held fixed, how much does the generation strategy matter? What limits agreement with what experts wrote: the strategy, or what the strategy was given to read? And which errors does a claim-level audit against the cited source catch, and which can it not see? This paper is an evaluation and benchmark contribution: it proposes no new method, but compares system designs for evidence-grounded generation under one control; we expect its measurement lessons to be not specific to this domain.
```

## 3. section{Introduction} (v3 l. 46 / v4 l. 46)

- Edits: Introduction, para 3, last sentence (deleted; same point in Limitation (ii))
- Sources: E (length)

Old:

```latex
We answer the questions with a controlled benchmark in which the generation strategy is the only variable (Figure~\ref{fig:overview}). Each of 100 OMIM phenotype entries with 2--12 references is written from its header and exactly the papers its curators cited, with the causal gene withheld; only 19\% of the cited papers are readable in full through open access. The strategies form three paradigms (\emph{read and write}; \emph{extract, then write}; \emph{memory first}), one control (a memory-only draft with no papers) and three add-ons, each tested against its parent. Each strategy writes a whole entry, but the primary endpoint, \emph{OMIM facts conveyed}, scores only what the draft says about each cited paper against curator-written per-paper text: OMIM's allelic-variant descriptions as deposited in ClinVar, each split once, without sight of any draft, into a fixed list of facts (6,652 over 476 paragraphs). Draft content beyond this reference is checked only by the audit.
```

New:

```latex
We answer the questions with a controlled benchmark in which the generation strategy is the only variable (Figure~\ref{fig:overview}). Each of 100 OMIM phenotype entries with 2--12 references is written from its header and exactly the papers its curators cited, with the causal gene withheld; only 19\% of the cited papers are readable in full through open access. The strategies form three paradigms (\emph{read and write}; \emph{extract, then write}; \emph{memory first}), one control (a memory-only draft with no papers) and three add-ons, each tested against its parent. Each strategy writes a whole entry, but the primary endpoint, \emph{OMIM facts conveyed}, scores only what the draft says about each cited paper against curator-written per-paper text: OMIM's allelic-variant descriptions as deposited in ClinVar, each split once, without sight of any draft, into a fixed list of facts (6,652 over 476 paragraphs).
```

## 4. section{Introduction} (v3 l. 48 / v4 l. 48)

- Edits: Introduction, para 4 (hidden full text); Introduction, para 4 (stated facts); Introduction, para 4 (case table first); Introduction, para 4 (ablation clause)
- Sources: E; Number check 1, 6; B; D1; D4; E; D1; E (length)

Old:

```latex
\textbf{In the regime tested, what limits agreement is what the strategy was given to read, not how it reads.} The direction is expected: curators wrote from full papers, so drafts written from less text must convey less. What we add is the size of the effect within the same papers and an attribution of what the drafts lack. When the full text of papers that have one is hidden and the same entries are rewritten from their abstracts, coverage of the same fixed facts falls from 79.8\% to 36.1\% (means over 46 entries, no arm repaired; paired difference $+43.7$ points, $+38.3$ to $+49.1$). Each fixed fact also carries a model judgement of whether the text supplied for its paper states it. On the 2,372 facts it states, direct reading, the agentic curator and the evidence graph convey 93.6--94.4\% (means over entries), with differences from direct reading under one point whose intervals include zero; on the 2,669 facts it does not state, they convey 5.5--6.9\%. Between strategies, on the 93 entries every strategy completed, only case table first is clearly behind direct reading ($-1.9$ points, $-3.1$ to $-0.8$), most of all on facts stated in full-text papers ($-8.4$, $-14.3$ to $-3.8$), and part of its gap reflects the extraction effort of our implementation. These results hold for entries with 2--12 references, inputs that fit one prompt and one model.
```

New:

```latex
\textbf{In the regime tested, what limits agreement is what the strategy was given to read, not how it reads.} The direction is expected: curators wrote from full papers, so drafts written from less text must convey less. What we add is the size of the effect within the same papers and an attribution of what the drafts lack. When the full text of papers that have one is hidden and the same entries are rewritten from their abstracts, coverage of the same fixed facts falls from 79.8\% to 36.1\% (means over 46 entries, no arm repaired; Figure~\ref{fig:hidden}). Each fixed fact also carries a model judgement of whether the text supplied for its paper states it. On facts it states, direct reading, the agentic curator and the evidence graph convey 93.6--94.4\% (means over entries), with differences from direct reading under one point whose intervals include zero (Table~\ref{tab:stated}). On facts it does not state, they convey 5.5--6.9\%. The two memory-based strategies are far behind every reading strategy (Table~\ref{tab:main}). Among the reading strategies, only our case-table-first implementation trails direct reading on the entries every strategy completed: its mean difference, $-1.9$ points, has a bootstrap interval that excludes zero, but the sign test does not reach 0.05 ($p=0.071$). Its deficit is largest on facts stated in full-text papers, and a matched ablation suggests, as an inference, that part of it reflects the extraction effort of our implementation (Section~\ref{sec:ablation}). These results hold for one model and for entries with 2--12 references whose papers fit one prompt, a regime in which direct reading is expected to do well.
```

## 5. section{Introduction} (v3 l. 50 / v4 l. 50)

- Edits: Introduction, contributions (2); Introduction, contributions (5); Introduction, contributions (closing sentence)
- Sources: Number check 4; Number check 14; D7; E (length; the same limits are in the abstract and Section 5)

Old:

```latex
Our contributions are: (1) a benchmark and harness for evidence-grounded knowledge-base writing against curator-written references, built only from public resources \citep{sayers2026database,Louden2020MedgenNcbis,rosonovski2024europe,seal2023genenames}, with a claim-level audit, fixed fact lists and per-entry release of every draft, verdict and score; (2) a controlled comparison of three paradigms, a control and three add-ons under one model, reporting completion (stopped replies are an outcome, not an exclusion), run-to-run variation and a matched ablation; (3) a within-paper measurement of how much access bounds agreement, with missed and conveyed facts attributed and strategies compared on the facts the supplied text states; (4) a characterisation of what the audit can and cannot see; (5) a memory-only control by creation date, and negative results at this scale for recall-then-verify, a small learned guide and reconciliation; and (6) measurement lessons (Section~\ref{sec:discussion}). One model family wrote, audited and judged everything; no curator has read any draft, verdict or fact judgement; only open-access text without supplementary material was available; and every strategy was given the curators' reference list. The generated entries are drafts for expert review, not clinical guidance.
```

New:

```latex
Our contributions are: (1) a benchmark and harness for evidence-grounded knowledge-base writing against curator-written references, built only from public resources \citep{sayers2026database,Louden2020MedgenNcbis,rosonovski2024europe,seal2023genenames}, with a claim-level audit, fixed fact lists and per-entry release of every draft, verdict and score; (2) a controlled comparison of three paradigms, a control and three add-ons under one model, reporting completion as an outcome and comparing entries only when every strategy completed them, run-to-run variation and a matched ablation; (3) a within-paper measurement of how much access bounds agreement, with missed and conveyed facts attributed and strategies compared on the facts the supplied text states; (4) a characterisation of what the audit can and cannot see; (5) a memory-only control by creation date, and, at this scale, negative results for recall-then-verify and reconciliation and a held-out gain from a small learned guide that is not distinguishable from zero; and (6) measurement lessons (Section~\ref{sec:discussion}). One model family wrote, audited and judged everything, no curator has read any draft, and every strategy was given the curators' reference list (Section~\ref{sec:discussion}). The generated entries are drafts for expert review, not clinical guidance.
```

## 6. section{Related Work} (v3 l. 57 / v4 l. 57)

- Edits: Related work, para 1 (list of clinical-genetics work); Related work, para 1 (closest work)
- Sources: Citation check 2b item 1

Old:

```latex
Concept recognition against the Human Phenotype Ontology uses dedicated taggers \citep{luo2021phenotagger,groza2024fasthpocr} and, increasingly, language models \citep{groza2024evaluation,yang2024enhancing,garcia2025improving}. Structured prompting and assistant tools have been proposed for populating and maintaining knowledge bases \citep{caufield2024structured,caufield2024curategpt,toro2024dynamic,niyonkuru2025leveraging}, as have an agent that assists manual gene function annotation \citep{Li2025GenewhispererEnhancing}, generative annotation of the severity of ontology phenotypes \citep{Murphy2024HarnessingGenerative} and agents for ontology curation of natural phenotypes \citep{balhoff2026frontier}. In clinical genetics, language models have been applied to extracting variant, gene--disease and gene--phenotype evidence from papers \citep{li2025autopm3,furlan2025eagleai,wang2026pubmind,yin2026benchmarking}, benchmarked on clinical-genetics reasoning \citep{queen2025cgbench}, given database tools for genomics questions \citep{Jin2023GenegptAugmenting}, and evaluated for gene-set function \citep{hu2025evaluation}, gene prioritisation \citep{Kim2024AssessingUtility} and rare-disease diagnostics \citep{twede2026evidence}. FlyAOC scores memorisation, pipeline and agent harnesses that search a paper corpus against FlyBase curators' annotations \citep{zhang2026flyaoc}; GEN-KnowRD generates schema-guided rare-disease profiles, assesses their quality and builds a knowledge base from them, evaluated by disease ranking on patient benchmarks \citep{yan2026genknowrd}; PaperQA2 writes cited Wikipedia-style summaries of scientific topics, compared against existing Wikipedia articles \citep{skarlinski2024language}; and \citet{groza2026systematic} measure model memory of rare-disease genes and phenotypes. In our benchmark the cited papers are fixed, the reference is the curators' own per-paper text and structured fields, and the generation strategy is the only variable.
```

New:

```latex
Concept recognition against the Human Phenotype Ontology uses dedicated taggers \citep{luo2021phenotagger,groza2024fasthpocr} and, increasingly, language models \citep{groza2024evaluation,yang2024enhancing,garcia2025improving}. Structured prompting and assistant tools have been proposed for populating and maintaining knowledge bases \citep{caufield2024structured,caufield2024curategpt,toro2024dynamic,niyonkuru2025leveraging}, as have an agent that assists manual gene function annotation \citep{Li2025GenewhispererEnhancing}, generative annotation of the severity of ontology phenotypes \citep{Murphy2024HarnessingGenerative} and agents for ontology curation of natural phenotypes \citep{balhoff2026frontier}. In clinical genetics, language models have been applied to extracting variant, gene--disease and gene--phenotype evidence from papers \citep{li2025autopm3,furlan2025eagleai,wang2026pubmind,yin2026benchmarking}, given database tools for genomics questions \citep{Jin2023GenegptAugmenting}, and evaluated for gene-set function \citep{hu2025evaluation}, gene prioritisation \citep{Kim2024AssessingUtility} and rare-disease diagnostics \citep{twede2026evidence}. FlyAOC scores memorisation, pipeline and agent harnesses that search a paper corpus against FlyBase curators' annotations \citep{zhang2026flyaoc}; GEN-KnowRD generates schema-guided rare-disease profiles, assesses their quality and builds a knowledge base from them, evaluated by disease ranking on patient benchmarks \citep{yan2026genknowrd}; PaperQA2 writes cited Wikipedia-style summaries of scientific topics, compared against existing Wikipedia articles \citep{skarlinski2024language}; and \citet{groza2026systematic} measure model memory of rare-disease genes and phenotypes. CGBench, built from ClinGen's expert-curated literature interpretations, scores model explanations against human explanations, but compares models rather than generation strategies \citep{queen2025cgbench}. In our benchmark the cited papers are fixed, the reference is the curators' own per-paper text and structured fields, and the generation strategy is the only variable.
```

## 7. section{Related Work} (v3 l. 60 / v4 l. 60)

- Edits: Related work, para 2 (DocETL)
- Sources: Citation check 2a (DocETL)

Old:

```latex
Retrieval augmentation supplies a model with selected passages \citep{Lewis2020RetrievalaugmentedGeneration}, possibly retrieving on demand and critiquing its own output \citep{Asai2023SelfragLearning}. Whether this beats placing all documents in a long context is contested: one re-evaluation finds long context generally ahead on question answering \citep{Li2024LongContext}; others argue that very long contexts dilute focus on relevant information \citep{Yu2024DefenseRag}, propose hybrids \citep{li2024retrieval}, or report no single winner \citep{Li2025LaraBenchmarking}. Graph intermediates are used for query-focused summarisation \citep{edge2024local} and retrieval \citep{Gutirrez2024HipporagNeurobiologically}, and systematic comparisons ask when graphs help \citep{han2025rag,xiang2025use}. Table- and database-centred pipelines rewrite document-processing operations agentically \citep{shankar2025docetl}, reconcile extracted databases for systematic reviews \citep{joshi2026sliders} or carry out deep research over large databases \citep{liu2026datastorm}. Agentic and retrieval-augmented systems write cited answers or articles from the scientific literature \citep{Lla2023PaperqaRetrievalaugmented,Asai2024OpenscholarSynthesizing,singh2025ai2,skarlinski2024language}, or Wikipedia-like articles from Internet sources \citep{shao2024assisting}. Here, by contrast, the papers are fixed to the curators' reference list, the reference is the curators' own text, all paradigms share one audit and one scoring, and access is measured and manipulated.
```

New:

```latex
Retrieval augmentation supplies a model with selected passages \citep{Lewis2020RetrievalaugmentedGeneration}, possibly retrieving on demand and critiquing its own output \citep{Asai2023SelfragLearning}. Whether this beats placing all documents in a long context is contested: one re-evaluation finds long context generally ahead on question answering \citep{Li2024LongContext}; others argue that very long contexts dilute focus on relevant information \citep{Yu2024DefenseRag}, propose hybrids \citep{li2024retrieval}, or report no single winner \citep{Li2025LaraBenchmarking}. Graph intermediates are used for query-focused summarisation \citep{edge2024local} and retrieval \citep{Gutirrez2024HipporagNeurobiologically}, and systematic comparisons ask when graphs help \citep{han2025rag,xiang2025use}. Document-processing pipelines are rewritten agentically \citep{shankar2025docetl}, and database-centred systems reconcile extracted databases for systematic reviews \citep{joshi2026sliders} or carry out deep research over large databases \citep{liu2026datastorm}. Agentic and retrieval-augmented systems write cited answers or articles from the scientific literature \citep{Lla2023PaperqaRetrievalaugmented,Asai2024OpenscholarSynthesizing,singh2025ai2,skarlinski2024language}, or Wikipedia-like articles from Internet sources \citep{shao2024assisting}. Here, by contrast, the papers are fixed to the curators' reference list, the reference is the curators' own text, all paradigms share one audit and one scoring, and access is measured and manipulated.
```

## 8. subsection{Strategies} (v3 l. 93 / v4 l. 93)

- Edits: Sec. 3.2 Strategies (agentic curator)
- Sources: Citation check 3 (balhoff2026frontier credit)

Old:

```latex
The strategies are three paradigms, one control and three add-ons (Figure~\ref{fig:overview}; Appendix Table~\ref{tab:app_strategies}). \emph{Read and write}: \textbf{direct reading} puts all papers in one prompt and is the baseline; the \textbf{agentic curator} works in a folder of the papers with read and search tools and must give a verbatim quote for every paragraph. \emph{Extract, then write}: the \textbf{evidence graph} extracts quote-backed findings per paper (discarding any whose quote is not in the paper; none was) into a graph of papers, genes, variants, phenotypes and inheritance; \textbf{case table first} extracts one record per reported patient or family per paper and pools them. In both, the writer sees only the intermediate, synopsis terms are computed by rule, and so is inheritance for the table. \emph{Memory first}: \textbf{recall, then verify} writes from memory, audits the draft against the papers, and keeps supported claims, restates partly supported ones, corrects contradicted ones and deletes the rest; it may not add content from the papers. The \textbf{memory-only control} is the memory draft with no papers, audited but not repaired. The add-ons are \textbf{second-hand evidence} on direct reading (for a paper not readable in full, passages from later open-access papers that describe it), the \textbf{reconciled case database} on case table first (merging the same patient, family or variant across papers), and a \textbf{learned curation guide} on direct reading (rules learned in two reflection rounds from 27 training entries). These are our own implementations; published systems were not run. The four strategies that read the papers are the \emph{reading strategies}.
```

New:

```latex
The strategies are three paradigms, one control and three add-ons (Figure~\ref{fig:overview}; Appendix Table~\ref{tab:app_strategies}). \emph{Read and write}: \textbf{direct reading} puts all papers in one prompt and is the baseline; the \textbf{agentic curator} (a term \citet{balhoff2026frontier} also use for agents working in a workspace that supplies the source publication) works in a folder of the papers with read and search tools and must give a verbatim quote for every paragraph. \emph{Extract, then write}: the \textbf{evidence graph} extracts quote-backed findings per paper (discarding any whose quote is not in the paper; none was) into a graph of papers, genes, variants, phenotypes and inheritance; \textbf{case table first} extracts one record per reported patient or family per paper and pools them. In both, the writer sees only the intermediate, synopsis terms are computed by rule, and so is inheritance for the table. \emph{Memory first}: \textbf{recall, then verify} writes from memory, audits the draft against the papers, and keeps supported claims, restates partly supported ones, corrects contradicted ones and deletes the rest; it may not add content from the papers. The \textbf{memory-only control} is the memory draft with no papers, audited but not repaired. The add-ons are \textbf{second-hand evidence} on direct reading (for a paper not readable in full, passages from later open-access papers that describe it), the \textbf{reconciled case database} on case table first (merging the same patient, family or variant across papers), and a \textbf{learned curation guide} on direct reading (rules learned in two reflection rounds from 27 training entries). These are our own implementations; published systems were not run. The four strategies that read the papers are the \emph{reading strategies}.
```

## 9. subsection{Audit, scoring and statistics} (v3 l. 99 / v4 l. 99)

- Edits: Sec. 3.3 Completion
- Sources: Number check 4

Old:

```latex
\textbf{Completion.} $S$ completes $e$ when its draft exists and no per-paper call failed. A one-call strategy whose reply is stopped loses the entry, whereas a per-paper strategy loses a paper; scoring the second and excluding the first would bias the comparison. Strategies are therefore compared on entries all of them completed, completion is an outcome, and a sensitivity analysis counts a missing draft as zero.
```

New:

```latex
\textbf{Completion.} $S$ completes $e$ when its draft exists and no per-paper call failed. A one-call strategy whose reply is stopped loses the entry, whereas a per-paper strategy loses a paper; scoring the second and excluding the first would bias the comparison. Completion is therefore reported as an outcome, strategies are compared only on entries every one of them completed, and a sensitivity analysis counts a missing draft as zero.
```

## 10. subsection{Audit, scoring and statistics} (v3 l. 107 / v4 l. 107)

- Edits: Sec. 3.3 Definitions (24%)
- Sources: Number check 7; D5

Old:

```latex
No fact went unjudged in any run. \emph{OMIM facts conveyed}, the primary endpoint, is this coverage averaged over entries (the \emph{mean over entries}); paired differences are means over entries of per-entry differences. Every level in the main text is a mean over entries unless it is marked \emph{pooled}, i.e.\ the same ratio over all facts in a group, the only form in which the attributions of missed and conveyed facts exist. A claim is \emph{judged supported} when the audit's final verdict is ``supported''; this is a judgement of fidelity to the cited text by the model family that wrote the draft, not of correctness, and \emph{unsupported} is not \emph{wrong}. Finally, each fixed fact carries a judgement of whether the text available for its paper \emph{states}, \emph{partly states} or does \emph{not state} it (a ``stated'' verdict needs a quote verified in that text). It is a property of the supplied text, the same for every strategy, and a model judgement. The reference covers a minority of the task: 24\% of a direct-reading draft's statements have a counterpart in the paragraph (Appendix~\ref{app:addons}).
```

New:

```latex
No fact went unjudged in any run. \emph{OMIM facts conveyed}, the primary endpoint, is this coverage averaged over entries (the \emph{mean over entries}); paired differences are means over entries of per-entry differences. Every level in the main text is a mean over entries unless it is marked \emph{pooled}, i.e.\ the same ratio over all facts in a group, the only form in which the attributions of missed and conveyed facts exist. A claim is \emph{judged supported} when the audit's final verdict is ``supported''; this is a judgement of fidelity to the cited text by the model family that wrote the draft, not of correctness, and \emph{unsupported} is not \emph{wrong}. Finally, each fixed fact carries a judgement of whether the text available for its paper \emph{states}, \emph{partly states} or does \emph{not state} it (a ``stated'' verdict needs a quote verified in that text). It is a property of the supplied text, the same for every strategy, and a model judgement. The reference covers a minority of the task: on the 68 held-out entries of the guide experiment, 24\% of a direct-reading draft's statements have a counterpart in the paragraph (Appendix~\ref{app:addons}).
```

## 11. subsection{Audit, scoring and statistics} (v3 l. 111 / v4 l. 111)

- Edits: Sec. 3.3 Statistics; Sec. 3.3 Statistics, last clause
- Sources: Number check 5; B; E (length); B (sign test reported for the main comparison only)

Old:

```latex
\textbf{Statistics.} We report paired differences from direct reading with a bootstrap 95\% interval over entries (10,000 resamples; \citealp{Efron1979BootstrapMethods}), the number of entries better, worse and tied, the median difference and an exact sign test \citep{Dixon1946StatisticalSign}, with Holm correction \citep{holm1979simple} across the secondary headline measures; the primary endpoint is not adjusted. The interval over entries is the test of a difference. The main comparison is one run per entry; as a yardstick for how much a difference moves when generation, audit and scoring are repeated, we report replicate noise from three replicates on 30 entries. ``Points'' are percentage points.
```

New:

```latex
\textbf{Statistics.} Paired differences from direct reading are means over entries, reported with a bootstrap 95\% interval over entries (10,000 resamples; \citealp{Efron1979BootstrapMethods}) and the number of entries better, worse and tied. For the main comparison we also apply an exact two-sided sign test to the paired differences, ties dropped \citep{Dixon1946StatisticalSign}. For the eight secondary headline measures its $p$-values are adjusted by Holm's method \citep{holm1979simple} across those measures within each strategy; the primary endpoint is not adjusted. The interval and the sign test are the tests of a difference. The main comparison is one run per entry; as a yardstick for how much a difference moves when generation, audit and scoring are repeated, we report replicate noise from three replicates on 30 entries. ``Points'' are percentage points.
```

## 12. section{Experiments} (v3 l. 117 / v4 l. 117)

- Edits: Abstract, sentence 6; Sec. 4 opening; Sec. 4 opening (takeaways, tightened; experiment-table pointer merged); Sec. 4 takeaway (1)
- Sources: D1; E (takeaways); E; Number check 10 (avoid 'nearly all')

Old:

```latex
Appendix Table~\ref{tab:app_experiments} lists every experiment with its entry set and the number of entries compared. Every result rests on judgements by the model family that wrote the drafts; none was validated by a person.
```

New:

```latex
\textbf{Takeaways.} (1) Access bounds agreement: hiding the full text of the same papers lowers coverage sharply, and the reading strategies convey more than nine in ten of the facts the supplied text states. (2) Three reading strategies are close; our case-table-first implementation trails them, most where full text is readable. (3) Drafting from memory conveys far less, and memory alone contributes little for the newest entries. (4) The audit checks fidelity to the cited text, not correctness. Appendix Table~\ref{tab:app_experiments} lists every experiment and its entry set; every result rests on judgements by the model family that wrote the drafts, none validated by a person.
```

## 13. subsection{What limits agreement: access to the source} (v3 l. 121 / v4 l. 121)

- Edits: Sec. 4.1 opening paragraph
- Sources: E (length, to keep the 10-page limit)

Old:

```latex
Curators wrote from full papers, so a draft written from an abstract must convey less of what they wrote; the direction of the access effect is expected. What we measure is its size within the same papers, and how much of what the drafts lack was in the text they were given, with three analyses: a within-paper manipulation, an attribution of missed facts and a provenance check of conveyed facts. Section~\ref{sec:stated} compares strategies on the facts the text states.
```

New:

```latex
The direction of the access effect is expected (Section~\ref{sec:intro}); we measure its size within the same papers and how much of what the drafts lack was in the text they were given.
```

## 14. subsection{What limits agreement: access to the source} (v3 l. 123 / v4 l. 123)

- Edits: Sec. 4.1 Hiding the full text
- Sources: E; E (duplicate figure reference); E (counts are in the Figure 2 caption)

Old:

```latex
\textbf{Hiding the full text of the same papers.} In 49 entries, the 91 papers readable in full were hidden and each entry was rewritten by direct reading from their abstracts, with and without second-hand passages from later open-access papers; all conditions are scored on the 46 entries with a full-text draft (136 paragraphs, the same 2,120 fixed facts). The full-text arm is the main run's direct-reading draft taken before the audit's repair round, so no arm is repaired (Figure~\ref{fig:hidden}). Coverage is 79.8\% with the full text and 36.1\% from the abstracts (paired difference $+43.7$ points, $+38.3$ to $+49.1$; 45 entries higher, none lower, one tied); second-hand passages raise abstract-only coverage to 40.9\% ($+4.9$, $+2.8$ to $+7.1$; 33 better, 9 worse, 4 tied). After repair the difference is $+43.9$ (Appendix Table~\ref{tab:app_hidden}).
```

New:

```latex
\textbf{Hiding the full text of the same papers.} In 49 entries, the 91 papers readable in full were hidden and each entry was rewritten by direct reading from their abstracts, with and without second-hand passages from later open-access papers; all conditions are scored on the same fixed facts of the 46 entries with a full-text draft. The full-text arm is the main run's direct-reading draft taken before the audit's repair round, so no arm is repaired. Coverage is 79.8\% with the full text and 36.1\% from the abstracts, higher with the full text in every entry but one, which tied (Figure~\ref{fig:hidden}). Second-hand passages raise abstract-only coverage to 40.9\%. With the full-text arm scored after repair, the difference is $+43.9$ points (Appendix Table~\ref{tab:app_hidden}).
```

## 15. subsection{What limits agreement: access to the source} (v3 l. 138 / v4 l. 138)

- Edits: Sec. 4.1 Where the missed facts went
- Sources: E

Old:

```latex
\textbf{Where the missed facts went.} Each fact that direct reading did not fully convey was checked against the text available for its paper (Figure~\ref{fig:missed}; pooled). For full-text papers, 245 of 501 missed facts (49\%) were stated in the text the model read; for abstract-only papers 46 of 2,837 (2\%), and for title-only papers none of 341. Over all 6,498 facts, 43\% were conveyed, 4\% were omitted although stated in the available text, 13\% were omitted and partly stated, and 40\% were not in the available text.
```

New:

```latex
\textbf{Where the missed facts went.} Each fact that direct reading did not fully convey was checked against the text available for its paper (Figure~\ref{fig:missed}; pooled). For full-text papers, 49\% of missed facts were stated in the text the model read; for abstract-only papers 2\%, and for title-only papers none. Over all facts, 43\% were conveyed and 40\% were not in the available text; only 4\% were omitted although stated there (Appendix Table~\ref{tab:app_missed}).
```

## 16. subsection{What limits agreement: access to the source} (v3 l. 140 / v4 l. 140)

- Edits: Sec. 4.1 Where the conveyed facts came from
- Sources: Number check 8; E

Old:

```latex
\textbf{Where the conveyed facts came from.} Every fact direct reading conveyed was checked against the writer's text for its paper and, if not stated there, against the entry's other supplied papers (pooled; Appendix Table~\ref{tab:app_conveyed}). Of the 1,420 facts conveyed in full from abstract-only papers, 1,061 (74.7\%) are stated in the paper's own abstract, 222 (15.6\%) are partly stated there, 102 (7.2\%) are stated only in another supplied paper, 11 (0.8\%) are partly stated only in another supplied paper, and 24 (1.7\%) are stated in no supplied text; over abstract- and title-only papers together, 24 of 1,458. Facts conveyed only in part are more often outside the text: 58 of 583 (10.0\%) for abstract-only papers. A fact stated in no supplied text may have been recalled, inferred from what the text does state, or misjudged.
```

New:

```latex
\textbf{Where the conveyed facts came from.} Every fact direct reading conveyed was checked against the writer's text for its paper and, if not stated there or only partly stated, against the entry's other supplied papers (pooled; Appendix Table~\ref{tab:app_conveyed}). Of the 1,420 facts conveyed in full from abstract-only papers, 74.7\% are stated in the paper's own abstract and 7.2\% only in another supplied paper. Only 24 (1.7\%) are stated in no supplied text. Facts conveyed only in part are more often outside the text (10.0\% for abstract-only papers). A fact stated in no supplied text may have been recalled, inferred from what the text does state, or misjudged.
```

## 17. subsection{Controlled comparison of the strategies} (v3 l. 144 / v4 l. 144)

- Edits: Sec. 4.2 Completion
- Sources: E; E (length)

Old:

```latex
\textbf{Completion.} Of the 100 entries, 93 were completed by all six strategies; the memory-based strategies completed all 100, and the others lost one to three drafts or had incomplete entries (Appendix Table~\ref{tab:app_completion}).
```

New:

```latex
\textbf{Completion.} Of the 100 entries, 93 were completed by all six strategies; the others lost drafts or per-paper calls (Appendix Table~\ref{tab:app_completion}).
```

## 18. subsection{Controlled comparison of the strategies} (v3 l. 171 / v4 l. 171)

- Edits: Sec. 4.2 paragraph heading; Sec. 4.2 main paragraph; Sec. 4.2 sign tests (memory-based strategies as a clause); Sec. 4.2 yardstick; Sec. 4.2 ablation sentence
- Sources: B; Number check 3, 9; B; D1; D7; E; B; E (length); E (length); D1

Old:

```latex
\textbf{Three reading strategies are close; case table first is behind.} On the primary endpoint, direct reading, the evidence graph and the agentic curator lie within 0.7 points of one another (Table~\ref{tab:main}). The evidence graph's difference from direct reading, $-0.5$, has an interval that includes zero; the agentic curator's, $-0.6$, has one that touches zero ($-1.3$ to $+0.0$), with better/worse counts (31/42) that lean negative; case table first's, $-1.9$ ($-3.1$ to $-0.8$), excludes zero. As a yardstick for how much such differences move, repeating generation, audit and scoring three times on 30 entries gives a replicate-noise 95\% half-width of 1.0 point on a difference between two strategies over 93 entries (1.8 over 30) (Appendix~\ref{app:stability}). On those 30 entries the evidence graph's difference from direct reading was $+0.7$, $+1.9$ and $+0.5$ points in the three replicates, opposite in sign to its $-0.5$ on the 93 entries, an illustration of that noise. On 20 entries created in 2026, not used in developing the strategies, the ordering is the same (Appendix~\ref{app:new}).
```

New:

```latex
\textbf{Three reading strategies are close; case table first trails them.} On the primary endpoint, direct reading, the evidence graph and the agentic curator lie within 0.7 points of one another (Table~\ref{tab:main}). The evidence graph's difference from direct reading has an interval that includes zero, and the agentic curator's one that touches zero. Case table first's mean difference, $-1.9$ points, has an interval that excludes zero, but the sign test does not reach 0.05 ($p=0.071$). For the evidence graph the sign test gives $p=0.213$ and for the agentic curator $p=0.242$; after Holm adjustment no secondary headline measure differs from direct reading for any of these three, whereas the two memory-based strategies differ on the primary endpoint ($p<0.001$) and on four or five secondary measures each (Appendix Table~\ref{tab:app_sign}). On the ablation entries, the matched variant moved case table first from $-2.3$ to $-0.2$ points against direct reading; crediting this to extraction effort is an inference (Section~\ref{sec:ablation}).

As a yardstick, not a test, generation, audit and scoring were repeated three times on 30 entries (Appendix~\ref{app:stability}); replicate noise alone gives a 95\% half-width of 1.0 point on a difference between two strategies over 93 entries. The ordering is the same on entries created in 2026, which were not used in developing the strategies (Appendix~\ref{app:new}). Stopped replies were frequent there, so 20 of 30 entries are compared, and five strategies were run.
```

## 19. subsection{Controlled comparison of the strategies} (v3 l. 175 / v4 l. 177)

- Edits: Sec. 4.2 Secondary measures (cost)
- Sources: E

Old:

```latex
\textbf{Secondary measures.} Extract-then-write raises synopsis recall at lower precision and produces more variants OMIM does not list (111 and 130 against 36, pooled; Appendix Tables~\ref{tab:app_full} and~\ref{tab:app_varinh}). Recall, then verify may not add content from the papers, so its low coverage is partly by construction. Everything costs \$1.15--\$1.18 per entry at list price for read-and-write and \$1.72--\$1.78 for extract-then-write (Appendix Table~\ref{tab:app_cost}).
```

New:

```latex
\textbf{Secondary measures.} Extract-then-write raises synopsis recall at lower precision and produces more variants OMIM does not list (111 and 130 against 36, pooled; Appendix Tables~\ref{tab:app_full} and~\ref{tab:app_varinh}). Recall, then verify may not add content from the papers, so its low coverage is partly by construction. At list price, read-and-write costs \$1.15--\$1.18 per entry in all. Extract-then-write costs \$1.72--\$1.78 (Appendix Table~\ref{tab:app_cost}).
```

## 20. subsection{Strategies compared on the facts the supplied text states} (v3 l. 179 / v4 l. 181)

- Edits: Sec. 4.3 first paragraph
- Sources: E

Old:

```latex
Of the 6,239 fixed facts of the 93 compared entries, the supplied text states 2,372, partly states 1,198 and does not state 2,669 (for full-text papers 1,246 of 1,639 facts are stated, for abstract-only papers 1,099 of 4,221, for title-only papers 27 of 379). Because this judgement is a property of the supplied text, every strategy is scored on the same facts in each restriction (Table~\ref{tab:stated}; Appendix Table~\ref{tab:app_stated}).
```

New:

```latex
Of the 6,239 fixed facts of the compared entries, the supplied text states 2,372 and does not state 2,669; it states the rest in part (Appendix Table~\ref{tab:app_stated}). Because this judgement is a property of the supplied text, every strategy is scored on the same facts in each restriction (Table~\ref{tab:stated}; Appendix Table~\ref{tab:app_stated}).
```

## 21. subsection{Strategies compared on the facts the supplied text states} (v3 l. 204 / v4 l. 206)

- Edits: Sec. 4.3 second paragraph
- Sources: Number check 10; D3; E

Old:

```latex
On stated facts, direct reading conveys 94.4\%, the evidence graph 94.2\% and the agentic curator 93.6\%, and their differences from direct reading have intervals that include zero. On facts the text does not state, the reading strategies convey 5.5--6.9\%, no more than the memory-only control's 8.2\%. This contrast, with the within-paper experiment, is the evidence that access bounds agreement: on what was readable, three strategies convey nearly all of it. Two caveats apply. The judgement of what the text states is the model's; and the restriction has a ceiling of its own: on facts stated in abstract-only papers the reading strategies convey 95.5--97.1\% and most entries tie (58 of 79 for the evidence graph). Case table first is the exception. Its deficit is larger on stated facts ($-3.4$; 16 entries better, 42 worse, 31 tied) than overall ($-1.9$), and largest on facts stated in full-text papers ($-8.4$; 9/28/3), where it conveys 80.1\% against 88.5\%.
```

New:

```latex
On facts the supplied text states, direct reading, the evidence graph and the agentic curator convey 93.6--94.4\%, and their differences from direct reading have intervals that include zero. On facts the text does not state, the reading strategies convey 5.5--6.9\%, no more than the memory-only control's 8.2\%. This contrast, with the within-paper experiment, is the evidence that access bounds agreement. Two caveats apply. The same model family judged both what the text states and what the draft conveys, so this analysis supports the hidden-full-text experiment and does not stand alone. And the restriction has a ceiling of its own: on facts stated in abstract-only papers the reading strategies convey 95.5--97.1\% and most entries tie. Case table first is the exception: its deficit is larger on stated facts than overall, and largest on facts stated in full-text papers ($-8.4$ points; Table~\ref{tab:stated}).
```

## 22. subsection{Strategies compared on the facts the supplied text states} (figure/table caption) (v3 l. 209 / v4 l. 211)

- Edits: Figure 4 caption
- Sources: Number check 11; D8

Old:

```latex
\caption{Paired difference from direct reading in OMIM facts conveyed (points, means over entries, 95\% intervals) by the share of an entry's references readable in full; the one entry with all references in full text is in no group. Shaded: replicate-noise half-widths over 93 ($\pm$1.0) and 30 entries ($\pm$1.8), a yardstick, not a test. Memory-based strategies are off scale ($-18.1$ to $-59.6$; Appendix Table~\ref{tab:app_strata}). Observational.}
```

New:

```latex
\caption{Paired difference from direct reading in OMIM facts conveyed (points, means over entries, 95\% intervals) by the share of an entry's references readable in full; the one entry with all references in full text is in no group. Shaded: replicate-noise half-widths for a difference over 93 entries ($\pm$1.0) and over 30 entries ($\pm$1.8), a yardstick, not a test; the groups have 21--46 entries, so the $\pm$1.8 band is the nearer guide. Memory-based strategies are off scale ($-18.1$ to $-59.6$; Appendix Table~\ref{tab:app_strata}). Observational.}
```

## 23. subsection{Entries with more full text: an observational comparison} (v3 l. 221 / v4 l. 223)

- Edits: Sec. 4.4; Sec. 4.4 ablation-set explanation; Sec. 4.4 first sentence
- Sources: E; E (length); E (length; the same statement is in the Figure 4 caption)

Old:

```latex
Grouping the 93 entries by the share of references readable in full gives 46 with none, 25 with under half and 21 with half or more; the one entry with all references in full text is in no group (Figure~\ref{fig:strata}; Appendix Table~\ref{tab:app_strata}). It is observational: across entries, few per group, confounded with creation date and journal. One pattern is consistent across analyses: case table first falls behind where full text is readable ($-4.0$ ($-6.3$ to $-2.0$) and $-6.1$ ($-8.3$ to $-3.6$) points in the groups with full text against $+0.6$ ($-0.3$ to $+1.6$) without; $-8.4$ on facts stated in full-text papers). The evidence graph is not consistent: $-1.8$ ($-4.4$ to $+0.7$) in the top group, but $+1.7$ on facts stated in full-text papers and $+1.0$ ($-0.9$ to $+2.8$) on the 38 entries of the matched ablation. The ablation reuses the main run's drafts for direct reading, the evidence graph and case table first, so the estimates differ only in the entries averaged: on the ablation's 19 entries with half or more full text the evidence graph's difference is $-1.2$ ($-3.8$ to $+1.3$), and on its other 19 it is $+3.1$ ($+1.0$ to $+5.6$). The agentic curator, too, trails in the top group ($-2.0$, $-3.4$ to $-0.7$) but not on facts stated in full-text papers ($-0.2$). We therefore do not claim that the reading strategies in general separate where more full text is readable.
```

New:

```latex
Grouping the 93 entries by the share of references readable in full gives 46 with none, 25 with under half and 21 with half or more (Figure~\ref{fig:strata}; Appendix Table~\ref{tab:app_strata}). It is observational: across entries, few per group, confounded with creation date and journal. One pattern is consistent across analyses: case table first trails where full text is readable ($-4.0$ and $-6.1$ points in the two groups with full text, against $+0.6$ without; Figure~\ref{fig:strata}). The evidence graph is not consistent: it is at $-1.8$ points in the top group but $+1.7$ on facts stated in full-text papers, and $+1.0$ on the entries of the matched ablation. The ablation reuses the main run's drafts, so the estimates differ only in the entries averaged: on its entries with half or more full text the evidence graph is at $-1.2$, on the others at $+3.1$ (Appendix~\ref{app:ablation}). The agentic curator, too, trails in the top group ($-2.0$) but not on facts stated in full-text papers ($-0.2$). We therefore do not claim that the reading strategies in general separate where more full text is readable.
```

## 24. subsection{What the audit can and cannot see} (v3 l. 225 / v4 l. 227)

- Edits: Sec. 4.5 What it removes; Sec. 4.5 audit control
- Sources: E

Old:

```latex
\textbf{What it removes.} The memory-only control, audited but never repaired, has 50.8\% of claims judged supported, 22.1\% unsupported and 0.6\% contradicted; the other paradigms reach 94.2--96.5\% judged supported. In 60 paragraphs the audit had passed, one fact was altered by rule (a count, a zygosity, a residue or a mode of inheritance); the audit flagged all 60, each on a claim with the altered value. This planted-error test is not a sensitivity estimate: it shows that blunt single-value substitutions in paragraphs the audit had passed are caught. Re-audited unaltered with fresh model calls, the same 60 paragraphs drew no flag (0 of 361 claims flagged; 6 partly supported, 3 not auditable): the rate at which a re-audit flags a paragraph that had passed once, not a false-flag rate on arbitrary paragraphs. Omissions and misattributed citations remain untested.
```

New:

```latex
\textbf{What it removes.} The memory-only control, audited but never repaired, has 50.8\% of claims judged supported, 22.1\% unsupported and 0.6\% contradicted. After repair, the other strategies reach 94.2--96.5\% judged supported. In 60 paragraphs the audit had passed, one fact was altered by rule (a count, a zygosity, a residue or a mode of inheritance); the audit flagged all 60, each on a claim with the altered value. This planted-error test is not a sensitivity estimate: it shows that blunt single-value substitutions in paragraphs the audit had passed are caught. Re-audited unaltered with fresh model calls, the same 60 paragraphs drew no flag (0 of 361 claims flagged): the rate at which a re-audit flags a paragraph that had passed once, not a false-flag rate on arbitrary paragraphs. Omissions and misattributed citations remain untested.
```

## 25. subsection{What the audit can and cannot see} (v3 l. 227 / v4 l. 229)

- Edits: Sec. 4.5 What it cannot see
- Sources: E

Old:

```latex
\textbf{What it cannot see.} Of 112 claims about hidden papers whose supporting quote came from a later paper's passage, the full text supports 74, partly supports 24, does not support 11 (an upper bound, as supplements are excluded) and contradicts 3; an audit against what the writer saw passes them. The audit checks fidelity, not correctness: a draft that copies a source's error passes. Of 37 facts on which a direct-reading draft contradicted the reference, the same model judged the paper to support the draft in 22 (13 undecidable): unconfirmed leads.
```

New:

```latex
\textbf{What it cannot see.} Of 112 claims about hidden papers whose supporting quote came from a later paper's passage, the full text does not support 11 (an upper bound, as supplements are excluded) and contradicts 3 (Appendix Table~\ref{tab:app_secondhand_claims}); an audit against what the writer saw passes them. The audit checks fidelity, not correctness: a draft that copies a source's error passes. Of 37 facts on which a direct-reading draft contradicted the reference, the same model judged the paper to support the draft in 22 (13 undecidable): unconfirmed leads.
```

## 26. subsection{The memory-only control as a contamination check} (v3 l. 231 / v4 l. 233)

- Edits: Sec. 4.6; Sec. 4.6 memory; Sec. 4.6 memorisation sentence (wording made no stronger than the log)
- Sources: Number check 12; D6; E; E (length); D6; notes compliance; D6; E (length)

Old:

```latex
The memory-only control conveys 5.7\% of facts for entries from 620000 onward (12.6--24.1\% for older bands) and 7.0\% on the 2026 entries, against 52.2\% for direct reading (Figure~\ref{fig:memory}): memory alone contributes little for the newest entries. This does not show that reading results are free of memorisation: a fact the abstract states may also be recalled, and within abstract-only papers direct-reading coverage declines from 49.8\% (600000--609999) to 37.9\% (620000 onward; pooled).
```

New:

```latex
The memory-only control conveys 5.7\% of facts for the newest band (12.6--24.1\% for older ones; Figure~\ref{fig:memory}) and 7.0\% on the 2026 entries: memory alone contributes little there. Nor are reading results shown free of memorisation: within abstract-only papers, direct-reading coverage (pooled) falls from 49.8\% in the second-oldest band to 37.9\% in the newest, consistent with memory helping on older entries and not separated from reading; the classic band is lowest (33.0\%).
```

## 27. subsection{Matched ablation of the extract-then-write implementations} (v3 l. 235 / v4 l. 237)

- Edits: Sec. 4.7; Sec. 4.7 last sentence
- Sources: Number check 13; D1; E; E (length)

Old:

```latex
On 40 entries weighted towards full text (22 with at least half their papers in full text, 29 with at least one; 38 compared), \emph{matched} raises per-paper extraction to high effort and lets the writer choose synopsis terms (and, for case table first, inheritance); \emph{plus text} also gives the writer the papers' text. Matching moves case table first from $-2.3$ to $-0.2$ points against direct reading (matched minus original $+2.1$, $+1.1$ to $+3.2$) and the evidence graph from $+1.0$ ($-0.9$ to $+2.8$) to $+1.8$ ($+0.4$ to $+3.3$; Appendix Tables~\ref{tab:app_abl_means}--\ref{tab:app_abl_diff}). The two changes in \emph{matched} were made together. Choosing synopsis terms cannot change which facts are extracted, so we attribute the gain in facts to extraction effort; that attribution is an inference, not a separate measurement. Adding the papers' text raises claims judged supported but not facts.
```

New:

```latex
On 40 entries weighted towards full text (38 compared; Appendix~\ref{app:ablation}), \emph{matched} raises per-paper extraction to high effort and lets the writer choose synopsis terms (and, for case table first, inheritance); \emph{plus text} also gives the writer the papers' text. Matching moves case table first from $-2.3$ to $-0.2$ points against direct reading; the step itself is $+2.1$ points ($+1.1$ to $+3.2$). It moves the evidence graph from $+1.0$ to $+1.8$; that step, $+0.8$ ($-0.5$ to $+2.1$), is not distinguishable from zero (Appendix Tables~\ref{tab:app_abl_means}--\ref{tab:app_abl_diff}). The two changes in \emph{matched} were made together, but choosing synopsis terms cannot change which facts are extracted, so we attribute case table first's gain in facts to extraction effort, as an inference. Adding the text raises claims judged supported, not facts.
```

## 28. subsection{Add-ons: a small gain with costs, two results indistinguishable from zero} (v3 l. 237 / v4 l. 239)

- Edits: Sec. 4.8 title
- Sources: Number check 14; Number check 14; E (one line)

Old:

```latex
\subsection{Add-ons: one small gain with costs, and two nulls}
```

New:

```latex
\subsection{Add-ons: a small gain with costs, two results indistinguishable from zero}
```

## 29. subsection{Add-ons: a small gain with costs, two results indistinguishable from zero} (v3 l. 239 / v4 l. 241)

- Edits: Sec. 4.8 text; Sec. 4.8 second-hand evidence
- Sources: Number check 2, 14, 15; D7; E; Number check 15; D7; E (length)

Old:

```latex
\textbf{Second-hand evidence} raises OMIM facts conveyed by $+1.8$ points ($+1.0$ to $+2.8$; 96 entries) but also unsupported claims before repair (0.4\% to 3.9\%). \textbf{The learned curation guide} did not improve its own training entries and changed facts by $+1.0$ ($+0.0$ to $+2.0$) on 68 held-out entries. \textbf{Reconciliation} changed facts by $+0.1$ ($-0.1$ to $+0.4$) and no other score; the case database was not validated against per-patient ground truth (Appendices~\ref{app:hidden}--\ref{app:addons}).
```

New:

```latex
\textbf{Second-hand evidence} raises OMIM facts conveyed by $+1.8$ points on 96 entries (Appendix Table~\ref{tab:app_secondhand}). It also raises unsupported claims before repair (0.4\% to 3.9\%) and contradictions with the reference (0.4\% to 0.7\% of facts). \textbf{The learned curation guide} did not improve its own training entries; on the held-out entries its difference in facts, $+1.0$ points ($+0.0$ to $+2.0$), is not distinguishable from zero (Appendix Table~\ref{tab:app_guide}). \textbf{Reconciliation} changed no score by more than 0.1 point (Appendix Table~\ref{tab:app_recon}); the case database was not validated against per-patient ground truth.
```

## 30. section{Discussion and Limitations} (v3 l. 243 / v4 l. 245)

- Edits: Sec. 5 Discussion, first sentences; Sec. 5 Discussion, case table sentence; Sec. 5 first sentence
- Sources: D2; B; D1; Number check 16; E (length); D2; E (length)

Old:

```latex
In the regime tested (2--12 references, 19\% of papers readable in full, inputs that fit one prompt, one model), what the strategy was given to read limits agreement far more than how it reads. Case table first falls behind where full text is readable; whether the others separate there is not settled. \textbf{Measurement lessons:} handle stopped replies symmetrically; fix fact lists before scoring; compare strategies on the facts the supplied text states, to separate reading from access; report run-to-run noise beside intervals over entries; and match settings unrelated to the representation before blaming it.
```

New:

```latex
For this model and in the regime tested (2--12 references, 19\% of papers readable in full, inputs that fit one prompt), what limits agreement with curator-written text is access to the source, far more than how the strategy reads. Our case-table-first implementation trails, most where full text is readable (overall, an interval that excludes zero but a sign test that does not reach 0.05); whether the other strategies separate there is not settled. \textbf{Measurement lessons:} handle stopped replies symmetrically; fix fact lists before scoring; compare strategies on the facts the supplied text states, to separate reading from access; report run-to-run noise beside intervals over entries; and match settings unrelated to the representation before blaming it.
```

## 31. section{Discussion and Limitations} (v3 l. 245 / v4 l. 247)

- Edits: Sec. 5 Limitations (vi); Sec. 5 Limitations; Sec. 5 Limitation (iv); Sec. 5 Limitation (ix)
- Sources: D7; E (length); E (wording)

Old:

```latex
\textbf{Limitations.} (i) One model family wrote, audited and judged everything, including what the supplied text states; no human has read any draft, verdict or fact judgement, and whether the strategies stay close for other model families is unknown. (ii) The reference is indirect and narrow (variant-centred paragraphs, two-source ontology annotations, gene and inheritance tables; no narrative sections); other draft content is checked only by the audit. (iii) Every strategy is given the curators' reference list (retrieval was tested on ten entries; Appendix~\ref{app:updates}). (iv) Only open-access text without supplementary material was available; whether a conveyed fact the abstract states was read or recalled cannot be separated. (v) Variant names are not validated against sequences; inheritance is compared as coarse classes. (vi) Strategies were developed on the main entries; the 2026 set has 20 compared entries and five strategies. (vii) Stopped replies remove entries unevenly. (viii) Entries with few references dominate, and inputs too large for one prompt were not tested (Appendix~\ref{app:large}). (ix) The audit was not tested on omissions or misattributed citations. (x) Cost is at list price for one model.
```

New:

```latex
\textbf{Limitations.} (i) One model family wrote, audited and judged everything, including what the supplied text states; no human has read any draft, verdict or fact judgement; other model families are untested. (ii) The reference is indirect and narrow (variant-centred paragraphs, two-source ontology annotations, gene and inheritance tables; no narrative sections); other draft content is checked only by the audit. (iii) Every strategy is given the curators' reference list (retrieval was tested on ten entries; Appendix~\ref{app:updates}). (iv) Only open-access text without supplements was available; reading and recall of facts the abstract states cannot be separated. (v) Variant names are not validated against sequences; inheritance is compared as coarse classes. (vi) Strategies were developed on the main entries; the 2026 set has 20 compared entries, five strategies and frequent stopped replies. (vii) Stopped replies remove entries unevenly. (viii) Entries with few references dominate, and inputs too large for one prompt were not tested (Appendix~\ref{app:large}). (ix) The audit was not tested on omissions or misattributions. (x) Cost is at list price for one model.
```

## 32. section{Conclusion} (v3 l. 251 / v4 l. 253)

- Edits: Sec. 6 Conclusion; Sec. 5 first sentence
- Sources: D2; Number check 16; E; D2; E (length)

Old:

```latex
On 100 OMIM entries drafted by one model from exactly the cited papers, what limits agreement with curator-written text is access to the source. Hiding the full text of the same papers lowers coverage from 79.8\% to 36.1\%; three reading strategies convey 93.6--94.4\% of the facts the supplied text states and almost none of the rest. Case table first falls behind where full text is readable. No judgement was validated by a person.
```

New:

```latex
For this model and in the regime tested, what limits agreement with curator-written text is access to the source. Hiding the full text of the same papers lowers coverage from 79.8\% to 36.1\%; three reading strategies convey 93.6--94.4\% of the facts the supplied text states. Our case-table-first implementation trails where full text is readable. No judgement was validated by a person.
```

## 33. section{Main comparison: full results} (figure/table caption) (v3 l. 390 / v4 l. 392)

- Edits: App. C, caption of Table app_paired
- Sources: B

Old:

```latex
\caption{Paired differences from direct reading on the 93 compared entries: points (means over entries), bootstrap 95\% interval, entries better/worse/same.}
```

New:

```latex
\caption{Paired differences from direct reading on the 93 compared entries: points (means over entries), bootstrap 95\% interval, entries better/worse/same. Sign tests and Holm-adjusted results are in Table~\ref{tab:app_sign}.}
```

## 34. section{Main comparison: full results} (figure/table caption) (v3 l. 406 / v4 l. 408)

- Edits: new table inserted after Table app_paired
- Sources: B (new appendix Table app_sign, copied from log 2.3a)

Old:

```latex
(none)
```

New:

```latex
\bottomrule
\end{tabularx}
\end{table}

\begin{table}[!htbp]
\caption{Sign tests on the 93 compared entries: exact two-sided sign test on the paired differences from direct reading (ties dropped). The primary endpoint is not adjusted. For the secondary headline measures the sign-test $p$-value was adjusted by Holm's method across those measures within each strategy; the last column lists the measures whose adjusted $p$ is below 0.05, with adjusted $p$ and the mean paired difference in points.}
\label{tab:app_sign}
\scriptsize
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{2.4cm}>{\centering\arraybackslash}p{2.6cm}>{\centering\arraybackslash}p{1.4cm}>{\raggedright\arraybackslash}X}
\toprule
Strategy minus direct reading & Primary endpoint: sign test $p$ (better / worse / tied) & Secondary headline measures & \ldots{} with Holm-adjusted $p<0.05$ \\
\midrule
Evidence graph & 0.213 (33 / 45 / 15) & 8 & none \\
Agentic curator & 0.242 (31 / 42 / 20) & 8 & none \\
Memory only (control) & $<$0.001 (7 / 85 / 1) & 8 & Claims supported by cited paper ($<$0.001; $-$45.3); claims unsupported or contradicted, before the repair round ($<$0.001; +22.4); OMIM allelic variants recovered ($<$0.001; $-$51.3); causal gene F1 (0.011; $-$13.6) \\
Recall, then verify & $<$0.001 (2 / 89 / 2) & 8 & Clinical synopsis HPO F1, exact ($<$0.001; $-$11.0); clinical synopsis HPO F1, hierarchical ($<$0.001; $-$15.7); OMIM allelic variants recovered ($<$0.001; $-$54.9); causal gene F1 (0.002; $-$14.7); inheritance matches OMIM ($<$0.001; $-$20.4) \\
Case table first & 0.071 (31 / 48 / 14) & 8 & none \\
```

## 35. section{Measurement stability} (v3 l. 722 / v4 l. 741)

- Edits: App. E Measurement stability prose
- Sources: Number check 3

Old:

```latex
Judge variation: the same drafts and fact lists judged three times (top). Evidence graph minus direct reading in the three judgings: $+0.7$/$+0.5$/$+1.3$ points; per-fact agreement between two judgings of the same draft: 3,498 of 3,654 statuses (95.7\%). Run-to-run variation: generation, audit and scoring repeated three times on 30 entries (bottom). Evidence graph minus direct reading in replicates 1/2/3: $+0.7$/$+1.9$/$+0.5$ points; within-entry SD of that paired difference 5.0 points, giving a replicate-noise 95\% half-width of 1.0 point over 93 entries and 1.8 points over 30. One replicate is one sample; the main comparison is a single run per entry. The half-width is a yardstick for how much a difference of this kind moves when generation, audit and scoring are repeated; the bootstrap interval over entries is the test of a difference. On these 30 entries the evidence graph is ahead of direct reading in all three replicates and all three judgings, whereas on the 93 entries of the main comparison its difference is $-0.5$ ($-1.5$ to $+0.5$). Crediting a fact anywhere in the draft rather than only in text citing its paper (same 30 entries): direct reading 46\% against 47\%, evidence graph 46\% against 46\%, case table first 45\% against 45\%, so strategies that pool across papers do not lose credit under another citation.
```

New:

```latex
Judge variation: the same drafts and fact lists judged three times (top). Evidence graph minus direct reading in the three judgings: $+0.7$/$+0.5$/$+1.3$ points; per-fact agreement between two judgings of the same draft: 3,498 of 3,654 statuses (95.7\%). Run-to-run variation: generation, audit and scoring repeated three times on 30 entries (bottom). Evidence graph minus direct reading in replicates 1/2/3: $+0.7$/$+1.9$/$+0.5$ points; within-entry SD of that paired difference 5.0 points, giving a replicate-noise 95\% half-width of 1.0 point over 93 entries and 1.8 points over 30. One replicate is one sample; the main comparison is a single run per entry. The half-width is a yardstick for how much a difference of this kind moves when generation, audit and scoring are repeated; the bootstrap interval over entries is the test of a difference. On these 30 entries the evidence graph is ahead of direct reading in all three replicates and all three judgings, whereas on the 93 entries of the main comparison its difference is $-0.5$ ($-1.5$ to $+0.5$). Replicate 1 reproduces the main run on these entries, so the difference in sign comes from which entries are averaged, not from replicate noise; the replicates themselves range from $+0.5$ to $+1.9$. Crediting a fact anywhere in the draft rather than only in text citing its paper (same 30 entries): direct reading 46\% against 47\%, evidence graph 46\% against 46\%, case table first 45\% against 45\%, so strategies that pool across papers do not lose credit under another citation.
```

## 36. section{Reconciled case database and learned curation guide} (v3 l. 947 / v4 l. 966)

- Edits: App. H Reconciliation, planted test
- Sources: Number check 17; D7

Old:

```latex
\textbf{Reconciliation.} Over the 100 entries, reconciliation proposed 57 merges of patient or family records and accepted 40 (17 rejected by the verifier) in 27 entries; it merged 11 variant names and found 57 conflicts between papers. Counted individuals went from 2,580 to 2,413 (net; counts rose in a few entries where a re-report gave a larger family size) and families from 1,126 to 1,092. A planted test on six entries merged 10 of 10 copied reports with their originals and no unrelated records. The accepted merges were not checked by a person. Cost: one or two extra calls per entry. None of the entry-level measures uses patient counts, so no change in them is expected. Agreement of the table's patient-count fractions with those in the HPO annotations (about 560 terms) was 48\% before and after, with a mean absolute difference of 0.26; each reference fraction comes from one source while the table pools all papers.
```

New:

```latex
\textbf{Reconciliation.} Over the 100 entries, reconciliation proposed 57 merges of patient or family records and accepted 40 (17 rejected by the verifier) in 27 entries; it merged 11 variant names and found 57 conflicts between papers. Counted individuals went from 2,580 to 2,413 (net; counts rose in a few entries where a re-report gave a larger family size) and families from 1,126 to 1,092. A planted test on six entries merged 10 of 10 copied reports with their originals and merged no unrelated records; this easy case shows only that a stated re-report is caught. The accepted merges were not checked by a person. Cost: one or two extra calls per entry. None of the entry-level measures uses patient counts, so no change in them is expected. Agreement of the table's patient-count fractions with those in the HPO annotations (about 560 terms) was 48\% before and after, with a mean absolute difference of 0.26; each reference fraction comes from one source while the table pools all papers.
```

## Not applied, or applied with a deviation

- Number check 3 (replicate sentence, Sec. 4.2): the corrected one-clause explanation was first written, then the sentence was
  deleted from the main text for length (the brief allowed deletion). The correct explanation (replicate 1 reproduces the main
  run on those entries; the sign differs because of which entries are averaged; replicates range +0.5 to +1.9) is now in
  Appendix E (entry 35).
- Number check 5: the brief's B section replaced its correction; the statistics paragraph now describes what is reported
  (bootstrap interval, better/worse/tied, exact sign test with Holm across the eight secondary headline measures within each
  strategy, primary unadjusted), and the Holm-adjusted results are now reported (log 2.3a).
- Number check 9: applied as two sentences in Sec. 4.2 (20 of 30 compared, five strategies, stopped replies frequent).
- Number check 13: the evidence graph's step is given as +0.8 (-0.5 to +2.1), not distinguishable from zero; the
  attribution is to case table first's gain.
- Number check 14: the guide is described as "not distinguishable from zero" (brief D7) rather than the number check's
  "not clearly distinguishable"; section title: "a small gain with costs, two results indistinguishable from zero"
  (reconciliation's facts difference +0.1, -0.1 to +0.4, is also indistinguishable from zero).
- Number check 16: the Conclusion carries "for this model and in the regime tested" (brief D2) rather than the full
  parenthetical; the parenthetical regime is in the Discussion.
- Citation check, CGBench sentence: worded to the abstract ("built from ClinGen's expert-curated literature
  interpretations, scores model explanations against human explanations, but compares models rather than generation
  strategies"). The abstract does not say "individual publications", so that phrase was not used. To keep the Introduction
  consistent with it, "compares models rather than strategies" was added to the Introduction's list of how the closest work
  differs (entry 2).
- Citation check, Balhoff credit: worded to the abstract ("agents working in a workspace that supplies the source
  publication").
- E, compact experiments table in the main text: not added; the main text needed trimming to stay within 10 pages.

## Numbers new to the paper in this pass

| Number | Where | Log section |
|---|---|---|
| Sign-test p 0.213 (evidence graph), 0.242 (agentic curator), 0.071 (case table first) on the primary endpoint | Intro (0.071), Sec. 4.2, App. Table app_sign | 2.3a |
| Primary endpoint p < 0.001 for memory only and recall, then verify | Sec. 4.2, App. Table app_sign | 2.3a |
| 8 secondary headline measures; Holm-adjusted p < 0.05 for none / none / none (graph, curator, table), four measures (memory only), five (recall, then verify) | Sec. 3.3 ("eight"), Sec. 4.2, App. Table app_sign | 2.3a |
| Holm-adjusted p 0.011 (memory only, causal gene F1) and 0.002 (recall, then verify, causal gene F1); the other listed adjusted p are < 0.001 | App. Table app_sign | 2.3a |
| 0.05 (significance threshold of the sign test) | Intro, Sec. 4.2, Sec. 5 | 2.3a ("below 0.05") |
| "no score by more than 0.1 point" (reconciliation) | Sec. 4.8 | 7 (largest absolute paired difference in the table is 0.1) |

Numbers new to the main text only (already in the appendix of v3): 33.0% classic band, abstract-only papers, direct reading
(log 2.10); facts contradicted 0.4% to 0.7% with second-hand evidence (log 6.3); evidence graph matched step +0.8 (-0.5 to
+2.1) (log 5); "21-46 entries" per access group in the Figure 4 caption (log 2.9); 20 of 30 entries for the 2026 set
(log 10); 68 held-out entries attached to the 24% figure (log 8). In Appendix E the replicate range "+0.5 to +1.9" restates
the replicate values already given there (log 4.2).
