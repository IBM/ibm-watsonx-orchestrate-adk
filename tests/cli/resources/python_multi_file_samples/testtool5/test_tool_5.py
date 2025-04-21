from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


class SideModTool2:

   def execute(self, input):
      return 'returning hello world, ' + input

   def bray(self):
      return "HEE HAW!!"


@tool(name="test-tool 5 name", description="testtool5-description", permission=ToolPermission.READ_ONLY)
def my_tool(input: str) -> str:
   temp = SideModTool2()
   return temp.execute(input)
