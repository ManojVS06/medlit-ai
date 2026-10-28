"""
PubMed service — searches and retrieves articles from NCBI E-utilities.

HOW NCBI E-UTILITIES WORK:
NCBI provides HTTP APIs for accessing their databases. We use two:

1. ESearch — Search a database and get a list of matching record IDs.
   URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
   Input: search query, filters
   Output: list of PMIDs + total count

2. EFetch — Retrieve full records for specific IDs.
   URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
   Input: list of PMIDs
   Output: full article metadata in XML format

WHY TWO STEPS:
This is a common API pattern called "search then fetch."
- Search is fast but returns only IDs (lightweight).
- Fetch is heavier but gives you full data.
- This lets PubMed serve millions of searches efficiently.

RATE LIMITS:
- Without API key: 3 requests/second
- With API key: 10 requests/second
- We add the api_key, tool, and email parameters as required.

ERROR HANDLING STRATEGY:
External APIs can fail in many ways. We handle:
1. Network errors (timeout, DNS, connection refused)
2. HTTP errors (500, 503, 429)
3. Malformed responses (invalid XML, missing fields)
4. Empty results (valid search, no matches)
5. Missing abstracts (common — not every article has one)

Each error type gets a clear, user-friendly message.
"""

import logging
import xml.etree.ElementTree as ET

import httpx

from app.core.config import settings
from app.schemas.pubmed import PubMedArticle, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

# NCBI E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Timeout for HTTP requests to NCBI (seconds)
# PubMed can be slow during peak hours.
NCBI_TIMEOUT = 30.0


class PubMedServiceError(Exception):
    """Custom exception for PubMed service failures.

    WHY A CUSTOM EXCEPTION:
    Instead of catching generic Exception everywhere, we can catch
    PubMedServiceError specifically. This lets the API router return
    an appropriate HTTP status code (502 for upstream failures vs
    500 for our own bugs).
    """
    pass


def _build_esearch_params(request: SearchRequest) -> dict:
    """
    Build the query parameters for the ESearch API.

    This translates our SearchRequest into PubMed's URL parameters.
    We separate this to make it testable and readable.

    PubMed ESearch parameters:
    - db: database name ("pubmed")
    - term: the search query
    - retstart: offset for pagination (0-based)
    - retmax: max results to return
    - retmode: response format ("json" — ESearch supports JSON!)
    - datetype: which date field to filter on
    - mindate/maxdate: date range
    - sort: result ordering
    """
    # Calculate retstart from page number.
    # Page 1, max_results=10 → retstart=0
    # Page 2, max_results=10 → retstart=10
    # Page 3, max_results=10 → retstart=20
    retstart = (request.page - 1) * request.max_results

    params: dict = {
        "db": "pubmed",
        "term": request.query,
        "retstart": retstart,
        "retmax": request.max_results,
        "retmode": "json",  # ESearch returns JSON
        "sort": "relevance",
    }

    # Add NCBI identification (required by terms of use)
    if settings.NCBI_API_KEY:
        params["api_key"] = settings.NCBI_API_KEY
    if settings.NCBI_EMAIL:
        params["email"] = settings.NCBI_EMAIL
    if settings.NCBI_TOOL:
        params["tool"] = settings.NCBI_TOOL

    # Add optional date filter
    if request.date_from or request.date_to:
        params["datetype"] = "pdat"  # Publication date
        if request.date_from:
            params["mindate"] = request.date_from
        if request.date_to:
            params["maxdate"] = request.date_to

    # Add publication type filter
    # PubMed uses "ptyp" field qualifier for publication types
    if request.publication_type:
        params["term"] = f'{request.query} AND {request.publication_type}[pt]'

    return params


