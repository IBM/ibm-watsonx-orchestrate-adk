import pytest
import typer
from unittest.mock import patch, MagicMock

from ibm_watsonx_orchestrate.cli.commands.runtime import runtime_command

# When push_image is called directly (not via the CLI runner), typer raises
# typer.exceptions.Exit rather than SystemExit.  Accept either.
_EXIT = (SystemExit, typer.exceptions.Exit)


# ---------------------------------------------------------------------------
# push-image command — S3 source (explicit)
# ---------------------------------------------------------------------------

class TestPushImageS3:
    def test_dispatches_to_push_image_s3(self, tmp_path):
        archive = tmp_path / "agent.tar.gz"
        archive.write_bytes(b"x")

        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True), patch(
            "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_s3"
        ) as mock_s3:
            runtime_command.push_image(
                image=str(archive),
                name="agent-1",
                workload_type="agent",
                tag="v1",
                source_type="s3",
            )
        mock_s3.assert_called_once_with(
            image_path=str(archive),
            workload_name="agent-1",
            workload_type="agent",
            tag="v1",
            description=None,
            version_description=None,
            mcp_transport=None,
            eval_timeout_seconds=None,
        )

    def test_auto_detects_s3_for_local_file(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")

        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True), patch(
            "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_s3"
        ) as mock_s3:
            # source_type=None → auto-detect from file existence
            runtime_command.push_image(
                image=str(archive),
                name="agent-1",
                workload_type="agent",
                tag="v1",
                source_type=None,
            )
        mock_s3.assert_called_once()

    def test_passes_optional_fields(self, tmp_path):
        archive = tmp_path / "toolkit.tar.gz"
        archive.write_bytes(b"x")

        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True), patch(
            "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_s3"
        ) as mock_s3:
            runtime_command.push_image(
                image=str(archive),
                name="my-toolkit",
                workload_type="mcp_toolkit",
                tag="v1",
                source_type="s3",
                mcp_transport="streamable_http",
                description="A toolkit",
                version_description="Initial",
            )
        call_kwargs = mock_s3.call_args[1]
        assert call_kwargs["mcp_transport"] == "streamable_http"
        assert call_kwargs["description"] == "A toolkit"
        assert call_kwargs["version_description"] == "Initial"


# ---------------------------------------------------------------------------
# push-image command — registry source
# ---------------------------------------------------------------------------

class TestPushImageRegistry:
    def test_dispatches_to_push_image_registry(self):
        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True), patch(
            "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_registry"
        ) as mock_reg:
            runtime_command.push_image(
                image="docker.io/myorg/agent-1:latest",
                name="agent-1",
                workload_type="agent",
                tag="v2",
                source_type="registry",
                app_id="conn-abc",
                source_host=None,
            )
        mock_reg.assert_called_once_with(
            source_image="docker.io/myorg/agent-1:latest",
            workload_name="agent-1",
            workload_type="agent",
            tag="v2",
            source_connection_id="conn-abc",
            source_host=None,
            description=None,
            version_description=None,
            mcp_transport=None,
            eval_timeout_seconds=None,
        )

    def test_auto_detects_registry_for_oci_ref(self):
        """A non-existent local path should auto-resolve to registry source."""
        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True), patch(
            "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_registry"
        ) as mock_reg:
            runtime_command.push_image(
                image="docker.io/myorg/agent-1:latest",
                name="agent-1",
                workload_type="agent",
                tag="v1",
                source_type=None,
            )
        mock_reg.assert_called_once()


# ---------------------------------------------------------------------------
# Feature flag guard
# ---------------------------------------------------------------------------

class TestFeatureFlagGuard:
    def test_exits_when_feature_flag_not_set(self, tmp_path):
        """push_image must exit with an error when FEATURE_ARM_PUSH is not true."""
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        with patch.object(runtime_command, "ENABLE_ARM_PUSH", False):
            with pytest.raises(_EXIT):
                runtime_command.push_image(
                    image=str(archive),
                    name="agent-1",
                    workload_type="agent",
                    tag="v1",
                    source_type="s3",
                )

    def test_proceeds_when_feature_flag_set(self, tmp_path):
        """push_image must not exit on the feature flag check when FEATURE_ARM_PUSH=true."""
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        with patch.object(runtime_command, "ENABLE_ARM_PUSH", True):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.runtime.runtime_command.RuntimeController.push_image_s3"
            ):
                # Should not raise due to feature flag
                runtime_command.push_image(
                    image=str(archive),
                    name="agent-1",
                    workload_type="agent",
                    tag="v1",
                    source_type="s3",
                )


# ---------------------------------------------------------------------------
# Validation — missing / invalid inputs
# ---------------------------------------------------------------------------

class TestPushImageValidation:
    def test_empty_tag_exits(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="agent-1",
                workload_type="agent",
                tag="   ",
                source_type="s3",
            )

    def test_invalid_workload_type_exits(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="agent-1",
                workload_type="bad_type",
                tag="v1",
                source_type="s3",
            )

    def test_mcp_toolkit_without_transport_exits(self, tmp_path):
        archive = tmp_path / "toolkit.tar.gz"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="my-toolkit",
                workload_type="mcp_toolkit",
                tag="v1",
                source_type="s3",
                mcp_transport=None,
            )

    def test_mcp_toolkit_unsupported_transport_exits(self, tmp_path):
        archive = tmp_path / "toolkit.tar.gz"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="my-toolkit",
                workload_type="mcp_toolkit",
                tag="v1",
                source_type="s3",
                mcp_transport="http_sse",
            )

    def test_eval_without_timeout_exits(self, tmp_path):
        archive = tmp_path / "eval.tar"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="my-eval",
                workload_type="eval",
                tag="v1",
                source_type="s3",
                eval_timeout_seconds=None,
            )

    def test_unknown_source_type_exits(self, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"x")
        with pytest.raises(_EXIT):
            runtime_command.push_image(
                image=str(archive),
                name="agent-1",
                workload_type="agent",
                tag="v1",
                source_type="ftp",
            )
