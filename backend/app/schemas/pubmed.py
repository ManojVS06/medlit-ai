"""
Pydantic schemas for PubMed search and article retrieval.

WHY SEPARATE SCHEMAS FOR PUBMED:
The summarization schemas (summary.py) define how WE structure a summary.
These schemas define how we represent EXTERNAL data from PubMed.

We keep them separate because:
1. PubMed data has its own structure (PMIDs, MeSH terms, author lists).
2. Our summary schema shouldn't depend on PubMed-specific fields.
3. If we later add another data source (e.g., Semantic Scholar), only
   the source-specific schemas and service change — not the summary logic.

KEY CONCEPTS:
- SearchRequest: What the user sends us (query, filters, pagination).
- PubMedArticle: Our normalized representation of one PubMed record.
- SearchResponse: The full response with articles + pagination metadata.

DESIGN DECISION — Why not use PubMed's raw XML structure?
PubMed XML has deeply nested, complex structures (MedlineCitation,
Article, AuthorList, etc.). We flatten this into a clean, simple model
that the frontend can consume directly. This is called a
Data Transfer Object (DTO) pattern — we translate external complexity
into internal simplicity.
"""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    A search request from the user.

    The user provides a query string and optional filters.
    Pydantic validates everything before we touch PubMed.

    WHY VALIDATE HERE:
    - Prevents empty queries from hitting PubMed (wastes a request).
    - Limits max_results to prevent accidentally fetching 10,000 records.
    - Ensures page >= 1 (0 or negative pages don't make sense).
    """

    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Search query (e.g., 'exercise type 2 diabetes HbA1c')",
        examples=["exercise type 2 diabetes glycemic control"],
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results per page (1-50)",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-based)",
    )

    # Optional filters
    date_from: str | None = Field(
        default=None,
        description="Start date filter (YYYY/MM/DD or YYYY)",
        examples=["2020/01/01", "2020"],
    )
    date_to: str | None = Field(
        default=None,
        description="End date filter (YYYY/MM/DD or YYYY)",
        examples=["2024/12/31", "2024"],
    )
    publication_type: str | None = Field(
        default=None,
        description="Filter by publication type (e.g., 'Review', 'Clinical Trial', 'Meta-Analysis')",
        examples=["Randomized Controlled Trial"],
    )


class PubMedArticle(BaseModel):
    """
    Normalized representation of a single PubMed article.

    This is the core data model for articles throughout the app.
    We extract only the fields we need from PubMed's complex XML.

    DESIGN DECISION — Why these specific fields?
    These map directly to what researchers need when screening:
    - pmid: Unique identifier, links to the original publication.
    - title: For quick identification.
    - authors: For citation and credibility assessment.
    - journal: Publication venue matters for quality assessment.
    - pub_date: Recency affects relevance.
    - abstract: The main text we'll summarize.
    - doi: Alternative identifier and link.
    - pub_types: Helps filter by study design (RCT, review, etc.)
    """

    pmid: str = Field(
        description="PubMed unique identifier",
    )
    title: str = Field(
        default="Title not available",
        description="Article title",
    )
    authors: list[str] = Field(
        default_factory=list,
        description="List of author names (LastName FirstInitials format)",
    )
    journal: str = Field(
        default="Journal not available",
        description="Journal name",
    )
    pub_date: str = Field(
        default="Date not available",
        description="Publication date (formatted as available)",
    )
    abstract: str = Field(
        default="",
        description="Article abstract text (may be empty if not available)",
    )
    doi: str | None = Field(
        default=None,
        description="Digital Object Identifier, if available",
    )
    pub_types: list[str] = Field(
        default_factory=list,
        description="Publication types (e.g., 'Journal Article', 'Randomized Controlled Trial')",
    )
    pubmed_url: str = Field(
        default="",
        description="Direct link to the PubMed page for this article",
    )


class SearchResponse(BaseModel):
    """
    Complete response for a PubMed search.

    Contains the articles AND pagination metadata so the frontend
    knows how many total results exist and what page we're on.

    WHY PAGINATION METADATA:
    PubMed may return 50,000 results for a broad query. We only
    fetch a small page at a time. The frontend needs total_results
    to show "Page 1 of 500" and render pagination controls.
    """

    articles: list[PubMedArticle] = Field(
        default_factory=list,
        description="List of articles for the current page",
    )
    total_results: int = Field(
        default=0,
        description="Total number of results matching the query",
    )
    page: int = Field(
        default=1,
        description="Current page number",
    )
    max_results: int = Field(
        default=10,
        description="Results per page",
    )
    query: str = Field(
        default="",
        description="The search query that was executed",
    )
    search_source: str = Field(
        default="PubMed (NCBI E-utilities)",
        description="Data source for transparency",
    )

