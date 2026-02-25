"""
Credit Card Tools Module

Contains tool definitions for credit card operations.
Uses dict-based tool definitions to match the TypeScript implementation.
"""

from .credit_card_service import CreditCardService


# Localized message templates for credit card balance display
# Templates use {variable} placeholders that get replaced with actual values
MESSAGE_TEMPLATES: dict[str, str] = {
    "en-US": """Credit Card Balance:
Card: {card_number} ({card_type})
Current Balance: {current_balance}
Available Credit: {available_credit}
Credit Limit: {credit_limit}
Minimum Payment: {minimum_payment}
Payment Due: {payment_due_date}""",
    "es-MX": """Saldo de Tarjeta de Crédito:
Tarjeta: {card_number} ({card_type})
Saldo Actual: {current_balance}
Crédito Disponible: {available_credit}
Límite de Crédito: {credit_limit}
Pago Mínimo: {minimum_payment}
Fecha de Pago: {payment_due_date}""",
    "fr-FR": """Solde de Carte de Crédit:
Carte: {card_number} ({card_type})
Solde Actuel: {current_balance}
Crédit Disponible: {available_credit}
Limite de Crédit: {credit_limit}
Paiement Minimum: {minimum_payment}
Date d'Échéance: {payment_due_date}""",
    "de-DE": """Kreditkartensaldo:
Karte: {card_number} ({card_type})
Aktueller Saldo: {current_balance}
Verfügbares Guthaben: {available_credit}
Kreditlimit: {credit_limit}
Mindestzahlung: {minimum_payment}
Fälligkeitsdatum: {payment_due_date}""",
}


async def get_credit_card_balance_handler(args: dict, extra: dict) -> dict:
    """
    Get credit card balance tool handler.

    This tool demonstrates:
    1. Using JWT token from CONTEXT VARIABLES (customer-provided via API)
    2. Using locale from SYSTEM CONTEXT (provided by Watson Orchestrate)
    """
    _meta = extra.get("_meta", {})

    # Extract JWT token from CONTEXT VARIABLES (passed by API caller)
    jwt_token = _meta.get("com.ibm.orchestrate/context", {}).get("jwtToken")

    if not jwt_token:
        raise ValueError(
            "JWT token is required. It must be provided in context variables by the API caller."
        )

    # Use JWT token to authenticate with backend service
    card_balance = CreditCardService.get_credit_card_balance(jwt_token)

    # Extract locale from SYSTEM CONTEXT with fallback to en-US
    locale = _meta.get("com.ibm.orchestrate/systemcontext", {}).get("locale", "en-US")

    # Get message template for locale, fallback to en-US if locale not supported
    template = MESSAGE_TEMPLATES.get(locale, MESSAGE_TEMPLATES["en-US"])

    # Fill in template with actual values
    message = (
        template.replace("{card_number}", card_balance.card_number)
        .replace("{card_type}", card_balance.card_type)
        .replace("{current_balance}", f"${card_balance.current_balance:.2f}")
        .replace("{available_credit}", f"${card_balance.available_credit:.2f}")
        .replace("{credit_limit}", f"${card_balance.credit_limit:.2f}")
        .replace("{minimum_payment}", f"${card_balance.minimum_payment:.2f}")
        .replace("{payment_due_date}", card_balance.payment_due_date)
    )

    return {
        "content": [
            {
                "type": "text",
                "text": message,
                "annotations": {"audience": ["user"]},
            }
        ]
    }


# Tool definitions in dict format (matching TypeScript structure)
get_credit_card_balance_tool = {
    "name": "get_credit_card_balance",
    "config": {
        "title": "Get Credit Card Balance",
        "description": (
            "Retrieve current credit card balance and details for the authenticated customer"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "handler": get_credit_card_balance_handler,
}

# Export all credit card tools
credit_card_tools = [get_credit_card_balance_tool]
