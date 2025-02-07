import os
import logging
import yaml
from copy import deepcopy
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load

DEFAULT_CONFIG_FILE_FOLDER = f"{os.path.expanduser('~')}/.config/orchestrate"
DEFAULT_CONFIG_FILE = "config.yaml"

AUTH_CONFIG_FILE_FOLDER = f"{os.path.expanduser('~')}/.cache/orchestrate"
AUTH_CONFIG_FILE = "credentials.yaml"

# Section Headers
AUTH_SECTION_HEADER = "auth"
APP_SECTION_HEADER = "app"

# Option Names
AUTH_MCSP_API_KEY_OPT = "wxo_mcsp_api_key"
AUTH_MCSP_TOKEN_OPT = "wxo_mcsp_token"

APP_WXO_URL_OPT = "wxo_url"

logger = logging.getLogger(__name__)

def merge_configs(source: dict, destination: dict) -> dict:
    merged_object = deepcopy(source)

    for key, value in destination.items():
        if isinstance(value, dict):
            node = merged_object.setdefault(key, {})
            merged_object[key] = merge_configs(node, value)
        else:
            merged_object[key] = value
    return merged_object


class Config:
    def __init__(
        self,
        config_file_folder: str = DEFAULT_CONFIG_FILE_FOLDER,
        config_file: str = DEFAULT_CONFIG_FILE,
    ):
        self.config_file_folder = config_file_folder
        self.config_file = config_file
        self.config_file_path = os.path.join(self.config_file_folder, self.config_file)

        # Check if config file already exists
        if not os.path.exists(self.config_file_path):
            self.create_config_file()

    def create_config_file(self) -> None:
        logger.info(f'Creating config file at location "{self.config_file_path}"')

        os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
        open(self.config_file_path, 'a').close()


    def read(self, section: str, option: str) -> any:
        try:
            with open(self.config_file_path, "r") as conf_file:
                config_data = yaml.load(conf_file, Loader=yaml.SafeLoader)
                if config_data is None:
                    return None
                return config_data[section][option]
        except KeyError:
            return None

    def write(self, section: str, option: str, value: any) -> None:
        obj = {section :
                {option : value}
            }
        self.save(obj)

    def save(self, object: dict) -> None:
        config_data = {}
        try:
            with open(self.config_file_path, 'r') as conf_file:
                config_data = yaml_safe_load(conf_file) or {}
        except FileNotFoundError:
            pass
        
        config_data = merge_configs(config_data, object)
            
        with open(self.config_file_path, 'w') as conf_file:
            yaml.dump(config_data, conf_file, allow_unicode=True)
