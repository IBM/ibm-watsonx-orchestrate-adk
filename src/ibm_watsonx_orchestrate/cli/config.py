import os
import logging
import yaml
from copy import deepcopy

from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from enum import Enum
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

# Section Headers
AUTH_SECTION_HEADER = "auth"
CONTEXT_SECTION_HEADER = "context"
ENVIRONMENTS_SECTION_HEADER = "environments"
PYTHON_REGISTRY_HEADER = "python_registry"
USER_ENV_CACHE_HEADER = "cached_user_env"
LICENSE_HEADER = "license"
SETTINGS_HEADER = "settings"
PREVIOUS_DOCKER_CONTEXT = "previous_docker_context"

# Option Names
AUTH_MCSP_API_KEY_OPT = "wxo_mcsp_api_key"
AUTH_MCSP_TOKEN_OPT = "wxo_mcsp_token"
AUTH_MCSP_TOKEN_EXPIRY_OPT = "wxo_mcsp_token_expiry"
CONTEXT_ACTIVE_ENV_OPT = "active_environment"
PYTHON_REGISTRY_TYPE_OPT = "type"
PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT = "skip_version_check"
PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT = "test_package_version_override"
ENV_WXO_URL_OPT = "wxo_url"
ENV_CRN_OPT = "crn"
ENV_IAM_URL_OPT = "iam_url"
PROTECTED_ENV_NAME = "local"
ENV_AUTH_TYPE = "auth_type"
BYPASS_SSL = "bypass_ssl"
VERIFY = "verify"
ENV_ACCEPT_LICENSE = 'accepts_license_agreements'
FILE_ENCODING = "file_encoding"
DOCKER_CONTEXT = "docker"
USE_NATIVE_DOCKER = "use_native_docker"

DEFAULT_LOCAL_SERVICE_URL = "http://localhost:4321"
CHAT_UI_PORT = "3000"

DEFAULT_CONFIG_FILE_FOLDER = f"{os.path.expanduser('~')}/.config/orchestrate"
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG_FILE_CONTENT = {
    CONTEXT_SECTION_HEADER: {CONTEXT_ACTIVE_ENV_OPT: None},
    PYTHON_REGISTRY_HEADER: {
        PYTHON_REGISTRY_TYPE_OPT: str(RegistryType.PYPI),
        PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT: None,
        PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT: False
    },
    ENVIRONMENTS_SECTION_HEADER: {
        PROTECTED_ENV_NAME: {
            ENV_WXO_URL_OPT: DEFAULT_LOCAL_SERVICE_URL
        }
    },
    USER_ENV_CACHE_HEADER: {}
}

AUTH_CONFIG_FILE_FOLDER = f"{os.path.expanduser('~')}/.cache/orchestrate"
AUTH_CONFIG_FILE = "credentials.yaml"
AUTH_CONFIG_FILE_CONTENT = {
    AUTH_SECTION_HEADER: {
        PROTECTED_ENV_NAME: None
    }
}

logger = logging.getLogger(__name__)


def merge_configs(source: dict, destination: dict) -> dict:
    if source:
        merged_object = deepcopy(source)
    else:
        merged_object = {}

    for key, value in destination.items():
        if isinstance(value, dict):
            node = merged_object.setdefault(key, {})
            merged_object[key] = merge_configs(node, value)
        else:
            merged_object[key] = value
    return merged_object


def _check_if_default_config_file(folder, file):
    return folder == DEFAULT_CONFIG_FILE_FOLDER and file == DEFAULT_CONFIG_FILE


def _check_if_auth_config_file(folder, file):
    return folder == AUTH_CONFIG_FILE_FOLDER and file == AUTH_CONFIG_FILE

def clear_protected_env_credentials_token():
    auth_cfg = Config(config_file_folder=AUTH_CONFIG_FILE_FOLDER, config_file=AUTH_CONFIG_FILE)
    if auth_cfg.exists(AUTH_SECTION_HEADER, PROTECTED_ENV_NAME, AUTH_MCSP_TOKEN_OPT):
        auth_cfg.delete(AUTH_SECTION_HEADER, PROTECTED_ENV_NAME, AUTH_MCSP_TOKEN_OPT)


class ConfigFileTypes(str, Enum):
    AUTH = 'auth'
    CONFIG = 'config'
    DOCPROC_FEATURE_CONF= 'docproc_feature'

