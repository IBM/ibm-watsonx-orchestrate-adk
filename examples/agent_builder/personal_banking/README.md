# Personal Banking Agent Example

This example demonstrates how to create a personal banking agent with Python tools that simulate stateful, long-running operations.

## Purpose

This example demonstrates key techniques for building sophisticated Python tools:

1. **Re-entrant Python Tools**: How to build tools that can be called multiple times with the same `instance_id` to resume execution from where they left off
2. **Multi-Step User Interactions**: How to implement tools that require multiple confirmations and interactions with users through elicitation
3. **External State Persistence**: How to use external databases (AstraDB) to maintain state across tool invocations
4. **Simulated Long-Running Operations**: How to simulate background processing by checking elapsed time between invocations. In real life system, the long running operation will be maintained in an external system.

**Important Note on Python Tool Architecture:**
Python tools themselves are **stateless** and **not long-running**. Each tool invocation is a synchronous, short-lived execution. To simulate stateful behavior and background operations, this example relies on **external services** (AstraDB) to persist state between invocations. The "long-running" behavior is simulated through re-entrant calls that resume from saved state.

For production use cases requiring true background processing and stateful operations, consider using **wxO Agentic Workflow**, which provides native support for long-running workflows, state management, and asynchronous execution.

## Prerequisites

### AstraDB Setup

This example uses AstraDB for persistent state storage. You'll need:

