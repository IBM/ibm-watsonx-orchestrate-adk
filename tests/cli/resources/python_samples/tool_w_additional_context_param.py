from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.run.context import AgentRun


@tool(
  description="Mock tool for testing context passing with request context.",
)
def context_mock(current_run : AgentRun, previous_run: AgentRun) -> str:
  return f"Current Context: {current_run}\n Previous Context {previous_run}"