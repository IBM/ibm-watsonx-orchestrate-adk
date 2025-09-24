import json
import sys
import rich
import yaml
import logging
from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client import VoiceConfigurationsClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

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
      with open(file, 'r') as f:
        content = yaml.load(f, Loader=yaml.SafeLoader)

    elif file.endswith(".json"):
      with open(file, 'r') as f:
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
    return client.get(voice_config_id)

  def get_voice_config_by_name(self, voice_config_name: str) -> VoiceConfiguration | None:
    client = self.get_voice_configurations_client()
    configs = client.get_by_name(voice_config_name)
    if len(configs) == 0:
      logger.error(f"No voice_configs with the name '{voice_config_name}' found. Failed to get config")
      sys.exit(1)
    
    if len(configs) > 1:
      logger.error(f"Multiple voice_configs with the name '{voice_config_name}' found. Failed to get config")
      sys.exit(1)
      
    return configs[0]

  def list_voice_configs(self, verbose: bool) -> None:
    voice_configs = self.fetch_voice_configs()

    if verbose:
      json_configs = [json.loads(x.dumps_spec()) for x in voice_configs]
      rich.print_json(json.dumps(json_configs, indent=4))
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

      for config in voice_configs:
        attached_agents = [x.display_name or x.name or x.id for x in config.attached_agents]
        config_table.add_row(
          config.name,
          config.voice_configuration_id,
          config.speech_to_text.provider,
          config.text_to_speech.provider,
          ",".join(attached_agents)
        )
      
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




    
    


