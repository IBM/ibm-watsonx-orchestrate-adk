#!/usr/bin/env python3
"""
Interactive Personal Banking Tool Tester

This script allows you to test different scenarios with the personal banking tools:
1. Complete transfer with all parameters
2. Transfer with missing parameters (elicitation)
3. Cancel a transfer
4. Resume a transfer with instance_id
5. Do something else (digression)
6. List account balances
7. Get contact information
8. Update contact information
"""

import json
import os
import sys
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from the same directory as this script
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path)
except ImportError:
    # dotenv not installed, environment variables must be set manually
    pass

# Add the tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from transfer_money import transfer_money
from list_accounts import list_accounts
from get_contact import get_contact
from change_contact import change_contact


# Global variables to track last used values
last_instance_id = None
last_from_account = "CHK-001"
last_to_account = "SAV-002"
last_amount = "100.00"


def print_separator():
    """Print a visual separator"""
    print("\n" + "=" * 80 + "\n")


def print_response(response, title: str = "Response"):
    """Pretty print the response"""
    print(f"\n{title}:")
    
    # Unwrap ToolResponse if present
    if hasattr(response, 'content'):
        response = response.content
    
    # Handle both dict and Pydantic models
    if hasattr(response, 'model_dump'):
        # Pydantic v2
        print(json.dumps(response.model_dump(), indent=2))
    elif hasattr(response, 'dict'):
        # Pydantic v1
        print(json.dumps(response.dict(), indent=2))
    else:
        # Plain dict
        print(json.dumps(response, indent=2))


def get_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def test_complete_transfer():
    """Test a complete transfer with all parameters"""
    print_separator()
    print("TEST 1: Complete Transfer with All Parameters")
    print_separator()
    
    global last_from_account, last_to_account, last_amount
    
    from_account = get_input("Enter source account", last_from_account)
    to_account = get_input("Enter destination account", last_to_account)
    amount = float(get_input("Enter amount", last_amount))
    
    # Update last used values
    last_from_account = from_account
    last_to_account = to_account
    last_amount = str(amount)
    
    print("\nInitiating transfer...")
    response = transfer_money(
        from_account=from_account,
        to_account=to_account,
        amount=amount
    )
    
    print_response(response, "Initial Response")
    
    # Unwrap ToolResponse if present
    content = response.content if hasattr(response, 'content') else response
    
    # Track instance_id
    global last_instance_id
    status = content.status if hasattr(content, 'status') else content.get("status", {})
    if hasattr(status, 'instance_id'):
        last_instance_id = status.instance_id
    elif isinstance(status, dict):
        last_instance_id = status.get("instance_id")
    
    # Check if we need confirmation
    if hasattr(status, 'state'):
        state = status.state
        elicitation = status.elicitation
        instance_id = status.instance_id
    else:
        state = status.get("state")
        elicitation = status.get("elicitation", {})
        instance_id = status.get("instance_id")
    
    if state == "input_required":
        question = elicitation.question if hasattr(elicitation, 'question') else elicitation.get('question')
        elicitation_id = elicitation.elicitation_id if hasattr(elicitation, 'elicitation_id') else elicitation.get('elicitation_id')
        
        print(f"\n{question}")
        
        confirm = get_input("Confirm? (yes/no)", "yes").lower()
        
        print("\nSending confirmation...")
        response = transfer_money(
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            instance_id=instance_id,
            elicitation_id=elicitation_id,
            elicitation_response={
                "action": "accept" if confirm == "yes" else "reject",
                "content": {"value": confirm}
            }
        )
        
        print_response(response, "After Confirmation")
    
    return response


