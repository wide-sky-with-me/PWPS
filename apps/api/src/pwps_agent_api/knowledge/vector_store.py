"""Milvus-backed vector store provider for knowledge retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.knowledge.reranker import Reranker
from pwps_agent_api.schemas import KnowledgeHit, KnowledgeQuery, SourceType

_DEFAULT_COLLECTION = "pwps_knowledge"
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorStoreProvider:
    """Retrieve knowledge from a Milvus vector store populated by the ingest CLI."""

    collection_name: str = _DEFAULT_COLLECTION
    score_threshold: float = 0.3
    reranker: Reranker = field(default_factory=Reranker)

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeHit]:
        settings = get_settings()
        if not settings.embedding_api_key:
            return []

        try:
            from pymilvus import MilvusClient  # type: ignore[import-untyped]

            from pwps_agent_api.core.llm import get_embedding_model

            embedding = get_embedding_model(settings)
            search_query = self._build_search_query(query)
            query_vector = await embedding.aembed_query(search_query)

            client = MilvusClient(uri=settings.milvus_uri)
            if not client.has_collection(self.collection_name):
                return []

            # Ensure collection is loaded
            try:
                client.load_collection(self.collection_name)
            except Exception:
                pass

            results = client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=10,
                output_fields=[
                    "text",
                    "source_type",
                    "source_id",
                    "title",
                    "source_ref",
                    "section_path",
                    "target_fields",
                    "limitations",
                ],
            )
        except Exception:
            log.debug("Vector store search failed, falling back", exc_info=True)
            return []

        hits: list[KnowledgeHit] = []
        for match in results[0]:
            entity = match.get("entity", {})
            score = match.get("distance", 0.0)
            if score < self.score_threshold:
                continue
            hits.append(_entity_to_hit(entity, score))

        # Apply reranker if available
        return await self.reranker.rerank(search_query, hits, settings)

    def _build_search_query(self, query: KnowledgeQuery) -> str:
        parts = list(query.target_fields)
        if query.query:
            parts.append(query.query)
        if query.purpose:
            parts.append(query.purpose)
        return " ".join(parts)


def _entity_to_hit(entity: dict[str, object], score: float) -> KnowledgeHit:
    source_type_str = str(entity.get("source_type", "local_document"))
    try:
        source_type = SourceType(source_type_str)
    except ValueError:
        source_type = SourceType.LOCAL_DOCUMENT

    section_path_raw = str(entity.get("section_path", ""))
    section_path = section_path_raw.split(",") if section_path_raw else []
    target_fields_raw = str(entity.get("target_fields", ""))
    target_fields = target_fields_raw.split(",") if target_fields_raw else []

    source_ref = entity.get("source_ref")
    limitations = entity.get("limitations")

    return KnowledgeHit(
        source_type=source_type,
        source_id=str(entity.get("source_id", "unknown")),
        title=str(entity.get("title", "")),
        source_ref=str(source_ref) if source_ref else None,
        section_path=section_path,
        content=str(entity.get("text", "")),
        target_fields=target_fields,
        score=score,
        limitations=str(limitations) if limitations else None,
    )
