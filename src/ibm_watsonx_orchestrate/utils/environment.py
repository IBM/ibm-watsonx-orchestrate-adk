import importlib.resources as resources
import logging
import os
import platform
import subprocess
import sys
import tempfile
import requests
import time
from pathlib import Path
from typing import Tuple, OrderedDict, Any
from urllib.parse import urlparse
from enum import Enum

from dotenv import dotenv_values

from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType
from ibm_watsonx_orchestrate.cli.commands.server.types import DirectAIEnvConfig, ModelGatewayEnvConfig
from ibm_watsonx_orchestrate.cli.config import USER_ENV_CACHE_HEADER, Config
from ibm_watsonx_orchestrate.client.utils import is_arm_architecture, path_for_vm
from ibm_watsonx_orchestrate.utils.utils import parse_bool_safe, parse_int_safe, parse_string_safe, parse_bool_safe_and_get_raw_val
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

logger = logging.getLogger(__name__)

class DeveloperEditionSources(str, Enum):
    MYIBM = "myibm"
    ORCHESTRATE = "orchestrate"
    INTERNAL = "internal"
    CUSTOM = "custom"

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return self.value

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
        "WATSONX_URL",
        "WO_INSTANCE",
        "USE_SAAS_ML_TOOLS_RUNTIME",
        "AUTHORIZATION_URL",
        "OAUTH_REDIRECT_URL",
        "OPENSOURCE_REGISTRY_PROXY",
        "WDU_RUNTIME_SOURCE",
        "LATEST_ENV_FILE",
    }

    def __init__ (self, config: Config):
        self.__config = config

    def get_compose_file (self, ignore_cache: bool = False) -> Path:
        if not ignore_cache:
            cache_dir = Path.home() / ".cache" / "orchestrate"
            cache_dir.mkdir(parents=True, exist_ok=True)

            compose_file_cache_location = Path(path_for_vm(cache_dir / "docker-compose.yml"))

            if compose_file_cache_location.exists():
                return compose_file_cache_location

        custom_compose_path = self.__get_compose_file_path()
        return Path(custom_compose_path) if custom_compose_path else self.__get_default_compose_file()

    def __get_compose_file_path (self) -> str:
        return self.__config.read(USER_ENV_CACHE_HEADER, "DOCKER_COMPOSE_FILE_PATH")

    @staticmethod
    def __get_default_compose_file () -> Path:
        with resources.as_file(
                resources.files("ibm_watsonx_orchestrate.developer_edition.resources.docker").joinpath("compose-lite.yml")
        ) as compose_file:
            return compose_file
    
    @staticmethod
    def __set_if_not_in_user_env(key: str, value: Any, target_dict: dict, user_env: dict) -> None:
        if key not in user_env:
            target_dict[key] = value

    @staticmethod
    def get_default_env_file () -> Path:
        with resources.as_file(
                resources.files("ibm_watsonx_orchestrate.developer_edition.resources.docker").joinpath("default.env")
        ) as env_file:
            return env_file

    @staticmethod
    def read_env_file (env_path: Path | str) -> OrderedDict:
        return dotenv_values(env_path)

    def get_user_env (self, user_env_file: Path | str | None, fallback_to_persisted_env: bool = True) -> dict:
        if user_env_file is not None and isinstance(user_env_file, str):
            user_env_file = Path(user_env_file)

        user_env = self.read_env_file(user_env_file) if user_env_file is not None else {}

        if fallback_to_persisted_env is True and not user_env:
            user_env = self.__get_persisted_user_env() or {}

        return user_env


    @staticmethod
    def get_dev_edition_source_core(env_dict: dict | None) -> DeveloperEditionSources | str:
        if not env_dict:
            return DeveloperEditionSources.MYIBM

        source = env_dict.get("WO_DEVELOPER_EDITION_SOURCE")

        if source:
            return source
        if env_dict.get("WO_INSTANCE"):
            return DeveloperEditionSources.ORCHESTRATE
        return DeveloperEditionSources.MYIBM

    def get_dev_edition_source(self, user_env_file: str) -> DeveloperEditionSources | str:
        return self.get_dev_edition_source_core(self.get_user_env(user_env_file))

    @staticmethod
    def merge_env (default_env_path: Path, user_env_path: Path | None) -> dict:
        merged = dotenv_values(str(default_env_path))

        if user_env_path is not None:
            user_env = dotenv_values(str(user_env_path))
            merged.update(user_env)

        return merged

    @staticmethod
    def resolve_auth_type (env_dict: dict) -> str | None:
        auth_type = env_dict.get("WO_AUTH_TYPE")

        # Try infer the auth type if not provided
        if not auth_type:
            instance_url = env_dict.get("WO_INSTANCE")
            if instance_url:
                if ".cloud.ibm.com" in instance_url:
                    auth_type = EnvironmentAuthType.IBM_CLOUD_IAM.value
                elif ".ibm.com" in instance_url:
                    auth_type = EnvironmentAuthType.MCSP.value
                elif "https://cpd" in instance_url:
                    auth_type = EnvironmentAuthType.CPD.value

        return auth_type

    @staticmethod
    def __get_default_registry_env_vars_by_dev_edition_source (default_env: dict, user_env: dict, source: str) -> dict[str, str]:
        component_registry_var_names = {key for key in default_env if key.endswith("_REGISTRY")} | {'REGISTRY_URL'}

        registry_url = parse_string_safe(value=user_env.get("REGISTRY_URL", None), override_empty_to_none=True)
        user_env["HAS_USER_PROVIDED_REGISTRY_URL"] = registry_url is not None

        if not registry_url:
            if source == DeveloperEditionSources.INTERNAL:
                registry_url = "us.icr.io/watson-orchestrate-private"
            elif source == DeveloperEditionSources.MYIBM:
                registry_url = "cp.icr.io/cp/wxo-lite"
            elif source == DeveloperEditionSources.ORCHESTRATE:
                # extract the hostname from the WO_INSTANCE URL, and replace the "api." prefix with "registry." to construct the registry URL per region
                wo_url = user_env.get("WO_INSTANCE")

                if not wo_url:
                    raise ValueError(
                        "WO_INSTANCE is required in the environment file if the developer edition source is set to 'orchestrate'.")

                wo_auth_type = EnvService.resolve_auth_type(user_env)

                if wo_auth_type == EnvironmentAuthType.CPD.value:
                    registry_url = "cpd/cp/wxo-lite"

                else:
                    parsed = urlparse(wo_url)
                    hostname = parsed.hostname

                    registry_url = f"registry.{hostname[4:]}/cp/wxo-lite"
            elif source == DeveloperEditionSources.CUSTOM:
                registry_url = user_env.get("CUSTOM_REGISTRY_URL")
                if not registry_url:
                    raise ValueError(
                        f"REGISTRY_URL is required in the environment file when the developer edition source is set to 'custom'."
                    )
            else:
                raise ValueError(
                    f"Unknown value for developer edition source: {source}. Must be one of {list(map(str, DeveloperEditionSources))}."
                )
        
        # For non-custom use cases remove etcd and elastic search as they have different default registries
        if source != DeveloperEditionSources.CUSTOM:
            component_registry_var_names -= {"ETCD_REGISTRY", "ELASTICSEARCH_REGISTRY"}
        # In the custom case default the OPENSOURCE_REGISTRY_PROXY to also be the REGISTRY_URL
        else:
            component_registry_var_names.add("OPENSOURCE_REGISTRY_PROXY")
        
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
        target_file = None
        if target_path:
            target_file = target_path

        else:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as ntf:
                target_file = ntf.name

        with safe_open(target_file, "w") as file:
            for key, val in merged_env.items():
                file.write(f"{key}={val}\n")

        return Path(target_file)

    def persist_user_env (self, env: dict, include_secrets: bool = False, source: DeveloperEditionSources| str | None = None) -> None:
        if include_secrets:
            persistable_env = env
        else:
            persistable_env = {k: env[k] for k in EnvService.__NON_SECRET_ENV_ITEMS if k in env}
        
        if source == DeveloperEditionSources.CUSTOM and "REGISTRY_URL" in env:
            persistable_env["CUSTOM_REGISTRY_URL"] = env.get("REGISTRY_URL")

        persistable_env["LLM_HAS_GROQ_API_KEY"] = 'GROQ_API_KEY' in env
        persistable_env["LLM_HAS_WATSONX_APIKEY"] = 'WATSONX_APIKEY' in env
        persistable_env["LLM_HAS_WO_INSTANCE"] = 'WO_INSTANCE' in env and \
                                                 (env.get('WO_API_KEY', None) is not None or env.get('WATSONX_PASSWORD', None) is not None)


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
            use_model_proxy = bool(env_dict.get("WO_INSTANCE"))
            if not use_model_proxy:
                model_config = DirectAIEnvConfig.model_validate(env_dict)
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
    def apply_llm_api_key_defaults (env_dict: dict, user_dict: dict = {}) -> None:
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

        # configure default/preferred model properly based on availability of apikeys
        wo_instance = env_dict.get("WO_INSTANCE")
        groq_key = env_dict.get("GROQ_API_KEY")
        use_saas_ml_tools_runtime = bool(wo_instance)
        env_dict.setdefault("USE_SAAS_ML_TOOLS_RUNTIME", str(use_saas_ml_tools_runtime).lower())
        
        if wo_instance:
            # both wx.ai and groq supported
            pass
        elif llm_value and not groq_key:
            # wx.ai only
            EnvService.__set_if_not_in_user_env("PREFERRED_MODELS", "watsonx/meta-llama/llama-3-2-90b-vision-instruct,watsonx/meta-llama/llama-3-405b-instruct", env_dict, user_dict)
            EnvService.__set_if_not_in_user_env("DEFAULT_LLM_MODEL", "watsonx/meta-llama/llama-3-2-90b-vision-instruct", env_dict, user_dict)
            EnvService.__set_if_not_in_user_env("DEFAULT_FLOW_LLM_MODEL", "watsonx/meta-llama/llama-3-3-70b-instruct", env_dict, user_dict)
        elif not llm_value and groq_key:
            # groq only
            EnvService.__set_if_not_in_user_env("PREFERRED_MODELS", "groq/openai/gpt-oss-120b", env_dict, user_dict)
            EnvService.__set_if_not_in_user_env("DEFAULT_LLM_MODEL", "groq/openai/gpt-oss-120b", env_dict, user_dict)
            EnvService.__set_if_not_in_user_env("DEFAULT_FLOW_LLM_MODEL", "groq/openai/gpt-oss-120b", env_dict, user_dict)
        elif llm_value and groq_key:
            # wx.ai and groq
            pass
        else:
            raise RuntimeError("Please set at least one of `GROQ_API_KEY`, `WATSONX_APIKEY` or `WO_INSTANCE`")
    
    @staticmethod
    def _check_dev_edition_server_health(username: str, password: str) -> bool:
        url = "http://localhost:4321/api/v1/auth/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'username': username, 'password': password}
        try:
            response = requests.post(url, headers=headers, data=data)
            if 200 <= response.status_code < 300:
                return True
        except:
            pass
        return False

    @staticmethod
    def _wait_for_dev_edition_server_health_check(health_user, health_pass, timeout_seconds=120, interval_seconds=3):
        start_time = time.time()
        while time.time() - start_time <= timeout_seconds:
            try:
                res = EnvService._check_dev_edition_server_health(username=health_user, password=health_pass)
                if res:
                    return True
            except requests.RequestException as e:
                pass

            time.sleep(interval_seconds)
        return False


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

        EnvService.apply_llm_api_key_defaults(merged_env_dict, user_env)
        return merged_env_dict

    def define_saas_wdu_runtime (self, value: str = "none") -> None:
        self.__config.write(USER_ENV_CACHE_HEADER, "WDU_RUNTIME_SOURCE", value)

    @staticmethod
    def did_user_provide_registry_url (env_dict: dict) -> bool:
        has_user_provided_registry_url = parse_bool_safe(env_dict.get("HAS_USER_PROVIDED_REGISTRY_URL"), fallback=None)

        if has_user_provided_registry_url is None:
            raise Exception("Unable to determine if user has provided REGISTRY_URL.")

        return has_user_provided_registry_url


