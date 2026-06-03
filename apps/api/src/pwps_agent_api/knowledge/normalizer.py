from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from pwps_agent_api.schemas import Evidence, KnowledgeHit, KnowledgeQuery, SourceType


@dataclass(frozen=True)
class EvidenceNormalizer:
    async def normalize(self, query: KnowledgeQuery, hits: list[KnowledgeHit]) -> list[Evidence]:
        requested_fields = set(query.target_fields)
        retrieved_at = datetime.now(UTC).isoformat()
        return [
            Evidence(
                evidence_id=_evidence_id(hit, requested_fields),
                source_type=hit.source_type,
                source_title=hit.title,
                source_ref=hit.source_ref,
                section_path=hit.section_path,
                content=hit.content,
                target_fields=[
                    field_name for field_name in hit.target_fields if field_name in requested_fields
                ],
                credibility=_credibility_for(hit.source_type),
                limitations=hit.limitations,
                retrieved_at=retrieved_at,
                metadata={
                    **hit.metadata,
                    "page": hit.page,
                    "table_id": hit.table_id,
                    "score": hit.score,
                },
            )
            for hit in hits
        ]


def _credibility_for(source_type: SourceType) -> float:
    return {
        SourceType.ENTERPRISE_STANDARD: 0.9,
        SourceType.LOCAL_STANDARD: 0.8,
        SourceType.LOCAL_DOCUMENT: 0.65,
        SourceType.TEXTBOOK_OR_HANDBOOK: 0.65,
    }.get(source_type, 0.5)


def _evidence_id(hit: KnowledgeHit, requested_fields: set[str]) -> str:
    target_fields = sorted(requested_fields.intersection(hit.target_fields))
    digest = sha256(",".join(target_fields).encode()).hexdigest()[:12]
    return f"local-document-{hit.source_id}-{digest}"
