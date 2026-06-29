"""
Integration tests for flow translation export/import functionality.

These tests require a running Orchestrate Server (local or remote) and test
the complete workflow of:
1. Creating/importing a flow tool
2. Exporting translations to CSV
3. Modifying translations
4. Importing translations back
5. Verifying the translations are applied

Run with: pytest tests/integration_tests/flow_builder/translation_flow/
"""

import pytest
import os
import tempfile
import csv
from pathlib import Path
import subprocess
import json
import asyncio
import requests

from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
from ibm_watsonx_orchestrate.client.tools.builder_client import BuilderClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.cli.commands.environment.environment_controller import activate
from ibm_watsonx_orchestrate.cli.config import Config, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT
from ibm_watsonx_orchestrate.flow_builder import utils as flow_builder_utils
from ibm_watsonx_orchestrate_clients.common.credentials import Credentials
from ibm_watsonx_orchestrate_clients.common.service_instance.local_service_instance import (
    DEFAULT_LOCAL_SERVICE_URL,
    LocalServiceInstance,
)
from .tools.translation_test_flow import build_translation_test_flow

# Check if Orchestrate Server is running before running integration tests
try:
    response = requests.get("http://localhost:4025/health", timeout=2)
    server_available = response.status_code == 200
except (requests.ConnectionError, requests.Timeout):
    server_available = False

if not server_available:
    pytest.skip(
        "Orchestrate Server not available. These integration tests require a running server. "
        "Run them via: tests/integration_tests/run_integration_tests.sh",
        allow_module_level=True
    )


@pytest.fixture(scope="module", autouse=True)
def ensure_local_environment():
    """Force translation integration tests to use clean local clients."""
    cfg = Config()
    previous_active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    activate("local")

    monkeypatch = pytest.MonkeyPatch()

    def _instantiate_local_tool_client(client_cls, *args, **kwargs):
        if client_cls is ToolClient:
            class _DummyClient:
                def __init__(self):
                    self.credentials = Credentials(url=DEFAULT_LOCAL_SERVICE_URL)
                    self.token = None

            local_service_instance = LocalServiceInstance(_DummyClient())
            tenant_access_token = local_service_instance.tenant_access_token
            if tenant_access_token is None:
                raise RuntimeError("Failed to obtain local tenant access token for translation tests")
            return ToolClient(
                base_url=DEFAULT_LOCAL_SERVICE_URL,
                api_key=tenant_access_token,
                is_local=True
            )
        return instantiate_client(client_cls, *args, **kwargs)

    monkeypatch.setattr(flow_builder_utils, "instantiate_client", _instantiate_local_tool_client)
    monkeypatch.setattr(
        "tests.integration_tests.flow_builder.translation_flow.test_translation_flow.instantiate_client",
        _instantiate_local_tool_client
    )

    yield

    monkeypatch.undo()
    cfg.write(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, previous_active_env)

@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_flow():
    """
    Build and compile the test flow for translation testing.
    Returns the compiled flow object.
    """
    flow = await build_translation_test_flow().compile_deploy()
    return flow


@pytest.fixture(scope="module")
def flow_json_file_path():
    """
    Return the path to the flowJson.json file.
    This provides a properly structured flow model file for testing.
    """
    return str(Path(__file__).parent / "tools" / "flowJson.json")


@pytest.fixture(scope="module")
def flow_model_from_file(flow_json_file_path):
    """
    Load the flow model from flowJson.json file.
    This provides a properly structured flow model for testing.
    """
    with open(flow_json_file_path, 'r', encoding='utf-8') as f:
        flow_model = json.load(f)
    return flow_model