class EnvSettingsService:

    def __init__(self, env_file: Path | str) -> None:
        self.__env_dict = dotenv_values(str(env_file))
        self.__warns = {}

    def get_env(self) -> dict:
        return self.__env_dict

    def get_user_provided_docker_os_type(self) -> str | None:
        return parse_string_safe(value=self.__env_dict.get("DOCKER_IMAGE_OS_TYPE"), override_empty_to_none=True)

    def get_user_provided_docker_arch_type(self) -> str | None:
        return parse_string_safe(value=self.__env_dict.get("DOCKER_IMAGE_ARCH_TYPE"), override_empty_to_none=True)

    def get_wo_instance_url(self) -> str:
        return self.__env_dict["WO_INSTANCE"]

    def get_parsed_wo_instance_details(self) -> Tuple[str, str, str, str]:
        instance_url = self.get_wo_instance_url()
        parsed = urlparse(instance_url)
        route_parts = parsed.path.split("/")

        orchestrate_namespace = route_parts[2]      # this is usually "cpd-instance-1"
        wxo_tenant_id = route_parts[4]

        return parsed.scheme, parsed.netloc, orchestrate_namespace, wxo_tenant_id

    def get_wo_username(self) -> str:
        return self.__env_dict.get("WO_USERNAME")

    def get_wo_password(self) -> str:
        return self.__env_dict.get("WO_PASSWORD")

    def get_wo_api_key(self) -> str:
        return self.__env_dict.get("WO_API_KEY")

    def use_parallel_docker_image_layer_pulls(self) -> bool:
        parsed = parse_bool_safe(value=self.__env_dict.get("DOCKER_IMAGE_PULL_LAYERS_PARALLELISM"), fallback=True)
        if parsed is True and self.get_docker_pull_parallel_worker_count() < 2:
            self.__issue_warning(key=self.use_parallel_docker_image_layer_pulls.__name__,
                                 msg="DOCKER_IMAGE_PULL_LAYERS_PARALLELISM has been disabled due to DOCKER_IMAGE_PULL_PARALLEL_WORKERS_COUNT being less than 2.")

            return False

        return parsed

    def get_docker_pull_parallel_worker_count(self) -> int:
        fallback = 7
        min = 1
        max = 10

        parsed = parse_int_safe(value=self.__env_dict.get("DOCKER_IMAGE_PULL_PARALLEL_WORKERS_COUNT"),
                                fallback=fallback)

        if parsed < min:
            self.__issue_warning(key=self.get_docker_pull_parallel_worker_count.__name__,
                                 msg=f"DOCKER_IMAGE_PULL_PARALLEL_WORKERS_COUNT is less than minimum ({min}). Defaulting to {fallback}.")

            parsed = fallback

        elif parsed > max:
            self.__issue_warning(key=self.get_docker_pull_parallel_worker_count.__name__,
                                 msg=f"DOCKER_IMAGE_PULL_PARALLEL_WORKERS_COUNT is greater than allowed maximum ({max}). Falling back to maximuim.")

            parsed = max

        return parsed

    def use_ranged_requests_during_docker_pulls(self) -> bool:
        use_ranged_requests = parse_bool_safe(value=self.__env_dict.get("USE_RANGE_REQUESTS_IN_DOCKER_IMAGE_PULLS"), fallback=None)
        is_user_provided = True

        if use_ranged_requests is None:
            use_ranged_requests = True
            is_user_provided = False

        if not self.use_parallel_docker_image_layer_pulls() and use_ranged_requests is True:
            use_ranged_requests = False
            if is_user_provided:
                self.__issue_warning(key=self.use_ranged_requests_during_docker_pulls.__name__,
                                     msg="USE_RANGE_REQUESTS_IN_DOCKER_IMAGE_PULLS is not supported when DOCKER_IMAGE_PULL_LAYERS_PARALLELISM is enabled. Disabled USE_RANGE_REQUESTS_IN_DOCKER_IMAGE_PULLS.")

        return use_ranged_requests

    def get_wo_instance_ssl_verify(self) -> bool | str:
        ssl_verify, path = parse_bool_safe_and_get_raw_val(value=self.__env_dict.get("WO_VERIFY_SSL"), fallback=True)
        if ssl_verify is True and path is not None and isinstance(path, str):
            if not os.path.exists(path) or not os.path.isfile(path):
                logger.error(f"WO SSL verification certificate path not found or could not be accessed: {str(path)}")
                sys.exit(1)

            return str(path)

        return ssl_verify

    def ignore_docker_layer_caching(self) -> bool:
        return parse_bool_safe(value=self.__env_dict.get("IGNORE_DOCKER_LAYER_CACHING"), fallback=False)

    def __issue_warning(self, key: str, msg: str) -> None:
        if self.__warns.get(key) is None or self.__warns.get(key) is not True:
            logger.warn(msg)
            self.__warns[key] = True
