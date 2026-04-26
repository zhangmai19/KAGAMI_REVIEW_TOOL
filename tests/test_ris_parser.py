"""Tests for RIS file parser."""

import tempfile
from pathlib import Path

import pytest

from parser.ris_parser import parse_ris_file, _safe_year
from models.paper import Paper


class TestSafeYear:
    """Tests for _safe_year utility function."""

    def test_integer_year(self):
        assert _safe_year(2023) == 2023

    def test_string_year(self):
        assert _safe_year("2023") == 2023

    def test_date_string(self):
        assert _safe_year("2023-05-15") == 2023

    def test_none(self):
        assert _safe_year(None) is None

    def test_empty_string(self):
        assert _safe_year("") is None

    def test_invalid_string(self):
        assert _safe_year("abc") is None


class TestRISParser:
    """Tests for RIS file parsing."""

    def _create_ris_file(self, content: str) -> str:
        """Create a temporary RIS file and return its path."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ris", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            return f.name

    def test_parse_basic_ris(self):
        ris_content = """TY  - JOUR
TI  - Test Paper Title
AU  - John Doe
AU  - Jane Smith
PY  - 2023
AB  - This is a test abstract.
JO  - Test Journal
DO  - 10.1234/test.2023
ER  - 
"""
        path = self._create_ris_file(ris_content)
        try:
            papers = parse_ris_file(path)
            assert len(papers) == 1
            assert papers[0].title == "Test Paper Title"
            assert "John Doe" in papers[0].authors
            assert "Jane Smith" in papers[0].authors
            assert papers[0].year == 2023
            assert papers[0].abstract == "This is a test abstract."
            assert papers[0].venue == "Test Journal"
            assert papers[0].doi == "10.1234/test.2023"
            assert papers[0].source == "ris"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_parse_multiple_entries(self):
        ris_content = """TY  - JOUR
TI  - First Paper
AU  - Author One
PY  - 2022
AB  - Abstract one.
ER  - 

TY  - JOUR
TI  - Second Paper
AU  - Author Two
PY  - 2023
AB  - Abstract two.
ER  - 
"""
        path = self._create_ris_file(ris_content)
        try:
            papers = parse_ris_file(path)
            assert len(papers) == 2
            assert papers[0].title == "First Paper"
            assert papers[1].title == "Second Paper"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_skip_entries_without_title(self):
        ris_content = """TY  - JOUR
AU  - Author Only
PY  - 2023
ER  - 
"""
        path = self._create_ris_file(ris_content)
        try:
            papers = parse_ris_file(path)
            assert len(papers) == 0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_empty_file(self):
        path = self._create_ris_file("")
        try:
            papers = parse_ris_file(path)
            assert len(papers) == 0
        finally:
            Path(path).unlink(missing_ok=True)
