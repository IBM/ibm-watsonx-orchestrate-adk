from ibm_watsonx_orchestrate.flow_builder.flows import (
    FlowFactory
)
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocumentClassificationResponse, NodeErrorHandlerConfig
import os
import json


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
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
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

        assert "error_handler_config" not in actual_spec

    def test_doc_classifier_node_with_error_handler_config(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docclassifier_retry")
        doc_classifier_node = aflow.docclassifier(
            name="document_classifier_node",
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            classes=CustomClasses(),
            error_handler_config=NodeErrorHandlerConfig(
                error_message="Classification failed",
                max_retries=3,
                retry_interval=2000,
            ),
        )
        spec = doc_classifier_node.get_spec().to_json()

        assert "error_handler_config" in spec
        assert spec["error_handler_config"]["max_retries"] == 3
        assert spec["error_handler_config"]["retry_interval"] == 2000
        assert spec["error_handler_config"]["error_message"] == "Classification failed"

    def test_doc_classifier_node_without_error_handler_config(self):
        aflow = FlowFactory.create_flow(name="custom_flow_docclassifier_no_retry")
        doc_classifier_node = aflow.docclassifier(
            name="document_classifier_node",
            llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            classes=CustomClasses(),
        )
        spec = doc_classifier_node.get_spec().to_json()

        assert "error_handler_config" not in spec
