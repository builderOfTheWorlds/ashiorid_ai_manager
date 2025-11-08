"""HTTP client for LLM Proxy Service."""

import httpx
import time
from typing import Dict, Any

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger
from shared.common_types import LLMRequest

logger = get_logger(__name__)


class LLMClient:
    """Client for LLM Proxy Service."""

    def __init__(self, config: Dict):
        service_config = config.get("services", {}).get("llm_proxy", {})
        self.base_url = service_config.get("url", "http://llm-proxy:8001")
        self.timeout = service_config.get("timeout", 30)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def generate(self, request: LLMRequest) -> Dict[str, Any]:
        """Generate LLM response."""
        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"LLM request failed: {e}")
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
