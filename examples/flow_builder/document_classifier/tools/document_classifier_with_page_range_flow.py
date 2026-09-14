from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocClassifierClass, DocumentProcessingCommonInput, PageRange
)


class CustomClasses(BaseModel):
    """
    Configuration schema for document classification classes.

    Defines the document types/classes that the classifier can identify.
    Each class is configured with a DocClassifierClass that specifies the
    class name used for categorizing input documents.
    """
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="Invoice"))
    contract: DocClassifierClass = Field(default=DocClassifierClass(class_name="Contract"))
    tax_form: DocClassifierClass = Field(default=DocClassifierClass(class_name="TaxForm"))
    bill_of_lading: DocClassifierClass = Field(default=DocClassifierClass(class_name="BillOfLading"))


@flow(
    name="document_classifier_with_page_range",
    display_name="Document Classifier with Page Range",
    description=(
        "Classifies documents into custom classes using only a specific page range. "
        "Limiting classification to a subset of pages is useful for multi-page documents "
        "where the relevant identifying content appears on known pages (e.g. a cover page)."
    ),
    input_schema=DocumentProcessingCommonInput
)
def build_docclassifier_flow_with_page_range(aflow: Flow = None) -> Flow:
    """
    Build a document classifier flow that classifies based on a page range.

    This example demonstrates how to use the page_range parameter to restrict
    classification to a specific set of pages within a document. This is useful
    when:
    - Documents have a predictable structure and the identifying content is
      always on certain pages (e.g. the first two pages).
    - You want to reduce the amount of text sent to the LLM for classification.

    Use PageRange(start=<n>, end=<m>) to specify the 1-based inclusive range
    of pages to use for classification.

    Args:
        aflow: The Flow object to build upon

    Returns:
        Flow: The configured flow with page-range-scoped document classification
    """
    doc_classifier_node = aflow.docclassifier(
        name="document_classifier_page_range_node",
        display_name="Classify Document (Pages 1-2)",
        description=(
            "Classifies documents into custom classes by inspecting only pages 1 and 2. "
            "Suitable for multi-page documents whose document type is identifiable from "
            "the cover or summary page."
        ),
        llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        classes=CustomClasses(),
        page_range=PageRange(start=1, end=2),  # Classify based on pages 1-2 only
    )

    aflow.sequence(START, doc_classifier_node, END)
    return aflow
