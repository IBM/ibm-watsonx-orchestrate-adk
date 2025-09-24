import importlib.resources as resources
import logging
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

from ibm_watsonx_orchestrate.cli.commands.server.types import WatsonXAIEnvConfig, ModelGatewayEnvConfig
from ibm_watsonx_orchestrate.cli.config import USER_ENV_CACHE_HEADER, Config
from ibm_watsonx_orchestrate.client.utils import is_arm_architecture

logger = logging.getLogger(__name__)


class EnvService:

    __ALWAYS_UNSET: set[str] = {
        "WO_API_KEY",
        "WO_INSTANCE",
        "DOCKER_IAM_KEY",
        "WO_DEVELOPER_EDITION_SOURCE",
        "WATSONX_SPACE_ID",
        "WATSONX_APIKEY",
        "WO_USERNAME",
        "WO_PASSWORD",
    }

    __NON_SECRET_ENV_ITEMS: set[str] = {
        "WO_DEVELOPER_EDITION_SOURCE",
        "WO_INSTANCE",
        "USE_SAAS_ML_TOOLS_RUNTIME",
        "AUTHORIZATION_URL",
        "OPENSOURCE_REGISTRY_PROXY",
        "SAAS_WDU_RUNTIME",
        "LATEST_ENV_FILE",
    }

    def __init__ (self, config: Config):
        self.__config = config

    def get_compose_file (self) -> Path:
        custom_compose_path = self.__get_compose_file_path()
        return Path(custom_compose_path) if custom_compose_path else self.__get_default_compose_file()

    def __get_compose_file_path (self) -> str:
        return self.__config.read(USER_ENV_CACHE_HEADER, "DOCKER_COMPOSE_FILE_PATH")

    @staticmethod
    def __get_default_compose_file () -> Path:
        with resources.as_file(
                resources.files("ibm_watsonx_orchestrate.docker").joinpath("compose-lite.yml")
        ) as compose_file:
            return compose_file

    @staticmethod
    def get_default_env_file () -> Path:
        with resources.as_file(
                resources.files("ibm_watsonx_orchestrate.docker").joinpath("default.env")
        ) as env_file:
            return env_file

    @staticmethod
    def read_env_file (env_path: Path | str) -> dict:
        return dotenv_values(str(env_path))

    def get_user_env (self, user_env_file: Path | str, fallback_to_persisted_env: bool = True) -> dict:
        if user_env_file is not None and isinstance(user_env_file, str):
            user_env_file = Path(user_env_file)

        user_env = self.read_env_file(user_env_file) if user_env_file is not None else {}

        if fallback_to_persisted_env is True and not user_env:
            user_env = self.__get_persisted_user_env() or {}

        return user_env

    @staticmethod
    def get_dev_edition_source_core(env_dict: dict | None) -> str:
        if not env_dict:
            return "myibm"

        source = env_dict.get("WO_DEVELOPER_EDITION_SOURCE")

        if source:
            return source
        if env_dict.get("WO_INSTANCE"):
            return "orchestrate"
        return "myibm"

    def get_dev_edition_source(self, user_env_file: str):
        return self.get_dev_edition_source_core(self.get_user_env(user_env_file))

    @staticmethod
    def merge_env (default_env_path: Path, user_env_path: Path | None) -> dict:
        merged = dotenv_values(str(default_env_path))

        if user_env_path is not None:
            user_env = dotenv_values(str(user_env_path))
            merged.update(user_env)

        return merged

    @staticmethod
    def __get_default_registry_env_vars_by_dev_edition_source (default_env: dict, user_env: dict, source: str) -> dict[str, str]:
        component_registry_var_names = {key for key in default_env if key.endswith("_REGISTRY")} | {'REGISTRY_URL'}

        registry_url = user_env.get("REGISTRY_URL", None)
        if not registry_url:
            if source == "internal":
                registry_url = "us.icr.io/watson-orchestrate-private"
            elif source == "myibm":
                registry_url = "cp.icr.io/cp/wxo-lite"
            elif source == "orchestrate":
                # extract the hostname from the WO_INSTANCE URL, and replace the "api." prefix with "registry." to construct the registry URL per region
                wo_url = user_env.get("WO_INSTANCE")

                if not wo_url:
                    raise ValueError(
                        "WO_INSTANCE is required in the environment file if the developer edition source is set to 'orchestrate'.")

                parsed = urlparse(wo_url)
                hostname = parsed.hostname

                registry_url = f"registry.{hostname[4:]}/cp/wxo-lite"
            else:
                raise ValueError(
                    f"Unknown value for developer edition source: {source}. Must be one of ['internal', 'myibm', 'orchestrate']."
                )

        result = {name: registry_url for name in component_registry_var_names}
        return result

    @staticmethod
    def prepare_clean_env (env_file: Path) -> None:
        """Remove env vars so terminal definitions don't override"""
        keys_from_file = set(dotenv_values(str(env_file)).keys())
        keys_to_unset = keys_from_file | EnvService.__ALWAYS_UNSET
        for key in keys_to_unset:
            os.environ.pop(key, None)

    @staticmethod
    def write_merged_env_file (merged_env: dict, target_path: str = None) -> Path:
        if target_path:
            file = open(target_path, "w")
        else:
            file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env")

        with file:
            for key, val in merged_env.items():
                file.write(f"{key}={val}\n")
        return Path(file.name)

    def persist_user_env (self, env: dict, include_secrets: bool = False) -> None:
        if include_secrets:
            persistable_env = env
        else:
            persistable_env = {k: env[k] for k in EnvService.__NON_SECRET_ENV_ITEMS if k in env}

        self.__config.save(
            {
                USER_ENV_CACHE_HEADER: persistable_env
            }
        )

    def __get_persisted_user_env (self) -> dict | None:
        user_env = self.__config.get(USER_ENV_CACHE_HEADER) if self.__config.get(USER_ENV_CACHE_HEADER) else None
        return user_env

    def set_compose_file_path_in_env (self, path: str = None) -> None:
        self.__config.save(
            {
                USER_ENV_CACHE_HEADER: {
                    "DOCKER_COMPOSE_FILE_PATH": path
                }
            }
        )

    @staticmethod
    def __get_dbtag_from_architecture (merged_env_dict: dict) -> str:
        """Detects system architecture and returns the corresponding DBTAG."""
        arm64_tag = merged_env_dict.get("ARM64DBTAG")
        amd_tag = merged_env_dict.get("AMDDBTAG")

        if is_arm_architecture():
            return arm64_tag
        else:
            return amd_tag

    @staticmethod
    def __apply_server_env_dict_defaults (provided_env_dict: dict) -> dict:

        env_dict = provided_env_dict.copy()

        env_dict['DBTAG'] = EnvService.__get_dbtag_from_architecture(merged_env_dict=env_dict)

        model_config = None
        try:
            use_model_proxy = env_dict.get("USE_SAAS_ML_TOOLS_RUNTIME")
            if not use_model_proxy or use_model_proxy.lower() != 'true':
                model_config = WatsonXAIEnvConfig.model_validate(env_dict)
        except ValueError:
            pass

        # If no watsonx ai detials are found, try build model gateway config
        if not model_config:
            try:
                model_config = ModelGatewayEnvConfig.model_validate(env_dict)
            except ValueError as e:
                pass

        if not model_config:
            logger.error(
                "Missing required model access environment variables. Please set Watson Orchestrate credentials 'WO_INSTANCE' and 'WO_API_KEY'. For CPD, set 'WO_INSTANCE', 'WO_USERNAME' and either 'WO_API_KEY' or 'WO_PASSWORD'. Alternatively, you can set WatsonX AI credentials directly using 'WATSONX_SPACE_ID' and 'WATSONX_APIKEY'")
            sys.exit(1)

        env_dict.update(model_config.model_dump(exclude_none=True))

        return env_dict

    @staticmethod
    def auto_configure_callback_ip (merged_env_dict: dict) -> dict:
        """
        Automatically detect and configure CALLBACK_HOST_URL if it's empty.

        Args:
            merged_env_dict: The merged environment dictionary

        Returns:
            Updated environment dictionary with CALLBACK_HOST_URL set
        """
        callback_url = merged_env_dict.get('CALLBACK_HOST_URL', '').strip()

        # Only auto-configure if CALLBACK_HOST_URL is empty
        if not callback_url:
            logger.info("Auto-detecting local IP address for async tool callbacks...")

            system = platform.system()
            ip = None

            try:
                if system in ("Linux", "Darwin"):
                    result = subprocess.run(["ifconfig"], capture_output=True, text=True, check=True)
                    lines = result.stdout.splitlines()

                    for line in lines:
                        line = line.strip()
                        # Unix ifconfig output format: "inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255"
                        if line.startswith("inet ") and "127.0.0.1" not in line:
                            candidate_ip = line.split()[1]
                            # Validate IP is not loopback or link-local
                            if (candidate_ip and
                                    not candidate_ip.startswith("127.") and
                                    not candidate_ip.startswith("169.254")):
                                ip = candidate_ip
                                break

                elif system == "Windows":
                    result = subprocess.run(["ipconfig"], capture_output=True, text=True, check=True)
                    lines = result.stdout.splitlines()

                    for line in lines:
                        line = line.strip()
                        # Windows ipconfig output format: "   IPv4 Address. . . . . . . . . . . : 192.168.1.100"
                        if "IPv4 Address" in line and ":" in line:
                            candidate_ip = line.split(":")[-1].strip()
                            # Validate IP is not loopback or link-local
                            if (candidate_ip and
                                    not candidate_ip.startswith("127.") and
                                    not candidate_ip.startswith("169.254")):
                                ip = candidate_ip
                                break

                else:
                    logger.warning(f"Unsupported platform: {system}")
                    ip = None

            except Exception as e:
                logger.debug(f"IP detection failed on {system}: {e}")
                ip = None

            if ip:
                callback_url = f"http://{ip}:4321"
                merged_env_dict['CALLBACK_HOST_URL'] = callback_url
                logger.info(f"Auto-configured CALLBACK_HOST_URL to: {callback_url}")
            else:
                # Fallback for localhost
                callback_url = "http://host.docker.internal:4321"
                merged_env_dict['CALLBACK_HOST_URL'] = callback_url
                logger.info(f"Using Docker internal URL: {callback_url}")
                logger.info("For external tools, consider using ngrok or similar tunneling service.")
        else:
            logger.info(f"Using existing CALLBACK_HOST_URL: {callback_url}")

        return merged_env_dict

    @staticmethod
    def apply_llm_api_key_defaults (env_dict: dict) -> None:
        llm_value = env_dict.get("WATSONX_APIKEY")
        if llm_value:
            env_dict.setdefault("ASSISTANT_LLM_API_KEY", llm_value)
            env_dict.setdefault("ASSISTANT_EMBEDDINGS_API_KEY", llm_value)
            env_dict.setdefault("ROUTING_LLM_API_KEY", llm_value)
            env_dict.setdefault("BAM_API_KEY", llm_value)
            env_dict.setdefault("WXAI_API_KEY", llm_value)
        space_value = env_dict.get("WATSONX_SPACE_ID")
        if space_value:
            env_dict.setdefault("ASSISTANT_LLM_SPACE_ID", space_value)
            env_dict.setdefault("ASSISTANT_EMBEDDINGS_SPACE_ID", space_value)
            env_dict.setdefault("ROUTING_LLM_SPACE_ID", space_value)

    @staticmethod
    def __drop_auth_routes (env_dict: dict) -> dict:
        auth_url_key = "AUTHORIZATION_URL"
        env_dict_copy = env_dict.copy()

        auth_url = env_dict_copy.get(auth_url_key)
        if not auth_url:
            return env_dict_copy

        parsed_url = urlparse(auth_url)
        new_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        env_dict_copy[auth_url_key] = new_url

        return env_dict_copy

    @staticmethod
    def prepare_server_env_vars_minimal (user_env: dict = {}) -> dict:
        default_env = EnvService.read_env_file(EnvService.get_default_env_file())
        dev_edition_source = EnvService.get_dev_edition_source_core(user_env)
        default_registry_vars = EnvService.__get_default_registry_env_vars_by_dev_edition_source(default_env, user_env,
                                                                                                 source=dev_edition_source)

        # Update the default environment with the default registry variables only if they are not already set
        for key in default_registry_vars:
            if key not in default_env or not default_env[key]:
                default_env[key] = default_registry_vars[key]

        # Merge the default environment with the user environment
        merged_env_dict = {
            **default_env,
            **user_env,
        }

        return merged_env_dict

    @staticmethod
    def prepare_server_env_vars (user_env: dict = {}, should_drop_auth_routes: bool = False) -> dict:
        merged_env_dict = EnvService.prepare_server_env_vars_minimal(user_env)

        merged_env_dict = EnvService.__apply_server_env_dict_defaults(merged_env_dict)

        if should_drop_auth_routes:
            # NOTE: this is only needed in the case of co-pilot as of now.
            merged_env_dict = EnvService.__drop_auth_routes(merged_env_dict)

        # Auto-configure callback IP for async tools
        merged_env_dict = EnvService.auto_configure_callback_ip(merged_env_dict)

        EnvService.apply_llm_api_key_defaults(merged_env_dict)

        return merged_env_dict

    def define_saas_wdu_runtime (self, value: str = "none") -> None:
        self.__config.write(USER_ENV_CACHE_HEADER, "SAAS_WDU_RUNTIME", value)
