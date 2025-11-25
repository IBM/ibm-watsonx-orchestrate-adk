from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, PlainTextReadingOrder


@flow(
    name="text_extraction_structure_flow_example",
    display_name="Text Extraction with Structure Example",
    description="Extracts text content and document structure from input documents using document processing. Supports PDF, DOCX, images, and other formats.",
    input_schema=DocProcInput
)
def build_docproc_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow that outputs both text and document structure.
    
    This flow creates a document processing pipeline that extracts raw text
    content along with the structural information (headings, paragraphs, tables,
    etc.) from input documents.
    
    Args:
        aflow (Flow, optional): Flow builder instance.
    
    Returns:
        Flow: Configured text extraction flow with structure output (START → docproc → END)
        
    Note:
        The document_structure parameter is set to True to include structural
        information in the output. This is useful for downstream processing
        that requires understanding of document layout.
    """
    assert aflow is not None, "Flow instance must be provided"
    
    # Create document processing node for text extraction with structure
    doc_proc_node = aflow.docproc(
        name="a_text_extraction_node",
        display_name="Text extraction node with document structure",
        description="Extracts the raw text from an input document and its structure",
        task="text_extraction",  # Specifies text extraction task
        document_structure=True,  # Output the document structure. This defaults to False.
    )

    # Connect nodes in sequence: START → docproc → END
    aflow.sequence(START, doc_proc_node, END)
    return aflow
