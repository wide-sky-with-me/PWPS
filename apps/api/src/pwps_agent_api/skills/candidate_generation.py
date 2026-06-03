"""Candidate generation skill — generates candidate field values.

Refactored to:
- Load prompt template from DomainSpec
- Use domain.default_prior instead of hardcoded _DEFAULT_VALUES
- Support tool-calling for knowledge retrieval
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.guard import GuardValidator
from pwps_agent_api.schemas import Evidence, FieldState, FieldStatus, InferencePolicy

CandidateBundle = dict[str, list[dict[str, Any]]]


class FieldCandidate(BaseModel):
    """A single candidate value for a field."""

    value: Any = Field(description="The candidate value")
    confidence: float = Field(ge=0, le=1, description="Confidence score")
    reason: str = Field(description="Why this candidate is suggested")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence IDs")
    risks: list[str] = Field(default_factory=list, description="Known risks or caveats")


class CandidateResponse(BaseModel):
    """Structured response for candidate generation."""

    candidates: dict[str, list[FieldCandidate]] = Field(
        description="Map of field name to list of candidates"
    )


# Legacy fallback values (used only when no domain pack is loaded)
_LEGACY_DEFAULT_VALUES: dict[str, str | dict[str, str]] = {
    "consumable": "ER50-6",
    "consumable_specification": "1.2mm",
    "shielding_gas": "Ar+CO2",
    "current_range": {"min": "180A", "max": "240A"},
    "voltage_range": {"min": "22V", "max": "28V"},
    "travel_speed": {"min": "25cm/min", "max": "35cm/min"},
    "heat_input": {"min": "0.8kJ/mm", "max": "1.6kJ/mm"},
    "polarity": "DCEP",
    "preheat_temperature": "not required by MVP prior",
    "interpass_temperature": "max 250degC",
    "pwht": "not specified by MVP prior",
}

_DEFAULT_PROMPT = """You are a welding procedure candidate generation assistant.
Given a set of target fields, existing field states, and supporting evidence,
generate candidate values for each field that needs a value.

Rules:
- Skip fields with InferencePolicy PROVIDED_ONLY (they must come from the user).
- Skip fields that already have a CONFIRMED value (unless status is NEEDS_REPAIR).
- For each remaining field, generate 1-3 candidate values with confidence and reasoning.
- Base candidates on the provided evidence when available; otherwise use domain knowledge.
- Each candidate must include: value, confidence (0-1), reason, evidence_ids, risks.

