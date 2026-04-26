"""OpenAlex academic database retriever.

Strategy: "Precise recall via filter.title.search, broadened by per-term queries."
When keyword_groups are provided, the retriever queries each term individually
via OpenAlex's filter.title.search API, then applies boolean_filter() to keep
only papers matching ALL AND-groups.
"""

import os
from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import normalize_doi
from utils.boolean_filter import boolean_filter
from utils.logging import get_logger

logger = get_logger(__name__)


class OpenAlexRetriever(BaseRetriever):
    """Retriever for the OpenAlex academic database.

    OpenAlex is a free, open catalog of the global research system.
    No API key required, but providing an email enables the polite pool
    for faster access.

    Search strategy:
    - Without keyword_groups: uses the 'search' parameter (full-text relevance)
    - With keyword_groups: uses 'filter.title.search' per term for precision,
      then boolean_filter() for AND/OR logic
    """

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: Optional[str] = None):
        self.email = email or os.getenv("OPENALEX_EMAIL")
        if self.email and ("example.com" in self.email or "your_" in self.email):
            logger.warning(
                f"OPENALEX_EMAIL='{self.email}' looks like a placeholder. "
                "Set a real email in .env to access the polite pool "
                "(faster, more reliable API access)."
            )
            self.email = None

    @property
    def name(self) -> str:
        return "OpenAlex"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    def _request(self, params: dict) -> dict:
        if self.email:
            params["mailto"] = self.email

        with httpx.Client(timeout=30) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()

    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        keyword_groups: Optional[List[List[str]]] = None,
    ) -> List[Paper]:
        """Search OpenAlex for papers matching the query.

        When keyword_groups are provided, uses a precise search strategy:
        - Queries each term via filter.title.search (much more relevant than
          the generic 'search' parameter)
        - Merges all results
        - Applies boolean_filter() to keep only papers matching ALL groups

        Args:
            query: Broad recall query string.
            max_results: Desired number of final results.
            from_year: Start year filter (inclusive).
            to_year: End year filter (inclusive).
            keyword_groups: Optional boolean filter groups for post-filtering.
        """
        if keyword_groups:
            return self._search_with_boolean_filter(
                query, max_results, from_year, to_year, keyword_groups
            )

        return self._search_fuzzy(query, max_results, from_year, to_year)

    def _search_with_boolean_filter(
        self,
        fallback_query: str,
        max_results: int,
        from_year: Optional[int],
        to_year: Optional[int],
        keyword_groups: List[List[str]],
    ) -> List[Paper]:
        """Search with per-term queries + boolean filtering.

        Strategy (3 layers of recall):
        1. filter.title.search per term — precise, finds papers with term in title
        2. filter.abstract.search per term — broader, finds papers mentioning term
           in their abstract
        3. Generic 'search' fallback — broadest, full-text relevance search

        All results are merged (dedup), then boolean_filter() keeps only
        papers matching ALL AND-groups.
        """
        seen_dois = set()
        seen_titles_normalized = set()
        all_papers: List[Paper] = []

        total_terms = sum(len(g) for g in keyword_groups)
        per_term_limit = max(max_results, max(200, 400 // max(total_terms, 1)))
        logger.info(
            f"Boolean filtering: {total_terms} terms across {len(keyword_groups)} groups, "
            f"per-term limit = {per_term_limit}"
        )

        # Layer 1: title.search per term (most precise)
        for idx, group in enumerate(keyword_groups):
            group_total = 0
            for term in group:
                logger.info(f"  Group {idx + 1} title.search: '{term}'")
                try:
                    term_papers = self._search_title(
                        term, per_term_limit, from_year, to_year
                    )
                except Exception as e:
                    logger.error(f"  title.search '{term}' failed: {e}")
                    term_papers = []

                added = self._merge_papers(
                    term_papers, all_papers, seen_dois, seen_titles_normalized
                )
                group_total += added
                logger.info(
                    f"    title.search '{term}': {len(term_papers)} fetched, {added} new"
                )

            logger.info(f"  Group {idx + 1} title.search total new: {group_total}")

        # Layer 2: abstract.search per term (broader recall)
        # Only needed if we haven't filled our quota yet
        for idx, group in enumerate(keyword_groups):
            for term in group:
                logger.info(f"  Group {idx + 1} abstract.search: '{term}'")
                try:
                    term_papers = self._search_abstract(
                        term, per_term_limit, from_year, to_year
                    )
                except Exception as e:
                    logger.error(f"  abstract.search '{term}' failed: {e}")
                    term_papers = []

                added = self._merge_papers(
                    term_papers, all_papers, seen_dois, seen_titles_normalized
                )
                logger.info(
                    f"    abstract.search '{term}': {len(term_papers)} fetched, {added} new"
                )

        # Layer 3: generic search fallback
        logger.info(f"  Fallback fuzzy query: '{fallback_query}'")
        try:
            fallback_papers = self._search_fuzzy(
                fallback_query, per_term_limit, from_year, to_year
            )
        except Exception as e:
            logger.error(f"  Fallback query failed: {e}")
            fallback_papers = []

        added = self._merge_papers(
            fallback_papers, all_papers, seen_dois, seen_titles_normalized
        )
        logger.info(
            f"  Fallback: {len(fallback_papers)} fetched, {added} new"
        )

        logger.info(
            f"Total candidates before boolean filter: {len(all_papers)}"
        )

        # Apply boolean filtering
        papers = boolean_filter(all_papers, keyword_groups)
        logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]

    def _search_title(
        self,
        query: str,
        max_results: int,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:
        """Search using filter.title.search — searches only in paper titles.

        This is much more precise than the generic 'search' parameter,
        which does full-text search and returns many irrelevant results
        sorted by citation count.
        """
        filters = [f"title.search:{query}"]
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        return self._fetch_pages(
            params_extra={"filter": ",".join(filters)},
            max_results=max_results,
            sort="cited_by_count:desc",
        )

    def _search_abstract(
        self,
        query: str,
        max_results: int,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:
        """Search using filter.abstract.search — searches in paper abstracts.

        Broader than title.search but more targeted than generic search.
        """
        filters = [f"abstract.search:{query}"]
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        return self._fetch_pages(
            params_extra={"filter": ",".join(filters)},
            max_results=max_results,
            sort="cited_by_count:desc",
        )

    @staticmethod
    def _merge_papers(
        new_papers: List[Paper],
        all_papers: List[Paper],
        seen_dois: set,
        seen_titles_normalized: set,
    ) -> int:
        """Merge new papers into all_papers with dedup. Returns count of new additions."""
        added = 0
        for p in new_papers:
            if OpenAlexRetriever._is_new_paper(p, seen_dois, seen_titles_normalized):
                all_papers.append(p)
                added += 1
        return added

    def _search_fuzzy(
        self,
        query: str,
        max_results: int,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:
        """Search using the generic 'search' parameter (full-text relevance).

        Used as fallback or when no keyword_groups are provided.
        Note: this often returns irrelevant high-citation papers for
        niche queries.
        """
        filters = []
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        params_extra = {"search": query}
        if filters:
            params_extra["filter"] = ",".join(filters)

        return self._fetch_pages(
            params_extra=params_extra,
            max_results=max_results,
            sort="cited_by_count:desc",
        )

    def _fetch_pages(
        self,
        params_extra: dict,
        max_results: int,
        sort: str = "cited_by_count:desc",
    ) -> List[Paper]:
        """Paginated fetch with shared paper-parsing logic."""
        papers: List[Paper] = []
        per_page = 50
        page = 1

        while len(papers) < max_results:
            params = {
                "per-page": per_page,
                "page": page,
                "sort": sort,
            }
            params.update(params_extra)

            try:
                data = self._request(params)
            except Exception as e:
                logger.error(f"OpenAlex request failed: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                title = item.get("title")
                if not title:
                    continue

                abstract = self._reconstruct_abstract(
                    item.get("abstract_inverted_index")
                )

                authorships = item.get("authorships") or []
                authors = []
                for a in authorships:
                    author = a.get("author") or {}
                    name = author.get("display_name")
                    if name:
                        authors.append(name)

                doi = normalize_doi(item.get("doi"))

                venue = None
                primary_location = item.get("primary_location") or {}
                source = primary_location.get("source") or {}
                venue = source.get("display_name")

                papers.append(
                    Paper(
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=item.get("publication_year"),
                        venue=venue,
                        doi=doi,
                        url=item.get("id"),
                        source="openalex",
                        citation_count=item.get("cited_by_count"),
                    )
                )

                if len(papers) >= max_results:
                    break

            # Check if there are more pages
            meta = data.get("meta", {})
            next_cursor = meta.get("next_cursor")
            if not next_cursor and len(results) < per_page:
                break

            page += 1
            if page > 20:  # Safety limit
                break

        return papers

    @staticmethod
    def _is_new_paper(
        paper: Paper,
        seen_dois: set,
        seen_titles_normalized: set,
    ) -> bool:
        """Check if a paper is not already in the seen sets."""
        if paper.doi and paper.doi in seen_dois:
            return False
        if paper.doi:
            seen_dois.add(paper.doi)

        from utils.boolean_filter import normalize
        norm_title = normalize(paper.title or "")
        if norm_title and norm_title in seen_titles_normalized:
            return False
        if norm_title:
            seen_titles_normalized.add(norm_title)

        return True

    @staticmethod
    def _reconstruct_abstract(index: Optional[dict]) -> Optional[str]:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not index:
            return None

        words = []
        for word, positions in index.items():
            for pos in positions:
                words.append((pos, word))

        words.sort(key=lambda x: x[0])
        return " ".join(word for _, word in words)
