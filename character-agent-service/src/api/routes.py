"""
API routes for Character Agent Service.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends

import sys
sys.path.append('../..')
from shared.common_types import (
    CharacterPersonality,
    CharacterMessage,
    CharacterResponse,
)
from shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_character_service(request: Request):
    """Dependency to get character service from app state."""
    return request.app.state.app_state.character_service


def get_conversation_service(request: Request):
    """Dependency to get conversation service from app state."""
    return request.app.state.app_state.conversation_service


def get_metrics(request: Request):
    """Dependency to get metrics from app state."""
    return request.app.state.metrics


@router.get("/characters", response_model=List[CharacterPersonality])
async def list_characters(
    character_service=Depends(get_character_service),
):
    """
    List all available characters.

    Returns:
        List of character personalities
    """
    try:
        characters = await character_service.list_characters()
        return characters

    except Exception as e:
        logger.error(f"Failed to list characters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_name}", response_model=CharacterPersonality)
async def get_character(
    character_name: str,
    character_service=Depends(get_character_service),
):
    """
    Get a specific character's personality.

    Args:
        character_name: Name of the character

    Returns:
        Character personality
    """
    try:
        character = await character_service.get_character(character_name)

        if not character:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{character_name}' not found"
            )

        return character

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get character: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/characters", response_model=CharacterPersonality)
async def create_character(
    character: CharacterPersonality,
    character_service=Depends(get_character_service),
):
    """
    Create a new character.

    Args:
        character: Character personality definition

    Returns:
        Created character
    """
    try:
        created = await character_service.create_character(character)

        logger.info(f"Character created: {character.name}")

        return created

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create character: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/characters/{character_name}/chat", response_model=CharacterResponse)
async def chat_with_character(
    character_name: str,
    message: CharacterMessage,
    request: Request,
    conversation_service=Depends(get_conversation_service),
    character_service=Depends(get_character_service),
    metrics=Depends(get_metrics),
):
    """
    Chat with a character.

    Args:
        character_name: Name of the character to chat with
        message: Message to send to the character

    Returns:
        Character's response
    """
    start_time = time.time()

    try:
        # Verify character exists
        character = await character_service.get_character(character_name)
        if not character:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{character_name}' not found"
            )

        logger.info(
            f"Chat request: character={character_name}, "
            f"message_length={len(message.message)}"
        )

        # Process chat
        response = await conversation_service.chat(
            character_name=character_name,
            message=message.message,
            context=message.context,
            metadata=message.metadata,
        )

        # Update metrics
        latency = time.time() - start_time
        response.latency_ms = latency * 1000

        metrics["chat_count"].labels(
            character=character_name,
            status="success",
        ).inc()

        metrics["chat_latency"].labels(
            character=character_name,
        ).observe(latency)

        if response.lore_sources:
            metrics["lore_context_count"].inc()

        logger.info(
            f"Chat completed: character={character_name}, "
            f"latency_ms={response.latency_ms:.2f}, "
            f"lore_sources={len(response.lore_sources)}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        metrics["chat_count"].labels(
            character=character_name,
            status="error",
        ).inc()

        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_name}/conversations")
async def get_character_conversations(
    character_name: str,
    limit: int = 10,
    offset: int = 0,
    conversation_service=Depends(get_conversation_service),
):
    """
    Get conversation history for a character.

    Args:
        character_name: Name of the character
        limit: Maximum number of conversations to return
        offset: Offset for pagination

    Returns:
        List of conversations
    """
    try:
        conversations = await conversation_service.get_conversations(
            character_name=character_name,
            limit=limit,
            offset=offset,
        )

        return {
            "character": character_name,
            "conversations": conversations,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/characters/{character_name}")
async def delete_character(
    character_name: str,
    character_service=Depends(get_character_service),
):
    """
    Delete a character.

    Args:
        character_name: Name of the character to delete

    Returns:
        Deletion status
    """
    try:
        await character_service.delete_character(character_name)

        logger.info(f"Character deleted: {character_name}")

        return {
            "status": "success",
            "character": character_name,
            "message": "Character deleted",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete character: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    conversation_service=Depends(get_conversation_service),
    character_service=Depends(get_character_service),
):
    """
    Get service statistics.

    Returns:
        Service statistics
    """
    try:
        total_characters = await character_service.count_characters()
        total_conversations = await conversation_service.count_conversations()

        return {
            "total_characters": total_characters,
            "total_conversations": total_conversations,
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
