# Improving direct reading: published evidence for candidate methods

Prepared 2026-11-20. Each source was checked on a primary page (arXiv, ACL Anthology, publisher, PMC/Europe PMC or
vendor documentation) on that date; URLs are in the reference list. PubMed's site blocked automated reading, so PubMed
records were read through the Europe PMC API. In-repo measurements are cited by file. "Shown" means a source measured
it. "Expected here" is my inference and has not been measured.

**Where the headroom is.** Of all OMIM facts, 43% were conveyed, 4% were stated in the supplied text and left out, 13%
were partly stated and 40% were in no text the pipeline could read (`README.md`, finding 3). So methods that only read
the supplied text better can add about 4 points plus part of the 13. The union of three runs (+3.3) already covers most
of that ceiling, which suggests that many omissions are a matter of which facts a given run picks, not facts the model
cannot get. Methods that widen access work on the 40%.

## Summary

| # | Method | Mechanism | Best evidence | Expected effect on facts conveyed | Added calls / entry | Main risk |
|---|---|---|---|---|---|---|
| 1 | Expanded legal access | Read full text of free-to-read but unlicensed papers | In-repo: abstract 31.2% vs full text 77.4% on the same papers; full-text mining beats abstracts [R2] | **Large**: about a third of facts sit on such papers; up to +10–15 pts if all were read in full | 0 (more input tokens) | Licence/TDM terms; version differences |
| 2 | Supplement parsing | Add supplementary tables and text | Supplements raised curated-variant recall 2→53% and 8→46% [R7]; ~85% of LitVar variants are supplement-only [R8] | **Small**: OMIM facts mostly come from the main text; helps counts, zygosity and controls | 0–1 | Huge, noisy tables; parsing errors |
| 3 | Omission check and revise | Second pass lists stated-but-missing facts, then revises | Omission step raised recall and lowered precision in clinical IE [R11]; self-reflection +1.8 recall pts on RCT extraction [R15] | **Small**: +1–2 pts; aimed straight at the 4-pt gap | +1 (or +2) | Padding; drift from house style |
| 4 | Long-context layout, quotes first | Task after documents; quote then write | Vendor: "up to 30%" from queries at the end [R16]; position bias persists but is shrinking [R19, R20] | **None–small**: inputs are short; in-repo padding showed no loss | 0 | Quote-first can cut correctness [R23] |
| 5 | Schema/checklist prompt | Name every field curators record | Customised prompts +15 recall pts [R15]; guidelines + error rules raised GPT-4 recall [R25] | **Small**: +0.5–2 pts; the prompt already has half the checklist | 0 | Over-inclusion of trivia |
| 6 | Per-paper map then reduce | One call per paper, then assemble | Chain of Agents beat 200k full context on very long inputs [R27]; in-repo −1.9 to +1.8 pts | **None–small** at 5k–150k tokens | +n papers (2–12) +1 | Cost 2–3×; merge errors |
| 7 | Sample ensemble + merge | Several drafts, merge the facts they agree on | Atomic self-consistency raised recall over USC [R29]; model ensemble +5.9 recall pts [R15] | **Small–moderate**: +1.5–2.5 pts; in-repo ceiling +3.3 | +2–3 drafts +1 merge | Duplicates, longer entries, added errors |
| 8 | More test-time compute | Raise effort (xhigh/max) | Higher reasoning budget does not reliably improve summaries [R32]; inverse scaling with distractors [R33] | **None–small**; the writer already runs at `high` | 0 (more output tokens) | Cost; overthinking |
| 9 | Few-shot exemplar entries | Show curated entries for granularity | 5 examples raised GPT-4 recall [R25]; ICL beat experts on completeness [R35] | **Small**: 0–1.5 pts; the learned guide did nothing measurable here | 0 (+5–15k cached tokens) | Copying facts from exemplars |
| 10 | Question-driven filling | Per paper/field questions answered against text | CoVe lowers hallucination (a precision gain) [R36]; omission step [R11] | **Small**: 0–1.5 pts | +n to +n×q | Cost; in-repo PaperQA2 −14.5 pts |
| 11 | Citation contexts | Use later papers' descriptions of unreadable papers | Citances cover most of the abstract plus 20% more concepts [R37]; in-repo +1.8 pts | **Small** (measured here) | Retrieval + ~1 | 25% quotation-error base rate [R38] |
| 12 | Prompt optimisation | Search prompts against the fact scorer | GEPA beats MIPROv2 and GRPO across six tasks [R40] | **None–small**: in-repo learned guide +1.0 (0.0–2.0) | 0 at run time; large one-off | Overfitting to the scorer |
| 13 | *Added:* figures and pedigrees as images | Give the model figure and pedigree images | A major portion of AutoPM3's false negatives came from supplements or figures [R9] | **Unknown–small** | 0–1 | No published effect size |

