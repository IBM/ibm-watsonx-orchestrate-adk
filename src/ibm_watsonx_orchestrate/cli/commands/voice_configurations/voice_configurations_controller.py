import json
import sys
import rich
import yaml
import logging
from pathlib import Path
from typing import Optional, List, Any
from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration, VoiceConfigurationListEntry
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client import VoiceConfigurationsClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

logger = logging.getLogger(__name__)

class VoiceConfigurationsController:

  def __init__(self):
    self.voice_configs_client = None

  def get_voice_configurations_client(self):
    if not self.voice_configs_client:
      self.voice_configs_client = instantiate_client(VoiceConfigurationsClient)
    return self.voice_configs_client


  def import_voice_config(self, file: str) -> VoiceConfiguration:

    if file.endswith('.yaml') or file.endswith('.yml'):
      with safe_open(file, 'r') as f:
        content = yaml.load(f, Loader=yaml.SafeLoader)

    elif file.endswith(".json"):
      with safe_open(file, 'r') as f:
        content = json.load(f)

    else:
      raise BadRequest("file must end in .yaml, .yml or .json")

    return VoiceConfiguration.model_validate(content)


  def fetch_voice_configs(self) -> list[VoiceConfiguration]:
    client = self.get_voice_configurations_client()
    res = client.list()

    voice_configs = []

    for config in res:
      try:
        voice_configs.append(VoiceConfiguration.model_validate(config))
      except:
        name = config.get('name', None)
        logger.error(f"Config '{name}' could not be parsed")

    return voice_configs
  
  def get_voice_config(self, voice_config_id: str) -> VoiceConfiguration | None:
    client = self.get_voice_configurations_client()
    logger.info(f"Sensitive fields, such as API keys, have been removed")
    return client.get_by_id(voice_config_id)

  def get_voice_config_by_name(self, voice_config_name: str) -> VoiceConfiguration | None:
    client = self.get_voice_configurations_client()
    configs = client.get_by_name(voice_config_name)
    if len(configs) == 0:
      logger.error(f"No voice_configs with the name '{voice_config_name}' found. Failed to get config")
      sys.exit(1)
    
    if len(configs) > 1:
      logger.error(f"Multiple voice_configs with the name '{voice_config_name}' found. Failed to get config")
      sys.exit(1)
      
    logger.info(f"Sensitive fields, such as API keys, have been removed")
    return configs[0]

  def list_voice_configs(self, verbose: bool, format: Optional[ListFormats]=None) -> List[dict[str | Any]] | List[VoiceConfigurationListEntry] | str | None:
    voice_configs = self.fetch_voice_configs()

    if verbose:
      json_configs = [json.loads(x.dumps_spec()) for x in voice_configs]
      rich.print_json(json.dumps(json_configs, indent=4))
      return json_configs
    else:
      config_table = rich.table.Table(
        show_header=True, 
        header_style="bold white", 
        title="Voice Configurations",
        show_lines=True
      )

      column_args={
        "Name" : {"overflow": "fold"},
        "ID" : {"overflow": "fold"},
        "STT Provider" : {"overflow": "fold"},
        "TTS Provider" : {"overflow": "fold"},
        "Attached Agents" : {}
      }

      for column in column_args:
        config_table.add_column(column, **column_args[column])

      config_details = []

      for config in voice_configs:
        attached_agents = [x.name or x.id for x in config.attached_agents]
        entry = VoiceConfigurationListEntry(
          name=config.name,
          id=config.voice_configuration_id,
          speech_to_text_provider=config.speech_to_text.provider,
          text_to_speech_provider=config.text_to_speech.provider,
          attached_agents=attached_agents
        )
        config_details.append(entry)
        config_table.add_row(*entry.get_row_details())
      
      match format:
        case ListFormats.JSON:
          return config_details
        case ListFormats.Table:
          return rich_table_to_markdown(config_table)
        case _:
          rich.print(config_table)

  def create_voice_config(self, voice_config: VoiceConfiguration) -> str | None:
    client = self.get_voice_configurations_client()
    res = client.create(voice_config)
    config_id = res.get("id",None)
    if config_id:
      logger.info(f"Sucessfully created voice config '{voice_config['name']}'. id: '{config_id}'")
    
    return config_id


  def update_voice_config_by_id(self, voice_config_id: str, voice_config: VoiceConfiguration) -> str | None:
    client = self.get_voice_configurations_client()
    res = client.update(voice_config_id,voice_config)
    config_id = res.get("id",None)
    if config_id:
      logger.info(f"Sucessfully updated voice config '{voice_config['name']}'. id: '{config_id}'")

    return config_id

  def update_voice_config_by_name(self, voice_config_name: str, voice_config: VoiceConfiguration) -> str | None: 
    client = self.get_voice_configurations_client()
    existing_config = client.get_by_name(voice_config_name)

    if existing_config and len(existing_config) > 0:
      config_id = existing_config[0].voice_configuration_id
      client.update(config_id,voice_config)
    else:
      logger.warning(f"Voice config '{voice_config_name}' not found, creating new config instead")
      config_id = self.create_voice_config(voice_config)

    return config_id

  def publish_or_update_voice_config(self, voice_config: VoiceConfiguration) -> str | None:
    client = self.get_voice_configurations_client()
    voice_config_name = voice_config.name
    existing_config = client.get_by_name(voice_config_name)

    if existing_config and len(existing_config) > 0:
      config_id = existing_config[0].voice_configuration_id
      client.update(config_id,voice_config)
    else:
      client.create(voice_config)

  def remove_voice_config_by_id(self, voice_config_id: str) -> None:
    client = self.get_voice_configurations_client()
    client.delete(voice_config_id)
    logger.info(f"Sucessfully deleted voice config '{voice_config_id}'")

  def remove_voice_config_by_name(self, voice_config_name: str) -> None:
    client = self.get_voice_configurations_client()
    voice_config = self.get_voice_config_by_name(voice_config_name)
    if voice_config:
      client.delete(voice_config.voice_configuration_id)
      logger.info(f"Sucessfully deleted voice config '{voice_config_name}'")
    else:
      logger.info(f"Voice config '{voice_config_name}' not found")

  def resolve_config_id(
      self,
      config_id: Optional[str] = None,
      config_name: Optional[str] = None
  ) -> str:
    """Resolve config ID from either ID or name."""
    if not config_id and not config_name:
      logger.error("Either --id or --name must be provided")
      sys.exit(1)

    if config_id and config_name:
      # Validate they match
      client = self.get_voice_configurations_client()
      try:
        config = client.get_by_id(config_id)
        if not config:
          logger.error(f"Voice config with ID '{config_id}' not found")
          sys.exit(1)

        actual_name = config.name if hasattr(config, 'name') else config.get('name')
        if actual_name != config_name:
          logger.error(f"Voice config ID '{config_id}' has name '{actual_name}', not '{config_name}'")
          sys.exit(1)

        return config_id
      except Exception as e:
        logger.error(f"Failed to validate voice config: {e}")
        sys.exit(1)

    if config_id:
      return config_id

    # Resolve by name
    try:
      client = self.get_voice_configurations_client()
      configs = client.get_by_name(config_name)

      if not configs:
        logger.error(f"Voice config with name '{config_name}' not found")
        sys.exit(1)

      if len(configs) > 1:
        logger.error(f"Multiple voice configs with name '{config_name}' found. Use --id to specify which one.")
        sys.exit(1)

      return configs[0].voice_configuration_id
    except Exception as e:
      logger.error(f"Failed to resolve voice config: {e}")
      sys.exit(1)

  def export_voice_config(
      self,
      config_id: str,
      output_path: str
  ) -> None:
    """Export a voice config to a YAML file."""
    output_file = Path(output_path)
    output_file_extension = output_file.suffix

    if output_file_extension not in [".yaml", ".yml"]:
      logger.error(f"Output file must end with '.yaml' or '.yml'. Provided file '{output_path}' ends with '{output_file_extension}'")
      sys.exit(1)

    client = self.get_voice_configurations_client()

    try:
      config = client.get_by_id(config_id)
    except Exception as e:
      logger.error(f"Failed to get voice config: {e}")
      sys.exit(1)

    if not config:
      logger.error(f"Voice config not found: {config_id}")
      sys.exit(1)

    # Validate structure
    try:
      voice_config_model = VoiceConfiguration.model_validate(config)
    except Exception as e:
      logger.error(f"Failed to validate voice config: {e}")
      sys.exit(1)

    # Remove response-only fields
    export_data = voice_config_model.model_dump(
      exclude_none=True,
      exclude={'voice_configuration_id', 'tenant_id', 'attached_agents'}
    )

    try:
      with safe_open(output_path, 'w') as outfile:
        yaml.dump(export_data, outfile, sort_keys=False, default_flow_style=False, allow_unicode=True)

      logger.info(f"Exported voice config '{voice_config_model.name}' to '{output_path}'")
      logger.info(f"Sensitive fields, such as API keys, have been removed")

    except Exception as e:
      logger.error(f"Failed to write export file: {e}")
      sys.exit(1)

