"""
Character management service.
"""

from typing import Dict, List, Optional

from sqlalchemy import select, func

import sys
sys.path.append('../..')
from shared.common_types import CharacterPersonality
from shared.logging_config import get_logger

from src.db.models import Character
from src.db.database import DatabaseManager

logger = get_logger(__name__)


class CharacterService:
    """Service for managing characters."""

    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.personalities = config.get("personalities", {})

    async def initialize(self):
        """Initialize service and load pre-defined characters."""
        logger.info("Initializing character service")

        # Load pre-defined characters from config
        for char_key, char_data in self.personalities.items():
            try:
                existing = await self.get_character(char_data["name"])
                if not existing:
                    character = CharacterPersonality(
                        name=char_data["name"],
                        description=char_data["description"],
                        system_prompt=char_data["system_prompt"],
                        background_lore=char_data.get("background_lore", []),
                        traits=char_data.get("traits", {}),
                        preferred_model=char_data.get("preferred_model", "llama3.2:3b"),
                    )
                    await self.create_character(character)
                    logger.info(f"Loaded pre-defined character: {character.name}")
            except Exception as e:
                logger.error(f"Failed to load character {char_key}: {e}")

        logger.info("Character service initialized")

    async def list_characters(self) -> List[CharacterPersonality]:
        """List all characters."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(Character))
            characters = result.scalars().all()

            return [self._model_to_personality(char) for char in characters]

    async def get_character(self, name: str) -> Optional[CharacterPersonality]:
        """Get a character by name."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Character).where(Character.name == name)
            )
            character = result.scalar_one_or_none()

            return self._model_to_personality(character) if character else None

    async def create_character(self, personality: CharacterPersonality) -> CharacterPersonality:
        """Create a new character."""
        async with self.db_manager.get_session() as session:
            # Check if character already exists
            existing = await session.execute(
                select(Character).where(Character.name == personality.name)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Character '{personality.name}' already exists")

            # Create new character
            character = Character(
                name=personality.name,
                description=personality.description,
                system_prompt=personality.system_prompt,
                traits=personality.traits,
                preferred_model=personality.preferred_model,
            )

            session.add(character)
            await session.commit()
            await session.refresh(character)

            logger.info(f"Character created: {personality.name}")
            return self._model_to_personality(character)

    async def delete_character(self, name: str):
        """Delete a character."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Character).where(Character.name == name)
            )
            character = result.scalar_one_or_none()

            if not character:
                raise ValueError(f"Character '{name}' not found")

            await session.delete(character)
            await session.commit()

            logger.info(f"Character deleted: {name}")

    async def count_characters(self) -> int:
        """Count total characters."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(func.count(Character.id)))
            return result.scalar()

    def _model_to_personality(self, character: Character) -> CharacterPersonality:
        """Convert database model to Pydantic model."""
        return CharacterPersonality(
            name=character.name,
            description=character.description,
            system_prompt=character.system_prompt,
            background_lore=[],
            traits=character.traits or {},
            preferred_model=character.preferred_model or "llama3.2:3b",
        )
