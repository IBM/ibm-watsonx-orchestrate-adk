import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from ibm_watsonx_orchestrate.cli.commands.runtime.runtime_controller import (
    RuntimeController,
    SOURCE_TYPE_S3,
    SOURCE_TYPE_REGISTRY,
)
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(
    upload_url_response=None,
    upload_s3_side_effect=None,
    register_response=None,
    register_side_effect=None,
):
    mock = MagicMock()
    mock.get_upload_url.return_value = upload_url_response or {
        "upload_url": "https://s3.example.com/bucket/key?sig=x",
        "upload_path": "abc123/agent.tar.gz",
        "expires_at": "2026-01-01T00:05:00Z",
        "ttl_seconds": 300,
    }
    if upload_s3_side_effect:
        mock.upload_to_s3.side_effect = upload_s3_side_effect
    mock.register_workload.return_value = register_response or {
        "workload_id": "wid-123",
        "workload_name": "agent-1",
        "tag": "v1",
        "image_ref": "stg.icr.io/wxo-workloads/t/wid/agent-1:v1",
        "lifecycle_status": "importing",
    }
    if register_side_effect:
        mock.register_workload.side_effect = register_side_effect
    return mock


def _arm_client_patch(mock_client):
    return patch(
        "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_controller.instantiate_client",
        return_value=mock_client,
    )


# ---------------------------------------------------------------------------
# Validate archive path
# ---------------------------------------------------------------------------

class TestValidateArchivePath:
    def test_accepts_tar(self, tmp_path):
        f = tmp_path / "agent.tar"
        f.write_bytes(b"x")
        RuntimeController._validate_archive_path(f)  # no exception

    def test_accepts_tar_gz(self, tmp_path):
        f = tmp_path / "agent.tar.gz"
        f.write_bytes(b"x")
        RuntimeController._validate_archive_path(f)

    def test_accepts_tgz(self, tmp_path):
        f = tmp_path / "agent.tgz"
        f.write_bytes(b"x")
        RuntimeController._validate_archive_path(f)

    def test_rejects_zip(self, tmp_path):
        f = tmp_path / "agent.zip"
        f.write_bytes(b"x")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            RuntimeController._validate_archive_path(f)

    def test_rejects_sql_gz(self, tmp_path):
        """agent.sql.gz must be rejected — only .tar.gz is valid, not arbitrary .gz."""
        f = tmp_path / "agent.sql.gz"
        f.write_bytes(b"x")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            RuntimeController._validate_archive_path(f)

    def test_rejects_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            RuntimeController._validate_archive_path(tmp_path / "missing.tar")

    def test_rejects_directory(self, tmp_path):
        with pytest.raises(ValueError, match="Expected a file"):
            RuntimeController._validate_archive_path(tmp_path)


# ---------------------------------------------------------------------------
# Validate workload type
# ---------------------------------------------------------------------------

class TestValidateWorkloadType:
    @pytest.mark.parametrize("wt", ["agent", "mcp_toolkit", "guardrails", "eval"])
    def test_valid_types(self, wt):
        RuntimeController._validate_workload_type(wt)  # no exception

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid workload type"):
            RuntimeController._validate_workload_type("unknown_type")


# ---------------------------------------------------------------------------
# Build workload payload
# ---------------------------------------------------------------------------

class TestBuildWorkloadPayload:
    def test_s3_payload_includes_required_fields(self):
        payload = RuntimeController._build_workload_payload(
            workload_name="agent-1",
            workload_type="agent",
            source_type=SOURCE_TYPE_S3,
            tag="v1",
            source_s3_key="abc123/agent.tar.gz",
        )
        assert payload["workload_name"] == "agent-1"
        assert payload["workload_type"] == "agent"
        assert payload["source_type"] == SOURCE_TYPE_S3
        assert payload["tag"] == "v1"
        assert payload["source_s3_key"] == "abc123/agent.tar.gz"

    def test_registry_payload_includes_required_fields(self):
        payload = RuntimeController._build_workload_payload(
            workload_name="agent-1",
            workload_type="agent",
            source_type=SOURCE_TYPE_REGISTRY,
            tag="v2",
            source_image="docker.io/myorg/agent-1:latest",
            source_connection_id="conn-abc",
        )
        assert payload["source_type"] == SOURCE_TYPE_REGISTRY
        assert payload["source_image"] == "docker.io/myorg/agent-1:latest"
        assert payload["source_connection_id"] == "conn-abc"

    def test_none_fields_are_omitted(self):
        payload = RuntimeController._build_workload_payload(
            workload_name="agent-1",
            workload_type="agent",
            source_type=SOURCE_TYPE_S3,
            tag="v1",
        )
        assert "source_s3_key" not in payload
        assert "source_image" not in payload
        assert "source_connection_id" not in payload
        assert "description" not in payload
        assert "mcp_transport" not in payload

    def test_optional_fields_included_when_provided(self):
        payload = RuntimeController._build_workload_payload(
            workload_name="agent-1",
            workload_type="mcp_toolkit",
            source_type=SOURCE_TYPE_S3,
            tag="v1",
            source_s3_key="k",
            description="My workload",
            version_description="Initial release",
            mcp_transport="streamable_http",
        )
        assert payload["description"] == "My workload"
        assert payload["version_description"] == "Initial release"
        assert payload["mcp_transport"] == "streamable_http"


# ---------------------------------------------------------------------------
# push_image_s3
# ---------------------------------------------------------------------------

