import json
import importlib
import inspect
import sys
from pathlib import Path
from typing import List
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import BaseChannel, TwilioWhatsappChannel, TwilioSMSChannel, SlackChannel, WebchatChannel, GenesysBotConnectorChannel, FacebookChannel, TeamsChannel
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open


# Mapping of channel type strings to their implementation classes
CHANNEL_CLASSES = {
    'webchat': WebchatChannel,
    'twilio_whatsapp': TwilioWhatsappChannel,
    'twilio_sms': TwilioSMSChannel,
    'byo_slack': SlackChannel,
    'genesys_bot_connector': GenesysBotConnectorChannel,
    'facebook': FacebookChannel,
    'teams': TeamsChannel
}

class ChannelLoader:
    """Utility class for loading channel configurations from files."""

    @staticmethod
    def from_python(file: str) -> List[BaseChannel]:
        """Import all Channel instances from a Python file."""
        file_path = Path(file)
        file_directory = file_path.parent
        file_name = file_path.stem

        sys.path.append(str(file_directory))
        try:
            module = importlib.import_module(file_name)

            channels = []
            for _, obj in inspect.getmembers(module):
                if isinstance(obj, BaseChannel):
                    channels.append(obj)
            return channels
        finally:
            # Always clean up sys.path
            if str(file_directory) in sys.path:
                sys.path.remove(str(file_directory))

    @staticmethod
    def from_spec(file: str) -> BaseChannel:
        """Load a channel configuration from a spec file.

        Args:
            file: Path to the channel configuration file (.yaml, .yml, or .json)

        Returns:
            BaseChannel: An instance of the appropriate channel subclass
        """
        # Handle YAML/JSON spec files
        with safe_open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml. For Python files, use from_python() instead.')

        if not content.get("channel"):
            raise BadRequest(f"Field 'channel' not provided. Please ensure the channel type is specified (e.g., 'twilio_whatsapp')")

        channel_type = content.get('channel')
        channel_class = CHANNEL_CLASSES.get(channel_type)

        if not channel_class:
            supported = ', '.join(CHANNEL_CLASSES.keys())
            raise BadRequest(f"Unsupported channel type: '{channel_type}'. Supported types: {supported}")

        channel = channel_class.model_validate(content)

        return channel
