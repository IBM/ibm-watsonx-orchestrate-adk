from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, PlainTextReadingOrder


@flow(
    name ="text_extraction_simple_flow_example",
    display_name="Simple Text Extraction Flow",
    description="This flow consists of one node: a docproc node, which extracts text from the input document",
    input_schema=DocProcInput
)
def build_docproc_flow(aflow: Flow) -> Flow:
    """
    Build a simple text extraction flow.
    
    This flow creates a minimal document processing pipeline that extracts raw text
    content from input documents. It supports various document formats including PDF,
    DOCX, images (PNG, JPG), and other common file types.
    
    Args:
        aflow (Optional[Flow]): Flow builder instance provided by the @flow decorator.
            While typed as optional for flexibility, this parameter is always provided
            at runtime by the framework.
    
    Returns:
        Flow: Configured text extraction flow with a single docproc node
            (START → docproc → END)
    """
    # Ensure Flow instance is provided (guaranteed by @flow decorator at runtime)
    assert aflow is not None, "Flow instance must be provided by the @flow decorator"
    
    # Create document processing node configured for text extraction
    doc_proc_node = aflow.docproc(
        name="simplest_text_extraction_node",
        display_name="Simplest text extraction node",
        description="Extracts the raw text from an input document",
        task="text_extraction",  # Specifies text extraction task
    )

    # Connect nodes in sequence
    aflow.sequence(START, doc_proc_node, END)
    return aflow
