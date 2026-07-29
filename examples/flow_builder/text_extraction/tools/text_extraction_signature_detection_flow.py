"""Text Extraction with Signature Detection Example."""

import logging

from ibm_watsonx_orchestrate.flow_builder.flows import (
    END,
    START,
    Flow,
    flow,
)
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput

# Configure logging
logger = logging.getLogger(__name__)


@flow(
    name="text_extraction_signature_detection_flow",
    display_name="Text Extraction with Signature Detection",
    description=(
        "Extracts text from input documents and detects the presence of signatures. "
        "When enable_signature_detection is True, the output includes a signatures array "
        "with presence, location, page number, and confidence for each detected signature."
    ),
    input_schema=DocProcInput,
)
def build_docproc_signature_detection_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow that also performs signature detection.

    This flow creates a document processing pipeline that extracts raw text
    content from an input document and detects signatures within the document.
    Useful when:
    - Verifying whether a contract or form has been signed
    - Auditing documents for signature presence and location
    - Automating signature validation workflows

    Args:
        aflow: Flow builder instance provided by the @flow decorator.

    Returns:
        Flow: Configured text extraction flow with signature detection enabled
            (START → docproc → END)
    """
    assert aflow is not None, "Flow instance must be provided"

    try:
        # Create document processing node configured for text extraction
        # with signature detection enabled.
        # The output will include a signatures array alongside the extracted text.
        doc_proc_node = aflow.docproc(
            name="text_extraction_with_signature_detection_node",
            display_name="Extract Text and Detect Signatures",
            description="Extracts raw text from an input document and detects signatures",
            task="text_extraction",
            enable_signature_detection=True,
        )

        # Connect nodes in sequence: START → docproc → END
        aflow.sequence(START, doc_proc_node, END)

        logger.info("Text extraction with signature detection flow built successfully")
        return aflow

    except Exception as e:
        logger.error(f"Failed to build text extraction signature detection flow: {e}", exc_info=True)
        raise
