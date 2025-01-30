import json
import yaml
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, model_validator, ConfigDict
from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool
from pydantic import Field
from typing import Annotated

# TO-DO: this is just a placeholder. Will update this later to align with backend
DEFAULT_LLM = "watsonx/meta-llama/llama-3-1-70b-instruct"


class BaseAgentSpec(BaseModel):
    def dump_spec(self, file: str) -> None:
        dumped = self.model_dump(mode='json', exclude_unset=True, exclude_none=True)
        with open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, sort_keys=False)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.model_dump(mode='json', exclude_none=True)
        return json.dumps(dumped, indent=2)

# ===============================
#       EXPERT AGENT TYPES
# ===============================
class ExpertAgentType(str, Enum):
    EXPERT = "expert"

class ExpertAgentSpec(BaseAgentSpec):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    description: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    type: ExpertAgentType = None
    role: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    goal: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    instructions: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    backstory: Optional[str] = None
    tools: Optional[List[str]] | Optional[List['BaseTool']] = None
    llm: str = DEFAULT_LLM
    
    def __init__(self, *args, **kwargs):
        if "tools" in kwargs and kwargs["tools"]:
            kwargs["tools"] = [x.__tool_spec__.name if isinstance(x, BaseTool) else x for x in kwargs["tools"]]
        super().__init__(*args, **kwargs)

    @model_validator(mode="before")
    def validate_fields_for_expert(cls, values):
        return validate_expert_agent_fields(values, mandatory_for_expert=True)

def validate_expert_agent_fields(values: dict, mandatory_for_expert: bool = True) -> dict:
    """
    Common validation function for expert agent fields.
    
    Parameters:
    - values: The values to validate
    - mandatory_for_expert: Whether the fields are mandatory (True for create, False for patch)
    
    Returns:
    - dict: The validated values
    """
    #Test for type
    if values.get('type') is None:
        raise ValueError("'type' cannot be empty or just whitespace")

    # Check for empty strings or whitespace
    for field in ["name", "type", "role", "goal", "instructions", "tools", "llm"]:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")
    
    return values

# ===============================
#     ORCHESTRATE AGENT TYPES
# ===============================

class AgentManagementStyle(str, Enum):
    SUPERVISOR = 'supervisor'

class SupervisorConfig(BaseModel):
    reflection_enabled : bool | None = False
    reflection_retry_count: int | None = 0

class OrchestrateAgentSpec(BaseAgentSpec):
    name: Annotated[str, Field(json_schema_extra={"min_length_str":1})] = None
    management_style: AgentManagementStyle = AgentManagementStyle.SUPERVISOR
    management_style_config: Optional[SupervisorConfig] = None
    llm: str = DEFAULT_LLM
    agents: Optional[List[str]] | Optional[List['ExpertAgentSpec']]= None

    def __init__(self, *args, **kwargs):
        if "agents" in kwargs and kwargs["agents"]:
            kwargs["agents"] = [x.name if isinstance(x, ExpertAgentSpec) else x for x in kwargs["agents"]]
        super().__init__(*args, **kwargs)

    @model_validator(mode="before")
    def validate_model(cls, values: Dict) -> Dict:
         return orchestrate_agent_model_validation(cls, values)

def safe_strip(value):
    return value.strip() if isinstance(value, str) else value

def orchestrate_agent_model_validation(cls, values) -> Dict:

    name = safe_strip(values.get("name", ""))

    if not name:
        raise ValueError("name is required and cannot be whitespace")
    
    return values