def test_missing_parameters():
    """Test transfer with missing parameters (elicitation)"""
    print_separator()
    print("TEST 2: Transfer with Missing Parameters")
    print_separator()
    
    print("Starting transfer without parameters...")
    print("The tool will request missing information via elicitation.\n")
    
    global last_instance_id, last_from_account, last_to_account, last_amount
    
    # Start with no parameters
    response = transfer_money(
        from_account=None,
        to_account=None,
        amount=None
    )
    
    print_response(response, "Initial Response")
    
    # Loop until transfer is complete or user quits
    max_iterations = 10  # Safety limit
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Unwrap ToolResponse if present
        content = response.content if hasattr(response, 'content') else response
        status = content.status if hasattr(content, 'status') else content.get("status", {})
        
        if hasattr(status, 'instance_id'):
            instance_id = status.instance_id
            state = status.state
            elicitation = status.elicitation if hasattr(status, 'elicitation') else None
        else:
            instance_id = status.get("instance_id")
            state = status.get("state")
            elicitation = status.get("elicitation")
        
        last_instance_id = instance_id
        
        # Check if we're done
        if state == "completed":
            print("\n✅ Transfer completed successfully!")
            break
        elif state == "failed":
            print("\n❌ Transfer failed!")
            break
        elif state == "working":
            print("\n⏳ Transfer is processing...")
            break
        elif state != "input_required":
            print(f"\n⚠️  Unexpected state: {state}")
            break
        
        # Handle elicitation
        if not elicitation:
            print("\n⚠️  No elicitation found but state is input_required")
            break
        
        question = elicitation.question if hasattr(elicitation, 'question') else elicitation.get('question')
        elicitation_id = elicitation.elicitation_id if hasattr(elicitation, 'elicitation_id') else elicitation.get('elicitation_id')
        parameter = elicitation.parameter if hasattr(elicitation, 'parameter') else elicitation.get('parameter')
        options = elicitation.options if hasattr(elicitation, 'options') else elicitation.get('options')
        
        print(f"\n{question}")
        print("(Type 'quit' to save and exit, resume later with option 4)")
        
        # Get appropriate default based on parameter
        if parameter == "from_account":
            default = last_from_account
        elif parameter == "to_account":
            default = last_to_account
        elif parameter == "amount":
            default = last_amount
        else:
            default = ""
        
        # Get user input
        if options:
            user_input = get_input(f"Enter response ({'/'.join(options)})", options[0] if options else default)
        else:
            user_input = get_input("Enter response", default)
        
        # Check for quit
        if user_input.lower() == 'quit':
            print(f"\n✅ Transfer paused. Use instance_id '{instance_id}' to resume later.")
            return response
        
        # Update last used values
        if parameter == "from_account":
            last_from_account = user_input
        elif parameter == "to_account":
            last_to_account = user_input
        elif parameter == "amount":
            last_amount = user_input
        
        # Determine action (accept/reject for confirmation, otherwise accept)
        if parameter == "confirmation" or "confirm" in question.lower():
            action = "accept" if user_input.lower() in ["yes", "y"] else "reject"
        else:
            action = "accept"
        
        # Respond to elicitation
        response = transfer_money(
            instance_id=instance_id,
            elicitation_id=elicitation_id,
            elicitation_response={
                "action": action,
                "content": {"value": user_input}
            }
        )
        
        print_response(response, f"After Providing {parameter}")
    
    if iteration >= max_iterations:
        print("\n⚠️  Reached maximum iterations. Something may be wrong.")
    
    return response


def test_cancel_transfer():
    """Test cancelling a transfer"""
    print_separator()
    print("TEST 3: Cancel a Transfer")
    print_separator()
    
    global last_from_account, last_to_account, last_amount, last_instance_id
    
    from_account = get_input("Enter source account", last_from_account)
    to_account = get_input("Enter destination account", last_to_account)
    amount = float(get_input("Enter amount", last_amount))
    
    # Update last used values
    last_from_account = from_account
    last_to_account = to_account
    last_amount = str(amount)
    
    print("\nInitiating transfer...")
    response = transfer_money(
        from_account=from_account,
        to_account=to_account,
        amount=amount
    )
    
    print_response(response, "Initial Response")
    
    status = response.get("status", {})
    instance_id = status.get("instance_id")
    
    print("\nCancelling transfer...")
    response = transfer_money(
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        instance_id=instance_id,
        transfer_action="cancel"
    )
    
    print_response(response, "After Cancellation")
    
    return response


