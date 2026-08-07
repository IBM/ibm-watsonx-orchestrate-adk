from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigField, NodeErrorHandlerConfig
import os
import json
class UserInput(BaseModel):
    buyer: DocExtConfigField = Field(title="Buyer", default=DocExtConfigField(name="Buyer", field_name="buyer"))
    seller: DocExtConfigField = Field(title="Seller", default=DocExtConfigField(name="Seller", field_name="seller"))
    agreement_date: DocExtConfigField = Field(title="Agreement date", default=DocExtConfigField(name="Agreement Date", field_name="agreement_name"))


class TestDocExtNode():
    
    def setup_method(self):
        self.parent_dir_path = os.path.dirname(os.path.realpath(__file__))

    def teardown_method(self):
        pass

    def test_doc_ext_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docext_example")
        doc_ext_node, CEEResponse = aflow.docext(
            name="contract_extractor",
            display_name="Extract fields from a contract",
            description="Extracts fields from an input contract file",
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            fields=UserInput(),
        )
        expected_extraction_spec = json.loads(open(self.parent_dir_path + "/resources/docext_spec.json").read())
        actual_extraction_spec = doc_ext_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_extraction_spec["version"] == "TIP"
        assert actual_extraction_spec["kind"] == "docext"
        assert actual_extraction_spec["name"] == "contract_extractor"
        assert actual_extraction_spec["output_schema"]['$ref'].split("/")[-1] == expected_extraction_spec["schemas"]["DocExtFieldValue"]["title"] 
        
        assert aflow_json_spec["spec"]["kind"] == expected_extraction_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_extraction_spec["spec"]["name"]
        for k,v in aflow_json_spec["schemas"]["DocExtFieldValue"]["properties"].items():
            assert aflow_json_spec["schemas"]["DocExtFieldValue"]["properties"][k]["title"] == expected_extraction_spec["schemas"]["DocExtFieldValue"]["properties"][k]["title"]

        assert "error_handler_config" not in actual_extraction_spec

    def test_doc_ext_node_with_error_handler_config(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docext_retry")
        doc_ext_node, _ = aflow.docext(
            name="contract_extractor",
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            fields=UserInput(),
            error_handler_config=NodeErrorHandlerConfig(
                error_message="Extraction failed",
                max_retries=3,
                retry_interval=2000,
            ),
        )
        spec = doc_ext_node.get_spec().to_json()

        assert "error_handler_config" in spec
        assert spec["error_handler_config"]["max_retries"] == 3
        assert spec["error_handler_config"]["retry_interval"] == 2000
        assert spec["error_handler_config"]["error_message"] == "Extraction failed"

    def test_doc_ext_node_without_error_handler_config(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docext_no_retry")
        doc_ext_node, _ = aflow.docext(
            name="contract_extractor",
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            fields=UserInput(),
        )
        spec = doc_ext_node.get_spec().to_json()

        assert "error_handler_config" not in spec
