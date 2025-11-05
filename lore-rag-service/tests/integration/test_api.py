"""
Integration tests for Lore RAG API.
"""

import pytest
from httpx import AsyncClient
from src.main import app


class TestLoreRAGAPI:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "lore-rag-service"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "lore-rag-service"
            assert "endpoints" in data

    # Note: Actual search/ingestion testing requires running Qdrant and Ollama
    @pytest.mark.skip(reason="Requires running Qdrant and Ollama")
    @pytest.mark.asyncio
    async def test_search(self):
        """Test semantic search endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "What is a wizard?",
                "collection": "lore",
                "limit": 5,
            }
            response = await client.post("/search", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "query" in data

    @pytest.mark.skip(reason="Requires running Qdrant and Ollama")
    @pytest.mark.asyncio
    async def test_ingest_documents(self):
        """Test document ingestion endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            documents = [
                {
                    "text": "Gandalf is a wizard.",
                    "source": "test",
                }
            ]
            response = await client.post("/ingest", json=documents)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
