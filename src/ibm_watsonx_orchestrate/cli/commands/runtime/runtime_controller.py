import logging
import sys
from pathlib import Path
from typing import NoReturn, Optional

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TransferSpeedColumn, TimeRemainingColumn

from ibm_watsonx_orchestrate.client.runtime.arm_client import ARMClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException, format_client_api_error
from ibm_watsonx_orchestrate_clients.common.utils import instantiate_client

logger = logging.getLogger(__name__)

# Supported archive extensions for S3 upload.
# .tar.gz files have path.suffix == ".gz" and path.suffixes[-2:] == [".tar", ".gz"].
_VALID_EXTENSIONS = {".tar", ".tgz"}
_VALID_DOUBLE_SUFFIXES = {(".tar", ".gz")}

# Valid workload types per ARM ADR.
VALID_WORKLOAD_TYPES = {"agent", "mcp_toolkit", "guardrails", "eval"}

# Valid source types.
SOURCE_TYPE_S3 = "s3"
SOURCE_TYPE_REGISTRY = "registry"


class RuntimeController:
    """Orchestrates ARM image push flows on behalf of the CLI.

    Two public entry points:

    * ``push_image_s3``       — upload a local OCI archive via S3 presigned URL.
    * ``push_image_registry`` — bind a remote registry image to ARM.
    """

    def __init__(self) -> None:
        self._client: Optional[ARMClient] = None

    def _get_client(self) -> ARMClient:
        """Return a lazily-instantiated ARMClient for the active environment."""
        if not self._client:
            self._client = instantiate_client(ARMClient)
        return self._client

    # ------------------------------------------------------------------
    # S3 push flow
    # ------------------------------------------------------------------

    def push_image_s3(
        self,
        image_path: str,
        workload_name: str,
        workload_type: str,
        tag: str,
        description: Optional[str] = None,
        version_description: Optional[str] = None,
        mcp_transport: Optional[str] = None,
        eval_timeout_seconds: Optional[int] = None,
    ) -> dict:
        """Upload a local OCI image archive to ARM via S3 presigned URL.

        Flow::

            ADK → POST /arm/v1/upload_files/{filename}  (get presigned URL)
            ADK → PUT  <presigned_url>                   (stream archive)
            ADK → POST /arm/v1/workloads                 (register workload)

        Args:
            image_path:            Local path to the OCI archive (.tar/.tar.gz/.tgz).
            workload_name:         Unique workload name per tenant.
            workload_type:         One of: agent | mcp_toolkit | guardrails | eval.
            tag:                   Version tag (e.g. "v1"). Mandatory — no auto-generation.
            description:           Optional workload description.
            version_description:   Optional description for this specific version tag.
            mcp_transport:         Required when workload_type is mcp_toolkit.
            eval_timeout_seconds:  Required when workload_type is eval.

        Returns:
            ARM 201 response dict with workload_id, image_ref, tag, lifecycle_status, etc.
        """
        image_path = Path(image_path)
        self._validate_archive_path(image_path)
        self._validate_workload_type(workload_type)

        console = Console()
        client = self._get_client()

        # Step 1 — get presigned URL
        filename = image_path.name
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(description="Requesting upload URL from ARM...", total=None)
            try:
                url_response = client.get_upload_url(filename)
            except ClientAPIException as e:
                logger.error(f"Failed to get upload URL: {format_client_api_error(e)}")
                sys.exit(1)

        upload_url = url_response["upload_url"]
        upload_path = url_response["upload_path"]
        ttl_seconds = url_response.get("ttl_seconds", 300)
        expires_at = url_response.get("expires_at", "")

        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Upload URL obtained (TTL: {ttl_seconds}s, expires: {expires_at}). "
            f"Uploading {filename} ({file_size_mb:.1f} MB)..."
        )

        # Step 2 — stream file to S3 with live progress
        try:
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    description=f"Uploading {filename}...",
                    total=image_path.stat().st_size,
                )

                def _on_chunk(n_bytes: int) -> None:
                    progress.advance(task, n_bytes)

                client.upload_to_s3(upload_url, str(image_path), progress_callback=_on_chunk)
        except requests.HTTPError as e:
            logger.error(
                f"S3 upload failed (HTTP {e.response.status_code}): {e.response.text}"
            )
            sys.exit(1)
        except FileNotFoundError as e:
            logger.error(str(e))
            sys.exit(1)

        logger.info("Upload complete. Registering workload with ARM...")

        # Step 3 — register workload
        payload = self._build_workload_payload(
            workload_name=workload_name,
            workload_type=workload_type,
            source_type=SOURCE_TYPE_S3,
            tag=tag,
            source_s3_key=upload_path,
            description=description,
            version_description=version_description,
            mcp_transport=mcp_transport,
            eval_timeout_seconds=eval_timeout_seconds,
        )

        return self._register_workload(client, payload, workload_name, tag, console)

    # ------------------------------------------------------------------
    # Registry push flow
    # ------------------------------------------------------------------

    def push_image_registry(
        self,
        source_image: str,
        workload_name: str,
        workload_type: str,
        tag: str,
        source_connection_id: Optional[str] = None,
        source_host: Optional[str] = None,
        description: Optional[str] = None,
        version_description: Optional[str] = None,
        mcp_transport: Optional[str] = None,
        eval_timeout_seconds: Optional[int] = None,
    ) -> dict:
        """Bind a remote registry image to ARM.

        ARM will pull the image from the source registry and copy it into
        the ARM cluster registry.  The builder must have already pushed the
        image to the source registry before calling this.

        Args:
            source_image:          Fully-qualified OCI image reference
                                   (e.g. ``"docker.io/myorg/agent-1:latest"``).
            workload_name:         Unique workload name per tenant.
            workload_type:         One of: agent | mcp_toolkit | guardrails | eval.
            tag:                   Version tag (e.g. "v1"). Mandatory.
            source_connection_id:  wxo-connection app-id for private registry credentials.
                                   Omit for public registries.
            source_host:           Override the source registry login endpoint.
                                   Omit to have ARM derive it from ``source_image``.
            description:           Optional workload description.
            version_description:   Optional description for this specific version tag.
            mcp_transport:         Required when workload_type is mcp_toolkit.
            eval_timeout_seconds:  Required when workload_type is eval.

        Returns:
            ARM 201 response dict with workload_id, image_ref, tag, lifecycle_status, etc.
        """
        self._validate_workload_type(workload_type)

        console = Console()
        client = self._get_client()

        logger.info(f"Registering workload '{workload_name}:{tag}' from registry image '{source_image}'...")

        payload = self._build_workload_payload(
            workload_name=workload_name,
            workload_type=workload_type,
            source_type=SOURCE_TYPE_REGISTRY,
            tag=tag,
            source_image=source_image,
            source_connection_id=source_connection_id,
            source_host=source_host,
            description=description,
            version_description=version_description,
            mcp_transport=mcp_transport,
            eval_timeout_seconds=eval_timeout_seconds,
        )

        return self._register_workload(client, payload, workload_name, tag, console)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _register_workload(
        self, client: ARMClient, payload: dict, workload_name: str, tag: str, console: Console
    ) -> dict:
        """Call POST /arm/v1/workloads and print a success summary."""
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(description="Registering workload with ARM...", total=None)
            try:
                result = client.register_workload(payload)
            except ClientAPIException as e:
                self._handle_register_error(e, workload_name, tag)

        workload_id = result.get("workload_id", "")
        image_ref = result.get("image_ref", "")
        lifecycle_status = result.get("lifecycle_status", "")

        logger.info(
            f"✅ Workload '{workload_name}:{tag}' registered successfully.\n"
            f"   workload_id:      {workload_id}\n"
            f"   image_ref:        {image_ref}\n"
            f"   lifecycle_status: {lifecycle_status}"
        )
        return result

    @staticmethod
    def _handle_register_error(e: ClientAPIException, workload_name: str, tag: str) -> NoReturn:
        """Translate ARM error codes into user-friendly messages, then exit."""
        response = getattr(e, "response", None)
        code = ""
        if response is not None:
            try:
                body = response.json()
                code = body.get("code", "")
            except Exception:
                pass

        if code == "TAG_ALREADY_EXISTS":
            logger.error(
                f"Tag '{tag}' already exists for workload '{workload_name}'. "
                f"Supply a different --tag to publish a new version."
            )
        elif code == "MISSING_TAG":
            logger.error("A version tag is required. Use --tag to supply one.")
        elif code == "PLACEMENT_POLICY_VIOLATION":
            logger.error(
                f"ARM placement policy violation: {format_client_api_error(e)}"
            )
        elif code in ("S3_OBJECT_NOT_FOUND", "ARCHIVE_INVALID"):
            logger.error(
                f"ARM could not process the uploaded archive ({code}): "
                f"{format_client_api_error(e)}"
            )
        else:
            logger.error(f"Failed to register workload: {format_client_api_error(e)}")
        sys.exit(1)

    @staticmethod
    def _validate_archive_path(path: Path) -> None:
        """Ensure the file exists and has a supported extension."""
        if not path.exists():
            raise FileNotFoundError(f"Image archive not found: {path}")
        if not path.is_file():
            raise ValueError(f"Expected a file, got a directory: {path}")
        # Check both the last suffix (.tar, .tgz) and the last two suffixes
        # (.tar.gz) so that e.g. agent.sql.gz is rejected with a clear message
        # rather than passing through as ".gz" and failing server-side.
        suffixes = tuple(s.lower() for s in path.suffixes[-2:])
        last = suffixes[-1] if suffixes else ""
        if last not in _VALID_EXTENSIONS and suffixes not in _VALID_DOUBLE_SUFFIXES:
            raise ValueError(
                f"Unsupported file extension '{path.name}'. "
                f"Expected one of: .tar, .tar.gz, .tgz"
            )

    @staticmethod
    def _validate_workload_type(workload_type: str) -> None:
        """Raise ValueError if workload_type is not one of the ARM-supported values."""
        if workload_type not in VALID_WORKLOAD_TYPES:
            raise ValueError(
                f"Invalid workload type '{workload_type}'. "
                f"Expected one of: {', '.join(sorted(VALID_WORKLOAD_TYPES))}"
            )

    @staticmethod
    def _build_workload_payload(
        workload_name: str,
        workload_type: str,
        source_type: str,
        tag: str,
        source_s3_key: Optional[str] = None,
        source_image: Optional[str] = None,
        source_connection_id: Optional[str] = None,
        source_host: Optional[str] = None,
        description: Optional[str] = None,
        version_description: Optional[str] = None,
        mcp_transport: Optional[str] = None,
        eval_timeout_seconds: Optional[int] = None,
    ) -> dict:
        """Build the POST /arm/v1/workloads request body.

        None-valued fields are omitted entirely — ARM rejects unknown null keys.
        """
        payload: dict = {
            "workload_name": workload_name,
            "workload_type": workload_type,
            "source_type": source_type,
            "image_tag": tag,
        }
        if description is not None:
            payload["description"] = description
        if version_description is not None:
            payload["version_description"] = version_description
        if source_s3_key is not None:
            payload["source_s3_key"] = source_s3_key
        if source_image is not None:
            payload["source_image"] = source_image
        if source_connection_id is not None:
            payload["source_connection_id"] = source_connection_id
        if source_host is not None:
            payload["source_host"] = source_host
        if mcp_transport is not None:
            payload["mcp_transport"] = mcp_transport
        if eval_timeout_seconds is not None:
            payload["eval_timeout_seconds"] = eval_timeout_seconds
        return payload