async def _esearch(params: dict) -> tuple[list[str], int]:
    """
    Call PubMed ESearch and return (list_of_pmids, total_count).

    ESearch JSON response structure:
    {
        "esearchresult": {
            "count": "12345",         # Total results
            "retmax": "10",           # How many IDs returned
            "retstart": "0",          # Offset
            "idlist": ["12345", "67890", ...]  # The PMIDs
        }
    }

    Returns:
        Tuple of (pmid_list, total_result_count)

    Raises:
        PubMedServiceError on any failure.
    """
    try:
        async with httpx.AsyncClient(timeout=NCBI_TIMEOUT) as client:
            response = await client.get(ESEARCH_URL, params=params)
            response.raise_for_status()

        data = response.json()
        result = data.get("esearchresult", {})

        # Check for NCBI error messages
        if "ERROR" in result:
            error_msg = result["ERROR"]
            logger.error(f"ESearch returned error: {error_msg}")
            raise PubMedServiceError(f"PubMed search error: {error_msg}")

        pmids = result.get("idlist", [])
        total_count = int(result.get("count", 0))

        logger.info(
            f"ESearch returned {len(pmids)} PMIDs "
            f"(total: {total_count}, query: '{params.get('term', '')}')"
        )
        return pmids, total_count

    except httpx.TimeoutException:
        logger.error("ESearch request timed out")
        raise PubMedServiceError(
            "PubMed search timed out. The service may be busy — please try again."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"ESearch HTTP error: {e.response.status_code}")
        raise PubMedServiceError(
            f"PubMed returned HTTP {e.response.status_code}. "
            "The service may be temporarily unavailable."
        )
    except httpx.RequestError as e:
        logger.error(f"ESearch network error: {e}")
        raise PubMedServiceError(
            "Could not connect to PubMed. Check your internet connection."
        )
    except (ValueError, KeyError) as e:
        logger.error(f"ESearch response parsing error: {e}")
        raise PubMedServiceError(
            "Received an unexpected response from PubMed."
        )


async def _efetch(pmids: list[str]) -> list[PubMedArticle]:
    """
    Call PubMed EFetch to get full article details for a list of PMIDs.

    WHY XML (not JSON):
    EFetch's JSON mode for PubMed is limited and not fully supported
    for all record types. XML is the official, complete format.
    We parse it with Python's built-in xml.etree.ElementTree.

    EFetch XML structure (simplified):
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345</PMID>
          <Article>
            <ArticleTitle>...</ArticleTitle>
            <Abstract>
              <AbstractText>...</AbstractText>
            </Abstract>
            <AuthorList>
              <Author>
                <LastName>Smith</LastName>
                <Initials>J</Initials>
              </Author>
            </AuthorList>
            <Journal>
              <Title>Journal Name</Title>
            </Journal>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>

    Args:
        pmids: List of PubMed IDs to fetch.

    Returns:
        List of PubMedArticle models.

    Raises:
        PubMedServiceError on failure.
    """
    if not pmids:
        return []

    params: dict = {
        "db": "pubmed",
        "id": ",".join(pmids),  # Comma-separated PMIDs
        "retmode": "xml",       # XML is the complete format
        "rettype": "abstract",  # Include abstracts
    }

    # Add NCBI identification
    if settings.NCBI_API_KEY:
        params["api_key"] = settings.NCBI_API_KEY
    if settings.NCBI_EMAIL:
        params["email"] = settings.NCBI_EMAIL
    if settings.NCBI_TOOL:
        params["tool"] = settings.NCBI_TOOL

    try:
        async with httpx.AsyncClient(timeout=NCBI_TIMEOUT) as client:
            response = await client.get(EFETCH_URL, params=params)
            response.raise_for_status()

        articles = _parse_efetch_xml(response.text)
        logger.info(f"EFetch parsed {len(articles)} articles from {len(pmids)} PMIDs")
        return articles

    except httpx.TimeoutException:
        logger.error("EFetch request timed out")
        raise PubMedServiceError(
            "PubMed article retrieval timed out. Please try again."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"EFetch HTTP error: {e.response.status_code}")
        raise PubMedServiceError(
            f"PubMed returned HTTP {e.response.status_code} when fetching articles."
        )
    except httpx.RequestError as e:
        logger.error(f"EFetch network error: {e}")
        raise PubMedServiceError(
            "Could not connect to PubMed for article retrieval."
        )
    except ET.ParseError as e:
        logger.error(f"EFetch XML parsing error: {e}")
        raise PubMedServiceError(
            "Received malformed data from PubMed."
        )


