"""Google Scholar retriever via SerpAPI.

WARNING: Direct scraping of Google Scholar is not recommended due to
Terms of Service and rate limiting. This module uses SerpAPI for
compliance and stability.
"""

import os
from typing import List, Optional

import httpx

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import clean_abstract, normalize_doi
from utils.boolean_filter import boolean_filter
from utils.logging import get_logger

logger = get_logger(__name__)


class ScholarRetriever(BaseRetriever):
    """Retriever for Google Scholar via SerpAPI.

    Requires a SerpAPI key. This is the recommended approach
    for accessing Google Scholar data.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")

    @property
    def name(self) -> str:
        return "Google Scholar"

    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        keyword_groups: Optional[List[List[str]]] = None,
    ) -> List[Paper]:
        """Search Google Scholar via SerpAPI."""
        if not self.api_key:
            logger.warning("SerpAPI key not provided. Skipping Google Scholar search.")
            return []

        papers: List[Paper] = []
        start = 0
        per_page = 20

        while len(papers) < max_results:
            params = {
                "engine": "google_scholar",
                "q": query,
                "num": per_page,
                "start": start,
                "api_key": self.api_key,
            }

            if from_year:
                params["as_ylo"] = from_year
            if to_year:
                params["as_yhi"] = to_year

            try:
                with httpx.Client(timeout=30) as client:
                    response = client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
            except Exception as e:
                logger.error(f"SerpAPI request failed: {e}")
                break

            results = data.get("organic_results", [])

            if not results:
                break

            for item in results:
                title = item.get("title")
                if not title:
                    continue

                # Remove HTML tags from title
                import re
                title = re.sub(r"<[^>]+>", "", title)

                # Snippet as abstract proxy
                snippet = item.get("snippet", "")
                abstract = clean_abstract(snippet) if snippet else None

                # Publication info
                pub_info = item.get("publication_info", {})
                authors_str = pub_info.get("authors", [])
                authors = []
                if isinstance(authors_str, list):
                    for a in authors_str:
                        name = a.get("name", "")
                        if name:
                            authors.append(name)

                # Extract year from summary
                year = None
                summary = pub_info.get("summary", "")
                year_match = re.search(r"\b(19|20)\d{2}\b", summary)
                if year_match:
                    year = int(year_match.group())

                url = item.get("link")

                papers.append(
                    Paper(
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        url=url,
                        source="google_scholar",
                    )
                )

                if len(papers) >= max_results:
                    break

            # Check pagination
            pagination = data.get("serpapi_pagination", {})
            if not pagination.get("next"):
                break

            start += per_page

            if start > 200:
                break

        logger.info(f"Google Scholar: retrieved {len(papers)} papers before filtering")

        if keyword_groups:
            papers = boolean_filter(papers, keyword_groups)
            logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]