@pytest.fixture(scope="module")
def imported_flow_tool(flow_json_file_path):
    """
    Import the test flow tool and return its details.
    This fixture sets up the flow tool that will be used for translation tests.
    """
    activate("local")

    controller = ToolsController()
    local_tool_client = flow_builder_utils.instantiate_client(ToolClient)

    existing_tools = local_tool_client.get_draft_by_name("translation_test_flow")
    for existing_tool in existing_tools:
        try:
            local_tool_client.delete(tool_id=existing_tool["id"])
        except Exception:
            pass

    controller.import_tool(
        kind=ToolKind.flow,
        file=flow_json_file_path
    )

    existing_tools = local_tool_client.get_draft_by_name("translation_test_flow")

    if not existing_tools:
        pytest.skip("Flow tool was not imported successfully")

    tool_info = {"id": existing_tools[0]["id"], "name": existing_tools[0]["name"]}

    yield tool_info

    # Cleanup: Delete the tool after tests
    try:
        local_tool_client.delete(tool_id=tool_info["id"])
    except Exception as e:
        print(f"Cleanup warning: Could not delete tool {tool_info['id']}: {e}")


class TestTranslationExportIntegration:
    """Integration tests for translation export functionality"""
    
    def test_export_translations_from_file(self, flow_json_file_path, tmp_path):
        """
        Test exporting translations from a flow file.
        Uses the flowJson.json file which contains a properly structured flow model.
        """
        controller = ToolsController()
        output_file = tmp_path / "exported_from_file.csv"
        
        # Export translations using flow file path
        controller.export_flow_translations(
            file=flow_json_file_path,
            translation_output_path=str(output_file)
        )
        
        assert output_file.exists(), "Translation CSV should be exported"
        assert output_file.stat().st_size > 0, "CSV file should not be empty"
        
        # Verify CSV structure
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) > 0, "CSV should contain translation entries"
            # Check for expected columns
            assert 'path' in rows[0], "CSV should have 'path' column"
            assert 'source (en)' in rows[0], "CSV should have 'source (en)' column"
    
    def test_export_translations_from_imported_tool(self, imported_flow_tool, tmp_path):
        """Test exporting translations from an already imported flow tool"""
        controller = ToolsController()
        output_file = tmp_path / "exported_from_tool.csv"
        
        # Export translations using tool name
        controller.export_flow_translations(
            name=imported_flow_tool["name"],
            translation_output_path=str(output_file)
        )
        
        assert output_file.exists(), "Translation CSV should be exported"
        assert output_file.stat().st_size > 0, "CSV file should not be empty"
    
    def test_export_translations_creates_parent_directories(self, imported_flow_tool, tmp_path):
        """Test that export creates parent directories if they don't exist"""
        controller = ToolsController()
        nested_path = tmp_path / "nested" / "dir" / "translations.csv"
        
        controller.export_flow_translations(
            name=imported_flow_tool["name"],
            translation_output_path=str(nested_path)
        )
        
        assert nested_path.exists(), "Should create nested directories"


