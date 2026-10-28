"""
API routes for summarization.

WHY A SEPARATE ROUTER:
FastAPI lets you organize routes into "routers" — think of them as
sub-applications. Each router handles a specific domain:
  - /api/summaries → this file
  - /api/articles  → articles router (Milestone 3)
  - /api/comparisons → comparisons router (Milestone 7)

This keeps main.py clean and each file focused on one responsibility.

HOW IT CONNECTS:
1. main.py includes this router with `app.include_router(...)`.
2. A POST request to /api/summaries arrives.
3. FastAPI validates the request body against SummarizeRequest.
4. If validation fails → automatic 422 error with details.
5. If valid → our handler calls the summarization service.
6. The service returns a SummarizeResponse.
7. FastAPI serializes it to JSON and sends it back.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.summary import SummarizeRequest, SummarizeResponse
from app.services.summarization_service import mock_summarize

logger = logging.getLogger(__name__)

# Create a router with a prefix and tag.
# prefix="/api/summaries" means all routes here start with /api/summaries.
# tags group related endpoints in the auto-generated API docs.
router = APIRouter(
    prefix="/api/summaries",
    tags=["Summaries"],
)


@router.post(
    "",
    response_model=SummarizeResponse,
    status_code=200,
    summary="Summarize a research abstract",
    description=(
        "Takes a research abstract and returns a structured 13-field summary. "
        "Currently uses a mock provider (keyword extraction). "
        "Real LLM integration will be added in Milestone 4."
    ),
)
async def create_summary(request: SummarizeRequest) -> SummarizeResponse:
    """
    Summarize a single research abstract.

    The request body must contain `abstract_text` (50-15000 characters).
    Optionally include `title` and `pmid` for source tracking.

    Returns a structured summary with 13 fields plus metadata.
    """
    try:
        logger.info(
            f"Summarization request: {len(request.abstract_text)} chars, "
            f"PMID={request.pmid or 'none'}"
        )
        result = mock_summarize(request)
        logger.info(f"Summarization complete (provider={result.provider})")
        return result

    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Summarization failed",
                "message": str(e),
                "hint": "Check the abstract text and try again.",
            },
        )
