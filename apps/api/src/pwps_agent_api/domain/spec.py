"""DomainSpec — the contract between the framework and a domain pack.

A DomainSpec is a frozen dataclass that bundles all domain-specific
configuration: field definitions, prompt templates, audit dimensions,
default priors, render templates, and optional seed documents.

The framework loads a DomainSpec at startup and passes it through the
workflow.  Skills read prompt templates from it; the knowledge layer
uses its default priors as a soft fallback; the output layer uses its
render templates for final document rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pwps_agent_api.fields import FieldRegistry


@dataclass(frozen=True)
class DomainSpec:
    """Unified domain configuration loaded from a domain pack."""

    # --- Identity ---
    name: str
    """Domain identifier, e.g. 'welding', 'pressure_vessel'."""

    version: str
    """Semantic version of the domain pack, e.g. '1.0.0'."""

    # --- Schema layer ---
    field_registry: FieldRegistry
    """Field definitions, groups, dependencies, and policies."""

    # --- Prompt layer ---
    prompt_templates: dict[str, str] = field(default_factory=dict)
    """Mapping of skill name -> prompt template content (markdown).

    Keys correspond to skill names: 'requirement_understanding',
    'candidate_generation', 'field_planning', 'audit', 'risk_summary', etc.
    """

    audit_dimensions: list[str] = field(default_factory=list)
    """Ordered list of audit dimension names for the audit prompt.

    Example: ['工艺兼容性', '参数完整性', '热过程合规性', '证据充分性', '字段约束']
    The audit skill queries rules by these dimensions.
    """

    # --- Knowledge layer ---
    default_prior: dict[str, Any] = field(default_factory=dict)
    """Soft fallback values for candidate generation.

    Used when the knowledge retrieval returns no results.  Values are
    marked with low confidence (source_type=MODEL_PRIOR) so the guard
    layer flags them for human review.

    Structure: {field_name: value_or_dict}
    Example: {'consumable': 'ER50-6', 'current_range': {'min': '180A', 'max': '240A'}}
    """

    seed_documents: list[Path] = field(default_factory=list)
    """Optional paths to seed knowledge documents for ingestion.

    When the domain pack is installed, these documents can be
    automatically ingested into the vector store.
    """

    # --- Output layer ---
    render_templates: dict[str, str] = field(default_factory=dict)
    """Mapping of output name -> render template content.

    Used by the output layer to produce domain-specific documents
    (e.g., WPS table, PDF report) from the generic WorkflowState.
    """

    def get_prompt(self, skill_name: str) -> str | None:
        """Return the prompt template for a skill, or None if not found."""
        return self.prompt_templates.get(skill_name)

    def get_render_template(self, name: str) -> str | None:
        """Return a render template by name, or None if not found."""
        return self.render_templates.get(name)
