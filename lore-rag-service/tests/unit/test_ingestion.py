"""
Unit tests for ingestion service.
"""

import pytest
from shared.common_types import DocumentChunk


class TestIngestion:
    """Test ingestion functionality."""

    def test_document_chunk_creation(self):
        """Test creating a document chunk."""
        chunk = DocumentChunk(
            text="This is a test chunk",
            source="test_source",
            metadata={"key": "value"},
        )

        assert chunk.text == "This is a test chunk"
        assert chunk.source == "test_source"
        assert chunk.metadata["key"] == "value"

    def test_document_chunk_validation(self):
        """Test document chunk validation."""
        # Valid chunk
        chunk = DocumentChunk(
            text="Test",
            source="source",
        )
        assert chunk.metadata is None

        # Test with metadata
        chunk_with_meta = DocumentChunk(
            text="Test",
            source="source",
            metadata={"index": 0},
        )
        assert chunk_with_meta.metadata["index"] == 0
