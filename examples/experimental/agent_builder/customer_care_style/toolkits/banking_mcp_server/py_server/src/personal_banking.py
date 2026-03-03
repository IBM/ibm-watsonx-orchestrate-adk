"""
Personal Banking Tools Module

Contains tool definitions for personal banking operations.
Uses dict-based tool definitions to match the TypeScript implementation.
"""

from dataclasses import asdict
from datetime import datetime, timedelta
import random
import string

from .personal_banking_service import PersonalBankingService
from .local_store import set_local_variable, get_local_variable, delete_local_variable
from . import logger


async def get_account_balance_handler(args: dict, extra: dict) -> dict:
    """Get account balance tool handler."""
    customer_id = args.get("customerId")
    account_type = args.get("account_type", "")

    if not customer_id:
        raise ValueError("Customer ID is required")

    account_balance = PersonalBankingService.get_account_balance(customer_id, account_type)

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Account Balance:\n"
                    f"Customer ID: {account_balance['customer_id']}\n"
                    f"Account Type: {account_balance['account_type']}\n"
                    f"Balance: ${account_balance['balance']:.2f} {account_balance['currency']}\n"
                    f"As of: {account_balance['as_of_date']}"
                ),
                "annotations": {"audience": ["user"]},
            }
        ],
        "structuredContent": account_balance,
    }


async def get_account_statement_handler(args: dict, extra: dict) -> dict:
    """Get account statement tool handler."""
    customer_id = args.get("customerId")
    account_type = args.get("account_type", "")
    days = args.get("days", 30)

    if not customer_id:
        raise ValueError("Customer ID is required")

    account_statement = PersonalBankingService.get_account_statement(
        customer_id, account_type, days
    )

    transaction_text = "\n".join(
        f"  {t['date']} | {t['description']:<35} | "
        f"{'+'if t['amount'] >= 0 else ''}${t['amount']:>10.2f} | "
        f"Balance: ${t['balance']:.2f}"
        for t in account_statement["transactions"]
    )

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Account Statement:\n"
                    f"Customer ID: {account_statement['customer_id']}\n"
                    f"Account Type: {account_statement['account_type']}\n"
                    f"Period: {account_statement['start_date']} to {account_statement['end_date']}\n\n"
                    f"Recent Transactions:\n{transaction_text}"
                ),
            }
        ],
        "structuredContent": account_statement,
    }


