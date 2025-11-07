"""Main FastAPI application for AI Manager Service."""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

import sys
sys.path.append('../..')
from shared.base_config import load_service_config
from shared.logging_config import setup_logging, get_logger

from src.api import routes
from src.services.orchestrator import OrchestratorService
from src.services.event_generator import WorldEventGenerator
from src.services.llm_client import LLMClient
from src.services.character_client import CharacterClient
from src.services.lore_client import LoreClient
from src.services.simulation_client import SimulationClient
from src import dependencies

# Load configuration
config = load_service_config("ai-manager")
setup_logging(config["service"]["name"])
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "ai_manager_requests_total",
    "Total requests to AI Manager",
    ["endpoint", "method"]
)
REQUEST_LATENCY = Histogram(
    "ai_manager_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"]
)
ACTIVE_SESSIONS = Gauge(
    "ai_manager_active_sessions",
    "Number of active user sessions"
)
WORLD_EVENTS_GENERATED = Counter(
    "ai_manager_world_events_total",
    "Total world events generated",
    ["event_type"]
)
SERVICE_HEALTH = Gauge(
    "ai_manager_service_health",
    "Health status of dependent services",
    ["service"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""

    logger.info("Starting AI Manager Service")

    # Initialize service clients
    llm_client = LLMClient(config)
    character_client = CharacterClient(config)
    lore_client = LoreClient(config)
    simulation_client = SimulationClient(config)

    # Initialize orchestrator
    dependencies.orchestrator_service = OrchestratorService(
        config=config,
        llm_client=llm_client,
        character_client=character_client,
        lore_client=lore_client,
        simulation_client=simulation_client,
    )
    await dependencies.orchestrator_service.initialize()

    # Initialize world event generator
    dependencies.event_generator = WorldEventGenerator(
        config=config,
        simulation_client=simulation_client,
        llm_client=llm_client,
    )
    await dependencies.event_generator.initialize()

    # Start event generator if enabled
    if config.get("world_events", {}).get("enabled", True):
        dependencies.event_generator.start()

    logger.info("AI Manager Service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down AI Manager Service")
    if dependencies.event_generator:
        await dependencies.event_generator.stop()


# Create FastAPI app
app = FastAPI(
    title="AI Manager Service",
    description="Master orchestrator for Ashiorid AI Manager",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api/v1")

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-manager",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Manager",
        "description": "Master orchestrator for Ashiorid AI Manager",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api": "/api/v1",
            "docs": "/docs"
        }
    }
