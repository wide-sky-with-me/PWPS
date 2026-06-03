"""Field state query tool — queries the current workflow state."""

from __future__ import annotations

import json

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class FieldStateQueryInput(BaseModel):
    """Input for field state query."""

    field_names: list[str] = Field(
        default_factory=list,
        description="List of field names to query. Empty list returns all fields.",
    )


class FieldStateQuery(BaseTool):
    """Query the current field states in the workflow.

    Returns the current values, status, risk level, and evidence for requested fields.
    Use this tool to understand what fields have been confirmed, what's still unknown,
    and what evidence supports each field.
    """

    name: str = "get_field_state"
    description: str = (
        "Query the current field states in the workflow. "
        "Input: list of field names (empty = all fields). "
        "Returns: current values, status, risk level, and evidence for each field."
    )
    args_schema: type[BaseModel] = FieldStateQueryInput

    # This tool needs access to the workflow state, which is injected at runtime
    _workflow_state: object = None
    _field_registry: object = None

    def bind_state(self, workflow_state: object, field_registry: object) -> "FieldStateQuery":
        """Bind the workflow state and registry to this tool instance."""
        self._workflow_state = workflow_state
        self._field_registry = field_registry
        return self

    async def _arun(self, field_names: list[str] | None = None) -> str:
        """Query field states."""
        if self._workflow_state is None:
            return json.dumps({"error": "No workflow state bound to this tool."})

        state = self._workflow_state
        requested = field_names or list(state.field_states.keys())

        results = []
        for name in requested:
            fs = state.field_states.get(name)
            if fs is None:
                results.append({"field": name, "status": "not_found"})
                continue

            results.append({
                "field": name,
                "value": fs.value,
                "status": fs.status.value if fs.status else None,
                "source_type": fs.source_type.value if fs.source_type else None,
                "risk_level": fs.risk_level.value if fs.risk_level else None,
                "confidence": fs.confidence,
                "needs_human_confirmation": fs.needs_human_confirmation,
                "evidence_ids": fs.evidence_ids,
            })

        return json.dumps(results, ensure_ascii=False)

    def _run(self, field_names: list[str] | None = None) -> str:
        raise NotImplementedError("Use async version")
