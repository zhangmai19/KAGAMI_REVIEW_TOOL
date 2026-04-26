"""PubMed academic database retriever via Entrez API."""

import os
from typing import List, Optional
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper
from retriever.base import BaseRetriever
from utils.text import clean_abstract, normalize_doi
from utils.boolean_filter import boolean_filter
from utils.logging import get_logger

logger = get_logger(__name__)


class PubMedRetriever(BaseRetriever):
    """Retriever for PubMed via the NCBI Entrez API.

    Requires an NCBI API key for higher rate limits.
    Suitable for biomedical and life science literature.
    """

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")
        self.email = email or os.getenv("PUBMED_EMAIL")

    @property
    def name(self) -> str:
        return "PubMed"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    def _request(self, url: str, params: dict) -> str:
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email

        params["tool"] = "AutoLitReview-Agent"

        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.text

    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        keyword_groups: Optional[List[List[str]]] = None,
    ) -> List[Paper]:
        """Search PubMed for papers matching the query."""
        # Build date filter
        date_filter = ""
        if from_year or to_year:
            start = f"{from_year}/01/01" if from_year else "1800/01/01"
            end = f"{to_year}/12/31" if to_year else "2099/12/31"
            date_filter = f' AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'

        full_query = query + date_filter

        # Step 1: Search for PMIDs
        search_params = {
            "db": "pubmed",
            "term": full_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }

        try:
            search_text = self._request(self.SEARCH_URL, search_params)
            import json
            search_data = json.loads(search_text)
            pmids = search_data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []

        if not pmids:
            return []

        # Step 2: Fetch details
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }

        try:
            xml_text = self._request(self.FETCH_URL, fetch_params)
        except Exception as e:
            logger.error(f"PubMed fetch failed: {e}")
            return []

        # Step 3: Parse XML
        papers = self._parse_xml(xml_text)

        logger.info(f"PubMed: retrieved {len(papers)} papers before filtering")

        if keyword_groups:
            papers = boolean_filter(papers, keyword_groups)
            logger.info(f"After boolean filtering: {len(papers)} papers")

        return papers[:max_results]

    def _parse_xml(self, xml_text: str) -> List[Paper]:
        """Parse PubMed XML response into Paper objects."""
        papers: List[Paper] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return papers

        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue

            article_data = medline.find("Article")
            if article_data is None:
                continue

            # Title
            title_el = article_data.find(".//ArticleTitle")
            title = title_el.text if title_el is not None and title_el.text else None
            if not title:
                continue

            # Abstract
            abstract_parts = []
            for abstract_text in article_data.findall(".//AbstractText"):
                text = "".join(abstract_text.itertext())
                label = abstract_text.get("Label")
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = clean_abstract(" ".join(abstract_parts)) if abstract_parts else None

            # Authors
            authors = []
            author_list = article_data.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last = author.findtext("LastName", "")
                    fore = author.findtext("ForeName", "")
                    name = f"{fore} {last}".strip()
                    if name:
                        authors.append(name)

            # Year
            year = None
            pub_date = article_data.find(".//PubDate")
            if pub_date is not None:
                year_text = pub_date.findtext("Year")
                if year_text and year_text.isdigit():
                    year = int(year_text)

            # DOI
            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = normalize_doi(article_id.text)
                    break

            # Venue
            venue = None
            journal = article_data.find(".//Journal/Title")
            if journal is not None and journal.text:
                venue = journal.text

            # PMID as URL
            pmid = medline.findtext("PMID")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

            papers.append(
                Paper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    year=year,
                    venue=venue,
                    doi=doi,
                    url=url,
                    source="pubmed",
                )
            )

        return papers
