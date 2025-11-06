from typing import Optional, Literal, Union, ClassVar
from pydantic import BaseModel, Field, ConfigDict, model_validator
import json
from enum import Enum

from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion

class ChannelType(str, Enum):
    """Supported channel types for agent integrations."""
    WEBCHAT = "webchat"
    TWILIO_WHATSAPP = "twilio_whatsapp"
    TWILIO_SMS = "twilio_sms"
    SLACK = "byo_slack"
    # TEAMS = "teams"
    # MESSENGER = "messenger"
    # GENESYS_BOT_CONNECTOR = "genesys_bot_connector"
    # GENESYS_AUDIO_CONNECTOR = "genesys_audio_connector"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)


class ChannelKind(str, Enum):
    CHANNEL = "channel"

    def __str__(self):
        return self.value

    def __repr__(self):
        return repr(self.value)

class BaseChannel(BaseModel):
    """Base class for all channel types.

    This class defines common fields and behaviors for all channel implementations.
    Response-only fields (marked in SERIALIZATION_EXCLUDE) should not be sent to the API
    when creating or updating channels.
    """

    # Fields to exclude when serializing for API requests (response-only fields)
    SERIALIZATION_EXCLUDE: ClassVar[set] = {
        "channel_id", "tenant_id", "agent_id", "environment_id",
        "created_on", "created_by", "updated_at", "updated_by"
    }

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # User-editable fields
    name: str = Field(..., max_length=64, description="Channel name (required)")
    description: Optional[str] = Field(None, max_length=1024)
    channel: str = Field(..., description="Channel type identifier")
    spec_version: SpecVersion = SpecVersion.V1
    kind: ChannelKind = ChannelKind.CHANNEL

    # Response-only fields
    channel_id: Optional[str] = Field(None, description="Channel ID (response only)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (response only)")
    agent_id: Optional[str] = Field(None, description="Agent ID (response only)")
    environment_id: Optional[str] = Field(None, description="Environment ID (response only)")
    created_on: Optional[str] = Field(None, description="Creation timestamp (response only)")
    created_by: Optional[str] = Field(None, description="Creator user ID (response only)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (response only)")
    updated_by: Optional[str] = Field(None, description="Last updater user ID (response only)")

    def dumps_spec(self, exclude_none: bool = True, exclude_unset: bool = False) -> str:
        """Serialize channel to JSON string for API submission.

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
        """Get the API endpoint path for this channel type.

        By default, returns the channel type as-is. Subclasses can override
        this if the API path differs from the channel type value.

        Returns:
            API endpoint path segment (e.g., 'slack', 'twilio_whatsapp')
        """
        return self.channel

class WebchatChannel(BaseChannel):
    """Webchat channel configuration.

    Enables integration with watsonx Orchestrate webchat.
    This channel is primarily managed through the embed command
    which generates embed code snippets for web integration.

    Attributes:
        channel: Always "webchat"
    """

    channel: Literal["webchat"] = "webchat"

class TwilioWhatsappChannel(BaseChannel):
    """Twilio WhatsApp channel configuration.

    Enables integration with WhatsApp through Twilio API.

    Required credentials:
        - Twilio Account SID
        - Twilio Authentication Token

    Attributes:
        channel: Always "twilio_whatsapp"
        account_sid: Twilio Account SID
        twilio_authentication_token: Twilio Auth Token
    """

    channel: Literal["twilio_whatsapp"] = "twilio_whatsapp"
    account_sid: Optional[str] = Field(
        None,
        min_length=34,
        max_length=34,
        pattern="^AC[0-9a-fA-F]{32}$",
        description="Twilio Account SID"
    )
    twilio_authentication_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Twilio Authentication Token"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Twilio credentials are provided."""
        if not self.account_sid:
            raise ValueError("account_sid is required for twilio_whatsapp channels")
        if not self.twilio_authentication_token:
            raise ValueError("twilio_authentication_token is required for twilio_whatsapp channels")
        return self

class TwilioSMSChannel(BaseChannel):
    """Twilio SMS channel configuration.

    Enables integration with SMS through Twilio API.

    Required credentials:
        - Twilio Account SID
        - Twilio Authentication Token

    Attributes:
        channel: Always "twilio_sms"
        account_sid: Twilio Account SID
        twilio_authentication_token: Twilio Auth Token
        phone_number: Optional phone number for SMS
    """

    channel: Literal["twilio_sms"] = "twilio_sms"
    account_sid: Optional[str] = Field(
        None,
        min_length=34,
        max_length=34,
        pattern="^AC[0-9a-fA-F]{32}$",
        description="Twilio Account SID"
    )
    twilio_authentication_token: Optional[str] = Field(
        None,
        min_length=1,
        description="Twilio Authentication Token"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Phone number for SMS"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Twilio credentials are provided."""
        if not self.account_sid:
            raise ValueError("account_sid is required for twilio_sms channels")
        if not self.twilio_authentication_token:
            raise ValueError("twilio_authentication_token is required for twilio_sms channels")
        return self

class SlackTeam(BaseModel):
    """Slack team/workspace configuration.

    Attributes:
        id: Slack team/workspace ID
        bot_access_token: Bot user OAuth token for this team
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str = Field(..., min_length=1, description="Slack team/workspace ID")
    bot_access_token: str = Field(..., min_length=1, description="Bot user OAuth token")


class SlackChannel(BaseChannel):
    """Slack channel configuration.

    Enables integration with Slack using the BYO (Bring Your Own) Slack app model.

    Required credentials:
        - client_id: Slack API client ID
        - client_secret: Slack API client secret
        - signing_secret: Slack API signing secret
        - teams: List of Slack teams with bot access tokens

    Attributes:
        channel: Always "byo_slack"
        client_id: Slack API client ID
        client_secret: Slack API client secret
        signing_secret: Slack API signing secret
        teams: List of Slack teams/workspaces with their bot tokens
    """

    channel: Literal["byo_slack"] = "byo_slack"

    def get_api_path(self) -> str:
        """Get the API endpoint path for this channel type.

        Note: The API uses 'slack' in the URL path but 'byo_slack' in the payload.
        """
        return "slack"

    client_id: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API client ID"
    )
    client_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API client secret"
    )
    signing_secret: Optional[str] = Field(
        None,
        min_length=1,
        description="Slack API signing secret"
    )
    teams: Optional[list[SlackTeam]] = Field(
        None,
        description="List of Slack teams/workspaces with their bot access tokens"
    )

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate that required Slack credentials are provided."""
        if not self.client_id:
            raise ValueError("client_id is required for byo_slack channels")
        if not self.client_secret:
            raise ValueError("client_secret is required for byo_slack channels")
        if not self.signing_secret:
            raise ValueError("signing_secret is required for byo_slack channels")
        if not self.teams or len(self.teams) == 0:
            raise ValueError("at least one team with bot_access_token is required for byo_slack channels")
        return self

# Union type for all channel types (will expand)
Channel = Union[TwilioWhatsappChannel, TwilioSMSChannel, SlackChannel, WebchatChannel]
