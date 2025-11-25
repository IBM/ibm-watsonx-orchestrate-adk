import logging
from typing import Any, Dict, List

from ibm_watsonx_orchestrate.flow_builder.flows import (
    END,
    START,
    Flow,
    flow,
)
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput

# Configure logging
logger = logging.getLogger(__name__)


def get_sample_invoice_kvp_schema() -> List[Dict[str, Any]]:
    """
    Generate a sample KVP schema for invoice document processing.
    
    This schema defines the structure and fields to extract from invoice documents,
    including company information, invoice metadata, and line items.
    
    Returns:
        List[Dict[str, Any]]: A list containing the invoice KVP schema definition
        
    """
    return [{
        "document_type": "MyInvoice",
        "document_description": (
            "An invoice is a financial document issued by a seller to a buyer, "
            "outlining products or services provided, quantities, prices, and payment terms."
        ),
        "fields": {
            "company_name": {
                "description": "Name of the company issuing the invoice.",
                "example": "ABC Corporation",
                "default": "",
            },
            "company_address": {
                "description": "Address of the company.",
                "example": "123 Business St, Sydney, NSW",
                "default": "",
            },
            "invoice_number": {
                "description": "Invoice number assigned by the company.",
                "example": "12345",
                "default": "",
            },
            "invoice_date": {
                "description": "Invoice issue date in ISO 8601 format.",
                "example": "2025-07-14",
                "default": "",
            },
            "line_items": {
                "type": "array",
                "description": "List of items included in the invoice.",
                "columns": {
                    "item_no": {
                        "description": "Material or product number.",
                        "example": "12345",
                        "default": "",
                    },
                    "description": {
                        "description": "Description of the material or product. This can appear in multiple lines.",
                        "example": "Steel rods 10mm 85% PEFC certified",
                        "default": "",
                    },
                    "quantity": {
                        "description": "Quantity of the item supplied.",
                        "example": "50",
                        "default": "",
                    },
                    "price_per_unit": {
                        "description": "Price per unit of the item.",
                        "example": "20.00",
                        "default": "",
                    },
                    "amount": {
                        "description": "Total amount for the item (quantity × price_per_unit).",
                        "example": "1000.00",
                        "default": "",
                    },
                },
            },
        },
    }]


@flow(
    name="text_extraction_kvps_flow_example",
    display_name="Text Extraction with KVP Extraction Flow",
    description=(
        "This flow consists of one node: a docproc node, which extracts text "
        "and custom key-value pairs from the input document using a predefined schema"
    ),
    input_schema=DocProcInput,
)
def build_docproc_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow with Key-Value Pair (KVP) extraction capabilities.
    
    This flow creates a document processing pipeline that:
    1. Extracts raw text content from input documents
    2. Identifies and extracts structured key-value pairs based on a predefined schema
    
    The KVP extraction uses a schema-driven approach to identify specific fields
    like company information, invoice numbers, dates, and line items from invoices.
    
    Runtime Parameter Override:
        All KVP-related parameters (kvp_schemas, kvp_model_name, kvp_force_schema_name,
        kvp_enable_text_hints) can be provided at runtime when invoking the flow.
        Runtime values will override the default values configured in this flow definition.
        This allows for dynamic configuration without modifying the flow code.
    
    Args:
        aflow: Flow builder instance provided by the @flow decorator.
    
    Returns:
        Flow: Configured text extraction flow with KVP extraction
            (START → docproc_node → END)
        
    Example:
        >>> flow = build_docproc_flow()
        >>> # Flow will extract text and KVPs from documents
    """
    # Validate Flow instance (defensive programming)
    assert aflow is not None, "Flow instance must be provided by the @flow decorator"
    
    try:
        # Get the KVP schema for invoice processing
        kvp_schemas = get_sample_invoice_kvp_schema()
        
        # Create document processing node configured for text and KVP extraction
        doc_proc_node = aflow.docproc(
            name="text_extraction_with_kvp_node",
            display_name="Text Extraction with KVP Node",
            description="Extracts raw text and structured key-value pairs from an input document",
            task="text_extraction",
            # KVP extraction parameters.
            #  Note: All kvp_* parameters below can be overridden at runtime when invoking the flow.
            #  Runtime values take precedence over these default configuration values.
            kvp_schemas=kvp_schemas,  # type: ignore[arg-type]  # Can be overridden at runtime
            # Optional: Uncomment to use a specific LLM for KVP extraction. This defaults to mistral-small. (can be overridden at runtime)
            # kvp_model_name="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
            # Optional: Uncomment to force a specific schema (can be overridden at runtime)
            # kvp_force_schema_name="MyInvoice", # The "document_type" that will be used for KVP extraction. If not specified, the engine will try to match the input document to the given schemas.
            # Optional: Enable/disable text hints for KVP extraction (can be overridden at runtime)
            # kvp_enable_text_hints=True,
        )
        
        # Connect nodes in sequence: START → doc_proc_node → END
        aflow.sequence(START, doc_proc_node, END)
        
        logger.info("Text extraction with KVP flow built successfully")
        return aflow
        
    except Exception as e:
        logger.error(f"Failed to build text extraction KVP flow: {e}", exc_info=True)
        raise
