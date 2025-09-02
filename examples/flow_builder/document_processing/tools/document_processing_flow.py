from pydantic import BaseModel, Field
from .get_kvp_schemas_for_invoice import get_kvp_schemas_for_invoice
from .get_kvp_schemas_for_utility_bill import get_kvp_schemas_for_utility_bill
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END, Branch
)
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocExtConfigField, DocumentProcessingCommonInput

class CustomClasses(BaseModel):
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="invoice"))
    bill_of_lading: DocClassifierClass = Field(default=DocClassifierClass(class_name="bill_of_lading"))
    contract: DocClassifierClass = Field(default=DocClassifierClass(class_name="contract"))
    purchase_order: DocClassifierClass = Field(default=DocClassifierClass(class_name="purchase_order"))
    utility_bill: DocClassifierClass = Field(default=DocClassifierClass(class_name="utility_bill"))
    tax_form: DocClassifierClass = Field(default=DocClassifierClass(class_name="tax_form"))


class Fields(BaseModel):
    buyer: DocExtConfigField = Field(name="Buyer", default=DocExtConfigField(name="Buyer", field_name="buyer"))
    seller: DocExtConfigField = Field(name="Seller", default=DocExtConfigField(name="Seller", field_name="seller"))
    agreement_date: DocExtConfigField = Field(name="Agreement date", default=DocExtConfigField(name="Agreement Date", field_name="agreement_date", type="date"))

def build_docclassifier_node(aflow: Flow = None) -> Flow:
    doc_classifier_node = aflow.docclassifier(
        name="document_classifier_node",
        display_name="document_classifier_node",
        description="Classifies documents into a custom class.",
        llm="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        classes=CustomClasses(),
    )
    return doc_classifier_node

def build_docext_node(aflow: Flow= None) -> Flow:
    doc_ext_node, ExtractedValues = aflow.docext(
        name="doc_ext_node",
        display_name="doc_ext_node",
        description="Extracts custom field values (key-value-pairs) from a document using different extraction schemas.",
        llm="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        fields=Fields(),
        enable_hw=True
    )
    return doc_ext_node, ExtractedValues

def build_docproc_node_for_invoice(aflow: Flow= None) -> Flow:
    doc_proc_node = aflow.docproc(
        name="text_extraction_with_document_structure_for_invoice",
        display_name="text_extraction_node",
        description="Extracts the raw text and semantic structure from a document.",
        task="text_extraction",
        document_structure=True,
        input_map="kvp_schemas=flow.get_kvp_schemas_for_invoice.output",
        enable_hw=True
    )
    return doc_proc_node

def build_docproc_node_for_utility_bill(aflow: Flow= None) -> Flow:
    doc_proc_node = aflow.docproc(
        name="text_extraction_with_document_structure_for_utility_bill",
        display_name="text_extraction_node",
        description="Extracts the raw text and semantic structure from a document.",
        task="text_extraction",
        document_structure=True,
        input_map="kvp_schemas=flow.get_kvp_schemas_for_utility_bill.output",
        enable_hw=True
    )
    return doc_proc_node


@flow(
    name ="document_processing_flow",
    display_name="document_processing_flow",
    description="Process documents",
    input_schema=DocumentProcessingCommonInput
)
def build_document_processing_flow(aflow: Flow = None) -> Flow:
    # How this flow works:
    # The flow will execute the doc_classifier_node and return class_name(invoce, utitlity_bill, contract, etc....)
    # Based on the result of doc_classifier_node execution, 
    #           if class_name in ['invoice','bill_of_lading'], the flow will invoke get_kvp_schemas_for_invoice_tool_node to get kvp_shemas output and map the output into doc_proc_for_invoice_node, then invoke doc_proc_for_invoice_node
    #           if class_name in ['utility_bill'], the flow will invoke doc_proc_for_utility_bill_node to get kvp_shemas output and map the output into doc_proc_for_utility_bill_node, then invoke doc_proc_for_utility_bill_node
    #           if class_name in ['contract','purchase_order'], the flow will execute doc_ext_node
    #           Otherwise, the flow will execute doc_ext_node by default

    get_kvp_schemas_for_invoice_tool_node = aflow.tool(get_kvp_schemas_for_invoice,output_schema=list)
    get_kvp_schemas_for_utility_bill_tool_node = aflow.tool(get_kvp_schemas_for_utility_bill, output_schema=list)

    doc_ext_node, _ = build_docext_node(aflow)
    doc_classifier_node = build_docclassifier_node(aflow)
    doc_proc_for_invoice_node = build_docproc_node_for_invoice(aflow)
    doc_proc_for_utility_bill_node = build_docproc_node_for_utility_bill(aflow)

    document_kind_branch: Branch = aflow.conditions()
    document_kind_branch.condition(expression="flow.document_classifier_node.output.class_name.strip().lower() in ['invoice','bill_of_lading']", to_node=get_kvp_schemas_for_invoice_tool_node)\
        .condition(expression="flow.document_classifier_node.output.class_name.strip().lower() in ['utility_bill']", to_node=get_kvp_schemas_for_utility_bill_tool_node)\
        .condition(expression="flow.document_classifier_node.output.class_name.strip().lower() in ['contract','purchase_order']", to_node=doc_ext_node)\
        .condition(to_node=doc_ext_node, default=True)
    
    aflow.sequence(START, doc_classifier_node,document_kind_branch)

    aflow.edge(get_kvp_schemas_for_invoice_tool_node, doc_proc_for_invoice_node)
    aflow.edge(get_kvp_schemas_for_utility_bill_tool_node, doc_proc_for_utility_bill_node)
    aflow.edge(doc_proc_for_utility_bill_node, END)
    aflow.edge(doc_proc_for_invoice_node, END)
    aflow.edge(doc_ext_node, END)

    return aflow
