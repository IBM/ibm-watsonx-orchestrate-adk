from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigEntity
import os
import json
class UserInput(BaseModel):
    buyer: DocExtConfigEntity = Field(name="Buyer", default=DocExtConfigEntity(name="Buyer", field_name="buyer"))
    seller: DocExtConfigEntity = Field(name="Seller", default=DocExtConfigEntity(name="Seller", field_name="seller"))
    agreement_date: DocExtConfigEntity = Field(name="Agreement date", default=DocExtConfigEntity(name="Agreement Date", field_name="agreement_name"))


class TestDocExtNodes():
    
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
            llm="meta-llama/llama-3-2-11b-vision-instruct",
            input_entities=UserInput(),
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
        
