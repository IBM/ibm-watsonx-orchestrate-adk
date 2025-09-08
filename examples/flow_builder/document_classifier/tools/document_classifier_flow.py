from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocumentProcessingCommonInput, DocumentClassificationResponse


class CustomClasses(BaseModel):
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="Invoice"))


@flow(
    name ="custom_flow_docclassifier_example",
    display_name="custom_flow_docclassifier_example",
    description="Classifies documents into custom classes.",
    input_schema=DocumentProcessingCommonInput
)
def build_docclassifier_flow(aflow: Flow = None) -> Flow:
    # aflow.docclassifier return a DocClassifierNode object
    # DocumentClassificationResponse is the output schema of DocClassifierNode and it can be used as input schema for the next node

    doc_classifier_node = aflow.docclassifier(
        name="document_classifier_node",
        display_name="document_classifier_node",
        description="Classifies documents into one custom class.",
        llm="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        classes=CustomClasses(),
    )

    aflow.sequence(START, doc_classifier_node, END)
    return aflow
