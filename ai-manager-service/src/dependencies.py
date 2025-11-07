"""Dependency injection for FastAPI routes."""

from src.services.orchestrator import OrchestratorService
from src.services.event_generator import WorldEventGenerator

# Global service instances
orchestrator_service: OrchestratorService = None
event_generator: WorldEventGenerator = None


def get_orchestrator() -> OrchestratorService:
    """Get orchestrator service instance."""
    return orchestrator_service


def get_event_generator() -> WorldEventGenerator:
    """Get event generator instance."""
    return event_generator
