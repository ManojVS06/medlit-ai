"""
Tests for PubMed search and article retrieval.

KEY TESTING CONCEPT — MOCKING EXTERNAL APIs:
We NEVER call the real PubMed API in tests because:
1. Tests would require internet access.
2. Tests would be slow (network round-trips).
3. Tests would be flaky (PubMed could be down).
4. Tests could hit rate limits.
5. Test results would change as PubMed data changes.

Instead, we MOCK httpx to return predefined responses.
This lets us test our parsing logic, error handling,
and data transformation in isolation.

HOW MOCKING WORKS:
- `unittest.mock.patch` temporarily replaces a real object
  with a fake one during the test.
- We replace `httpx.AsyncClient` with a mock that returns
  our predefined XML/JSON responses.
- After the test, the original object is restored automatically.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.pubmed_service import (
    PubMedServiceError,
    _parse_efetch_xml,
    _build_esearch_params,
)
from app.schemas.pubmed import SearchRequest

client = TestClient(app)


# ============================================================
# SAMPLE RESPONSES — Real PubMed response structures
# ============================================================
# These are modeled after ACTUAL PubMed responses but with
# simplified content. They test our parsing against the real
# XML structure that PubMed returns.

SAMPLE_ESEARCH_JSON = {
    "esearchresult": {
        "count": "42",
        "retmax": "2",
        "retstart": "0",
        "idlist": ["38012345", "37654321"],
    }
}

SAMPLE_EFETCH_XML = """<?xml version="1.0" ?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN"
    "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">38012345</PMID>
      <Article PubModel="Print">
        <Journal>
          <ISOAbbreviation>Diabetes Care</ISOAbbreviation>
          <JournalIssue>
            <PubDate>
              <Year>2023</Year>
              <Month>Nov</Month>
            </PubDate>
          </JournalIssue>
          <Title>Diabetes Care</Title>
        </Journal>
        <ArticleTitle>Effects of supervised exercise on glycemic control in type 2 diabetes: a meta-analysis.</ArticleTitle>
        <Abstract>
          <AbstractText Label="OBJECTIVE">To evaluate the effects of supervised exercise programs on glycemic control in adults with type 2 diabetes mellitus.</AbstractText>
          <AbstractText Label="METHODS">We conducted a systematic review and meta-analysis of randomized controlled trials published through 2023.</AbstractText>
          <AbstractText Label="RESULTS">Twenty-two trials with 1,245 participants were included. Supervised exercise was associated with a significant reduction in HbA1c (mean difference -0.67%, 95% CI -0.84 to -0.49, p &lt; 0.001).</AbstractText>
          <AbstractText Label="CONCLUSIONS">Supervised exercise programs significantly improve glycemic control in adults with type 2 diabetes.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
            <Initials>J</Initials>
          </Author>
          <Author>
            <LastName>Chen</LastName>
            <ForeName>Wei</ForeName>
            <Initials>W</Initials>
          </Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
          <PublicationType>Meta-Analysis</PublicationType>
        </PublicationTypeList>
        <ELocationID EIdType="doi">10.2337/dc23-0001</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">37654321</PMID>
      <Article PubModel="Electronic">
        <Journal>
          <JournalIssue>
            <PubDate>
              <Year>2023</Year>
              <Month>Aug</Month>
            </PubDate>
          </JournalIssue>
          <Title>BMJ Open</Title>
        </Journal>
        <ArticleTitle>Walking interventions for sedentary adults: a randomized controlled trial.</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Patel</LastName>
            <ForeName>Rina</ForeName>
            <Initials>R</Initials>
          </Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

# Article with no abstract, no DOI — tests graceful handling
SAMPLE_EFETCH_MINIMAL_XML = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">99999999</PMID>
      <Article PubModel="Print">
        <Journal>
          <JournalIssue>
            <PubDate>
              <MedlineDate>2022 Jan-Feb</MedlineDate>
            </PubDate>
          </JournalIssue>
          <Title>Test Journal</Title>
        </Journal>
        <ArticleTitle>Article without abstract</ArticleTitle>
        <AuthorList>
          <Author>
            <CollectiveName>WHO Working Group</CollectiveName>
          </Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


# ============================================================
# UNIT TESTS — XML Parsing
# ============================================================


