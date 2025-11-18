"""
Retry handler with exponential backoff for transient error handling.

This module provides a decorator that implements automatic retry logic with
exponential backoff and jitter for handling transient errors in HTTP requests.
"""

import os
import time
import random
import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Optional

import requests

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default configuration values
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 1000  # milliseconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_JITTER_PERCENTAGE = 0.2


def get_env_config():
    """
    Get retry configuration from environment variables.
    
    Environment variables:
        ADK_MAX_RETRIES: Maximum number of retry attempts (default: 3)
        ADK_RETRY_INTERVAL: Initial retry interval in milliseconds (default: 1000)
        ADK_BACKOFF_MULTIPLIER: Multiplier for exponential backoff (default: 2.0)
        ADK_JITTER_PERCENTAGE: Percentage of jitter to add (default: 0.2)
    
    Returns:
        dict: Configuration dictionary with retry settings
    """
    config = {}
    
    # Read max retries from environment
    if 'ADK_MAX_RETRIES' in os.environ:
        try:
            config['max_retries'] = int(os.environ['ADK_MAX_RETRIES'])
        except ValueError:
            logger.warning(
                f"Invalid ADK_MAX_RETRIES value: {os.environ['ADK_MAX_RETRIES']}. "
                f"Using default: {DEFAULT_MAX_RETRIES}"
            )
            config['max_retries'] = DEFAULT_MAX_RETRIES
    else:
        config['max_retries'] = DEFAULT_MAX_RETRIES
    
    # Read retry interval from environment
    if 'ADK_RETRY_INTERVAL' in os.environ:
        try:
            config['retry_interval'] = int(os.environ['ADK_RETRY_INTERVAL'])
        except ValueError:
            logger.warning(
                f"Invalid ADK_RETRY_INTERVAL value: {os.environ['ADK_RETRY_INTERVAL']}. "
                f"Using default: {DEFAULT_RETRY_INTERVAL}"
            )
            config['retry_interval'] = DEFAULT_RETRY_INTERVAL
    else:
        config['retry_interval'] = DEFAULT_RETRY_INTERVAL
    
    # Read backoff multiplier from environment
    if 'ADK_BACKOFF_MULTIPLIER' in os.environ:
        try:
            config['backoff_multiplier'] = float(os.environ['ADK_BACKOFF_MULTIPLIER'])
        except ValueError:
            logger.warning(
                f"Invalid ADK_BACKOFF_MULTIPLIER value: {os.environ['ADK_BACKOFF_MULTIPLIER']}. "
                f"Using default: {DEFAULT_BACKOFF_MULTIPLIER}"
            )
            config['backoff_multiplier'] = DEFAULT_BACKOFF_MULTIPLIER
    else:
        config['backoff_multiplier'] = DEFAULT_BACKOFF_MULTIPLIER
    
    # Read jitter percentage from environment
    if 'ADK_JITTER_PERCENTAGE' in os.environ:
        try:
            config['jitter_percentage'] = float(os.environ['ADK_JITTER_PERCENTAGE'])
        except ValueError:
            logger.warning(
                f"Invalid ADK_JITTER_PERCENTAGE value: {os.environ['ADK_JITTER_PERCENTAGE']}. "
                f"Using default: {DEFAULT_JITTER_PERCENTAGE}"
            )
            config['jitter_percentage'] = DEFAULT_JITTER_PERCENTAGE
    else:
        config['jitter_percentage'] = DEFAULT_JITTER_PERCENTAGE
    
    return config


