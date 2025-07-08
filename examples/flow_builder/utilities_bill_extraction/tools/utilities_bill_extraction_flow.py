from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocumentContent

@flow(
    name ="utilities_extraction_flow_example",
    display_name="utilities_extraction_flow_example",
    description="This flow contains a single docproc node that extracts fields from an utility bill document",
    input_schema=DocumentContent
)
def build_docproc_flow(aflow: Flow = None) -> Flow:
    doc_proc_node = aflow.docproc(
        name="kvp_utility_bills_extraction",
        display_name="kvp_utility_bills_extraction",
        description="Extract key-value pairs from an utilities bill",
        task="kvp_utility_bills_extraction"
    )

    aflow.edge(START, doc_proc_node).edge(doc_proc_node,END)

    return aflow
