"""Tests for domain pack loading."""

from pathlib import Path

import pytest

from pwps_agent_api.domain.loader import list_domains, load_domain
from pwps_agent_api.domain.spec import DomainSpec

DOMAINS_DIR = str(Path(__file__).resolve().parents[2] / "domains")


@pytest.fixture(autouse=True)
def _set_domain_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set PWPS_DOMAIN_PATH to the test domains directory."""
    monkeypatch.setenv("PWPS_DOMAIN_PATH", DOMAINS_DIR)


class TestDomainDiscovery:
    def test_list_domains_finds_welding(self) -> None:
        domains = list_domains()
        assert "welding" in domains

    def test_load_domain_returns_domain_spec(self) -> None:
        domain = load_domain("welding")
        assert isinstance(domain, DomainSpec)
        assert domain.name == "welding"
        assert domain.version == "1.0.0"


class TestFieldRegistryFromDomain:
    def test_domain_has_all_fields(self) -> None:
        domain = load_domain("welding")
        assert len(domain.field_registry.fields) == 19

    def test_domain_has_all_groups(self) -> None:
        domain = load_domain("welding")
        assert len(domain.field_registry.groups) == 5

    def test_domain_field_groups_are_valid(self) -> None:
        domain = load_domain("welding")
        # Should not raise — model_validator runs on construction
        # Calling explicitly to verify no cross-field issues
        domain.field_registry.validate_group_references()  # type: ignore[operator]

    def test_domain_has_required_fields(self) -> None:
        domain = load_domain("welding")
        required = [
            f for f in domain.field_registry.fields.values() if f.required_for_start
        ]
        # base_material, thickness, welding_process, joint_type, welding_position
        assert len(required) >= 5


class TestPromptTemplates:
    def test_domain_has_all_prompts(self) -> None:
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

    def test_prompts_are_non_empty(self) -> None:
        domain = load_domain("welding")
        for name, content in domain.prompt_templates.items():
            assert len(content) > 0, f"Prompt '{name}' is empty"


class TestAuditDimensions:
    def test_domain_has_audit_dimensions(self) -> None:
        domain = load_domain("welding")
        assert len(domain.audit_dimensions) == 5
        assert "工艺兼容性" in domain.audit_dimensions


class TestDefaultPrior:
    def test_domain_has_default_prior(self) -> None:
        domain = load_domain("welding")
        assert len(domain.default_prior) > 0
        assert "consumable" in domain.default_prior

    def test_default_prior_has_confidence(self) -> None:
        domain = load_domain("welding")
        for field_name, prior in domain.default_prior.items():
            assert "value" in prior, f"Prior '{field_name}' missing 'value'"
            assert "confidence" in prior, f"Prior '{field_name}' missing 'confidence'"


class TestDomainSpecHelpers:
    def test_get_prompt_returns_content(self) -> None:
        domain = load_domain("welding")
        prompt = domain.get_prompt("audit")
        assert prompt is not None
        assert "审计" in prompt or "audit" in prompt.lower()

    def test_get_prompt_returns_none_for_missing(self) -> None:
        domain = load_domain("welding")
        assert domain.get_prompt("nonexistent") is None

    def test_get_render_template_returns_none_for_missing(self) -> None:
        domain = load_domain("welding")
        assert domain.get_render_template("nonexistent") is None
