import logging
from typing import Any


class SpanLogger:
    """
    A logger wrapper designed for span-based logging that delegates to a standard 
    Python logger while providing a consistent interface with info, debug, warning, 
    error, and critical methods.
    
    This logger is specifically designed for tracing and observability in distributed
    systems where span context is important.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    # ------------------------------------------------------------------
    # Core logging methods
    # ------------------------------------------------------------------

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with severity DEBUG."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with severity INFO."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with severity WARNING."""
        self._logger.warning(msg, *args, **kwargs)

    # Alias for compatibility
    warn = warning

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with severity ERROR."""
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with severity CRITICAL."""
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: Any, *args: Any, exc_info: bool = True, **kwargs: Any) -> None:
        """Log a message with severity ERROR, including exception info."""
        self._logger.exception(msg, *args, exc_info=exc_info, **kwargs)

    def log(self, level: int, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a message with an explicit integer severity level."""
        self._logger.log(level, msg, *args, **kwargs)

    # ------------------------------------------------------------------
    # Level / handler helpers
    # ------------------------------------------------------------------

    def setLevel(self, level: int) -> None:
        """Set the logging level for the underlying logger."""
        self._logger.setLevel(level)

    def isEnabledFor(self, level: int) -> bool:
        """Return True if a message of the given severity would be processed."""
        return self._logger.isEnabledFor(level)

    # ------------------------------------------------------------------
    # Factory method
    # ------------------------------------------------------------------

    @classmethod
    def get_logger(cls, name: str) -> "SpanLogger":
        """
        Return a :class:`SpanLogger` for the given *name*.

        Usage::

            from ibm_watsonx_orchestrate.span_logging import SpanLogger

            logger = SpanLogger.get_logger(__name__)
            logger.info("Hello, world!")

        Args:
            name: Typically ``__name__`` of the calling module.

        Returns:
            A :class:`SpanLogger` instance backed by the standard
            :mod:`logging` logger with the same name.
        """
        return cls(name)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"SpanLogger(name={self._logger.name!r}, level={self._logger.level})"
