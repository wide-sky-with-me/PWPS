"""Audit engine — validates field states against domain rules.

Refactored to support two modes:
1. Deterministic mode: fast rule-based checks (legacy, for fallback)
2. LLM mode: LLM-driven audit with knowledge retrieval (primary)

The LLM mode uses the audit prompt template from the domain pack
and queries the knowledge base for specific audit rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.schemas import (
    AuditIssue,
    AuditResult,
    AuditRuleType,
    Evidence,
    FieldState,
    FieldStatus,
    InferencePolicy,
    Publishability,
    RiskLevel,
    SourceType,
)


class LLMAuditIssue(BaseModel):
    """Single audit issue from LLM audit."""

    issue_id: str = Field(description="Unique identifier for the issue")
    rule_type: str = Field(description="hard, risk, or completeness")
    severity: str = Field(description="high, medium, or low")
    target_fields: list[str] = Field(description="Affected field names")
    description: str = Field(description="Human-readable description")
    recommended_action: str = Field(description="What to do about it")
    repair_target: str = Field(description="Which field group to revisit")


class LLMAuditResponse(BaseModel):
    """Structured response from LLM audit."""

    issues: list[LLMAuditIssue] = Field(default_factory=list)
    summary: str = Field(description="Overall audit summary")


# Default audit prompt (used when no domain pack provides one)
_DEFAULT_AUDIT_PROMPT = """You are a welding procedure audit expert.
Review the current field states for a pWPS draft and identify issues.

Check these dimensions:
1. Process compatibility (welding_process + consumable, position)
2. Parameter completeness (current, voltage, speed)
3. Thermal compliance (preheat, interpass, PWHT evidence)
4. Evidence sufficiency (high-risk fields need credible evidence)
5. Field constraints (PROVIDED_ONLY fields, required fields)

