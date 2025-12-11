from re import A
from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
import os
import json

from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, DocProcKVPSchema, DocProcOutputFormat, TextExtractionObjectResponse

class TestDocProcNode():
    
    def setup_method(self):
        self.parent_dir_path = os.path.dirname(os.path.realpath(__file__))

    def teardown_method(self):
        pass

    def test_text_extraction_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="text_extraction_flow_example")
        text_extraction_node = aflow.docproc(
            name="text_extraction",
            display_name="text_extraction",
            description="Extract text out of a document's contents.",
            task="text_extraction",
            kvp_model_name="mistralai/pixtral-12b"
        )
        expected_text_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/docproc_spec.json").read())
        actual_text_extraction_spec = text_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()
        #print(json.dumps(aflow_json_spec, indent=2))

        assert actual_text_extraction_spec["task"] == "text_extraction"
        assert actual_text_extraction_spec["kind"] == "docproc"
        assert actual_text_extraction_spec["name"] == "text_extraction"
        assert actual_text_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert "TextExtractionResponse" in actual_text_extraction_spec["output_schema"]["$ref"]
        assert actual_text_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["TextExtractionResponse"]["title"] 
        assert actual_text_extraction_spec.get("output_format") is None

        assert aflow_json_spec["spec"]["kind"] == expected_text_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_text_extraction_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["title"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["properties"]["kvp_model_name"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["properties"]["kvp_model_name"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["properties"]["document_ref"]["format"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["properties"]["document_ref"]["format"]
        assert aflow_json_spec["schemas"]["TextExtractionResponse"] is not None
        assert aflow_json_spec["schemas"].get("TextExtractionObjectResponse") is None

        
    def test_text_extraction_node_with_output_format(self):
        aflow = FlowFactory.create_flow(
          name="text_extraction_flow_example",
          input_schema=DocProcInput,
        )

        text_extraction_node = aflow.docproc(
            name="text_extraction",
            display_name="text_extraction",
            description="Extract text out of a document's contents.",
            task="text_extraction",
            output_format=DocProcOutputFormat.object,
        )
        actual_text_extraction_spec = text_extraction_node.get_spec().to_json()
        expected_text_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/docproc_output_format_spec.json").read())
        aflow_json_spec = aflow.to_json()
        #print(json.dumps(aflow_json_spec, indent=2))

        assert actual_text_extraction_spec["task"] == "text_extraction"
        assert actual_text_extraction_spec["kind"] == "docproc"
        assert actual_text_extraction_spec["name"] == "text_extraction"
      
        assert actual_text_extraction_spec["output_format"] == "object"
        assert actual_text_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert "TextExtractionObjectResponse" in actual_text_extraction_spec["output_schema"]["$ref"]
        assert actual_text_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["TextExtractionObjectResponse"]["title"]

        assert aflow_json_spec["schemas"].get("TextExtractionResponse") is None
        assert aflow_json_spec["schemas"].get("TextExtractionObjectResponse") is not None
        assert aflow_json_spec["schemas"]["TextExtractionObjectResponse"] == expected_text_extraction_spec["schemas"]["TextExtractionObjectResponse"]


    def test_text_extraction_node_with_kvpschema_spec_generation(self):
        kvp_schema = {
            "document_type": "MyInvoice",
            "document_description": "My own invoice document.",
            "additional_prompt_instructions": "Focus on the total amount due.",
            "fields": {
              "invoice_number": {
                "description": "The unique identifier for the invoice.",
                "example": "INV-1001",
                "default": ""
              },
              "total_amount": {
                "description": "The total amount due on the invoice.",
                "example": "1500.00",
                "default": ""
              },
              "is_final_notice": {
                "description": "Indicates if this invoice is a final notice. This is a checkbox field.",
                "example": "Yes",
                "default": "No",
                "available_options": [
                  "Yes",
                  "No"
                ]
              }
            }
          }

        aflow = FlowFactory.create_flow(name="text_extraction_flow_example")
        text_extraction_node = aflow.docproc(
            name="text_extraction",
            display_name="text_extraction",
            description="Extract text out of a document's contents.",
            task="text_extraction",
            kvp_schemas = [ DocProcKVPSchema(**kvp_schema) ],
        )
        expected_text_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/docproc_kvpschema_spec.json").read())
        actual_text_extraction_spec = text_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_text_extraction_spec["task"] == "text_extraction"
        assert actual_text_extraction_spec["kind"] == "docproc"
        assert actual_text_extraction_spec["name"] == "text_extraction"
        assert actual_text_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert actual_text_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["TextExtractionResponse"]["title"]
        docprocKvpSchema = DocProcKVPSchema(**kvp_schema)
        assert actual_text_extraction_spec['kvp_schemas'][0] == docprocKvpSchema
        
        assert aflow_json_spec["spec"]["kind"] == expected_text_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_text_extraction_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["title"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert aflow_json_spec["schemas"]["text_extraction_input"]["properties"]["kvp_schemas"] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["properties"]["kvp_schemas"]
        assert aflow_json_spec["nodes"]["text_extraction"]["spec"]["kvp_schemas"][0] == docprocKvpSchema
        assert aflow_json_spec["schemas"]["TextExtractionResponse"] is not None
        #docprocKvpSchema.to_dict()
        
    def test_text_extraction_node_with_advanced_params_spec_generation(self):
        """Test the docproc node with advanced parameters like kvp_force_schema_name and kvp_enable_text_hints."""
        kvp_schema = {
            "document_type": "MyInvoice",
            "document_description": "My own invoice document.",
            "additional_prompt_instructions": "Focus on the total amount due.",
            "fields": {
              "invoice_number": {
                "description": "The unique identifier for the invoice.",
                "example": "INV-1001",
                "default": ""
              },
              "total_amount": {
                "description": "The total amount due on the invoice.",
                "example": "1500.00",
                "default": ""
              }
            }
        }

        aflow = FlowFactory.create_flow(name="text_extraction_flow_example")
        text_extraction_node = aflow.docproc(
            name="text_extraction",
            display_name="text_extraction",
            description="Extract text out of a document's contents.",
            task="text_extraction",
            kvp_schemas = [ DocProcKVPSchema(**kvp_schema) ],
            kvp_force_schema_name = "MyInvoice",
            kvp_enable_text_hints = False
        )
        expected_text_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/docproc_advanced_params_spec.json").read())
        actual_text_extraction_spec = text_extraction_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_text_extraction_spec["task"] == "text_extraction"
        assert actual_text_extraction_spec["kind"] == "docproc"
        assert actual_text_extraction_spec["name"] == "text_extraction"
        assert actual_text_extraction_spec["input_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["text_extraction_input"]["title"]
        assert actual_text_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_text_extraction_spec["schemas"]["TextExtractionResponse"]["title"]
        
        # Test the advanced parameters
        assert actual_text_extraction_spec["kvp_force_schema_name"] == "MyInvoice"
        assert actual_text_extraction_spec["kvp_enable_text_hints"] == False
        
        docprocKvpSchema = DocProcKVPSchema(**kvp_schema)
        assert actual_text_extraction_spec['kvp_schemas'][0] == docprocKvpSchema
        
        assert aflow_json_spec["schemas"]["TextExtractionResponse"] is not None

        # Check that the parameters are correctly included in the flow JSON spec
        assert "kvp_force_schema_name" in aflow_json_spec["nodes"]["text_extraction"]["spec"]
        assert aflow_json_spec["nodes"]["text_extraction"]["spec"]["kvp_force_schema_name"] == "MyInvoice"
        assert "kvp_enable_text_hints" in aflow_json_spec["nodes"]["text_extraction"]["spec"]
        assert aflow_json_spec["nodes"]["text_extraction"]["spec"]["kvp_enable_text_hints"] == False
