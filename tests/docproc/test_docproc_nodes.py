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
        
