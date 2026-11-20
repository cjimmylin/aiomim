# Audit coverage: planted errors beyond single values (Experiment C, run omim100)

Planted in the 'kg' drafts; natural omissions from the 'direct' drafts. Seed 23, replicate salt 'auditstress-1'. Pool of passed single-paper paragraphs: 1494.

## Audit on planted errors

| Class | Items | Truth known | Paragraph flagged | Planted claim flagged | Control paragraph flagged | Control planted-claim analogue flagged |
|---|---|---|---|---|---|---|
| C1 citation swap, other entry | 30 | 30 | 30/30 (100%) | 30/30 (100%) | 0/30 (0%) | 0/30 (0%) |
| C2 citation swap, same entry | 30 | 26 | 26/26 (100%) | 26/26 (100%) | 0/26 (0%) | 0/26 (0%) |
| C3 conflation | 30 | 25 | 25/25 (100%) | 25/25 (100%) | 0/25 (0%) | 0/25 (0%) |
| C4 over-citation | 30 | 30 | 0/30 (0%) | 0/30 (0%) | 0/30 (0%) | 0/30 (0%) |
| C5 dropped qualifier | 30 | 30 | 11/30 (37%) | 11/30 (37%) | 0/30 (0%) | 0/30 (0%) |
| C6 omitted finding | 30 | 30 | 0/30 (0%) | 0/0 (n/a) | 0/30 (0%) | 0/0 (n/a) |

Counts are over truth-known items. 'Planted claim flagged': at least one planted claim unsupported or contradicted, over items where a planted claim was identified. C4's expected outcome is a pass (the claim takes the best cited paper's verdict); C6's is a pass (the audit judges only what is written).

