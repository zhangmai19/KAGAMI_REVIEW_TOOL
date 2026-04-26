"""Tests for deduplication utility."""

from models.paper import Paper
from utils.dedup import deduplicate_papers, normalize_title


class TestNormalizeTitle:
    """Tests for title normalization."""

    def test_lowercase(self):
        assert normalize_title("Test Title") == "test title"

    def test_remove_punctuation(self):
        assert normalize_title("Test: A Title!") == "test a title"

    def test_normalize_whitespace(self):
        assert normalize_title("Test   Title") == "test title"

    def test_empty_string(self):
        assert normalize_title("") == ""


class TestDeduplicatePapers:
    """Tests for paper deduplication."""

    def test_dedup_by_doi(self):
        papers = [
            Paper(title="Paper A", doi="10.1234/a"),
            Paper(title="Paper B", doi="10.1234/a"),  # Same DOI
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1

    def test_dedup_by_title_similarity(self):
        papers = [
            Paper(title="A systematic review of AI agents"),
            Paper(title="A systematic review of AI agents."),  # Almost identical
        ]
        result = deduplicate_papers(papers, title_similarity_threshold=0.95)
        assert len(result) == 1

    def test_different_papers(self):
        papers = [
            Paper(title="Paper about machine learning"),
            Paper(title="Paper about deep learning"),
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 2

    def test_doi_case_insensitive(self):
        papers = [
            Paper(title="Paper A", doi="10.1234/ABC"),
            Paper(title="Paper B", doi="10.1234/abc"),
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1

    def test_no_doi_dedup_by_title(self):
        papers = [
            Paper(title="Same Title Paper"),
            Paper(title="Same Title Paper"),
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1

    def test_empty_list(self):
        result = deduplicate_papers([])
        assert len(result) == 0
