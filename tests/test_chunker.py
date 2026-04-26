"""Tests for paper chunking."""

from models.paper import Paper
from analyzer.chunker import chunk_papers


class TestChunkPapers:
    """Tests for the paper chunking function."""

    def _make_papers(self, count: int) -> list[Paper]:
        """Create test papers with abstracts."""
        return [
            Paper(
                id=f"#{i}",
                title=f"Test Paper {i}",
                abstract=f"This is the abstract for test paper number {i}. " * 10,
                authors=["Author"],
                year=2023,
            )
            for i in range(1, count + 1)
        ]

    def test_single_chunk(self):
        papers = self._make_papers(5)
        chunks = chunk_papers(papers, max_tokens=50000, max_papers_per_chunk=25)
        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_multiple_chunks_by_paper_count(self):
        papers = self._make_papers(30)
        chunks = chunk_papers(papers, max_tokens=50000, max_papers_per_chunk=10)
        assert len(chunks) == 3
        assert all(len(chunk) == 10 for chunk in chunks)

    def test_multiple_chunks_by_token_limit(self):
        papers = self._make_papers(10)
        chunks = chunk_papers(papers, max_tokens=200, max_papers_per_chunk=25)
        assert len(chunks) > 1

    def test_empty_input(self):
        chunks = chunk_papers([], max_tokens=12000, max_papers_per_chunk=25)
        assert len(chunks) == 0

    def test_single_paper(self):
        papers = self._make_papers(1)
        chunks = chunk_papers(papers, max_tokens=12000, max_papers_per_chunk=25)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1

    def test_all_papers_in_chunks(self):
        papers = self._make_papers(25)
        chunks = chunk_papers(papers, max_tokens=200, max_papers_per_chunk=5)
        total_papers = sum(len(chunk) for chunk in chunks)
        assert total_papers == 25
