"""
Pydantic schemas for summarization requests and responses.

WHY SCHEMAS MATTER:
Think of schemas as contracts between the frontend and backend.
The frontend says: "I'll send you data shaped like THIS."
The backend says: "I'll respond with data shaped like THAT."

If either side violates the contract, Pydantic immediately raises
a clear error — instead of the bug silently propagating and causing
a confusing crash somewhere else.

KEY CONCEPTS:
- `BaseModel`: Every schema inherits from this. Pydantic validates
  all fields when an instance is created.
- `Field(...)`: Adds constraints (min/max length, descriptions, examples).
- Optional fields: Use `str | None = None` for fields that may be absent.
- The `model_config` dict controls JSON serialization behavior.

DESIGN DECISION:
We define 13 structured fields for a summary, matching the project spec.
When a field can't be determined from the abstract, we use a standard
sentinel string: "Not reported in the provided abstract".
This makes missing information EXPLICIT rather than silently null.
"""

from pydantic import BaseModel, Field


# Sentinel value for information not found in the abstract.
# Using a constant prevents typos and makes it searchable.
NOT_REPORTED = "Not reported in the provided abstract"


class SummarizeRequest(BaseModel):
    """
    Request to summarize a single research abstract.

    The frontend sends this when the user clicks "Summarize".
    We require the abstract text and optionally accept metadata
    (title, PMID) for reference tracking.
    """

    abstract_text: str = Field(
        ...,  # Required field (no default)
        min_length=50,
        max_length=15000,
        description="The research abstract text to summarize",
        examples=[
            "BACKGROUND: Type 2 diabetes is a growing health concern..."
        ],
    )
    title: str | None = Field(
        default=None,
        max_length=500,
        description="Article title, if available",
    )
    pmid: str | None = Field(
        default=None,
        max_length=20,
        description="PubMed ID, if available",
    )


class StructuredSummary(BaseModel):
    """
    The 13-field structured summary of a research abstract.

    Each field corresponds to a specific aspect that researchers
    care about when screening literature. Fields use the NOT_REPORTED
    sentinel when information isn't available in the source abstract.

    IMPORTANT: This schema is used for BOTH mock and real LLM output.
    The LLM is instructed to produce JSON matching this exact schema.
    Pydantic validates the LLM's output — if the LLM returns garbage,
    validation fails and we handle the error gracefully.
    """

    research_objective: str = Field(
        default=NOT_REPORTED,
        description="The primary research question or objective",
    )
    study_design: str = Field(
        default=NOT_REPORTED,
        description="Type of study (e.g., RCT, cohort, meta-analysis)",
    )
    population: str = Field(
        default=NOT_REPORTED,
        description="Study population and sample size, if reported",
    )
    intervention: str = Field(
        default=NOT_REPORTED,
        description="Intervention or exposure being studied",
    )
    comparator: str = Field(
        default=NOT_REPORTED,
        description="Control or comparison group, if reported",
    )
    outcomes: str = Field(
        default=NOT_REPORTED,
        description="Primary and secondary outcomes measured",
    )
    main_findings: str = Field(
        default=NOT_REPORTED,
        description="Key results and findings",
    )
    statistical_results: str = Field(
        default=NOT_REPORTED,
        description="Statistical results (p-values, CIs, effect sizes) when explicitly stated",
    )
    authors_conclusion: str = Field(
        default=NOT_REPORTED,
        description="The conclusion as stated by the authors",
    )
    limitations: str = Field(
        default=NOT_REPORTED,
        description="Study limitations mentioned in the abstract",
    )
    not_reported: str = Field(
        default=NOT_REPORTED,
        description="Important information that was NOT found in the abstract",
    )
    plain_language_summary: str = Field(
        default=NOT_REPORTED,
        description="A concise plain-language summary of the study",
    )
    source_references: str = Field(
        default=NOT_REPORTED,
        description="Source information (PMID, title) for traceability",
    )


class SummarizeResponse(BaseModel):
    """
    The complete response for a summarization request.

    Wraps the structured summary with metadata about how it was generated.
    This metadata helps the user understand what produced the summary
    and whether to trust it.
    """

    summary: StructuredSummary
    provider: str = Field(
        description="Which LLM provider generated this summary (e.g., 'mock', 'gemini')",
    )
    disclaimer: str = Field(
        default=(
            "This summary was generated by AI and has not been verified by a "
            "domain expert. Always consult the original publication for "
            "authoritative information."
        ),
        description="Standard disclaimer about AI-generated content",
    )
    source_pmid: str | None = Field(
        default=None,
        description="PMID of the source article, if provided",
    )
    source_title: str | None = Field(
        default=None,
        description="Title of the source article, if provided",
    )
