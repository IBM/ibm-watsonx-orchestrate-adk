
from typing import Optional,Dict
from pydantic import BaseModel, model_validator

class WelcomeContent(BaseModel):
    welcome_message: str
    description: Optional[str] = None
    is_default_message: bool = False

    @model_validator(mode='before')
    def validate_fields(cls,values):
        return validate_welcome_content_fields(values)


def validate_welcome_content_fields(values: Dict):
    for field in ['welcome_message']:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")
    return values