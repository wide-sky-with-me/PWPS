"""Virtual welding engineer decision actor.

Uses LLM to evaluate candidate values against evidence and field
dependencies, then selects the best candidate or requests more info.
Falls back to deterministic first-candidate selection when no LLM is
configured.
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.actors.base import DecisionActor
from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.schemas import (
    DecisionContext,
    DecisionResult,
    DecisionType,
    RiskLevel,
)

_SYSTEM_PROMPT = """You are a qualified welding engineer reviewing candidate values
for a pWPS (preliminary Welding Procedure Specification).

Given a set of candidate values for each field, evaluate them against:
1. The supporting evidence quality and relevance
2. Domain constraints (e.g., GMAW requires specific wire types, not SMAW electrodes)
3. Cross-field dependencies (e.g., current range must match consumable diameter)
4. Risk level of each field

For each field, select the BEST candidate (by index) and explain why.
If no candidate is adequate, mark the field as needing more information.

Output your evaluation as structured JSON."""


class FieldEvaluation(BaseModel):
    """Evaluation result for a single field."""

    field_name: str = Field(description="The field name")
    selected_index: int = Field(
        default=0, ge=0, description="Index of the selected candidate (0-based)"
    )
    reason: str = Field(description="Why this candidate was selected")
    risk_notes: list[str] = Field(default_factory=list, description="Risk notes or caveats")
    needs_more_info: bool = Field(default=False, description="True if no candidate is adequate")


class ActorDecision(BaseModel):
    """Structured decision output from the virtual actor."""

    evaluations: list[FieldEvaluation] = Field(description="Per-field evaluations")
    overall_risk: str = Field(default="medium", description="Overall risk: low, medium, or high")


class VirtualDecisionActor(DecisionActor):
    """LLM-backed actor that evaluates and selects from candidates."""

    @property
    def actor_name(self) -> str:
        return "virtual_decision_actor"

    async def decide(self, context: DecisionContext) -> DecisionResult:
        if not context.candidate_bundle:
            return DecisionResult(
                decision_type=DecisionType.REQUEST_MORE_INFO,
                reason="No candidates were provided.",
                risk_level=RiskLevel.HIGH,
                requires_replan=True,
            )

        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback_decide(context)

        return await self._llm_decide(context)

    def _fallback_decide(self, context: DecisionContext) -> DecisionResult:
        """Deterministic fallback: accept first candidate for each field."""
        selected_values: dict[str, Any] = {}
        concerns: list[str] = []

        for field_name, field_candidates in context.candidate_bundle.items():
            if not field_candidates:
                concerns.append(f"No candidate available for {field_name}.")
                continue
            selected_values[field_name] = field_candidates[0]["value"]
            concerns.extend(field_candidates[0].get("risks", []))

        if not selected_values:
            return DecisionResult(
                decision_type=DecisionType.REQUEST_MORE_INFO,
                reason="No acceptable candidates were available.",
                concerns=concerns,
                risk_level=RiskLevel.HIGH,
                requires_replan=True,
            )

        return DecisionResult(
            decision_type=DecisionType.ACCEPT_RECOMMENDED,
            selected_values=selected_values,
            reason="Accepted deterministic recommended candidates.",
            concerns=concerns,
            risk_level=RiskLevel.MEDIUM if concerns else RiskLevel.LOW,
        )

    async def _llm_decide(self, context: DecisionContext) -> DecisionResult:
        """LLM-powered evaluation of candidates."""
        # Build evaluation prompt
        prompt_parts = [
            f"Run ID: {context.run_id}",
            f"Target fields: {', '.join(context.target_fields)}",
            "",
        ]

        # Add evidence summary
        if context.evidence_summary:
            prompt_parts.append("## Evidence")
            for ev in context.evidence_summary[:5]:
                prompt_parts.append(
                    f"- [{ev.get('source_type', 'unknown')}] "
                    f"{ev.get('source_title', 'N/A')}: {ev.get('content', '')[:200]}"
                )
            prompt_parts.append("")

        # Add candidates
        prompt_parts.append("## Candidates to evaluate")
        for field_name, candidates in context.candidate_bundle.items():
            prompt_parts.append(f"\n### {field_name}")
            for i, c in enumerate(candidates):
                prompt_parts.append(
                    f"  [{i}] value={c['value']}, confidence={c.get('confidence', '?')}, "
                    f"reason={c.get('reason', 'N/A')}"
                )
                if c.get("risks"):
                    prompt_parts.append(f"       risks={c['risks']}")
                if c.get("evidence_ids"):
                    prompt_parts.append(f"       evidence={c['evidence_ids']}")

        # Add recommended values
        if context.recommended_values:
            prompt_parts.append(f"\n## System recommended: {context.recommended_values}")

        prompt = "\n".join(prompt_parts)

        model = get_chat_model()
        structured_model = model.with_structured_output(ActorDecision, method="json_mode")

        try:
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            raw = await structured_model.ainvoke(messages)
            decision = ActorDecision.model_validate(raw)
        except Exception:
            return self._fallback_decide(context)

        # Convert to DecisionResult
        selected_values: dict[str, Any] = {}
        concerns: list[str] = []

        for eval in decision.evaluations:
            candidates = context.candidate_bundle.get(eval.field_name, [])
            if eval.needs_more_info or not candidates:
                concerns.append(f"{eval.field_name}: needs more information. {eval.reason}")
                continue

            idx = min(eval.selected_index, len(candidates) - 1)
            selected_values[eval.field_name] = candidates[idx]["value"]
            concerns.extend(eval.risk_notes)

        if not selected_values:
            return DecisionResult(
                decision_type=DecisionType.REQUEST_MORE_INFO,
                reason="LLM determined no candidates are adequate.",
                concerns=concerns,
                risk_level=RiskLevel.HIGH,
                requires_replan=True,
            )

        risk_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}
        risk_level = risk_map.get(decision.overall_risk, RiskLevel.MEDIUM)

        return DecisionResult(
            decision_type=DecisionType.ACCEPT_RECOMMENDED,
            selected_values=selected_values,
            reason="LLM evaluated and selected best candidates.",
            concerns=concerns,
            risk_level=risk_level,
        )
