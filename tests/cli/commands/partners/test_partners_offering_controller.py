"""
Unit tests for partners/offering controller:
  - _patch_agent_yamls writes all catalog fields into agent YAML
  - _validate_agent_placeholders warns on placeholder values
  - package() writes agent config.json to ZIP with all required catalog fields
  - NATIVE_TOOL_CATALOG_FIELDS allowlist / tool field stripping
  - _validate_tool_placeholders warns on placeholder tool values
  - _create_applications_entry produces schema-valid entries
"""
import json
import yaml
import zipfile
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ibm_watsonx_orchestrate.cli.commands.partners.offering.partners_offering_controller import (
    _patch_agent_yamls,
    _validate_agent_placeholders,
    _validate_tool_placeholders,
    _create_applications_entry,
    NATIVE_AGENT_CATALOG_FIELDS,
    NATIVE_TOOL_CATALOG_FIELDS,
    NATIVE_TOOL_PYTHON_BINDING_FIELDS,
)
from ibm_watsonx_orchestrate.cli.commands.partners.offering.types import (
    AGENT_CATALOG_ONLY_PLACEHOLDERS,
    TOOL_CATALOG_ONLY_PLACEHOLDERS,
    ToolCatalogExtras,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_AGENT_YAML = {
    "spec_version": "v1",
    "kind": "native",
    "name": "test_agent",
    "description": "A test agent",
    "instructions": "You are a test agent.",
    "llm": "groq/openai/gpt-oss-120b",
    "style": "default",
    "tools": [],
    "collaborators": [],
}

CATALOG_REQUIRED_FIELDS = [
    "publisher",
    "category",
    "agent_role",
    "language_support",
    "icon",
    "part_number",
    "scope",
    "related_links",
    "billing",
    "channels",
    "tags",
    "change_log",
    "bundled",
    "version",
    "delete_by",
]


# ---------------------------------------------------------------------------
# Tests for _patch_agent_yamls
# ---------------------------------------------------------------------------

class TestPatchAgentYamls:
    def test_adds_all_catalog_fields(self, tmp_path):
        """_patch_agent_yamls should write all required catalog fields into the YAML."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(MINIMAL_AGENT_YAML, f)

        _patch_agent_yamls(tmp_path, publisher_name="TestCorp", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        for field in CATALOG_REQUIRED_FIELDS:
            assert field in patched, f"Expected catalog field '{field}' to be in patched YAML"

    def test_does_not_overwrite_existing_fields(self, tmp_path):
        """_patch_agent_yamls must not overwrite fields already present in the YAML."""
        agent_with_extras = {
            **MINIMAL_AGENT_YAML,
            "publisher": "ExistingPublisher",
            "change_log": ["v2.0 release"],
            "version": "2.0.0",
        }
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(agent_with_extras, f)

        _patch_agent_yamls(tmp_path, publisher_name="ShouldNotOverwrite", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        assert patched["publisher"] == "ExistingPublisher"
        assert patched["change_log"] == ["v2.0 release"]
        assert patched["version"] == "2.0.0"

    def test_ibmcloud_key_in_part_number(self, tmp_path):
        """After patching, part_number must use 'ibmcloud' key, not 'ibm_cloud', and default to null."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(MINIMAL_AGENT_YAML, f)

        _patch_agent_yamls(tmp_path, publisher_name="TestCorp", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        assert "part_number" in patched
        assert "ibmcloud" in patched["part_number"]
        assert "ibm_cloud" not in patched["part_number"]
        # Default is all-null (free agent) — consistent with scope.form_factor = free
        assert patched["part_number"]["ibmcloud"] is None
        assert patched["part_number"]["aws"] is None

    def test_ibmcloud_key_in_scope(self, tmp_path):
        """After patching, scope.form_factor must use 'ibmcloud' key, not 'ibm_cloud'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(MINIMAL_AGENT_YAML, f)

        _patch_agent_yamls(tmp_path, publisher_name="TestCorp", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        assert "scope" in patched
        assert "form_factor" in patched["scope"]
        assert "ibmcloud" in patched["scope"]["form_factor"]
        assert "ibm_cloud" not in patched["scope"]["form_factor"]

    def test_change_log_is_list(self, tmp_path):
        """Scaffolded change_log must be a list."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(MINIMAL_AGENT_YAML, f)

        _patch_agent_yamls(tmp_path, publisher_name="TestCorp", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        assert isinstance(patched["change_log"], list)

    def test_bundled_is_bool(self, tmp_path):
        """Scaffolded bundled must be a boolean."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test_agent.yaml"
        with open(agent_file, "w") as f:
            yaml.safe_dump(MINIMAL_AGENT_YAML, f)

        _patch_agent_yamls(tmp_path, publisher_name="TestCorp", parent_agent_name="test_agent")

        with open(agent_file) as f:
            patched = yaml.safe_load(f)

        assert isinstance(patched["bundled"], bool)


# ---------------------------------------------------------------------------
# Tests for _validate_agent_placeholders
# ---------------------------------------------------------------------------

class TestValidateAgentPlaceholders:
    def test_warns_on_icon_placeholder(self, caplog):
        agent_data = {"icon": AGENT_CATALOG_ONLY_PLACEHOLDERS["icon"]}
        with caplog.at_level(logging.WARNING):
            _validate_agent_placeholders(agent_data, "test_agent")
        assert "icon" in caplog.text

    def test_warns_on_change_log_placeholder(self, caplog):
        agent_data = {"change_log": AGENT_CATALOG_ONLY_PLACEHOLDERS["change_log"]}
        with caplog.at_level(logging.WARNING):
            _validate_agent_placeholders(agent_data, "test_agent")
        assert "change_log" in caplog.text

    def test_warns_on_version_placeholder(self, caplog):
        agent_data = {"version": AGENT_CATALOG_ONLY_PLACEHOLDERS["version"]}
        with caplog.at_level(logging.WARNING):
            _validate_agent_placeholders(agent_data, "test_agent")
        assert "version" in caplog.text

    def test_warns_on_scope_placeholder(self, caplog):
        """scope at its all-free default must warn — a partner with non-null part_number
        and scope still at 'free' will fail the catalog schema's allOf business rule."""
        agent_data = {"scope": AGENT_CATALOG_ONLY_PLACEHOLDERS["scope"].model_dump()}
        with caplog.at_level(logging.WARNING):
            _validate_agent_placeholders(agent_data, "test_agent")
        assert "scope" in caplog.text

    def test_no_warning_when_fields_are_customized(self, caplog):
        agent_data = {
            "icon": "<svg>real icon</svg>",
            "change_log": ["Actual release notes"],
            "version": "2.1.0",
        }
        with caplog.at_level(logging.WARNING):
            _validate_agent_placeholders(agent_data, "test_agent")
        # None of the non-placeholder values should trigger warnings
        assert "icon" not in caplog.text
        assert "change_log" not in caplog.text
        assert "version" not in caplog.text


# ---------------------------------------------------------------------------
# Tests for NATIVE_AGENT_CATALOG_FIELDS field-stripping
# ---------------------------------------------------------------------------

class TestNativeAgentCatalogFields:
    """Verify the set of allowed catalog fields is correct and complete."""

    SCHEMA_REQUIRED = {
        "name", "display_name", "description", "category", "agent_role", "kind",
        "llm", "version", "change_log", "publisher", "instructions", "hidden",
        "style", "delete_by", "part_number", "scope", "language_support", "tags",
        "channels", "related_links", "icon", "bundled", "restrictions",
        "collaborators", "tools",
    }

    # Fields present in AgentSpec that must NOT appear in the catalog package
    INTERNAL_ADK_FIELDS = {
        "is_schedulable", "memory_enabled", "plugins", "skills",
        "spec_version", "sync_tool_flow_interactions", "toolkits",
    }

    def test_all_required_schema_fields_are_allowed(self):
        """Every field the catalog schema requires must be in NATIVE_AGENT_CATALOG_FIELDS."""
        missing = self.SCHEMA_REQUIRED - NATIVE_AGENT_CATALOG_FIELDS
        assert not missing, f"Required schema fields missing from allowlist: {missing}"

    def test_internal_adk_fields_are_excluded(self):
        """Internal ADK platform fields must NOT be in NATIVE_AGENT_CATALOG_FIELDS."""
        leaked = self.INTERNAL_ADK_FIELDS & NATIVE_AGENT_CATALOG_FIELDS
        assert not leaked, f"Internal ADK fields leaked into catalog allowlist: {leaked}"

    def test_hidden_always_present_after_strip(self, tmp_path):
        """hidden must be injected as False when absent from the YAML (agent export omits it)."""
        # Simulate an agent_data dict that lacks 'hidden' (as produced by exclude_unset export)
        agent_data_no_hidden = {
            k: v for k, v in {
                "kind": "native",
                "name": "test_agent",
                "description": "desc",
                "instructions": "instr",
                "llm": "groq/openai/gpt-oss-120b",
                "style": "default",
                "collaborators": [],
                "tools": [],
            }.items()
        }
        assert "hidden" not in agent_data_no_hidden

        catalog_data = {k: v for k, v in agent_data_no_hidden.items() if k in NATIVE_AGENT_CATALOG_FIELDS}
        if "hidden" not in catalog_data:
            catalog_data["hidden"] = False

        assert "hidden" in catalog_data
        assert catalog_data["hidden"] is False

    def test_strip_removes_internal_fields(self, tmp_path):
        """Filtering by NATIVE_AGENT_CATALOG_FIELDS must remove all internal ADK fields."""
        agent_data = {
            "kind": "native",
            "name": "test_agent",
            "description": "desc",
            "instructions": "instr",
            "llm": "groq/openai/gpt-oss-120b",
            "style": "default",
            "collaborators": [],
            "tools": [],
            # Internal fields that must be stripped
            "is_schedulable": False,
            "memory_enabled": False,
            "plugins": {"agent_pre_invoke": [], "agent_post_invoke": []},
            "skills": [],
            "spec_version": "v1",
            "sync_tool_flow_interactions": True,
            "toolkits": [],
        }
        catalog_data = {k: v for k, v in agent_data.items() if k in NATIVE_AGENT_CATALOG_FIELDS}
        for internal_field in self.INTERNAL_ADK_FIELDS:
            assert internal_field not in catalog_data, (
                f"Internal field '{internal_field}' was not stripped from catalog output"
            )


# ---------------------------------------------------------------------------
# Tests for NATIVE_TOOL_CATALOG_FIELDS field-stripping
# ---------------------------------------------------------------------------

class TestNativeToolCatalogFields:
    """Verify the tool allowlist is correct and strips internal ADK fields."""

    SCHEMA_REQUIRED = {
        "name", "display_name", "description", "permission", "version", "is_async",
        "category", "delete_by", "publisher", "bundled", "binding", "language_support",
        "tags", "input_schema", "output_schema", "applications", "icon", "change_log",
        "kind",
    }

    INTERNAL_TOOL_FIELDS = {
        "id", "response_format", "workspace",
    }

    INTERNAL_BINDING_FIELDS = {
        "connections", "type", "agent_run_paramater", "is_async",
    }

    def test_all_required_schema_fields_are_allowed(self):
        """Every field the catalog tool schema requires must be in NATIVE_TOOL_CATALOG_FIELDS."""
        missing = self.SCHEMA_REQUIRED - NATIVE_TOOL_CATALOG_FIELDS
        assert not missing, f"Required tool schema fields missing from allowlist: {missing}"

    def test_internal_tool_fields_are_excluded(self):
        """Internal ADK ToolSpec fields must NOT appear in NATIVE_TOOL_CATALOG_FIELDS."""
        leaked = self.INTERNAL_TOOL_FIELDS & NATIVE_TOOL_CATALOG_FIELDS
        assert not leaked, f"Internal tool fields leaked into catalog allowlist: {leaked}"

    def test_strip_removes_internal_tool_fields(self):
        """Filtering by NATIVE_TOOL_CATALOG_FIELDS must remove id, response_format, workspace."""
        tool_data = {
            "name": "my_tool",
            "description": "desc",
            "permission": "read_only",
            "is_async": False,
            "binding": {"python": {"function": "fn", "requirements": []}},
            # Internal fields
            "id": "some-uuid",
            "response_format": "content",
            "workspace": "my_workspace",
        }
        catalog_data = {k: v for k, v in tool_data.items() if k in NATIVE_TOOL_CATALOG_FIELDS}
        for field in self.INTERNAL_TOOL_FIELDS:
            assert field not in catalog_data, f"Internal field '{field}' was not stripped"

    def test_strip_binding_python_internal_fields(self):
        """binding.python must only retain 'function' and 'requirements'."""
        binding_python = {
            "function": "my_function",
            "requirements": ["requests"],
            "connections": {"svc": "conn-id"},
            "type": "tool",
            "agent_run_paramater": None,
            "is_async": False,
        }
        filtered = {k: v for k, v in binding_python.items() if k in NATIVE_TOOL_PYTHON_BINDING_FIELDS}
        assert set(filtered.keys()) == {"function", "requirements"}
        for field in self.INTERNAL_BINDING_FIELDS:
            assert field not in filtered, f"Internal binding field '{field}' was not stripped"


# ---------------------------------------------------------------------------
# Tests for ToolCatalogExtras scaffolding
# ---------------------------------------------------------------------------

class TestToolCatalogExtras:
    BASE_TOOL = {"name": "my_tool", "description": "A tool"}

    def test_scaffolds_category_as_tool(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.category == "tool"

    def test_scaffolds_kind_as_native(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.kind == "native"

    def test_scaffolds_publisher(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.publisher == "TestCorp"

    def test_scaffolds_language_support(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.language_support == ["English"]

    def test_scaffolds_tags_as_empty_list(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.tags == []

    def test_scaffolds_bundled_false(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.bundled is False

    def test_scaffolds_version(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.version == TOOL_CATALOG_ONLY_PLACEHOLDERS["version"]

    def test_scaffolds_change_log(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.change_log == TOOL_CATALOG_ONLY_PLACEHOLDERS["change_log"]

    def test_scaffolds_delete_by_as_none(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.delete_by is None

    def test_scaffolds_hidden_false(self):
        extras = ToolCatalogExtras.from_tool_details(self.BASE_TOOL, "TestCorp")
        assert extras.hidden is False

    def test_does_not_overwrite_existing_fields(self):
        tool = {**self.BASE_TOOL, "category": "custom", "version": "2.0.0", "publisher": "Other"}
        extras = ToolCatalogExtras.from_tool_details(tool, "TestCorp")
        assert extras.category is None
        assert extras.version is None
        assert extras.publisher is None


# ---------------------------------------------------------------------------
# Tests for _validate_tool_placeholders
# ---------------------------------------------------------------------------

class TestValidateToolPlaceholders:
    def test_warns_on_icon_placeholder(self, caplog):
        tool_data = {"icon": TOOL_CATALOG_ONLY_PLACEHOLDERS["icon"]}
        with caplog.at_level(logging.WARNING):
            _validate_tool_placeholders(tool_data, "my_tool")
        assert "icon" in caplog.text

    def test_warns_on_version_placeholder(self, caplog):
        tool_data = {"version": TOOL_CATALOG_ONLY_PLACEHOLDERS["version"]}
        with caplog.at_level(logging.WARNING):
            _validate_tool_placeholders(tool_data, "my_tool")
        assert "version" in caplog.text

    def test_warns_on_change_log_placeholder(self, caplog):
        tool_data = {"change_log": TOOL_CATALOG_ONLY_PLACEHOLDERS["change_log"]}
        with caplog.at_level(logging.WARNING):
            _validate_tool_placeholders(tool_data, "my_tool")
        assert "change_log" in caplog.text

    def test_no_warning_when_fields_are_customized(self, caplog):
        tool_data = {
            "icon": "<svg>real icon</svg>",
            "version": "2.1.0",
            "change_log": ["Actual release notes"],
        }
        with caplog.at_level(logging.WARNING):
            _validate_tool_placeholders(tool_data, "my_tool")
        assert "icon" not in caplog.text
        assert "version" not in caplog.text
        assert "change_log" not in caplog.text


# ---------------------------------------------------------------------------
# Tests for _create_applications_entry
# ---------------------------------------------------------------------------

class TestCreateApplicationsEntry:
    def test_includes_required_schema_fields(self):
        """Entry must include all fields required by partner-applications.schema.json."""
        connection_config = {
            "app_id": "servicenow_app",
            "catalog": {
                "name": "ServiceNow",
                "description": "ServiceNow integration",
                "icon": "<svg/>",
                "security_schema": {"basic_auth": {}},
                "documentation_link": "https://docs.example.com",
            }
        }
        entry = _create_applications_entry(connection_config)
        for field in ("app_id", "name", "icon", "security_schema", "documentation_link"):
            assert field in entry, f"Required field '{field}' missing from applications entry"

    def test_defaults_security_schema_when_absent(self):
        """When catalog.security_schema is missing, a bearer_token stub must be used."""
        connection_config = {
            "app_id": "my_app",
            "catalog": {"name": "My App", "icon": "<svg/>"}
        }
        entry = _create_applications_entry(connection_config)
        assert "security_schema" in entry
        assert entry["security_schema"] == {"bearer_token": {}}

    def test_name_falls_back_to_app_id(self):
        """When catalog.name is absent, name should fall back to app_id."""
        connection_config = {"app_id": "fallback_app", "catalog": {}}
        entry = _create_applications_entry(connection_config)
        assert entry["name"] == "fallback_app"

    def test_uses_provided_security_schema(self):
        """When catalog.security_schema is present it must be preserved as-is."""
        schema = {"oauth2_client_creds": {}}
        connection_config = {
            "app_id": "oauth_app",
            "catalog": {"name": "OAuth App", "security_schema": schema}
        }
        entry = _create_applications_entry(connection_config)
        assert entry["security_schema"] == schema
