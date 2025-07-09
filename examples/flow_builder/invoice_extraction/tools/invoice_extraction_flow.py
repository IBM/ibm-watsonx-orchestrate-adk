from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import DocumentContent

@flow(
    name ="invoice_extraction_flow_example",
    display_name="invoice_extraction_flow_example",
    description="This flow only contains a single docproc node",
    input_schema=DocumentContent
)
def build_docproc_flow(aflow: Flow = None) -> Flow:
    doc_proc_node = aflow.docproc(
        name="kvp_invoices_extraction",
        display_name="kvp_invoices_extraction",
        description="Extract key-value pairs from an invoice",
        task="kvp_invoices_extraction"
    )

    aflow.edge(START, doc_proc_node).edge(doc_proc_node,END)

    return aflow