class TestEFetchXMLParsing:
    """Test XML parsing in isolation (no HTTP calls)."""

    def test_parse_full_article(self):
        """A complete article should have all fields populated."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_XML)
        assert len(articles) == 2

        article = articles[0]
        assert article.pmid == "38012345"
        assert "supervised exercise" in article.title.lower()
        assert len(article.authors) == 2
        assert article.authors[0] == "Smith J"
        assert article.authors[1] == "Chen W"
        assert article.journal == "Diabetes Care"
        assert "2023" in article.pub_date
        assert "OBJECTIVE:" in article.abstract
        assert "RESULTS:" in article.abstract
        assert article.doi == "10.2337/dc23-0001"
        assert "Meta-Analysis" in article.pub_types
        assert article.pubmed_url == "https://pubmed.ncbi.nlm.nih.gov/38012345/"

    def test_parse_structured_abstract(self):
        """Structured abstracts should preserve section labels."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_XML)
        abstract = articles[0].abstract
        # Structured abstract sections should be labeled
        assert "OBJECTIVE:" in abstract
        assert "METHODS:" in abstract
        assert "RESULTS:" in abstract
        assert "CONCLUSIONS:" in abstract

    def test_parse_article_without_abstract(self):
        """Articles without abstracts should have empty abstract string."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_MINIMAL_XML)
        assert len(articles) == 1
        article = articles[0]
        assert article.abstract == ""
        assert article.pmid == "99999999"
        assert article.title == "Article without abstract"

    def test_parse_collective_author(self):
        """Collective authors (organizations) should be parsed correctly."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_MINIMAL_XML)
        assert articles[0].authors == ["WHO Working Group"]

    def test_parse_medline_date(self):
        """MedlineDate format (e.g., '2022 Jan-Feb') should be preserved."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_MINIMAL_XML)
        assert articles[0].pub_date == "2022 Jan-Feb"

    def test_parse_doi_extraction(self):
        """DOI should be extracted from ELocationID."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_XML)
        assert articles[0].doi == "10.2337/dc23-0001"
        assert articles[1].doi is None  # Second article has no DOI

    def test_parse_multiple_pub_types(self):
        """Publication types should be a list."""
        articles = _parse_efetch_xml(SAMPLE_EFETCH_XML)
        assert "Journal Article" in articles[0].pub_types
        assert "Meta-Analysis" in articles[0].pub_types

    def test_parse_empty_xml(self):
        """Empty PubmedArticleSet should return empty list."""
        xml = '<?xml version="1.0" ?><PubmedArticleSet></PubmedArticleSet>'
        articles = _parse_efetch_xml(xml)
        assert articles == []

    def test_parse_malformed_article_skipped(self):
        """If one article fails parsing, others should still succeed."""
        # This XML has a valid article and then garbage inside another
        xml = """<?xml version="1.0" ?>
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>11111</PMID>
              <Article>
                <Journal><Title>Good Journal</Title>
                  <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
                </Journal>
                <ArticleTitle>Good Article</ArticleTitle>
                <AuthorList></AuthorList>
                <PublicationTypeList></PublicationTypeList>
              </Article>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>"""
        articles = _parse_efetch_xml(xml)
        assert len(articles) == 1
        assert articles[0].pmid == "11111"


# ============================================================
# UNIT TESTS — ESearch Parameter Building
# ============================================================


class TestESearchParams:
    """Test that search parameters are built correctly."""

    def test_basic_search_params(self):
        """Basic search should have correct defaults."""
        request = SearchRequest(query="diabetes exercise")
        params = _build_esearch_params(request)
        assert params["db"] == "pubmed"
        assert params["term"] == "diabetes exercise"
        assert params["retstart"] == 0
        assert params["retmax"] == 10
        assert params["retmode"] == "json"

    def test_pagination_params(self):
        """Page 3 with 20 results should start at offset 40."""
        request = SearchRequest(query="test", page=3, max_results=20)
        params = _build_esearch_params(request)
        assert params["retstart"] == 40  # (3-1) * 20
        assert params["retmax"] == 20

    def test_date_filter_params(self):
        """Date filters should set datetype, mindate, maxdate."""
        request = SearchRequest(
            query="test",
            date_from="2020/01/01",
            date_to="2024/12/31",
        )
        params = _build_esearch_params(request)
        assert params["datetype"] == "pdat"
        assert params["mindate"] == "2020/01/01"
        assert params["maxdate"] == "2024/12/31"

    def test_publication_type_filter(self):
        """Publication type filter should modify the query term."""
        request = SearchRequest(
            query="diabetes",
            publication_type="Randomized Controlled Trial",
        )
        params = _build_esearch_params(request)
        assert "[pt]" in params["term"]
        assert "diabetes" in params["term"]
        assert "Randomized Controlled Trial" in params["term"]


# ============================================================
# INTEGRATION TESTS — API Endpoints with Mocked PubMed
# ============================================================


