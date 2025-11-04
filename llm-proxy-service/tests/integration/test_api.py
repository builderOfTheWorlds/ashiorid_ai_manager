"""
Integration tests for LLM Proxy API.
"""

import pytest
from httpx import AsyncClient
from src.main import app


class TestLLMProxyAPI:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "llm-proxy-service"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "llm-proxy-service"
            assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_providers_list(self):
        """Test listing providers."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/providers")
            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert "default_provider" in data

    # Note: Actual LLM request testing would require running providers
    # These tests are marked as skip by default
    @pytest.mark.skip(reason="Requires running LLM providers")
    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test chat completion endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "provider": "ollama",
                "model": "llama3.2:1b",
                "temperature": 0.7,
            }
            response = await client.post("/v1/chat/completions", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data["provider"] == "ollama"