async def prepare_money_transfer_handler(args: dict, extra: dict) -> dict:
    """
    Prepare money transfer tool handler.

    This is the FIRST STEP in a two-step transaction pattern.
    It collects transfer details through interactive widgets (account pickers, date picker)
    and then presents a confirmation dialog with the transfer details.
    """
    logger.info(f"[TRANSFER] Handler called with args: {args}")
    
    customer_id = args.get("customerId")
    amount = args.get("amount", 0)
    from_account_id = args.get("from_account_id")
    to_account_id = args.get("to_account_id")
    scheduled_date = args.get("scheduled_date")
    memo = args.get("memo")
    
    logger.info(f"[TRANSFER] Parsed: customer_id={customer_id}, amount={amount}, from={from_account_id}, to={to_account_id}")

    _meta = extra.get("_meta", {})
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")

    if not thread_id:
        raise ValueError("Thread ID is required")

    if not customer_id:
        raise ValueError("Customer ID is required")

    all_accounts = PersonalBankingService.get_accounts(customer_id)
    logger.info(f"[TRANSFER] Got {len(all_accounts)} accounts")

    # Step 1: If from_account_id is missing, show picker for "from" account
    if not from_account_id:
        from_accounts = [
            acc
            for acc in all_accounts
            if acc.can_transfer_from and acc.account_id != to_account_id
        ]

        picker_options = [
            {
                "value": acc.account_id,
                "label": f"{acc.account_name}{' (' + acc.account_holder + ')' if acc.account_holder else ''}",
                "description": f"{acc.account_type} - {acc.account_id}",
            }
            for acc in from_accounts
        ]

        return {
            "_meta": {
                "com.ibm.orchestrate/widget": {
                    "type": "options",
                    "title": "Select Account to Transfer From",
                    "description": "Choose the account you want to transfer money from:",
                    "options": picker_options,
                    "on_event": {
                        "tool": "prepare_money_transfer",
                        "parameters": {
                            k: v for k, v in {
                                "amount": amount,
                                "from_account_id": from_account_id,
                                "to_account_id": to_account_id,
                                "scheduled_date": scheduled_date,
                                "memo": memo,
                            }.items() if v is not None
                        },
                        "map_input_to": "from_account_id",
                    },
                }
            }
        }

    # Step 2: Check if the from account is locked
    selected_from_account = next(
        (acc for acc in all_accounts if acc.account_id == from_account_id), None
    )

    if selected_from_account and selected_from_account.is_locked:
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"I'm sorry, but your {selected_from_account.account_name} account "
                        f"({selected_from_account.account_id}) is currently locked. "
                        "You'll need to speak with a customer service agent to resolve "
                        "this issue before you can transfer funds from this account."
                    ),
                    "annotations": {"audience": ["user"]},
                }
            ],
            "_meta": {
                "nextTool": {
                    "name": "request_agent_handoff",
                    "arguments": {
                        "reason": (
                            f"Customer attempted to transfer from locked account: "
                            f"{selected_from_account.account_name} ({selected_from_account.account_id})"
                        ),
                    },
                }
            },
        }

    # Step 3: If to_account_id is missing, show picker for "to" account
    if not to_account_id:
        to_accounts = [
            acc
            for acc in all_accounts
            if acc.can_transfer_to and acc.account_id != from_account_id
        ]

        picker_options = [
            {
                "value": acc.account_id,
                "label": f"{acc.account_name}{' (' + acc.account_holder + ')' if acc.account_holder else ''}",
                "description": f"{acc.account_type} - {acc.account_id}",
            }
            for acc in to_accounts
        ]

        return {
            "_meta": {
                "com.ibm.orchestrate/widget": {
                    "type": "options",
                    "title": "Select Account to Transfer To",
                    "description": "Choose the account you want to transfer money to:",
                    "options": picker_options,
                    "on_event": {
                        "tool": "prepare_money_transfer",
                        "parameters": {
                            k: v for k, v in {
                                "amount": amount,
                                "from_account_id": from_account_id,
                                "to_account_id": to_account_id,
                                "scheduled_date": scheduled_date,
                                "memo": memo,
                            }.items() if v is not None
                        },
                        "map_input_to": "to_account_id",
                    },
                }
            }
        }

    # Step 4: If scheduled_date is missing, show date picker
    if not scheduled_date:
        today = datetime.now()
        min_date = today + timedelta(days=3)
        max_date = today + timedelta(days=30)

        return {
            "_meta": {
                "com.ibm.orchestrate/widget": {
                    "type": "datetime",
                    "collection_type": "date",
                    "title": "Select Transfer Date",
                    "description": (
                        "Choose when you want the transfer to occur "
                        "(must be at least 3 days from now, within 30 days):"
                    ),
                    "min_datetime": min_date.strftime("%Y-%m-%d"),
                    "max_datetime": max_date.strftime("%Y-%m-%d"),
                    "on_event": {
                        "tool": "prepare_money_transfer",
                        "parameters": {
                            k: v for k, v in {
                                "amount": amount,
                                "from_account_id": from_account_id,
                                "to_account_id": to_account_id,
                                "scheduled_date": scheduled_date,
                                "memo": memo,
                            }.items() if v is not None
                        },
                        "map_input_to": "scheduled_date",
                    },
                }
            }
        }

    # Step 5: All required info collected, validate the transfer
    validation = PersonalBankingService.validate_transfer(
        customer_id, from_account_id, to_account_id, amount
    )
    from_account = validation["from_account"]
    to_account = validation["to_account"]

    # Generate transaction ID
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
    transaction_id = f"TXN-{int(datetime.now().timestamp() * 1000)}-{random_suffix}"

    # Create transaction details object
    transaction_details = {
        "customer_id": customer_id,
        "transaction_id": transaction_id,
        "from_account_id": from_account_id,
        "from_account_name": from_account.account_name,
        "to_account_id": to_account_id,
        "to_account_name": to_account.account_name,
        "amount": amount,
        "scheduled_date": scheduled_date,
        "memo": memo,
        "created_at": datetime.now().isoformat(),
    }

    # Store transaction details in LOCAL STORE
    set_local_variable(thread_id, f"transaction_{transaction_id}", transaction_details)

    schedule_text = (
        f"\n- **Scheduled Date:** {scheduled_date}"
        if scheduled_date
        else "\n- **Processing:** Immediate"
    )
    memo_text = f"\n- **Memo:** {memo}" if memo else ""

    # Confirmation widget definition
    confirmation_widget = {
        "type": "confirmation",
        "title": "Confirm Transfer",
        "confirmation_text": (
            f"## Confirm Transfer\n\n"
            f"Please review the transfer details below and confirm to proceed:\n\n"
            f"**Transfer Details:**\n"
            f"- **From Account:** {from_account.account_name} ({from_account_id})\n"
            f"- **To Account:** {to_account.account_name} ({to_account_id})\n"
            f"- **Amount:** ${amount:.2f}{schedule_text}{memo_text}\n\n"
            f"**Transaction ID:** {transaction_id}"
        ),
        "on_confirm": {
            "tool": "confirm_or_cancel_money_transfer",
            "parameters": {
                "transaction_id": transaction_id,
                "action": "confirm",
            },
        },
        "on_cancel": {
            "tool": "confirm_or_cancel_money_transfer",
            "parameters": {
                "transaction_id": transaction_id,
                "action": "cancel",
            },
        },
    }

    return {"_meta": {"com.ibm.orchestrate/widget": confirmation_widget}}


