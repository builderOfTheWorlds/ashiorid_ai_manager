"""
Text chunking service.
"""

from typing import Dict, Any, List, Tuple
import sys
sys.path.append('../..')
from shared.logging_config import get_logger
from src.utils.text_utils import (
    detect_chapter_boundaries,
    detect_scene_boundaries,
)

logger = get_logger(__name__)


class ChunkerService:
    """Service for text chunking."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize chunker service.

        Args:
            config: Service configuration
        """
        self.config = config
        self.chunk_config = config.get('processing', {}).get('chunking', {})

        # Import tiktoken for token counting
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            self.has_tiktoken = True
        except ImportError:
            logger.warning("tiktoken not available, using character-based estimation")
            self.tokenizer = None
            self.has_tiktoken = False

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Input text

        Returns:
            Token count
        """
        if self.has_tiktoken and self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough estimate: ~4 characters per token
            return len(text) // 4

    def chunk_by_tokens(
        self,
        text: str,
        chunk_size: int = 2048,
        overlap: int = 200,
        min_size: int = 100,
    ) -> List[str]:
        """
        Chunk text by token count with overlap.

        Args:
            text: Input text
            chunk_size: Target chunk size in tokens
            overlap: Overlap size in tokens
            min_size: Minimum chunk size in tokens

        Returns:
            List of text chunks
        """
        if not text.strip():
            return []

        chunks = []

        # Split into sentences for better boundaries
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds chunk size, split it
            if sentence_tokens > chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by characters
                words = sentence.split()
                temp_chunk = []
                temp_tokens = 0

                for word in words:
                    word_tokens = self.count_tokens(word)
                    if temp_tokens + word_tokens > chunk_size:
                        if temp_chunk:
                            chunks.append(' '.join(temp_chunk))
                        temp_chunk = [word]
                        temp_tokens = word_tokens
                    else:
                        temp_chunk.append(word)
                        temp_tokens += word_tokens

                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))

            elif current_tokens + sentence_tokens > chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    # Keep last few sentences for overlap
                    overlap_chunk = []
                    overlap_tokens = 0
                    for sent in reversed(current_chunk):
                        sent_tokens = self.count_tokens(sent)
                        if overlap_tokens + sent_tokens <= overlap:
                            overlap_chunk.insert(0, sent)
                            overlap_tokens += sent_tokens
                        else:
                            break
                    current_chunk = overlap_chunk + [sentence]
                    current_tokens = overlap_tokens + sentence_tokens
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens

            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add final chunk
        if current_chunk and current_tokens >= min_size:
            chunks.append(' '.join(current_chunk))

        logger.debug(f"Created {len(chunks)} chunks from text (strategy: token_count)")
        return chunks

    def chunk_by_chapters(self, text: str) -> List[Tuple[str, str]]:
        """
        Chunk text by chapters.

        Args:
            text: Input text

        Returns:
            List of (chapter_title, chapter_text) tuples
        """
        boundaries = detect_chapter_boundaries(text)

        if not boundaries:
            logger.warning("No chapter boundaries detected, falling back to token chunking")
            chunks = self.chunk_by_tokens(text)
            return [(f"Section {i+1}", chunk) for i, chunk in enumerate(chunks)]

        chapters = []

        for i, (pos, title) in enumerate(boundaries):
            # Get text from this boundary to next (or end)
            if i < len(boundaries) - 1:
                next_pos = boundaries[i + 1][0]
                chapter_text = text[pos:next_pos]
            else:
                chapter_text = text[pos:]

            chapters.append((title, chapter_text.strip()))

        logger.debug(f"Created {len(chapters)} chapter chunks")
        return chapters

    def chunk_by_scenes(self, text: str) -> List[str]:
        """
        Chunk text by scenes.

        Args:
            text: Input text

        Returns:
            List of scene text chunks
        """
        boundaries = detect_scene_boundaries(text)

        if not boundaries:
            logger.warning("No scene boundaries detected, falling back to token chunking")
            return self.chunk_by_tokens(text)

        # Add start and end positions
        boundaries = [0] + boundaries + [len(text)]

        scenes = []
        for i in range(len(boundaries) - 1):
            scene_text = text[boundaries[i]:boundaries[i + 1]].strip()
            if scene_text:
                scenes.append(scene_text)

        logger.debug(f"Created {len(scenes)} scene chunks")
        return scenes

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text using configured strategy.

        Args:
            text: Input text

        Returns:
            List of text chunks
        """
        strategy = self.chunk_config.get('strategy', 'token_count')
        chunk_size = self.chunk_config.get('chunk_size_tokens', 2048)
        overlap = self.chunk_config.get('chunk_overlap_tokens', 200)
        min_size = self.chunk_config.get('min_chunk_size_tokens', 100)

        if strategy == 'chapter':
            chapter_chunks = self.chunk_by_chapters(text)
            # Return just the text, not titles
            return [chunk_text for _, chunk_text in chapter_chunks]

        elif strategy == 'scene':
            return self.chunk_by_scenes(text)

        else:  # token_count
            return self.chunk_by_tokens(
                text,
                chunk_size=chunk_size,
                overlap=overlap,
                min_size=min_size,
            )

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        import re

        # Simple sentence splitting (could be improved with NLTK)
        # Split on . ! ? followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        return [s.strip() for s in sentences if s.strip()]
