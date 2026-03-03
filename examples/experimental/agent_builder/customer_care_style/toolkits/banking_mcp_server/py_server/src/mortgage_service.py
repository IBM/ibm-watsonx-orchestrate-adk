"""
Mortgage Service - Mock Implementation

Contains mock business logic for mortgage operations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import string


@dataclass
class MortgageBalance:
    """Mortgage balance information."""

    loan_number: str
    original_amount: float
    outstanding_balance: float
    interest_rate: float
    monthly_payment: float
    next_payment_date: str
    remaining_term_months: int


@dataclass
class MortgagePayment:
    """Mortgage payment record."""

    payment_date: str
    amount: float
    principal: float
    interest: float
    escrow: float
    balance_after: float


@dataclass
class PreparedPayment:
    """Prepared payment awaiting confirmation."""

    transaction_id: str
    customer_id: str
    loan_number: str
    amount: float
    payment_date: str
    current_balance: float
    expires_at: str


@dataclass
class PaymentValidationResult:
    """Result of payment date validation."""

    is_valid: bool
    error_message: str | None = None


class MortgageService:
    """Mock Mortgage Service."""

    @staticmethod
    def get_mortgage_balance(customer_id: str) -> MortgageBalance:
        """Get mortgage balance and details."""
        return MortgageBalance(
            loan_number=f"MTG-{customer_id}-001",
            original_amount=350000.00,
            outstanding_balance=287450.32,
            interest_rate=3.75,
            monthly_payment=1620.50,
            next_payment_date="2026-01-01",
            remaining_term_months=276,
        )

    @staticmethod
    def get_mortgage_payments(customer_id: str, count: int = 6) -> dict:
        """Get mortgage payment history."""
        loan_number = f"MTG-{customer_id}-001"
        all_payments = [
            MortgagePayment(
                payment_date="2025-12-01",
                amount=1620.50,
                principal=722.15,
                interest=898.35,
                escrow=0,
                balance_after=287450.32,
            ),
            MortgagePayment(
                payment_date="2025-11-01",
                amount=1620.50,
                principal=719.88,
                interest=900.62,
                escrow=0,
                balance_after=288172.47,
            ),
            MortgagePayment(
                payment_date="2025-10-01",
                amount=1620.50,
                principal=717.61,
                interest=902.89,
                escrow=0,
                balance_after=288892.35,
            ),
            MortgagePayment(
                payment_date="2025-09-01",
                amount=1620.50,
                principal=715.35,
                interest=905.15,
                escrow=0,
                balance_after=289609.96,
            ),
            MortgagePayment(
                payment_date="2025-08-01",
                amount=1620.50,
                principal=713.10,
                interest=907.40,
                escrow=0,
                balance_after=290325.31,
            ),
            MortgagePayment(
                payment_date="2025-07-01",
                amount=1620.50,
                principal=710.86,
                interest=909.64,
                escrow=0,
                balance_after=291038.41,
            ),
        ]

        return {
            "customer_id": customer_id,
            "loan_number": loan_number,
            "payments": [
                {
                    "payment_date": p.payment_date,
                    "amount": p.amount,
                    "principal": p.principal,
                    "interest": p.interest,
                    "escrow": p.escrow,
                    "balance_after": p.balance_after,
                }
                for p in all_payments[:count]
            ],
        }

    @staticmethod
    def validate_payment_date(payment_date: str) -> PaymentValidationResult:
        """Validate payment date."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            payment_date_obj = datetime.strptime(payment_date, "%Y-%m-%d")
        except ValueError:
            return PaymentValidationResult(
                is_valid=False,
                error_message=f"Invalid date format: {payment_date}. Please use YYYY-MM-DD format.",
            )

        thirty_days_from_now = today + timedelta(days=30)

        # Check if date is in the past
        if payment_date_obj < today:
            return PaymentValidationResult(
                is_valid=False,
                error_message=(
                    f"We're unable to schedule a payment for {payment_date} as this date has "
                    "already passed. Please select today's date or a date within the next 30 days."
                ),
            )

        # Check if date is more than 30 days in the future
        if payment_date_obj > thirty_days_from_now:
            latest_date = thirty_days_from_now.strftime("%Y-%m-%d")
            return PaymentValidationResult(
                is_valid=False,
                error_message=(
                    f"We can only schedule payments up to 30 days in advance. The date you "
                    f"selected ({payment_date}) is beyond this window. Please choose a date "
                    f"on or before {latest_date}."
                ),
            )

        return PaymentValidationResult(is_valid=True)

    @staticmethod
    def prepare_payment(
        customer_id: str,
        amount: float,
        payment_date: str,
    ) -> PreparedPayment:
        """Prepare a mortgage payment."""
        loan_number = f"MTG-{customer_id}-001"
        current_balance = 287450.32
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
        transaction_id = f"TXN-{int(datetime.now().timestamp() * 1000)}-{random_suffix}"
        # 5 minutes from now
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()

        return PreparedPayment(
            transaction_id=transaction_id,
            customer_id=customer_id,
            loan_number=loan_number,
            amount=amount,
            payment_date=payment_date,
            current_balance=current_balance,
            expires_at=expires_at,
        )

    @staticmethod
    def process_mortgage_payment(
        customer_id: str,
        loan_number: str,
        amount: float,
        payment_date: str,
    ) -> str:
        """
        Process a mortgage payment.
        In a real implementation, this would call your mortgage system to process the payment.
        """
        # Mock implementation - in production this would:
        # - Process the payment with your mortgage system
        # - Update the mortgage balance
        # - Create payment records
        # - Return confirmation number from mortgage system
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
        return f"CONF-{int(datetime.now().timestamp() * 1000)}-{random_suffix}"
