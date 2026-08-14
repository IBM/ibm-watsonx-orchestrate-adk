from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START, AgentNode


class AgentNodeOutput(BaseModel):
    value: str = Field(description="Agent response")


class FlowOutput(BaseModel):
    out: str = Field(description="")


@flow(
    name="count_tracker_flow",
    display_name="Count Tracker Flow",
    output_schema=FlowOutput,
    schedulable=True,
    suppress_agent_summarization=True,
    llm_model="watsonx/openai/gpt-oss-120b",
)
def build_count_tracker_flow(aflow: Flow) -> Flow:
    """Delegates to the count_tracker_agent to retrieve the current running count."""

    agent_node: AgentNode = aflow.agent(
        name="count_tracker",
        display_name="count_tracker_agent",
        agent="count_tracker_agent",
        message="What is the current count?",
        description="count_tracker_agent",
        output_schema=AgentNodeOutput,
        thread_control_policy="REUSE_AND_CORRELATE",
    )

    aflow.sequence(START, agent_node, END)

    aflow.map_output(
        output_variable="out",
        expression="flow.count_tracker.output.value",
    )

    return aflow
