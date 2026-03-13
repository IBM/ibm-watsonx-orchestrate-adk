"""
Mortgage Tools Module

Contains tool definitions for mortgage operations.
Uses dict-based tool definitions to match the TypeScript implementation.
"""

from datetime import datetime, timedelta

from .mortgage_service import MortgageService
from .local_store import set_local_variable, get_local_variable, delete_local_variable
from . import logger


async def get_mortgage_balance_handler(args: dict, extra: dict) -> dict:
    """
    Get mortgage balance tool handler.

    This is a TOOL RESPONSE TO USER example that bypasses the LLM entirely,
    eliminating hallucination risk for critical data.
    """
    customer_id = args.get("customerId")

    if not customer_id:
        raise ValueError("Customer ID is required")

    output = MortgageService.get_mortgage_balance(customer_id)

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Your current mortgage balance and details are displayed below:\n"
                    f"Loan Number: {output.loan_number}\n"
                    f"Original Amount: ${output.original_amount:,.2f}\n"
                    f"Outstanding Balance: ${output.outstanding_balance:,.2f}\n"
                    f"Interest Rate: {output.interest_rate}%\n"
                    f"Monthly Payment: ${output.monthly_payment:.2f}\n"
                    f"Next Payment Due: {output.next_payment_date}\n"
                    f"Remaining Term: {output.remaining_term_months} months "
                    f"({output.remaining_term_months // 12} years)"
                ),
                "annotations": {"audience": ["user"]},
            }
        ],
        "structuredContent": {
            "loan_number": output.loan_number,
            "original_amount": output.original_amount,
            "outstanding_balance": output.outstanding_balance,
            "interest_rate": output.interest_rate,
            "monthly_payment": output.monthly_payment,
            "next_payment_date": output.next_payment_date,
            "remaining_term_months": output.remaining_term_months,
        },
    }


async def get_mortgage_payments_handler(args: dict, extra: dict) -> dict:
    """
    Get mortgage payments tool handler.

    This is a HYBRID RESPONSE example that demonstrates how to have the model
    formulate part of the response while ensuring critical data comes directly
    from your code.
    """
    customer_id = args.get("customerId")
    count = args.get("count", 6)

    if not customer_id:
        raise ValueError("Customer ID is required")

    output = MortgageService.get_mortgage_payments(customer_id, count)

    # Create markdown table for user display
    markdown_table_rows = [
        "| Payment Date | Total Amount | Principal | Interest | Escrow | Balance After |",
        "|--------------|--------------|-----------|----------|--------|---------------|",
    ]
    for p in output["payments"]:
        markdown_table_rows.append(
            f"| {p['payment_date']} | ${p['amount']:.2f} | ${p['principal']:.2f} | "
            f"${p['interest']:.2f} | ${p['escrow']:.2f} | ${p['balance_after']:,.2f} |"
        )
    markdown_table = "\n".join(markdown_table_rows)

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"The last {count} months of mortgage payment data has been retrieved "
                    "and will be displayed to the user in a table format immediately "
                    "following your response."
                ),
                "annotations": {"audience": ["assistant"]},
            },
            {
                "type": "text",
                "text": (
                    f"**Recent Mortgage Payments**\n\n"
                    f"**Loan Number:** {output['loan_number']}\n\n"
                    f"{markdown_table}"
                ),
                "annotations": {"audience": ["user"]},
            },
        ],
        "structuredContent": output,
    }


