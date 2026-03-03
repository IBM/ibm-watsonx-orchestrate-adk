"""
Global Store Module

Provides a simple key-value store for global variables that persist
across all MCP servers within the same conversation thread.

Global variables are appropriate for data that should be shared
across all MCP servers in a conversation, such as:
- Customer ID (authenticated user)
- Authentication tokens
- User permissions

NOTE: This is a sample implementation using in-memory storage.
In production, use a persistent store (Redis, database, etc.).
"""

from typing import Any

# In-memory store: dict[thread_id, dict[variable_name, value]]
_global_store: dict[str, dict[str, Any]] = {}


def set_global_variable(thread_id: str, variable_name: str, value: Any) -> None:
    """
    Set a variable in the global store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to store
        value: Value to store (any type)
    """
    if thread_id not in _global_store:
        _global_store[thread_id] = {}
    _global_store[thread_id][variable_name] = value


def get_global_variable(thread_id: str, variable_name: str) -> Any | None:
    """
    Get a variable from the global store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to retrieve

    Returns:
        The stored value, or None if not found
    """
    return _global_store.get(thread_id, {}).get(variable_name)


def delete_global_variable(thread_id: str, variable_name: str) -> bool:
    """
    Delete a variable from the global store for a specific thread.

    Args:
        thread_id: The unique thread identifier from system context
        variable_name: Name of the variable to delete

    Returns:
        True if the variable was deleted, False if it didn't exist
    """
    if thread_id in _global_store and variable_name in _global_store[thread_id]:
        del _global_store[thread_id][variable_name]
        return True
    return False
