from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField, DocumentProcessingCommonInput, LanguageCode
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
    name="document_extractor_with_language",
    display_name="Document Extractor with Language",
    description=(
        "Extracts custom fields from a document using a specified OCR language. "
        "Setting the language ensures the correct OCR engine is used for scanned PDFs "
        "and images, improving field extraction accuracy for non-Latin script documents."
    ),
    input_schema=DocumentProcessingCommonInput
)
def build_docext_flow_with_language(aflow: Flow = None) -> Flow:
    """
    Build a document extraction flow with language-aware OCR support.

    This example demonstrates how to use the language parameter to select the
    correct OCR engine before field extraction. For scanned PDFs and images the
    OCR engine must match the document's script — without it, non-Latin characters
    are not recognised and extracted field values will be incorrect or empty.
    Programmatic documents (PDF, .docx, .pptx) do not require this setting.

    Use the LanguageCode enum to specify the ISO-639 language code that matches
    the document's language.

    Args:
        aflow: The Flow object to build upon

    Returns:
        Flow: The configured flow with document extraction capabilities
    """

    doc_ext_node, _ExtractedValues = aflow.docext(
        name="contract_extractor_language",
        display_name="Extract fields (German)",
        description=(
            "Extracts fields from a German-language scanned contract document. "
            "Uses the German OCR engine to correctly recognise Latin-script characters."
        ),
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        field_extraction_method="layout",
        fields=Fields(),
        language=LanguageCode.de,
    )

    aflow.sequence(START, doc_ext_node, END)
    return aflow
