"""
Re-entrant Money Transfer Tool

This tool implements a stateful banking transfer system.
It demonstrates synchronous execution with timeout, re-entrant calls, state management,
user input elicitation, and cancellation support using AstraDB for state persistence.
"""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from astrapy import DataAPIClient

# Suppress AstraDB warnings about in-memory sorting and missing indexes
logging.getLogger("astrapy").setLevel(logging.ERROR)
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


# Connection ID for Money Transfer App (contains token, url, and keyspace)
CONNECTION_PERSONAL_BANKING = 'personal_banking_app'


class TransferState(Enum):
    """Transfer states aligned with RFC-0792 and MCP Tasks specification"""
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"


class TransferStep(Enum):
    """Steps in the money transfer workflow"""
    VALIDATE_INPUT = "validate_input"
    CHECK_BALANCE = "check_balance"
    CONFIRM_TRANSFER = "confirm_transfer"
    LOCK_ACCOUNTS = "lock_accounts"
    DEBIT_FROM = "debit_from_account"
    CREDIT_TO = "credit_to_account"
    RELEASE_LOCKS = "release_locks"
    RECORD_TRANSACTION = "record_transaction"
    COMPLETE = "complete"


class ElicitationResponse(BaseModel):
    """User's response to an elicitation request"""
    value: Any = Field(..., description="User's response value (string, float, boolean, etc.)")
    action: str = Field(default="accept", description="Action to take: 'accept', 'reject', or 'cancel'")
    content: Optional[Dict[str, Any]] = Field(default=None, description="Optional additional content")


# Pydantic models for response types
class TransferProgress(BaseModel):
    """Progress information for the transfer"""
    current_step: str = Field(description="Current step description")
    step_number: int = Field(description="Current step number")
    total_steps: int = Field(description="Total number of steps")


class TransferElicitation(BaseModel):
    """Elicitation request for user input"""
    elicitation_id: str = Field(description="Unique ID for this elicitation")
    question: str = Field(description="Question to ask the user")
    parameter: Optional[str] = Field(default=None, description="Parameter being requested")
    options: Optional[list[str]] = Field(default=None, description="Available options for the user")


class TransferInputs(BaseModel):
    """Current input values for the transfer"""
    from_account: Optional[str] = Field(default=None, description="Source account ID")
    to_account: Optional[str] = Field(default=None, description="Destination account ID")
    amount: Optional[float] = Field(default=None, description="Transfer amount")


class TransferStatus(BaseModel):
    """Status information for the transfer"""
    instance_id: str = Field(description="Unique transfer instance ID")
    name: str = Field(description="Transfer name")
    state: str = Field(description="Current transfer state")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    inputs: Optional[TransferInputs] = Field(default=None, description="Current input values")
    message: Optional[str] = Field(default=None, description="Status message or error")
    progress: Optional[TransferProgress] = Field(default=None, description="Progress information")
    elicitation: Optional[TransferElicitation] = Field(default=None, description="Elicitation request")


class TransferOutput(BaseModel):
    """Output data for completed transfer"""
    transaction_id: str = Field(description="Unique transaction ID")
    from_account: str = Field(description="Source account ID")
    to_account: str = Field(description="Destination account ID")
    amount: float = Field(description="Transfer amount")
    status: str = Field(description="Transaction status")
    timestamp: str = Field(description="Completion timestamp")


class TransferResponse(BaseModel):
    """Complete response from the transfer tool"""
    status: TransferStatus = Field(description="Transfer status information")
    output: Optional[TransferOutput] = Field(default=None, description="Transfer output (when completed)")


