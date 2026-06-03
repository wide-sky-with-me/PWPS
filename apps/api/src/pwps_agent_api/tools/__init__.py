"""Unified tool set for LLM Skills.

These tools are framework-provided and available to all domain packs.
LLM Skills can call them during reasoning to retrieve knowledge,
compute values, and query workflow state.
"""

from pwps_agent_api.tools.calculator import HeatInputCalculator
from pwps_agent_api.tools.field_state import FieldStateQuery
from pwps_agent_api.tools.knowledge import KnowledgeQueryTool
from pwps_agent_api.tools.web_search import WebSearchTool

__all__ = [
    "HeatInputCalculator",
    "FieldStateQuery",
    "KnowledgeQueryTool",
    "WebSearchTool",
]


def get_all_tools() -> list[object]:
    """Return all framework-provided tools as a list."""
    return [
        KnowledgeQueryTool(),
        WebSearchTool(),
        HeatInputCalculator(),
        FieldStateQuery(),
    ]
