"""
Main FastAPI application for Data Preparation Service.
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
from src.services.normalizer import NormalizerService
from src.services.quality_checker import QualityCheckerService
from src.services.chunker import ChunkerService
from src.services.llm_enhancer import LLMEnhancerService
from src.services.file_manager import FileManagerService
from src.services.job_manager import JobManagerService
from src.services.processing_pipeline import ProcessingPipeline
from src.utils.llm_client import LLMClient


# Metrics
PROCESSING_COUNT = Counter(
    'data_prep_processing_total',
    'Total number of processing jobs',
    ['job_type', 'status']
)

PROCESSING_LATENCY = Histogram(
    'data_prep_processing_duration_seconds',
    'Processing job latency',
    ['job_type']
)

CHUNKS_CREATED = Counter(
    'data_prep_chunks_created_total',
    'Total number of chunks created'
)

FILES_PROCESSED = Counter(
    'data_prep_files_processed_total',
    'Total number of files processed',
    ['status']
)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.config = None
        self.normalizer = None
        self.quality_checker = None
        self.chunker = None
        self.llm_client = None
        self.llm_enhancer = None
        self.file_manager = None
        self.job_manager = None
        self.pipeline = None
        self.start_time = time.time()
        self.logger = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    app_state.config = load_service_config("data-prep-service", config_dir=".")
    setup_logging(
        "data-prep-service",
        log_level=app_state.config["logging"]["level"],
        log_format=app_state.config["logging"]["format"],
    )
    app_state.logger = get_logger("data-prep-service")
    app_state.logger.info("Starting Data Preparation Service")

    # Initialize services
    app_state.normalizer = NormalizerService(app_state.config)
    app_state.quality_checker = QualityCheckerService(app_state.config)
    app_state.chunker = ChunkerService(app_state.config)

    # Initialize LLM client and enhancer
    app_state.llm_client = LLMClient(app_state.config)
    app_state.llm_enhancer = LLMEnhancerService(app_state.config, app_state.llm_client)
    await app_state.llm_enhancer.initialize()

    # Initialize file and job managers
    app_state.file_manager = FileManagerService(app_state.config)
    app_state.job_manager = JobManagerService()

    # Initialize processing pipeline
    app_state.pipeline = ProcessingPipeline(
        config=app_state.config,
        normalizer=app_state.normalizer,
        quality_checker=app_state.quality_checker,
        chunker=app_state.chunker,
        llm_enhancer=app_state.llm_enhancer,
        file_manager=app_state.file_manager,
        job_manager=app_state.job_manager,
    )

    app_state.logger.info("Data Preparation Service started successfully")

    yield

    # Shutdown
    app_state.logger.info("Shutting down Data Preparation Service")
    if app_state.llm_client:
        await app_state.llm_client.close()
    app_state.logger.info("Data Preparation Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Ashiorid Data Preparation Service",
    description="Process source text files into ML-ready training data",
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
        service="data-prep-service",
        version="0.1.0",
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    uptime = time.time() - app_state.start_time

    # Check LLM proxy connectivity
    llm_healthy = False
    try:
        if app_state.llm_client:
            llm_healthy = await app_state.llm_client.health_check()
    except Exception as e:
        app_state.logger.error(f"LLM proxy health check failed: {e}")

    # Check file system access
    fs_healthy = False
    try:
        if app_state.file_manager:
            # Try to access output directory
            app_state.file_manager.output_dir.exists()
            fs_healthy = True
    except Exception as e:
        app_state.logger.error(f"File system health check failed: {e}")

    # Overall status
    status = "healthy" if (llm_healthy or not app_state.config.get('processing', {}).get('llm_enhancement', {}).get('enabled')) and fs_healthy else "degraded"

    return {
        "status": status,
        "service": "data-prep-service",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "components": {
            "llm_proxy": "healthy" if llm_healthy else "unhealthy",
            "file_system": "healthy" if fs_healthy else "unhealthy",
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
        "service": "data-prep-service",
        "version": "0.1.0",
        "description": "Process source text files into ML-ready training data",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "process_batch": "/process/batch",
            "process_file": "/process/file",
            "job_status": "/jobs/{job_id}",
            "list_files": "/files",
            "download_file": "/files/{filename}",
            "file_metadata": "/files/{filename}/metadata",
            "delete_file": "/files/{filename}",
            "reprocess": "/reprocess/{filename}",
            "stats": "/stats",
        },
    }


# Include API routes
app.include_router(routes.router)


# Expose app state for routes
app.state.app_state = app_state
app.state.metrics = {
    "processing_count": PROCESSING_COUNT,
    "processing_latency": PROCESSING_LATENCY,
    "chunks_created": CHUNKS_CREATED,
    "files_processed": FILES_PROCESSED,
}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info",
    )
