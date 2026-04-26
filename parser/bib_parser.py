"""BibTeX file parser for academic literature records."""

from pathlib import Path
from typing import List, Optional

import bibtexparser

from models.paper import Paper
from utils.text import clean_abstract, normalize_doi


def _safe_year(value) -> Optional[int]:
    """Extract a valid year from a BibTeX year field."""
    if not value:
        return None

    value = str(value).strip()

    if value.isdigit() and len(value) == 4:
        return int(value)

    # Try to extract 4-digit year
    for i in range(len(value) - 3):
        if value[i : i + 4].isdigit():
            return int(value[i : i + 4])

    return None


def parse_bib_file(file_path: str | Path) -> List[Paper]:
    """Parse a BibTeX file into a list of Paper objects.

    Args:
        file_path: Path to the BibTeX file.

    Returns:
        List of Paper objects parsed from the file.
    """
    file_path = Path(file_path)

    with file_path.open("r", encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    papers: List[Paper] = []

    for entry in bib_database.entries:
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        # Clean LaTeX braces
        title = title.replace("{", "").replace("}", "")

        abstract = clean_abstract(entry.get("abstract") or "")
        if abstract:
            abstract = abstract.replace("{", "").replace("}", "")

        # Parse authors
        author_str = entry.get("author") or ""
        authors = []
        if author_str:
            author_str = author_str.replace("{", "").replace("}", "")
            authors = [a.strip() for a in author_str.split(" and ") if a.strip()]

        year = _safe_year(entry.get("year"))
        doi = normalize_doi(entry.get("doi"))
        venue = (entry.get("journal") or entry.get("booktitle") or "").strip()
        venue = venue.replace("{", "").replace("}", "")
        url = entry.get("url") or entry.get("ee")

        keywords_str = entry.get("keywords") or ""
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        papers.append(
            Paper(
                title=title,
                abstract=abstract,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                url=url,
                source="bibtex",
                keywords=keywords,
            )
        )

    return papers
