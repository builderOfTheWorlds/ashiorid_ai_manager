"""
Centralized logging configuration for Ashiorid AI Manager.

Supports two output formats:
- JSON: Structured logging for production (machine-readable)
- HUMAN: Pretty-printed logs for development (human-readable)

Environment variables:
- LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- LOG_FORMAT: Output format (json or human)
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
import os


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON for machine parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """
    Custom formatter that outputs pretty-printed logs for human reading.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        # Get color for log level
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build log message
        log_parts = [
            f"{color}[{record.levelname}]{reset}",
            f"[{timestamp}]",
            f"[{record.name}]",
            record.getMessage(),
        ]

        # Add location info for errors
        if record.levelno >= logging.ERROR:
            log_parts.append(
                f"({record.module}.{record.funcName}:{record.lineno})"
            )

        message = " ".join(log_parts)

        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    service_name: str = "ashiorid",
    log_level: str = None,
    log_format: str = None,
) -> None:
    """
    Set up logging configuration for a service.

    Args:
        service_name: Name of the service (used as logger name)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to LOG_LEVEL env var or INFO
        log_format: Output format ('json' or 'human')
                   Defaults to LOG_FORMAT env var or 'human'
    """
    # Get configuration from environment or defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "human")

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Set formatter based on format choice
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = HumanFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set logging level for some noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log initial message
    logger = logging.getLogger(service_name)
    logger.info(
        f"Logging initialized for {service_name} "
        f"(level={log_level}, format={log_format})"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function for adding structured data to logs
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """
    Log a message with additional context data.

    Args:
        logger: Logger instance
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        message: Log message
        **context: Additional key-value pairs to include in log
    """
    # Create a LogRecord with extra fields
    record = logger.makeRecord(
        logger.name,
        level,
        "(log_with_context)",
        0,
        message,
        (),
        None,
    )
    record.extra_fields = context
    logger.handle(record)


# Example usage
if __name__ == "__main__":
    # Test JSON format
    print("=== JSON Format ===")
    setup_logging("test-service", log_level="DEBUG", log_format="json")
    logger = get_logger("test-service")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    try:
        1 / 0
    except Exception:
        logger.exception("An exception occurred")

    print("\n=== Human Format ===")
    setup_logging("test-service", log_level="DEBUG", log_format="human")
    logger = get_logger("test-service")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    try:
        1 / 0
    except Exception:
        logger.exception("An exception occurred")
