"""Text Extraction with Page Range Example."""

import logging

from ibm_watsonx_orchestrate.flow_builder.flows import (
    END,
    START,
    Flow,
    flow,
)
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, PageRange

# Configure logging
logger = logging.getLogger(__name__)


@flow(
    name="text_extraction_page_range_flow",
    display_name="Text Extraction with Page Range",
    description=(
        "Extracts text from a specific page range of input documents. "
        "Useful for processing only relevant sections of large documents."
    ),
    input_schema=DocProcInput,
)
def build_docproc_page_range_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow that processes only a specific page range.

    This flow creates a document processing pipeline that extracts raw text
    content from a specified range of pages in the input document. This is
    particularly useful when:
    - Processing large documents where only certain pages are relevant
    - Extracting specific sections (e.g., pages 1-5 of a report)
    - Reducing processing time and costs by limiting the scope

    Args:
        aflow: Flow builder instance provided by the @flow decorator.

    Returns:
        Flow: Configured text extraction flow with page range filtering
            (START → docproc → END)
    """
    assert aflow is not None, "Flow instance must be provided"
    
    try:
        # Create document processing node configured for text extraction with page range
        # This will extract text only from pages 1 through 5 of the document
        # Note: page_range can be overridden at runtime when invoking the flow
        doc_proc_node = aflow.docproc(
            name="text_extraction_with_page_range_node",
            display_name="Extract Text from Pages 1-5",
            description="Extracts raw text from a specific page range of the input document",
            task="text_extraction",
            page_range=PageRange(start=1, end=5),  # Extract only pages 1-5 (can be overridden at runtime)
        )

        # Connect nodes in sequence: START → docproc → END
        aflow.sequence(START, doc_proc_node, END)
        
        logger.info("Text extraction with page range flow built successfully")
        return aflow
        
    except Exception as e:
        logger.error(f"Failed to build text extraction page range flow: {e}", exc_info=True)
        raise
