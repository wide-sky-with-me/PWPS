"""Risk summary skill — generates a comprehensive risk report."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.schemas import AuditResult, FieldState

_DEFAULT_PROMPT = """You are a welding procedure risk analyst.
Given audit results and field states, produce a comprehensive risk summary
suitable for a welding engineer review.

Rules:
- Categorize risks by severity (critical, high, medium, low)
- Explain the practical implications of each risk
- Suggest mitigation actions
- Use Chinese where appropriate for field labels
- Be concise but actionable"""


class RiskItem(BaseModel):
    """A single risk item in the summary."""

    category: str = Field(description="Risk category: critical, high, medium, low")
    field_name: str = Field(description="Affected field")
    description: str = Field(description="Risk description")
    mitigation: str = Field(description="Suggested mitigation action")


class RiskSummaryOutput(BaseModel):
    """Structured output for risk summary."""

    overall_risk: str = Field(description="Overall risk level: low, medium, high, critical")
    risks: list[RiskItem] = Field(description="Individual risk items")
    summary: str = Field(description="Executive summary of risks")
    publishability_note: str = Field(description="Note about publishability implications")


@dataclass(frozen=True)
class RiskSummarySkill:
    skill_name: str = "risk_summary"
    skill_version: str = "0.1.0"
    prompt_version: str = "0.1.0"

    async def run(
        self,
        audit_result: AuditResult,
        field_states: dict[str, FieldState],
        domain: DomainSpec | None = None,
    ) -> RiskSummaryOutput:
        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback(audit_result, field_states)

        prompt = domain.get_prompt("risk_summary") if domain else None
        if prompt is None:
            prompt = _DEFAULT_PROMPT

        return await self._llm_summarize(audit_result, field_states, prompt)

    def _fallback(
        self,
        audit_result: AuditResult,
        field_states: dict[str, FieldState],
    ) -> RiskSummaryOutput:
        risks = []
        for issue in audit_result.issues:
            category = {
                "high": "critical" if issue.rule_type == "hard" else "high",
                "medium": "medium",
                "low": "low",
            }.get(issue.severity.value, "medium")

            risks.append(
                RiskItem(
                    category=category,
                    field_name=", ".join(issue.target_fields),
                    description=issue.description,
                    mitigation=issue.recommended_action,
                )
            )

        # Add high-risk fields without evidence
        for name, state in field_states.items():
            if state.risk_level.value == "high" and state.needs_human_confirmation:
                if not any(r.field_name == name for r in risks):
                    risks.append(
                        RiskItem(
                            category="high",
                            field_name=name,
                            description=(
                                f"{name} is high-risk and was auto-confirmed without human review"
                            ),
                            mitigation=("Have a qualified welding engineer review this value"),
                        )
                    )

        overall = "low"
        if any(r.category == "critical" for r in risks):
            overall = "critical"
        elif any(r.category == "high" for r in risks):
            overall = "high"
        elif risks:
            overall = "medium"

        return RiskSummaryOutput(
            overall_risk=overall,
            risks=risks,
            summary=f"{len(risks)} risk(s) identified. {audit_result.summary}",
            publishability_note=f"Publishability: {audit_result.publishability.value}",
        )

    async def _llm_summarize(
        self,
        audit_result: AuditResult,
        field_states: dict[str, FieldState],
        prompt_template: str,
    ) -> RiskSummaryOutput:
        audit_text = "\n".join(
            f"- [{issue.severity}] {issue.description} -> {issue.recommended_action}"
            for issue in audit_result.issues
        )
        fields_text = "\n".join(
            f"- {name}: value={state.value}, risk={state.risk_level}"
            for name, state in field_states.items()
            if state.value is not None
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(RiskSummaryOutput)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(
                content=(
                    f"Audit issues:\n{audit_text}\n\n"
                    f"Confirmed fields:\n{fields_text}\n\n"
                    f"Publishability: {audit_result.publishability.value}"
                )
            ),
        ]

        try:
            raw = await structured_model.ainvoke(messages)
            return RiskSummaryOutput.model_validate(raw)
        except Exception:
            return self._fallback(audit_result, field_states)
