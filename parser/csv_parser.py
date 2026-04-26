"""CSV file parser for academic literature records."""

import csv
from pathlib import Path
from typing import List, Optional

from models.paper import Paper
from utils.text import clean_abstract, normalize_doi


# Common column name mappings
COLUMN_ALIASES = {
    "title": ["title", "article_title", "document_title", "ti"],
    "abstract": ["abstract", "ab", "summary"],
    "authors": ["authors", "author", "au", "author_names"],
    "year": ["year", "publication_year", "pub_year", "py"],
    "doi": ["doi", "digital_object_identifier"],
    "venue": ["journal", "source", "venue", "publication_name", "so"],
    "url": ["url", "link", "doi_url"],
    "source": ["database", "source", "origin"],
    "keywords": ["keywords", "author_keywords", "de"],
    "citation_count": ["cited_by", "citations", "tc", "times_cited"],
}


def _find_column(headers: List[str], field: str) -> Optional[str]:
    """Find the matching column name from headers."""
    headers_lower = {h.lower().strip(): h for h in headers}
    aliases = COLUMN_ALIASES.get(field, [field])

    for alias in aliases:
        if alias in headers_lower:
            return headers_lower[alias]

    return None


def _safe_year(value) -> Optional[int]:
    """Extract a valid year from a CSV year field."""
    if not value:
        return None

    value = str(value).strip()

    if value.isdigit() and len(value) == 4:
        return int(value)

    return None


def _safe_int(value) -> Optional[int]:
    """Safely convert a value to int."""
    if not value:
        return None

    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def parse_csv_file(file_path: str | Path, encoding: str = "utf-8-sig") -> List[Paper]:
    """Parse a CSV file into a list of Paper objects.

    Supports various CSV formats from different academic databases
    by mapping common column name variants.

    Args:
        file_path: Path to the CSV file.
        encoding: File encoding (default utf-8-sig for BOM handling).

    Returns:
        List of Paper objects parsed from the file.
    """
    file_path = Path(file_path)

    with file_path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Build column mapping
        col_map = {}
        for field in COLUMN_ALIASES:
            col = _find_column(headers, field)
            if col:
                col_map[field] = col

        papers: List[Paper] = []

        for row in reader:
            title = (row.get(col_map.get("title", "")) or "").strip()
            if not title:
                continue

            abstract = clean_abstract(row.get(col_map.get("abstract", "")) or "")

            # Parse authors
            authors_str = row.get(col_map.get("authors", "")) or ""
            authors = [a.strip() for a in authors_str.split(";") if a.strip()]
            if not authors:
                authors = [a.strip() for a in authors_str.split(",") if a.strip()]

            year = _safe_year(row.get(col_map.get("year", "")))
            doi = normalize_doi(row.get(col_map.get("doi", "")))
            venue = (row.get(col_map.get("venue", "")) or "").strip()
            url = (row.get(col_map.get("url", "")) or "").strip() or None
            source = (row.get(col_map.get("source", "")) or "").strip() or "csv"

            keywords_str = row.get(col_map.get("keywords", "")) or ""
            keywords = [k.strip() for k in keywords_str.split(";") if k.strip()]

            citation_count = _safe_int(row.get(col_map.get("citation_count", "")))

            papers.append(
                Paper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    year=year,
                    venue=venue,
                    doi=doi,
                    url=url,
                    source=source,
                    keywords=keywords,
                    citation_count=citation_count,
                )
            )

    return papers
