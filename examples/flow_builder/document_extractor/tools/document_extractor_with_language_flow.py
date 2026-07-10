"""Document Extractor with Language Example."""

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import END, START, Flow, flow
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField,
    DocumentProcessingCommonInput,
    LanguageCode,
)


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
        default=DocExtConfigField(
            name="Buyer",
            field_name="buyer",
        )
    )

    seller: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Seller",
            field_name="seller",
        )
    )

    agreement_date: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Agreement Date",
            field_name="agreement_date",
            type="date",
        )
    )

    agreement_number: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Agreement Number",
            field_name="agreement_number",
            description="The identifier of this contract.",
        )
    )

    contract_type: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Contract Type",
            field_name="contract_type",
            type="string",
            description="The type of contract between the buyer and the seller.",
        )
    )


@flow(
    name="document_extractor_with_language",
    display_name="Document Extractor with Language",
    description=(
        "Extracts custom fields from a document using a specified OCR language. "
        "Setting the language ensures the correct OCR engine is used for scanned PDFs "
        "and images, improving field extraction accuracy for non-Latin script documents."
    ),
    input_schema=DocumentProcessingCommonInput,
)
def build_docext_language_flow(aflow: Flow) -> Flow:
    """
    Build a document extraction flow with language-aware OCR support.

    This example demonstrates how to use the language parameter to select the
    correct OCR engine before field extraction.

    Use the LanguageCode enum to specify the ISO-639 language code that matches
    the document's language.

    Args:
        aflow: Flow builder instance provided by the @flow decorator.

    Returns:
        Flow: Configured document extraction flow with language setting
            (START → docext → END)
    """
    doc_ext_node, _ExtractedValues = aflow.docext(
        name="contract_extractor_language",
        display_name="Extract Fields (Japanese)",
        description=(
            "Extracts fields from a Japanese-language scanned contract document. "
            "Uses the Japanese OCR engine to correctly recognise non-Latin characters."
        ),
        llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        fields=Fields(),
        language=LanguageCode.ja,
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
