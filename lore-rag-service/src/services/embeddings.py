"""
Embedding service using Ollama.
"""

from typing import Dict, List

import httpx

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Ollama."""

    def __init__(self, config: Dict):
        self.config = config
        ollama_config = config.get("ollama", {})

        self.host = ollama_config.get("host", "http://localhost:11434")
        self.model = ollama_config.get("model", "nomic-embed-text")
        self.timeout = ollama_config.get("timeout", 60)
        self.batch_size = ollama_config.get("batch_size", 32)

        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize embedding service."""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.host,
                timeout=self.timeout,
            )

            logger.info(f"Embedding service initialized: {self.host}, model={self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.info("Embedding service closed")

    async def health_check(self) -> bool:
        """Check if Ollama is healthy."""
        try:
            if not self.client:
                return False

            response = await self.client.get("/api/tags")
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        try:
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding")
            if not embedding:
                raise ValueError("No embedding returned from Ollama")

            logger.debug(f"Generated embedding: dim={len(embedding)}")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            logger.debug(f"Processing batch {i // self.batch_size + 1}: {len(batch)} texts")

            # Generate embeddings for batch
            batch_embeddings = []
            for text in batch:
                embedding = await self.generate_embedding(text)
                batch_embeddings.append(embedding)

            embeddings.extend(batch_embeddings)

        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings

    async def get_model_info(self) -> Dict:
        """Get information about the embedding model."""
        try:
            response = await self.client.get("/api/show", params={"name": self.model})
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {}
