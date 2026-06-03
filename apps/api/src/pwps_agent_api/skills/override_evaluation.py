"""Override evaluation skill — evaluates user overrides against system recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.schemas import FieldState

_DEFAULT_PROMPT = """You are a welding procedure override evaluator.
When a user overrides a system-recommended value, evaluate whether the
override is safe and compatible with other confirmed fields.

Rules:
- Check for process-consumable compatibility (e.g., GMAW requires GMAW-compatible wire)
- Check for material-consumable compatibility
- Check parameter ranges against material and thickness
- Flag any conflicts or risks introduced by the override
- Recommend whether to accept, reject, or request more information"""


class OverrideEvaluationOutput(BaseModel):
    """Structured output for override evaluation."""

    is_safe: bool = Field(description="Whether the override is safe to accept")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, high")
    conflicts: list[str] = Field(default_factory=list, description="Conflicts with other fields")
    recommendation: str = Field(description="Recommendation: accept, reject, or request_more_info")
    reasoning: str = Field(description="Explanation of the evaluation")


@dataclass(frozen=True)
class OverrideEvaluationSkill:
    skill_name: str = "override_evaluation"
    skill_version: str = "0.1.0"
    prompt_version: str = "0.1.0"

    async def run(
        self,
        field_name: str,
        override_value: str,
        original_value: str | None,
        field_states: dict[str, FieldState],
        domain: DomainSpec | None = None,
    ) -> OverrideEvaluationOutput:
        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback(field_name, override_value, field_states)

        prompt = domain.get_prompt("override_evaluation") if domain else None
        if prompt is None:
            prompt = _DEFAULT_PROMPT

        return await self._llm_evaluate(
            field_name, override_value, original_value, field_states, prompt
        )

    def _fallback(
        self,
        field_name: str,
        override_value: str,
        field_states: dict[str, FieldState],
    ) -> OverrideEvaluationOutput:
        # Check for known hard conflicts
        process = None
        for name, state in field_states.items():
            if name == "welding_process" and state.value:
                process = str(state.value)

        if field_name == "consumable" and process == "GMAW" and override_value == "J422":
            return OverrideEvaluationOutput(
                is_safe=False,
                risk_level="high",
                conflicts=["J422 is a SMAW electrode, incompatible with GMAW"],
                recommendation="reject",
                reasoning=(
                    "J422 cannot be used with GMAW. Use ER50-6 or another GMAW-compatible wire."
                ),
            )

        return OverrideEvaluationOutput(
            is_safe=True,
            risk_level="medium",
            recommendation="accept",
            reasoning=(
                f"Override of {field_name} to {override_value} accepted. Manual review recommended."
            ),
        )

    async def _llm_evaluate(
        self,
        field_name: str,
        override_value: str,
        original_value: str | None,
        field_states: dict[str, FieldState],
        prompt_template: str,
    ) -> OverrideEvaluationOutput:
        context = "\n".join(
            f"- {name}: {state.value} (status={state.status}, risk={state.risk_level})"
            for name, state in field_states.items()
            if state.value is not None
        )

        user_prompt = (
            f"Evaluate this override:\n"
            f"Field: {field_name}\n"
            f"Original value: {original_value}\n"
            f"Override value: {override_value}\n\n"
            f"Other confirmed fields:\n{context}"
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(OverrideEvaluationOutput)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(content=user_prompt),
        ]

        try:
            raw = await structured_model.ainvoke(messages)
            return OverrideEvaluationOutput.model_validate(raw)
        except Exception:
            return self._fallback(field_name, override_value, field_states)
