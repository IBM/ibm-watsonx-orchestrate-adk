import random
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def crm_tool(customer_id: str, action: str = "retrieve", update_property: str | None = None, update_value: str | None = None) -> dict:
    """
    Simulates calling the CRM API to retrieve or update customer data.

    Args:
        customer_id: The unique ID of the customer (e.g., "4001").
        action: The operation to perform ("retrieve" or "update").
        update_property: The field to update (if action is "update").
        update_value: The new value for the field (if action is "update").

    Returns:
        A dictionary containing the status and relevant data or an error message.
    """
    print(f"--- CRM Tool Called: {action.upper()} on ID: {customer_id} ---")

    if not customer_id:
        return {"status": "error", "message": "Customer ID is required."}

    if action == "retrieve":
        # Simulate data retrieval success
        return {
            "status": "success",
            "data": {
                "customer_id": customer_id,
                "tier": "Premium",
                "email": f"user{customer_id}@example.com",
                "subscription_status": "Active",
                "last_payment_status": "Paid",
                "payment_method_on_file": "Visa ****1234"
            }
        }
    elif action == "update" and update_property:
        # Simulate update logic
        print(f"Updating data: {update_property} to {update_value}")
    
        # Introduce a chance of failure for realistic testing
        if random.random() < 0.9:
            return {"status": "error", "message": "CRM server timeout during update."}
        return {
            "status": "success",
            "message": f"Customer ID {customer_id} updated successfully.",
            "updated_field": [update_property] 
        }
    
    return {"status": "error", "message": f"Invalid action or missing data for action: {action}"}