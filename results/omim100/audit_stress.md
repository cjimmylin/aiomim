# Audit coverage: planted errors beyond single values (Experiment C, run omim100)

Planted in the 'kg' drafts; natural omissions from the 'direct' drafts. Seed 23, replicate salt 'auditstress-1'. Pool of passed single-paper paragraphs: 1494.

## Audit on planted errors

| Class | Items | Truth known | Paragraph flagged | Planted claim flagged | Control paragraph flagged | Control planted-claim analogue flagged |
|---|---|---|---|---|---|---|
| C1 citation swap, other entry | 5 | 5 | 5/5 (100%) | 5/5 (100%) | 0/5 (0%) | 0/5 (0%) |
| C2 citation swap, same entry | 5 | 4 | 4/4 (100%) | 4/4 (100%) | 0/4 (0%) | 0/4 (0%) |
| C3 conflation | 5 | 3 | 3/3 (100%) | 3/3 (100%) | 0/3 (0%) | 0/3 (0%) |
| C4 over-citation | 5 | 5 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |
| C5 dropped qualifier | 5 | 5 | 2/5 (40%) | 2/5 (40%) | 0/5 (0%) | 0/5 (0%) |
| C6 omitted finding | 5 | 5 | 0/5 (0%) | 0/0 (n/a) | 0/5 (0%) | 0/0 (n/a) |

Counts are over truth-known items. 'Planted claim flagged': at least one planted claim unsupported or contradicted, over items where a planted claim was identified. C4's expected outcome is a pass (the claim takes the best cited paper's verdict); C6's is a pass (the audit judges only what is written).

