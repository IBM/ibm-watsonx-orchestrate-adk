
from typing import Optional,Dict
from pydantic import BaseModel, ConfigDict, model_validator, model_serializer

class WelcomeContent(BaseModel):
    """
    Supports two shapes:
      - flat: {"welcome_message": ..., "description": ..., "is_default_message": ...}
      - locale-keyed: {"default": {...}, "pt-BR": {...}, "is_default_message": ...}
    Locale entries are kept as extra fields so they round-trip unchanged.
    """
    model_config = ConfigDict(extra="allow")

    welcome_message: Optional[str] = None
    description: Optional[str] = None
    is_default_message: bool = False
    is_user_barge_in_disabled: bool = False

    @model_validator(mode='before')
    def validate_fields(cls,values):
        return validate_welcome_content_fields(values)

    @model_validator(mode='after')
    def require_message_or_locales(self):
        # Flat shape still requires welcome_message. Locale-keyed shape carries it inside each locale entry.
        if self.welcome_message is None and not self.model_extra:
            raise ValueError("welcome_message is required")
        return self

    @model_serializer(mode='wrap')
    def _serialize(self, handler):
        data = handler(self)
        # Locale-keyed payloads have no flat welcome_message. Do not add flat-only defaults to them.
        if self.welcome_message is None:
            for field in ("description", "is_default_message", "is_user_barge_in_disabled"):
                if field not in self.model_fields_set:
                    data.pop(field, None)
        return data


def validate_welcome_content_fields(values: Dict):
    for field in ['welcome_message']:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")
    return values
