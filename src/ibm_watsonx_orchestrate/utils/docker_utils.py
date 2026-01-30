import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
from abc import abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import MutableMapping, Tuple
from urllib.parse import urlparse

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_manager import get_vm_manager
from ibm_watsonx_orchestrate.client.utils import get_os_type, path_for_vm

import requests
import typer
from requests import Response
from rich.progress import (
    BarColumn, Progress, TextColumn, TimeRemainingColumn, TaskProgressColumn, DownloadColumn
)

from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType
from ibm_watsonx_orchestrate.cli.config import AUTH_CONFIG_FILE_FOLDER
from ibm_watsonx_orchestrate.client.utils import get_architecture, concat_bin_files, is_arm_architecture, \
    get_arm_architectures
from ibm_watsonx_orchestrate.utils.environment import EnvSettingsService, EnvService, DeveloperEditionSources
from ibm_watsonx_orchestrate.utils.tokens import CpdWxOTokenService
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load, parse_string_safe, parse_int_safe


logger = logging.getLogger(__name__)
LIMA_VM_NAME = "ibm-watsonx-orchestrate"

class DockerOCIContainerMediaTypes(str, Enum):
    LIST_V1 = "application/vnd.oci.image.index.v1+json"
    LIST_V2 = "application/vnd.docker.distribution.manifest.list.v2+json"
    V1 = "application/vnd.oci.image.manifest.v1+json"
    V2 = "application/vnd.docker.distribution.manifest.v2+json"

    def __str__(self) -> str:
        return str(self.value)


class DockerUtils:

    @staticmethod
    def ensure_docker_installed() -> None:
        """
        Ensure that Docker is installed inside the active VM (Lima, WSL, or native).
        """
        vm = get_vm_manager()

        try:
            result = vm.run_docker_command(["--version"], capture_output=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, result.stdout, result.stderr
                )
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.error(f"Unable to find docker inside {vm.__class__.__name__}")
            sys.exit(1)


    @staticmethod
    def image_exists_locally (image: str, tag: str) -> bool: # this might have to be updated
        DockerUtils.ensure_docker_installed()

        result = subprocess.run([
            "docker",
            "images",
            "--format",
            "\"{{.Repository}}:{{.Tag}}\"",
            "--filter",
            f"reference={image}"
        ], env=os.environ, capture_output=True)

        return f"{image}:{tag}" in str(result.stdout)

    @staticmethod
    def check_exclusive_observability (langfuse_enabled: bool, ibm_tele_enabled: bool):
        if langfuse_enabled and ibm_tele_enabled:
            return False
        return True
    
    def import_image (tar_file_path: Path):
        DockerUtils.ensure_docker_installed()
        vm = get_vm_manager()

        if tar_file_path is None:
            raise ValueError("No image path provided. Cannot import docker image.")

        if not tar_file_path.exists() or not tar_file_path.is_file():
            raise ValueError(f"Provided path of tar file does not exist or could not be accessed. Cannot import docker image @ \"{tar_file_path}\".")

        try:
            # Copy the tar file to a staging cache directory
            staging_dir = Path.home() / ".cache" / "orchestrate"
            staging_dir.mkdir(parents=True, exist_ok=True)
            cached_tar_path = staging_dir / tar_file_path.name
            shutil.copy(tar_file_path, cached_tar_path)

            resolved_path = path_for_vm(cached_tar_path)


            if isinstance(resolved_path, Path):
                load_path = str(resolved_path.absolute())
            elif isinstance(resolved_path, str):
                load_path = resolved_path
            else:
                raise TypeError(f"Unsupported type for resolved_path: {type(resolved_path)}")

            result = vm.run_docker_command(
                ["load", "-i", load_path],
                capture_output=True
            )


            logger.info(result.stdout if hasattr(result, "stdout") else "Docker image imported successfully")

        except subprocess.CalledProcessError as ex:
            logger.error(f"Failed to import docker image. Return Code: {ex.returncode}")

            if ex.output:
                logger.debug(f"Command output: {ex.output.decode()}")

            if ex.stderr:
                logger.debug(f"Command error output: {ex.stderr.decode()}")

            sys.exit(1)

    @staticmethod
    def is_docker_container_running (container_name):
        DockerUtils.ensure_docker_installed()

        vm = get_vm_manager()

        result = vm.run_docker_command(["ps", "-f", f"name={container_name}"], capture_output=True)
        if result and result.stdout:
            return container_name in result.stdout
        return False


class CpdDockerPullProgressNotifier:

    @abstractmethod
    def initialize (self):
        raise NotImplementedError()

    @abstractmethod
    def progress (self, chunk_size: int):
        raise NotImplementedError()

    @abstractmethod
    def completed (self):
        raise NotImplementedError()

    @abstractmethod
    def failed(self):
        raise NotImplementedError()

    @abstractmethod
    def is_initialized (self) -> bool:
        raise NotImplementedError()


