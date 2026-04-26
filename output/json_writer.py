"""JSON report writer for structured literature review output."""

import json
from typing import Any, Dict, List, Optional

from models.paper import Paper


def write_json_report(
    topic: str,
    synthesis: Dict[str, Any],
    papers: List[Paper],
    output_path: str,
    search_strategy: Optional[Dict[str, Any]] = None,
    coverage: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate a JSON literature review report.

    Args:
        topic: Research topic.
        synthesis: Global synthesis result.
        papers: List of all papers.
        output_path: Output file path.
        search_strategy: Search strategy details.
        coverage: Coverage report.
    """
    years = [p.year for p in papers if p.year]

    report = {
        "topic": topic,
        "search_strategy": search_strategy or {},
        "corpus": {
            "paper_count": len(papers),
            "year_range": [min(years), max(years)] if years else None,
            "sources": sorted(set(p.source or "Unknown" for p in papers)),
        },
        "review": synthesis,
        "coverage": coverage or {},
        "evidence_map": {
            paper.id: {
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "doi": paper.doi,
                "source": paper.source,
                "citation_count": paper.citation_count,
            }
            for paper in papers
            if paper.id
        },
        "references": [
            {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "doi": paper.doi,
                "url": paper.url,
                "source": paper.source,
            }
            for paper in papers
        ],
        "disclaimer": (
            "This review is based only on available titles and abstracts. "
            "Every claim is grounded in evidence citations. "
            "Unsupported claims are marked as insufficient_evidence."
        ),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
