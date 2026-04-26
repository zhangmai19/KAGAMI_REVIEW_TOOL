"""Crossref academic database retriever."""

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


class CrossrefRetriever(BaseRetriever):
    """Retriever for the Crossref academic database.

    Free API. Providing an email enables the polite pool.
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: Optional[str] = None):
        self.email = email or os.getenv("CROSSREF_EMAIL")

    @property
    def name(self) -> str:
        return "Crossref"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    def _request(self, params: dict) -> dict:
        headers = {}
        if self.email:
            headers["User-Agent"] = (
                f"AutoLitReview-Agent/0.1 (mailto:{self.email})"
            )

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
        """Search Crossref for papers matching the query."""
        papers: List[Paper] = []
        offset = 0
        per_page = 50

        while len(papers) < max_results:
            params = {
                "query": query,
                "rows": min(per_page, max_results - len(papers)),
                "offset": offset,
                "sort": "relevance",
            }

            if from_year:
                params["filter"] = f"from-pub-date:{from_year}"
            if to_year:
                date_filter = f"until-pub-date:{to_year}"
                params["filter"] = (
                    f"{params.get('filter', '')},{date_filter}"
                    if "filter" in params
                    else date_filter
                )

            try:
                data = self._request(params)
            except Exception as e:
                logger.error(f"Crossref request failed: {e}")
                break

            message = data.get("message", {})
            items = message.get("items", [])

            if not items:
                break

            for item in items:
                title_list = item.get("title") or []
                title = title_list[0] if title_list else None
                if not title:
                    continue

                # Crossref abstracts may be in HTML
                abstract = item.get("abstract")
                if abstract:
                    import re
                    abstract = re.sub(r"<[^>]+>", "", abstract)
                    abstract = clean_abstract(abstract)

                author_list = item.get("author") or []
                authors = []
                for a in author_list:
                    given = a.get("given", "")
                    family = a.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)

                # Extract year
                year = None
                pub_date = item.get("published-print") or item.get("published-online") or {}
                date_parts = pub_date.get("date-parts") or [[]]
                if date_parts and date_parts[0]:
                    year = date_parts[0][0]

                doi = normalize_doi(item.get("DOI"))

                # Venue
                venue = None
                container = item.get("container-title") or []
                if container:
                    venue = container[0]

                url = item.get("URL")

                papers.append(
                    Paper(
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        venue=venue,
                        doi=doi,
                        url=url,
                        source="crossref",
                        citation_count=item.get("is-referenced-by-count"),
                    )
                )

                if len(papers) >= max_results:
                    break

            total = message.get("total-results", 0)
            if offset + per_page >= total:
                break

            offset += per_page

            if offset > 1000:
                break

        logger.info(f"Crossref: retrieved {len(papers)} papers before filtering")

        if keyword_groups:
            papers = boolean_filter(papers, keyword_groups)
            logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]
