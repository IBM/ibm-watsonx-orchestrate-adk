"""Text Extraction with Signature Detection Example."""

from ibm_watsonx_orchestrate.flow_builder.flows import (
    END,
    START,
    Flow,
    flow,
)
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput


@flow(
    name="text_extraction_signature_detection_flow",
    display_name="Text Extraction with Signature Detection",
    description=(
        "Extracts text from input documents and detects the presence of signatures. "
        "When detect_signatures is True, the output includes a signatures array "
        "with presence, location, page number, and confidence for each detected signature."
    ),
    input_schema=DocProcInput,
)
def build_docproc_signature_detection_flow(aflow: Flow) -> Flow:
    """Build a text extraction flow that also performs signature detection."""
    doc_proc_node = aflow.docproc(
        name="text_extraction_with_signature_detection_node",
        display_name="Extract Text and Detect Signatures",
        description="Extracts raw text from an input document and detects signatures",
        task="text_extraction",
        document_structure=True,
        detect_signatures=True
    )

    aflow.sequence(START, doc_proc_node, END)

    return aflow
