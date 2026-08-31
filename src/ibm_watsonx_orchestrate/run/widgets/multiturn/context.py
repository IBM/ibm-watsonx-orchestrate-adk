"""
Conversation context tracking for multi-turn widgets.

This module provides classes for tracking conversational context across
multiple turns in a multi-turn widget interaction.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class TurnStatus(str, Enum):
    """Status of a conversation turn"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class TurnRecord(BaseModel):
    """
    Record of a single turn in a multi-turn conversation.
    
    Captures all relevant information about a single interaction turn,
    including user input, widget state, and metadata.
    
    Attributes:
        turn_number: Sequential turn number (1-based)
        timestamp: When this turn occurred
        widget_name: Name of the widget used in this turn
        user_input: User's input for this turn (if any)
        widget_state: State of the widget at this turn
        status: Status of this turn
        metadata: Additional metadata for this turn
        error: Error information if turn failed
    
    Example:
        >>> record = TurnRecord(
        ...     turn_number=1,
        ...     widget_name="username_input",
        ...     user_input="john.doe",
        ...     widget_state={"value": "john.doe"},
        ...     status=TurnStatus.COMPLETED
        ... )
    """
    
    turn_number: int = Field(ge=1, description="Sequential turn number (1-based)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    widget_name: str
    user_input: Optional[Any] = None
    widget_state: Dict[str, Any] = Field(default_factory=dict)
    status: TurnStatus = TurnStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    def mark_completed(self) -> None:
        """Mark this turn as completed"""
        self.status = TurnStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark this turn as failed with error message"""
        self.status = TurnStatus.FAILED
        self.error = error

    def mark_skipped(self) -> None:
        """Mark this turn as skipped"""
        self.status = TurnStatus.SKIPPED


class ConversationContext(BaseModel):
    """
    Tracks context across a multi-turn conversation.
    
    Maintains the complete history of a multi-turn interaction, including
    all turns, their states, and associated metadata. This enables the
    system to maintain context across multiple exchanges.
    
    Attributes:
        conversation_id: Unique identifier for this conversation
        session_id: Optional session identifier for state persistence
        turn_history: List of all turns in this conversation
        metadata: Additional conversation-level metadata
        created_at: When this conversation started
        updated_at: When this conversation was last updated
        is_active: Whether this conversation is still active
    
    Example:
        >>> context = ConversationContext(
        ...     conversation_id="conv_123",
        ...     session_id="session_456"
        ... )
        >>> context.add_turn(
        ...     widget_name="username_input",
        ...     user_input="john.doe",
        ...     widget_state={"value": "john.doe"}
        ... )
    """
    
    conversation_id: str = Field(
        default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}"
    )
    session_id: Optional[str] = None
    turn_history: List[TurnRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    def add_turn(
        self,
        widget_name: str,
        user_input: Optional[Any] = None,
        widget_state: Optional[Dict[str, Any]] = None,
        status: TurnStatus = TurnStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnRecord:
        """
        Add a new turn to the conversation history.
        
        Args:
            widget_name: Name of the widget for this turn
            user_input: User's input (if any)
            widget_state: Current widget state
            status: Status of this turn
            metadata: Additional turn metadata
            
        Returns:
            The created TurnRecord
            
        Example:
            >>> context = ConversationContext()
            >>> turn = context.add_turn(
            ...     widget_name="email_input",
            ...     user_input="user@example.com",
            ...     widget_state={"value": "user@example.com", "valid": True}
            ... )
            >>> turn.turn_number
            1
        """
        turn_number = len(self.turn_history) + 1
        
        turn = TurnRecord(
            turn_number=turn_number,
            widget_name=widget_name,
            user_input=user_input,
            widget_state=widget_state or {},
            status=status,
            metadata=metadata or {},
        )
        
        self.turn_history.append(turn)
        self.updated_at = datetime.utcnow()
        
        return turn

    def get_history(self, limit: Optional[int] = None) -> List[TurnRecord]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of turns to return (most recent first)
            
        Returns:
            List of turn records
            
        Example:
            >>> context = ConversationContext()
            >>> context.add_turn("widget1", "input1")
            >>> context.add_turn("widget2", "input2")
            >>> history = context.get_history(limit=1)
            >>> len(history)
            1
        """
        if limit is None:
            return self.turn_history.copy()
        return self.turn_history[-limit:] if limit > 0 else []

    def get_last_turn(self) -> Optional[TurnRecord]:
        """
        Get the most recent turn.
        
        Returns:
            The last TurnRecord, or None if no turns exist
            
        Example:
            >>> context = ConversationContext()
            >>> context.add_turn("widget1", "input1")
            >>> last = context.get_last_turn()
            >>> last.widget_name
            'widget1'
        """
        return self.turn_history[-1] if self.turn_history else None

    def get_turn_by_number(self, turn_number: int) -> Optional[TurnRecord]:
        """
        Get a specific turn by its number.
        
        Args:
            turn_number: The turn number to retrieve (1-based)
            
        Returns:
            The TurnRecord, or None if not found
            
        Example:
            >>> context = ConversationContext()
            >>> context.add_turn("widget1", "input1")
            >>> turn = context.get_turn_by_number(1)
            >>> turn.widget_name
            'widget1'
        """
        for turn in self.turn_history:
            if turn.turn_number == turn_number:
                return turn
        return None

    def get_current_turn_number(self) -> int:
        """
        Get the current turn number (next turn to be added).
        
        Returns:
            The next turn number
            
        Example:
            >>> context = ConversationContext()
            >>> context.get_current_turn_number()
            1
            >>> context.add_turn("widget1", "input1")
            >>> context.get_current_turn_number()
            2
        """
        return len(self.turn_history) + 1

    def update_last_turn(
        self,
        user_input: Optional[Any] = None,
        widget_state: Optional[Dict[str, Any]] = None,
        status: Optional[TurnStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TurnRecord]:
        """
        Update the most recent turn.
        
        Args:
            user_input: New user input
            widget_state: New widget state
            status: New status
            metadata: Additional metadata to merge
            
        Returns:
            The updated TurnRecord, or None if no turns exist
            
        Example:
            >>> context = ConversationContext()
            >>> context.add_turn("widget1")
            >>> context.update_last_turn(
            ...     user_input="updated_input",
            ...     status=TurnStatus.COMPLETED
            ... )
        """
        if not self.turn_history:
            return None
        
        last_turn = self.turn_history[-1]
        
        if user_input is not None:
            last_turn.user_input = user_input
        if widget_state is not None:
            last_turn.widget_state.update(widget_state)
        if status is not None:
            last_turn.status = status
        if metadata is not None:
            last_turn.metadata.update(metadata)
        
        last_turn.timestamp = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return last_turn

    def close(self) -> None:
        """
        Mark this conversation as closed/inactive.
        
        Example:
            >>> context = ConversationContext()
            >>> context.close()
            >>> context.is_active
            False
        """
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation summary
            
        Example:
            >>> context = ConversationContext()
            >>> context.add_turn("widget1", "input1", status=TurnStatus.COMPLETED)
            >>> summary = context.get_summary()
            >>> summary['total_turns']
            1
        """
        completed_turns = sum(
            1 for turn in self.turn_history 
            if turn.status == TurnStatus.COMPLETED
        )
        failed_turns = sum(
            1 for turn in self.turn_history 
            if turn.status == TurnStatus.FAILED
        )
        
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "total_turns": len(self.turn_history),
            "completed_turns": completed_turns,
            "failed_turns": failed_turns,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_seconds": (self.updated_at - self.created_at).total_seconds(),
        }

# Made with Bob
