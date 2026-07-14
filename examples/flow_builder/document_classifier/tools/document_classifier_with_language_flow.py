from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocClassifierClass, DocumentProcessingCommonInput, LanguageCode
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
    name="document_classifier_with_language",
    display_name="Document Classifier with Language",
    description=(
        "Classifies documents into custom classes using a specified OCR language. "
        "Setting the language ensures the correct OCR engine is used for scanned PDFs "
        "and images, improving classification accuracy for non-Latin script documents."
    ),
    input_schema=DocumentProcessingCommonInput
)
def build_docclassifier_flow_with_language(aflow: Flow = None) -> Flow:
    """
    Build a document classifier flow with language-aware OCR support.

    This example demonstrates how to use the language parameter to select the
    correct OCR engine before classification. 

    Use the LanguageCode enum to specify the ISO-639 language code that matches
    the document's language.

    Args:
        aflow: The Flow object to build upon

    Returns:
        Flow: The configured flow with document classification capabilities
    """
    doc_classifier_node = aflow.docclassifier(
        name="document_classifier_language_node",
        display_name="Classify Document (French)",
        description=(
            "Classifies French-language scanned documents or images into custom classes. "
            "Uses the French OCR engine to correctly recognise Latin-script characters."
        ),
        llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        classes=CustomClasses(),
        language=LanguageCode.fr,
    )

    aflow.sequence(START, doc_classifier_node, END)
    return aflow
