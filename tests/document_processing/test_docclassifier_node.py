from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass
import os
import json

from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocumentClassificationResponse


class CustomClasses(BaseModel):
    buyer: DocClassifierClass = Field(default=DocClassifierClass(class_name="Buyer"))
    seller: DocClassifierClass = Field(default=DocClassifierClass(class_name="Seller"))
    agreement_date: DocClassifierClass = Field(default=DocClassifierClass(class_name="Agreement_Date"))


class TestDocClassifierNode():
    def setup_method(self):
        self.parent_dir_path = os.path.dirname(os.path.realpath(__file__))

    def teardown_method(self):
        pass

    def test_doc_ext_node_spec_generation(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docclassifier_test")
        doc_classifier_node = aflow.docclassifier(
            name="document_classifier_node",
            display_name="document_classifier_node",
            description="Classify custom classes from a document",
            llm="watsonx/meta-llama/llama-3-2-11b-vision-instruct",
            classes=CustomClasses(),
        )
        expected_spec = json.loads(open(self.parent_dir_path + "/resources/doc_classifier_spec.json").read())
        actual_spec = doc_classifier_node.get_spec().to_json()
        aflow_json_spec = aflow.to_json()

        assert actual_spec["version"] == "TIP"
        assert actual_spec["kind"] == "docclassifier"
        assert actual_spec["name"] == "document_classifier_node"
        assert actual_spec["input_schema"]['$ref'].split("/")[-1] == expected_spec["schemas"]["document_classifier_node_input"]["title"]
        assert actual_spec["output_schema"]['$ref'].split("/")[-1] == expected_spec["schemas"]["DocumentClassificationResponse"]["title"] 
        
        assert aflow_json_spec["spec"]["kind"] == expected_spec["spec"]["kind"]
        assert aflow_json_spec["spec"]["name"] == expected_spec["spec"]["name"]
        assert aflow_json_spec["schemas"]["document_classifier_node_input"]["title"] == expected_spec["schemas"]["document_classifier_node_input"]["title"]

        
