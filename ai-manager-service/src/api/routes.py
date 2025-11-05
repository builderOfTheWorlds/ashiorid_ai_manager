"""API routes for AI Manager Service."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

import sys
sys.path.append('../../..')
from shared.common_types import LLMProvider

from src.main import get_orchestrator, get_event_generator
from src.services.orchestrator import OrchestratorService
from src.services.event_generator import WorldEventGenerator

router = APIRouter()


# Request/Response models
class QueryRequest(BaseModel):
    """User query request."""
    query: str = Field(..., description="User query or prompt")
    locale: Optional[str] = Field(default="en-US", description="User locale")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    include_simulation: bool = Field(default=True, description="Include simulation data")
    include_lore: bool = Field(default=True, description="Include lore context")


class QueryResponse(BaseModel):
    """Query response."""
    response: str
    sources: List[str] = []
    simulation_snapshot: Optional[Dict] = None
    metadata: Dict[str, Any] = {}


class CharacterQueryRequest(BaseModel):
    """Character-based query request."""
    character_name: str
    message: str
    locale: Optional[str] = "en-US"
    include_simulation: bool = True


class WorldEventRequest(BaseModel):
    """Trigger world event request."""
    event_type: str
    description: Optional[str] = None
    agent_ids: Optional[List[str]] = []
    location: Optional[tuple[int, int]] = None


class SystemStatusResponse(BaseModel):
    """System status response."""
    status: str
    services: Dict[str, Dict[str, Any]]
    simulation: Dict[str, Any]
    world_events: List[Dict[str, Any]]


# ============================================================================
# Query Endpoints
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """
    Process a user query with full orchestration.

    This endpoint coordinates all services to provide a comprehensive response:
    - Searches lore database for relevant context
    - Retrieves current simulation state
    - Generates response using LLM with full context
    """
    try:
        response = await orchestrator.process_query(
            query=request.query,
            locale=request.locale,
            context=request.context,
            include_simulation=request.include_simulation,
            include_lore=request.include_lore,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/character/query", response_model=QueryResponse)
async def query_character(
    request: CharacterQueryRequest,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """
    Query a specific character with simulation context.

    Combines character personality with current simulation state
    for contextually-aware character responses.
    """
    try:
        response = await orchestrator.query_character(
            character_name=request.character_name,
            message=request.message,
            locale=request.locale,
            include_simulation=request.include_simulation,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# World Event Endpoints
# ============================================================================

@router.post("/events/trigger")
async def trigger_world_event(
    request: WorldEventRequest,
    event_generator: WorldEventGenerator = Depends(get_event_generator)
):
    """Manually trigger a world event."""
    try:
        event = await event_generator.generate_event(
            event_type=request.event_type,
            description=request.description,
            agent_ids=request.agent_ids,
            location=request.location,
        )
        return {"status": "success", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/recent")
async def get_recent_events(
    limit: int = 20,
    event_generator: WorldEventGenerator = Depends(get_event_generator)
):
    """Get recent world events."""
    try:
        events = await event_generator.get_recent_events(limit=limit)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# System Status Endpoints
# ============================================================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    orchestrator: OrchestratorService = Depends(get_orchestrator),
    event_generator: WorldEventGenerator = Depends(get_event_generator)
):
    """Get overall system status."""
    try:
        status = await orchestrator.get_system_status()

        # Add world events
        recent_events = await event_generator.get_recent_events(limit=10)
        status["world_events"] = recent_events

        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/health")
async def check_service_health(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Check health of all dependent services."""
    try:
        health = await orchestrator.check_service_health()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