For each issue found, provide:
- issue_id, rule_type (hard/risk/completeness), severity (high/medium/low)
- target_fields, description, recommended_action, repair_target"""


@dataclass(frozen=True)
class AuditEngine:
    """Validates field states against domain rules."""

    audit_version: str = "0.2.0"

    def audit(
        self,
        field_states: dict[str, FieldState],
        registry: FieldRegistry,
        evidence_store: dict[str, Evidence] | None = None,
        domain: DomainSpec | None = None,
    ) -> AuditResult:
        """Run audit — uses LLM if available, falls back to deterministic."""
        settings = get_settings()
        if settings.llm_api_key and domain is not None:
            # LLM mode: deep reasoning with knowledge retrieval
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, we can't use asyncio.run
                    # Fall back to deterministic mode
                    return self._deterministic_audit(field_states, registry, evidence_store)
                return asyncio.run(
                    self._llm_audit(field_states, registry, evidence_store or {}, domain)
                )
            except Exception:
                return self._deterministic_audit(field_states, registry, evidence_store)

        # Deterministic mode: fast rule-based checks
        return self._deterministic_audit(field_states, registry, evidence_store)

    async def async_audit(
        self,
        field_states: dict[str, FieldState],
        registry: FieldRegistry,
        evidence_store: dict[str, Evidence] | None = None,
        domain: DomainSpec | None = None,
    ) -> AuditResult:
        """Async audit — always uses LLM when available."""
        settings = get_settings()
        if settings.llm_api_key and domain is not None:
            try:
                return await self._llm_audit(field_states, registry, evidence_store or {}, domain)
            except Exception:
                return self._deterministic_audit(field_states, registry, evidence_store)

        return self._deterministic_audit(field_states, registry, evidence_store)

    async def _llm_audit(
        self,
        field_states: dict[str, FieldState],
        registry: FieldRegistry,
        evidence_store: dict[str, Evidence],
        domain: DomainSpec,
    ) -> AuditResult:
        """LLM-driven audit with knowledge retrieval."""
        # Build context for LLM
        field_text = self._build_field_context(field_states, registry)
        evidence_text = self._build_evidence_context(evidence_store)

        # Get audit prompt from domain pack
        prompt_template = domain.get_prompt("audit")
        if prompt_template is None:
            prompt_template = _DEFAULT_AUDIT_PROMPT

        # Include audit dimensions from domain
        dimensions_text = ""
        if domain.audit_dimensions:
            dimensions_text = "\n\nAudit dimensions:\n" + "\n".join(
                f"- {d}" for d in domain.audit_dimensions
            )

        user_prompt = (
            f"Audit these pWPS field states:\n\n{field_text}\n\n"
            f"Available evidence:\n{evidence_text}"
            f"{dimensions_text}"
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(LLMAuditResponse)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(content=user_prompt),
        ]

        raw = await structured_model.ainvoke(messages)
        response = LLMAuditResponse.model_validate(raw)

        # Convert LLM response to AuditResult
        issues = []
        for llm_issue in response.issues:
            try:
                rule_type = AuditRuleType(llm_issue.rule_type)
            except ValueError:
                rule_type = AuditRuleType.RISK
            try:
                severity = RiskLevel(llm_issue.severity)
            except ValueError:
                severity = RiskLevel.MEDIUM

            issues.append(
                AuditIssue(
                    issue_id=llm_issue.issue_id,
                    rule_type=rule_type,
                    severity=severity,
                    target_fields=llm_issue.target_fields,
                    description=llm_issue.description,
                    recommended_action=llm_issue.recommended_action,
                    repair_target=llm_issue.repair_target,
                    source_rule="llm_audit",
                )
            )

        publishability = self._determine_publishability(issues)

        return AuditResult(
            publishability=publishability,
            issues=issues,
            summary=response.summary or f"{len(issues)} audit issue(s) found.",
            audit_version=self.audit_version,
        )

    def _deterministic_audit(
        self,
        field_states: dict[str, FieldState],
        registry: FieldRegistry,
        evidence_store: dict[str, Evidence] | None = None,
    ) -> AuditResult:
        """Deterministic rule-based audit (legacy fallback)."""
        issues: list[AuditIssue] = []
        issues.extend(_audit_provided_only(field_states, registry))
        issues.extend(_audit_process_consumable_match(field_states))
        issues.extend(_audit_required_fields(field_states, registry))
        issues.extend(_audit_high_risk_auto_confirmation(field_states, registry))
        issues.extend(_audit_low_credibility_evidence(field_states, registry, evidence_store or {}))
        issues.extend(_audit_parameter_completeness(field_states, registry))
        issues.extend(_audit_heat_input_consistency(field_states))
        issues.extend(
            _audit_thermal_evidence_required(field_states, registry, evidence_store or {})
        )
        issues.extend(_audit_position_process_compatibility(field_states))
        issues.extend(_audit_thickness_material_consistency(field_states))

        publishability = self._determine_publishability(issues)

        return AuditResult(
            publishability=publishability,
            issues=issues,
            summary=f"{len(issues)} audit issue(s) found.",
            audit_version=self.audit_version,
        )

    @staticmethod
    def _determine_publishability(issues: list[AuditIssue]) -> Publishability:
        """Determine publishability from audit issues."""
        if any(issue.rule_type is AuditRuleType.HARD for issue in issues):
            return Publishability.REFERENCE_ONLY
        if issues:
            return Publishability.NEEDS_CONFIRMATION
        return Publishability.DRAFT_PUBLISHABLE

    @staticmethod
    def _build_field_context(
        field_states: dict[str, FieldState], registry: FieldRegistry
    ) -> str:
        """Build field context string for LLM audit."""
        lines = []
        for name, state in field_states.items():
            spec = registry.fields.get(name)
            spec_info = ""
            if spec:
                spec_info = (
                    f" (label={spec.label}, type={spec.field_type}, "
                    f"high_risk={spec.high_risk}, "
                    f"inference_policy={spec.inference_policy.value})"
                )
            status = state.status.value if state.status else 'N/A'
            source = state.source_type.value if state.source_type else 'N/A'
            risk = state.risk_level.value if state.risk_level else 'N/A'
            lines.append(
                f"- {name}: value={state.value}, status={status}, "
                f"source={source}, "
                f"risk={risk}, "
                f"evidence_ids={state.evidence_ids}"
                f"{spec_info}"
            )
        return "\n".join(lines)

    @staticmethod
    def _build_evidence_context(evidence_store: dict[str, Evidence]) -> str:
        """Build evidence context string for LLM audit."""
        if not evidence_store:
            return "No evidence available."

        lines = []
        for _eid, ev in evidence_store.items():
            lines.append(
                f"- [{ev.source_type.value}] {ev.source_title}: "
                f"{ev.content[:150]}... "
                f"(credibility={ev.credibility:.2f}, fields={ev.target_fields})"
            )
        return "\n".join(lines[:10])  # Limit to top 10


# ---------------------------------------------------------------------------
# Deterministic audit functions (legacy fallback)
# ---------------------------------------------------------------------------


def _audit_provided_only(
    field_states: dict[str, FieldState], registry: FieldRegistry
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for field_name, state in field_states.items():
        spec = registry.get_field(field_name)
        if (
            spec.inference_policy is InferencePolicy.PROVIDED_ONLY
            and state.value is not None
            and state.source_type is not SourceType.USER_INPUT
        ):
            issues.append(
                AuditIssue(
                    issue_id=f"provided-only-{field_name}",
                    rule_type=AuditRuleType.HARD,
                    severity=RiskLevel.HIGH,
                    target_fields=[field_name],
                    description=f"{field_name} is provided-only but was not user supplied.",
                    recommended_action="Clear the field or request explicit user input.",
                    repair_target="meta_group",
                    source_rule="provided_only_no_model_fill",
                )
            )
    return issues


def _audit_process_consumable_match(field_states: dict[str, FieldState]) -> list[AuditIssue]:
    process = _field_value(field_states, "welding_process")
    consumable = _field_value(field_states, "consumable")
    if process == "GMAW" and consumable == "J422":
        return [
            AuditIssue(
                issue_id="process-consumable-match",
                rule_type=AuditRuleType.HARD,
                severity=RiskLevel.HIGH,
                target_fields=["welding_process", "consumable"],
                description="J422 is not compatible with the current GMAW process.",
                recommended_action="Use a GMAW-compatible wire or change welding process.",
                repair_target="consumable_group",
                source_rule="process_consumable_match",
            )
        ]
    return []


def _audit_required_fields(
    field_states: dict[str, FieldState], registry: FieldRegistry
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for field_name, spec in registry.fields.items():
        state = field_states.get(field_name)
        if spec.required_for_draft and (state is None or state.value in (None, "")):
            issues.append(
                AuditIssue(
                    issue_id=f"missing-required-{field_name}",
                    rule_type=AuditRuleType.COMPLETENESS,
                    severity=RiskLevel.MEDIUM,
                    target_fields=[field_name],
                    description=f"{field_name} is required for draft output.",
                    recommended_action="Confirm the field before treating the draft as complete.",
                    repair_target=spec.group,
                    source_rule="required_field_completeness",
                )
            )
    return issues


def _audit_high_risk_auto_confirmation(
    field_states: dict[str, FieldState], registry: FieldRegistry
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for field_name, state in field_states.items():
        spec = registry.get_field(field_name)
        if (
            spec.high_risk
            and state.status is FieldStatus.CONFIRMED
            and state.needs_human_confirmation
        ):
            issues.append(
                AuditIssue(
                    issue_id=f"high-risk-auto-{field_name}",
                    rule_type=AuditRuleType.RISK,
                    severity=RiskLevel.HIGH,
                    target_fields=[field_name],
                    description=f"{field_name} was auto-confirmed but requires human review.",
                    recommended_action="Have a qualified welding engineer review this value.",
                    repair_target=spec.group,
                    source_rule="high_risk_auto_confirmation",
                )
            )
    return issues


def _audit_low_credibility_evidence(
    field_states: dict[str, FieldState],
    registry: FieldRegistry,
    evidence_store: dict[str, Evidence],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for field_name, state in field_states.items():
        spec = registry.get_field(field_name)
        if (
            spec.high_risk
            and state.status is FieldStatus.CONFIRMED
            and _strongest_credibility(state, evidence_store) < 0.7
        ):
            issues.append(
                AuditIssue(
                    issue_id=f"low-credibility-evidence-{field_name}",
                    rule_type=AuditRuleType.RISK,
                    severity=RiskLevel.HIGH,
                    target_fields=[field_name],
                    description=f"{field_name} relies on low-credibility evidence.",
                    recommended_action=(
                        "Replace model prior with standard, PQR, WPQR, or enterprise evidence."
                    ),
                    repair_target=spec.group,
                    source_rule="low_credibility_evidence",
                )
            )
    return issues


def _strongest_credibility(
    state: FieldState,
    evidence_store: dict[str, Evidence],
) -> float:
    return max(
        (
            evidence_store[evidence_id].credibility
            for evidence_id in state.evidence_ids
            if evidence_id in evidence_store
        ),
        default=0.0,
    )


def _audit_parameter_completeness(
    field_states: dict[str, FieldState], registry: FieldRegistry
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    param_fields = ["current_range", "voltage_range", "travel_speed"]
    missing = [
        f for f in param_fields if f not in field_states or field_states[f].value in (None, "")
    ]
    if missing:
        issues.append(
            AuditIssue(
                issue_id="parameter-completeness",
                rule_type=AuditRuleType.COMPLETENESS,
                severity=RiskLevel.MEDIUM,
                target_fields=missing,
                description=f"Welding parameters missing: {', '.join(missing)}.",
                recommended_action="Confirm all welding parameters before finalizing.",
                repair_target="parameter_group",
                source_rule="parameter_completeness",
            )
        )
    return issues


def _audit_heat_input_consistency(
    field_states: dict[str, FieldState],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    current = _field_value(field_states, "current_range")
    voltage = _field_value(field_states, "voltage_range")
    speed = _field_value(field_states, "travel_speed")
    heat = _field_value(field_states, "heat_input")

    if all(v is not None for v in [current, voltage, speed, heat]):
        try:
            if (
                isinstance(current, dict)
                and isinstance(voltage, dict)
                and isinstance(speed, dict)
                and isinstance(heat, dict)
            ):
                c_avg = (_parse_num(current.get("min")) + _parse_num(current.get("max"))) / 2
                v_avg = (_parse_num(voltage.get("min")) + _parse_num(voltage.get("max"))) / 2
                s_avg = (_parse_num(speed.get("min")) + _parse_num(speed.get("max"))) / 2
                h_avg = (_parse_num(heat.get("min")) + _parse_num(heat.get("max"))) / 2

                if s_avg > 0:
                    calculated = (c_avg * v_avg * 60) / (s_avg * 1000)
                    if abs(calculated - h_avg) > 0.5:
                        issues.append(
                            AuditIssue(
                                issue_id="heat-input-consistency",
                                rule_type=AuditRuleType.RISK,
                                severity=RiskLevel.MEDIUM,
                                target_fields=[
                                    "heat_input",
                                    "current_range",
                                    "voltage_range",
                                    "travel_speed",
                                ],
                                description=(
                                    f"Calculated heat input ({calculated:.1f} kJ/mm) differs "
                                    f"from declared ({h_avg:.1f} kJ/mm)."
                                ),
                                recommended_action="Verify heat input calculation.",
                                repair_target="parameter_group",
                                source_rule="heat_input_consistency",
                            )
                        )
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return issues


def _parse_num(val: object) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"(\d+(?:\.\d+)?)", str(val))
    return float(m.group(1)) if m else 0.0


def _audit_thermal_evidence_required(
    field_states: dict[str, FieldState],
    registry: FieldRegistry,
    evidence_store: dict[str, Evidence],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    thermal_fields = ["preheat_temperature", "interpass_temperature", "pwht"]
    for field_name in thermal_fields:
        state = field_states.get(field_name)
        spec = registry.get_field(field_name)
        if state is None or state.value in (None, ""):
            continue
        if not spec.high_risk:
            continue
        credibility = _strongest_credibility(state, evidence_store)
        if credibility < 0.5:
            issues.append(
                AuditIssue(
                    issue_id=f"thermal-evidence-{field_name}",
                    rule_type=AuditRuleType.RISK,
                    severity=RiskLevel.HIGH,
                    target_fields=[field_name],
                    description=(
                        f"{field_name} has value but lacks credible evidence "
                        f"(credibility={credibility:.2f})."
                    ),
                    recommended_action="Provide standard or PQR evidence for thermal values.",
                    repair_target=spec.group,
                    source_rule="thermal_evidence_required",
                )
            )
    return issues


def _audit_position_process_compatibility(
    field_states: dict[str, FieldState],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    process = _field_value(field_states, "welding_process")
    position = _field_value(field_states, "welding_position")

    if process and position:
        if process == "SAW" and position not in ("flat", "平焊"):
            issues.append(
                AuditIssue(
                    issue_id="position-process-saw",
                    rule_type=AuditRuleType.HARD,
                    severity=RiskLevel.HIGH,
                    target_fields=["welding_process", "welding_position"],
                    description=(
                        "SAW (submerged arc welding) is typically limited to flat position."
                    ),
                    recommended_action=(
                        "Change to flat position or use a different process."
                    ),
                    repair_target="basic_condition_group",
                    source_rule="position_process_compatibility",
                )
            )
    return issues


def _audit_thickness_material_consistency(
    field_states: dict[str, FieldState],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    material = _field_value(field_states, "base_material")
    thickness = _field_value(field_states, "thickness")

    if material and thickness:
        try:
            m = re.search(r"(\d+(?:\.\d+)?)", str(thickness))
            if m:
                t = float(m.group(1))
                if t < 1.0:
                    issues.append(
                        AuditIssue(
                            issue_id="thickness-too-thin",
                            rule_type=AuditRuleType.RISK,
                            severity=RiskLevel.HIGH,
                            target_fields=["thickness"],
                            description=(
                                f"Thickness {thickness} is very thin. "
                                "Special procedures may be required."
                            ),
                            recommended_action="Verify thin-plate welding procedure.",
                            repair_target="basic_condition_group",
                            source_rule="thickness_material_consistency",
                        )
                    )
                if t > 100:
                    issues.append(
                        AuditIssue(
                            issue_id="thickness-very-thick",
                            rule_type=AuditRuleType.RISK,
                            severity=RiskLevel.MEDIUM,
                            target_fields=["thickness"],
                            description=(
                                f"Thickness {thickness} is very thick. "
                                "Multi-pass and PWHT may be required."
                            ),
                            recommended_action="Verify thick-plate welding requirements.",
                            repair_target="basic_condition_group",
                            source_rule="thickness_material_consistency",
                        )
                    )
        except (TypeError, ValueError):
            pass
    return issues


def _field_value(field_states: dict[str, FieldState], field_name: str) -> object:
    state = field_states.get(field_name)
    return None if state is None else state.value