- C2 truth unknown (variant occurs in the new paper's text): 4 items, paragraph flagged 4, planted-claim-analogue flagged 0/0.
- C3 truth unknown (variant occurs in the new paper's text): 5 items, paragraph flagged 5, planted-claim-analogue flagged 4/5.

### Verdict on the planted claim (worst planted claim per item, truth-known items)

| Class | contradicted | unsupported | partially supported | supported | not checkable |
|---|---|---|---|---|---|
| C1 | 5 | 25 | 0 | 0 | 0 |
| C2 | 10 | 16 | 0 | 0 | 0 |
| C3 | 2 | 23 | 0 | 0 | 0 |
| C4 | 0 | 0 | 1 | 29 | 0 |
| C5 | 11 | 0 | 4 | 15 | 0 |
| C6 | 0 | 0 | 0 | 0 | 0 |

Claim level (C1, C4: every claim is planted):

- C1: 173 of 173 claims flagged (100%).
- C4: 0 of 178 claims flagged (0%).

### C4: the added paper's own verdicts

Of 178 claims, the decomposer attributed 176 to the added paper. Its own verdicts: not_attributed 2, unsupported 176. Share judged supported or partly by the added (unrelated) paper: 0%; flagged: 100%.

### C5 by deletion rule

| Rule | Items | Paragraph flagged | Planted claim flagged | Worst verdict |
|---|---|---|---|---|
| count | 4 | 1 | 1/4 | contradicted 1, partially_supported 1, supported 2 |
| hedge | 8 | 2 | 2/8 | contradicted 2, partially_supported 2, supported 4 |
| negation | 8 | 8 | 8/8 | contradicted 8 |
| single family or patient | 2 | 0 | 0/2 | supported 2 |
| zygosity | 8 | 0 | 0/8 | partially_supported 1, supported 7 |

### Control (all unaltered paragraphs, re-audited fresh)

113 paragraphs, 0 flagged (0%); 733 claims, 0 flagged (0.0), 15 partly supported.

## C6 completeness check

### Planted deletions

| | Items | Omissions listed (mean / median) | Deleted sentence listed: mechanical | judge full | judge full or partial |
|---|---|---|---|---|---|
| Sentence deleted | 30 | 6.03 / 5 | 22/29 (76%) | 16/29 (55%) | 24/29 (83%) |
| Unaltered (false-alarm side) | 30 | 5.59 / 3 | 4/29 (14%) | 0/29 (0%) | 2/29 (7%) |

Quotes verified: 175 of 175 omissions (deleted), 162 of 162 (unaltered). Judge full matches with a verified quote: 16 (deleted), 0 (unaltered).

### Natural omissions (direct-reading drafts)

28 papers (0 failed), 60 curator facts stated in the text the writer had but absent from the draft. Listed by the check (judge 'states it'): 24 (40%); including 'states part': 28 (47%); with a verified quote: 24 (40%).

Omissions listed: 284 (10.14 per paper; 284 with a verified quote). Matching any curator fact about the paper: 56 (20%); including partial matches 83 (29%).

## Citation precision (stored audits, no new calls)

Paragraphs citing two or more papers; each (claim, paper the claim is attributed to) pair's own verdict.

| Strategy | Entries replayed | Multi-citation paragraphs (replayed / all) | Pairs | Not supported | Supported or partly | Claims passing with a non-supporting cited paper |
|---|---|---|---|---|---|---|
| kg | 80 | 209 / 272 | 1438 | 6% | 94% | 76 of 991 |
| direct | 84 | 338 / 442 | 2493 | 7% | 93% | 142 of 1782 |
| agent | 87 | 335 / 400 | 2262 | 4% | 96% | 78 of 1772 |
| cohort | 78 | 242 / 306 | 1846 | 7% | 93% | 118 of 1254 |
| recall | 88 | 137 / 165 | 830 | 3% | 97% | 25 of 708 |
| closedbook | 100 | 39 / 39 | 166 | 27% | 73% | 17 of 121 |

## Calls and cost

New model calls: 540 (cap 600); safety-filter stops: 2; refusals raised: 0; failed calls: 0; list-price cost $43.7849.

## Decisions

- Strategy planted in: the evidence-graph drafts ('kg') of run omim100, as the single-value planted test, with its selection rule (paragraphs passed as fully supported, citing one paper, longer than 150 characters); at most 3 items per entry per class. One seeded order of that pool serves all classes, so classes share paragraphs and one control audit of the union of their unaltered paragraphs serves every class.
- C3 is planted in the same 'kg' drafts, not the direct-reading drafts: its truth (the moved variant does not occur in paper B's text) is decided mechanically from the paper text, so it needs no stored omission judgement, and keeping one strategy keeps the classes comparable. The moved sentence names a variant and carries no author citation (so it is not explicitly attributed to paper A); it is inserted at a seeded sentence boundary after B's first sentence; B must not already name that variant.
- C6's planted deletions are in the 'kg' drafts; C6's natural omissions use the direct-reading drafts ('direct'), where the stored judgements are: curator facts of gold paragraphs citing one paper, marked absent from the draft and stated (verdict 'yes', quote verified) in the text the writer had. Facts marked partly conveyed or partly stated are not targets.
- Citation swaps (C1, C2) and over-citation (C4) change the in-text author-year label as well as the cited PMID (only paragraphs whose label occurs in the text are used): 'A et al. (2000)' -> 'B et al. (2010)' for swaps, 'A et al. (2000) and B et al. (2010)' or '(A et al., 2000; B et al., 2010)' for over-citation. The new paper of C1 and C4 is a random readable paper (abstract or full text) of another entry; of C2 a random readable other paper of the same entry.
- Variant occurrence (C2, C3) is decided on the text the auditor reads (title, abstract and full text cut at 180,000 characters). A variant occurs if any of its protein or nucleotide keys (kg.protein_key / nucleotide_key, so one- and three-letter, 'arg123-to-trp', p. and c. forms meet), its residue or nucleotide position, or its raw name occurs in the paper. C2 items are truth-known when the paragraph names at least one variant that does not occur in the new paper; C3 items when none of the moved sentence's variants occurs in B.
- Planted claim: C1 and C4 every claim; C2 claims naming a variant absent from the new paper; C3 claims naming the moved variant; C5 claims taken from the altered sentence (at least 60% of a claim's content words in the sentence, or at least two of the content words next to the deletion point, else the best-overlapping claim); C6 none. An item counts as 'planted claim flagged' when any planted claim is unsupported or contradicted. Control analogue: the same rule on the unaltered paragraph (for C3, the moved sentence's claims in paper A's own paragraph, against paper A).
- C6 deleted sentence: not the first sentence, carrying a variant or a number (years and MIM numbers aside) that appears nowhere else in the draft's text citing that paper. Mechanical match: a listed omission names one of the sentence's variants (by key) or carries all its numbers (number words read as digits). Judge match: stage 'judge'. The draft text given to the check is all paragraphs of the entry citing the paper (as in scoring).
- The audit is run on items in fixed chunks of 5 (one claim-decomposition call per chunk, then one call per cited paper), not on one 60-paragraph holder as the single-value test did (decomposition batches of 25); this lets the pilot's calls be reused and the run resume. All calls are made under the replicate salt 'auditstress-1', so altered and control audits are fresh and from the same run.
- Per-paper verdicts are kept by `auditstress.audit_paragraphs`, which runs the audit's own prompts and best-verdict rule (verify._decompose, verify._audit_prompt); a unit test checks it agrees with verify.verify_entry.
- Citation precision: the run's entry files keep only each claim's best verdict, not every paper's. Per-paper verdicts were recovered by replaying the stored audit from the model-reply cache with a backend that refuses any uncached call (no new calls). That is possible only for entries the repair round left unchanged; entries with a revised or deleted paragraph are excluded, and a paragraph is kept only if the replayed best verdict of every claim equals the stored one.

## Pilot review

- Pilot: 5 items of each class, 20 controls, 5 C6 completeness items, 5 natural papers: 94 calls; estimate for the full run about 555 calls (under the 600 cap), so 30 per class were kept.
- C5 rules were tightened once before the pilot after reading the built edits (no calls involved): zygosity no longer deletes before 'for'/'in ... state' (left no sentence), counts must end in a people noun or a clause boundary, sentence-initial 'In 2 of 5' is not taken, 'more/less likely' and 'likely to/than' are not taken, 'as in one patient' is not taken.
- All 30 C5 edits were then read. hedge (8): 5 change the claim (e.g. 'possibly transient' -> 'transient', 'likely pathogenic' -> 'pathogenic'), 2 are nearly meaning-preserving because the sentence still reads 'suggested that', 1 degenerate ('pathogenic or likely pathogenic' -> 'pathogenic or pathogenic'). negation (8): all grammatical, all reverse the claim (so they plant contradictions, not broadening). zygosity (8): all grammatical; about 3 nearly meaning-preserving where de novo or dominant inheritance implies heterozygosity. count (4): 2 clean, 1 ungrammatical ('Variants were familial in which inheritance could be determined'), 1 awkward. single family/patient (2): both clean. No rule mostly produced ungrammatical or meaning-preserving edits, so all five survive.
- C6 mechanical matching was corrected after the pilot (no new calls; recomputed at summary time): number words and thousands separators are read as digits, and a listed omission matches on all the sentence's numbers even when the sentence also names a variant (variant names written with a hyphen, 'p.P102-V104del', do not parse as keys).
- After the main run, the C5 planted-claim selector was widened (no new calls; recomputed at summary time): a claim also counts as taken from the altered sentence when it contains two of the content words next to the deletion point. Two flagged negation items (C5.5, C5.18) had been missed by the overlap rule alone because the decomposer had added context words to the claim.

## Deviations from the design

- Size: 30 items per class instead of the design's 'about 60', and at most 600 new model calls instead of 1,200 (pilot included), at the user's request for a smaller budget. Items were built and run as 30 per class from the start (seeded order).
- Natural omissions capped at 60 curator facts (seeded sample, facts of papers readable in full taken first): 60 of the 130 eligible facts, on 28 papers. The design did not set a cap.
- Audit grouping: items are audited in fixed chunks of 5 (one claim-decomposition call per chunk), where the single-value test audited all 60 in one holder (decomposition batches of 25). Prompts and verdict rules are otherwise the audit's own.
- Citation precision could not be read from 'the existing audit files': the entry files keep only each claim's best verdict. Per-paper verdicts were recovered without new calls by replaying the audit from the model-reply cache, which is possible only for entries whose paragraphs the repair round left unchanged (about 80-88% of entries per strategy; all closed-book entries, which have no repair).
- Unaltered controls are one audit of the union of all classes' unaltered paragraphs (113 paragraphs), not a separate control per class; each class's control figures are read from it for that class's own paragraphs.
- Papers are loaded at the access level the run recorded, from cached responses only (no new fetches); every paper's access level matched papers.json.
- Safety-filter stops: 2, both on the completeness check of item C6.24 (the altered and the unaltered draft text of the same paper). Recorded, not retried; C6 completeness figures are over 29 items.
