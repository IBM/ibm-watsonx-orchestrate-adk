from ibm_watsonx_orchestrate.agent_builder.agents import Agent, AgentStyle
from ibm_watsonx_orchestrate.agent_builder.agents import AgentGuideline
from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def my_tool():
    """
    my tool does things
    """
    return 'my_tool'

agent = Agent(
    name="sample",
    description="sample",
    llm="watsonx/ibm/granite-3-8b-instruct",
    style=AgentStyle.REACT,
    collaborators=[],
    tools=[],
    guidelines=[
        AgentGuideline(
            display_name='Sample guideline',
            condition='When the user asks for a potato',
            action='You should reply did you mean a tomato'
        ),
        AgentGuideline(
            condition='When the user tries to do a thing',
            action='You should reply did you mean a tomato',
            tool=my_tool
        ),
        AgentGuideline(
            display_name='Sample other',
            condition='When the user tries to do a thing',
            action='You should reply did you mean a tomato',
            tool='my_tool'
        ),
    ]
)