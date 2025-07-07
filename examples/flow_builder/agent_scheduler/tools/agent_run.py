'''
Build a simple hello world flow that will combine the result of two tools.
'''

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START, AgentNode

class AgentRequest(BaseModel):
    agent_id: str = Field(description="The agent id.")
    request: str = Field(description="The request to the agent.")

class AgentResponse(BaseModel):
    response: str = Field(description="The response from the agent")

def build_agent_run_node(aflow: Flow) -> AgentNode:
    agent_run_node = aflow.agent(
        name="run_an_agent",
        agent="{agent_id}",
        title="Running the agent",
        description="Running the agent with the specified request.",
        message="Here is the request: {request}",
        input_schema=AgentRequest,
        output_schema=AgentResponse
    )

    return agent_run_node

@flow(
        name = "agent_run",
        input_schema=AgentRequest,
        output_schema=AgentResponse,
        schedulable=True
    )
def build_agent_run_flow(aflow: Flow = None) -> Flow:
    """
    This flow will take an agent id and a request and run the agent with the request.
    """

    agent_run_node = build_agent_run_node(aflow)

    aflow.sequence(START, agent_run_node, END)

    return aflow
