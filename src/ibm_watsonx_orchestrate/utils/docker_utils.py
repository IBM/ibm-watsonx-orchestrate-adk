import logging
import os
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import MutableMapping
from urllib.parse import urlparse

import requests
import typer

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.utils.environment import EnvService

logger = logging.getLogger(__name__)


class DockerUtils:

    @staticmethod
    def ensure_docker_installed () -> None:
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.error("Unable to find an installed docker")
            sys.exit(1)

    @staticmethod
    def check_exclusive_observability(langfuse_enabled: bool, ibm_tele_enabled: bool):
        if langfuse_enabled and ibm_tele_enabled:
            return False
        if langfuse_enabled and DockerUtils.__is_docker_container_running("docker-frontend-server-1"):
            return False
        if ibm_tele_enabled and DockerUtils.__is_docker_container_running("docker-langfuse-web-1"):
            return False
        return True

    @staticmethod
    def __is_docker_container_running(container_name):
        DockerUtils.ensure_docker_installed()
        command = ["docker",
                   "ps",
                   "-f",
                   f"name={container_name}"
                   ]
        result = subprocess.run(command, env=os.environ, capture_output=True)
        if container_name in str(result.stdout):
            return True
        return False


class DockerLoginService:

    def __init__(self, env_service: EnvService):
        self.__env_service = env_service

    def login_by_dev_edition_source(self, env_dict: dict) -> None:
        source = self.__env_service.get_dev_edition_source_core(env_dict=env_dict)

        if env_dict.get('WO_DEVELOPER_EDITION_SKIP_LOGIN', None) == 'true':
            logger.info('WO_DEVELOPER_EDITION_SKIP_LOGIN is set to true, skipping login.')
            logger.warning('If the developer edition images are not already pulled this call will fail without first setting WO_DEVELOPER_EDITION_SKIP_LOGIN=false')
        else:
            if not env_dict.get("REGISTRY_URL"):
                raise ValueError("REGISTRY_URL is not set.")
            registry_url = env_dict["REGISTRY_URL"].split("/")[0]
            if source == "internal":
                iam_api_key = env_dict.get("DOCKER_IAM_KEY")
                if not iam_api_key:
                    raise ValueError(
                        "DOCKER_IAM_KEY is required in the environment file if WO_DEVELOPER_EDITION_SOURCE is set to 'internal'.")
                self.__docker_login(iam_api_key, registry_url, "iamapikey")
            elif source == "myibm":
                wo_entitlement_key = env_dict.get("WO_ENTITLEMENT_KEY")
                if not wo_entitlement_key:
                    raise ValueError("WO_ENTITLEMENT_KEY is required in the environment file.")
                self.__docker_login(wo_entitlement_key, registry_url, "cp")
            elif source == "orchestrate":
                wo_auth_type = env_dict.get("WO_AUTH_TYPE")
                api_key, username = self.__get_docker_cred_by_wo_auth_type(auth_type=wo_auth_type, env_dict=env_dict)
                self.__docker_login(api_key, registry_url, username)

    @staticmethod
    def __docker_login(api_key: str, registry_url: str, username: str = "iamapikey") -> None:
        logger.info(f"Logging into Docker registry: {registry_url} ...")
        result = subprocess.run(
            ["docker", "login", "-u", username, "--password-stdin", registry_url],
            input=api_key.encode("utf-8"),
            capture_output=True,
        )
        if result.returncode != 0:
            logger.error(f"Error logging into Docker:\n{result.stderr.decode('utf-8')}")
            sys.exit(1)
        logger.info("Successfully logged in to Docker.")

    @staticmethod
    def __get_docker_cred_by_wo_auth_type(auth_type: str | None, env_dict: dict) -> tuple[str, str]:
        # Try infer the auth type if not provided
        if not auth_type:
            instance_url = env_dict.get("WO_INSTANCE")
            if instance_url:
                if ".cloud.ibm.com" in instance_url:
                    auth_type = "ibm_iam"
                elif ".ibm.com" in instance_url:
                    auth_type = "mcsp"
                elif "https://cpd" in instance_url:
                    auth_type = "cpd"

        if auth_type in {"mcsp", "ibm_iam"}:
            wo_api_key = env_dict.get("WO_API_KEY")
            if not wo_api_key:
                raise ValueError(
                    "WO_API_KEY is required in the environment file if the WO_AUTH_TYPE is set to 'mcsp' or 'ibm_iam'.")
            instance_url = env_dict.get("WO_INSTANCE")
            if not instance_url:
                raise ValueError(
                    "WO_INSTANCE is required in the environment file if the WO_AUTH_TYPE is set to 'mcsp' or 'ibm_iam'.")
            path = urlparse(instance_url).path
            if not path or '/' not in path:
                raise ValueError(
                    f"Invalid WO_INSTANCE URL: '{instance_url}'. It should contain the instance (tenant) id.")
            tenant_id = path.split('/')[-1]
            return wo_api_key, f"wxouser-{tenant_id}"
        elif auth_type == "cpd":
            wo_api_key = env_dict.get("WO_API_KEY")
            wo_password = env_dict.get("WO_PASSWORD")
            if not wo_api_key and not wo_password:
                raise ValueError(
                    "WO_API_KEY or WO_PASSWORD is required in the environment file if the WO_AUTH_TYPE is set to 'cpd'.")
            wo_username = env_dict.get("WO_USERNAME")
            if not wo_username:
                raise ValueError("WO_USERNAME is required in the environment file if the WO_AUTH_TYPE is set to 'cpd'.")
            return wo_api_key or wo_password, wo_username  # type: ignore[return-value]
        else:
            raise ValueError(
                f"Unknown value for WO_AUTH_TYPE: '{auth_type}'. Must be one of ['mcsp', 'ibm_iam', 'cpd'].")


