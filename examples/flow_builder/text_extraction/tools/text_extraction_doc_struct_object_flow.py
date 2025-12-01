from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, DocProcOutputFormat, TextExtractionObjectResponse


@flow(
    name="text_extraction_object_output_flow_example",
    display_name="Text Extraction with Object Output Example",
    description="Extracts text content and document structure from input documents using document processing. The output will be an Object instead of a file URL. Supports PDF, DOCX, images, and other formats.",
    input_schema=DocProcInput,
    output_schema=TextExtractionObjectResponse,
)
def build_docproc_flow(flow: Flow) -> Flow:
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
    assert flow is not None, "Flow instance must be provided"
    
    # Create document processing node for text extraction with structure
    doc_proc_node = flow.docproc(
        name="a_text_extraction_node",
        display_name="Text extraction node with document structure",
        description="Extracts the raw text from an input document and its structure",
        task="text_extraction",  # Specifies text extraction task
        document_structure=True,  # Output the document structure. This defaults to False.

        output_format=DocProcOutputFormat.object,  # Output format is JSON object

    )

    # Explicitly map all flow inputs to the docproc node to prevent automap from
    # overriding input values with potentially incorrect automatic mappings.
    doc_proc_node.map_input(input_variable="document_ref", expression="flow.input.document_ref")
    doc_proc_node.map_input(input_variable="kvp_schemas", expression="flow.input.kvp_schemas")
    doc_proc_node.map_input(input_variable="kvp_model_name", expression="flow.input.kvp_model_name")
    doc_proc_node.map_input(input_variable="kvp_force_schema_name", expression="flow.input.kvp_force_schema_name")
    doc_proc_node.map_input(input_variable="kvp_enable_text_hints", expression="flow.input.kvp_enable_text_hints")

    # Connect nodes in sequence: START → docproc → END
    flow.sequence(START, doc_proc_node, END)

    # Explicit output mapping is required when using DocProcOutputFormat.object.
    # Without explicit mapping, the automap feature would attempt to automatically map outputs,
    # which could inject large document structures into the LLM context and cause token overflow.
    # By explicitly mapping each output field, we maintain control over what data flows through.
    flow.map_output(output_variable="text", expression="flow[\"Text extraction node with document structure\"].output.text")
    flow.map_output(output_variable="metadata", expression="flow[\"Text extraction node with document structure\"].output.metadata")
    flow.map_output(output_variable="kvps", expression="flow[\"Text extraction node with document structure\"].output.kvps")
    flow.map_output(output_variable="styles", expression="flow[\"Text extraction node with document structure\"].output.styles")
    flow.map_output(output_variable="top_level_structures", expression="flow[\"Text extraction node with document structure\"].output.top_level_structures")
    flow.map_output(output_variable="all_structures", expression="flow[\"Text extraction node with document structure\"].output.all_structures")

    return flow
