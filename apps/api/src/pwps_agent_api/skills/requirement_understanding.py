"""Requirement understanding skill — extracts fields from natural language input.

Refactored to:
- Load prompt template from DomainSpec
- Dynamically generate extraction schema from FieldRegistry
- Keep lightweight regex fallback for no-LLM environments
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, create_model

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.schemas import FieldState, FieldStatus, SourceType


def _build_extraction_model(registry: FieldRegistry) -> type[BaseModel]:
    """Dynamically build a Pydantic model for field extraction from the registry.

    Includes all fields that are required_for_start=True or have examples,
    which are likely to appear in user input.
    """
    fields: dict[str, Any] = {}
    for name, spec in registry.fields.items():
        # Include fields that users typically provide in initial input
        if spec.required_for_start or spec.examples:
            description = spec.description
            if spec.examples:
                description += f" Examples: {', '.join(spec.examples)}"
            if spec.enum_values:
                description += f" One of: {', '.join(spec.enum_values)}"
            fields[name] = (str | None, Field(None, description=description))

    return create_model("ExtractedFields", **fields)


@dataclass(frozen=True)
class RequirementUnderstandingSkill:
    """Extracts structured field values from user's natural language input."""

    skill_name: str = "requirement_understanding"
    skill_version: str = "0.3.0"
    prompt_version: str = "0.3.0"

    async def run(
        self,
        raw_input: str,
        domain: DomainSpec | None = None,
        registry: FieldRegistry | None = None,
    ) -> dict[str, FieldState]:
        """Extract fields from user input.

        Args:
            raw_input: User's natural language description.
            domain: Domain pack for prompt template. If None, uses default prompt.
            registry: Field registry for dynamic schema generation. If None, uses default.

        Returns:
            Mapping of field_name -> FieldState for extracted fields.
        """
        # Resolve registry
        if registry is None:
            from pwps_agent_api.fields import load_default_field_registry
            registry = load_default_field_registry()

        # Resolve prompt
        prompt = domain.get_prompt("requirement_understanding") if domain else None
        if prompt is None:
            prompt = _DEFAULT_PROMPT

        # Build dynamic extraction model from registry
        ExtractedFields = _build_extraction_model(registry)

        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback_extract(raw_input, registry)

        model = get_chat_model()
        structured_model = model.with_structured_output(ExtractedFields, method="json_mode")

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=raw_input),
        ]
        try:
            raw = await structured_model.ainvoke(messages)
        except Exception:
            return self._fallback_extract(raw_input, registry)
        extracted = ExtractedFields.model_validate(raw)

        result: dict[str, FieldState] = {}
        for field_name, value in extracted.model_dump(exclude_none=True).items():
            if value is not None and field_name in registry.fields:
                spec = registry.fields[field_name]
                result[field_name] = FieldState(
                    name=field_name,
                    group=spec.group,
                    value=value,
                    status=FieldStatus.PROVIDED,
                    source_type=SourceType.USER_INPUT,
                    inference_policy=spec.inference_policy,
                    confidence=1.0,
                )
        return result

    def _fallback_extract(
        self, raw_input: str, registry: FieldRegistry
    ) -> dict[str, FieldState]:
        """Lightweight regex fallback when no LLM API key is configured."""
        extracted: dict[str, str] = {}

        # Material grade pattern
        material_match = re.search(r"Q\d{3}[A-Z]?", raw_input, flags=re.IGNORECASE)
        if material_match:
            extracted["base_material"] = material_match.group(0).upper()

        # Thickness pattern
        thickness_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", raw_input, flags=re.IGNORECASE)
        if thickness_match:
            extracted["thickness"] = f"{thickness_match.group(1)}mm"

        # Welding process
        for process in ("GMAW", "SMAW", "GTAW", "SAW"):
            if process in raw_input.upper():
                extracted["welding_process"] = process
                break

        # Joint type (Chinese)
        if "对接" in raw_input:
            extracted["joint_type"] = "对接焊"

        # Welding position (Chinese)
        if "平焊" in raw_input:
            extracted["welding_position"] = "平焊"

        result: dict[str, FieldState] = {}
        for field_name, value in extracted.items():
            if field_name in registry.fields:
                spec = registry.fields[field_name]
                result[field_name] = FieldState(
                    name=field_name,
                    group=spec.group,
                    value=value,
                    status=FieldStatus.PROVIDED,
                    source_type=SourceType.USER_INPUT,
                    inference_policy=spec.inference_policy,
                    confidence=1.0,
                )
        return result


# Default prompt used when no domain pack provides one
_DEFAULT_PROMPT = """You are a welding procedure requirement extraction assistant.
Given a user's natural-language description of welding requirements, extract the
explicitly mentioned fields. Return ONLY the fields the user explicitly provided;
do NOT infer or guess values that were not stated.

If the user does not explicitly mention a field, do NOT include it in the output."""