async def confirm_or_cancel_money_transfer_handler(args: dict, extra: dict) -> dict:
    """
    Confirm or cancel money transfer tool handler.

    This is the SECOND STEP in a two-step transaction pattern.
    IMPORTANT: This tool is hidden from the model (visibility: ["app"]).
    """
    customer_id = args.get("customerId")
    transaction_id = args.get("transaction_id", "")
    action = args.get("action", "")

    _meta = extra.get("_meta", {})
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")

    if not thread_id:
        raise ValueError("Thread ID is required")

    # Retrieve transaction from LOCAL STORE
    transaction = get_local_variable(thread_id, f"transaction_{transaction_id}")

    if not transaction:
        raise ValueError(
            f"Transaction {transaction_id} not found. "
            "It may have expired or been processed already."
        )

    # Verify transaction belongs to this customer (security check)
    if transaction["customer_id"] != customer_id:
        raise ValueError("Transaction does not belong to this customer")

    # Clean up local variable
    delete_local_variable(thread_id, f"transaction_{transaction_id}")

    if action == "cancel":
        schedule_text = (
            f"\n- Scheduled Date: {transaction['scheduled_date']}"
            if transaction.get("scheduled_date")
            else ""
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Transfer Cancelled\n\n"
                        f"Transaction ID: {transaction_id}\n\n"
                        f"The transfer has been cancelled and no funds were moved.\n\n"
                        f"Transfer Details:\n"
                        f"- From Account: {transaction['from_account_name']} ({transaction['from_account_id']})\n"
                        f"- To Account: {transaction['to_account_name']} ({transaction['to_account_id']})\n"
                        f"- Amount: ${transaction['amount']:.2f}{schedule_text}"
                    ),
                    "annotations": {"audience": ["user"]},
                },
                {
                    "type": "text",
                    "text": (
                        f"The transfer with transaction ID {transaction_id} "
                        "has been cancelled by the user."
                    ),
                    "annotations": {"audience": ["assistant"]},
                },
            ]
        }

    # Handle confirmation - process the actual transfer
    transfer_result = PersonalBankingService.transfer_money(
        transaction["customer_id"],
        transaction["from_account_id"],
        transaction["to_account_id"],
        transaction["amount"],
        transaction.get("scheduled_date"),
        transaction.get("memo"),
    )

    schedule_text = (
        f"\n- Scheduled Date: {transaction['scheduled_date']}\n- Status: Scheduled"
        if transaction.get("scheduled_date")
        else "\n- Status: Completed immediately"
    )

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Transfer Confirmed Successfully!\n\n"
                    f"Confirmation Number: {transfer_result.transfer_id}\n"
                    f"Transaction ID: {transaction_id}\n\n"
                    f"Transfer Details:\n"
                    f"- From Account: {transaction['from_account_name']} ({transaction['from_account_id']})\n"
                    f"- To Account: {transaction['to_account_name']} ({transaction['to_account_id']})\n"
                    f"- Amount: ${transaction['amount']:.2f}{schedule_text}\n"
                    f"- Confirmed At: {transfer_result.timestamp}\n\n"
                    f"Your transfer has been processed successfully."
                ),
                "annotations": {"audience": ["user"]},
            }
        ]
    }


