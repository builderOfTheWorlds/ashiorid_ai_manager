"""API routes for Simulation Engine."""

from typing import List
from fastapi import APIRouter, HTTPException, Request, Depends

import sys
sys.path.append('../..')
from shared.common_types import SimulationAgent, SimulationState
from shared.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

def get_simulation_service(request: Request):
    return request.app.state.app_state.simulation_service

@router.post("/simulation/start")
async def start_simulation(
    num_agents: int = 100,
    simulation_service=Depends(get_simulation_service),
):
    """Start the simulation with initial agents."""
    try:
        await simulation_service.start(num_agents)
        logger.info(f"Simulation started with {num_agents} agents")
        return {"status": "started", "num_agents": num_agents}
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulation/stop")
async def stop_simulation(simulation_service=Depends(get_simulation_service)):
    """Stop the simulation."""
    try:
        await simulation_service.stop()
        logger.info("Simulation stopped")
        return {"status": "stopped"}
    except Exception as e:
        logger.error(f"Failed to stop simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/simulation/status", response_model=SimulationState)
async def get_simulation_status(simulation_service=Depends(get_simulation_service)):
    """Get current simulation status."""
    try:
        return await simulation_service.get_status()
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents", response_model=List[SimulationAgent])
async def list_agents(
    limit: int = 100,
    offset: int = 0,
    simulation_service=Depends(get_simulation_service),
):
    """List all agents."""
    try:
        agents = await simulation_service.get_agents(limit=limit, offset=offset)
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}", response_model=SimulationAgent)
async def get_agent(agent_id: str, simulation_service=Depends(get_simulation_service)):
    """Get a specific agent."""
    try:
        agent = await simulation_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/action")
async def agent_action(
    agent_id: str,
    action: str,
    simulation_service=Depends(get_simulation_service),
):
    """Manually trigger an agent action."""
    try:
        result = await simulation_service.manual_action(agent_id, action)
        return {"agent_id": agent_id, "action": action, "result": result}
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
async def get_recent_events(
    limit: int = 50,
    simulation_service=Depends(get_simulation_service),
):
    """Get recent simulation events."""
    try:
        events = await simulation_service.get_recent_events(limit=limit)
        return {"events": events, "total": len(events)}
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
