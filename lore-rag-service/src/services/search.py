"""
Semantic search service.
"""

from typing import Dict

import sys
sys.path.append('../..')
from shared.common_types import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SearchResult,
)
from shared.logging_config import get_logger

logger = get_logger(__name__)


class SearchService:
    """Service for semantic search over vector database."""

    def __init__(self, config: Dict, qdrant_service, embedding_service):
        self.config = config
        self.qdrant_service = qdrant_service
        self.embedding_service = embedding_service

        search_config = config.get("search", {})
        self.default_limit = search_config.get("default_limit", 5)
        self.max_limit = search_config.get("max_limit", 100)
        self.default_threshold = search_config.get("default_threshold", 0.7)

    async def search(self, search_request: SemanticSearchRequest) -> SemanticSearchResponse:
        """
        Perform semantic search.

        Args:
            search_request: Search request with query and filters

        Returns:
            Search response with results
        """
        try:
            import time
            start_time = time.time()

            # Validate and normalize parameters
            limit = min(search_request.limit, self.max_limit)
            threshold = search_request.threshold

            logger.debug(
                f"Search: query='{search_request.query}', "
                f"collection={search_request.collection}, "
                f"limit={limit}, threshold={threshold}"
            )

            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(
                search_request.query
            )

            # Perform vector search
            results = await self.qdrant_service.search(
                collection_name=search_request.collection,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=threshold,
            )

            # Convert to search results
            search_results = []
            for result in results:
                payload = result.get("payload", {})

                search_results.append(SearchResult(
                    text=payload.get("text", ""),
                    score=result.get("score", 0.0),
                    source=payload.get("source", "unknown"),
                    metadata=payload.get("metadata"),
                ))

            latency_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Search completed: {len(search_results)} results, "
                f"latency_ms={latency_ms:.2f}"
            )

            return SemanticSearchResponse(
                results=search_results,
                query=search_request.query,
                total_results=len(search_results),
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise
