"""
State management for multi-turn widgets.

This module provides classes for managing state persistence across
multiple turns in a multi-turn widget interaction. Supports session-based,
context-based, and hybrid state management strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import json
from datetime import datetime, timedelta
import uuid


class StateManager(ABC):
    """
    Abstract base class for state management.
    
    Defines the interface for state persistence strategies. Implementations
    can use different storage backends (memory, Redis, database, etc.).
    """

    @abstractmethod
    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        Save state for a session.
        
        Args:
            session_id: Unique session identifier
            state: State data to persist
            
        Raises:
            StateManagerError: If save operation fails
        """
        pass

    @abstractmethod
    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load state for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            State data if found, None otherwise
            
        Raises:
            StateManagerError: If load operation fails
        """
        pass

    @abstractmethod
    def delete_state(self, session_id: str) -> None:
        """
        Delete state for a session.
        
        Args:
            session_id: Unique session identifier
            
        Raises:
            StateManagerError: If delete operation fails
        """
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """
        Check if state exists for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if state exists, False otherwise
        """
        pass


class StateManagerError(Exception):
    """Exception raised for state management errors"""
    pass


class SessionStateManager(StateManager):
    """
    Session-based state storage using in-memory dictionary.
    
    This implementation stores state in memory. For production use,
    this should be replaced with a persistent backend like Redis or
    a database.
    
    Attributes:
        ttl: Time-to-live for sessions in seconds (default: 1 hour)
        _storage: Internal storage dictionary
        
    Example:
        >>> manager = SessionStateManager(ttl=3600)
        >>> manager.save_state("session_123", {"key": "value"})
        >>> state = manager.load_state("session_123")
        >>> state["key"]
        'value'
    """

    def __init__(self, ttl: int = 3600):
        """
        Initialize session state manager.
        
        Args:
            ttl: Time-to-live for sessions in seconds
        """
        self.ttl = ttl
        self._storage: Dict[str, Dict[str, Any]] = {}

    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Save state with TTL tracking"""
        try:
            self._storage[session_id] = {
                "state": state,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=self.ttl),
            }
        except Exception as e:
            raise StateManagerError(f"Failed to save state: {str(e)}")

    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load state if not expired"""
        try:
            if session_id not in self._storage:
                return None

            session_data = self._storage[session_id]
            
            # Check if expired
            if datetime.utcnow() > session_data["expires_at"]:
                del self._storage[session_id]
                return None

            return session_data["state"]
        except Exception as e:
            raise StateManagerError(f"Failed to load state: {str(e)}")

    def delete_state(self, session_id: str) -> None:
        """Delete state for session"""
        try:
            if session_id in self._storage:
                del self._storage[session_id]
        except Exception as e:
            raise StateManagerError(f"Failed to delete state: {str(e)}")

    def exists(self, session_id: str) -> bool:
        """Check if non-expired state exists"""
        if session_id not in self._storage:
            return False
        
        session_data = self._storage[session_id]
        if datetime.utcnow() > session_data["expires_at"]:
            del self._storage[session_id]
            return False
        
        return True

    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
            
        Example:
            >>> manager = SessionStateManager()
            >>> # ... add some sessions ...
            >>> count = manager.cleanup_expired()
        """
        expired = [
            sid for sid, data in self._storage.items()
            if datetime.utcnow() > data["expires_at"]
        ]
        
        for sid in expired:
            del self._storage[sid]
        
        return len(expired)


class ContextStateManager(StateManager):
    """
    Context-based state storage (stateless with context passing).
    
    This implementation doesn't actually persist state externally.
    Instead, it expects state to be passed in the conversation context.
    This is useful for serverless environments or when external state
    storage is not available.
    
    Example:
        >>> manager = ContextStateManager()
        >>> # State is managed in conversation context, not persisted
        >>> manager.save_state("session_123", {"key": "value"})
        >>> # Returns None - state must be provided via context
        >>> manager.load_state("session_123")
    """

    def __init__(self):
        """Initialize context state manager"""
        # Context-based manager doesn't persist state
        pass

    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        No-op for context-based storage.
        
        State is expected to be embedded in conversation context
        and passed between turns.
        """
        # Context-based storage doesn't persist
        pass

    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns None - state must be provided via context.
        
        In context-based storage, state is passed in the conversation
        context rather than being persisted.
        """
        return None

    def delete_state(self, session_id: str) -> None:
        """No-op for context-based storage"""
        pass

    def exists(self, session_id: str) -> bool:
        """Always returns False for context-based storage"""
        return False


class HybridStateManager(StateManager):
    """
    Hybrid state management combining session and context storage.
    
    Uses session-based storage as primary with context-based as fallback.
    Provides resilience against session store failures while maintaining
    the benefits of persistent storage.
    
    Attributes:
        session_manager: Primary session-based state manager
        context_manager: Fallback context-based state manager
        prefer_session: Whether to prefer session storage (default: True)
        
    Example:
        >>> manager = HybridStateManager(ttl=3600)
        >>> manager.save_state("session_123", {"key": "value"})
        >>> state = manager.load_state("session_123")
        >>> state["key"]
        'value'
    """

    def __init__(self, ttl: int = 3600, prefer_session: bool = True):
        """
        Initialize hybrid state manager.
        
        Args:
            ttl: Time-to-live for session storage in seconds
            prefer_session: Whether to prefer session storage over context
        """
        self.session_manager = SessionStateManager(ttl=ttl)
        self.context_manager = ContextStateManager()
        self.prefer_session = prefer_session

    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        Save state to session storage.
        
        Attempts to save to session storage. If it fails, logs the error
        but doesn't raise (context-based fallback will be used).
        """
        try:
            self.session_manager.save_state(session_id, state)
        except StateManagerError as e:
            # Log error but don't raise - context fallback will be used
            print(f"Warning: Session state save failed: {e}")

    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load state from session storage.
        
        Attempts to load from session storage first. If not found or
        fails, returns None (context-based state should be provided).
        """
        try:
            state = self.session_manager.load_state(session_id)
            if state is not None:
                return state
        except StateManagerError as e:
            print(f"Warning: Session state load failed: {e}")
        
        # Fallback to context (returns None, state should be in context)
        return self.context_manager.load_state(session_id)

    def delete_state(self, session_id: str) -> None:
        """Delete state from session storage"""
        try:
            self.session_manager.delete_state(session_id)
        except StateManagerError as e:
            print(f"Warning: Session state delete failed: {e}")

    def exists(self, session_id: str) -> bool:
        """Check if state exists in session storage"""
        try:
            return self.session_manager.exists(session_id)
        except StateManagerError:
            return False

    def sync_from_context(
        self, 
        session_id: str, 
        context_state: Dict[str, Any]
    ) -> None:
        """
        Synchronize state from context to session storage.
        
        Useful for restoring session state from context after a
        session store failure or restart.
        
        Args:
            session_id: Session identifier
            context_state: State from conversation context
            
        Example:
            >>> manager = HybridStateManager()
            >>> context_state = {"key": "value"}
            >>> manager.sync_from_context("session_123", context_state)
        """
        try:
            self.session_manager.save_state(session_id, context_state)
        except StateManagerError as e:
            print(f"Warning: Failed to sync state from context: {e}")


class WidgetState(BaseModel):
    """
    Represents the state of a multi-turn widget.
    
    Encapsulates all state information for a widget, including
    current values, validation status, and metadata.
    
    Attributes:
        widget_name: Name of the widget
        current_value: Current value of the widget
        is_valid: Whether the current value is valid
        validation_errors: List of validation errors (if any)
        metadata: Additional state metadata
        updated_at: When state was last updated
        
    Example:
        >>> state = WidgetState(
        ...     widget_name="email_input",
        ...     current_value="user@example.com",
        ...     is_valid=True
        ... )
    """
    
    widget_name: str
    current_value: Optional[Any] = None
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_value(self, value: Any, is_valid: bool = True) -> None:
        """
        Update the widget value.
        
        Args:
            value: New value
            is_valid: Whether the value is valid
        """
        self.current_value = value
        self.is_valid = is_valid
        self.updated_at = datetime.utcnow()

    def add_validation_error(self, error: str) -> None:
        """
        Add a validation error.
        
        Args:
            error: Error message
        """
        self.validation_errors.append(error)
        self.is_valid = False
        self.updated_at = datetime.utcnow()

    def clear_validation_errors(self) -> None:
        """Clear all validation errors"""
        self.validation_errors = []
        self.is_valid = True
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "widget_name": self.widget_name,
            "current_value": self.current_value,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetState":
        """
        Create from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            WidgetState instance
        """
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

# Made with Bob
