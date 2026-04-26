"""Main orchestrator for the automated literature review workflow."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from models.paper import Paper, CorpusSummary
from retriever.base import BaseRetriever
from retriever.openalex import OpenAlexRetriever
from retriever.semantic_scholar import SemanticScholarRetriever
from retriever.crossref import CrossrefRetriever
from query.keyword_expander import KeywordExpander
from query.boolean_builder import get_builder, BooleanQueryBuilder
from parser.ris_parser import parse_ris_file
from parser.bib_parser import parse_bib_file
from parser.csv_parser import parse_csv_file
from parser.paper_normalizer import assign_paper_ids, filter_papers_with_abstracts
from analyzer.chunker import chunk_papers
from analyzer.llm_client import LLMClient
from analyzer.chunk_analyzer import ChunkAnalyzer
from analyzer.synthesizer import Synthesizer
from analyzer.validator import validate_chunk_result, validate_synthesis
from analyzer.coverage_checker import check_coverage, get_missing_papers
from output.report_writer import ReportWriter
from utils.dedup import deduplicate_papers
from utils.io import save_json, ensure_dir
from utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


class LiteratureReviewAgent:
    """Orchestrates the complete automated literature review workflow.

    Supports two main modes:
    1. File-based: Upload RIS/BibTeX/CSV files for analysis.
    2. Search-based: Query academic databases automatically.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        output_dir: str = "data/output",
        max_tokens_per_chunk: int = 12000,
        max_papers_per_chunk: int = 25,
        dedup_threshold: float = 0.95,
    ):
        self.model = model
        self.output_dir = output_dir
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.max_papers_per_chunk = max_papers_per_chunk
        self.dedup_threshold = dedup_threshold

        self.llm_client = LLMClient(model=model)
        self.keyword_expander = KeywordExpander(self.llm_client)
        self.chunk_analyzer = ChunkAnalyzer(self.llm_client)
        self.synthesizer = Synthesizer(self.llm_client)
        self.report_writer = ReportWriter(output_dir)

    def review_from_file(
        self,
        topic: str,
        file_path: str,
        file_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a literature review from an uploaded file.

        Args:
            topic: Research topic.
            file_path: Path to RIS/BibTeX/CSV file.
            file_format: File format override (auto-detected if None).

        Returns:
            Complete review result dictionary.
        """
        console.print("[bold blue]Starting literature review from file...[/bold blue]")

        # Step 1: Parse file
        console.print("[bold]Step 1:[/bold] Parsing file...")
        papers = self._parse_file(file_path, file_format)
        console.print(f"  Parsed {len(papers)} papers")

        # Step 2: Process papers
        console.print("[bold]Step 2:[/bold] Processing papers...")
        result = self._process_papers(topic, papers)

        console.print("[bold green]Literature review complete![/bold green]")
        return result

    def review_from_search(
        self,
        topic: str,
        keywords: List[str],
        databases: Optional[List[str]] = None,
        max_papers: int = 150,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a literature review by searching academic databases.

        Args:
            topic: Research topic.
            keywords: Seed keywords.
            databases: List of databases to search.
            max_papers: Maximum papers to retrieve.
            from_year: Start year filter.
            to_year: End year filter.

        Returns:
            Complete review result dictionary.
        """
        console.print("[bold blue]Starting literature review from search...[/bold blue]")
        databases = databases or ["openalex", "semantic_scholar"]

        # Step 1: Expand keywords
        console.print("[bold]Step 1:[/bold] Expanding keywords...")
        expanded = self.keyword_expander.expand(topic, keywords)

        search_strategy = {
            "expanded_keywords": expanded,
            "boolean_queries": {},
        }

        # Step 2: Generate boolean queries
        console.print("[bold]Step 2:[/bold] Generating boolean queries...")
        for db in databases:
            try:
                builder = get_builder(db)
                query = builder.build(expanded)
                search_strategy["boolean_queries"][builder.database_name] = query
            except ValueError as e:
                logger.warning(f"Skipping unknown database: {db} ({e})")

        # Step 3: Search databases
        console.print("[bold]Step 3:[/bold] Searching databases...")
        all_papers = self._search_databases(
            topic, keywords, databases, max_papers, from_year, to_year
        )

        # Step 4: Process papers
        console.print("[bold]Step 4:[/bold] Processing papers...")
        result = self._process_papers(
            topic, all_papers, search_strategy=search_strategy
        )

        console.print("[bold green]Literature review complete![/bold green]")
        return result

    def _parse_file(self, file_path: str, file_format: Optional[str] = None) -> List[Paper]:
        """Parse a file into Paper objects."""
        path = Path(file_path)

        if file_format is None:
            ext = path.suffix.lower()
            format_map = {
                ".ris": "ris",
                ".bib": "bibtex",
                ".csv": "csv",
                ".json": "json",
                ".jsonl": "jsonl",
            }
            file_format = format_map.get(ext)
            if file_format is None:
                raise ValueError(f"Unsupported file format: {ext}")

        if file_format == "ris":
            return parse_ris_file(path)
        elif file_format == "bibtex":
            return parse_bib_file(path)
        elif file_format == "csv":
            return parse_csv_file(path)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    def _search_databases(
        self,
        topic: str,
        keywords: List[str],
        databases: List[str],
        max_papers: int,
        from_year: Optional[int],
        to_year: Optional[int],
    ) -> List[Paper]:
        """Search multiple academic databases."""
        retrievers: List[BaseRetriever] = []

        for db in databases:
            db_lower = db.lower()
            if db_lower == "openalex":
                retrievers.append(OpenAlexRetriever())
            elif db_lower == "semantic_scholar":
                retrievers.append(SemanticScholarRetriever())
            elif db_lower == "crossref":
                retrievers.append(CrossrefRetriever())
            else:
                logger.warning(f"Unknown database: {db}")

        all_papers: List[Paper] = []

        for retriever in retrievers:
            try:
                query = " ".join(keywords)
                papers = retriever.search(
                    query=query,
                    max_results=max_papers,
                    from_year=from_year,
                    to_year=to_year,
                )
                all_papers.extend(papers)
                console.print(f"  {retriever.name}: {len(papers)} papers")
            except Exception as e:
                logger.error(f"Failed to search {retriever.name}: {e}")
                console.print(f"  [red]{retriever.name}: Failed - {e}[/red]")

        return all_papers

    def _process_papers(
        self,
        topic: str,
        papers: List[Paper],
        search_strategy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Core processing pipeline for papers.

        Steps:
        1. Deduplicate
        2. Filter papers without abstracts
        3. Assign IDs
        4. Chunk
        5. Analyze chunks
        6. Check coverage
        7. Synthesize
        8. Validate
        9. Generate reports
        """
        # Deduplicate
        console.print("  Deduplicating...")
        original_count = len(papers)
        papers = deduplicate_papers(papers, self.dedup_threshold)
        duplicates_removed = original_count - len(papers)

        # Filter papers without abstracts
        with_abstract, without_abstract = filter_papers_with_abstracts(papers)
        console.print(
            f"  Papers with abstracts: {len(with_abstract)}, "
            f"without: {len(without_abstract)}"
        )

        # Assign IDs
        papers = assign_paper_ids(with_abstract)

        # Corpus summary
        years = [p.year for p in papers if p.year]
        corpus_summary = CorpusSummary(
            total=original_count,
            with_abstract=len(with_abstract),
            without_abstract=len(without_abstract),
            duplicates_removed=duplicates_removed,
            year_range=[min(years), max(years)] if years else None,
            sources=sorted(set(p.source or "Unknown" for p in papers)),
        )

        # Chunk papers
        console.print("  Chunking papers...")
        chunks = chunk_papers(
            papers,
            max_tokens=self.max_tokens_per_chunk,
            max_papers_per_chunk=self.max_papers_per_chunk,
            model=self.model,
        )
        console.print(f"  Created {len(chunks)} chunks")

        # Analyze chunks
        console.print("  Analyzing chunks...")
        chunk_results: List[Dict[str, Any]] = []
        valid_paper_ids = {p.id for p in papers if p.id}

        for idx, chunk in enumerate(chunks, start=1):
            console.print(f"  Analyzing chunk {idx}/{len(chunks)}...")
            result = self.chunk_analyzer.analyze_chunk(idx, chunk)
            chunk_results.append(result)

            # Validate chunk result
            validation = validate_chunk_result(result, valid_paper_ids)
            if not validation["valid"]:
                logger.warning(
                    f"Chunk {idx} validation issues: "
                    f"invalid_ids={validation['invalid_ids']}, "
                    f"claims_without_evidence={len(validation['claims_without_evidence'])}"
                )

        # Check coverage
        console.print("  Checking coverage...")
        coverage = check_coverage(papers, chunk_results)
        console.print(
            f"  Coverage: {coverage['coverage_ratio']:.1%} "
            f"({coverage['used_count']}/{coverage['total_papers']})"
        )

        # Re-analyze missing papers if any
        if coverage["missing_ids"]:
            console.print(
                f"  Re-analyzing {len(coverage['missing_ids'])} missing papers..."
            )
            missing_papers = get_missing_papers(papers, coverage)
            if missing_papers:
                # Create a single chunk for missing papers
                missing_result = self.chunk_analyzer.analyze_chunk(
                    chunk_id=len(chunks) + 1,
                    papers=missing_papers,
                )
                chunk_results.append(missing_result)

                # Re-check coverage
                coverage = check_coverage(papers, chunk_results)
                console.print(
                    f"  Updated coverage: {coverage['coverage_ratio']:.1%}"
                )

        # Synthesize
        console.print("  Synthesizing global review...")
        try:
            synthesis = self.synthesizer.synthesize(chunk_results)
        except Exception as e:
            logger.error(f"Global synthesis failed: {e}")
            console.print(f"  [red]Synthesis failed: {e}[/red]")
            console.print("  [yellow]Falling back to direct chunk result merge...[/yellow]")
            synthesis = self._fallback_synthesis(chunk_results, valid_paper_ids)

        # Validate synthesis
        validation = validate_synthesis(synthesis, valid_paper_ids)
        if not validation["valid"]:
            logger.warning(
                f"Synthesis validation issues: "
                f"invalid_ids={validation['invalid_ids']}, "
                f"claims_without_evidence={len(validation['claims_without_evidence'])}"
            )

        # Generate reports
        console.print("  Generating reports...")
        output_files = self.report_writer.write_all(
            topic=topic,
            synthesis=synthesis,
            papers=papers,
            coverage=coverage,
            search_strategy=search_strategy,
            chunk_results=chunk_results,
        )

        return {
            "topic": topic,
            "corpus_summary": corpus_summary.model_dump(),
            "coverage": coverage,
            "synthesis": synthesis,
            "validation": validation,
            "output_files": {k: str(v) for k, v in output_files.items()},
            "chunk_count": len(chunks),
        }

    def _fallback_synthesis(
        self,
        chunk_results: List[Dict[str, Any]],
        valid_paper_ids: set,
    ) -> Dict[str, Any]:
        """Create a fallback synthesis by merging chunk results without LLM.

        Used when the global synthesis LLM call fails.
        Simply concatenates results from all chunks.
        """
        from analyzer.coverage_checker import collect_evidence_ids

        all_evidence = set()
        for cr in chunk_results:
            all_evidence.update(collect_evidence_ids(cr))

        def _merge_field(field_name: str) -> List[Dict[str, Any]]:
            items = []
            for cr in chunk_results:
                for item in cr.get(field_name, []):
                    if isinstance(item, dict):
                        items.append(item)
            return items

        return {
            "global_topic_clusters": _merge_field("topic_clusters"),
            "global_research_questions": _merge_field("research_questions"),
            "global_method_categories": _merge_field("method_categories"),
            "global_theoretical_frameworks": _merge_field("theoretical_frameworks"),
            "global_data_types": _merge_field("data_types"),
            "global_key_findings": _merge_field("key_findings"),
            "global_research_gaps": _merge_field("research_gaps"),
            "global_limitations": _merge_field("limitations"),
            "coverage_check": {
                "all_evidence_ids_used": sorted(all_evidence & valid_paper_ids),
                "possibly_underused_ids": [],
            },
            "_fallback": True,
            "_note": "Global LLM synthesis failed; results are merged chunk-level analyses without cross-chunk synthesis.",
        }
