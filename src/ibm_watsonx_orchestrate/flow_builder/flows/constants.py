"""
Predefined constants for Flow.
"""
import sys

START = sys.intern("__start__")
END = sys.intern("__end__")

ANY_USER = sys.intern("__any_user__")
CURRENT_USER = sys.intern("__current_user__")
FLOW_CONTEXT = sys.intern("FlowContext")

RESERVED = {
    START,
    END,
    FLOW_CONTEXT,
    ANY_USER,
    CURRENT_USER
}


