import logging
import os
from pathlib import Path
from typing import Callable, Optional

import requests

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

logger = logging.getLogger(__name__)

# Chunk size for streaming uploads to S3 (8 MB).
_UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024

# Fixed ARM API path segment, appended to the server URL.
# Per Aaron Nguyen (#88741): server_url (e.g. http://localhost:8080/api) is
# mutable and supplied via ARM_SERVER_URL; arm/v1 is the stable ARM path.
_ARM_PATH = "arm/v1"

# Default server URL for local development (matches the ARM service at
# http://localhost:8080/api/v1/arm/v1/...).  Override via ARM_SERVER_URL env var
# when targeting a non-local environment (e.g. dev-conn staging).
_DEFAULT_LOCAL_SERVER_URL = "http://localhost:8080/api/v1"


class _ProgressFileReader:
    """File-like wrapper that streams in fixed-size chunks with a known length.

    Passing a plain Python generator to ``requests.put`` causes urllib3 to use
    ``Transfer-Encoding: chunked`` and discard ``Content-Length``.  S3/MinIO
    presigned PUT endpoints signed with standard SigV4 reject chunked uploads
    with HTTP 411 (Length Required).  This wrapper exposes ``__len__`` so that
    requests can see the payload size upfront, preventing chunked encoding.

    Args:
        path:       Path to the file to stream.
        chunk_size: Number of bytes to read per ``read()`` call.
        callback:   Optional callable invoked with ``len(chunk)`` after each
                    read.  Used by the CLI to advance a live progress bar.
    """

    def __init__(
        self,
        path: Path,
        chunk_size: int,
        callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._path = path
        self._chunk_size = chunk_size
        self._callback = callback
        self._fh = None
        self._size = path.stat().st_size

    def __enter__(self) -> "_ProgressFileReader":
        self._fh = open(self._path, "rb")
        return self

    def __exit__(self, *args) -> None:
        if self._fh:
            self._fh.close()

    def __len__(self) -> int:
        """Return the total file size so requests sends Content-Length, not chunked."""
        return self._size

    def read(self, size: int = -1) -> bytes:
        chunk = self._fh.read(self._chunk_size if size == -1 else size)
        if chunk and self._callback is not None:
            self._callback(len(chunk))
        return chunk

    def __iter__(self):
        while True:
            chunk = self.read(self._chunk_size)
            if not chunk:
                break
            yield chunk


class ARMClient(BaseWXOClient):
    """HTTP client for the ARM Placement Engine API.

    **Base URL**: built as ``{ARM_SERVER_URL}/{_ARM_PATH}`` where
    ``ARM_SERVER_URL`` is read from the environment (default:
    ``http://localhost:8080/api`` for local development).  Set
    ``ARM_SERVER_URL`` to point at a non-local ARM instance (e.g. dev-conn).

    .. note::
        The ``base_url``, ``api_key``, and ``is_local`` constructor arguments
        are required by ``BaseWXOClient`` and are forwarded to it unchanged,
        but they have **no effect on the ARM base URL**.  ``BaseWXOClient``
        appends a WxO-specific path to ``base_url`` and stores the result in
        ``self.base_url``; ARMClient immediately overwrites ``self.base_url``
        with the ARM-specific URL derived from ``ARM_SERVER_URL``.  The WxO
        orchestrate URL is irrelevant to ARM — only ``ARM_SERVER_URL``
        controls which ARM server is targeted.

    Covers the three calls the ADK needs for the image-push flow:

    1. ``get_upload_url``  — ``POST /arm/v1/upload_files/{filename}``
       Returns a short-lived S3 presigned PUT URL and the opaque
       ``upload_path`` that must be passed verbatim to ``register_workload``.

    2. ``upload_to_s3``  — ``PUT <presigned_url>``
       Streams the local archive directly to S3.  No ARM ``Authorization``
       header is sent — the SigV4 signature is embedded in the presigned URL.

    3. ``register_workload``  — ``POST /arm/v1/workloads``
       Registers the image with ARM (source_type = "s3" or "registry") and
       triggers the copy into the ARM cluster registry.
    """

    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False,
                 verify=None, authenticator=None):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            is_local=is_local,
            verify=verify,
            authenticator=authenticator,
        )
        # ARM_SERVER_URL is the sole authority for the ARM base URL.
        # BaseWXOClient sets self.base_url to a WxO orchestrate URL — we
        # immediately overwrite it here with the ARM-specific URL.
        server_url = os.environ.get("ARM_SERVER_URL", _DEFAULT_LOCAL_SERVER_URL).rstrip("/")
        self.base_url = f"{server_url}/{_ARM_PATH}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_upload_url(self, filename: str) -> dict:
        """Request a short-lived S3 presigned upload URL from ARM.

        Args:
            filename: Base filename of the archive (e.g. ``"agent-1.tar.gz"``).
                      Must end with ``.tar``, ``.tar.gz``, or ``.tgz``.

        Returns:
            The ARM response dict::

                {
                    "upload_url":  "<presigned PUT URL>",
                    "upload_path": "<upload_id>/<filename>",  # use verbatim as source_s3_key
                    "expires_at":  "<ISO-8601 timestamp>",
                    "ttl_seconds": 300,
                }

        Raises:
            ClientAPIException: on any non-2xx response from ARM.
        """
        basename = Path(filename).name
        return self._post(f"/upload_files/{basename}")

    def upload_to_s3(
        self,
        upload_url: str,
        file_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Stream a local file to S3 using a presigned PUT URL.

        The presigned URL already contains the SigV4 signature in its query
        string.  No ``Authorization`` header must be added — doing so would
        invalidate the signature.

        Uses ``_ProgressFileReader`` to stream the file in chunks while
        retaining an explicit ``Content-Length``.  Passing a plain Python
        generator to ``requests.put`` causes urllib3 to switch to
        ``Transfer-Encoding: chunked`` and strip ``Content-Length``, which
        S3/MinIO presigned PUT endpoints reject with HTTP 411.

        Args:
            upload_url:         The ``upload_url`` value returned by ``get_upload_url``.
            file_path:          Local path to the archive to upload.
            progress_callback:  Optional callable invoked with the number of bytes
                                read after each chunk.  Used by the CLI to drive a
                                live progress bar.

        Raises:
            requests.HTTPError: if S3 rejects the upload.
            FileNotFoundError: if ``file_path`` does not exist.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image archive not found: {file_path}")

        file_size = file_path.stat().st_size

        with _ProgressFileReader(file_path, _UPLOAD_CHUNK_SIZE, progress_callback) as stream:
            response = requests.put(
                upload_url,
                data=stream,
                headers={
                    "Content-Length": str(file_size),
                    # Explicit Content-Type guards against presigned URLs that sign
                    # the Content-Type header — omitting it would cause a 403.
                    "Content-Type": "application/octet-stream",
                },
                # No Authorization header — signature is in the URL query string.
            )
            response.raise_for_status()

    def register_workload(self, payload: dict) -> dict:
        """Register a workload image with ARM (create or add version).

        Args:
            payload: Request body matching ``POST /arm/v1/workloads``.
                     Required fields depend on ``source_type``::

                         # S3 method
                         {
                             "workload_name":  "agent-1",
                             "workload_type":  "agent",
                             "source_type":    "s3",
                             "source_s3_key":  "<upload_path verbatim>",
                             "tag":            "v1",
                         }

                         # Registry method
                         {
                             "workload_name":        "agent-1",
                             "workload_type":        "agent",
                             "source_type":          "registry",
                             "source_image":         "docker.io/myorg/agent-1:latest",
                             "source_connection_id": "<connection_id>",  # optional
                             "tag":                  "v1",
                         }

        Returns:
            The ARM 201 response dict containing ``workload_id``,
            ``workload_tag_id``, ``image_ref``, ``tag``,
            ``lifecycle_status``, ``audit_id``, etc.

        Raises:
            ClientAPIException: on any non-2xx response from ARM.
        """
        return self._post("/workloads", data=payload)

    # ------------------------------------------------------------------
    # BaseAPIClient abstract stubs (not used by ARM client directly)
    # ------------------------------------------------------------------

    def create(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def delete(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def update(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def get(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError
