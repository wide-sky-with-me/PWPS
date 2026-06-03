"""Knowledge query tool — searches the local vector store and knowledge base."""

from __future__ import annotations

import json

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class KnowledgeQueryInput(BaseModel):
    """Input for knowledge query tool."""

    query: str = Field(description="Natural language query to search for in the knowledge base.")
    target_fields: list[str] = Field(
        default_factory=list,
        description="Optional list of field names to focus the search on.",
    )


class KnowledgeQueryTool(BaseTool):
    """Search the local knowledge base for welding standards,
    WPS/PQR examples, and technical documents.

    Returns evidence with source type, credibility, and content.
    Use this tool to find standard requirements, material specifications,
    and historical welding procedure examples.
    """

    name: str = "knowledge_query"
    description: str = (
        "Search the local knowledge base for welding standards, WPS/PQR examples, "
        "material specifications, and technical documents. "
        "Input: a natural language query. "
        "Returns: a list of evidence items with source, credibility, and content."
    )
    args_schema: type[BaseModel] = KnowledgeQueryInput

    async def _arun(self, query: str, target_fields: list[str] | None = None) -> str:
        """Execute the knowledge query."""
        from pwps_agent_api.knowledge import KnowledgeService
        from pwps_agent_api.schemas import KnowledgeQuery

        service = KnowledgeService()
        knowledge_query = KnowledgeQuery(
            query=query,
            target_fields=target_fields or [],
        )

        try:
            evidence = await service.evidence_for_fields(knowledge_query.target_fields or [query])
            results = []
            for ev in evidence[:5]:  # Limit to top 5
                results.append({
                    "evidence_id": ev.evidence_id,
                    "source_type": ev.source_type.value,
                    "source_title": ev.source_title,
                    "content": ev.content[:500],
                    "credibility": ev.credibility,
                    "target_fields": ev.target_fields,
                    "limitations": ev.limitations,
                })
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _run(self, query: str, target_fields: list[str] | None = None) -> str:
        """Synchronous fallback (not used in async context)."""
        raise NotImplementedError("Use async version")
