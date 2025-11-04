"""
Shared utilities for Ashiorid AI Manager.

This package contains common functionality used across all microservices:
- Logging configuration (JSON and human-readable formats)
- Base configuration utilities (YAML loading, environment variables)
- Common data types and models (Pydantic schemas)
"""

__version__ = "0.1.0"

from .logging_config import setup_logging, get_logger
from .base_config import load_config, get_env
from .common_types import (
    HealthStatus,
    ServiceStatus,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "load_config",
    "get_env",
    "HealthStatus",
    "ServiceStatus",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
]
