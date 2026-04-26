"""Markdown report writer for literature review output."""

from typing import Any, Dict, List, Optional

from models.paper import Paper


def _render_evidence_items(
    items: List[Dict[str, Any]],
    title_key: str = "cluster_name",
    text_key: str = "synthesis",
) -> str:
    """Render a list of evidence-backed items as Markdown."""
    if not items:
        return "_insufficient_evidence_\n"

    lines = []

    for i, item in enumerate(items, start=1):
        if isinstance(item, str):
            lines.append(f"{i}. {item}")
            continue

        title = item.get(title_key) or item.get("finding") or item.get("limitation") or item.get("gap")
        text = item.get(text_key) or item.get("description") or ""
        evidence = item.get("evidence_ids", [])

        if title:
            lines.append(f"### {i}. {title}")

        if text:
            lines.append(f"\n{text}")

        if evidence:
            lines.append(f"\nEvidence: {', '.join(evidence)}")

        lines.append("")

    return "\n".join(lines)


def write_markdown_report(
    topic: str,
    synthesis: Dict[str, Any],
    papers: List[Paper],
    output_path: str,
    search_strategy: Optional[Dict[str, Any]] = None,
    coverage: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate a Markdown literature review report.

    Args:
        topic: Research topic.
        synthesis: Global synthesis result.
        papers: List of all papers.
        output_path: Output file path.
        search_strategy: Search strategy details.
        coverage: Coverage report.
    """
    # Build references section
    references = []
    for paper in papers:
        authors = ", ".join(paper.authors[:5]) if paper.authors else "Unknown"
        if len(paper.authors) > 5:
            authors += " et al."
        references.append(
            f"- **{paper.id}**: {authors} ({paper.year or 'Unknown'}). "
            f"{paper.title}. *{paper.venue or 'N/A'}*. "
            f"DOI: {paper.doi or 'N/A'}"
        )

    # Build evidence map
    evidence_map_lines = []
    for paper in papers:
        evidence_map_lines.append(
            f"| {paper.id} | {paper.title[:80]} | {paper.source or 'N/A'} | "
            f"{paper.year or 'N/A'} | {paper.doi or 'N/A'} |"
        )

    # Build search strategy section
    search_section = ""
    if search_strategy:
        expanded = search_strategy.get("expanded_keywords", {})
        boolean_queries = search_strategy.get("boolean_queries", {})

        search_section = "## 2. Search Strategy\n\n"

        if expanded:
            search_section += "### Expanded Keywords\n\n"
            for concept in expanded.get("concepts", []):
                search_section += f"- **{concept.get('concept', '')}**: "
                synonyms = concept.get("synonyms", [])
                variants = concept.get("variants", [])
                search_section += ", ".join(synonyms + variants) + "\n"
            search_section += "\n"

        if boolean_queries:
            search_section += "### Boolean Queries\n\n"
            for db, query in boolean_queries.items():
                search_section += f"**{db}**:\n```\n{query}\n```\n\n"

    # Build coverage section
    coverage_section = ""
    if coverage:
        coverage_section = (
            f"## 11. Coverage Report\n\n"
            f"- Total papers: {coverage.get('total_papers', 0)}\n"
            f"- Papers cited in analysis: {coverage.get('used_count', 0)}\n"
            f"- Coverage ratio: {coverage.get('coverage_ratio', 0):.1%}\n"
        )
        missing = coverage.get("missing_ids", [])
        if missing:
            coverage_section += f"- Missing papers: {', '.join(missing)}\n"

    md = f"""# Automated Literature Review Report

> **Disclaimer**: This review is based only on available titles and abstracts.
> Every claim is grounded in evidence citations (e.g., #1, #2).
> Unsupported claims are marked as _insufficient_evidence_.

## 1. Topic

{topic}

{search_section}
## {3 if search_strategy else 2}. Corpus Description

- **Total papers analyzed**: {len(papers)}
- **Year range**: {min((p.year for p in papers if p.year), default='N/A')} – {max((p.year for p in papers if p.year), default='N/A')}
- **Sources**: {', '.join(sorted(set(p.source or 'Unknown' for p in papers)))}

## {4 if search_strategy else 3}. Topic Clusters

{_render_evidence_items(
    synthesis.get("global_topic_clusters", []),
    title_key="cluster_name",
    text_key="synthesis"
)}

## {5 if search_strategy else 4}. Research Questions

{_render_evidence_items(
    synthesis.get("global_research_questions", []),
    title_key="question",
    text_key="synthesis"
)}

## {6 if search_strategy else 5}. Method Categories

{_render_evidence_items(
    synthesis.get("global_method_categories", []),
    title_key="method_type",
    text_key="synthesis"
)}

## {7 if search_strategy else 6}. Theoretical Frameworks

{_render_evidence_items(
    synthesis.get("global_theoretical_frameworks", []),
    title_key="framework",
    text_key="synthesis"
)}

## {8 if search_strategy else 7}. Data Types

{_render_evidence_items(
    synthesis.get("global_data_types", []),
    title_key="data_type",
    text_key="synthesis"
)}

## {9 if search_strategy else 8}. Key Findings

{_render_evidence_items(
    synthesis.get("global_key_findings", []),
    title_key="finding",
    text_key="description"
)}

## {10 if search_strategy else 9}. Research Gaps

{_render_evidence_items(
    synthesis.get("global_research_gaps", []),
    title_key="gap",
    text_key="synthesis"
)}

## {11 if search_strategy else 10}. Limitations

{_render_evidence_items(
    synthesis.get("global_limitations", []),
    title_key="limitation",
    text_key="description"
)}

{coverage_section}
## {12 if search_strategy else (11 if coverage else 10)}. Evidence Map

| ID | Title | Source | Year | DOI |
|---|---|---|---|---|
{chr(10).join(evidence_map_lines)}

## References

{chr(10).join(references)}

---

*Generated by AutoLitReview-Agent. This report is based strictly on available titles and abstracts.*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
