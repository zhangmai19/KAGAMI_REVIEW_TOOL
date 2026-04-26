"""OpenAlex academic database retriever."""

from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import clean_abstract, normalize_doi
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
        self.email = email

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
    ) -> List[Paper]:
        """Search OpenAlex for papers matching the query."""
        papers: List[Paper] = []
        per_page = 50
        page = 1

        filters = []
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        while len(papers) < max_results:
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

        logger.info(f"OpenAlex: retrieved {len(papers)} papers")
        return papers

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
