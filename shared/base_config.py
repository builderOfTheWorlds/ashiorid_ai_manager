"""
Base configuration utilities for Ashiorid AI Manager.

Provides utilities for:
- Loading YAML configuration files
- Reading environment variables with type conversion
- Merging configuration from multiple sources
"""

import os
import yaml
from typing import Any, Dict, Optional, TypeVar, Type
from pathlib import Path


T = TypeVar("T")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Dictionary containing configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        try:
            config = yaml.safe_load(f)
            return config or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in configuration file {config_path}: {e}"
            )


def get_env(
    key: str,
    default: Optional[T] = None,
    value_type: Type[T] = str,
    required: bool = False,
) -> Optional[T]:
    """
    Get an environment variable with type conversion.

    Args:
        key: Environment variable name
        default: Default value if not found
        value_type: Type to convert to (str, int, float, bool)
        required: If True, raise error if variable is not set

    Returns:
        Environment variable value converted to specified type

    Raises:
        ValueError: If required variable is not set or type conversion fails
    """
    value = os.getenv(key)

    if value is None:
        if required:
            raise ValueError(f"Required environment variable not set: {key}")
        return default

    # Type conversion
    try:
        if value_type == bool:
            # Handle boolean conversion specially
            return value.lower() in ("true", "1", "yes", "on")  # type: ignore
        elif value_type == int:
            # Handle Kubernetes service URL format (e.g., tcp://10.43.125.137:5432)
            if isinstance(value, str) and "://" in value:
                # Extract port from URL format
                try:
                    # Split by '://' and take the part after it
                    host_port = value.split("://", 1)[1]
                    # Extract port number (after the last colon)
                    if ":" in host_port:
                        port_str = host_port.rsplit(":", 1)[1]
                        # Remove any trailing path or query parameters
                        port_str = port_str.split("/")[0].split("?")[0]
                        return int(port_str)  # type: ignore
                except (IndexError, ValueError):
                    # If parsing fails, try direct conversion (will raise error below)
                    pass
            return int(value)  # type: ignore
        elif value_type == float:
            return float(value)  # type: ignore
        else:
            return value  # type: ignore
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Failed to convert environment variable {key}={value} "
            f"to type {value_type.__name__}: {e}"
        )


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple configuration dictionaries.

    Later configs override earlier ones. Nested dicts are merged recursively.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration dictionary
    """
    result: Dict[str, Any] = {}

    for config in configs:
        result = _deep_merge(result, config)

    return result


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with override values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = _deep_merge(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def load_service_config(
    service_name: str,
    config_dir: str = ".",
    config_file: str = "config.yaml",
) -> Dict[str, Any]:
    """
    Load configuration for a service from file and environment.

    Priority (highest to lowest):
    1. Environment variables
    2. Service-specific config file
    3. Defaults

    Args:
        service_name: Name of the service
        config_dir: Directory containing config file
        config_file: Name of config file

    Returns:
        Complete configuration dictionary
    """
    # Load config file
    config_path = Path(config_dir) / config_file
    if config_path.exists():
        file_config = load_config(str(config_path))
    else:
        file_config = {}

    # Common environment variables
    env_config = {
        "service": {
            "name": service_name,
            "environment": get_env("ENVIRONMENT", "development"),
            "debug": get_env("DEBUG", False, value_type=bool),
        },
        "logging": {
            "level": get_env("LOG_LEVEL", "INFO"),
            "format": get_env("LOG_FORMAT", "human"),
        },
        "database": {
            "url": get_env("DATABASE_URL"),
            "host": get_env("POSTGRES_HOST", "postgres"),
            "port": get_env("POSTGRES_PORT", 5432, value_type=int),
            "database": get_env("POSTGRES_DB", "ashiorid"),
            "user": get_env("POSTGRES_USER", "ashiorid_user"),
            "password": get_env("POSTGRES_PASSWORD"),
        },
        "redis": {
            "url": get_env("REDIS_URL"),
            "host": get_env("REDIS_HOST", "redis"),
            "port": get_env("REDIS_PORT", 6379, value_type=int),
            "db": get_env("REDIS_DB", 0, value_type=int),
        },
        "qdrant": {
            "url": get_env("QDRANT_URL"),
            "host": get_env("QDRANT_HOST", "qdrant"),
            "port": get_env("QDRANT_PORT", 6333, value_type=int),
        },
        "monitoring": {
            "prometheus_enabled": get_env("PROMETHEUS_ENABLED", True, value_type=bool),
            "metrics_port": get_env("METRICS_PORT", 9090, value_type=int),
        },
    }

    # Merge configs (env overrides file)
    return merge_configs(file_config, env_config)


# Example usage
if __name__ == "__main__":
    # Test loading config
    print("=== Environment Variable Loading ===")
    print(f"LOG_LEVEL: {get_env('LOG_LEVEL', 'INFO')}")
    print(f"DEBUG: {get_env('DEBUG', False, value_type=bool)}")
    print(f"PORT: {get_env('PORT', 8000, value_type=int)}")

    print("\n=== Config Merging ===")
    config1 = {
        "service": {"name": "test", "port": 8000},
        "database": {"host": "localhost"},
    }
    config2 = {
        "service": {"port": 9000, "debug": True},
        "redis": {"host": "localhost"},
    }
    merged = merge_configs(config1, config2)
    print(yaml.dump(merged, default_flow_style=False))

    print("\n=== Deep Merge Test ===")
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    override = {"a": {"b": 10}, "e": 4}
    result = _deep_merge(base, override)
    print(f"Base: {base}")
    print(f"Override: {override}")
    print(f"Result: {result}")
