"""Text Extraction with Language Example."""

import logging

from ibm_watsonx_orchestrate.flow_builder.flows import (
    END,
    START,
    Flow,
    flow,
)
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, LanguageCode

# Configure logging
logger = logging.getLogger(__name__)


@flow(
    name="text_extraction_with_language_flow",
    display_name="Text Extraction with Language",
    description=(
        "Extracts text from documents using a specified OCR language. "
        "Setting the language improves OCR accuracy for scanned PDFs and images "
        "that contain non-Latin scripts such as Japanese, Korean, or Arabic."
    ),
    input_schema=DocProcInput,
)
def build_docproc_language_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow with language-aware OCR support.

    This example demonstrates how to use the language parameter to select the
    correct OCR engine for the document's script. 

    Use the LanguageCode enum to specify the ISO-639 language code that matches
    the document's language.

    Args:
        aflow: Flow builder instance provided by the @flow decorator.

    Returns:
        Flow: Configured text extraction flow with language setting
            (START → docproc → END)
    """
    doc_proc_node = aflow.docproc(
        name="text_extraction_language_node",
        display_name="Extract Text (Japanese)",
        description=(
            "Extracts text from a Japanese-language scanned document or image. "
            "Uses the Japanese OCR engine to correctly recognise non-Latin characters."
        ),
        task="text_extraction",
        language=LanguageCode.ja,
    )

    aflow.sequence(START, doc_proc_node, END)
    return aflow
