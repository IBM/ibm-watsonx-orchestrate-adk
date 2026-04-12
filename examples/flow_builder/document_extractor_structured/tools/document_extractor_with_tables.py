"""
Document Extractor with Tables Tool.

This module provides a flow builder tool for extracting structured data from documents,
including support for table extraction. It defines a custom schema for fields to extract
and creates a document extraction flow using the IBM watsonx Orchestrate flow builder.

The tool uses layout-based extraction method to accurately extract both regular fields
and tabular data from structured documents like invoices.
"""

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import END, START, Flow, flow
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField,
    DocExtConfigTableField,
    DocumentProcessingCommonInput,
)


class Fields(BaseModel):
    """
    Configuration schema for document extraction fields.

    Defines the fields to be extracted from documents, including their names,
    types, and descriptions. Each field is configured with a DocExtConfigField
    or DocExtConfigTableField that specifies how the document extractor should
    identify and extract the information.

    Fields defined in this schema:
        buyer: The purchasing party
        seller: The selling party
        agreement_date: The date when the agreement was signed (date type)
        pincode: Postal code (number type)
        line_items: Table containing invoice line items with columns for item name,
                   quantity, unit price, and total amount
    """

    buyer: DocExtConfigField = Field(
        default=DocExtConfigField(name="Buyer", field_name="buyer")
    )
    seller: DocExtConfigField = Field(
        default=DocExtConfigField(name="Seller", field_name="seller")
    )
    agreement_date: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Agreement Date", field_name="agreement_date", type="date"
        ),
    )
    pincode: DocExtConfigField = Field(
        default=DocExtConfigField(name="pincode", field_name="pincode", type="number"),
    )

    # Example 1: Invoice Line Items Table
    line_items: DocExtConfigTableField = Field(
        default=DocExtConfigTableField(
            name="Invoice Line Items",
            field_name="line_items",
            description="The line items of the invoice.",
            fields=[
                DocExtConfigField(
                    name="Item Name",
                    field_name="item",
                    type="string",
                    description="Name of the item",
                    example_value="Product ABC",
                ),
                DocExtConfigField(
                    name="Quantity",
                    field_name="quantity",
                    type="number",
                    description="Quantity of items ordered",
                    example_value="10",
                ),
                DocExtConfigField(
                    name="Unit Price",
                    field_name="unit_price",
                    type="number",
                    description="Price per unit",
                    example_value="50.00",
                ),
                DocExtConfigField(
                    name="Amount",
                    field_name="amount",
                    type="number",
                    description="The total amount for the line item.",
                    example_value="500.00",
                ),
            ],
        ),
    )


@flow(
    name="structured_document_extractor_tool",
    display_name="structured_document_extractor_tool",
    description="Extraction of custom fields from a document with tables, specified by the user.",
    input_schema=DocumentProcessingCommonInput,
)
def build_docext_flow(aflow: Flow) -> Flow:
    """
    Build a document extraction flow for structured documents with tables.

    This function creates a flow that extracts custom fields (including tables) from
    documents using the document extractor node. It configures the extractor to use
    the layout-based extraction method, which is required for table extraction.

    Args:
        aflow: The Flow object to build upon

    Returns:
        Flow: The configured flow with document extraction capabilities

    Note:
        - aflow.docext returns two items:
          1. doc_ext_node: A node to be added into the flow
          2. ExtractedValues: The output schema that can be passed to other nodes
        - field_extraction_method must be set to "layout" to extract tables from
          structured documents
    """

    doc_ext_node, ExtractedValues = aflow.docext(
        name="structured_document_extractor",
        display_name="Extract fields from an invoice",
        description="Extracts fields from an input invoice file",
        llm="watsonx/meta-llama/llama-3-2-11b-vision-instruct",
        fields=Fields(),
        enable_hw=True,
        field_extraction_method="layout",
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
