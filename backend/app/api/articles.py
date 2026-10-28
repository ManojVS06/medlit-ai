"""
API routes for PubMed article search and retrieval.

ROUTES:
  POST /api/articles/search  — Search PubMed for articles
  GET  /api/articles/{pmid}  — Fetch a single article by PMID

WHY POST FOR SEARCH (instead of GET):
GET requests pass parameters in the URL query string, which works for
simple searches. But our search has a complex body (query + filters),
and URLs have length limits. POST lets us send structured JSON in the
request body, which is cleaner for complex search requests.

Some APIs (like Elasticsearch) also use POST for search because the
request body can be large and complex. It's a pragmatic choice.

ERROR HANDLING:
We catch PubMedServiceError specifically and return HTTP 502 (Bad Gateway),
which tells the client "our upstream service (PubMed) had a problem."
This is different from HTTP 500 (our own code crashed).
"""

import logging
import re

from fastapi import APIRouter, HTTPException

from app.schemas.pubmed import PubMedArticle, SearchRequest, SearchResponse
from app.services.pubmed_service import (
    PubMedServiceError,
    fetch_article_by_pmid,
    search_pubmed,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/articles",
    tags=["Articles"],
)


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=200,
    summary="Search PubMed for articles",
    description=(
        "Searches PubMed using NCBI E-utilities. Returns article metadata "
        "including title, authors, journal, abstract, and source links. "
        "This performs a keyword-based PubMed search — it does not constitute "
        "a systematic literature review."
    ),
)
async def search_articles(request: SearchRequest) -> SearchResponse:
    """
    Search PubMed for articles matching the query.

    The request body supports:
    - query: search terms (required)
    - max_results: results per page (default 10, max 50)
    - page: page number (default 1)
    - date_from/date_to: optional date filters
    - publication_type: optional type filter
    """
    try:
        result = await search_pubmed(request)
        logger.info(
            f"Search returned {len(result.articles)} articles "
            f"(total: {result.total_results})"
        )
        return result

    except PubMedServiceError as e:
        # Upstream service failure → 502 Bad Gateway
        logger.error(f"PubMed service error: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "PubMed service error",
                "message": str(e),
                "hint": "PubMed may be temporarily unavailable. Try again in a moment.",
            },
        )
    except Exception as e:
        # Unexpected error → 500 Internal Server Error
        logger.error(f"Unexpected search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Search failed",
                "message": "An unexpected error occurred during search.",
            },
        )


@router.get(
    "/{pmid}",
    response_model=PubMedArticle,
    status_code=200,
    summary="Fetch a single article by PMID",
    description="Retrieves full article metadata from PubMed by its PMID.",
)
async def get_article(pmid: str) -> PubMedArticle:
    """
    Fetch a single article from PubMed.

    The PMID must be a valid PubMed identifier (numeric string).
    Returns 404 if the article is not found.
    """
    # Basic PMID validation — PMIDs are numeric strings
    if not re.match(r"^\d{1,10}$", pmid):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid PMID",
                "message": f"'{pmid}' is not a valid PubMed ID. PMIDs are numeric.",
            },
        )

    try:
        article = await fetch_article_by_pmid(pmid)
        if article is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Article not found",
                    "message": f"No article found with PMID {pmid}.",
                },
            )
        return article

    except PubMedServiceError as e:
        logger.error(f"PubMed service error fetching PMID {pmid}: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "PubMed service error",
                "message": str(e),
            },
        )

