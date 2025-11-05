"""
Lore context service for fetching relevant lore from lore-rag-service.
"""

from typing import Dict, List

import httpx

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class LoreContextService:
    """Service for fetching lore context."""

    def __init__(self, config: Dict):
        self.config = config
        lore_config = config.get("services", {}).get("lore_rag", {})

        self.url = lore_config.get("url", "http://lore-rag:8002")
        self.timeout = lore_config.get("timeout", 30)

        self.client = httpx.AsyncClient(base_url=self.url, timeout=self.timeout)

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    async def health_check(self) -> bool:
        """Check lore RAG health."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Lore RAG health check failed: {e}")
            return False

    async def get_context(
        self,
        query: str,
        collection: str = "lore",
        limit: int = 3,
        threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Get relevant lore context.

        Args:
            query: Search query
            collection: Lore collection
            limit: Max results
            threshold: Similarity threshold

        Returns:
            List of lore results
        """
        try:
            response = await self.client.post(
                "/search",
                json={
                    "query": query,
                    "collection": collection,
                    "limit": limit,
                    "threshold": threshold,
                },
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            return [
                {
                    "text": r.get("text", ""),
                    "source": r.get("source", "unknown"),
                    "score": r.get("score", 0.0),
                }
                for r in results
            ]

        except httpx.HTTPError as e:
            logger.error(f"Lore context request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching lore context: {e}")
            return []
