from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ..libref.sidemod import SideMod


@tool(name="testtool6_name", description="testtool6-description", permission=ToolPermission.READ_ONLY)
def my_tool(input: str) -> str:
   temp = SideMod()
   return temp.execute(input)