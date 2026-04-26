"""Tests for analysis result validation."""

from analyzer.validator import validate_chunk_result, validate_synthesis
from analyzer.coverage_checker import check_coverage, collect_evidence_ids, get_missing_papers
from models.paper import Paper


class TestCollectEvidenceIds:
    """Tests for evidence ID collection from nested structures."""

    def test_simple_structure(self):
        data = {
            "topic_clusters": [
                {"cluster_name": "Test", "evidence_ids": ["#1", "#2"]},
            ]
        }
        ids = collect_evidence_ids(data)
        assert ids == {"#1", "#2"}

    def test_nested_structure(self):
        data = {
            "chunk_id": 1,
            "papers_covered": ["#1", "#2", "#3"],
            "topic_clusters": [
                {"evidence_ids": ["#1"]},
                {"evidence_ids": ["#2", "#3"]},
            ],
        }
        ids = collect_evidence_ids(data)
        assert ids == {"#1", "#2", "#3"}

    def test_empty_structure(self):
        ids = collect_evidence_ids({})
        assert ids == set()


class TestCheckCoverage:
    """Tests for coverage checking."""

    def test_full_coverage(self):
        papers = [
            Paper(id="#1", title="Paper 1"),
            Paper(id="#2", title="Paper 2"),
        ]
        chunk_results = [
            {"papers_covered": ["#1", "#2"], "topic_clusters": [{"evidence_ids": ["#1", "#2"]}]},
        ]
        report = check_coverage(papers, chunk_results)
        assert report["coverage_ratio"] == 1.0
        assert report["missing_ids"] == []

    def test_partial_coverage(self):
        papers = [
            Paper(id="#1", title="Paper 1"),
            Paper(id="#2", title="Paper 2"),
            Paper(id="#3", title="Paper 3"),
        ]
        chunk_results = [
            {"evidence_ids": ["#1", "#2"]},
        ]
        report = check_coverage(papers, chunk_results)
        assert report["coverage_ratio"] == 2 / 3
        assert "#3" in report["missing_ids"]

    def test_invalid_ids(self):
        papers = [Paper(id="#1", title="Paper 1")]
        chunk_results = [{"evidence_ids": ["#1", "#99"]}]
        report = check_coverage(papers, chunk_results)
        assert "#99" in report["invalid_ids"]

    def test_empty_papers(self):
        report = check_coverage([], [])
        assert report["coverage_ratio"] == 0


class TestGetMissingPapers:
    """Tests for getting missing paper objects."""

    def test_get_missing(self):
        papers = [
            Paper(id="#1", title="Paper 1"),
            Paper(id="#2", title="Paper 2"),
            Paper(id="#3", title="Paper 3"),
        ]
        coverage = {"missing_ids": ["#2", "#3"]}
        missing = get_missing_papers(papers, coverage)
        assert len(missing) == 2
        assert missing[0].id == "#2"
        assert missing[1].id == "#3"


class TestValidateChunkResult:
    """Tests for chunk result validation."""

    def test_valid_result(self):
        result = {
            "chunk_id": 1,
            "papers_covered": ["#1", "#2"],
            "topic_clusters": [
                {"cluster_name": "Test", "evidence_ids": ["#1", "#2"]},
            ],
        }
        valid_ids = {"#1", "#2"}
        report = validate_chunk_result(result, valid_ids)
        assert report["valid"] is True
        assert report["invalid_ids"] == []

    def test_invalid_ids(self):
        result = {
            "topic_clusters": [
                {"evidence_ids": ["#1", "#99"]},
            ],
        }
        valid_ids = {"#1", "#2"}
        report = validate_chunk_result(result, valid_ids)
        assert report["valid"] is False
        assert "#99" in report["invalid_ids"]


class TestValidateSynthesis:
    """Tests for synthesis validation."""

    def test_valid_synthesis(self):
        synthesis = {
            "global_topic_clusters": [
                {"cluster_name": "Test", "evidence_ids": ["#1", "#2"]},
            ],
        }
        valid_ids = {"#1", "#2"}
        report = validate_synthesis(synthesis, valid_ids)
        assert report["valid"] is True

    def test_synthesis_with_invalid_ids(self):
        synthesis = {
            "global_topic_clusters": [
                {"evidence_ids": ["#1", "#999"]},
            ],
        }
        valid_ids = {"#1", "#2"}
        report = validate_synthesis(synthesis, valid_ids)
        assert report["valid"] is False
        assert "#999" in report["invalid_ids"]
