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

    Defines the fields to be extracted from a simple Excel file. It defines a single
    table to be extracted with the following rows: invoice number, invoice date,
    invoice total, taxes, and customer name.
    """
    line_items: DocExtConfigTableField = Field(
        default=DocExtConfigTableField(
            name="Invoice Line Items",
            field_name="line_items",
            description="The line items of the invoice.",
            fields=[
                DocExtConfigField(
                    name="Invoice number",
                    field_name="invoice_number",
                    type="string",
                    description="The number of the invoice",
                    example_value="123456",
                ),
                DocExtConfigField(
                    name="Invoice date",
                    field_name="invoice_date",
                    type="date",
                    description="The date of the invoice",
                    example_value="2026-05-05",
                ),
                DocExtConfigField(
                    name="Invoice total",
                    field_name="invoice_total",
                    type="string",
                    description="The total price of the invoice",
                    example_value="$556.44",
                ),
                DocExtConfigField(
                    name="Taxes",
                    field_name="taxes",
                    type="string",
                    description="The taxes of the invoice",
                    example_value="$60.33",
                ),
                DocExtConfigField(
                    name="Customer name",
                    field_name="customer_name",
                    type="string",
                    description="The name of the customer on the invoice",
                    example_value="XYZ, Inc.",
                ),
            ],
        ),
    )

@flow(
    name="structured_document_extractor_tool_simple_excel",
    display_name="structured_document_extractor_tool_simple_excel",
    description="Extraction of custom fields from a simple excel file.",
    input_schema=DocumentProcessingCommonInput,
)
def build_docext_flow(aflow: Flow) -> Flow:
    """
    Build a document extraction flow for excel files with a simple table.
    """
    doc_ext_node, _ExtractedValues = aflow.docext(
        name="structured_document_extractor_simple_excel",
        display_name="Extract fields from an excel file",
        description="Extracts fields from an excel file",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=Fields(),
        field_extraction_method="layout",
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
