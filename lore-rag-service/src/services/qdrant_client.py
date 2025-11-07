"""
Qdrant client service for vector database operations.
"""

from typing import Dict, List, Optional

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class QdrantService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self, config: Dict):
        self.config = config
        qdrant_config = config.get("qdrant", {})

        self.host = qdrant_config.get("host", "qdrant")
        self.port = qdrant_config.get("port", 6333)
        self.use_grpc = qdrant_config.get("use_grpc", False)
        self.timeout = qdrant_config.get("timeout", 30)

        # Collection settings
        self.default_collection = qdrant_config.get("collections", {}).get("default", "lore")
        self.vector_size = qdrant_config.get("collections", {}).get("vector_size", 768)
        self.distance = qdrant_config.get("collections", {}).get("distance", "Cosine")

        self.client: Optional[AsyncQdrantClient] = None

    async def initialize(self):
        """Initialize Qdrant client."""
        try:
            # Create async client
            if self.use_grpc:
                url = f"http://{self.host}:{self.config.get('qdrant', {}).get('grpc_port', 6334)}"
                self.client = AsyncQdrantClient(
                    url=url,
                    prefer_grpc=True,
                    timeout=self.timeout,
                )
            else:
                url = f"http://{self.host}:{self.port}"
                self.client = AsyncQdrantClient(
                    url=url,
                    timeout=self.timeout,
                )

            logger.info(f"Qdrant client initialized: {url}")

            # Ensure default collection exists
            await self.ensure_collection(self.default_collection)

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    async def close(self):
        """Close Qdrant client."""
        if self.client:
            await self.client.close()
            logger.info("Qdrant client closed")

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            if not self.client:
                return False

            # Try to list collections as health check
            await self.client.get_collections()
            return True

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def ensure_collection(self, collection_name: str, vector_size: Optional[int] = None):
        """Ensure a collection exists, create if it doesn't."""
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if collection_name not in collection_names:
                logger.info(f"Creating collection: {collection_name}")
                await self.create_collection(collection_name, vector_size)
            else:
                logger.debug(f"Collection already exists: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def create_collection(self, collection_name: str, vector_size: Optional[int] = None):
        """Create a new collection."""
        size = vector_size or self.vector_size

        # Map distance string to Distance enum
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclid": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        distance = distance_map.get(self.distance, Distance.COSINE)

        try:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=size,
                    distance=distance,
                ),
            )

            logger.info(
                f"Collection created: {collection_name} "
                f"(size={size}, distance={self.distance})"
            )

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    async def delete_collection(self, collection_name: str):
        """Delete a collection."""
        try:
            await self.client.delete_collection(collection_name)
            logger.info(f"Collection deleted: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    async def list_collections(self) -> List[Dict]:
        """List all collections."""
        try:
            collections = await self.client.get_collections()

            result = []
            for collection in collections.collections:
                result.append({
                    "name": collection.name,
                })

            return result

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get information about a collection."""
        try:
            info = await self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "vector_size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    async def upsert_points(
        self,
        collection_name: str,
        points: List[PointStruct],
    ):
        """Upsert points into a collection."""
        try:
            await self.client.upsert(
                collection_name=collection_name,
                points=points,
            )

            logger.debug(f"Upserted {len(points)} points to {collection_name}")

        except Exception as e:
            logger.error(f"Failed to upsert points: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Filter] = None,
    ) -> List[Dict]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            query_filter: Optional filter for metadata

        Returns:
            List of search results with scores and payloads
        """
        try:
            results = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            search_results = []
            for result in results:
                search_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                })

            logger.debug(
                f"Search returned {len(search_results)} results from {collection_name}"
            )

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def count_points(self, collection_name: str) -> int:
        """Count points in a collection."""
        try:
            info = await self.get_collection_info(collection_name)
            return info.get("points_count", 0) if info else 0

        except Exception as e:
            logger.error(f"Failed to count points: {e}")
            return 0
