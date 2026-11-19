# aiomim

Automated, evidence-grounded curation of [OMIM](https://www.omim.org)-style entries from the published literature.

OMIM is the reference catalogue of human genes and genetic disorders. It is written by hand: roughly one new entry and
ten updates a day. `aiomim` is a proof of concept that an entry can be drafted automatically from the papers a curator
would read, with every sentence traceable to a quote in a cited paper, and that the result can be scored against the
entry OMIM's curators actually wrote.

Given a MIM number, the pipeline:

1. assembles a **gold standard** for that entry from public, OMIM-derived sources;
2. **retrieves** the literature (OMIM's own reference list, or a search from scratch);
3. **extracts** quote-backed findings from each paper and discards any whose quote is not in the paper;
4. joins the findings into an **evidence knowledge graph** (papers, genes, variants, HPO phenotypes, inheritance);
5. **writes** the entry from the graph in OMIM's layout and style;
6. **audits** every claim against the cited paper, and revises what the audit flags;
7. **scores** the entry against the gold standard;
8. builds a **review page** where a curator accepts, edits or rejects each paragraph.

> **Status:** work in progress. The pipeline stages are implemented and unit-tested; the first evaluation run
> against real OMIM entries has not been recorded here yet.

## Quick start

```bash
pip install -e ".[dev]"
```

The model is called through the [Claude Code](https://claude.com/claude-code) CLI in headless mode, so the pipeline
runs on a Claude subscription and needs no API key. Install the CLI and log in once (`claude`, then `/login`).

```bash
aiomim gold 500001                       # what gold-standard material exists for this entry
```

```bash
aiomim run 500001 --run demo             # replicate the entry and score it
```

```bash
aiomim report demo                       # build runs/demo/report.html, the curator review page
```

Everything is cached under `data/` (HTTP responses, model replies, ontologies), so re-running a command repeats no
network or model calls. Outputs go to `runs/<run>/<mim>/`.

## Commands

| Command | What it does |
|---|---|
| `aiomim gold MIM…` | Show the gold standard available for each entry. |
| `aiomim select --from 2026/01/01 --to 2026/11/30` | List entries created in a date window with their gold coverage, to build an evaluation set (entries newer than the model's training data are the cleanest test). |
| `aiomim run MIM… [--retrieval oracle\|open] [--strategy kg\|direct\|both] [--jobs N]` | Replicate existing entries and score them. |
| `aiomim create --title "…" --gene SYMBOL [--pmid …]` | Draft a **new** entry from a title, gene and optional seed papers. |
| `aiomim update MIM… [--as-of YEAR]` | Propose **updates** to an existing entry from literature it does not cite; `--as-of` back-tests against the references OMIM later added. |
| `aiomim report RUN` | Build the single-file HTML review page for a run. |
| `aiomim summary RUN` | Recompute and print the score table for a run. |

`--retrieval oracle` (default) gives the pipeline exactly the references OMIM cites and withholds the causal gene, which
must be recovered from the papers. `--retrieval open` gives it the entry's title and gene and has it find the
literature itself. `--strategy direct` is the baseline with no extraction and no graph: the papers go straight into
one prompt.

## How it works

```
 MIM number
     │
     ▼
 gold.py ───────────────► GoldEntry (public sources; used only for scoring and, in oracle mode, the PMID list)
     │
     ▼
 retrieve.py   oracle: OMIM's reference list        open: plan queries → PubMed + Europe PMC → triage → citation hop
     │         abstracts from PubMed; full text from Europe PMC / PMC where open access
     ▼
 extract.py    one call per paper → findings: OMIM-style statement + verbatim quotes + genes, variants, phenotypes
     │         grounding.py checks every quote against the paper text; no quote found → finding discarded
     │         phenotype phrases → HPO terms (exact match, else model picks among ontology search hits)
     ▼
 kg.py         evidence graph: Paper─reports▶Finding─▶Gene / Variant / Phenotype / Inheritance, provenance on every edge
     │         gene aliases → approved symbol; "G14459A", "m.14459G>A", "A72V", "p.Ala72Val" → one variant node
     ▼
 synthesize.py writer sees only verified findings, arranged by the graph; each paragraph must name its findings
     │         clinical synopsis, inheritance and the gene–phenotype table are computed from the graph
     ▼
 verify.py     independent audit: per cited paper, each claim → supported / partial / unsupported / contradicted
     │         one repair round on flagged paragraphs, then re-audit
     ▼
 evaluate.py   scores against GoldEntry           report/  curator review page (accept / edit / reject, export)
```

### Guards against hallucination

The design assumes the model will sometimes be wrong and places a check after each step that does not depend on the
model being right:

- **Quotes are checked without a model.** Each finding carries verbatim quotes; a token-level matcher looks for them
  in the paper. A changed number, residue or gene symbol fails the match, and the finding is dropped.
- **The writer cannot cite what it was not given.** A paragraph must list finding IDs; paragraphs with none, or with
  IDs that do not exist, are deleted. Author–year citations in the text that match no supplied paper are reported.
- **HPO IDs cannot be invented.** The model may only choose among candidates returned by a search of the ontology.
- **Structured fields are computed, not written.** Clinical synopsis, inheritance and gene links come from counting
  support in the graph, restricted to papers that are about the entry's subject.
- **A second reader audits the result** against the paper text, without seeing the findings or the graph. An audit
  verdict of "supported" whose own evidence quote is not in the paper is downgraded.
- **A curator has the last word.** The review page shows, for each paragraph, the claims, verdicts, quotes and papers.

### The knowledge graph as retrieval index

The writer's context is assembled from the graph rather than from text chunks ranked by embedding similarity. For
each section it receives the findings filed there, oldest first, and alongside them the cross-paper tables the graph
makes possible: which papers report variants in each gene, the distinct variants after merging the different ways
papers name them, which modes of inheritance are asserted and by whom, and which clinical features are reported
present or absent in how many papers. `--strategy both` runs the no-graph baseline on the same papers so the two can
be compared on the same scores.

## The gold standard

OMIM's site forbids crawling and its full text requires a licensed API key, so the default gold standard is built
from sources that redistribute OMIM-derived data publicly:

| Part of the entry | Source |
|---|---|
| Title, symbol, alternative titles, entry type | NCBI E-utilities (`db=omim`), MedGen, OMIM's public `mim2gene.txt` |
| Reference list | NCBI E-utilities link `omim_pubmed_cited` |
| Gene–phenotype links | NCBI `mim2gene_medgen` (GeneMap rows), MedGen |
| Mode of inheritance | HPO annotations (`phenotype.hpoa`), MedGen |
| Clinical synopsis as HPO terms | HPO annotations (`phenotype.hpoa`) |
| Allelic variants and **OMIM's own per-paper text** | ClinVar, submitter "OMIM": each allelic-variant paragraph with the PMID it summarises |
| Full entry text (optional) | OMIM API, if `OMIM_API_KEY` is set |

The ClinVar submissions are the important one: they are paragraphs written by OMIM's curators, each tied to the
paper it summarises, which lets "is each paper portrayed accurately?" be measured directly.

Gold material is fetched at run time into `data/` and is not committed to this repository.

## Scores

| Score | Meaning |
|---|---|
| **Claims supported** | Of the atomic claims in the generated entry, the share the audit found stated in the cited paper. Needs no gold. *Claim error rate* is the share found unsupported or contradicted. |
| **Gold-fact coverage** | OMIM's per-paper paragraphs are split into atomic facts; the share the draft conveys (a partial match counts half). *Contradicted* counts facts the draft gets wrong. |
| **HPO exact F1** | Generated clinical-synopsis HPO terms against HPO's annotations of the entry, identical IDs only. |
| **HPO hierarchical F1** | The same after adding every ancestor of each term to both sets, so a near miss in the ontology earns partial credit. |
| **HPO semantic F1** | Best-match average of Lin similarity between the two term sets. |
| **Variant recall** | Share of OMIM's allelic variants for the entry that appear among the generated ones, matched across notations. |
| **Gene F1 / inheritance match** | Causal gene(s) and mode(s) of inheritance against OMIM's. |
| **Reference recall / precision** | Cited PMIDs against OMIM's reference list (a retrieval score in `open` mode). |

## Layout

```
src/aiomim/
  config.py  cache.py  llm.py  models.py     settings, disk cache, Claude Code wrapper, shared data model
  sources/                                   NCBI, Europe PMC, full text, HPO, HGNC, ClinVar, MedGen, OMIM API
  gold.py  retrieve.py  extract.py  grounding.py  kg.py  synthesize.py  verify.py  evaluate.py  update.py
  pipeline.py  cli.py  render.py  report/
tests/                                       offline unit and end-to-end tests; live tests marked `network`
```

```bash
python -m pytest -m "not network and not llm"
```

## Limits of this proof of concept

To be written up with the first evaluation results.