class DockerComposeCore:

    def __init__(self, env_service: EnvService) -> None:
        self.__env_service = env_service

    def service_up (self, service_name: str, friendly_name: str, final_env_file: Path, compose_env: MutableMapping = None) -> subprocess.CompletedProcess[bytes]:
        base_command = self.__ensure_docker_compose_installed()
        compose_path = self.__env_service.get_compose_file()

        command = base_command + [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "up",
            service_name,
            "-d",
            "--remove-orphans"
        ]

        kwargs = {}
        if compose_env is not None:
            kwargs["env"] = compose_env

        logger.info(f"Starting docker-compose {friendly_name} service...")

        return subprocess.run(command, capture_output=False, **kwargs)

    def services_up(self, profiles: list[str], final_env_file: Path, supplementary_compose_args: list[str]) -> subprocess.CompletedProcess[bytes]:
        compose_path = self.__env_service.get_compose_file()
        command = self.__ensure_docker_compose_installed()[:]

        for profile in profiles:
            command += ["--profile", profile]

        compose_args = [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "up"
        ]

        for arg in supplementary_compose_args:
            compose_args.append(arg)

        compose_args.append("-d")
        compose_args.append("--remove-orphans")

        command += compose_args

        logger.info("Starting docker-compose services...")
        return subprocess.run(command, capture_output=False)

    def service_down (self, service_name: str, friendly_name: str, final_env_file: Path, is_reset: bool = False) -> subprocess.CompletedProcess[bytes]:
        base_command = self.__ensure_docker_compose_installed()
        compose_path = self.__env_service.get_compose_file()

        command = base_command + [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "down",
            service_name
        ]

        if is_reset:
            command.append("--volumes")
            logger.info(f"Stopping docker-compose {friendly_name} service and resetting volumes...")

        else:
            logger.info(f"Stopping docker-compose {friendly_name} service...")

        return subprocess.run(command, capture_output=False)

    def services_down (self, final_env_file: Path, is_reset: bool = False) -> subprocess.CompletedProcess[bytes]:
        base_command = self.__ensure_docker_compose_installed()
        compose_path = self.__env_service.get_compose_file()

        command = base_command + [
            "--profile", "*",
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "down"
        ]

        if is_reset:
            command.append("--volumes")
            logger.info("Stopping docker-compose service and resetting volumes...")

        else:
            logger.info("Stopping docker-compose services...")

        return subprocess.run(command, capture_output=False)

    def services_logs (self, final_env_file: Path, should_follow: bool = True) -> subprocess.CompletedProcess[bytes]:
        compose_path = self.__env_service.get_compose_file()

        command = [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "--profile", "*",
            "logs"
        ]

        if should_follow is True:
            command.append("--follow")

        command = self.__ensure_docker_compose_installed() + command

        logger.info("Docker Logs...")
        return subprocess.run(command, capture_output=False)

    def service_container_bash_exec (self, service_name: str, log_message: str, final_env_file: Path, bash_command: str) -> subprocess.CompletedProcess[bytes]:
        base_command = self.__ensure_docker_compose_installed()
        compose_path = self.__env_service.get_compose_file()

        command = base_command + [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "exec",
            service_name,
            "bash",
            "-c",
            bash_command
        ]

        logger.info(log_message)
        return subprocess.run(command, capture_output=False)

    @staticmethod
    def __ensure_docker_compose_installed() -> list:
        try:
            subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
            return ["docker", "compose"]
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        try:
            subprocess.run(["docker-compose", "version"], check=True, capture_output=True)
            return ["docker-compose"]
        except (FileNotFoundError, subprocess.CalledProcessError):
            # NOTE: ideally, typer should be a type that's injected into the constructor but is referenced directly for
            # the purposes of reporting some info to the user.
            typer.echo("Unable to find an installed docker-compose or docker compose")
            sys.exit(1)