class AstraDBStateStore:
    """AstraDB-based state store for flow instances using Table API"""
    
    def __init__(self, api_token: str, api_endpoint: str, keyspace: str = "default_keyspace"):
        """
        Initialize AstraDB connection with credentials.
        
        Args:
            api_token: AstraDB API token
            api_endpoint: AstraDB API endpoint URL
            keyspace: AstraDB keyspace name (default: "default_keyspace")
        """
        self.api_token = api_token
        self.api_endpoint = api_endpoint
        self.keyspace = keyspace
        self.table_name = "transaction_data"
        self._table = None
    
    def _get_table(self):
        """Get or create AstraDB table connection"""
        if self._table is None:
            # Initialize DataAPIClient
            client = DataAPIClient()
            database = client.get_database(
                self.api_endpoint,
                token=self.api_token
            )
            
            # Get the table
            self._table = database.get_table(self.table_name, keyspace=self.keyspace)
        
        return self._table
    
    def save(self, instance_id: str, state: Dict[str, Any], ttl_seconds: int = 3600) -> str:
        """
        Save flow state to AstraDB table.
        
        Returns:
            The task_id that was generated for this save operation
        """
        table = self._get_table()
        
        # Use existing task_id if present (already generated), otherwise create new one
        task_id = state.get("task_id")
        if not task_id:
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
        
        # Convert state to JSON string for storage
        state_json = json.dumps(state)
        
        # Insert new row with task_id
        # AstraDB Data API expects UUID values as strings in proper UUID format
        row_data = {
            "instance_id": instance_id,  # Keep as string (valid UUID format)
            "task_id": task_id,  # Keep as string (valid UUID format)
            "state": state.get("state"),
            "state_data": state_json,
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at")
        }
            
        table.insert_one(row_data)
        return task_id
    
    def load(self, instance_id: Optional[str] = None, task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load flow state from AstraDB table.
        
        Args:
            instance_id: Transfer instance ID (loads most recent state for this instance)
            task_id: Specific task ID (loads exact interaction)
        
        Returns:
            Transfer state dict or None if not found
        """
        table = self._get_table()
        
        if task_id:
            # Direct lookup by task_id (primary key)
            # AstraDB Data API expects UUID values as strings
            result = table.find_one({"task_id": task_id})
            if result and "state_data" in result:
                return json.loads(result["state_data"])
        elif instance_id:
            # Find the most recent row by instance_id (sorted by updated_at descending)
            # AstraDB Data API expects UUID values as strings
            results = table.find(
                {"instance_id": instance_id},
                sort={"updated_at": -1},
                limit=1
            )
            
            # Get first (and only) result
            for result in results:
                if "state_data" in result:
                    # Parse JSON string back to dict
                    return json.loads(result["state_data"])
        
        return None
    
    def delete(self, instance_id: str) -> None:
        """Delete all flow state records for given instance_id"""
        table = self._get_table()
        # AstraDB Data API expects UUID values as strings
        table.delete_many({"instance_id": instance_id})


class ReentrantTransferTool:
    """Re-entrant money transfer tool simulating flow behavior"""
    
    def __init__(self, api_token: str, api_endpoint: str, keyspace: str = "default_keyspace", timeout: float = 30.0):
        """
        Initialize the transfer tool.
        
        Args:
            api_token: AstraDB API token
            api_endpoint: AstraDB API endpoint URL
            keyspace: AstraDB keyspace name (default: "default_keyspace")
            timeout: Maximum execution time per call in seconds
        """
        self.timeout = timeout
        self.state_store = AstraDBStateStore(api_token, api_endpoint, keyspace)
        self.api_token = api_token
        self.api_endpoint = api_endpoint
        self.keyspace = keyspace
        self.steps = [
            (TransferStep.VALIDATE_INPUT, self._validate_input),
            (TransferStep.CHECK_BALANCE, self._check_balance),
            (TransferStep.CONFIRM_TRANSFER, self._confirm_transfer),
            (TransferStep.LOCK_ACCOUNTS, self._lock_accounts),
            (TransferStep.DEBIT_FROM, self._debit_from_account),
            (TransferStep.CREDIT_TO, self._credit_to_account),
            (TransferStep.RELEASE_LOCKS, self._release_locks),
            (TransferStep.RECORD_TRANSACTION, self._record_transaction),
            (TransferStep.COMPLETE, self._complete),
        ]
    
    def transfer_money(
        self,
        from_account: Optional[str] = None,
        to_account: Optional[str] = None,
        amount: Optional[float] = None,
        instance_id: Optional[str] = None,
        transfer_action: Optional[str] = None,
        elicitation_id: Optional[str] = None,
        elicitation_response: Optional[Dict[str, Any]] = None
    ) -> TransferResponse:
        """
        Transfer money between accounts with streamlined re-entrant support.
        
        Streamlined Transfer:
        1. If instance_id is missing → new transfer, otherwise continue existing
        2. Check from_account → if missing, return elicitation (create task)
        3. Check to_account → if missing, return elicitation (create task)
        4. Check amount → if missing, return elicitation (create task)
        5. If all 3 fields present → confirm transfer (create task)
        6. If confirmed → simulate transfer (create task)
        7. Update successful transfer → state=completed, return
        
        Args:
            from_account: Source account ID (optional, will be requested if not provided)
            to_account: Destination account ID (optional, will be requested if not provided)
            amount: Amount to transfer (optional, will be requested if not provided)
            instance_id: Existing transfer instance ID for re-entrant calls
            transfer_action: Transfer control action (e.g., "cancel", "status", "input_changed")
            elicitation_id: ID of elicitation being responded to (required when providing elicitation_response)
            elicitation_response: User's response to elicitation. When the agent receives an elicitation
                request (with elicitation_id), it should respond by calling this tool with both
                elicitation_id and elicitation_response parameters. The response should include:
                - value: The user's answer (string, number, boolean, etc.)
                - action: "accept" (default), "reject", or "cancel"
                - content: Optional additional data
        
        Returns:
            TransferResponse with status and optional output
        """
        
        # STEP 1: Load or create state
        if instance_id:
            # Continue existing transfer
            state = self.state_store.load(instance_id=instance_id)
            if not state:
                return self._error_response(instance_id, f"Transfer instance {instance_id} not found")
            
            # Update state with any newly provided parameters (whether transfer_action is set or not)
            # This allows users to provide missing parameters when resuming
            params_updated = False
            if from_account is not None and state.get("from_account") != from_account:
                state["from_account"] = from_account
                params_updated = True
            if to_account is not None and state.get("to_account") != to_account:
                state["to_account"] = to_account
                params_updated = True
            if amount is not None and state.get("amount") != amount:
                state["amount"] = amount
                params_updated = True
            
            # Handle transfer_action="input_changed" - reset transfer state
            if transfer_action is not None and transfer_action == "input_changed":
                # Reset state to restart transfer from appropriate step
                # Clear any working/completed state and restart validation
                if state["state"] in [TransferState.WORKING.value, TransferState.COMPLETED.value]:
                    state["state"] = TransferState.INPUT_REQUIRED.value
                    state["transfer_start_time"] = None
                    state["transaction_id"] = None
                    state["output"] = None
                params_updated = True
            
            # Save state if parameters were updated
            if params_updated:
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
        else:
            # New transfer
            instance_id = str(uuid.uuid4())
            state = self._create_initial_state(instance_id, from_account, to_account, amount)
        
        # Validate accounts if they are provided (before any processing)
        # This catches invalid accounts early and asks for valid input via elicitation
        account_list = self._get_account_list()
        
        if state.get("from_account") is not None:
            if not self._validate_account_exists(state["from_account"]):
                # Invalid account - create new elicitation to ask again
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
                state["state"] = TransferState.INPUT_REQUIRED.value
                state["elicitations"]["current_elicitation_id"] = task_id
                invalid_account = state["from_account"]
                state["from_account"] = None  # Reset to ask again
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
                
                return self._create_elicitation_request(
                    state,
                    task_id,
                    f"Invalid source account '{invalid_account}'. Please select a valid account:",
                    parameter="from_account",
                    options=account_list if account_list else None
                )
        
        if state.get("to_account") is not None:
            if not self._validate_account_exists(state["to_account"]):
                # Invalid account - create new elicitation to ask again
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
                state["state"] = TransferState.INPUT_REQUIRED.value
                state["elicitations"]["current_elicitation_id"] = task_id
                invalid_account = state["to_account"]
                state["to_account"] = None  # Reset to ask again
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
                
                return self._create_elicitation_request(
                    state,
                    task_id,
                    f"Invalid destination account '{invalid_account}'. Please select a valid account:",
                    parameter="to_account",
                    options=account_list if account_list else None
                )
        
        # Handle transfer_action="status" - return current status based on state
        if transfer_action == "status":
            # 1. If there's a pending elicitation (INPUT_REQUIRED), return that
            if state["state"] == TransferState.INPUT_REQUIRED.value:
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
                return self._format_response(state)
            
            # 2. If in the middle of transfer (WORKING), check background processing
            if state["state"] == TransferState.WORKING.value:
                state = self._check_background_processing(state, instance_id)
                self.state_store.save(instance_id, state)
                return self._format_response(state)
            
            # 3. If completed/failed, just return the final state
            if state["state"] in [TransferState.COMPLETED.value, TransferState.FAILED.value]:
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
                return self._format_response(state)
            
            # Default: return current state
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
            return self._format_response(state)
        
        # Check if transfer is in WORKING state and update if completed
        # This applies to normal transfer (not status checks)
        if state["state"] == TransferState.WORKING.value:
            state = self._check_background_processing(state, instance_id)
            # If state changed to completed, return immediately
            if state["state"] == TransferState.COMPLETED.value:
                return self._format_response(state)
        
        # Handle transfer_action="cancel"
        if transfer_action == "cancel":
            return self._cancel_flow(state)
        
        # Handle elicitation response
        if elicitation_response:
            if not elicitation_id:
                # Agent didn't provide elicitation_id - re-present the last elicitation for confirmation
                # This can happen after user digression when agent loses context
                if state["state"] == TransferState.INPUT_REQUIRED.value:
                    # Re-present the current elicitation and ask agent to provide elicitation_id
                    state["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.state_store.save(instance_id, state)
                    response = self._format_response(state)
                    # Add a note in the status message to remind about elicitation_id
                    if hasattr(response, 'status'):
                        response.status.message = "IMPORTANT: When responding to this elicitation, you must provide both elicitation_id and elicitation_response parameters. The elicitation_id is provided in the status.elicitation.elicitation_id field."
                    return response
                else:
                    # No pending elicitation, cannot process response
                    return self._error_response(instance_id, "elicitation_response provided but no pending elicitation found. Please check the current state first.")
            
            state = self._handle_elicitation_response(state, elicitation_id, elicitation_response)
            # Update timestamp and save state after handling elicitation
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
        
        # If already completed or failed, return immediately
        if state["state"] in [TransferState.COMPLETED.value, TransferState.FAILED.value]:
            return self._format_response(state)
        
        # Get account list for elicitations
        account_list = self._get_account_list()
        
        # STEP 2: Check from_account - if missing, return elicitation
        if state["from_account"] is None:
            # Reuse existing task_id if already in INPUT_REQUIRED state, otherwise create new one
            if state["state"] == TransferState.INPUT_REQUIRED.value and state.get("task_id"):
                task_id = state["task_id"]
            else:
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
            return self._create_elicitation_request(
                state, task_id, "What is the source account ID?", parameter="from_account", options=account_list
            )
        
        # STEP 3: Check to_account - if missing, return elicitation
        if state["to_account"] is None:
            # Reuse existing task_id if already in INPUT_REQUIRED state, otherwise create new one
            if state["state"] == TransferState.INPUT_REQUIRED.value and state.get("task_id"):
                task_id = state["task_id"]
            else:
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
            return self._create_elicitation_request(
                state, task_id, "What is the destination account ID?", parameter="to_account", options=account_list
            )
        
        # STEP 4: Check amount - if missing, return elicitation
        if state["amount"] is None:
            # Reuse existing task_id if already in INPUT_REQUIRED state, otherwise create new one
            if state["state"] == TransferState.INPUT_REQUIRED.value and state.get("task_id"):
                task_id = state["task_id"]
            else:
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
            return self._create_elicitation_request(
                state, task_id, "What is the transfer amount?", parameter="amount"
            )
        
        # Validate inputs
        if state["amount"] <= 0:
            state["state"] = TransferState.FAILED.value
            state["error"] = "Amount must be greater than zero"
            self.state_store.save(instance_id, state)
            return self._format_response(state)
        
        if state["from_account"] == state["to_account"]:
            state["state"] = TransferState.FAILED.value
            state["error"] = "Cannot transfer to the same account"
            self.state_store.save(instance_id, state)
            return self._format_response(state)
        
        # Check balance before confirmation
        balance_check_result = self._check_balance(state)
        if balance_check_result is not None:
            # Insufficient funds - return elicitation to ask for amount again
            return balance_check_result
        
        # STEP 5: All fields present and balance sufficient - ask for confirmation
        if not state.get("confirmed"):
            # Reuse existing task_id if already in INPUT_REQUIRED state, otherwise create new one
            if state["state"] == TransferState.INPUT_REQUIRED.value and state.get("task_id"):
                task_id = state["task_id"]
            else:
                task_id = str(uuid.uuid4())
                state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
            question = f"Confirm transfer of ${state['amount']:.2f} from {state['from_account']} to {state['to_account']}?"
            return self._create_elicitation_request(state, task_id, question, options=["yes", "no"])
        
        # STEP 6: Confirmed - start or check background transfer processing
        if "transfer_start_time" not in state:
            # First time - start the transfer
            state["transfer_start_time"] = datetime.now(timezone.utc).isoformat()
            state["state"] = TransferState.WORKING.value
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update progress to show initiating
            state["progress"] = {
                "current_step": "Initiating transfer...",
                "step_number": 1,
                "total_steps": 9
            }
            state["message"] = "Transfer is being initiated in the background. This will take approximately 60 seconds."
            self.state_store.save(instance_id, state)
            
            # Simulate initial processing delay (10 seconds) before returning
            print(f"[DEBUG] Initiating background transfer... (returning after 10s)")
            time.sleep(10)
            
            # Return with WORKING state - actual completion happens when user resumes
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(instance_id, state)
        else:
            # Transfer already started - use common background processing check
            state = self._check_background_processing(state, instance_id)
        
        return self._format_response(state)
    
    def _create_initial_state(
        self,
        instance_id: str,
        from_account: Optional[str],
        to_account: Optional[str],
        amount: Optional[float]
    ) -> Dict[str, Any]:
        """Create initial flow state"""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "instance_id": instance_id,
            "task_id": None,  # Will be set when saved
            "name": "transfer_money",
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "state": TransferState.WORKING.value,
            "current_step": TransferStep.VALIDATE_INPUT.value,
            "step_index": 0,
            "steps_completed": [],
            "created_at": now,
            "updated_at": now,
            "error": None,
            "output": {},
            "elicitations": {},
            "transaction_id": None
        }
    
    def _create_elicitation_request(
        self,
        state: Dict[str, Any],
        elicitation_id: str,
        question: str,
        parameter: Optional[str] = None,
        options: Optional[list[str]] = None
    ) -> TransferResponse:
        """Helper to create elicitation response"""
        # Debug logging
        logging.info(f"Creating elicitation for parameter '{parameter}' with {len(options) if options else 0} options")
        if options:
            logging.debug(f"Options: {options}")
        
        # Convert empty list to None for cleaner serialization
        if options is not None and len(options) == 0:
            options = None
            logging.warning(f"Empty options list for parameter '{parameter}', setting to None")
        
        # Store current elicitation in state so it can be recreated on status checks
        state["elicitations"]["current_elicitation_id"] = elicitation_id
        state["elicitations"]["current_question"] = question
        state["elicitations"]["current_parameter"] = parameter
        state["elicitations"]["current_options"] = options
        
        # Update timestamp and save state to persist the elicitation
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state_store.save(state["instance_id"], state)
        
        elicitation = TransferElicitation(
            elicitation_id=elicitation_id,
            question=question,
            parameter=parameter,
            options=options
        )
        
        progress = TransferProgress(
            current_step="Collecting transfer details..." if parameter else "Awaiting confirmation...",
            step_number=state["step_index"] + 1,
            total_steps=len(self.steps)
        )
        
        # Include current input values
        inputs = TransferInputs(
            from_account=state.get("from_account"),
            to_account=state.get("to_account"),
            amount=state.get("amount")
        )
        
        status = TransferStatus(
            instance_id=state["instance_id"],
            name=state["name"],
            state=TransferState.INPUT_REQUIRED.value,
            created_at=state["created_at"],
            updated_at=state["updated_at"],
            inputs=inputs,
            elicitation=elicitation,
            progress=progress
        )
        
        return TransferResponse(status=status)
    
    def _get_account_list(self) -> list[str]:
        """Fetch list of valid account IDs from the accounts table"""
        try:
            client = DataAPIClient(self.api_token)
            database = client.get_database(self.api_endpoint, keyspace=self.keyspace)
            table = database.get_table("accounts")
            
            # Query all accounts
            result = table.find({})
            account_ids = [row.get("account_id", "") for row in result if row.get("account_id")]
            account_ids.sort()  # Sort for consistent ordering
            
            if not account_ids:
                logging.warning("No accounts found in accounts table - table may be empty or not created")
                print("⚠️  WARNING: No accounts found in database. Please run setup_astra_table.sh to create and populate the accounts table.")
            else:
                logging.info(f"Successfully fetched {len(account_ids)} accounts from database")
            
            return account_ids
        except Exception as e:
            logging.error(f"Failed to fetch account list: {type(e).__name__}: {e}")
            print(f"⚠️  ERROR: Failed to fetch accounts from database: {e}")
            print("   Please ensure:")
            print("   1. ASTRA_TOKEN and ASTRA_URL are set correctly")
            print("   2. The accounts table exists (run setup_astra_table.sh)")
            print("   3. The database is accessible")
            import traceback
            logging.debug(traceback.format_exc())
            # Return empty list if fetch fails - elicitation will work without options
            return []
    
    def _validate_account_exists(self, account_id: str) -> bool:
        """Check if an account ID exists in the accounts table"""
        try:
            client = DataAPIClient(self.api_token)
            database = client.get_database(self.api_endpoint, keyspace=self.keyspace)
            table = database.get_table("accounts")
            
            # Query for specific account
            result = table.find_one({"account_id": account_id})
            return result is not None
        except Exception as e:
            logging.warning(f"Failed to validate account {account_id}: {e}")
            # If validation fails, assume account is valid to avoid blocking transfers
            return True
    
    def _get_account_balance(self, account_id: str) -> Optional[float]:
        """Get the current balance of an account"""
        try:
            client = DataAPIClient(self.api_token)
            database = client.get_database(self.api_endpoint, keyspace=self.keyspace)
            table = database.get_table("accounts")
            
            # Query for specific account
            result = table.find_one({"account_id": account_id})
            if result and "balance" in result:
                return float(result["balance"])
            return None
        except Exception as e:
            logging.error(f"Failed to get balance for account {account_id}: {e}")
            return None
    
    def _validate_input(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Validate input parameters and request missing ones via elicitation"""
        
        # Get list of valid accounts for elicitation options
        account_list = self._get_account_list()
        
        # Check for missing from_account or invalid from_account
        if state["from_account"] is None:
            # Check if we have an invalid account marker
            invalid_account = state.pop("_invalid_from_account", None)
            
            # Generate task_id first to use as elicitation_id
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Save with the pre-generated task_id
            self.state_store.save(state["instance_id"], state)
            
            # Create appropriate question based on whether this is a retry
            if invalid_account:
                question = f"Invalid source account '{invalid_account}'. Please select a valid account:"
            else:
                question = "What is the source account ID?"
            
            return self._create_elicitation_request(
                state,
                task_id,  # Use task_id as elicitation_id
                question,
                parameter="from_account",
                options=account_list  # Always provide list, even if empty
            )
        
        # Validate from_account exists (for accounts provided upfront, not via elicitation)
        if not self._validate_account_exists(state["from_account"]):
            # Invalid account - ask again
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            invalid_account = state["from_account"]
            state["from_account"] = None  # Reset to ask again
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(state["instance_id"], state)
            
            return self._create_elicitation_request(
                state,
                task_id,
                f"Invalid source account '{invalid_account}'. Please select a valid account:",
                parameter="from_account",
                options=account_list  # Always provide list, even if empty
            )
        
        # Check for missing to_account or invalid to_account
        if state["to_account"] is None:
            # Check if we have an invalid account marker
            invalid_account = state.pop("_invalid_to_account", None)
            
            # Generate task_id first to use as elicitation_id
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Save with the pre-generated task_id
            self.state_store.save(state["instance_id"], state)
            
            # Create appropriate question based on whether this is a retry
            if invalid_account:
                question = f"Invalid destination account '{invalid_account}'. Please select a valid account:"
            else:
                question = "What is the destination account ID?"
            
            return self._create_elicitation_request(
                state,
                task_id,  # Use task_id as elicitation_id
                question,
                parameter="to_account",
                options=account_list  # Always provide list, even if empty
            )
        
        # Validate to_account exists (for accounts provided upfront, not via elicitation)
        if not self._validate_account_exists(state["to_account"]):
            # Invalid account - ask again
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            invalid_account = state["to_account"]
            state["to_account"] = None  # Reset to ask again
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(state["instance_id"], state)
            
            return self._create_elicitation_request(
                state,
                task_id,
                f"Invalid destination account '{invalid_account}'. Please select a valid account:",
                parameter="to_account",
                options=account_list  # Always provide list, even if empty
            )
        
        # Check for missing amount
        if state["amount"] is None:
            # Generate task_id first to use as elicitation_id
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Save with the pre-generated task_id
            self.state_store.save(state["instance_id"], state)
            
            return self._create_elicitation_request(
                state,
                task_id,  # Use task_id as elicitation_id
                "What is the transfer amount?",
                parameter="amount"
            )
        
        # Validate amount is positive
        if state["amount"] <= 0:
            state["state"] = TransferState.FAILED.value
            state["error"] = "Amount must be greater than zero"
            self.state_store.save(state["instance_id"], state)
            return self._format_response(state)
        
        # Validate accounts are different
        if state["from_account"] == state["to_account"]:
            state["state"] = TransferState.FAILED.value
            state["error"] = "Cannot transfer to the same account"
            self.state_store.save(state["instance_id"], state)
            return self._format_response(state)
        
        return None
    
    def _check_balance(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Check if source account has sufficient balance"""
        from_account = state.get("from_account")
        amount = state.get("amount")
        
        if not from_account or amount is None:
            return None
        
        # Get current balance
        balance = self._get_account_balance(from_account)
        
        if balance is None:
            # Could not retrieve balance - log warning but continue
            logging.warning(f"Could not retrieve balance for account {from_account}, skipping balance check")
            return None
        
        # Check if sufficient funds
        if balance < amount:
            # Insufficient funds - ask for amount again
            task_id = str(uuid.uuid4())
            state["task_id"] = task_id
            state["state"] = TransferState.INPUT_REQUIRED.value
            state["elicitations"]["current_elicitation_id"] = task_id
            state["amount"] = None  # Reset amount to ask again
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.state_store.save(state["instance_id"], state)
            
            return self._create_elicitation_request(
                state,
                task_id,
                f"Insufficient funds in account {from_account}. Current balance: ${balance:.2f}. Please enter a different amount:",
                parameter="amount"
            )
        
        # Sufficient funds - continue
        logging.info(f"Balance check passed: {from_account} has ${balance:.2f}, transferring ${amount:.2f}")
        return None
    
    def _confirm_transfer(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Request user confirmation for the transfer"""
        # Check if we already have a current elicitation for confirmation
        current_elicitation_id = state.get("elicitations", {}).get("current_elicitation_id")
        
        # If we have a current elicitation, check if we got a response
        if current_elicitation_id and current_elicitation_id in state.get("elicitations", {}):
            response = state["elicitations"][current_elicitation_id]
            if response.get("action") == "reject" or response.get("action") == "cancel":
                state["state"] = TransferState.FAILED.value
                state["error"] = "Transfer cancelled by user"
                self.state_store.save(state["instance_id"], state)
                return self._format_response(state)
            # User confirmed, continue with transfer
            return None
        
        # Need user confirmation - generate new task_id to use as elicitation_id
        task_id = str(uuid.uuid4())
        state["task_id"] = task_id
        state["state"] = TransferState.INPUT_REQUIRED.value
        state["elicitations"]["current_elicitation_id"] = task_id
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Save with the pre-generated task_id
        self.state_store.save(state["instance_id"], state)
        
        question = f"Confirm transfer of ${state['amount']:.2f} from {state['from_account']} to {state['to_account']}?"
        return self._create_elicitation_request(
            state,
            task_id,  # Use task_id as elicitation_id
            question,
            options=["yes", "no"]
        )
    
    def _lock_accounts(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Lock accounts to prevent concurrent modifications"""
        return None
    
    def _debit_from_account(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Deduct amount from source account"""
        try:
            from_account = state["from_account"]
            amount = state["amount"]
            
            print(f"[DEBIT] Starting debit of ${amount:.2f} from {from_account}")
            
            # Get current balance
            current_balance = self._get_account_balance(from_account)
            if current_balance is None:
                state["state"] = TransferState.FAILED.value
                state["error"] = f"Failed to retrieve balance for account {from_account}"
                print(f"[DEBIT] ERROR: Failed to retrieve balance for {from_account}")
                return None
            
            print(f"[DEBIT] Current balance: ${current_balance:.2f}")
            
            # Calculate new balance
            new_balance = current_balance - amount
            print(f"[DEBIT] New balance will be: ${new_balance:.2f}")
            
            # Update account balance in database
            client = DataAPIClient(self.api_token)
            database = client.get_database(self.api_endpoint, keyspace=self.keyspace)
            table = database.get_table("accounts")
            
            # Update the balance
            print(f"[DEBIT] Updating database...")
            
            table.update_one(
                {"account_id": from_account},
                {"$set": {"balance": new_balance}}
            )
            
            # Note: AstraDB update_one returns None on success, so we verify by reading back
            # Verify the update worked by checking the new balance
            verify_balance = self._get_account_balance(from_account)
            if verify_balance is None or abs(verify_balance - new_balance) > 0.01:
                state["state"] = TransferState.FAILED.value
                state["error"] = f"Failed to debit account {from_account} - balance verification failed"
                logging.error(f"Debit failed for {from_account}: expected {new_balance}, got {verify_balance}")
                print(f"[DEBIT] ERROR: Update verification failed - expected ${new_balance:.2f}, got ${verify_balance:.2f if verify_balance else 'None'}")
                return None
            
            print(f"[DEBIT] ✓ Successfully debited ${amount:.2f} from {from_account}. New balance: ${new_balance:.2f}")
            logging.info(f"Debited ${amount:.2f} from {from_account}. New balance: ${new_balance:.2f}")
            return None
            
        except Exception as e:
            state["state"] = TransferState.FAILED.value
            state["error"] = f"Error debiting account: {str(e)}"
            logging.error(f"Exception in _debit_from_account: {e}", exc_info=True)
            return None
    
    def _credit_to_account(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Add amount to destination account"""
        try:
            to_account = state["to_account"]
            amount = state["amount"]
            
            print(f"[CREDIT] Starting credit of ${amount:.2f} to {to_account}")
            
            # Get current balance
            current_balance = self._get_account_balance(to_account)
            if current_balance is None:
                state["state"] = TransferState.FAILED.value
                print(f"[CREDIT] ERROR: Failed to retrieve balance for {to_account}")
                state["error"] = f"Failed to retrieve balance for account {to_account}"
                return None
            
            print(f"[CREDIT] Current balance: ${current_balance:.2f}")
            
            # Calculate new balance
            new_balance = current_balance + amount
            print(f"[CREDIT] New balance will be: ${new_balance:.2f}")
            
            # Update account balance in database
            client = DataAPIClient(self.api_token)
            database = client.get_database(self.api_endpoint, keyspace=self.keyspace)
            table = database.get_table("accounts")
            
            # Update the balance
            print(f"[CREDIT] Updating database...")
            
            table.update_one(
                {"account_id": to_account},
                {"$set": {"balance": new_balance}}
            )
            
            # Note: AstraDB update_one returns None on success, so we verify by reading back
            # Verify the update worked by checking the new balance
            verify_balance = self._get_account_balance(to_account)
            if verify_balance is None or abs(verify_balance - new_balance) > 0.01:
                state["state"] = TransferState.FAILED.value
                state["error"] = f"Failed to credit account {to_account} - balance verification failed"
                logging.error(f"Credit failed for {to_account}: expected {new_balance}, got {verify_balance}")
                print(f"[CREDIT] ERROR: Update verification failed - expected ${new_balance:.2f}, got ${verify_balance:.2f if verify_balance else 'None'}")
                return None
            
            print(f"[CREDIT] ✓ Successfully credited ${amount:.2f} to {to_account}. New balance: ${new_balance:.2f}")
            logging.info(f"Credited ${amount:.2f} to {to_account}. New balance: ${new_balance:.2f}")
            return None
            
        except Exception as e:
            state["state"] = TransferState.FAILED.value
            state["error"] = f"Error crediting account: {str(e)}"
            logging.error(f"Exception in _credit_to_account: {e}", exc_info=True)
            return None
    
    def _release_locks(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Release account locks"""
        return None
    
    def _record_transaction(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Record the completed transaction"""
        state["transaction_id"] = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        return None
    
    def _complete(self, state: Dict[str, Any]) -> Optional[TransferResponse]:
        """Mark transfer as complete"""
        state["output"] = {
            "transaction_id": state["transaction_id"],
            "from_account": state["from_account"],
            "to_account": state["to_account"],
            "amount": state["amount"],
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return None
    
    def _handle_elicitation_response(
        self,
        state: Dict[str, Any],
        elicitation_id: str,
        elicitation_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle user response to elicitation"""
        if "elicitations" not in state:
            state["elicitations"] = {}
        state["elicitations"][elicitation_id] = elicitation_response
        
        # Check for rejection/cancellation
        action = elicitation_response.get("action", "accept")
        if action in ["reject", "cancel"]:
            state["state"] = TransferState.FAILED.value
            state["error"] = "Transfer cancelled by user"
            # Clear pending elicitation
            state["elicitations"]["current_elicitation_id"] = None
            return state
        
        # Extract the parameter value from the response
        # Value can be at top level or in content
        value = elicitation_response.get("value")
        if not value and "content" in elicitation_response:
            content = elicitation_response["content"]
            value = content.get("value") or content.get("selected_value")
        
        if value:
            # Check what we're waiting for based on current state
            if state.get("from_account") is None:
                # Validate the account before accepting it
                if not self._validate_account_exists(str(value)):
                    # Invalid account - mark it for re-asking but don't set it
                    state["_invalid_from_account"] = str(value)
                    # Keep from_account as None so validation will ask again
                else:
                    state["from_account"] = value
                    # Clear any invalid marker
                    state.pop("_invalid_from_account", None)
            elif state.get("to_account") is None:
                # Validate the account before accepting it
                if not self._validate_account_exists(str(value)):
                    # Invalid account - mark it for re-asking but don't set it
                    state["_invalid_to_account"] = str(value)
                    # Keep to_account as None so validation will ask again
                else:
                    state["to_account"] = value
                    # Clear any invalid marker
                    state.pop("_invalid_to_account", None)
            elif state.get("amount") is None:
                state["amount"] = float(value)
            elif not state.get("confirmed"):
                # This is the confirmation response
                if str(value).lower() in ["yes", "y", "true", "1"]:
                    state["confirmed"] = True
                else:
                    state["state"] = TransferState.FAILED.value
                    state["error"] = "Transfer cancelled by user"
                    # Clear pending elicitation
                    state["elicitations"]["current_elicitation_id"] = None
                    return state
        
        # Clear the current elicitation since it has been answered
        if elicitation_id == state.get("elicitations", {}).get("current_elicitation_id"):
            state["elicitations"]["current_elicitation_id"] = None
            state["elicitations"]["current_question"] = None
            state["elicitations"]["current_parameter"] = None
            state["elicitations"]["current_options"] = None
        
        # Move from INPUT_REQUIRED back to WORKING
        if state["state"] == TransferState.INPUT_REQUIRED.value:
            state["state"] = TransferState.WORKING.value
        
        return state
    
    def _check_background_processing(self, state: Dict[str, Any], instance_id: str) -> Dict[str, Any]:
        """Check if background processing is complete and update state accordingly"""
        if "transfer_start_time" in state:
            start_time = datetime.fromisoformat(state["transfer_start_time"])
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            if elapsed >= 60:
                # Transfer is complete - perform actual database updates
                print(f"[DEBUG] Transfer processing complete after {elapsed:.1f}s - executing database updates")
                
                # Execute the actual transfer steps
                debit_result = self._debit_from_account(state)
                if debit_result is not None:
                    # Debit failed - save error state and return
                    state["state"] = TransferState.FAILED.value
                    state["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.state_store.save(instance_id, state)
                    return state
                
                credit_result = self._credit_to_account(state)
                if credit_result is not None:
                    # Credit failed - save error state and return
                    state["state"] = TransferState.FAILED.value
                    state["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.state_store.save(instance_id, state)
                    return state
                
                # Both operations succeeded - finalize
                transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
                state["transaction_id"] = transaction_id
                state["output"] = {
                    "transaction_id": transaction_id,
                    "from_account": state["from_account"],
                    "to_account": state["to_account"],
                    "amount": state["amount"],
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                state["state"] = TransferState.COMPLETED.value
                state["message"] = f"Transfer completed successfully. Transaction ID: {transaction_id}"
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
            else:
                # Still processing - update message with remaining time
                remaining = 60 - elapsed
                print(f"[DEBUG] Transfer still processing... {remaining:.1f}s remaining")
                state["message"] = f"Transfer is being processed in the background. Approximately {remaining:.0f} seconds remaining."
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.state_store.save(instance_id, state)
        
        return state
    
    def _cancel_flow(self, state: Dict[str, Any]) -> TransferResponse:
        """Cancel the transfer"""
        state["state"] = TransferState.FAILED.value
        state["error"] = "Transfer was cancelled by user"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state_store.save(state["instance_id"], state)
        return self._format_response(state)
    
    def _error_response(self, instance_id: str, error_message: str) -> TransferResponse:
        """Create error response"""
        now = datetime.now(timezone.utc).isoformat()
        status = TransferStatus(
            instance_id=instance_id,
            name="transfer_money",
            state=TransferState.FAILED.value,
            message=error_message,
            created_at=now,
            updated_at=now
        )
        return TransferResponse(status=status)
    
    def _format_response(self, state: Dict[str, Any]) -> TransferResponse:
        """Format response according to RFC-0792"""
        # If state is INPUT_REQUIRED and there's a pending elicitation, recreate it
        if state["state"] == TransferState.INPUT_REQUIRED.value:
            current_elicitation_id = state.get("elicitations", {}).get("current_elicitation_id")
            if current_elicitation_id:
                # Recreate the elicitation response from stored state data
                question = state["elicitations"].get("current_question")
                parameter = state["elicitations"].get("current_parameter")
                options = state["elicitations"].get("current_options")
                
                if question:
                    # Use the stored elicitation data to recreate the response
                    return self._create_elicitation_request(
                        state,
                        current_elicitation_id,
                        question,
                        parameter,
                        options
                    )
        
        # Build status
        status_dict = {
            "instance_id": state["instance_id"],
            "name": state["name"],
            "state": state["state"],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"]
        }
        
        # Add current input values to status
        status_dict["inputs"] = TransferInputs(
            from_account=state.get("from_account"),
            to_account=state.get("to_account"),
            amount=state.get("amount")
        )
        
        # Add message if present in state
        if state.get("message"):
            status_dict["message"] = state["message"]
        elif state["state"] == TransferState.FAILED.value and state.get("error"):
            status_dict["message"] = state["error"]
        
        # Add progress for working state
        if state["state"] == TransferState.WORKING.value:
            # Use progress from state if already set, otherwise generate from current_step
            if "progress" in state and isinstance(state["progress"], dict):
                status_dict["progress"] = TransferProgress(**state["progress"])
            elif "current_step" in state:
                status_dict["progress"] = TransferProgress(
                    current_step=self._get_step_message(state["current_step"]),
                    step_number=state.get("step_index", 0) + 1,
                    total_steps=len(self.steps)
                )
        
        status = TransferStatus(**status_dict)
        
        # Add output for completed state
        output = None
        if state["state"] == TransferState.COMPLETED.value and state.get("output"):
            output = TransferOutput(**state["output"])
        
        return TransferResponse(status=status, output=output)
    
    def _get_step_message(self, step: str) -> str:
        """Get user-friendly message for a step"""
        messages = {
            "validate_input": "Validating transfer details...",
            "check_balance": "Checking account balance...",
            "confirm_transfer": "Awaiting confirmation...",
            "lock_accounts": "Securing accounts...",
            "debit_from_account": "Processing debit...",
            "credit_to_account": "Processing credit...",
            "release_locks": "Finalizing transaction...",
            "record_transaction": "Recording transaction...",
            "complete": "Completing transfer..."
        }
        return messages.get(step, "Processing...")


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
            import logging
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


@tool(
    permission=ToolPermission.READ_WRITE,
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_PERSONAL_BANKING, type=ConnectionType.KEY_VALUE)
    ]
)
def transfer_money(
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
    amount: Optional[float] = None,
    instance_id: Optional[str] = None,
    transfer_action: Optional[str] = None,
    elicitation_id: Optional[str] = None,
    elicitation_response: Optional[ElicitationResponse] = None
) -> TransferResponse:
    """Transfer money between accounts with re-entrant support.
    
    This tool implements a banking transfer flow.
    It can be called multiple times with the same instance_id to resume execution,
    provide user input, check status, or cancel the operation. State is persisted
    for reliability across invocations.
    
    Usage:
    - New transfer: Call with from_account, to_account, amount (missing params trigger elicitation)
    - Continue flow: Call with instance_id + elicitation_response when state="input_required"
    - Check status: Call with instance_id + transfer_action="status"
    - Change inputs: Call with instance_id + transfer_action="input_changed" + new parameters
    - Cancel: Call with instance_id + transfer_action="cancel"
    
    CRITICAL RULES - MUST FOLLOW:
    1. NEVER claim a transfer is complete unless the tool returns state="completed" with a transaction_id.
    2. NEVER make up or fabricate transfer results. Only report what the tool actually returns.
    3. When state="failed", the transfer has FAILED - inform the user of the failure and the error message.
    4. When state="input_required", WAIT for user input - do NOT call the tool again until user responds.
    5. When state="working", the transfer is processing in background (~60 seconds):
       - Do NOT call repeatedly or automatically poll
       - Inform user it's processing and suggest they ask you to check status later
       - Do NOT claim it's complete until you call with transfer_action="status" and get state="completed"
    6. Only call again when: (a) user provides input for elicitation, (b) user explicitly asks
       to check status, or (c) user wants to cancel.
    7. If the tool fails multiple times, do NOT pretend the transfer succeeded. Report the actual failure.
    
    ELICITATION HANDLING - CRITICAL:
    When responding to elicitations (state="input_required"):
    - You MUST provide BOTH elicitation_id AND elicitation_response parameters
    - The elicitation_id is found in status.elicitation.elicitation_id from the previous response
    - Example: transfer_money(instance_id="...", elicitation_id="...", elicitation_response={...})
    - If you forget the elicitation_id, the tool will re-present the question with a reminder
    
    Status responses include current parameter values (from_account, to_account, amount).
    
    Args:
        from_account: Source account ID (e.g., "CHK-001"). Optional - will be requested via elicitation if not provided.
        to_account: Destination account ID (e.g., "SAV-002"). Optional - will be requested via elicitation if not provided.
        amount: Amount to transfer (must be positive). Optional - will be requested via elicitation if not provided.
        instance_id: Existing transfer instance ID for re-entrant calls
        transfer_action: Transfer control action with three possible values:
            - "cancel": Terminate the transfer and return failed state
            - "status": Get current status immediately without timeout
            - "input_changed": Update input parameters and restart flow from appropriate step
        elicitation_id: ID of elicitation being responded to
        elicitation_response: User's response to elicitation (ElicitationResponse object or dict)
            - value: User's response (string, float, boolean, etc.)
            - action: "accept" (default), "reject", or "cancel"
            - content: Optional additional content (dict)
        
        Example: ElicitationResponse(value="CHK-001", action="accept")
        Or as dict: {"value": "CHK-001", "action": "accept"}
    
    Returns:
        Transfer response with output and status containing instance_id, state, progress, and elicitation details
    """
    # Get credentials from connections or environment variables
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Convert ElicitationResponse to dict if provided
    elicitation_dict = None
    if elicitation_response is not None:
        if isinstance(elicitation_response, ElicitationResponse):
            elicitation_dict = elicitation_response.model_dump()
        else:
            elicitation_dict = elicitation_response
    
    # Create a new instance for each call (tools are stateless)
    tool = ReentrantTransferTool(api_token=api_token, api_endpoint=api_endpoint, keyspace=keyspace)
    return tool.transfer_money(
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        instance_id=instance_id,
        transfer_action=transfer_action,
        elicitation_id=elicitation_id,
        elicitation_response=elicitation_dict
    )
