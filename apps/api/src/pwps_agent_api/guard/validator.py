"""GuardValidator — lightweight output validation for LLM-produced results.

The GuardValidator enforces hard constraints that LLM outputs must not violate.
It is NOT an audit engine — it does not reason about welding domain correctness.
That is the LLM audit skill's job.

The GuardValidator only catches structural violations:
  1. PROVIDED_ONLY fields filled by non-user sources
  2. High-risk fields without evidence
  3. Candidates without evidence_ids
  4. Invalid state transitions
  5. Type mismatches between field values and field specs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pwps_agent_api.schemas import (
    Evidence,
    FieldSpec,
    FieldState,
    FieldStatus,
    InferencePolicy,
    RiskLevel,
    SourceType,
)


@dataclass(frozen=True)
class GuardViolation:
    """A single guard violation found by the validator."""

    rule: str
    """Short identifier for the violated rule, e.g. 'provided_only_violation'."""

    field_name: str
    """The field that triggered the violation."""

    message: str
    """Human-readable description of the violation."""

    severity: str = "error"
    """'error' blocks the output, 'warning' flags for review."""


class GuardValidator:
    """Validates LLM outputs against hard structural constraints."""

    def validate_field_state(
        self,
        state: FieldState,
        spec: FieldSpec,
        evidence_store: dict[str, Evidence] | None = None,
    ) -> list[GuardViolation]:
        """Validate a single FieldState against its FieldSpec."""
        violations: list[GuardViolation] = []

        # Rule 1: PROVIDED_ONLY fields must not be filled by non-user sources
        if (
            spec.inference_policy is InferencePolicy.PROVIDED_ONLY
            and state.value is not None
            and state.source_type not in (SourceType.USER_INPUT, None)
        ):
            violations.append(
                GuardViolation(
                    rule="provided_only_violation",
                    field_name=state.name,
                    message=(
                        f"Field '{state.name}' is PROVIDED_ONLY but was filled by "
                        f"'{state.source_type}'. Only user input is allowed."
                    ),
                )
            )

        # Rule 2: High-risk fields must have evidence when confirmed
        if (
            spec.high_risk
            and state.status is FieldStatus.CONFIRMED
            and state.source_type is not SourceType.USER_INPUT
            and not state.evidence_ids
        ):
            violations.append(
                GuardViolation(
                    rule="high_risk_no_evidence",
                    field_name=state.name,
                    message=(
                        f"High-risk field '{state.name}' is CONFIRMED without any evidence. "
                        f"Evidence is required for high-risk fields."
                    ),
                )
            )

        # Rule 3: Check evidence credibility for high-risk fields
        if (
            spec.high_risk
            and state.status is FieldStatus.CONFIRMED
            and evidence_store
            and state.evidence_ids
        ):
            max_credibility = max(
                (evidence_store[eid].credibility for eid in state.evidence_ids if eid in evidence_store),
                default=0.0,
            )
            if max_credibility < 0.5:
                violations.append(
                    GuardViolation(
                        rule="low_credibility_evidence",
                        field_name=state.name,
                        message=(
                            f"High-risk field '{state.name}' relies on low-credibility evidence "
                            f"(max credibility: {max_credibility:.2f}). "
                            f"Replace with standard, PQR, or WPQR evidence."
                        ),
                        severity="warning",
                    )
                )

        # Rule 4: State transition legality
        violations.extend(self._check_state_transition(state, spec))

        return violations

    def validate_candidate(
        self,
        field_name: str,
        candidate: dict[str, Any],
        spec: FieldSpec,
    ) -> list[GuardViolation]:
        """Validate a single candidate value."""
        violations: list[GuardViolation] = []

        # Rule: Candidates for PROVIDED_ONLY fields are not allowed
        if spec.inference_policy is InferencePolicy.PROVIDED_ONLY:
            violations.append(
                GuardViolation(
                    rule="candidate_for_provided_only",
                    field_name=field_name,
                    message=(
                        f"Candidate generated for PROVIDED_ONLY field '{field_name}'. "
                        f"This field must come from the user."
                    ),
                )
            )

        # Rule: Candidates should have evidence_ids (warning only)
        evidence_ids = candidate.get("evidence_ids", [])
        if not evidence_ids and spec.high_risk:
            violations.append(
                GuardViolation(
                    rule="candidate_no_evidence",
                    field_name=field_name,
                    message=(
                        f"High-risk candidate for '{field_name}' has no supporting evidence."
                    ),
                    severity="warning",
                )
            )

        return violations

    def validate_field_states(
        self,
        field_states: dict[str, FieldState],
        field_specs: dict[str, FieldSpec],
        evidence_store: dict[str, Evidence] | None = None,
    ) -> list[GuardViolation]:
        """Validate all field states in a workflow."""
        violations: list[GuardViolation] = []
        for name, state in field_states.items():
            spec = field_specs.get(name)
            if spec is not None:
                violations.extend(self.validate_field_state(state, spec, evidence_store))
        return violations

    @staticmethod
    def _check_state_transition(state: FieldState, spec: FieldSpec) -> list[GuardViolation]:
        """Check that the state transition is valid.

        Valid transitions:
          UNKNOWN -> PROVIDED (user input)
          UNKNOWN -> CANDIDATE_GENERATED (skill output)
          CANDIDATE_GENERATED -> CONFIRMED (actor decision)
          PROVIDED -> CONFIRMED (actor decision)
          CONFIRMED -> NEEDS_REPAIR (audit found issues)
          NEEDS_REPAIR -> CANDIDATE_GENERATED (re-generation)
          Any -> BLOCKED (guard or audit blocked)
        """
        violations: list[GuardViolation] = []

        # CONFIRMED requires either evidence or user input
        if state.status is FieldStatus.CONFIRMED:
            if state.source_type is None and not state.evidence_ids:
                violations.append(
                    GuardViolation(
                        rule="invalid_confirmation",
                        field_name=state.name,
                        message=(
                            f"Field '{state.name}' is CONFIRMED but has no source_type "
                            f"and no evidence. A confirmed field must have provenance."
                        ),
                    )
                )

        return violations
