# Personal Banking Tools - Interactive Tester

This interactive tester allows you to test different scenarios with the personal banking tools including transfers and contact management.

## Prerequisites

1. **AstraDB Setup**: Make sure you have set up your AstraDB database and table:
   ```bash
   ./setup_astra_table.sh
   ```

2. **Environment Variables**: Create a `.env` file with your AstraDB credentials:
   ```bash
   cp .env.example .env
   # Edit .env and add your ASTRA_TOKEN and ASTRA_URL
   ```

3. **Python Dependencies**: Install required packages:
   ```bash
   pip install astrapy python-dotenv
   ```

## Running the Tester

### Option 1: Direct Execution
```bash
cd examples/agent_builder/personal_banking
python personal_banking_tester.py
```

### Option 2: Make it executable (Unix/Linux/Mac)
```bash
chmod +x personal_banking_tester.py
./personal_banking_tester.py
```

## Available Test Scenarios

The tester provides an interactive menu with the following test scenarios:

### 1. Complete Transfer with All Parameters
Tests a straightforward transfer where all required parameters are provided upfront:
- Source account
- Destination account
- Amount

The tool will still request confirmation before completing the transfer.

### 2. Transfer with Missing Parameters (Elicitation)
Tests the elicitation flow where parameters are missing:
- Starts with no parameters
- Tool requests each missing parameter one by one
- Demonstrates the re-entrant nature of the tool
- Shows how state is maintained across multiple calls

### 3. Cancel a Transfer
Tests the cancellation flow:
- Initiates a transfer
- Cancels it using the `flow_action="cancel"` parameter
- Shows how to abort an in-progress transfer

### 4. Resume a Transfer with instance_id
Tests resuming a paused transfer:
- Starts a transfer
- Saves the `instance_id`
- Simulates resuming the transfer later
- Demonstrates state persistence

### 5. Do Something Else (Digression)
Simulates user digression - asking about something unrelated to the current transfer.

### 6. List Account Balances
Displays all accounts and their current balances from the database.

### 7. Get Contact Information
Retrieves the logged-in user's contact information including name, address, and email.

### 8. Update Contact Information
Updates one or more contact fields (name, address, email) for the logged-in user.

## Understanding the Output

Each test will display JSON responses showing:

- **status**: Current state of the transfer
  - `instance_id`: Unique identifier for this transfer flow
  - `state`: Current state (`working`, `input_required`, `completed`, `failed`)
  - `elicitation`: Information about requested user input (if applicable)
  - `progress`: Current step and progress information

- **output**: Final transfer details (when completed)
  - `transaction_id`: Unique transaction identifier
  - `from_account`: Source account
  - `to_account`: Destination account
  - `amount`: Transfer amount
  - `status`: Final status
  - `timestamp`: Completion timestamp

## Example Session

```
Personal Banking Tools - Interactive Tester
================================================================================

Available Tests:
1. Complete transfer with all parameters
2. Transfer with missing parameters (elicitation)
3. Cancel a transfer
4. Resume a transfer with instance_id
5. Do something else (digression)
6. List account balances
7. Get contact information
8. Update contact information
q. Quit

Select a test (1-8, q): 1

================================================================================

TEST 1: Complete Transfer with All Parameters

================================================================================

Enter source account [CHK-001]: CHK-001
Enter destination account [SAV-002]: SAV-002
Enter amount [100.00]: 150.00

Initiating transfer...

Response:
{
  "status": {
    "instance_id": "abc123...",
    "name": "transfer_money",
    "state": "input_required",
    "elicitation": {
      "elicitation_id": "confirm-xyz",
      "question": "Confirm transfer of $150.00 from CHK-001 to SAV-002?",
      "options": ["yes", "no"]
    },
    ...
  }
}

Confirm transfer of $150.00 from CHK-001 to SAV-002?
Confirm? (yes/no) [yes]: yes

Sending confirmation...

After Confirmation:
{
  "status": {
    "instance_id": "abc123...",
    "name": "transfer_money",
    "state": "completed",
    ...
  },
  "output": {
    "transaction_id": "TXN-12345678",
    "from_account": "CHK-001",
    "to_account": "SAV-002",
    "amount": 150.0,
    "status": "completed",
    "timestamp": "2026-03-27T14:30:00.000Z"
  }
}
```

## Troubleshooting

### Import Error
If you get an import error, make sure you're running the script from the correct directory:
```bash
cd examples/agent_builder/personal_banking
python personal_banking_tester.py
```

### AstraDB Connection Error
If you get connection errors:
1. Verify your `.env` file has correct `ASTRA_TOKEN` and `ASTRA_URL`
2. Make sure the AstraDB table is set up: `./setup_astra_table.sh`
3. Check that your AstraDB token has not expired

### State Not Found Error
If you get "Flow instance not found" errors:
- The state may have expired (default TTL is 3600 seconds)
- The instance_id may be incorrect
- The database table may have been cleared

## Notes

- Each transfer creates a new `instance_id` for tracking
- State is persisted in AstraDB for reliability
- The tool demonstrates RFC-0792 flow behavior
- All transfers are simulated (no real money is transferred)
- The tool includes built-in delays to simulate processing time

## Cleanup

To delete the AstraDB table and all state data:
```bash
./delete_astra_table.sh