## 1. Expanded legal access to full text

**Mechanism.** Find more readable copies of each cited paper: OA locations (publisher, PMC, repositories, preprints,
accepted manuscripts) from OpenAlex/Unpaywall [R4], PMC's Author Manuscript Dataset (licensed for text mining) [R3],
and publisher full-text links declared for TDM in Crossref metadata, usable under institutional TDM terms [R5].

**Evidence.** In-repo, hiding the full text of the same papers dropped conveyed facts from 77.4% to 31.2%: a
paired difference of 43.9 points, higher in 45 of 46 entries. Across 15M articles, full text consistently beat
abstracts; for disease–gene associations the AUC rose from 0.85 to 0.91 [R2]. Bronze OA (free on the publisher site
with no open licence) was the commonest kind of OA [R1]. That matches the third of facts on papers that are free but
unlicensed. Preprints change little: discrete changes in conclusions occurred in 7.2% of non-COVID abstracts [R6].

**Transfer.** Direct, because it is measured on this task. **Expected:** the largest lever. If those papers were read in
full, the third of facts on them would move from about 40% to about 78% conveyed, roughly +12 points. The real gain
scales with the share that can lawfully be mined. Being free to read does not grant mining rights [R3, R5], so this
needs licence review. **Calls:** 0 added; input grows from about 330 to 8,700 tokens per paper. **Risk:** licence breaches;
an accepted manuscript differing from the version of record.

## 2. Supplementary material

**Mechanism.** Fetch supplements (the Europe PMC `supplementaryFiles` endpoint returned a zip for an OA test article
[R10]), convert tables to text, and append them, filtered to rows that mention the gene or variants.

**Evidence.** For COSMIC and InSiGHT, recall of curated variants rose from 2% to 53% and from 8% to 46% once supplements
were mined [R7]. Most unique variants in LitVar 2.0 (~85%) appear only in supplements, though large sequencing tables
dominate that count [R8]. In AutoPM3 (ClinGen PM3 evidence), a major portion of false negatives came from
supplements or figures [R9]. The pipeline's full texts exclude supplements (`results/omim100_secondhand/secondhand_check.md`).

**Transfer.** Partial. OMIM's text cites a few landmark variants plus counts, controls, zygosity and ancestry, which
supplements often tabulate, but it applies only to papers whose full text is readable. **Expected:** +0.5–1.5. **Calls:**
0–1. **Risk:** inputs of hundreds of thousands of tokens, and table rows misread out of context.

## 3. Omission check and revise

**Mechanism.** After the draft, a call compares the papers with the draft and lists facts the text states that the
draft leaves out. A second step, which can be the same call, revises the draft. Chain of Density does the same thing at
a fixed length [R12]; Self-Refine is the general loop [R13].

**Evidence.** In self-verification for clinical IE (GPT-3.5/GPT-4-0314, short notes), the omission step raised recall,
for example from 0.928 to 0.946 for medication names, while precision fell. A pruning step restored precision, and F1
rose 0.056 on average [R11]. On full-text RCT extraction, self-reflection lifted recall only from 0.572 to 0.590 [R15].
Intrinsic self-correction of reasoning can degrade answers [R14]. CoD readers preferred denser summaries, but
informativeness traded against readability [R12].

**Transfer.** Moderate. It targets exactly the stated-but-omitted facts, and the source text is in context, so the check
is grounded, unlike reasoning self-correction. Evidence comes from older models. **Expected:** +1–2 points, with a
small faithfulness cost that the existing audit can catch. **Calls:** +1 or +2. **Risk:** filler, and the entry growing
beyond OMIM's register.

## 4. Long-context layout and quote extraction

**Mechanism.** Put documents first and the task after them. At present the instructions sit in the system prompt and
nothing follows the papers (`src/aiomim/synthesize.py`). Ask the model to quote the relevant passages before writing.

