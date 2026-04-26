"""Coverage checking for evidence-based literature review."""

from typing import Any, Dict, List, Set

from models.paper import Paper
from utils.logging import get_logger

logger = get_logger(__name__)


def collect_evidence_ids(obj: Any) -> Set[str]:
    """Recursively collect all evidence IDs from a nested structure.

    Searches for 'evidence_ids' and 'papers_covered' keys.
    """
    ids = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "evidence_ids" and isinstance(value, list):
                ids.update(str(v) for v in value)
            elif key == "papers_covered" and isinstance(value, list):
                ids.update(str(v) for v in value)
            else:
                ids.update(collect_evidence_ids(value))
    elif isinstance(obj, list):
        for item in obj:
            ids.update(collect_evidence_ids(item))

    return ids


def check_coverage(
    papers: List[Paper],
    chunk_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Check evidence coverage across the corpus.

    Identifies papers that were not cited in any chunk analysis,
    as well as any invalid (nonexistent) paper IDs referenced.

    Args:
        papers: Full list of papers.
        chunk_results: List of chunk-level analysis results.

    Returns:
        Coverage report dictionary.
    """
    all_ids = {paper.id for paper in papers if paper.id}
    used_ids = set()

    for result in chunk_results:
        used_ids.update(collect_evidence_ids(result))

    missing_ids = all_ids - used_ids
    invalid_ids = used_ids - all_ids

    report = {
        "total_papers": len(all_ids),
        "used_count": len(used_ids & all_ids),
        "missing_ids": sorted(
            missing_ids,
            key=lambda x: int(x.replace("#", "")) if x.startswith("#") else 0,
        ),
        "invalid_ids": sorted(invalid_ids),
        "coverage_ratio": len(used_ids & all_ids) / len(all_ids) if all_ids else 0,
    }

    if missing_ids:
        logger.warning(
            f"Coverage check: {len(missing_ids)} papers not cited in analysis: "
            f"{', '.join(sorted(missing_ids)[:10])}..."
        )

    if invalid_ids:
        logger.warning(
            f"Coverage check: {len(invalid_ids)} invalid IDs referenced: "
            f"{', '.join(sorted(invalid_ids)[:10])}..."
        )

    return report


def get_missing_papers(
    papers: List[Paper],
    coverage_report: Dict[str, Any],
) -> List[Paper]:
    """Get Paper objects for papers missing from analysis.

    Args:
        papers: Full list of papers.
        coverage_report: Output from check_coverage().

    Returns:
        List of Paper objects that were not covered.
    """
    missing_ids = set(coverage_report.get("missing_ids", []))
    return [p for p in papers if p.id in missing_ids]
