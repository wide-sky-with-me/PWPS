"""Field planning skill — generates retrieval plans for field groups.

Refactored to load prompt template from DomainSpec.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.llm import get_chat_model
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.schemas import FieldSpec, FieldState, SourceType

_DEFAULT_PROMPT = """You are a welding knowledge retrieval planner.
Given a set of fields that need values, generate an optimal retrieval plan
that specifies what to search for and from which sources.

Rules:
- Prioritize authoritative sources (standards, PQR, enterprise docs)
- Consider field dependencies (e.g., consumable depends on process and material)
- Include specific search queries for each field
- Flag fields that may need multiple evidence sources"""


class RetrievalTarget(BaseModel):
    """A single retrieval target within a plan."""

    field_name: str = Field(description="The field to retrieve evidence for")
    query: str = Field(description="Search query for this field")
    preferred_sources: list[str] = Field(
        default_factory=list, description="Preferred source types in priority order"
    )
    purpose: str = Field(description="Why this evidence is needed")
    required_evidence_type: str = Field(
        default="standard_reference", description="Type of evidence needed"
    )


class FieldPlanningOutput(BaseModel):
    """Structured output for field planning."""

    targets: list[RetrievalTarget] = Field(description="Retrieval targets")
    summary: str = Field(description="Brief summary of the retrieval plan")


@dataclass(frozen=True)
class FieldPlanningSkill:
    skill_name: str = "field_planning"
    skill_version: str = "0.1.0"
    prompt_version: str = "0.1.0"

    async def run(
        self,
        target_fields: list[str],
        field_specs: dict[str, FieldSpec],
        field_states: dict[str, FieldState],
        domain: DomainSpec | None = None,
    ) -> FieldPlanningOutput:
        settings = get_settings()
        if not settings.llm_api_key:
            return self._fallback(target_fields, field_specs)

        prompt = domain.get_prompt("field_planning") if domain else None
        if prompt is None:
            prompt = _DEFAULT_PROMPT

        return await self._llm_plan(target_fields, field_specs, field_states, prompt)

    def _fallback(
        self, target_fields: list[str], field_specs: dict[str, FieldSpec]
    ) -> FieldPlanningOutput:
        targets = []
        for field_name in target_fields:
            spec = field_specs.get(field_name)
            if spec is None:
                continue
            targets.append(
                RetrievalTarget(
                    field_name=field_name,
                    query=f"{spec.label} {spec.description}",
                    preferred_sources=[
                        SourceType.LOCAL_STANDARD.value,
                        SourceType.LOCAL_DOCUMENT.value,
                        SourceType.TEXTBOOK_OR_HANDBOOK.value,
                    ],
                    purpose=f"Generate candidate values for {spec.label}",
                )
            )

        return FieldPlanningOutput(
            targets=targets,
            summary=f"Retrieval plan for {len(targets)} field(s).",
        )

    async def _llm_plan(
        self,
        target_fields: list[str],
        field_specs: dict[str, FieldSpec],
        field_states: dict[str, FieldState],
        prompt_template: str,
    ) -> FieldPlanningOutput:
        field_text = "\n".join(
            f"- {name}: {field_specs[name].label} ({field_specs[name].description})"
            for name in target_fields
            if name in field_specs
        )
        context = "\n".join(
            f"- {name}={state.value}"
            for name, state in field_states.items()
            if state.value is not None
        )

        model = get_chat_model()
        structured_model = model.with_structured_output(FieldPlanningOutput)

        messages = [
            SystemMessage(content=prompt_template),
            HumanMessage(
                content=(
                    f"Generate a retrieval plan for these fields:\n\n{field_text}\n\n"
                    f"Known context:\n{context}"
                )
            ),
        ]

        try:
            raw = await structured_model.ainvoke(messages)
            return FieldPlanningOutput.model_validate(raw)
        except Exception:
            return self._fallback(target_fields, field_specs)