def _parse_efetch_xml(xml_text: str) -> list[PubMedArticle]:
    """
    Parse EFetch XML response into PubMedArticle models.

    This is where we translate PubMed's complex XML structure into
    our clean, flat data model. Each PubmedArticle XML element becomes
    one PubMedArticle Pydantic model.

    DEFENSIVE PARSING:
    PubMed XML is inconsistent — some articles miss fields, have
    different structures, or use alternate elements. We use helper
    functions with safe defaults to handle all cases.
    """
    root = ET.fromstring(xml_text)
    articles = []

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            article = _parse_single_article(article_elem)
            articles.append(article)
        except Exception as e:
            # If ONE article fails to parse, log it and skip.
            # Don't let one bad record break the entire search.
            pmid = _safe_find_text(article_elem, ".//PMID", "unknown")
            logger.warning(f"Failed to parse article PMID={pmid}: {e}")
            continue

    return articles


def _parse_single_article(elem: ET.Element) -> PubMedArticle:
    """Parse a single <PubmedArticle> XML element into our model."""

    # --- PMID ---
    pmid = _safe_find_text(elem, ".//PMID", "unknown")

    # --- Title ---
    title = _safe_find_text(
        elem,
        ".//Article/ArticleTitle",
        "Title not available",
    )

    # --- Authors ---
    authors = _parse_authors(elem)

    # --- Journal ---
    journal = _safe_find_text(
        elem,
        ".//Journal/Title",
        # Fallback to abbreviated journal name
        _safe_find_text(elem, ".//Journal/ISOAbbreviation", "Journal not available"),
    )

    # --- Publication Date ---
    pub_date = _parse_pub_date(elem)

    # --- Abstract ---
    abstract = _parse_abstract(elem)

    # --- DOI ---
    doi = _parse_doi(elem)

    # --- Publication Types ---
    pub_types = [
        pt.text
        for pt in elem.findall(".//PublicationTypeList/PublicationType")
        if pt.text
    ]

    # --- PubMed URL ---
    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    return PubMedArticle(
        pmid=pmid,
        title=title,
        authors=authors,
        journal=journal,
        pub_date=pub_date,
        abstract=abstract,
        doi=doi,
        pub_types=pub_types,
        pubmed_url=pubmed_url,
    )


def _safe_find_text(
    elem: ET.Element, path: str, default: str = ""
) -> str:
    """
    Safely extract text from an XML element.

    WHY: elem.find(path) returns None if the element doesn't exist.
    Calling .text on None would crash. This helper handles it cleanly.
    """
    found = elem.find(path)
    if found is not None and found.text:
        return found.text.strip()
    return default


def _parse_authors(elem: ET.Element) -> list[str]:
    """
    Extract author names from the AuthorList.

    PubMed has two author formats:
    1. Individual: <LastName> + <Initials>  → "Smith JA"
    2. Collective: <CollectiveName>          → "WHO Working Group"

    We handle both, and return an empty list if no authors found.
    """
    authors = []
    for author in elem.findall(".//AuthorList/Author"):
        last = author.findtext("LastName", "")
        initials = author.findtext("Initials", "")
        if last:
            name = f"{last} {initials}".strip()
            authors.append(name)
        else:
            # Collective author (e.g., an organization)
            collective = author.findtext("CollectiveName", "")
            if collective:
                authors.append(collective)
    return authors