def retry_with_backoff(
    max_retries: Optional[int] = None,
    retry_interval: Optional[int] = None,  # milliseconds
    backoff_multiplier: Optional[float] = None,
    jitter_percentage: Optional[float] = None,
    context_name: Optional[str] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that implements exponential backoff with jitter for retrying operations.
    
    This decorator automatically retries failed operations with an exponentially
    increasing delay between attempts. Jitter is added to prevent thundering herd
    problems when multiple clients retry simultaneously.
    
    Args:
        max_retries: Maximum number of retry attempts (default: from ADK_MAX_RETRIES env var or 3)
        retry_interval: Initial retry interval in milliseconds (default: from ADK_RETRY_INTERVAL env var or 1000)
        backoff_multiplier: Multiplier for exponential backoff (default: from ADK_BACKOFF_MULTIPLIER env var or 2.0)
            - With default values: 1s → 2s → 4s → 8s...
        jitter_percentage: Percentage of jitter to add (default: from ADK_JITTER_PERCENTAGE env var or 0.2 = ±20%)
            - Adds random variation to prevent synchronized retries
        context_name: Optional context name for better logging (e.g., node name)
    
    Returns:
        Decorated function with retry capability
    
    Raises:
        Original exception if max retries exceeded
    
    Example:
        >>> @retry_with_backoff(max_retries=5, retry_interval=2000)
        ... def fetch_data():
        ...     response = requests.get("https://api.example.com/data")
        ...     return response.json()
    
    Retryable Errors:
        - requests.Timeout
        - requests.ConnectionError  
        - HTTP 500, 502, 503, 504 (server errors)
        - HTTP 429 (rate limit)
    
    Non-Retryable Errors (fail fast):
        - HTTP 400, 401, 403, 404 (client errors except 429)
    """
    # Get defaults from environment if not provided
    env_config = get_env_config()
    actual_max_retries = max_retries if max_retries is not None else env_config['max_retries']
    actual_retry_interval = retry_interval if retry_interval is not None else env_config['retry_interval']
    actual_backoff_multiplier = backoff_multiplier if backoff_multiplier is not None else env_config['backoff_multiplier']
    actual_jitter_percentage = jitter_percentage if jitter_percentage is not None else env_config['jitter_percentage']
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            current_interval = actual_retry_interval / 1000.0  # Convert to seconds
            last_exception = None
            
            # Extract context for better logging
            func_name = context_name or func.__name__
            
            while attempt <= actual_max_retries:
                try:
                    # Attempt the operation
                    result = func(*args, **kwargs)
                    
                    # Log successful retry if this wasn't the first attempt
                    if attempt > 0:
                        logger.info(
                            f"[{func_name}] Retry {attempt}/{max_retries} succeeded"
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    if not _is_retryable_error(e):
                        logger.error(
                            f"[{func_name}] Non-retryable error: {type(e).__name__}: {str(e)}"
                        )
                        raise
                    
                    attempt += 1
                    
                    # Check if we've exceeded max retries
                    if attempt > actual_max_retries:
                        logger.error(
                            f"[{func_name}] Max retries ({actual_max_retries}) exceeded. "
                            f"Last error: {type(e).__name__}: {str(e)}"
                        )
                        raise
                    
                    # Calculate wait time with jitter
                    jitter = random.uniform(-actual_jitter_percentage, actual_jitter_percentage)
                    wait_time = current_interval * (1 + jitter)
                    
                    # Special handling for rate limit errors (429)
                    if _is_rate_limit_error(e):
                        wait_time *= 2  # Double the wait time for rate limits
                        logger.warning(
                            f"[{func_name}] Rate limit hit. "
                            f"Retry {attempt}/{actual_max_retries} after {wait_time:.2f}s. "
                            f"Error: {str(e)}"
                        )
                    else:
                        logger.warning(
                            f"[{func_name}] Retry {attempt}/{actual_max_retries} "
                            f"after {wait_time:.2f}s wait. "
                            f"Error: {type(e).__name__}: {str(e)}"
                        )
                    
                    # Wait before next retry
                    time.sleep(wait_time)
                    
                    # Increase interval for next attempt (exponential backoff)
                    current_interval *= actual_backoff_multiplier
            
            # Should never reach here, but raise last exception as fallback
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected retry logic error in {func_name}")
        
        return wrapper
    return decorator


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should be retried.
    
    Args:
        error: The exception to evaluate
    
    Returns:
        True if the error is retryable, False otherwise
    
    Retryable errors:
        - Timeout errors (requests.Timeout, socket.timeout)
        - Connection errors (requests.ConnectionError)
        - Server errors (HTTP 5xx)
        - Rate limit errors (HTTP 429)
    
    Non-retryable errors:
        - Client errors (HTTP 4xx except 429)
        - Authentication errors (HTTP 401, 403)
    """
    # Timeout and connection errors are always retryable
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return True
    
    # Check for ClientAPIException (defined in base_api_client.py)
    # We check by class name to avoid circular imports
    if error.__class__.__name__ == 'ClientAPIException':
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
            return _is_retryable_status_code(status_code)
    
    # Check HTTP status codes for requests.HTTPError
    if isinstance(error, requests.HTTPError):
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
            return _is_retryable_status_code(status_code)
    
    # Unknown errors are not retryable by default (fail fast)
    # This prevents infinite retries on unexpected errors
    return False


def _is_retryable_status_code(status_code: int) -> bool:
    """
    Determine if an HTTP status code should trigger a retry.
    
    Args:
        status_code: HTTP status code
    
    Returns:
        True if retryable, False otherwise
    """
    # Server errors (5xx) are retryable
    if 500 <= status_code < 600:
        return True
    
    # Rate limit (429) is retryable
    if status_code == 429:
        return True
    
    # Client errors (4xx) are not retryable
    # These indicate problems with the request itself
    if 400 <= status_code < 500:
        return False
    
    # Other status codes are not retryable
    return False


def _is_rate_limit_error(error: Exception) -> bool:
    """
    Check if the error is a rate limit error (HTTP 429).
    
    Args:
        error: The exception to check
    
    Returns:
        True if this is a rate limit error
    """
    # Check by class name to avoid circular imports
    if error.__class__.__name__ == 'ClientAPIException':
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            return error.response.status_code == 429
    
    if isinstance(error, requests.HTTPError):
        if hasattr(error, 'response') and error.response is not None:
            return error.response.status_code == 429
    
    return False


def create_retry_decorator_from_config(
    max_retries: Optional[int] = None,
    retry_interval: Optional[int] = None,
    context_name: Optional[str] = None
) -> Callable:
    """
    Create a retry decorator with configuration from NodeErrorHandlerConfig.
    
    This is a convenience function for creating retry decorators with
    configuration extracted from YAML error_handler_config settings.
    
    Args:
        max_retries: Maximum retry attempts (None uses default: 3)
        retry_interval: Initial retry interval in ms (None uses default: 1000)
        context_name: Optional context name for logging (e.g., "gather_research")
    
    Returns:
        Configured retry decorator
    
    Example:
        >>> config = NodeErrorHandlerConfig(max_retries=5, retry_interval=2000)
        >>> decorator = create_retry_decorator_from_config(
        ...     max_retries=config.max_retries,
        ...     retry_interval=config.retry_interval,
        ...     context_name="information_gatherer_agent"
        ... )
        >>> @decorator
        ... def call_agent():
        ...     return agent.execute()
    """
    kwargs = {}
    
    if max_retries is not None:
        kwargs['max_retries'] = max_retries
    
    if retry_interval is not None:
        kwargs['retry_interval'] = retry_interval
    
    if context_name is not None:
        kwargs['context_name'] = context_name
    
    return retry_with_backoff(**kwargs)
