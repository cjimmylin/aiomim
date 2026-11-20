# Experiment B: published systems as released

Design: `docs/experiments-round2.md`, section B, at the reduced sizes. OMIM facts conveyed (present + half partial, over judged facts of the fixed lists); comparison strategies from run omim100 on the same entries. Paired differences from direct reading are in points: mean (bootstrap 95% interval over entries); better/worse/tied; exact sign test p. With 4 or 10 entries the intervals are wide and the sign test cannot reach p < 0.05 with 4 entries (the smallest possible p is 0.125): every result here is exploratory.

## What was run

| System | Package and version | Entry point | Entries attempted | Completed | Safety stops | Role |
|---|---|---|---|---|---|---|
| PaperQA2 | paper-qa 2026.8.12 | paperqa.Docs.aadd (one document per paper) + Docs.aquery (one per question) | 10 | 10 | 0 | main PaperQA2 result (whole-chunk embeddings) |
| PaperQA2, 512-token embedding cut | paper-qa 2026.8.12 | paperqa.Docs.aadd (one document per paper) + Docs.aquery (one per question) | 10 | 10 | 0 | sensitivity result (the shared embedder's 512-token cut) |
| GraphRAG local | graphrag 3.3.0 | `graphrag index --method standard` (CLI), then `graphrag.cli.query.run_local_search` per question with the CLI's defaults | 4 | 4 | 0 | main GraphRAG result (local search, the CLI's default) |
| GraphRAG global | graphrag 3.3.0 | the same indexes as GraphRAG local; `graphrag.cli.query.run_global_search` per question with the CLI's defaults | 4 | 4 | 0 | GraphRAG global search on the same indexes |
| STORM | knowledge-storm 1.1.1 | `STORMWikiRunner.run` (research, outline, article, polish) with its default arguments | 10 | 0 | 30 | no article produced |

STORM: completion 0 of 10. The model's safety filter stopped every chain-of-thought prompt of STORM's research stage (30 of 30 fresh requests; the 20 plain outline prompts were answered), so no article was produced; nothing was retried or reworded. There is nothing to score.

GraphRAG ran on 4 entries: the fixed rule takes entries in the seeded order while they fit in 1,000 model calls; the fifth entry (611521) did not fit in what was left, so the run stopped below the design's floor of 6.

## Side by side on the 4 entries every system completed

Entries: 615582, 616326, 620029, 621313.

| Measure | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 49.6% (n=4) | 49.6% (n=4) | 46.2% (n=4) | 46.0% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 51.6% (n=4) | 51.3% (n=4) | 47.3% (n=4) | 47.7% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 73.9% (n=4) | 75.2% (n=4) | 65.8% (n=4) | 68.2% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 2.1% (n=4) | 3.1% (n=4) | 4.1% (n=4) | 20.5% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 76.4% (n=4) | 76.5% (n=4) | 68.0% (n=4) | 67.4% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 4.5% (n=4) | 5.2% (n=4) | 4.8% (n=4) | 21.5% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 70.0% (n=4) | 70.3% (n=4) | 61.9% (n=4) | 61.0% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 72.0% (n=4) | 72.3% (n=4) | 63.8% (n=4) | 62.3% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -10.0 (-18.5 to -2.8); 0/4/0; p=0.125; n=4 | -10.0 (-20.2 to +0.2); 1/3/0; p=0.625; n=4 | -13.4 (-25.3 to -1.5); 1/3/0; p=0.625; n=4 | -13.6 (-27.1 to -5.4); 0/4/0; p=0.125; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -9.8 (-19.6 to -2.9); 0/4/0; p=0.125; n=4 | -10.1 (-21.8 to -0.2); 1/3/0; p=0.625; n=4 | -14.2 (-26.8 to -2.0); 1/3/0; p=0.625; n=4 | -13.8 (-27.8 to -2.9); 0/4/0; p=0.125; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -14.9 (-25.6 to -5.0); 0/4/0; p=0.125; n=4 | -13.6 (-27.4 to +0.2); 1/3/0; p=0.625; n=4 | -23.0 (-45.8 to -1.8); 1/3/0; p=0.625; n=4 | -20.6 (-33.9 to -7.3); 0/4/0; p=0.125; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | -0.9 (-5.4 to +2.8); 1/1/2; p=1.000; n=4 | +0.1 (-3.4 to +3.8); 1/1/2; p=1.000; n=4 | +1.1 (+0.0 to +2.1); 2/0/2; p=0.500; n=4 | +17.5 (+0.4 to +50.2); 3/0/1; p=0.250; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -14.1 (-24.6 to -5.9); 0/4/0; p=0.125; n=4 | -13.9 (-27.2 to -0.7); 1/3/0; p=0.625; n=4 | -22.4 (-41.4 to -3.4); 1/3/0; p=0.625; n=4 | -23.0 (-40.8 to -5.2); 0/4/0; p=0.125; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | -0.0 (-2.0 to +1.9); 1/1/2; p=1.000; n=4 | +0.6 (+0.0 to +1.9); 1/0/3; p=1.000; n=4 | +0.2 (-1.3 to +1.9); 1/1/2; p=1.000; n=4 | +16.9 (+0.0 to +50.0); 2/0/2; p=0.500; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |

Per entry, (a) / (b):

