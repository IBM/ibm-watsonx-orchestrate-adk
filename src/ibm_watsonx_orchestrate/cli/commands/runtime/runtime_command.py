import logging
import os
import pathlib
from typing import Optional

import typer
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.cli.commands.runtime.runtime_controller import (
    RuntimeController,
    SOURCE_TYPE_S3,
    SOURCE_TYPE_REGISTRY,
    VALID_WORKLOAD_TYPES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature flag
# ARM push commands are in active development and must only be exposed when
# FEATURE_ARM_PUSH=true is set in the environment.  This prevents accidental
# use before the feature is validated on a live WxO instance.
# ---------------------------------------------------------------------------
_FEATURE_ENABLED = os.environ.get("FEATURE_ARM_PUSH", "").strip().lower() == "true"

runtime_app = typer.Typer(
    no_args_is_help=True,
    help="[Preview] Manage custom agent and MCP toolkit workload images in ARM.",
    hidden=not _FEATURE_ENABLED,
)

# Allowed workload types (kept in sync with runtime_controller.VALID_WORKLOAD_TYPES)
_WORKLOAD_TYPE_HELP = "Workload type: agent | mcp_toolkit | guardrails | eval"
_TAG_HELP = (
    "Version tag for this image (e.g. 'v1', 'v2'). Required — auto-generation is "
    "not supported. Supplying the same tag twice for the same workload returns an error."
)


@runtime_app.command(
    name="push-image",
    help=(
        "[Preview] Push a custom agent or MCP toolkit Docker image to the ARM registry.\n\n"
        "Two upload methods are supported:\n\n"
        "  S3 method (default for local files): supply --image as a path to a .tar/.tar.gz/.tgz "
        "archive and --source-type s3.  The ADK obtains a short-lived S3 presigned URL from ARM, "
        "streams the archive directly to S3, then calls ARM to copy the image into the cluster "
        "registry.  The entire upload must complete within the presigned URL TTL (default 300s).\n\n"
        "  Registry method: supply --image as a fully-qualified OCI reference and "
        "--source-type registry.  ARM pulls the image from the source registry and copies it "
        "into the cluster registry.  Use --app-id to supply credentials for private registries."
    ),
)
def push_image(
    image: Annotated[
        str,
        typer.Option(
            "--image", "-i",
            help=(
                "For --source-type s3: path to a local OCI archive (.tar, .tar.gz, or .tgz). "
                "For --source-type registry: fully-qualified OCI image reference "
                "(e.g. 'docker.io/myorg/agent-1:latest')."
            ),
        ),
    ],
    name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help=(
                "Unique workload name for this tenant (e.g. 'my-agent'). "
                "Used as the image repository name in the ARM registry. "
                "Re-using the same name with a new --tag adds a new version."
            ),
        ),
    ],
    workload_type: Annotated[
        str,
        typer.Option("--type", "-t", help=_WORKLOAD_TYPE_HELP),
    ],
    tag: Annotated[
        str,
        typer.Option("--tag", help=_TAG_HELP),
    ],
    source_type: Annotated[
        Optional[str],
        typer.Option(
            "--source-type",
            help=(
                "How the image is sourced: 's3' (upload a local archive) or "
                "'registry' (pull from a remote OCI registry). "
                "Defaults to 's3' when --image is a local file path, 'registry' otherwise."
            ),
        ),
    ] = None,
    app_id: Annotated[
        Optional[str],
        typer.Option(
            "--app-id", "-a",
            help=(
                "wxo-connection app-id holding pull credentials for a private source registry. "
                "Only used with --source-type registry. Omit for public registries."
            ),
        ),
    ] = None,
    source_host: Annotated[
        Optional[str],
        typer.Option(
            "--source-host",
            help=(
                "Override the source registry login endpoint when it differs from the host "
                "parsed out of the image reference (e.g. a VPC-internal ECR endpoint). "
                "Only used with --source-type registry."
            ),
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Human-readable description of the workload."),
    ] = None,
    version_description: Annotated[
        Optional[str],
        typer.Option(
            "--version-description",
            help="Human-readable description of this specific version tag.",
        ),
    ] = None,
    mcp_transport: Annotated[
        Optional[str],
        typer.Option(
            "--mcp-transport",
            help=(
                "MCP transport protocol. Required when --type is mcp_toolkit. "
                "Currently only 'streamable_http' is accepted."
            ),
        ),
    ] = None,
    eval_timeout_seconds: Annotated[
        Optional[int],
        typer.Option(
            "--eval-timeout-seconds",
            help="Evaluation timeout in seconds. Required when --type is eval.",
        ),
    ] = None,
) -> None:
    # ------------------------------------------------------------------
    # Resolve source_type when not explicitly supplied.
    # A local file path → s3; anything else (OCI ref) → registry.
    # ------------------------------------------------------------------
    if source_type is None:
        candidate = pathlib.Path(image)
        source_type = SOURCE_TYPE_S3 if candidate.exists() and candidate.is_file() else SOURCE_TYPE_REGISTRY

    # ------------------------------------------------------------------
    # Validate tag is non-empty (Belt-and-suspenders — typer enforces
    # the option is present but the user could pass an empty string.)
    # ------------------------------------------------------------------
    if not tag or not tag.strip():
        logger.error("--tag is required and must not be empty.")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Validate workload type
    # ------------------------------------------------------------------
    if workload_type not in VALID_WORKLOAD_TYPES:
        logger.error(
            f"Invalid --type '{workload_type}'. "
            f"Expected one of: {', '.join(sorted(VALID_WORKLOAD_TYPES))}"
        )
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Type-specific validation
    # ------------------------------------------------------------------
    if workload_type == "mcp_toolkit" and not mcp_transport:
        logger.error("--mcp-transport is required when --type is mcp_toolkit.")
        raise typer.Exit(code=1)

    if workload_type == "mcp_toolkit" and mcp_transport != "streamable_http":
        logger.error(
            f"Unsupported --mcp-transport '{mcp_transport}'. "
            f"Only 'streamable_http' is currently supported."
        )
        raise typer.Exit(code=1)

    if workload_type == "eval" and eval_timeout_seconds is None:
        logger.error("--eval-timeout-seconds is required when --type is eval.")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    controller = RuntimeController()

    if source_type == SOURCE_TYPE_S3:
        controller.push_image_s3(
            image_path=image,
            workload_name=name,
            workload_type=workload_type,
            tag=tag,
            description=description,
            version_description=version_description,
            mcp_transport=mcp_transport,
            eval_timeout_seconds=eval_timeout_seconds,
        )
    elif source_type == SOURCE_TYPE_REGISTRY:
        controller.push_image_registry(
            source_image=image,
            workload_name=name,
            workload_type=workload_type,
            tag=tag,
            source_connection_id=app_id,
            source_host=source_host,
            description=description,
            version_description=version_description,
            mcp_transport=mcp_transport,
            eval_timeout_seconds=eval_timeout_seconds,
        )
    else:
        logger.error(
            f"Unknown --source-type '{source_type}'. Expected 's3' or 'registry'."
        )
        raise typer.Exit(code=1)
