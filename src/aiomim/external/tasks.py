"""The task wording given to each system (fixed in docs/experiments-round2.md, section B).

STORM is given the entry title as its topic. PaperQA2 and GraphRAG, which answer
questions, are given the same six section questions per entry; their answers are
concatenated in this order. The wording is neutral: it names the disorder, asks for
statements supported by and cited to the supplied papers, and says nothing about how the
answer is scored or about any reference fact list. The title is the OMIM title in ordinary
capitalisation (`corpus.ordinary_title`); the causal gene is not named.
"""

from __future__ import annotations

from .corpus import ordinary_title

#: (section key, section heading, question template). `{title}` is the title in ordinary capitalisation.
SECTION_QUESTIONS: tuple[tuple[str, str, str], ...] = (
    ("description", "Description",
     "What is {title}? Give a concise description of the disorder: its main features, its cause as far as "
     "it is known, and how it was first recognised. Cite the papers that support each statement."),
    ("clinical_features", "Clinical features",
     "What are the clinical features of {title}? Describe the patients and families reported, including age "
     "at onset, signs and symptoms, the findings of investigations, and the course of the disease. Cite the "
     "papers that support each statement."),
    ("inheritance", "Inheritance",
     "How is {title} inherited? State the mode of inheritance and the evidence for it in the reported "
     "families. Cite the papers that support each statement."),
    ("molecular_genetics", "Molecular genetics",
     "What is known about the molecular genetics of {title}? Name the gene or genes involved and, for each "
     "paper, the variants it reported and in which patients or families. Cite the papers that support each "
     "statement."),
    ("genotype_phenotype", "Genotype-phenotype correlations",
     "What relationships between genotype and phenotype have been reported for {title}? Cite the papers that "
     "support each statement."),
    ("pathogenesis", "Pathogenesis and functional studies",
     "What is known about the pathogenesis of {title}, and what functional evidence (cellular, biochemical "
     "or animal studies) has been reported? Cite the papers that support each statement."),
)


def storm_topic(title: str) -> str:
    """STORM's topic: the entry title (OMIM's upper-case title is put into ordinary capitalisation)."""
    return ordinary_title(title)


def section_questions(title: str) -> list[dict[str, str]]:
    """The six questions for one entry: [{key, section, question}], in their fixed order."""
    t = ordinary_title(title)
    return [{"key": key, "section": heading, "question": template.format(title=t)}
            for key, heading, template in SECTION_QUESTIONS]


if __name__ == "__main__":
    import sys

    title = " ".join(sys.argv[1:]) or "ATRIAL STANDSTILL 1"
    print("STORM topic:", storm_topic(title))
    for q in section_questions(title):
        print(f"[{q['section']}] {q['question']}")