| Entry | PaperQA2 | PaperQA2, 512-token embedding cut | GraphRAG local | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|---|---|---|
| 615582 | 37.5% / 41.8% | 33.2% / 38.5% | 42.4% / 43.8% | 41.8% / 46.1% | 48.7% / 50.3% | 51.3% / 53.6% | 54.3% / 57.6% | 45.4% / 44.4% |
| 616326 | 36.2% / 40.1% | 42.1% / 45.4% | 18.4% / 24.3% | 30.3% / 29.6% | 40.1% / 43.4% | 37.5% / 43.4% | 41.4% / 43.4% | 41.4% / 43.4% |
| 620029 | 59.4% / 59.4% | 57.8% / 56.2% | 53.9% / 50.8% | 78.9% / 82.8% | 82.8% / 84.4% | 83.6% / 80.5% | 75.8% / 74.2% | 75.0% / 77.3% |
| 621313 | 65.3% / 65.3% | 65.3% / 65.3% | 70.3% / 70.3% | 33.1% / 32.2% | 66.9% / 67.8% | 66.1% / 66.1% | 66.9% / 67.8% | 64.4% / 61.0% |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2 | 15,445 | 1.9% | 57.0 | 199,000 | 28,972 | $2.17 | 490 | 165 (n=3) |
| PaperQA2, 512-token embedding cut | 15,002 | 1.0% | 57.0 | 190,249 | 28,044 | $2.08 | 481 | 245 (n=4) |
| GraphRAG local | 37,932 | 19.5% | 134.8 | 699,331 | 199,975 | $9.29 | 1,990 | 962 (n=4) |
| GraphRAG global | 63,752 | 13.7% | 165.2 | 1,288,343 | 289,518 | $12.14 | 2,844 | 1,328 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG local: share of characters by kind of mapping: sources 68.9%, entities/relationships only 11.6%, community reports only 0.0%, none 19.5%.
- GraphRAG global: share of characters by kind of mapping: sources 0.0%, entities/relationships only 0.0%, community reports only 86.3%, none 13.7%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

## PaperQA2 on its own entries

Role: main PaperQA2 result (whole-chunk embeddings). Entries attempted: 10; completed: 10.

| Measure | PaperQA2 | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 47.4% (n=10) | 61.9% (n=10) | 61.9% (n=10) | 61.7% (n=10) | 57.6% (n=10) |
| (b) facts conveyed, credited anywhere in the draft | 50.8% (n=10) | 63.7% (n=10) | 62.2% (n=10) | 63.1% (n=10) | 57.7% (n=10) |
| (c) (a) on facts the supplied text states | 70.4% (n=10) | 88.8% (n=10) | 89.5% (n=10) | 92.1% (n=10) | 84.8% (n=10) |
| (c) (a) on facts the supplied text does not state | 6.2% (n=10) | 11.8% (n=10) | 10.6% (n=10) | 5.5% (n=10) | 6.4% (n=10) |
| (c) (b) on facts the supplied text states | 72.8% (n=10) | 90.3% (n=10) | 90.5% (n=10) | 92.7% (n=10) | 84.4% (n=10) |
| (c) (b) on facts the supplied text does not state | 11.5% (n=10) | 13.6% (n=10) | 11.7% (n=10) | 7.3% (n=10) | 7.0% (n=10) |
| (c) (a) on facts the supplied text states or partly states | 64.3% (n=10) | 81.7% (n=10) | 82.0% (n=10) | 84.2% (n=10) | 77.9% (n=10) |
| (c) (b) on facts the supplied text states or partly states | 67.2% (n=10) | 83.4% (n=10) | 82.4% (n=10) | 85.4% (n=10) | 77.6% (n=10) |

Paired differences from direct reading:

| Measure | PaperQA2 | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -14.5 (-21.8 to -7.0); 1/9/0; p=0.021; n=10 | -0.1 (-2.2 to +1.9); 5/5/0; p=1.000; n=10 | -0.2 (-4.1 to +3.4); 4/4/2; p=1.000; n=10 | -4.4 (-8.6 to -0.2); 3/7/0; p=0.344; n=10 |
| (b) facts conveyed, credited anywhere in the draft | -12.8 (-19.2 to -6.1); 1/9/0; p=0.021; n=10 | -1.5 (-3.1 to +0.1); 1/5/4; p=0.219; n=10 | -0.6 (-4.4 to +3.2); 4/4/2; p=1.000; n=10 | -6.0 (-9.7 to -2.2); 1/7/2; p=0.070; n=10 |
| (c) (a) on facts the supplied text states | -18.4 (-25.5 to -10.7); 1/9/0; p=0.021; n=10 | +0.7 (-2.0 to +3.3); 4/4/2; p=1.000; n=10 | +3.3 (-1.4 to +8.0); 6/3/1; p=0.508; n=10 | -4.0 (-7.6 to +0.0); 2/7/1; p=0.180; n=10 |
| (c) (a) on facts the supplied text does not state | -5.7 (-11.5 to -0.4); 2/6/2; p=0.289; n=10 | -1.2 (-3.3 to +0.6); 3/4/3; p=1.000; n=10 | -6.3 (-16.4 to +1.6); 1/6/3; p=0.125; n=10 | -5.4 (-14.8 to +1.4); 3/5/2; p=0.727; n=10 |
| (c) (b) on facts the supplied text states | -17.5 (-24.4 to -9.9); 1/9/0; p=0.021; n=10 | +0.2 (-2.0 to +2.3); 5/5/0; p=1.000; n=10 | +2.4 (-2.2 to +6.8); 6/3/1; p=0.508; n=10 | -5.9 (-9.7 to -1.5); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text does not state | -2.0 (-4.7 to +0.4); 2/6/2; p=0.289; n=10 | -1.9 (-4.7 to +0.4); 2/4/4; p=0.688; n=10 | -6.2 (-14.4 to -0.1); 1/7/2; p=0.070; n=10 | -6.6 (-15.3 to -0.7); 1/5/4; p=0.219; n=10 |
| (c) (a) on facts the supplied text states or partly states | -17.4 (-24.9 to -9.0); 1/9/0; p=0.021; n=10 | +0.3 (-2.5 to +2.8); 6/4/0; p=0.754; n=10 | +2.4 (-1.4 to +6.2); 5/4/1; p=1.000; n=10 | -3.8 (-7.7 to +0.4); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text states or partly states | -16.2 (-23.2 to -8.6); 1/9/0; p=0.021; n=10 | -1.1 (-3.2 to +1.0); 4/6/0; p=0.754; n=10 | +2.0 (-2.5 to +6.2); 5/4/1; p=1.000; n=10 | -5.8 (-9.8 to -1.5); 2/7/1; p=0.180; n=10 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2 | 14,849 | 1.6% | 57.6 | 202,536 | 27,790 | $2.18 | 480 | 167 (n=8) |
| Direct reading | 12,143 | 0.0% | 2.0 | 34,447 | 9,128 | $0.43 | 73 | not recorded |
| Agentic curator | 11,675 | 0.0% | 2.0 | 103,517 | 14,026 | $0.46 | 114 | not recorded |
| Evidence graph | 14,406 | 0.0% | 7.6 | 73,145 | 24,773 | $0.89 | 190 | not recorded |
| Case table first | 13,776 | 0.0% | 7.6 | 82,262 | 26,849 | $0.97 | 208 | not recorded |

