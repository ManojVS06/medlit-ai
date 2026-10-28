"""
Mock summarization service — deterministic, no LLM required.

WHY THIS EXISTS:
Before integrating a real LLM (Milestone 4), we need a working
summarization service to build and test against. This mock:

1. Demonstrates the SERVICE INTERFACE that real providers will implement.
2. Lets us develop the frontend without API keys.
3. Makes automated tests fast, free, and deterministic.
4. Shows how structured extraction COULD work with simple heuristics.

HOW IT WORKS:
- Scans the abstract text for keywords associated with each field.
- Extracts surrounding sentences as the field value.
- Returns NOT_REPORTED for fields it can't find.

This is intentionally simple and imperfect — the point is to establish
the data flow, not to produce good summaries. The real LLM will replace
this logic in Milestone 4.

DESIGN PATTERN — Strategy Pattern:
We'll define a base interface (ABC) and implement it multiple ways:
  - MockProvider (this file) — deterministic, for testing
  - GeminiProvider (Milestone 4) — calls Google Gemini API
  - OllamaProvider (Milestone 4) — calls a local Ollama model

The summarization service picks the right provider based on config,
and the rest of the app doesn't know or care which one is running.
"""

import logging
import re

from app.schemas.summary import (
    NOT_REPORTED,
    StructuredSummary,
    SummarizeRequest,
    SummarizeResponse,
)

logger = logging.getLogger(__name__)


def _extract_sentences_near_keyword(
    text: str, keywords: list[str], max_sentences: int = 2
) -> str | None:
    """
    Find sentences containing any of the keywords.
    Returns up to max_sentences joined together, or None if no match.

    This is a crude heuristic — real extraction needs an LLM.
    """
    # Split text into sentences (simple regex, not perfect)
    sentences = re.split(r'(?<=[.!?])\s+', text)

    matches = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(kw.lower() in sentence_lower for kw in keywords):
            matches.append(sentence.strip())
            if len(matches) >= max_sentences:
                break

    return " ".join(matches) if matches else None


def _generate_plain_language_summary(text: str) -> str:
    """Generate a simple plain-language summary from the first 2 sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) >= 2:
        return f"{sentences[0]} {sentences[1]}"
    elif sentences:
        return sentences[0]
    return NOT_REPORTED


def mock_summarize(request: SummarizeRequest) -> SummarizeResponse:
    """
    Generate a structured summary using keyword-based extraction.

    This function demonstrates the EXACT interface that the real
    LLM-based summarization will use. The input and output types
    are identical — only the extraction logic changes.

    Args:
        request: Validated summarization request with abstract text.

    Returns:
        SummarizeResponse with structured fields and metadata.
    """
    text = request.abstract_text
    logger.info(
        f"Mock summarization for abstract ({len(text)} chars), "
        f"PMID={request.pmid or 'unknown'}"
    )

    summary = StructuredSummary(
        research_objective=_extract_sentences_near_keyword(
            text,
            ["objective", "aim", "purpose", "goal", "investigate",
             "examine", "evaluate", "assess", "determine", "study aimed"],
        ) or NOT_REPORTED,

        study_design=_extract_sentences_near_keyword(
            text,
            ["randomized", "randomised", "cohort", "cross-sectional",
             "meta-analysis", "systematic review", "case-control",
             "observational", "prospective", "retrospective", "trial",
             "double-blind", "single-blind", "open-label"],
        ) or NOT_REPORTED,

        population=_extract_sentences_near_keyword(
            text,
            ["participants", "patients", "subjects", "n =", "n=",
             "sample", "enrolled", "recruited", "adults", "children",
             "men", "women", "aged"],
        ) or NOT_REPORTED,

        intervention=_extract_sentences_near_keyword(
            text,
            ["intervention", "treatment", "therapy", "exercise",
             "drug", "dose", "administered", "received", "program",
             "protocol", "regimen"],
        ) or NOT_REPORTED,

        comparator=_extract_sentences_near_keyword(
            text,
            ["control", "placebo", "comparator", "compared to",
             "compared with", "versus", "vs.", "standard care",
             "usual care", "sham"],
        ) or NOT_REPORTED,

        outcomes=_extract_sentences_near_keyword(
            text,
            ["outcome", "endpoint", "measured", "primary outcome",
             "secondary outcome", "HbA1c", "blood glucose", "mortality",
             "morbidity", "quality of life", "adverse"],
        ) or NOT_REPORTED,

        main_findings=_extract_sentences_near_keyword(
            text,
            ["found", "showed", "demonstrated", "resulted",
             "significant", "improved", "reduced", "increased",
             "decreased", "difference", "effect", "associated"],
        ) or NOT_REPORTED,

        statistical_results=_extract_sentences_near_keyword(
            text,
            ["p =", "p=", "p <", "p<", "CI", "confidence interval",
             "odds ratio", "hazard ratio", "risk ratio", "effect size",
             "95%", "statistically significant", "mean difference"],
        ) or NOT_REPORTED,

        authors_conclusion=_extract_sentences_near_keyword(
            text,
            ["conclusion", "conclude", "in summary", "these findings",
             "our results suggest", "we conclude", "taken together",
             "in conclusion"],
        ) or NOT_REPORTED,

        limitations=_extract_sentences_near_keyword(
            text,
            ["limitation", "limitations", "however", "caveat",
             "weakness", "shortcoming", "bias", "small sample",
             "generalizability", "future research"],
        ) or NOT_REPORTED,

        not_reported=_identify_missing_fields(text),

        plain_language_summary=_generate_plain_language_summary(text),

        source_references=(
            f"PMID: {request.pmid}" if request.pmid
            else f"Title: {request.title}" if request.title
            else "Source not specified"
        ),
    )

    return SummarizeResponse(
        summary=summary,
        provider="mock",
        source_pmid=request.pmid,
        source_title=request.title,
    )


def _identify_missing_fields(text: str) -> str:
    """Identify which standard fields appear to be missing from the abstract."""
    missing = []
    text_lower = text.lower()

    checks = [
        (["sample", "n =", "n=", "participants", "subjects", "enrolled"],
         "Sample size"),
        (["p =", "p=", "p <", "confidence interval", "95%"],
         "Statistical measures"),
        (["limitation", "limitations", "weakness"],
         "Study limitations"),
        (["control", "placebo", "comparator", "compared"],
         "Comparator/control group"),
        (["conclusion", "conclude", "findings suggest"],
         "Explicit conclusion"),
        (["adverse", "side effect", "safety", "harm"],
         "Safety/adverse events"),
        (["funding", "funded", "grant", "sponsor"],
         "Funding source"),
    ]

    for keywords, label in checks:
        if not any(kw in text_lower for kw in keywords):
            missing.append(label)

    if missing:
        return f"Not explicitly mentioned: {', '.join(missing)}"
    return "All standard fields appear to be addressed"
