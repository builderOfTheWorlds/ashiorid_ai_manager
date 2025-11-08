"""HTTP client for Character Agent Service."""

import httpx
import time
from typing import Dict, Any, List

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class CharacterClient:
    """Client for Character Agent Service."""

    def __init__(self, config: Dict):
        service_config = config.get("services", {}).get("character_agent", {})
        self.base_url = service_config.get("url", "http://character-agent:8003")
        self.timeout = service_config.get("timeout", 20)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def list_characters(self) -> List[Dict[str, Any]]:
        """List all available characters."""
        try:
            response = await self.client.get("/characters")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to list characters: {e}")
            raise

    async def chat(
        self,
        character_name: str,
        message: str,
        context: List[str] = None,
    ) -> Dict[str, Any]:
        """Chat with a character."""
        try:
            payload = {
                "character_name": character_name,
                "message": message,
                "context": context or [],
            }

            response = await self.client.post(
                f"/characters/{character_name}/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to chat with character {character_name}: {e}")
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
