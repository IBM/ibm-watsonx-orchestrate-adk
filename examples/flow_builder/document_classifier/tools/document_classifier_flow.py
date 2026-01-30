from pydoc import Doc
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocumentProcessingCommonInput, DocumentClassificationResponse


class CustomClasses(BaseModel):
    """
    Configuration schema for document classification classes.
    
    Defines the document types/classes that the classifier can identify.
    Each class is configured with a DocClassifierClass that specifies the
    class name used for categorizing input documents. The classifier uses
    an LLM to analyze documents and assign them to one of these classes.
    
    Example custom classes:
        invoice: Configuration for identifying invoice documents
        contract: Configuration for identifying contract documents
        tax_form: Configuration for identifying tax form documents
        bill_of_lading: Configuration for identifying bill of lading documents
    """
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="Invoice"))
    contract: DocClassifierClass = Field(default=DocClassifierClass(class_name="Contract"))
    tax_form: DocClassifierClass = Field(default=DocClassifierClass(class_name="TaxForm"))
    bill_of_lading: DocClassifierClass = Field(default=DocClassifierClass(class_name="BillOfLading"))


@flow(
    name ="custom_flow_docclassifier_example",
    display_name="custom_flow_docclassifier_example",
    description="Classifies documents into custom classes.",
    input_schema=DocumentProcessingCommonInput
)
def build_docclassifier_flow(aflow: Flow = None) -> Flow:
    # aflow.docclassifier returns a DocClassifierNode object.
    # The output schema of a DocClassifierNode is a DocumentClassifierResponse object.

    doc_classifier_node = aflow.docclassifier(
        name="document_classifier_node",
        display_name="document_classifier_node",
        description="Classifies documents into one custom class.",
        llm="watsonx/meta-llama/llama-3-2-11b-vision-instruct",
        classes=CustomClasses(),
    )

    aflow.sequence(START, doc_classifier_node, END)

    return aflow
