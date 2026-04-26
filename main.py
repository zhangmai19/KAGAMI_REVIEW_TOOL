"""AutoLitReview-Agent: CLI entry point.

An open-source agent for citation-grounded, abstract-based academic literature review.
"""

from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from agents.literature_review_agent import LiteratureReviewAgent

app = typer.Typer(
    name="autolitreview",
    help="Automated literature review agent with evidence-grounded analysis.",
)
console = Console()


@app.command()
def review_from_ris(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic"),
    ris_path: str = typer.Option(..., "--ris-path", "-r", help="Path to RIS file"),
    output_dir: str = typer.Option("data/output", "--output", "-o", help="Output directory"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="LLM model name"),
    max_tokens: int = typer.Option(12000, "--max-tokens", help="Max tokens per chunk"),
    max_papers: int = typer.Option(25, "--max-papers", help="Max papers per chunk"),
):
    """Run a literature review from an RIS file."""
    load_dotenv()

    agent = LiteratureReviewAgent(
        model=model,
        output_dir=output_dir,
        max_tokens_per_chunk=max_tokens,
        max_papers_per_chunk=max_papers,
    )

    result = agent.review_from_file(topic=topic, file_path=ris_path)

    _print_result(result)


@app.command()
def review_from_bib(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic"),
    bib_path: str = typer.Option(..., "--bib-path", "-b", help="Path to BibTeX file"),
    output_dir: str = typer.Option("data/output", "--output", "-o", help="Output directory"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="LLM model name"),
    max_tokens: int = typer.Option(12000, "--max-tokens", help="Max tokens per chunk"),
    max_papers: int = typer.Option(25, "--max-papers", help="Max papers per chunk"),
):
    """Run a literature review from a BibTeX file."""
    load_dotenv()

    agent = LiteratureReviewAgent(
        model=model,
        output_dir=output_dir,
        max_tokens_per_chunk=max_tokens,
        max_papers_per_chunk=max_papers,
    )

    result = agent.review_from_file(topic=topic, file_path=bib_path, file_format="bibtex")

    _print_result(result)


@app.command()
def review_from_csv(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic"),
    csv_path: str = typer.Option(..., "--csv-path", "-c", help="Path to CSV file"),
    output_dir: str = typer.Option("data/output", "--output", "-o", help="Output directory"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="LLM model name"),
    max_tokens: int = typer.Option(12000, "--max-tokens", help="Max tokens per chunk"),
    max_papers: int = typer.Option(25, "--max-papers", help="Max papers per chunk"),
):
    """Run a literature review from a CSV file."""
    load_dotenv()

    agent = LiteratureReviewAgent(
        model=model,
        output_dir=output_dir,
        max_tokens_per_chunk=max_tokens,
        max_papers_per_chunk=max_papers,
    )

    result = agent.review_from_file(topic=topic, file_path=csv_path, file_format="csv")

    _print_result(result)


@app.command()
def review_from_search(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic"),
    keywords: Optional[list[str]] = typer.Option(None, "--keyword", "-k", help="Search keywords (can specify multiple)"),
    databases: Optional[list[str]] = typer.Option(None, "--database", "-d", help="Databases to search"),
    max_papers: int = typer.Option(150, "--max-papers", help="Maximum papers to retrieve"),
    from_year: Optional[int] = typer.Option(None, "--from-year", help="Start year filter"),
    to_year: Optional[int] = typer.Option(None, "--to-year", help="End year filter"),
    output_dir: str = typer.Option("data/output", "--output", "-o", help="Output directory"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="LLM model name"),
    max_tokens: int = typer.Option(12000, "--max-tokens", help="Max tokens per chunk"),
    max_papers_per_chunk: int = typer.Option(25, "--max-papers", help="Max papers per chunk"),
):
    """Run a literature review by searching academic databases."""
    load_dotenv()

    if not keywords:
        keywords = [topic]

    agent = LiteratureReviewAgent(
        model=model,
        output_dir=output_dir,
        max_tokens_per_chunk=max_tokens,
        max_papers_per_chunk=max_papers_per_chunk,
    )

    result = agent.review_from_search(
        topic=topic,
        keywords=keywords,
        databases=databases or ["openalex", "semantic_scholar"],
        max_papers=max_papers,
        from_year=from_year,
        to_year=to_year,
    )

    _print_result(result)


def _print_result(result: dict):
    """Print a summary of the review result."""
    console.print()
    console.print("[bold green]Review Complete![/bold green]")
    console.print(f"  Topic: {result.get('topic', 'N/A')}")

    corpus = result.get("corpus_summary", {})
    console.print(f"  Papers analyzed: {corpus.get('with_abstract', 0)}")
    console.print(f"  Duplicates removed: {corpus.get('duplicates_removed', 0)}")

    coverage = result.get("coverage", {})
    console.print(f"  Coverage: {coverage.get('coverage_ratio', 0):.1%}")

    output_files = result.get("output_files", {})
    if output_files:
        console.print("\n[bold]Output files:[/bold]")
        for fmt, path in output_files.items():
            console.print(f"  {fmt}: {path}")


if __name__ == "__main__":
    app()
