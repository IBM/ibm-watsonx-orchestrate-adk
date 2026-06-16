from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField, DocumentProcessingCommonInput, PageRange
)


class Fields(BaseModel):
    """
    Configuration schema for document extraction fields.
    
    Defines the fields to be extracted from contract documents, including
    their names, types, and descriptions. Each field is configured with
    a DocExtConfigField that specifies how the document extractor should
    identify and extract the information.
    """
    buyer: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Buyer",
            field_name="buyer"
        )
    )
    
    seller: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Seller",
            field_name="seller"
        )
    )
    
    agreement_date: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Agreement Date",
            field_name="agreement_date",
            type="date"
        )
    )
    
    agreement_number: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Agreement Number",
            field_name="agreement_number",
            description="The identifier of this contract."
        )
    )
    
    contract_type: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Contract Type",
            field_name="contract_type",
            type="string",
            description="The type of contract between the buyer and the seller."
        )
    )


@flow(
    name="document_extractor_with_page_range",
    display_name="Document Extractor with Page Range",
    description="Extraction of custom fields from specific pages of a document.",
    input_schema=DocumentProcessingCommonInput
)
def build_docext_flow_with_page_range(aflow: Flow = None) -> Flow:
    """
    Build a document extraction flow with page range support.
    
    This example demonstrates how to use the page_range parameter to extract
    fields only from specific pages of a document. This is useful when:
    - You have multi-page documents but only need data from certain pages
    - You want to reduce processing time by limiting extraction scope
    
    Args:
        aflow: The Flow object to build upon
    
    Returns:
        Flow: The configured flow with document extraction capabilities
    """

    doc_ext_node, _ExtractedValues = aflow.docext(
        name="contract_extractor_page_range",
        display_name="Extract fields from specified pages",
        description="Extracts fields from pages 1-3 of an input contract file",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=Fields(),
        field_extraction_method="layout",  # Required for page_range support
        page_range=PageRange(start=1, end=3)  # Only extract from pages 1-3
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
