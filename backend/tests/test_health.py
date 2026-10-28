"""
Test the health check endpoint.

This is our first test! It verifies the most basic thing:
"Does the server start and respond to requests?"

KEY CONCEPTS:
- `TestClient` is a fake HTTP client that sends requests to our FastAPI app
  WITHOUT actually starting a server. It simulates browser requests in-memory.
- Each test function starts with `test_` so pytest discovers it automatically.
- `assert` checks that a condition is true. If not, the test fails.
"""

from fastapi.testclient import TestClient

from app.main import app

# Create a test client — this is like having a browser that talks directly
# to the app without needing a running server
client = TestClient(app)


def test_health_check_returns_200():
    """The health endpoint should return HTTP 200 (OK)."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_returns_correct_body():
    """The health endpoint should return our service info."""
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "medlit-ai"
    assert "version" in data
    assert "llm_provider" in data


def test_health_check_shows_mock_provider_by_default():
    """In development, the default LLM provider should be 'mock'."""
    response = client.get("/health")
    data = response.json()
    assert data["llm_provider"] == "mock"
