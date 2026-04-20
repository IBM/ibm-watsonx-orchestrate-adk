"""
List Accounts Tool

This tool retrieves all bank accounts from the AstraDB accounts table.
It uses the same connection pattern as transfer_money.py to access the database.
"""

import logging
import os
from typing import List
from pydantic import BaseModel, Field
from astrapy import DataAPIClient

# Suppress AstraDB warnings about in-memory sorting and missing indexes
logging.getLogger("astrapy").setLevel(logging.ERROR)

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections


# Connection ID for Money Transfer App (contains token, url, and keyspace)
CONNECTION_PERSONAL_BANKING = 'personal_banking_app'


class Account(BaseModel):
    """
    Represents a bank account with its details.
    """
    account_number: str = Field(..., description='The account number')
    account_type: str = Field(..., description='The type of account (checking, savings, etc.)')
    balance: float = Field(..., description='The current balance in the account')


class AccountList(BaseModel):
    """
    Represents a list of accounts.
    """
    accounts: List[Account] = Field(..., description='List of accounts')
    total_accounts: int = Field(..., description='Total number of accounts')


def get_astra_credentials() -> tuple[str, str, str]:
    """
    Get AstraDB credentials from connections or environment variables.
    
    Since BadRequest exception calls sys.exit(1), we need to check for environment
    variables first to avoid triggering BadRequest when connections are not configured.
    
    The connection should be a key-value type with keys matching environment variable names:
    - ASTRA_TOKEN: AstraDB API token
    - ASTRA_URL: AstraDB API endpoint URL
    - ASTRA_NAMESPACE: AstraDB namespace name (optional, defaults to "default_keyspace")
    
    Returns:
        Tuple of (api_token, api_endpoint, keyspace)
        
    Raises:
        ValueError: If credentials are not found
    """
    # Check environment variables first to avoid BadRequest sys.exit()
    api_token = os.getenv("ASTRA_TOKEN")
    api_endpoint = os.getenv("ASTRA_URL")
    keyspace = os.getenv("ASTRA_NAMESPACE", "default_keyspace")  # Default to "default_keyspace"
    
    # If env vars are not set, try to get from connection (key-value type)
    # Connection keys match environment variable names for consistency
    if not api_token or not api_endpoint:
        try:
            conn_creds = connections.key_value(CONNECTION_PERSONAL_BANKING)
            if not api_token:
                api_token = conn_creds.get("ASTRA_TOKEN")
            if not api_endpoint:
                api_endpoint = conn_creds.get("ASTRA_URL")
            if not keyspace or keyspace == "default_keyspace":
                # Allow connection to override default keyspace
                conn_keyspace = conn_creds.get("ASTRA_NAMESPACE")
                if conn_keyspace:
                    keyspace = conn_keyspace
        except Exception as e:
            # Connection failed, but env vars might be set
            logging.debug(f"Failed to get credentials from connection: {type(e).__name__}: {e}")
    
    # Final validation
    if not api_token or not isinstance(api_token, str):
        raise ValueError(
            f"Missing API token. Either configure connection '{CONNECTION_PERSONAL_BANKING}' "
            "with 'ASTRA_TOKEN' key or set ASTRA_TOKEN environment variable."
        )
    
    if not api_endpoint or not isinstance(api_endpoint, str):
        raise ValueError(
            f"Missing API endpoint. Either configure connection '{CONNECTION_PERSONAL_BANKING}' "
            "with 'ASTRA_URL' key or set ASTRA_URL environment variable."
        )
    
    if not isinstance(keyspace, str):
        raise ValueError(
            f"Invalid keyspace value. Must be a string."
        )
    
    return api_token, api_endpoint, keyspace


def get_accounts_from_db(api_token: str, api_endpoint: str, keyspace: str) -> List[Account]:
    """
    Retrieve all accounts from the AstraDB accounts table.
    
    Args:
        api_token: AstraDB API token
        api_endpoint: AstraDB API endpoint URL
        keyspace: AstraDB keyspace name
        
    Returns:
        List of Account objects
        
    Raises:
        Exception: If database query fails
    """
    try:
        # Initialize AstraDB client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Get the accounts table
        table = database.get_table("accounts")
        
        # Query all accounts
        result = table.find({})
        
        # Convert to Account objects
        accounts = []
        for row in result:
            accounts.append(Account(
                account_number=row.get("account_id", ""),
                account_type=row.get("account_type", "").title(),  # Capitalize first letter
                balance=float(row.get("balance", 0.0))
            ))
        
        # Sort by account number for consistent ordering
        accounts.sort(key=lambda x: x.account_number)
        
        return accounts
        
    except Exception as e:
        logging.error(f"Failed to retrieve accounts from database: {type(e).__name__}: {e}")
        raise Exception(f"Failed to retrieve accounts: {str(e)}")


@tool(
    permission=ToolPermission.READ_ONLY,
    description="Get a list of all bank accounts with their types and balances from the database",
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_PERSONAL_BANKING, type=ConnectionType.KEY_VALUE)
    ]
)
def list_accounts() -> AccountList:
    """
    Retrieve a list of all bank accounts including account numbers, types, and balances.
    
    This tool queries the AstraDB accounts table to get real-time account information.
    The accounts are retrieved from the database and include:
    - Account number (e.g., CHK-001, SAV-002)
    - Account type (Checking, Savings, etc.)
    - Current balance

    Returns:
        An AccountList object containing the list of accounts with their details.
        
    Raises:
        ValueError: If database credentials are not configured
        Exception: If database query fails
    """
    # Get credentials from connections or environment variables
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Retrieve accounts from database
    accounts = get_accounts_from_db(api_token, api_endpoint, keyspace)
    
    # Create and return AccountList
    account_list = AccountList(
        accounts=accounts,
        total_accounts=len(accounts)
    )
    
    return account_list


if __name__ == '__main__':
    # Test the tool directly (bypassing decorator for testing)
    import sys
    
    # Get credentials
    try:
        api_token, api_endpoint, keyspace = get_astra_credentials()
        accounts = get_accounts_from_db(api_token, api_endpoint, keyspace)
        
        print("Account List:")
        print(f"Total Accounts: {len(accounts)}")
        for account in accounts:
            print(f"  - {account.account_number} ({account.account_type}): ${account.balance:.2f}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

# Made with Bob