async def prepare_mortgage_payment_handler(args: dict, extra: dict) -> dict:
    """
    Prepare mortgage payment tool handler.

    This is the FIRST STEP in a two-step transaction pattern.
    """
    customer_id = args.get("customerId")
    amount = args.get("amount", 0)
    payment_date = args.get("payment_date")

    _meta = extra.get("_meta", {})
    thread_id = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("thread_id")

    if not thread_id:
        raise ValueError("Thread ID is required")

    if not customer_id:
        raise ValueError("Customer ID is required")

    # Validate amount
    if amount > 10000:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Payment amount must be less than $10,000.",
                    "annotations": {"audience": ["user"]},
                }
            ],
            "structuredContent": {
                "transaction_id": "",
                "loan_number": "",
                "amount": 0,
                "payment_date": "",
                "current_balance": 0,
                "expires_at": "",
            },
            "isError": True,
        }

    # If payment_date is not provided, show date picker widget
    if not payment_date:
        today = datetime.now()
        max_date = today + timedelta(days=30)

        date_picker_widget = {
            "type": "datetime",
            "collection_type": "date",
            "title": "Select Payment Date",
            "description": (
                "Choose when you want to make the mortgage payment "
                "(must be in the future, within 30 days):"
            ),
            "min_datetime": today.strftime("%Y-%m-%d"),
            "max_datetime": max_date.strftime("%Y-%m-%d"),
            "on_event": {
                "tool": "prepare_mortgage_payment",
                "parameters": {
                    k: v for k, v in args.items() if v is not None
                },
                "map_input_to": "payment_date",
            },
        }

        return {
            "_meta": {
                "com.ibm.orchestrate/widget": date_picker_widget,
            },
        }

    # Validate payment date
    validation = MortgageService.validate_payment_date(payment_date)
    if not validation.is_valid:
        return {
            "content": [
                {
                    "type": "text",
                    "text": validation.error_message,
                    "annotations": {"audience": ["user"]},
                }
            ],
            "structuredContent": {
                "transaction_id": "",
                "loan_number": "",
                "amount": 0,
                "payment_date": "",
                "current_balance": 0,
                "expires_at": "",
            },
            "isError": True,
        }

    prepared_payment = MortgageService.prepare_payment(customer_id, amount, payment_date)

    # Store payment details in LOCAL STORE
    set_local_variable(
        thread_id,
        f"payment_{prepared_payment.transaction_id}",
        {
            "transaction_id": prepared_payment.transaction_id,
            "customer_id": prepared_payment.customer_id,
            "loan_number": prepared_payment.loan_number,
            "amount": prepared_payment.amount,
            "payment_date": prepared_payment.payment_date,
            "current_balance": prepared_payment.current_balance,
            "expires_at": prepared_payment.expires_at,
        },
    )

    # Confirmation widget definition
    confirmation_widget = {
        "type": "confirmation",
        "title": "Confirm Mortgage Payment",
        "confirmation_text": (
            f"## Confirm Mortgage Payment\n\n"
            f"Please review the payment details below and confirm to proceed:\n\n"
            f"**Payment Details:**\n"
            f"- **Loan Number:** {prepared_payment.loan_number}\n"
            f"- **Amount:** ${prepared_payment.amount:.2f}\n"
            f"- **Payment Date:** {prepared_payment.payment_date}\n"
            f"- **Current Balance:** ${prepared_payment.current_balance:,.2f}\n\n"
            f"**Transaction ID:** {prepared_payment.transaction_id}\n\n"
            f"This transaction will expire in 5 minutes at "
            f"{prepared_payment.expires_at}"
        ),
        "on_confirm": {
            "tool": "confirm_or_cancel_mortgage_payment",
            "parameters": {
                "transaction_id": prepared_payment.transaction_id,
                "action": "confirm",
            },
        },
        "on_cancel": {
            "tool": "confirm_or_cancel_mortgage_payment",
            "parameters": {
                "transaction_id": prepared_payment.transaction_id,
                "action": "cancel",
            },
        },
    }

    return {
        "structuredContent": {
            "transaction_id": prepared_payment.transaction_id,
            "loan_number": prepared_payment.loan_number,
            "amount": prepared_payment.amount,
            "payment_date": prepared_payment.payment_date,
            "current_balance": prepared_payment.current_balance,
            "expires_at": prepared_payment.expires_at,
        },
        "_meta": {"com.ibm.orchestrate/widget": confirmation_widget},
    }


