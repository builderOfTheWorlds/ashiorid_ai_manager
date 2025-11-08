"""
LLM-powered text enhancement service.
"""

from typing import Dict, Any, List, Optional
import asyncio
import sys
sys.path.append('../..')
from shared.logging_config import get_logger
from src.utils.llm_client import LLMClient

logger = get_logger(__name__)


class LLMEnhancerService:
    """Service for LLM-powered text enhancement."""

    def __init__(self, config: Dict[str, Any], llm_client: LLMClient):
        """
        Initialize LLM enhancer service.

        Args:
            config: Service configuration
            llm_client: LLM client instance
        """
        self.config = config
        self.llm_client = llm_client
        self.llm_config = config.get('processing', {}).get('llm_enhancement', {})
        self.enabled = self.llm_config.get('enabled', True)

        # Check if LLM service is available
        self.llm_available = False

    async def initialize(self):
        """Initialize and check LLM availability."""
        if self.enabled:
            self.llm_available = await self.llm_client.health_check()
            if self.llm_available:
                logger.info("LLM enhancement service initialized and available")
            else:
                logger.warning(
                    "LLM enhancement service not available - will skip enhancement"
                )
        else:
            logger.info("LLM enhancement disabled in configuration")

    async def enhance_chunk(self, text: str, chunk_id: int) -> Dict[str, Any]:
        """
        Enhance a single chunk with LLM-generated metadata.

        Args:
            text: Chunk text
            chunk_id: Chunk identifier

        Returns:
            Metadata dictionary
        """
        metadata = {
            "chunk_id": chunk_id,
            "enhanced": False,
        }

        if not self.enabled or not self.llm_available:
            return metadata

        features = self.llm_config.get('features', {})
        prompts = self.llm_config.get('prompt_templates', {})
        model = self.llm_config.get('model')

        # Generate summary
        if features.get('generate_summaries', True):
            summary_prompt = prompts.get('summary', '') + "\n\n" + text
            summary = await self.llm_client.generate(
                prompt=summary_prompt,
                model=model,
                temperature=0.5,
            )
            if summary:
                metadata['summary'] = summary.strip()

        # Extract characters
        if features.get('extract_characters', True):
            char_prompt = prompts.get('characters', '') + "\n\n" + text
            characters = await self.llm_client.generate(
                prompt=char_prompt,
                model=model,
                temperature=0.3,
            )
            if characters:
                # Parse character list (format: "Name: description")
                char_list = self._parse_character_list(characters)
                if char_list:
                    metadata['characters'] = char_list

        # Tag themes
        if features.get('tag_themes', True):
            theme_prompt = prompts.get('themes', '') + "\n\n" + text
            themes = await self.llm_client.generate(
                prompt=theme_prompt,
                model=model,
                temperature=0.3,
            )
            if themes:
                # Parse comma-separated themes
                theme_list = [t.strip() for t in themes.split(',') if t.strip()]
                if theme_list:
                    metadata['themes'] = theme_list

        # Detect narrative arc
        if features.get('detect_narrative_arc', True):
            arc_prompt = prompts.get('narrative_arc', '') + "\n\n" + text
            arc = await self.llm_client.generate(
                prompt=arc_prompt,
                model=model,
                temperature=0.2,
            )
            if arc:
                metadata['narrative_arc'] = arc.strip().lower()

        # Identify POV
        if features.get('identify_pov', True):
            pov_prompt = prompts.get('pov', '') + "\n\n" + text
            pov = await self.llm_client.generate(
                prompt=pov_prompt,
                model=model,
                temperature=0.2,
            )
            if pov:
                metadata['pov'] = pov.strip().lower()

        # Determine embedding hint based on content
        metadata['embedding_hint'] = self._determine_embedding_hint(metadata)
        metadata['enhanced'] = True

        logger.debug(f"Enhanced chunk {chunk_id} with LLM metadata")
        return metadata

    async def enhance_chunks(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Enhance multiple chunks with batching and rate limiting.

        Args:
            chunks: List of text chunks

        Returns:
            List of metadata dictionaries
        """
        if not self.enabled or not self.llm_available:
            logger.info("LLM enhancement skipped (disabled or unavailable)")
            return [{"chunk_id": i, "enhanced": False} for i in range(len(chunks))]

        batch_size = self.llm_config.get('batch_size', 5)
        rate_limit = self.llm_config.get('rate_limit_delay_seconds', 0.5)

        metadata_list = []

        logger.info(f"Enhancing {len(chunks)} chunks with LLM (batch_size={batch_size})")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_start_idx = i

            # Process batch concurrently
            tasks = [
                self.enhance_chunk(chunk, batch_start_idx + j)
                for j, chunk in enumerate(batch)
            ]

            batch_metadata = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for j, meta in enumerate(batch_metadata):
                if isinstance(meta, Exception):
                    logger.error(f"Enhancement error for chunk {i + j}: {meta}")
                    metadata_list.append({"chunk_id": i + j, "enhanced": False, "error": str(meta)})
                else:
                    metadata_list.append(meta)

            # Rate limiting
            if i + batch_size < len(chunks):
                await asyncio.sleep(rate_limit)

            # Log progress
            progress = min((i + batch_size) / len(chunks) * 100, 100)
            logger.info(f"Enhancement progress: {progress:.1f}%")

        logger.info(f"Enhanced {len(metadata_list)} chunks")
        return metadata_list

    def _parse_character_list(self, characters_text: str) -> List[str]:
        """
        Parse character list from LLM output.

        Args:
            characters_text: Raw LLM output

        Returns:
            List of character names
        """
        lines = characters_text.strip().split('\n')
        characters = []

        for line in lines:
            # Try to extract name (before : or -)
            if ':' in line:
                name = line.split(':')[0].strip()
            elif '-' in line:
                name = line.split('-')[0].strip()
            else:
                name = line.strip()

            # Remove list markers (1., *, -, etc.)
            name = name.lstrip('0123456789.*- ')

            if name and len(name) < 50:  # Sanity check
                characters.append(name)

        return characters

    def _determine_embedding_hint(self, metadata: Dict[str, Any]) -> str:
        """
        Determine embedding hint based on metadata.

        Args:
            metadata: Chunk metadata

        Returns:
            Embedding hint string
        """
        themes = metadata.get('themes', [])

        # Priority-based hints
        if 'worldbuilding' in themes or 'magic_system' in themes:
            return 'worldbuilding'
        elif 'character' in str(metadata.get('characters', [])):
            return 'character'
        elif metadata.get('pov') or 'dialogue' in themes:
            return 'dialogue'
        elif 'mystery' in themes or 'prophecy' in themes:
            return 'lore'
        else:
            return 'general'