**Evidence.** Anthropic's guidance says queries at the end "can improve response quality by up to 30 percent in tests,
especially with complex, multidocument inputs" [R16]. No test details are given. The only published test is from 2023
(Claude Instant/Claude 2, 70–95k-token multiple-choice QA): accuracy fell as the answer moved away from the end, and
quote scratchpads helped; Claude 2 went from 0.939 to 0.961 [R17]. Independent work: the original lost-in-the-middle
paper found query-aware placement barely helped multi-document QA [R18]. Later papers find a bias by distance from
the end [R19], smaller middle-position drops in newer models [R20], better SummHay scores with relevant documents at
the bottom (Claude 3 Opus 28.0 vs 20.4) [R22], over-emphasis on the end of books [R24], and accuracy falling with
length on simple tasks [R21]. Generating citations in the same pass cut correctness for GPT-4o from 78.2 to 69.4 [R23].

**Transfer.** Weak. Median input is about 5k tokens, and in-repo padding with up to 30× unrelated text lost no
coverage (`results/padding/`). **Expected:** 0–0.5 points. **Calls:** 0. **Check first:** conveyed rate by paper
position, since oldest-first places early papers far from the end.

## 5. Schema- or checklist-guided reading

**Mechanism.** List every field curators record. The house style already asks for counts, ancestry, consanguinity,
zygosity, segregation and functional evidence. It does not ask for population controls, animal models, age, sex or
onset, or variant detection method in every case.

**Evidence.** On full-text RCT extraction, prompts naming the target outcomes raised recall from 0.572 to 0.721
(statistics fields: 0.349 to 0.613) with precision about level [R15]. For clinical NER, annotation guidelines raised
GPT-4 relaxed recall from 0.852 to 0.919 (MTSamples) and error-analysis rules from 0.593 to 0.650 (VAERS) [R25]. On
ClinGen-derived tasks, models fell short on fine-grained protocol-following [R26].

**Transfer.** Good for the type of intervention; the gains were from low baselines with older models. **Expected:**
+0.5–2 points, concentrated in the categories most often missed. **Calls:** 0. **Risk:** listing every field invites
trivia OMIM omits, which costs no recall but lengthens entries.

## 6. Per-document map, then reduce

**Mechanism.** Each paper goes to its own call, which returns findings; a final call writes the entry.

**Evidence.** Chain of Agents (NeurIPS 2024) beat Claude 3 with 200k-token full context on NarrativeQA (Opus 6.6 to
24.0) and BookSum. Gains grew with input length, and the inputs were book-length [R27]. In-repo, per-paper strategies
came within noise of direct reading or below it: −0.5 (evidence graph) and −1.9 (case table) on 93 entries. At
matched effort, the evidence graph was +1.8 (+0.4 to +3.3) on 38 entries (`results/ablation40/strategies.md`).

**Transfer.** Direct in-repo evidence beats the literature. **Expected:** 0 to +2 points at about twice the cost
($0.56 vs $0.26). **Calls:** +n+1. **Risk:** lower variant precision, as seen in-repo.

## 7. Sampling ensembles and merging

**Mechanism.** Generate k drafts and merge the facts. Universal self-consistency only selects one draft [R28], so
merging is what raises recall.

**Evidence.** Atomic self-consistency (EMNLP 2024; ChatGPT, Llama, closed-book, 50 samples) raised ASQA from 37.1 to
44.1 and QAMPARI recall from 13.8 to 20.5. Precision held, but an inclusive variant cut it to 13.4 [R29]. A three-model
ensemble raised full-text RCT recall by 5.9 points and precision by about 2 [R15].

**Transfer.** Good. In-repo the union of three runs gives +3.3, and ASC captured a quarter to a third of its oracle gap.
**Expected:** +1.5–2.5 points. **Calls:** +2–3 drafts plus 1 merge; prompt caching makes the repeated paper input
cheap. **Risk:** duplicated or conflicting paragraphs, and more claims for the audit to repair.

## 8. Test-time compute

**Mechanism.** Raise effort above the writer's current `high` (`src/aiomim/config.py`) to `xhigh` or `max`.

**Evidence.** Anthropic recommends sweeping effort and reserving the top levels for measured gains. It also notes,
for some models, that effort "barely changes how long the model's replies are" [R30, R31]. Larger reasoning budgets did not reliably
improve summaries and could reduce factual consistency (o1/o3/GPT-5) [R32]. Longer reasoning made Claude models more
distractible [R33]. Reasoning helped long-context multiple-choice reasoning (o1-preview 57.7% vs 50.1%) [R34], which
is a different target.