async def confirm_or_cancel_mortgage_payment_handler(args: dict, extra: dict) -> dict:
    """
    Confirm or cancel mortgage payment tool handler.

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

    # Retrieve payment from LOCAL STORE
    payment = get_local_variable(thread_id, f"payment_{transaction_id}")

    if not payment:
        raise ValueError(
            f"Payment {transaction_id} not found. "
            "It may have expired or been processed already."
        )

    # Verify payment belongs to this customer (security check)
    if payment["customer_id"] != customer_id:
        raise ValueError("Payment does not belong to this customer")

    # Clean up local variable
    delete_local_variable(thread_id, f"payment_{transaction_id}")

    if action == "cancel":
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Payment Cancelled\n\n"
                        f"Transaction ID: {transaction_id}\n\n"
                        f"The mortgage payment has been cancelled and no charges were processed.\n\n"
                        f"Payment Details:\n"
                        f"- Loan Number: {payment['loan_number']}\n"
                        f"- Amount: ${payment['amount']:.2f}\n"
                        f"- Payment Date: {payment['payment_date']}"
                    ),
                    "annotations": {"audience": ["user"]},
                },
                {
                    "type": "text",
                    "text": (
                        f"The mortgage payment with transaction ID {transaction_id} "
                        "has been cancelled by the user."
                    ),
                    "annotations": {"audience": ["assistant"]},
                },
            ]
        }

    # Handle confirmation - process the actual payment
    confirmation_number = MortgageService.process_mortgage_payment(
        payment["customer_id"],
        payment["loan_number"],
        payment["amount"],
        payment["payment_date"],
    )
    confirmed_at = datetime.now().isoformat()

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Payment Confirmed Successfully!\n\n"
                    f"Confirmation Number: {confirmation_number}\n"
                    f"Transaction ID: {transaction_id}\n\n"
                    f"Payment Details:\n"
                    f"- Loan Number: {payment['loan_number']}\n"
                    f"- Amount Paid: ${payment['amount']:.2f}\n"
                    f"- Payment Date: {payment['payment_date']}\n"
                    f"- Confirmed At: {confirmed_at}\n\n"
                    f"Your payment has been processed and your mortgage balance has been updated."
                ),
                "annotations": {"audience": ["user"]},
            },
            {
                "type": "text",
                "text": (
                    f"The mortgage payment has been confirmed with confirmation number "
                    f"{confirmation_number}. The payment has been processed successfully."
                ),
                "annotations": {"audience": ["assistant"]},
            },
        ]
    }


# Tool definitions in dict format (matching TypeScript structure)
get_mortgage_balance_tool = {
    "name": "get_mortgage_balance",
    "config": {
        "title": "Get Mortgage Balance",
        "description": (
            "Retrieve current outstanding mortgage balance for the authenticated customer. "
            "Response bypasses LLM to ensure data accuracy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "handler": get_mortgage_balance_handler,
}

get_mortgage_payments_tool = {
    "name": "get_mortgage_payments",
    "config": {
        "title": "Get Mortgage Payments",
        "description": "Retrieve recent mortgage payment history for the authenticated customer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of payment records to retrieve (default 6)",
                },
            },
            "required": [],
        },
    },
    "handler": get_mortgage_payments_handler,
}

prepare_mortgage_payment_tool = {
    "name": "prepare_mortgage_payment",
    "config": {
        "title": "Prepare Mortgage Payment",
        "description": (
            "Prepare a mortgage payment for the authenticated customer. "
            "Amount must be less than $10,000. "
            "Payment date must be in the future but not more than 30 days out."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Payment amount (must be less than $10,000)",
                },
                "payment_date": {
                    "type": "string",
                    "description": "Payment date in YYYY-MM-DD format (optional - if not provided, a date picker will be shown)",
                },
            },
            "required": ["amount"],
        },
    },
    "handler": prepare_mortgage_payment_handler,
}

confirm_or_cancel_mortgage_payment_tool = {
    "name": "confirm_or_cancel_mortgage_payment",
    "config": {
        "title": "Confirm or Cancel Mortgage Payment",
        "description": (
            "Handle user action (confirm or cancel) for a previously prepared mortgage payment "
            "using the transaction ID."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID from prepare_mortgage_payment",
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
    "handler": confirm_or_cancel_mortgage_payment_handler,
}

# Export all mortgage tools
mortgage_tools = [
    get_mortgage_balance_tool,
    get_mortgage_payments_tool,
    prepare_mortgage_payment_tool,
    confirm_or_cancel_mortgage_payment_tool,
]
