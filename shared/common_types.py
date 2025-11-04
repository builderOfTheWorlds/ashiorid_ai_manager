"""
Common data types and Pydantic models for Ashiorid AI Manager.

Shared schemas for inter-service communication:
- Health status
- Service status
- LLM requests and responses
- Agent states
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =================================================================
# Enums
# =================================================================


class HealthStatus(str, Enum):
    """Health status for services and components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceStatus(str, Enum):
    """Operational status for services."""

    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class AgentState(str, Enum):
    """State of simulation agents."""

    IDLE = "idle"
    ACTIVE = "active"
    SLEEPING = "sleeping"
    DEAD = "dead"


# =================================================================
# Health Check Models
# =================================================================


class HealthCheck(BaseModel):
    """Standard health check response."""

    status: HealthStatus
    service: str
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


class ServiceInfo(BaseModel):
    """Service information and status."""

    name: str
    status: ServiceStatus
    health: HealthStatus
    version: str = "0.1.0"
    uptime_seconds: float = 0.0
    requests_total: int = 0
    errors_total: int = 0
    metadata: Optional[Dict[str, Any]] = None


# =================================================================
# LLM Models
# =================================================================


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: str  # "system", "user", "assistant"
    content: str


class LLMRequest(BaseModel):
    """Request to LLM proxy service."""

    messages: List[LLMMessage]
    provider: LLMProvider = LLMProvider.OLLAMA
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """Response from LLM proxy service."""

    content: str
    provider: LLMProvider
    model: str
    usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    latency_ms: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None


class LLMError(BaseModel):
    """Error response from LLM proxy service."""

    error: str
    provider: LLMProvider
    model: Optional[str] = None
    retryable: bool = False
    details: Optional[Dict[str, Any]] = None


# =================================================================
# RAG Models
# =================================================================


class DocumentChunk(BaseModel):
    """A chunk of text for RAG ingestion."""

    text: str
    source: str
    metadata: Optional[Dict[str, Any]] = None


class SemanticSearchRequest(BaseModel):
    """Request for semantic search in RAG."""

    query: str
    collection: str = "lore"
    limit: int = Field(default=5, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata_filter: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """A single search result from RAG."""

    text: str
    score: float
    source: str
    metadata: Optional[Dict[str, Any]] = None


class SemanticSearchResponse(BaseModel):
    """Response from semantic search."""

    results: List[SearchResult]
    query: str
    total_results: int
    latency_ms: float


# =================================================================
# Character Agent Models
# =================================================================


class CharacterPersonality(BaseModel):
    """Character agent personality configuration."""

    name: str
    description: str
    system_prompt: str
    background_lore: List[str] = Field(default_factory=list)
    traits: Dict[str, Any] = Field(default_factory=dict)
    preferred_model: str = "llama3.2:3b"


class CharacterMessage(BaseModel):
    """Message to/from a character agent."""

    character_name: str
    message: str
    context: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CharacterResponse(BaseModel):
    """Response from a character agent."""

    character_name: str
    response: str
    reasoning: Optional[str] = None
    lore_sources: List[str] = Field(default_factory=list)
    latency_ms: float
    metadata: Optional[Dict[str, Any]] = None


# =================================================================
# Simulation Models
# =================================================================


class AgentAttributes(BaseModel):
    """Attributes for a simulation agent."""

    hunger: float = Field(default=0.5, ge=0.0, le=1.0)
    thirst: float = Field(default=0.5, ge=0.0, le=1.0)
    energy: float = Field(default=1.0, ge=0.0, le=1.0)
    health: float = Field(default=1.0, ge=0.0, le=1.0)


class SimulationAgent(BaseModel):
    """A simulation agent."""

    id: str
    name: str
    state: AgentState = AgentState.IDLE
    position: tuple[int, int] = (0, 0)
    attributes: AgentAttributes = Field(default_factory=AgentAttributes)
    inventory: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class SimulationState(BaseModel):
    """Overall simulation state."""

    tick: int = 0
    active_agents: int = 0
    total_agents: int = 0
    ticks_per_second: float = 0.0
    world_events: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class WorldEvent(BaseModel):
    """An event in the simulation world."""

    id: str
    type: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    affected_agents: List[str] = Field(default_factory=list)
    location: Optional[tuple[int, int]] = None
    metadata: Optional[Dict[str, Any]] = None


# =================================================================
# Metrics Models
# =================================================================


class ServiceMetrics(BaseModel):
    """Metrics for a service."""

    service_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requests_per_second: float = 0.0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    active_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    custom_metrics: Optional[Dict[str, float]] = None


# =================================================================
# Example usage and validation
# =================================================================


if __name__ == "__main__":
    # Test models
    print("=== Health Check ===")
    health = HealthCheck(
        status=HealthStatus.HEALTHY,
        service="test-service",
        details={"database": "connected", "redis": "connected"},
    )
    print(health.model_dump_json(indent=2))

    print("\n=== LLM Request ===")
    llm_req = LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant"),
            LLMMessage(role="user", content="What is the meaning of life?"),
        ],
        provider=LLMProvider.OLLAMA,
        model="llama3.2:3b",
        temperature=0.8,
    )
    print(llm_req.model_dump_json(indent=2))

    print("\n=== Simulation Agent ===")
    agent = SimulationAgent(
        id="agent-001",
        name="Wanderer",
        state=AgentState.ACTIVE,
        position=(10, 20),
        attributes=AgentAttributes(hunger=0.3, thirst=0.6, energy=0.8),
        inventory=["sword", "bread", "water"],
    )
    print(agent.model_dump_json(indent=2))

    print("\n=== Character Personality ===")
    gandalf = CharacterPersonality(
        name="Gandalf",
        description="A wise and powerful wizard",
        system_prompt="You are Gandalf the Grey, a wizard of great wisdom...",
        background_lore=["Fellowship of the Ring", "The Hobbit"],
        traits={"wisdom": 10, "power": 9, "patience": 8},
    )
    print(gandalf.model_dump_json(indent=2))
