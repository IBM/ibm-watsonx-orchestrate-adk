from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocProcInput,
    DocProcOutputFormat,
    OutputContentType,
    TextExtractionObjectResponse,
)


@flow(
    name="text_extraction_output_content_types_flow_example",
    display_name="Text Extraction with Output Content Types Flow",
    description=(
        "This flow demonstrates the output_content_types parameter of the docproc node. "
        "It requests all three content types — plain text, markdown, and HTML — from the "
        "text extraction API. The response contains each requested format as a separate field."
    ),
    input_schema=DocProcInput,
    output_schema=TextExtractionObjectResponse,
)
def build_docproc_flow(aflow: Flow) -> Flow:
    """
    Build a text extraction flow that requests text, markdown, and HTML output.

    The output_content_types parameter controls which formats are returned by the
    text extraction API:
      - OutputContentType.text     → response.text     (plain text)
      - OutputContentType.markdown → response.markdown (markdown-formatted text)
      - OutputContentType.html     → response.html     (HTML-formatted text)

    Passing an empty list [] skips text extraction entirely, which is useful
    when only KVP extraction is needed (avoids unnecessary processing).

    When output_content_types is not set (None), the API defaults to ["text"]
    for backward compatibility.

    Args:
        aflow: Flow builder instance provided by the @flow decorator.

    Returns:
        Flow: Configured flow (START → docproc → END)
    """
    assert aflow is not None, "Flow instance must be provided by the @flow decorator"

    doc_proc_node = aflow.docproc(
        name="text_extraction_output_content_types_node",
        display_name="Text extraction with output content types node",
        description=(
            "Extracts text from a document in plain text, markdown, and HTML formats. "
            "Each requested format is returned as a separate field in the response."
        ),
        task="text_extraction",
        # Request specific content formats. Change this list to suit your needs, e.g.:
        #   [OutputContentType.text]                          — plain text only (default)
        #   [OutputContentType.markdown]                      — markdown only
        #   [OutputContentType.text, OutputContentType.html]  — text and HTML
        #   []                                                — skip text extraction (KVPs only)
        output_content_types=[
            OutputContentType.text,
            OutputContentType.markdown,
            OutputContentType.html,
        ],
        # Use output_format=object so the response fields (text, markdown, html)
        # are returned as an inline JSON object rather than a file reference.
        output_format=DocProcOutputFormat.object,
    )

    # Map the flow input document_ref directly to the node so the user-supplied
    # document reference is forwarded without automap interference.
    doc_proc_node.map_input(
        input_variable="document_ref",
        expression="flow.input.document_ref",
    )

    aflow.sequence(START, doc_proc_node, END)

    # Map each content-type field from the node output to the flow output.
    aflow.map_output(
        output_variable="text",
        expression='flow["Text extraction with output content types node"].output.text',
    )
    aflow.map_output(
        output_variable="markdown",
        expression='flow["Text extraction with output content types node"].output.markdown',
    )
    aflow.map_output(
        output_variable="html",
        expression='flow["Text extraction with output content types node"].output.html',
    )
    # kvps and metadata come from the inherited AssemblyJsonOutput base class,
    # not from output_content_types. They are populated when kvp_schemas or
    # document_structure are configured on the node spec respectively.
    aflow.map_output(
        output_variable="kvps",
        expression='flow["Text extraction with output content types node"].output.kvps',
    )
    aflow.map_output(
        output_variable="metadata",
        expression='flow["Text extraction with output content types node"].output.metadata',
    )

    return aflow
