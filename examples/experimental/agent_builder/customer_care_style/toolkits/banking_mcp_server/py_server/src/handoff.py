"""
Agent Handoff Tools Module

Contains tool definitions for transferring customers to human agents.
Uses dict-based tool definitions to match the TypeScript implementation.
"""


async def request_agent_handoff_handler(args: dict, extra: dict) -> dict:
    """
    Request agent handoff tool handler.

    Presents the user with options to either request a callback or
    connect to an agent in real-time.
    """
    reason = args.get("reason")
    customer_id = args.get("customerId")

    customer_context = (
        f" Customer ID: {customer_id}." if customer_id else " Customer not yet authenticated."
    )
    context_message = (
        f"User requested agent assistance. Reason: {reason}.{customer_context}"
        if reason
        else f"User requested to speak with an agent.{customer_context}"
    )

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    "I'd be happy to connect you with one of our agents. "
                    "How would you like to proceed?"
                ),
                "annotations": {"audience": ["user"]},
            }
        ],
        "_meta": {
            "com.ibm.orchestrate/widget": {
                "type": "options",
                "title": "Choose Connection Type",
                "description": "Select how you would like to connect with an agent:",
                "options": [
                    {"value": "realtime", "label": "Connect Now"},
                    {"value": "callback", "label": "Request Callback"},
                ],
                "on_event": {
                    "tool": "process_agent_handoff_choice",
                    "parameters": {"context_message": context_message},
                    "map_input_to": "handoff_type",
                },
            }
        },
    }


async def process_agent_handoff_choice_handler(args: dict, extra: dict) -> dict:
    """
    Process agent handoff choice tool handler.

    Handles the user's selection from the handoff options.
    For real-time handoff, issues the transfer_to_live_agent response type.
    For callback, confirms the callback request.

    This tool has visibility: ["app"] to prevent the model from calling it directly.
    """
    handoff_type = args.get("handoff_type", "")
    context_message = args.get("context_message", "")

    if handoff_type == "realtime":
        # Issue the transfer_to_live_agent response type for real-time handoff
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Connecting you to an agent...",
                    "annotations": {"audience": ["user"]},
                }
            ],
            "_meta": {
                "com.ibm.orchestrate/extensions": {
                    "transfer_to_live_agent": {
                        "message_to_human_agent": context_message,
                        "agent_available": "Please wait while I connect you to an agent.",
                        "agent_unavailable": (
                            "I'm sorry, but no agents are online at the moment. "
                            "Please try again later or request a callback."
                        ),
                    }
                }
            },
        }
    else:
        # Handle callback request
        # In a real implementation, this would create a callback ticket/request
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Thank you! I've submitted your callback request. "
                        "One of our agents will contact you within the next business day. "
                        "You'll receive a confirmation email shortly with the details."
                    ),
                    "annotations": {"audience": ["user"]},
                }
            ]
        }


# Tool definitions in dict format (matching TypeScript structure)
request_agent_handoff_tool = {
    "name": "request_agent_handoff",
    "config": {
        "title": "Request Agent Handoff",
        "description": (
            "Initiate a handoff to a human agent. "
            "Presents options for callback or real-time connection."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for requesting agent assistance",
                },
            },
            "required": [],
        },
    },
    "handler": request_agent_handoff_handler,
}

process_agent_handoff_choice_tool = {
    "name": "process_agent_handoff_choice",
    "config": {
        "title": "Process Agent Handoff Choice",
        "description": (
            "Process the user selection for agent handoff type (real-time or callback)"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "handoff_type": {
                    "type": "string",
                    "description": "Type of handoff selected (realtime or callback)",
                },
                "context_message": {
                    "type": "string",
                    "description": "Context message for the agent",
                },
            },
            "required": ["handoff_type", "context_message"],
        },
        "_meta": {
            "ui": {
                "visibility": ["app"],
            },
        },
    },
    "handler": process_agent_handoff_choice_handler,
}

# Export all handoff tools
handoff_tools = [request_agent_handoff_tool, process_agent_handoff_choice_tool]
