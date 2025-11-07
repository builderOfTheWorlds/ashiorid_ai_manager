"""Integration tests for Simulation Engine API."""

import pytest
from httpx import AsyncClient
from src.main import app


class TestSimulationEngineAPI:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_status_before_start(self):
        """Test getting status before simulation starts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/simulation/status")
            assert response.status_code == 200
            data = response.json()
            assert "tick" in data
            assert "active_agents" in data
            assert data["ticks_per_second"] == 0

    @pytest.mark.asyncio
    async def test_start_simulation(self):
        """Test starting simulation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/simulation/start", params={"num_agents": 10})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_get_agents(self):
        """Test listing agents."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/agents")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            assert "simulation_agent_count" in response.text
            assert "simulation_tick_count" in response.text
