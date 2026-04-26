"""Semantic Scholar academic database retriever."""

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


class SemanticScholarRetriever(BaseRetriever):
    """Retriever for the Semantic Scholar academic database.

    Free API with rate limits. An API key can be provided for
    higher rate limits.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    FIELDS = "paperId,title,abstract,authors,year,venue,externalIds,citationCount,url"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    @property
    def name(self) -> str:
        return "Semantic Scholar"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    def _request(self, params: dict) -> dict:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        with httpx.Client(timeout=30) as client:
            response = client.get(self.BASE_URL, params=params, headers=headers)
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
        """Search Semantic Scholar for papers matching the query."""
        papers: List[Paper] = []
        offset = 0
        per_page = 100

        year_filter = ""
        if from_year and to_year:
            year_filter = f"{from_year}-{to_year}"
        elif from_year:
            year_filter = f"{from_year}-"
        elif to_year:
            year_filter = f"-{to_year}"

        while len(papers) < max_results:
            params = {
                "query": query,
                "limit": min(per_page, max_results - len(papers)),
                "offset": offset,
                "fields": self.FIELDS,
            }

            if year_filter:
                params["year"] = year_filter

            try:
                data = self._request(params)
            except Exception as e:
                logger.error(f"Semantic Scholar request failed: {e}")
                break

            results = data.get("data", [])

            if not results:
                break

            for item in results:
                title = item.get("title")
                if not title:
                    continue

                abstract = clean_abstract(item.get("abstract"))

                author_list = item.get("authors") or []
                authors = [a.get("name", "") for a in author_list if a.get("name")]

                # Extract DOI from external IDs
                external_ids = item.get("externalIds") or {}
                doi = normalize_doi(external_ids.get("DOI"))

                venue = item.get("venue") or None

                papers.append(
                    Paper(
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=item.get("year"),
                        venue=venue,
                        doi=doi,
                        url=item.get("url"),
                        source="semantic_scholar",
                        citation_count=item.get("citationCount"),
                    )
                )

                if len(papers) >= max_results:
                    break

            # Check if there are more results
            total = data.get("total", 0)
            if offset + per_page >= total:
                break

            offset += per_page

            if offset > 1000:  # Safety limit
                break

        logger.info(f"Semantic Scholar: retrieved {len(papers)} papers before filtering")

        if keyword_groups:
            papers = boolean_filter(papers, keyword_groups)
            logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]