class CpdRichProgress(Progress):

    def get_default_columns(self):
        return (
            TextColumn("[#32afff][progress.description]{task.description}"),
            TaskProgressColumn(text_format="[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(complete_style="#32afff", finished_style="#366d1b"),
            DownloadColumn(binary_units=False),
            TimeRemainingColumn(compact=True, elapsed_when_finished=True),
            TextColumn("[red]{task.fields[status]}"),
        )

    @staticmethod
    def get_instance ():
        return CpdRichProgress(
            transient=False,
            auto_refresh=True,
            refresh_per_second=5,
        )


class SimpleRichCpdDockerPullProgressNotifier(CpdDockerPullProgressNotifier):

    def __init__ (self, layer_descriptor: str, layer_bytes: int, progress: CpdRichProgress):
        self.__progress = progress
        self.__layer_descriptor = layer_descriptor
        self.__layer_bytes = layer_bytes

        self.__lock = threading.Lock()
        self.__task = None

    def initialize (self):
        with self.__lock:
            self.__task = self.__progress.add_task(self.__layer_descriptor, total=self.__layer_bytes, visible=True, status="")
            self.__progress.update(self.__task, completed=0)

    def progress (self, chunk_size: int):
        with self.__lock:
            self.__progress.update(self.__task, advance=chunk_size)

    def completed (self):
        with self.__lock:
            if not self.__progress.tasks[self.__task].finished:
                self.__progress.update(self.__task, completed=self.__layer_bytes, visible=True)

    def failed (self):
        with self.__lock:
            if not self.__progress.tasks[self.__task].finished:
                self.__progress.update(self.__task, status="[ Failed ]")

    def is_initialized (self) -> bool:
        with self.__lock:
            return self.__task is not None


class CpdDockerRequestsService:

    def __init__ (self, env_settings: EnvSettingsService, cpd_wxo_token_service: CpdWxOTokenService) -> None:
        self.__cpd_wxo_token_service = cpd_wxo_token_service
        url_scheme, hostname, orchestrate_namespace, wxo_tenant_id = env_settings.get_parsed_wo_instance_details()
        self.__wxo_tenant_id = wxo_tenant_id

        self.__ssl_verify = env_settings.get_wo_instance_ssl_verify()

        self.__cpd_docker_url = f"{url_scheme}://{hostname}/orchestrate/{orchestrate_namespace}/docker"
        # self.__cpd_docker_url = f"{url_scheme}://{hostname}""

    def is_docker_proxy_up(self):
        url = f"{self.__cpd_docker_url}/health"
        headers = {
            **self.__get_base_request_headers(),
            "Accept": "application/json",
        }

        response = None

        try:
            response = requests.get(url, headers=headers, verify=self.__ssl_verify)

            if response.status_code != 200:
                self.__dump_response_content(response)
                logger.error(f"Received non-200 response from upstream CPD Docker service. Received: {response.status_code}{self.__get_log_request_id(response)}")
                return False

            if response.json()["status"] != "OK":
                logger.error(f"Upstream CPD Docker service responded with non-OK status. Received: {response.json()['status']}{self.__get_log_request_id(response)}")
                return False

        except (json.decoder.JSONDecodeError, KeyError):
            self.__dump_response_content(response)
            logger.error(f"Received unrecognized or unparsable response from upstream CPD Docker service{self.__get_log_request_id(response)}")
            return False

        except Exception as ex:
            logger.error(ex)
            logger.error("Failed to reach upstream CPD Docker service.")
            return False

        return True

    def get_manifests(self, image: str, tag: str,
                      manifest_media_type: str = DockerOCIContainerMediaTypes.LIST_V2.value) -> list:
        url = f"{self.__cpd_docker_url}/v2/{image}/manifests/{tag}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": manifest_media_type,
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code == 404:
            if manifest_media_type == DockerOCIContainerMediaTypes.LIST_V2.value:
                return self.get_manifests(image=image, tag=tag, manifest_media_type=DockerOCIContainerMediaTypes.LIST_V1.value)

            else:
                logger.error(f"Could not find OCI manifest list for image {image}:{tag}")
                logger.error("Image may not exist in docker registry.")
                sys.exit(1)

        if response.status_code != 200:
            self.__dump_response_content(response)
            raise Exception(f"Received unexpected, non-200 response while trying to retrieve manifests for image {image}:{tag}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        try:
            resp_json = response.json()

        except json.decoder.JSONDecodeError:
            raise Exception(f"Failed to parse JSON from cloud registry response while trying to fetch manifests for image {image}:{tag}.{self.__get_log_request_id(response)}")

        if "manifests" not in resp_json:
            raise Exception(
                f"Received unrecognized response from cloud registry while retrieving manifests for image {image}:{tag}.{self.__get_log_request_id(response)}")

        elif len(resp_json["manifests"]) < 1:
            raise Exception(f"Retrieved manifests list is empty for image {image}:{tag}.")

        return resp_json["manifests"]

    def get_manifest_for_digest (self, image: str, digest: str, media_type: str):
        url = f"{self.__cpd_docker_url}/v2/{image}/manifests/{digest}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code == 404:
            raise Exception(f"Could not find manifest for image {image}@{digest}.")

        if response.status_code != 200:
            self.__dump_response_content(response)
            raise Exception(f"Received unexpected, non-200 response while trying to retrieve manifest for image {image}@{digest}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        try:
            resp_json = response.json()

        except json.decoder.JSONDecodeError:
            raise Exception(f"Failed to parse JSON from cloud registry response while trying to fetch manifest for image {image}@{digest}.{self.__get_log_request_id(response)}")

        return resp_json

    def get_manifest (self, image: str, tag: str, media_type: str):
        url = f"{self.__cpd_docker_url}/v2/{image}/manifests/{tag}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code == 404:
            raise Exception(f"Could not find manifest for image {image}:{tag}.")

        if response.status_code != 200:
            self.__dump_response_content(response)
            raise Exception(f"Received unexpected, non-200 response while trying to retrieve manifest for image {image}:{tag}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        try:
            resp_json = response.json()

        except json.decoder.JSONDecodeError:
            raise Exception(f"Failed to parse JSON from cloud registry response while trying to fetch manifest for image {image}:{tag}.{self.__get_log_request_id(response)}")

        return {
            "manifest" : resp_json,
            "digest" : response.headers.get("docker-content-digest")
        }

    def get_head_digest (self, image: str, tag: str, media_type: str) -> str | None:
        url = f"{self.__cpd_docker_url}/v2/{image}/manifests/{tag}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        response = requests.head(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code >= 500:
            self.__dump_response_content(response)
            raise Exception(f"Failed to retrieve HEAD digest for image {image}:{tag}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        elif response.status_code == 200:
            return response.headers.get("docker-content-digest")

        else:
            return None

    def get_manifest_list_or_manifest(self, image: str, tag: str) -> Tuple[list[dict] | None, dict | None, str | None]:
        url = f"{self.__cpd_docker_url}/v2/{image}/manifests/{tag}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": ", ".join([
                DockerOCIContainerMediaTypes.LIST_V2.value,
                DockerOCIContainerMediaTypes.LIST_V1.value,
                DockerOCIContainerMediaTypes.V2.value
            ]),
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code == 404:
            logger.error(f"Could not find OCI manifest(s) for image {image}:{tag}. Received: {response.status_code}{self.__get_log_request_id(response)}")
            logger.error("Image may not exist in docker registry.")
            sys.exit(1)

        elif response.status_code != 200:
            self.__dump_response_content(response)
            raise Exception(f"Failed to retrieve manifest list or manifest digest for image {image}:{tag}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        content_type = parse_string_safe(value=response.headers.get("content-type"), override_empty_to_none=True)
        is_manifest_list = False
        digest = None

        if content_type is None:
            logger.error(f"Received a response from cloud registry which does not include content type response header{self.__get_log_request_id(response)}")
            sys.exist(1)

        elif content_type in (DockerOCIContainerMediaTypes.LIST_V2.value, DockerOCIContainerMediaTypes.LIST_V1.value):
            is_manifest_list = True

        elif content_type != DockerOCIContainerMediaTypes.V2.value:
            logger.error(f"Received a response from cloud registry with an unexpected content type: {content_type}{self.__get_log_request_id(response)}")
            sys.exit(1)

        else:
            digest = parse_string_safe(value=response.headers.get("docker-content-digest"), override_empty_to_none=True)

            if digest is None:
                raise Exception(f"Received an unexpected manfiest response from cloud registry which is missing docker content digest header{self.__get_log_request_id(response)}")

        try:
            resp_json = response.json()

        except json.decoder.JSONDecodeError:
            raise Exception(f"Failed to parse JSON from cloud registry response while trying to fetch manifest(s) for image {image}:{tag}.{self.__get_log_request_id(response)}")

        if is_manifest_list:
            if "manifests" not in resp_json:
                raise Exception(f"Received unrecognized manifest list response from cloud registry for image {image}:{tag}.{self.__get_log_request_id(response)}")

            elif len(resp_json["manifests"]) < 1:
                raise Exception(f"Retrieved manifests list is empty for image {image}:{tag}.")

            return resp_json["manifests"], None, digest

        else:
            return None, resp_json, digest

    def get_config_blob (self, image: str, config_digest: str, media_type: str):
        url = f"{self.__cpd_docker_url}/v2/{image}/blobs/{config_digest}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify)

        if response.status_code != 200:
            self.__dump_response_content(response)
            raise Exception(f"Received unexpected, non-200 response while trying to retrieve config blob (digest: {config_digest}) for image {image}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        return response.content

    def get_streaming_blob_response (self, image: str, blob_digest: str, media_type: str, layer: dict, byte_range: dict = None):
        url = f"{self.__cpd_docker_url}/v2/{image}/blobs/{blob_digest}"
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        if byte_range is not None and "start" in byte_range and "end" in byte_range:
            headers["Range"] = f"bytes={byte_range['start']}-{byte_range['end']}"

        response = requests.get(url, headers=headers, verify=self.__ssl_verify, stream=True)

        if response.status_code not in (200, 206):
            if "urls" in layer:
                return self.__get_streaming_layer_blob_url_response(url=layer["urls"][0], image=image, blob_digest=blob_digest, media_type=media_type)

            else:
                raise Exception(f"Failed to download layer {blob_digest}. Received unexpected, non-200 response for image {image}. Received: {response.status_code}{self.__get_log_request_id(response)}")

        return response

    def __get_streaming_layer_blob_url_response(self, url: str, image: str, blob_digest: str, media_type: str):
        headers = {
            **self.__get_base_request_headers(image),
            "Accept": media_type,
        }

        response = requests.get(url, headers=headers, verify=self.__ssl_verify, stream=True)

        if response.status_code != 200:
            raise Exception(f"Failed to download layer {blob_digest}. Received unexpected, non-200 response for image {image}. Received: {response.status_code}, Custom URL: \"{url}\"{self.__get_log_request_id(response)}")

        return response

    def __get_base_request_headers (self, image: str = None):
        return {
            "Authorization" : f"Bearer {self.__cpd_wxo_token_service.get_token()}",
            "X-Tenant-ID" : self.__wxo_tenant_id,
            **({ "scope" : f"repository:{image}:pull" } if image else {}),
            **({ "Accept-Encoding" : "gzip" } if image else {}),
        }

    @staticmethod
    def __get_log_request_id (response: Response, ignore_comma_prefix: bool = False) -> str:
        id = "<unknown>"

        if response is not None and response.headers.get("X-Service-Request-ID"):
            id = response.headers.get("X-Service-Request-ID")

        result = f"{'' if ignore_comma_prefix else ', '}Request ID: {id}"

        if response is not None and response.headers.get("IBM-CPD-Transaction-ID"):
            result += f", CPD Transaction ID: {response.headers.get('IBM-CPD-Transaction-ID')}"

        return result

    @staticmethod
    def __dump_response_content(response: Response) -> None:
        if isinstance(response.content, bytes):
            logger.debug(f"Server response: {response.content.decode(response.encoding)}")


class WoDockerBlobCacheService:

    def __init__(self, env_settings: EnvSettingsService):
        self.__ignore_docker_layer_caching = env_settings.ignore_docker_layer_caching()

    def blob_exists(self, blob_digest: str) -> bool:
        if self.__ignore_docker_layer_caching:
            return False

        with threading.Lock():
            bin_path = self.__get_layer_bin_path(blob_digest)
            json_path = self.__get_layer_json_path(blob_digest)

            return bin_path.exists() and bin_path.is_file() and json_path.exists() and json_path.is_file()

    def clear_blob_cache(self, blob_digest: str) -> None:
        with threading.Lock():
            layer_folder = self.__get_layer_folder(blob_digest)

            if layer_folder.exists() and layer_folder.is_dir():
                shutil.rmtree(str(layer_folder))

    def clear_cache(self) -> bool:
        with threading.Lock():
            layers_path = self.__get_layer_folders()
            if layers_path.exists():
                shutil.rmtree(layers_path)
                return True

            return False

    def cache_blob(self, blob_digest: str, layer_json: dict, blob_bin_path: Path, chunk_size: int) -> None:
        if self.__ignore_docker_layer_caching:
            return

        self.clear_blob_cache(blob_digest)

        with threading.Lock():
            layer_folder = self.__get_layer_folder(blob_digest)
            if not layer_folder.exists() or not layer_folder.is_dir():
                os.makedirs(layer_folder)

            with open(str(self.__get_layer_json_path(blob_digest)), "w") as f:
                json.dump(layer_json, f, indent=4)

            with open(blob_bin_path, "rb") as source:
                with open(str(self.__get_layer_bin_path(blob_digest)), "wb") as target:
                    while True:
                        chunk = source.read(chunk_size)

                        if chunk:
                            target.write(chunk)

                        else:
                            break

    def deploy_blob(self, blob_digest: str, target_path: Path, chunk_size: int,
                    fn_report_progress: Callable[[int], bool]) -> None:
        if self.__ignore_docker_layer_caching:
            return

        with threading.Lock():
            with open(str(self.__get_layer_bin_path(blob_digest)), "rb") as source:
                with open(str(target_path), "wb") as target:
                    while True:
                        chunk = source.read(chunk_size)

                        if chunk:
                            target.write(chunk)
                            if fn_report_progress is not None and fn_report_progress(len(chunk)) is True:
                                break

                        else:
                            break

    def get_blob_digests(self) -> list[str]:
        layers_dir = self.__get_layer_folders()
        digests = []

        if layers_dir.exists() and layers_dir.is_dir():
            for hash_scheme in os.listdir(layers_dir):
                hash_scheme_dir: Path = layers_dir.joinpath(hash_scheme)
                if hash_scheme_dir.is_dir():
                    for hash in os.listdir(hash_scheme_dir):
                        if hash_scheme_dir.joinpath(hash).is_dir():
                            digests.append(f"{hash_scheme}:{hash}")

        return digests

    def __get_layer_bin_path(self, blob_digest:str) -> Path:
        return Path(os.path.join(self.__get_layer_folder(blob_digest), "layer.bin"))

    def __get_layer_json_path(self, blob_digest:str) -> Path:
        return Path(os.path.join(self.__get_layer_folder(blob_digest), "layer.json"))

    def __get_layer_folder(self, blob_digest:str) -> Path:
        return Path(os.path.join(self.__get_layer_folders(), *blob_digest.split(":")))

    def __get_layer_folders(self) -> Path:
        return Path(os.path.join(AUTH_CONFIG_FILE_FOLDER, "layers"))


class DockerImageBlobRetrieverService:

    __1_mb = 1024 * 1024
    __10_mb = 10 * __1_mb
    __20_mb = 20 * __1_mb
    __50_mb = 50 * __1_mb
    __100_mb = 100 * __1_mb
    __150_mb = 150 * __1_mb
    __200_mb = 2 * __100_mb
    __500_mb = 500 * __1_mb
    __1_gb = 1024 * __1_mb

    def __init__(self, env_settings: EnvSettingsService, docker_requests_service: CpdDockerRequestsService,
                 blob_cache: WoDockerBlobCacheService) -> None:
        self.__docker_requests_service = docker_requests_service
        self.__blob_cache = blob_cache
        self.__queued_tasks = []
        self.__use_ranged_requests = env_settings.use_ranged_requests_during_docker_pulls()
        self.__use_parallel_docker_image_pulls = env_settings.use_parallel_docker_image_layer_pulls()

    def clear_queue(self) -> None:
        # this does not have be thread safe because, by design, it's called on the main thread before and after threads
        # start and stop.
        self.__queued_tasks = []

    def retrieve(self, image: str, layer: dict, layer_digest: str, media_type: str, layer_gzip_tar_file_path: str,
                 progress_instance: CpdRichProgress) -> None:
        if self.__use_parallel_docker_image_pulls is True:
            # progress_notifier, cancel_event and blob_chunk_size need to be set.
            self.__queued_tasks.append({
                "image": image,
                "layer": layer,
                "layer_digest": layer_digest,
                "media_type": media_type,
                "layer_gzip_tar_file_path": layer_gzip_tar_file_path,
            })

        else:
            layer_bytes = int(layer["size"])
            progress_notifier = SimpleRichCpdDockerPullProgressNotifier(layer_descriptor=layer["layer_descriptor"],
                                                                        layer_bytes=layer_bytes,
                                                                        progress=progress_instance)

            self.__retrieve(image=image, layer=layer, layer_digest=layer_digest, media_type=media_type, cancel_event=None,
                            layer_gzip_tar_file_path=layer_gzip_tar_file_path, progress_notifier=progress_notifier,
                            blob_chunk_size=self.__get_blob_chunk_size(layer_bytes), byte_range=None)

    def retrieve_queued_blobs(self, executor: ThreadPoolExecutor, progress_instance: CpdRichProgress) -> None:
        if len(self.__queued_tasks) < 1:
            return

        try:
            ranged_subtasks = {}
            all_subtasks = []
            for pull_task in self.__queued_tasks:
                subtasks = self.__get_ranged_pull_subtasks(pull_task)

                if len(subtasks) > 0:
                    pull_task["file_parts"] = [x["layer_gzip_tar_file_path"] for x in subtasks]
                    all_subtasks.extend(subtasks)
                    ranged_subtasks[pull_task["layer"]["layer_descriptor"]] = pull_task

                else:
                    all_subtasks.append(pull_task)

            self.__retrieve_blobs_parallelly(all_subtasks=all_subtasks, executor=executor,
                                             progress_instance=progress_instance, ranged_subtasks=ranged_subtasks)

            # extract any ranged pull file parts.
            msg_logged = False
            for layer_descriptor, ranged_subtask in ranged_subtasks.items():
                if not msg_logged:
                    logger.debug("Extracting layers")
                    msg_logged = True

                try:
                    concat_bin_files(target_bin_file=ranged_subtask["layer_gzip_tar_file_path"],
                                     source_files=ranged_subtask["file_parts"], read_chunk_size=self.__200_mb,
                                     delete_source_files_post=True)

                except Exception as ex:
                    logger.error(f"Failed to extract layer: {layer_descriptor}")
                    raise ex

                try:
                    self.__blob_cache.cache_blob(blob_digest=ranged_subtask["layer_digest"],
                                                 layer_json=ranged_subtask["layer"],
                                                 blob_bin_path=ranged_subtask["layer_gzip_tar_file_path"],
                                                 chunk_size=self.__50_mb)

                except Exception as ex:
                    logger.error(f"Failed to cache layer: {layer_descriptor}")
                    raise ex

        finally:
            self.clear_queue()

    def __retrieve_blobs_parallelly(self, all_subtasks: list[dict], executor: ThreadPoolExecutor,
                                    progress_instance: CpdRichProgress, ranged_subtasks: dict) -> None:
        progress_notifiers = {}
        cancel_event = threading.Event()
        futures = []
        has_failed = False

        try:
            for subtask in all_subtasks:
                name = subtask["layer"]["layer_descriptor"]
                subtask_layer_bytes = subtask["layer"]["size"]
                progress_notifier = None

                if name in progress_notifiers.keys():
                    progress_notifier = progress_notifiers[name]

                else:
                    layer_bytes = ranged_subtasks[name]["layer"]["size"] \
                        if name in ranged_subtasks.keys() \
                        else subtask_layer_bytes

                    progress_notifier = SimpleRichCpdDockerPullProgressNotifier(layer_descriptor=name,
                                                                                layer_bytes=layer_bytes,
                                                                                progress=progress_instance)

                    progress_notifiers[name] = progress_notifier

                blob_chunk_size = self.__get_blob_chunk_size(subtask_layer_bytes)
                future = executor.submit(self.__retrieve, **subtask, cancel_event=cancel_event,
                                         progress_notifier=progress_notifier, blob_chunk_size=blob_chunk_size)

                future.layer_name = name
                futures.append(future)

            done, not_done = wait(futures, return_when=FIRST_EXCEPTION)
            failed_futures = [x for x in done if x.exception() is not None]
            progress_instance.stop()
            if len(failed_futures) > 0:
                has_failed = True
                executor.shutdown(wait=False, cancel_futures=True)

                for pull_task in failed_futures:
                    logger.error(f"{pull_task.layer_name}: {pull_task.exception()}")

        except Exception as ex:
            has_failed = True
            if len(futures) > 0:
                cancel_event.set()
                executor.shutdown(wait=False, cancel_futures=True)
                progress_instance.stop()

            logger.error(ex)
            logger.error(f"Failed to spawn layer pulls. Cancelling operation.")

        finally:
            if has_failed:
                logger.error("CPD Docker image pull failed. Please try again.")
                sys.exit(1)

    def __get_ranged_pull_subtasks(self, pull_task: dict) -> list:
        if (
                not self.__use_ranged_requests or
                self.__blob_cache.blob_exists(pull_task["layer_digest"])
        ):
            return []

        layer_bytes = int(pull_task["layer"]["size"])

        if layer_bytes < self.__200_mb:
            return []

        start_index = 0
        end_index = layer_bytes - 1
        range_end_index = 0
        counter = 0

        subtasks = []

        while True:
            range_end_index = start_index + self.__150_mb

            if range_end_index > end_index:
                range_end_index = end_index

            ranged_subtask = deepcopy(pull_task)
            ranged_subtask["byte_range"] = {
                "start": start_index,
                "end": range_end_index
            }

            ranged_subtask["layer"]["layer_gzip_tar_file_path"] = ranged_subtask["layer_gzip_tar_file_path"]
            ranged_subtask["layer_gzip_tar_file_path"] = str(os.path.join(os.path.dirname(ranged_subtask["layer_gzip_tar_file_path"]), f"part-{counter}.bin"))
            ranged_subtask["layer"]["size"] = range_end_index - start_index + 1

            counter += 1

            subtasks.append(ranged_subtask)

            start_index = range_end_index + 1

            if range_end_index >= end_index:
                break

        return subtasks

    @staticmethod
    def __cached_blob_deploy_progress(chunk_size: int, cancel_event: threading.Event,
                                      progress_notifier: CpdDockerPullProgressNotifier) -> bool:
        progress_notifier.progress(chunk_size=chunk_size)
        return cancel_event is not None and cancel_event.is_set()

    def __retrieve(self, image: str, layer: dict, layer_digest: str, media_type: str, layer_gzip_tar_file_path: str,
                   blob_chunk_size: int, progress_notifier: CpdDockerPullProgressNotifier, byte_range: dict = None,
                   cancel_event: threading.Event | None = None) -> None:
        try:
            is_ranged_pull = byte_range is not None and "start" in byte_range and "end" in byte_range
            if not is_ranged_pull or not progress_notifier.is_initialized():
                # if this is a ranged request, the progress bar task might already have been initialized. hence, we only
                # initialize when needed.
                progress_notifier.initialize()

            if self.__blob_cache.blob_exists(layer_digest) is True:
                if is_ranged_pull is True:
                    # this should not happen but it's here as a sanity check.
                    raise Exception("System attempting to retrieve layer when it should be deployed from cache")

                self.__blob_cache.deploy_blob(
                    blob_digest=layer_digest, target_path=Path(layer_gzip_tar_file_path), chunk_size=self.__50_mb,
                    fn_report_progress= lambda csize: self.__cached_blob_deploy_progress(
                        chunk_size=csize, cancel_event=cancel_event, progress_notifier=progress_notifier
                    )
                )

            else:
                streaming_layer_resp = self.__docker_requests_service.get_streaming_blob_response(
                    image=image, blob_digest=layer_digest, media_type=media_type, layer=layer, byte_range=byte_range
                )

                streaming_layer_resp.raise_for_status()

                with open(layer_gzip_tar_file_path, "wb") as file:
                    for chunk in streaming_layer_resp.iter_content(chunk_size=blob_chunk_size):
                        if cancel_event is not None and cancel_event.is_set():
                            return

                        if chunk:
                            file.write(chunk)
                            progress_notifier.progress(chunk_size=len(chunk))

                if not is_ranged_pull:
                    self.__blob_cache.cache_blob(blob_digest=layer_digest, layer_json=layer,
                                                 blob_bin_path=Path(layer_gzip_tar_file_path), chunk_size=self.__50_mb)

            if not is_ranged_pull:
                # we do not want to set the notifier to completed when servicing ranged requests. ranged requests are
                # executed in parallel and hence will complete when parallelly executing ranged requests complete.
                progress_notifier.completed()

        except Exception as ex:
            if progress_notifier is not None:
                progress_notifier.failed()

            if cancel_event is not None:
                cancel_event.set()

            raise ex

    def __get_blob_chunk_size(self, layer_bytes: int):
        if layer_bytes >= self.__1_gb:
            return self.__100_mb

        elif layer_bytes >= self.__500_mb:
            return self.__50_mb

        elif layer_bytes >= self.__200_mb:
            return self.__20_mb

        elif layer_bytes >= self.__100_mb:
            return self.__10_mb

        else:
            return self.__1_mb


class BaseCpdDockerImagePullService:

    @abstractmethod
    def pull(self, image: str, tag: str, manifest: dict, local_image_name: str) -> None:
        raise NotImplementedError()


class CpdDockerV1ImagePullService(BaseCpdDockerImagePullService):

    def __init__ (self, docker_requests_service: CpdDockerRequestsService) -> None:
        self.__docker_requests_service = docker_requests_service

    def pull(self, image: str, tag: str, manifest: dict, local_image_name: str) -> None:
        raise NotImplementedError()


class CpdDockerV2ImagePullService(BaseCpdDockerImagePullService):

    def __init__ (self, env_settings: EnvSettingsService, docker_requests_service: CpdDockerRequestsService,
                  blob_retriever: DockerImageBlobRetrieverService) -> None:
        self.__docker_requests_service = docker_requests_service
        self.__blob_retriever = blob_retriever
        self.__pull_worker_count = env_settings.get_docker_pull_parallel_worker_count()

    def pull(self, image: str, tag: str, manifest: dict, local_image_name: str) -> None:
        final_image_tar = None

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, prefix="rendered-image-") as ntf:
                final_image_tar = ntf.name

            with tempfile.TemporaryDirectory() as image_structure_dir:
                with ThreadPoolExecutor(max_workers=self.__pull_worker_count) as executor:
                    self.__pull_and_construct_image_archive(executor=executor, final_image_tar=final_image_tar,
                                                            image=image, image_structure_dir=image_structure_dir,
                                                            manifest=manifest, tag=tag,
                                                            local_image_name=local_image_name)

            logger.debug("Importing docker image")
            DockerUtils.import_image(Path(final_image_tar))

        finally:
            if final_image_tar is not None:
                os.unlink(final_image_tar)

    def __pull_and_construct_image_archive(self, executor: ThreadPoolExecutor, final_image_tar: str, image: str,
                                           image_structure_dir: str, manifest: dict, tag: str, local_image_name: str) -> None:
        media_type = manifest['mediaType']
        config_digest = manifest["config"]["digest"]
        config_blob_file_path = os.path.join(image_structure_dir, f"{config_digest[7:]}.json")

        with open(config_blob_file_path, 'wb') as file:
            file.write(self.__docker_requests_service.get_config_blob(image, config_digest, media_type))

        content = [{
            "Config": f"{config_digest[7:]}.json",
            "RepoTags": [
                f"{local_image_name}:{tag}"
            ],
            "Layers": []
        }]

        with CpdRichProgress.get_instance() as progress_instance:
            computed_layer_id = self.__retrieve_layers(config_blob_file_path=config_blob_file_path, content=content,
                                                       executor=executor, image=image,
                                                       image_structure_dir=image_structure_dir, manifest=manifest,
                                                       media_type=media_type, progress_instance=progress_instance)

        logger.debug("Retrieved layers")

        with open(os.path.join(image_structure_dir, 'manifest.json'), 'w') as file:
            file.write(json.dumps(content))

        with open(os.path.join(image_structure_dir, "repositories"), "w") as repo_file:
            repo_file.write(json.dumps({
                f"{local_image_name}": {
                    "tag": computed_layer_id,
                }
            }))

        logger.debug("Compressing archive")
        with tarfile.open(final_image_tar, mode="w") as tar:
            tar.add(image_structure_dir, arcname=os.path.sep)

    def __retrieve_layers(self, config_blob_file_path: str, content: list, executor: ThreadPoolExecutor, image: str,
                          image_structure_dir: str, manifest: dict, media_type: str,
                          progress_instance: CpdRichProgress) -> str:
        parent_id = ""
        last_layer_digest = manifest["layers"][-1]['digest']
        layer_count = len(manifest["layers"])
        computed_layer_id = None

        if len(manifest["layers"]) < 1:
            # this should never happen but is here as a sanity check.
            raise Exception("Encountered a docker manifest without any layers")

        self.__blob_retriever.clear_queue()

        for layer_index, layer in enumerate(manifest["layers"]):
            layer_track = f"{str(layer_index + 1).zfill(len(str(layer_count)))} / {layer_count}"
            layer_digest = layer["digest"]
            layer_descriptor = f"{layer['digest'][7:20]} [ {layer_track} ]"
            layer["layer_descriptor"] = layer_descriptor

            if "size" not in layer:
                # the size should typically be there. this is just a sanity check.
                raise Exception(f"Encountered a docker manifest layer which is missing \"size\". Layer digest: {layer_digest}")

            computed_layer_id = hashlib.sha256(f"{parent_id}\n{layer_digest}\n".encode('utf-8')).hexdigest()

            layer_dir_path = os.path.join(image_structure_dir, computed_layer_id)
            os.mkdir(layer_dir_path)

            # Creating VERSION file
            with open(os.path.join(layer_dir_path, 'VERSION'), 'w') as file:
                file.write('1.0')

            layer_gzip_tar_file_path = os.path.join(layer_dir_path, "layer_gzip.tar")

            self.__blob_retriever.retrieve(image=image, layer=layer, layer_digest=layer_digest, media_type=media_type,
                                           layer_gzip_tar_file_path=layer_gzip_tar_file_path,
                                           progress_instance=progress_instance)

            # NOTE: we're explicitly using unix path separator here to account for windows. docker, in windows, runs in
            # WSL which is linux and uses unix path separator while python code that executes in native windows
            # environment on the same system (which means that it will use a windows path seapartor). this causes a
            # clash that causes docker image tar import failures (which execute in WSL).
            content[0]["Layers"].append("/".join(Path(layer_gzip_tar_file_path).relative_to(image_structure_dir).parts))

            with open(os.path.join(layer_dir_path, 'json'), 'w') as json_file:
                config_json = None
                if last_layer_digest == layer_digest:
                    with open(config_blob_file_path, "r") as config_file:
                        config_json = json.load(config_file)

                    del config_json["history"]

                    for key in [x for x in config_json.keys() if x.lower() == "rootfs"]:
                        config_json.pop(key, None)

                else:
                    config_json = self.__fallback_layer_config_json()

                config_json["id"] = computed_layer_id

                if parent_id:
                    config_json["parent"] = parent_id

                json_file.write(json.dumps(config_json))
                parent_id = config_json["id"]

        self.__blob_retriever.retrieve_queued_blobs(executor=executor, progress_instance=progress_instance)

        return computed_layer_id

    @staticmethod
    def __fallback_layer_config_json ():
        return {
            "created": "1970-01-01T00:00:00Z",
            "container_config": {
                "Hostname": "",
                "Domainname": "",
                "User": "",
                "AttachStdin": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "Tty": False,
                "OpenStdin": False,
                "StdinOnce": False,
                "Env": None,
                "Cmd": None,
                "Image": "",
                "Volumes": None,
                "WorkingDir": "",
                "Entrypoint": None,
                "OnBuild": None,
                "Labels": None
            }
        }


class GetCpdDockerImageManifestAndDigestService:

    def __init__(self, env_settings: EnvSettingsService, docker_requests_service: CpdDockerRequestsService) -> None:
        self.__env_settings = env_settings
        self.__docker_requests_service = docker_requests_service

        self.__os_type_override_warning_given = False
        self.__arch_type_override_warning_given = False

    def get(self, image: str, tag: str, platform_variant: str = None) -> Tuple[dict | None, str | None]:
        # NOTE: this implementation only supports schema version v2 manifests which is compatible with all wxo specific
        # images that are hosted in cloud private registry.

        manifests, manifest, digest = self.__docker_requests_service.get_manifest_list_or_manifest(image=image, tag=tag)

        if manifests:
            digest, media_type = self.__get_compatible_digest(image=image, tag=tag, manifest_list=manifests,
                                                              platform_variant=platform_variant)

            manifest = self.__docker_requests_service.get_manifest_for_digest(image=image, digest=digest,
                                                                              media_type=media_type)

        schema_version = parse_int_safe(manifest.get("schemaVersion"), fallback=None)
        if schema_version is None:
            # should never happen ideally. sanity check.
            raise Exception("Encountered a docker image schema manfiest which does not have a valid schema version")

        else:
            manifest.setdefault("schemaVersion", schema_version)

        return manifest, digest

    def __get_compatible_digest(self, image: str, tag: str, manifest_list: list = None,
                                platform_variant: str = None) -> Tuple[str, str]:
        os_type = self.__get_os_type()
        archs, native_arch, is_user_provided, is_native_arm_arch = self.__get_machine_architectures()
        archs_str = ", ".join([f"\"{x}\"" for x in archs]) if len(archs) > 1 else f"\"{archs[0]}\""
        archs_str = f"architecture{'s' if len(archs) > 1 else ''} {archs_str}"
        platform_variant = parse_string_safe(value=platform_variant, override_empty_to_none=True)

        manifests = deepcopy(manifest_list) \
            if manifest_list is not None \
            else self.__docker_requests_service.get_manifests(image=image, tag=tag)

        manifests = [x for x in manifest_list if
                     x is not None and
                     "mediaType" in x and
                     "digest" in x and
                     "size" in x and
                     "platform" in x and
                     "architecture" in x["platform"] and
                     "os" in x["platform"] and
                     isinstance(x["platform"]["os"], str) and
                     isinstance(x["platform"]["architecture"], str) and
                     x["platform"]["os"].lower() != "unknown" and
                     x["platform"]["architecture"].lower() != "unknown"]

        combos = self.__get_os_arch_combinations(manifests)
        supported_media_types = [DockerOCIContainerMediaTypes.V1.value, DockerOCIContainerMediaTypes.V2.value]

        manifests = [x for x in manifests if
                     x["platform"]["os"].lower() == os_type and
                     x["platform"]["architecture"].lower() in archs]

        if len(manifests) < 1:
            logger.error(f"Could not find docker manifest compatible with OS type \"{os_type}\" and {archs_str} for image {image}:{tag}.")
            logger.info(f"Available docker image OS type and machine architecture combinations: {combos}")
            # logger.info("You may override docker image pull OS type and machine architecture through using DOCKER_IMAGE_OS_TYPE and DOCKER_IMAGE_ARCH_TYPE settings in your environment file.")
            sys.exit(1)

        elif len(manifests) > 1:
            if is_user_provided is True or not is_native_arm_arch:
                manifest_types = ", ".join(set([f"\"{x['mediaType']}\"" for x in manifests]))
                manifests = [x for x in manifests if x["mediaType"] in supported_media_types]
                if len(manifests) < 1:
                    logger.error(f"Encountered unknown/incompatible manifest types ({manifest_types}) for image {image}:{tag}. Cannot pull image without compatible manifest type. Please contact support.")
                    sys.exit(1)

                manifests = [manifests[0]]

            else:
                # native arm arch.
                native_arch_manifests = [x for x in manifests if x["platform"]["architecture"].lower() == native_arch]
                non_arch_manifests = [x for x in manifests if x["platform"]["architecture"].lower() not in get_arm_architectures()]
                other_arm_arch_manifests = [x for x in manifests if
                                            x["platform"]["architecture"].lower() in get_arm_architectures() and
                                            x["platform"]["architecture"].lower() != native_arch]

                check_variants = False

                if len(native_arch_manifests) > 0:
                    # give priority to native arm arch.
                    manifests = native_arch_manifests
                    check_variants = True   # only arm manifests have variants, AFAIK.

                elif len(non_arch_manifests) > 0:
                    # users may be using rosetta. fallback to amd64 arch by design.
                    manifests = non_arch_manifests

                else:
                    # we may have encountered an arm architecture which is arm but has no supported manifests. things
                    # should not get to this but it's here as a sanity check.
                    logger.error(f"Encountered no compatible AMD64 and native ARM architecture manifests for image {image}:{tag}. Cannot pull image without compatible manifest type. Please contact support.")
                    logger.debug(f"Available non-native ARM manifest types: {', '.join(set([x['platform']['architecture'] for x in other_arm_arch_manifests]))}")
                    sys.exit(1)

                # arm chipset images can have multiple platform variant manifests. in such cases, we either choose the
                # manifests that match the platform variant or we fall back to choosing the latest (which is usualy the
                # last, as per tests).
                if check_variants and platform_variant is not None:
                    variant_manifests = [x for x in manifests if "variant" in x["platform"] and parse_string_safe(
                        value=x["platform"]["variant"], override_empty_to_none=True,
                        force_default_to_empty=True).lower() == platform_variant.lower()]

                    if len(variant_manifests) < 1:
                        logger.error(f"Could not find docker manifest compatible with OS type {os_type} and {archs_str} for image {image}:{tag} and variant {platform_variant}.")
                        sys.exit(1)

                    elif len(variant_manifests) > 1:
                        # this should never happen. but it's here as a sanity check.
                        logger.error(f"Encountered multiple manifests matching OS type {os_type}, {archs_str} and variant {platform_variant} for image {image}:{tag}.")
                        sys.exit(1)

                    else:
                        manifests = variant_manifests

                elif check_variants and platform_variant is None:
                    manifests = [manifests[-1]]

        if manifests[0]['mediaType'] not in supported_media_types:
            logger.error(f"Encountered an unknown/incompatible manifest type ({manifests[0]['mediaType']}) for image {image}:{tag}. Cannot pull image without compatible manifest type. Please contact support.")
            sys.exit(1)

        return manifests[0]["digest"], manifests[0]["mediaType"]

    def __get_os_type(self) -> str:
        # NOTE: we're exclusively using linux because of how ADK is set up to use colima vm and rancher. hence, it's
        # always a linux VM even on mac and windows OSes.
        os_type = "linux"
        os_type_override = self.__env_settings.get_user_provided_docker_os_type()
        if os_type_override is not None and os_type != os_type_override:
            if not self.__os_type_override_warning_given:
                logger.warning(f"Overriding your native docker OS type \"{os_type}\" with \"{os_type_override}\"")
                self.__os_type_override_warning_given = True

            os_type = os_type_override

        return os_type.lower()

    def __get_machine_architectures(self) -> Tuple[list[str], str, bool, bool]:
        native_arch = get_architecture()
        user_provided_arch = self.__env_settings.get_user_provided_docker_arch_type()
        is_arm_arch = is_arm_architecture()
        override = False

        if user_provided_arch is not None:
            user_provided_arch = user_provided_arch.lower()

        if user_provided_arch is not None and user_provided_arch != native_arch:
            override = True
            if not self.__arch_type_override_warning_given:
                logger.warning(f"Overriding your native docker machine architecture type \"{native_arch}\" with \"{user_provided_arch}\"")
                self.__arch_type_override_warning_given = True

        architectures = [user_provided_arch] if override else [native_arch]
        if not override and is_arm_arch:
            # support for rosetta.
            architectures.append("amd64")

        return architectures, native_arch, override, is_arm_arch

    @staticmethod
    def __get_os_arch_combinations(manifests: list[dict]) -> dict:
        combos = {}
        for manifest in manifests:
            mos = manifest["platform"]["os"]
            march = manifest["platform"]["architecture"]

            if mos not in combos.keys():
                combos[mos] = []

            if march not in combos[mos]:
                combos[mos].append(march)

        return combos


class CpdDockerImagePullService:

    def __init__(self, cpd_v1_image_pull_service: CpdDockerV1ImagePullService,
                 cpd_v2_image_pull_service: CpdDockerV2ImagePullService,
                 get_manifest_and_digest_service: GetCpdDockerImageManifestAndDigestService) -> None:
        self.__cpd_v1_image_pull_service = cpd_v1_image_pull_service
        self.__cpd_v2_image_pull_service = cpd_v2_image_pull_service
        self.__get_manifest_and_digest_service = get_manifest_and_digest_service

    def pull (self, image: str, tag: str, local_image_name: str, platform_variant: str = None):
        # all non-wxo images, in the non-air-gapped cpd deployment, will be pulled from public docker hub registry by
        # docker compose and docker. in the air-gapped cpd case, all images (including wxo images) will be hosted in a
        # private docker registry and a unique REGISTRY_URL and related credentials will be provided by said users, in
        # their .env file ... which is to state that the system will go back to relying on docker to do image pulls.

        logger.info(f"Pulling CPD image: {local_image_name}:{tag}")

        manifest, digest = self.__get_manifest_and_digest_service.get(image=image, tag=tag,
                                                                      platform_variant=platform_variant)

        # if "schemaVersion" in manifest and "config" in manifest and "layers" in manifest and manifest["schemaVersion"] == 2:
        if manifest["schemaVersion"] == 2:
            logger.debug(f"Digest: {digest}")
            self.__cpd_v2_image_pull_service.pull(image=image, tag=tag, manifest=manifest, local_image_name=local_image_name)
            logger.info(f"Docker image pulled - {local_image_name}:{tag}@{digest}")

        else:
            logger.error(f"Cannot pull V1 docker schema manifest version image for {image}:{tag}. Encountered schema version: {manifest['schemaVersion']}")
            logger.error("WxO CPD docker image pulls only support V2 docker schema manifest versions, presently.")
            sys.exit(1)


class DockerLoginService:

    def __init__ (self, env_service: EnvService):
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
            if source == DeveloperEditionSources.INTERNAL:
                iam_api_key = env_dict.get("DOCKER_IAM_KEY")
                if not iam_api_key:
                    raise ValueError(
                        "DOCKER_IAM_KEY is required in the environment file if WO_DEVELOPER_EDITION_SOURCE is set to 'internal'.")
                self.__docker_login(iam_api_key, registry_url, "iamapikey")
            elif source == DeveloperEditionSources.MYIBM:
                wo_entitlement_key = env_dict.get("WO_ENTITLEMENT_KEY")
                if not wo_entitlement_key:
                    raise ValueError("WO_ENTITLEMENT_KEY is required in the environment file.")
                self.__docker_login(wo_entitlement_key, registry_url, "cp")
            elif source == DeveloperEditionSources.ORCHESTRATE:
                wo_auth_type = self.__env_service.resolve_auth_type(env_dict)
                if wo_auth_type == EnvironmentAuthType.CPD.value and not self.__env_service.did_user_provide_registry_url(env_dict):
                    # docker login is not required when auth type is cpd and user has not provided a custom registry
                    # URL. when in this mode, the system sets REGISTRY_URL to "cpd/cp/wxo-lite" and the system does
                    # custom docker registry image pulls. when a REGISTRY_URL is provided by user and in cpd mode (i.e.,
                    # the user is in air-gapped cpd deployment), it is expected that all images (wxo and non-wxo) will
                    # be hosted in custom docker registry inside the air gapped cpd deployment. hence, we would want to
                    # perform docker login in such a case so that images may be pulled from that custom air gapped
                    # docker registry. on the flip side, when in a non-air-gapped deployment of cpd, we only need to
                    # pull cpd specific images through custom docker pull implementation since cpd does not allow direct
                    # ingress into services (/docker proxy in this case) which is why we rely on custom docker pull
                    # implementation to pull images from a custom route in cpd cluster.
                    logger.info('Authentication type is CPD and user has not provided a REGISTRY_URL. Skipping docker login.')

                else:
                    api_key, username = self.__get_docker_cred_by_wo_auth_type(auth_type=wo_auth_type, env_dict=env_dict)
                    self.__docker_login(api_key, registry_url, username)
            elif source == DeveloperEditionSources.CUSTOM:
                username = env_dict.get("REGISTRY_USERNAME")
                password = env_dict.get("REGISTRY_PASSWORD")
                if not username or not password:
                    logger.warning("REGISTRY_USERNAME or REGISTRY_PASSWORD are missing in the environment file. These values are needed for registry authentication when WO_DEVELOPER_EDITION_SOURCE is set to 'custom'. Skipping registry login." )
                    return
                self.__docker_login(password, registry_url, username)


    @staticmethod
    def __docker_login(api_key: str, registry_url: str, username: str = "iamapikey") -> None:
        """
        Log into a Docker registry (Lima, WSL, or native Docker).
        """
        vm = get_vm_manager()
        logger.info(f"Logging into Docker registry inside {vm.__class__.__name__}: {registry_url} ...")
        result = vm.run_docker_command(
            ["login", "-u", username, "--password-stdin", registry_url],
            input=api_key,        
            capture_output=True,
        )

        if result.returncode != 0:
            err = result.stderr if result.stderr else "Unknown error"
            logger.error(f"Error logging into Docker:\n{err}")
            sys.exit(1)

        logger.info("Successfully logged into Docker.")


    @staticmethod
    def __get_docker_cred_by_wo_auth_type(auth_type: str | None, env_dict: dict) -> tuple[str, str]:
        if auth_type in {EnvironmentAuthType.MCSP.value, EnvironmentAuthType.IBM_CLOUD_IAM.value}:
            wo_api_key = env_dict.get("WO_API_KEY")
            if not wo_api_key:
                raise ValueError(f"WO_API_KEY is required in the environment file if the WO_AUTH_TYPE is set to '{EnvironmentAuthType.MCSP.value}' or '{EnvironmentAuthType.IBM_CLOUD_IAM.value}'.")
            instance_url = env_dict.get("WO_INSTANCE")
            if not instance_url:
                raise ValueError(f"WO_INSTANCE is required in the environment file if the WO_AUTH_TYPE is set to '{EnvironmentAuthType.MCSP.value}' or '{EnvironmentAuthType.IBM_CLOUD_IAM.value}'.")
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
                raise ValueError(f"WO_API_KEY or WO_PASSWORD is required in the environment file if the WO_AUTH_TYPE is set to '{EnvironmentAuthType.CPD.value}'.")
            wo_username = env_dict.get("WO_USERNAME")
            if not wo_username:
                raise ValueError(f"WO_USERNAME is required in the environment file if the WO_AUTH_TYPE is set to '{EnvironmentAuthType.CPD.value}'.")
            return wo_api_key or wo_password, wo_username  # type: ignore[return-value]
        else:
            raise ValueError(f"Unknown value for WO_AUTH_TYPE: '{auth_type}'. Must be one of ['{EnvironmentAuthType.MCSP.value}', '{EnvironmentAuthType.IBM_CLOUD_IAM.value}', '{EnvironmentAuthType.CPD.value}'].")


class DockerComposeCore:

    def __init__(self, env_service: EnvService) -> None:
        self.__env_service = env_service

    def service_up(
        self,
        service_name: str,
        friendly_name: str,
        final_env_file: Path,
        compose_env: MutableMapping | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        """
        Start a single docker-compose service inside the VM (Lima, WSL, or native Docker).
        """
        # compose_path = self.__env_service.get_compose_file()
        final_env_file = path_for_vm(final_env_file)
        compose_path = path_for_vm(self.__env_service.get_compose_file())

        # Build docker-compose command as a list
        command = [
            "compose",
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "up", service_name,
            "-d", "--remove-orphans",
        ]

        self.__pull_cpd_images(final_env_file=final_env_file, service_name=service_name)

        vm = get_vm_manager()
        logger.info(
            f"Starting docker-compose {friendly_name} service inside {vm.__class__.__name__}..."
        )
        return vm.run_docker_command(command, capture_output=True, env=compose_env)

    def services_up(self, profiles: list[str], final_env_file: Path, supplementary_compose_args: list[str]) -> subprocess.CompletedProcess[bytes]:
        final_env_file = path_for_vm(final_env_file)
        compose_path = path_for_vm(self.__env_service.get_compose_file())

        self.__pull_cpd_images(final_env_file=final_env_file, service_name=None)

        command: list[str] = ["compose"]
        for profile in profiles:
            command += ["--profile", profile]
        command += [
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "up",
        ]
        command += supplementary_compose_args
        command += ["-d", "--remove-orphans"]

        logger.info("Starting docker-compose services...")

        vm = get_vm_manager()

        # vm.run_docker_command will prepend "docker"
        return vm.run_docker_command(command, capture_output=False)
    
    def service_down (self, service_name: str, friendly_name: str, final_env_file: Path, is_reset: bool = False) -> subprocess.CompletedProcess[bytes]:
        base_command = self.__ensure_docker_compose_installed()
        final_env_file = path_for_vm(final_env_file)
        compose_path = path_for_vm(self.__env_service.get_compose_file())

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

        vm = get_vm_manager()

        output = vm.shell(command, capture_output=True)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=output.encode() if output else b"", stderr=b"")


    def services_down(self, final_env_file: Path, is_reset: bool = False) -> subprocess.CompletedProcess[bytes]:
        """
        Stop docker-compose services inside the VM. Optionally reset volumes.
        """
        final_env_file = path_for_vm(final_env_file)
        compose_path = path_for_vm(self.__env_service.get_compose_file())
        
        # Choose correct profile argument for OS
        profile_arg = "'*'" if get_os_type() == "windows" else "*"

        # Build docker-compose command
        command = [
            "docker",
            "compose",
            "--profile",
            profile_arg,
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "down"
        ]
        if is_reset:
            command.append("--volumes")
            logger.info("Stopping docker-compose service and resetting volumes...")
        else:
            logger.info("Stopping docker-compose services...")

        vm = get_vm_manager()

        # Capture output so we can construct CompletedProcess
        output = vm.shell(command, capture_output=True)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=(output.stdout if isinstance(output, subprocess.CompletedProcess) else str(output)).encode() if output else b"",
            stderr=b""
        )




    def services_logs(self, final_env_file: Path, should_follow: bool = True) -> subprocess.CompletedProcess[bytes]:
        """
        Show docker-compose logs inside the VM (Lima, WSL, or native Docker).
        """
        final_env_file = path_for_vm(final_env_file)
        compose_path = path_for_vm(self.__env_service.get_compose_file())

        # Choose correct profile argument for OS
        profile_arg = "'*'" if get_os_type() == "windows" else "*"

        # Build command list
        command = [
            "compose",
            "-f", str(compose_path),
            "--env-file", str(final_env_file),
            "--profile", profile_arg,
            "logs"
        ]
        if should_follow:
            command.append("--follow")

        logger.info("Docker Logs...")

        vm = get_vm_manager()
        # Delegate to Docker lifecycle manager
        return vm.run_docker_command(command, capture_output=False)


    def service_container_bash_exec(
        self,
        service_name: str,
        log_message: str,
        final_env_file: Path,
        bash_command: str
    ) -> subprocess.CompletedProcess[bytes]:
        """
        Run a bash command inside a running service container
        (works with Lima, WSL, or native Docker).
        """

        compose_path = path_for_vm(self.__env_service.get_compose_file())

        vm_env_dir = Path.home() / ".cache/orchestrate"
        vm_env_dir.mkdir(parents=True, exist_ok=True)

        vm_env_file = vm_env_dir / final_env_file.name

        shutil.copy(final_env_file, vm_env_file)

        vm_env_file = path_for_vm(vm_env_file)


        # Build docker compose exec command as a list
        docker_command = [
            "compose",
            "-f", str(compose_path),
            "--env-file", str(vm_env_file),
            "exec",
            service_name,
            "bash",
            "-c",
            bash_command
        ]

        logger.info(log_message)

        vm = get_vm_manager()
        return vm.run_docker_command(docker_command, capture_output=False)
        
    def trim_cpd_image_layer_cache (self, final_env_file: Path) -> int:
        env_settings = EnvSettingsService(final_env_file)

        if self.__env_service.resolve_auth_type(env_settings.get_env()) != EnvironmentAuthType.CPD.value:
            logger.error("Encountered a non-CPD environment. This operation can only be run for CPD.")
            sys.exit(1)

        cpd_images = self.__get_cpd_service_images(final_env_file)

        if len(cpd_images) < 1:
            return 0

        blob_cache = WoDockerBlobCacheService(env_settings=env_settings)

        manifest_digests = set([])
        cache_digests = set(blob_cache.get_blob_digests())

        if len(cache_digests) < 1:
            logger.info("Orchestrate CPD docker image layer cache is already empty.")
            return 0

        docker_requests_service = self.__get_docker_requests_service(env_settings=env_settings)
        get_manifest_and_digest_service = GetCpdDockerImageManifestAndDigestService(
            docker_requests_service=docker_requests_service,
            env_settings=env_settings
        )

        for cpd_image in cpd_images:
            try:
                manifest, digest = get_manifest_and_digest_service.get(image=cpd_image["core_image"],
                                                                       tag=cpd_image["tag"])

                # NOTE: only scheam version 2 is supported by cpd image pull service at the present moment.
                if manifest["schemaVersion"] == 2 and len(manifest["layers"]) > 0:
                    for layer in manifest["layers"]:
                        manifest_digests.add(layer["digest"])

                logger.info(f"Retrieved manifest for {cpd_image['image']}:{cpd_image['tag']}@{digest}")

            except SystemExit:
                logger.error(f"Failed to retrieve manifest and digest for CPD docker image {cpd_image['image']}:{cpd_image['tag']}")
                raise

            except Exception as ex:
                logger.error(ex)
                logger.error(f"Failed to retrieve manifest and digest for CPD docker image {cpd_image['image']}:{cpd_image['tag']}")
                sys.exit(1)

        count = 0
        drop_digests = cache_digests.symmetric_difference(manifest_digests)
        if len(drop_digests) > 0:
            for drop_digest in drop_digests:
                try:
                    blob_cache.clear_blob_cache(blob_digest=drop_digest)
                    count += 1

                except Exception as ex:
                    logger.error(f"Failed to clear cache for digest {drop_digest}")
                    raise ex

        return count

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

    def __get_docker_requests_service(self, env_settings: EnvSettingsService) -> CpdDockerRequestsService:
        docker_requests_service = CpdDockerRequestsService(env_settings=env_settings,
                                                           cpd_wxo_token_service=CpdWxOTokenService(env_settings))

        if docker_requests_service.is_docker_proxy_up() is not True:
            logger.error("Upstream CPD Docker service is not running or is not in a ready state. Please try again later.")
            sys.exit(1)

        return docker_requests_service

    def __get_cpd_service_images (self, final_env_file: Path) -> list:
        rendered_yaml_file_path = None

        try:
            base_command = self.__ensure_docker_compose_installed()
            compose_path = self.__env_service.get_compose_file()

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml", prefix="rendered-") as ntf:
                rendered_yaml_file_path = ntf.name

            command = base_command + [
                "-f", str(compose_path),
                "--env-file", str(final_env_file),
                "config",
                "--output",
                rendered_yaml_file_path
            ]

            cmd_result = subprocess.run(command, capture_output=False)

            if cmd_result.returncode != 0:
                stderr_decoded = cmd_result.stderr.decode('utf-8') if isinstance(cmd_result.stderr, bytes) else cmd_result.stderr
                error_message = stderr_decoded if stderr_decoded else "Error occurred."
                logger.error(error_message)
                raise Exception("Error rendering docker compose config to file")

            with open(rendered_yaml_file_path, "rb") as rendered_yaml_file:
                rendered_compose_config = yaml_safe_load(rendered_yaml_file)

            result = []
            for service in list(rendered_compose_config.get("services")):
                image_with_tag = rendered_compose_config["services"][service]["image"]
                if image_with_tag.startswith("cpd/"):
                    temp = image_with_tag.split(":")
                    if len(temp) not in (1, 2):
                        # should ideally never happen but here just in case.
                        logger.error(f"Failed to parse image tag for image \"{image_with_tag}\".")
                        sys.exit(1)

                    result.append({
                        "service" : service,
                        "image": temp[0],
                        "tag" : "latest" if len(temp) < 2 else temp[1],
                        "core_image" : temp[0][4:]
                    })

            return result

        finally:
            if rendered_yaml_file_path is not None:
                os.unlink(rendered_yaml_file_path)

    def __pull_cpd_images (self, final_env_file: Path, service_name: str|None) -> None:
        # Fix: Resolve path for Windows so dotenv_values can read it
        system = get_os_type()
        if system == "windows":
            # Convert /mnt/c/... to C:/... so Python can open it
            env_file_for_reading = str(final_env_file).replace("/mnt/c/", "C:/")
        else:
            env_file_for_reading = str(final_env_file)

        # Copy to a local path if needed (optional safety for WSL)
        if not Path(env_file_for_reading).exists():
            raise FileNotFoundError(f"Env file not found at {env_file_for_reading}")

        env_settings = EnvSettingsService(env_file_for_reading)

        auth_type = self.__env_service.resolve_auth_type(env_settings.get_env())
        provided_registry = self.__env_service.did_user_provide_registry_url(env_settings.get_env())

        if (
                self.__env_service.resolve_auth_type(env_settings.get_env()) != EnvironmentAuthType.CPD.value or
                self.__env_service.did_user_provide_registry_url(env_settings.get_env())
        ):
            # no need to do custom docker image pulls when auth mode is cpd or when we're in an air-gapped cpd
            # environment (where there will be a private docker registry hosted with all the necessary images). we will
            # rely on docker compose and docker to perform docker image pulls.
            return

        cpd_images = self.__get_cpd_service_images(env_file_for_reading)
        service_name = parse_string_safe(value=service_name, override_empty_to_none=True)

        if service_name:
            cpd_images = [x for x in cpd_images if x["service"] == service_name]

        cpd_images = [x for x in cpd_images if not DockerUtils.image_exists_locally(image=x["image"], tag=x["tag"])]

        if len(cpd_images) < 1:
            return

        docker_requests_service = self.__get_docker_requests_service(env_settings=env_settings)
        cpd_image_pull_service = CpdDockerImagePullService(
            cpd_v1_image_pull_service=CpdDockerV1ImagePullService(
                docker_requests_service=docker_requests_service
            ),
            cpd_v2_image_pull_service=CpdDockerV2ImagePullService(
                docker_requests_service=docker_requests_service,
                env_settings=env_settings,
                blob_retriever=DockerImageBlobRetrieverService(
                    docker_requests_service=docker_requests_service,
                    env_settings=env_settings,
                    blob_cache=WoDockerBlobCacheService(env_settings=env_settings)
                )
            ),
            get_manifest_and_digest_service=GetCpdDockerImageManifestAndDigestService(
                docker_requests_service=docker_requests_service,
                env_settings=env_settings
            ),
        )

        for cpd_image in cpd_images:
            try:
                cpd_image_pull_service.pull(image=cpd_image["core_image"], tag=cpd_image["tag"],
                                            local_image_name=cpd_image['image'])

            except SystemExit:
                logger.error(f"Failed to pull CPD docker image {cpd_image['image']}:{cpd_image['tag']}")
                raise

            except Exception as ex:
                logger.error(ex)
                logger.error(f"Failed to pull CPD docker image {cpd_image['image']}:{cpd_image['tag']}")
                sys.exit(1)