1. **AstraDB Account**: Sign up at [astra.datastax.com](https://astra.datastax.com)

2. **Database Setup**:
   - Create a database (or use existing)
   - Note your API Endpoint: `https://[database-id]-[region].apps.astra.datastax.com`

3. **Generate Application Token**:
   - Go to Settings → Tokens in AstraDB console
   - Create a new token with "Database Administrator" role
   - Copy the token (starts with `AstraCS:...`)

4. **Configure Environment**:
   Create a `.env` file with your AstraDB credentials:
   ```bash
   # AstraDB Configuration
   # Get your token from: https://astra.datastax.com/settings/tokens
   ASTRA_TOKEN=AstraCS:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ASTRA_URL=https://<your-astra-endpoint>
   ASTRA_KEYSPACE=default_keyspace
   ```

5. **Create the Tables**:
   ```bash
   # Run the setup script to create both required tables
   chmod +x setup_astra_table.sh
   ./setup_astra_table.sh
   ```
   
   This creates two tables:
   
   **transaction_data table** (for flow state persistence):
   - `instance_id` (uuid, INDEXED): Unique flow instance identifier
   - `task_id` (uuid, PRIMARY KEY): Task/interaction identifier
   - `state` (text): Current flow state
   - `state_data` (text): JSON string containing full flow state
   - `created_at` (text): ISO 8601 timestamp
   - `updated_at` (text): ISO 8601 timestamp
   
   **accounts table** (for account balances):
   - `account_id` (text, PRIMARY KEY): Unique account identifier
   - `account_type` (text): Type of account (checking, savings, etc.)
   - `balance` (decimal): Current account balance
   
   The accounts table is initialized with sample data from `account_list.json`:
   - CHK-001 (checking): $1000
   - SAV-002 (savings): $1000
   - CHK-003 (checking): $1000
   - SAV-004 (savings): $1000
   - CHK-005 (checking): $1000

## Overview

This example includes several Python tools that demonstrate how to simulate stateful, long-running operations using external state persistence:

### Transfer Money Tool
The `transfer_money` tool simulates a multi-step money transfer process with:
- **Synchronous execution with timeout** (30 seconds default)
- **Re-entrant calls** using `instance_id` to resume execution
- **State persistence** in AstraDB across multiple invocations
- **User input elicitation** with confirmation dialogs
- **Progress tracking** with step-by-step status
- **Cancellation support** via `flow_action` parameter
- **Four operation states**: `working`, `input_required`, `completed`, `failed`

### Additional Tools
- **list_accounts**: Retrieve all account balances from the database
- **get_contact**: Get user contact information
- **change_contact**: Update user contact information (name, address, email)

## Key Features

### 1. Re-entrant Behavior
The tool can be called multiple times with the same `instance_id` to:
- Resume execution after timeout
- Provide user input responses
- Check current status
- Cancel the operation

### 2. Operation States
- **working**: Operation is currently executing
- **input_required**: Operation is waiting for user input
- **completed**: Operation finished successfully
- **failed**: Operation encountered an error or was cancelled

### 3. Workflow Steps
The transfer process includes 9 discrete steps:
1. Validate input parameters
2. Check account balance
3. Request user confirmation (elicitation)
4. Lock accounts
5. Debit from source account
6. Credit to destination account
7. Release locks
8. Record transaction
9. Complete transfer

## Usage

The tools can be used directly in Python or through the WatsonX Orchestrate agent. The transfer_money tool supports:
- Initial transfer requests with account and amount
- Re-entrant calls using `instance_id` to resume or check status
- User confirmation through elicitation
- Cancellation via `flow_action="cancel"`

## Tool Parameters

### transfer_money
- **Required**: `from_account`, `to_account`, `amount`
- **Optional**: `instance_id` (for resuming), `transfer_action` (for cancellation), `elicitation_id` and `elicitation_response` (for user input)

### list_accounts
- No parameters required

### get_contact
- No parameters required

### change_contact
- **Optional**: `name`, `address`, `email` (at least one required)

## Installation

1. **Set up AstraDB** (see Prerequisites above)

2. **Configure environment**:
   ```bash
   cd examples/agent_builder/personal_banking
   ```
   Create a `.env` file with your AstraDB credentials:
   ```bash
   # AstraDB Configuration
   # Get your token from: https://astra.datastax.com/settings/tokens
   ASTRA_TOKEN=AstraCS:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ASTRA_URL=https://<your-astra-endpoint>
   ASTRA_KEYSPACE=default_keyspace
   ```

3. **Create the AstraDB tables**:
   ```bash
   chmod +x setup_astra_table.sh
   ./setup_astra_table.sh
   ```

4. **Install dependencies**:
   ```bash
   pip install -r tools/requirements.txt
   ```

5. **Import the tool and agent**:
   ```bash
   chmod +x import-all.sh
   ./import-all.sh
   ```

   The script will:
   - Configure the AstraDB connections (token and URL)
   - Import the Python tool (with dependencies)
   - Import the agent

## State Persistence

Operation state is **manually persisted** to **AstraDB** using the Table API. The tool explicitly calls `state_store.save()` and `state_store.load()` to manage state. This allows:
- **Persistent state**: State survives tool restarts and can be resumed across invocations
- **Scalable**: Handles multiple concurrent operations
- **Reliable**: Built on Apache Cassandra
- **TTL Support**: Automatic cleanup of expired states (1 hour default)

**Note**: State persistence is not automatic - the tool code must explicitly save state to AstraDB after each significant change.

## Testing with an Agent

To test this tool with a WatsonX Orchestrate agent:

1. **Ensure AstraDB is configured** (see Installation above)

2. **Chat with the agent**:
```bash
orchestrate chat -a personal_banking_agent
```

3. **Try these scenarios**:
   - "Transfer $100 from CHK-001 to SAV-002"
   - "What's the status of my transfer?" (while it's running)
   - "Cancel the transfer" (to test cancellation)
   - Answer "yes" or "no" to confirmation prompts

## Key Behaviors Demonstrated

This example demonstrates several important patterns for simulating stateful, long-running operations with Python tools:

1. **Progressive Parameter Collection**: The tool uses elicitation to collect missing parameters one at a time:
   - Requests `from_account` if not provided
   - Requests `to_account` if not provided
   - Requests `amount` if not provided
   - Validates each parameter and re-requests if invalid

2. **Account Validation**: Validates that accounts exist in the database before proceeding, using elicitation to request valid accounts if invalid ones are provided

3. **Balance Checking**: Verifies sufficient funds before allowing transfer to proceed, with elicitation to request a different amount if insufficient

4. **User Confirmation**: Requests explicit user confirmation before executing the transfer with a yes/no elicitation

5. **Simulated Background Processing**:
   - Initial call starts the transfer and returns after 10 seconds with `WORKING` state
   - Subsequent re-entrant calls check elapsed time (60 seconds total) to simulate background processing
   - State transitions from `WORKING` to `COMPLETED` when simulated time elapses
   - Demonstrates how to simulate long-running operations that span multiple tool invocations

6. **Re-entrancy with Manual State Persistence**:
   - Tool can be called multiple times with the same `instance_id` to check status or resume
   - State is manually saved to AstraDB using `state_store.save()` after each significant change
   - State is loaded from AstraDB using `state_store.load()` when resuming with an `instance_id`
   - Supports parameter updates during re-entrant calls via `transfer_action="input_changed"`

7. **Elicitation Response Handling**: Properly handles user responses to elicitations with validation of `elicitation_id` and `elicitation_response` parameters

8. **Cancellation Support**: Users can cancel operations at any time via `transfer_action="cancel"`

9. **Progress Tracking**: Reports current step and progress through the simulated multi-step process

## Implementation Notes

### Python Tool Limitations

**Python tools are stateless and synchronous by design.** They:
- Execute as short-lived, synchronous function calls
- Do not maintain state between invocations
- Cannot run background processes or operations
- Rely on external services (like AstraDB in this example) to persist state
- Simulate long-running behavior through re-entrant calls and external state storage

This example demonstrates a **simulation pattern** where:
- State is persisted to AstraDB between tool invocations
- The tool is called multiple times with the same `instance_id` to resume execution
- Each invocation is still synchronous and completes within the timeout period
- Background operations are simulated, not actually running in the background

### When to Use wxO Agentic Workflow

For production use cases that require true stateful, long-running operations, consider using **wxO Agentic Workflow** instead of Python tools. Agentic Workflow provides:
- **Native state management**: Built-in state persistence without external dependencies
- **True background execution**: Operations that run asynchronously in the background
- **Long-running workflows**: Support for workflows that span hours or days
- **Event-driven architecture**: React to external events and triggers
- **Workflow orchestration**: Complex multi-step processes with branching and parallel execution

### Production Considerations

A production banking system would also:
- Use enterprise-grade state store with high availability (this uses AstraDB which is production-ready)
- Implement proper account locking mechanisms with distributed locks
- Actually interact with banking systems via secure APIs
- Handle distributed execution across multiple nodes
- Provide more sophisticated error handling and retry logic
- Implement compensation/rollback for partial failures
- Include comprehensive audit logging and compliance features
- Support transaction versioning and history

## Utility Scripts

### Reset Account Balances

After testing transfers, you can reset all account balances back to their initial values:

```bash
./reset_accounts_balance.sh
```

This script:
- Reads account data from `account_list.json`
- Updates all account balances in the database
- Uses upsert to create accounts if they don't exist

## Files

- `tools/transfer_money.py` - Main re-entrant tool implementation
- `tools/list_accounts.py` - Tool to list available accounts
- `tools/get_contact.py` - Tool to retrieve user contact information
- `tools/change_contact.py` - Tool to update user contact information
- `tools/requirements.txt` - Python dependencies for the tools
- `agents/personal_banking_agent.yaml` - Agent configuration
- `account_list.json` - Initial account data with balances
- `contacts.json` - User contact information data
- `setup_astra_table.sh` - Script to create both transaction_data and accounts tables
- `delete_astra_table.sh` - Script to delete both transaction_data and accounts tables
- `reset_accounts_balance.sh` - Script to reset account balances to initial values
- `import-all.sh` - Script to import tools and agent
- `personal_banking_tester.py` - Standalone test script for testing tools
- `.env.example` - Example environment configuration file (create `.env` from this)
- `README.md` - This file
- `TESTER_README.md` - Documentation for the test script
- `TRANSFER_MONEY_SPEC.md` - Detailed specification for the transfer_money tool

## Learn More

- [AstraDB Documentation](https://docs.datastax.com/en/astra/home/astra.html)
- [WatsonX Orchestrate Agent Builder Documentation](https://ibm.github.io/watsonx-orchestrate/)