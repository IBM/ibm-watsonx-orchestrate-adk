import json
import importlib
import inspect
import sys
from pathlib import Path
from typing import List
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import BasePhoneChannel, GenesysAudioConnectorChannel, SIPTrunkChannel
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open


# Mapping of phone channel type strings to their implementation classes
PHONE_CHANNEL_CLASSES = {
    'genesys_audio_connector': GenesysAudioConnectorChannel,
    'sip_trunk': SIPTrunkChannel,
}

class PhoneChannelLoader:
    """Utility class for loading phone channel configurations from files."""

    @staticmethod
    def from_python(file: str) -> List[BasePhoneChannel]:
        """Import all PhoneChannel instances from a Python file."""
        file_path = Path(file)
        file_directory = file_path.parent
        file_name = file_path.stem

        sys.path.append(str(file_directory))
        try:
            module = importlib.import_module(file_name)

            phone_channels = []
            for _, obj in inspect.getmembers(module):
                if isinstance(obj, BasePhoneChannel):
                    phone_channels.append(obj)
            return phone_channels
        finally:
            # Always clean up sys.path
            if str(file_directory) in sys.path:
                sys.path.remove(str(file_directory))

    @staticmethod
    def from_spec(file: str) -> BasePhoneChannel:
        """Load a phone channel configuration from a spec file.

        Args:
            file: Path to the phone channel configuration file (.yaml, .yml, or .json)

        Returns:
            BasePhoneChannel: An instance of the appropriate phone channel subclass
        """
        # Handle YAML/JSON spec files
        with safe_open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                content = yaml_safe_load(f)
            elif file.endswith('.json'):
                content = json.load(f)
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml. For Python files, use from_python() instead.')

        if not content.get("service_provider"):
            raise BadRequest(f"Field 'service_provider' not provided. Please ensure the phone channel type is specified (e.g., 'genesys_audio_connector')")

        channel_type = content.get('service_provider')
        channel_class = PHONE_CHANNEL_CLASSES.get(channel_type)

        if not channel_class:
            supported = ', '.join(PHONE_CHANNEL_CLASSES.keys())
            raise BadRequest(f"Unsupported phone channel type: '{channel_type}'. Supported types: {supported}")

        phone_channel = channel_class.model_validate(content)

        return phone_channel
