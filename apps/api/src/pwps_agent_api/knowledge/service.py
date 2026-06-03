from dataclasses import dataclass, field

from pwps_agent_api.knowledge.local_document import LocalDocumentProvider
from pwps_agent_api.knowledge.model_prior import ModelPriorKnowledgeService
from pwps_agent_api.knowledge.normalizer import EvidenceNormalizer
from pwps_agent_api.knowledge.vector_store import VectorStoreProvider
from pwps_agent_api.schemas import Evidence, KnowledgeQuery, SourceType

_SOURCE_PRIORITY = {
    SourceType.USER_INPUT: 100,
    SourceType.ENTERPRISE_STANDARD: 90,
    SourceType.LOCAL_STANDARD: 80,
    SourceType.STRUCTURED_KB: 70,
    SourceType.HISTORY_PQR: 70,
    SourceType.HISTORY_WPS: 65,
    SourceType.TEXTBOOK_OR_HANDBOOK: 60,
    SourceType.LOCAL_DOCUMENT: 55,
    SourceType.WEB: 40,
    SourceType.MODEL_PRIOR: 10,
}


@dataclass(frozen=True)
class KnowledgeService:
    local_documents: LocalDocumentProvider = field(default_factory=LocalDocumentProvider)
    vector_store: VectorStoreProvider = field(default_factory=VectorStoreProvider)
    model_prior: ModelPriorKnowledgeService = field(default_factory=ModelPriorKnowledgeService)
    normalizer: EvidenceNormalizer = field(default_factory=EvidenceNormalizer)

    async def evidence_for_fields(self, target_fields: list[str]) -> list[Evidence]:
        query = KnowledgeQuery(target_fields=target_fields)

        # Try vector store first (if Milvus is available)
        vector_hits = await self.vector_store.search(query)
        vector_evidence = await self.normalizer.normalize(query, vector_hits)

        # Fall back to local documents for fields not covered by vector store
        covered_fields = {
            field_name for item in vector_evidence for field_name in item.target_fields
        }
        uncovered_fields = [f for f in target_fields if f not in covered_fields]

        local_evidence: list[Evidence] = []
        if uncovered_fields:
            local_query = KnowledgeQuery(target_fields=uncovered_fields)
            local_hits = await self.local_documents.search(local_query)
            local_evidence = await self.normalizer.normalize(local_query, local_hits)

        covered_fields.update(
            field_name for item in local_evidence for field_name in item.target_fields
        )

        # Model prior for any remaining uncovered fields
        fallback_fields = [
            field_name for field_name in target_fields if field_name not in covered_fields
        ]
        prior_evidence = await self.model_prior.evidence_for_fields(fallback_fields)

        return [*vector_evidence, *local_evidence, *prior_evidence]


def strongest_evidence_source(
    evidence_store: dict[str, Evidence],
    evidence_ids: list[str],
) -> SourceType:
    sources = [
        evidence_store[evidence_id].source_type
        for evidence_id in evidence_ids
        if evidence_id in evidence_store
    ]
    return max(sources, key=lambda source: _SOURCE_PRIORITY[source], default=SourceType.MODEL_PRIOR)
