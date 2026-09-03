"""
Multi-turn widgets for conversational interactions.

This module provides classes for handling multi-turn conversational widgets
that span multiple exchanges between the user and the system, maintaining
state and context throughout the interaction flow.

Key Components:
    - MultiTurnWidget: Main class for single-field conversational widgets
    - StateManager classes: State persistence strategies
    - ConversationContext: Context tracking across turns
    - TurnRecord: Individual turn records

Example:
    >>> from ibm_watsonx_orchestrate.run.widgets import TextInput
    >>> from ibm_watsonx_orchestrate.run.widgets.multiturn import MultiTurnWidget
    >>> 
    >>> widget = MultiTurnWidget(
    ...     name="username_input",
    ...     input=TextInput(
    ...         name="username",
    ...         title="Enter your username",
    ...         required=True
    ...     )
    ... )
    >>> widget.initialize()
    >>> response = widget.to_response()
"""

from .types import MultiTurnWidget
from .state import (
    StateManager,
    SessionStateManager,
    ContextStateManager,
    HybridStateManager,
    WidgetState,
    StateManagerError,
)
from .context import (
    ConversationContext,
    TurnRecord,
    TurnStatus,
)

__all__ = [
    # Main widget class
    "MultiTurnWidget",
    
    # State management
    "StateManager",
    "SessionStateManager",
    "HybridStateManager",
    "WidgetState",
    "StateManagerError",
    
    # Context tracking
    "ConversationContext",
    "TurnRecord",
    "TurnStatus",
]

# Made with Bob
