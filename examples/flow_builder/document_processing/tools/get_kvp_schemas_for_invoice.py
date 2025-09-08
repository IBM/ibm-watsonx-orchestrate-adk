from typing import Literal, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_kvp_schemas_for_invoice(place_holder: str) -> list:
    """
    Return a DocProcKVPSchema object
    Args:
        place_holder (str): str object

    Returns:
        DocProcKVPSchema: A DocProcKVPSchema object
    """


    return [{
  "document_type": "Invoice",
  "document_description": "An invoice is a financial document issued by a seller to a buyer, outlining products or services provided, quantities, prices, and payment terms. It serves as a request for payment in a sales transaction.",
  "fields": {
    "company_name": {
      "description": "Name of the company issuing the invoice.",
      "example": "ABC Corporation",
      "default": ""
    },
    "company_address": {
      "description": "Address of the company.",
      "example": "123 Business St, Sydney, NSW",
      "default": ""
    },
    "company_telephone": {
      "description": "Telephone number of the company.",
      "example": "+61 2 1234 5678",
      "default": ""
    },
    "company_fax": {
      "description": "Fax number of the company.",
      "example": "+61 2 8765 4321",
      "default": ""
    },
    "invoice_no": {
      "description": "Invoice number assigned by the company.",
      "example": "12345",
      "default": ""
    },
    "invoice_date": {
      "description": "Invoice issue date.",
      "example": "2025-07-14",
      "default": ""
    },
    "line_items": {
      "type": "array",
      "description": "List of items included in the invoice.",
      "columns": {
        "item_no": {
          "description": "Material or product number.",
          "example": "12345",
          "default": ""
        },
        "description": {
          "description": "Description of the material or product. This can appear in multiple lines.",
          "example": "Steel rods 10mm 85% PEFC certified",
          "default": ""
        },
        "quantity": {
          "description": "Quantity of the item supplied.",
          "example": "50",
          "default": ""
        },
        "uom": {
          "description": "Unit of measure for the item.",
          "example": "1000.00",
          "default": ""
        },

        "price_per_unit": {
          "description": "Price per unit of the item.",
          "example": "20.00",
          "default": ""
        },
        "amount": {
          "description": "Total amount.",
          "example": "1000.00",
          "default": ""
        },
        "gst": {
          "description": "GST amount applied to the item.",
          "example": "100.00",
          "default": ""
        },
        "amount_incl_gst": {
          "description": "Total amount including GST.",
          "example": "1100.00",
          "default": ""
        },
        "delivery_no": {
          "description": "Delivery number for the item shipment. Look next to 'Del No.'",
          "example": "803883243",
          "default": ""
        },
        "customer_part_no": {
          "description": "Customer's part number for the item. Look next to 'Cust Part No.'",
          "example": "CUST-5678",
          "default": ""
        }
      }
    }
  }
}]
