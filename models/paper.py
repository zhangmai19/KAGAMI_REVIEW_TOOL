from typing import List, Optional

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """Unified paper record for the literature review pipeline."""

    id: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    citation_count: Optional[int] = None


class SearchInput(BaseModel):
    """User input for literature search."""

    topic: str
    keywords: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=lambda: ["openalex", "semantic_scholar"])
    max_papers: int = 150
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    language: str = "en"


class CorpusSummary(BaseModel):
    """Summary statistics of the paper corpus."""

    total: int = 0
    with_abstract: int = 0
    without_abstract: int = 0
    duplicates_removed: int = 0
    year_range: Optional[List[int]] = None
    sources: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """A single evidence-backed claim."""

    claim: str
    description: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class ChunkResult(BaseModel):
    """Result from analyzing a single chunk of papers."""

    chunk_id: int
    papers_covered: List[str] = Field(default_factory=list)
    topic_clusters: List[EvidenceItem] = Field(default_factory=list)
    research_questions: List[EvidenceItem] = Field(default_factory=list)
    method_categories: List[EvidenceItem] = Field(default_factory=list)
    theoretical_frameworks: List[EvidenceItem] = Field(default_factory=list)
    data_types: List[EvidenceItem] = Field(default_factory=list)
    key_findings: List[EvidenceItem] = Field(default_factory=list)
    research_gaps: List[EvidenceItem] = Field(default_factory=list)
    limitations: List[EvidenceItem] = Field(default_factory=list)
    uncertain_or_missing: List[EvidenceItem] = Field(default_factory=list)


class CoverageReport(BaseModel):
    """Report on evidence coverage across the corpus."""

    total_papers: int = 0
    used_count: int = 0
    missing_ids: List[str] = Field(default_factory=list)
    invalid_ids: List[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0