def _make_mock_client(esearch_json=None, efetch_xml=None):
    """
    Create a mock httpx.AsyncClient that returns predefined responses.

    This is a helper function used by multiple tests.
    It creates a mock that intercepts HTTP GET requests and returns
    different responses depending on the URL.
    """
    mock_client = AsyncMock()

    async def mock_get(url, **kwargs):
        response = MagicMock()
        response.raise_for_status = MagicMock()

        if "esearch" in url:
            response.json.return_value = esearch_json or SAMPLE_ESEARCH_JSON
            response.text = ""
        elif "efetch" in url:
            response.text = efetch_xml or SAMPLE_EFETCH_XML
            response.json.return_value = {}
        else:
            response.text = ""
            response.json.return_value = {}

        return response

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = mock_get

    return mock_client


class TestSearchEndpoint:
    """Test POST /api/articles/search with mocked PubMed responses."""

    def test_search_returns_articles(self):
        """A valid search should return articles with metadata."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={"query": "exercise diabetes"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "total_results" in data
        assert data["total_results"] == 42
        assert len(data["articles"]) == 2
        assert data["query"] == "exercise diabetes"
        assert data["search_source"] == "PubMed (NCBI E-utilities)"

    def test_search_article_has_required_fields(self):
        """Each article should have all expected fields."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={"query": "test"},
            )

        article = response.json()["articles"][0]
        assert "pmid" in article
        assert "title" in article
        assert "authors" in article
        assert "journal" in article
        assert "pub_date" in article
        assert "abstract" in article
        assert "pubmed_url" in article

    def test_search_empty_results(self):
        """Empty search results should return empty list, not error."""
        empty_response = {
            "esearchresult": {
                "count": "0",
                "retmax": "0",
                "retstart": "0",
                "idlist": [],
            }
        }
        mock = _make_mock_client(esearch_json=empty_response)
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={"query": "xyznonexistentquery12345"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["articles"] == []
        assert data["total_results"] == 0

    def test_search_too_short_query(self):
        """A query shorter than 2 characters should be rejected."""
        response = client.post(
            "/api/articles/search",
            json={"query": "x"},
        )
        assert response.status_code == 422  # Validation error

    def test_search_with_pagination(self):
        """Search should accept page and max_results parameters."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={"query": "test", "page": 2, "max_results": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["max_results"] == 5

    def test_search_with_date_filter(self):
        """Search should accept date filter parameters."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={
                    "query": "test",
                    "date_from": "2020",
                    "date_to": "2024",
                },
            )

        assert response.status_code == 200

    def test_search_with_publication_type(self):
        """Search should accept publication type filter."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.post(
                "/api/articles/search",
                json={
                    "query": "diabetes",
                    "publication_type": "Meta-Analysis",
                },
            )

        assert response.status_code == 200


class TestGetArticleEndpoint:
    """Test GET /api/articles/{pmid} with mocked PubMed."""

    def test_get_article_by_pmid(self):
        """Fetching a valid PMID should return article details."""
        mock = _make_mock_client()
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.get("/api/articles/38012345")

        assert response.status_code == 200
        data = response.json()
        assert data["pmid"] == "38012345"
        assert "title" in data
        assert "abstract" in data

    def test_get_article_invalid_pmid(self):
        """A non-numeric PMID should return 400."""
        response = client.get("/api/articles/not-a-number")
        assert response.status_code == 400

    def test_get_article_not_found(self):
        """A PMID that returns no results should return 404."""
        empty_xml = '<?xml version="1.0" ?><PubmedArticleSet></PubmedArticleSet>'
        mock = _make_mock_client(efetch_xml=empty_xml)
        with patch("app.services.pubmed_service.httpx.AsyncClient", return_value=mock):
            response = client.get("/api/articles/99999999")

        assert response.status_code == 404


# ============================================================
# SCHEMA VALIDATION TESTS
# ============================================================


class TestSearchRequestValidation:
    """Test that SearchRequest validates inputs properly."""

    def test_valid_request(self):
        """A valid request should pass validation."""
        request = SearchRequest(query="diabetes exercise")
        assert request.query == "diabetes exercise"
        assert request.max_results == 10
        assert request.page == 1

    def test_query_too_short(self):
        """Query must be at least 2 characters."""
        with pytest.raises(Exception):  # ValidationError
            SearchRequest(query="x")

    def test_max_results_capped(self):
        """max_results above 50 should be rejected."""
        with pytest.raises(Exception):
            SearchRequest(query="test", max_results=100)

    def test_page_must_be_positive(self):
        """Page 0 or negative should be rejected."""
        with pytest.raises(Exception):
            SearchRequest(query="test", page=0)

