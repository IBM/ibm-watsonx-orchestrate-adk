from enum import Enum
from typing import Optional, Dict, List, Annotated
from annotated_types import Len
from pydantic import BaseModel, model_validator


class PromptState(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MISSING = ""


class AgentPrompt(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    prompt: str
    state: PromptState = PromptState.ACTIVE
        
    @model_validator(mode='before')
    def validate_fields(cls,values):
        return validate_agent_prompt_fields(values)


def validate_agent_prompt_fields(values: Dict):
    for field in ['id','title','prompt','state']:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")
    return values

class StarterPrompts(BaseModel):
    is_default_prompts: bool = False
    prompts: Annotated[List[AgentPrompt], Len(min_length=1)]