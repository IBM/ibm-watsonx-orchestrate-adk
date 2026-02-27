"""
Logger Module

Provides structured logging using structlog.
Equivalent to the TypeScript pino-based logger.
"""

import os
import structlog


def configure_logging() -> None:
    """Configure structlog for the application."""
    log_level = os.getenv("LOG_LEVEL", "info").upper()

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Configure logging on module import
configure_logging()

# Get the logger instance
_logger = structlog.get_logger()


def info(message: str, **data) -> None:
    """Log an informational message."""
    if data:
        _logger.info(message, **data)
    else:
        _logger.info(message)


def warn(message: str, **data) -> None:
    """Log a warning message."""
    if data:
        _logger.warning(message, **data)
    else:
        _logger.warning(message)


def error(message: str, **data) -> None:
    """Log an error message."""
    if data:
        _logger.error(message, **data)
    else:
        _logger.error(message)


def debug(message: str, **data) -> None:
    """Log a debug message."""
    if data:
        _logger.debug(message, **data)
    else:
        _logger.debug(message)


