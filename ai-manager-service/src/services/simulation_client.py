"""HTTP client for Simulation Engine Service."""

import httpx
import time
from typing import Dict, Any, List

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class SimulationClient:
    """Client for Simulation Engine Service."""

    def __init__(self, config: Dict):
        service_config = config.get("services", {}).get("simulation_engine", {})
        self.base_url = service_config.get("url", "http://simulation-engine:8004")
        self.timeout = service_config.get("timeout", 10)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def get_status(self) -> Dict[str, Any]:
        """Get simulation status."""
        try:
            response = await self.client.get("/simulation/status")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get simulation status: {e}")
            raise

    async def start_simulation(self, num_agents: int = 100) -> Dict[str, Any]:
        """Start simulation."""
        try:
            response = await self.client.post(
                "/simulation/start",
                params={"num_agents": num_agents},
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to start simulation: {e}")
            raise

    async def stop_simulation(self) -> Dict[str, Any]:
        """Stop simulation."""
        try:
            response = await self.client.post("/simulation/stop")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to stop simulation: {e}")
            raise

    async def get_agents(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get agents."""
        try:
            response = await self.client.get(
                "/agents",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get agents: {e}")
            raise

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent simulation events."""
        try:
            response = await self.client.get(
                "/simulation/events",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get events: {e}")
            raise

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        start = time.time()
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
