from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def payment_tool(action: str, transaction_id: str | None = None, amount: float | None = None) -> dict:
    """
    Simulates calling the Payment Gateway API to execute transactions or check status.

    Args:
        action: The transaction operation ("check_history", "process_refund").
        transaction_id: The ID of the transaction to look up or refund.
        amount: The amount for the refund (required for 'process_refund').

    Returns:
        A dictionary containing the status and results of the transaction attempt.
    """
    print(f"--- Payment Tool Called: {action.upper()} ---")

    if action == "check_history":
        if not transaction_id:
            return {"status": "error", "message": "Transaction ID is required to check history."}
        # Simulate payment history check
        return {
            "status": "success",
            "data": {
                "transaction_id": transaction_id,
                "date": "2025-11-20",
                "amount": 100.00,
                "currency": "USD",
                "status": "Settled",
                "is_refunded": False
            }
        }
    
    elif action == "process_refund":
        if not transaction_id or not amount or amount <= 0:
            return {"status": "error", "message": "Transaction ID and valid amount are required for refund."}
        
        # Simulate refund processing success
        # Check if refund already exists (simulated complexity)
        if "refunded" in transaction_id.lower():
             return {"status": "error", "message": f"Transaction {transaction_id} already refunded."}

        return {
            "status": "success",
            "message": f"Refund of ${amount:.2f} successfully queued for transaction {transaction_id}.",
            "new_transaction_id": "REFUND-12345"
        }

    return {"status": "error", "message": f"Unsupported payment action: {action}"}