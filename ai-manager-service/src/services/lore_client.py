"""HTTP client for Lore RAG Service."""

import httpx
import time
from typing import Dict, Any, List

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class LoreClient:
    """Client for Lore RAG Service."""

    def __init__(self, config: Dict):
        service_config = config.get("services", {}).get("lore_rag", {})
        self.base_url = service_config.get("url", "http://lore-rag:8002")
        self.timeout = service_config.get("timeout", 15)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def search(
        self,
        query: str,
        collection_name: str = "lore",
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Search lore database."""
        try:
            payload = {
                "query": query,
                "collection_name": collection_name,
                "limit": limit,
                "score_threshold": score_threshold,
            }

            response = await self.client.post("/search", json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Lore search failed: {e}")
            raise

    async def ingest_text(
        self,
        text: str,
        source: str,
        collection_name: str = "lore",
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Ingest text into lore database."""
        try:
            payload = {
                "text": text,
                "source": source,
                "collection_name": collection_name,
                "metadata": metadata or {},
            }

            response = await self.client.post("/ingest", json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Lore ingestion failed: {e}")
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
