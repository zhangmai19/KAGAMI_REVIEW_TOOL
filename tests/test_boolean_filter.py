"""Tests for the boolean filter module."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.paper import Paper
from utils.boolean_filter import (
    normalize,
    match_term,
    match_group,
    boolean_filter,
    expanded_keywords_to_groups,
    groups_to_broad_query,
)


# ── normalize ──

def test_normalize_basic():
    assert normalize("Hello World") == "hello world"


def test_normalize_strips_punctuation():
    # Apostrophe becomes space, hyphen kept, period removed
    assert normalize("It's a test-case.") == "it s a test-case"


def test_normalize_collapses_spaces():
    assert normalize("  hello   world  ") == "hello world"


def test_normalize_empty():
    assert normalize("") == ""


def test_normalize_mixed():
    text = normalize("Reinsurance: A Risk-Transfer Mechanism (2023)")
    assert "reinsurance" in text
    assert "risk-transfer" in text
    assert ":" not in text
    assert "(" not in text


# ── match_term ──

def test_match_term_single_word():
    assert match_term("reinsurance model", "reinsurance")


def test_match_term_plural():
    assert match_term("reinsurers provide coverage", "reinsurer")


def test_match_term_plural_es():
    assert match_term("processes of risk", "process")


def test_match_term_phrase():
    assert match_term("catastrophe bond issuance", "catastrophe bond")


def test_match_term_no_match():
    assert not match_term("healthcare costs", "reinsurance")


def test_match_term_case_insensitive():
    assert match_term("REINSURANCE Market", "reinsurance")


def test_match_term_word_boundary():
    # "cat" should NOT match "catastrophe"
    assert not match_term("catastrophe bond", "cat")


# ── match_group ──

def test_match_group_any_match():
    text = "reinsurance risk transfer"
    assert match_group(text, ["reinsurance", "cat bond", "derivative"])


def test_match_group_none_match():
    text = "healthcare diagnosis"
    assert not match_group(text, ["reinsurance", "cat bond"])


def test_match_group_empty():
    assert not match_group("some text", [])


# ── boolean_filter ──

def _make_paper(title: str, abstract: str = "") -> Paper:
    return Paper(title=title, abstract=abstract, source="test")


def test_boolean_filter_no_groups():
    papers = [_make_paper("Test")]
    assert boolean_filter(papers, []) == papers


def test_boolean_filter_single_group():
    papers = [
        _make_paper("Reinsurance risk model", "Abstract about risk transfer"),
        _make_paper("Healthcare AI", "Abstract about diagnosis"),
    ]
    result = boolean_filter(papers, [["reinsurance", "risk transfer"]])
    assert len(result) == 1
    assert "Reinsurance" in result[0].title


def test_boolean_filter_and_groups():
    papers = [
        _make_paper("Reinsurance risk model", "Mutual insurance and risk sharing"),
        _make_paper("Reinsurance pricing", "Pricing models for traditional insurance"),
        _make_paper("Healthcare AI", "Diagnosis and prediction"),
    ]
    keyword_groups = [
        ["reinsurance", "risk transfer"],
        ["mutual insurance", "insurtech"],
    ]
    result = boolean_filter(papers, keyword_groups)
    assert len(result) == 1
    assert "Reinsurance risk model" in result[0].title


def test_boolean_filter_three_groups():
    papers = [
        _make_paper(
            "Reinsurance risk model",
            "Mutual insurance frameworks for risk sharing and risk pooling",
        ),
        _make_paper(
            "Reinsurance pricing",
            "Mutual insurance and risk sharing only",
        ),
    ]
    keyword_groups = [
        ["reinsurance"],
        ["mutual insurance"],
        ["risk sharing", "risk pooling"],
    ]
    result = boolean_filter(papers, keyword_groups)
    # Both papers have reinsurance + mutual insurance + risk sharing
    assert len(result) == 2


def test_boolean_filter_phrase_match():
    papers = [
        _make_paper("Cat bond issuance", "Catastrophe bond market analysis"),
        _make_paper("Bond pricing", "Regular bond market"),
    ]
    result = boolean_filter(papers, [["catastrophe bond", "cat bond"]])
    assert len(result) == 1
    assert "Cat bond" in result[0].title


def test_boolean_filter_all_filtered_out():
    papers = [
        _make_paper("AI in medicine", "Deep learning for diagnosis"),
        _make_paper("Machine learning", "Neural network architecture"),
    ]
    result = boolean_filter(papers, [["reinsurance"]])
    assert len(result) == 0


def test_boolean_filter_title_and_abstract_combined():
    papers = [
        _make_paper("Risk modeling", "Reinsurance and mutual insurance strategies"),
        _make_paper("Risk modeling", "Healthcare risk assessment"),
    ]
    # "reinsurance" is in abstract of first paper only
    keyword_groups = [["reinsurance"], ["risk"]]
    result = boolean_filter(papers, keyword_groups)
    assert len(result) == 1


# ── expanded_keywords_to_groups ──

def test_expanded_keywords_to_groups():
    expanded = {
        "concepts": [
            {
                "concept": "reinsurance",
                "synonyms": ["risk transfer", "cat bond"],
                "variants": ["reinsurances"],
            },
            {
                "concept": "machine learning",
                "synonyms": ["ML", "deep learning"],
                "variants": [],
            },
        ]
    }
    groups = expanded_keywords_to_groups(expanded)
    assert len(groups) == 2
    assert "reinsurance" in groups[0]
    assert "risk transfer" in groups[0]
    assert "machine learning" in groups[1]
    assert "ML" in groups[1]


def test_expanded_keywords_to_groups_dedup():
    expanded = {
        "concepts": [
            {
                "concept": "AI",
                "synonyms": ["ai", "AI"],  # duplicates
                "variants": [],
            },
        ]
    }
    groups = expanded_keywords_to_groups(expanded)
    # Should deduplicate
    assert len(groups[0]) == 1


# ── groups_to_broad_query ──

def test_groups_to_broad_query():
    groups = [
        ["reinsurance", "risk transfer"],
        ["mutual insurance", "insurtech"],
        ["risk sharing"],
    ]
    query = groups_to_broad_query(groups)
    assert query == "reinsurance mutual insurance risk sharing"


def test_groups_to_broad_query_empty():
    assert groups_to_broad_query([]) == ""


# ── integration: keyword_groups through the full pipeline ──

def test_keyword_groups_end_to_end():
    """Simulate the full flow: keyword_groups → expanded → builder → filter."""
    from query.boolean_builder import OpenAlexQueryBuilder

    # User-defined keyword_groups
    keyword_groups = [
        ["reinsurance", "risk transfer", "cat bond"],
        ["mutual insurance", "insurtech"],
        ["risk sharing", "risk pooling"],
    ]

    # Convert to expanded format (as agent does)
    from agents.literature_review_agent import LiteratureReviewAgent
    expanded = LiteratureReviewAgent._keyword_groups_to_expanded(keyword_groups)

    # Build query artifacts
    builder = OpenAlexQueryBuilder()
    artifacts = builder.build_all(expanded)

    assert artifacts["broad_query"] == "reinsurance mutual insurance risk sharing"
    assert len(artifacts["keyword_groups"]) == 3

    # Apply boolean filter to mock papers
    papers = [
        _make_paper(
            "Reinsurance risk transfer",
            "Mutual insurance frameworks for risk sharing",
        ),
        _make_paper("AI in healthcare", "Diagnosis and prediction"),
    ]

    filtered = boolean_filter(papers, artifacts["keyword_groups"])
    assert len(filtered) == 1
    assert "Reinsurance" in filtered[0].title
