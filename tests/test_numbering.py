"""Tests for paper numbering and normalization."""

from models.paper import Paper
from parser.paper_normalizer import (
    assign_paper_ids,
    papers_to_numbered_text,
    filter_papers_with_abstracts,
)


class TestAssignPaperIds:
    """Tests for paper ID assignment."""

    def test_default_prefix(self):
        papers = [
            Paper(title="Paper A"),
            Paper(title="Paper B"),
            Paper(title="Paper C"),
        ]
        result = assign_paper_ids(papers)
        assert result[0].id == "#1"
        assert result[1].id == "#2"
        assert result[2].id == "#3"

    def test_custom_prefix(self):
        papers = [Paper(title="Paper A"), Paper(title="Paper B")]
        result = assign_paper_ids(papers, prefix="P")
        assert result[0].id == "P1"
        assert result[1].id == "P2"

    def test_empty_list(self):
        result = assign_paper_ids([])
        assert result == []

    def test_modifies_in_place(self):
        papers = [Paper(title="Paper A")]
        result = assign_paper_ids(papers)
        assert result is papers  # Same object reference
        assert papers[0].id == "#1"


class TestPapersToNumberedText:
    """Tests for converting papers to numbered text format."""

    def test_basic_format(self):
        papers = [
            Paper(
                id="#1",
                title="Test Paper",
                authors=["Author A"],
                year=2023,
                venue="Test Journal",
                doi="10.1234/test",
                abstract="Test abstract.",
            )
        ]
        text = papers_to_numbered_text(papers)
        assert "[#1]" in text
        assert "Title: Test Paper" in text
        assert "Authors: Author A" in text
        assert "Year: 2023" in text
        assert "Abstract: Test abstract." in text

    def test_unknown_fields(self):
        papers = [Paper(id="#1", title="No Info Paper")]
        text = papers_to_numbered_text(papers)
        assert "Authors: Unknown" in text
        assert "Year: Unknown" in text
        assert "Abstract: No abstract available." in text

    def test_multiple_papers(self):
        papers = [
            Paper(id="#1", title="Paper 1"),
            Paper(id="#2", title="Paper 2"),
        ]
        text = papers_to_numbered_text(papers)
        assert "[#1]" in text
        assert "[#2]" in text


class TestFilterPapersWithAbstracts:
    """Tests for filtering papers by abstract availability."""

    def test_filter_with_abstracts(self):
        papers = [
            Paper(title="Has Abstract", abstract="Some abstract."),
            Paper(title="No Abstract", abstract=None),
            Paper(title="Empty Abstract", abstract=""),
            Paper(title="Whitespace Abstract", abstract="   "),
        ]
        with_abs, without_abs = filter_papers_with_abstracts(papers)
        assert len(with_abs) == 1
        assert len(without_abs) == 3
        assert with_abs[0].title == "Has Abstract"

    def test_all_have_abstracts(self):
        papers = [
            Paper(title="A", abstract="Abstract A"),
            Paper(title="B", abstract="Abstract B"),
        ]
        with_abs, without_abs = filter_papers_with_abstracts(papers)
        assert len(with_abs) == 2
        assert len(without_abs) == 0

    def test_none_have_abstracts(self):
        papers = [
            Paper(title="A", abstract=None),
            Paper(title="B", abstract=None),
        ]
        with_abs, without_abs = filter_papers_with_abstracts(papers)
        assert len(with_abs) == 0
        assert len(without_abs) == 2
