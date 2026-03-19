from enum import Enum
from typing import List, Union

from pydantic import BaseModel, ConfigDict

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
    weight: float | None = None
    model_name: str = None

class ModelPolicyInner(BaseModel):
    strategy: ModelPolicyStrategy = None
    retry: ModelPolicyRetry = None
    targets: List[Union['ModelPolicyInner', ModelPolicyTarget]] = None


class ModelPolicy(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    display_name: str
    description: str
    policy: ModelPolicyInner