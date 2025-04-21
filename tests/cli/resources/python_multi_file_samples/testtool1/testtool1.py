from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from libref.sidemod import SideMod


@tool(name="testtool1_name", description="testtool1-description", permission=ToolPermission.READ_ONLY)
def my_tool(input: str) -> str:
   temp = SideMod()
   return temp.execute(input)