"""Utility functions for deduplicating paper records."""

import re
from difflib import SequenceMatcher
from typing import List, Set

from models.paper import Paper


def normalize_title(title: str) -> str:
    """Normalize a paper title for comparison."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def deduplicate_papers(
    papers: List[Paper],
    title_similarity_threshold: float = 0.95,
) -> List[Paper]:
    """Remove duplicate papers based on DOI and title similarity.

    Priority order:
    1. DOI exact match (case-insensitive)
    2. Normalized title exact match
    3. Title similarity above threshold
    """
    seen_dois: Set[str] = set()
    seen_titles: List[str] = []
    unique: List[Paper] = []

    for paper in papers:
        # Check DOI dedup
        if paper.doi:
            doi = paper.doi.lower().strip()
            if doi in seen_dois:
                continue
            seen_dois.add(doi)

        # Check title dedup
        norm_title = normalize_title(paper.title)

        duplicate_by_title = False
        for existing_title in seen_titles:
            sim = SequenceMatcher(None, norm_title, existing_title).ratio()
            if sim >= title_similarity_threshold:
                duplicate_by_title = True
                break

        if duplicate_by_title:
            continue

        seen_titles.append(norm_title)
        unique.append(paper)

    return unique
