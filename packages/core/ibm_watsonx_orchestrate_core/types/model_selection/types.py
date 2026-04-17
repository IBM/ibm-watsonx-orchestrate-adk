from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import Field, BaseModel, ConfigDict, model_validator


class ModelSelectionSettings(BaseModel):
    default_llm: str | None = Field(description="Default LLM for the tenant", default=None)
    llm_denylist: List[str] = Field(description="LLMs that are not allowed to be used by the tenant for the new agents",
                                    default_factory=list)


class ModelSelectionPatch(BaseModel):
    """
    Patch schema for updating model selection settings.

    Supports multiple operations in one request:
    - default_llm: Update the default LLM (cannot be empty string)
    - add_to_llm_denylist: Add models to the denylist
    - remove_from_llm_denylist: Remove models from the denylist

    Note: Models cannot appear in both add and remove lists.
    """
    default_llm: str | None = None
    add_to_llm_denylist: list[str] | None = None
    remove_from_llm_denylist: list[str] | None = None

    @model_validator(mode='after')
    def validate_default_llm_not_empty(self):
        """Ensure default_llm is not an empty string."""
        if self.default_llm is not None and self.default_llm.strip() == "":
            raise ValueError("default_llm cannot be an empty string")
        return self

    @model_validator(mode='after')
    def validate_no_overlap(self):
        """Ensure no model appears in both add and remove lists."""
        if self.add_to_llm_denylist and self.remove_from_llm_denylist:
            add_set = set(self.add_to_llm_denylist)
            remove_set = set(self.remove_from_llm_denylist)
            overlap = add_set & remove_set
            if overlap:
                raise ValueError(f"Models cannot be in both add and remove lists: {', '.join(sorted(overlap))}")
        return self

    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        """Ensure at least one field is provided."""
        if not any([self.default_llm, self.add_to_llm_denylist, self.remove_from_llm_denylist]):
            raise ValueError(
                "At least one field must be provided: default_llm, add_to_llm_denylist, or remove_from_llm_denylist")
        return self


class GetModelSelectionResponse(BaseModel):
    model_selection_settings: ModelSelectionSettings
    warnings: list[str] = Field(default_factory=list, description="Warnings about denied model being used")
