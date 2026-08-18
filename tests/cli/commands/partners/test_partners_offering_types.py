"""
Unit tests for partners/offering types:
  - OfferingPartNumber / OfferingFormFactor field naming (ibmcloud not ibm_cloud)
  - OfferingRelatedLinkTypes enum value (embedded not embeded)
  - OfferingAgentExtras.from_agent_details scaffolding of required catalog fields
"""
import pytest
from ibm_watsonx_orchestrate.cli.commands.partners.offering.types import (
    OfferingPartNumber,
    OfferingFormFactor,
    OfferingRelatedLinkTypes,
    OfferingAgentExtras,
    AGENT_CATALOG_ONLY_PLACEHOLDERS,
)


class TestOfferingPartNumber:
    """Tests for :class:`OfferingPartNumber` — verifies correct field naming (``ibmcloud`` not ``ibm_cloud``)."""

    def test_ibmcloud_field_name(self):
        """OfferingPartNumber must serialize with key 'ibmcloud', not 'ibm_cloud'."""
        pn = OfferingPartNumber(aws="D111", ibmcloud="D222", cp4d=None)
        dumped = pn.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped
        assert dumped["ibmcloud"] == "D222"

    def test_ibmcloud_default(self):
        """Default OfferingPartNumber uses the placeholder value for ibmcloud."""
        pn = OfferingPartNumber()
        dumped = pn.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped


class TestOfferingFormFactor:
    """Tests for :class:`OfferingFormFactor` — verifies correct field naming (``ibmcloud`` not ``ibm_cloud``)."""

    def test_ibmcloud_field_name(self):
        """OfferingFormFactor must serialize with key 'ibmcloud', not 'ibm_cloud'."""
        ff = OfferingFormFactor(aws="free", ibmcloud="paid", cp4d="free")
        dumped = ff.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped
        assert dumped["ibmcloud"] == "paid"

    def test_ibmcloud_default(self):
        """Default OfferingFormFactor uses the placeholder value for ibmcloud."""
        ff = OfferingFormFactor()
        dumped = ff.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped


class TestOfferingRelatedLinkTypes:
    """Tests for :class:`OfferingRelatedLinkTypes` — verifies enum values, including the old ``embeded`` typo fix."""

    def test_embedded_value(self):
        """EMBEDDED enum member must have value 'embedded' (not the old typo 'embeded')."""
        assert OfferingRelatedLinkTypes.EMBEDDED == "embedded"
        assert str(OfferingRelatedLinkTypes.EMBEDDED) == "embedded"

    def test_hyperlink_value(self):
        assert OfferingRelatedLinkTypes.HYPERLINK == "hyperlink"

    def test_no_embeded_typo(self):
        """The old misspelled EMBEDED member must not exist."""
        assert not hasattr(OfferingRelatedLinkTypes, "EMBEDED")


class TestOfferingAgentExtrasScaffolding:
    """Tests for :meth:`OfferingAgentExtras.from_agent_details` — scaffolds missing required catalog fields."""

    BASE_AGENT = {
        "name": "test_agent",
        "kind": "native",
        "description": "A test agent",
    }

    def test_scaffolds_change_log(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.change_log == AGENT_CATALOG_ONLY_PLACEHOLDERS["change_log"]

    def test_scaffolds_bundled(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.bundled is False

    def test_scaffolds_version(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.version == AGENT_CATALOG_ONLY_PLACEHOLDERS["version"]

    def test_scaffolds_delete_by_as_none(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.delete_by is None

    def test_does_not_overwrite_existing_change_log(self):
        agent = {**self.BASE_AGENT, "change_log": ["Bug fix", "New feature"]}
        extras = OfferingAgentExtras.from_agent_details(agent, "TestCorp", "test_agent")
        assert extras.change_log is None  # field not set on extras when already present

    def test_does_not_overwrite_existing_bundled(self):
        agent = {**self.BASE_AGENT, "bundled": True}
        extras = OfferingAgentExtras.from_agent_details(agent, "TestCorp", "test_agent")
        assert extras.bundled is None  # field not set on extras when already present

    def test_does_not_overwrite_existing_version(self):
        agent = {**self.BASE_AGENT, "version": "2.3.1"}
        extras = OfferingAgentExtras.from_agent_details(agent, "TestCorp", "test_agent")
        assert extras.version is None  # field not set on extras when already present

    def test_scaffolds_publisher(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.publisher == "TestCorp"

    def test_scaffolds_category(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.category == "agent"

    def test_scaffolds_language_support(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.language_support == ["English"]

    def test_related_links_keys_are_capitalized(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.related_links is not None
        for link in extras.related_links:
            assert link.key[0].isupper(), f"Link key '{link.key}' must start with a capital letter"
            assert "_" not in link.key, f"Link key '{link.key}' must not contain underscores"

    def test_related_links_embedded_type_is_correct(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.related_links is not None
        for link in extras.related_links:
            assert link.type in ("hyperlink", "embedded"), (
                f"Link type '{link.type}' is invalid (must be 'hyperlink' or 'embedded')"
            )

    def test_part_number_uses_ibmcloud_key(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.part_number is not None
        dumped = extras.part_number.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped
        # Default is all-null (free agent) — not "my-part-number"
        assert dumped["ibmcloud"] is None
        assert dumped["aws"] is None
        assert dumped["cp4d"] is None

    def test_scope_form_factor_uses_ibmcloud_key(self):
        extras = OfferingAgentExtras.from_agent_details(self.BASE_AGENT, "TestCorp", "test_agent")
        assert extras.scope is not None
        dumped = extras.scope.form_factor.model_dump()
        assert "ibmcloud" in dumped
        assert "ibm_cloud" not in dumped
