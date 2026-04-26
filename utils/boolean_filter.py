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

    - Phrase (contains space): flexible substring match
      - Treats spaces in the term as matching any whitespace/hyphen run
      - e.g. "risk sharing" matches "risk sharing", "risk-sharing", "risk  sharing"
      - Also matches if all individual words appear nearby (within 5 words)
    - Single word: word-boundary match with simple plural support

    The text is expected to be pre-normalized (lowercase, no punctuation).
    The term is lowercased internally.
    """
    term = term.lower().strip()
    if not term:
        return False

    # Ensure text is normalized for matching
    text = normalize(text) if not text.islower() else text

    # Phrase → flexible matching
    if " " in term:
        words = term.split()

        # Strategy 1: flexible space/hyphen match
        # Build regex where spaces in term match [\s-]+ in text
        pattern_parts = [re.escape(w) for w in words]
        flexible_pattern = r"[\s-]+".join(pattern_parts)
        if re.search(flexible_pattern, text):
            return True

        # Strategy 2: proximity match — all words appear within a window
        # This catches re-orderings like "insurance, P2P-based" matching "p2p insurance"
        if len(words) <= 6:  # Only for reasonable-length phrases
            # Find positions of each word
            word_positions = []
            for w in words:
                word_pat = rf"\b{re.escape(w)}(?:s|es)?\b"
                positions = [m.start() for m in re.finditer(word_pat, text)]
                if not positions:
                    break
                word_positions.append(positions)
            else:
                # All words found — check if any combination fits within a window
                # Window size: number of words in phrase * 8 characters (generous)
                window = len(words) * 8
                if _words_within_window(word_positions, window):
                    return True

        return False

    # Single word → boundary match + simple plural (s/es)
    pattern = rf"\b{re.escape(term)}(?:s|es)?\b"
    return re.search(pattern, text) is not None


def _words_within_window(word_positions: list, window: int) -> bool:
    """Check if there's a combination of positions (one per word) all within `window` chars."""
    if len(word_positions) == 1:
        return True

    # For small number of words, try all combinations
    # (typical phrases have 2-4 words, so this is tractable)
    from itertools import product

    for combo in product(*word_positions):
        span = max(combo) - min(combo)
        if span <= window:
            return True

    return False


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
    # Diagnostics: count how many papers pass each individual group
    group_pass_counts = [0] * len(keyword_groups)
    for p in papers:
        combined = normalize((p.title or "") + " " + (p.abstract or ""))
        group_results = [match_group(combined, group) for group in keyword_groups]
        for i, passed in enumerate(group_results):
            if passed:
                group_pass_counts[i] += 1
        if all(group_results):
            filtered.append(p)

    logger.info(
        f"Boolean filter: {len(papers)} → {len(filtered)} papers "
        f"({len(keyword_groups)} AND-groups)"
    )
    for i, (group, count) in enumerate(zip(keyword_groups, group_pass_counts)):
        logger.info(
            f"  Group {i + 1} ({', '.join(group)}): "
            f"{count}/{len(papers)} papers match"
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
