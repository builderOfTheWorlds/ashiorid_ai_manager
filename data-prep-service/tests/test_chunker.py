"""
Tests for text chunking service.
"""

import sys
sys.path.append('..')

from src.services.chunker import ChunkerService


def test_chunker_by_tokens():
    """Test token-based chunking."""
    config = {
        'processing': {
            'chunking': {
                'strategy': 'token_count',
                'chunk_size_tokens': 100,
                'chunk_overlap_tokens': 20,
                'min_chunk_size_tokens': 10,
            }
        }
    }

    chunker = ChunkerService(config)

    # Create a long text
    text = " ".join([f"This is sentence number {i}." for i in range(100)])

    chunks = chunker.chunk_by_tokens(text, chunk_size=100, overlap=20, min_size=10)

    assert len(chunks) > 0, "Should create chunks"
    assert all(isinstance(chunk, str) for chunk in chunks), "Chunks should be strings"

    # Check that chunks are not too large
    for chunk in chunks:
        token_count = chunker.count_tokens(chunk)
        assert token_count <= 150, f"Chunk too large: {token_count} tokens"

    print(f"✓ Token chunking tests passed (created {len(chunks)} chunks)")


def test_chapter_detection():
    """Test chapter boundary detection."""
    config = {
        'processing': {
            'chunking': {
                'strategy': 'chapter',
                'chunk_size_tokens': 2048,
                'chunk_overlap_tokens': 200,
                'min_chunk_size_tokens': 100,
            }
        }
    }

    chunker = ChunkerService(config)

    text = """
Chapter 1: The Beginning

This is the first chapter content.

Chapter 2: The Middle

This is the second chapter content.

Chapter 3: The End

This is the third chapter content.
"""

    chapters = chunker.chunk_by_chapters(text)

    assert len(chapters) >= 3, f"Should detect at least 3 chapters, found {len(chapters)}"

    # Check that chapter titles are captured
    titles = [title for title, _ in chapters]
    assert any("Chapter 1" in title or "The Beginning" in title for title in titles)

    print(f"✓ Chapter detection tests passed (found {len(chapters)} chapters)")


if __name__ == "__main__":
    test_chunker_by_tokens()
    test_chapter_detection()
    print("\nAll chunker tests passed!")
