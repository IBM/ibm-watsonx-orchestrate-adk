from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
import os
import json

class TestDocProcNodes():
    
    def setup_method(self):
        self.parent_dir_path = os.path.dirname(os.path.realpath(__file__))

    def teardown_method(self):
        pass

    def test_text_extraction_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="text_extraction_flow_test")
        text_extraction_node = aflow.docproc(
            name="text_extraction",
            display_name="text_extraction",
            description="Extract text out of a document's contents.",
            task="text_extraction"
        )
        expected_text_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/text_extraction_spec.json").read())
        actual_text_extraction_spec = text_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_text_extraction_spec["task"] == "text_extraction"
        assert actual_text_extraction_spec["kind"] == "docproc"
        assert actual_text_extraction_spec["name"] == "text_extraction"
        assert actual_text_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert actual_text_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["TextExtractionResponse"]["title"] 
        
        assert aflow_json_spec["spec"]["kind"] == expected_text_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_text_extraction_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["title"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["properties"]["document_ref"]["format"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["properties"]["document_ref"]["format"]
        assert aflow_json_spec["schemas"]["TextExtractionResponse"]["required"] == expected_text_extraction_spec["schemas"]["TextExtractionResponse"]["required"]
        

    def test_invoice_extraction_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="invoice_extraction_flow_test")
        invoice_extraction_node = aflow.docproc(
            name="kvp_invoices_extraction_test",
            display_name="kvp_invoices_extraction_test",
            description="Extract key-value pairs from an invoice",
            task="kvp_invoices_extraction"
        )
        expected_invoice_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/invoice_extraction_spec.json").read())
        actual_invoice_extraction_spec = invoice_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_invoice_extraction_spec["task"] == "kvp_invoices_extraction"
        assert actual_invoice_extraction_spec["kind"] == "docproc"
        assert actual_invoice_extraction_spec["name"] == "kvp_invoices_extraction_test"
        assert actual_invoice_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_invoice_extraction_spec["schemas"]["kvp_invoices_extraction_test_input"]["title"]
        assert actual_invoice_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_invoice_extraction_spec["schemas"]["KVPInvoicesExtractionResponse"]["title"] 
        
        assert aflow_json_spec["spec"]["kind"] == expected_invoice_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_invoice_extraction_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["kvp_invoices_extraction_test_input"]["title"] == expected_invoice_extraction_spec["schemas"]["kvp_invoices_extraction_test_input"]["title"]
        assert aflow_json_spec["schemas"]["kvp_invoices_extraction_test_input"]["properties"]["document_ref"]["format"] == expected_invoice_extraction_spec["schemas"]["kvp_invoices_extraction_test_input"]["properties"]["document_ref"]["format"]
        assert aflow_json_spec["schemas"]["KVPInvoicesExtractionResponse"]["required"] == expected_invoice_extraction_spec["schemas"]["KVPInvoicesExtractionResponse"]["required"]
        for field_name, field_detail in aflow_json_spec["schemas"]["Invoice"]["properties"].items():
            field_detail["title"] == expected_invoice_extraction_spec["schemas"]["Invoice"]["properties"][field_name]["title"]


    def test_utilities_extraction_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="utilities_extraction_flow_test")
        utilities_extraction_node = aflow.docproc(
            name="utilities_extraction_test",
            display_name="utilities_extraction_test",
            description="Extract text out of a document's contents.",
            task="kvp_utility_bills_extraction"
        )
        expected_utilities_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/utilities_extraction_spec.json").read())
        actual_utilities_extraction_spec = utilities_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_utilities_extraction_spec["task"] == "kvp_utility_bills_extraction"
        assert actual_utilities_extraction_spec["kind"] == "docproc"
        assert actual_utilities_extraction_spec["name"] == "utilities_extraction_test"
        assert actual_utilities_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_utilities_extraction_spec["schemas"]["utilities_extraction_test_input"]["title"]
        assert actual_utilities_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_utilities_extraction_spec["schemas"]["KVPUtilityBillsExtractionResponse"]["title"] 
        
        assert aflow_json_spec["spec"]["kind"] == expected_utilities_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_utilities_extraction_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["utilities_extraction_test_input"]["title"] == expected_utilities_extraction_spec["schemas"]["utilities_extraction_test_input"]["title"]
        assert aflow_json_spec["schemas"]["utilities_extraction_test_input"]["properties"]["document_ref"]["format"] == expected_utilities_extraction_spec["schemas"]["utilities_extraction_test_input"]["properties"]["document_ref"]["format"]
        assert aflow_json_spec["schemas"]["KVPUtilityBillsExtractionResponse"]["required"] == expected_utilities_extraction_spec["schemas"]["KVPUtilityBillsExtractionResponse"]["required"]
        for field_name, field_detail in aflow_json_spec["schemas"]["UtilityBill"]["properties"].items():
            field_detail["title"] == expected_utilities_extraction_spec["schemas"]["UtilityBill"]["properties"][field_name]["title"]
