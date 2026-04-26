"""Text processing utilities."""

import re
from typing import Optional


def clean_abstract(abstract: Optional[str]) -> Optional[str]:
    """Clean and normalize an abstract string."""
    if not abstract:
        return None

    abstract = abstract.strip()

    # Remove common prefix patterns
    abstract = re.sub(r"^Abstract[:\s]*", "", abstract, flags=re.IGNORECASE)
    abstract = re.sub(r"^Summary[:\s]*", "", abstract, flags=re.IGNORECASE)

    # Normalize whitespace
    abstract = re.sub(r"\s+", " ", abstract).strip()

    return abstract if abstract else None


def truncate_abstract(
    abstract: Optional[str],
    max_chars: int = 3000,
) -> tuple[Optional[str], bool]:
    """Truncate an abstract if it exceeds max_chars.

    Returns:
        Tuple of (truncated_abstract, was_truncated)
    """
    if not abstract:
        return None, False

    if len(abstract) <= max_chars:
        return abstract, False

    return abstract[:max_chars] + "...", True


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize a DOI string."""
    if not doi:
        return None

    doi = doi.strip()

    # Remove common URL prefixes
    doi = re.sub(r"^https?://doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:", "", doi, flags=re.IGNORECASE)

    return doi.lower() if doi else None
