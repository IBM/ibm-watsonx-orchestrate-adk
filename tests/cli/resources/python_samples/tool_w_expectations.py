from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool(
        description="test_python_tool",
        expected_credentials=["test"]
    )
def my_tool():
    pass

@tool(
        description="test_python_tool",
        expected_credentials=[{"app_id": "test", "type": "basic_auth"}]
    )
def my_tool_w_type():
    pass
