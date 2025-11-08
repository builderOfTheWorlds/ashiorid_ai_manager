"""
Main FastAPI application for Character Agent Service.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Import shared utilities
import sys
sys.path.append('..')
from shared.logging_config import setup_logging, get_logger
from shared.base_config import load_service_config
from shared.common_types import HealthCheck, HealthStatus

# Import local modules
from src.api import routes
from src.services.character import CharacterService
from src.services.conversation import ConversationService
from src.services.lore_context import LoreContextService
from src.services.llm_client import LLMClientService
from src.db.database import DatabaseManager


# Metrics
CHAT_COUNT = Counter(
    'character_agent_chats_total',
    'Total number of character chats',
    ['character', 'status']
)

CHAT_LATENCY = Histogram(
    'character_agent_chat_duration_seconds',
    'Chat latency',
    ['character']
)

LORE_CONTEXT_COUNT = Counter(
    'character_agent_lore_contexts_total',
    'Total number of lore context retrievals'
)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.config = None
        self.db_manager = None
        self.character_service = None
        self.conversation_service = None
        self.lore_context_service = None
        self.llm_client_service = None
        self.start_time = time.time()
        self.logger = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    app_state.config = load_service_config("character-agent-service", config_dir=".")
    setup_logging(
        "character-agent-service",
        log_level=app_state.config["logging"]["level"],
        log_format=app_state.config["logging"]["format"],
    )
    app_state.logger = get_logger("character-agent-service")
    app_state.logger.info("Starting Character Agent Service")

    # Initialize database
    app_state.db_manager = DatabaseManager(app_state.config)
    await app_state.db_manager.initialize()

    # Initialize services
    app_state.llm_client_service = LLMClientService(app_state.config)
    app_state.lore_context_service = LoreContextService(app_state.config)

    app_state.character_service = CharacterService(
        app_state.config,
        app_state.db_manager,
    )
    await app_state.character_service.initialize()

    app_state.conversation_service = ConversationService(
        app_state.config,
        app_state.db_manager,
        app_state.llm_client_service,
        app_state.lore_context_service,
    )

    app_state.logger.info("Character Agent Service started successfully")

    yield

    # Shutdown
    app_state.logger.info("Shutting down Character Agent Service")
    if app_state.db_manager:
        await app_state.db_manager.close()
    if app_state.llm_client_service:
        await app_state.llm_client_service.close()
    if app_state.lore_context_service:
        await app_state.lore_context_service.close()
    app_state.logger.info("Character Agent Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Ashiorid Character Agent Service",
    description="AI characters with distinct personalities for world-building",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    app_state.logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url),
        },
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint."""
    return HealthCheck(
        status=HealthStatus.HEALTHY,
        service="character-agent-service",
        version="0.1.0",
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    uptime = time.time() - app_state.start_time

    # Check database connectivity
    db_healthy = False
    try:
        if app_state.db_manager:
            db_healthy = await app_state.db_manager.health_check()
    except Exception as e:
        app_state.logger.error(f"Database health check failed: {e}")

    # Check LLM proxy connectivity
    llm_healthy = False
    try:
        if app_state.llm_client_service:
            llm_healthy = await app_state.llm_client_service.health_check()
    except Exception as e:
        app_state.logger.error(f"LLM proxy health check failed: {e}")

    # Check lore RAG connectivity
    lore_healthy = False
    try:
        if app_state.lore_context_service:
            lore_healthy = await app_state.lore_context_service.health_check()
    except Exception as e:
        app_state.logger.error(f"Lore RAG health check failed: {e}")

    # Overall status
    status = "healthy" if (db_healthy and llm_healthy and lore_healthy) else "degraded"

    return {
        "status": status,
        "service": "character-agent-service",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "llm_proxy": "healthy" if llm_healthy else "unhealthy",
            "lore_rag": "healthy" if lore_healthy else "unhealthy",
        },
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Info endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "character-agent-service",
        "version": "0.1.0",
        "description": "AI characters with distinct personalities",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "characters": "/characters",
            "chat": "/characters/{name}/chat",
        },
    }


# Include API routes
app.include_router(routes.router)


# Expose app state for routes
app.state.app_state = app_state
app.state.metrics = {
    "chat_count": CHAT_COUNT,
    "chat_latency": CHAT_LATENCY,
    "lore_context_count": LORE_CONTEXT_COUNT,
}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info",
    )
