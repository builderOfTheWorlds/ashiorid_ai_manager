"""
Document ingestion service.
"""

import uuid
from typing import Dict, List

from qdrant_client.models import PointStruct
import tiktoken

import sys
sys.path.append('../..')
from shared.common_types import DocumentChunk
from shared.logging_config import get_logger

logger = get_logger(__name__)


class IngestionService:
    """Service for ingesting documents into vector database."""

    def __init__(self, config: Dict, qdrant_service, embedding_service):
        self.config = config
        self.qdrant_service = qdrant_service
        self.embedding_service = embedding_service

        text_config = config.get("text_processing", {})
        self.chunk_size = text_config.get("chunk_size", 512)
        self.chunk_overlap = text_config.get("chunk_overlap", 50)
        self.min_chunk_size = text_config.get("min_chunk_size", 100)

        # Initialize tokenizer for chunking
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken, using simple tokenizer: {e}")
            self.tokenizer = None

    def _chunk_text(self, text: str, source: str) -> List[DocumentChunk]:
        """
        Split text into chunks.

        Args:
            text: Input text
            source: Source identifier

        Returns:
            List of document chunks
        """
        chunks = []

        if self.tokenizer:
            # Token-based chunking
            tokens = self.tokenizer.encode(text)

            for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                chunk_tokens = tokens[i:i + self.chunk_size]

                if len(chunk_tokens) >= self.min_chunk_size:
                    chunk_text = self.tokenizer.decode(chunk_tokens)

                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        source=source,
                        metadata={
                            "chunk_index": len(chunks),
                            "token_count": len(chunk_tokens),
                        },
                    ))
        else:
            # Simple word-based chunking
            words = text.split()
            words_per_chunk = self.chunk_size * 4  # Rough estimate: 1 token ≈ 4 words

            for i in range(0, len(words), words_per_chunk - self.chunk_overlap):
                chunk_words = words[i:i + words_per_chunk]

                if len(chunk_words) >= self.min_chunk_size:
                    chunk_text = " ".join(chunk_words)

                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        source=source,
                        metadata={
                            "chunk_index": len(chunks),
                            "word_count": len(chunk_words),
                        },
                    ))

        logger.debug(f"Chunked text into {len(chunks)} chunks")
        return chunks

    async def ingest(
        self,
        documents: List[DocumentChunk],
        collection: str,
    ) -> Dict:
        """
        Ingest documents into a collection.

        Args:
            documents: List of document chunks
            collection: Target collection name

        Returns:
            Ingestion results
        """
        try:
            # Ensure collection exists
            await self.qdrant_service.ensure_collection(collection)

            # Extract texts for embedding
            texts = [doc.text for doc in documents]

            logger.info(f"Generating embeddings for {len(texts)} documents")

            # Generate embeddings
            embeddings = await self.embedding_service.generate_embeddings(texts)

            if len(embeddings) != len(documents):
                raise ValueError(
                    f"Embedding count mismatch: {len(embeddings)} != {len(documents)}"
                )

            # Create points for Qdrant
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point_id = str(uuid.uuid4())

                payload = {
                    "text": doc.text,
                    "source": doc.source,
                    "metadata": doc.metadata or {},
                }

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )

                points.append(point)

            # Upsert points
            logger.info(f"Upserting {len(points)} points to collection '{collection}'")
            await self.qdrant_service.upsert_points(collection, points)

            return {
                "status": "success",
                "documents_ingested": len(documents),
                "embeddings_generated": len(embeddings),
                "points_upserted": len(points),
            }

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise

    async def ingest_text(
        self,
        text: str,
        source: str,
        collection: str,
    ) -> Dict:
        """
        Ingest a single text document.

        Args:
            text: Input text
            source: Source identifier
            collection: Target collection

        Returns:
            Ingestion results
        """
        try:
            # Chunk the text
            chunks = self._chunk_text(text, source)

            logger.info(f"Ingesting {len(chunks)} chunks from '{source}'")

            # Ingest chunks
            result = await self.ingest(chunks, collection)

            result["chunks_created"] = len(chunks)

            return result

        except Exception as e:
            logger.error(f"Text ingestion failed: {e}", exc_info=True)
            raise
