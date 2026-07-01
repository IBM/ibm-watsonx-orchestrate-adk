"""Utility functions for knowledge base operations."""

import os
from typing import Optional
from croniter import croniter


def get_minimum_schedule_interval_minutes() -> int:
    """
    Get the minimum allowed schedule interval in minutes.
    Can be configured via KNOWLEDGE_BASE_MIN_SCHEDULE_INTERVAL_MINUTES environment variable.
    
    Returns:
        int: Minimum interval in minutes (default: 60)
    """
    return int(os.environ.get("KNOWLEDGE_BASE_MIN_SCHEDULE_INTERVAL_MINUTES", "60"))


def get_schedule_pattern_interval_minutes(pattern: str) -> Optional[int]:
    """
    Calculate the interval in minutes for a given cron pattern.
    
    Args:
        pattern: Cron pattern string (e.g., '0 0 * * *')
    
    Returns:
        Optional[int]: Interval in minutes, or None if pattern is invalid or interval cannot be determined
    """
    try:
        # Validate the cron pattern
        if not croniter.is_valid(pattern):
            return None
        
        # Create a croniter instance
        cron = croniter(pattern)
        
        # Get the next two occurrences
        next_time = cron.get_next()
        following_time = cron.get_next()
        
        # Calculate the interval in minutes
        interval_seconds = following_time - next_time
        interval_minutes = int(interval_seconds / 60)
        
        return interval_minutes
    except Exception:
        # If any error occurs, return None
        return None