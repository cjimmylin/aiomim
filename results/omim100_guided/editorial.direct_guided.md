# Editorial precision — run `omim100_guided`

What a draft says about each paper that has an OMIM paragraph, split into atomic statements and checked against that paragraph. *Precision* is the share of draft statements OMIM's paragraph also makes (partly counts half). The OMIM paragraph compared is the allelic-variant text deposited in ClinVar; a statement with no counterpart there may still be in another section of the OMIM entry, so the rate is for comparing strategies on the same entries.

Entries common to all strategies: 68. Left out, no draft from some strategy (writer stopped): 118210, 615817.

| Strategy | Statements | Precision (pooled) | Precision (entry mean) | Statements per paper | OMIM facts per paper | Statements per OMIM fact |
|---|---|---|---|---|---|---|
| direct | 7,997 | 24% | 29% | 24.0 | 11.9 | 2.02 |
| guided | 7,400 | 25% | 31% | 22.2 | 11.9 | 1.87 |

| Strategy | Paper read as | Paragraphs | Statements | Precision | Statements per paper |
|---|---|---|---|---|---|
| direct | fulltext | 103 | 4,381 | 20% | 42.5 |
| direct | abstract | 205 | 3,494 | 28% | 17.0 |
| direct | title | 25 | 122 | 55% | 4.9 |
| guided | fulltext | 103 | 4,060 | 22% | 39.4 |
| guided | abstract | 205 | 3,220 | 29% | 15.7 |
| guided | title | 25 | 120 | 54% | 4.8 |
