"""
Welcome Tool Module

Contains the welcome tool that is automatically invoked when a thread begins
to greet the customer and authenticate them with a PIN.

Uses dict-based tool definitions to match the TypeScript implementation.
"""

from .customer_database import get_customer_profile_by_phone, verify_customer_pin
from .global_store import set_global_variable
from . import logger


async def welcome_customer_handler(args: dict, extra: dict) -> dict:
    """
    Welcome customer tool handler.

    This is a welcome tool that is automatically invoked when a thread begins.
    It retrieves the customer's telephone number from context, looks up their
    profile, greets them by name, and requests PIN authentication.
    """
    _meta = extra.get("_meta", {})

    logger.info("[WELCOME] Received request", extra=extra)

    # Extract telephone number from customer context
    telephone_number = _meta.get("com.ibm.orchestrate/context", {}).get("telephoneNumber")

    logger.info(f"[WELCOME] Extracted telephoneNumber: {telephone_number}")

    # Look up customer profile by telephone number
    customer_profile = (
        get_customer_profile_by_phone(telephone_number) if telephone_number else None
    )

    # If we can't find telephone number or customer profile, transfer to agent
    if not telephone_number or not customer_profile:
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Welcome! I was unable to find your account. "
                        "Let me connect you with an agent who can assist you."
                    ),
                    "annotations": {"audience": ["user"]},
                }
            ],
            "_meta": {
                "com.ibm.orchestrate/extensions": {
                    "transfer_to_live_agent": {
                        "message_to_human_agent": (
                            "Customer account could not be found. Authentication failed."
                        ),
                        "agent_available": "Please wait while I connect you to an agent.",
                        "agent_unavailable": (
                            "I'm sorry, but no agents are online at the moment. "
                            "Please try again later."
                        ),
                    }
                }
            },
        }

    # Greet the customer by name and request PIN
    # Note: customerId is NOT stored yet - only after successful PIN verification
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Hello {customer_profile.first_name} {customer_profile.last_name}! "
                    "Welcome to CustomerCare Banking."
                ),
                "annotations": {"audience": ["user"]},
            }
        ],
        "_meta": {
            "com.ibm.orchestrate/widget": {
                "type": "number",
                "collection_type": "integer",
                "title": (
                    "For your security, please enter your 4-digit PIN. "
                    "You can speak it or use the keypad, then press #."
                ),
                "min_number": 0,
                "max_number": 9999,
                "min_digits": 4,
                "max_digits": 4,
                "on_event": {
                    "tool": "verify_customer_pin",
                    "parameters": {},
                    "map_input_to": "pin",
                },
            }
        },
    }


async def verify_customer_pin_handler(args: dict, extra: dict) -> dict:
    """
    Verify customer PIN tool handler.

    Verifies the PIN entered by the customer during the welcome flow.
    This tool has visibility: ["app"] to prevent the model from calling it directly.
    """
    pin = args.get("pin", "")
    _meta = extra.get("_meta", {})

    # Extract telephone number from context
    telephone_number = _meta.get("com.ibm.orchestrate/context", {}).get("telephoneNumber")
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")

    # Verify PIN using telephone number
    is_valid = telephone_number and verify_customer_pin(telephone_number, pin)

    if is_valid and telephone_number:
        # Look up customer profile to get customerId
        customer_profile = get_customer_profile_by_phone(telephone_number)

        # Store customer ID in global store ONLY after successful PIN verification
        if thread_id and customer_profile:
            set_global_variable(thread_id, "customerId", customer_profile.customer_id)

        return {
            "content": [
                {
                    "type": "text",
                    "text": "Thank you! Your PIN has been verified. How can I assist you today?",
                    "annotations": {"audience": ["user"]},
                }
            ],
            "_meta": {
                # Signal all MCP servers to refresh their tool/resources lists for this thread
                # since the user is now authenticated and new tools/resources may be available
                "refreshThreadCapabilities": thread_id,
            },
        }
    else:
        # Incorrect PIN - allow re-entry (user can ask to speak with agent if needed) - the model would call the request_agent_handoff tool
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "I'm sorry, but the PIN you entered is incorrect. "
                        "Please try again, or you can ask to speak with an agent "
                        "if you need assistance."
                    ),
                    "annotations": {"audience": ["user"]},
                }
            ],
            "_meta": {
                "com.ibm.orchestrate/widget": {
                    "type": "number",
                    "collection_type": "integer",
                    "title": (
                        "Please enter your 4-digit PIN. "
                        "You can speak it or use the keypad, then press #."
                    ),
                    "min_number": 0,
                    "max_number": 9999,
                    "min_digits": 4,
                    "max_digits": 4,
                    "on_event": {
                        "tool": "verify_customer_pin",
                        "parameters": {},
                        "map_input_to": "pin",
                    },
                }
            },
        }


# Tool definitions in dict format (matching TypeScript structure)
welcome_customer_tool = {
    "name": "welcome_customer",
    "config": {
        "title": "Welcome Customer",
        "description": "Welcome the customer and authenticate them with their PIN",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "_meta": {
            "welcomeTool": True,
            "ui": {
                "visibility": ["app"],
            },
        },
    },
    "handler": welcome_customer_handler,
}

verify_customer_pin_tool = {
    "name": "verify_customer_pin",
    "config": {
        "title": "Verify Customer PIN",
        "description": "Verify the PIN entered by the customer",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pin": {
                    "type": "string",
                    "description": "PIN entered by the customer",
                },
            },
            "required": ["pin"],
        },
    },
    "handler": verify_customer_pin_handler,
}

# Export all welcome tools
welcome_tools = [welcome_customer_tool, verify_customer_pin_tool]