def test_check_status_or_update():
    """Test checking status or updating inputs of a transfer with instance_id"""
    print_separator()
    print("TEST 4: Check Status or Update Inputs with instance_id")
    print_separator()
    
    global last_instance_id, last_from_account, last_to_account, last_amount
    
    # Ask for instance_id with last used as default
    default_instance = last_instance_id if last_instance_id else ""
    instance_id = get_input("Enter instance_id to check/update", default_instance)
    
    if not instance_id:
        print("\n❌ Error: instance_id is required")
        return None
    
    # Update last instance_id
    last_instance_id = instance_id
    
    # Ask if user wants to check status or update parameters
    print("\nWhat would you like to do?")
    print("  1. Check current status (no changes)")
    print("  2. Update transfer parameters (change accounts or amount)")
    print("  3. Continue with missing information")
    action = get_input("Select action (1/2/3)", "1")
    
    provide_params = action == "2"
    check_status_only = action == "1"
    
    from_account = None
    to_account = None
    amount = None
    
    if provide_params in ["yes", "y"]:
        print("\nProvide parameters to update (leave blank to skip):")
        from_account_input = get_input("Enter source account (optional)", "")
        to_account_input = get_input("Enter destination account (optional)", "")
        amount_input = get_input("Enter amount (optional)", "")
        
        # Only set if provided
        if from_account_input:
            from_account = from_account_input
            last_from_account = from_account_input
        if to_account_input:
            to_account = to_account_input
            last_to_account = to_account_input
        if amount_input:
            amount = float(amount_input)
            last_amount = amount_input
    
    if check_status_only:
        print(f"\nChecking status of transfer: {instance_id}")
        # Call with transfer_action="status" to just check status
        response = transfer_money(
            instance_id=instance_id,
            transfer_action="status"
        )
    else:
        print(f"\nContinuing transfer with instance_id: {instance_id}")
        if from_account or to_account or amount:
            print(f"Updating with: from_account={from_account}, to_account={to_account}, amount={amount}")
        else:
            print("Tool will check its state and request any missing information...")
        
        # Call with instance_id and any provided parameters
        response = transfer_money(
            instance_id=instance_id,
            from_account=from_account,
            to_account=to_account,
            amount=amount
        )
    
    print_response(response, "Current Status")
    
    # Loop to handle any remaining elicitations
    max_iterations = 10  # Safety limit
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Unwrap ToolResponse if present
        content = response.content if hasattr(response, 'content') else response
        status = content.status if hasattr(content, 'status') else content.get("status", {})
        
        if hasattr(status, 'state'):
            state = status.state
            elicitation = status.elicitation if hasattr(status, 'elicitation') else None
        else:
            state = status.get("state")
            elicitation = status.get("elicitation")
        
        # Check if we're done
        if state == "completed":
            print("\n✅ Transfer completed successfully!")
            break
        elif state == "failed":
            print("\n❌ Transfer failed!")
            break
        elif state == "working":
            print("\n⏳ Transfer is processing...")
            break
        elif state != "input_required":
            print(f"\n⚠️  Unexpected state: {state}")
            break
        
        # Handle elicitation
        if not elicitation:
            print("\n⚠️  No elicitation found but state is input_required")
            break
        
        if hasattr(elicitation, 'question'):
            question = elicitation.question
            elicitation_id = elicitation.elicitation_id
            parameter = elicitation.parameter if hasattr(elicitation, 'parameter') else None
            options = elicitation.options if hasattr(elicitation, 'options') else None
        else:
            question = elicitation.get('question')
            elicitation_id = elicitation.get('elicitation_id')
            parameter = elicitation.get('parameter')
            options = elicitation.get('options')
        
        print(f"\n{question}")
        print("(Type 'quit' to save and exit, resume later)")
        
        # Get appropriate default based on parameter
        if parameter == "from_account":
            default = last_from_account
        elif parameter == "to_account":
            default = last_to_account
        elif parameter == "amount":
            default = last_amount
        else:
            default = ""
        
        # Get user input
        if options:
            user_input = get_input(f"Enter response ({'/'.join(options)})", options[0] if options else default)
        else:
            user_input = get_input("Enter response", default)
        
        # Check for quit
        if user_input.lower() == 'quit':
            print(f"\n✅ Transfer paused. Use instance_id '{instance_id}' to resume later.")
            return response
        
        # Update last used values
        if parameter == "from_account":
            last_from_account = user_input
        elif parameter == "to_account":
            last_to_account = user_input
        elif parameter == "amount":
            last_amount = user_input
        
        # Determine action (accept/reject for confirmation, otherwise accept)
        if parameter == "confirmation" or "confirm" in question.lower():
            action = "accept" if user_input.lower() in ["yes", "y"] else "reject"
        else:
            action = "accept"
        
        # Respond to elicitation
        response = transfer_money(
            instance_id=instance_id,
            elicitation_id=elicitation_id,
            elicitation_response={
                "action": action,
                "content": {"value": user_input}
            }
        )
        
        print_response(response, f"After Providing {parameter}")
    
    if iteration >= max_iterations:
        print("\n⚠️  Reached maximum iterations. Something may be wrong.")
    
    return response