**Expected:** 0–1 points. **Calls:** 0; output tokens increase. Cheap to sweep on a sample.

## 9. Few-shot exemplar entries

**Mechanism.** Add two or three OMIM entries, with their papers or excerpts, as `<example>`s [R16].

**Evidence.** For GPT-4, five annotated examples raised VAERS recall from 0.650 to 0.774 [R25]. In clinical
summarisation, even one in-context example "considerably improved performance", and GPT-4 summaries with in-context
examples were rated more complete than experts' [R35].

**Transfer.** Partial: those tasks had short inputs and copying formats. In-repo, a learned curation guide gave +1.0
(0.0 to +2.0, p 0.59) (`results/omim100_guided/strategies.md`). **Expected:** 0–1.5 points. **Risk:** facts leaking from
exemplars, though the audit would flag them as unsupported.

## 10. Question-driven filling

**Mechanism.** Ask fixed questions of each paper (patients? controls? model organism?) and write from the answers.

**Evidence.** Chain-of-Verification reduces hallucination: it is a precision method [R36]. The recall evidence is the
omission step [R11] and field-specific prompts [R15]. In-repo, a document-query pipeline (PaperQA2, 10 entries) conveyed 14.5 points
fewer than direct reading, and the tool-using agent 0.6 fewer.

**Expected:** 0–1.5 points; mostly redundant with items 3 and 5. **Calls:** +n to +n×q. **Risk:** cost, and answers
to questions the paper does not address.

## 11. Citation contexts for unreadable papers

**Evidence.** Citances to an article covered most of its abstract's information plus 20% more concepts [R37]. A
meta-analysis put total quotation errors in medical articles at 25.4% (major 11.9%) [R38]. In-repo second-hand
evidence gave +1.8 points (+1.0 to +2.8, 96 entries), raised variant recall by 5.0 points, and added unsupported and
contradicted claims (`results/omim100_secondhand/strategies.md`).

**Expected:** small but already measured. **Risk:** errors carried over from the citing paper.

## 12. Prompt optimisation

**Evidence.** DSPy pipelines beat standard few-shot prompting by more than 25% for GPT-3.5 [R39]. GEPA beats MIPROv2 by
more than 10% and GRPO by 6% on average across six tasks [R40]. I found no controlled study of its effect on
extraction recall. In-repo, the learned guide is the nearest analogue and had no clear effect.

**Expected:** 0–1 points. The fact scorer makes optimisation feasible, but it costs hundreds of scored runs, and the
optimiser can overfit to the scorer's quirks.

## 13. Added: figures and pedigrees as images

**Mechanism.** The full-text parser keeps captions and table text but drops images (`src/aiomim/sources/fulltext.py`).
Pedigrees encode consanguinity, zygosity, affected counts and sex, which are among the most-missed fact kinds. Page
images or figure files would be added for readable papers.

**Evidence.** Weak: AutoPM3 attributes many false negatives to figures and supplements [R9]; Anthropic claims better
chart reading for Opus 5.5 with no curation numbers [R31]. **Expected:** unknown. A 10-entry pilot would settle it.

## References

[EPMC] = record and abstract read through `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<PMID>&resultType=core`; numbers from full text came from that service's `fullTextXML` endpoint for the PMCID shown.