- C2 truth unknown (variant occurs in the new paper's text): 1 items, paragraph flagged 1, planted-claim-analogue flagged 0/0.
- C3 truth unknown (variant occurs in the new paper's text): 2 items, paragraph flagged 2, planted-claim-analogue flagged 1/2.

### Verdict on the planted claim (worst planted claim per item, truth-known items)

| Class | contradicted | unsupported | partially supported | supported | not checkable |
|---|---|---|---|---|---|
| C1 | 0 | 5 | 0 | 0 | 0 |
| C2 | 2 | 2 | 0 | 0 | 0 |
| C3 | 0 | 3 | 0 | 0 | 0 |
| C4 | 0 | 0 | 1 | 4 | 0 |
| C5 | 2 | 0 | 1 | 2 | 0 |
| C6 | 0 | 0 | 0 | 0 | 0 |

Claim level (C1, C4: every claim is planted):

- C1: 22 of 22 claims flagged (100%).
- C4: 0 of 23 claims flagged (0%).

### C4: the added paper's own verdicts

Of 23 claims, the decomposer attributed 21 to the added paper. Its own verdicts: not_attributed 2, unsupported 21. Share judged supported or partly by the added (unrelated) paper: 0%; flagged: 100%.

### C5 by deletion rule

| Rule | Items | Paragraph flagged | Planted claim flagged | Worst verdict |
|---|---|---|---|---|
| hedge | 2 | 0 | 0/2 | partially_supported 1, supported 1 |
| negation | 2 | 2 | 2/2 | contradicted 2 |
| zygosity | 1 | 0 | 0/1 | supported 1 |

### Control (all unaltered paragraphs, re-audited fresh)

20 paragraphs, 0 flagged (0%); 129 claims, 0 flagged (0.0), 1 partly supported.

## C6 completeness check

### Planted deletions

| | Items | Omissions listed (mean / median) | Deleted sentence listed: mechanical | judge full | judge full or partial |
|---|---|---|---|---|---|
| Sentence deleted | 5 | 5 / 5 | 3/5 (60%) | 3/5 (60%) | 4/5 (80%) |
| Unaltered (false-alarm side) | 5 | 4 / 3 | 1/5 (20%) | 0/5 (0%) | 1/5 (20%) |

Quotes verified: 25 of 25 omissions (deleted), 20 of 20 (unaltered). Judge full matches with a verified quote: 3 (deleted), 0 (unaltered).

### Natural omissions (direct-reading drafts)

5 papers (0 failed), 15 curator facts stated in the text the writer had but absent from the draft. Listed by the check (judge 'states it'): 6 (40%); including 'states part': 6 (40%); with a verified quote: 6 (40%).

Omissions listed: 38 (7.6 per paper; 38 with a verified quote). Matching any curator fact about the paper: 14 (37%); including partial matches 16 (42%).

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

New model calls: 94 (cap 600); safety-filter stops: 0; refusals raised: 0; failed calls: 0; list-price cost $7.1216.

## Decisions

- Strategy planted in: the evidence-graph drafts ('kg') of run omim100, as the single-value planted test, with its selection rule (paragraphs passed as fully supported, citing one paper, longer than 150 characters); at most 3 items per entry per class. One seeded order of that pool serves all classes, so classes share paragraphs and one control audit of the union of their unaltered paragraphs serves every class.
- C3 is planted in the same 'kg' drafts, not the direct-reading drafts: its truth (the moved variant does not occur in paper B's text) is decided mechanically from the paper text, so it needs no stored omission judgement, and keeping one strategy keeps the classes comparable. The moved sentence names a variant and carries no author citation (so it is not explicitly attributed to paper A); it is inserted at a seeded sentence boundary after B's first sentence; B must not already name that variant.
- C6's planted deletions are in the 'kg' drafts; C6's natural omissions use the direct-reading drafts ('direct'), where the stored judgements are: curator facts of gold paragraphs citing one paper, marked absent from the draft and stated (verdict 'yes', quote verified) in the text the writer had. Facts marked partly conveyed or partly stated are not targets.
- Citation swaps (C1, C2) and over-citation (C4) change the in-text author-year label as well as the cited PMID (only paragraphs whose label occurs in the text are used): 'A et al. (2000)' -> 'B et al. (2010)' for swaps, 'A et al. (2000) and B et al. (2010)' or '(A et al., 2000; B et al., 2010)' for over-citation. The new paper of C1 and C4 is a random readable paper (abstract or full text) of another entry; of C2 a random readable other paper of the same entry.
- Variant occurrence (C2, C3) is decided on the text the auditor reads (title, abstract and full text cut at 180,000 characters). A variant occurs if any of its protein or nucleotide keys (kg.protein_key / nucleotide_key, so one- and three-letter, 'arg123-to-trp', p. and c. forms meet), its residue or nucleotide position, or its raw name occurs in the paper. C2 items are truth-known when the paragraph names at least one variant that does not occur in the new paper; C3 items when none of the moved sentence's variants occurs in B.
- Planted claim: C1 and C4 every claim; C2 claims naming a variant absent from the new paper; C3 claims naming the moved variant; C5 claims taken from the altered sentence (at least 60% of a claim's content words in the sentence, else the best-overlapping claim); C6 none. An item counts as 'planted claim flagged' when any planted claim is unsupported or contradicted. Control analogue: the same rule on the unaltered paragraph (for C3, the moved sentence's claims in paper A's own paragraph, against paper A).
- C6 deleted sentence: not the first sentence, carrying a variant or a number (years and MIM numbers aside) that appears nowhere else in the draft's text citing that paper. Mechanical match: a listed omission names one of the sentence's variants (by key), or, for a sentence without variants, carries all its numbers. Judge match: stage 'judge'. The draft text given to the check is all paragraphs of the entry citing the paper (as in scoring).
- The audit is run on items in fixed chunks of 5 (one claim-decomposition call per chunk, then one call per cited paper), not on one 60-paragraph holder as the single-value test did (decomposition batches of 25); this lets the pilot's calls be reused and the run resume. All calls are made under the replicate salt 'auditstress-1', so altered and control audits are fresh and from the same run.
- Per-paper verdicts are kept by `auditstress.audit_paragraphs`, which runs the audit's own prompts and best-verdict rule (verify._decompose, verify._audit_prompt); a unit test checks it agrees with verify.verify_entry.
- Citation precision: the run's entry files keep only each claim's best verdict, not every paper's. Per-paper verdicts were recovered by replaying the stored audit from the model-reply cache with a backend that refuses any uncached call (no new calls). That is possible only for entries the repair round left unchanged; entries with a revised or deleted paragraph are excluded, and a paragraph is kept only if the replayed best verdict of every claim equals the stored one.

## Deviations from the design

- None.
