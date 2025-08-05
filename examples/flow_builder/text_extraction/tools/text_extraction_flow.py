from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput


@flow(
    name ="text_extraction_flow_example",
    display_name="text_extraction_flow_example",
    description="This flow consists of one node: a docproc node, which extracts text from the input document",
    input_schema=DocProcInput
)
def build_docproc_flow(aflow: Flow = None) -> Flow:
    doc_proc_node = aflow.docproc(
        name="text_extraction",
        display_name="text_extraction",
        description="Extract text out of a document's contents.",
        task="text_extraction"
    )

    aflow.sequence(START, doc_proc_node, END)
    return aflow