- R1 Piwowar H et al. The state of OA. PeerJ 2018;6:e4375. EPMC PMID 29456894 (peerj.com returned 403).
- R2 Westergaard D et al. Text-mining in 15 million full-text articles versus abstracts. PLoS Comput Biol 2018. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005962
- R3 PMC text mining collections. https://pmc.ncbi.nlm.nih.gov/tools/textmining/
- R4 OpenAlex Location object. https://help.openalex.org/api-entities/works/work-object/location-object
- R5 Crossref, Accessing full texts (TDM). https://www.crossref.org/documentation/retrieve-metadata/text-and-data-mining/
- R6 Brierley L et al. Changes between preprint and publication. PLoS Biol 2022. EPMC PMID 35104285
- R7 Jimeno Yepes A, Verspoor K. Importance of supplementary material. Database 2014. EPMC PMID 24520105, PMC3920087
- R8 Allot A et al. LitVar 2.0. Nat Genet 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC11096795
- R9 Li S et al. AutoPM3. Bioinformatics 2025. EPMC PMID 40586923, PMC12263107
- R10 Europe PMC supplementary files endpoint, live request: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3920087/supplementaryFiles
- R11 Gero Z et al. Self-verification improves few-shot clinical IE. 2023. https://arxiv.org/abs/2306.00024
- R12 Adams G et al. Chain of Density. NewSum 2023. https://aclanthology.org/2023.newsum-1.7/
- R13 Madaan A et al. Self-Refine. NeurIPS 2023. https://arxiv.org/abs/2303.17651
- R14 Huang J et al. LLMs cannot self-correct reasoning yet. ICLR 2024. https://arxiv.org/abs/2310.01798
- R15 Li L, Mathrani A, Susnjak T. LLMs for meta-analysis data extraction. 2025 (Table 2). https://arxiv.org/abs/2507.15152 ; https://arxiv.org/html/2507.15152v1
- R16 Anthropic, Prompting best practices: long context prompting; examples. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- R17 Anthropic, Prompt engineering for Claude's long context window, 2023. https://www.anthropic.com/news/prompting-long-context
- R18 Liu NF et al. Lost in the Middle. TACL 2024. https://aclanthology.org/2024.tacl-1.9/ ; https://arxiv.org/html/2307.03172
- R19 Veseli B et al. Positional biases shift as inputs approach context window limits. COLM 2025. https://arxiv.org/abs/2508.07479
- R20 Zhang C et al. Positional failures in long-context LLMs. 2026. https://arxiv.org/abs/2605.23170
- R21 Hong K, Troynikov A, Huber J. Context Rot. Chroma, 2025. https://www.trychroma.com/research/context-rot
- R22 Laban P et al. Summary of a Haystack. 2024. https://arxiv.org/abs/2407.01370 ; https://arxiv.org/html/2407.01370
- R23 Zhang J et al. LongCite. 2024. https://arxiv.org/html/2409.02897v3
- R24 Kim Y et al. FABLES. COLM 2024. https://arxiv.org/abs/2404.01261
- R25 Hu Y et al. Clinical NER via prompt engineering. JAMIA 2024. EPMC PMID 38281112, PMC11339492
- R26 Queen O, Zhang HG, Zou J. CGBench. NeurIPS 2025. https://arxiv.org/abs/2510.11985
- R27 Zhang Y et al. Chain of Agents. NeurIPS 2024. https://arxiv.org/html/2406.02818 ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/ee71a4b14ec26710b39ee6be113d7750-Abstract.html
- R28 Chen X et al. Universal Self-Consistency. 2023. https://arxiv.org/abs/2311.17311
- R29 Thirukovalluru R et al. Atomic Self-Consistency. EMNLP 2024. https://aclanthology.org/2024.emnlp-main.706/ ; https://arxiv.org/html/2405.13131v1
- R30 Anthropic, Effort. https://platform.claude.com/docs/en/build-with-claude/effort
- R31 Anthropic, Prompting Claude Opus 5.5. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- R32 Yuan H, Zhang H. Understanding LLM reasoning for abstractive summarization. 2025. https://arxiv.org/abs/2512.03503
- R33 Gema AP et al. Inverse scaling in test-time compute. TMLR 2025. https://arxiv.org/abs/2507.14417
- R34 Bai Y et al. LongBench v2. 2024. https://arxiv.org/abs/2412.15204
- R35 Van Veen D et al. Adapted LLMs outperform experts in clinical summarization. Nat Med 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11479659/
- R36 Dhuliawala S et al. Chain-of-Verification. Findings ACL 2024. https://aclanthology.org/2024.findings-acl.212/
- R37 Divoli A, Nakov P, Hearst MA. Do peers see more in a paper than its authors? Adv Bioinformatics 2012. EPMC PMID 23227044
- R38 Jergas H, Baethge C. Quotation accuracy in medical journal articles. PeerJ 2015. EPMC PMID 26528420
- R39 Khattab O et al. DSPy. 2023. https://arxiv.org/abs/2310.03714
- R40 Agrawal LA et al. GEPA. ICLR 2026. https://arxiv.org/abs/2507.19457

Not used as evidence (no primary page found or not relevant enough): EU DSM Directive TDM articles (EUR-Lex pages did
not render); Unpaywall data-format page (empty render; OpenAlex used instead).