Output a JSON object where keys are field names and values are lists of candidates."""


@dataclass(frozen=True)
class CandidateGenerationSkill:
    """Generates candidate values for fields that need values."""

    skill_name: str = "candidate_generation"
    skill_version: str = "0.3.0"
    prompt_version: str = "0.3.0"

    async def run(
        self,
        *,
        target_fields: list[str],
        field_states: dict[str, FieldState],
        evidence: list[Evidence],
        registry: FieldRegistry,
        domain: DomainSpec | None = None,
    ) -> CandidateBundle:
        """Generate candidate values for target fields.

        Args:
            target_fields: Fields that need candidate values.
            field_states: Current workflow field states.
            evidence: Available evidence from knowledge retrieval.
            registry: Field registry for field specs.
            domain: Domain pack for prompt template and default priors.
        """
        fields_needing_candidates = self._fields_needing_candidates(
            target_fields, field_states, registry
        )
        if not fields_needing_candidates:
            return {}

        # Resolve default prior from domain pack or legacy fallback
        default_prior = _LEGACY_DEFAULT_VALUES
        if domain is not None and domain.default_prior:
            default_prior = {
                k: v.get("value", v) if isinstance(v, dict) else v
                for k, v in domain.default_prior.items()
            }

        settings = get_settings()
        if not settings.llm_api_key:
            candidates = self._fallback_generate(
                fields_needing_candidates, evidence, registry, default_prior
            )
        else:
            # Resolve prompt from domain pack
            prompt = domain.get_prompt("candidate_generation") if domain else None
            if prompt is None:
                prompt = _DEFAULT_PROMPT

            candidates = await self._llm_generate(
                fields_needing_candidates, field_states, evidence, registry, prompt
            )

        # Filter invalid candidates using GuardValidator
        return self._filter_invalid_candidates(candidates, registry)

    def _fields_needing_candidates(
        self,
        target_fields: list[str],
        field_states: dict[str, FieldState],
        registry: FieldRegistry,
    ) -> list[str]:
        result: list[str] = []
        for field_name in target_fields:
            spec = registry.get_field(field_name)
            if spec.inference_policy is InferencePolicy.PROVIDED_ONLY:
                continue
            if field_name not in field_states:
                result.append(field_name)
            elif field_states[field_name].status is FieldStatus.NEEDS_REPAIR:
                result.append(field_name)
        return result

    def _filter_invalid_candidates(
        self,
        candidates: CandidateBundle,
        registry: FieldRegistry,
    ) -> CandidateBundle:
        """Filter out invalid candidates using GuardValidator."""
        guard = GuardValidator()
        filtered: CandidateBundle = {}

        for field_name, field_candidates in candidates.items():
            spec = registry.get_field(field_name)
            valid_candidates = []
            for candidate in field_candidates:
                violations = guard.validate_candidate(field_name, candidate, spec)
                # Only keep candidates without error-level violations
                has_errors = any(v.severity == "error" for v in violations)
                if not has_errors:
                    valid_candidates.append(candidate)
            if valid_candidates:
                filtered[field_name] = valid_candidates

        return filtered

    def _fallback_generate(
        self,
        fields_needing_candidates: list[str],
        evidence: list[Evidence],
        registry: FieldRegistry,
        default_prior: dict[str, Any],
    ) -> CandidateBundle:
        """Deterministic fallback using domain default priors."""
        evidence_by_field: dict[str, list[str]] = {}
        for item in evidence:
            for field_name in item.target_fields:
                if field_name in fields_needing_candidates:
                    evidence_by_field.setdefault(field_name, []).append(item.evidence_id)

        result: CandidateBundle = {}
        for field_name in fields_needing_candidates:
            value = default_prior.get(field_name)
            if value is None:
                continue
            result[field_name] = [
                {
                    "value": value,
                    "confidence": 0.35,
                    "reason": (
                        "Candidate backed by attached evidence."
                        if evidence_by_field.get(field_name)
                        else "Low-confidence candidate from domain prior. Requires human review."
                    ),
                    "evidence_ids": evidence_by_field.get(field_name, []),
                    "risks": [
                        "Low-confidence prior value. Requires qualified welding engineer review."
                    ],
                }
            ]
        return result

    async def _llm_generate(
        self,
        fields_needing_candidates: list[str],
        field_states: dict[str, FieldState],
        evidence: list[Evidence],
        registry: FieldRegistry,
        prompt_template: str,
    ) -> CandidateBundle:
        """LLM-powered candidate generation."""
        evidence_by_field: dict[str, list[str]] = {}
        for item in evidence:
            for field_name in item.target_fields:
                if field_name in fields_needing_candidates:
                    evidence_by_field.setdefault(field_name, []).append(item.evidence_id)

        field_specs = {name: registry.get_field(name) for name in fields_needing_candidates}

        context_parts = []
        for field_name in fields_needing_candidates:
            spec = field_specs[field_name]
            context_parts.append(
                f"- {field_name} ({spec.label}): {spec.description}"
                f"\n  Type: {spec.field_type}, Unit: {spec.unit or 'N/A'}"
                f"\n  Enum values: {spec.enum_values or 'N/A'}"
                f"\n  High risk: {spec.high_risk}"
            )

        relevant_evidence = [
            item
            for item in evidence
            if any(f in fields_needing_candidates for f in item.target_fields)
        ]
        evidence_text = ""
        if relevant_evidence:
            evidence_text = "\n\nRelevant evidence:\n" + "\n".join(
                f"- [{item.source_type.value}] {item.source_title}: {item.content[:200]}"
                for item in relevant_evidence
            )

        confirmed = {
            name: state.value for name, state in field_states.items() if state.value is not None
        }
        context_str = (
            "; ".join(f"{n}={v}" for n, v in confirmed.items())
            if confirmed
            else "No fields confirmed yet."
        )

        user_prompt = (
            f"Generate candidates for these welding procedure fields:\n\n"
            f"{chr(10).join(context_parts)}"
            f"{evidence_text}\n\n"
            f"Material context: {context_str}"
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(CandidateResponse)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(content=user_prompt),
        ]
        try:
            raw = await structured_model.ainvoke(messages)
        except Exception:
            return self._fallback_generate(
                fields_needing_candidates, evidence, registry, _LEGACY_DEFAULT_VALUES
            )
        response = CandidateResponse.model_validate(raw)

        result: CandidateBundle = {}
        for field_name, candidates in response.candidates.items():
            if field_name not in fields_needing_candidates:
                continue
            result[field_name] = [
                {
                    "value": c.value,
                    "confidence": c.confidence,
                    "reason": c.reason,
                    "evidence_ids": c.evidence_ids or evidence_by_field.get(field_name, []),
                    "risks": c.risks or ["Requires qualified welding engineer review."],
                }
                for c in candidates
            ]
        return result
