"""Boolean query builder abstract base class and implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BooleanQueryBuilder(ABC):
    """Abstract base class for database-specific boolean query builders."""

    @abstractmethod
    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        """Build a boolean query from expanded keywords.

        Args:
            expanded_keywords: Output from KeywordExpander.expand().

        Returns:
            Boolean query string for the target database.
        """
        ...

    @property
    @abstractmethod
    def database_name(self) -> str:
        """Name of the target database."""
        ...


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
    """Boolean query builder for OpenAlex API."""

    @property
    def database_name(self) -> str:
        return "OpenAlex"

    def build(self, expanded_keywords: Dict[str, Any]) -> str:
        # OpenAlex uses simple text search
        concepts = expanded_keywords.get("concepts", [])
        if not concepts:
            return ""

        terms = []
        for concept in concepts:
            terms.append(concept.get("concept", ""))

        return " ".join(t for t in terms if t)


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
