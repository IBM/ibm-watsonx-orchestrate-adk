from enum import Enum
from typing_extensions import Optional

from pydantic import BaseModel, model_validator

from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment

class PlatformType(str, Enum):
    GENESYS = 'genesys'

    def __str__(self) -> str:
        return str(self.value)

class ApplicationPostfix(str, Enum):
    GENESYS = 'i_genesys_configuration'

    def __str__(self) -> str:
        return str(self.value)

class GenesysPlatformConnection(BaseModel):
    platform_type: PlatformType = PlatformType.GENESYS
    app_id: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    endpoint: Optional[str] = None
    environment: ConnectionEnvironment

    @model_validator(mode='after')
    def validate_values(self):
        required_fields = ['app_id', 'client_id', 'client_secret', 'endpoint', 'environment']
        missing_fields = []

        for field in required_fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required fields for Genesys platform configuration: {', '.join(missing_fields)}")

        return self

    def get_entries(self):
        return [
            f"client_id={self.client_id}",
            f"client_secret={self.client_secret}",
            f"endpoint={self.endpoint}"
        ]