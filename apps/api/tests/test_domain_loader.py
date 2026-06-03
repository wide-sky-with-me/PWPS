"""Tests for domain pack loading."""

import os
import pytest
from pathlib import Path

from pwps_agent_api.domain.loader import load_domain, list_domains
from pwps_agent_api.domain.spec import DomainSpec


DOMAINS_DIR = str(Path(__file__).resolve().parents[2] / "domains")


@pytest.fixture(autouse=True)
def _set_domain_path(monkeypatch: pytest.MonkeyPatch):
    """Set PWPS_DOMAIN_PATH to the test domains directory."""
    monkeypatch.setenv("PWPS_DOMAIN_PATH", DOMAINS_DIR)


class TestDomainDiscovery:
    def test_list_domains_finds_welding(self):
        domains = list_domains()
        assert "welding" in domains

    def test_load_domain_returns_domain_spec(self):
        domain = load_domain("welding")
        assert isinstance(domain, DomainSpec)
        assert domain.name == "welding"
        assert domain.version == "1.0.0"


class TestFieldRegistryFromDomain:
    def test_domain_has_all_fields(self):
        domain = load_domain("welding")
        assert len(domain.field_registry.fields) == 19

    def test_domain_has_all_groups(self):
        domain = load_domain("welding")
        assert len(domain.field_registry.groups) == 5

    def test_domain_field_groups_are_valid(self):
        domain = load_domain("welding")
        # Should not raise
        domain.field_registry.validate_group_references()

    def test_domain_has_required_fields(self):
        domain = load_domain("welding")
        required = [f for f in domain.field_registry.fields.values() if f.required_for_start]
        assert len(required) >= 5  # base_material, thickness, welding_process, joint_type, welding_position


class TestPromptTemplates:
    def test_domain_has_all_prompts(self):
        domain = load_domain("welding")
        expected = [
            "requirement_understanding",
            "candidate_generation",
            "field_planning",
            "audit",
            "risk_summary",
            "override_evaluation",
        ]
        for name in expected:
            assert name in domain.prompt_templates, f"Missing prompt: {name}"

    def test_prompts_are_non_empty(self):
        domain = load_domain("welding")
        for name, content in domain.prompt_templates.items():
            assert len(content) > 0, f"Prompt '{name}' is empty"


class TestAuditDimensions:
    def test_domain_has_audit_dimensions(self):
        domain = load_domain("welding")
        assert len(domain.audit_dimensions) == 5
        assert "工艺兼容性" in domain.audit_dimensions


class TestDefaultPrior:
    def test_domain_has_default_prior(self):
        domain = load_domain("welding")
        assert len(domain.default_prior) > 0
        assert "consumable" in domain.default_prior

    def test_default_prior_has_confidence(self):
        domain = load_domain("welding")
        for field_name, prior in domain.default_prior.items():
            assert "value" in prior, f"Prior '{field_name}' missing 'value'"
            assert "confidence" in prior, f"Prior '{field_name}' missing 'confidence'"


class TestDomainSpecHelpers:
    def test_get_prompt_returns_content(self):
        domain = load_domain("welding")
        prompt = domain.get_prompt("audit")
        assert prompt is not None
        assert "审计" in prompt or "audit" in prompt.lower()

    def test_get_prompt_returns_none_for_missing(self):
        domain = load_domain("welding")
        assert domain.get_prompt("nonexistent") is None

    def test_get_render_template_returns_none_for_missing(self):
        domain = load_domain("welding")
        assert domain.get_render_template("nonexistent") is None
