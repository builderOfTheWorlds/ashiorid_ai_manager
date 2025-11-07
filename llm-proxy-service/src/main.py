"""
Main FastAPI application for LLM Proxy Service.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Import shared utilities
import sys
sys.path.append('..')
from shared.logging_config import setup_logging, get_logger
from shared.base_config import load_service_config
from shared.common_types import HealthCheck, HealthStatus

# Import local modules
from src.api import routes
from src.services.proxy import LLMProxyService


# Metrics
REQUEST_COUNT = Counter(
    'llm_proxy_requests_total',
    'Total number of LLM requests',
    ['provider', 'model', 'status']
)

REQUEST_LATENCY = Histogram(
    'llm_proxy_request_duration_seconds',
    'LLM request latency',
    ['provider', 'model']
)

TOKEN_USAGE = Counter(
    'llm_proxy_tokens_total',
    'Total number of tokens used',
    ['provider', 'model', 'type']  # type: prompt or completion
)

COST_TRACKING = Counter(
    'llm_proxy_cost_total',
    'Total cost of LLM requests in USD',
    ['provider', 'model']
)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.config = None
        self.proxy_service = None
        self.start_time = time.time()
        self.logger = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    app_state.config = load_service_config("llm-proxy-service", config_dir=".")
    setup_logging(
        "llm-proxy-service",
        log_level=app_state.config["logging"]["level"],
        log_format=app_state.config["logging"]["format"],
    )
    app_state.logger = get_logger("llm-proxy-service")
    app_state.logger.info("Starting LLM Proxy Service")

    # Initialize proxy service
    app_state.proxy_service = LLMProxyService(app_state.config)
    await app_state.proxy_service.initialize()

    app_state.logger.info("LLM Proxy Service started successfully")

    yield

    # Shutdown
    app_state.logger.info("Shutting down LLM Proxy Service")
    if app_state.proxy_service:
        await app_state.proxy_service.shutdown()
    app_state.logger.info("LLM Proxy Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Ashiorid LLM Proxy Service",
    description="Unified LLM proxy with batching, caching, and cost tracking",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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
        service="llm-proxy-service",
        version="0.1.0",
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    uptime = time.time() - app_state.start_time

    # Check provider connectivity
    provider_status = {}
    if app_state.proxy_service:
        provider_status = await app_state.proxy_service.check_providers()

    return {
        "status": "healthy",
        "service": "llm-proxy-service",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "providers": provider_status,
        "cache_enabled": app_state.config.get("cache", {}).get("enabled", False),
        "rate_limit_enabled": app_state.config.get("rate_limit", {}).get("enabled", False),
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
        "service": "llm-proxy-service",
        "version": "0.1.0",
        "description": "Unified LLM proxy for Ashiorid AI Manager",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "chat_completions": "/v1/chat/completions",
            "providers": "/providers",
        },
    }


# Include API routes
app.include_router(routes.router, prefix="/v1")
app.include_router(routes.admin_router)


# Expose app state for routes
app.state.app_state = app_state
app.state.metrics = {
    "request_count": REQUEST_COUNT,
    "request_latency": REQUEST_LATENCY,
    "token_usage": TOKEN_USAGE,
    "cost_tracking": COST_TRACKING,
}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
