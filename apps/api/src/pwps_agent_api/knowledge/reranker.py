"""Reranker using SiliconFlow's reranking API (OpenAI-compatible)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from pwps_agent_api.core.config import Settings, get_settings
from pwps_agent_api.schemas import KnowledgeHit

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Reranker:
    """Rerank KnowledgeHits by relevance to the query using a cross-encoder model."""

    top_n: int = 5

    async def rerank(
        self,
        query: str,
        hits: list[KnowledgeHit],
        settings: Settings | None = None,
    ) -> list[KnowledgeHit]:
        if not hits:
            return []

        s = settings or get_settings()
        if not s.reranker_api_key:
            return hits[: self.top_n]

        try:
            documents = [hit.content for hit in hits]
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{s.reranker_base_url}/rerank",
                    json={
                        "model": s.reranker_model,
                        "query": query,
                        "documents": documents,
                        "top_n": min(self.top_n, len(hits)),
                    },
                    headers={"Authorization": f"Bearer {s.reranker_api_key}"},
                    timeout=15,
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
        except Exception:
            log.debug("Reranker API failed, returning original order", exc_info=True)
            return hits[: self.top_n]

        # Map results back to hits by index
        reranked: list[KnowledgeHit] = []
        for item in results:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(hits):
                hit = hits[idx]
                # Update score with reranker relevance
                reranked.append(
                    KnowledgeHit(
                        source_type=hit.source_type,
                        source_id=hit.source_id,
                        title=hit.title,
                        source_ref=hit.source_ref,
                        section_path=hit.section_path,
                        content=hit.content,
                        target_fields=hit.target_fields,
                        page=hit.page,
                        table_id=hit.table_id,
                        score=item.get("relevance_score", hit.score),
                        limitations=hit.limitations,
                        metadata=hit.metadata,
                    )
                )
        return reranked
