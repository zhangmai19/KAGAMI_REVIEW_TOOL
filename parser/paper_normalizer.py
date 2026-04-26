"""Paper normalization and numbering utilities."""

from typing import List

from models.paper import Paper


def assign_paper_ids(papers: List[Paper], prefix: str = "#") -> List[Paper]:
    """Assign stable evidence IDs to papers.

    Args:
        papers: List of Paper objects.
        prefix: ID prefix (default "#").

    Returns:
        The same list with IDs assigned.
    """
    for idx, paper in enumerate(papers, start=1):
        paper.id = f"{prefix}{idx}"

    return papers


def papers_to_numbered_text(papers: List[Paper]) -> str:
    """Convert papers into a strict text format for LLM input.

    Format:
        [#1]
        Title: ...
        Authors: ...
        Year: ...
        Venue: ...
        DOI: ...
        Abstract: ...
    """
    blocks = []

    for paper in papers:
        authors = ", ".join(paper.authors) if paper.authors else "Unknown"
        year = paper.year if paper.year else "Unknown"
        abstract = paper.abstract or "No abstract available."

        block = (
            f"[{paper.id}]\n"
            f"Title: {paper.title}\n"
            f"Authors: {authors}\n"
            f"Year: {year}\n"
            f"Venue: {paper.venue or 'Unknown'}\n"
            f"DOI: {paper.doi or 'Unknown'}\n"
            f"Abstract: {abstract}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def filter_papers_with_abstracts(papers: List[Paper]) -> tuple[List[Paper], List[Paper]]:
    """Separate papers into those with and without abstracts.

    Returns:
        Tuple of (papers_with_abstracts, papers_without_abstracts)
    """
    with_abstract = []
    without_abstract = []

    for paper in papers:
        if paper.abstract and paper.abstract.strip():
            with_abstract.append(paper)
        else:
            without_abstract.append(paper)

    return with_abstract, without_abstract
