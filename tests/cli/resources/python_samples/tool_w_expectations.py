from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials, ConnectionType


@tool(
        description="test_python_tool",
        expected_credentials=[ExpectedCredentials(app_id="test", type=[ConnectionType.BASIC_AUTH])]
    )
def my_tool():
    pass

@tool(
        description="test_python_tool",
        expected_credentials=[ExpectedCredentials(app_id="test", type=[ConnectionType.BASIC_AUTH])]
    )
def my_tool_w_type():
    pass