- Direct reading: audit and repair round 8.4 calls, $1.20, 243 model seconds per entry (not included above).
- Agentic curator: audit and repair round 7.7 calls, $1.10, 237 model seconds per entry (not included above).
- Evidence graph: audit and repair round 8.9 calls, $1.33, 294 model seconds per entry (not included above).
- Case table first: audit and repair round 7.4 calls, $1.26, 289 model seconds per entry (not included above).

Settings changed from the defaults of paper-qa 2026.8.12:

| Setting | Default | Value | Reason |
|---|---|---|---|
| llm | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | answer writing; the local adapter in front of the project's one model (no other provider) |
| llm_config (api_base, api_key, timeout) | None (router built from llm, provider endpoint, provider key from env, LiteLLM default timeout) | package's default router layout + api_base=<adapter>, api_key=sk-local-dummy, timeout=900 | point the answer role at the adapter; dummy key; adapter asks for a client timeout >= 900 s (its queue is capped at 3 concurrent calls) |
| summary_llm (+ summary_llm_config, same router change) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | contextual summaries of evidence; the local adapter in front of the project's one model (no other provider) |
| agent.agent_llm (+ agent_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | pointed at the adapter for safety; not used by Docs.aquery (no call was made in this role) |
| parsing.enrichment_llm (+ enrichment_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | media enrichment of PDFs; pointed at the adapter for safety; not used for .txt papers (no call was made in this role) |
| embedding (+ embedding_config kwargs api_base, api_key) | text-embedding-3-small | openai/bge-small-en-v1.5 via adapter /v1/embeddings (fastembed BAAI/bge-small-en-v1.5, 384 dims) | the one local embedding model shared by all systems; no hosted embedding |
| parsing.use_doc_details | True | False | no outside metadata lookup (Crossref, Semantic Scholar, Unpaywall, OpenAlex, retractions, journal quality); citation and title are supplied instead |
| Docs.aadd(citation=, docname=, title=) | None: citation inferred by `llm` from the first chunk; docname derived from it (Author+Year) | citation = the paper's reference line (first line of <pmid>.txt, from the export); docname = <Surname><Year>-<PMID> from papers.csv; title from papers.csv | corpus = exactly the entry's papers, one document each; no call or lookup spent on metadata; citations in answers map back to the PubMed id unambiguously |
| entry point | agent_query with agent_type 'ToolSelector' (pqa ask) | Docs.aadd per paper, then Docs.aquery per question (the README's 'Manual (No Agent)' usage) | the default agent selects tools by function calling, which the adapter refuses; the 'fake' agent also ends with a function-calling Complete step (select_tool with tool_choice) that the adapter refuses; Docs.aquery needs none and keeps retrieval, contextual summaries and answer |
| environment | LiteLLM fetches its model cost map from GitHub; telemetry defaults | LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, DO_NOT_TRACK=1, ANONYMIZED_TELEMETRY=False, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=<local>; outbound proxy = a local logger that refuses and records every non-local connection | no outside service is contacted; any attempt is logged |
| embedding input length (adapter /v1/embeddings, long_inputs='pool') | bge-small-en-v1.5 truncates every input at 512 tokens, so a default 5,000-character PaperQA chunk (about 1,100-1,300 tokens) is embedded from its first ~510 tokens only | an input over 510 tokens (model tokenizer, without [CLS]/[SEP]) is split into consecutive non-overlapping windows of at most 510 tokens; each is embedded, the vectors are averaged (unweighted) and re-normalised; shorter inputs are embedded exactly as before | the 512-token cut is an artefact of the shared local embedding model, not of PaperQA2 (whose default embedding, text-embedding-3-small, takes 8,191 tokens); pooling embeds the whole chunk |

## PaperQA2, 512-token embedding cut on its own entries

Role: sensitivity result (the shared embedder's 512-token cut). Entries attempted: 10; completed: 10.

| Measure | PaperQA2, 512-token embedding cut | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 49.1% (n=10) | 61.9% (n=10) | 61.9% (n=10) | 61.7% (n=10) | 57.6% (n=10) |
| (b) facts conveyed, credited anywhere in the draft | 51.5% (n=10) | 63.7% (n=10) | 62.2% (n=10) | 63.1% (n=10) | 57.7% (n=10) |
| (c) (a) on facts the supplied text states | 72.4% (n=10) | 88.8% (n=10) | 89.5% (n=10) | 92.1% (n=10) | 84.8% (n=10) |
| (c) (a) on facts the supplied text does not state | 7.1% (n=10) | 11.8% (n=10) | 10.6% (n=10) | 5.5% (n=10) | 6.4% (n=10) |
| (c) (b) on facts the supplied text states | 74.0% (n=10) | 90.3% (n=10) | 90.5% (n=10) | 92.7% (n=10) | 84.4% (n=10) |
| (c) (b) on facts the supplied text does not state | 10.6% (n=10) | 13.6% (n=10) | 11.7% (n=10) | 7.3% (n=10) | 7.0% (n=10) |
| (c) (a) on facts the supplied text states or partly states | 66.5% (n=10) | 81.7% (n=10) | 82.0% (n=10) | 84.2% (n=10) | 77.9% (n=10) |
| (c) (b) on facts the supplied text states or partly states | 68.6% (n=10) | 83.4% (n=10) | 82.4% (n=10) | 85.4% (n=10) | 77.6% (n=10) |

Paired differences from direct reading:

| Measure | PaperQA2, 512-token embedding cut | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -12.9 (-21.5 to -4.9); 2/8/0; p=0.109; n=10 | -0.1 (-2.2 to +1.9); 5/5/0; p=1.000; n=10 | -0.2 (-4.1 to +3.4); 4/4/2; p=1.000; n=10 | -4.4 (-8.6 to -0.2); 3/7/0; p=0.344; n=10 |
| (b) facts conveyed, credited anywhere in the draft | -12.2 (-19.7 to -4.7); 2/8/0; p=0.109; n=10 | -1.5 (-3.1 to +0.1); 1/5/4; p=0.219; n=10 | -0.6 (-4.4 to +3.2); 4/4/2; p=1.000; n=10 | -6.0 (-9.7 to -2.2); 1/7/2; p=0.070; n=10 |
| (c) (a) on facts the supplied text states | -16.4 (-25.1 to -7.9); 2/8/0; p=0.109; n=10 | +0.7 (-2.0 to +3.3); 4/4/2; p=1.000; n=10 | +3.3 (-1.4 to +8.0); 6/3/1; p=0.508; n=10 | -4.0 (-7.6 to +0.0); 2/7/1; p=0.180; n=10 |
| (c) (a) on facts the supplied text does not state | -4.7 (-13.6 to +2.3); 4/4/2; p=1.000; n=10 | -1.2 (-3.3 to +0.6); 3/4/3; p=1.000; n=10 | -6.3 (-16.4 to +1.6); 1/6/3; p=0.125; n=10 | -5.4 (-14.8 to +1.4); 3/5/2; p=0.727; n=10 |
| (c) (b) on facts the supplied text states | -16.3 (-24.5 to -7.8); 2/8/0; p=0.109; n=10 | +0.2 (-2.0 to +2.3); 5/5/0; p=1.000; n=10 | +2.4 (-2.2 to +6.8); 6/3/1; p=0.508; n=10 | -5.9 (-9.7 to -1.5); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text does not state | -3.0 (-8.9 to +1.2); 3/3/4; p=1.000; n=10 | -1.9 (-4.7 to +0.4); 2/4/4; p=0.688; n=10 | -6.2 (-14.4 to -0.1); 1/7/2; p=0.070; n=10 | -6.6 (-15.3 to -0.7); 1/5/4; p=0.219; n=10 |
| (c) (a) on facts the supplied text states or partly states | -15.2 (-23.9 to -6.4); 1/9/0; p=0.021; n=10 | +0.3 (-2.5 to +2.8); 6/4/0; p=0.754; n=10 | +2.4 (-1.4 to +6.2); 5/4/1; p=1.000; n=10 | -3.8 (-7.7 to +0.4); 3/7/0; p=0.344; n=10 |
| (c) (b) on facts the supplied text states or partly states | -14.8 (-22.9 to -6.4); 2/8/0; p=0.109; n=10 | -1.1 (-3.2 to +1.0); 4/6/0; p=0.754; n=10 | +2.0 (-2.5 to +6.2); 5/4/1; p=1.000; n=10 | -5.8 (-9.8 to -1.5); 2/7/1; p=0.180; n=10 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| PaperQA2, 512-token embedding cut | 14,633 | 1.4% | 57.6 | 194,940 | 27,094 | $2.10 | 472 | 244 (n=10) |
| Direct reading | 12,143 | 0.0% | 2.0 | 34,447 | 9,128 | $0.43 | 73 | not recorded |
| Agentic curator | 11,675 | 0.0% | 2.0 | 103,517 | 14,026 | $0.46 | 114 | not recorded |
| Evidence graph | 14,406 | 0.0% | 7.6 | 73,145 | 24,773 | $0.89 | 190 | not recorded |
| Case table first | 13,776 | 0.0% | 7.6 | 82,262 | 26,849 | $0.97 | 208 | not recorded |

- Direct reading: audit and repair round 8.4 calls, $1.20, 243 model seconds per entry (not included above).
- Agentic curator: audit and repair round 7.7 calls, $1.10, 237 model seconds per entry (not included above).
- Evidence graph: audit and repair round 8.9 calls, $1.33, 294 model seconds per entry (not included above).
- Case table first: audit and repair round 7.4 calls, $1.26, 289 model seconds per entry (not included above).

Settings changed from the defaults of paper-qa 2026.8.12:

| Setting | Default | Value | Reason |
|---|---|---|---|
| llm | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | answer writing; the local adapter in front of the project's one model (no other provider) |
| llm_config (api_base, api_key, timeout) | None (router built from llm, provider endpoint, provider key from env, LiteLLM default timeout) | package's default router layout + api_base=<adapter>, api_key=sk-local-dummy, timeout=900 | point the answer role at the adapter; dummy key; adapter asks for a client timeout >= 900 s (its queue is capped at 3 concurrent calls) |
| summary_llm (+ summary_llm_config, same router change) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | contextual summaries of evidence; the local adapter in front of the project's one model (no other provider) |
| agent.agent_llm (+ agent_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | pointed at the adapter for safety; not used by Docs.aquery (no call was made in this role) |
| parsing.enrichment_llm (+ enrichment_llm_config) | gpt-4o-2024-11-20 | openai/claude-opus-5-5 | media enrichment of PDFs; pointed at the adapter for safety; not used for .txt papers (no call was made in this role) |
| embedding (+ embedding_config kwargs api_base, api_key) | text-embedding-3-small | openai/bge-small-en-v1.5 via adapter /v1/embeddings (fastembed BAAI/bge-small-en-v1.5, 384 dims) | the one local embedding model shared by all systems; no hosted embedding |
| parsing.use_doc_details | True | False | no outside metadata lookup (Crossref, Semantic Scholar, Unpaywall, OpenAlex, retractions, journal quality); citation and title are supplied instead |
| Docs.aadd(citation=, docname=, title=) | None: citation inferred by `llm` from the first chunk; docname derived from it (Author+Year) | citation = the paper's reference line (first line of <pmid>.txt, from the export); docname = <Surname><Year>-<PMID> from papers.csv; title from papers.csv | corpus = exactly the entry's papers, one document each; no call or lookup spent on metadata; citations in answers map back to the PubMed id unambiguously |
| entry point | agent_query with agent_type 'ToolSelector' (pqa ask) | Docs.aadd per paper, then Docs.aquery per question (the README's 'Manual (No Agent)' usage) | the default agent selects tools by function calling, which the adapter refuses; the 'fake' agent also ends with a function-calling Complete step (select_tool with tool_choice) that the adapter refuses; Docs.aquery needs none and keeps retrieval, contextual summaries and answer |
| environment | LiteLLM fetches its model cost map from GitHub; telemetry defaults | LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, DO_NOT_TRACK=1, ANONYMIZED_TELEMETRY=False, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=<local>; outbound proxy = a local logger that refuses and records every non-local connection | no outside service is contacted; any attempt is logged |

## GraphRAG local on its own entries

Role: main GraphRAG result (local search, the CLI's default). Entries attempted: 4; completed: 4.

| Measure | GraphRAG local | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 46.2% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 47.3% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 65.8% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 4.1% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 68.0% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 4.8% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 61.9% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 63.8% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | GraphRAG local | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -13.4 (-25.3 to -1.5); 1/3/0; p=0.625; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -14.2 (-26.8 to -2.0); 1/3/0; p=0.625; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -23.0 (-45.8 to -1.8); 1/3/0; p=0.625; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | +1.1 (+0.0 to +2.1); 2/0/2; p=0.500; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -22.4 (-41.4 to -3.4); 1/3/0; p=0.625; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | +0.2 (-1.3 to +1.9); 1/1/2; p=1.000; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (a) on facts the supplied text states or partly states | -21.3 (-39.5 to -3.1); 1/3/0; p=0.625; n=4 | -0.2 (-2.9 to +2.4); 2/2/0; p=1.000; n=4 | +2.3 (-4.5 to +9.4); 2/1/1; p=1.000; n=4 | -2.8 (-7.0 to +2.2); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text states or partly states | -21.1 (-39.1 to -2.9); 1/3/0; p=0.625; n=4 | -0.2 (-3.2 to +2.8); 2/2/0; p=1.000; n=4 | +1.2 (-7.3 to +9.4); 2/1/1; p=1.000; n=4 | -5.5 (-8.7 to -0.8); 1/3/0; p=0.625; n=4 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| GraphRAG local | 37,932 | 19.5% | 134.8 | 699,331 | 199,975 | $9.29 | 1,990 | 962 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG local: share of characters by kind of mapping: sources 68.9%, entities/relationships only 11.6%, community reports only 0.0%, none 19.5%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

Settings changed from the defaults of graphrag 3.3.0:

| Setting | Default | Value | Reason |
|---|---|---|---|
| completion_models.default_completion_model.model | gpt-4.1 | openai/claude-opus-5-5 | the project's one model through the local adapter |
| completion_models.default_completion_model.api_base | (none: the provider's public endpoint) | ${GRAPHRAG_API_BASE} = http://127.0.0.1:<port>/v1 | the local adapter (127.0.0.1 only) |
| completion_models.default_completion_model.api_key | ${GRAPHRAG_API_KEY} (.env: <API_KEY>) | sk-local-dummy (in .env) | dummy key; the adapter needs none and no real key is passed to the package |
| completion_models.default_completion_model.call_args | {} (LiteLLM/OpenAI client defaults: its own timeout and retries) | {"extra_headers": {"X-Aiomim-Tag": "<system>/<mim>/<step>"}, "max_retries": 0, "timeout": 1800} | client timeout 1800 s (a call can take minutes); the OpenAI client's own retries off (GraphRAG's retry and the adapter's retry remain); ledger tag header (bookkeeping only) |
| completion_models.default_completion_model.retry | {"max_retries": "(unset: package default 7)", "type": "exponential_backoff"} | {"max_retries": 2, "type": "exponential_backoff"} | few client retries: the adapter already retries transient failures with back-off; max_retries must be > 1 for this retry type |
| embedding_models.default_embedding_model.model | text-embedding-3-large | openai/bge-small-en-v1.5 | the adapter's local embedding model (BAAI/bge-small-en-v1.5, 384 dimensions), the same for all systems |
| embedding_models.default_embedding_model.api_base | (none: the provider's public endpoint) | ${GRAPHRAG_API_BASE} = http://127.0.0.1:<port>/v1 | the local adapter (127.0.0.1 only) |
| embedding_models.default_embedding_model.api_key | ${GRAPHRAG_API_KEY} (.env: <API_KEY>) | sk-local-dummy (in .env) | dummy key; the adapter needs none and no real key is passed to the package |
| embedding_models.default_embedding_model.call_args | {} (LiteLLM/OpenAI client defaults: its own timeout and retries) | {"extra_headers": {"X-Aiomim-Tag": "<system>/<mim>/<step>"}, "max_retries": 0, "timeout": 1800} | client timeout 1800 s (a call can take minutes); the OpenAI client's own retries off (GraphRAG's retry and the adapter's retry remain); ledger tag header (bookkeeping only) |
| embedding_models.default_embedding_model.retry | {"max_retries": "(unset: package default 7)", "type": "exponential_backoff"} | {"max_retries": 2, "type": "exponential_backoff"} | few client retries: the adapter already retries transient failures with back-off; max_retries must be > 1 for this retry type |
| extract_graph.completion_model_id | default_completion_model | completion_extract_graph | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/extract_graph), to count calls by workflow step; requests are otherwise identical |
| summarize_descriptions.completion_model_id | default_completion_model | completion_summarize_descriptions | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/summarize_descriptions), to count calls by workflow step; requests are otherwise identical |
| community_reports.completion_model_id | default_completion_model | completion_community_reports | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/community_reports), to count calls by workflow step; requests are otherwise identical |
| local_search.completion_model_id | default_completion_model | completion_local_search | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/local_search), to count calls by workflow step; requests are otherwise identical |
| global_search.completion_model_id | default_completion_model | completion_global_search | a copy of default_completion_model that differs only in the ledger tag header (<system>/<mim>/global_search), to count calls by workflow step; requests are otherwise identical |
| concurrent_requests | 25 | 3 | the adapter's concurrency cap (3), so GraphRAG does not flood it |
| input/ (input_storage.base_dir, input.type text) | (empty folder) | the entry's exported papers, one <pmid>.txt per paper | the corpus: exactly the supplied papers; GraphRAG's text reader titles each document by its file name, which maps it back to the PubMed id |
| environment | (inherited) | fresh environment: no proxy variables, no provider keys; LITELLM_LOCAL_MODEL_COST_MAP=True, LITELLM_TELEMETRY=False, ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1, OTEL_SDK_DISABLED=true, HF_HUB_OFFLINE=1, TIKTOKEN_CACHE_DIR=data/cache/tiktoken | telemetry off, nothing reaches an outside service; tiktoken encodings filled once beforehand |
| vector_store.vector_size (effective; not set by us) | 3072 | 384 | a consequence of the embedding model, not a change in settings.yaml: the package's own validate_config detects the model's 384-dimensional vectors and overrides vector_size (logged as a warning) |

## GraphRAG global on its own entries

Role: GraphRAG global search on the same indexes. Entries attempted: 4; completed: 4.

| Measure | GraphRAG global | Direct reading | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | 46.0% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 59.6% (n=4) | 56.5% (n=4) |
| (b) facts conveyed, credited anywhere in the draft | 47.7% (n=4) | 61.5% (n=4) | 60.9% (n=4) | 60.8% (n=4) | 56.5% (n=4) |
| (c) (a) on facts the supplied text states | 68.2% (n=4) | 88.8% (n=4) | 88.4% (n=4) | 92.0% (n=4) | 86.8% (n=4) |
| (c) (a) on facts the supplied text does not state | 20.5% (n=4) | 3.0% (n=4) | 2.9% (n=4) | 1.1% (n=4) | 2.0% (n=4) |
| (c) (b) on facts the supplied text states | 67.4% (n=4) | 90.4% (n=4) | 90.7% (n=4) | 91.5% (n=4) | 84.2% (n=4) |
| (c) (b) on facts the supplied text does not state | 21.5% (n=4) | 4.6% (n=4) | 4.7% (n=4) | 3.5% (n=4) | 3.2% (n=4) |
| (c) (a) on facts the supplied text states or partly states | 61.0% (n=4) | 83.2% (n=4) | 83.0% (n=4) | 85.5% (n=4) | 80.4% (n=4) |
| (c) (b) on facts the supplied text states or partly states | 62.3% (n=4) | 84.9% (n=4) | 84.7% (n=4) | 86.0% (n=4) | 79.4% (n=4) |

Paired differences from direct reading:

| Measure | GraphRAG global | Agentic curator | Evidence graph | Case table first |
|---|---|---|---|---|
| (a) facts conveyed, credited to paragraphs citing the paper | -13.6 (-27.1 to -5.4); 0/4/0; p=0.125; n=4 | +0.0 (-1.8 to +1.8); 2/2/0; p=1.000; n=4 | -0.0 (-4.9 to +4.2); 2/1/1; p=1.000; n=4 | -3.1 (-6.5 to +0.1); 1/3/0; p=0.625; n=4 |
| (b) facts conveyed, credited anywhere in the draft | -13.8 (-27.8 to -2.9); 0/4/0; p=0.125; n=4 | -0.6 (-2.9 to +2.1); 1/2/1; p=1.000; n=4 | -0.7 (-7.6 to +5.5); 1/1/2; p=1.000; n=4 | -5.0 (-7.0 to -1.7); 0/3/1; p=0.250; n=4 |
| (c) (a) on facts the supplied text states | -20.6 (-33.9 to -7.3); 0/4/0; p=0.125; n=4 | -0.4 (-2.9 to +2.4); 1/2/1; p=1.000; n=4 | +3.2 (-4.7 to +10.7); 3/1/0; p=0.625; n=4 | -2.0 (-4.9 to +3.1); 1/3/0; p=0.625; n=4 |
| (c) (a) on facts the supplied text does not state | +17.5 (+0.4 to +50.2); 3/0/1; p=0.250; n=4 | -0.1 (-0.9 to +0.7); 1/1/2; p=1.000; n=4 | -1.9 (-4.7 to +0.0); 0/2/2; p=0.500; n=4 | -1.0 (-2.0 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (b) on facts the supplied text states | -23.0 (-40.8 to -5.2); 0/4/0; p=0.125; n=4 | +0.2 (-2.3 to +2.8); 2/2/0; p=1.000; n=4 | +1.1 (-7.5 to +8.9); 2/1/1; p=1.000; n=4 | -6.2 (-10.9 to -0.8); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text does not state | +16.9 (+0.0 to +50.0); 2/0/2; p=0.500; n=4 | +0.1 (-0.9 to +1.3); 1/1/2; p=1.000; n=4 | -1.1 (-2.1 to +0.0); 0/2/2; p=0.500; n=4 | -1.4 (-3.4 to +0.0); 0/2/2; p=0.500; n=4 |
| (c) (a) on facts the supplied text states or partly states | -22.2 (-37.8 to -9.4); 0/4/0; p=0.125; n=4 | -0.2 (-2.9 to +2.4); 2/2/0; p=1.000; n=4 | +2.3 (-4.5 to +9.4); 2/1/1; p=1.000; n=4 | -2.8 (-7.0 to +2.2); 1/3/0; p=0.625; n=4 |
| (c) (b) on facts the supplied text states or partly states | -22.6 (-39.0 to -6.1); 0/4/0; p=0.125; n=4 | -0.2 (-3.2 to +2.8); 2/2/0; p=1.000; n=4 | +1.2 (-7.3 to +9.4); 2/1/1; p=1.000; n=4 | -5.5 (-8.7 to -0.8); 1/3/0; p=0.625; n=4 |

Text, calls, cost and time per entry (means over these entries):

| Arm | Characters | No mapped citation | Calls | Input tokens | Output tokens | List price | Model seconds | Wall seconds |
|---|---|---|---|---|---|---|---|---|
| GraphRAG global | 63,752 | 13.7% | 165.2 | 1,288,343 | 289,518 | $12.14 | 2,844 | 1,328 (n=4) |
| Direct reading | 11,127 | 0.0% | 2.0 | 26,655 | 8,893 | $0.36 | 70 | not recorded |
| Agentic curator | 11,651 | 0.0% | 2.0 | 63,673 | 12,852 | $0.39 | 105 | not recorded |
| Evidence graph | 14,232 | 0.0% | 7.2 | 60,772 | 23,895 | $0.80 | 185 | not recorded |
| Case table first | 14,256 | 0.0% | 7.2 | 72,123 | 26,896 | $0.88 | 207 | not recorded |

- GraphRAG global: share of characters by kind of mapping: sources 0.0%, entities/relationships only 0.0%, community reports only 86.3%, none 13.7%.
- Direct reading: audit and repair round 6.5 calls, $0.93, 201 model seconds per entry (not included above).
- Agentic curator: audit and repair round 6.5 calls, $0.98, 227 model seconds per entry (not included above).
- Evidence graph: audit and repair round 7.5 calls, $1.19, 272 model seconds per entry (not included above).
- Case table first: audit and repair round 7.5 calls, $1.21, 291 model seconds per entry (not included above).

Settings changed from the defaults of graphrag 3.3.0:

The same table as GraphRAG local.

## STORM on its own entries

Role: no article produced. Entries attempted: 10; completed: 0; stopped: 10.

Requests per entry: 5.0 distinct (50 fresh in all), $0.07 at list price.

Settings changed from the defaults of knowledge-storm 1.1.1:

| Setting | Default | Value | Reason |
|---|---|---|---|
| LM, all five roles (conv_simulator_lm, question_asker_lm, outline_gen_lm, article_gen_lm, article_polish_lm) | STORMWikiLMConfigs.init_openai_model: LitellmModel gpt-4o-mini-2024-07-18 (conversation, question asking), gpt-4-0125-preview (outline), gpt-4o-2024-05-13 (article, polish) | LitellmModel openai/claude-opus-5-5, api_base = local adapter, api_key = dummy | the local adapter in front of the project's one model (Claude Opus 5.5, effort medium) |
| LM temperature / top_p / max_tokens | temperature 1.0, top_p 0.9; max_tokens 500 / 500 / 400 / 700 / 4000 per role | sent unchanged, but ignored by the adapter (the command-line model takes no sampling or length parameters; replies are not cut at max_tokens) | the adapter cannot pass them to the model; recorded, not chosen |
| LM request timeout | LiteLLM default (600 s) | 1800 s | adapter calls queue behind a concurrency cap of 3 and can take minutes; the harness asks for >= 900 s |
| retriever (rm) | a web search API (YouRM / BingSearch / ... in the examples) | VectorRM over the entry's supplied papers only (offline Qdrant on disk), k = search_top_k = 3 | the papers may not go to an outside service; the corpus is exactly the supplied papers |
| VectorRM corpus CSV | user supplied (content, title, url, description) | one row per supplied paper: content = the exported <pmid>.txt (reference line, title, abstract, full text as the entry's access level allows); title = paper title; url = https://pubmed.ncbi.nlm.nih.gov/<pmid>/ (identifier only, never fetched); description = the reference line | the corpus is exactly the supplied papers; the url identifies the PubMed id for citation mapping |
| VectorRM / QdrantVectorStoreManager embedding_model | BAAI/bge-m3 (1024 dims) | BAAI/bge-small-en-v1.5 (384 dims), loaded locally by the package's own HuggingFaceEmbeddings | the small local embedding model used by all three systems |
| VectorRM / QdrantVectorStoreManager device | mps | cpu | no Apple GPU (or any GPU) on this machine |
| Qdrant collection vector size | 1024 (hard-coded in QdrantVectorStoreManager._check_create_collection) | 384: the collection is created with this size before the package's own builder is called (the builder then loads it instead of creating it) | a hard-coded 1024 cannot hold 384-dimensional vectors; smallest change |
| qdrant_client.Document | `from qdrant_client import Document` in QdrantVectorStoreManager.create_or_update_vector_store (fails: qdrant-client has no such name in any release checked, 1.7-1.20) | the name is set to langchain_core.documents.Document (the class the code uses: page_content, metadata, split by the LangChain text splitter) before the builder is called | the released corpus builder cannot run otherwise; smallest change, no behaviour added |
| dependency versions (unpinned by knowledge-storm 1.1.1) | whatever the resolver picks: uv picked sentence-transformers 2.2.2 + transformers 4.17.0 (fails to import: huggingface_hub has no cached_download) and qdrant-client 1.20.0 (no QdrantClient.search, which langchain_qdrant.Qdrant, used by VectorRM, calls) | sentence-transformers 5.7.0 (newest), transformers 4.57.6; qdrant-client 1.15.1 (newest release with QdrantClient.search); torch 2.15.0+cpu | the newest versions with which the released VectorRM path imports and runs |
| telemetry / outside calls | LiteLLM telemetry off (set by the package); cost map local (set by the package); Hugging Face hub online | also LITELLM_TELEMETRY=False, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1, ANONYMIZED_TELEMETRY=False, DO_NOT_TRACK=1; models fetched once beforehand; no other provider key in the environment | nothing but the adapter and the Wikipedia pages of the perspective step may be reached |
| LiteLLM disk cache location | ~/.storm_local_cache | HOME set to runs/external/storm/_home, so the cache is runs/external/storm/_home/.storm_local_cache | keep the run's files inside the run folder; caching behaviour unchanged |

## Claim-level audit without repair (4 common entries)

Systems: paragraphs with mapped citations, audited here. Comparison strategies: the stored audit of their drafts before their repair round (run omim100), on the same entries.

| Arm | Paragraphs | Claims | Supported | Partly supported | Unsupported | Contradicted | Not checkable |
|---|---|---|---|---|---|---|---|
| PaperQA2 | 128 | 853 | 780 (91.4%) | 66 (7.7%) | 2 (0.2%) | 5 (0.6%) | 0 (0.0%) |
| GraphRAG local | 283 | 1382 | 1241 (89.8%) | 107 (7.7%) | 33 (2.4%) | 1 (0.1%) | 0 (0.0%) |
| Direct reading | 87 | 581 | 571 (98.3%) | 10 (1.7%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Agentic curator | 92 | 644 | 635 (98.6%) | 9 (1.4%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Evidence graph | 127 | 770 | 746 (96.9%) | 21 (2.7%) | 3 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| Case table first | 125 | 866 | 836 (96.5%) | 29 (3.4%) | 1 (0.1%) | 0 (0.0%) | 0 (0.0%) |

## Deviations from the design

1. Reduced sizes (decided before any run finished, at the project owner's request): PaperQA2 and STORM on the first 10 entries of the seeded order instead of 24; GraphRAG within 1,000 model calls (floor 6 entries) instead of 3,000 (floor 12). Every result here is exploratory.
2. PaperQA2 was run without its agent: `Docs.aadd` per paper and `Docs.aquery` per question (the README's 'Manual (No Agent)' usage) instead of the default `agent_query` (`pqa ask`). The default agent selects tools by function calling, and the 'fake' agent ends with a function-calling Complete step; the adapter in front of the project's command-line model cannot serve tool calls. Retrieval, contextual summaries and the answer step are PaperQA2's own; the agent's iterative search and its decision to stop are not exercised.
3. Embedding cut and re-run: the shared local embedder (bge-small-en-v1.5) truncates at 512 tokens, so the first PaperQA2 run (`paperqa`) embedded only the first ~510 tokens of each ~5,000-character chunk. PaperQA2 was re-run with whole-chunk embeddings (windows of 510 tokens averaged; `paperqa_pooled`), which is reported as the main result; the first run is kept as a sensitivity result. Requests identical between the two runs were served from the cache in the second, so its fresh calls understate what a stand-alone run costs (calls here count every distinct request once, wherever it was first made).
4. GraphRAG on 4 entries (621313, 615582, 616326, 620029), below the design's floor of 6: the fixed in-order rule stopped when the fifth entry (611521) did not fit in what was left of the 1,000-call cap (the operator's projection; the tally in the ledgers is 698 calls, including the global-search queries and a smoke test).
5. GraphRAG global search was added on the same 4 indexes (the CLI default is local search, which is the main GraphRAG result). Its citations name community reports only; a report is mapped to the papers of the text units its community's entities came from, a looser mapping than PaperQA2's (named papers) or local search's (text units, entities, relationships; a block's papers are the union over every record it cites, counting only records the query showed the model).
6. STORM did not complete any entry: the model's safety filter stopped every chain-of-thought prompt of its research stage (30 of 30 fresh requests stopped; the 20 plain outline prompts were answered), so no article was produced. Per the rules, nothing was retried or reworded. STORM is reported as completion 0 of 10.
7. The comparison strategies' drafts (run omim100) are the published drafts, after their one audit-and-repair round; the systems' drafts had none. The design treats every arm alike without repair; the repair round moved coverage by about 0.2 points in the hidden-full-text experiment, so this favours the comparison strategies very slightly at most. Their (a) and (c) come from stored marks; (b) from stored whole-draft marks where present, otherwise scored here once (the same path).
8. Bookkeeping corrected in this summary: calls, tokens and cost count each distinct request once with the figures it had when made (the ledgers' `full_*` totals count cached re-runs again; PaperQA2's first-run entry 621313 was re-saved from the cache twice, tripling its `full_*` figures); the saved `seconds` of that entry (6.9 s) is a cached re-save and its real wall time (177.2 s) is taken from `runs/external/paperqa/pilot.log`; GraphRAG local's query seconds are the sum of per-question seconds in `meta` (no query-run record), added to the recorded index time. PaperQA2 (whole-chunk) entries 301059 and 621313 were served entirely from the cache (all requests identical to the first run) and have no wall time of their own; its other entries' wall times understate a stand-alone run for the same reason.
9. Wall-clock time is not recorded per strategy in run omim100 (only per entry for all strategies together); for the comparison strategies, time is the sum of model-call seconds (`model_seconds`), which is also given for the systems. Systems ran with the adapter's concurrency cap of 3; the comparison strategies' generation is mostly one or a few calls.
10. Systems were asked six fixed section questions (PaperQA2, GraphRAG) and their answers concatenated; the comparison strategies write an OMIM-style entry in one pass. GraphRAG's answers include headings and framing lines as separate blocks; all text counts for (b) and the uncited share.
11. The claim-level audit without repair was run on the 4 entries both PaperQA2 and GraphRAG completed, not on every entry of each system, on every paragraph with mapped citations.
12. Judge noise: (b) credits facts anywhere in the draft and should not fall below (a), but it does on 5 system entries (paperqa/620029, paperqa/620249, graphrag/620029, graphrag_global/616326, graphrag_global/621313): the two are separate judge passes, so differences of a few points between them are within the judge's noise.
13. Extent of the comparison strategies' repair round on these 10 entries (paragraphs revised / deleted / in the final drafts): Direct reading 3 / 0 / 234; Agentic curator 2 / 0 / 240; Evidence graph 5 / 0 / 317; Case table first 1 / 0 / 291.