def _parse_pub_date(elem: ET.Element) -> str:
    """
    Extract and format the publication date.

    PubMed dates can be in different elements and formats:
    1. <PubDate><Year>2023</Year><Month>Jan</Month></PubDate>
    2. <PubDate><MedlineDate>2023 Jan-Feb</MedlineDate></PubDate>

    We try to build "YYYY Mon" or fall back to whatever is available.
    """
    # Try ArticleDate first (usually the electronic publication date)
    pub_date_elem = elem.find(".//Article/ArticleDate")
    if pub_date_elem is not None:
        year = pub_date_elem.findtext("Year", "")
        month = pub_date_elem.findtext("Month", "")
        day = pub_date_elem.findtext("Day", "")
        if year:
            parts = [year]
            if month:
                parts.append(month.zfill(2))
            if day:
                parts.append(day.zfill(2))
            return "/".join(parts)

    # Try Journal PubDate
    pub_date_elem = elem.find(".//Journal/JournalIssue/PubDate")
    if pub_date_elem is not None:
        # Check for MedlineDate first (free-text format)
        medline_date = pub_date_elem.findtext("MedlineDate", "")
        if medline_date:
            return medline_date

        year = pub_date_elem.findtext("Year", "")
        month = pub_date_elem.findtext("Month", "")
        season = pub_date_elem.findtext("Season", "")
        if year:
            if month:
                return f"{year} {month}"
            if season:
                return f"{year} {season}"
            return year

    return "Date not available"


def _parse_abstract(elem: ET.Element) -> str:
    """
    Extract abstract text.

    PubMed abstracts can be:
    1. Simple: single <AbstractText> element
    2. Structured: multiple <AbstractText Label="BACKGROUND"> elements

    For structured abstracts, we concatenate all sections with their labels.
    This preserves the structure (BACKGROUND:, METHODS:, RESULTS:, etc.)
    which our summarizer can use.
    """
    abstract_parts = []
    for abstract_text in elem.findall(".//Abstract/AbstractText"):
        label = abstract_text.get("Label", "")
        # Collect all text content including text in child elements
        text = "".join(abstract_text.itertext()).strip()
        if text:
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)

    return " ".join(abstract_parts)


def _parse_doi(elem: ET.Element) -> str | None:
    """
    Extract the DOI from ELocationID or ArticleIdList.

    DOIs can appear in two places in PubMed XML:
    1. <ELocationID EIdType="doi">10.xxxx/yyyy</ELocationID>
    2. <ArticleId IdType="doi">10.xxxx/yyyy</ArticleId>
    """
    # Try ELocationID first
    for eloc in elem.findall(".//Article/ELocationID"):
        if eloc.get("EIdType") == "doi" and eloc.text:
            return eloc.text.strip()

    # Fallback to ArticleIdList
    for aid in elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi" and aid.text:
            return aid.text.strip()

    return None


# ============================================================
# PUBLIC API — These functions are called by the API router
# ============================================================


async def search_pubmed(request: SearchRequest) -> SearchResponse:
    """
    Search PubMed for articles matching the request.

    This is the main entry point for the PubMed service.
    It orchestrates the two-step search:
    1. ESearch to get PMIDs
    2. EFetch to get full article details

    Args:
        request: Validated search request.

    Returns:
        SearchResponse with articles and pagination metadata.

    Raises:
        PubMedServiceError if PubMed is unavailable or returns errors.
    """
    logger.info(
        f"PubMed search: query='{request.query}', "
        f"page={request.page}, max_results={request.max_results}"
    )

    # Step 1: ESearch — get matching PMIDs
    params = _build_esearch_params(request)
    pmids, total_count = await _esearch(params)

    if not pmids:
        logger.info(f"No results for query: '{request.query}'")
        return SearchResponse(
            articles=[],
            total_results=total_count,
            page=request.page,
            max_results=request.max_results,
            query=request.query,
        )

    # Step 2: EFetch — get full article details
    articles = await _efetch(pmids)

    return SearchResponse(
        articles=articles,
        total_results=total_count,
        page=request.page,
        max_results=request.max_results,
        query=request.query,
    )


async def fetch_article_by_pmid(pmid: str) -> PubMedArticle | None:
    """
    Fetch a single article by its PMID.

    Useful when the user clicks on an article to see its full details,
    or when we need to refresh article data.

    Args:
        pmid: The PubMed ID to fetch.

    Returns:
        PubMedArticle if found, None if not.

    Raises:
        PubMedServiceError on network/service failures.
    """
    articles = await _efetch([pmid])
    return articles[0] if articles else None

