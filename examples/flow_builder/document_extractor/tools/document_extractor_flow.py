from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigField, DocumentProcessingCommonInput


class Fields(BaseModel):
    buyer: DocExtConfigField = Field(name="Buyer", default=DocExtConfigField(name="Buyer", field_name="buyer"))
    seller: DocExtConfigField = Field(name="Seller", default=DocExtConfigField(name="Seller", field_name="seller"))
    agreement_date: DocExtConfigField = Field(name="Agreement date", default=DocExtConfigField(name="Agreement Date", field_name="agreement_date", type="date"))


@flow(
    name ="custom_flow_docext_example",
    display_name="custom_flow_docext_example",
    description="Extraction of custom fields from a document, specified by the user.",
    input_schema=DocumentProcessingCommonInput
)
def build_docext_flow(aflow: Flow = None) -> Flow:
    # aflow.docext return 2 things
    # doc_ext_node which is a node to be added into aflow
    # ExtractedValues is the ouput schema of aflow.docext and it can be pass to other nodes as input schema

    doc_ext_node, ExtractedValues = aflow.docext(
        name="contract_extractor",
        display_name="Extract fields from a contract",
        description="Extracts fields from an input contract file",
        llm="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        fields=Fields(),
        enable_hw=True
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
