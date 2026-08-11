"""
DocuMind AI — Jules REST API Unit Tests
Tests the JulesClient service and FastAPI admin endpoints with mocked HTTP responses.
"""

from unittest.mock import AsyncMock, patch
import pytest
import uuid
from httpx import AsyncClient, ASGITransport, Response
from app.main import app
from app.services.jules import JulesClient, JulesAPIError
from app.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_jules_client_unconfigured():
    """Client raises JulesAPIError when api_key is empty/None."""
    with patch("app.services.jules.settings.JULES_API_KEY", None):
        client = JulesClient(api_key=None)
        with pytest.raises(JulesAPIError) as exc_info:
            await client.list_sources()
        assert exc_info.value.status_code == 400
        assert "Jules API key is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_jules_client_list_sources():
    """Client correctly fetches sources from Jules REST API."""
    mock_resp = Response(
        200,
        json={
            "sources": [
                {
                    "name": "sources/github/bobalover/boba",
                    "id": "github/bobalover/boba",
                    "githubRepo": {"owner": "bobalover", "repo": "boba"},
                }
            ]
        },
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        client = JulesClient(api_key="test_key_123")
        sources = await client.list_sources()
        assert "sources" in sources
        assert len(sources["sources"]) == 1
        assert sources["sources"][0]["id"] == "github/bobalover/boba"


@pytest.mark.asyncio
async def test_jules_client_create_session():
    """Client correctly creates a new coding session."""
    mock_resp = Response(
        201,
        json={
            "name": "sessions/12345",
            "id": "12345",
            "title": "Fix Bug",
            "prompt": "Fix RAG retrieval bug",
            "state": "ACTIVE",
        },
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        client = JulesClient(api_key="test_key_123")
        session = await client.create_session(
            prompt="Fix RAG retrieval bug",
            source="sources/github/amanydvvv/DocuMind_AI",
            title="Fix Bug",
        )
        assert session["id"] == "12345"
        assert session["title"] == "Fix Bug"


@pytest.mark.asyncio
async def test_jules_client_get_session():
    """Client fetches session state and outputs."""
    mock_resp = Response(
        200,
        json={
            "name": "sessions/12345",
            "id": "12345",
            "outputs": [
                {
                    "pullRequest": {
                        "url": "https://github.com/amanydvvv/DocuMind_AI/pull/1",
                        "title": "Fix RAG retrieval bug",
                    }
                }
            ],
        },
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        client = JulesClient(api_key="test_key_123")
        session = await client.get_session("12345")
        assert session["id"] == "12345"
        assert session["outputs"][0]["pullRequest"]["url"] == "https://github.com/amanydvvv/DocuMind_AI/pull/1"


@pytest.mark.asyncio
async def test_jules_router_unauthorized():
    """Router rejects unauthenticated requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        response = await test_client.get("/api/admin/jules/sources")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_jules_router_list_sources():
    """Router returns sources list for authenticated admin user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
        password = "password1234"
        res = await test_client.post("/api/auth/signup", json={"email": email, "password": password})
        assert res.status_code == 201
        token = res.json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})

        mock_resp = Response(200, json={"sources": []})
        with patch("app.services.jules.settings.JULES_API_KEY", "test_key_123"):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                response = await test_client.get("/api/admin/jules/sources")
                assert response.status_code == 200
                assert response.json()["sources"] == []
