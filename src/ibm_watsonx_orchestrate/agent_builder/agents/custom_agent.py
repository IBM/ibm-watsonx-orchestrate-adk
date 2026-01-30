from pydantic import Field
from ibm_watsonx_orchestrate.agent_builder.agents.agent import Agent


class CustomAgent(Agent):
    """Agent subclass for custom agents that includes the file path for upload."""
    custom_agent_file_path: str | None = Field(default=None, exclude=True)
    
    def __repr__(self):
        return f"CustomAgent(name='{self.name}', description='{self.description}', file_path='{self.custom_agent_file_path}')"