"""
Multi-turn widget types for conversational interactions.

This module provides the MultiTurnWidget class for handling single-field
widgets across multiple conversational turns, with state management and
context tracking.

The MultiTurnWidget completely reuses FormInput components from the FormWidget,
ensuring that any future changes to form widgets automatically apply to
multi-turn flows as well.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union
import uuid

from ..forms.types import FormInput
from .context import ConversationContext, TurnStatus
from .state import (
    StateManager,
    HybridStateManager,
    WidgetState,
    StateManagerError,
)


class MultiTurnWidget(BaseModel):
    """
    Multi-turn conversational widget for single-field interactions.
    
    Supports state persistence and context tracking across multiple
    conversational exchanges while completely reusing FormInput components
    from FormWidget. This ensures that any future changes to form widgets
    automatically apply to multi-turn flows as well.
    
    This class enables tools to collect user input through a series of
    conversational turns, maintaining state and context throughout the
    interaction. Each widget focuses on a single field per turn, creating
    a more natural conversational flow compared to multi-field forms.
    
    Attributes:
        name: Unique widget identifier (auto-generated if not provided)
        input: Single FormInput widget (completely reused from FormWidget)
        response_type: Always "multiturn_form" to distinguish from forms
        session_id: Optional session identifier for state persistence
        context: Conversational context tracking
        state_manager: State persistence manager (hybrid by default)
        turn_number: Current turn in conversation (1-based)
        is_complete: Whether interaction is finished
        description: Optional widget description
        
    Note:
        The title parameter is not needed at the MultiTurnWidget level.
        Titles should be specified on the individual FormInput items
        (e.g., TextInput.title, NumberInput.title, etc.).
        
    Example:
        >>> from ibm_watsonx_orchestrate.run.widgets import TextInput
        >>>
        >>> widget = MultiTurnWidget(
        ...     name="username_input",
        ...     input=TextInput(
        ...         name="username",
        ...         title="Enter your username",  # Title on the input
        ...         required=True,
        ...         placeholder="john.doe"
        ...     )
        ... )
        >>>
        >>> # Initialize the widget
        >>> widget.initialize()
        >>>
        >>> # Generate response for user
        >>> response = widget.to_response()
        >>>
        >>> # After user provides input
        >>> widget.update_state(user_input="john.doe")
        >>>
        >>> # Mark as complete
        >>> widget.mark_complete()
        >>>
        >>> # Cleanup
        >>> widget.cleanup()
    """
    
    # Core fields
    name: str = Field(
        default_factory=lambda: f"multiturn_{uuid.uuid4().hex[:12]}"
    )
    input: FormInput  # Completely reused from FormWidget
    response_type: str = Field(default="multiturn_form", frozen=True)
    
    # State management
    session_id: Optional[str] = None
    context: ConversationContext = Field(
        default_factory=ConversationContext
    )
    state_manager: StateManager = Field(
        default_factory=lambda: HybridStateManager(ttl=3600)
    )
    
    # Lifecycle tracking
    turn_number: int = Field(default=1, ge=1)
    is_complete: bool = False
    
    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

    def initialize(self, session_id: Optional[str] = None) -> None:
        """
        Initialize widget state and context.
        
        Sets up the widget for a new multi-turn interaction, including
        generating or validating session ID, initializing state manager,
        and creating conversation context.
        
        Args:
            session_id: Optional session identifier. If not provided,
                       a new one will be generated.
                       
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="email", title="Email")
            ... )
            >>> widget.initialize(session_id="session_123")
            >>> widget.session_id
            'session_123'
        """
        # Generate or use provided session ID
        if session_id:
            self.session_id = session_id
        elif not self.session_id:
            self.session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        # Link session to context
        self.context.session_id = self.session_id
        
        # Initialize turn number
        self.turn_number = 1
        self.is_complete = False
        
        # Try to load existing state
        try:
            existing_state = self.state_manager.load_state(self.session_id)
            if existing_state:
                # Restore from existing state
                self._restore_from_state(existing_state)
        except StateManagerError as e:
            # Log but continue - will start fresh
            print(f"Warning: Could not load existing state: {e}")

    def update_state(
        self,
        user_input: Any,
        metadata: Optional[Dict[str, Any]] = None,
        is_valid: bool = True,
        validation_errors: Optional[list[str]] = None,
    ) -> None:
        """
        Update widget state after user input.
        
        Validates user input, updates internal state, persists to state
        manager, and updates context with turn record.
        
        Args:
            user_input: User's input for this turn
            metadata: Optional additional metadata
            is_valid: Whether the input is valid
            validation_errors: List of validation errors (if any)
            
        Raises:
            StateManagerError: If state persistence fails
            
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="email", title="Email")
            ... )
            >>> widget.initialize()
            >>> widget.update_state(
            ...     user_input="user@example.com",
            ...     is_valid=True
            ... )
            >>> widget.turn_number
            2
        """
        # Create widget state
        widget_state = WidgetState(
            widget_name=self.input.name,
            current_value=user_input,
            is_valid=is_valid,
            validation_errors=validation_errors or [],
            metadata=metadata or {},
        )
        
        # Add turn to context
        turn = self.context.add_turn(
            widget_name=self.input.name,
            user_input=user_input,
            widget_state=widget_state.to_dict(),
            status=TurnStatus.COMPLETED if is_valid else TurnStatus.FAILED,
            metadata=metadata or {},
        )
        
        # Persist state
        state_data = {
            "widget_name": self.name,
            "input_name": self.input.name,
            "turn_number": self.turn_number,
            "widget_state": widget_state.to_dict(),
            "context": self.context.model_dump(),
            "is_complete": self.is_complete,
        }
        
        if self.session_id:
            try:
                self.state_manager.save_state(self.session_id, state_data)
            except StateManagerError as e:
                print(f"Warning: Failed to persist state: {e}")
        
        # Increment turn number
        self.turn_number += 1

    def get_context(self) -> Dict[str, Any]:
        """
        Retrieve current conversational context.
        
        Returns:
            Dictionary containing conversation context
            
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="name", title="Name")
            ... )
            >>> widget.initialize()
            >>> context = widget.get_context()
            >>> context["conversation_id"]
            'conv_...'
        """
        return {
            "conversation_id": self.context.conversation_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "is_complete": self.is_complete,
            "widget_name": self.name,
            "input_name": self.input.name,
            "turn_history": [
                turn.model_dump() for turn in self.context.turn_history
            ],
        }

    def set_context(self, context: Dict[str, Any]) -> None:
        """
        Update conversational context.
        
        Useful for restoring context from external source or
        synchronizing with conversation state.
        
        Args:
            context: Context dictionary to apply
            
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="name", title="Name")
            ... )
            >>> widget.initialize()
            >>> context = {"turn_number": 3, "is_complete": True}
            >>> widget.set_context(context)
            >>> widget.turn_number
            3
        """
        if "turn_number" in context:
            self.turn_number = context["turn_number"]
        if "is_complete" in context:
            self.is_complete = context["is_complete"]
        if "session_id" in context:
            self.session_id = context["session_id"]
            self.context.session_id = context["session_id"]

    def mark_complete(self) -> None:
        """
        Mark the multi-turn interaction as complete.
        
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="name", title="Name")
            ... )
            >>> widget.initialize()
            >>> widget.mark_complete()
            >>> widget.is_complete
            True
        """
        self.is_complete = True
        self.context.close()
        
        # Update persisted state
        if self.session_id:
            try:
                state_data = self.state_manager.load_state(self.session_id)
                if state_data:
                    state_data["is_complete"] = True
                    self.state_manager.save_state(self.session_id, state_data)
            except StateManagerError as e:
                print(f"Warning: Failed to update completion state: {e}")

    def cleanup(self, delete_state: bool = False) -> None:
        """
        Cleanup resources and optionally delete state.
        
        Args:
            delete_state: Whether to delete persisted state (default: False)
            
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="name", title="Name")
            ... )
            >>> widget.initialize()
            >>> widget.cleanup(delete_state=True)
        """
        # Mark as complete if not already
        if not self.is_complete:
            self.mark_complete()
        
        # Optionally delete state
        if delete_state and self.session_id:
            try:
                self.state_manager.delete_state(self.session_id)
            except StateManagerError as e:
                print(f"Warning: Failed to delete state: {e}")

    def to_response(self) -> Dict[str, Any]:
        """
        Generate response payload for the chat interface.
        
        Creates a response in the format expected by the WatsonX Orchestrate
        runtime, following the Arch.Guide specification for multiturn_form.
        
        Returns:
            Dictionary containing the complete response structure
            
        Example:
            >>> from ibm_watsonx_orchestrate.run.widgets import TextInput
            >>>
            >>> widget = MultiTurnWidget(
            ...     name="email_input",
            ...     input=TextInput(
            ...         name="email",
            ...         title="Email Address",  # Title on the input
            ...         required=True
            ...     )
            ... )
            >>> widget.initialize()
            >>> response = widget.to_response()
            >>> response["response_type"]
            'multiturn_form'
        """
        # Build JSON schema
        json_schema = {
            "type": "object",
            "properties": {
                self.input.name: self.input.to_json_schema()
            },
        }
        
        if self.input.required:
            json_schema["required"] = [self.input.name]
        
        if self.title:
            json_schema["title"] = self.title
        
        if self.description:
            json_schema["description"] = self.description
        
        # Build UI schema
        ui_schema = {
            self.input.name: self.input.to_ui_schema()
        }
        
        # Build form data (default values)
        form_data = {}
        default_value = self.input.to_form_data()
        if default_value is not None:
            form_data[self.input.name] = default_value
        
        # Build complete response
        response = {
            "response_type": self.response_type,
            "name": self.name,
            "json_schema": json_schema,
            "ui_schema": ui_schema,
            "form_data": form_data,
        }
        
        # Add context information
        if self.session_id:
            response["session_id"] = self.session_id
        
        response["context"] = {
            "conversation_id": self.context.conversation_id,
            "turn_number": self.turn_number,
            "is_complete": self.is_complete,
        }
        
        return response

    def _restore_from_state(self, state_data: Dict[str, Any]) -> None:
        """
        Restore widget from persisted state.
        
        Args:
            state_data: State data to restore from
        """
        if "turn_number" in state_data:
            self.turn_number = state_data["turn_number"]
        if "is_complete" in state_data:
            self.is_complete = state_data["is_complete"]
        if "context" in state_data:
            # Restore context
            try:
                self.context = ConversationContext(**state_data["context"])
            except Exception as e:
                print(f"Warning: Could not restore context: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the multi-turn interaction.
        
        Returns:
            Dictionary with interaction summary
            
        Example:
            >>> widget = MultiTurnWidget(
            ...     input=TextInput(name="name", title="Name")
            ... )
            >>> widget.initialize()
            >>> widget.update_state("John Doe")
            >>> summary = widget.get_summary()
            >>> summary["total_turns"]
            1
        """
        context_summary = self.context.get_summary()
        
        return {
            "widget_name": self.name,
            "input_name": self.input.name,
            "session_id": self.session_id,
            "current_turn": self.turn_number,
            "is_complete": self.is_complete,
            "conversation_summary": context_summary,
        }

    def model_dump(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        """
        Override Pydantic's model_dump to return response structure.
        
        This allows the widget to be serialized directly to the
        response format expected by the runtime.
        """
        return self.to_response()

    def dict(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        """Override Pydantic v1 dict() for backward compatibility"""
        return self.model_dump(**kwargs)

# Made with Bob
