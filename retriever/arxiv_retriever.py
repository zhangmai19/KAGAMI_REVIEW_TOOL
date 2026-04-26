"""arXiv preprint retriever."""

from typing import List, Optional
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import clean_abstract, normalize_doi
from utils.logging import get_logger

logger = get_logger(__name__)


class ArxivRetriever(BaseRetriever):
    """Retriever for arXiv preprints via the arXiv API."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "arXiv"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    def _request(self, params: dict) -> str:
        with httpx.Client(timeout=30) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.text

    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:
        """Search arXiv for papers matching the query."""
        papers: List[Paper] = []
        start = 0
        per_page = 50

        while len(papers) < max_results:
            params = {
                "search_query": f"all:{query}",
                "start": start,
                "max_results": min(per_page, max_results - len(papers)),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            try:
                xml_text = self._request(params)
            except Exception as e:
                logger.error(f"arXiv request failed: {e}")
                break

            new_papers = self._parse_xml(xml_text)

            if not new_papers:
                break

            # Apply year filter
            for paper in new_papers:
                if from_year and paper.year and paper.year < from_year:
                    continue
                if to_year and paper.year and paper.year > to_year:
                    continue
                papers.append(paper)

                if len(papers) >= max_results:
                    break

            if len(new_papers) < per_page:
                break

            start += per_page

            if start > 500:
                break

        logger.info(f"arXiv: retrieved {len(papers)} papers")
        return papers

    def _parse_xml(self, xml_text: str) -> List[Paper]:
        """Parse arXiv Atom XML response into Paper objects."""
        papers: List[Paper] = []

        # Define namespace
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"arXiv XML parse error: {e}")
            return papers

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else None
            if not title:
                continue

            summary_el = entry.find("atom:summary", ns)
            abstract = clean_abstract(summary_el.text.strip()) if summary_el is not None and summary_el.text else None

            authors = []
            for author_el in entry.findall("atom:author", ns):
                name_el = author_el.find("atom:name", ns)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            # Year from published date
            year = None
            published_el = entry.find("atom:published", ns)
            if published_el is not None and published_el.text:
                try:
                    year = int(published_el.text[:4])
                except (ValueError, IndexError):
                    pass

            # DOI
            doi_el = entry.find("arxiv:doi", ns)
            doi = normalize_doi(doi_el.text) if doi_el is not None and doi_el.text else None

            # URL
            entry_id = entry.find("atom:id", ns)
            url = entry_id.text if entry_id is not None and entry_id.text else None

            # Categories as keywords
            keywords = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term")
                if term:
                    keywords.append(term)

            papers.append(
                Paper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    year=year,
                    doi=doi,
                    url=url,
                    source="arxiv",
                    keywords=keywords,
                )
            )

        return papers