class Config:

    def __init__(
            self,
            config_file_folder: str = DEFAULT_CONFIG_FILE_FOLDER,
            config_file: str = DEFAULT_CONFIG_FILE,
    ):
        self.config_file_folder = config_file_folder
        self.config_file = config_file
        self.config_file_path = os.path.join(self.config_file_folder, self.config_file)
        self.file_type = None

        if _check_if_default_config_file(folder=self.config_file_folder, file=self.config_file):
            self.file_type = ConfigFileTypes.CONFIG
        elif _check_if_auth_config_file(folder=self.config_file_folder, file=self.config_file):
            self.file_type = ConfigFileTypes.AUTH

        # Check if config file already exists
        if not os.path.exists(self.config_file_path):
            self.create_config_file()

        # Check if file has defaults
        with open(self.config_file_path, 'r') as conf_file:
            config_data = yaml_safe_load(conf_file) or {}
            if self.file_type == ConfigFileTypes.CONFIG:
                if not config_data.get(ENVIRONMENTS_SECTION_HEADER, {}).get(PROTECTED_ENV_NAME, False):
                    logger.debug("Setting default config data")
                    self.create_defaults(DEFAULT_CONFIG_FILE_CONTENT)

                if not config_data.get(PYTHON_REGISTRY_HEADER, {}).get(PYTHON_REGISTRY_TYPE_OPT, False):
                    self.create_defaults({
                        PYTHON_REGISTRY_HEADER: DEFAULT_CONFIG_FILE_CONTENT.get(PYTHON_REGISTRY_HEADER, {})
                    })

            elif self.file_type == ConfigFileTypes.AUTH:
                if PROTECTED_ENV_NAME not in set(config_data.get(AUTH_SECTION_HEADER, {}).keys()):
                    logger.debug("Setting default credentials data")
                    self.create_defaults(AUTH_CONFIG_FILE_CONTENT)

    def create_config_file(self) -> None:
        logger.info(f'Creating config file at location "{self.config_file_path}"')

        os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
        open(self.config_file_path, 'a').close()

    def create_defaults(self, default_content):
        self.save(default_content)

    def get_active_env(self):
        return self.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)

    def get_active_env_config(self, option):
        return self.read(ENVIRONMENTS_SECTION_HEADER, self.get_active_env()).get(option)

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
        obj = {section:
                   {option: value}
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

    def get(self, *args):
        """
        Accesses an item of arbitrary depth from the config file.
        Takes an arbitrary number of args. Uses the args in order
        as keys to access deeper sections of the config and then returning the last specified key.
        """

        config_data = {}
        try:
            with open(self.config_file_path, 'r') as conf_file:
                config_data = yaml_safe_load(conf_file) or {}
        except FileNotFoundError:
            pass

        if len(args) < 1:
            return config_data

        try:
            nested_dict = config_data
            for key in args[:-1]:
                nested_dict = nested_dict[key]

            return nested_dict[args[-1]]
        except KeyError as e:
            raise KeyError(f"Failed to get data from config. Key {e} not in {list(nested_dict.keys())}")

    def delete(self, *args) -> None:
        """
        Deletes an item of arbitrary depth from the config file.
        Takes an arbitrary number of args. Uses the args in order
        as keys to access deeper sections of the config and then deleting the last specified key.
        """
        if len(args) < 1:
            raise BadRequest("Config.delete() requires at least one positional argument")

        config_data = {}
        try:
            with open(self.config_file_path, 'r') as conf_file:
                config_data = yaml_safe_load(conf_file) or {}
        except FileNotFoundError:
            pass

        try:
            deletion_data = deepcopy(config_data)
            nested_dict = deletion_data
            for key in args[:-1]:
                nested_dict = nested_dict[key]

            del (nested_dict[args[-1]])
        except KeyError as e:
            raise KeyError(f"Failed to delete from config. Key {e} not in {list(nested_dict.keys())}")

        with open(self.config_file_path, 'w') as conf_file:
            yaml.dump(deletion_data, conf_file, allow_unicode=True)

    def exists(self, *args) -> bool:
        """
        Determines if an item of arbitrary depth exists in the config file.
        Takes an arbitrary number of args. Uses the args in order
        as keys to access deeper sections of the config and then deleting the last specified key.
        """
        if len(args) < 1:
            raise BadRequest("Config.delete() requires at least one positional argument")

        config_data = {}
        try:
            with open(self.config_file_path, 'r') as conf_file:
                config_data = yaml_safe_load(conf_file) or {}
        except FileNotFoundError:
            pass

        expression = "config_data"
        for key in args:
            temp = eval(expression)

            if not isinstance(temp, dict) or key not in temp:
                return False

            else:
                expression += f"['{key}']"

        return True
