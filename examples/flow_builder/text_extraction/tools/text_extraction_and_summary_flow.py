from typing import Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocProcField,
    DocProcInput,
    DocProcKVPSchema,
    DocProcKey,
    DocProcOutputFormat,
    NodeErrorHandlerConfig,
    TextExtractionObjectResponse,
)


class TextSummaryType(BaseModel):
    summary: str = Field(description="Summary of the input text", default="")

class TestFlowResultType(TextExtractionObjectResponse):
    summary_text: str = Field(description="The summary of the text computed by the 'Text summary' node.", default="")

INVOICE_KVP_SCHEMA: DocProcKVPSchema = DocProcKVPSchema(
    document_type="MyInvoice",
    document_description="A simple invoice document",
    fields = {
        "invoice_number" : DocProcField(
            description="he unique identifier for the invoice.",
            default="",
            example="INV-0001",
        ),
        "total_amount" : DocProcField(
            description="The total amount due on the invoice.",
            default="",
            example="1000.00",
        ),
        "due_date" : DocProcField(
            description="The date on which the invoice is due.",
            default="",
            example="2023-01-01",
        )
    }
)

@flow(
    name="text_extraction_and_summary_flow_example",
    display_name="Text Extraction and Summary Flow",
    description="This flow consists of two nodes. The first node extracts the raw text out of a document's contents. The second node uses the raw text to generate a summary using the GenAI node.",
    input_schema=DocProcInput,
    output_schema=TestFlowResultType
)
def build_docproc_flow(flow: Flow) -> Flow:
    # Create the docproc node for text extraction
    doc_proc_node = flow.docproc(
        name="text_extraction_node",
        display_name="Generic text extraction node",
        description="Extract the raw text out of a document's contents.",
        task="text_extraction",
        #document_structure=True,
        output_format=DocProcOutputFormat.object,  # Return JSON object instead of document reference
        # Optional KVP (Key-Value Pair) extraction parameters:
        kvp_schemas=[ INVOICE_KVP_SCHEMA ],
        kvp_force_schema_name="MyInvoice",  # Force a specific schema to be used
    )

    # Explicitly map all flow inputs to the docproc node to prevent automap from
    # overriding input values with potentially incorrect automatic mappings.
    doc_proc_node.map_input(input_variable="document_ref", expression="flow.input.document_ref")
    doc_proc_node.map_input(input_variable="kvp_schemas", expression="flow.input.kvp_schemas")
    doc_proc_node.map_input(input_variable="kvp_model_name", expression="flow.input.kvp_model_name")
    doc_proc_node.map_input(input_variable="kvp_force_schema_name", expression="flow.input.kvp_force_schema_name")
    doc_proc_node.map_input(input_variable="kvp_enable_text_hints", expression="flow.input.kvp_enable_text_hints")

    # A Prompt node that will summarize the text extracted from the input invoice.
    my_summary_node = flow.prompt(
      name="my_summary_node",
      display_name="Text summary node",
      description="Text summary node",
      system_prompt=[
          "You are a knowledge source."
      ],
      user_prompt=[
          "Write a 2 sentence summary of: {text}"
      ],
      error_handler_config=NodeErrorHandlerConfig(
          error_message="An error has occurred while invoking the LLM",
          max_retries=1,
          retry_interval=1000
      ),
      input_schema=TextExtractionObjectResponse,
      output_schema=TextSummaryType,
    )

    # Map the text extracted from the input invoice to the user prompt of the Prompt node.
    my_summary_node.map_input(input_variable="text", expression="flow[\"Generic text extraction node\"].output.text")

    # START --> text extraction node --> prompt node --> END
    flow.sequence(START, doc_proc_node, my_summary_node, END)

    # Explicit output mapping is required when using DocProcOutputFormat.object.
    # Without explicit mapping, the automap feature would attempt to automatically map outputs,
    # which could inject large document structures into the LLM context and cause token overflow.
    # By explicitly mapping each output field, we maintain control over what data flows through.

    # summary_text is the output from the Prompt node.
    flow.map_output(output_variable="summary_text", expression="flow[\"Text summary node\"].output.summary")
    # The text is the original raw text extracted from the input invoice, produced by the text extraction node.
    flow.map_output(output_variable="text", expression="flow[\"Generic text extraction node\"].output.text")
    # The kvps are the extracted kvps produced by the text extraction node.
    flow.map_output(output_variable="metadata", expression="flow[\"Generic text extraction node\"].output.metadata")
    flow.map_output(output_variable="kvps", expression="flow[\"Generic text extraction node\"].output.kvps")

    # These are not produced by this example, but you need them if you set document_structure=True.
    flow.map_output(output_variable="styles", expression="flow[\"Text extraction node with document structure\"].output.styles")
    flow.map_output(output_variable="top_level_structures", expression="flow[\"Text extraction node with document structure\"].output.top_level_structures")
    flow.map_output(output_variable="all_structures", expression="flow[\"Text extraction node with document structure\"].output.all_structures")

    return flow