class TestPushImageS3:
    def test_full_s3_flow_success(self, tmp_path):
        archive = tmp_path / "agent.tar.gz"
        archive.write_bytes(b"fake-tar-content")
        mock_client = _make_mock_client()

        with _arm_client_patch(mock_client):
            controller = RuntimeController()
            result = controller.push_image_s3(
                image_path=str(archive),
                workload_name="agent-1",
                workload_type="agent",
                tag="v1",
            )

        mock_client.get_upload_url.assert_called_once_with("agent.tar.gz")
        # upload_to_s3 is called with a progress_callback kwarg from the controller
        upload_call = mock_client.upload_to_s3.call_args
        assert upload_call[0][0] == "https://s3.example.com/bucket/key?sig=x"
        assert upload_call[0][1] == str(archive)
        assert callable(upload_call[1].get("progress_callback"))
        mock_client.register_workload.assert_called_once()
        registered_payload = mock_client.register_workload.call_args[0][0]
        assert registered_payload["source_type"] == SOURCE_TYPE_S3
        assert registered_payload["source_s3_key"] == "abc123/agent.tar.gz"
        assert registered_payload["tag"] == "v1"
        assert result["workload_id"] == "wid-123"

    def test_exits_on_missing_archive(self, tmp_path):
        controller = RuntimeController()
        with pytest.raises((FileNotFoundError, SystemExit)):
            controller.push_image_s3(
                image_path=str(tmp_path / "missing.tar"),
                workload_name="agent-1",
                workload_type="agent",
                tag="v1",
            )

    def test_exits_on_invalid_extension(self, tmp_path):
        bad_file = tmp_path / "agent.zip"
        bad_file.write_bytes(b"x")
        controller = RuntimeController()
        with pytest.raises((ValueError, SystemExit)):
            controller.push_image_s3(
                image_path=str(bad_file),
                workload_name="agent-1",
                workload_type="agent",
                tag="v1",
            )

    def test_exits_on_get_upload_url_failure(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        mock_response = MagicMock()
        mock_response.status_code = 503
        exc = ClientAPIException(request=MagicMock(), response=mock_response)
        mock_client = _make_mock_client()
        mock_client.get_upload_url.side_effect = exc

        with _arm_client_patch(mock_client):
            controller = RuntimeController()
            with pytest.raises(SystemExit):
                controller.push_image_s3(
                    image_path=str(archive),
                    workload_name="agent-1",
                    workload_type="agent",
                    tag="v1",
                )

    def test_exits_on_tag_already_exists(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {"code": "TAG_ALREADY_EXISTS"}
        exc = ClientAPIException(request=MagicMock(), response=mock_response)
        mock_client = _make_mock_client(register_side_effect=exc)

        with _arm_client_patch(mock_client):
            controller = RuntimeController()
            with pytest.raises(SystemExit):
                controller.push_image_s3(
                    image_path=str(archive),
                    workload_name="agent-1",
                    workload_type="agent",
                    tag="v1",
                )

    def test_passes_mcp_transport_in_payload(self, tmp_path):
        archive = tmp_path / "toolkit.tar.gz"
        archive.write_bytes(b"x")
        mock_client = _make_mock_client()

        with _arm_client_patch(mock_client):
            RuntimeController().push_image_s3(
                image_path=str(archive),
                workload_name="my-toolkit",
                workload_type="mcp_toolkit",
                tag="v1",
                mcp_transport="streamable_http",
            )

        payload = mock_client.register_workload.call_args[0][0]
        assert payload["mcp_transport"] == "streamable_http"


# ---------------------------------------------------------------------------
# push_image_registry
# ---------------------------------------------------------------------------

class TestPushImageRegistry:
    def test_full_registry_flow_success(self):
        mock_client = _make_mock_client()

        with _arm_client_patch(mock_client):
            result = RuntimeController().push_image_registry(
                source_image="docker.io/myorg/agent-1:latest",
                workload_name="agent-1",
                workload_type="agent",
                tag="v2",
                source_connection_id="conn-abc",
            )

        mock_client.get_upload_url.assert_not_called()
        mock_client.upload_to_s3.assert_not_called()
        mock_client.register_workload.assert_called_once()
        payload = mock_client.register_workload.call_args[0][0]
        assert payload["source_type"] == SOURCE_TYPE_REGISTRY
        assert payload["source_image"] == "docker.io/myorg/agent-1:latest"
        assert payload["source_connection_id"] == "conn-abc"
        assert payload["tag"] == "v2"
        assert result["workload_id"] == "wid-123"

    def test_public_registry_omits_connection_id(self):
        mock_client = _make_mock_client()

        with _arm_client_patch(mock_client):
            RuntimeController().push_image_registry(
                source_image="docker.io/myorg/agent-1:latest",
                workload_name="agent-1",
                workload_type="agent",
                tag="v1",
            )

        payload = mock_client.register_workload.call_args[0][0]
        assert "source_connection_id" not in payload

    def test_source_host_included_when_provided(self):
        mock_client = _make_mock_client()

        with _arm_client_patch(mock_client):
            RuntimeController().push_image_registry(
                source_image="123456.dkr.ecr.us-east-1.amazonaws.com/agent-1:v1",
                workload_name="agent-1",
                workload_type="agent",
                tag="v1",
                source_host="vpc-internal.ecr.endpoint",
            )

        payload = mock_client.register_workload.call_args[0][0]
        assert payload["source_host"] == "vpc-internal.ecr.endpoint"

    def test_exits_on_invalid_workload_type(self):
        with pytest.raises((ValueError, SystemExit)):
            RuntimeController().push_image_registry(
                source_image="docker.io/myorg/agent-1:latest",
                workload_name="agent-1",
                workload_type="invalid_type",
                tag="v1",
            )
