"""Boolean query builder abstract base class and implementations.

Each builder produces two things:
1. A database-specific boolean query string (for display / export / WoS API)
2. keyword_groups: a structured list-of-lists used by boolean_filter()
   for post-retrieval Python-side filtering

For OpenAlex and other free-text APIs, the strategy is:
- "Broad recall via API, precise filtering via Python boolean logic"
- The query string is a simple broad query (first term from each group)
- keyword_groups are used by retrievers to filter results after fetching
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BooleanQueryBuilder(ABC):
    """Abstract base class for database-specific boolean query builders."""

    @abstractmethod
    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        """Build a boolean query string from expanded keywords.

        Args:
            expanded_keywords: Output from KeywordExpander.expand().

        Returns:
            Boolean query string for the target database.
        """
        ...

    def build_keyword_groups(
        self, expanded_keywords: Dict[str, Any]
    ) -> List[List[str]]:
        """Extract keyword_groups from expanded keywords.

        Each concept becomes one AND-group; synonyms/variants are OR-terms.

        Args:
            expanded_keywords: Output from KeywordExpander.expand().

        Returns:
            keyword_groups for boolean_filter().
        """
        groups = []
        for concept in expanded_keywords.get("concepts", []):
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

    def build_broad_query(
        self, expanded_keywords: Dict[str, Any]
    ) -> str:
        """Generate a broad recall query string for API search.

        Takes the first (most representative) term from each group.
        """
        groups = self.build_keyword_groups(expanded_keywords)
        terms = [g[0] for g in groups if g]
        return " ".join(terms)

    @property
    @abstractmethod
    def database_name(self) -> str:
        """Name of the target database."""
        ...

    def build_all(
        self, expanded_keywords: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build all query artifacts at once.

        Returns:
            {
                "boolean_query": str,        # DB-specific query string
                "keyword_groups": list,      # For boolean_filter()
                "broad_query": str,          # For API search
            }
        """
        return {
            "boolean_query": self.build(expanded_keywords),
            "keyword_groups": self.build_keyword_groups(expanded_keywords),
            "broad_query": self.build_broad_query(expanded_keywords),
        }


class WoSQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for Web of Science."""

    @property
    def database_name(self) -> str:
        return "Web of Science"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        concept_groups = []
        exclude_terms = []

        for concept in concepts:
            terms = [concept.get("concept", "")]
            terms.extend(concept.get("synonyms", []))
            terms.extend(concept.get("variants", []))
            terms = [t for t in terms if t]

            if terms:
                quoted = [f'"{t}"' if " " in t else t for t in terms]
                concept_groups.append(f'({" OR ".join(quoted)})')

            excludes = concept.get("exclude_terms", [])
            exclude_terms.extend(excludes)

        query = " AND\n".join(concept_groups)

        if exclude_terms:
            quoted_excludes = [f'"{t}"' for t in exclude_terms]
            query += f'\nNOT TS=({" OR ".join(quoted_excludes)})'

        return f"TS=({query})"


class ScopusQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for Scopus."""

    @property
    def database_name(self) -> str:
        return "Scopus"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        concept_groups = []
        exclude_terms = []

        for concept in concepts:
            terms = [concept.get("concept", "")]
            terms.extend(concept.get("synonyms", []))
            terms.extend(concept.get("variants", []))
            terms = [t for t in terms if t]

            if terms:
                quoted = [f'"{t}"' if " " in t else t for t in terms]
                concept_groups.append(f'({" OR ".join(quoted)})')

            excludes = concept.get("exclude_terms", [])
            exclude_terms.extend(excludes)

        query = "\n  AND\n  ".join(concept_groups)

        result = f"TITLE-ABS-KEY(\n  {query}\n)"

        if exclude_terms:
            quoted_excludes = [f'"{t}"' for t in exclude_terms]
            result += f'\nAND NOT TITLE-ABS-KEY({" OR ".join(quoted_excludes)})'

        return result


class PubMedQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for PubMed."""

    @property
    def database_name(self) -> str:
        return "PubMed"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        concept_groups = []
        exclude_terms = []

        for concept in concepts:
            terms = [concept.get("concept", "")]
            terms.extend(concept.get("synonyms", []))
            terms.extend(concept.get("variants", []))
            terms = [t for t in terms if t]

            if terms:
                quoted = [f'"{t}"[Title/Abstract]' if " " in t else f'{t}[Title/Abstract]' for t in terms]
                concept_groups.append(f'({" OR ".join(quoted)})')

            excludes = concept.get("exclude_terms", [])
            exclude_terms.extend(excludes)

        query = " AND ".join(concept_groups)

        if exclude_terms:
            quoted_excludes = [f'"{t}"[Title/Abstract]' for t in exclude_terms]
            query += f' NOT ({" OR ".join(quoted_excludes)})'

        return query


class ScholarQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for Google Scholar (simplified format)."""

    @property
    def database_name(self) -> str:
        return "Google Scholar"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        concept_groups = []

        for concept in concepts:
            terms = [concept.get("concept", "")]
            terms.extend(concept.get("synonyms", []))
            terms = [t for t in terms if t]

            if terms:
                # Scholar uses simple OR groups
                quoted = [f'"{t}"' if " " in t else t for t in terms[:3]]  # Limit terms
                concept_groups.append(f'({" OR ".join(quoted)})')

        return " ".join(concept_groups)


class OpenAlexQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for OpenAlex API.

    OpenAlex does not natively support boolean queries in its search API.
    Strategy: generate a broad recall query (first term from each group),
    then use keyword_groups for Python-side boolean filtering.
    """

    @property
    def database_name(self) -> str:
        return "OpenAlex"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        """Build a broad recall query for OpenAlex.

        Uses the main concept from each group to maximize recall.
        Precise filtering is handled by keyword_groups + boolean_filter().
        """
        return self.build_broad_query(expanded_keywords)


class ArxivQueryBuilder(BooleanQueryBuilder):
    """Boolean query builder for arXiv API."""

    @property
    def database_name(self) -> str:
        return "arXiv"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        terms = []
        for concept in concepts:
            terms.append(concept.get("concept", ""))
            terms.extend(concept.get("synonyms", [])[:2])

        return " AND ".join(f'all:"{t}"' for t in terms if t)


def get_builder(database: str) -> BooleanQueryBuilder:
    """Get the appropriate boolean query builder for a database.

    Args:
        database: Database name string.

    Returns:
        BooleanQueryBuilder instance.
    """
    builders = {
        "wos": WoSQueryBuilder,
        "web_of_science": WoSQueryBuilder,
        "scopus": ScopusQueryBuilder,
        "pubmed": PubMedQueryBuilder,
        "scholar": ScholarQueryBuilder,
        "google_scholar": ScholarQueryBuilder,
        "openalex": OpenAlexQueryBuilder,
        "arxiv": ArxivQueryBuilder,
    }

    builder_class = builders.get(database.lower())
    if not builder_class:
        raise ValueError(
            f"Unknown database: {database}. "
            f"Supported: {', '.join(builders.keys())}"
        )

    return builder_class()
