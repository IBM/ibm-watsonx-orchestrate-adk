import json
from datetime import date, timedelta
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# Simulates a data tool that returns large, structured JSON.
@tool(
    name="get_order_history",
    description=(
        "Retrieve the full order history for a customer account. "
        "Returns a structured JSON list of all orders, including line items. "
        "For high-volume accounts this response can be very large."
    ),
    permission=ToolPermission.READ_ONLY,
)
def get_order_history(customer_id: str, max_orders: int = 200) -> str:
    """
    Fetch a customer's order history.

    Args:
        customer_id: The unique identifier for the customer account.
        max_orders:  Maximum number of orders to return (default 200).
                     Set high intentionally to exercise large-message compaction.

    Returns:
        A JSON string containing order records. May be large for active accounts.
    """

    # --- Mock: generate synthetic order records ---
    # Might need to increase response lenght depending on your compaction settings
    orders = []

    for i in range(min(max_orders, 200)):
        order = {
            "order_id": f"ORD-{customer_id}-{10000 + i}",            
            "status": "DELIVERED" if i % 5 != 0 else "PENDING",
            "total": round(50.0 + (i * 7.35) % 500, 2),
            "line_items": [
                {
                    "sku": f"SKU-{100 + j}",
                    "description": f"Product {100 + j} — Standard Edition",
                    "quantity": (j % 3) + 1,
                    "unit_price_usd": round(12.99 + j * 3.5, 2),
                }
                for j in range(5)  # 5 line items per order
            ]
        }
        orders.append(order)

    result = {
        "customer_id": customer_id,
        "total_orders": len(orders),
        "orders": orders,
    }
    
    return json.dumps(result, indent=2)
