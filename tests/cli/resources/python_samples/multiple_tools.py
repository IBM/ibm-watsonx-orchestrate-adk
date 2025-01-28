from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from typing import Optional, List, Dict


@tool()
def my_tool(description="test_python_tool"):
    pass


@tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
def my_tool_1():
    pass


@tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
def my_tool_2(input: str) -> str:
    pass


@tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
def my_tool_3(input: None) -> None:
    pass


@tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
def my_tool_4(input: Optional[str]) -> Optional[str]:
    pass


@tool()
def sample_tool(sampleA: List[str], b: Optional[List[str]]) -> List[str]:
    pass


@tool()
def sample_tool_1(
    sampleA: Dict[str, str], b: Optional[Dict[str, str]]
) -> List[Dict[str, str]]:
    pass