def test_do_something_else():
    """Simulate digression - user does something unrelated to transfer"""
    import random
    
    print_separator()
    print("TEST 5: Do Something Else (Digression Simulation)")
    print_separator()
    
    print("\nThis simulates the user asking about something unrelated to the transfer.")
    user_input = input("\nWhat would you like to ask or do? ").strip()
    
    if not user_input:
        print("\n(No input provided)")
        return None
    
    # Generate a random response to simulate handling digression
    responses = [
        f"I understand you're asking about '{user_input}'. Let me help you with that.",
        f"That's an interesting question about '{user_input}'. Here's what I can tell you...",
        f"Regarding '{user_input}', I'd be happy to assist with that.",
        f"I see you want to know about '{user_input}'. Let me look into that for you.",
        f"Thanks for asking about '{user_input}'. I can help with that.",
    ]
    
    random_response = random.choice(responses)
    print(f"\n🤖 Agent Response: {random_response}")
    print("\n(This is a simulated response. In a real scenario, the agent would handle")
    print("the digression and could return to the transfer task later.)")
    
    return random_response


def test_list_accounts():
    """Test listing all account balances"""
    print_separator()
    print("TEST 6: List Account Balances")
    print_separator()
    
    print("\nRetrieving all account balances from database...")
    
    try:
        # Call the list_accounts tool
        response = list_accounts()
        
        # Unwrap ToolResponse if present
        if hasattr(response, 'content'):
            result = response.content
        else:
            result = response
        
        # Handle both Pydantic models and dicts
        if hasattr(result, 'accounts'):
            accounts = result.accounts
            total_accounts = result.total_accounts
        else:
            accounts = result.get('accounts', [])
            total_accounts = result.get('total_accounts', 0)
        
        print(f"\n✅ Found {total_accounts} accounts:")
        print("\n" + "-" * 80)
        print(f"{'Account Number':<20} {'Type':<20} {'Balance':>20}")
        print("-" * 80)
        
        for account in accounts:
            # Handle both Pydantic models and dicts
            if hasattr(account, 'account_number'):
                acc_num = account.account_number
                acc_type = account.account_type
                balance = account.balance
            else:
                acc_num = account.get('account_number', '')
                acc_type = account.get('account_type', '')
                balance = account.get('balance', 0.0)
            
            print(f"{acc_num:<20} {acc_type:<20} ${balance:>19,.2f}")
        
        print("-" * 80)
        
        # Calculate total balance
        if hasattr(accounts[0] if accounts else None, 'balance'):
            total_balance = sum(account.balance for account in accounts)
        else:
            total_balance = sum(account.get('balance', 0.0) for account in accounts)
        
        print(f"{'TOTAL':<20} {'':<20} ${total_balance:>19,.2f}")
        print("-" * 80)
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error listing accounts: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_get_contact():
    """Test getting contact information"""
    print_separator()
    print("TEST 7: Get Contact Information")
    print_separator()
    
    print("\nRetrieving user contact information from database...")
    
    try:
        # Call the get_contact tool
        response = get_contact()
        
        # Unwrap ToolResponse if present
        if hasattr(response, 'content'):
            contact = response.content
        else:
            contact = response
        
        # Handle both Pydantic models and dicts
        if hasattr(contact, 'contact_id'):
            contact_id = contact.contact_id
            name = contact.name
            address = contact.address
            email = contact.email
        else:
            contact_id = contact.get('contact_id', '')
            name = contact.get('name', '')
            address = contact.get('address', '')
            email = contact.get('email', '')
        
        print(f"\n✅ Contact Information Retrieved:")
        print("\n" + "-" * 80)
        print(f"Contact ID: {contact_id}")
        print(f"Name:       {name}")
        print(f"Address:    {address}")
        print(f"Email:      {email}")
        print("-" * 80)
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error retrieving contact: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_update_contact():
    """Test updating contact information"""
    print_separator()
    print("TEST 8: Update Contact Information")
    print_separator()
    
    print("\nYou can update one or more fields (leave blank to skip):")
    
    # Get current contact first to show defaults
    try:
        current_contact = get_contact()
        if hasattr(current_contact, 'content'):
            current_contact = current_contact.content
        
        if hasattr(current_contact, 'name'):
            current_name = current_contact.name
            current_address = current_contact.address
            current_email = current_contact.email
        else:
            current_name = current_contact.get('name', '')
            current_address = current_contact.get('address', '')
            current_email = current_contact.get('email', '')
        
        print(f"\nCurrent values:")
        print(f"  Name:    {current_name}")
        print(f"  Address: {current_address}")
        print(f"  Email:   {current_email}")
        print()
    except Exception as e:
        print(f"\n⚠️  Could not retrieve current contact: {e}")
        current_name = ""
        current_address = ""
        current_email = ""
    
    # Get new values from user
    new_name = get_input("Enter new name (or leave blank to keep current)", "")
    new_address = get_input("Enter new address (or leave blank to keep current)", "")
    new_email = get_input("Enter new email (or leave blank to keep current)", "")
    
    # Check if any field was provided
    if not new_name and not new_address and not new_email:
        print("\n⚠️  No fields provided to update. Cancelling.")
        return None
    
    # Build update parameters
    update_params = {}
    if new_name:
        update_params['name'] = new_name
    if new_address:
        update_params['address'] = new_address
    if new_email:
        update_params['email'] = new_email
    
    print(f"\nUpdating contact with: {', '.join(update_params.keys())}...")
    
    try:
        # Call the change_contact tool
        response = change_contact(**update_params)
        
        # Unwrap ToolResponse if present
        if hasattr(response, 'content'):
            result = response.content
        else:
            result = response
        
        # Handle both Pydantic models and dicts
        if hasattr(result, 'success'):
            success = result.success
            message = result.message
            updated_fields = result.updated_fields
        else:
            success = result.get('success', False)
            message = result.get('message', '')
            updated_fields = result.get('updated_fields', {})
        
        if success:
            print(f"\n✅ {message}")
            print("\nUpdated fields:")
            print("-" * 80)
            for field, value in updated_fields.items():
                print(f"  {field}: {value}")
            print("-" * 80)
        else:
            print(f"\n❌ {message}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error updating contact: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main interactive menu"""
    print("\n" + "=" * 80)
    print("Personal Banking Tools - Interactive Tester")
    print("=" * 80)
    
    # Check environment variables
    if not os.getenv("ASTRA_TOKEN") or not os.getenv("ASTRA_URL"):
        print("\n⚠️  WARNING: ASTRA_TOKEN and/or ASTRA_URL environment variables not set.")
        print("Make sure you have a .env file with these values, or connections configured.")
        print("See .env.example for reference.\n")
    
    while True:
        print("\nAvailable Tests:")
        print("1. Complete transfer with all parameters")
        print("2. Transfer with missing parameters (elicitation)")
        print("3. Cancel a transfer")
        print("4. Resume a transfer with instance_id")
        print("5. Do something else (digression)")
        print("6. List account balances")
        print("7. Get contact information")
        print("8. Update contact information")
        print("q. Quit")
        
        choice = input("\nSelect a test (1-8, q): ").strip().lower()
        
        try:
            if choice == "q":
                print("\nExiting tester. Goodbye!")
                break
            elif choice == "1":
                test_complete_transfer()
            elif choice == "2":
                test_missing_parameters()
            elif choice == "3":
                test_cancel_transfer()
            elif choice == "4":
                test_check_status_or_update()
            elif choice == "5":
                test_do_something_else()
            elif choice == "6":
                test_list_accounts()
            elif choice == "7":
                test_get_contact()
            elif choice == "8":
                test_update_contact()
            else:
                print("Invalid choice. Please select 1-8 or q.")
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()

# Made with Bob
