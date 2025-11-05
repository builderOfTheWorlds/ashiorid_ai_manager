"""Integration tests for Character Agent API."""

import pytest
from httpx import AsyncClient
from src.main import app


class TestCharacterAgentAPI:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_list_characters(self):
        """Test listing characters."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/characters")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
