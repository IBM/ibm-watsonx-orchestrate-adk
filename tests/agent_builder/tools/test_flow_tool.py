
import json
from ibm_watsonx_orchestrate.agent_builder.tools.flow_tool import create_flow_json_tool
from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import tool
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolPermission, WXOFile
from ibm_watsonx_orchestrate.flow_builder.flows import flow
from ibm_watsonx_orchestrate.flow_builder.flows.constants import END, START
from ibm_watsonx_orchestrate.flow_builder.flows.flow import Flow


def test_flow_tool_support_wxo_file_input_output(snapshot):
    @tool(
        permission=ToolPermission.READ_ONLY
    )
    def get_file(file_url: WXOFile) -> WXOFile:
        """
        Returns a file url for download.
        Args:
            file_url (WxOFile): A file url for input
        Returns:
            WxOFile: A file url for download.
        """
        pass

    @flow(
        name="hello_file_flow",
        input_schema=WXOFile,
        output_schema=WXOFile
    )
    def build_hello_file_flow(aflow: Flow = None) -> Flow:

        get_file_node = aflow.tool(
            get_file, input_schema=WXOFile, output_schema=WXOFile)
        aflow.edge(START, get_file_node).edge(get_file_node, END)
        return aflow

    flow_tool = create_flow_json_tool(build_hello_file_flow().to_json(),
                                      name='hello-flow-tool',
                                      description='This is a flow tool to generate hello world with file claim',
                                      permission=ToolPermission.READ_ONLY)

    spec = json.loads(flow_tool.dumps_spec())

    assert spec['binding']['flow']['model']['spec']['input_schema']['$ref'] == '#/schemas/hello_file_flow_input'
    assert spec['binding']['flow']['model']['schemas']['hello_file_flow_input']['properties']['data']['type'] == 'string'
    assert spec['binding']['flow']['model']['schemas']['hello_file_flow_input']['properties']['data']['format'] == 'wxo-file'

    assert spec['binding']['flow']['model']['spec']['output_schema']['type'] == 'string'
    assert spec['binding']['flow']['model']['spec']['output_schema']['format'] == 'wxo-file'

    snapshot.assert_match(spec)
