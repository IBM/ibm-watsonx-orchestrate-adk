"""
Change Contact Tool

This tool updates contact information in the AstraDB contact_details table.
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


class ContactUpdateResult(BaseModel):
    """
    Represents the result of a contact update operation.
    """
    contact_id: str = Field(..., description='The contact identifier')
    success: bool = Field(..., description='Whether the update was successful')
    message: str = Field(..., description='Status message')
    updated_fields: dict = Field(..., description='Fields that were updated')


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


def update_contact_in_db(
    api_token: str,
    api_endpoint: str,
    keyspace: str,
    contact_id: str,
    name: Optional[str] = None,
    address: Optional[str] = None,
    email: Optional[str] = None
) -> ContactUpdateResult:
    """
    Update contact information in the AstraDB contact_details table.
    
    Args:
        api_token: AstraDB API token
        api_endpoint: AstraDB API endpoint URL
        keyspace: AstraDB keyspace name
        contact_id: The contact ID to update
        name: New name (optional)
        address: New address (optional)
        email: New email (optional)
        
    Returns:
        ContactUpdateResult object with update status
        
    Raises:
        Exception: If database query fails
    """
    try:
        # Initialize AstraDB client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Get the contact_details table
        table = database.get_table("contact_details")
        
        # First, check if contact exists
        existing = table.find_one({"contact_id": contact_id})
        if not existing:
            return ContactUpdateResult(
                contact_id=contact_id,
                success=False,
                message=f"Contact with ID '{contact_id}' not found",
                updated_fields={}
            )
        
        # Build update document with only provided fields
        update_doc = {}
        updated_fields = {}
        
        if name is not None:
            update_doc["name"] = name
            updated_fields["name"] = name
        
        if address is not None:
            update_doc["address"] = address
            updated_fields["address"] = address
        
        if email is not None:
            update_doc["email"] = email
            updated_fields["email"] = email
        
        # If no fields to update, return early
        if not update_doc:
            return ContactUpdateResult(
                contact_id=contact_id,
                success=False,
                message="No fields provided to update",
                updated_fields={}
            )
        
        # Perform the update
        # Note: update_one does not return a value - it either succeeds or throws an exception
        table.update_one(
            filter={"contact_id": contact_id},
            update={"$set": update_doc}
        )
        
        # If we reach here, the update was successful (no exception was thrown)
        return ContactUpdateResult(
            contact_id=contact_id,
            success=True,
            message=f"Successfully updated contact {contact_id}",
            updated_fields=updated_fields
        )
        
    except Exception as e:
        logging.error(f"Failed to update contact in database: {type(e).__name__}: {e}")
        raise Exception(f"Failed to update contact: {str(e)}")


@tool(
    permission=ToolPermission.READ_WRITE,
    description="Update the logged-in user's contact information (name, address, email) in the database",
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_PERSONAL_BANKING, type=ConnectionType.KEY_VALUE)
    ]
)
def change_contact(
    name: Optional[str] = None,
    address: Optional[str] = None,
    email: Optional[str] = None
) -> ContactUpdateResult:
    """
    Update the logged-in user's contact information.
    
    This tool updates the AstraDB contact_details table with new contact information for the current user.
    You can update one or more fields (name, address, email) at a time.
    Only the fields you provide will be updated; others will remain unchanged.
    
    The contact ID is always 'USER' since we assume a single logged-in user.

    Args:
        name: New name for the user (optional)
        address: New address for the user (optional)
        email: New email for the user (optional)

    Returns:
        A ContactUpdateResult object containing the update status and updated fields.
        
    Raises:
        ValueError: If database credentials are not configured or no fields provided
        Exception: If database query fails
    """
    # Validate that at least one field is provided
    if name is None and address is None and email is None:
        raise ValueError("At least one field (name, address, or email) must be provided to update")
    
    # Get credentials from connections or environment variables
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Update contact in database (always use 'USER' as contact_id)
    result = update_contact_in_db(
        api_token=api_token,
        api_endpoint=api_endpoint,
        keyspace=keyspace,
        contact_id="USER",
        name=name,
        address=address,
        email=email
    )
    
    return result


if __name__ == '__main__':
    # Test the tool directly (bypassing decorator for testing)
    import sys
    
    # Get credentials
    try:
        if len(sys.argv) < 2:
            print("Usage: python change_contact.py [--name <name>] [--address <address>] [--email <email>]")
            print("Example: python change_contact.py --name 'John Doe' --email 'john.doe@example.com'")
            sys.exit(1)
        
        # Parse optional arguments
        name = None
        address = None
        email = None
        
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == '--name' and i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--address' and i + 1 < len(sys.argv):
                address = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--email' and i + 1 < len(sys.argv):
                email = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        api_token, api_endpoint, keyspace = get_astra_credentials()
        result = update_contact_in_db(api_token, api_endpoint, keyspace, "USER", name, address, email)
        
        print(f"Update Result:")
        print(f"  Success: {result.success}")
        print(f"  Message: {result.message}")
        if result.updated_fields:
            print(f"  Updated Fields:")
            for field, value in result.updated_fields.items():
                print(f"    - {field}: {value}")
        
        sys.exit(0 if result.success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

# Made with Bob