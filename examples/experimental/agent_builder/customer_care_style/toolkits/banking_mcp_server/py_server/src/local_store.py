"""
Local Store Module

Provides a simple key-value store for local variables that are
specific to a single MCP server within a conversation thread.

Local variables are appropriate for data that should be isolated
to a specific MCP server, such as:
- Pending transactions awaiting confirmation
- Multi-step operation state
- Temporary calculations
- Draft data before commit

NOTE: This is a sample implementation using in-memory storage.
In production, use a persistent store (Redis, database, etc.).
"""

from typing import Any

# In-memory store: dict[thread_id, dict[variable_name, value]]
_local_store: dict[str, dict[str, Any]] = {}


def set_local_variable(thread_id: str, variable_name: str, value: Any) -> None:
    """
    Set a variable in the local store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to store
        value: Value to store (any type)
    """
    if thread_id not in _local_store:
        _local_store[thread_id] = {}
    _local_store[thread_id][variable_name] = value


def get_local_variable(thread_id: str, variable_name: str) -> Any | None:
    """
    Get a variable from the local store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to retrieve

    Returns:
        The stored value, or None if not found
    """
    return _local_store.get(thread_id, {}).get(variable_name)


def delete_local_variable(thread_id: str, variable_name: str) -> bool:
    """
    Delete a variable from the local store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to delete

    Returns:
        True if the variable was deleted, False if it didn't exist
    """
    if thread_id in _local_store and variable_name in _local_store[thread_id]:
        del _local_store[thread_id][variable_name]
        return True
    return False
