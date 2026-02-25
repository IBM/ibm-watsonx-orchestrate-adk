"""
Credit Card Service - Mock Implementation

Contains mock business logic for credit card operations.
"""

from dataclasses import dataclass


@dataclass
class CreditCardBalance:
    """Credit card balance information."""

    card_number: str
    card_type: str
    current_balance: float
    available_credit: float
    credit_limit: float
    minimum_payment: float
    payment_due_date: str
    last_statement_date: str
    last_statement_balance: float


class CreditCardService:
    """Mock Credit Card Service."""

    @staticmethod
    def get_credit_card_balance(jwt_token: str) -> CreditCardBalance:
        """
        Get credit card balance and details using JWT authentication.

        Args:
            jwt_token: JWT token for authentication with backend service

        Returns:
            Credit card balance information
        """
        # In a real implementation, this would:
        # 1. Validate the JWT token
        # 2. Extract customer ID from the token claims
        # 3. Make an authenticated API call to the backend service
        # 4. Return the actual credit card data

        # For demo purposes, we'll just validate the token exists
        if not jwt_token:
            raise ValueError("JWT token is required")

        # Mock response - in production this would come from your backend API
        return CreditCardBalance(
            card_number="**** **** **** 4532",
            card_type="Platinum Rewards",
            current_balance=2847.63,
            available_credit=7152.37,
            credit_limit=10000.00,
            minimum_payment=85.43,
            payment_due_date="2026-01-28",
            last_statement_date="2025-12-28",
            last_statement_balance=2654.21,
        )
