"""Field summary skill — generates a human-readable summary of confirmed fields."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.schemas import FieldState

_DEFAULT_PROMPT = """You are a welding procedure summarizer.
Given a set of confirmed field states, produce a concise human-readable
summary suitable for a welding engineer review document.

Rules:
- Group fields by their logical category (base material, process, consumable, parameters, thermal)
- Highlight any high-risk fields or fields needing human confirmation
- Use Chinese for field labels where appropriate
- Be concise but complete"""


class FieldSummaryOutput(BaseModel):
    """Structured output for field summary."""

    summary: str = Field(description="Human-readable summary of all confirmed fields")
    highlights: list[str] = Field(
        default_factory=list, description="Key points or risks to highlight"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Fields that are still unknown or empty"
    )


@dataclass(frozen=True)
class FieldSummarySkill:
    skill_name: str = "field_summary"
    skill_version: str = "0.1.0"
    prompt_version: str = "0.1.0"

    async def run(
        self, field_states: dict[str, FieldState], domain: DomainSpec | None = None
    ) -> FieldSummaryOutput:
        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback(field_states)

        prompt = domain.get_prompt("field_summary") if domain else None
        if prompt is None:
            prompt = _DEFAULT_PROMPT

        return await self._llm_summarize(field_states, prompt)

    def _fallback(self, field_states: dict[str, FieldState]) -> FieldSummaryOutput:
        confirmed = []
        missing = []
        highlights = []

        for name, state in field_states.items():
            if state.value is not None:
                confirmed.append(f"{name}: {state.value}")
                if state.needs_human_confirmation:
                    highlights.append(f"{name} 需要人工确认")
                if state.risk_level.value == "high":
                    highlights.append(f"{name} 为高风险字段")
            else:
                missing.append(name)

        return FieldSummaryOutput(
            summary="已确认字段: " + "; ".join(confirmed) if confirmed else "尚无已确认字段",
            highlights=highlights,
            missing_fields=missing,
        )

    async def _llm_summarize(
        self, field_states: dict[str, FieldState], prompt_template: str
    ) -> FieldSummaryOutput:
        field_text = "\n".join(
            f"- {name}: value={state.value}, status={state.status}, "
            f"risk={state.risk_level}, needs_confirmation={state.needs_human_confirmation}"
            for name, state in field_states.items()
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(FieldSummaryOutput)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(content=f"Summarize these welding procedure fields:\n\n{field_text}"),
        ]

        try:
            raw = await structured_model.ainvoke(messages)
            return FieldSummaryOutput.model_validate(raw)
        except Exception:
            return self._fallback(field_states)
