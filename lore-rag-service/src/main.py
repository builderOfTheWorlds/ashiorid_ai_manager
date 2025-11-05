"""
Main FastAPI application for Lore RAG Service.
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
from src.services.qdrant_client import QdrantService
from src.services.embeddings import EmbeddingService
from src.services.search import SearchService
from src.services.ingestion import IngestionService


# Metrics
SEARCH_COUNT = Counter(
    'lore_rag_searches_total',
    'Total number of searches',
    ['collection', 'status']
)

SEARCH_LATENCY = Histogram(
    'lore_rag_search_duration_seconds',
    'Search latency',
    ['collection']
)

INGESTION_COUNT = Counter(
    'lore_rag_ingestions_total',
    'Total number of ingestions',
    ['collection', 'status']
)

EMBEDDING_COUNT = Counter(
    'lore_rag_embeddings_total',
    'Total number of embeddings generated'
)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.config = None
        self.qdrant_service = None
        self.embedding_service = None
        self.search_service = None
        self.ingestion_service = None
        self.start_time = time.time()
        self.logger = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    app_state.config = load_service_config("lore-rag-service", config_dir=".")
    setup_logging(
        "lore-rag-service",
        log_level=app_state.config["logging"]["level"],
        log_format=app_state.config["logging"]["format"],
    )
    app_state.logger = get_logger("lore-rag-service")
    app_state.logger.info("Starting Lore RAG Service")

    # Initialize services
    app_state.qdrant_service = QdrantService(app_state.config)
    await app_state.qdrant_service.initialize()

    app_state.embedding_service = EmbeddingService(app_state.config)
    await app_state.embedding_service.initialize()

    app_state.search_service = SearchService(
        app_state.config,
        app_state.qdrant_service,
        app_state.embedding_service,
    )

    app_state.ingestion_service = IngestionService(
        app_state.config,
        app_state.qdrant_service,
        app_state.embedding_service,
    )

    app_state.logger.info("Lore RAG Service started successfully")

    yield

    # Shutdown
    app_state.logger.info("Shutting down Lore RAG Service")
    if app_state.qdrant_service:
        await app_state.qdrant_service.close()
    if app_state.embedding_service:
        await app_state.embedding_service.close()
    app_state.logger.info("Lore RAG Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Ashiorid Lore RAG Service",
    description="Semantic search over fictional universe knowledge",
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
        service="lore-rag-service",
        version="0.1.0",
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    uptime = time.time() - app_state.start_time

    # Check Qdrant connectivity
    qdrant_healthy = False
    try:
        if app_state.qdrant_service:
            qdrant_healthy = await app_state.qdrant_service.health_check()
    except Exception as e:
        app_state.logger.error(f"Qdrant health check failed: {e}")

    # Check Ollama connectivity
    ollama_healthy = False
    try:
        if app_state.embedding_service:
            ollama_healthy = await app_state.embedding_service.health_check()
    except Exception as e:
        app_state.logger.error(f"Ollama health check failed: {e}")

    # Overall status
    status = "healthy" if (qdrant_healthy and ollama_healthy) else "degraded"

    return {
        "status": status,
        "service": "lore-rag-service",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "components": {
            "qdrant": "healthy" if qdrant_healthy else "unhealthy",
            "ollama": "healthy" if ollama_healthy else "unhealthy",
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
        "service": "lore-rag-service",
        "version": "0.1.0",
        "description": "Semantic search over fictional universe knowledge",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "search": "/search",
            "ingest": "/ingest",
            "collections": "/collections",
        },
    }


# Include API routes
app.include_router(routes.router)


# Expose app state for routes
app.state.app_state = app_state
app.state.metrics = {
    "search_count": SEARCH_COUNT,
    "search_latency": SEARCH_LATENCY,
    "ingestion_count": INGESTION_COUNT,
    "embedding_count": EMBEDDING_COUNT,
}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info",
    )
