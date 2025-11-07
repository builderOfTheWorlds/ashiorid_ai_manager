"""
Conversation management service.
"""

from typing import Dict, List, Optional

from sqlalchemy import select, func

import sys
sys.path.append('../..')
from shared.common_types import CharacterResponse, LLMMessage
from shared.logging_config import get_logger

from src.db.models import Conversation
from src.db.database import DatabaseManager

logger = get_logger(__name__)


class ConversationService:
    """Service for managing conversations."""

    def __init__(self, config: Dict, db_manager: DatabaseManager, llm_client, lore_context):
        self.config = config
        self.db_manager = db_manager
        self.llm_client = llm_client
        self.lore_context = lore_context

        char_config = config.get("characters", {})
        self.max_lore_results = char_config.get("max_lore_results", 3)
        self.max_history_messages = char_config.get("max_history_messages", 10)

    async def chat(
        self,
        character_name: str,
        message: str,
        context: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> CharacterResponse:
        """
        Chat with a character.

        Args:
            character_name: Name of the character
            message: User message
            context: Optional additional context
            metadata: Optional metadata

        Returns:
            Character response
        """
        import time
        start_time = time.time()

        # Get character from database
        from src.services.character import CharacterService
        # Note: This is simplified; in production use dependency injection
        async with self.db_manager.get_session() as session:
            from src.db.models import Character
            result = await session.execute(
                select(Character).where(Character.name == character_name)
            )
            character = result.scalar_one_or_none()

        if not character:
            raise ValueError(f"Character '{character_name}' not found")

        # Get lore context
        lore_sources = []
        lore_context_text = ""

        if character.lore_collection:
            lore_results = await self.lore_context.get_context(
                query=message,
                collection=character.lore_collection,
                limit=self.max_lore_results,
            )
            lore_sources = [r.get("source", "unknown") for r in lore_results]
            lore_context_text = "\n\n".join([r.get("text", "") for r in lore_results])

        # Get conversation history
        history = await self._get_recent_history(character_name, limit=self.max_history_messages)

        # Build messages for LLM
        messages = []

        # System prompt with lore context
        system_content = character.system_prompt
        if lore_context_text:
            system_content += f"\n\nRelevant lore context:\n{lore_context_text}"

        messages.append(LLMMessage(role="system", content=system_content))

        # Add history
        for hist in history:
            messages.append(LLMMessage(role="user", content=hist.user_message))
            messages.append(LLMMessage(role="assistant", content=hist.character_response))

        # Add current message
        messages.append(LLMMessage(role="user", content=message))

        # Call LLM
        response_text = await self.llm_client.chat(
            messages=messages,
            model=character.preferred_model or "llama3.2:3b",
            temperature=0.8,
        )

        # Save conversation
        await self._save_conversation(
            character_name=character_name,
            user_message=message,
            character_response=response_text,
            lore_sources=lore_sources,
            metadata=metadata,
        )

        latency_ms = (time.time() - start_time) * 1000

        return CharacterResponse(
            character_name=character_name,
            response=response_text,
            reasoning=None,
            lore_sources=lore_sources,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    async def _get_recent_history(self, character_name: str, limit: int) -> List[Conversation]:
        """Get recent conversation history."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.character_name == character_name)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
            )
            history = result.scalars().all()
            return list(reversed(history))

    async def _save_conversation(
        self,
        character_name: str,
        user_message: str,
        character_response: str,
        lore_sources: List[str],
        metadata: Optional[Dict],
    ):
        """Save conversation to database."""
        async with self.db_manager.get_session() as session:
            conversation = Conversation(
                character_name=character_name,
                user_message=user_message,
                character_response=character_response,
                lore_sources=lore_sources,
                properties=metadata,  # Map metadata param to properties column
            )
            session.add(conversation)
            await session.commit()

    async def get_conversations(
        self,
        character_name: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        """Get conversation history."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.character_name == character_name)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            conversations = result.scalars().all()

            return [
                {
                    "id": conv.id,
                    "user_message": conv.user_message,
                    "character_response": conv.character_response,
                    "lore_sources": conv.lore_sources,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                }
                for conv in conversations
            ]

    async def count_conversations(self) -> int:
        """Count total conversations."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(func.count(Conversation.id)))
            return result.scalar()
