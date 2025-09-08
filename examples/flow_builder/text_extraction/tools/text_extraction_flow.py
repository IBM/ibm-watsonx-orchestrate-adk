from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, PlainTextReadingOrder


@flow(
    name ="text_extraction_flow_example",
    display_name="text_extraction_flow_example",
    description="This flow consists of one node: a docproc node, which extracts text from the input document",
    input_schema=DocProcInput
)
def build_docproc_flow(aflow: Flow = None) -> Flow:
    # introduce new params for docproc node

    # plain_text_reading_order(type PlainTextReadingOrder): (PlainTextReadingOrder.block_structure, PlainTextReadingOrder.simple_line): 
    #       Optional parameter. Controls the reading order of the extracted text. 
    #       Defaults to PlainTextReadingOrder.block_structure. If set to PlainTextReadingOrder.simple_line, the extracted text will follow a strict left-to-right/top-to-bottom reading order. 
    #       The default, PlainTextReadingOrder.block_structure, identifies groups of text on the page (e.g., multiple columns) and follows the left-to-right reading order within those groups. 

    # document_structure(type boolean): If `document_structure` is set to `true`, the output will contain the additional fields returned by WDU as part of its document "assembly".
    doc_proc_node = aflow.docproc(
        name="text_extraction_with_document_structure",
        display_name="text_extraction_node",
        description="Extract text out of a document's contents.",
        task="text_extraction",
        document_structure=True,
        enable_hw=True
    )

    aflow.sequence(START, doc_proc_node, END)
    return aflow
