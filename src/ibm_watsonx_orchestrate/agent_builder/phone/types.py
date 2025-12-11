from typing import Optional, Literal, Union, ClassVar
from pydantic import BaseModel, Field, ConfigDict, model_validator
import json
from enum import Enum

from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion


class PhoneChannelType(str, Enum):
    """Supported phone channel types."""
    GENESYS_AUDIO_CONNECTOR = "genesys_audio_connector"
    # SIP = "sip"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)


class PhoneChannelKind(str, Enum):
    PHONE = "phone"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)


class BasePhoneChannel(BaseModel):
    """Base class for all phone channel types.

    Phone channels are global resources (not scoped to agent/environment).
    Multiple agents can attach to the same phone config.

    Response-only fields (marked in SERIALIZATION_EXCLUDE) should not be sent to the API
    when creating or updating phone channels.
    """

    # Fields to exclude when serializing for API requests (response-only fields)
    SERIALIZATION_EXCLUDE: ClassVar[set] = {
        "id", "tenant_id", "attached_environments", "phone_numbers",
        "created_on", "created_by", "updated_at", "updated_by"
    }

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # User-editable fields
    name: str = Field(..., max_length=64, description="Phone config name (required)")
    description: Optional[str] = Field(None, max_length=1024)
    service_provider: str = Field(..., description="Service provider identifier")
    spec_version: SpecVersion = SpecVersion.V1
    kind: PhoneChannelKind = PhoneChannelKind.PHONE

    # Response-only fields
    id: Optional[str] = Field(None, description="Phone config ID (response only)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (response only)")
    attached_environments: Optional[list[dict[str, str]]] = Field(None, description="Attached agent/environment pairs (response only)")
    phone_numbers: Optional[list[dict[str, str]]] = Field(None, description="Phone numbers (response only)")
    created_on: Optional[str] = Field(None, description="Creation timestamp (response only)")
    created_by: Optional[str] = Field(None, description="Creator user ID (response only)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (response only)")
    updated_by: Optional[str] = Field(None, description="Last updater user ID (response only)")

    def dumps_spec(self, exclude_none: bool = True, exclude_unset: bool = False) -> str:
        """Serialize phone config to JSON string for API submission.

        Args:
            exclude_none: Exclude fields with None values
            exclude_unset: Exclude fields that were not explicitly set

        Returns:
            JSON string representation
        """
        data = self.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            exclude=self.SERIALIZATION_EXCLUDE
        )
        return json.dumps(data, indent=2)

    def get_api_path(self) -> str:
        """Get the API endpoint path for this phone channel type.

        All phone channels use 'phone' as the API path.

        Returns:
            API endpoint path segment (always 'phone')
        """
        return "phone"


class GenesysAudioConnectorChannel(BasePhoneChannel):
    """Genesys Audio Connector phone channel configuration.

    Enables phone/voice integration with Genesys Audio Connector.

    Phone channels are global.
    Multiple agents can attach to the same phone config.

    Required credentials:
        - api_key: Genesys API key
        - client_secret: Genesys client secret

    Attributes:
        service_provider: Always "genesys_audio_connector"
        security: Object containing api_key and client_secret
    """

    service_provider: Literal[PhoneChannelType.GENESYS_AUDIO_CONNECTOR] = PhoneChannelType.GENESYS_AUDIO_CONNECTOR
    security: Optional[dict[str, str]] = Field(
        None,
        description="Security credentials with api_key and client_secret"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Genesys Audio Connector credentials are provided."""
        if not self.security:
            raise ValueError("security is required for genesys_audio_connector phone channels")
        if not isinstance(self.security, dict):
            raise ValueError("security must be a dictionary")
        if "api_key" not in self.security or not self.security["api_key"]:
            raise ValueError("security.api_key is required for genesys_audio_connector phone channels")
        if "client_secret" not in self.security or not self.security["client_secret"]:
            raise ValueError("security.client_secret is required for genesys_audio_connector phone channels")
        return self


# Union type for all phone channel types (will expand)
PhoneChannel = Union[GenesysAudioConnectorChannel]