async def available_accounts_resource_handler(args: dict, extra: dict) -> str:
    """Available Accounts Resource handler."""
    customer_id = args.get("customerId")

    if not customer_id:
        return "Error: Customer ID is required to retrieve accounts."

    accounts = PersonalBankingService.get_accounts(customer_id)

    # Format accounts for display
    account_list = "\n\n".join(
        f"• {acc.account_id} - {acc.account_name}"
        f"{' (' + acc.account_holder + ')' if acc.account_holder else ''}\n"
        f"  Type: {acc.account_type} | "
        f"Transfer From: {'✓' if acc.can_transfer_from else '✗'} | "
        f"Transfer To: {'✓' if acc.can_transfer_to else '✗'}"
        for acc in accounts
    )

    return f"Available Accounts for Transfers:\n\n{account_list}\n\nNote: Use these account IDs when transferring money."


# Tool definitions in dict format (matching TypeScript structure)
get_account_balance_tool = {
    "name": "get_account_balance",
    "config": {
        "title": "Get Account Balance",
        "description": "Retrieve current account balance for the authenticated customer",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_type": {
                    "type": "string",
                    "description": "Type of account (checking, savings)",
                },
            },
            "required": ["account_type"],
        },
    },
    "handler": get_account_balance_handler,
}

get_account_statement_tool = {
    "name": "get_account_statement",
    "config": {
        "title": "Get Account Statement",
        "description": (
            "Retrieve recent account statement with transactions for the authenticated customer"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_type": {
                    "type": "string",
                    "description": "Type of account (checking, savings)",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to retrieve (default 30)",
                },
            },
            "required": ["account_type"],
        },
    },
    "handler": get_account_statement_handler,
}

prepare_money_transfer_tool = {
    "name": "prepare_money_transfer",
    "config": {
        "title": "Prepare Money Transfer",
        "description": (
            "Prepare a transfer between your accounts. IMPORTANT: When the user specifies "
            "an account by name (e.g., \"my son's account\" or \"my checking account\"), "
            "use the \"Available Accounts\" resource to look up and confirm the account ID."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Amount to transfer in USD",
                },
                "from_account_id": {
                    "type": "string",
                    "description": "Account ID to transfer from. If not provided, a picker will be shown after the tool has been called. If user specifies by name, look up in \"Available Accounts\" resource.",
                },
                "to_account_id": {
                    "type": "string",
                    "description": "Account ID to transfer to. If not provided, a picker will be shown after the tool has been called. If user specifies by name, look up in \"Available Accounts\" resource.",
                },
                "scheduled_date": {
                    "type": "string",
                    "description": "Date to schedule the transfer in YYYY-MM-DD format (e.g., 2026-04-15). If not provided, a picker will be shown after the tool has been called.",
                },
                "memo": {
                    "type": "string",
                    "description": "Optional memo or description for the transfer",
                },
            },
            "required": ["amount"],
        },
        "_meta": {
            "ui": {
                # Reference IBM Orchestrate's built-in widget
                "resourceUri": "ui://ibm.com/orchestrate/widget",
            },
        },
    },
    "handler": prepare_money_transfer_handler,
}

confirm_or_cancel_money_transfer_tool = {
    "name": "confirm_or_cancel_money_transfer",
    "config": {
        "title": "Confirm or Cancel Money Transfer",
        "description": (
            "Handle user action (confirm or cancel) for a previously prepared money transfer "
            "using the transaction ID."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID from prepare_money_transfer",
                },
                "action": {
                    "type": "string",
                    "description": "Action to take (confirm or cancel)",
                },
            },
            "required": ["transaction_id", "action"],
        },
        "_meta": {
            "ui": {
                "visibility": ["app"],
            },
        },
    },
    "handler": confirm_or_cancel_money_transfer_handler,
}

# Export all personal banking tools
personal_banking_tools = [
    get_account_balance_tool,
    get_account_statement_tool,
    prepare_money_transfer_tool,
    confirm_or_cancel_money_transfer_tool,
]

# Resource definition
available_accounts_resource = {
    "uri": "banking://accounts/available",
    "name": "Available Accounts",
    "description": (
        "List of accounts you can transfer money between, including account IDs, "
        "names, types, and transfer capabilities"
    ),
    "mimeType": "text/plain",
    "handler": available_accounts_resource_handler,
}

# Export all personal banking resources
personal_banking_resources = [available_accounts_resource]
