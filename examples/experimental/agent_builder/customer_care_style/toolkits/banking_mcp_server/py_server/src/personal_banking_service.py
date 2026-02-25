"""
Personal Banking Service - Mock Implementation

Contains mock business logic for personal banking operations.
"""

from dataclasses import dataclass
from datetime import datetime
import random
import string


@dataclass
class Account:
    """Bank account information."""

    account_id: str
    account_name: str
    account_type: str
    can_transfer_from: bool
    can_transfer_to: bool
    is_locked: bool
    account_holder: str | None = None


@dataclass
class Transaction:
    """Transaction record."""

    date: str
    description: str
    amount: float
    balance: float


@dataclass
class TransferResult:
    """Result of a money transfer."""

    customer_id: str
    from_account_id: str
    to_account_id: str
    amount: float
    transfer_id: str
    status: str
    timestamp: str
    scheduled_date: str | None = None
    memo: str | None = None


class PersonalBankingService:
    """Mock Personal Banking Service."""

    @staticmethod
    def get_accounts(customer_id: str) -> list[Account]:
        """
        Get list of accounts for a customer.
        Includes owned accounts and registered external accounts for transfers.
        """
        # Mock account data - in a real system, this would query a database
        return [
            Account(
                account_id="acc_checking_001",
                account_name="Primary Checking",
                account_type="checking",
                can_transfer_from=True,
                can_transfer_to=True,
                is_locked=True,  # This account is locked - requires customer service
            ),
            Account(
                account_id="acc_savings_001",
                account_name="High Yield Savings",
                account_type="savings",
                can_transfer_from=True,
                can_transfer_to=True,
                is_locked=False,
            ),
            Account(
                account_id="acc_checking_002",
                account_name="Business Checking",
                account_type="checking",
                can_transfer_from=True,
                can_transfer_to=True,
                is_locked=False,
            ),
            Account(
                account_id="acc_investment_001",
                account_name="Investment Account",
                account_type="investment",
                can_transfer_from=False,  # Cannot transfer from investment accounts
                can_transfer_to=True,
                is_locked=False,
            ),
            Account(
                account_id="acc_external_son_001",
                account_name="Son's College Fund",
                account_type="external_savings",
                can_transfer_from=False,  # Cannot transfer from son's account
                can_transfer_to=True,
                is_locked=False,
                account_holder="Michael Johnson (Son)",
            ),
            Account(
                account_id="acc_investment_002",
                account_name="Retirement IRA",
                account_type="retirement",
                can_transfer_from=False,  # Cannot transfer from retirement accounts
                can_transfer_to=True,
                is_locked=False,
            ),
        ]

    @staticmethod
    def get_account_balance(
        customer_id: str, account_type: str
    ) -> dict:
        """Get account balance by account type."""
        # Mock balance data
        balance = 5432.18 if account_type == "checking" else 12750.50
        return {
            "customer_id": customer_id,
            "account_type": account_type,
            "balance": balance,
            "currency": "USD",
            "as_of_date": datetime.now().isoformat(),
        }

    @staticmethod
    def get_account_statement(
        customer_id: str, account_type: str, days: int = 30
    ) -> dict:
        """Get account statement with transactions."""
        end_date = datetime.now()
        start_date = datetime.now()
        # Simplified date calculation for mock data

        # Mock transaction data
        transactions = [
            Transaction(
                date="2025-12-18",
                description="Direct Deposit - Salary",
                amount=3500.00,
                balance=5432.18,
            ),
            Transaction(
                date="2025-12-15",
                description="Online Purchase - Amazon",
                amount=-87.43,
                balance=1932.18,
            ),
            Transaction(
                date="2025-12-12",
                description="ATM Withdrawal",
                amount=-100.00,
                balance=2019.61,
            ),
            Transaction(
                date="2025-12-10",
                description="Transfer to Savings",
                amount=-500.00,
                balance=2119.61,
            ),
        ]

        return {
            "customer_id": customer_id,
            "account_type": account_type,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "transactions": [
                {
                    "date": t.date,
                    "description": t.description,
                    "amount": t.amount,
                    "balance": t.balance,
                }
                for t in transactions
            ],
        }

    @staticmethod
    def transfer_money(
        customer_id: str,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        scheduled_date: str | None = None,
        memo: str | None = None,
    ) -> TransferResult:
        """Transfer money between accounts."""
        # Validate that from and to accounts are different
        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")

        # Generate a mock transfer ID
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
        transfer_id = f"TXN-{int(datetime.now().timestamp() * 1000)}-{random_suffix}"
        timestamp = datetime.now().isoformat()
        status = "scheduled" if scheduled_date else "completed"

        return TransferResult(
            customer_id=customer_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            scheduled_date=scheduled_date,
            memo=memo,
            transfer_id=transfer_id,
            status=status,
            timestamp=timestamp,
        )

    @staticmethod
    def validate_transfer(
        customer_id: str,
        from_account_id: str,
        to_account_id: str,
        amount: float,
    ) -> dict:
        """
        Validate a transfer request.
        Returns account details if valid, raises error if invalid.
        """
        accounts = PersonalBankingService.get_accounts(customer_id)
        from_account = next((acc for acc in accounts if acc.account_id == from_account_id), None)
        to_account = next((acc for acc in accounts if acc.account_id == to_account_id), None)

        if not from_account:
            raise ValueError(f"Source account {from_account_id} not found")

        if not to_account:
            raise ValueError(f"Destination account {to_account_id} not found")

        if not from_account.can_transfer_from:
            raise ValueError(
                f"Cannot transfer from {from_account.account_name} - transfers not allowed"
            )

        if not to_account.can_transfer_to:
            raise ValueError(
                f"Cannot transfer to {to_account.account_name} - transfers not allowed"
            )

        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero")

        return {"from_account": from_account, "to_account": to_account}
