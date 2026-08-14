"""Utility functions for knowledge base operations."""

from datetime import datetime, timezone

def format_next_occurrence_relative(next_occurrence: str) -> str:
    """
    Format an ISO-8601 UTC timestamp as a human-readable relative string.

    Examples:
        "2026-07-02T14:00:00Z"  ->  "In 20m"
        "2026-07-03T09:00:00Z"  ->  "In 2h"
        "2026-07-09T00:00:00Z"  ->  "In 7d"

    Falls back to the raw string if it cannot be parsed.
    """
    try:
        # Parse ISO-8601 (with or without trailing Z)
        ts = next_occurrence.rstrip("Z")
        dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta_secs = int((dt - now).total_seconds())
        if delta_secs <= 0:
            return "Imminent"
        minutes = delta_secs // 60
        if minutes < 60:
            return f"In {minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"In {hours}h"
        days = hours // 24
        return f"In {days}d"
    except Exception:
        return next_occurrence