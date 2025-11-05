"""
Main FastAPI application for Simulation Engine.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

import sys
sys.path.append('..')
from shared.logging_config import setup_logging, get_logger
from shared.base_config import load_service_config
from shared.common_types import HealthCheck, HealthStatus

from src.api import routes
from src.services.simulation import SimulationService
from src.db.database import DatabaseManager

# Metrics
AGENT_COUNT = Gauge('simulation_agents_total', 'Total number of agents', ['state'])
TICK_COUNT = Counter('simulation_ticks_total', 'Total simulation ticks')
TICK_LATENCY = Histogram('simulation_tick_duration_seconds', 'Tick processing time')
EVENT_COUNT = Counter('simulation_events_total', 'Total events', ['type'])

class AppState:
    """Application state container."""
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.simulation_service = None
        self.start_time = time.time()
        self.logger = None

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager."""
    app_state.config = load_service_config("simulation-engine", config_dir=".")
    setup_logging(
        "simulation-engine",
        log_level=app_state.config["logging"]["level"],
        log_format=app_state.config["logging"]["format"],
    )
    app_state.logger = get_logger("simulation-engine")
    app_state.logger.info("Starting Simulation Engine")

    app_state.db_manager = DatabaseManager(app_state.config)
    await app_state.db_manager.initialize()

    app_state.simulation_service = SimulationService(app_state.config, app_state.db_manager)
    await app_state.simulation_service.initialize()

    app_state.logger.info("Simulation Engine started successfully")
    yield

    app_state.logger.info("Shutting down Simulation Engine")
    if app_state.simulation_service:
        await app_state.simulation_service.stop()
    if app_state.db_manager:
        await app_state.db_manager.close()
    app_state.logger.info("Simulation Engine stopped")

app = FastAPI(
    title="Ashiorid Simulation Engine",
    description="Agent simulation with 100+ lightweight AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_state.logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(
        status=HealthStatus.HEALTHY,
        service="simulation-engine",
        version="0.1.0",
    )

@app.get("/health/detailed")
async def detailed_health_check():
    uptime = time.time() - app_state.start_time

    db_healthy = False
    if app_state.db_manager:
        db_healthy = await app_state.db_manager.health_check()

    sim_status = "stopped"
    if app_state.simulation_service:
        sim_status = "running" if app_state.simulation_service.is_running else "stopped"

    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "simulation-engine",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "simulation_status": sim_status,
        "components": {"database": "healthy" if db_healthy else "unhealthy"},
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    return {
        "service": "simulation-engine",
        "version": "0.1.0",
        "description": "Agent simulation engine",
        "endpoints": {
            "health": "/health",
            "start": "/simulation/start",
            "stop": "/simulation/stop",
            "status": "/simulation/status",
            "agents": "/agents",
        },
    }

app.include_router(routes.router)
app.state.app_state = app_state
app.state.metrics = {
    "agent_count": AGENT_COUNT,
    "tick_count": TICK_COUNT,
    "tick_latency": TICK_LATENCY,
    "event_count": EVENT_COUNT,
}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
