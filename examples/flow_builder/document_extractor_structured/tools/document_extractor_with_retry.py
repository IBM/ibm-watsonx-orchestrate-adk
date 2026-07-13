from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import END, START, Flow, flow
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField,
    DocExtConfigTableField,
    DocumentProcessingCommonInput,
    NodeErrorHandlerConfig,
)


class Fields(BaseModel):
    """
    Configuration schema for invoice document extraction fields.

    Defines the top-level fields and tables to be extracted from invoice documents.

    Fields defined in this schema:
        invoice_number: The unique identifier for the invoice
        invoice_date: The date the invoice was issued (date type)
        line_items: Table containing invoice line items with columns for item ID,
                    quantity, description, unit price, and total
    """
    invoice_number: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Invoice Number",
            field_name="invoice_number",
            description="The unique identifier for the invoice.",
        )
    )
    invoice_date: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Invoice Date",
            field_name="invoice_date",
            type="date",
            description="The date the invoice was issued.",
        )
    )
    line_items: DocExtConfigTableField = Field(
        default=DocExtConfigTableField(
            name="Line Items",
            field_name="line_items",
            description="The line items of the invoice.",
            fields=[
                DocExtConfigField(
                    name="Item ID",
                    field_name="item_id",
                    type="string",
                    description="The unique identifier for the line item.",
                ),
                DocExtConfigField(
                    name="Qty",
                    field_name="qty",
                    type="number",
                    description="Quantity of units ordered.",
                ),
                DocExtConfigField(
                    name="Description",
                    field_name="description",
                    type="string",
                    description="A description of the product or service.",
                ),
                DocExtConfigField(
                    name="Unit Price",
                    field_name="unit_price",
                    type="number",
                    description="Price per single unit.",
                ),
                DocExtConfigField(
                    name="Total",
                    field_name="total",
                    type="number",
                    description="Total cost for this line item.",
                ),
            ],
        )
    )


@flow(
    name="document_extractor_with_retry_tool",
    display_name="document_extractor_with_retry_tool",
    description="Extraction of invoice fields and line items from a document, with automatic retry on failures.",
    input_schema=DocumentProcessingCommonInput,
)
def build_docext_flow(aflow: Flow) -> Flow:
    """
    Build a document extraction flow for invoices with retry support.

    This function creates a flow that extracts top-level invoice fields and a
    line-items table from documents using the document extractor node. The node
    is configured with retry logic so that failures (e.g. service timeouts) are
    retried automatically before the error is surfaced.
    """
    doc_ext_node, ExtractedValues = aflow.docext(
        name="invoice_document_extractor",
        display_name="Extract fields from an invoice",
        description="Extracts invoice number, invoice date, and line items from an invoice file",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=Fields(),
        enable_hw=True,
        field_extraction_method="layout",
        error_handler_config=NodeErrorHandlerConfig(
            error_message="An error has occurred while extracting fields from the document",
            max_retries=3,
            retry_interval=2000,
        ),
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
