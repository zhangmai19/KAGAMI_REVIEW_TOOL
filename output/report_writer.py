"""High-level report writer that orchestrates all output formats."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.paper import Paper
from output.markdown_writer import write_markdown_report
from output.json_writer import write_json_report
from output.ris_writer import write_ris_file
from utils.io import save_json, save_text, ensure_dir
from utils.logging import get_logger

logger = get_logger(__name__)


class ReportWriter:
    """Orchestrate generation of all output formats."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = ensure_dir(output_dir)

    def write_all(
        self,
        topic: str,
        synthesis: Dict[str, Any],
        papers: List[Paper],
        coverage: Optional[Dict[str, Any]] = None,
        search_strategy: Optional[Dict[str, Any]] = None,
        chunk_results: Optional[List[Dict[str, Any]]] = None,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """Generate all output files.

        Args:
            topic: Research topic.
            synthesis: Global synthesis result.
            papers: List of all papers.
            coverage: Coverage report.
            search_strategy: Search strategy details.
            chunk_results: Chunk-level results.
            formats: List of output formats to generate.

        Returns:
            Dictionary mapping format name to output file path.
        """
        formats = formats or ["markdown", "json"]
        output_files = {}

        # Always write intermediate files
        self._write_intermediate(papers, coverage, search_strategy, chunk_results)

        if "markdown" in formats:
            path = self.output_dir / "final_report.md"
            write_markdown_report(
                topic=topic,
                synthesis=synthesis,
                papers=papers,
                output_path=str(path),
                search_strategy=search_strategy,
                coverage=coverage,
            )
            output_files["markdown"] = path
            logger.info(f"Markdown report written to {path}")

        if "json" in formats:
            path = self.output_dir / "final_report.json"
            write_json_report(
                topic=topic,
                synthesis=synthesis,
                papers=papers,
                output_path=str(path),
                search_strategy=search_strategy,
                coverage=coverage,
            )
            output_files["json"] = path
            logger.info(f"JSON report written to {path}")

        if "ris" in formats:
            path = self.output_dir / "papers.ris"
            write_ris_file(papers, str(path))
            output_files["ris"] = path

        return output_files

    def _write_intermediate(
        self,
        papers: List[Paper],
        coverage: Optional[Dict[str, Any]],
        search_strategy: Optional[Dict[str, Any]],
        chunk_results: Optional[List[Dict[str, Any]]],
    ):
        """Write intermediate data files."""
        # Papers JSONL
        from utils.io import save_jsonl
        save_jsonl(papers, self.output_dir / "papers.jsonl")

        # Numbered text
        from parser.paper_normalizer import papers_to_numbered_text
        numbered_text = papers_to_numbered_text(papers)
        save_text(numbered_text, self.output_dir / "papers_numbered.txt")

        # Coverage report
        if coverage:
            save_json(coverage, self.output_dir / "coverage.json")

        # Search strategy
        if search_strategy:
            save_json(search_strategy, self.output_dir / "search_strategy.json")

        # Chunk results
        if chunk_results:
            for idx, result in enumerate(chunk_results, start=1):
                save_json(result, self.output_dir / f"chunk_{idx}.json")
