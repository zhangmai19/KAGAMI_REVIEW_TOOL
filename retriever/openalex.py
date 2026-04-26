"""OpenAlex academic database retriever.

Strategy: "Broad recall via API, precise filtering via Python boolean logic."
When keyword_groups are provided, the retriever fetches more results from
OpenAlex and then applies boolean_filter() to narrow them down.
"""

import os
from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import clean_abstract, normalize_doi
from utils.boolean_filter import boolean_filter
from utils.logging import get_logger

logger = get_logger(__name__)


class OpenAlexRetriever(BaseRetriever):
    """Retriever for the OpenAlex academic database.

    OpenAlex is a free, open catalog of the global research system.
    No API key required, but providing an email enables the polite pool
    for faster access.
    """

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: Optional[str] = None):
        self.email = email or os.getenv("OPENALEX_EMAIL")

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

        When keyword_groups are provided, uses a broad-recall strategy:
        fetches more results from the API, then applies boolean_filter()
        to precisely narrow down to papers matching the AND/OR logic.

        Args:
            query: Broad recall query string (e.g. "insurance risk model").
            max_results: Desired number of final results.
            from_year: Start year filter (inclusive).
            to_year: End year filter (inclusive).
            keyword_groups: Optional boolean filter groups for post-filtering.
        """
        # If boolean filtering is active, fetch more to compensate for filtering loss
        fetch_limit = max_results
        if keyword_groups:
            fetch_limit = max(max_results * 5, 500)
            logger.info(
                f"Boolean filtering active: fetching {fetch_limit} papers "
                f"to filter down to ~{max_results}"
            )

        papers: List[Paper] = []
        per_page = 50
        page = 1

        filters = []
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        while len(papers) < fetch_limit:
            params = {
                "search": query,
                "per-page": per_page,
                "page": page,
                "sort": "cited_by_count:desc",
            }

            if filters:
                params["filter"] = ",".join(filters)

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

                if len(papers) >= fetch_limit:
                    break

            # Check if there are more pages
            meta = data.get("meta", {})
            next_cursor = meta.get("next_cursor")
            if not next_cursor and len(results) < per_page:
                break

            page += 1

            if page > 20:  # Safety limit
                break

        logger.info(f"OpenAlex: retrieved {len(papers)} papers before filtering")

        # Apply boolean filtering if keyword_groups are provided
        if keyword_groups:
            papers = boolean_filter(papers, keyword_groups)
            logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]

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
