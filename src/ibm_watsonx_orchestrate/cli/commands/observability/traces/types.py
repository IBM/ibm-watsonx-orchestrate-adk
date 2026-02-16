"""Type definitions for traces CLI commands."""

from enum import Enum


class SortField(str, Enum):
    """Valid sort fields for trace search."""
    START_TIME = "start_time"
    END_TIME = "end_time"


class SortDirection(str, Enum):
    """Valid sort directions for trace search."""
    ASC = "asc"
    DESC = "desc"

# Made with Bob
