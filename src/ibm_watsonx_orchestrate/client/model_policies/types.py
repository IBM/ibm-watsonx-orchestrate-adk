from enum import Enum
from typing import Optional, List, Dict, Any, Union

from pydantic import Field, BaseModel, ConfigDict

class ModelPolicyStrategyMode(str, Enum):
    LOAD_BALANCED = "loadbalance"
    FALL_BACK = "fallback"
    SINGLE = "single"

class ModelPolicyStrategy(BaseModel):
    mode: ModelPolicyStrategyMode = None
    on_status_codes: List[int] = None

class ModelPolicyRetry(BaseModel):
    attempts: int = None
    on_status_codes: List[int] = None

class ModelPolicyTarget(BaseModel):
    model_id: str = None
    weight: int = None


class ModelPolicyInner(BaseModel):
    strategy: ModelPolicyStrategy = None
    retry: ModelPolicyRetry = None
    targets: List[Union[ModelPolicyTarget, 'ModelPolicyInner']] = None


class ModelPolicy(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    display_name: str
    policy: ModelPolicyInner