class TestTranslationImportIntegration:
    """Integration tests for translation import functionality"""
    
    def test_import_translations_roundtrip(self, imported_flow_tool, tmp_path):
        """
        Test complete roundtrip: export -> modify -> import -> verify
        
        Note: This test verifies that imported translations persist and are not
        overwritten by subsequent operations.
        """
        controller = ToolsController()
        export_file = tmp_path / "export.csv"
        import_file = tmp_path / "import.csv"
    
        # Step 1: Export translations
        controller.export_flow_translations(
            name=imported_flow_tool["name"],
            translation_output_path=str(export_file)
        )
    
        # Step 2: Modify translations by adding French translations
        with open(export_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    
        # Add French translations to the 'fr' column
        for row in rows:
            if 'fr' in row:
                row['fr'] = 'MODIFIED'
    
        # Write modified translations
        with open(import_file, 'w', encoding='utf-8', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    
        # Step 3: Import modified translations
        controller.import_flow_translations(
            translation_path=str(import_file),
            name=imported_flow_tool["name"]
        )
    
        # Step 4: Export again to verify changes
        # IMPORTANT: Do NOT reimport the tool here, as that would overwrite translations
        verify_file = tmp_path / "verify.csv"
        controller.export_flow_translations(
            name=imported_flow_tool["name"],
            translation_output_path=str(verify_file)
        )
    
        # Verify the modifications were applied
        with open(verify_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            verify_rows = list(reader)
    
        # Debug: Print the rows to see what we got
        print(f"\nOriginal rows: {len(rows)}")
        print(f"Verify rows: {len(verify_rows)}")
        for i, row in enumerate(verify_rows):
            print(f"Row {i}: {row}")
    
        # Check that at least one row has 'MODIFIED' in the 'fr' column
        has_modified = any(
            'MODIFIED' in row.get('fr', '')
            for row in verify_rows
        )
        assert has_modified, f"Imported translations should be reflected in export. Got rows: {verify_rows}"
    
    def test_import_translations_with_tool_id(self, imported_flow_tool, tmp_path):
        """Test importing translations using tool ID directly"""
        controller = ToolsController()
        
        # Create a minimal valid CSV
        csv_file = tmp_path / "translations.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'en', 'locale'])
            writer.writerow(['test.key', 'Test Value', 'en'])
        
        # Import using tool ID
        controller.import_flow_translations(
            translation_path=str(csv_file),
            tool_id=imported_flow_tool["id"]
        )
        
        # If no exception, import succeeded


class TestTranslationCLIIntegration:
    """Integration tests for CLI commands"""
    
    def test_cli_export_command(self, flow_json_file_path, tmp_path):
        """
        Test the CLI export command end-to-end using a flow file.
        This test verifies that the controller can export translations from a flow file.
        """
        controller = ToolsController()
        output_file = tmp_path / "cli_export.csv"
        
        # Export using the controller (simulating CLI behavior)
        controller.export_flow_translations(
            file=flow_json_file_path,
            translation_output_path=str(output_file)
        )
        
        assert output_file.exists(), "CLI export should create CSV file"
        assert output_file.stat().st_size > 0, "Exported CSV should not be empty"
    
    def test_cli_import_command(self, imported_flow_tool, tmp_path):
        """Test the CLI import command end-to-end"""
        controller = ToolsController()
        
        # First export to get a valid CSV
        export_file = tmp_path / "for_import.csv"
        controller.export_flow_translations(
            name=imported_flow_tool["name"],
            translation_output_path=str(export_file)
        )
        
        # Run CLI import command
        result = subprocess.run(
            [
                "python", "-m", "ibm_watsonx_orchestrate.cli.main",
                "tools", "translation-import",
                "-k", "flow",
                "--name", imported_flow_tool["name"],
                "--translation", str(export_file)
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONPATH": "src:packages/core:packages/clients:packages/agentic-sdk"
            }
        )
        
        assert result.returncode == 0, f"CLI import failed: {result.stderr}"
    
    def test_cli_import_during_tool_import(self, flow_json_file_path, tmp_path):
        """
        Test that translations can be exported from a flow file and then
        the flow can be imported with those translations.
        
        Note: This test focuses on the export part. Full import-with-translations
        would require additional tool import functionality.
        """
        controller = ToolsController()
        translation_file = tmp_path / "translations_for_import.csv"
        
        # First, export translations from the flow file
        controller.export_flow_translations(
            file=flow_json_file_path,
            translation_output_path=str(translation_file)
        )
        
        assert translation_file.exists(), "Translation file should be created"
        
        # Verify the translation file has valid content
        with open(translation_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 0, "Translation file should have content"
            assert 'path' in content, "Translation file should contain 'path' column"


class TestTranslationErrorHandling:
    """Integration tests for error handling"""
    
    def test_export_nonexistent_tool(self, tmp_path):
        """Test exporting translations for a tool that doesn't exist"""
        controller = ToolsController()
        output_file = tmp_path / "should_fail.csv"
        
        with pytest.raises(Exception):  # Should raise BadParameter or similar
            controller.export_flow_translations(
                name="nonexistent_tool_12345",
                translation_output_path=str(output_file)
            )
    
    def test_import_nonexistent_file(self, imported_flow_tool):
        """Test importing from a file that doesn't exist"""
        controller = ToolsController()
        
        with pytest.raises(Exception):  # Should raise BadParameter
            controller.import_flow_translations(
                translation_path="/nonexistent/path/file.csv",
                name=imported_flow_tool["name"]
            )


    
    def test_builder_client_export_with_identifier(self, imported_flow_tool):
        """Test BuilderClient export_translations with tool identifier"""
        client = instantiate_client(BuilderClient)
        
        response = client.export_translations(
            flow_identifier=imported_flow_tool["id"]
        )
        
        assert response.status_code == 200
        assert len(response.content) > 0


# Run configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

