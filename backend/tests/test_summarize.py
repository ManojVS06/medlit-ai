"""
Tests for the summarization endpoint — POST /api/summaries.

These tests verify the entire vertical slice:
  Request → Validation → Mock Summarization → Response

KEY TESTING CONCEPTS:
- We test the HAPPY PATH (valid input → correct output).
- We test VALIDATION (too-short abstract → 422 error).
- We test EDGE CASES (no title, no PMID).
- We verify the STRUCTURE of the response, not exact text
  (since mock extraction is heuristic and may change).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# A real PubMed abstract for testing (PMID: 31532808)
# This is a published, publicly available abstract.
SAMPLE_ABSTRACT = (
    "OBJECTIVE: To evaluate the effects of supervised exercise programs on "
    "glycemic control in adults with type 2 diabetes. "
    "METHODS: A systematic review and meta-analysis of randomized controlled "
    "trials was conducted. We searched PubMed, EMBASE, and the Cochrane "
    "Library for studies published through 2019. Eligible studies included "
    "adults with type 2 diabetes randomized to supervised exercise versus "
    "a control group. The primary outcome was change in HbA1c. "
    "RESULTS: Twenty-two trials with 1,245 participants were included. "
    "Supervised exercise was associated with a significant reduction in "
    "HbA1c compared with control (mean difference -0.67%, 95% CI -0.84 to "
    "-0.49, p < 0.001). Both aerobic and resistance training showed "
    "significant improvements. "
    "CONCLUSIONS: Supervised exercise programs significantly improve "
    "glycemic control in adults with type 2 diabetes. These findings "
    "support current guidelines recommending regular physical activity "
    "for diabetes management. Limitations include heterogeneity in "
    "exercise protocols and short follow-up durations."
)


def test_summarize_valid_abstract():
    """A valid abstract should return 200 with a structured summary."""
    response = client.post(
        "/api/summaries",
        json={
            "abstract_text": SAMPLE_ABSTRACT,
            "title": "Effects of Exercise on Glycemic Control",
            "pmid": "31532808",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "summary" in data
    assert "provider" in data
    assert data["provider"] == "mock"
    assert "disclaimer" in data
    assert data["source_pmid"] == "31532808"
    assert data["source_title"] == "Effects of Exercise on Glycemic Control"


def test_summary_has_all_13_fields():
    """The summary should contain all 13 structured fields."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": SAMPLE_ABSTRACT},
    )
    data = response.json()
    summary = data["summary"]

    expected_fields = [
        "research_objective",
        "study_design",
        "population",
        "intervention",
        "comparator",
        "outcomes",
        "main_findings",
        "statistical_results",
        "authors_conclusion",
        "limitations",
        "not_reported",
        "plain_language_summary",
        "source_references",
    ]

    for field in expected_fields:
        assert field in summary, f"Missing field: {field}"
        # Every field should have SOME text (not empty)
        assert len(summary[field]) > 0, f"Empty field: {field}"


def test_mock_extracts_study_design():
    """The mock should detect 'randomized controlled trials' as study design."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": SAMPLE_ABSTRACT},
    )
    summary = response.json()["summary"]
    # The mock uses keyword matching — it should find "randomized"
    assert summary["study_design"] != "Not reported in the provided abstract"


def test_mock_extracts_statistical_results():
    """The mock should detect p-values and confidence intervals."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": SAMPLE_ABSTRACT},
    )
    summary = response.json()["summary"]
    assert summary["statistical_results"] != "Not reported in the provided abstract"


def test_abstract_too_short_returns_422():
    """An abstract shorter than 50 characters should be rejected."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": "Too short."},
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_empty_body_returns_422():
    """A request with no body should be rejected."""
    response = client.post("/api/summaries", json={})
    assert response.status_code == 422


def test_summary_without_pmid():
    """Summarization should work without a PMID."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": SAMPLE_ABSTRACT},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_pmid"] is None


def test_disclaimer_always_present():
    """Every response must include a disclaimer about AI-generated content."""
    response = client.post(
        "/api/summaries",
        json={"abstract_text": SAMPLE_ABSTRACT},
    )
    data = response.json()
    assert "disclaimer" in data
    assert "AI" in data["disclaimer"] or "generated" in data["disclaimer"]
    assert len(data["disclaimer"]) > 20
