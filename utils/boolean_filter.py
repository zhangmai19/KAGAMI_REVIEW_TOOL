"""Boolean filter for paper retrieval results.

Implements TS-style boolean logic (AND across groups, OR within groups)
as a post-retrieval Python filter.

Design principle: "OpenAlex recalls broadly, Python filters precisely."

keyword_groups semantics:
    [
        ["A1", "A2", ...],   # Group A (OR within)
        ["B1", "B2", ...],   # Group B (OR within)
    ]
    => (any term in group A) AND (any term in group B)

This is equivalent to Web of Science TS= boolean queries.
"""

import re
from typing import List, Optional

from models.paper import Paper
from utils.logging import get_logger

logger = get_logger(__name__)


def normalize(text: str) -> str:
    """Normalize text for matching: lowercase, strip punctuation."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_term(text: str, term: str) -> bool:
    """Check if a single term matches in the text.

    - Phrase (contains space): substring match
    - Single word: word-boundary match with simple plural support

    The text is expected to be pre-normalized (lowercase, no punctuation).
    The term is lowercased internally.
    """
    term = term.lower().strip()
    if not term:
        return False

    # Ensure text is normalized for matching
    text = normalize(text) if not text.islower() else text

    # Phrase → direct substring match
    if " " in term:
        return term in text

    # Single word → boundary match + simple plural (s/es)
    pattern = rf"\b{re.escape(term)}(?:s|es)?\b"
    return re.search(pattern, text) is not None


def match_group(text: str, terms: List[str]) -> bool:
    """Check if ANY term in the group matches (OR logic)."""
    return any(match_term(text, t) for t in terms)


def boolean_filter(
    papers: List[Paper],
    keyword_groups: List[List[str]],
) -> List[Paper]:
    """Filter papers using boolean logic across keyword groups.

    Args:
        papers: List of Paper objects to filter.
        keyword_groups: List of keyword groups.
            Each group is a list of terms (OR within group).
            Groups are combined with AND logic.

    Returns:
        Filtered list of Paper objects.

    Example:
        keyword_groups = [
            ["reinsurance", "risk transfer", "cat bond"],
            ["mutual insurance", "insurtech"],
            ["risk sharing", "risk pooling"],
        ]
        # => (reinsurance OR "risk transfer" OR "cat bond")
        #    AND (mutual insurance OR insurtech)
        #    AND (risk sharing OR "risk pooling")
    """
    if not keyword_groups:
        return papers

    filtered = []
    for p in papers:
        combined = normalize((p.title or "") + " " + (p.abstract or ""))
        if all(match_group(combined, group) for group in keyword_groups):
            filtered.append(p)

    logger.info(
        f"Boolean filter: {len(papers)} → {len(filtered)} papers "
        f"({len(keyword_groups)} AND-groups)"
    )
    return filtered


def expanded_keywords_to_groups(
    expanded: dict,
) -> List[List[str]]:
    """Convert KeywordExpander output to keyword_groups format.

    Each concept becomes one AND-group; synonyms/variants are OR-terms
    within that group.

    Args:
        expanded: Output from KeywordExpander.expand(), with structure:
            {
                "concepts": [
                    {
                        "concept": "machine learning",
                        "synonyms": ["ML", ...],
                        "variants": ["machine learnings", ...],
                        ...
                    },
                    ...
                ]
            }

    Returns:
        keyword_groups suitable for boolean_filter().
    """
    groups = []
    for concept in expanded.get("concepts", []):
        terms = []
        main = concept.get("concept", "")
        if main:
            terms.append(main)
        terms.extend(concept.get("synonyms", []))
        terms.extend(concept.get("variants", []))
        # Deduplicate while preserving order
        seen = set()
        unique_terms = []
        for t in terms:
            t_lower = t.lower()
            if t_lower not in seen:
                seen.add(t_lower)
                unique_terms.append(t)
        if unique_terms:
            groups.append(unique_terms)
    return groups


def groups_to_broad_query(keyword_groups: List[List[str]]) -> str:
    """Generate a broad recall query string from keyword groups.

    Takes the first (most representative) term from each group
    to form a simple, broad query for the search API.

    This implements the "broad recall" strategy:
    the API returns many results, then boolean_filter() narrows them down.

    Args:
        keyword_groups: List of keyword groups.

    Returns:
        A space-joined query string.
    """
    terms = []
    for group in keyword_groups:
        if group:
            # Use the first term (main concept) from each group
            terms.append(group[0])
    return " ".join(terms)
