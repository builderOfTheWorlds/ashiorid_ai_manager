"""Integration tests for AI Manager API."""

import pytest
from httpx import AsyncClient
from src.main import app


class TestAIManagerAPI:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "AI Manager"
            assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            assert "ai_manager_requests_total" in response.text
