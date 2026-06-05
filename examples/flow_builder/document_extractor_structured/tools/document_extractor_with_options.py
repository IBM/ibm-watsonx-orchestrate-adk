from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigField, DocumentProcessingCommonInput


class Fields(BaseModel):
    """
    Document extraction schema using available_options to reduce hallucinations.
    
    The available_options field constrains LLM outputs to valid values when extracting
    data that's inferred from visual cues rather than explicit text (e.g., € → "EUR",
    stamps → "Paid"). Requires field_extraction_method="layout".
    """
    buyer: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Buyer",
            field_name="buyer",
            description="The purchasing party"
        )
    )
    
    seller: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Seller",
            field_name="seller",
            description="The selling party"
        )
    )
    
    currency: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Currency",
            field_name="currency",
            type="string",
            description="The currency used in the invoice. May appear as symbols (€, $, £, ¥) rather than spelled out",
            available_options=[
                "USD",
                "EUR",
                "GBP",
                "JPY",
                "CAD",
                "AUD",
                "CHF",
                "CNY"
            ]
        )
    )

@flow(
    name="structured_document_extractor_with_options_example",
    display_name="Document Extractor with Available Options",
    description="Extract structured data from invoices using available_options to reduce hallucinations for fields inferred from visual cues",
    input_schema=DocumentProcessingCommonInput
)
def build_docext_with_options_flow(aflow: Flow) -> Flow:
    """
    Document extraction flow using available_options to constrain LLM outputs and reduce
    hallucinations when extracting fields from visual cues.
    Requires field_extraction_method="layout".
    """
    doc_ext_node, _ExtractedValues = aflow.docext(
        name="invoice_extractor_with_options",
        display_name="Extract Invoice Fields with Options",
        description="Extracts invoice information with available_options to reduce hallucinations for inferred fields",
        llm="watsonx/meta-llama/llama-3-2-11b-vision-instruct",
        fields=Fields(),
        field_extraction_method="layout"  # Required for available_options
    )

    # Connect the nodes in sequence
    aflow.sequence(START, doc_ext_node, END)
    
    return aflow

# Made with Bob
