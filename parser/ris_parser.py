"""RIS file parser for academic literature records."""

from pathlib import Path
from typing import List, Optional

import rispy

from models.paper import Paper
from utils.text import clean_abstract, normalize_doi


def _safe_year(value) -> Optional[int]:
    """Extract a valid year from various RIS date field formats."""
    if not value:
        return None

    if isinstance(value, int):
        return value

    value = str(value).strip()

    # Try to extract 4-digit year
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])

    return None


def parse_ris_file(file_path: str | Path) -> List[Paper]:
    """Parse a RIS file into a list of Paper objects.

    Args:
        file_path: Path to the RIS file.

    Returns:
        List of Paper objects parsed from the file.
    """
    file_path = Path(file_path)

    with file_path.open("r", encoding="utf-8-sig") as f:
        entries = rispy.load(f)

    papers: List[Paper] = []

    for entry in entries:
        title = (
            entry.get("title")
            or entry.get("primary_title")
            or entry.get("secondary_title")
            or ""
        ).strip()

        abstract = clean_abstract(
            entry.get("abstract")
            or entry.get("notes_abstract")
            or ""
        )

        authors = entry.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]

        year = _safe_year(
            entry.get("year")
            or entry.get("publication_year")
            or entry.get("date")
        )

        doi = normalize_doi(entry.get("doi"))

        venue = (
            entry.get("journal_name")
            or entry.get("secondary_title")
            or entry.get("publication_name")
        )

        url = entry.get("url")
        if isinstance(url, list):
            url = url[0] if url else None

        keywords = entry.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]

        if not title:
            continue

        papers.append(
            Paper(
                title=title,
                abstract=abstract,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                url=url,
                source="ris",
                keywords=keywords,
            )
        )

    return papers
