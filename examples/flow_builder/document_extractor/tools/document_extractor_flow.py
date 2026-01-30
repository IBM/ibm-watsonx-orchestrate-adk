from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigField, DocumentProcessingCommonInput


class Fields(BaseModel):
    """
    Configuration schema for document extraction fields.
    
    Defines the fields to be extracted from contract documents, including
    their names, types, and descriptions. Each field is configured with
    a DocExtConfigField that specifies how the document extractor should
    identify and extract the information.
    
    In this example, we define a number of custom fields for a Contract or 
    Agreement document:
        buyer: The purchasing party in the contract
        seller: The selling party in the contract
        agreement_date: The date when the agreement was signed (date type)
        agreement_number: Unique identifier for the contract
        contract_type: Classification of the contract 
    """
    buyer: DocExtConfigField = Field(
        name="Buyer",
        default=DocExtConfigField(
            name="Buyer",
            field_name="buyer"
        )
    )
    
    seller: DocExtConfigField = Field(
        name="Seller",
        default=DocExtConfigField(
            name="Seller",
            field_name="seller"
        )
    )
    
    agreement_date: DocExtConfigField = Field(
        name="Agreement date",
        default=DocExtConfigField(
            name="Agreement Date",
            field_name="agreement_date",
            type="date"
        )
    )
    
    agreement_number: DocExtConfigField = Field(
        name="Agreement number",
        default=DocExtConfigField(
            name="Agreement Number",
            field_name="agreement_number",
            description="The identifier of this contract."
        )
    )
    
    contract_type: DocExtConfigField = Field(
        name="Contract type",
        default=DocExtConfigField(
            name="Contract Type",
            field_name="contract_type",
            type="string",
            description="The type of contract between the buyer and the seller."
        )
    )


@flow(
    name ="custom_flow_docext_example",
    display_name="custom_flow_docext_example",
    description="Extraction of custom fields from a document, specified by the user.",
    input_schema=DocumentProcessingCommonInput
)
def build_docext_flow(aflow: Flow = None) -> Flow:
    # aflow.docext returns 2 objects: the document extractor node and the schema of the extracted values.
    # In this example, doc_ext_node is the node and is added to the flow.
    # _ExtractedValues is the output schema of doc_ext_node and can be used as the input schema of nodes downstream in the flow.

    doc_ext_node, _ExtractedValues = aflow.docext(
        name="contract_extractor",
        display_name="Extract fields from a contract",
        description="Extracts fields from an input contract file",
        llm="watsonx/meta-llama/llama-3-2-11b-vision-instruct",
        fields=Fields()
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
