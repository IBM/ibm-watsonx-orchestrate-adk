"""
Get Contact Tool

This tool retrieves contact information from the AstraDB contact_details table.
It uses the same connection pattern as list_accounts.py to access the database.
"""

import logging
import os
from typing import Optional
from pydantic import BaseModel, Field
from astrapy import DataAPIClient

# Suppress AstraDB warnings about in-memory sorting and missing indexes
logging.getLogger("astrapy").setLevel(logging.ERROR)

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections


# Connection ID for Money Transfer App (contains token, url, and keyspace)
CONNECTION_PERSONAL_BANKING = 'personal_banking_app'


class Contact(BaseModel):
    """
    Represents a contact with their details.
    """
    contact_id: str = Field(..., description='The contact identifier')
    name: str = Field(..., description='The contact\'s full name')
    address: str = Field(..., description='The contact\'s mailing address')
    email: str = Field(..., description='The contact\'s email address')


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


def get_contact_from_db(api_token: str, api_endpoint: str, keyspace: str, contact_id: str) -> Optional[Contact]:
    """
    Retrieve a specific contact from the AstraDB contact_details table.
    
    Args:
        api_token: AstraDB API token
        api_endpoint: AstraDB API endpoint URL
        keyspace: AstraDB keyspace name
        contact_id: The contact ID to retrieve
        
    Returns:
        Contact object if found, None otherwise
        
    Raises:
        Exception: If database query fails
    """
    try:
        # Initialize AstraDB client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Get the contact_details table
        table = database.get_table("contact_details")
        
        # Query for the specific contact
        result = table.find_one({"contact_id": contact_id})
        
        if not result:
            return None
        
        # Convert to Contact object
        contact = Contact(
            contact_id=result.get("contact_id", ""),
            name=result.get("name", ""),
            address=result.get("address", ""),
            email=result.get("email", "")
        )
        
        return contact
        
    except Exception as e:
        logging.error(f"Failed to retrieve contact from database: {type(e).__name__}: {e}")
        raise Exception(f"Failed to retrieve contact: {str(e)}")


@tool(
    permission=ToolPermission.READ_ONLY,
    description="Get the logged-in user's contact information from the database",
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_PERSONAL_BANKING, type=ConnectionType.KEY_VALUE)
    ]
)
def get_contact() -> Contact:
    """
    Retrieve the logged-in user's contact information.
    
    This tool queries the AstraDB contact_details table to get the user's contact information including:
    - Full name
    - Mailing address
    - Email address
    
    The contact ID is always 'USER' since we assume a single logged-in user.

    Returns:
        A Contact object containing the user's contact details.
        
    Raises:
        ValueError: If database credentials are not configured or contact not found
        Exception: If database query fails
    """
    # Get credentials from connections or environment variables
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Retrieve contact from database (always use 'USER' as contact_id)
    contact = get_contact_from_db(api_token, api_endpoint, keyspace, "USER")
    
    if not contact:
        raise ValueError("User contact information not found")
    
    return contact


if __name__ == '__main__':
    # Test the tool directly (bypassing decorator for testing)
    import sys
    
    # Get credentials
    try:
        api_token, api_endpoint, keyspace = get_astra_credentials()
        contact = get_contact_from_db(api_token, api_endpoint, keyspace, "USER")
        
        if contact:
            print(f"User Contact Information:")
            print(f"  Name: {contact.name}")
            print(f"  Address: {contact.address}")
            print(f"  Email: {contact.email}")
        else:
            print("User contact information not found")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

# Made with Bob