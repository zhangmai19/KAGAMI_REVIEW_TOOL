"""Validation of analysis results against evidence constraints."""

import re
from typing import Any, Dict, List, Optional, Set

from models.paper import Paper
from utils.logging import get_logger

logger = get_logger(__name__)


def _collect_all_ids(obj: Any) -> Set[str]:
    """Recursively collect all evidence_ids from a nested structure."""
    ids = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "evidence_ids" and isinstance(value, list):
                ids.update(str(v) for v in value)
            elif key == "papers_covered" and isinstance(value, list):
                ids.update(str(v) for v in value)
            else:
                ids.update(_collect_all_ids(value))
    elif isinstance(obj, list):
        for item in obj:
            ids.update(_collect_all_ids(item))

    return ids


def _find_claims_without_evidence(obj: Any, path: str = "") -> List[Dict[str, str]]:
    """Find claims that lack evidence_ids."""
    issues = []

    if isinstance(obj, dict):
        # Check if this dict looks like a claim (has description/finding/gap/etc. but no evidence_ids)
        claim_keys = {"description", "finding", "gap", "limitation", "question", "synthesis"}
        has_claim_content = bool(claim_keys & set(obj.keys()))

        if has_claim_content and "evidence_ids" not in obj:
            claim_text = ""
            for k in claim_keys:
                if k in obj and obj[k]:
                    claim_text = str(obj[k])[:100]
                    break
            issues.append({
                "path": path,
                "issue": "missing_evidence_ids",
                "claim_preview": claim_text,
            })
        elif has_claim_content and "evidence_ids" in obj:
            if not obj["evidence_ids"]:
                claim_text = ""
                for k in claim_keys:
                    if k in obj and obj[k]:
                        claim_text = str(obj[k])[:100]
                        break
                issues.append({
                    "path": path,
                    "issue": "empty_evidence_ids",
                    "claim_preview": claim_text,
                })

        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            issues.extend(_find_claims_without_evidence(value, child_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            issues.extend(_find_claims_without_evidence(item, f"{path}[{i}]"))

    return issues


def validate_chunk_result(
    result: Dict[str, Any],
    valid_paper_ids: Set[str],
) -> Dict[str, Any]:
    """Validate a chunk analysis result.

    Checks:
    1. All evidence_ids reference valid paper IDs
    2. All claims have evidence_ids
    3. papers_covered matches actual paper IDs
    4. No invalid (nonexistent) IDs are cited

    Args:
        result: Chunk analysis result.
        valid_paper_ids: Set of valid paper IDs in this chunk.

    Returns:
        Validation report dictionary.
    """
    used_ids = _collect_all_ids(result)
    invalid_ids = used_ids - valid_paper_ids
    missing_from_coverage = valid_paper_ids - used_ids

    claims_without_evidence = _find_claims_without_evidence(result)

    return {
        "valid": len(invalid_ids) == 0 and len(claims_without_evidence) == 0,
        "invalid_ids": sorted(invalid_ids),
        "missing_from_coverage": sorted(
            missing_from_coverage,
            key=lambda x: int(x.replace("#", "")) if x.startswith("#") else 0,
        ),
        "claims_without_evidence": claims_without_evidence,
        "total_valid_ids": len(used_ids & valid_paper_ids),
        "total_invalid_ids": len(invalid_ids),
    }


def validate_synthesis(
    synthesis: Dict[str, Any],
    valid_paper_ids: Set[str],
) -> Dict[str, Any]:
    """Validate a global synthesis result.

    Checks:
    1. All evidence_ids reference valid paper IDs
    2. All claims have evidence_ids
    3. No fabricated IDs

    Args:
        synthesis: Global synthesis result.
        valid_paper_ids: Set of all valid paper IDs.

    Returns:
        Validation report dictionary.
    """
    used_ids = _collect_all_ids(synthesis)
    invalid_ids = used_ids - valid_paper_ids

    claims_without_evidence = _find_claims_without_evidence(synthesis)

    coverage = synthesis.get("coverage_check", {})
    claimed_used = set(coverage.get("all_evidence_ids_used", []))

    return {
        "valid": len(invalid_ids) == 0 and len(claims_without_evidence) == 0,
        "invalid_ids": sorted(invalid_ids),
        "claims_without_evidence": claims_without_evidence,
        "total_evidence_ids": len(used_ids),
        "total_invalid_ids": len(invalid_ids),
        "coverage_ids_match": claimed_used == (used_ids & valid_paper_ids),
    }
